"""Document existing V19 verification receipts; no numerical evaluation entry."""
from pathlib import Path
import sys,json,csv,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from evaluation.density_verification import sha,write_json
F=R/'experiments/tiegcm_2022_mar25_independent_verification_v19';V18=R/'experiments/tiegcm_2022_mar25_density_validation_v18'
def load(p):return json.loads(Path(p).read_text())
def rr(p):return list(csv.DictReader(Path(p).open()))
def mt(h,rows):return '| '+' | '.join(h)+' |\n| '+' | '.join(['---']*len(h))+' |\n'+''.join('| '+' | '.join(map(str,row))+' |\n' for row in rows)+'\n'
def main():
 s=load(F/'result_closed.json');assert s['status']=='VERIFICATION_CLOSED_PASS' and s['field_failures']==0
 first=load(F/'supervision_result.json');last=load(F/'continuation_supervision.json');assert last['qualification']=='PASS' and last['returncode']==0
 diag=load(F/'float_roundoff_diagnosis_closed.json');asset=load(F/'asset_protection_after.json');detail=rr(F/'numeric_verification_detail.csv');coeff=rr(F/'coefficient_and_exp_diagnostics.csv');pert=rr(F/'prediction_exp_perturbation.csv')
 write_json(F,'verification_status.json',dict(status='VERIFICATION_CLOSED_PASS',PASS=True,authoritative_result='result_closed.json',initial_worker_result='result.json retained INCONCLUSIVE TypeError serialization interruption',original_V18_status='INCONCLUSIVE retained',first_worker_returncode=first['returncode'],checkpoint_tables_returncode=last['returncode'],V18_scientific_scores_still_one=True,scientific_joint_benefit_PASS=False))
 size=sum(p.stat().st_size for p in F.rglob('*') if p.is_file());assert size<150*2**20
 write_json(F,'resource_audit.json',dict(supervised_wall_s=first['elapsed_s']+last['elapsed_s'],initial_native_and_contract_worker_wall_s=first['elapsed_s'],initial_worker_returncode=1,initial_worker_error='lossless JSON representation of numpy.bool_; occurred before metrics loop',never_reached_tables_checkpoint_wall_s=last['elapsed_s'],checkpoint_returncode=0,sampled_peak_tree_RSS_bytes=max(first['peak_sampled_tree_rss_bytes'],last['peak_sampled_tree_rss_bytes']),CPU_user_s=first['children_cpu_user_s']+last['children_cpu_user_s'],CPU_system_s=first['children_cpu_system_s']+last['children_cpu_system_s'],regression_tests=22,test_wall_s=.121,supervision_sampling_gaps=len(first['gaps'])+len(last['gaps']),all_cleanup_verified=first['cleanup_verified'] and last['cleanup_verified'],full_entry_retries=0,complete_metric_table_verifications=1,new_scientific_scoring=0,new_fitting=0,new_model_runs=0,old_directories_written=0,all_output_bytes_before_documentation=size,wall_limit_s=600,RSS_limit_bytes=4*2**30,public_limit_bytes=150*2**20,GPU=0,download_bytes=0,DART=0,orbit=0,sampled_resources_not_OS_isolation=True))
 write_json(F,'tests_closed.json',dict(PASS=True,total_tests=22,initial_contract_tests=19,serialization_and_checkpoint_tests=3,test_logs=[dict(path=n,SHA256=sha(R/n)) for n in ['logs/v19_verification_tests.log','logs/v19_serialization_tests.log']],tests_executed_before_complete_metrics_access=True,zero_atol_no_exception=True))
 lines=[
 '# V19：2022-03-25真实密度评价的独立数值复核闭环',
 '**V19=VERIFICATION_CLOSED_PASS。V18原历史INCONCLUSIVE及其全部旧结果保持不变。数值复核PASS不等于校正方法科学收益PASS；独立确认2022累计联合0/12，2021冻结对照1/12。**',
 '## 1. 今日完成情况',
 '起始本地与远端main均为0c93ddcea2bef867a639a3045b5e7937d0d5fa2c。本轮只读验证既有V18评分。没有调用V18的prepare/history/score/launch入口，没有新增正式评分、参数文件、物理积分、下载、AI/DART或轨道传播。',
 'V18公开SHA清单各项与Git提交字节验证通过；冻结参数SHA为743cbf099c417a4b74a530151c08c6c5a8c746cfc0ee5ae30a3ca54075521470，与receipt一致。原协议、指标表、共同域、原失败诊断、2021结果及V17 ENGINEERING_PASS均未修改。35个原始模型NetCDF和原CDF哈希一致，前后4160个受保护文件不变。',
 '证据边界：V18公开manifest没有保存matched_local.npz和完整ID文件的历史SHA，本轮不追认不存在的旧证明。V19在使用前冻结当前SHA，并通过原CDF精确值、冻结历史sample_SHA、已有窗口ID哈希及原生NetCDF查询交叉确认内容身份。NPZ与完整ID文件本轮前后SHA分别为4621d2fb62339a2a0f6c0d220cc31fcf6aa763eabb802701bc455cff3c85e94d、9c66535b17c1fb13e80b8b0e331f2a3ca34691f323348121a6301ec1c45a1657。',
 '## 2. 关键技术解释：C1与C2分离',
 'C1仅核查冻结历史样本和b的来源，以排序中位数独立检查五个既有b；这属于诊断纯函数，不生成、修改或选择参数。03—06与15—18各360点，晚间low/mid/high历史N=124/117/119。五个冻结sample_SHA与当前原始输入完全一致，NumPy指数值与保存乘数逐位相同。',
 '源码检查表明：原正式评分通过LogMedianCorrection.multiplier再次调用numpy.exp(b)，并非直接使用文件multiplier字段。五个结果恰好逐位等于冻结乘数，因此C2以该乘数为数值合同可以精确复现正式算法；没有把不同math.exp值悄悄替换为新参数。',
 mt(['18Z中纬项','实际值'],[['冻结b','0.13412716979060235'],['math.exp(b)','1.1435382339160527'],['numpy.exp(b)及冻结乘数','1.1435382339160525'],['差异','1 ULP = 2.220446049250313e-16']]),
 '在全天965个中纬样本中，替代math.exp使950点乘积改变，最大密度差4.0389678347315804e-28 kg/m³，最大相对预测差3.5547306224654163e-16；低、高纬未改变。一个因子ULP不意味着所有乘积都改变恰好一个ULP。',
 mt(['原失败历史analysis Bias','值 kg/m³','与主值绝对差','冻结比较'],[['V18主值','5.453772204284436e-16','0','—'],['原math.exp替代复算','5.453772204285187e-16','7.513900122230137e-29','FAIL'],['C2冻结乘数复算','5.453772204284436e-16','0','PASS']]),
 'Bias是有符号误差的均值，正负项接近抵消；乘数末位差使近零均值的相对差超过1e-13。这里abs(main-independent)/abs(independent)=1.3777436681946943e-13，原诊断abs(main/independent-1)=1.376676550535194e-13还有一次浮点抵消；这只是诊断相对差写法的末位差，两者都不改变原isclose拒绝结论。',
 '严格沿用np.isclose(main,independent,rtol=1e-13,atol=0)，绝不四舍五入Bias。独立值为0时只接受主值也为0；极小量容差按浮点乘积计算，不另设floor或豁免。真正超限、NaN/Inf、缺字段、SHA和ID变更均拒绝。该现象理论上也可能影响其他近抵消指标；本轮没有以替代指数实现生成一轮新评分，冻结合同下所有既有指标均通过完整复核。',
 '## 3. 实际独立复核结果',
 '原始Swarm A CDF直接读取2880条UTC30秒瞬时密度，质量规则与坐标条件不变。所有原始时间、密度、位置、flag和quality与缓存逐位一致，完整ID索引及Raw对应值一致。独立读取目标25帧原生DEN/ZG，检查维度、单位、填值、有限正值和单调性。以GRS80→同一ITRS位置→WGS84重建显式Map-A，再独立八列插值2880点，包含零权重列、无外推。相对原查询最大相对差4.440892098500626e-16，低于原1e-13门槛。',
 'C2只用经原始模型检查的原Raw查询值及冻结乘数重建；没有使用主实验校正数组作为输入。6组共17280个预测值与主保存数组逐位一致，最大绝对/相对差均0。原查询数值合同与原生模型独立重构的微小舍入差分开检查，未将新的浮点查询结果覆盖原Raw。',
 mt(['复核对象','完整行数/数量','结果'],[['总体指标metrics.csv',42,'PASS'],['纬区指标region_metrics.csv',126,'PASS'],['非重叠块time_block_metrics.csv',18,'PASS'],['点级改善/恶化/不变计数',112,'PASS'],['共同域coverage.csv',42,'PASS'],['既有联合判定',20,'全部一致'],['其中正式累计窗口',12,'联合0/12'],['非重叠联合样本等价核验',12,'全部一致'],['2021/2022引用对照行',336,'PASS'],['2021原联合判据只读算术',12,'联合1/12'],['逐字段检查',9051,'失败0，其中数值检查5053项']]),
 '所有9项主要指标（MAE、RMSE、Bias、Relative RMS、Relative P95、Relative Bias、logRMS、Pearson、最大绝对误差）与N、有效性状态、覆盖率、均值及附加Bias比值均核对。完整主值、独立值、绝对差、相对差、允许绝对误差和PASS写入numeric_verification_detail.csv。该表的最大数值相对差1.941733108167607e-16出现在指数函数诊断，未触及原容差；每项科学指标均保持原定义。',
 '时间窗均左闭右开：历史360，累计未来1/3/6h为120/360/720，不重叠0—1/1—3/3—6h为120/240/360。所有方法窗口ID哈希一致；low/mid/high实际计数由window_sample_identity及原区域表逐一核验，低于30不允许OK/PASS。Stale06只用同日冻结06Z因子。',
 'future poison检查是两份独立原数据副本的历史输入不变性证明：06Z未来乘1e20不进入03—06，18Z未来乘1e20不进入15—18。五组历史样本保持逐位相同，并对应原毒化记录的参数SHA；不再运行正式拟合或生成参数。',
 '## 4. 联合与跨年份科学解释',
 '独立复算12个累计组合全部四标志及所有既有8个非重叠后续块判定。0—1h与future_1h使用完全相同ID，按原行核查，不人为扩充独立重复次数。',
 mt(['截点','方法','1h','3h','6h'],[['06Z','GlobalAdaptive06','FAIL','FAIL','FAIL'],['18Z','GlobalAdaptive18','FAIL','FAIL','FAIL'],['18Z','LatitudeAdaptive18','FAIL','FAIL','FAIL'],['18Z','Stale06','FAIL','FAIL','FAIL']]),
 '2022共19/48个单项条件满足，但联合0/12；这不是所有指标在每个窗口都无改善。2021冻结B14只有18Z LatitudeAdaptive18的1h联合PASS，总1/12，未混入A7/B7或其他日期。336行跨年引用逐字段核对，2021参数与源表SHA未变，未重新计算2021预测、重拟合或重新选择对照。',
 '2022晚间6h Raw/Global/Latitude RMSE分别2.2477515806666198/1.637720833981118/1.608623675977434×10^-13kg/m³，而Relative RMS分别19.10877858858094/25.10898367220366/25.41662610546821%。数值现已独立复核，这些结果仍不支持联合无退化收益。2021也曾出现绝对/相对指标方向相反；有限相邻日期不证明全年或跨季节稳定性。',
 '## 5. 遇到的问题、测试及资源',
 '首先19项合成正反例通过，正式读取完整指标表前完成。覆盖冻结因子复用、1ULP、近零Bias、超容差拒绝、ID/SHA/指标篡改、缺字段/非有限值、错误联合判断、历史写入拒绝和独占输出保护。',
 '首个只读工作进程在保存C1/C2诊断时因numpy.bool_不可JSON序列化退出1，耗时6.246602秒；此时原始CDF/模型与C1/C2已完成，但完整表格循环尚未执行。保留原预约、result.json=INCONCLUSIVE及不完整float_roundoff_diagnosis.json，不清理、不覆盖、不重新调用原完整入口。',
 '增加3项无损标量JSON转换、非有限拒绝和已完成检查点拒绝测试，共22项通过。追加continuation_protocol.json，将NumPy标量用item()无损转换为Python标量；原始浮点值、算法和容差不改。未执行过的指标阶段代码从冻结工具逐字接续，SHA可查；仅该阶段启动一次，耗时10.389655秒、退出0。闭环结果单独保存result_closed.json，初次中断证据不改写。没有把中断伪装成首个进程成功，也没有重复整套科学评分或完整复核。',
 f"两段监督合计{first['elapsed_s']+last['elapsed_s']:.6f}秒，采样进程树峰{max(first['peak_sampled_tree_rss_bytes'],last['peak_sampled_tree_rss_bytes'])/2**20:.3f}MiB，用户/系统CPU合计{first['children_cpu_user_s']+last['children_cpu_user_s']:.6f}/{first['children_cpu_system_s']+last['children_cpu_system_s']:.6f}秒，采样缺口0、清理均验证。预算600秒/4GiB/150MiB内；采样不是OS严格隔离或连续峰值保证。新增正式评分/拟合/模型/下载/GPU/DART/轨道均0。",
 '## 6. 当前状态与下一步',
 'V19独立数值复核闭环PASS；V18历史状态保持INCONCLUSIVE，原评分数值现在由新V19证据完整确认。旧图标题“独立复核未闭合”是当时历史记录，不修改；查本V19报告了解后续闭环。数值一致性不改变联合0/12的科学结论，不解除高度、观测独立性、Restart或轨道门禁。',
 '继续保持SCIENCE_TRAINING_READY=False、EXTERNAL_DATUM_UNVERIFIED、Restart=FAIL、DART=NOT_ADMITTED、REAL_ORBIT=BLOCKED。模型密度相对POD反演产品的条件性验证，不是完全独立真值或严格盲测。',
 '建议下一轮优先做独立日期/太阳地磁条件覆盖的只读可行性审查与预注册，再决定是否授权新增数据或合法物理场。保持固定方法，先检验适用边界，不立即增加校正参数。ZG外部物理零面和观测误差模型继续单列，DART与真实轨道仍不具备准入。本轮停止，不自动模拟或扩展。',
 '主要证据：asset_protection_before/after.json、coefficient_and_exp_diagnostics.csv、prediction_reconstruction.csv、numeric_verification_detail.csv、window_sample_identity.csv、future_poison_audit.json、joint_verification.csv、cross_year_reference_verification.csv、result_closed.json、verification_status.json。完整逐点数据和日志只留本地。',
 '### 领导汇报（300字以内）',
 '已完成2022年3月25日既有评分的完整独立数值复核，9051项检查零失败，原失败Bias使用冻结乘数后逐位一致，未放宽容差或重新评分。两种指数函数1ULP差异已确认。2022联合无退化仍为0/12，2021冻结结果1/12，说明数值正确不等于校正稳定有效。建议保持方法，先审查真正独立日期及活动条件覆盖，外部高度、Restart、DART和真实轨道门禁继续保留。'
 ]
 with (R/'reports/TIEGCM_2022_MAR25_INDEPENDENT_VERIFICATION_V19.md').open('x') as f:f.write('\n\n'.join(lines)+'\n')
 decision='''# V19闭环后的下一步决策

V19=VERIFICATION_CLOSED_PASS。V18原历史INCONCLUSIVE及所有结果不改。新证据完整复核原单次评分；不是新一轮科学评价。

独立确认2022 B14联合0/12、单项19/48，2021冻结B14联合1/12。继续研究固定方法适用范围的价值在于确定何时失效，不是已有普适收益。

下一任务建议仅做独立日期与太阳/地磁条件覆盖审查和预注册，按数据/模型可用性选日期，不按密度误差择优。实际下载、新物理场或算法研究另需授权。不要因数值闭环直接开始优化参数、DART、AI或轨道。

科学训练False、外部ZG基准未验证、RestartFAIL、DART未准入、真实轨道BLOCKED保持。先补独立日期与观测误差/物理高度依据，不用更复杂算法掩盖基础限制。
'''
 with (R/'docs/TIEGCM_V19_NEXT_DECISION.md').open('x') as f:f.write(decision)
 state=f'''\n\n## 2026-11-19 V19：V18既有评分独立数值复核闭环\n\nTIEGCM_2022_MAR25_INDEPENDENT_VERIFICATION_V19=VERIFICATION_CLOSED_PASS。V18原INCONCLUSIVE与旧失败文件不改；新增正式评分/拟合/积分均0。保护4160文件及35NetCDF/CDF/SHA不变。5个历史b及exp诊断通过，冻结乘数重建6组17280点与正式数组逐位一致；168指标行、18非重叠块、112点级计数、42覆盖、20既有联合、336跨年引用全面复核，9051字段检查失败0。future poison历史输入不变性/同日Stale06/共同ID通过，rtol1e-13 atol0不变。\n\n原math.exp与numpy.exp中纬乘数确差1ULP；原主评分再次调用numpy.exp(b)，结果与冻结multiplier逐位同值。按冻结合同复算原Bias=5.453772204284436e-16 kg/m³，与主值绝对差0。2022联合0/12、单项19/48，2021只读联合1/12独立确认；数值PASS不等于方法科学收益PASS。\n\n22项测试（19合成/3序列化与检查点）通过。原只读worker在表格阶段前因numpy.bool_ JSON序列化中断，原result.json与预约/日志保留；仅无损序列化补充后接续从未执行的冻结表格代码，不重跑原完整入口，闭环独立写result_closed.json。监督两段6.246602+10.389655=16.636257秒，峰采样112.750MiB，退出1/0如实保留。原V18本地NPZ/完整ID缺少旧公开哈希的证据边界明确记录，并以原件/历史样本SHA/窗口ID/原生模型交叉核实当前身份，未伪造追溯证明。\n\n报告reports/TIEGCM_2022_MAR25_INDEPENDENT_VERIFICATION_V19.md；决策docs/TIEGCM_V19_NEXT_DECISION.md；证据experiments/tiegcm_2022_mar25_independent_verification_v19/。仅新证据关闭复核；SCIENCE_TRAINING_READY=False/EXTERNAL_DATUM_UNVERIFIED/RestartFAIL/DARTNOT_ADMITTED/REAL_ORBITBLOCKED保持。后续独立日期覆盖审查需新任务，本轮停止，无新模型/下载/AI/轨道/外部联系。\n'''
 for name in ['STATUS.md','WORKLOG.md']:
  with (R/name).open('a') as f:f.write(state)
 print('V19 DOCUMENTED WITHOUT CHANGING PRIOR RESULTS',flush=True)
if __name__=='__main__':main()
