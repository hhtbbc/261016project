"""Summarize the retained single pass, never rerun fitting or scoring."""
from pathlib import Path
import sys,json,csv,time
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R),str(R/'src'),str(R/'scripts')]
from run_density_validation_v18 import F,OLD,PRE,V17,sha,load,rows,dump,table,epoch
from plot_density_validation_v18 import plot

def main():
 started=time.perf_counter();assert not load(F/'independent_verification.json')['PASS'];plot()
 protect=load(F/'source_manifest.json')['protected_SHA256'];changed=[n for n,h in protect.items() if sha(R/n)!=h];assert not changed,changed
 assert sha(F/'correction_parameters.json')==load(F/'parameter_freeze_receipt.json')['SHA256']
 dump('asset_protection_after.json',dict(PASS=True,protected_tracked_files=len(protect),old_2021_parameters_and_results_unchanged=True,all35_model_output_SHA_match=all(sha(R/x['path'])==x['SHA256'] for x in load(F/'source_manifest.json')['model_outputs']),original_evaluation_protocol_unchanged=sha(PRE/'frozen_evaluation_protocol.json')==load(F/'frozen_protocol.json')['original_protocol_SHA256']))
 sup=load(F/'supervision_result.json');ind=load(F/'independent_verification.json');j=[x for x in rows(F/'joint_assessment.csv') if x['window'].startswith('future_')];m=rows(F/'metrics.csv');reg=rows(F/'region_metrics.csv');params=load(F/'correction_parameters.json')['parameters'];oldparams=load(OLD/'correction_parameters.json')['parameters']['B14'];oldj=[x for x in rows(OLD/'joint_assessment.csv') if x['case']=='B14' and x['window'].startswith('future_')];oldm=rows(OLD/'metrics.csv');flags=['RMSE_BENEFIT','RELATIVE_RMS_BENEFIT','TAIL_NONWORSENED','LOW_LATITUDE_BIAS_NONWORSENED']
 result=dict(status='INCONCLUSIVE',formal_scientific_scoring_attempts=1,scoring_tables_generated=True,independent_verification='FAIL_NUMERICAL_TOLERANCE',scientific_conclusion_upgrade=False,main_table_joint_pass=sum(x['JOINT_NO_REGRET']=='PASS' for x in j),main_table_joint_total=len(j),main_table_flags_pass=sum(x[k]=='True' for x in j for k in flags),main_table_flags_total=4*len(j),future_poison='PASS',parameter_SHA_unchanged=True,original_assets_unchanged=True,queries=2880,new_model_runs=0,new_downloads=0,GPU=0,DART=0,orbit=0,automatic_scoring_retries=0,scientific_gates_unchanged=True)
 dump('result.json',result)
 # No complete old scientific result is changed; V16 and V17 states remain historical facts.
 def metric(rr,h,w,met,region='all'):
  return next(x for x in rr if x['case']=='B14' and int(x['cutoff'])==h and x['window']==w and x['method']==met and x['region']==region)
 def fmt(x,scale=1,dec=4):return f'{float(x)*scale:.{dec}f}' if x not in ['',None] else 'N/A'
 def mdtable(header,rr):return '| '+' | '.join(header)+' |\n| '+' | '.join(['---']*len(header))+' |\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rr)+'\n'
 report='''# V18：2022-03-25真实密度误差评价（独立复核未闭合）

**V18=INCONCLUSIVE。唯一一次正式CPU评分已经产生完整指标；独立验证未通过冻结容差，不能标记本轮科学验证PASS。未重跑评分、未修改参数或门槛。**

研究身份：HINDCAST / PROVISIONAL Map-A / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED。以下数值是已保留的单次主评价输出，尚待独立复核闭环；不将它们包装成获得独立验证的新方法。V17 ENGINEERING_PASS及V16原ENGINEERING_FAIL历史记录保持。

## 1. 数据与执行顺序

起始本地和远端HEAD均为7dd203e6981c87a9c012d189f1bca27656df66f8。使用run_id=094fcac3949c4e2e981d3baac1a5d8bf的新17天冷启动B14，非旧探索性B14。35个模型输出SHA核验一致，目标日原生secondary016/017覆盖00—次日00，共25帧。DEN/ZG保持ilev、g/cm3×1000及cm×0.01，原Map-A和八列规则不改。Swarm A DNSAPOD0301原CDF SHA=d2f647f723f774a446e6c07c9b1108c1dc521b76bb21a2d524d321d379b440a8。

准入只读元数据及SHA，不读未来密度。独立history进程仅切片读取03—06和15—18的瞬时density，各360条，查询对应模型后独占冻结correction_parameters.json。之后另一个score进程才读未来观测；06/18各自复制原始数据进行1e20毒化，历史参数字典逐项完全不变。原协议no_evaluation_or_fitting_this_task是准备任务范围，本轮授权覆盖其范围限制，但原文件及科学参数不变。

在任何校正应用前，先存Raw指标及raw_scoring_receipt；然后计算冻结校正结果。完整观测ID、UTC、位置、flag及逐点匹配只在本地common_sample_ids_local.csv/matched_local.npz，公共coverage.csv保存共同ID的SHA。全日2880/2880 flag0、密度正且有限、质量有效，2880/2880原Map-A查询成功，23040列全检查；不因误差大小剔除点。全天曲线只作描述，不冒充正式截点评价。

历史分段与全天读取的时间原点不同，可有末位插值舍入。启动前解析时间测试已记录implementation_addendum：按原rtol=1e-13,atol=0核对重读值，实际拟合/毒化保留历史阶段原值。未修改小时读取器或插值规则。参数冻结前后的SHA完全一致。

## 2. 历史参数冻结

'''
 co=[]
 for year,pp in [(2021,oldparams),(2022,params)]:
  for label,key in [('06Z global','GlobalAdaptive06'),('18Z global','GlobalAdaptive18')]:
   c=pp[key];co.append([year,label,c['N'],f"{c['b']:.15f}",f"{c['multiplier']:.15f}"])
  for k,c in pp['LatitudeAdaptive18'].items():co.append([year,'18Z '+k,c['N'],f"{c['b']:.15f}",f"{c['multiplier']:.15f}"])
 report+=mdtable(['年份','区域/截点','历史N','b','exp(b)'],co)
 report+='Stale06精确引用各自同日06Z系数，2022乘数0.9812354725102888，绝不使用3月23/24日参数。18Z三纬区历史N为124/117/119，均≥30；没有fallback。2021表只读既有冻结参数，未重新拟合。\n\n## 3. 原始物理密度误差\n\n'
 raw=[]
 for h in [6,18]:
  for lead in [1,3,6]:
   x=metric(m,h,f'future_{lead}h','Raw');raw.append([f'{h:02d}Z',lead,x['n'],fmt(x['RMSE'],1e13),fmt(x['relative_RMS'],100),fmt(x['bias'],1e13),fmt(x['relative_P95'],100)])
 report+=mdtable(['截点','累计h','N','RMSE (10^-13 kg/m³)','Relative RMS %','Bias (10^-13 kg/m³)','relative P95 %'],raw)
 report+='模型相对POD产品的条件性误差，不是绝对真值精度，也不证明ZG外部零面。所有正式1/3/6小时覆盖120/360/720点、质量和共同域覆盖率100%。\n\n## 4. 所有固定方法未来结果\n\n'
 future=[]
 for h in [6,18]:
  for method in (['Raw','GlobalAdaptive06'] if h==6 else ['Raw','GlobalAdaptive18','LatitudeAdaptive18','Stale06']):
   for lead in [1,3,6]:
    x=metric(m,h,f'future_{lead}h',method);future.append([f'{h:02d}Z',method,lead,fmt(x['RMSE'],1e13),fmt(x['relative_RMS'],100),fmt(x['relative_P95'],100)])
 report+=mdtable(['截点','方法','累计h','RMSE (10^-13 kg/m³)','Relative RMS %','P95 %'],future)
 report+='Raw/校正的MAE、Bias、logRMS、Pearson、最大绝对误差及完整指标见metrics.csv；非重叠块见time_block_metrics.csv，区域见region_metrics.csv，改善/恶化/不变点数见pointwise_diagnostics.csv，均保留不利结果。\n\n'
 jr=[]
 for x in j:jr.append([x['cutoff'],x['method'],x['window'],fmt(x['RMSE_gain_pct'],dec=2),fmt(x['relative_RMS_gain_pct'],dec=2),''.join('1' if x[k]=='True' else '0' for k in flags),x['JOINT_NO_REGRET']])
 report+='### 主评价四项联合判据（尚未独立闭环）\n\n'+mdtable(['截点','方法','窗口','RMSE改善%','相对RMS改善%','四标志顺序','联合'],jr)
 report+='四标志顺序为RMSE/相对RMS/P95/低纬绝对Bias，1满足、0失败。主表联合0/12，单项19/48满足；未将0/12解释成所有方法在每个指标均无收益。06Z校正三个累计窗口绝对RMSE均恶化，而1/3h相对RMS降低；18Z Global/Latitude三个窗口绝对RMSE均降低、相对RMS和P95均恶化。Stale06绝对RMSE三个窗口均恶化。累计窗口高度相关，禁止作12次独立试验或普通IID检验。\n\n### 纬区结构：未来6h\n\n'
 rr=[]
 for x in reg:
  if x['window']=='future_6h':rr.append([x['cutoff'],x['method'],x['region'],x['n'],fmt(x['RMSE'],1e13),fmt(x['relative_RMS'],100),fmt(x['relative_bias'],100)])
 report+=mdtable(['截点','方法','纬区','N','RMSE (10^-13 kg/m³)','Relative RMS %','Relative Bias %'],rr)
 report+='18Z低纬Raw relativeBias=-2.8435%，Global后+9.6495%、Latitude后+10.7801%；低纬过校正仍存在。高纬Raw已高估+5.0753%，两个18Z增幅方法推至+18.5865%/+17.8209%，并使高纬绝对RMSE恶化。纬度历史中位数并不足以保证未来各区相对误差无退化。\n\n## 5. 历史代表性与评价目标\n\n'
 gap=[]
 for x in rows(F/'history_future_residual_gap.csv'):
  if x['region']=='all' and x['window'].startswith('future_'):gap.append([x['cutoff'],x['window'],fmt(x['b_H'],dec=6),fmt(x['b_F_DIAGNOSTIC_ONLY'],dec=6),fmt(x['delta_b'],dec=6)])
 report+=mdtable(['截点','未来窗口','历史b_H','未来b_F（仅事后诊断）','b_F-b_H'],gap)
 report+='06Z到6小时未来中位数由负转正，历史代表性有限；18Z首小时中位数接近历史，但相对误差仍恶化，说明代表性不是唯一因素。RMSE²=mean(obs²×relativeError²)，相对RMS²=mean(relativeError²)，中位log残差估计器与这两个目标均不等价。高密度区域绝对误差改善可能掩盖相对误差损失；本轮不另拟合或用未来中位数生成预测。不能仅凭沿轨统计把模型空间误差、轨道采样、POD反演偏差及高度基准分别归为已验证因果来源。\n\n## 6. 2021年冻结B14只读对照\n\n'
 yr=[]
 for year,rrr in [(2021,oldm),(2022,m)]:
  for h in [6,18]:
   for method in (['Raw','GlobalAdaptive06'] if h==6 else ['Raw','GlobalAdaptive18','LatitudeAdaptive18','Stale06']):
    x=metric(rrr,h,'future_6h',method);yr.append([year,h,method,fmt(x['RMSE'],1e13),fmt(x['relative_RMS'],100),fmt(x['bias'],1e13)])
 report+=mdtable(['年份','截点','方法','6h RMSE (10^-13 kg/m³)','6h Relative RMS %','6h Bias (10^-13 kg/m³)'],yr)
 report+='''2021冻结B14联合1/12（仅18Z纬度首小时），2022单次主表0/12且尚待独立复核。2021/2022早晨b分别+0.189895/−0.018943，方向相反；晚间+0.116278/+0.120965相近，仍不能保证相同联合收益。两年18Z 6h纬度校正均表现为绝对RMSE降低而相对RMS升高。未证明稳定跨日期收益。两背景分别连续积分，均03-09冷启，06/18截点实际暖态历时16.25/16.75天；B14是候选背景身份，不是多变量充分收敛认证。同为3月有限相邻日期，不支持全年、全球或跨季节泛化。\n\n## 7. 测试与独立复核故障\n\n33项既有CPU回归全部通过：纬度14、晚间11、小时算子8。数据准入、历史与未来隔离、两个独立毒化输入、参数SHA、35卷SHA和旧结果保护均通过。独立程序直接读取CDF、25帧原生数据、2880点独立八列重构，所有先行断言通过；五个系数及exp(b)在冻结门槛内。

独立数值循环在18Z LatitudeAdaptive18的**历史analysis Bias**停止：主5.453772204284436e-16，复算5.453772204285187e-16 kg/m³，绝对差7.51e-29，约1.377e-13相对差，超过rtol1e-13/atol0。没有把它隐瞒为未来指标失败，也没有因为差小而绕过门槛。

独立复算使用math.exp，中纬乘数1.1435382339160527；冻结科学实现numpy.exp及冻结乘数为1.1435382339160525，相差1ULP。极小、近抵消的Bias对这次末位差敏感。只对该失败历史行作诊断，按原冻结乘数计算得到主值逐位一致；这不是重新评分或将独立FAIL改为PASS。主评分及参数均未更改，未再执行verify/score入口。独立循环尚未完成所有后续指标和联合判定，因此**整体INCONCLUSIVE**，不能宣布独立复核通过。

完整失败stdout、原始告警和查询轨迹本地保留；50条全天已知NetCDF告警按V17来源SHA通道记录，不修改原始属性或屏蔽真实数值问题。图表由已生成的一次性结果绘制，均注明独立复核未闭合；首次字体不含上标负号的草图移至本地，最终使用ASCII幂次单位，不重算科学结果。

## 8. 资源、版本与后续

'''
 report+=f"唯一正式评价监督耗时{sup['elapsed_s']:.6f}秒，采样树峰RSS{sup['peak_sampled_tree_rss_bytes']/2**20:.3f}MiB，直接wait返回1，qualification=FAIL，原因为复核断言；无超时/资源超限/采样缺口，清理完成。不是模型积分失败。后续仅失败诊断、图表和文件整理，不重复评分。来源、时间、共同样本哈希和代码SHA见source_manifest/frozen_protocol/parameter_freeze_receipt/sha256_manifest；最终资源汇总见resource_audit.json。\n\n"
 report+='下一轮建议只读闭合独立复核：使用已冻结乘数作独立指标算术，exp实现差异单独以冻结门槛验证；不重新拟合、不修改科学指标、不同意放宽容差或重选窗口。当前不自动执行该复核。闭合后再讨论增加真正独立季节/活动条件的观测与合法物理场，优先评价固定方法的适用边界，不直接加参数。ZG物理登记仍需正式证据；数学/工程有效率不能替代它。DART/Restart/真实气动与轨道门禁未闭合。\n\n继续保持SCIENCE_TRAINING_READY=False、EXTERNAL_DATUM_UNVERIFIED、Restart=FAIL、DART=NOT_ADMITTED、REAL_ORBIT=BLOCKED。未启动TIE-GCM/GPU/DART/AI/轨道、未下载数据或外部联系。本轮整理后停止。\n\n## 图表及解释\n\n'
 for c in rows(F/'figure_captions.csv'):report+=f"### {c['Chinese_title']}\n\n![{c['Chinese_title']}](../experiments/tiegcm_2022_mar25_density_validation_v18/{c['file']})\n\n{c['definition_and_interpretation']}\n\n"
 report+='''## 领导汇报（300字以内）\n\n已用工程验收通过的2022年3月25日物理场与2880条Swarm A实测完成一次固定协议评价，历史参数冻结和防泄漏测试通过。晚间全局、纬度校正虽降低绝对RMSE，却扩大相对误差及尾部误差，主表联合无退化0/12，不支持稳定跨日期收益。独立复核在近零历史Bias因指数函数1ULP差异超出冻结容差，已停止且未放宽门槛，整体暂为INCONCLUSIVE。建议下一轮只读闭合复核，再扩展独立日期；不启动同化、AI或轨道。
'''
 rp=R/'reports/TIEGCM_2022_MAR25_DENSITY_VALIDATION_V18.md'
 with rp.open('x') as f:f.write(report)
 decision='''# V18下一阶段决策

当前V18=INCONCLUSIVE，原因是独立算术复核未闭合，不是工程模型重算需求。唯一评分输出与参数全部保留，未来poison通过；不得重跑模型或重拟合以获得PASS。

下一轮如获授权，仅对现有冻结参数和原始数据进行只读复核。固定乘数的独立指标算术与exp(b)的函数库末位差检查应分开，保持rtol1e-13/atol0，不以近零指标放宽门槛。必须核验所有窗口、共同ID和联合判定；这不是允许修改既有失败记录。完成前不得升格科学结论。

主表18Z绝对RMSE改善、相对RMS和P95恶化，联合0/12；2021冻结1/12，不支持稳定普适收益。若闭环，下一项优先为独立季节/活动条件的固定方法适用性验证，需要独立数据和合法物理背景另授权，不自动增加校正参数。

外部ZG基准未验证、POD产品非独立真值、RestartFAIL、DART未准入、真实轨道BLOCKED和科学训练False保持。无新增模型/下载/训练/轨道授权。
'''
 with (R/'docs/TIEGCM_V18_NEXT_DECISION.md').open('x') as f:f.write(decision)
 state=f'''\n\n## 2026-11-19 V18：新2022 Mar25密度评价，独立复核未闭合\n\nTIEGCM_2022_MAR25_DENSITY_VALIDATION_V18=INCONCLUSIVE。唯一一次CPU科学评分已生成，未重试；35模型输出与原CDF/旧参数/原协议SHA不变，2880/2880真实八列查询，历史两窗口各360点，参数先冻结、两个截点独立1e20毒化通过。06Z b=-0.01894281508017137，18Z b=0.12096546690878363，局地低/中/高b=0.13122399131903073/0.13412716979060235/0.11448842140590543。18Z6h Raw/Global/Latitude RMSE=2.247752/1.637721/1.608624×10^-13kg/m³，相对RMS=19.1088/25.1090/25.4166%，主表联合0/12、单项19/48满足；2021冻结联合1/12只读对照，不宣称稳定收益。\n\n33CPU回归通过。独立CDF/25帧/2880点八列复算先行断言通过，但18Z局地历史analysis近零Bias因math.exp与numpy.exp中纬乘数1ULP差使相对差约1.377e-13，超过冻结rtol1e-13/atol0；独立循环中止，联合未独立闭环，不改FAIL为PASS。监督11.810303秒、采样峰346.887MiB、退出1，无模型重启/科学重评分/新参数/容差放宽。故整体INCONCLUSIVE而非完成科学PASS。图表仅整理已存结果并标明复核待闭合；原V17ENGINEERING_PASS与V16历史FAIL不变。\n\n报告reports/TIEGCM_2022_MAR25_DENSITY_VALIDATION_V18.md；决策docs/TIEGCM_V18_NEXT_DECISION.md；独立证据experiments/tiegcm_2022_mar25_density_validation_v18/。下一轮只读闭合算术复核需另授权；SCIENCE_TRAINING_READY=False/EXTERNAL_DATUM_UNVERIFIED/RestartFAIL/DARTNOT_ADMITTED/REAL_ORBITBLOCKED全部保持。本轮整理后停止，未TIE/GPU/AI/DART/轨道/下载或外部联系。\n'''
 for n in ['STATUS.md','WORKLOG.md']:
  with (R/n).open('a') as f:f.write(state)
 dump('presentation_addendum.json',dict(after_scoring_failure_only=True,scientific_scoring_not_repeated=True,plot_change='ASCII unit exponents replace unsupported font superscripts; added pending independent verification to every figure',original_plotter_snapshot_kept_local=True,final_plotter_SHA256=sha(R/'scripts/plot_density_validation_v18.py'),finalizer_SHA256=sha(Path(__file__))))
 dump('postprocessing_receipt.json',dict(wall_s=time.perf_counter()-started,no_fitting=True,no_scoring=True,no_verifier_rerun=True))
 print('V18 RETAINED OUTPUTS DOCUMENTED; STATUS INCONCLUSIVE',flush=True)
if __name__=='__main__':main()
