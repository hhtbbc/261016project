"""Write reports from frozen measured outputs; no querying, fitting or tuning."""
from pathlib import Path
import sys,json,csv,hashlib,re,time,datetime
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/causal_density_correction_v1'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def write(p,s):
 assert p.resolve().is_relative_to(ROOT)
 with p.open('x') as f:f.write(s)
def mdtable(rows,cols):return '|'+ '|'.join(cols)+'|\n|'+'|'.join(['---']*len(cols))+'|\n'+'\n'.join('|'+ '|'.join(str(x[c]) for c in cols)+'|' for x in rows)+'\n'
def main():
 start=time.perf_counter();rows=list(csv.DictReader((F/'improvements.csv').open()));metrics=list(csv.DictReader((F/'metrics.csv').open()));p=json.loads((F/'correction_parameters.json').read_text())['parameters'];ver=json.loads((F/'independent_verification.json').read_text());manifest=json.loads((F/'matched_samples_manifest.json').read_text());assert ver['PASS'];assert json.loads((F/'fit_evaluation_verification.json').read_text())['PASS']
 statuses={str(path.relative_to(F)):json.loads(path.read_text()) for path in list(F.glob('query_job*/status.json'))+[F/'evaluation_job/status.json']};testlogs=[ROOT/'logs'/n for n in ['causal_density_v1_v9tests.log','causal_density_v1_native_tests.log','causal_density_v1_hourly_tests_v2.log','causal_density_v1_operator_tests_v2.log','causal_density_v1_correction_tests.log']];testresults=[]
 for log in testlogs:
  s=log.read_text();m=re.search(r'Ran (\d+) tests in ([\d.]+)s',s);assert s.strip().endswith('OK');testresults.append(dict(file=str(log.relative_to(ROOT)),tests=int(m[1]),wall_s=float(m[2])))
 measured_wall=sum(s['elapsed_s'] for s in statuses.values())+ver['wall_s']+sum(x['wall_s'] for x in testresults);peak=max(s['peak_sampled_tree_rss_bytes'] for s in statuses.values());output=sum(x.stat().st_size for x in F.rglob('*') if x.is_file());assert measured_wall<600 and peak<4*2**30 and output<150*2**20
 resources=dict(measured_core_CPU_task_wall_sum_s=measured_wall,definition='Sum of 4 supervised subprocess tasks INCLUDING both failed pre-query attempts, independent verifier and 5 passing test suites; small interactive metadata/read/write commands not individually metered; not total conversation elapsed time',supervised_stages={k:{kk:v.get(kk) for kk in ['qualification','returncode','stop_reason','elapsed_s','peak_sampled_tree_rss_bytes','cleanup_verified']} for k,v in statuses.items()},unit_tests=testresults,independent_verifier_wall_s=ver['wall_s'],peak_sampled_tree_RSS_MiB=peak/2**20,peak_query_worker_rusage_MiB=json.loads((F/'query_run.json').read_text())['peak_RSS_MiB'],output_bytes_before_report=output,limits=dict(CPU_wall_s=600,RSS_GiB=4,output_MiB=150),new_download_bytes=0,GPU=0,TIE=0,DART=0,orbit=0)
 write(F/'resource_audit.json',json.dumps(resources,indent=2)+'\n')
 eng=[]
 for case in manifest['cases']:
  c=case['case'];row=next(x for x in csv.DictReader((ROOT/'results/thermosphere_observation_assimilation_feasibility_v1/eight_trajectory_provenance.csv').open()) if x['case']=='2022_'+c);folder=(ROOT/row['input']).parent;j=json.loads((folder/'run_status.json').read_text());assert j['returncode']==(None if c=='A14' else 0)
  eng.append(dict(case=c,engineering=case['engineering'],original_run_status=str((folder/'run_status.json').relative_to(ROOT)),original_status_SHA256=sha(folder/'run_status.json'),returncode=j['returncode'],original_run_wall_s=j['elapsed_s'],normal_exit_count=j['normal_exit_count'],density_queries_valid=not case['query_failures'],hourly_frames=case['frames'],DEN='g/cm3,ilev29 ->kg/m3 *1000',ZG='cm,ilev29 ->m *.01',A_previous_output_max_relative_difference=case['A_prior_max_relative_difference']))
 write(F/'engineering_identity_audit.json',json.dumps(eng,indent=2)+'\n')
 coeff=[dict(case=c,engineering=p[c]['engineering'],N=p[c]['calibration_N'],b=f"{p[c]['b']:.9f}",multiplier=f"{p[c]['density_multiplier']:.9f}") for c in p]
 mainrows=[]
 for x in rows:
  if x['case']=='B14' and x['window'].startswith('future_'):
   mainrows.append(dict(satellite=x['satellite'],window=x['window'],N=x['N'],raw_RMSE_e13=f"{float(x['raw_RMSE'])*1e13:.6f}",corrected_RMSE_e13=f"{float(x['corrected_RMSE'])*1e13:.6f}",RMSE_gain_pct=f"{float(x['RMSE_improvement_pct']):.4f}",raw_relativeRMS_pct=f"{float(x['raw_relative_RMS_pct']):.4f}",corrected_relativeRMS_pct=f"{float(x['corrected_relative_RMS_pct']):.4f}",relativeRMS_gain_pct=f"{float(x['relative_RMS_improvement_pct']):.4f}"))
 allsix=[]
 for x in rows:
  if x['window']=='future_6h':allsix.append(dict(case=x['case'],engineering=x['engineering'],satellite=x['satellite'],raw_relativeRMS_pct=f"{float(x['raw_relative_RMS_pct']):.4f}",corrected_relativeRMS_pct=f"{float(x['corrected_relative_RMS_pct']):.4f}",RMSE_gain_pct=f"{float(x['RMSE_improvement_pct']):.4f}"))
 report='''# 严格因果观测约束密度输出校正：首轮实验 v1

2026-11-16。`CAUSAL_DENSITY_CORRECTION=PILOT_COMPLETE`表示冻结实验已完成，**不是全球物理精度或同化科学PASS**。身份：PROVISIONAL Map-A / HINDCAST / OUTPUT_BIAS_CORRECTION / DEVELOPMENT_DIAGNOSTIC。

## 1. 科学问题与冻结设计

检验过去3小时A观测得到的一个标量偏差，是否能在未来1/3/6小时A及C轨迹保留收益。本轮按用户新指令使用严格半开窗口：校正[03,06)，评价[06,07)、[06,09)、[06,12)。06:00当前观测绝不参与估计；另预注册不重叠[07,09)、[09,12)作描述诊断。无趋势、空间、高度偏移拟合，无参数搜索。

v9 section3明确将局地核数值留待下一轮最终冻结，其并非已经实施算子。本轮启动前曾就候选冲突发出澄清；按本轮4.1/4.2明确公式冻结`b=median(ln(obs)-ln(TIE))`、`rho_corr=rho_raw*exp(b)`。没有混入v9局地核/时间衰减。旧v9预测端点/15分钟窗口也被本轮新半开累计窗口明确取代；原计划文件保持只读。协议SHA与系数文件关联，参数文件在未来指标计算前写入。

主背景B14沿用v9来源/工程选择，不由未来误差排名选定。A7/B7是独立对照；A14历史engineering PARTIAL，仅敏感性，不纳入主结论，也不升级原v1双轨资格。所有CDF/NetCDF只读，无TIE/GPU/DART/轨道启动或新观测下载。

## 2. 数据、工程身份与观测算子

复用2022 A/C各2880条0301原件。实际查询A的[03,12)1080点、C的[06,12)720点；四背景共7200次，全部有效，无补0/外推/裁边/备用密度。每个背景按真实原生ZG处理，10个连续小时帧03—12，29 ilev×36纬×72经；DEN g/cm3乘1000、ZG cm乘.01。NetCDF源卷SHA按历史data_audit逐一复核，源初场/GPI/input身份保留。运行退出记录和独立字段扫描另见engineering_identity_audit.json、independent_verification.json。

统一流程：CDF UTC/GRS80地理位置→EarthLocation ITRS→既有DensityQuery及Map-A显式适配→原生8列全有效检查→各列log密度垂直插值→水平密度双线性→时间密度线性。没有修改成熟10min provider；复用已验收hourly适配器。query_trace_local.jsonl保存每点源UTC、映射坐标、时间权重、水平邻点、层号/层高/垂直权重、顶高余量和拒绝原因。适配记录中的高度差是数值插值几何量，不能当坐标登记误差。

A/C原始共同有效质量均为0301 flag0、密度正且有限。所有原始/修正指标使用完全相同ID；每背景自身和工程PASS背景共同覆盖均100%。A14单独标记。旧逐点NPZ历史预期SHA未在v9清单中找到，因此本轮只冻结当前身份作为辅助对照；主实验重新读取历史SHA核验的原始NetCDF，不依赖其正确性。新A查询与旧结果在1e-12相对容差内一致，实际差见matched manifest。

## 3. 真实历史残差与校正量

'''+mdtable(coeff,list(coeff[0]))+'''
每条轨迹360个过去A样本，各自独立估计，不混合背景；C校正输入数0，B密度未读。未来A密度毒化20个数量级后，所有b精确不变。

B14历史log残差P05=-0.110067、P95=0.334888，std=0.147903；与高度、纬度的描述相关分别-0.328126/+0.312349，表明单一尺度不能消除所有轨道结构。纬度和高度相互相关，不能由这些相关性作因果归因。本轮不据此追加空间拟合。历史拟合RMSE下降36.6086%，relativeRMS16.9593%→15.1338%；该成绩单列为in-sample，不能证明未来收益。

## 4. B14主结果：未来密度误差

RMSE列单位为10^-13 kg/m³；相对RMS采用逐点观测密度作分母，无新floor。改善率正值为下降。

'''+mdtable(mainrows,list(mainrows[0]))+'''
结论：本日固定Map-A、固定B14下，A与C三个累计未来窗口的RMSE及相对RMS均下降，初步支持历史输出尺度校正具有局部时间外推和跨卫星迁移价值。不能外推为全年、独立真值或全球三维预测收益。

RMSE收益随累计时长略降：A43.98→41.79→39.64%，C40.38→39.63→38.75%；但相对RMS收益不是单调衰减。非重叠1—3h、3—6h的A相对RMS改善5.68%/25.61%，C2.04%/27.77%左右（精确值见improvements.csv）。累计窗口互相重叠，不能将3个数字当独立重复或据此拟合衰减时标。

B14六小时逐点：A514改善/206恶化；C520改善/200恶化。没有删除这些不利点。六小时A有符号相对Bias由-14.3961%变为-2.8888%；C由-14.8987%变为-3.4590%。低纬A偏差由-9.3877%变为+2.7928%，C由-9.7977%变为+2.3276%，体现局部过校正；中高纬另有不同收益。全部区域与N/A少样本标记见metrics.csv，不因平均改善隐藏局部恶化。

正的恒定乘数不改变Pearson相关；B14六小时A原始/修正均约0.98026，C均约0.98052。因此本轮证明的是偏差/幅值修正，**不是相关结构、初场或内部演化被改进**。无非正/非有限校正密度。

## 5. 其他背景及A14敏感性

'''+mdtable(allsix,list(allsix[0]))+'''
A7/B7在两个卫星的未来1/3/6小时累计RMSE也均改善；不根据改善幅度重选模型。A14仅敏感性，历史PARTIAL不改。不同背景校正后接近并不能证明其完整温度/风/组分或初态都准确。

## 6. 数值验证与资源

52项CPU测试通过：v9 14、原生provider18、hourly8、新观测算子6、校正因果6。覆盖解析插值/周期/极区/时间高度拒绝/填值/零权重坏邻列拒绝/Map-A追踪/未来毒化/非A禁拟合。合成场仅用于数值算法测试。独立直读3个真实CDF×3时刻=9探针，与既有解析一致；24个真实8列加权重建探针通过1e-13相对容差。独立显式扫描本次用到的原始DEN/ZG帧，_FillValue/missing_value、非有限、极大哨兵与非正DEN均为0；逐案逐文件记录保留。

两次正式查询前CPU工程失败已保留：首先错误假设v9保护清单含旧NPZ；其次通用监督器将NetCDF警告回显源代码中的np.nan误识别为致命数值输出。后者改为将Python警告原样保存结构化文件，不改监督器或密度有效门禁。前两次都未进行校正估计；独立query_job_v3正常退出。原始CDF/NetCDF未改。初次hourly/新测试入口缺PYTHONPATH错误也保留，修正入口后通过，不放宽容差。

'''+f"计量核心CPU任务累计{measured_wall:.3f}秒（包括两个失败查询前任务、最终查询、估计评价、独立核验和通过的测试套件）；小型交互文件检查未逐任务计时，不声称自然墙钟或全部进程总时间的精确值。最终查询监督10.928秒，估计/6图评价监督6.143秒，峰值采样进程树RSS{peak/2**20:.3f}MiB；当前实验目录约{output/2**20:.3f}MiB，低于150MiB。采样峰值不是连续瞬时峰值。完整资源定义见resource_audit.json。\n"+'''
## 7. 高度、观测及因果解释限制

EXTERNAL_DATUM_UNVERIFIED不变：Map-A仍把WGS84大地纬度及椭球高近似模型纬度/ZG。此次没有新证据证明零面相同，也没有用RMSE拟合高度。详见HEIGHT_DATUM_OFFICIAL_EVIDENCE_UPDATE_V1。尺度b可能同时吸收模型偏差、坐标误差和POD产品处理偏差，不能唯一解释成物理密度偏差。

A/C高度及轨迹接近，且反演方法相关；C称跨卫星开发诊断，不称完全独立真值。Swarm B仍未读。未来真实GPI是已有hindcast驱动，未来模型场是既有积分结果；未来观测未进入校正，但这不等于已经验证实时驱动预测。30秒点相关，没有做IID显著性检验。单日单cutoff不足以证明跨日期/活动/高度泛化；没有全局修正场物理守恒、初场更新、Restart或未来状态演化验证。

## 8. 后续准入与复现

建议下一轮冻结同一方法，在未参与参数选择的日期/截点作只读复现，并平行获取官方高度解释；不要自动升级到空间拟合或EnKF。DART八项准入仍不满足，Restart/He算子/误差模型/合法集合/版本实测/独立验证等未解决。真实Cd/面积/姿态/推力/完整受力和高度门禁未闭合，不开展真实轨道精度验证。

复现入口：source scripts/activate_orbit.sh；commands.json列出数据检查、52测试、查询和评价入口。各任务有一次性目录/参数文件保护，不能盲目重放到原目录；若未来复现需新tag授权。sha256_manifest.json记录代码、输入及轻量输出。原始匹配数组、全查询诊断及观测值只本地，公开派生残差/指标/图表不包含原始密度全表。
'''
 # Insert exact incremental percentages, avoid rounded speculative text.
 for sat in ['A','C']:
  x=next(x for x in rows if x['case']=='B14' and x['satellite']==sat and x['window']=='incremental_3_6h')
  if sat=='C':report=report.replace('27.77%左右',f"{float(x['relative_RMS_improvement_pct']):.4f}%")
 write(ROOT/'reports/CAUSAL_DENSITY_CORRECTION_PILOT_V1.md',report)
 decision='''# 因果密度输出校正：下一阶段决策 v1

2026-11-16。首轮PILOT_COMPLETE，保持OBSERVATION_CONSTRAINED_PHYSICS_FIRST。没有启动下一轮。

## 已有证据

B14 A历史360点得到b=0.1261252775，exp(b)=1.1344242772，未来1/3/6小时A和C累计RMSE均下降。六小时A相对RMS19.1526→14.6187%，C19.6946→15.0158%。但A206/720、C200/720个点恶化，低纬存在过校正，Pearson不变。只能支持该Map-A日期/截点的幅值偏差可被历史信息部分修正。

## 优先级

1. **保持中位数常数方法，做新的预注册截点/日期验证**，不是先增加模型复杂度。当前同日未来结果已查看，不能再作为新盲测；新cutoff、窗口、模型及数据角色须先冻结，不能筛选收益好的时段。优先使用已有覆盖中的未用日期，若缺独立C则另申请小下载，不在本轮执行。基于本次核心任务约26秒，下一轮CPU≤600秒、RSS≤4GiB、输出≤150MiB为候选预算，需按实际查询数重估。
2. **平行闭合外部高度登记**。现有b可能吸收高度误差，不以更小RMSE决定正确映射；复用维护者咨询草稿，未授权不发送。所有条件研究仍显式PROVISIONAL。
3. 待上述复现后，才另立单因素局地校正或时间有效性对照。不能在同一开发窗口改核宽、衰减后称独立改善。未来若加C历史，C降为输入/开发，B继续保留；B不得参与方法选择。

## DART八项检查：本轮不准入

|项目|状态|主要缺口|
|---|---|---|
|连续/分段Restart一致性|BLOCKED|已有数值FAIL未修复|
|状态与密度观测映射|PARTIAL|当前仅输出算子，含He及内部状态更新需验证|
|正式高度登记|BLOCKED|ZG外部零面无新官方证明|
|观测误差模型|PARTIAL|POD时间/跨星相关和系统尺度未定|
|版本兼容性实测|NOT_RUN|仅静态DART审查|
|合法成员生成及分析写回|NOT_RUN|不能伪造_NM或时间标签|
|集合资源与数量|PARTIAL|外部20/90示例不是已证最小数|
|未使用独立验证|PARTIAL|B保留但未取得/验证；C已开发且POD相关|

不因简化校正得到局部收益而自动部署EnKF。本轮没有改善内部状态或未来演化的证据。

## 轨道及科学状态

真实轨道验证继续BLOCKED：真实气动面积/Cd、姿态与推力、完整受力、高度及POD/SP3信息关联尚缺。SCIENCE_TRAINING_READY=False；A14工程PARTIAL保持；不运行DART、GPU或轨道。
'''
 write(ROOT/'docs/CAUSAL_DENSITY_CORRECTION_NEXT_DECISION_V1.md',decision)
 commands=dict(workspace=str(ROOT),environment='source scripts/activate_orbit.sh; PYTHONPATH=$PWD/src:$PWD for tests; CPU subprocess CUDA_VISIBLE_DEVICES empty',commands=['python -m unittest discover -s tests -p test_observation_feasibility_v1.py -v','python -m unittest discover -s tests -p test_tiegcm_density_provider.py -v','python -m unittest discover -s tests -p test_hourly_tiegcm_observation.py -v','python -m unittest discover -s tests -p test_causal_density_operator.py -v','python -m unittest discover -s tests -p test_causal_density_correction.py -v','python scripts/launch_causal_density_query_v1.py','python scripts/launch_causal_density_evaluation_v1.py','python scripts/verify_causal_density_v1.py','python scripts/finalize_causal_density_v1.py'],warning='Existing run directories/parameter files are immutable. No automatic rerun. Initial failures and versioned logs retained.')
 write(F/'commands.json',json.dumps(commands,indent=2)+'\n');write(F/'run_manifest.json',json.dumps(dict(state='PILOT_COMPLETE',scientific_validation='CONDITIONAL_SINGLE_DAY_ONLY',frozen_protocol_SHA256=sha(F/'frozen_protocol.json'),query_count=7200,fit_samples_per_case=360,final_test_count=52,CDF_probes=9,real_interpolation_probes=24,resources='resource_audit.json',science_training=False,external_datum='EXTERNAL_DATUM_UNVERIFIED',real_orbit='BLOCKED',A14='PARTIAL',new_GPI_TIE_DART_GPU_orbit_runs=0),indent=2)+'\n')
 status=ROOT/'STATUS.md';s=status.read_text();entry='> 最新（2026-11-16，因果密度输出校正v1）：CAUSAL_DENSITY_CORRECTION=PILOT_COMPLETE（条件单日实验完成，非科学PASS）。四背景7200次Map-A原生查询全部有效，52CPU测试/9CDF/24真实插值探针及显式原始填值扫描通过。主B14仅过去A[03,06)360点中位log偏差b0.1261252775、乘数1.1344242772；A未来1/3/6h RMSE下降43.9779/41.7904/39.6393%，C下降40.3839/39.6317/38.7484%。六小时相对RMS A19.1526→14.6187%、C19.6946→15.0158%；仍有A206/C200个点恶化、低纬过校正，Pearson不变，非全局或完全独立真值验证。A7/B7对照、A14仅PARTIAL敏感性，不择优换模型。恒定中位数按本轮明确公式冻结，未混入v9待定局地核；C不拟合、B未读，无新观测下载/TIE/GPU/DART/轨道。零面仍无新官方证据，DART八项未准入。报告reports/CAUSAL_DENSITY_CORRECTION_PILOT_V1.md；下一轮仅建议新日期/截点复现并平行高度登记，不自动执行。科学训练False/真实轨道BLOCKED/A14PARTIAL保留。\n\n';status.write_text(s.replace('# 当前状态\n\n','# 当前状态\n\n'+entry,1))
 work=ROOT/'WORKLOG.md';work.write_text(work.read_text()+f'''\n\n## 2026-11-16：严格因果密度校正首轮v1\n- 范围：CPU输出校正、观测算子验证、高度有界官方审查；无原始观测下载、TIE/DART/GPU/轨道。v9本地3c394fc...完整保留；用户记录的v9 SHA有笔误，以实际HEAD为准。远端仍b2c8752...且为本地祖先，正常推送一次因旧VSCode socket认证失败，未强推/覆盖，继续本地实验。\n- 协议：v9局地核为待最终冻结候选，本轮用户明确4.1/4.2常数中位数；曾发澄清，按当前明确公式和半开窗口冻结。B14主背景不由未来表现选择，A7/B7对照，A14工程PARTIAL仅敏感性。过去A[03,06)360点，各背景独立b；C未来不拟合，B未读；未来[06,07)/[06,09)/[06,12)，无衰减/拟合高度/调参。\n- 输入/算子：复用0301 CDF、hourly TIE及独立Map-A适配。4背景10小时帧、29ilev×36×72，7200真实查询全部有效；逐点时空/8邻列/垂直层及权重存query_trace_local.jsonl，原NetCDF/source/GPI/input历史SHA核验。未在v9保护表找到旧aligned NPZ的历史SHA，因此只冻结当前辅助身份，主实验重查原NetCDF。\n- 验证：52 CPU测试通过（14+18+8+6+6），9真实CDF探针、24真实8列重建探针通过；独立显式扫描原DEN/ZG填值/非有限/正性，0无效。未来A毒化20数量级不改变b；C/B禁止拟合；raw/corrected同ID。原数据及统计不改。\n- 结果：B14 b0.1261252775057784、exp(b)1.1344242772252575。A未来1/3/6h RMSE改善43.977936/41.790363/39.639338%；C40.383928/39.631699/38.748437%。6h relativeRMS A19.152622→14.618712%、C19.694606→15.015780%；A206/720、C200/720点恶化，低纬略过校正，Pearson缩放不变。累计RMSE收益略减，相对RMS收益非单调；不拟合衰减率或作IID显著性。全案例/区域/分析期和不重叠时段指标保留。\n- 异常保留：测试入口缺src PYTHONPATH；首查询前旧NPZ SHA列表KeyError；第二次通用监督将NetCDF warning回显np.nan误报fatal。两次未校正；第三次只把Python warnings原样存结构化文件，监督/物理门槛不改，数据不补0。CPU失败/脚本快照/事件日志保留；非模型积分重试。\n- 实测资源：计量核心CPU任务含失败尝试合计{measured_wall:.3f}秒（不冒称交互文件操作或自然等待总墙钟），查询监督10.928秒、估计绘图监督6.143秒、峰值采样树RSS{peak/2**20:.3f}MiB，目录约{output/2**20:.3f}MiB；600秒/4GiB/150MiB预算未扩张。6图已生成，图6视觉检查通过，52测试及独立核验日志/完整命令在新run目录。\n- 高度：重读NCAR2016 grid/altitude及VirES官方定义，仍无外部零面等价证明；复用已有咨询草稿，未发邮件。保持EXTERNAL_DATUM_UNVERIFIED。\n- 交付：reports/CAUSAL_DENSITY_CORRECTION_PILOT_V1.md、reports/HEIGHT_DATUM_OFFICIAL_EVIDENCE_UPDATE_V1.md、docs/CAUSAL_DENSITY_CORRECTION_NEXT_DECISION_V1.md；新模块/测试/查询与评价脚本、残差/系数/指标/覆盖/资源/SHA/6图。状态PILOT_COMPLETE不等于科学PASS；优先新cutoff/日期复现+高度登记，DART和真实轨道均不准入，科学训练False、A14PARTIAL不改。\n''')
 print('REPORTS, STATUS AND WORKLOG COMPLETE',flush=True)
if __name__=='__main__':main()
