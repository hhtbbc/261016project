# 最小真实数据推理方案（2026-10-19）
## 实际文件与大小
以本次Zenodo API为准：logs/zenodo_22250238_20261019.json、logs/zenodo_21859635_20261019.json。

|资源|字节|用途|
|---|---:|---|
|FourCastDEN.zip|90,106|源码/配置|
|static.zip|2,378,058|普通模型统计、气候态、坐标/磁坐标|
|static_log.zip|2,296,512|log-DEN配套资产|
|checkpoint_files.zip|2,901,442,296|四种模型的权重归档|
|2023.zip|18,149,758,909|全年8760个小时NPZ|

本次清单不支持“81.5GB公开测试包”的说法：实际ZIP为18.15GB，内部8760个NPZ文件总18,149,297,992字节。三个样本每个NPZ内未压缩NPY总2,407,180字节；若全年相同形状，展开约21.09GB，该估计未逐一下载确认，81.5GB可能来自其他版本/格式，不能作为已核实值。

## 是否能只取少量文件？
Zenodo未单独列出小时NPZ，但文件接口支持Range。实测返回206及正确Content-Range（logs/remote_range_probe.json）。scripts/fetch_minimal_test_window.py用只读seek封装读取ZIP中央目录，再请求指定成员的局部头和压缩字节，只解压选中的三个NPZ；检查所有响应必须206、范围/总长完全一致，单次<8MB，总传输<32MB。没有发起完整2023.zip下载。
实际已获取2023-01-04 00/01/02 UTC：2,076,717、2,078,968、2,080,379字节，共6,236,064字节；包括目录读取的HTTP总传输7,218,463字节。每个成员CRC32验证，另存SHA256于logs/minimal_data_download.log。ZIP全年MD5无法用局部字节校验，不能宣称整包MD5已通过。
数据路径 data/raw/test_minimal_2023/，保持原始内容不修改。中央目录清单 logs/test_archive_inventory.json；范围审计 logs/minimal_data_ranges.json。

## 最小帧数与数据量
Direct/Flow n_history=0，单步需t、t+1两帧；历史变体需t-1、t、t+1三帧。一次L步由get_data读取L+H+1帧，未来帧包含参考状态及必要的下边界/外部驱动，必须保持小时连续。
本次00/01两帧为4,155,685字节（约4.16MB）加普通static.zip 2,378,058字节，总非权重输入包约6.53MB。原CLI默认ics循环因__len__额外减1，最少准备3帧更稳妥；3帧加static.zip为8,614,122字节。6/12/24小时分别理论需7/13/25帧（n_history=0），今天不扩展实验。
每帧须保留14个NPZ键，包含非输出ZG、NE；六变量本体171通道，输入177二维通道与4个标量。静态资产须提供global_means/global_stds/time_means、lat/lon/lev、mag，ilev用于坐标核验。

## 权重核验与运行步骤
下载前已检查共享磁盘约681GB、内存和A100空闲显存。权重ZIP2.90GB低于5GB，可按本次授权下载；预期MD5=78aa5107bf60927e6898cb19449520b7。保存models/checkpoints/checkpoint_files.zip，验证尺寸/MD5，安全检查后解压至models/checkpoints/author；详情以logs/artifact_downloads.json为准。不得把ZIP后缀tar误认为一定是普通tar结构，需实际torch.load检查。
1. source scripts/activate310.sh，使用项目内Python3.10.19；执行依赖导入及CUDA已知数值FFT往返检查。
2. 检查真实样本键、层数、finite、DEN>0、坐标与正标准差。
3. 匹配Direct checkpoint与flow=False/n_history=0/log_DEN=False及普通static；按原架构建立网络并严格加载model_state，不允许strict=False掩盖不匹配。
4. 使用configs/fourcastden_direct_minimal.yaml；调用作者TGCMForecast.inference(0)，即00→01 UTC单步。验证脚本scripts/validate_fourcastden.py，只在前提满足时执行。
5. 保存pred/real/统计和逐变量RMSE/ACC。pred时间索引0是初始化，真正预测是索引1；密度反归一化并检查正值比例。结果只验证TIE-GCM单窗口，不证明观测或轨道精度。

## 补丁与停止条件
原始源码不改。运行副本补丁仅延迟可选apexpy，不跳过磁坐标输入或数据验证。若CUDA失败、权重不匹配、样本缺键/非有限/单位不明确，则停止相应阶段，保留完整traceback；不得随机输入冒充预测、重训或扩大下载。
完成执行后的实际状态见logs/minimal_validation.json、reports/FOURCASTDEN_ENVIRONMENT.md及STATUS.md。

## 今日实际完成
方案已在三个小时的小样本上落地；单步只读取其中00、01两帧，未扩展为多步。Direct权重严格加载且一次真实预测通过；权重包MD5及成员SHA256证据见logs/artifact_downloads.json和logs/checkpoint_sha256.json。四个成员大小分别：历史802,585,484字节、log-DEN776,484,108字节、Direct776,485,772字节、Flow776,485,772字节。仅Direct完成实际加载/预测，其余仅解压与校验。
复现命令：source scripts/activate310.sh，然后python scripts/validate_fourcastden.py，随后python scripts/check_minimal_result.py。请使用不同实验目录保存后续实验，避免覆盖本次结果；当前脚本默认目录固定，重跑会覆盖该目录结果，首次验证后无需重复运行。
配置已保留configs/fourcastden_direct_minimal.yaml；状态和误差日志见reports/FOURCASTDEN_ENVIRONMENT.md。没有将三个样本的获取当作完成10月20日的大气数据分析/可视化任务。
