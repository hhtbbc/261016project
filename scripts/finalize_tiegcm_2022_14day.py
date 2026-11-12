"""Actual-data-only 2022 spinup and observation figures / scientific reports."""
from pathlib import Path
import csv,json,sys,time,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from prepare_fourcastden_swarm_observation_v1 import sha,dump
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
TAG='tiegcm_2022_spinup_14day_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG
VARS=['DEN','TN','WIND_VECTOR','O1','O2','N2','HE']
def read(p):
 with p.open() as f:return list(csv.DictReader(f))
def mdtable(rows,keys):
 return ['|'+'|'.join(keys)+'|','|'+'|'.join(['---']*len(keys))+'|']+['|'+'|'.join(str(r.get(k,'')) for k in keys)+'|' for r in rows]
def main():
 start=time.perf_counter();assert json.loads((F/'pair_status.json').read_text())['PASS']
 summ=json.loads((O/'delta14/summary.json').read_text());obs=read(O/'observation/metrics.csv');imp=read(O/'observation/improvements.csv');joint=read(O/'joint_height_summary.csv');height=read(O/'delta14/native_ZG_density.csv');native=read(O/'delta14/native_summary.csv');figs=[]
 def select(rows,**kw):return next(r for r in rows if all(str(r[k])==str(v) for k,v in kw.items()))
 def jrow(year,scheme,h=450,period='candidate',domain='within_year_four_common'):return select(joint,year=year,scheme=scheme,height_km=h,period=period,domain=domain,region='global')
 def orow(group,ma='A'):return select(obs,group=group,mapping=ma,region='all')
 def save(fig,name):
  fig.text(.5,.006,'HINDCAST / PROVISIONAL coordinates / initial-state sensitivity != observation error',ha='center',fontsize=8);fig.tight_layout(rect=(0,.035,1,1));fig.savefig(O/name,dpi=155);plt.close(fig);figs.append(name)
 # 1: same UTC, no smoothing.
 old=read(ROOT/'results/tiegcm_2022_dual_initial_spinup_v1/comparison/native_ZG_density_hourly.csv');new=read(O/'delta14/native_ZG_density_hourly.csv')
 fig,ax=plt.subplots(figsize=(10,4))
 for label,rows in [('7-day',old),('14-day',new)]:
  a=[r for r in rows if r['height_km']=='450' and r['region']=='global' and float(r['time_doy_seconds'])>=82*86400];ax.plot([(float(r['time_doy_seconds'])-82*86400)/3600 for r in a],[100*float(r['relative_P95']) for r in a],label=label)
 ax.axhline(5,color='red',ls=':',label='5% descriptive target');ax.set(xlabel='Hours since 2022-03-23 00 UTC',ylabel='Weighted P95 relative DEN difference (%)',title='450 km native ZG / double initial-state difference');ax.legend();save(fig,'450km_7vs14_timeseries.png')
 # 2: vertical coordinates are different statistics.
 fig,axs=plt.subplots(1,2,figsize=(11,4))
 for scheme,label,folder in [('7day','7-day',ROOT/'results/tiegcm_2022_dual_initial_spinup_v1/comparison'),('14day','14-day',O/'delta14')]:
  p=read(folder/'native_profiles.csv');a=[r for r in p if r['variable']=='DEN' and r['period']=='candidate' and r['region']=='global'];axs[0].plot([100*float(r['relative_P95']) for r in a],[int(r['level']) for r in a],label=label)
  rr=[jrow(2022,scheme,h) for h in [200,300,400,450,475,500]];axs[1].plot([100*float(r['relative_P95']) for r in rr],[200,300,400,450,475,500],'o-',label=label)
 for ax in axs:ax.axvline(5,color='red',ls=':');ax.set_xlabel('Weighted relative P95 (%)');ax.legend()
 axs[0].set(ylabel='Native ilev index',title='Same pressure-coordinate index');axs[1].set(ylabel='Native ZG (km)',title='Same native geometric height / four-way common domain');save(fig,'pressure_vs_geometric_height.png')
 # 3: frozen gates, failed cells not merely P95.
 matrix=np.array([[summ['gates'][p][v]['failed_cells'] for p in ['candidate','last24h','endpoint']] for v in VARS])
 fig,ax=plt.subplots(figsize=(7,5));ax.imshow(matrix>0,cmap=matplotlib.colors.ListedColormap(['#bfe3dc','#f1aaa1']),vmin=0,vmax=1)
 for i in range(7):
  for j in range(3):ax.text(j,i,('PASS' if matrix[i,j]==0 else 'FAIL')+'\n'+str(matrix[i,j]),ha='center',va='center')
 ax.set_xticks(range(3),['Candidate 49 h','Last 24 h (25)','Endpoint']);ax.set_yticks(range(7),VARS);ax.set_title('2022 14-day frozen native-layer acceptance / failed cells');save(fig,'multivariable_acceptance.png')
 # 4: actual DNS and all four simulations.
 z=np.load(O/'observation/aligned_local.npz');tt=np.arange(len(z['utc']))/120;mask=z['common'];fig,ax=plt.subplots(figsize=(11,4));ax.plot(tt,np.where(mask,z['observed'],np.nan)*1e13,color='black',lw=1,label='Swarm A DNSAPOD0301')
 for gi,g in enumerate(['A7','B7','A14','B14']):ax.plot(tt,np.where(mask,z['values'][0,gi],np.nan)*1e13,label=g,lw=.8)
 ax.set(xlabel='2022-03-24 UTC hour',ylabel='Density (1e-13 kg/m3)',title=f'PROVISIONAL Map A / common N={mask.sum()}');ax.legend(ncol=5);save(fig,'swarm_four_trajectories.png')
 # 5: observation metrics and maps, no selection.
 fig,axs=plt.subplots(1,3,figsize=(13,4))
 for ax,key,scale,unit in zip(axs,['RMSE','bias','relative_RMS'],[1e13,1e13,100],['1e-13 kg/m3','1e-13 kg/m3','%']):
  for ma in 'ABDE':ax.plot(['A7','B7','A14','B14'],[float(orow(g,ma)[key])*scale for g in ['A7','B7','A14','B14']],'o-',label='Map '+ma)
  ax.set(title=key,ylabel=unit);ax.legend(fontsize=8)
 save(fig,'observation_metrics_maps.png')
 # 6: matched domains and windows across years.
 fig,axs=plt.subplots(1,2,figsize=(11,4))
 for year in [2021,2022]:
  axs[0].plot(['7-day','14-day'],[float(jrow(year,s)['relative_P95'])*100 for s in ['7day','14day']],'o-',label=str(year))
  for s,ls in [('7day','--'),('14day','-')]:axs[1].plot([200,300,400,450,475,500],[float(jrow(year,s,h,domain='cross_year_eight_common')['relative_P95'])*100 for h in [200,300,400,450,475,500]],ls,label=f'{year} {s}')
 axs[0].set(ylabel='450 km weighted relative P95 (%)',title='Within-year four-way common domain');axs[1].set(xlabel='Native ZG (km)',ylabel='Relative P95 (%)',title='Eight-way spatial/time-slot common domain')
 for ax in axs:ax.axhline(5,color='red',ls=':');ax.legend(fontsize=8)
 save(fig,'joint_2021_2022_internal.png')
 # 7: internal vs external different objects.
 jm=read(O/'observation/joint_year_metrics.csv');fig,axs=plt.subplots(1,2,figsize=(11,4))
 for year in [2021,2022]:
  axs[0].plot(['7-day','14-day'],[100*float(jrow(year,s)['relative_P95']) for s in ['7day','14day']],'o-',label=str(year))
  for group in ['A','B']:axs[1].plot(['7-day','14-day'],[100*float(select(jm,year=year,mapping='A',group=group+suffix)['relative_RMS']) for suffix in ['7','14']],'o-',label=f'{year} {group}')
 axs[0].set(title='Internal A/B difference at 450 km',ylabel='Weighted P95 (%)');axs[1].set(title='External Swarm comparison / Map A',ylabel='Relative RMS (%)')
 for ax in axs:ax.legend(fontsize=8)
 save(fig,'internal_vs_external.png')
 # 8: full coverage disclosure.
 fig,ax=plt.subplots(figsize=(9,4))
 for year in [2021,2022]:
  for scheme in ['7day','14day']:ax.plot([200,300,400,450,475,500],[100*float(jrow(year,scheme,h,domain='own_pair')['coverage']) for h in [200,300,400,450,475,500]],'o-',label=f'{year} {scheme}')
 ax.set(xlabel='Native ZG (km)',ylabel='Pair valid coverage (%)',ylim=(0,102),title='Own-domain coverage, not formal external coordinate validation');ax.legend();save(fig,'height_coverage.png')
 # Reports, explicit evidence and limitations.
 driver=json.loads((F/'driver_audit.json').read_text())
 common=['','实验标签：`'+TAG+'`。全部结论仅适用于两种官方完整初态、当前驱动和窗口。','', '原122候选、2021/2022旧轨迹、初始场、第三方物理源码只读；未生成NPZ训练候选、未拟合统计、未启动网络或轨道计算。SCIENCE_TRAINING_READY=False、EXTERNAL_DATUM_UNVERIFIED与真实轨道BLOCKED保留。']
 def report(name,lines):
  with (ROOT/name).open('x') as f:f.write('\n'.join(lines+common)+'\n')
 report('reports/TIEGCM_2022_14DAY_DRIVER_VALIDATION.md',['# 2022扩展驱动独立审计','','精确支持由实际驱动消费代码计算：模型03-09至25，GPI原始03-07至27，中心81日Fobs01-26至05-06，共101天Fobs及168个def Kp三小时桶。','本地缺7天Fobs与56桶Kp，官方GFZ小规模补齐2298字节；无估算、缺测填补或Fadj替代。',f"新GPI SHA256：`{driver['SHA256']}`。",'中心81日平均独立fsum核算；23041分钟驱动边界检查，新旧12961共同分钟节点一致至原容差。实际输出与日志驱动另由工程审计核验。','完整输入、来源与质量证据见experiments/'+TAG+'/driver_audit.json。'])
 eng=['# 2022双初态16天连续运行工程验收','','|组|步数|墙钟秒|采样RSS MiB|NetCDF GiB|主/次记录|退出|','|---|---:|---:|---:|---:|---|---|']
 for group in ['A14','B14']:
  r=json.loads((F/group/'run_status.json').read_text());a=json.loads((F/group/'data_audit.json').read_text());eng.append(f"|{group}|{a['model_steps']}|{r['elapsed_s']:.3f}|{r['peak_sampled_tree_rss_bytes']/2**20:.2f}|{r['netcdf_bytes']/2**30:.4f}|{a['primary_records']}/{a['secondary_records']}|rc{r['returncode']}, {r['normal_exit_count']} NORMAL EXIT|")
 eng+=['','每组一次完整连续启动，60秒/4MPI/OMP1，无Restart、重试或额外短例。17主/16次卷、384小时记录/49候选共同整点。全部卷时间、网格、单位、DEN正性、ZG单调、温度风组分及驱动独立审计通过。','', '监督异常披露：A14原监督器因/proc进程瞬逝竞态异常退出，原MPI继续运行。隔离guardian附着原进程组，新增模型启动0；退出码来自内核/proc zombie exit_code而非日志推断。保留监督采样中断和各进程生命周期VmHWM；A14采样峰值不宣称全程真实峰值，CPU waitrusage不可恢复项记null。B14只修复监督器只读采样，未修改物理、编译器或输入。','每组4800秒、总9600秒、5/12GiB、16GiB RSS和余盘20GiB未扩大；资源详见各run_status与guardian日志。']
 report('reports/TIEGCM_2022_14DAY_LONGRUN_VALIDATION.md',eng)
 spin=['# 2022年7/14天双初态预热对照','','共同目标窗03-23 00至25 00共49整点；最后24小时含两端25点。候选起点预热14天，03-24观测时实际已运行15—16天。7天方案观测日实际8—9天。','原生DEN与ZG为ilev；TN/风/组分依实际lev。Z非ZG。共同几何高度按各自真实ZG及正DEN作对数插值，不外推。','','## 原生层冻结规则与失败格','DEN5%、TN10K、水平风20m/s、主要组分5%，逐时/层/六区域≥95%有效点，组分floor1e-8不变；最大值、覆盖与失败格保留。','']
 spin+=mdtable([dict(variable=v,**{p:summ['gates'][p][v]['failed_cells'] for p in ['candidate','last24h','endpoint']}) for v in VARS],['variable','candidate','last24h','endpoint'])
 spin+=['','## 固定原生ZG与压力层不可互相替代','']
 spin+=mdtable([dict(km=h,P95_7_pct=100*float(jrow(2022,'7day',h)['relative_P95']),P95_14_pct=100*float(jrow(2022,'14day',h)['relative_P95']),coverage14_pct=100*float(jrow(2022,'14day',h,domain='own_pair')['coverage'])) for h in [200,300,400,450,475,500]],['km','P95_7_pct','P95_14_pct','coverage14_pct'])
 spin+=['','以上主比较为同年四轨共同有效域；各双轨自身覆盖率另报。逐时/逐层/区域矩阵、RMSE/P95/最大差、全窗/末24h/终点及N2 near-small/above1e-5绝对和相对诊断位于delta14/。不能把小分母作为所有组分失败的解释。','A7/A14及B7/B14交叉结果位于A14_A7/和B14_B7/，同时改变启动日期和更长历史驱动，不能全部称为单一初态误差。','趋势仅描述最后24h斜率和前后6小时水平，不凭有限轨迹证明平台或20/30天必然收敛。']
 report('reports/TIEGCM_2022_SPINUP_7VS14_COMPARISON.md',spin)
 ob=['# 2022 Swarm A四方案条件观测对照','','DNSAPOD0301，2022-03-24 UTC30秒瞬时反演密度，GRS80位置；原件SHA与旧逐点结果验证后复用，无新增观测下载。Map-A主条件预先指定，A/B/D/E全保留，所有16组合统一quality与共同有效ID。','单位kg/m³；相对RMS=sqrt(mean(((model−DNS)/DNS)^2))，Bias=mean(model−DNS)。Pearson不代表无偏；30秒点有时间相关性，不是独立重复。','']
 ob+=mdtable([dict(Map=ma,group=g,N=orow(g,ma)['n'],RMSE_e13=float(orow(g,ma)['RMSE'])*1e13,Bias_e13=float(orow(g,ma)['bias'])*1e13,relative_RMS_pct=float(orow(g,ma)['relative_RMS'])*100,Pearson=orow(g,ma)['Pearson']) for ma in 'ABDE' for g in ['A7','B7','A14','B14']],['Map','group','N','RMSE_e13','Bias_e13','relative_RMS_pct','Pearson'])
 ob+=['','正改善率表示降低，负值表示恶化；不得因结果择优坐标或初态。','']+mdtable(imp,['mapping','pair','n','RMSE_reduction_pct','relative_RMS_reduction_pct'])
 ob+=['','内部双初态趋同只约束模拟对初始状态的敏感性；外部误差还含模型共同偏差、驱动/结构、卫星位置到原生ZG的未知登记和DNS反演误差。故内部下降不能保证外部误差下降；不同映射可能改变改善方向。各自有效点、共同点与拒绝理由见coverage.csv。']
 report('reports/SWARM_TIEGCM_2022_7VS14_OBSERVATION_V1.md',ob)
 jr=['# 2021/2022两年双初态7/14天联合分析','','统一各年03-23至25的49帧，2021原73帧报告保持不变。共同域包括同年四轨及跨年八轨空间/时槽诊断；跨年时槽不是相同真实UTC。500km各自覆盖不足不得假装全球完整。','']
 jr+=mdtable([dict(year=y,scheme=s,P95_450_pct=100*float(jrow(y,s)['relative_P95']),P95_500_pct=100*float(jrow(y,s,500)['relative_P95']),own_500_coverage_pct=100*float(jrow(y,s,500,domain='own_pair')['coverage'])) for y in [2021,2022] for s in ['7day','14day']],['year','scheme','P95_450_pct','P95_500_pct','own_500_coverage_pct'])
 jr+=['','原生全变量匹配门槛见joint_native_gates.csv；两年观测误差全映射见observation/joint_year_metrics.csv。年份太阳/地磁驱动、初态历史、大气结构与卫星高度不同，不能作太阳活动单因素因果结论。内部趋同与外部观测符合是不同科学问题。']
 report('reports/TIEGCM_2021_2022_SPINUP_7VS14_JOINT_V1.md',jr)
 report('docs/FOURCASTDEN_2022_14DAY_DATA_QUALITY_DECISION.md',['# 14天研究后的AI数据质量决策','','不得自动替换原122帧；任何14天候选需独立版本、变量/时空/单位/层登记/掩码审计和授权。尚未通过全部冻结门槛时，完整171通道科学训练不放行。','优先缺口：一，未达标组分及层区的标签稳定性；二，外部高度登记与独立观测误差归因；三，样本季节/太阳地磁覆盖及正式训练/验证协议。','可另行设计DEN专项工程研究，但必须独立标签与授权，不删除其他变量来宣布全状态PASS。不拟合新归一化统计。','两年单一季节的73/49帧不足支撑泛化主张；后续先定义多个季节与安静/扰动窗口、按年份隔离的有界小样本试点和成本，再决定扩大，不能凭本轮指定一个已经足够的帧数。','不自动追加21/28天。只有定位具体未收敛变量/高度/区域并形成可检验机制或明确增益假设后，才提出新实验预算。'])
 report('reports/TIEGCM_2022_14DAY_BRIEFING.md',['# 三分钟组会汇报稿','','本轮我们没有训练AI，而是检验物理模拟作为训练标签是否稳定。在2022年相同目标窗口，分别从两套官方完整初态连续运行16天，前14天作为候选预热。太阳与地磁驱动、网格和物理参数保持相同，避免把配置差异误当初态影响。',f"在450公里原生几何高度、同年四轨共同域，7天双初态P95为{100*float(jrow(2022,'7day')['relative_P95']):.4f}%，14天为{100*float(jrow(2022,'14day')['relative_P95']):.4f}%。这衡量两条模拟之间的差异，不是对真实大气的预测精度。",'我们还分别检查温度、风和主要中性组分，保留所有未通过的层和区域；不能只看密度一个指标宣布全状态合格。随后将四条轨迹在同一批Swarm观测时刻和位置查询，使用固定的四种坐标假设，公平比较观测残差。', '这里最重要的认识是，模拟内部趋同和更接近观测是两件事。两套初态可以逐渐走向相同的共同偏差。外部高度参考面尚未严格登记，Swarm密度本身也有反演误差，所以观测结果仍是有条件对照。','下一步优先解决未达标标签变量和外部登记证据，再冻结训练数据质量与验证协议。原122帧、科学训练False和真实轨道BLOCKED均保持，不因为模型成功运行就跳过科学验收。'])
 dump(F/'finalization.json',dict(figures=figs,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,science_training_ready=False))
 print('Reports and actual-data figures complete',len(figs))
if __name__=='__main__':main()
