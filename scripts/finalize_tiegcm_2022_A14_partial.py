"""Publish only actual A14 data-audited evidence; dual14 stays incomplete."""
from pathlib import Path
import sys,json,csv,time,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from prepare_fourcastden_swarm_observation_v1 import dump,sha
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
TAG='tiegcm_2022_spinup_14day_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG

def read(p):
 with p.open() as f:return list(csv.DictReader(f))
def table(rows,keys):return ['|'+'|'.join(keys)+'|','|'+'|'.join(['---']*len(keys))+'|']+['|'+'|'.join(str(r[k]) for k in keys)+'|' for r in rows]
def main():
 started=time.perf_counter();a=json.loads((F/'A14/data_audit.json').read_text());run=json.loads((F/'A14/run_status.json').read_text());assert a['data_integrity_PASS'] and not a['engineering_PASS'] and not (F/'B14').exists()
 driver=json.loads((F/'driver_audit.json').read_text());obs=read(O/'observation_partial/metrics.csv');imp=read(O/'observation_partial/improvements.csv');cross=read(O/'A14_A7/native_ZG_density.csv');profiles=read(O/'A14_A7/native_profiles.csv');figs=[]
 def row(g,m='A'):return next(r for r in obs if r['group']==g and r['mapping']==m and r['region']=='all')
 def save(fig,name):
  fig.text(.5,.005,'A14 FILE DATA AUDIT PASS / MPI EXIT UNKNOWN / B14 NOT RUN / PROVISIONAL HINDCAST',ha='center',fontsize=8);fig.tight_layout(rect=(0,.04,1,1));fig.savefig(O/name,dpi=150);plt.close(fig);figs.append(name)
 z=np.load(O/'observation_partial/aligned_local.npz');mask=z['common'];hours=np.arange(len(mask))/120
 fig,ax=plt.subplots(figsize=(11,4));ax.plot(hours,z['observed']*1e13,label='Swarm A DNSAPOD0301',color='black',lw=.8)
 for gi,g in enumerate(['A7','B7','A14']):ax.plot(hours,np.where(mask,z['values'][0,gi],np.nan)*1e13,label=g,lw=.8)
 ax.set(xlabel='2022-03-24 UTC hour',ylabel='Density (1e-13 kg/m3)',title=f'Map A / same {mask.sum()} common observation IDs / B14 unavailable');ax.legend(ncol=4);save(fig,'partial_swarm_density_timeseries.png')
 fig,axs=plt.subplots(1,3,figsize=(12,4))
 for ax,key,factor,unit in zip(axs,['RMSE','bias','relative_RMS'],[1e13,1e13,100],['1e-13 kg/m3','1e-13 kg/m3','%']):
  for ma in 'ABDE':ax.plot(['A7','A14'],[float(row(g,ma)[key])*factor for g in ['A7','A14']],'o-',label='Map '+ma)
  ax.set(title=key,ylabel=unit);ax.legend(fontsize=8)
 save(fig,'partial_observation_map_sensitivity.png')
 fig,axs=plt.subplots(1,2,figsize=(9,4))
 for ax,gi,g in zip(axs,[0,2],['A7','A14']):
  x=z['observed'][mask]*1e13;y=z['values'][0,gi,mask]*1e13;ax.scatter(x,y,s=3,alpha=.5);lo=0;hi=max(x.max(),y.max());ax.plot([lo,hi],[lo,hi],'k:');ax.set(xlabel='DNS density (1e-13 kg/m3)',ylabel='Simulation (1e-13 kg/m3)',title=g+' / Map A / N='+str(mask.sum()),xlim=(lo,hi),ylim=(lo,hi))
 save(fig,'partial_observation_scatter.png')
 hh=read(O/'A14_A7/native_ZG_density_hourly.csv');rr=[r for r in hh if r['height_km']=='450' and r['region']=='global'];fig,ax=plt.subplots(figsize=(10,4));ax.plot([(float(r['time_doy_seconds'])-82*86400)/3600 for r in rr],[100*float(r['relative_P95']) for r in rr]);ax.axvline(0,color='red',ls=':');ax.set(xlabel='Hours relative to 2022-03-23 00 UTC',ylabel='Weighted P95 relative difference (%)',title='A14 vs A7 at native ZG 450 km / start-date + driving-history sensitivity');save(fig,'partial_A14_A7_450km.png')
 fig,axs=plt.subplots(1,2,figsize=(10,4));rr=[r for r in profiles if r['variable']=='DEN' and r['region']=='global' and r['period']=='candidate'];axs[0].plot([float(r['relative_P95'])*100 for r in rr],[int(r['level']) for r in rr]);axs[0].set(xlabel='Relative P95 (%)',ylabel='Native ilev index',title='Same pressure index / A14 vs A7')
 rr=[next(r for r in cross if r['height_km']==str(h) and r['region']=='global' and r['period']=='candidate') for h in [200,300,400,450,475,500]];axs[1].plot([float(r['relative_P95'])*100 for r in rr],[200,300,400,450,475,500],'o-');axs[1].set(xlabel='Relative P95 (%)',ylabel='Native ZG (km)',title='Same geometric height / A14 vs A7');save(fig,'partial_pressure_vs_height.png')
 fig,axs=plt.subplots(1,3,figsize=(12,4))
 for ax,k in zip(axs,['O1','O2','N2']):
  for period in ['candidate','last24h']:
   rr=[r for r in profiles if r['variable']==k and r['period']==period and r['region']=='global' and r['relative_P95']];ax.plot([float(r['relative_P95'])*100 for r in rr],[int(r['level']) for r in rr],label=period)
  ax.set(title=k+' mass mixing ratio / A14 vs A7',xlabel='Relative P95 (%)',ylabel='Native lev index');ax.legend(fontsize=8)
 save(fig,'partial_composition_profiles.png')
 fig,ax=plt.subplots(figsize=(10,4));original=json.loads((F/'A14/guardian_launch_once.json').read_text())['original_progress'];ss=run['resource_samples'];ax.scatter([original['wall_s']/60],[original['rss_bytes']/2**20],label='Last original supervisor sample',s=15);ax.plot([r['wall_s']/60 for r in ss],[r['rss_bytes']/2**20 for r in ss],label='Guardian samples');ax.axvspan(original['wall_s']/60,ss[0]['wall_s']/60,color='orange',alpha=.3,label='Unobserved RSS sampling interval');ax.set(xlabel='Minutes since original MPI start',ylabel='Sampled MPI tree RSS (MiB)',title='Same continuous A14 launch / supervision gap explicitly retained');ax.legend();save(fig,'partial_supervision_gap.png')
 checks=dict(DRIVER_VALIDATION='PASS',A14_DATA_INTEGRITY='PASS',A14_ENGINEERING='PARTIAL',B14_ENGINEERING='NOT_RUN',DUAL14_SENSITIVITY='NOT_AVAILABLE',FOUR_TRAJECTORY_OBSERVATION='PARTIAL',SCIENCE_TRAINING_READY=False,EXTERNAL_DATUM='EXTERNAL_DATUM_UNVERIFIED',REAL_ORBIT='BLOCKED')
 dump(F/'execution_decision.json',dict(statuses=checks,model_launches=1,unused_B14_authorization_not_consumed=True,reason='A14 launcher exit code unrecoverable after original supervisor /proc race; mandatory complete engineering gate not met',no_retry=True,allow_future_launch=False))
 def report(name,lines):
  with (ROOT/name).open('x') as f:f.write('\n'.join(lines)+'\n')
 report('reports/TIEGCM_2022_14DAY_DRIVER_VALIDATION.md',['# 2022扩展GPI审计：PASS','','实际代码精确计算：模型03-09至25，raw GPI03-07至27；中心81日Fobs支持01-26至05-06，共101天Fobs/168个def Kp桶。','本地缺7天Fobs与56个Kp桶，本轮从原官方GFZ接口补齐2298字节，无Fadj替代、缺测估算或填补。中心81日平均独立fsum核算，23041分钟静态节点合法；新旧12961个共有节点驱动一致至冻结容差。',f"新GPI SHA256 `{driver['SHA256']}`。",'实际A14输出2304个十分钟日志节点与所有暖态NetCDF驱动已核验，最大差见A14/data_audit.json；冷echo继承源场标量，不能当实际GPI覆盖。','全部来源和SHA见experiments/'+TAG+'/driver_audit.json。原GPI保持不变。'])
 eng=['# 2022年14天候选预热工程记录：PARTIAL','','**本轮未完成双轨实验。只启动A14一次，B14未启动；不重试、不以日志推断rc0。**','','|项|实际结果|','|---|---|',f"|A14时间|2022-03-09 00至03-25 00 UTC|",f"|步数|{a['model_steps']}|",f"|输出|{a['primary_records']} primary / {a['secondary_records']} hourly，33卷|",f"|原进程起算监督墙钟|{run['elapsed_s']:.6f}秒|",f"|NetCDF|{run['netcdf_bytes']}字节，{run['netcdf_bytes']/2**30:.5f}GiB|",f"|接管段采样树RSS峰值|{run['peak_sampled_tree_rss_bytes']/2**20:.3f}MiB，不是全程实测峰值|",f"|已观察进程生命周期VmHWM之和|{run['sum_current_process_lifetime_VmHWM_bytes']/2**20:.3f}MiB，非同时RSS测量|",'|日志|23040步、4 NORMAL EXIT|','|真实MPI退出码|未取得，保留null|','|文件数据完整性|PASS|','|完整工程验收|PARTIAL，不能放行B14|','','## 故障与证据','原监督器遍历/proc时遇到已消失的无关进程，ProcessLookupError退出。原MPI保持同一连续进程，无额外启动。独立guardian附着原进程组，继续原4800秒及输出/RSS/磁盘预算；但启动器被PID1回收，未观察到可读取的zombie退出码。NORMAL EXIT不能替代真实退出状态。','run_status.json保留returncode=null及stop_reason。其launcher_exit_source字段是预设采集路径说明，在raw_wait_status=null时不代表实际观察成功；以本报告和execution_decision为资格解释，不改写原故障记录。','接管前后RSS采样缺口保留，缺失waitrusage记null。不能声称全程连续监督和所有资源瞬时峰值已验证。','随后独立扫描全部33卷，检查17日主记录、384小时记录、49候选整点、时间/日历/步数、网格/单位/掩码、DEN正性、ZG逐列单调、温度风组分与实际驱动，数据完整性通过；完整工程资格仍未通过。','第一次准备阶段还发生一次配置字典重复键异常，模型启动0；日志留存。后续原监督器缺陷不是模型方程错误的证据。','A14不能自动作为正式科学训练标签，不替换原122帧。']
 report('reports/TIEGCM_2022_14DAY_LONGRUN_VALIDATION.md',eng)
 spin=['# 2022年7/14天对照：双初态部分未完成','','A7/B7既有结果只读复用，450km双初态候选P95=8.9310859%。本轮仅A14有完整且经数据审计的输出，MPI退出码未验证；B14未启动。**A14/B14 P95、14天双初态多变量通过状态均N/A，不能报告低于5%或已改善。**','允许独立完成A7/A14离线对照，但它比较同来源初态、不同起日和更长驱动历史，不能机械解释为纯初始化误差，逐格门槛亦不能被当作A14/B14充分性判断。','共同03-23至25共49整点，末24h25整点；6个高度及逐层/区域/全窗/末24h/终点统计见results/'+TAG+'/A14_A7/。DEN/ZG为ilev；Z不是ZG；组分为lev质量混合比，原floor1e-8不变，N2 near-small和above1e-5绝对/相对差单列。','']
 rr=[dict(km=h,P95_A14_vs_A7_pct=100*float(next(r for r in cross if r['height_km']==str(h) and r['period']=='candidate' and r['region']=='global')['relative_P95']),coverage_pct=100*float(next(r for r in cross if r['height_km']==str(h) and r['period']=='candidate' and r['region']=='global')['coverage'])) for h in [200,300,400,450,475,500]]
 spin+=table(rr,['km','P95_A14_vs_A7_pct','coverage_pct']);spin+=['','此表不是14天双初态差异，不与8.9311%作改善率相减。500km覆盖仅是原生模型共同域，不证明Swarm外部参考面已验证。']
 report('reports/TIEGCM_2022_SPINUP_7VS14_COMPARISON.md',spin)
 ob=['# 2022年Swarm条件观测对照：A14部分结果','','DNSAPOD0301，2022-03-24 UTC30秒瞬时反演密度，GRS80位置。既有原件/旧A7B7数组SHA核验后复用，观测下载0。新增A14四映射11520查询；12组合共同2880点。B14缺失，不补真值、不外推。','A14文件数据审计通过，但完整运行工程资格PARTIAL，以下为明确限定的数据分析证据。Map-A预先指定，B/D/E只作敏感性，不择优认定正确坐标；EXTERNAL_DATUM_UNVERIFIED保留。','RMSE/MAE/Bias单位1e-13 kg/m³，相对RMS为逐点相对残差平方均值根，不是RMSE除观测均值。','']
 ob+=table([dict(Map=ma,group=g,N=row(g,ma)['n'],MAE=float(row(g,ma)['MAE'])*1e13,RMSE=float(row(g,ma)['RMSE'])*1e13,Bias=float(row(g,ma)['bias'])*1e13,relative_RMS_pct=float(row(g,ma)['relative_RMS'])*100,Pearson=row(g,ma)['Pearson']) for ma in 'ABDE' for g in ['A7','B7','A14']],['Map','group','N','MAE','RMSE','Bias','relative_RMS_pct','Pearson'])
 ob+=['','正值为降低，负值为恶化；所有共同ID与失败记录均保留。','']+table(imp,['mapping','n','RMSE_reduction_pct','relative_RMS_reduction_pct'])
 ob+=['','Map-A下A14相对A7 RMSE降低6.03066%、相对RMS降低3.19811%；Map-B/E虽然RMSE降低约4.28%，相对RMS却分别增加约0.624%/0.628%。绝对与相对指标可能不同，不删不利结果。','不能证明14天双初态已趋同，也不能由单条轨迹观测改善推出预热充分。DNS是POD相关反演而非绝对真值，30秒点有时间相关性；未知外部高度登记与模型共同偏差仍影响评价。','全部分区指标、覆盖/拒绝、配置与原始源SHA见observation_partial/和observation_partial_audit.json。']
 report('reports/SWARM_TIEGCM_2022_7VS14_OBSERVATION_V1.md',ob)
 report('reports/TIEGCM_2021_2022_SPINUP_7VS14_JOINT_V1.md',['# 2021/2022联合分析的证据边界','','2021四轨已存在，2022已有A7/B7与本轮数据审计通过的A14，但B14未运行。2年×2初态×2预热的完整矩阵没有建成，本轮不伪造2022双初态14天结果，不重跑或覆盖2021。','既有匹配03-23至25的49帧，2021 7/14天与2022 7天450km双初态P95分别6.059497%、2.123731%、8.931086%；本轮2022 14天双初态N/A。2021原73帧5.86926/2.08102%是不同窗口，不能混为同一指标。','本轮新增A14观测对照说明单条轨迹改变可同时带来绝对指标改善、部分映射相对指标恶化；不能从此推断跨年双初态收敛规律。','2021观测方向不统一的历史结论不变。两年驱动、卫星高度与状态历史不同，不作单一太阳活动因果归因。'])
 report('docs/FOURCASTDEN_2022_14DAY_DATA_QUALITY_DECISION.md',['# 2022年14天任务后的数据质量决策','','SCIENCE_TRAINING_READY=False；原122帧不改、不提取替换、不拟合统计、不训练。B14未运行，无法审查完整14天标签稳定性。','优先三个缺口：1. 先修复并独立验证监督器异常时仍能可靠取得子进程退出状态的工程机制；2. 另行授权补齐B14并按原冻结标准评价组分、风与共同高度标签稳定性；3. 外部高度登记与正式数据/训练验证协议及季节活动覆盖。','当前不自动重跑A14或补B14。后续是否需要新的A14工程合格运行必须另行决策，不能凭NORMAL EXIT回填rc0。','DEN专项工程研究也需独立授权、明确限定变量与标签来源，不能删除失败变量宣布171通道科学PASS。两年单季73/49帧不支持普遍泛化；扩展量需预注册多季节/安静扰动窗口和资源预算，不凭本次指定足够样本数。'])
 report('reports/TIEGCM_2022_14DAY_BRIEFING.md',['# 三分钟中文组会稿','','本轮原计划完成2022年两种初态的14天预热，比较它们是否更一致，以及是否更接近Swarm沿轨反演密度。扩展太阳和地磁驱动已经完整补齐，新旧共同时间段一致，没有填补缺测或改动原数据。','实际只启动了smin的A14一次。模型输出完整16天、23040步和384小时记录，后续文件审计通过。但监督脚本在采样系统进程时发生竞态异常，虽然接管后模型继续跑完，最终没有拿到MPI的真实退出码。因此我们没有用正常退出日志代替工程资格，也没有启动第二条B14。','在不依赖第二条轨迹的部分，我们用相同2880个Swarm观测点对比A7和A14。Map-A下，RMSE从2.91516降到2.73936乘10的负13次方kg每立方米，约下降6.03%；相对RMS从20.55%降到19.89%。但换成B或E坐标假设，相对RMS略微恶化。','这说明即使某个绝对误差指标变好，也不能直接宣布预热充分。当前缺少B14，尚不能计算14天双初态差异；外部高度零面也未严格登记，Swarm密度本身有反演误差。内部趋同、外部观测符合和工程运行完整，是三个需要分别验证的问题。','下一步先把监督异常和退出状态恢复机制做成可靠的短测试，再由您决定是否补齐缺失轨迹。原122帧与科学训练门禁保持不变，本轮没有启动训练、轨道传播或额外模拟。'])
 dump(F/'partial_finalization.json',dict(figures=figs,wall_s=time.perf_counter()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,statuses=checks))
 print('Partial finalization',len(figs),'actual figures; B14 not run')
if __name__=='__main__':main()
