# FourCastDEN官方Direct两小时自回归验证
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 历史成果与本次范围

2026-10-19已完成Direct严格加载与Jan4 00→01单步、NumPy重算；原文件experiments/20261019_minimal_direct/result.npz的SHA256为 `c63a390ee2297673af12ee6b3231a55a4c73f81f05ebe5019b41ec2ed02f43b5`，本次只核验保留，不重复计作新成果。当前正式任务仅一次Jan4 00→01→02 Direct推理，真实网络forward恰好2次，无额外教师强制、6h/24h、训练或微调。新目录experiments/fourcastden_two_step_v1及data/processed/fourcastden_two_step_v1。

## 数据、模型与防泄漏

复用原始3个小时NPZ、官方Direct_ckpt.tar（SHA212187479c2df3ead151ec339683198f9e0632e23b892ac4d829ce1048724efb）、普通static和Linux仅可选导入补丁副本。原始源码逐字节对比原ZIP，四权重与static/static_log核验，所有资产原件不变。AFNONet 64,695,744参数，177二维输入、4标量、171输出，n_history=0、n_prediction=2、dt=1h、flow/log_DEN/perturb均false，FP32/TF32关闭，严格加载作者model_state。通过公开inference(0)调用，不改作者循环，避开全年CLI日期索引假设。

实际forward hooks已保存两次输入/输出：第一次171状态等于00时初态；第二次171状态逐元素等于第一次预测，且不是回填01时真物理场；各步后6辅助通道和4标量来自对应01/02时。CPU合成毒化测试替换未来真物理场但预测和网络输入不变，改变未来辅助条件则输入确实改变；此测试不属于真实模型成果。

未来F107/Kp及TLBC/ULBC/VLBC取作者已给定NPZ，SEA/sfeps由作者太阳几何函数计算，磁坐标用作者static。原始驱动值及每个样本来源见runtime.json。这些并非由网络自主预报的未来条件，不能称实时自主预测。NE/ZG虽在样本中，但不在171个预测通道中。Z是位势高度，ZG是几何高度。

## 评价定义

使用作者cos(latitude)/mean(cos(latitude))加权逐通道RMSE，以及相对作者time_means气候态的ACC。独立NumPy float64重算；ACC仅在异常范数分母有限且>0时报告，否则N/A。参考采用作者float32归一化后的同一目标场，原始NPZ反归一化重建舍入差另记录于analysis.json。不用更新后的01时真状态当持续性：持续性在两个目标时刻都固定00时171通道，网格、权重、气候态及有效掩码与AI一致。

下表为各变量逐压力层RMSE的算术平均，不是所有高度混成的RMSE，也不是固定几何高度450km误差。风cm/s→m/s和Z cm→m乘0.01，DEN g/cm³→kg/m³乘1000。样本本身无单位属性，依据作者UNIT_VARS和read_var未作SI转换的实际代码；不是依据docstring中的SI字样猜测。

|变量|SI单位|1h AI RMSE|1h持续性RMSE|2h AI RMSE|2h持续性RMSE|1h/2h AI ACC平均|
|---|---|---:|---:|---:|---:|---|
|TN|K|0.43379627|17.15594|0.75153378|33.515873|0.99998869/0.99996844|
|UN|m/s|0.59600236|19.903091|1.4741235|39.921303|0.99995943/0.99980535|
|VN|m/s|0.54527554|23.514835|1.3597473|46.747822|0.99996359/0.99988634|
|WN|m/s|0.018390183|0.4291345|0.05661045|0.76816028|0.99982973/0.99883387|
|Z|m|60.873675|3261.6766|126.8629|6404.432|0.99999443/0.99997853|
|DEN|kg/m3|1.9691618e-11|1.0889965e-09|2.616667e-11|2.1006508e-09|0.99998994/0.99997409|

六变量平均逐层RMSE均随第2步增大，但两步中每个171通道的AI RMSE都低于固定t0持续性。这里只是一个真实初态、两个目标时刻，不证明全年/磁暴/真实大气/轨道优越性。ACC很高也不等于独立观测验证。

## 分层密度与图

342行逐层指标见results/metrics/fourcastden_two_step_v1_layers.csv，12行变量汇总见summary.csv；116行DEN层/基准相对差与自然log差见density_layers.csv。相对差定义ρ预测/ρ参考−1，没有人为密度floor；两步预测全部有限且DEN100%正。逐界面记录ilev与参考ZG全球中位/范围，避免把压力面当固定高度。地图选参考ZG全球中位最接近450km的原生界面，图注明实际ilev与中位高度，未做450km外推或外部WGS84映射。

results/figures/fourcastden_two_step_v1_density_map_hour1/2.png包含真实参考、预测和相对差，配合density_vertical_errors、variables_vs_persistence、network_timing共5图。TN/UN/VN为28层lev，其余29层ilev，不能按同索引认定同高度。

## 数值核查与资源

独立RMSE相对作者记录最大差1.88200739e-07，满足既有rtol2e−5；ACC满足atol2e−6。新首步与历史结果最大归一化差0，说明历史行为保持，不是新的单步复现声明。192项全套测试通过（187项原测试+5项新CPU验证）。

A10080GB/torch2.4.1+cu121/CUDA runtime12.1，模型加载1.333029s，单独首次三帧读取及预处理0.052419s；作者正式inference含再次读取、评价与审计hooks共0.962696s。两次CUDA event网络耗时150.502/19.098ms，包含首次调用冷启动差异，不当成稳定吞吐基准。GPU阶段总墙钟5.600174s，小于300s。

显存记录在模型加载后reset峰值计数：推理阶段peak allocated 281.251MiB，peak reserved 1106.000MiB（含加载遗留缓存）。没有独立保存加载瞬态allocated峰，不能把此allocated数字当全流程峰，也不能直接与10月19日含checkpoint加载的峰相比较。初始GPU空闲显存由nvidia-smi确认。运行结果新增约17.065MiB，完整交付新增量由最终审计核算，远低于500MiB；无下载、无其他项目写入。

## S7兼容性发现与训练缺口

静态探针确认S7目标记录14键齐全、lat/lon/lev/ilev与官方static一致；TN/UN/VN各顶层2592个有限padding，需显式掩码/移除。NetCDF自动missing_value无法安全cast曾发警告，probe保留手工哨兵统计，不能仅看finite。未将S7输入网络。仍需整点1h抽取、完整记录质量、原训练归一化分布与物理配置审查；AI的Z非ZG，正式高度接口不变。

官方README只提供2023推理，训练主入口/2000—2021训练与2022验证数据、完整训练协议不齐；Lightning片段与AFNONet实际返回/条件接口有不一致。四权重已核验不等于四模型均可运行，更不等于完成论文训练复现。完整A—F路径、数据量/资源/防泄漏要求见FOURCASTDEN_PHASE2_RESEARCH_PLAN.md。建议下一次先做相同三帧的官方Flow两小时配对实验，需新授权；本次停止，不扩6/24h或训练。

## 可重复命令与文件

source scripts/activate310.sh；python -m unittest discover -s tests；python scripts/run_fourcastden_multistep.py（静态）；timeout 300s python scripts/run_fourcastden_multistep.py --execute（唯一一次，当前标签拒绝重复启动）；python scripts/analyze_fourcastden_multistep.py；python scripts/write_phase1_stage_review.py；python scripts/write_fourcastden_two_step_report.py；python scripts/audit_fourcastden_delivery.py。新复现实验须更换独立输出标签并保留本次文件，不能重跑旧validate_fourcastden.py覆盖单步结果。
