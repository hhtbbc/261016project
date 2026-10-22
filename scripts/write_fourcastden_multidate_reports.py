"""Evidence-derived five-window reports; no inference or parameter selection."""
import json,csv
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
from run_fourcastden_multistep import sha
F=ROOT/'experiments/fourcastden_multidate_v1'
def write(name,text):
 with (ROOT/name).open('x') as f:f.write(text.rstrip()+'\n')
def main():
 a=json.loads((F/'analysis.json').read_text());rt=json.loads((F/'runtime.json').read_text());s=json.loads((F/'supervision.json').read_text());dl=json.loads((F/'download.json').read_text());ls=json.loads((F/'log_DEN_static.json').read_text());days=a['initial_windows'];win=a['windows'];agg=a['aggregate'];drivers=a['drivers'];rec=rt['records'];checks=a['independent_metric_checks']
 def w(d,h,m):return next(x for x in win if x['date']==d and x['hour']==h and x['model']==m)
 # Clarify raw timing flag without changing original runtime evidence.
 scope=dict(first_forward_cold_this_model_field='Raw field indicates first invocation of that checkpoint; not necessarily cold process kernels',actual_process_first_forward='2023-03-23_Direct step1',Flow_first_window='First invocation with Flow weights but CUDA kernels already used by Direct; not globally cold',offline_costs_not_counted_as_GPU_network='Download, hashing, compressed result I/O and CPU metric/hook overhead separately accounted',strict_throughput_benchmark=False)
 with (F/'timing_scope.json').open('x') as f:json.dump(scope,f,indent=2)
 lines=[f'''# FourCastDEN多日期工程与数值验证（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 固定样本与历史保护

新增2023-03-23、06-21、09-23、12-21各00→01→02 UTC；日期由用户/预注册提前确定，不依新误差替换。Jan4仅读取旧Direct/Flow结果，不重放。实验experiments/fourcastden_multidate_v1；原始样本data/raw/fourcastden_multidate_v1；8个新预测数组data/processed/fourcastden_multidate_v1，仅本地保存。

执行前main本地/远端均为1d558c3852ccf7f02b30fcbda6426e57255d1fba，工作区原为干净。保护清单继承前两轮原始源码、Linux运行副本、四权重、static/static_log、Jan4样本及历史结果；预先逐SHA核验，最终交付audit再次核验。没有模型/数据安装或已有资产重下载。

## HTTP Range与数据合法性

先检查已有官方2023.zip中央目录，再远程读取ZIP中央目录确认同12成员的尺寸/压缩方法/CRC和实际header_offset。复用fetch_minimal_test_window.py的seek+Range方法，抽成无历史顶层副作用的BoundedRemoteZip；原下载脚本不改。每次强制206、精确Content-Range和限长body，200或范围不匹配时不读body即停止，预算前置检查，zipfile逐成员校验CRC。12文件SHA和全部请求见download.json，外层ZIP成员CRC及NPZ读入完整，没有宣称全年ZIP的MD5验证。

实际传输{dl['transfer_body_bytes']:,}字节（{dl['transfer_body_bytes']/2**20:.3f}MiB）<100MiB，用时{dl['wall_s']:.3f}s；仅12个新NPZ，无Jan4重下载，无18GB整包。原始文件独占创建、校验后设只读。数据检查14键、TN/UN/VN28lev、WN/Z/ZG/DEN/NE29ilev、3个下边界1×36×72和3个标量；36×72网格、finite、|x|>1e30哨兵拒绝、DEN/TN正、ZG逐列递增通过。

NPZ本身不包含经纬/压力坐标数组或单位属性，不能独立从其元数据证明坐标基准。模型使用原作者不可变static的lat/lon/lev/ilev；形状、训练统计、作者读取约定匹配。单位依据原UNIT_VARS和实际未SI换算代码：DEN g/cm3→kg/m3乘1000，风cm/s及Z/ZG cm→SI乘0.01。Z为位势高度，ZG为几何高度；不混为固定450km。

## 模型、序列与公平性

官方Direct和Flow各严格加载一次checkpoint，再各复用同一已加载网络处理四个独立序列；每序列重新用该窗00时初始化，非跨日期连续演化。AFNONet64,695,744参数、177二维输入/171输出/4标量、history0、2步、普通static、log_DENfalse、FP32且TF32关闭。Direct checkpoint SHA212187479c2df3ead151ec339683198f9e0632e23b892ac4d829ce1048724efb；Flow cc88b4bbee4d70b7a49c94ae3a8127768c1529368abbd7d5f76018d0166a3021。历史与本次config SHA、每窗数据SHA、结果SHA完整保存，无strict=False。

执行8次独立序列、16次实际forward，各两步的hook检查通过；Direct反馈预测状态，Flow归一化增量加到当前归一化状态后反馈。第二步未使用01时真实171状态；目标辅助和驱动按作者方法给定，故为HINDCAST。每个新日期Direct/Flow real、means/stds、climatology、辅助通道及标量逐元素相同。 公共YAML的date_time是继承作者CLI的未使用字段；本入口直接调用inference(ic)，真实起点由已核查的dataset.epochs三帧索引决定，不通过CLI日期减72小时逻辑。实际日期/文件/初态均逐窗记录，不能把遗留CLI字段当作实际运行日历。作者日志“包含12小时past history”实际指目录有12个样本，真正n_history=0；索引切片逐窗核查只有3个连续小时，未跨季节间隙取相邻时步。

## 自动化与独立数值验证

206项测试通过，既有Direct/Flow实际作者循环合成反馈、防未来物理真值泄漏、增量数学及新Range拒绝/预算/长度/CRC/样本契约全部通过；合成测试不作真实预测。8次GPU序列均成功，无重试，无新增Jan4预测。所有预测finite、DEN100%正、TN正，无裁剪/补0/后校正。各变量偏差/极值见summary.csv。

5窗×2模型×2时效全部171通道独立NumPy重算cos纬度加权RMSE和气候态ACC。最大RMSE相对差{max(c['max_RMSE_relative'] for c in checks):.3e}，ACC最大绝对差{max(c['max_ACC_absolute'] for c in checks):.3e}，满足原预注册rtol2e-5/ACC atol2e-6。加权均值与另一种加权sum/总权重RMSE实现一致；最终独立audit还会重算ACC及CSV。零异常范数分母应记N/A，不通过调阈值制造PASS。

## 资源与计时口径

唯一监督GPU进程树墙钟{s['wall_s']:.3f}s<600，监督峰RSS{s['peak_tree_RSS_bytes']/2**30:.3f}GiB<4，无超限、遗留失败或自动重试。子进程记录GPU阶段总墙钟{rt['GPU_wall_s']:.3f}s，包含模型加载、网络、指标、hooks、SHA及数组压缩等CPU/I/O；这不是纯GPU运算时间。子进程启动前的历史SHA检查/导入等计入监督墙钟，因此两个口径不同。

本次A10080GB、torch{rt['torch']}、CUDA runtime{rt['cuda']}，新增文件总量由delivery_audit.json核算，250MiB限额。模型加载Direct {rec[0]['model_load_s']:.6f}s，Flow {rec[4]['model_load_s']:.6f}s。进程第一次Direct forward {rec[0]['GPU_forward_ms'][0]:.6f}ms；余15个GPU事件约{min(v for i,r in enumerate(rec) for j,v in enumerate(r['GPU_forward_ms']) if (i,j)!=(0,0)):.3f}—{max(v for i,r in enumerate(rec) for j,v in enumerate(r['GPU_forward_ms']) if (i,j)!=(0,0)):.3f}ms。

Flow的首次模型调用已受Direct共享CUDA内核预热，raw字段first_forward_cold_this_model仅表示该checkpoint首次调用，不代表进程全冷；timing_scope.json专门澄清。没有额外warm-up/重复吞吐测量，不能把Direct第一窗冷事件与Flow暖事件比较后宣称Flow加速。每窗读取/预处理、作者循环（包括再次读取/metrics/hooks）、网络事件、推理峰显存及加载费用逐记录保存。

## 静态log-DEN审查

已校验官方log-DEN权重SHA{ls['checkpoint_sha256']}，CPU weights_only读取150个model_state条目、输入177通道，与官方对应结构一致；static_log DEN统计29层有限且std正。只读检查，无网络构造或forward。官方numpy.power(10, CUDA Tensor)反变换分支仍有兼容性风险，未经动态验证，不能声称该变体已经可正式推理。后续须隔离受审补丁/包装器及合成测试，不改原作者树。5窗三帧已备齐，log两步无需新数据；history两步仍需每窗前一小时或共同t0调整。

## 可重复命令与边界

source scripts/activate310.sh；python -m unittest discover -s tests；run_fourcastden_multidate.py静态、--fetch；supervise_fourcastden_multidate.py唯一一次；analyze_fourcastden_multidate.py；inspect_fourcastden_log_static.py；write_fourcastden_multidate_reports.py；audit_fourcastden_multidate.py。所有正式入口独占创建并拒绝旧标签重跑。未训练、未微调、未扩6/12/24h、无新TIE或卫星轨道积分。当前完成后停止，新的科学验证需另授权。
''']
 write('reports/FOURCASTDEN_MULTIDATE_VALIDATION.md',''.join(lines))
 lines=['''# 五日期Direct/Flow小规模泛化检查（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 统计单位与共同结论

新增四个日期与Jan4共5个初值，窗口为统计单位；每窗只2小时，所有t0均00 UTC。下述是对TIE-GCM模拟参考场的误差，不是独立观测精度，不是全年表现或显著性结论。不以格点数量放大样本量。持续性两个目标都固定各窗00时真状态，模型/参考/掩码/单位相同。

Flow在5窗两个时效的TN/VN/Z平均逐层RMSE均较低；第一小时UN/WN也是5/5窗较低。第二小时UN/WN分别4/5窗Flow较低：12月UN和1月WN由Direct较低。DEN第一小时Flow 3/5窗较低，但第二小时Direct 5/5窗较低。不能把不同变量单位混合投票得总体架构排名。

|时效h|变量|Flow平均层RMSE较低的窗口数|Direct较低|等窗平均Direct RMSE|等窗平均Flow RMSE|
|---:|---|---:|---:|---:|---:|''']
 for r in agg:lines.append(f"|{r['hour']}|{r['variable']}|{r['Flow_lower_RMSE_windows']}/5|{r['Direct_lower_RMSE_windows']}/5|{r['equal_window_mean_Direct_RMSE']:.6g}|{r['equal_window_mean_Flow_RMSE']:.6g}|")
 lines.append('''
单位TN K、风m/s、Z m、DEN kg/m3；先逐原生压力层计算作者加权RMSE，再层间等权平均，最后日期等权平均。单日期/每层/ACC/偏差/极值均保留CSV，不仅报告跨日均值。

## DEN：低层绝对量级与上层相对指标

下表均为第二小时；upper固定原生ilev数组20—28（坐标3—7）的逐层相对RMS算术平均。近400—500km组采用每个目标参考ZG全球中位落入该范围的原生层，再平均逐层相对RMS；层数/索引/实际中位见windows.csv，不能称固定几何高度误差。

|日期|Direct DEN平均层绝对RMSE kg/m3|Flow同指标|Direct近400—500组相对RMS %|Flow同指标 %|Direct顶层P95 %|Flow顶层P95 %|
|---|---:|---:|---:|---:|---:|---:|''')
 for d in days:
  x=w(d,2,'Direct');y=w(d,2,'Flow');lines.append(f"|{d}|{x['mean_DEN_layer_RMSE_kg_m3']:.6g}|{y['mean_DEN_layer_RMSE_kg_m3']:.6g}|{x['near400_500_mean_relative_RMS']*100:.6f}|{y['near400_500_mean_relative_RMS']*100:.6f}|{x['top_relative_P95']*100:.6f}|{y['top_relative_P95']*100:.6f}|")
 lines.append('''
这5窗两个时效，Flow在固定上层组和近400—500参考中位高度组的平均相对RMS/log RMS均较低；这与第二小时Direct全层平均绝对RMSE较低并不矛盾，底层密度大、绝对误差权重大。不能据此把某架构判定为真实高层大气更准确。顶层P95也不是所有日期/层均由Flow占优：9月和12月第二小时顶层P95略高于Direct，见表；需保留层/区域细节。

## 增长、偏差与异常

两模型在每个日期的六变量平均逐层RMSE都从第1小时增至第2小时（各30/30变量-日期）；但不等于每个格点或每层都增加。固定上层相对RMS第2/1小时倍率Direct约1.47—1.65，Flow约1.64—1.91，Flow在5窗增长倍率均更大，即使第二小时绝对相对RMS仍低于Direct。不能由2个预测目标估计长期增长率或证明多步漂移规律。

全部8新序列/历史两序列均有限且DEN正；没有发现需要停止的非物理输出。极区abs(model lat)>=60°，最大的原生点相对差出现在Jan4 +2h的顶层，Direct约2.940%、Flow约2.776%；新日期也保留全部极区/非极区/全局相对P95、最大值、log偏差。单个极区最大差不等于整体模型发散。没有依据先验阈值把某日期剔除。log偏差有空间/层变化，仅2h不足以确认长期系统漂移。

## 实际外部驱动与地磁解释

逐三帧原始驱动及SHA见drivers.csv。以下列出00→01→02的实际作者NPZ输入，不是由网络预测出的未来条件：

|日期|F10.7（sfu）三时刻|F10.7A（sfu）三时刻|Kp三时刻|
|---|---|---|---|''')
 for d in days:
  rr=[r for r in drivers if r['date']==d];lines.append(f"|{d}|"+'|'.join(', '.join(f"{x[k]:.3f}" for x in rr) for k in ['f107d','f107a','Kp'])+'|')
 lines.append('''
Mar23为已有GFZ整日增强候选（当日稍后Kp达7，Mar24达8），但本次00—02时作者输入仅0.5—0.867，不能称强磁暴窗口验证。作者NPZ驱动与GFZ原始3h定义/插值不必逐点相同，未替换/平滑原数据以强行一致。其余日期仅季节锚点，本次Kp输入总体0.5—4.117，F10.7约144.7—189.6 sfu。五窗不能隔离季节/参考场/驱动的因果，也没有足够强活动样本支持磁暴泛化；不能根据误差变化反推太阳活动原因。

## 性能与读写成本

本次8序列同一进程执行，Direct先、Flow后，两个模型各加载一次；不把加载后复用解释成独立冷启动8次。每窗独立初始化，但共享GPU内核/文件缓存。逐窗表如下，单独read测量不含入作者loop重复读/指标/hooks：

|序列|独立read/preprocess ms|作者循环 s|第1/2 forward GPU ms|推理allocated峰 MiB|
|---|---:|---:|---|---:|''')
 for r in rec:lines.append(f"|{r['tag']}|{r['read_preprocess_s']*1000:.3f}|{r['author_loop_metrics_hooks_s']:.6f}|{r['GPU_forward_ms'][0]:.3f}/{r['GPU_forward_ms'][1]:.3f}|{r['peak_allocated_bytes']/2**20:.3f}|")
 lines.append(f"\n模型加载Direct/Flow分别{rec[0]['model_load_s']:.3f}/{rec[4]['model_load_s']:.3f}s。监督全墙钟{s['wall_s']:.3f}s、峰RSS{s['peak_tree_RSS_bytes']/2**30:.3f}GiB，传输{dl['transfer_body_bytes']/2**20:.3f}MiB/下载{dl['wall_s']:.3f}s。GPU阶段19.099s包括记录SHA/压缩等CPU I/O；网络事件不是总成本。Flow首次调用已共享Direct的内核预热；不能将151ms对19ms当模型加速倍数，严格吞吐实验另设计，不在本次增加warm-up。\n")
 lines.append('''
## 数据文件与图表索引

- results/metrics/fourcastden_multidate_v1_layers.csv：5130行变量/原生层/日期/时效/模型指标。
- 同前缀summary.csv：180行变量汇总；density_layers.csv：2610行区域/层相对与log指标；windows.csv：30行窗口密度指标；drivers.csv：15行实际输入；paired.csv：60行逐变量对照；aggregate.csv：12行等窗统计。
- results/figures/fourcastden_multidate_v1_variables.png：六变量跨日期RMSE。
- 同前缀DEN_layers.png：分层相对误差；growth.png：误差增长；near400_500.png：原生层组对照。
- 同前缀density_maps.png：两模型第二小时逐日相对误差，参考ZG邻450km原生层，各图标实际中位/层索引，无固定高度外推。
- 同前缀drivers_errors.png：实际三时刻驱动与上层误差；performance.png：读取/网络/循环计时。
- experiments/fourcastden_multidate_v1/：配置、Range/CRC/SHA、运行、静态log-DEN、独立audit JSON。

## 工程事实与研究边界

工程/数值：合法12样本、8个两步序列、防真值泄漏、相同条件、独立指标与资源门禁通过。多日期观察：Flow的部分变量及上层相对误差优势跨5窗存在，Direct的第二小时DEN绝对指标跨5窗较低；优势依指标/层/时效而变。未证明：全年泛化、强磁暴稳定性、长时预测、训练目标因果优势、独立真实大气精度和最终卫星轨道精度。

优先改进假设：分层/相对或log密度目标值得验证；多步训练可能减少上层倍率增长，但当前没有足够长序列证明系统漂移或确认最佳训练方案。不得用2023窗口拟合统计、调权重或训练；下一步先补官方log-DEN变体和条件更强/更长窗口的预注册，详见NEXT_EXPERIMENT_DECISION。
''')
 write('reports/FOURCASTDEN_MULTIDATE_COMPARISON.md','\n'.join(lines))
 print('Two reports written from real data; no models executed.')
if __name__=='__main__':main()
