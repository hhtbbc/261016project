# 官方log-DEN五日期两小时验证（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 实际执行

Jan4、Mar23、Jun21、Sep23、Dec21各00→01→02 UTC全部成功，5序列/10真实forward。官方log权重严格加载一次后复用五窗，每窗重新从自己的00时真实状态开始；没有重跑Direct/Flow、没有下载、训练、扩窗、TIE或轨道积分。F/data_view仅15个已核验原文件的项目内软链接，实际目标逐一确认在工作区内，不是新增/修改原始数据。

完整配置config.yaml/保护SHA/preflight.json在experiments/fourcastden_logden_multidate_v1。15原始文件、static_log与其他原资产/历史结果最终audit逐SHA保护；每窗结果data/processed/fourcastden_logden_multidate_v1/YYYY-MM-DD.npz本地保存。补丁来源、完整diff和哈希见COMPATIBILITY报告。

## 初始状态与反馈

独立重算raw六变量与下边界的作者预处理，DEN先log10，使用官方对应均值/标准差，174通道与get_data逐元素匹配。Hook保存两次177二维输入、4标量和171输出，首输入为真实初态、第二次171通道逐元素等于第一次模型输出；没有01时真实状态反馈。每窗真实未来物理场仅评价，未来外部条件保留作者HINDCAST方法。原CLI date_time遗留字段未用于inference(ic)，实际epochs逐三小时核验。

所有五窗预测finite，TN正，DEN100%正，无裁剪/填零/指数修补或失败重试；各帧密度范围、形状、forward数、原生指标及结果SHA见逐日期runtime.json。作者normalized/native指标及共同物理评价分开，所有公式独立NumPy复核。真实数据科学准确度仍未由此验证。

## 资源

小CPU/CUDA兼容探针0.588s，无网络forward。正式监督墙钟17.213s，两者合计小于600；子进程GPU阶段（含CPU指标/hooks、压缩与SHA等）11.015s，不是纯GPU计算。监督RSS峰1.107GiB<4；加载分配显存峰987.240MiB；加载1.334883s。

|日期|单独读取/预处理ms|作者循环含指标/hooks s|两次forward GPU ms|已有两帧输出pow10 GPU ms|推理峰显存MiB|
|---|---:|---:|---|---:|---:|
|2023-01-04|50.632|0.948747|152.260/19.411|0.081920|282.400|
|2023-03-23|51.261|0.097820|19.474/18.832|0.069632|282.400|
|2023-06-21|50.978|0.096894|19.513/18.786|0.066560|282.400|
|2023-09-23|50.765|0.097556|19.446/18.955|0.068608|282.400|
|2023-12-21|52.361|0.097877|19.619/18.644|0.070656|282.400|

首次网络调用是冷启动；此后为复用同一模型/内核，没有额外warm-up或大量重复。pow10时间只针对已产生的两目标DEN指数张量，不是新forward，排除CPU→GPU传输和前面的仿射运算；作者循环本身另含预测和参考的反变换，不能直接将此微操作时间与总循环相加。数据读取在作者循环中也会发生，表中独立read是另一次测量。数据保存/压缩与SHA、审计开销在总阶段中，没有全归为网络推理。

## 可重复命令与停止

source scripts/activate310.sh；check_fourcastden_logden_compatibility.py建立隔离副本；python -m unittest discover -s tests（215）；run_fourcastden_logden_multidate.py静态；supervise_fourcastden_logden.py唯一正式GPU工作进程；analyze_fourcastden_three_models.py离线公平评价；write_fourcastden_logden_reports.py；audit_fourcastden_logden.py。所有科学输出独占创建，不得重用本标签覆盖；复现实验应另行授权和新标签。Direct/Flow只用原有数组，三模型原始数据/权重均不变，完整报告/CSV/图见THREE_MODEL_COMPARISON。
