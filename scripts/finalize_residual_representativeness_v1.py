"""Package already completed diagnostic outputs; never rerun queries or fit models."""
from pathlib import Path
import json,csv,hashlib,math,datetime,time
import numpy as np
R=Path(__file__).resolve().parents[1];F=R/'experiments/thermosphere_residual_representativeness_v1'
def load(n):return json.loads((F/n).read_text())
def rows(n):return list(csv.DictReader((F/n).open()))
def write(p,text):
 p=Path(p);p.resolve().relative_to(R)
 with p.open('x') as f:f.write(text)
def dump(n,x):write(F/n,json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def md(headers,records):return '| '+' | '.join(headers)+' |\n|'+ '|'.join(['---']*len(headers))+'|\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in records)+'\n'
def main():
 assert not (R/'reports/THERMOSPHERE_RESIDUAL_REPRESENTATIVENESS_V1.md').exists();run=load('run_result.json');verify=load('independent_verification.json');sup=load('logs/worker/status.json');assert run['PASS'] and verify['PASS'] and sup['qualification']=='PASS' and sup['returncode']==0
 g=rows('history_future_median_gap.csv');st=rows('history_future_residual_statistics.csv');co=rows('orbit_coverage_comparison.csv');err=rows('density_error_contribution.csv');metrics=rows('reproduced_frozen_metrics.csv');coords=rows('coordinate_roundtrip_tests.csv');blocks=rows('time_block_residual_statistics.csv');tails=rows('tail_diagnostics.csv')
 # Supplementary independent residual identity check using scalar math.log(o/p).
 a=np.load(F/'matched_diagnostics_local.npz');worst=0.;pairs=0
 for case in load('diagnostic_case_index.json'):
  p=case['prefix'];o=a[p+'_density']
  for name in case['methods']:
   raw=a[p+'_'+name+'_Raw'];e=np.log(o)-np.log(raw);ind=np.array([math.log(float(x)/float(y)) for x,y in zip(o,raw)]);r=np.exp(e-ind);assert np.allclose(r,1.,rtol=1e-13,atol=0);worst=max(worst,float(np.max(abs(r-1))));pairs+=len(o)
 dump('residual_formula_verification.json',dict(PASS=True,paired_rows=pairs,formula='vector ln(obs)-ln(model) versus independent scalar math.log(obs/model); compare exp of difference',max_relative_ratio_difference=worst,rtol=1e-13,atol=0,no_forecast_generated=True))
 mainrows=[]
 for day in ['2021-03-23','2021-03-24','2022-03-23','2022-03-24']:
  for hour in ['6','18']:
   pp=[x for x in g if (x['date'],x['cutoff'],x['case'],x['region'])==(day,hour,'B14','all')];ff={x['window']:x for x in pp};mainrows.append([day,hour,f"{float(pp[0]['b_H']):.6f}",*[f"{float(ff[f'future_{h}h']['b_F']):.6f}" for h in [1,3,6]],*[f"{float(ff[f'future_{h}h']['delta_b']):+.6f}" for h in [1,3,6]]])
 regionrows=[[x['date'],x['cutoff'],x['region'],f"{x['history_N']}/{x['future_N']}",f"{float(x['b_H']):.6f}",f"{float(x['b_F']):.6f}",f"{float(x['delta_b']):+.6f}",f"{float(x['histogram_overlap']):.3f}"] for x in g if x['case']=='B14' and x['region']!='all' and x['window']=='future_6h']
 controlrows=[]
 for case in ['B14','A7','B7']:
  gg=[x for x in g if x['case']==case and x['region']=='all'];rr=[x for x in g if x['case']==case and x['region']!='all'];controlrows.append([case,f"{min(float(x['delta_b']) for x in gg):+.6f} to {max(float(x['delta_b']) for x in gg):+.6f}",f"{sum(x['median_sign_flip']=='True' for x in gg)}/{len(gg)}",f"{min(float(x['delta_b']) for x in rr):+.6f} to {max(float(x['delta_b']) for x in rr):+.6f}",f"{sum(x['median_sign_flip']=='True' for x in rr)}/{len(rr)}"])
 contributionrows=[]
 for day in ['2021-03-23','2021-03-24','2022-03-23','2022-03-24']:
  for cutoff in ['6','18']:
   e=[x for x in err if x['date']==day and x['cutoff']==cutoff and x['case']=='B14' and x['window']=='future_6h' and x['group_type']=='density'];d={(x['method'],x['group']):x for x in e}
   for method in ['GlobalAdaptive','LatitudeAdaptive']:
    if (method,'Q1') not in d:continue
    absolute=[float(d['Raw',f'Q{i}']['absolute_MSE_contribution'])-float(d[method,f'Q{i}']['absolute_MSE_contribution']) for i in range(1,6)];relative=[float(d[method,f'Q{i}']['relative_MSE_contribution'])-float(d['Raw',f'Q{i}']['relative_MSE_contribution']) for i in range(1,6)];mm={x['method']:x for x in metrics if x['date']==day and x['cutoff']==cutoff and x['case']=='B14' and x['window']=='future_6h'}
    contributionrows.append([day,cutoff,method,f"{100*(1-float(mm[method]['RMSE'])/float(mm['Raw']['RMSE'])):+.3f}",f"{100*(1-float(mm[method]['relative_RMS'])/float(mm['Raw']['relative_RMS'])):+.3f}",f"{100*absolute[-1]/sum(absolute):.2f}",f"{100*sum(relative[:2])/sum(relative):.2f}"])
 coverage_rows=[]
 for day in ['2021-03-23','2022-03-23']:
  for win in ['analysis','future_6h']:
   for reg in ['all','low','mid','high']:
    x=next(x for x in co if (x['date'],x['cutoff'],x['case'],x['window'],x['region'])==(day,'18','B14',win,reg));coverage_rows.append([day,win,reg,x['N'],f"{float(x['north_fraction'])*100:.2f}",f"{float(x['height_mean_m'])/1000:.6f}"])
 tailrows=[[x['date'],x['method'],f"{float(x['relative_P95'])*100:.3f}",x['tail_N'],f"{float(x['tail_relative_SS_fraction'])*100:.2f}",f"{float(x['fraction_exceeding_Raw_P95'])*100:.2f}",f"{float(x['tail_low_latitude_fraction'])*100:.2f}",f"{float(x['tail_lowest_two_density_bins_fraction'])*100:.2f}"] for x in tails if x['date'].endswith('23') and x['cutoff']=='18' and x['case']=='B14']
 blockrows=[]
 for day in ['2021-03-23','2021-03-24','2022-03-23','2022-03-24']:
  for hour in ['6','18']:
   ss=[x for x in blocks if x['date']==day and x['cutoff']==hour and x['case']=='B14' and x['region']=='all'];hh=[float(x['median']) for x in ss if int(x['hours_from_cutoff_start'])<0];ff=[float(x['median']) for x in ss if int(x['hours_from_cutoff_start'])>=0];blockrows.append([day,hour,f'{min(hh):+.5f} to {max(hh):+.5f}',f'{min(ff):+.5f} to {max(ff):+.5f}'])
 maxs={k:max(abs(float(x[k])) for x in coords) for k in ['roundtrip_XYZ_error_m','library_forward_XYZ_error_m','latitude_crosscheck_error_deg','height_crosscheck_error_m','Map_A_height_identity_error_m']};sat=[x for x in coords if x['sample_kind']=='satellite' and x['ellipsoid']=='WGS84']
 coordtable=[[k,f'{v:.12g}'] for k,v in maxs.items()]
 report='''# 历史残差代表性与坐标数值一致性诊断 V1

2026-11-18 UTC；tag `thermosphere_residual_representativeness_v1`。

**执行完成，未产生新校正方法、未拟合新参数。** 身份：**PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED**。

## 1. 数据、协议及边界

预先固定2021/2022-03-23与03-24、每天06Z/18Z共8个日期—截点。主B14、控制A7/B7，共24个背景组合；A14排除，未使用Swarm B/C数值。四日各2880条0301 Swarm A原件、flag0/UTC30秒/瞬时density和GRS80坐标合同核实；六背景每组两卷、共12个NetCDF原SHA和ilev DEN/ZG单位核实。具体原始路径和SHA见source_manifest.json，本轮不上传原件。

协议在未来残差分布分析及坐标数值试验之前冻结，SHA `'''+load('protocol_sha256.json')['SHA256']+'''`。历史严格[cutoff−3h,cutoff)，未来累计[cutoff,cutoff+1/3/6h)；每组合历史360点、未来120/360/720点，共同域100%。4日各选定18小时窗口合计8640个不同观测时刻，不把重叠未来窗口计为独立数据。

优先复用v10/v11/v12/v13-B冻结缓存。仅缺03-23早窗B14未来及A7/B7历史/未来，共5760次必要查询按原Map-A算子重建；18个八列重建探针rtol1e-13/atol0通过，所有查询八列有效、无高度外推。其余20160个背景配对值复用旧缓存。所有旧参数和结果、原始CDF/NetCDF及坐标接口逐字不变（203项保护SHA）。

03-23 06Z没有此前冻结的Global/Latitude未来预测，本轮只做Raw残差诊断，不新建这些校正输出。其历史中位数虽作为诊断统计计算，但不用于生成新预测。误差分解只使用此前已存在的Global/Latitude结果；不将其他日期/方法移植到空白格。

## 2. 统计定义与稳健性

残差e=ln(obs)−ln(model)，所有密度有限且>0。统计均值、中位数、总体标准差(ddof0)、未缩放MAD、线性分位P05/P25/P75/P95、正残差比例。区域维持abs(原始GRS80纬度)<30、30≤abs<60、abs≥60，南北合并。

区域分布统计N≥30，否则N/A。N不是独立观测数量。直方图重叠OVL=sum(min(p_H,p_F))，固定边界−inf、−4至4每0.1、+inf，保留溢出；它只作描述、受分箱选择影响，不是总体分布相同概率或显著性。时间块预先固定1小时：历史3块、未来6块，不试其他块长。

384行分布统计、288行历史—未来中位数对照、区域与轨道覆盖、固定小时块全部公开。未来b_F是事后诊断值，**绝不作为可实时使用的系数**。不设事后“代表性PASS”阈值，不以日期数量4推断全年规律，不做IID显著性检验。

## 3. B14历史与未来残差代表性

所有b均无量纲log密度残差；Δ=b_F−b_H。

'''+md(['日期','cutoff UTC','b_H','b_F 1h','b_F 3h','b_F 6h','Δ1h','Δ3h','Δ6h'],mainrows)+'''
历史3小时不能统一代表未来。B14的24个累计未来比较中，Δ范围−0.133064至+0.120258，3个比较出现全域中位数符号翻转；这是重叠描述单元，不是24个独立实验。2021-03-23 06Z首小时由+0.015904变−0.038407，2022-03-23 06Z由+0.077442变−0.054387，说明历史正修正方向未必代表紧随其后的沿轨时段。

但不能把全部失败归因于中位数变化。**2021-03-23 18Z的历史中位数0.088227与未来6小时0.086280很接近（差−0.001947），此前Global的绝对RMSE仍改善20.501%，relative RMS却恶化12.649%。**历史/未来P25由−0.079886变−0.148432、MAD由0.138607变0.160909，分布形状和尾部并未因中位数接近而相同；同时中位数估计目标与平方误差权重本来不同。

2022两个日期18Z未来三个累计中位数均低于历史；06Z长期中位数反而更高。2021则混合，不支持跨年、跨截点统一的方向或单调衰减规律。A7/B7控制同样存在方向变化：

'''+md(['背景','全域Δ范围','全域符号翻转/24','纬区Δ范围','纬区符号翻转/72'],controlrows)+'''
不同背景的数值不完全相同，未据此替换主背景或挑选有利结果。

## 4. 纬度代表性与采样覆盖

B14未来6h，各区全部N≥30。OVL为上述固定分箱的描述性重叠。

'''+md(['日期','cutoff','区域','N历史/未来','历史中位数','未来中位数','Δ','OVL'],regionrows)+'''
2021-03-23 18Z低纬历史0.206033、未来0.072549，差约−0.13348：历史低纬强正残差不足以代表未来低纬，原纬度方法的+24.661%相对Bias与此相容。它是代表性不足的实测证据，不等于已经分离模型物理、卫星产品或高度误差的原因。

2022-03-23 18Z低纬历史0.035459、未来约0.17090，方向相反；高纬历史0.126380、未来约0.009900，差约−0.11648，提示高纬强增幅难以代表未来。低纬方法虽把relativeBias从−1.913%推到+1.627%，其relative RMS仍从23.372%变24.189%，**未来中位数本身不能解释均方误差及均值偏差全部变化**。

关键日期的覆盖摘要（观测椭球高，不代表已解决ZG零面）：

'''+md(['日期','窗口','区域','N','北半球比例%','平均观测高度km'],coverage_rows)+'''
2021该晚窗历史与未来全域平均高度约442.037/442.034km，纬区点数占比和半球比例亦相近，但低纬残差中位数仍明显变动。因此“只要历史纬度点数足够/高度均值相近就可代表未来”不成立。2022高纬平均高度约443.657→444.313km，与残差变化同时出现；**相关采样变化不证明高度导致误差**。时间、经度、地方时、南北轨道相位、模型空间结构及产品反演偏差仍耦合，沿轨数据不能独立识别各因素因果份额。

## 5. 绝对与相对误差矛盾：恒等式与实际贡献

在共同正值样本，r=(pred−obs)/obs：RMSE²=mean(obs²r²)，relativeRMS²=mean(r²)。不裁剪误差或删除难点。v12五分位算法原样复用，分箱只用于事后解释；并列值不人为打散。按密度、纬度、非重叠时间段、密度×纬度输出绝对/相对SS及对总MSE贡献，分母为完整窗口N而非各箱N。

下表引用既有B14冻结6h预测；“Q5绝对净收益占比”为Q5绝对MSE减少/总体减少；“Q1+Q2相对净变化占比”为低两箱相对MSE变化/总体变化，负/超过100%都可能出现，因为有其他箱相反抵消，不是概率。

'''+md(['日期','cutoff','既有方法','RMSE收益%','relativeRMS收益%','Q5绝对净收益占比%','Q1+Q2相对净变化占比%'],contributionrows)+'''
03-23晚窗：2021 Raw绝对SS的60.65%来自Q5，2022为67.48%。2021 Global/Latitude的Q5贡献分别占绝对净收益82.11%/113.79%，2022为100.24%/86.20%。这些窗口的Q1+Q2相对损失超过最终净恶化（2021约197.38%/142.21%，2022约135.22%/131.34%），因为高密度箱改善抵消了部分损失。**低密度相对损失能被绝对误差的高密度平方权重掩盖。**

2021低纬未来248点中124点在最低两密度箱；纬度方法最差5%相对误差点全部属于低纬且全部在Q1/Q2。2022低纬247点中103点在Q1/Q2，但纬度方法最差5%全部在Q1/Q2、无一在低纬，说明低密度风险不能简单等同低纬，跨年份空间位置不同。

'''+md(['日期','方法','relativeP95%','尾部点数','最差5%相对SS占比%','超过RawP95点比例%','尾部低纬比例%','尾部Q1/Q2比例%'],tailrows)+'''
例如2021纬度法有22.5%点超过Raw的P95，2022为12.22%，不是只有单个极端点变大；不能把P95恶化全部解释成一个最大离群点。最差5%点对相对SS的集中贡献仍需明确保留。

统一乘数a作用后r_corrected=a*r_raw+(a−1)。即便它缩小高密度主导的绝对差，也可能把原本接近零或已为正的相对差整体向正方向放大。log中位数优化的是对数残差的位置统计，不保证最小化绝对MSE、relative MSE或P95。这里未计算未来最优乘数、未拟合任何新参数。

## 6. 时间块与旧评价不变性

固定1h块的B14全域中位数范围：

'''+md(['日期','cutoff','历史三个小时块中位数范围','未来六个小时块中位数范围'],blockrows)+'''
累计1/3/6h结果会混合不同沿轨相位，不能把累计6h中位数接近历史解释为每小时稳定；不重叠小时统计已单列time_block_residual_statistics.csv。没有尝试不同块长挑结论，没有普通IID检验或虚构有效独立样本数。

144行配对误差独立复算；其中126行与v10—v13已有逐项记录一致，另外18行只是缺失早窗的Raw诊断，不是新校正预报。旧v12/v13中54行四旗标独立核验不变；本轮不创造新的联合评价PASS，也不为新日期—截点补造历史不存在的Latitude/Global结果。

## 7. 坐标数值一致性：已知与未知

在执行前冻结：GRS80 a=6378137m、逆扁率298.257222101；WGS84 a=6378137m、逆扁率298.257223563；float64。独立显式椭球正算/20步迭代反算与Astropy/ERFA交叉比较。198个固定解析点覆盖赤道/中高纬/正负极点/±180及±540经度/0、450、800km高度；另取每日期固定25个真实位置，共100点。两椭球共596行数值检查，原始XYZ保留本地，不上传完整位置数组。

预冻结数值容差：XYZ和高度1e-5m、角度5e-10°；来自float64地球尺度与数值保护因子，**不是实际坐标/大气模型精度界**。极点经度无定义时标N/A，以XYZ及高度检查，不拿经度奇异性制造失败。

'''+md(['数值项目','实际最大值'],coordtable)+'''
独立ERFA高度交叉检查最大约2.969e−9m。全部数值检查通过，未调整容差。

固定100个卫星位置，同一XYZ上WGS84−GRS80高度差为−0.000104568m至约−3.73e−9m（最大约0.104568mm），纬度差约±8.81e−10°；原GRS80大地纬度−地心纬度约−0.179743°至+0.180224°。两椭球表达差异很小不意味着大地/地心纬度可混用；本轮不把地心纬度作为新Map方案。

Map-A送入模型的纬度/高度与现有DensityQuery的WGS84结果一致，实际高度身份差0，ITRS原向量保留。经度周期、单位与极区边界数值自洽。**它不能证明模型地理纬度等于外部大地纬度，不能证明ZG等于椭球高，更不能识别默认下边界的未知零面。**没有新官方证据，EXTERNAL_DATUM_UNVERIFIED不变。

## 8. 复核、资源、异常与边界

45项不同CPU测试通过：新12、既有临时坐标14、小时查询8、时间/联合11。新测试初次因PYTHONPATH未配置无法导入，错误日志保留；仅修正命令环境后通过，源码/协议/容差未改变，正式诊断此前尚未启动。

唯一正式CPU任务监督returncode0/PASS、30.827680秒；worker29.822154秒、CPU33.409526秒、进程峰RSS330.895MiB，采样进程树峰329.656MiB；采样无缺口。独立核验8.590895秒包含在worker时间内，不重复加总。完成后服务器在整理阶段重启，中断未影响已结束的直接wait退出证据，恢复后未重跑诊断。

独立复核384统计行/288中位数差/3744贡献行/54旧联合行/596坐标行及203保护SHA；另用scalar math.log(obs/model)对25920配对值复算残差，exp差相对误差在预定1e-13内。总体与分箱绝对/相对MSE恒等式通过，未来ID与历史严格分离。原始及旧实验保持只读。resource_audit列出实际值、输出及定义；交互/编辑/Git不伪装成连续监控。完整查询轨迹/原始配对/位置数组仅本地_local文件；新公开CSV为派生统计。

无下载、联系人访问/邮件、GPU、模型积分、同化、轨道传播、新预测方法、新校正或高度拟合；全过程保持科学训练False、RestartFAIL、DART未准入、真实轨道BLOCKED与历史A14身份。

## 9. 科研结论及下一步

实测事实支持两种机制共同存在：**历史代表性随日期/截点/纬区变化；log中位数与平方误差/尾部目标不一致。**历史总体中位数接近仍可伴随不同尾部和严重相对损失，不能只靠刷新系数或缩小空间区间保证收益。

已识别高密度绝对权重与低密度相对损失的代数/统计机制；未分离模型物理误差、沿轨空间采样、高度零面或Swarm产品偏差的独立因果贡献。不把数值坐标回差当外部基准证明，也不以未闭合高度登记停止所有条件性研究。

建议下一轮首选**独立日期覆盖单因素复现**：保持现有背景身份、3h历史/06和18Z、估计器与四项标准，先预注册新增日期及观测—模型可用性，不改校正复杂度。若新增真实日期没有已批准模型覆盖，先申请数据/模型门禁，不能临时换日期或默认新积分。评价目标匹配的单因素估计器对照可作为之后独立方案，不本轮实施；坐标物理证据继续保留待确认，不用残差反推。

本轮COMPLETE表示诊断完成，不是校正科学PASS；结束即停止。
'''
 write(R/'reports/THERMOSPHERE_RESIDUAL_REPRESENTATIVENESS_V1.md',report)
 decision='''# 历史残差代表性诊断后的下一阶段决策 V1

状态：本轮只读诊断COMPLETE，未新增方法或科学准入。

实际证据：B14全域历史—未来中位数差跨24个重叠描述单元为−0.133064至+0.120258，3个符号翻转；纬区方向也变化。2021-03-23 18Z全域中位数几乎不变，旧Global相对RMS仍恶化12.649%，说明刷新/局地化系数不是充分条件。已复核高密度Q5驱动部分绝对净收益、低密度Q1/Q2驱动相对损失。两年尾部空间分布不相同。

优先建议：另授权一次**新增独立日期覆盖的同方法复现**，唯一主动改变观测日期覆盖，不同时改估计器/空间分区/历史时长/衰减。当前仅4个March日期、2年份，不能证明全年代表性。建议先新增每年2个预注册日期作为第一批（共4日、固定06/18Z），逐日期确认现有TIE-GCM有效时段/预热身份、官方观测产品版本/体积与独立用途；日期不可由RMSE挑选，不能把不合格模型场或不同预热身份静默混入。当前未指定日期或下载，不自动新积分。

若有合法现成背景：后续CPU分析预算≤600s、RSS≤4GiB、公开派生结果≤150MiB；原件下载预算应先按官方具体文件元数据另申请。若背景不足，则先提出模型/驱动与资源门禁，不沿用此次离线预算授权新模型。Swarm反演不是无误差真值，新日期也需说明是否真正未用于开发。

后续候选而非当前执行：保持固定数据/窗口，仅改变历史估计目标（log位置 vs relative平方目标）的单因素对照，事前冻结且仅历史拟合；它能检查目标不一致的贡献，不能同时加空间/高度/时间复杂参数。不用未来中位数或未来误差寻优。

坐标结论：当前Map-A转换通过数学容差；ZG物理零面及全模型纬度仍未知。暂不外部联系或发送邮件，不以亚毫米椭球差异替代外部基准证据。

SCIENCE_TRAINING_READY=False、EXTERNAL_DATUM_UNVERIFIED、RestartFAIL、DARTNOT_ADMITTED、REAL_ORBITBLOCKED及A14身份保持。本轮不自动进入新校正、FourCastDEN、DART或轨道实验，等待明确指令。
'''
 write(R/'docs/THERMOSPHERE_RESIDUAL_REPRESENTATIVENESS_NEXT_DECISION_V1.md',decision)
 total=sum(x.stat().st_size for x in F.rglob('*') if x.is_file())
 dump('resource_audit.json',dict(supervised_wall_s=sup['elapsed_s'],supervised_returncode=sup['returncode'],qualification=sup['qualification'],worker_wall_s=run['wall_s'],worker_CPU_s=run['CPU_s'],worker_peak_process_RSS_MiB=run['peak_process_RSS_MiB'],peak_sampled_tree_RSS_MiB=sup['peak_sampled_tree_rss_bytes']/2**20,supervisor_samples=len(sup['samples']),sampling_gaps=sup['gaps'],independent_verification_wall_s_INCLUDED_IN_WORKER=verify['wall_s'],preflight_wall_s=load('preflight.json')['wall_s'],unique_tests=45,test_suite_bodies_s=.043+.218+.142+.034,output_bytes_at_audit=total,public_output_limit_bytes=150*2**20,new_query_count=5760,new_fits=0,new_forecasts=0,GPU=0,TIE=0,DART=0,orbit=0,downloads=0,external_contact=0,one_formal_launch=True,formal_retries=0,server_recovery='Server interruption after successful formal run; only artifact/report finalization resumed, no second launch',resource_definition='tree RSS sampled; worker rusage process peak; independent audit already included in worker duration; interactive checks/editing/Git not represented as continuous trace',limits_PASS=sup['elapsed_s']<600 and sup['peak_sampled_tree_rss_bytes']<4*2**30 and total<150*2**20))
 dump('commands.json',dict(environment='source scripts/activate_orbit.sh',preflight='python scripts/prepare_residual_representativeness_v1.py',tests='PYTHONPATH="$PWD/src:$PWD" python -m unittest discover -s tests -p test_residual_representativeness.py -v',regressions=['test_provisional_coordinate_adapter.py','test_hourly_tiegcm_observation.py','test_late_day_correction.py'],sole_supervised_task='python scripts/launch_residual_representativeness_v1.py',independent_audit='verify_residual_representativeness_v1.verify() invoked within worker; no standalone re-run',finalization='python scripts/finalize_residual_representativeness_v1.py; read computed outputs only, no query/fitting',failed_initial_import_log='logs/residual_representativeness_v1_tests_initial_import.log',initial_schema_note='v10 has no source_manifest.json; use its own sha256_manifest and frozen matched cache, not an assumed common filename',existing_directory_policy='prepare and launch refuse existing directory/marker; do not remove outputs to rerun',base_commit='5b4d1be17841040fd7a29ff4eafae3bba6d784a2',protocol_SHA256=load('protocol_sha256.json')['SHA256']))
 p=R/'STATUS.md';s=p.read_text();intro='> 最新（2026-11-18，历史残差代表性/坐标数值诊断V1）：RESIDUAL_REPRESENTATIVENESS_DIAGNOSTIC=COMPLETE（只表示诊断执行完成）。四日期×06/18Z×B14/A7/B7共24背景，203保护SHA核实，复用20160旧配对值、仅缺窗重建5760查询全有效。45CPU测试；384统计/288中位数差/3744误差贡献/54旧联合/596坐标行独立复核，126历史指标保持。B14全域Δb −0.133064至+0.120258、3/24符号翻转；历史中位数近似稳定仍可有relativeRMS恶化，高密度绝对权重与低密度相对损失共同解释部分现象。2021低纬晚窗历史/未来.206033/.072549，2022高纬.126380/.009900。数值往返通过预冻结1e−5m/5e−10deg，实际卫星GRS80/WGS84高差最大.104568mm，大地/地心纬差最大.180224deg；不证明ZG零面。唯一监督exit0/PASS30.828s、worker峰330.895MiB；服务器在主任务完成后中断，恢复仅整理、不重跑。报告reports/THERMOSPHERE_RESIDUAL_REPRESENTATIVENESS_V1.md；无新参数/预测/下载/TIE/GPU/DART/轨道/外部联系，科学训练False/外部高度未验证/RestartFAIL/DART未准入/真实轨道BLOCKED及A14历史资格不改。下一步建议独立日期同方法复现，仅方案未执行。\n\n';p.write_text(s.replace('# 当前状态\n\n','# 当前状态\n\n'+intro,1))
 with (R/'WORKLOG.md').open('a') as f:f.write('''\n\n## 2026-11-18 — 历史残差代表性与坐标数值一致性诊断 V1\n\n目标/范围：OBSERVATION_CONSTRAINED_PHYSICS_FIRST，4固定日期(2021/2022-03-23/24)×06/18Z，B14主/A7B7控制，A14排除。开始根目录/realpath和main/远端=5b4d1be17841040fd7a29ff4eafae3bba6d784a2核实，读全部指定资料和已有模块。冻结协议SHA dfdeb2fe5354dbcd7d1652bd233e2ad9951182a3600a0b99b83eab84009e4077，先于未来分布与坐标试验。\n数据：四原CDF SHA/flag0/UTC30s/GRS80/密度正值通过，六背景12卷原SHA/ilevDEN(g/cm3)/ZG(cm)及工程记录通过。v10缓存格式不同（无source_manifest）已按它原始SHA清单处理；仅复用A值，不读取C/B/A14值参与分析。20160旧配对值复用，03-23早窗5760必要八列查询重建全有效，无外推。203受保护旧文件/参数/接口不改。\n学习/实现/运行：新增residual_representativeness模块、prepare/run/verify/launch/finalize脚本及12基础测试。source scripts/activate_orbit.sh；首次unittest缺PYTHONPATH导入失败，日志保留，设PYTHONPATH="$PWD/src:$PWD"后12通过，源码和协议无变化；既有临时坐标14/小时8/联合11通过，合计45不同测试。唯一CPU监督运行python scripts/launch_residual_representativeness_v1.py，真实exit0/PASS。服务器随后在整理阶段重启；恢复先检查run_result/退出证据/文件，不再启动诊断。\n结果：384分布统计、288中位数差、区域与覆盖/固定1h块，3744贡献行、596坐标行；126历史指标/54旧四旗标逐项核验不变。新03-23早窗无冻结校正结果，仅Raw统计；未来中位数不产生预测，无新拟合。B14全域Δb范围−.133064至+.120258，3/24符号翻转；2021-03-23 18Z全域中位数.088227/.086280近似稳定，但旧Global relativeRMS仍恶化12.649%。低纬历史代表性与估计目标不一致均有实测依据，非唯一物理因果归因。\n贡献：两年03-23晚窗Q5驱动大部分绝对净收益，Q1/Q2驱动相对损失；纬度法2021最差5%点全部低纬/低密度，2022最差5%全低密度而非低纬。保留全分箱/纬度/时间块，未删除不利点或普通IID显著性。\n坐标：预冻结独立显式椭球+Astropy/ERFA数值容差XYZ/高1e−5m、角5e−10deg，596行均通过；198解析/100固定卫星位置、原向量本地保留。往返XYZ最大2.945e−9m，库坐标独立正算最大2.013e−6m；同一卫星XYZ的GRS/WGS高度差最大.104568mm、大地地心纬差最大.180224deg。数值自洽不能解决ZG零面或模型纬度外部定义。\n资源：唯一监督30.827680s，worker29.822154s/CPU33.409526s/峰RSS330.895MiB，采样树峰约329.656MiB；独立8.590895s已含worker，不能重复相加。预检3.557768s，输出约19MiB；计算远低600s/4GiB/公开150MiB；交互编辑/Git/服务器暂停不冒充连续采样。原始新下载/模型/GPU/DART/轨道/训练/新校正/高度拟合/外部联系均0。\n文件：新experiments/thermosphere_residual_representativeness_v1/派生CSV/JSON及8PNG；报告reports/THERMOSPHERE_RESIDUAL_REPRESENTATIVENESS_V1.md；决策docs/THERMOSPHERE_RESIDUAL_REPRESENTATIVENESS_NEXT_DECISION_V1.md；实际命令/错误/资源/SHA均保存。完整配对、查询和原始XYZ_local仅本地，不上传。\n状态：COMPLETE仅诊断；SCIENCE_TRAINING_READY=False/EXTERNAL_DATUM_UNVERIFIED/RestartFAIL/DARTNOT_ADMITTED/REAL_ORBITBLOCKED和A14历史身份不变。下一步建议另授权新增独立日期覆盖、同算法同指标复现，先核模型有效域/预热和观测资产，不自动更换日期或积分；本轮完成停止，不新校正/AI/DART/轨道。按安全白名单正常提交/推送并独立核远端，最终SHA和同步结果在本地ignored审计及最终答复记录。\n''')
 print('Reports, decision, status/worklog and resource/command records prepared; no diagnostic re-run.')
if __name__=='__main__':main()
