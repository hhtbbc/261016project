"""Evidence-based six-hour reports and future-only decision; no network/model calls."""
import sys,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_fourcastden_multistep import sha,dump
from run_fourcastden_six_hour import F,DATES,MODELS

def main():
 a=json.loads((F/'analysis.json').read_text());rt=json.loads((F/'runtime.json').read_text());sup=json.loads((F/'supervision.json').read_text());audit=json.loads((F/'delivery_audit.json').read_text());driver=json.loads((F/'driver_comparison.json').read_text());short=json.loads((F/'short_check.json').read_text())
 def write(path,s):
  with (ROOT/path).open('x') as f:f.write(s)
 def win(d,m,h):return next(r for r in a['windows'] if r['date']==d and r['model']==m and r['hour']==h)
 def var(d,m,h,n):return next(r for r in a['summary'] if r['date']==d and r['model']==m and r['hour']==h and r['variable']==n)
 high='|日期|模型|+1h %|+2h %|+3h %|+4h %|+5h %|+6h %|\n|---|---|---:|---:|---:|---:|---:|---:|\n'
 absolute='|日期|模型|+1h|+2h|+3h|+4h|+5h|+6h|\n|---|---|---:|---:|---:|---:|---:|---:|\n'
 ends='|日期|模型|全层DEN RMSE kg/m3|近400—500组相对RMS %|固定upper20—28相对RMS %|顶层P95 %|极区最大相对差 %|\n|---|---|---:|---:|---:|---:|---:|\n'
 for d in DATES:
  for m in MODELS:
   high+=f'|{d}|{m}|'+ '|'.join(f"{win(d,m,h)['near400_500_mean_relative_RMS']*100:.6f}" for h in range(1,7))+'|\n'
   absolute+=f'|{d}|{m}|'+ '|'.join(f"{win(d,m,h)['mean_DEN_layer_RMSE_kg_m3']/1e-11:.5f}" for h in range(1,7))+'|\n'
   r=win(d,m,6);ends+=f"|{d}|{m}|{r['mean_DEN_layer_RMSE_kg_m3']:.8g}|{r['near400_500_mean_relative_RMS']*100:.6f}|{r['upper20_28_mean_relative_RMS']*100:.6f}|{r['top_relative_P95']*100:.4f}|{r['polar_relative_max']*100:.4f}|\n"
 perf='|日期/模型|加载s（复用为0）|读取解码ms|标准化ms|其余预处理ms|6次forward合计ms|native指标事件ms|loop s|保存s|显存allocated峰MiB|\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'
 for r in a['performance']:perf+=f"|{r['date']} {r['model']}|{r['model_load_s']:.4f}|{r['read_decode_s']*1000:.3f}|{r['normalization_s']*1000:.3f}|{r['other_preprocess_s']*1000:.3f}|{r['network_total_GPU_ms']:.3f}|{r['native_metrics_GPU_ms']:.3f}|{r['author_loop_metrics_hooks_s']:.4f}|{r['save_s']:.4f}|{r['peak_allocated_bytes']/2**20:.3f}|\n"
 validation=f'''# FourCastDEN两日期连续6小时执行验证（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 范围和数据门禁

固定2023-01-04与03-24，01初始化、目标02—07，每序列6步。新增8序列48正式forward，加唯一Jan4 Direct单forward短例。旧2h数组、官方源码/Linux副本、4权重、static/static_log/旧审计等{audit['protected_files_unchanged']}项SHA不变；没有训练、微调、12/24h、TIE或RK45。首检本地及远端main均a1b474481155d252281ec3ff7751351f82b4d18a。

已存ZIP目录先确认12成员与压缩字节25,019,661，网络中央目录再核CRC/尺寸/真实偏移。仅新增Jan4 04—07四帧、Mar24 00—07八帧。第一次第8成员文件名Range收到HTTP500（未读body），前7成员已CRC/SHA通过；保留ranges.json/失败日志，另一次有界补取只取剩5成员，共用40MiB预算，未重取成功帧、没有绕过CRC或200整包。最终累计响应体{audit['network_body_bytes']}字节={audit['network_body_bytes']/2**20:.3f}MiB，保守预留{audit['network_reserved_bytes']}字节<40MiB。所有成功数据Range均206/Content-Range/长度匹配，ZIP CRC与zlib复核，SHA和14键/shape/dtype/finite/有限哨兵/正DEN/TN/ZG单调校验通过，新raw0444。各文件实际min/max及单位契约、原压力网格见*_download.json/preflight；NPZ无独立坐标/单位/时间属性，不冒称外部高度验证。

## 任意步反馈与实际作者流程

新autoregression.check_autoregression支持任意正长度、H0/H1，逐步对比真实hooks的177/354通道、171输出、历史顺序、逐块下一小时6辅助和目标4标量。H1：[real00,real01]→[real01,pred02]→[pred02,pred03]→…→[pred05,pred06]。第三步开始两个状态均为预测。H0每步反馈前次预测；Flow逐步normalized delta相加；log始终匹配static_log、log10(g/cm3)、pow10逆变换，DEN乘1000转kg/m3。

6项新CPU测试调用实际作者inference循环与合成网络，对四模式的6步未来真值毒化均不改变预测，错误后期teacher forcing/aux/scalar/Flow直接状态被拒绝；任意1/3/7步合成也检查，不是额外真实模型预测。全232测试25.416s通过，旧ERFA合成测试dubious-year及focused扩展导入warning原样保留，未安装环境或屏蔽检查。

严格官方权重load_state_dict、原AFNONet，History66,870,720参数/354输入，其余64,695,744/177，均171输出。232测试与全部静态门禁先通过，再唯一Direct真实短例（{short['GPU_ms']:.3f}ms）验证有限/正密度及shape，之后正式第一步与其逐元素一致。每序列独立初始化，不跨日期传状态。实际174物理/LBC通道从原NPZ重建匹配标准化逐元素一致。新6步全部hooks通过；Jan4前2步与全部4模型既有2h结果逐元素一致，旧网络未重跑。

全部48预测状态finite、DEN100%正、TN正，无指数溢出/裁剪/补0/重试。网络、驱动、输入、补丁SHA与每序列配置/反馈/输出SHA在实验目录，原始第三方不改。已知未来条件为HINDCAST，不是实时自主预报。

## 公共物理与native评价

float64匹配逆变换、同raw目标02—07、普通physical climatology、固定real01持续性。密度kg/m3、温度K、风m/s、Z位势高度m；native作者log ACC/dex另表。cos纬度加权RMSE和ACC、无效分母N/A；独立加权求和实现复核{audit['common_physical_channel_checks']}个模型通道时效rtol1e-12。native normalized RMSE最大相对差{audit['author_normalized_RMSE_max_relative']:.3g}、ACC最大绝对差{audit['author_ACC_max_absolute']:.3g}，沿用rtol2e-5/atol1e-25/ACC2e-6，没有放宽。每模型每lead171/171通道均优于共同持续性，仍不是观测精度验证。

DEN全球/极区/非极区逐层RMSE、相对RMS/P95/max、自然ln差/偏差、固定upper20—28、参考ZG中位400—500组全保留。Jan4 near组21/22/23，Mar24 +1/+2h为20/21/22、+3—6h为20/21（22层中位高出500km）。因此跨lead近高组成员变化也会影响曲线，不能称固定几何高度误差；固定upper和全逐层结果提供补充。

## 运行资源与独立计时

{perf}

总监督{sup['wall_s']:.6f}s（含GPU worker启动和SHA等），GPU阶段{rt['GPU_phase_wall_s']:.6f}s含CPU I/O/压缩/评价；纯网络事件合计另列，不能用总墙钟当纯网络。短例先冷调用，正式NN已warm；各模型各加载一次复用两窗，未做额外吞吐warm-up。首次native指标事件546.599ms、log新分支116.391ms，含首次编译/派发及CUDA区间中的等待，并非纯kernel剖析；随后native指标区间约2ms。指标call墙钟与事件分别存储，不能据此给稳健速度排名。

DatasetTimer仅透传计时load_variables与_normalize，保留原返回值、原算术和原源文件；读取解码包含NPZ解压/字段抽取，其余预处理含solar/geomagnetic/拼接/张量转换。作者loop内部另有读取，不将前置独立读取与loop简单加总作总推理。MetricTimer透传三原指标函数，另存每次call wall/GPU events，无新增NNforward；独立raw重建、前缀完全一致与native指标复核证明所用数值路径通过。

监督峰RSS{sup['peak_RSS_bytes']/2**30:.3f}GiB，CUDAallocated峰约295—309MiB（reserved含缓存/加载，不等于活跃张量）；CPU分析{a['CPU_analysis_s']:.3f}s、峰{a['analysis_peak_RSS_KiB']/1024:.3f}MiB。初审新增{audit['new_files_bytes']/2**20:.3f}MiB<800MiB，网络<40MiB、GPU<600s/RSS<4GiB；原始和预测大NPZ只本地。实际GFZ与作者NPZ驱动分别记录，不以替换输入强行相等。

## 复现实验入口

source scripts/activate310.sh；unittest discover；run_fourcastden_six_hour.py --fetch（初次500留档）；同脚本--resume-fetch（一次剩余补取）；无参静态；supervise_fourcastden_six_hour.py；analyze_fourcastden_six_hour.py；audit_fourcastden_six_hour.py；write_fourcastden_six_hour_reports.py；最终audit --final。均once-only，不删除launch重试。新标签experiments/fourcastden_six_hour_v1，raw/processed同标签，logs/fourcastden_six_hour*。这里只证明工程/数值/对TIE参考的条件预测，不等于完整论文训练复现、真实大气或最终轨道准确性。
'''
 write('reports/FOURCASTDEN_SIX_HOUR_VALIDATION.md',validation)
 comparison=f'''# FourCastDEN四模型连续6小时比较（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 共同任务与主要发现

同01起点/02—07目标，History额外真实00，四组官方权重/匹配统计不同，是官方整套变体而非训练单因素消融。全部物理空间共同raw目标/普通气候态/相同real01持续性，六变量分别SI，不合成不同单位RMSE。只两个预选日期，不能用网格数当独立样本或选全年最优模型。

Jan4：高层DEN第一小时Flow最低，此后2—6h Direct最低。Mar24：第一小时Flow最低，2—4h History最低，5—6h log最低。Flow优势没有持续到6h，History在增强活动窗出现条件高层相对优势，与旧五季节窗较差结果并不矛盾。History全层绝对DEN仍两日期所有6时效最高，不能只报告其局部高层改善。log在Mar24 +6h六变量平均层RMSE均最低，但Jan4 +6h六变量均由Direct最低，不给总体架构结论。

## 高层密度相对RMS完整曲线

每项为参考ZG全球中位400—500km选出的原生ilev逐层相对RMS再平均；不是固定450km，也不是Swarm沿轨误差。

{high}

Mar24 near组前两步20/21/22，后四步20/21，跨lead组变化要与固定upper20—28/逐层指标一起分析；单个时效四模型组相同，配对公平。顶部/极区另列，不挑有利层。

## 全层DEN绝对RMSE（表内单位1e-11 kg/m3）

{absolute}

先逐层加权RMSE再平均，低层密度量级大；此指标与上层相对误差可能方向不同。第6小时完整指标：

{ends}

## 误差积累与非单调性

Jan4近高组6h/1h倍率Direct20.57、Flow25.59、log16.63、History14.95，Mar24分别8.75/11.01/7.46/9.35。以“首次达到首小时相对RMS的2倍”作描述性标记（不是验收/科学稳定性阈值）：Jan4四组均在+2h；Mar24 Flow/History +2h，Direct/log +3h。Flow在这两个窗口高层倍率较高，但其首小时基数更小，须同时看绝对误差表，不能据倍率单独判最不稳定。

History Jan4绝对DEN倍率2.74低于其他约11.72—19.08，实际终点误差反而最大；这是高起始误差的影响，不能说已消除积累。Mar24 History近高组所有6步优于Direct，第2—4步四组最低，最后仍次于log；值得再核对原训练/历史配置与独立窗口，不宜因五窗旧结果删除History。

TN/风/Z等的误差增长也明显，必须分变量/单位阅读summary.csv。Jan4 TN/UN/VN/Z约13—25倍、WN约11倍；Mar24 TN/UN/VN/Z约7—20倍、WN约9—12倍（具体每变量每组growth.csv），不能用这些倍数把K误差和m/s误差直接加总。不是所有曲线单调：Jan4 Flow/log/History的WN平均RMSE有一步下降；Mar24四组VN均有一步下降。DEN近高组和绝对指标本次均增长，这只是实际观察，不是推理中强制单调。

上层是否比其他层更快也非一概而论：Jan4近高组倍率高于全层相对RMS平均倍率，Mar24大体接近；near层组变动与不同初始误差会影响倍率。逐层6h误差、固定upper和自然log偏差完整保留，不能只用某个高度组选方案。

## 指数、正性与局地偏差

log未发生指数溢出、下溢、负或非有限密度；未观察到仅log独有的爆炸性数值异常。指数会把log误差映射为相对密度差，但较高或较低预测误差不能单因果归于指数，因为权重/非DEN统计/训练目标不同。全部TN约146.9—1736.6K，最大绝对风分量约1095.5m/s，Z约95.65—854.88km（位势高度，非ZG），无明显数值发散；这些范围筛查不等于科学准确。Mar24极区局地密度相对差最高约34%—38%，即使全球组RMS约4%，必须保留局地不利值，不把positive当准确。

## 计算、证据与下一步

8序列48正式forward+1短例，232测试/8208通道独立物理复核、533历史保护SHA通过。Jan4前2步与旧2h逐元素一致，证明新长序列未悄换初始/短时算法。监督39.700s、峰RSS1.316GiB，GPU阶段30.841s含I/O；每组6forward约110—113ms，不代表完整端到端成本。首native指标调用有编译/派发冷成本，后续更小，不能用它做模型速度结论。读取/预处理/加载/指标/保存/显存完整performance.csv；CPU分析10.554s、约636MiB。禁止据此直接声称相对TIE仿真多少倍整体加速。

8类CSV共10260逐层物理行、360变量汇总、5220区域密度、60窗口、8208原native、48增长、8性能、16驱动；8图high_DEN/absolute_DEN/variables/growth/two_dates/layers_6h/performance/drivers，统一results前缀fourcastden_six_hour_v1。实验配置、数据/权重/补丁SHA、step_physics/feedback与audit在experiments同标签；大数组本地。

可以设计同两窗四模型12h受限实验，24h应待12h验收，不能由6h无发散直接保证24h。不要仅挑当前较好的Direct/log删除Flow或History，保留完整对照和更多独立窗口；多步训练、分层/相对损失是有依据的待验假设，未训练/调参。详见LONG_HORIZON_DECISION；真实大气/轨道门禁继续。
'''
 write('reports/FOURCASTDEN_SIX_HOUR_COMPARISON.md',comparison)
 drvtable='|日期|UTC小时|作者F107|作者F107A|作者Kp|GFZ桶Kp|GFZ daily Fobs|GFZ中心81日Fobs|\n|---|---:|---:|---:|---:|---:|---:|---:|\n'
 for r in driver['rows']:drvtable+=f"|{r['date']}|{r['hour_UTC']}|{r['author_f107d']:.6f}|{r['author_f107a']:.6f}|{r['author_Kp']:.6f}|{r['GFZ_Kp'] if r['GFZ_Kp'] is not None else 'N/A'}|{r['GFZ_daily_Fobs'] if r['GFZ_daily_Fobs'] is not None else 'N/A'}|{r['GFZ_centered81_Fobs'] if r['GFZ_centered81_Fobs'] is not None else 'N/A'}|\n"
 geo=f'''# 地磁活动增强窗口条件比较（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY

## 外部选择和实际输入

Mar24按先验GFZ UTC00/03/06 Kp7.333/8/6.333（def、CCBY4.0）预注册，未看模型误差挑日期。实际作者NPZ 00—07 Kp7.15、7.25、7.4167、7.65、7.8833、7.7167、7.15、6.5833。Jan4 00—07为3.35、3.7833、4.1167、4.35、4.5833、4.6333、4.5、4.3667；它是普通工程基准，不称地磁安静对照。两窗同01UT初始化，同6目标lead；季节、太阳条件、初始状态与前期演化没有控制，不能作单因素地磁因果实验。

{drvtable}

GFZ三小时Kp按UTC桶列出，不拿它替代作者小时插值。作者Mar24 f107d152.64—154.94，GFZ同日observed Fobs157.5；作者f107a157.894→157.718，本地GFZ完整中心81日平均158.67654。不同约定/时点/处理链未完全恢复，不能宣称逐点一致或自行修正。原数据/冻结统计原样输入，driver_comparison.json保留源SHA与计算约定。Jan4同期GFZ不在已有本地支持范围，保持N/A，没有为报告额外下载。sfeps/SEA由官方时间与坐标计算，LBC和磁辅助也按作者原路径给定；这些未来条件不是由AI预报的。

## 条件表现

Jan4 +6h near组Direct1.239%、Flow1.477%、log1.336%、History1.555%；Mar24分别4.273%、4.359%、3.907%、4.045%。四组增强窗口终点相对误差更大约2.6—3.5倍，但这不是“磁暴使误差增大若干倍”的因果估计。更大误差在第1小时已存在；其6h/1h倍率反而低于Jan4，不能据此说活动窗口更稳定。

Mar24误差接近末段仍增长而作者Kp在04后下降，图上可见阶段变化，但只有6个lead、驱动和状态高度相关，也受递归累积影响，不能估计物理响应时延。near组第三步剔除中位超过500km的22层，跨lead变化还含分组变化；固定upper20—28均使用不变压力索引，补充结果同样显示末期误差更大。

History Mar24 +2—4h near组最低，+6h极区最大相对差约33.64%（其他约34.83—38.22%），但全层绝对DEN误差仍最大。log在Mar24晚期多数指标较好，在Jan4不优于Direct；不能据单个增强窗口选最终模型或据短时五窗完全排除History。极区局地差很大但密度仍有限正值，不混淆相对参考残差和数值发散。

未来还需更多按独立驱动选定的强活动/普通日期、不同季节与初始相位、历史可用条件协议、独立观测密度、固定评价和不使用2023调参。只两窗，没有统计显著性或全年结论，更不代表最终卫星轨道精度。
'''
 write('reports/FOURCASTDEN_GEOMAGNETIC_WINDOW_COMPARISON.md',geo)
 # Directory-only future plan; never fetch those members here.
 inv={x['name']:x for x in json.loads((ROOT/'logs/test_archive_inventory.json').read_text())};from datetime import datetime,timedelta
 future=[]
 for d in DATES:
  for lead in [12,24]:
   members=[]
   for h in range(lead+2):
    n=(datetime.fromisoformat(d)+timedelta(hours=h)).strftime('%Y_%m_%d_%H%M%S.npz');assert n in inv;members.append(dict(name=n,already_present=h<8,**{k:inv[n][k] for k in ['bytes','compressed','crc']}))
   future.append(dict(date=d,lead_hours=lead,missing_members=[x['name'] for x in members if not x['already_present']],missing_compressed_bytes=sum(x['compressed'] for x in members if not x['already_present']),members=members))
 dump(F/'long_horizon_data_plan.json',dict(status='DESIGN_ONLY_NO_DOWNLOAD',plans=future))
 decision='''# FourCastDEN长时效研究决策（2026-10-22；只设计）

## 当前可以与不能做的判断

两窗8个连续6h序列工程完成，任意步反馈/毒化/严格权重与匹配统计/物理空间指标通过。无非有限值或非正密度；误差增长明显且有变量局部下降，条件排序变化。支持设计下一步12h，不保证12/24h准确或物理稳定。当前没有12/24h执行许可，任务结束停止。

下一项优先同Jan4与Mar24、同01起点、同4官方变体的12h连续受限研究，完整保留History：它在Mar24高层有条件优势，不能依据旧季节窗排除。Direct/log是值得关注的候选但不是最终模型；Flow仍作重要增量对照。12h通过逐步finite/positive、反馈、物理范围、独立指标和资源门禁后，才另授权24h。若失败保留前缀，不重置真实物理状态、不剪裁或重试。

## 数据和资源（未来估计，不是本次授权）

同t0=01，12h需要00—13（14帧），每窗已00—07，缺08—13各6帧，合计12新NPZ；24h需要00—次日01（26帧），若直接从当前库存计算每窗缺18，合计36；若先补12h并通过，则每窗再补14—次日01各12，合计24。long_horizon_data_plan.json只检查既有官方中央目录成员存在/压缩大小/CRC，未来内容未CRC/SHA验证、未下载。

12h建议请求网络40MiB、GPU600s、RAM4GiB、新增1.5GiB；24h须另做资源预估，可能需要网络90MiB、新增3GiB的独立授权。依据当前6h约392MiB数据/39.7s监督作粗线性与I/O外推，不是实测，不保证预算内；运行前按真实成员/存储方案和小预检复核，若超预算停止，不能默认提高。

任意步检查器支持L，但未来新长度仍要新CPU毒化、两帧历史滑窗、future aux/标量对应测试；6h证明不能代替24h。不得在中途按真值纠偏。原统计/权重和公开测试集不用于调参，模型排序按预注册指标/场景而非挑残差最小日期。

## 优先研究问题

1. 多步误差：连续6h支持研究多步训练/暴露偏差假设，但需要独立训练/验证集，不能由两窗证明某个训练方案有效。应同时报告绝对误差、增长倍率、逐层/区域及持续性，不只优化末时效。
2. 分层/相对损失：全层绝对RMSE偏低层，高层相对表现与其不同，支持预注册上层/相对/log目标；原static_log模型并未在所有条件改善，不说明简单log开关必然有效。层权重/混合参数不能用这批2023测试拟合。
3. History：继续核查作者训练配置、历史辅助排列/标准化协议、checkpoint与原训练日志的一致性；当前按公开源码接口没有发现错误，Mar24有真实条件优势，不能因绝对指标较差就改统计或teacher forcing。需要更多独立强活动日期复核。
4. 完整训练复现仍缺原训练入口（README只提供推理）、2000—2021训练与2022验证清单和内容、预处理/统计来源、模型目标/损失/采样、优化器调度、种子/多次训练日志与资源预算。checkpoint含optimizer状态不等于训练流程可复现。

## 第三阶段轨道接入门禁

AI对TIE-GCM参考场的拟合、独立真实大气密度精度、最终卫星轨道精度、端到端效率分别验证。AI输出Z为位势高度，不是ZG；每小时输入/输出不等于S7十分钟；未来真实ZG不能偷偷作为AI独立预测的几何界面。需验证Z/ZG/外部高度、时间插值与密度查询、未来驱动可得性；保留EXTERNAL_DATUM_UNVERIFIED。还需Swarm真实Cd/有效面积/姿态/推力、共同力模型截断/星历/其他摄动及独立观测/轨道验证。

效率研究须同域/时间/hardware/输入条件，将数据生成、预处理、训练/离线场、在线查询、轨道积分分别统计；本轮网络事件和TIE仿真墙钟不能直接作整体加速比。只提出后续方案，本次不训练、不做新TIE/RK45、不延长预测。
'''
 write('docs/FOURCASTDEN_LONG_HORIZON_DECISION.md',decision)
 print('Wrote 3 reports and long-horizon design; no new forward/download')
if __name__=='__main__':main()
