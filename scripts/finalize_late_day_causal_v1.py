"""Generate measured late-day report/state; no parameter changes or new runs."""
from pathlib import Path
import sys,json,csv,re,time
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/causal_density_late_day_v1';sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
from prepare_fourcastden_swarm_observation_v1 import sha

def write(path,text):
 assert path.resolve().is_relative_to(ROOT)
 with path.open('x') as out:out.write(text)
def table(rows,keys):return '|'+ '|'.join(keys)+'|\n|'+'|'.join(['---']*len(keys))+'|\n'+'\n'.join('|'+ '|'.join(str(r[k]) for k in keys)+'|' for r in rows)+'\n'
def main():
 src=json.loads((F/'source_manifest.json').read_text());pr=json.loads((F/'frozen_protocol.json').read_text());par=json.loads((F/'correction_parameters.json').read_text());ver=json.loads((F/'independent_verification.json').read_text());status=json.loads((F/'cpu_job/status.json').read_text());assert ver['PASS'] and status['qualification']=='PASS' and status['returncode']==0
 tests=[]
 for n in ['late_day_causal_v1_tests.log','late_day_causal_v1_cross_year_tests.log','late_day_causal_v1_v10_tests.log','late_day_causal_v1_hourly_tests.log','late_day_causal_v1_native_tests.log']:
  s=(ROOT/'logs'/n).read_text();m=re.search(r'Ran (\d+) tests in ([\d.]+)s',s);assert s.strip().endswith('OK');tests.append(dict(log=n,N=int(m[1]),wall_s=float(m[2])))
 wall=status['elapsed_s']+json.loads((F/'preflight.json').read_text())['wall_s']+ver['wall_s']+sum(x['wall_s'] for x in tests);size=sum(p.stat().st_size for p in F.rglob('*') if p.is_file());assert wall<600 and status['peak_sampled_tree_rss_bytes']<4*2**30 and size<150*2**20
 resources=dict(measured_core_CPU_wall_sum_s=wall,definition='preflight + supervised matching/6 coefficient fits/evaluation/9 plots + independent validation +5 test suites; interactive file/metadata/report commands not individually timed, not whole conversation wallclock',supervisor_elapsed_s=status['elapsed_s'],supervisor_returncode=0,peak_sampled_tree_RSS_MiB=status['peak_sampled_tree_rss_bytes']/2**20,worker_peak_rusage_MiB=json.loads((F/'run_result.json').read_text())['peak_RSS_MiB'],sampling_definition='same-UID launched session; not continuous global peak',output_bytes_before_report=size,tests=tests,budgets={'CPU_wall_s':600,'RSS_GiB':4,'output_MiB':150},new_observation_bytes=0,GPU=0,TIE=0,DART=0,orbit=0)
 write(F/'resource_audit.json',json.dumps(resources,indent=2)+'\n')
 metrics=list(csv.DictReader((F/'metrics.csv').open()));joint=list(csv.DictReader((F/'joint_assessment.csv').open()));bins=list(csv.DictReader((F/'density_bin_gain_summary.csv').open()));reg=list(csv.DictReader((F/'region_metrics.csv').open()));future=[x for x in joint if x['window'].startswith('future')];assert len(future)==30
 coeff=[]
 for y in ['2021','2022']:coeff.append(dict(year=y,b06=f"{pr['stale06_coefficients'][y]:.9f}",multiplier06=f"{__import__('math').exp(pr['stale06_coefficients'][y]):.9f}",b18=f"{par['adaptive18'][y]['B14']['b18']:.9f}",multiplier18=f"{par['adaptive18'][y]['B14']['multiplier18']:.9f}"))
 primary=[]
 for y in ['2021','2022']:
  for w in ['future_1h','future_3h','future_6h']:
   for method in ['Raw','Adaptive18','Stale06','CrossYearTransfer18']:
    x=next(x for x in metrics if x['year']==y and x['case']=='B14' and x['window']==w and x['method']==method);g=next((g for g in joint if g['year']==y and g['case']=='B14' and g['window']==w and g['method']==method),None)
    primary.append(dict(year=y,window=w,method=method,N=x['n'],RMSE_e13=f"{float(x['RMSE'])*1e13:.6f}",relative_RMS_pct=f"{float(x['relative_RMS'])*100:.4f}",relative_P95_pct=f"{float(x['relative_P95'])*100:.4f}",RMSE_gain_pct='—' if g is None else f"{float(g['RMSE_gain_pct']):.4f}",relative_RMS_gain_pct='—' if g is None else f"{float(g['relative_RMS_gain_pct']):.4f}",JOINT='—' if g is None else g['JOINT_NO_REGRET']))
 regtable=[]
 for y in ['2021','2022']:
  for lat in ['low','mid','high']:
   vals={x['method']:x for x in reg if x['year']==y and x['case']=='B14' and x['window']=='future_6h' and x['region']==lat};regtable.append(dict(year=y,region=lat,N=vals['Raw']['n'],raw_relRMS_pct=f"{float(vals['Raw']['relative_RMS'])*100:.4f}",adaptive_relRMS_pct=f"{float(vals['Adaptive18']['relative_RMS'])*100:.4f}",raw_relativeBias_pct=f"{float(vals['Raw']['relative_bias'])*100:.4f}",adaptive_relativeBias_pct=f"{float(vals['Adaptive18']['relative_bias'])*100:.4f}"))
 decomp=[]
 for y in ['2021','2022']:
  for q in ['1','2','3','4','5']:
   x=next(x for x in bins if x['year']==y and x['window']=='future_6h' and x['method']=='Adaptive18' and x['quintile']==q);decomp.append(dict(year=y,quintile=q,N=x['N'],raw_absolute_SSE_share_pct=f"{float(x['raw_absolute_SSE_share'])*100:.2f}",raw_relative_SSE_share_pct=f"{float(x['raw_relative_SSE_share'])*100:.2f}",share_of_net_absolute_gain_pct=f"{float(x['fraction_of_net_absolute_MSE_reduction'])*100:.2f}",relative_MSE_increase=f"{float(x['relative_MSE_increase']):+.6f}"))
 blocks=[]
 for y in ['2021','2022']:
  for w in ['block_0_1h','block_1_3h','block_3_6h']:
   for method in ['Adaptive18','Stale06','CrossYearTransfer18']:
    x=next(x for x in joint if x['year']==y and x['case']=='B14' and x['window']==w and x['method']==method);blocks.append(dict(year=y,window=w,method=method,RMSE_gain_pct=f"{float(x['RMSE_gain_pct']):.3f}",relative_RMS_gain_pct=f"{float(x['relative_RMS_gain_pct']):.3f}",JOINT=x['JOINT_NO_REGRET']))
 report='''# 晚时段因果密度校正与双向跨年份迁移验证 v1

2026-11-16；`CAUSAL_DENSITY_LATE_DAY_VALIDATION=COMPLETE`仅表示冻结实验执行完成。身份`LATE_DAY_ROLLING_ORIGIN / PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED`，不宣布全面预测改善或物理验证PASS。

## 1. 预注册协议与输入完整性

主背景B14，两年均不更换；A7/B7工程合格控制，A14完全排除。2021 A14工程PASS仅敏感性的历史身份及2022 A14 PARTIAL都不改变。2021/2022 A0301各2880条、30秒、flag0，原件SHA与v10/v11 source记录一致。本轮拟合只用A，不读C/B密度，无新观测下载。

六背景均通过历史输入清单/实际NetCDF/source/GPI/input SHA、退出码0、4NORMAL EXIT、工程data_audit检查。每条原生时间序列含15:00至次日00:00连续10小时帧；确有24Z边界，可支持23:59:30观测插值。没有退回其他截点。DEN/ZG均ilev29，g/cm³×1000与cm×.01显式；实际使用帧原始填值/非有限/极大哨兵/DEN非正独立扫描全部0。6480次查询（2年×3背景×1080点）全部有效，自身和共同覆盖100%。原模型/观测文件未写入。

UTC校正[15,18)360点；未来[18,19)120、[18,21)360、[18,24)720，另列不重叠[18,19)、[19,21)、[21,24)。18:00只属于未来，24:00模型帧仅作插值支持，不加入卫星评价样本。复用v10/hourly/Map-A查询链、v11 metric_row/strata及v10标量正值应用，未改估计器或引入局地/高度/衰减拟合。

## 2. 方法与因果身份

Raw不校正；Adaptive18各年各背景只用自己的过去A残差中位数；Stale06仅B14原样使用同年03—06的旧系数；CrossYearTransfer18仅B14交换另一年15—18系数。六个本地历史参数和两年全部应用系数在未来指标计算前写入文件，并链接冻结协议SHA。未来密度毒化20个数量级不改变估计；没有未来观测选择或调参。

**双向迁移是回溯诊断，不是严格历史业务可用性验证**：2022→2021的系数在真实2021时尚不可获得。目标年未来密度未参与估计不代表跨年数据在实际预报时已知。Adaptive18/Stale06的同年时间隔离成立，整个模型驱动仍为已有真实GPI的HINDCAST。模型场未更新，输出尺度改进不等于更真实初始状态或状态同化。

## 3. B14早晨与晚间真实系数

'''+table(coeff,list(coeff[0]))+'''
2021晚间乘数比早晨增大约2.38%；2022晚间比早晨减小约0.28%。其他背景各自参数见correction_parameters.json，不跨背景交换。即使两个年份18Z系数接近，也不能据此推断未来收益接近。

## 4. 未来累计窗口完整主结果

RMSE单位10^-13 kg/m³。gain正为改善、负为恶化；其余密度单位kg/m³，MAE/Bias/logRMS/Pearson/有符号relativeBias等完整列见metrics.csv。

'''+table(primary,list(primary[0]))+'''
结论分开回答：

- **Stale06并非全面有效**：2021首小时RMSE也恶化，3/6h绝对RMSE改善但relative RMS全部恶化；2022三个累计绝对RMSE改善、relative RMS全部恶化。
- **新系数不保证更好**：2021 Adaptive18在首小时比Stale06更差，3/6h RMSE更好但relative RMS仍更差；2022 Adaptive18两种RMS都略优于Stale06，但仍明显差于Raw的relative RMS。
- **双向迁移只出现混合收益**：2022→2021首小时两指标都恶化，3/6h仅RMSE改善；2021→2022三个窗口RMSE改善但relative RMS恶化。不能把迁移叫稳定预测收益。
- 2021中高纬六小时relative RMS小幅改善，2022中高纬全部恶化，v11的区域改善不具有时间稳定性。

## 5. 联合评价：没有JOINT_NO_REGRET

事前定义，无综合加权分数：RMSE严格下降、relative RMS严格下降、relative P95不升、低纬有符号relativeBias绝对值不升；低纬N<30标N/A，不制造通过。所有比较对同ID、同质量和共同有效域。未来三个累计窗口：B14两年三方法18项，A7/B7两年12项，**合计0/30满足四项联合规则，30项均有足够低纬样本，没有N/A冒充失败/通过。**

2021 B14六小时Adaptive18 relativeP95由32.442%升至48.502%，2022由55.332%升至75.718%。未来点级：2021 Adaptive18 450改善/270恶化，Stale06 457/263，Transfer448/272；2022 Adaptive18只有293改善/427恶化，Stale06 290/430，Transfer302/418，虽然绝对RMSE下降。没有删除不利点或挑选最好时效。

## 6. 五分位分解解释指标矛盾

每年每未来窗口按**真实观测密度**np.quantile线性分位划5箱，边界同值不扰动，可能非严格等N；只作诊断，完全不参与估计/模型选择。此处六小时每箱144点。逐方法输出SSE、SSE/N对总MSE的贡献、SSE占比、对应relative平方量、平均相对Bias及log RMS。

验证恒等式RMSE²=mean(rho_obs²×relative_error²)，relativeRMS²=mean(relative_error²)。独立检查80个箱划分的数量、贡献和与比例和，以及所有112个全窗指标行和70个联合规则行。不存在把两个范数相减代替误差或改分母floor。

B14六小时Adaptive18分解：

'''+table(decomp,list(decomp[0]))+'''
`share_of_net_absolute_gain`是**带符号净收益分解**，并非概率；负值表示该箱抵消总体收益，大于100%表示高密度收益还被其他箱损失抵消。

2021最高密度Q5占Raw绝对SSE64.82%、贡献79.32%的净绝对MSE改善，Q1/Q2却恶化；2022 Q5占绝对SSE49.96%，贡献193.14%的净改善，Q1/Q2/Q3全部抵消收益，其中Q1原始relative SSE占75.16%。这直接支持“高密度收益主导绝对RMSE，低密度相对误差扩大”的解释；不是仅凭总体均值猜测，也不把密度箱等同于独立物理区域或因果机制。

## 7. 纬度×高度与时间结构

B14六小时区域：

'''+table(regtable,list(regtable[0]))+'''
低纬过校正在两年再次出现。2021低纬主要430—440km（N218），relative RMS27.223→32.267%；440—450km（N30）22.134→24.585%。2022低纬400—430km（N175）16.079→22.871%，430—440km（N73）19.022→25.406%。其余联合格N<30均明确N/A。高度取原始Swarm椭球高作统计分层，不能解释成已验证ZG登记或高度误差因果；纬度/高度/时刻/密度沿轨相关。

不重叠未来时段：

'''+table(blocks,list(blocks[0]))+'''
2021首小时明显不利，后续绝对误差改善，relative RMS只在21—24小幅改善；2022 absolute收益逐时变弱，relative RMS持续恶化。这些不构成普适指数衰减定律；累计窗口重叠，30秒点相关，没有普通IID显著性检验。

## 8. 数值、资源与复现

53项CPU测试通过（晚时段11、跨年10、v10校正6、hourly8、native18）；检查午夜/半开/未来毒化/旧06Z等价、箱贡献/同值处理、权重恒等式、四旗标和N/A拒绝。2160条CDF直接核对，18个真实8列重建探针，112全窗指标、80箱划分和70联合行独立重算通过。校正密度均正且有限，所有旧文件SHA保持到实验结束。

'''+f"预检/监督任务/独立核验/测试套件已计量合计{wall:.3f}秒；监督任务{status['elapsed_s']:.3f}秒真实exit0/PASS，峰值采样树RSS{status['peak_sampled_tree_rss_bytes']/2**20:.3f}MiB；报告前目录{size/2**20:.3f}MiB。小型交互文件检查未逐任务计时，不冒称整个会话自然墙钟或连续全局RSS峰值；600秒/4GiB/150MiB预算未扩大。\n"+'''
输入/协议/代码/输出SHA、原始运行身份及24Z记录见source_manifest/preflight/sha256_manifest。命令见commands.json。CPU作业和各文件采用独占创建，原标签不可盲目重放。只发布小型派生残差/指标/图，不上传CDF/NetCDF、完整匹配数组和查询缓存。

## 9. 高度与下一阶段资格

复用HEIGHT_DATUM_OFFICIAL_EVIDENCE_UPDATE_V1；本轮未取得新官方ZG零面定义或维护者回复，未发邮件、未重复历史搜索、未拟合高度。保持EXTERNAL_DATUM_UNVERIFIED与Map-A条件身份。

这次为局地校正提供**研究动机**：全局常数的空间/密度代表性不足，低纬过校正重复；并不证明某个局地核或纬度方案已有效。可在下一轮单独授权后，先冻结一个空间维度的受控对照并使用未参与选型的日期，不同时改变时间衰减/高度映射/估计器。DART不准入：Restart一致性FAIL、正式高度/误差模型/合法集合/版本实测/独立验证未齐备。真实轨道BLOCKED、科学训练False及两年A14原资格均保持。本轮停止，不自动开展下一项。
'''
 write(ROOT/'reports/CAUSAL_DENSITY_LATE_DAY_VALIDATION_V1.md',report)
 decision='''# 晚时段因果密度校正：下一阶段决策 v1

2026-11-16。晚间固定实验完成，未来联合无后悔0/30，未通过全面改善科学标准；不因绝对RMSE局部下降追认PASS。

## 已有实证

- 2021 B14 06Z/18Z b=.0939908/.1174984；2022 .1261253/.1233119。刷新时间不保证代表未来：2021首小时全部修正恶化，2022中高纬relative RMS也恶化。
- 2021六小时Adaptive绝对RMSE改善26.636%，relative RMS恶化9.296%；2022改善12.385%、relative RMS恶化37.300%。Transfer、Stale06同样没有联合通过。
- Q5贡献高密度净绝对改善，而Q1等低密度损失被总体绝对指标掩盖；低纬及特定观测高度联合格重复过校正。不能把分箱或沿轨相关当因果/独立重复。

## 建议下一轮仅一个受控局地因素

已有足够证据提出“小规模局地校正是否减少全局尺度过校正”的可检验假设，但没有证据预先宣布它一定有效。建议保持中位log估计器、3h历史、1/3/6h评价、Map-A和四项联合标准，只改变**一个空间代表性因素**（例如事先固定低/中/高纬分区），不同时加时间衰减、高度拟合或新损失。每区历史样本数门槛及无支撑行为必须事前冻结；不得读取目标未来Bias决定是否施加或缩小系数。

保留本次常数、Raw和Stale为基线；使用新授权且预先固定的未参与参数选择日期/截点，现有两日06/18Z只能叫开发诊断。B继续保留，不因局地方法复杂就提前用于调参。若要跨星验证，C仍须明确POD关联与开发身份。

资源候选：CPU≤600秒、RSS≤4GiB、输出≤150MiB；以本次6480查询/9图监督约20.46秒为外推依据，而不是新实测。缺观测时另申请，不本轮下载。新protocol必须先批准冻结，本轮不执行任何局地拟合。

## DART与轨道

当前不应进入DART：零增量Restart round-trip及连续/分段一致性、He观测算子、正式高度、观测误差/相关性、合法成员与当前版本实测及保留验证均未齐备。常数输出校正无法解决这些门禁。真实气动/姿态/推力和完整受力未闭合，轨道验证仍BLOCKED。SCIENCE_TRAINING_READY=False；2021 A14工程PASS仅敏感性、2022 A14工程PARTIAL保持。
'''
 write(ROOT/'docs/CAUSAL_DENSITY_LATE_DAY_NEXT_DECISION_V1.md',decision)
 write(F/'commands.json',json.dumps(dict(environment='source scripts/activate_orbit.sh; PYTHONPATH=$PWD/src:$PWD; CPU subprocess CUDA_VISIBLE_DEVICES empty, inherited GPU environment otherwise untouched',commands=['python -m unittest discover -s tests -p test_late_day_correction.py -v','python scripts/prepare_late_day_causal_v1.py','python scripts/launch_late_day_causal_v1.py','python -m unittest discover -s tests -p test_cross_year_correction.py -v','python -m unittest discover -s tests -p test_causal_density_correction.py -v','python -m unittest discover -s tests -p test_hourly_tiegcm_observation.py -v','python -m unittest discover -s tests -p test_tiegcm_density_provider.py -v','python scripts/verify_late_day_causal_v1.py','python scripts/finalize_late_day_causal_v1.py'],warning='Immutable run folders and parameters refuse replay. Future reproduction requires a separate authorized tag.'),indent=2)+'\n')
 write(F/'completion_audit.json',json.dumps(dict(state='COMPLETE',engineering_execution_PASS=True,science_full_benefit_PASS=False,joint_future_tests=30,joint_future_pass=0,joint_future_NA=0,tests=sum(x['N'] for x in tests),queries=6480,valid_queries=6480,CDF_records_independent=2160,metric_rows_independent=112,bin_partitions_independent=80,joint_rows_independent=70,EXTERNAL_DATUM='EXTERNAL_DATUM_UNVERIFIED',Restart='FAIL',DART='NOT_ADMITTED',real_orbit='BLOCKED',training=False,A14_2021='PASS/sensitivity only, excluded',A14_2022='PARTIAL, excluded'),indent=2)+'\n')
 p=ROOT/'STATUS.md';s=p.read_text();entry='> 最新（2026-11-16，晚时段因果校正v12）：CAUSAL_DENSITY_LATE_DAY_VALIDATION=COMPLETE（执行完成、全面收益未成立）。两年B14/A7/B7原卷SHA/15—24Z及次日00边界通过，6480Map-A查询全有效；53CPU测试、2160CDF直读、18插值探针、112指标/80箱划分/70联合行独立检查通过。B14晚间b2021=.1174983681（×1.1246797946）、b2022=.1233119240（×1.1312372259）；Stale06原值不重拟合、双向只迁B14。2021首小时全部修正两RMS均恶化；6h Adaptive RMSE改善26.636%、relativeRMS恶化9.296%；2022六小时改善12.385%、relativeRMS恶化37.300%。高密度箱贡献绝对收益、低密度箱放大相对损失，低纬过校正重复，2022中高纬也恶化。未来四旗标JOINT_NO_REGRET=0/30（无N/A），不宣布全面改善。无新下载/TIE/GPU/DART/轨道/局地拟合；A14两年均排除，2021PASS仅敏感性/2022PARTIAL历史保持。报告reports/CAUSAL_DENSITY_LATE_DAY_VALIDATION_V1.md；下一轮只建议另授权一个空间因素的受控局地对照，不自动执行。高度未验证、RestartFAIL、DART未准入、科学训练False、真实轨道BLOCKED不改。\n\n';p.write_text(s.replace('# 当前状态\n\n','# 当前状态\n\n'+entry,1))
 p=ROOT/'WORKLOG.md';p.write_text(p.read_text()+f'''\n\n## 2026-11-16：晚时段因果密度校正与双向跨年迁移v12\n- 范围：仅CPU，Raw/Adaptive18/Stale06/CrossYearTransfer18；不改中位数，不新增局地/高度/衰减拟合，不读B/C，不下载观测/TIE/GPU/DART/轨道。起始本地远端c7c401b...一致，无重复旧实验，历史未跟踪日志保留。\n- 门禁：两年B14主、A7/B7控制，六组输入/source/GPI/原CDF-NetCDF SHA与退出0/4NORMAL EXIT审计通过，15—次日00十帧连续且支持23:59:30。A14两年排除，2021工程PASS仅敏感性及2022PARTIAL不改。DEN/ZG ilev29、g/cm3×1000/cm×.01不改，实际原始帧显式填值/非有限/DEN非正0。6480真实查询全有效；完整8列/层/权重诊断只本地。\n- 冻结：各年[15,18)360过去A点，未来[18,19)/[18,21)/[18,24)120/360/720，非重叠三块；所有六本地参数及双向应用系数在未来指标前保存，毒化不变。2022→2021是回溯迁移，不称2021时已可用的业务因果预报。\n- 结果：B14 b18 2021 .11749836810129466、乘数1.1246797945787346；2022 .12331192397950375、乘数1.131237225937738。旧06值 .0939907670/.1261252775原样使用。2021首小时三修正均恶化，两年其余累计RMSE有改善但所有累计relativeRMS恶化。6h Adaptive RMSE改善26.636%/12.385%，relativeRMS恶化9.296%/37.300%，低纬Bias -2.356→9.818% / .577→13.776%，2022中高纬同样变差。未来四旗标联合0/30，无少样本N/A伪通过。\n- 分解：预注册未来观测五分位仅诊断；SSE/MSE贡献/占比、relative平方量、Bias/logRMS完整。2021Q5贡献79.32%净绝对改善，2022Q5 193.14%（其他箱抵消），Q1相对损失明显。带符号贡献不是概率；权重恒等式逐窗检验。纬×高N<30 N/A，高度是外部椭球高统计分层，非登记或因果证明。\n- 验证：53CPU测试，2160CDF直接一致，18真实插值探针，112指标行、80分箱贡献划分、70联合判定独立复核；正密度/有限全通过。旧原数据与代码/产物SHA保持，无失败重试。9真实图，图5视觉检查通过。\n- 资源：监督exit0/PASS {status['elapsed_s']:.3f}秒；核心预检+监督+核验+5套测试已计量合计{wall:.3f}秒，峰值采样RSS{status['peak_sampled_tree_rss_bytes']/2**20:.3f}MiB，报告前目录{size/2**20:.3f}MiB；交互小文件操作不逐项计时，不冒称对话自然墙钟/连续RSS峰值，600秒/4GiB/150MiB未扩张。\n- 高度：复用v10官方证据更新，无新定义/维护者回复，不重复历史搜索或发邮件。EXTERNAL_DATUM_UNVERIFIED、RestartFAIL、DART未准入、训练False、真实轨道BLOCKED保持。\n- 交付：reports/CAUSAL_DENSITY_LATE_DAY_VALIDATION_V1.md、docs/CAUSAL_DENSITY_LATE_DAY_NEXT_DECISION_V1.md、协议/来源/系数/指标/区域/密度箱/逐点/时间块/联合/资源/SHA/命令/9图。研究状态COMPLETE非科学PASS；有局地单因素假设依据，尚未证实局地有效，下一轮另授权，不自动执行。只公开轻量派生结果，原始和完整查询/匹配本地；Git结果以实际逐字HEAD核验为准。\n''')
 print('LATE DAY REPORT/STATE COMPLETE',flush=True)
if __name__=='__main__':main()
