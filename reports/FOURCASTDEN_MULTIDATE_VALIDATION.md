# FourCastDEN多日期工程与数值验证（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 固定样本与历史保护

新增2023-03-23、06-21、09-23、12-21各00→01→02 UTC；日期由用户/预注册提前确定，不依新误差替换。Jan4仅读取旧Direct/Flow结果，不重放。实验experiments/fourcastden_multidate_v1；原始样本data/raw/fourcastden_multidate_v1；8个新预测数组data/processed/fourcastden_multidate_v1，仅本地保存。

执行前main本地/远端均为1d558c3852ccf7f02b30fcbda6426e57255d1fba，工作区原为干净。保护清单继承前两轮原始源码、Linux运行副本、四权重、static/static_log、Jan4样本及历史结果；预先逐SHA核验，最终交付audit再次核验。没有模型/数据安装或已有资产重下载。

## HTTP Range与数据合法性

先检查已有官方2023.zip中央目录，再远程读取ZIP中央目录确认同12成员的尺寸/压缩方法/CRC和实际header_offset。复用fetch_minimal_test_window.py的seek+Range方法，抽成无历史顶层副作用的BoundedRemoteZip；原下载脚本不改。每次强制206、精确Content-Range和限长body，200或范围不匹配时不读body即停止，预算前置检查，zipfile逐成员校验CRC。12文件SHA和全部请求见download.json，外层ZIP成员CRC及NPZ读入完整，没有宣称全年ZIP的MD5验证。

实际传输25,849,991字节（24.652MiB）<100MiB，用时100.740s；仅12个新NPZ，无Jan4重下载，无18GB整包。原始文件独占创建、校验后设只读。数据检查14键、TN/UN/VN28lev、WN/Z/ZG/DEN/NE29ilev、3个下边界1×36×72和3个标量；36×72网格、finite、|x|>1e30哨兵拒绝、DEN/TN正、ZG逐列递增通过。

NPZ本身不包含经纬/压力坐标数组或单位属性，不能独立从其元数据证明坐标基准。模型使用原作者不可变static的lat/lon/lev/ilev；形状、训练统计、作者读取约定匹配。单位依据原UNIT_VARS和实际未SI换算代码：DEN g/cm3→kg/m3乘1000，风cm/s及Z/ZG cm→SI乘0.01。Z为位势高度，ZG为几何高度；不混为固定450km。

## 模型、序列与公平性

官方Direct和Flow各严格加载一次checkpoint，再各复用同一已加载网络处理四个独立序列；每序列重新用该窗00时初始化，非跨日期连续演化。AFNONet64,695,744参数、177二维输入/171输出/4标量、history0、2步、普通static、log_DENfalse、FP32且TF32关闭。Direct checkpoint SHA212187479c2df3ead151ec339683198f9e0632e23b892ac4d829ce1048724efb；Flow cc88b4bbee4d70b7a49c94ae3a8127768c1529368abbd7d5f76018d0166a3021。历史与本次config SHA、每窗数据SHA、结果SHA完整保存，无strict=False。

执行8次独立序列、16次实际forward，各两步的hook检查通过；Direct反馈预测状态，Flow归一化增量加到当前归一化状态后反馈。第二步未使用01时真实171状态；目标辅助和驱动按作者方法给定，故为HINDCAST。每个新日期Direct/Flow real、means/stds、climatology、辅助通道及标量逐元素相同。 公共YAML的date_time是继承作者CLI的未使用字段；本入口直接调用inference(ic)，真实起点由已核查的dataset.epochs三帧索引决定，不通过CLI日期减72小时逻辑。实际日期/文件/初态均逐窗记录，不能把遗留CLI字段当作实际运行日历。作者日志“包含12小时past history”实际指目录有12个样本，真正n_history=0；索引切片逐窗核查只有3个连续小时，未跨季节间隙取相邻时步。

## 自动化与独立数值验证

206项测试通过，既有Direct/Flow实际作者循环合成反馈、防未来物理真值泄漏、增量数学及新Range拒绝/预算/长度/CRC/样本契约全部通过；合成测试不作真实预测。8次GPU序列均成功，无重试，无新增Jan4预测。所有预测finite、DEN100%正、TN正，无裁剪/补0/后校正。各变量偏差/极值见summary.csv。

5窗×2模型×2时效全部171通道独立NumPy重算cos纬度加权RMSE和气候态ACC。最大RMSE相对差1.882e-07，ACC最大绝对差2.301e-07，满足原预注册rtol2e-5/ACC atol2e-6。加权均值与另一种加权sum/总权重RMSE实现一致；最终独立audit还会重算ACC及CSV。零异常范数分母应记N/A，不通过调阈值制造PASS。

## 资源与计时口径

唯一监督GPU进程树墙钟27.342s<600，监督峰RSS1.223GiB<4，无超限、遗留失败或自动重试。子进程记录GPU阶段总墙钟19.099s，包含模型加载、网络、指标、hooks、SHA及数组压缩等CPU/I/O；这不是纯GPU运算时间。子进程启动前的历史SHA检查/导入等计入监督墙钟，因此两个口径不同。

本次A10080GB、torch2.4.1+cu121、CUDA runtime12.1，新增文件总量由delivery_audit.json核算，250MiB限额。模型加载Direct 1.317814s，Flow 1.153406s。进程第一次Direct forward 151.550598ms；余15个GPU事件约18.221—20.112ms。

Flow的首次模型调用已受Direct共享CUDA内核预热，raw字段first_forward_cold_this_model仅表示该checkpoint首次调用，不代表进程全冷；timing_scope.json专门澄清。没有额外warm-up/重复吞吐测量，不能把Direct第一窗冷事件与Flow暖事件比较后宣称Flow加速。每窗读取/预处理、作者循环（包括再次读取/metrics/hooks）、网络事件、推理峰显存及加载费用逐记录保存。

## 静态log-DEN审查

已校验官方log-DEN权重SHAd314241ef9b91ba8e3405d77090b24ded03ceff361404f9ff5bd6212b828db18，CPU weights_only读取150个model_state条目、输入177通道，与官方对应结构一致；static_log DEN统计29层有限且std正。只读检查，无网络构造或forward。官方numpy.power(10, CUDA Tensor)反变换分支仍有兼容性风险，未经动态验证，不能声称该变体已经可正式推理。后续须隔离受审补丁/包装器及合成测试，不改原作者树。5窗三帧已备齐，log两步无需新数据；history两步仍需每窗前一小时或共同t0调整。

## 可重复命令与边界

source scripts/activate310.sh；python -m unittest discover -s tests；run_fourcastden_multidate.py静态、--fetch；supervise_fourcastden_multidate.py唯一一次；analyze_fourcastden_multidate.py；inspect_fourcastden_log_static.py；write_fourcastden_multidate_reports.py；audit_fourcastden_multidate.py。所有正式入口独占创建并拒绝旧标签重跑。未训练、未微调、未扩6/12/24h、无新TIE或卫星轨道积分。当前完成后停止，新的科学验证需另授权。
