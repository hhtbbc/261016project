"""Plot saved real comparisons and independently recalculate paired metrics."""
from pathlib import Path
import sys,json,csv,hashlib,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_swarm_tiegcm_2021_observation import F,O,GROUPS,table
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from netCDF4 import Dataset
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from atmosphere.tiegcm_density_provider import DATUM
from astropy.time import Time
from prepare_fourcastden_swarm_observation_v1 import sha,dump

def main():
    z=np.load(O/'aligned_local.npz');v=z['values'];obs=z['observed'];m=z['common'];ts=z['utc'];h=(ts-ts[0])/np.timedelta64(1,'h');names=list(GROUPS)
    metrics=list(csv.DictReader((O/'metrics.csv').open()));glob=[r for r in metrics if r['region']=='all']
    # Independent direct arithmetic, not calling production metric helper.
    for r in glob:
        x=v['ABDE'.index(r['mapping']),names.index(r['group']),m];y=obs[m];e=x-y
        assert np.isclose(float(r['RMSE']),np.sqrt(np.dot(e,e)/len(e)),rtol=1e-14)
        assert np.isclose(float(r['relative_RMS']),np.linalg.norm(e/y)/np.sqrt(len(e)),rtol=1e-14)
    inputs=json.loads((F/'inputs.json').read_text());protected={};small=[]
    for group,entry in inputs.items():
        d=ROOT/'experiments'/GROUPS[group]
        for e in entry['files']:
            p=d/e['file'];assert sha(p)==e['SHA256'];protected[str(p.relative_to(ROOT))]=e['SHA256']
        p=HourlyTiegcmObservation([d/e['file'] for e in entry['files']],{e['file']:e['SHA256'] for e in entry['files']},'2021-03-24','2021-03-25',group)
        # Grid-point query independent direct column log-density at midpoint height.
        height=float((p.arrays[0][0][20,18,10]+p.arrays[0][0][21,18,10])/2)
        q=p.query_native(Time('2021-03-24'),p.lat[18],p.lon[10],height,datum=DATUM)
        direct=np.exp(np.interp(height,p.arrays[0][0][:,18,10],np.log(p.arrays[0][1][:,18,10])))
        assert q.valid and np.isclose(q.rho_kg_m3,direct,rtol=1e-13)
        for zz,rr in p.arrays:
            assert np.isfinite(zz).all() and np.isfinite(rr).all() and (rr>0).all() and (np.diff(zz,axis=0)>0).all()
        small.append(dict(group=group,gridpoint_query=q.rho_kg_m3,independent_column=direct))
    caption='2021-03-24 UTC | PROVISIONAL | DNSAPOD 0301 | shared N='+str(int(m.sum()))
    figs=[]
    def save(fig,name):
        fig.suptitle(caption,fontsize=10);fig.tight_layout(rect=[0,0,1,.95]);fig.savefig(O/name,dpi=160);plt.close(fig);figs.append(name)
    for gi,label in [(0,'A'),(1,'B')]:
        fig,ax=plt.subplots(figsize=(11,4));ax.plot(h,obs*1e13,color='black',lw=.8,label='Swarm instantaneous')
        for k in [gi,gi+2]:ax.plot(h,v[0,k]*1e13,lw=.8,label=names[k]+' mapping A')
        ax.set(xlabel='UTC hour',ylabel='Density (1e-13 kg/m3)');ax.legend();save(fig,'timeseries_'+label+'.png')
    fig,axs=plt.subplots(2,2,figsize=(9,8));lim=np.nanmax(np.r_[obs[m],v[0,:,m].ravel()])*1e13
    for gi,ax in enumerate(axs.flat):
        ax.scatter(obs[m]*1e13,v[0,gi,m]*1e13,s=2,alpha=.3);ax.plot([0,lim],[0,lim],'k--');ax.set(title=names[gi]+' mapping A',xlabel='Swarm (1e-13 kg/m3)',ylabel='TIE-GCM (1e-13 kg/m3)')
    save(fig,'scatter.png')
    fig,axs=plt.subplots(1,3,figsize=(12,4))
    for ax,key,scale,title in zip(axs,['RMSE','bias','relative_RMS'],[1e13,1e13,100],['RMSE (1e-13 kg/m3)','Bias (1e-13 kg/m3)','Relative RMS (%)']):
        ax.bar(names,[float(next(r for r in glob if r['mapping']=='A' and r['group']==g)[key])*scale for g in names]);ax.set_title(title+' / A')
    save(fig,'spinup_metrics.png')
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    for gi,g in enumerate(names):
        for ax,key,scale in zip(axs,['relative_RMS','bias'],[100,1e13]):ax.plot(list('ABDE'),[float(next(r for r in glob if r['mapping']==a and r['group']==g)[key])*scale for a in 'ABDE'],'o-',label=g)
    axs[0].set_ylabel('Relative RMS (%)');axs[1].set_ylabel('Bias (1e-13 kg/m3)')
    for ax in axs:ax.set_xlabel('Conditional coordinate mapping');ax.legend()
    save(fig,'coordinate_sensitivity.png')
    table(O/'figure_sources.csv',[dict(figure=x,input='aligned_local.npz; metrics.csv',date='2021-03-24',status='PROVISIONAL') for x in figs])
    dump(F/'independent_audit.json',dict(PASS=True,verified_input_files=len(protected),protected=protected,small_actual_checks=small,metrics_independently_recalculated=16,common_samples=int(m.sum()),quality_pass=int(z['quality'].sum()),no_model_launches=True))
    lines=['# 2021年7/14天预热与同期Swarm-A密度条件对照','','实验标签：`swarm_tiegcm_2021_spinup_observation_v1`。日期2021-03-24 00:00—23:59:30 UTC；使用03-25 00时模型帧合法插值。PROVISIONAL / HINDCAST。','','## 真实结果（全部16方案共同样本）','','密度单位kg/m³；RMSE、Bias表中以1e-13 kg/m³表示。相关系数不代表绝对无偏精度。','','|映射|轨迹|N|RMSE|Bias|相对RMS %|Pearson|','|---|---|---:|---:|---:|---:|---:|']
    for r in glob:lines.append(f"|{r['mapping']}|{r['group']}|{r['n']}|{float(r['RMSE'])*1e13:.5f}|{float(r['bias'])*1e13:.5f}|{float(r['relative_RMS'])*100:.4f}|{float(r['Pearson']):.5f}|")
    lines+=['','## 7天与14天的比较','','正降低为改善，负值为恶化；不按指标择优选择映射。']
    for a in 'ABDE':
        for initial in 'AB':
            x=next(r for r in glob if r['mapping']==a and r['group']==initial+'7');y=next(r for r in glob if r['mapping']==a and r['group']==initial+'14')
            lines.append(f"- {a}映射、{initial}初态：RMSE相对降低{100*(1-float(y['RMSE'])/float(x['RMSE'])):.4f}%；相对RMS降低{100*(1-float(y['relative_RMS'])/float(x['relative_RMS'])):.4f}%。")
    lines+=['','## 数据、方法与有效域','','实际ESA目录确认唯一0301日文件，下载记录与CRC/SHA见experiments本标签/downloads.json；实际CDF TIME SYSTEM=UTC、density单位kg/m3，完整30秒2880条。仅用瞬时density；orbitmean不混入。实际官方HAPI确认0 nominal/1 anomalous及GRS80位置，未知flag隔离。原始观测仅本地。','',
    '四组各读取25整点；以year/mtime及CF time双重核验绝对时间，各文件SHA与原data_audit匹配，网格完全一致。DEN和ZG均为ilev，原单位g/cm3与cm，分别乘1000和.01。没有将lev中点组分高度错配到DEN。新小时适配层继承成熟八邻列查询，不改变原10分钟接口。垂直log密度、水平密度双线性、时间密度线性，无裁剪、无外推、无补洞。独立实际网格点查询与直接列公式复核通过。','',
    'GRS80观测位置先转地固点，再经已有适配器：A=WGS84大地纬度/椭球高近似原生；B=地心纬度及r−6371000m；D只替换纬度；E只替换高度。四映射不是误差上下界，不按观测拟合高度。正式接口仍EXTERNAL_DATUM_UNVERIFIED。','',
    '主统计为质量通过且16组合均有效的共同集合；自身有效率、拒绝原因和全部查询保留coverage.csv/queries_local.csv。所有比较等权沿轨样本；相对误差分母为正瞬时观测密度，无floor。Pearson以同集合计算。南北高纬±60°分组见metrics.csv。沿轨时间相关，仅一天，不能把采样点当独立重复或推断全年。','',
    '初态敏感性统计见paired_simulation_differences.csv，B−A以A为分母；A14−A7/B14−B7包含更早启动日期及额外真实驱动历史的影响，不能称纯初始化误差。预热收敛与对观测符合程度是两个独立评价问题。Swarm是POD反演产品，受气动/处理模型影响，不是无误差真值。','',
    '原始缺测值属性的NetCDF自动掩码发出dtype转换警告；本轮独立逐数组检查确认选取25帧DEN/ZG全部有限、DEN正、ZG严格递增，无缺失标记进入查询。警告日志保留。','',
    '## 验证、资源与复现','','新增8项合成单元测试；4项真实网格点/逐数组质量检查及16组主指标独立点积复算。源码、输入、结果清单SHA保留。运行期未启动TIE-GCM、GPU、训练或轨道。实际资源见runtime.json。','',
    '```bash','source scripts/activate_orbit.sh','PYTHONPATH=src python -m unittest discover -s tests -p test_hourly_tiegcm_observation.py -v','python scripts/run_swarm_tiegcm_2021_observation.py','python scripts/finalize_swarm_tiegcm_2021_observation.py','```','',
    '脚本使用独立目录且拒绝覆盖已完成标签；复现实验需先显式使用新标签，不直接重放完成目录。','',
    '## 结论边界与下一步','','本次提供有真实同期观测支撑的条件比较，不能证明ZG外部登记、模型真实全球准确度或真实轨道预测精度。原122帧不替换、不重标；SCIENCE_TRAINING_READY=False、SPINUP_SUFFICIENCY_UNVERIFIED保持。优先检视不同初态/区域误差与坐标敏感性，再设计2022独立观测比较；2022多日积分或真实AI训练均需另行授权。']
    (ROOT/'reports/SWARM_TIEGCM_2021_SPINUP_OBSERVATION_V1.md').open('x').write('\n'.join(lines)+'\n')
    print('\n'.join(lines[:25]))
if __name__=='__main__':main()
