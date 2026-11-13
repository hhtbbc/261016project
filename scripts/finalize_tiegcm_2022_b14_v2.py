"""Actual-data v2 synthesis; permanently discloses historical A14 PARTIAL."""
from pathlib import Path
import sys,json,csv,time,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_tiegcm_2022_b14_v2 import F,O,B,H,A,dump
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt

def read(p):
 with p.open() as f:return list(csv.DictReader(f))
def table(rows,keys):return ['|'+'|'.join(keys)+'|','|'+'|'.join(['---']*len(keys))+'|']+['|'+'|'.join(str(r[k]) for k in keys)+'|' for r in rows]
def main():
 start=time.perf_counter();assert json.loads((F/'B14_engineering_gate.json').read_text())['PASS'];assert not json.loads((A/'data_audit.json').read_text())['engineering_PASS'];summary=json.loads((O/'delta14/summary.json').read_text());joint=read(O/'joint_height_summary.csv');obs=read(O/'observation/metrics.csv');changes=read(O/'observation/improvements.csv');jm=read(O/'observation/joint_year_metrics.csv');figs=[]
 def sel(rows,**kw):return next(r for r in rows if all(str(r[k])==str(v) for k,v in kw.items()))
 def jr(y,s,h=450,p='candidate',domain='within_year_four_common'):return sel(joint,year=y,scheme=s,height_km=h,period=p,domain=domain,region='global')
 def obsrow(g,m='A'):return sel(obs,group=g,mapping=m,region='all')
 def save(fig,name):
  fig.text(.5,.006,'EXPLORATORY v2 / 2022 A14 ENGINEERING PARTIAL / B14 PASS / PROVISIONAL HINDCAST',ha='center',fontsize=8);fig.tight_layout(rect=(0,.04,1,1));fig.savefig(O/name,dpi=155);plt.close(fig);figs.append(name)
 # All curves are exact hourly statistics, no smoothing.
 prior=ROOT/'results/tiegcm_2022_dual_initial_spinup_v1/comparison';fig,ax=plt.subplots(figsize=(10,4))
 for label,folder in [('7-day',prior),('14-day (A14 PARTIAL)',O/'delta14')]:
  rows=[r for r in read(folder/'native_ZG_density_hourly.csv') if r['height_km']=='450' and r['region']=='global' and float(r['time_doy_seconds'])>=82*86400]
  ax.plot([(float(r['time_doy_seconds'])-82*86400)/3600 for r in rows],[float(r['relative_P95'])*100 for r in rows],label=label)
 ax.axhline(5,color='red',ls=':',label='5% candidate target');ax.set(xlabel='Hours since 2022-03-23 00 UTC',ylabel='Weighted relative DEN P95 (%)',title='Native ZG 450 km / two initial states / 49 hourly frames');ax.legend();save(fig,'450km_7vs14_timeseries.png')
 variables=['DEN','TN','WIND_VECTOR','O1','O2','N2','HE'];periods=['candidate','last24h','endpoint'];matrix=np.array([[summary['gates'][p][v]['failed_cells'] for p in periods] for v in variables]);fig,ax=plt.subplots(figsize=(7,5));ax.imshow(matrix>0,aspect='auto',cmap=matplotlib.colors.ListedColormap(['#c3e5dd','#efaaa1']),vmin=0,vmax=1)
 for i in range(len(variables)):
  for j in range(3):ax.text(j,i,('PASS' if matrix[i,j]==0 else 'FAIL')+'\n'+str(matrix[i,j]),ha='center',va='center')
 ax.set_xticks(range(3),['Candidate\n49 frames','Last 24 h\n25 frames','Endpoint\nMar25 00 UTC']);ax.set_yticks(range(7),variables);ax.set_title('2022 14-day native-layer frozen gates / failed cells');save(fig,'multivariable_acceptance.png')
 z=np.load(O/'observation/aligned_local.npz');mask=z['common'];hours=np.arange(len(mask))/120;fig,ax=plt.subplots(figsize=(11,4));ax.plot(hours,np.where(mask,z['observed'],np.nan)*1e13,color='black',lw=.8,label='Swarm A DNSAPOD0301')
 for gi,g in enumerate(['A7','B7','A14*','B14']):ax.plot(hours,np.where(mask,z['values'][0,gi],np.nan)*1e13,lw=.8,label=g)
 ax.set(xlabel='2022-03-24 UTC hour',ylabel='Density (1e-13 kg/m3)',title=f'Map A / common N={mask.sum()} / *A14 historical PARTIAL');ax.legend(ncol=5);save(fig,'swarm_four_schemes_timeseries.png')
 fig,axs=plt.subplots(1,3,figsize=(12,4))
 for ax,key,scale,unit in zip(axs,['RMSE','bias','relative_RMS'],[1e13,1e13,100],['1e-13 kg/m3','1e-13 kg/m3','%']):
  ax.bar(['A7','B7','A14*','B14'],[float(obsrow(g)[key])*scale for g in ['A7','B7','A14','B14']],color=['#638dba','#91aec5','#4ab8af','#256e78']);ax.axhline(0,color='black',lw=.5);ax.set(title=key+' / Map A',ylabel=unit)
 save(fig,'swarm_error_metrics.png')
 fig,axs=plt.subplots(1,2,figsize=(11,4))
 for ma in 'ABDE':
  for ax,key,factor in zip(axs,['RMSE','relative_RMS'],[1e13,100]):ax.plot(['A7','B7','A14*','B14'],[float(obsrow(g,ma)[key])*factor for g in ['A7','B7','A14','B14']],'o-',label='Map '+ma)
 axs[0].set(ylabel='RMSE (1e-13 kg/m3)',title='Same common observation IDs');axs[1].set(ylabel='Relative RMS (%)',title='All fixed mappings retained, none selected post hoc')
 for ax in axs:ax.legend(fontsize=8)
 save(fig,'coordinate_map_sensitivity.png')
 fig,axs=plt.subplots(1,2,figsize=(11,4))
 for y in [2021,2022]:
  axs[0].plot(['7-day','14-day'],[100*float(jr(y,s)['relative_P95']) for s in ['7day','14day']],'o-',label=str(y))
  for s,ls in [('7day','--'),('14day','-')]:axs[1].plot([200,300,400,450,475,500],[100*float(jr(y,s,h,domain='cross_year_eight_common')['relative_P95']) for h in [200,300,400,450,475,500]],ls,label=f'{y} {s}')
 axs[0].set(ylabel='450 km weighted relative P95 (%)',title='Mar23-25 (49 frames) / within-year four-way common');axs[1].set(xlabel='Native ZG (km)',ylabel='Relative P95 (%)',title='Eight-way common spatial/time-slot domain')
 for ax in axs:ax.axhline(5,color='red',ls=':');ax.legend(fontsize=8)
 save(fig,'joint_year_internal_sensitivity.png')
 fig,axs=plt.subplots(1,2,figsize=(11,4))
 for y in [2021,2022]:
  axs[0].plot(['7-day','14-day'],[100*float(jr(y,s)['relative_P95']) for s in ['7day','14day']],'o-',label=str(y))
  for g in ['A','B']:axs[1].plot(['7-day','14-day'],[100*float(sel(jm,year=y,mapping='A',group=g+s)['relative_RMS']) for s in ['7','14']],'o-',label=f'{y} {g}')
 axs[0].set(ylabel='Internal DEN difference P95 (%)',title='Native ZG 450 km / Mar23-25');axs[1].set(ylabel='Relative RMS vs DNS (%)',title='External conditional residual / Map A / Mar24')
 for ax in axs:ax.legend(fontsize=8)
 save(fig,'internal_vs_external.png')
 fig,axs=plt.subplots(1,2,figsize=(11,4))
 for label,folder in [('7-day',prior),('14-day',O/'delta14')]:
  rows=[r for r in read(folder/'native_profiles.csv') if r['variable']=='DEN' and r['period']=='candidate' and r['region']=='global'];axs[0].plot([100*float(r['relative_P95']) for r in rows],[int(r['level']) for r in rows],label=label)
  axs[1].plot([100*float(jr(2022,'7day' if label=='7-day' else '14day',h)['relative_P95']) for h in [200,300,400,450,475,500]],[200,300,400,450,475,500],'o-',label=label)
 axs[0].set(ylabel='Native ilev index',title='Same pressure-coordinate index');axs[1].set(ylabel='Native ZG (km)',title='Same native geometric height')
 for ax in axs:ax.axvline(5,color='red',ls=':');ax.set_xlabel('Relative DEN P95 (%)');ax.legend()
 save(fig,'pressure_vs_geometric_height.png')
 fig,ax=plt.subplots(figsize=(9,4))
 for y in [2021,2022]:
  for s in ['7day','14day']:ax.plot([200,300,400,450,475,500],[100*float(jr(y,s,h,domain='own_pair')['coverage']) for h in [200,300,400,450,475,500]],'o-',label=f'{y} {s}')
 ax.set(xlabel='Native ZG (km)',ylabel='Own-pair valid coverage (%)',ylim=(0,102),title='Mar23-25 / own-domain coverage disclosed separately');ax.legend();save(fig,'height_coverage.png')
 # Actual numerical summary, separate qualification dimensions.
 core={}
 for y in [2021,2022]:
  p7,p14=[100*float(jr(y,s)['relative_P95']) for s in ['7day','14day']];core[str(y)]=dict(P95_7_pct=p7,P95_14_pct=p14,reduction_pct=100*(1-p14/p7))
 dump(F/'science_summary.json',dict(core=core,native_gates=summary['gates'],A14_engineering='PARTIAL',B14_engineering='PASS',comparison='EXPLORATORY_V2',v1_complete_engineering='NOT_PASS',science_training_ready=False,figures=figs))
 status=json.loads((B/'status.json').read_text());audit=json.loads((B/'data_audit.json').read_text());manifest=json.loads((F/'input_manifest.json').read_text())
 def report(name,lines):
  with (ROOT/name).open('x') as f:f.write('\n'.join(lines)+'\n')
 boundary=['','工程身份：2022 A14数据完整PASS、历史工程PARTIAL、真实退出码UNKNOWN；B14按本轮独立工程审计PASS。仅探索性v2条件比较，不是原v1双轨完整工程PASS。SCIENCE_TRAINING_READY=False、EXTERNAL_DATUM_UNVERIFIED保留，原122帧不改。']
 eng=['# 2022 B14探索性v2连续模拟工程验收','','协议在启动前冻结；用户本轮明确选择方案B。没有调用旧B14入口，没有重跑A14，无Restart/自动重试。4-rank非物理MPI短测试0.622844秒、父wait rc0、四rank均同会话、清理通过；不是物理模拟预热证据。','','|项|实际结果|','|---|---|',f"|真实TIE-GCM启动|1次|",f"|积分|2022-03-09至25，23040步，60秒/4MPI/OMP1|",f"|监督墙钟|{status['elapsed_s']:.6f}秒|",f"|真实退出码|{status['returncode']}，{status['wait_source']}|",f"|监控资格/缺口/清理|{status['qualification']} / {len(status['gaps'])} / {status['cleanup_verified']}|",f"|采样进程会话RSS峰值|{status['peak_sampled_tree_rss_bytes']/2**20:.3f}MiB，非瞬时严格上界|",f"|CPU user/system|{status['children_cpu_user_s']:.3f}/{status['children_cpu_system_s']:.3f}秒，子进程rusage差值|",f"|NetCDF|{sum(e['bytes'] for e in audit['files'])}字节|",f"|主/小时次记录|{audit['primary_records']}/{audit['secondary_records']}|",f"|实际驱动最大差|{audit['NetCDF_driver_max_abs_difference']:.4e}|",'','每卷≤256MiB，B14新增≤5GiB、聚合会话采样RSS≤16GiB、余盘≥20GiB，计入既有A14后的总输出≤12GiB。监督运行截止4770秒，为4800秒总上限预留30秒清理/最终检查，预算未扩大。','全部33卷SHA/绝对日历/DOY/步长/网格/原生单位/填充、DEN正性、ZG递增、温度风及组分工程检查通过。2304个实际10分钟驱动日志节点及384暖态记录核验；冷echo继承源标量不当作实际驱动差。',f"可执行SHA `{manifest['files'][str((legacy_executable()).relative_to(ROOT))]}`。",'完整输入/协议/代码SHA见input_manifest.json、protocol.json及B14/data_audit.json；原status.json保留直接父子等待证据，派生run_status.json明确引用其SHA。']+boundary
 report('reports/TIEGCM_2022_B14_EXPLORATORY_V2.md',eng)
 spin=['# 2022年双初态7/14天预热条件比较v2','','统一目标窗03-23至25共49整点，末24h25整点。14天方案在候选起点预热14天，03-24观测日实际运行15—16天；7天方案观测日运行8—9天。相对差以同预热A为分母，不把A当真实大气。','DEN5%、TN10K、风矢量20m/s、组分5%，每时/层/六区域≥95%有效点；误差严格小于阈值的原规则与floor1e-8不变。加权P95与逐点通过率分开。','','## 原生层失败格数','']
 spin+=table([dict(variable=v,**{p:summary['gates'][p][v]['failed_cells'] for p in periods}) for v in variables],['variable','candidate','last24h','endpoint'])
 spin+=['','## 原生共同几何高度：同年四轨共同有效域','']+table([dict(km=h,P95_7_pct=100*float(jr(2022,'7day',h)['relative_P95']),P95_14_pct=100*float(jr(2022,'14day',h)['relative_P95']),own14_coverage_pct=100*float(jr(2022,'14day',h,domain='own_pair')['coverage']),failed_cells_14=summary['gates']['candidate']['ZG_'+str(h)+'km']['failed_cells']) for h in [200,300,400,450,475,500]],['km','P95_7_pct','P95_14_pct','own14_coverage_pct','failed_cells_14'])
 spin+=['',f"450km候选P95由{core['2022']['P95_7_pct']:.6f}%变为{core['2022']['P95_14_pct']:.6f}%，相对降低{core['2022']['reduction_pct']:.4f}%。是否低于5%按实际数值判断，不能据此替代完整多变量门槛。",'逐层/区域/时段RMSE、绝对与相对P95、最大差、覆盖和失败格见delta14/；N2在≤1e-5及>1e-5分别保留绝对差/相对差与超5%计数，不能把全部失败归为small放大。','DEN/ZG按ilev；TN、风和组分按实际lev，顶部padding N/A；Z非ZG。每列用实际ZG作log DEN插值，只在双方覆盖域内计算，无外推。','A7/A14原结果只读引用results/tiegcm_2022_spinup_14day_v1/A14_A7/；B7/B14新结果B14_B7/。它们同时改变启动日期和驱动历史，不能全部叫初态误差。最后24h高度趋势见last24h_trends.csv；有限的下降/平台表象不证明20/30天必然收敛。']+boundary
 report('reports/TIEGCM_2022_7VS14_COMPARISON_V2.md',spin)
 ob=['# 2022年Swarm A四方案条件观测对照v2','','2022-03-24 UTC00至23:59:30，DNSAPOD0301瞬时密度30秒。既有原始ZIP/CDF和旧数组SHA核验后复用，下载0；A7/B7/A14查询只读复用，仅新增B14四映射11520查询。全部16组合使用统一quality与共同ID；失败不补零、不外推。','Map-A预先指定为主条件，A/B/D/E定义不变，不择优拟合高度或物理。Swarm是POD相关反演，非无误差真值；30秒点相关，不作独立显著性。','单位：MAE/RMSE/Bias为1e-13 kg/m³，相对RMS=sqrt(mean(((model−DNS)/DNS)^2))，平均有符号相对偏差另列。','']
 ob+=table([dict(Map=ma,group=g,N=obsrow(g,ma)['n'],MAE=float(obsrow(g,ma)['MAE'])*1e13,RMSE=float(obsrow(g,ma)['RMSE'])*1e13,Bias=float(obsrow(g,ma)['bias'])*1e13,relRMS_pct=100*float(obsrow(g,ma)['relative_RMS']),signed_rel_bias_pct=100*float(obsrow(g,ma)['relative_bias']),Pearson=obsrow(g,ma)['Pearson']) for ma in 'ABDE' for g in ['A7','B7','A14','B14']],['Map','group','N','MAE','RMSE','Bias','relRMS_pct','signed_rel_bias_pct','Pearson'])
 ob+=['','正改善率=降低，负值=恶化。','']+table(changes,['mapping','pair','n','RMSE_reduction_pct','relative_RMS_reduction_pct'])
 ob+=['','内部差异缩小不保证外部误差降低：两条模拟可能趋向共同物理偏差；登记未知、驱动/边界/结构误差及DNS反演误差也进入残差。绝对与相对指标可能方向不同，不能相加RMSE或P95。分区与覆盖详见observation/metrics.csv和coverage.csv。']+boundary
 report('reports/SWARM_TIEGCM_2022_FOUR_SCHEME_V2.md',ob)
 synth=['# 2021/2022两年预热与真实观测联合分析v2','','匹配各年03-23至25的49整点；2021原73帧5.869/2.081%统计不覆盖、不混为同一窗口。两年驱动、卫星高度和大气历史不同，不作单一太阳/地磁因果归因。','','## 匹配窗口450km内部差异','']+table([dict(year=y,**core[str(y)]) for y in [2021,2022]],['year','P95_7_pct','P95_14_pct','reduction_pct'])
 synth+=['','同年四轨共同域是主比较；跨年八轨空间/时槽共同域是辅助诊断，不是相同真实UTC。200—500km各自身域及共同域、六区域与三时窗见joint_height_summary.csv和height_domain_coverage.csv。500km不足覆盖只能解释共同有效列，不能称全球完整。','原生多变量两年匹配门槛见joint_native_gates.csv；全部两年观测映射见observation/joint_year_metrics.csv。物理条件趋同与观测符合是不同统计对象；不能从某个初态/映射更接近DNS认定正确初态/高度。']+boundary
 synth+=['','## 两年同源初态的Map-A观测变化','']
 external=[]
 for year in [2021,2022]:
  for initial in ['A','B']:
   u,v=[sel(jm,year=year,mapping='A',group=initial+suffix) for suffix in ['7','14']]
   external.append(dict(year=year,initial=initial,RMSE7_e13=float(u['RMSE'])*1e13,RMSE14_e13=float(v['RMSE'])*1e13,RMSE_reduction_pct=100*(1-float(v['RMSE'])/float(u['RMSE'])),relRMS7_pct=float(u['relative_RMS'])*100,relRMS14_pct=float(v['relative_RMS'])*100))
 synth+=table(external,['year','initial','RMSE7_e13','RMSE14_e13','RMSE_reduction_pct','relRMS7_pct','relRMS14_pct'])
 synth+=['','## 原生层全候选49帧：失败格数','']
 matched=read(O/'joint_native_gates.csv');gate_rows=[]
 for case in ['2021_7day','2021_14day','2022_7day','2022_14day']:
  gate_rows.append(dict(case=case,**{v:sel(matched,case=case,variable=v,period='matched_candidate49')['failed_cells'] for v in variables}))
 synth+=table(gate_rows,['case',*variables])
 synth+=['','内部P95下降与观测误差下降逐初态分别判断。正改善率代表降低，负值代表恶化；不能将少数日期的描述性结果推广至所有年份和初态。2022 A14 PARTIAL身份在所有联合比较中保留。']
 report('reports/TIEGCM_2021_2022_SPINUP_SYNTHESIS_V2.md',synth)
 plan=['# 下一阶段AI训练与数据质量方案v2','','本轮仅方案，无GPU、无统计拟合、无新NPZ或122帧替换。完整科学训练门禁False；工程B14 PASS与A14受限身份分别保留。','','## 数据与变量','1. 以真实逐变量/层/区失败矩阵定位标签敏感性；原生压力DEN达标不等于固定高度或全大气状态达标。FourCastDEN的171目标是TN/UN/VN/WN/Z/DEN契约，O1/O2/N2/He不是直接的171目标通道，但组分不稳定会关联密度、温度与高度状态的物理可靠性，不能忽略诊断证据。','2. 可另建14天候选版本，但须另授权、明确A14工程PARTIAL与各时域身份，冻结选择原则/变量质量/层配准/掩码/单位审计。不得追认原122帧科学合格或删除失败变量宣布全状态PASS。','3. DEN专项小样本工程研究可提出独立受限协议：先做持续性及简单单步基线，再考虑DEN目标的独立网络工程；如果仍输入TN/风/Z，必须审查输入质量，不能以只预测DEN规避输入问题。不同输出头/架构不得冒充官方权重复现。','','WN未设置与DEN/TN/水平风相同的历史冻结门槛，不代表已通过全171目标质量审查；Z与ZG也不能混用。', '## 可执行的受限DEN推进顺序', '建议下一轮先另行冻结DEN工程候选v3协议，授权后CPU提取与177/4/目标通道契约审计，再单独批准小规模单步训练。可优先审查2021 B14与2022 B14v2：两者同为官方smax来源且工程PASS，选择理由是数据资格和来源一致，不是观测RMSE排名；A14仍用于敏感性边界，不自动作为完整合格标签。新候选绝不替换旧122帧。', 'DEN专项仍须按本轮真实DEN结果限定适用性；不通过的层区不得事后静默删除。若仅作工程过拟合/接口实验，须显式说明不能证明科学预测精度。', '## 严格隔离与Direct第一基线','2021仅训练；质量许可后仅用2021拟合训练统计并冻结方法/SHA。2022仅验证，不进梯度或归一化拟合；2023既有测试已被多轮诊断使用，不能把依据这些结果设计的改进称为全新独立测试；禁止再用2023调参，另预留未来未使用测试窗口。','正式Direct先保持177输入/4条件/171目标契约、原AFNONet架构，随机初始化独立训练，不篡改官方权重；先单步，再独立预注册多步改进。掩码顶部padding、逐通道缩放与cos纬度损失，分别报告DEN绝对/相对/log、固定压力层组和几何高度覆盖、其余变量单位指标及持续性对照。','训练前冻结一套独立优化器/学习率/批量/预算/随机种子/checkpoint恢复协议；合成SGD不是作者正式协议。可讨论AdamW独立基线，但不依据2023或本轮观测挑参数，资源需另审计授权；小样本先检查训练损失下降和2022泛化，不宣称全年能力。','','## 扩展数据的优先级','优先扩展季节覆盖，同时预注册安静/扰动及不同太阳活动条件；仅拉长同一春季窗口容易增加高度相关帧。按完整日期/事件块而非逐帧随机拆分，保留跨年验证。建议先预注册每年四季各安静/扰动窗口的小规模成本清点，再决定实际可得数据与帧数；这不是本轮启动授权，也不预设这些数量已足以训练大模型。','最优先三个缺口：未达标层/区及组分标签可靠性；外部高度登记与观测归因；足够季节活动覆盖与严格冻结的统计/训练验证协议。暂不自动21/28天或大规模训练。']+boundary
 report('docs/FOURCASTDEN_AFTER_B14_V2_TRAINING_PLAN.md',plan)
 report('reports/TIEGCM_B14_V2_BRIEFING.md',['# 三分钟组会汇报稿','','这轮我们在新的探索性协议下只补算了一条2022年smax轨迹。首先用四进程短MPI验证监督器确实拥有子进程并取得真实退出码，再冻结驱动、输入和资源预算。新的B14工程资格由直接等待、完整文件及驱动审计独立给出；旧A14仍是数据完整但工程PARTIAL，没有补造退出码。',f"统一03月23日至25日的49个时刻后，2022年450公里双初态密度P95从{core['2022']['P95_7_pct']:.4f}%变为{core['2022']['P95_14_pct']:.4f}%。这衡量模拟对初态的敏感性，不是对真实大气的预测误差。",'我们同时保留温度、风和主要组分的逐层逐区失败记录，不能只看450公里一项就宣布预热充分。然后在相同Swarm观测点上比较四套模拟，固定四种坐标假设，所有改善和恶化方向都保留。','最重要的是内部趋同与外部观测符合不必同步。两种初态可以走向相同的模型偏差，外部高度零面和反演观测不确定性也尚未分离。下一步可以逐步转向明确限定的DEN工程预测，但完整171通道科学训练仍需标签质量、样本代表性及独立训练验证协议，不能把工程成功直接当科学训练放行。'])
 dump(F/'finalization.json',dict(figures=figs,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,A14_engineering='PARTIAL',B14_engineering='PASS',science_training_ready=False));print('V2 reports and actual figures complete',len(figs))
def legacy_executable():
 from run_tiegcm_2022_b14_v2 import legacy_data
 return legacy_data.m.s.BUILD/'tiegcm2.0'
if __name__=='__main__':main()
