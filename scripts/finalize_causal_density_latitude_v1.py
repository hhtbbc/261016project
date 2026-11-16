"""Package frozen results and decisions; no fitting or observation queries."""
from pathlib import Path
import csv,json,hashlib,re,shutil,datetime
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/causal_density_latitude_correction_v1'
def load(n):return json.loads((F/n).read_text())
def rows(n):return list(csv.DictReader((F/n).open()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,s):
 p=ROOT/p;p.resolve().relative_to(ROOT)
 with p.open('x') as f:f.write(s)
def dump(n,x):write(str((F/n).relative_to(ROOT)),json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def md(headers,records):return '| '+' | '.join(headers)+' |\n|'+ '|'.join(['---']*len(headers))+'|\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in records)+'\n'
def main():
 v=load('independent_verification.json');assert v['PASS'];run=load('run_result.json');p=load('correction_parameters.json');m=rows('metrics.csv');r=rows('region_metrics.csv');j=rows('joint_assessment.csv');future=[x for x in j if x['window'].startswith('future_')];primary=[x for x in future if x['case']=='B14'];s=load('logs/worker/status.json');pre=load('preflight.json')
 assert s['qualification']=='PASS' and s['returncode']==0
 coeff=[]
 for y in ['2021','2022']:
  c=p['Global_and_Latitude'][y]['B14']
  for name,a in [('global',c['global_fit'])]+list(c['latitude'].items())+[('Stale06',p['Stale06'][y]['coefficient'])]:coeff.append([y,name,a['N'],f"{a['b']:.12f}",f"{a['multiplier']:.12f}"])
 alltable=[]
 for y in ['2021','2022']:
  for w in ['future_1h','future_3h','future_6h']:
   for x in m:
    if (x['year'],x['case'],x['window'])==(y,'B14',w):alltable.append([y,w,x['method'],x['n'],f"{float(x['RMSE'])*1e13:.6f}",f"{float(x['relative_RMS'])*100:.6f}",f"{float(x['relative_P95'])*100:.6f}"])
 gains=[]
 for x in primary:
  flags=sum(x[k]=='True' for k in ['RMSE_BENEFIT','RELATIVE_RMS_BENEFIT','TAIL_NONWORSENED','LOW_LATITUDE_BIAS_NONWORSENED']);gains.append([x['year'],x['window'],x['method'],f"{float(x['RMSE_gain_pct']):.4f}",f"{float(x['relative_RMS_gain_pct']):.4f}",f'{flags}/4',x['JOINT_NO_REGRET']])
 region=[]
 for x in r:
  if x['case']=='B14' and x['window']=='future_6h':region.append([x['year'],x['region'],x['method'],x['n'],f"{float(x['RMSE'])*1e13:.6f}",f"{float(x['relative_RMS'])*100:.6f}",f"{float(x['relative_bias'])*100:.6f}"])
 totals=[]
 for case in ['B14','A7','B7']:
  for method in ['GlobalAdaptive18','LatitudeAdaptive18','Stale06']:
   a=[x for x in future if x['case']==case and x['method']==method]
   if a:totals.append([case,method,len(a),*[sum(x[k]=='True' for x in a) for k in ['RMSE_BENEFIT','RELATIVE_RMS_BENEFIT','TAIL_NONWORSENED','LOW_LATITUDE_BIAS_NONWORSENED']],sum(x['JOINT_NO_REGRET']=='PASS' for x in a)])
 blocks=[]
 for x in j:
  if x['case']=='B14' and x['window'].startswith('block_'):blocks.append([x['year'],x['window'],x['method'],f"{float(x['RMSE_gain_pct']):.3f}",f"{float(x['relative_RMS_gain_pct']):.3f}"])
 controls=[]
 for x in future:
  if x['case']!='B14':controls.append([x['year'],x['case'],x['window'],x['method'],f"{float(x['RMSE_gain_pct']):.3f}",f"{float(x['relative_RMS_gain_pct']):.3f}",x['JOINT_NO_REGRET']])
 # Compact comparison table without any additional fitting.
 comp=[]
 for y in ['2021','2022']:
  for case in ['B14','A7','B7']:
   for w in ['future_1h','future_3h','future_6h']:
    d={x['method']:x for x in m if (x['year'],x['case'],x['window'])==(y,case,w)}
    comp.append(dict(year=y,case=case,window=w,latitude_vs_global_RMSE_gain_pct=100*(1-float(d['LatitudeAdaptive18']['RMSE'])/float(d['GlobalAdaptive18']['RMSE'])),latitude_vs_global_relative_RMS_gain_pct=100*(1-float(d['LatitudeAdaptive18']['relative_RMS'])/float(d['GlobalAdaptive18']['relative_RMS']))))
 with (F/'latitude_vs_global.csv').open('x',newline='') as out:w=csv.DictWriter(out,fieldnames=comp[0],lineterminator='\n');w.writeheader();w.writerows(comp)
 report='''# 纬度分区因果密度校正 v13-B

日期：2026-11-16 UTC。执行状态 **COMPLETE / 工程核验PASS**；稳定全面收益**未成立**。

身份：**PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED / DATE_HELD_OUT / SAME_CONTINUOUS_TIE_RUN**。
2021/2022-03-23是本轮预先固定的观测日期，区别于v10—v12的03-24；模型场来自旧连续模拟，不能称独立模型运行或全新盲测。

## 1. 数据和执行顺序

B14为主方案，A7/B7为控制，A14排除。两份现有CDF逐字SHA吻合、各2880条UTC严格30秒、flag0=2880，瞬时density kg/m³；原始GRS80大地纬度用于分区。六卷NetCDF逐字SHA吻合v13-A和原审计，原运行returncode0/4 NORMAL EXIT/工程PASS。DEN/ZG在ilev，原单位g/cm³/cm，分别×1000和×0.01。完整多变量科学质量并未因此通过。

本轮先补查同一03-23 B14 [03,06)：每年四真实整点帧，360/360八列查询通过；再冻结协议；随后重新核查六背景15—次日00的十帧、6480/6480实际Map-A查询。总新查询7200，填值/非有限/非正DEN/ZG非单调均0，无垂直外推；包括零权重邻列。18个独立列重建探针满足rtol1e-13/atol0。全部质量有效点进入共同域，没有为了改善删样本。

协议SHA：`'''+sha(F/'frozen_protocol.json')+'''`。
参数SHA：`'''+sha(F/'correction_parameters.json')+'''`。
协议在任何系数之前冻结；全部26个系数在未来评分之前写入并计算SHA，之后未来密度×1e20毒化测试系数逐项不变。Stale06只用当天03-23 [03,06)，未借03-24旧系数。

## 2. 唯一改变的因素

历史[15,18)内，GlobalAdaptive18为median(ln(obs)−ln(model))；LatitudeAdaptive18保持同一公式、历史窗口、质量掩码，仅分abs(lat)<30、30≤abs(lat)<60、abs(lat)≥60三组。未来每个点按自身原始观测纬度应用exp(b)，无平滑、借区、插值、缩放、时间衰减、高度拟合或参数搜索。它是沿已知卫星轨迹的密度输出后处理，不更新模型内部状态，不是全球状态同化，也不是已证明的业务未来预报。

每区历史与未来要求N≥30；不足时完整联合评价N/A，不能回退全局。实际历史各背景2021低/中/高=123/122/115，2022=119/117/124，全部支持；所有实际未来区域也满足N≥30，无N/A。累计1/3/6小时N=120/360/720，共同覆盖率100%。

## 3. B14冻结系数

'''+md(['年份','区域/方法','历史N','b','exp(b)'],coeff)+'''2021低纬系数比全局更大（×1.22879 vs ×1.09224），2022低纬更小（×1.03609 vs ×1.12683）。空间残差差异真实存在，但历史系数幅值并不能保证未来更合理。
控制组完整系数见correction_parameters.json；不跨背景、不跨年份混合。

## 4. B14未来实际误差

RMSE表单位为10⁻¹³ kg/m³；relative RMS与relative P95为百分比，分母固定真实观测密度。MAE/Bias/relativeBias/logRMS/Pearson/max_abs完整值见metrics.csv；不更改swarm_crossyear.metric_row/compare_density。

'''+md(['年','累计窗口','方法','N','RMSE','relative RMS %','relative P95 %'],alltable)+'''下表正改善率为相对Raw下降，负为恶化。四旗标须全部满足才PASS，无加权综合分数。

'''+md(['年','窗口','方法','RMSE收益%','relative RMS收益%','通过项','JOINT'],gains)+'''**主要结论：LatitudeAdaptive18在B14的6/6累计窗口降低绝对RMSE，但relative RMS仅1/6降低，relative P95为0/6不恶化，低纬Bias绝对值4/6不恶化；共11/24个单项通过，JOINT=0/6。** Global为10/24、0/6。Stale06仅2021首小时JOINT通过（3h/6h不通过）；这不构成纬度方法成功证据。

2021局地方法绝对RMSE三个窗口均优于全局，但相对RMS三个窗口均比全局更差（首小时差异很小）。2022局地方法绝对RMSE三个窗口均差于全局；相对RMS仅3h/6h比全局缓解恶化，仍差于Raw。不能称局地方法稳定优于全局。

## 5. 纬度结构和过校正

B14未来六小时，各区同一有效样本；RMSE单位10⁻¹³ kg/m³，Bias是平均有符号相对偏差百分比。

'''+md(['年','纬区','方法','N','RMSE','relative RMS %','relative Bias %'],region)+'''2021低纬Raw +1.450%→Global +10.807%→Latitude +24.661%，局地反而显著加重过校正；低纬relative RMS25.674%→40.003%。2022低纬Raw−1.913%→Global+10.527%→Latitude+1.627%，局地缓解Bias，但relative RMS23.372%→24.189%仍恶化。
2021中纬Bias−4.690%翻转为+7.560%，relative RMS17.654%→20.642%；高纬虽Bias较接近零，relative RMS仍17.753%→18.480%。2022中/高纬Bias分别+5.299%/+19.173%，relative RMS19.228%→21.220%与23.754%→32.583%。因此并未消除空间过校正，也不能从一项Bias改善推断整区误差改善。

## 6. 时间块、点级与背景对照

非重叠块与累计窗分别报告，不把重叠累计窗当独立重复。30秒点有时间相关性，本轮无IID显著性检验。

'''+md(['年','非重叠块','方法','RMSE收益%','relative RMS收益%'],blocks)+'''局地2021仅首小时两RMS同时改善，后两块相对RMS恶化；2022三个块相对RMS都恶化。收益并非固定随时长单调衰减，不能据此拟合未经授权的时间衰减。
点级改善/恶化/不变及全部区域统计见pointwise_diagnostics.csv，未仅保留改善点。

'''+md(['控制年','背景','窗口','方法','RMSE收益%','relative RMS收益%','JOINT'],controls)+'''A7/B7的局地方法均6/6降低RMSE但只1/6降低relative RMS，尾部0/6不恶化；12个控制局地联合评价全部FAIL，支持“空间分区未带来稳定全面收益”，不能按更好的背景替换B14。

'''+md(['背景','方法','未来评价数','RMSE通过','relativeRMS通过','尾部通过','低纬Bias通过','JOINT通过'],totals)+'''以上42个未来方法×年份×背景×累计窗口联合评价共1项PASS，来自B14 Stale06的2021首小时；纬度方法0/18。不能把42项视为42个独立科研重复。98行联合文件还包含历史分析与非重叠块，不能把其总数当主要未来评价数。

## 7. 独立验证、资源与复现

14项新CPU测试及既有11项联合/14项观测可行性/8项小时查询/18项原生密度测试，共65项不同测试全部通过。边界±30/±60、N29拒绝/N30支持、NaN/Inf/零/负密度拒绝、缺区不借用、未来毒化、同样本ID、已有目录拒绝覆盖均覆盖。
独立程序使用排序取中位数、math.exp、直接NumPy物理公式，复算26个系数、560行区域/总体指标、98行联合判定，容差rtol1e-13/atol0不放宽；两份原CDF和全部原NetCDF再SHA核验、205个受保护文件逐字保持、8张PNG解码通过。
独立核验脚本初次把latitude字段误写为lat，KeyError退出；仅修正核验器字段映射后重跑核验成功。失败日志保留，正式拟合/未来评价没有重跑、参数不变。

实际预检3.424746s；正式直接父子监督15.439902s，returncode0/qualificationPASS，worker14.366274s；独立核验4.075124s。worker自报峰RSS318.047MiB，进程树采样峰317.379MiB，两者定义不同，采样峰不能冒充连续树峰。正式监督无采样缺口。独立失败耗时与测试日志另列resource_audit.json；编辑/交互检查未伪装成完整逐秒监控。无下载/GPU/新TIE/DART/轨道，产物远低150MiB，进程内存远低4GiB。

入口：source scripts/activate_orbit.sh；先测试，再prepare（目录必须不存在），最后launch（一次性标记）。verify仅独立复核。具体命令和停止保护见commands.json。现目录保留不得原地重新prepare/launch，复现应先另行授权独立tag，不能删除本结果。

## 8. 科研结论和限制

本轮证明历史纬度残差存在差异，未证明三段常数空间校正能在两个年份稳定改善未来联合指标。2021低纬更大历史系数放大未来过校正，2022低纬系数虽缓解Bias，却把相对误差风险留在中高纬。空间代表性不是唯一已证实的误差原因；历史窗口代表性、纬度与高度/地方时/轨道位置耦合、POD反演偏差和高度登记仍是待验证解释，不能从本实验分离因果。
RMSE²=mean(obs²×relative_error²)，relativeRMS²=mean(relative_error²)，故绝对与相对指标仍可反向；纬度分区并未改变这种目标权重差异。不能通过重新分区/缩放/挑窗把本轮改成PASS。
Map-A仍是临时条件假设，未新增正式高度证据；日期数量只有两天、同一来源POD且同一连续物理运行，沿轨结果不能外推全球。科学训练False、RestartFAIL、DART未准入、真实轨道BLOCKED、2021A14工程PASS仅历史敏感性/2022A14PARTIAL均保持。

下一步：先只读研究历史窗口对未来同纬区的代表性及高度登记，预注册更多日期/截点再申请独立验证；不直接推广局地方法，不通过增加DART复杂度掩盖当前相对误差与尾部恶化。本轮完成即停。
'''
 write('reports/CAUSAL_DENSITY_LATITUDE_CORRECTION_V1.md',report)
 decision='''# v13-B后续决策（未执行下一阶段）

结论：工程完成，纬度分区稳定全面收益未成立。B14局地JOINT0/6，A7/B7局地0/12；相对RMS只在2021首小时改善，全部局地尾部评价恶化。

不部署LatitudeAdaptive18为通用校正器，不修改本轮边界/中位数/窗口/系数，不继续寻优。保留Raw、Global和本轮所有失败结果。

建议优先级：

1. **官方高度登记闭合**：核实ZG零点、模型地理纬度与GRS80/WGS84关系，按现有未发送咨询草稿补齐正式证据；当前不发送或修改接口。
2. **独立历史代表性诊断**：预注册日期/截点，分别统计同一纬区历史与未来残差的分布稳定性，禁止用未来残差反向调系数。先用已有只读数据；需要新日期下载另申请。使用联合四标准，保持Raw对照，两个年份分别报告，不以格点/30秒点作独立重复。
3. 仅在上述审查后另立单因素候选实验。不能同时加入高度拟合、时间衰减或平滑；新空间方法必须由用户另授权、先冻结，再独立日期验证。本轮证据只支持继续诊断空间/时间代表性，不支持增加模型复杂度或业务部署。

候选下一轮只读诊断预算：CPU≤600s、RSS≤4GiB、派生产物≤150MiB、无GPU/物理积分/同化/轨道；这是申请方案，不是授权执行。原始数据保持只读，Swarm B保留不读取。

DART准入仍不具备：Restart连续/分段一致性FAIL；正式高度未登记；观测误差与相关性、状态更新算子、合法集合生成、本地版本兼容性及独立验证/集合资源门禁未闭合。简单输出校正的部分绝对收益不能替代这些条件。
科学训练False、真实轨道BLOCKED、两年A14历史身份保持。本轮停止，等待明确下一轮指令。
'''
 write('docs/CAUSAL_DENSITY_LATITUDE_CORRECTION_NEXT_DECISION_V1.md',decision)
 commands=['source scripts/activate_orbit.sh','python -m unittest discover -s tests -p test_causal_density_latitude.py -v','python scripts/prepare_causal_density_latitude_v1.py','python scripts/launch_causal_density_latitude_v1.py','python scripts/verify_causal_density_latitude_v1.py']
 dump('commands.json',dict(actual_order=commands,regressions=['test_late_day_correction.py','test_observation_feasibility_v1.py','test_hourly_tiegcm_observation.py','test_tiegcm_density_provider.py'],no_rerun_warning='prepare refuses existing experiment; supervisor launch_once marker refuses repeated run; do not remove histories to rerun',verification_initial_error_log='logs/latitude_correction_v1_verification.log',verification_success_log='logs/latitude_correction_v1_verification_fixed.log',new_model_queries=7200,network='no observation/data network access; Git synchronization only',base_code_commit='dcff26fca4f637d6c7bda693a1ef0319e6ba59b9',frozen_code_SHA='frozen_protocol.json.code_SHA256'))
 total=sum(x.stat().st_size for x in F.rglob('*') if x.is_file())
 dump('resource_audit.json',dict(preflight_wall_s=pre['wall_s'],supervised_formal_wall_s=s['elapsed_s'],worker_wall_s=run['wall_s'],independent_verification_wall_s=v['wall_s'],independent_verification_first_attempt_failed_wall_s=2.123991313,measured_stage_wall_s_sum=pre['wall_s']+s['elapsed_s']+v['wall_s']+2.123991313,tests_distinct=65,test_runtime_basis='Ran N tests in ... lines in logs; initial13 plus final14 executions retained',worker_peak_RSS_MiB=run['peak_RSS_MiB'],peak_sampled_tree_RSS_MiB=s['peak_sampled_tree_rss_bytes']/2**20,supervisor_samples=len(s['samples']),sampling_gaps=s['gaps'],output_bytes_at_audit=total,output_limit_bytes=150*2**20,min_sampled_disk_free_bytes=min(x['free_disk_bytes'] for x in s['samples']),formal_returncode=0,formal_launches=1,formal_retries=0,query_count=7200,downloads=0,GPU=0,TIE=0,DART=0,orbit=0,continuous_global_monitor=False,limits_note='Measured stages and test logs cover computational analysis; interactive inspection/editing not falsely reconstructed as continuous monitoring. Supervisor sampled RSS is not a guaranteed continuous tree peak. Worker rusage is process maximum.',all_measured_limits_PASS=total<150*2**20 and s['elapsed_s']<600 and s['peak_sampled_tree_rss_bytes']<4*2**30))
 status=ROOT/'STATUS.md';old=status.read_text();intro='> 最新（2026-11-16，v13-B纬度分区因果校正）：CAUSAL_DENSITY_LATITUDE=COMPLETE（执行完成，非科学收益PASS）。03-23两年B14早窗720/720、六背景晚窗6480/6480八列查询与SHA通过，先冻结协议/26系数再未来评分及毒化验证。65项CPU测试；独立复算26系数/560指标/98联合行、205旧资产逐字不变。B14局地未来1/3/6h RMSE收益2021=52.598/26.049/26.460%，2022=8.479/7.516/10.288%；relativeRMS收益2021=13.599/−39.513/−36.349%，2022=−25.872/−25.334/−18.570%。局地B14联合0/6、A7/B7联合0/12；低纬2021过校正加重、2022Bias缓解但中高纬仍有恶化。正式监督exit0/PASS15.440s、worker峰RSS318.047MiB；核验器字段名错误一次已修正并保留日志，正式实验无重跑。无下载/新TIE/GPU/DART/轨道，历史目录不改。报告reports/CAUSAL_DENSITY_LATITUDE_CORRECTION_V1.md；科学训练False/外部高度未验证/RestartFAIL/DART未准入/真实轨道BLOCKED/A14历史身份保持。任务完成即停。\n\n';status.write_text(old.replace('# 当前状态\n\n','# 当前状态\n\n'+intro,1))
 with (ROOT/'WORKLOG.md').open('a') as f:f.write('''\n\n## 2026-11-16 — v13-B 纬度分区因果密度校正\n\n目标：仅改变空间代表性，03-23独立观测日期，B14主/A7B7控制，A14排除。根目录realpath已核验；起始本地/远端main=dcff26fca4f637d6c7bda693a1ef0319e6ba59b9，无覆盖旧目录。\n实际：重验两CDF与六原卷/配置/驱动SHA；B14同日[03,06)各360/360四帧八列、晚间六背景各1080/1080十帧，共7200有效查询，无外推或填充值；协议SHA bb1346ddbb0bae33fb8678a0b5341d804b627612999fd94e113a7c23ca90941c。所有26系数先冻结再未来毒化和评分，Stale不借03-24。三纬区历史N2021=123/122/115，2022=119/117/124。\n环境/命令：source scripts/activate_orbit.sh；unittest新14+旧51=65项；prepare_causal_density_latitude_v1.py→launch_causal_density_latitude_v1.py→verify_causal_density_latitude_v1.py。入口有已存在目录/一次性标记拒绝重复，未运行GPU/TIE/DART/轨道或下载。完整命令见experiments/causal_density_latitude_correction_v1/commands.json。\n结果：B14局地1/3/6h绝对RMSE均下降，但relative RMS仅2021首小时下降；联合0/6、控制局地0/12。2021六小时Raw/Global/Latitude相对RMS20.795/23.426/28.354%，2022为22.197/28.189/26.319%。低纬Bias2021从+1.450%变+24.661%，2022从−1.913%变+1.627%；未形成一致收益。B14局地四旗标计11/24（6+1+0+4），全部局地尾部未通过。42项主要未来联合评价中仅2021 B14 Stale首小时通过，不是新方法成功。\n验证：独立排序中位数/exp/历史N和SHA/560指标/98联合行，rtol1e-13 atol0；未来毒化不影响系数；205保护文件不变，8PNG。核验器首试误读缓存latitude为lat发生KeyError，仅修正核验脚本后复核成功，失败日志与成功日志均保留，正式拟合评价未重跑。\n资源：预检3.425s，正式监督15.440s/exit0/PASS，worker14.366s/峰RSS318.047MiB，独立核验4.075s；采样树317.379MiB不是连续最大值。CPU计算阶段远低600s，输出约21MiB且<150MiB；编辑/交互不虚构连续采样。详见resource_audit.json。\n文件：src/evaluation/causal_density_latitude.py，prepare/run/verify/launch/finalize入口，tests/test_causal_density_latitude.py，新实验CSV/JSON/8图；reports/CAUSAL_DENSITY_LATITUDE_CORRECTION_V1.md和下一阶段决策。完整逐点原始值/查询轨迹只保存在_local缓存，不入库。\n状态：COMPLETE仅工程执行，科学训练False/高度未登记/RestartFAIL/DART未准入/真实轨道BLOCKED不变，2021A14工程PASS仅历史敏感性、2022A14PARTIAL保持。下一步建议先闭合高度与只读历史代表性诊断，不自动新校正/同化；完成后停止。Git按安全规则逐文件白名单、远端复核再正常推送，最终SHA与同步结果由本轮本地sync审计及最终答复记录。\n''')
 print('Report, decision, status, worklog, resource and command records written.')
if __name__=='__main__':main()
