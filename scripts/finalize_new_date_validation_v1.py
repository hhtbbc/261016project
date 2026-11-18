"""Publish already frozen V14-A evidence; never fit or query a model."""
from pathlib import Path
import json,csv,hashlib,datetime
R=Path(__file__).resolve().parents[1];F=R/'experiments/causal_density_new_date_validation_v1'
assert R==Path('/workspace/data/20261016') and F.resolve().is_relative_to(R)
def load(n):return json.loads((F/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,v):(F/n).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
j=list(csv.DictReader((F/'joint_assessment.csv').open()));future=[x for x in j if x['window'].startswith('future_')];main=[x for x in future if x['case']=='B14']
table='|截点|方法|窗口|RMSE改善%|relative RMS改善%|联合评价|\n|---|---|---|---:|---:|---|\n'+''.join(f"|{x['cutoff']}Z|{x['method']}|{x['window']}|{float(x['RMSE_gain_pct']):.4f}|{float(x['relative_RMS_gain_pct']):.4f}|{x['JOINT_NO_REGRET']}|\n" for x in main)
a=load('observation_acquisition_audit.json');res=load('result.json');s=load('logs/worker/status.json');ex=load('expansion_audit.json')
report='''# 新日期因果密度校正复现 V14-A

身份：NEW_DATE_REPLICATION / SAME_CONTINUOUS_TIE_RUN / HINDCAST / PROVISIONAL Map-A / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED。

## 数据、协议与实际执行

2021-03-25 Swarm A DNSAPOD_2 0301仅下载一次，140187 bytes。ZIP CRC、安全解压、HDR校验和CDF合同通过；2880条、严格30秒UTC、00:00—23:59:30、flag=0为2880条，密度正且有限。采用瞬时density（kg/m³）和既有质量规则。下载及每个原始成员SHA见observation_acquisition_audit.json；本地SHA不是发布方独立校验和。

B14、A7、B7均有00时至次日00时25个连续整点帧，实际primary边界存在。DEN/ZG位于ilev，原单位g/cm³、cm，转换乘1000、0.01。目标帧填充值、有限性、正密度、ZG单调性检查通过；6480/6480真实沿轨查询满足八列完整、禁止外推，包括零权重列。18个独立插值探针通过。源码和输入SHA可由source_manifest.json追溯。

先数据准入，再冻结协议，再历史估计全部参数并冻结SHA，再future poison test，最后评分。两个截点及全部窗口按原方案执行；18Z Stale06在每个背景单独使用当天该背景03—06时系数，不跨背景借用。每区历史N：低124、中124、高112，均满足30门槛。未来样本N=120/360/720，共同样本身份一致。未添加新算法、未改纬区或阈值。

## B14真实未来结果

正改善率表示误差下降；负值表示恶化。

'''+table+'''
B14联合评价1/12；Latitude18为1/3，只有首小时PASS。控制组A7为2/12，B7为1/12；全部背景合计4/36，仅作描述，不是36次独立实验。三个背景Latitude18首小时均PASS，3/6小时均FAIL。完整绝对指标、尾部、Bias、Pearson、log RMS及点级改善数见metrics.csv、region_metrics.csv和pointwise_diagnostics.csv。非重叠时块见time_block_metrics.csv，不能把累计窗口当独立重复。

B14系数：Global06 b=0.18989491524790836（乘数1.2091225306395847）；Global18 b=0.11627769769983942（1.1233077688083657）；低/中/高纬b=0.20197732181886607、0.1382123402349773、0.08228617552619255（乘数1.2238202537792597、1.1482193375542802、1.085766485168805）。完整三背景参数、历史身份和协议SHA见correction_parameters.json。

## 代表性及局部误差解释

06Z历史b=0.189895，未来1/3/6小时中位数=-0.011120/0.077441/0.000571，存在符号翻转或明显漂移。18Z历史b=0.116278，未来为0.128702/0.047106/0.064851，短时较接近但3/6小时漂移。未来中位数仅用于事后诊断，不参与预测。

18Z六小时低纬Raw relative Bias=-9.3378%，Global=+1.8416%，Latitude=+10.9543%；低纬relative RMS由23.1810%升至28.1820%。中高纬Latitude relative Bias也由-8.5987%/-1.5963%变为+4.9487%/+6.8434%。低纬未来残差中位数0.225127甚至高于历史0.201977，仍出现相对均值过校正，说明历史中位数偏高并非唯一机制：残差分布、估计目标与相对平方误差目标的差异仍需区分。不能从沿轨诊断分离坐标、物理结构及产品偏差的独立因果贡献。

相比3月23/24日，新日期再现“部分绝对RMSE改善而相对RMS恶化”，但增加首小时有限联合收益。3月24日未运行Latitude，图中保留N/A，不补造对照。日期相邻且同一连续运行，B14在本日06/18Z实际已积分16.25/16.75天，A7/B7为9.25/9.75天；背景标签不意味着此刻恰好14/7天。不能视为跨季节、独立模型实现或全年泛化证据。

## 独立验证与资源

37项既有测试通过（纬区14、晚间11、下载12）；独立复核15个系数、504指标行、84联合评价行（含分析和非重叠时块），rtol=1e-13、atol=0。future poison、样本隔离、原始SHA及2979个受保护旧文件SHA不变检查通过。独立验证不重新进行因果实验。

监督进程38.466秒；worker CPU23.902秒，峰值RSS331.223MiB，采样进程树峰值328.859MiB。独立核验已计入worker成本，不重复相加。实际日志及资源见resource_audit.json；新增积分/GPU/DART/轨道均0。

## 2022缺口及科学状态

2022 B14现有真实输出截至03-25 00时。完整新日缺少01时至次日00时24帧，两个注册查询跨度直接需要其中20帧，次日primary也缺失。Restart一致性FAIL，禁止未经验证续算。跨季节方案及资源依据见docs/THERMOSPHERE_MULTIDATE_DATA_EXPANSION_PLAN_V1.md，均未执行。

NEW_DATE_VALIDATION=COMPLETE只表示工程执行完成；SCIENCE_TRAINING_READY=False，EXTERNAL_DATUM_UNVERIFIED，Restart=FAIL，DART=NOT_ADMITTED，REAL_ORBIT=BLOCKED。O1/O2/N2等历史多变量门禁不变，A14不参与。Map-A有效覆盖率不是外部高度登记证明。
'''
(R/'reports/CAUSAL_DENSITY_NEW_DATE_VALIDATION_V1.md').write_text(report)
plan='''# 多日期数据扩展计划 V1（未执行）

## 已有覆盖和低成本方案A

实际扫描23组、292个NetCDF文件，详见existing_model_inventory.csv。该全库扫描仅是元数据覆盖审计，不是所有场的重新工程验收。严格同B14身份、至少14天候选预热及完整06/18Z条件下：2021可用3月23/24/25日，2022可用23/24日；本轮结束后均已参与开发评价，没有更多未评价日期。不得用预热期、A14、2023 S3/S7或作者NPZ冒充同身份新日期。

2022-03-25缺少后24小时；最小合法建议是新目录独立连续Mar09—Mar26共17天24480步，而非对旧文件append或未经验证Restart。现有GPI实际Mar07—Mar27；保持旧±2天原始驱动支持策略时，准备Mar07—Mar28共22天、176个Kp桶，中心81日Fobs支持Jan26—May07共102天。应重新审计已有原始数据缺口与驱动边界，不声称现有GPI已证明不能运行，也不在本轮生成驱动。需要一份未来授权的2022-03-25 Swarm A原始产品；本轮未下载。

## 跨季节方案B

预注册候选2021/2022：春03-23（已有开发基准）、夏06-21、秋09-23、冬12-21；这是日历季节覆盖日期，不声称精确天文节气日，也未查看候选密度来择日。活动类别尚未赋值，需要官方Fobs、Kp审计；这些日期本身不保证磁暴覆盖。六个非春季候选未取得/未读取。

每个新季节背景从目标日前14天00时冷启动，运行至目标日后2天00时，共16天23040步，正式注册目标日06/18Z。采用合法官方同网格smax完整34状态源和真实SOURCE_START，不伪造时间；季节适应性及14天预热充分性必须独立审查，不能预先声称科学PASS。每次预计17份primary、384份secondary。新驱动按运行前后各2日支持：21天、168个Kp桶，中心Fobs101天。精确起止日期在seasonal_expansion_candidates.csv。

春季CSV的16天窗口是统一候选模板；2021现有实际B14是17天至Mar26，2022是16天至Mar25。只读子集可用于相同评价，不把实际2021运行改写成16天，也不声称缩短运行与旧轨迹逐位相同。

## 资源估算与依据

历史MPI4/OMP1：2021 B14 24480步2553.4046秒、NetCDF3581251512bytes；2022 B14 23040步2429.7879秒、3371589248bytes。证据路径、SHA、实际步数和公式在expansion_audit.json，按秒/步、bytes/天估算，硬件负载、I/O、季节适应均带来不确定性，区间不是统计置信界。

2022春季17天：约42.56—43.03分钟，1.5倍规划64.54分钟，NetCDF约3.34GiB。建议另获一次运行授权，硬预算4800秒、RSS16GiB、输出5GiB、至少20GiB剩余磁盘，MPI4/OMP1，失败不重试。

六个新季节16天：各40.05—40.50分钟，1.5倍规划各60.74分钟；顺序合计约4.05小时，规划6.07小时；NetCDF约18.84GiB。加2022春季补齐共约22.18GiB，建议任务磁盘至少50GiB以保留20GiB空闲与日志余量。GPU0；不含额外smin配对、Restart修复或多季节预热充分性实验，也不含批量卫星产品。上述全部需要额外用户授权，不满足本轮600秒预算。

## 执行优先级

方案A原纯观测扩展成本低但同B14合格日期基本耗尽；补2022 Mar25可提供最接近的跨年份复现，需一次独立新物理运行。方案B科学价值更高（分布覆盖），成本和初态适应风险更高。建议先审定2022补齐，再分阶段批准夏季两年份配对，最后视预热/驱动门禁决定完整六次。保持算法和评价不变；目标参数化修改应另立单因素实验，不能与日期扩展同时发生。Restart=FAIL、外部高度和观测独立性仍是正式同化/轨道门禁。本轮所有候选均未执行。
'''
(R/'docs/THERMOSPHERE_MULTIDATE_DATA_EXPANSION_PLAN_V1.md').write_text(plan)
(R/'docs/CAUSAL_DENSITY_NEW_DATE_NEXT_DECISION_V1.md').write_text('''# 新日期下一阶段决策

本轮仅扩展日期。18Z Latitude首小时在B14/A7/B7均通过联合标准，3/6小时均失败；06Z首小时绝对RMSE反而恶化。因此不得推广为稳定局地校正收益。

优先保持现有算法，申请一次2022新日期模型完整覆盖及对应观测扩展，以分离年份/日期差异；继而分阶段跨季节数据，禁止依据未来密度择日。当前无更多未用且符合相同B14成熟窗口的现成日期。可另立评价目标匹配研究，但不与日期扩展同时修改算法。未来中位数仅作诊断，不作为可用预测参数。

所有后续运行、下载须另获授权；本轮停止。EXTERNAL_DATUM_UNVERIFIED、Restart=FAIL、DART=NOT_ADMITTED、REAL_ORBIT=BLOCKED、SCIENCE_TRAINING_READY=False保持。
''')
for name in ['STATUS.md','WORKLOG.md']:
 p=R/name;p.write_text(p.read_text()+'''\n\n## 2026-11-18 V14-A 新日期复现及扩展计划\n
NEW_DATE_VALIDATION=COMPLETE；MULTIDATE_EXPANSION_PLAN=COMPLETE。2021-03-25指定ZIP实际下载140187bytes，2880条质量有效；三背景25帧及6480/6480八列查询通过。37测试及独立复核通过，旧2979文件SHA不变。唯一监督任务38.466秒、CPU23.902秒、峰值331.223MiB。B14联合1/12，仅Latitude18首小时PASS；A7为2/12、B7为1/12，3/6小时局地方法仍FAIL。2022完整新日缺24小时帧，不能未经验证Restart续算。报告reports/CAUSAL_DENSITY_NEW_DATE_VALIDATION_V1.md；计划docs/THERMOSPHERE_MULTIDATE_DATA_EXPANSION_PLAN_V1.md。命令与资源见新实验目录。本轮未启动任何积分/GPU/DART/轨道，不自动进入下一轮；既有科学/高度/Restart门禁不变。\n''')
p=R/'.gitignore';p.write_text(p.read_text()+'\n# New-date full matching arrays and query traces stay local\n/experiments/causal_density_new_date_validation_v1/*_local.*\n/experiments/causal_density_new_date_validation_v1/**/*_local.*\n!/logs/new_date_v1*.log\n')
put('resource_audit.json',dict(supervised_wall_s=s['elapsed_s'],worker=res,sampled_tree_peak_bytes=s['peak_sampled_tree_rss_bytes'],tests_distinct=37,test_wall_s=.127,independent_verification_included=True,public_output_bytes=sum(p.stat().st_size for p in F.rglob('*') if p.is_file() and '_local.' not in p.name),limits=dict(wall_s=600,RSS_GiB=4,download_bytes=1048576,public_MiB=150),PASS=True))
put('commands.json',dict(commands=['source scripts/activate_orbit.sh; python scripts/launch_new_date_validation_v1.py','python -m unittest discover -s tests -p test_causal_density_latitude.py','python -m unittest discover -s tests -p test_late_day_correction.py','python -m unittest discover -s tests -p test_bounded_swarm_acquisition.py','worker internally: python scripts/verify_new_date_validation_v1.py','python scripts/finalize_new_date_validation_v1.py'],test_logs=['logs/new_date_v1_latitude_tests.log','logs/new_date_v1_late_tests.log','logs/new_date_v1_acquisition_tests.log'],supervisor_log='logs/new_date_v1_supervisor.log',new_model_starts=0))
for n,h in load('audit_run_plan.json')['protected_SHA256'].items():assert sha(R/n)==h,n
put('final_state.json',dict(status='COMPLETE',history_2979_SHA_unchanged=True,main_joint_pass=sum(x['JOINT_NO_REGRET']=='PASS' for x in main),main_joint_total=len(main),all_joint_pass=sum(x['JOINT_NO_REGRET']=='PASS' for x in future),all_joint_total=len(future),no_further_work_authorized=True))
paths=[p for p in F.rglob('*') if p.is_file() and '_local.' not in p.name and p.name!='sha256_manifest.json']+[R/n for n in ['scripts/run_new_date_validation_v1.py','scripts/verify_new_date_validation_v1.py','scripts/launch_new_date_validation_v1.py','scripts/finalize_new_date_validation_v1.py','reports/CAUSAL_DENSITY_NEW_DATE_VALIDATION_V1.md','docs/THERMOSPHERE_MULTIDATE_DATA_EXPANSION_PLAN_V1.md','docs/CAUSAL_DENSITY_NEW_DATE_NEXT_DECISION_V1.md']]
put('sha256_manifest.json',{str(p.relative_to(R)):sha(p) for p in paths})
print('Final documentation and manifests complete; no fitting/query/evaluation repeated.')
