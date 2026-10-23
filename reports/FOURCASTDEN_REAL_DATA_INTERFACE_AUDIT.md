# FourCastDEN真实数据只读接口审计（2026-10-23）

READ_ONLY_TEST_INTERFACE / NOT_TRAINING / TIEGCM_REFERENCE_ONLY

## 实际执行与隔离

仅既有2023-01-04 00/01/02三个真实NPZ，只读CPU。没有实例化网络、加载checkpoint、执行模型forward/真实loss/backward/optimizer.step；没有新预测/训练/TIE/RK45/原数据下载。没有创建2023训练Dataset，只调用原EpochPairs验证其仍拒绝train/validation。独立inspect_pair不是Dataset，只返回shape/hash/比较证据，不返回可训练张量。

OfficialFrameSource直接复用作者TGCMDataset.get_data，默认普通static。官方参考不是另写公式：object.__new__构造不含网络的TGCMForecast，仅运行其原inference的输入拼接，在forecast边界捕获input/scalar后立即抛专用异常停止，绝不评估网络/指标。两组分别真实状态初始化；01→02不是旧自回归预测状态任务。00→01另与历史真实forward的input0/scalars0逐元素相同，旧预测不重跑。

|配对UTC|input|scalar|target|最大输入差|
|---|---|---|---|---:|
|2023-01-04T00:00:00+00:00 → 2023-01-04T01:00:00+00:00|[1, 177, 36, 72]|[1, 1, 4]|[1, 171, 36, 72]|0.0|
|2023-01-04T01:00:00+00:00 → 2023-01-04T02:00:00+00:00|[1, 177, 36, 72]|[1, 1, 4]|[1, 171, 36, 72]|0.0|


每组当前171state、下一小时3LBC/SEA/磁纬磁经六aux拼177；4scalar f107d/f107a/Kp/sfeps为目标时刻，171truth单列只检查目标。所有通道/标量/目标逐元素差0。TN/UN/VN各28、WN/Z/DEN各29，共171；输入维36×72。原文件名和源码约定为UTC，作者dataset epochs本身naive，先核对三明确小时再登记UTC；NPZ本身没有时区/单位/完整坐标属性，不能称外部高程基准已验证。

## 防泄漏与时间规则

在官方原循环的目标171物理场及独立source目标state分别毒化为9，aux/scalar不动；两组input/scalar SHA均不变、target SHA改变。证明当前真实物理场与未来条件区分正确，不允许将目标物理场作为当前输入。torch.inference_mode以及临时patch禁止Module调用、backward和DirectTrainer初始化，model计数0，CUDA_VISIBLE_DEVICES为空。

8项新只读/合成时间测试加3项既有时间隔离测试共11项通过（logs/fourcastden_real_interface_tests_v2.log）；不重跑含训练的原全套合成实验。2000—2021每年train、2022validation合法，2023两split拒绝；缺小时/重复/跨年/跨split/非UTC/naive/非法shape和NaN拒绝。首次新测试对shape错误的异常类型期望写成ValueError，实际np.assert_array_equal发AssertionError；仅修正测试预期，首次失败日志保留，无物理容差变化。历史247项是上一任务证据，本次不称重新运行全部255项。

## 归一化、单位与精度差异

174物理/LBC通道按原mean/std逐层float32归一化，与官方data前174完全一致；3scalar独立固定归一化公式与原输出在float32舍入界内吻合，实际送入官方/adapter的全部4scalar逐元素一致。SEA/磁纬磁经直接由原get_data目标时刻给定，完整6aux与捕获官方输入逐元素一致。没有重新计算2023均值/方差或测试误差调参。

独立AffineNormalizer辅助组件内部float64，而作者数组算术float32，三个样本最大归一化差9.53674316e-07，不是训练输入差异；真正OfficialFrameSource/177输入差仍0。最初v1诊断错误地要求该高精度参考组件与float32逐元素相同，断言失败，记录initial_failure.json和原checker/log完整保留；v2分离“原float32路径精确比较”与“辅助float64参考差异记录”，未改原数据/官方统计/原pipeline或放宽输入门槛。

往返按float32量化理论误差界检查，逐变量原生/SI绝对和相对误差全表CSV。DEN最大相对往返约4.13557509e-08；近零UN点相对误差可到0.003068，但最大绝对风误差仅约2.5e-5m/s，不能只报相对误差或认定物理故障。

|变量|原生单位|SI转换|3帧最大往返绝对误差(SI)|
|---|---|---|---:|
|TN|K|1|1.3132601e-05|
|UN|cm/s|×0.01 m/s|2.4830867e-05|
|VN|cm/s|×0.01 m/s|2.62109e-05|
|WN|cm/s|×0.01 m/s|9.3485607e-07|
|Z|cm，位势高度|×0.01 m|0.0071573257|
|DEN|g/cm3|×1000 kg/m3|3.8589895e-15|
|TLBC|K|1|6.1519677e-07|
|ULBC|cm/s|×0.01 m/s|2.0664099e-06|
|VLBC|cm/s|×0.01 m/s|2.3611581e-06|


Z是位势高度，ZG是几何高度，不能互换；本检查未建立WGS84关系。官方static原来源年份及精确采样仍未确认，接口对齐不等于训练分布匹配。当前普通路径不运行log-DEN。

## 原始数据/填充值

三NPZ14键/shape/dtype/finite/abs>1e30哨兵/正TN/TLBC/DEN/ZG递增均通过，未发现缺失值，无替换或补0。作者read_var会在lev顶层全为missing_value时删掉该padding层，SI转换代码被注释，原生cgs单位保留；不能盲用文档字符串SI，也不能将新的有限异常值默认视作padding。本次NPZ已预处理，不据其无缺失推断任意原NetCDF都合法。逐字段实际范围/SHA在interface_audit.json。

## 官方资料继续核查与邮件

本次仅对两个已知记录的versions/latest各请求一次，均HTTP200，软件仍22250238、数据仍21859635，响应SHA与上轮元数据相同；未找到新的官方训练代码、2000—2021或2022数据地址/清单/申请步骤，不猜URL扫描、不下载多年数据。MDPI通讯信息页一次HTTP403，未核实通讯作者与邮箱，不猜邮箱；邮件草稿AUTHOR_RESOURCE_REQUEST已准备，未发送。网页搜索未提供可用官方新资源，不用无关检索结果补证据。

## 备用数据与当前结论

已有S7 secondary坐标lat/lon/lev/ilev与普通static逐元素一致，含所需字段（原变量Kp不是小写kp），但不证明作者物理配置/初态/预热/统计相同。备选2021/2022新驱动/真实日历和14字段短诊断需要另授权，现有2023 GPI不能改标签；详见ALTERNATIVE_TRAINING_DATA_PLAN。当前已验证真实2023只读路径，不等于已经取得合法非2023训练数据、验证其分布或完成真实训练。候选73/49帧和所有正式门槛见REAL_TRAINING_READINESS。

本次CPU审计8.0606秒，所有原始/历史/权重/上轮训练checkpoint SHA仍须最终delivery_audit核验；新增文件预算200MiB，大资产不上传。任务结束安全Git同步后停止，不开始真实训练或大气仿真。
