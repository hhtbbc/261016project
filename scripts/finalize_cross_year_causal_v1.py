"""Publish measured v11 results and limitations; no new model evaluation or fitting."""
from pathlib import Path
import sys,json,csv,re,time
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/cross_year_causal_density_validation_v1'
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
from prepare_fourcastden_swarm_observation_v1 import sha

def write(path,text):
 assert path.resolve().is_relative_to(ROOT)
 with path.open('x') as out:out.write(text)
def mdtable(rows,keys):return '|'+ '|'.join(keys)+'|\n|'+'|'.join(['---']*len(keys))+'|\n'+'\n'.join('|'+ '|'.join(str(x[k]) for k in keys)+'|' for x in rows)+'\n'
def main():
 start=time.perf_counter();result=json.loads((F/'run_result.json').read_text());ver=json.loads((F/'independent_verification.json').read_text());assert result['PASS'] and ver['PASS'];source=json.loads((F/'source_manifest.json').read_text());status=json.loads((F/'cpu_job/status.json').read_text());assert status['qualification']=='PASS' and status['returncode']==0
 tests=[]
 for n in ['cross_year_causal_v1_tests.log','cross_year_causal_v1_v10_correction_tests.log','cross_year_causal_v1_operator_tests.log','cross_year_causal_v1_hourly_tests.log','cross_year_causal_v1_native_tests.log']:
  s=(ROOT/'logs'/n).read_text();m=re.search(r'Ran (\d+) tests in ([\d.]+)s',s);assert s.strip().endswith('OK');tests.append(dict(log=n,N=int(m[1]),wall_s=float(m[2])))
 measured=status['elapsed_s']+json.loads((F/'preflight.json').read_text())['wall_s']+ver['wall_s']+sum(x['wall_s'] for x in tests);size=sum(p.stat().st_size for p in F.rglob('*') if p.is_file());assert measured<600 and size<150*2**20 and status['peak_sampled_tree_rss_bytes']<4*2**30
 resources=dict(measured_core_CPU_task_wall_sum_s=measured,wall_definition='preflight + supervised matching/fitting/evaluation/7plots + independent validation +5 test suites; small interactive metadata/report/write commands not individually metered; not conversation elapsed time',supervisor_elapsed_s=status['elapsed_s'],supervisor_returncode=0,peak_sampled_tree_RSS_MiB=status['peak_sampled_tree_rss_bytes']/2**20,worker_peak_rusage_MiB=result['peak_RSS_MiB'],RSS_definition='same UID child session sampled; not continuous global peak',directory_bytes_before_reports=size,tests=tests,new_observation_bytes=0,GPU=0,TIE=0,DART=0,orbit=0,limits={'wall_s':600,'RSS_GiB':4,'output_MiB':150})
 write(F/'resource_audit.json',json.dumps(resources,indent=2)+'\n')
 params=json.loads((F/'correction_parameters.json').read_text());rows=list(csv.DictReader((F/'metrics.csv').open()));gains=list(csv.DictReader((F/'improvements.csv').open()));regions=list(csv.DictReader((F/'region_metrics.csv').open()));points=list(csv.DictReader((F/'pointwise_diagnostics.csv').open()));hist=list(csv.DictReader((F/'historical_residual_comparison.csv').open()))
 ctable=[dict(case=c,role=d['role'],b_2021=f"{d['b_2021']:.9f}",multiplier=f"{d['multiplier_2021']:.9f}",N=d['N']) for c,d in params['adaptive'].items()]
 primary=[]
 for window in ['future_1h','future_3h','future_6h']:
  for method in ['Raw','Transfer','Adaptive']:
   x=next(x for x in rows if x['case']=='B14' and x['window']==window and x['method']==method);g=next((g for g in gains if g['case']=='B14' and g['window']==window and g['region']=='all' and g['method']==method),None)
   primary.append(dict(window=window,method=method,N=x['n'],RMSE_e13=f"{float(x['RMSE'])*1e13:.6f}",RMSE_gain_pct='—' if g is None else f"{float(g['RMSE_improvement_pct']):.4f}",relative_RMS_pct=f"{float(x['relative_RMS'])*100:.4f}",relative_RMS_gain_pct='—' if g is None else f"{float(g['relative_RMS_improvement_pct']):.4f}"))
 controls=[]
 for c in ['A7','B7','A14']:
  x=next(x for x in gains if x['case']==c and x['window']=='future_6h' and x['region']=='all' and x['method']=='Adaptive');controls.append(dict(case=c,role=source['cases'][c]['role'],RMSE_gain_pct=f"{float(x['RMSE_improvement_pct']):.4f}",relative_RMS_gain_pct=f"{float(x['relative_RMS_improvement_pct']):.4f}"))
 regional=[]
 for reg in ['low','mid','high','height_430_440km','height_440_450km','height_450_460km','height_460_470km']:
  rr={x['method']:x for x in regions if x['case']=='B14' and x['window']=='future_6h' and x['region']==reg};regional.append(dict(region=reg,N=rr['Raw']['n'],raw_relative_RMS_pct=f"{float(rr['Raw']['relative_RMS'])*100:.4f}",transfer_relative_RMS_pct=f"{float(rr['Transfer']['relative_RMS'])*100:.4f}",adaptive_relative_RMS_pct=f"{float(rr['Adaptive']['relative_RMS'])*100:.4f}"))
 nonoverlap=[]
 for win in ['future_1h','incremental_1_3h','incremental_3_6h']:
  for method in ['Transfer','Adaptive']:
   x=next(x for x in gains if x['case']=='B14' and x['window']==win and x['region']=='all' and x['method']==method);nonoverlap.append(dict(window=win,method=method,N=x['N'],RMSE_gain_pct=f"{float(x['RMSE_improvement_pct']):.4f}",relative_RMS_gain_pct=f"{float(x['relative_RMS_improvement_pct']):.4f}"))
 report='''# 跨年份因果密度校正验证 v1

2026-11-16。`CROSS_YEAR_CAUSAL_DENSITY_VALIDATION=COMPLETE`指冻结方案执行及审计完成，**不是科学泛化PASS**。实验身份`CROSS_YEAR_METHOD_REPLICATION / PROVISIONAL Map-A / HINDCAST`。数据以前用于原始密度对照，并非全新盲测。

## 1. 目标、输入和工程身份

使用既有2021-03-24 Swarm A DNSAPOD0301（2880条、30秒、flag0），只读复用。CDF SHA与v9原始记录一致，字段UTC/密度kg/m³/角度deg/高度m由原读取器检查。输入清单`experiments/swarm_tiegcm_2021_spinup_observation_v1/inputs.json`中8卷NetCDF SHA与实际文件、各组历史data_audit逐项一致，不能用另造清单替代。四组DEN及ZG均为ilev29；DEN g/cm³×1000，ZG cm×.01；原生有效小时数据10帧03—12。

2021 A7/B7/A14/B14的真实运行退出码均为0、4个NORMAL EXIT，工程审计均PASS。2021 A14仍按研究角色仅敏感性；**不是2022 A14的历史PARTIAL**。2022 A14 PARTIAL保持，不跨年份套用工程身份。2021 O1/O2/N2科学门禁失败以及完整大气状态未通过不变。工程PASS、DEN可查询、多变量科学资格分别记录。

B14主背景按事前来源/工程身份选定，A7/B7对照，A14敏感性；不根据本轮未来RMSE排序。原始CDF/NetCDF、v10代码/报告/系数保持，未下载观测、未运行物理积分、DART、GPU或轨道。启动前本地/远端HEAD均c469f9c...，未重复推送；历史未跟踪同步日志保留。

## 2. 冻结时间、方法与因果隔离

2021-03-24 06:00 UTC截止，历史严格[03,06)360点；未来[06,07)120、[06,09)360、[06,12)720点。另列不重叠[06,07)、[07,09)、[09,12)。这些窗口在模型查询/估计前已冻结。

- Raw：原始Map-A背景，b=0。
- Transfer：**仅B14**，原样使用v10的b2022=0.1261252775057784、exp(b)=1.1344242772252575，不用2021历史拟合。
- Adaptive：各背景只对自己的过去A观测估计median(ln(obs)-ln(model))，未来统一乘exp(b2021)。不混合背景，不使用C/B，不搜索核、趋势、学习率或高度偏移。

系数文件在未来误差计算前写入并链接frozen_protocol SHA。未来A密度毒化20个数量级，各背景系数逐位不变。新模块显式接收日期，复用v10标量应用/质量/误差函数；旧v10硬编码日期入口保持只读，单元测试确认2022调用等价。Transfer只允许B14且拒绝其他背景或修改系数。

## 3. 观测算子及数值检查

复用GRS80地理位置→ITRS→DensityQuery WGS84→显式Map-A→hourly provider。每列log密度垂直、水平密度双线性、时间密度线性插值不变，8邻列即使零权重也必须有效。4320次查询（四背景各1080）全部有效，各自与共同域覆盖100%，无补零/裁边/外推/备用密度。逐点时空权重/垂直层/源文件/质量/拒绝原因存本地query_trace_local.jsonl。

本次用到的原始DEN/ZG帧显式_FillValue/missing_value、非有限、极大哨兵及DEN非正检查均为0；12个真实八列加权重建在1e-13相对容差内通过。独立CDF直读1080条UTC/密度/标志/坐标与匹配数组精确一致。独立54个全窗指标行重算MAE/RMSE/Bias/relativeRMS/P95/logRMS通过1e-13相对容差，未放宽旧门槛。48个CPU测试通过，原始数据与旧产物SHA保持。

## 4. 真实2021历史系数

'''+mdtable(ctable,list(ctable[0]))+'''
B14 2021历史log残差mean=0.048994247、median=0.093990767、P05=-0.383838061、P95=0.364801430、std=0.240566806。2022 mean=0.122461744、median=0.126125278、P05=-0.110067201、P95=0.334887601、std=0.147903160。2021分布明显更宽，均值与中位数也不同。高度相关2021+0.062992/2022-0.328126、纬度相关2021-0.093108/2022+0.312349；均为描述相关，不是高度或太阳活动因果证明。

完整逐背景两年均值/中位数/乘数/P05/P95及相关见historical_residual_comparison.csv。2022只读复用v10真实残差与参数，未重新拟合或运行2022查询。

## 5. B14未来结果：绝对与相对误差结论分歧

RMSE单位10^-13 kg/m³；改善率正=改善，负=恶化。所有方法使用同一ID集合。

'''+mdtable(primary,list(primary[0]))+'''
**按绝对RMSE，Transfer和Adaptive都改善；按relative RMS，二者三个累计窗口均恶化。** 因而用户给出的四种解释情形必须按指标区分：RMSE符合“情况1”，relative RMS符合“情况4”。不能挑RMSE宣布整体泛化成功，也不能说2022系数完全没有迁移作用。

Transfer的RMSE在三个窗口均低于Adaptive，但Adaptive的relative RMS均优于Transfer。没有跨全部指标的单一赢家。2021自适应使用较小乘数，减轻了迁移尺度的部分过校正，却未恢复到Raw的整体relative RMS水平。

六小时Raw/Adaptive/Transfer的relative P95为41.0294%/54.9278%/59.9872%；log RMS为0.248409/0.224725/0.225218。可见log RMS与绝对RMSE改善，同时相对尾部和relative RMS恶化。Pearson三者均0.953325，因为恒定正乘数不改变相关性。

这不是指标实现错误：RMSE²=mean[rho_obs²×relative_error²]，relativeRMS²=mean[relative_error²]。绝对密度幅值大的点在前者中权重更大；某些相对误差的放大可被绝对RMSE改善掩盖。中位log偏差是log残差L1意义的尺度估计，不保证最小化物理RMSE或relative RMS。**本轮未根据此结果更换估计器。**

## 6. 背景敏感性、逐点和区域诊断

六小时Adaptive：

'''+mdtable(controls,list(controls[0]))+'''
不同背景上复现了RMSE改善、relative RMS恶化的方向。A14不进入主背景结论。B14未来720点，Adaptive470改善/250恶化、Transfer455改善/265恶化，无不变点，没有删除不利点。多数点改善也不保证平方相对误差降低。

B14六小时区域relative RMS（%）：

'''+mdtable(regional,list(regional[0]))+'''
2021低纬raw平均有符号相对Bias仅+0.4502%，Adaptive后+10.3495%、Transfer后+13.9532%，低纬过校正明显重复且更严重；2022低纬A由-9.3877%到+2.7928%。同时中高纬relative RMS改善。430—440km组恶化、其他高度组改善，但高度和纬度沿轨相互关联，不能把组间差异直接归因于高度。所有预注册区域N及N/A保留在region_metrics.csv，未事后重划区域。

不重叠时间窗：

'''+mdtable(nonoverlap,list(nonoverlap[0]))+'''
相对收益在1—3h恶化、3—6h改善，不呈单调时间衰减。累计窗口相互重叠，30秒点相关；未做IID显著性检验，也不将720个样本称720次独立实验。

## 7. 两年联合解释、限制与高度

2022 B14自适应A的六小时relative RMS19.1526→14.6187%，与本轮2021的24.0041→25.0208%方向不同。绝对RMSE收益在两日复现，但“绝对和相对同时改善”没有跨年份稳定复现。仅两个日期，不能宣布年度泛化或单一太阳/地磁活动因果；太阳地磁驱动、轨道高度、物理场和观测处理条件不同。

本轮有限重读[NCAR官方grid/altitude页](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/grid.html)仍标April2016，未发现新增ZG零面与GRS80/WGS84严格等价定义；仓库没有新维护者回复，不发送邮件。继续引用reports/HEIGHT_DATUM_OFFICIAL_EVIDENCE_UPDATE_V1.md，不重复历史搜索或编造误差界。正式接口EXTERNAL_DATUM_UNVERIFIED；Map-A不因为某个指标更小而升级。b可能混合模型、坐标及POD反演尺度偏差。未来真实GPI为HINDCAST，未验证实时驱动不确定性。

## 8. 资源、复现与准入

'''+f"预检/受监督匹配-拟合-评价-7图/独立核验/5测试套件已计量墙钟合计{measured:.3f}秒；监督任务{status['elapsed_s']:.3f}秒，峰值采样进程树{status['peak_sampled_tree_rss_bytes']/2**20:.3f}MiB。目录在报告前{size/2**20:.3f}MiB。轻量交互文件检查未逐项计时，不冒称整个对话自然墙钟。无失败重试，600秒/4GiB/150MiB预算未扩大。\n"+'''
入口source scripts/activate_orbit.sh；具体命令见commands.json。已有运行目录、参数及输出以独占创建保护，不能盲目在原tag重跑。CPU监督器真实wait返回0、清理通过，完整资源/输入输出/code SHA保存。只公开派生残差/指标/图表，原始CDF/NetCDF、完整匹配和逐点查询数组本地。

CROSS_YEAR_CAUSAL_DENSITY_VALIDATION=COMPLETE只代表实验执行完成；总体稳定收益证据不足。SCIENCE_TRAINING_READY=False、DART未准入、Restart一致性FAIL、真实轨道BLOCKED、外部高度未验证及两年各自A14工程状态保持。不根据本轮结果调整系数、扩展模型、增加截点或运行同化。
'''
 write(ROOT/'reports/CROSS_YEAR_CAUSAL_DENSITY_VALIDATION_V1.md',report)
 decision='''# 跨年份因果校正：下一阶段决策 v1

2026-11-16。本轮完成执行，不宣布泛化PASS，不启动下一轮。

## 核心判断

1. 2022固定系数在2021 B14上能降低绝对RMSE，但relative RMS和相对尾部恶化，不能直接作为长期通用系数。
2. 2021过去3小时自适应也降低RMSE，却仍提高三个累计窗口的relative RMS。相比Transfer，它减轻相对误差，但绝对RMSE更高，不是全指标优胜。
3. 2021/2022均观察到低纬过校正；2021低纬relative RMS恶化更强，说明全局常数的代表性限制值得优先检查。高度、纬度、时间相关，不能据此直接拟合高度偏移。

## 下一轮优先建议（仅方案）

优先保留当前常数方法作为可解释基线，冻结更多未拟合截点/日期的评价协议，并先明确绝对RMSE、relative RMS、log RMS和尾部误差的联合科学目标；不能为当前好看而删指标或修改旧判据。候选为现有覆盖中固定的其他截点/日期，与本轮06Z和已查看未来窗口分开登记，严格过去3h/未来1/3/6h，同一半开规则，输出同样区域表和失败覆盖。2021/2022都已经开发查看，不称盲测；Swarm B继续保留，不纳入任何选型。

同时做无需新拟合的低/中/高纬、高度、绝对/相对误差分解，区分全局尺度和沿轨代表性。若未来另立局地或时间衰减对照，必须单因素、先冻结、不得本轮事后追加。现有结果不足以直接跳到DART，也不能因绝对RMSE改善就替代物理高度依据。

下一轮候选CPU≤600秒、RSS≤4GiB、输出≤150MiB；按本轮4320查询/7图监督约14秒外推仅供资源估算，更多截点重叠查询可只读复用，但不得把估算当实测。无需GPU/TIE积分/轨道；数据不足时另申请观测，不自动下载。

## 保持关闭的门禁

- Restart连续/分段一致性仍FAIL，未修复/重试。
- 外部高度EXTERNAL_DATUM_UNVERIFIED；咨询草稿未发送，无维护者新回复。
- DART状态更新/含He观测算子/观测误差/合法集合/版本实测和独立验证未齐备。
- 真实气动/姿态/推力/完整受力与POD-SP3关联未闭合，真实轨道验证BLOCKED。
- 科学训练False；2021 A14工程PASS仅敏感性，2022 A14历史PARTIAL保持。
'''
 write(ROOT/'docs/CROSS_YEAR_CAUSAL_DENSITY_NEXT_DECISION_V1.md',decision)
 commands=dict(environment='source scripts/activate_orbit.sh; PYTHONPATH=$PWD/src:$PWD (and scripts for preparation); CPU-only subprocess configuration',commands=['python -m unittest discover -s tests -p test_cross_year_correction.py -v','python scripts/prepare_cross_year_causal_v1.py','python scripts/launch_cross_year_causal_v1.py','python -m unittest discover -s tests -p test_causal_density_correction.py -v','python -m unittest discover -s tests -p test_causal_density_operator.py -v','python -m unittest discover -s tests -p test_hourly_tiegcm_observation.py -v','python -m unittest discover -s tests -p test_tiegcm_density_provider.py -v','python scripts/verify_cross_year_causal_v1.py','python scripts/finalize_cross_year_causal_v1.py'],warning='One immutable run-tag. Existing folders and coefficient files refuse replay; future rerun requires new version.',network='No new observations; one official height documentation version check, no new official definition or reply')
 write(F/'commands.json',json.dumps(commands,indent=2)+'\n')
 write(F/'completion_audit.json',json.dumps(dict(state='COMPLETE',identity='CROSS_YEAR_METHOD_REPLICATION, not blind',stable_all_metric_benefit=False,engineering_workflow_PASS=True,tests=sum(x['N'] for x in tests),queries=4320,query_coverage=1.,independent_metric_rows=54,full_science_PASS=False,formal_datum='EXTERNAL_DATUM_UNVERIFIED',DART='NOT_ADMITTED',restart='FAIL',real_orbit='BLOCKED',A14_2021='engineering PASS/sensitivity role',A14_2022='engineering PARTIAL'),indent=2)+'\n')
 p=ROOT/'STATUS.md';s=p.read_text();entry='> 最新（2026-11-16，跨年份因果密度校正v11）：CROSS_YEAR_CAUSAL_DENSITY_VALIDATION=COMPLETE（执行完成，非全指标泛化PASS）。复用2021 A0301及inputs.json8卷SHA，4320次Map-A查询全有效；48CPU测试、1080CDF直接匹配、12插值重建、54指标行独立复核通过。B14历史360点b2021=0.0939907670，乘数1.0985496030；Transfer固定b2022=0.1261252775。2021未来1/3/6h Adaptive RMSE改善27.6119/20.4714/20.4004%，Transfer34.7921/24.9096/25.9526%；但relative RMS三个累计窗口两法均恶化，6h Raw24.0041%、Adaptive25.0208%、Transfer26.2255%。低纬过校正重复，Adaptive470改善/250恶化，Transfer455/265。2021 A14工程PASS但仅敏感性，不能套用2022 A14 PARTIAL；O1/O2/N2科学FAIL保留。无新下载/拟合高度/新TIE/GPU/DART/轨道，v10及旧产物保持。绝对收益复现、相对收益跨年不稳定；优先固定更多截点的联合误差评价，不直接部署DART。报告reports/CROSS_YEAR_CAUSAL_DENSITY_VALIDATION_V1.md；科学训练False/高度未验证/RestartFAIL/真实轨道BLOCKED保持。\n\n';p.write_text(s.replace('# 当前状态\n\n','# 当前状态\n\n'+entry,1))
 p=ROOT/'WORKLOG.md';p.write_text(p.read_text()+f'''\n\n## 2026-11-16：跨年份严格因果密度校正v11\n- 授权范围：仅CPU复用2021 A与TIE四组，固定2022 B14系数Transfer、2021过去3h Adaptive，不增加模型复杂度，无新观测下载/TIE/GPU/DART/轨道。起始本地远端均c469f9c...，未重复推送，保护历史未跟踪同步日志。\n- 预注册：B14主、A7/B7对照、A14敏感性；2021[03,06)360与未来[06,07)/[06,09)/[06,12)120/360/720及不重叠时间窗。仅B14 Transfer，精确b2022 .1261252775057784。所有Adaptive只各自过去A残差中位数，参数先冻结再未来评价；未来毒化不变，B/C未读。\n- 输入：2021CDF SHA/UTC/单位/flag0共2880检查；inputs.json的8原NetCDF卷SHA与历史审计匹配，DEN/ZG ilev29及g/cm3×1000/cm×.01不改。四组真实退出0和4NORMAL EXIT、工程PASS；2021 A14仍仅敏感性，与2022历史PARTIAL分别保留。全状态O1/O2/N2科学失败不解除。\n- 复用：原hourly/provider、Map-A、v10标量应用、quality/metric_row/strata；新日期显式evaluation.cross_year_correction模块不改变旧2022入口。4320真实查询全有效、10小时帧；8列/层/权重完整本地记录，所有填值/非有限/非正扫描通过。48CPU测试通过，1080CDF数据独立精确匹配、12插值探针、54指标行物理公式独立复算通过。\n- 结果：B14 b2021 .09399076703699727、乘数1.0985496030025081。1/3/6h Adaptive绝对RMSE下降27.6119/20.4714/20.4004%，Transfer34.7921/24.9096/25.9526%；但相对RMS全部累计窗口恶化。6h Raw/Adaptive/Transfer relativeRMS24.0041/25.0208/26.2255%，relativeP9541.0294/54.9278/59.9872%，logRMS .248409/.224725/.225218，Pearson缩放不变。A7/B7/A14亦RMSE改善而相对RMS恶化。\n- 结构：2021低纬有符号relativeBias .4502→10.3495% Adaptive/13.9532% Transfer，过校正重复；低纬及430—440km相对RMS变差，中高纬改善。6h Adaptive470改善250恶化，Transfer455改善265恶化。7—9h相对误差恶化、9—12h改善，不拟合衰减或作IID显著性；不把两年差异归因单一太阳活动。\n- 实测：监督任务正常exit0/PASS {status['elapsed_s']:.3f}秒，核心任务含预检/核验/测试墙钟合计{measured:.3f}秒（零散文件检查不逐项计时，不冒称自然墙钟），峰值采样树RSS{status['peak_sampled_tree_rss_bytes']/2**20:.3f}MiB，报告前目录{size/2**20:.3f}MiB。无失败重试，600秒/4GiB/150MiB未扩大。7图已生成，图5视觉检查通过。\n- 高度：仅复核官方grid页仍April2016，无新零面定义/维护者回复，不重复历史搜索，不发邮件；引用v10高度报告。EXTERNAL_DATUM_UNVERIFIED、RestartFAIL、DART未准入、真实轨道BLOCKED和科学训练False保持。\n- 交付：reports/CROSS_YEAR_CAUSAL_DENSITY_VALIDATION_V1.md、docs/CROSS_YEAR_CAUSAL_DENSITY_NEXT_DECISION_V1.md及新run协议/输入/系数/区域/点级/资源/命令/SHA/7图。结论绝对RMSE部分跨年收益复现，但全指标稳定收益未成立；下一轮仅建议联合评价目标和预注册新截点/日期，不自动运行。原始观测、完整匹配和逐点查询只本地；Git最终SHA及同步结果以实际核验记录为准。\n''')
 print('CROSS YEAR REPORT AND STATE COMPLETE',flush=True)
if __name__=='__main__':main()
