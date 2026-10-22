"""Render reports from real log-DEN and historical Direct/Flow evidence."""
import json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'experiments/fourcastden_logden_multidate_v1'
def write(p,s):
 with (ROOT/p).open('x') as f:f.write(s.rstrip()+'\n')
def main():
 a=json.loads((F/'analysis.json').read_text());rt=json.loads((F/'runtime.json').read_text());c=json.loads((F/'compatibility.json').read_text());sup=json.loads((F/'supervision.json').read_text());cond=json.loads((F/'condition_comparison.json').read_text());days=a['dates'];models=a['models'];agg=a['aggregate'];win=a['windows']
 def w(d,h,m):return next(r for r in win if r['date']==d and r['hour']==h and r['model']==m)
 compat=f'''# 官方log-DEN兼容性验证（2026-10-22）

## 实际发现

小张量而非真实模型先检查：CPU np.power(10,Tensor)可返回CPU Tensor，但经NumPy转换路径；CUDA相同调用明确TypeError：can't convert cuda:0 device type tensor to numpy。torch.pow(10,Tensor)保留FP32 dtype/device，CPU和GPU与独立NumPy float64（以同一float32指数为输入）最大相对差{c['devices']['cuda']['torch_pow']['max_relative_error']:.3e}<3e-7。溢出/下溢不裁剪，测试明确拒绝非有限或非正输出。formal输出的批量反变换也逐点复核，不把标准化log值当密度，不使用exp。

另有两个初始化/形状问题：原get_time_means拒绝static_log的(1,C,36,72)；原log分支pred(29,36,72)*std(29)在尾轴无法广播。实际CPU原循环测试出现RuntimeError，保留logs/fourcastden_logden_tests_initial_failure.log。保值去除气候态前导1维、逐层std/mean明确索引为(29,1,1)后，CPU逐通道NumPy等价测试通过。一次合成毒化用999把未来参考log指数推到溢出，保护门禁正确拒绝；失败日志tests_synthetic_overflow_failure.log保留，随后用仍可有限反变换的9改变未来真实物理状态，证明预测反馈不依赖它，另保留显式overflow/underflow拒绝测试。没有改变科学样本、预测或容差。

## 隔离补丁及数学边界

原始third_party/FourCastDEN、原Linux副本、AFNONet、官方权重和static_log原件均不改。仅在experiments/fourcastden_logden_multidate_v1/inference_overlay.py运行副本修改：

1. get_time_means绑定到src/fourcastden/logden.py::load_log_time_means，验证并reshape，不改值/dtype/顺序。
2. 使用的inference分支两处逐层仿射运算显式std/mean[den_idx,None,None]，实现作者本意逐通道标准化逆操作。
3. 两处np.power(10,Tensor)换torch.pow(10,Tensor)。无网络参数/结构/状态更新/其他物理变量方程改变。

完整diff compatibility.patch，源SHA `{c['source_SHA256']}`，最终覆盖层SHA `{c['overlay_SHA256']}`，补丁SHA `{c['patch_SHA256']}`。stage1文件保留为本次修复过程证据，不是可用最终版本。完整覆盖代码仅本地，Git保存补丁、生成器、助手模块与SHA；不声称未使用的其他log方法也已修复。

MetricTrace只在隔离模块包装原指标函数，原参数和返回值不变，捕获归一化RMSE及FP32物理DEN操作数以独立复核，不修改结果。真实自回归仍调用作者inference，第一步/第二步输出在标准化log空间直接反馈（flow=false）。

## 表示、单位和模型配置

原始NPZ的DEN依作者单位声明为g/cm3，dataset_tiegcm在归一化前np.log10(DEN)，匹配static_log：L=y*std_log+mean_log，rho(g/cm3)=10**L，rho(kg/m3)=rho*1000。其他TN/风/Z保持原物理表示及对应单位。log气候态指数恢复是几何均值，不是物理密度算术均值。

static_log不只是DEN统计不同：TN等均值/标准差/气候态也有差别（statistics_differences.json），必须各自匹配官方权重，不强制相同。三种作者预训练整体配置对照不是“只切换log开关”的训练消融，不能将性能变化全归因于表示。

官方Baseline_log_DEN_ckpt.tar SHA d314241ef9b91ba8e3405d77090b24ded03ceff361404f9ff5bd6212b828db18，严格加载150项state，{rt['parameters']:,}参数，同177输入/171输出/4条件AFNONet，history0/log_DENtrue/flowfalse/普通FP32/TF32false。215项全套测试通过，含实际隔离作者log_DEN=true CPU循环/防未来真值泄漏和指标捕获，无真实模型CPU额外预测。

## 评价空间

原返回RMSE对DEN在物理g/cm3，其余各自原单位；原DEN ACC在log标准化空间/自己的log气候态。原归一化RMSE和乘std后的原生RMSE另存，DEN后者单位dex，不与kg/m3混排。捕获原函数FP32物理DEN输入，用float64重算其RMSE满足预注册rtol2e-5/atol1e-25；原native ACC满足atol2e-6。没有用放宽容差掩盖问题。

公平指标另将三模型以各自官方统计float64反变换，全部与同一原始NPZ目标比较，密度kg/m3，使用同一普通物理气候态。旧Direct/Flow预测数组和报告不改；本轮与旧“归一化后还原参考”的指标存在微小舍入定义差。normalization_roundtrip保留初态/目标重建误差：log表示float32初态最大相对舍入约{max(r['initial_DEN_max_relative'] for r in a['normalization_roundtrip'] if r['model']=='LogDEN'):.3e}，这是官方表示精度，未用未来真值校正。

## 辅助条件与限制

原始初态、未来LBC和驱动使用同15个不可变文件，标量和磁通道逐元素相同。官方static与static_log坐标精度不同，SEA计算后的归一化差最大{max(r['SEA_max_abs'] for r in cond):.3e}；保留匹配官方计算，不强制改其中一套辅助或重新拟合统计。因这些数值/统计与权重差别，本次并非所有归一化张量相同的单因素消融。

focused CPU日志曾出现一次numpy.ndarray尺寸导入警告；未改变环境/忽略错误，正式GPU运行与完整215测试未因此失败，所有数值检查另有实际证据；原日志保留。只证明所用NPZ/AFNO路径通过，不声称所有可选扩展已兼容。
'''
 write('reports/FOURCASTDEN_LOGDEN_COMPATIBILITY.md',compat)
 val=f'''# 官方log-DEN五日期两小时验证（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 实际执行

Jan4、Mar23、Jun21、Sep23、Dec21各00→01→02 UTC全部成功，5序列/10真实forward。官方log权重严格加载一次后复用五窗，每窗重新从自己的00时真实状态开始；没有重跑Direct/Flow、没有下载、训练、扩窗、TIE或轨道积分。F/data_view仅15个已核验原文件的项目内软链接，实际目标逐一确认在工作区内，不是新增/修改原始数据。

完整配置config.yaml/保护SHA/preflight.json在experiments/fourcastden_logden_multidate_v1。15原始文件、static_log与其他原资产/历史结果最终audit逐SHA保护；每窗结果data/processed/fourcastden_logden_multidate_v1/YYYY-MM-DD.npz本地保存。补丁来源、完整diff和哈希见COMPATIBILITY报告。

## 初始状态与反馈

独立重算raw六变量与下边界的作者预处理，DEN先log10，使用官方对应均值/标准差，174通道与get_data逐元素匹配。Hook保存两次177二维输入、4标量和171输出，首输入为真实初态、第二次171通道逐元素等于第一次模型输出；没有01时真实状态反馈。每窗真实未来物理场仅评价，未来外部条件保留作者HINDCAST方法。原CLI date_time遗留字段未用于inference(ic)，实际epochs逐三小时核验。

所有五窗预测finite，TN正，DEN100%正，无裁剪/填零/指数修补或失败重试；各帧密度范围、形状、forward数、原生指标及结果SHA见逐日期runtime.json。作者normalized/native指标及共同物理评价分开，所有公式独立NumPy复核。真实数据科学准确度仍未由此验证。

## 资源

小CPU/CUDA兼容探针{c['compatibility_probe_wall_s']:.3f}s，无网络forward。正式监督墙钟{sup['wall_s']:.3f}s，两者合计小于600；子进程GPU阶段（含CPU指标/hooks、压缩与SHA等）{rt['GPU_phase_wall_s']:.3f}s，不是纯GPU计算。监督RSS峰{sup['peak_RSS_bytes']/2**30:.3f}GiB<4；加载分配显存峰{rt['loading_peak_allocated_bytes']/2**20:.3f}MiB；加载{rt['records'][0]['model_load_s']:.6f}s。

|日期|单独读取/预处理ms|作者循环含指标/hooks s|两次forward GPU ms|已有两帧输出pow10 GPU ms|推理峰显存MiB|
|---|---:|---:|---|---:|---:|
'''
 for r in rt['records']:val+=f"|{r['date']}|{r['read_preprocess_s']*1000:.3f}|{r['author_loop_metrics_hooks_s']:.6f}|{r['GPU_forward_ms'][0]:.3f}/{r['GPU_forward_ms'][1]:.3f}|{r['inverse_pow10_two_target_fields_gpu_ms']:.6f}|{r['peak_allocated_bytes']/2**20:.3f}|\n"
 val+='''
首次网络调用是冷启动；此后为复用同一模型/内核，没有额外warm-up或大量重复。pow10时间只针对已产生的两目标DEN指数张量，不是新forward，排除CPU→GPU传输和前面的仿射运算；作者循环本身另含预测和参考的反变换，不能直接将此微操作时间与总循环相加。数据读取在作者循环中也会发生，表中独立read是另一次测量。数据保存/压缩与SHA、审计开销在总阶段中，没有全归为网络推理。

## 可重复命令与停止

source scripts/activate310.sh；check_fourcastden_logden_compatibility.py建立隔离副本；python -m unittest discover -s tests（215）；run_fourcastden_logden_multidate.py静态；supervise_fourcastden_logden.py唯一正式GPU工作进程；analyze_fourcastden_three_models.py离线公平评价；write_fourcastden_logden_reports.py；audit_fourcastden_logden.py。所有科学输出独占创建，不得重用本标签覆盖；复现实验应另行授权和新标签。Direct/Flow只用原有数组，三模型原始数据/权重均不变，完整报告/CSV/图见THREE_MODEL_COMPARISON。
'''
 write('reports/FOURCASTDEN_LOGDEN_VALIDATION.md',val)
 lines=['''# 三个官方模型：五日期两小时密度对照（2026-10-22）
HINDCAST / common raw physical TIEGCM reference / NO_TRAINING

## 共同物理空间协议

Direct/Flow读取历史数组，只有log-DEN新增五个两小时序列。各自保留官方checkpoint/匹配统计，全部输出反变换到同一物理表示。目标统一为原始NPZ物理场（不是各模型归一化再还原的近似目标），DEN kg/m3；气候态固定普通static/time_means物理值。统一cos纬度RMSE/ACC、全部有效原生格点、自然ln密度比误差；无后校正。旧报告不覆盖。原作者log空间ACC和dex指标单独CSV，不参与物理指标排名。

5个初值等权，不能以格点制造显著性。所有t0均00 UTC，未来真实外部条件已知；本次不是全年/强磁暴或实时独立预报。三模型权重及统计不同，只对照官方整套预训练配置，不能认定性能差就是单一log开关因果。

## 核心结果：预期没有得到支持

第二小时log-DEN在5/5窗全层平均绝对DEN RMSE最低；但两个时效、5/5窗固定上层(index20—28)及参考ZG全球中位400—500km原生层组的平均相对RMS均高于Direct和Flow，Flow该指标在所有五窗最低。**本次没有证据表明官方log-DEN改善了高层相对误差。** 不能只报告绝对RMSE改善。

## 第二小时逐窗密度

“全层”是先逐压力层RMSE再算术平均，非所有高度混合RMSE；近400—500组是参考中位高度定位原生层，非固定450km几何剖面。

|日期|模型|全层平均绝对RMSE kg/m3|近400—500组相对RMS %|同组自然log RMS|顶层相对P95 %|
|---|---|---:|---:|---:|---:|''']
 for d in days:
  for m in models:
   r=w(d,2,m);lines.append(f"|{d}|{m}|{r['mean_DEN_layer_RMSE_kg_m3']:.6g}|{r['near400_500_mean_relative_RMS']*100:.6f}|{r['near400_500_mean_log_RMS']:.7g}|{r['top_relative_P95']*100:.6f}|")
 lines.append('''
第一小时全层DEN绝对指标最低的窗数：log-DEN3、Direct1、Flow1；第二小时log-DEN5，其余0。底层相对RMS第二小时log模型在4/5窗较低，但12月并非；上层未改善，未显示普遍层间相对误差均衡。极低密度顶部P95也无稳定log优势，逐层/极区数据完整保留，不删除不利层。

## 其他物理变量的代价

下表第二小时等窗平均逐层RMSE；每变量单位独立，不相加。

|变量|SI单位|Direct|Flow|log-DEN|
|---|---|---:|---:|---:|''')
 for n,u in zip(['TN','UN','VN','WN','Z','DEN'],['K','m/s','m/s','m/s','m','kg/m3']):
  r=next(r for r in agg if r['hour']==2 and r['variable']==n);lines.append(f"|{n}|{u}|{r['Direct_equal_window_mean_RMSE']:.7g}|{r['Flow_equal_window_mean_RMSE']:.7g}|{r['LogDEN_equal_window_mean_RMSE']:.7g}|")
 lines.append('''
log模型没有在任一日期/时效取得TN/UN/VN/WN/Z平均逐层RMSE的三者最小值。第二小时等窗均值TN/Z较Direct约高18.9%/20.6%，并未用密度改善掩盖其他变量代价；这不是统计显著性声明，也不能全部归因于log变换，因非DEN统计与训练权重也不同。

## 误差增长、指数与稳定性

三模型所有日期六变量平均逐层RMSE都从第1h增到第2h；每个格点或层不必如此。固定上层相对RMS的两步倍率：Direct约1.47—1.65，Flow1.64—1.91，log-DEN1.50—1.68。log增长倍率小于Flow不等于绝对误差更小，其第一小时起点已经更高。仅两个目标不能证明长时递归稳定性、无漂移或长期指数放大。

log所有预测密度有限正值、无溢出/下溢或裁剪，不等于已经更准确；正性部分来自指数表示本身。指数反变换与NumPy参考相符，顶层/极区误差是保留的科学残差，没有因异常图形修改输入/结果。上层自然log偏差不同日期可正可负，短例不足以认定系统性长期漂移。

## 驱动、统计与精度限制

三者实际F10.7/F10.7A/Kp与未来下边界来自同15个原始样本。数值标量与磁辅助逐元素一致；SEA因官方static的坐标dtype不同，归一化差最大约1.07e-6，保留作者匹配路径，未强制替换输入。static_log非DEN统计也不同，statistics_differences与roundtrip记录保留。log初态密度的float32表示往返约数ppm，普通模型约0.04ppm；本轮公共目标不随模型改变，也不利用未来参考校正预测。

五日期Kp范围仍约0.5—4.117，Mar23 00—02仅0.5—0.867；不能把候选整日的后来磁暴当此窗口已覆盖。5窗季节/驱动/参考变化混杂，不能建立因果关联或全年优越性。对TIE-GCM参考的拟合精度、独立观测大气精度及最终轨道精度三者严格区分，正式Swarm参数/高度/预热和受力门禁不变。

## 资源与成果索引

兼容/正式监督总墙钟小于18秒，峰RSS约1.11GiB，未下载新数据。log加载约1.335s，首forward152.260ms，其余约18.64—19.62ms；两目标输出pow10约0.067—0.082ms。旧Direct/Flow计时来自不同进程、冷启动、加载/缓存状态与审计开销，不能直接宣称模型吞吐优势。完整performance.csv分别保留读取、加载、网络事件、循环和反变换口径；严格重复吞吐方案仅设计，未增加warm-up。

- results/metrics/fourcastden_three_model_v1_layers.csv：6840行公共物理逐层RMSE/ACC。
- 同前缀summary.csv：240行变量汇总；density_layers.csv：3480行区域相对/log指标；windows.csv：40行窗口密度指标。
- 同前缀author_native_logden.csv：1710行作者原指标、标准化RMSE与dex指标；paired.csv/aggregate.csv：逐窗与等窗对照；performance.csv：15行来源明确的历史/本次计时。
- results/figures/fourcastden_three_model_v1_near400_500.png、DEN_layers.png、variables.png、growth.png、top_polar.png、performance.png：6张真实数据图。
- experiments/fourcastden_logden_multidate_v1/analysis.json及delivery_audit.json：原生指标复核、共同评价、往返误差、保护SHA和资源。

下一步建议先补齐官方history公平基线，再独立授权6h增长检查，之后考虑12/24h。log/逐层相对损失仍是待检验训练假设，本次预训练配置并未支持“log必然改善高层”的主张；不得根据2023测试调参后反称独立泛化。详见NEXT_EXPERIMENT_DECISION最新节。本次停止，不训练或轨道积分。
''')
 write('reports/FOURCASTDEN_THREE_MODEL_COMPARISON.md','\n'.join(lines))
 print('Compatibility, validation and three-model comparison reports generated.')
if __name__=='__main__':main()
