"""Saved-data figures, independent arithmetic, and bounded cross-year conclusions."""
from pathlib import Path
import sys,json,csv,time,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_swarm_tiegcm_2022_observation import F,O,OLD,MAPS,table
from prepare_fourcastden_swarm_observation_v1 import sha,dump
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    started=time.perf_counter();rows=list(csv.DictReader((O/'metrics.csv').open()));globalrows=[r for r in rows if r['region']=='all']
    new=np.load(O/'aligned_local.npz');old=np.load(OLD/'aligned_local.npz');figures=[]
    def save(fig,name):
        fig.suptitle('2021/2022 Mar24 | PROVISIONAL | DNSAPOD0301 | smin, seven-day warmup',fontsize=10)
        fig.tight_layout(rect=[0,0,1,.95]);fig.savefig(O/name,dpi=160);plt.close(fig);figures.append(name)
    def metric(year,ma='A',region='all'):
        return next(r for r in rows if r['year']==str(year) and r['mapping']==ma and r['region']==region)
    h=(new['utc']-new['utc'][0])/np.timedelta64(1,'h');m=new['common'];obs=new['density'];v=new['values']
    fig,ax=plt.subplots(figsize=(12,4));ax.plot(h,obs*1e13,color='black',lw=.8,label='Swarm instantaneous, 2022-03-24');ax.plot(h,v[0]*1e13,lw=.8,label='TIE-GCM smin7 / Map A');ax.set(xlabel='UTC hour',ylabel='Density (1e-13 kg/m3)');ax.legend();save(fig,'2022_density_timeseries.png')
    fig,ax=plt.subplots(figsize=(6,6));lim=max(obs[m].max(),v[0,m].max())*1e13;ax.scatter(obs[m]*1e13,v[0,m]*1e13,s=3,alpha=.35);ax.plot([0,lim],[0,lim],'k--');r=metric(2022);ax.set(xlabel='Swarm (1e-13 kg/m3)',ylabel='TIE-GCM Map A (1e-13 kg/m3)',title=f"2022-03-24 N={r['n']} | relRMS={float(r['relative_RMS'])*100:.2f}%");save(fig,'2022_density_scatter.png')
    fig,axs=plt.subplots(1,4,figsize=(14,4))
    for ax,key,scale,title in zip(axs,['RMSE','relative_RMS','bias','common_coverage'],[1e13,100,1e13,100],['RMSE (1e-13 kg/m3)','Relative RMS (%)','Bias (1e-13 kg/m3)','Common coverage (%)']):
        ax.bar(['2021 A7','2022 smin7'],[float(metric(y)[key])*scale for y in [2021,2022]]);ax.set_title(title+' / Map A')
    save(fig,'crossyear_metrics.png')
    fig,axs=plt.subplots(1,2,figsize=(11,4));regions=['low','mid','high','north','south']
    for ax,key,scale,title in zip(axs,['relative_RMS','relative_bias'],[100,100],['Relative RMS (%)','Signed mean relative bias (%)']):
        for i,y in enumerate([2021,2022]):
            rr=[metric(y,region=g) for g in regions];ax.bar(np.arange(len(regions))+(i-.5)*.36,[float(r[key])*scale for r in rr],width=.36,label=str(y))
            for k,r in enumerate(rr):ax.annotate('N='+r['n'],(k+(i-.5)*.36,float(r[key])*scale*.5),fontsize=7,rotation=90,va='center',color='white')
        ax.set_xticks(range(len(regions)),regions);ax.set_title(title+' / A');ax.legend()
    save(fig,'latitude_errors.png')
    fig,axs=plt.subplots(1,2,figsize=(10,4))
    for ax,key,scale,title in zip(axs,['relative_RMS','relative_bias'],[100,100],['Relative RMS (%)','Signed relative bias (%)']):
        for y in [2021,2022]:ax.plot(list(MAPS),[float(metric(y,ma)[key])*scale for ma in MAPS],'o-',label=str(y))
        ax.set(xlabel='Hypothesis (no best-map selection)',ylabel=title);ax.legend()
    save(fig,'coordinate_sensitivity.png')
    fig,axs=plt.subplots(2,1,figsize=(11,7),sharex=True)
    for y in [2021,2022]:
        rr=[metric(y,region=f'UTC_{x:02d}_{x+3:02d}') for x in range(0,24,3)]
        axs[0].plot(np.arange(1.5,24,3),[float(r['relative_RMS'])*100 for r in rr],'o-',label=str(y))
        axs[1].plot(np.arange(1.5,24,3),[float(r['relative_bias'])*100 for r in rr],'o-',label=str(y))
    axs[0].set_ylabel('Relative RMS (%)');axs[1].set(ylabel='Signed relative bias (%)',xlabel='UTC / fixed 3-hour blocks; descriptive, no confidence interval')
    for ax in axs:ax.legend()
    save(fig,'three_hour_blocks.png')
    drives=list(csv.DictReader((O/'drivers.csv').open()));fig,axs=plt.subplots(3,1,figsize=(10,7),sharex=True)
    for ax,k,unit in zip(axs,['f107d','f107a','Kp'],['F10.7 (sfu)','F10.7A (sfu)','Kp']):
        for y in [2021,2022]:
            rr=[r for r in drives if r['year']==str(y)];ax.plot(range(len(rr)),[float(r[k]) for r in rr],label=str(y))
        ax.set_ylabel(unit);ax.legend()
    axs[-1].set_xlabel('Mar24 UTC hour / saved model driver scalars');save(fig,'actual_drivers.png')
    # Common-domain independent arithmetic and old metrics: no model queries.
    for y,vals,observed,mask in [(2021,old['values'][:,0],old['observed'],old['common']),(2022,v,obs,m)]:
        for mi,ma in enumerate(MAPS):
            r=metric(y,ma);err=vals[mi,mask]-observed[mask];rel=err/observed[mask]
            for key,value in [('RMSE',np.sqrt(np.dot(err,err)/len(err))),('relative_RMS',np.linalg.norm(rel)/np.sqrt(len(rel))),('relative_bias',rel.mean()),('bias',err.mean())]:assert np.isclose(float(r[key]),value,rtol=1e-13,atol=0)
    for rel,hs in json.loads((F/'protected_after.json').read_text()).items():assert sha(ROOT/rel)==hs
    from PIL import Image
    for name in figures:
        with Image.open(O/name) as im:im.verify()
    table(O/'figure_sources.csv',[dict(figure=n,source='metrics.csv;aligned_local.npz;prior 2021 aligned_local.npz;drivers.csv',status='PROVISIONAL',date='2021/2022-03-24') for n in figures])
    main=['# 2022年Swarm-A同期密度独立观测对照','','标签：swarm_tiegcm_2022_observation_v1。PROVISIONAL / HINDCAST / NOT_TRAINING。','','## 实际结果','','2022-03-24 00:00—23:59:30 UTC；模型使用03-24 00至03-25 00的25帧。现有唯一2002 smin完整初态轨迹，从03-16连续至03-25；未新增双初态或14天模拟。','','密度MAE/RMSE/Bias下表单位1e-13 kg/m³；相对量为百分数。relative_bias=mean((模拟−观测)/观测)，另存bias/mean(观测)，二者不混用。','','|Map|N|MAE|RMSE|Bias|相对RMS %|有符号相对Bias %|Pearson|覆盖率 %|','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in globalrows:
        if r['year']!='2022':continue
        main.append(f"|{r['mapping']}|{r['n']}|{float(r['MAE'])*1e13:.5f}|{float(r['RMSE'])*1e13:.5f}|{float(r['bias'])*1e13:.5f}|{float(r['relative_RMS'])*100:.4f}|{float(r['relative_bias'])*100:.4f}|{float(r['Pearson']):.5f}|{float(r['common_coverage'])*100:.2f}|")
    dl=json.loads((F/'downloads.json').read_text());runtime=json.loads((F/'runtime.json').read_text())
    main+=['','## 观测、模拟与处理证据','',f"- ESA实际目录唯一0301目标，ZIP {dl['product']['bytes']}字节，SHA256 `{dl['product']['SHA256']}`；含目录及HAPI共{dl['total_bytes']}字节<10MiB。无发布方SHA，不能冒称官方签名。ZIP CRC及成员SHA已检查，原件只本地。",'- CDF实物TIME SYSTEM=UTC、30秒、density kg/m3、latitude deg/altitude m；只用瞬时density，不以density_orbitmean补值。官方HAPI当前产品说明0=nominal、1=anomalous、GRS80地理坐标；未知码隔离。nominal不代表无反演误差。','- 现有小时适配器使用year/mtime与CF time双重日期核对；原NetCDF SHA匹配data_audit。DEN/ZG均ilev，分别g/cm3×1000和cm×.01，25帧质量完整。两时刻×四水平邻列必须全部有效，垂直log密度、水平/时间密度线性，不跨缺帧，不补零外推。','- A为WGS84大地纬度及椭球高近似原生；B为地心纬度及r−6371000m；D只改纬度，E只改高度。正式EXTERNAL_DATUM_UNVERIFIED不解除。','- 主共同域为本年所有映射同时有效且观测质量通过。2021沿用已冻结四轨迹/16方案共同域，2022为现有单轨迹/4映射共同域。两年样本ID不同，绝不当同一卫星位置或单因素年份实验。','- 先冻结低纬abs<30、中纬30≤abs<60、高纬≥60、南北高纬、半球、400/430/440/450/460/470/500km高度边界、3小时连续块。少于30点标N/A。沿轨样本相关，不给逐点独立置信区间。',f"- 主阶段墙钟{runtime['wall_s']:.3f}秒，峰值RSS{runtime['peak_RSS_MiB']:.3f}MiB，{runtime['queries']}次实际查询，共同样本{runtime['common']}。资源上限1800秒/4GiB，0模型启动。",'- 初始字段missing_value的NetCDF dtype自动掩码警告保留；选取DEN/ZG直接验证全部有限、密度正、高度递增，无异常填入统计。','', '## 复现与交付','','```bash','source scripts/activate_orbit.sh','PYTHONPATH=src python -m unittest discover -s tests -p test_swarm_crossyear.py -v','python scripts/run_swarm_tiegcm_2022_observation.py','python scripts/finalize_swarm_tiegcm_crossyear.py','```','','已完成标签独占写保护；复现实验必须显式指定新标签（当前脚本常量），不覆盖原目录。逐点数据和原CDF仅本地，指标/图/审计可公开。','', '## 门禁','','只有同期观测的条件符合程度获得独立数据证据，不是全球密度真值验证，也不是轨道精度。SPINUP_SUFFICIENCY_UNVERIFIED、科学训练False、真实轨道BLOCKED保持。2022只有一条轨迹，不能由本次结果判定7天充分或14天有效。']
    (ROOT/'reports/SWARM_TIEGCM_2022_OBSERVATION_V1.md').open('x').write('\n'.join(main)+'\n')
    cross=['# 2021/2022同协议Swarm沿轨密度跨年份比较','','## 主要可比结果：Map-A、相同smin完整初态、7天预热','','RMSE、Bias单位1e-13 kg/m³。','','|年份|N|RMSE|相对RMS %|Bias|平均有符号相对偏差 %|Pearson|共同覆盖率 %|','|---|---:|---:|---:|---:|---:|---:|---:|']
    for y in [2021,2022]:
        r=metric(y);cross.append(f"|{y}|{r['n']}|{float(r['RMSE'])*1e13:.5f}|{float(r['relative_RMS'])*100:.4f}|{float(r['bias'])*1e13:.5f}|{float(r['relative_bias'])*100:.4f}|{float(r['Pearson']):.5f}|{float(r['common_coverage'])*100:.2f}|")
    cross+=['','## 配置与不可比因素','','configuration_comparability.json直接核实两年SOURCE/SOURCE_START、STEP、HEELIS/GSWM、HELIUM、输出规则相同，初态/GPI当前SHA已查；可执行/apex原冻结SHA相同。日历/太阳地磁驱动不同，IGRF按年份计算。2021有四条轨迹，本表只读其A7；2022无B7/A14/B14，不能补造或把跨年当预热单因素实验。两年卫星实际高度、轨道采样、地方时/驱动和反演处理条件可能不同，绝对RMSE不可直接排名物理准确度。','', '## 驱动与密度水平（描述性，不作因果归因）','']
    for y in [2021,2022]:
        r=metric(y);rr=[x for x in drives if x['year']==str(y)]
        cross.append(f"- {y}观测/模拟共同样本平均密度={float(r['observed_mean']):.8e}/{float(r['simulated_mean']):.8e} kg/m³。"+'；'.join(f"{k}={min(float(x[k]) for x in rr):.6f}—{max(float(x[k]) for x in rr):.6f}" for k in ['f107d','f107a','Kp'])+'。')
    cross+=['','只比较这两个日期，不能断言某驱动造成误差变化。drivers.csv是24个实际整点标量，非额外观测或逐秒内部trace。','', '## 区域与坐标敏感性','']
    for y in [2021,2022]:
        for region in ['low','mid','high','north','south']:
            r=metric(y,region=region);cross.append(f"- {y} {region}：N={r['n']}，相对RMS={float(r['relative_RMS'])*100:.3f}%，相对偏差={float(r['relative_bias'])*100:.3f}%。")
    sens=list(csv.DictReader((O/'mapping_sensitivity.csv').open()))
    for r in sens:cross.append(f"- {r['year']} Map{r['mapping']}/A密度相对变化绝对P95={float(r['absolute_P95'])*100:.4f}%。这是条件敏感性，不是未知ZG登记误差的置信区间。")
    cross+=['','高度分组和3小时块详见metrics.csv，空/不足区域保留N/A。高度、纬度、时间共同变化，分组不是单独高度因果效应。不同映射下RMSE/相对RMS可能排序不同，不从中选最优高度方案；未知ZG零面、POD气动反演误差、模型物理偏差尚不能独立拆分。','', '## 下一阶段明确建议','','值得开展2022同驱动双合法初态的预热敏感性验证，因为当前唯一轨迹无法估计初始化残差，2021结果也不能外推2022；但是观测残差不能证明延长预热会改善精度。优先先完成2022第二初态7天配对，沿用冻结多变量门槛，再以配对差异决定是否投入14天双初态，而不是直接默认14天更好。新模型积分须另授权。本轮没有运行这些未来实验。','', '外部高度登记应并行请求独立官方依据；它影响观测解释，但不阻止明确披露假设的条件研究。训练数据质量清单现在可以继续只读完善，正式自主训练不应抢先：至少需两年预热敏感性与物理质量接受范围、训练/验证时间隔离、仅训练年统计冻结、单位/网格/padding与缺测规则、独立验证协议和小样本限制、损失/优化器/学习率/资源冻结。不得用2022拟合训练统计或2023调参。','', '## 实验审计','','2021原结果和脚本、原观测读取后SHA保持；16个旧全局指标逐项复现，未重跑2021沿轨查询。2022先实际网格点对照与单位检查，再完整一天查询。新7项分组/指标/共同样本测试通过；既有8项小时接口测试复核单独记录。所有图均来自实际保存结果。','', '报告与图目录：results/swarm_tiegcm_2022_observation_v1；主报告SWARM_TIEGCM_2022_OBSERVATION_V1.md。无TIE、GPU、轨道或训练。']
    (ROOT/'reports/SWARM_TIEGCM_2021_2022_COMPARISON_V1.md').open('x').write('\n'.join(cross)+'\n')
    dump(F/'postprocess_audit.json',dict(PASS=True,global_metric_sets_independently_recomputed=8,figures=figures,old_assets_unchanged=True,wall_s=time.perf_counter()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
    print('\n'.join(cross[:12]))
if __name__=='__main__':main()
