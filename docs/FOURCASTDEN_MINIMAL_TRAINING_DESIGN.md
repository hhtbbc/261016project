# FourCastDEN独立Direct最小训练设计（2026-10-23）

## 身份与约定

已取得官方推理包，不是完整训练代码。官方资源审计见FOURCASTDEN_OFFICIAL_TRAINING_RESOURCE_AUDIT；本工程为独立训练实现/合成工程验证，不称重现论文全部训练。保留原AFNONet结构与数学运算，不引入残留Lightning的(value,flow)/warp接口，也不把ERA5 FourCastNet训练当作TIE训练。原件/权重/历史实验只读。

|项目|代码确认的推理约定|独立训练选择或未知信息|
|---|---|---|
|forward|models/afnonet.py AFNONet(x,y)，x[B,177,36,72]，y[B,1,4]或可reshape4标量，输出[B,171,36,72]|Direct直接预测归一化下一状态，不累加增量|
|网络|patch4/embed768/depth12/num_blocks8/MLP4/drop0，64,695,744参数|合成GPU不缩架构、随机初始化；不load官方checkpoint|
|变量|TN/UN/VN各28，WN/Z/DEN各29，合171；输入再加3LBC/SEA/磁纬/磁经|原生Z为位势高度非ZG；压力层非固定高度|
|条件|真实当前171状态+目标时刻6aux，目标4scalar f107d/f107a/Kp/sfeps|独立训练配对按已验证inference对齐，不据残留__getitem__推断原精确训练策略|
|标准化|物理/LBC174层zscore、固定scalar/太阳/磁处理由作者dataset.get_data提供|OfficialFrameSource复用原loader；AffineNormalizer提供独立可测仿射组件，不能替代完整太阳/磁/标量预处理|
|损失|论文登记/官方搜索摘要有L2训练描述；代码训练片段MSE和utils/LpLoss，活动推理指标有cos纬度权重|本次训练使用归一化171通道无权MSE；不能证明原作者训练是否纬度/通道/相对加权；不把评价权重当训练权重|
|优化器|注释YAML AdamW、残留Lightning Lamb，不足追溯四权重真实训练|SGD lr1e-4/momentum0，仅合成预算设计；支持显式AdamW接口但未GPU执行|
|调度|原片段Cosine、活动配置残留不构成协议|独立StepLR step_size1/gamma1，恒定学习率，仅接口验证|
|精度与裁剪|原四权重推理FP32|合成FP32/TF32关闭，clip norm1，确定性开启；CuBLAS启动前:4096:8，不AMP|
|seed|原训练seed未取得|本次20261023，Python/NumPy/TorchCPU/CUDA统一，CPU重复验证；GPU跨机器位级确定性未证明|
|采样|dataset注释过滤每年前3天，SAMPLER_PERCENT指向缺失入口|EpochPairs显式连续一小时、同年、不跨split，train2000—2021/val2022，2023拒绝|
|checkpoint|推理读取model_state严格load|训练另存optimizer/scheduler/step/RNG/模式/config/元数据，可信本地.pt；不从官方权重恢复训练|

## 数据与训练调用接口

src/training/pipeline.py的OfficialFrameSource接收已配置作者TGCMDataset，按epochs和get_data([i],inference=True)提取state/aux/scalar。EpochPairs只把当前171物理状态与下一小时aux拼为177，目标171只作label；未来真值毒化输入不变。训练和验证各自索引必须在允许年份，缺帧/重复/跨年/非UTC拒绝。validate_disjoint核整个输入与目标历元集合；未来窗口打乱只能在训练合法pair集合内，不能打乱小时字段或跨年拼接。真实adapter尚未取得非2023样本验证，不称已跑通真实训练。

DirectTrainer.train_step：train模式→zero_grad→forward→finite MSE→backward→有限非零梯度统计→可选clip→optimizer.step→scheduler.step→计数。validation_step在no_grad/eval下只计算loss，结束恢复原模式，不更新参数/step。所有输入/输出shape和finite检查，错误立即抛出。

保存采用exclusive新文件，路径限制工作区；restore要求trusted_local=True，官方models目录拒绝，严格model_state/完整config/合成标签一致。恢复Python/NumPy/TorchCPU/CUDA RNG、optimizer和scheduler、step与train/eval模式。pickle仅本地可信，不能加载未知下载checkpoint。现有标签限定工程合成，未来真实训练必须独立协议与显式标签，不静默沿用合成授权。

## 预算与可重复性

默认执行仅synthetic_batch，没有真实文件路径；配置configs/training/direct_synthetic_smoke.json无官方checkpoint。GPU唯一成功预检3步，checkpoint仅step2一份，约247MiB；完整Adam状态checkpoint会超过本次500MiB新增预算，因此选择SGD0动量，不声称作者最优配置。CPU测试用Tiny网络验证接口与有动量恢复，GPU使用完整AFNO证明反向传播实际可运行，二者不可混为训练精度成果。

首轮v1因CuBLAS确定性环境缺失第一forward中止，零完成step；保留v1和源码SHA。独立cublas_v2在torch导入前设置环境后3步成功，未关闭确定性。两进程累计监督约12.25秒<300，进程GPU峰约1.24GiB<20GiB；以SMOKE_TEST真实记录为准。已知原self.norm未在forward_features调用，因此norm两参数无梯度，保留原数学，不“修复”成另一网络。

训练能力/合成loss下降/真实大气学习能力分别验证。本次不真实训练、不多步训练、不微调官方权重、不TIE/RK45/新长时预测；未来真实数据与优化器/训练轮数/验证策略均须另授权及独立run-tag。
