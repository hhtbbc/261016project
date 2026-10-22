# 官方log-DEN兼容性验证（2026-10-22）

## 实际发现

小张量而非真实模型先检查：CPU np.power(10,Tensor)可返回CPU Tensor，但经NumPy转换路径；CUDA相同调用明确TypeError：can't convert cuda:0 device type tensor to numpy。torch.pow(10,Tensor)保留FP32 dtype/device，CPU和GPU与独立NumPy float64（以同一float32指数为输入）最大相对差4.636e-08<3e-7。溢出/下溢不裁剪，测试明确拒绝非有限或非正输出。formal输出的批量反变换也逐点复核，不把标准化log值当密度，不使用exp。

另有两个初始化/形状问题：原get_time_means拒绝static_log的(1,C,36,72)；原log分支pred(29,36,72)*std(29)在尾轴无法广播。实际CPU原循环测试出现RuntimeError，保留logs/fourcastden_logden_tests_initial_failure.log。保值去除气候态前导1维、逐层std/mean明确索引为(29,1,1)后，CPU逐通道NumPy等价测试通过。一次合成毒化用999把未来参考log指数推到溢出，保护门禁正确拒绝；失败日志tests_synthetic_overflow_failure.log保留，随后用仍可有限反变换的9改变未来真实物理状态，证明预测反馈不依赖它，另保留显式overflow/underflow拒绝测试。没有改变科学样本、预测或容差。

## 隔离补丁及数学边界

原始third_party/FourCastDEN、原Linux副本、AFNONet、官方权重和static_log原件均不改。仅在experiments/fourcastden_logden_multidate_v1/inference_overlay.py运行副本修改：

1. get_time_means绑定到src/fourcastden/logden.py::load_log_time_means，验证并reshape，不改值/dtype/顺序。
2. 使用的inference分支两处逐层仿射运算显式std/mean[den_idx,None,None]，实现作者本意逐通道标准化逆操作。
3. 两处np.power(10,Tensor)换torch.pow(10,Tensor)。无网络参数/结构/状态更新/其他物理变量方程改变。

完整diff compatibility.patch，源SHA `f4594dfefc4e273175b946efb05fb99920acc2ca24f8dfa789d874e1b55b55c9`，最终覆盖层SHA `f1e8fd5acb61ae8fd06b01839ba4be2ffeb8b52385b819e2dc59faa9965d7e1d`，补丁SHA `d7ffa94cfd9576979b68edce1c011c3a7b6d7536847126503df6e2a5d403147c`。stage1文件保留为本次修复过程证据，不是可用最终版本。完整覆盖代码仅本地，Git保存补丁、生成器、助手模块与SHA；不声称未使用的其他log方法也已修复。

MetricTrace只在隔离模块包装原指标函数，原参数和返回值不变，捕获归一化RMSE及FP32物理DEN操作数以独立复核，不修改结果。真实自回归仍调用作者inference，第一步/第二步输出在标准化log空间直接反馈（flow=false）。

## 表示、单位和模型配置

原始NPZ的DEN依作者单位声明为g/cm3，dataset_tiegcm在归一化前np.log10(DEN)，匹配static_log：L=y*std_log+mean_log，rho(g/cm3)=10**L，rho(kg/m3)=rho*1000。其他TN/风/Z保持原物理表示及对应单位。log气候态指数恢复是几何均值，不是物理密度算术均值。

static_log不只是DEN统计不同：TN等均值/标准差/气候态也有差别（statistics_differences.json），必须各自匹配官方权重，不强制相同。三种作者预训练整体配置对照不是“只切换log开关”的训练消融，不能将性能变化全归因于表示。

官方Baseline_log_DEN_ckpt.tar SHA d314241ef9b91ba8e3405d77090b24ded03ceff361404f9ff5bd6212b828db18，严格加载150项state，64,695,744参数，同177输入/171输出/4条件AFNONet，history0/log_DENtrue/flowfalse/普通FP32/TF32false。215项全套测试通过，含实际隔离作者log_DEN=true CPU循环/防未来真值泄漏和指标捕获，无真实模型CPU额外预测。

## 评价空间

原返回RMSE对DEN在物理g/cm3，其余各自原单位；原DEN ACC在log标准化空间/自己的log气候态。原归一化RMSE和乘std后的原生RMSE另存，DEN后者单位dex，不与kg/m3混排。捕获原函数FP32物理DEN输入，用float64重算其RMSE满足预注册rtol2e-5/atol1e-25；原native ACC满足atol2e-6。没有用放宽容差掩盖问题。

公平指标另将三模型以各自官方统计float64反变换，全部与同一原始NPZ目标比较，密度kg/m3，使用同一普通物理气候态。旧Direct/Flow预测数组和报告不改；本轮与旧“归一化后还原参考”的指标存在微小舍入定义差。normalization_roundtrip保留初态/目标重建误差：log表示float32初态最大相对舍入约4.950e-06，这是官方表示精度，未用未来真值校正。

## 辅助条件与限制

原始初态、未来LBC和驱动使用同15个不可变文件，标量和磁通道逐元素相同。官方static与static_log坐标精度不同，SEA计算后的归一化差最大1.073e-06；保留匹配官方计算，不强制改其中一套辅助或重新拟合统计。因这些数值/统计与权重差别，本次并非所有归一化张量相同的单因素消融。

focused CPU日志曾出现一次numpy.ndarray尺寸导入警告；未改变环境/忽略错误，正式GPU运行与完整215测试未因此失败，所有数值检查另有实际证据；原日志保留。只证明所用NPZ/AFNO路径通过，不声称所有可选扩展已兼容。
