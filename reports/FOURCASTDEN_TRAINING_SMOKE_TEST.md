# FourCastDEN独立训练工程合成预检（2026-10-23）

INDEPENDENT_IMPLEMENTATION / SYNTHETIC_ENGINEERING_ONLY / NO_REAL_DATA_TRAINING

## 已完成与未完成

本次建立src/training/pipeline.py、独立配置与执行/监督脚本；不是官方完整训练复现。原AFNONet全64,695,744参数/36×72/177二维+4标量→171输出，未缩小架构，随机初始化，未读官方checkpoint或真实NPZ。原第三方树/四权重/static/既有实验SHA保护见delivery_audit。未12/24h预测、TIE、RK45、真实训练/微调。

247项全套CPU测试27.191秒通过，其中8项新增训练测试覆盖shape/loss/backward/梯度/参数更新、validation无更新、非2023年份与连续窗口/跨年/时区拒绝、split分离、未来目标毒化不改变输入、仿射归一化往返、同seed重复，以及含SGD动量/调度/RNG/模型/step的精确checkpoint恢复与下一步等价。旧ERFA合成dubious-year警告保留，不改变环境。

## GPU实际两次启动，累计只完成3个训练step

v1首次在第一forward的CuBLAS运算被确定性检查拒绝，缺CUBLAS_WORKSPACE_CONFIG，0完成step、0optimizer更新，无checkpoint；监督4.679802秒，日志/代码SHA/失败标记完整保留。未关闭确定性检查或改网络，将环境:4096:8在torch导入前设置，用独立cublas_v2标签纠正预检；不是隐藏失败或覆盖重跑同标签。

成功预检执行step1/2，保存唯一checkpoint，释放模型，随机重建同结构后严格恢复到step2，再执行step3；总共3训练更新，另一次独立合成validation无更新，没有真实数据。两进程监督合计12.246402秒<300，成功进程5.407854秒内部墙钟，监督7.566601秒。CUDA确定性/FP32/TF32关闭保留。

|step|合成MSE|裁剪前梯度L2|train_step墙钟秒|
|---|---:|---:|---:|
|1|141.807479858|51.937309121|0.606011|
|2|141.802276611|51.930065712|0.120207|
|3|141.797103882|51.922608393|0.129580|


loss只是任意标准化合成映射的MSE，降低只证明链路更新，不代表真实温度/密度精度改善。随机未训练输出不按物理DEN正值评价，张量不是物理大气。验证合成loss=142.194595337亦无科学解释。

## checkpoint与资源

GPU step2模型SHA恢复精确一致；优化器param_groups/state和scheduler完全一致、step=2，之后成功step3。GPU配置SGD momentum0，optimizer状态无动量张量，CPU测试另外使用momentum0.9证明非空optimizer状态恢复与连续训练数值等价。RNG包括Python/NumPy/CPU/CUDA、training/eval状态、config/label/代码来源。加载只允许可信本地产生.pt，拒绝官方权重目录，不声称可安全加载未知pickle。

唯一synthetic_step2.pt为258850242字节=246.859MiB，留本地不上传。新增500MiB预算不足以保存完整Adam类参数+两动量状态（约0.75GiB），因此工程配置显式SGD0动量/lr1e-4/固定调度/clip1，是资源可控的独立假设，不冒充作者优化器，不改变架构追求loss。未来正式优化器/存储需另核协议与预算。

成功进程CUDA allocated峰611.882MiB、reserved峰710.000MiB，nvidia-smi进程峰1.244GiB<20GiB；CPU ru_maxrss峰1357.691MiB。仅batch1/单步/SGD/FP32实测，不能外推完整Adam、多步展开/大batch时长与显存。模型原声明但未调用norm.weight/norm.bias无梯度，与既有推理源码一致，未修补该数学行为；其余有效梯度统计逐step保存。

## 运行入口与下一门禁

source scripts/activate310.sh；unittest discover；run_fourcastden_training_smoke.py由监督v1启动（失败已保留）；run_fourcastden_training_smoke_cublas.py由独立监督启动（3step通过）。once-only目录，不自动追加step/真实训练。future真实数据需合法2000—2021/2022样本、官方预处理/统计与许可、预注册日期及split、接口单步与多步指标、资源门禁；现有OfficialFrameSource/EpochPairs真实路径仅实现，尚未真实样本运行，不称已验证真实训练。

模型与训练损失、checkpoint兼容经过工程验证，与TIE参考拟合、真实观测密度、最终轨道精度和效率分别论证。第三阶段高度/Z/ZG/WGS84、小时场插值、驱动可得性、真实Swarm气动/姿态/推力及共同受力门禁继续。下一优先取得作者材料和非2023小样本，而非立即大训练。
