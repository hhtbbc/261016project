# V56 · 官方证据交接、非目标多时效索引与未来隔离

**V56_NON_TARGET_TIME_INDEX_AND_SEALING_COMPLETE_VERIFIED / EXTERNAL_EVIDENCE_NOT_RECEIVED**。

## 外部证据及历史保护

起始 HEAD、origin/main 和远端 main 为 d526f4ca3dcc7b1a2f35f9a1d203d23fc5487fd1。V55 16、V54 18、V53 16、V52 33 项发布条目和 V50 冻结清单核验通过。V51 94 卷、V48 66 卷、V49 证据、Swarm 两份上传和 accepted ZIP 及 CDF/HDR 身份均保持。GFZ 两日 V54 原件与 V38 逐字相同，仍为 −1。V37 原件、历史定义和 λ=0.5 保持。STATUS 和 WORKLOG 既有本地修改保留。

调用现有 V55 检查器，只读确认三类声明及两个精确 0504 均 NOT_ACQUIRED。只复核三处官方公开联系入口，沿用 V55 草稿，整理可复制主题、精简英文、附件、回件格式及验收命令。优先提交 GFZ，ESA/NCAR 并行。未登录、接受条款、下载原始产品、发送或提交。 [人工指南](../docs/V56_OFFICIAL_INQUIRY_DISPATCH_GUIDE.md)

## 时间、身份和数值实测

V37 保持 06Z/18Z、[t−3h,t) 和 1/3/6 小时。制作 2020-01-31、02-29、12-31 开始的三个 49 帧小时场，每场跨两个午夜，覆盖跨月、闰年与跨年。36 个端点全部按绝对 UTC 推导，18Z+6h 指向次日 00Z。独立重算全部样本 ID。每行保存源 SHA、时间、角色、split、输入窗口和封存状态。历史最后允许的小时记录是 t−1h。累计评分窗 [t,t+h) 正式右端排除。三个合成 split 支持区间互不重叠，重叠或共端点均拒绝。

V37 两年开发日期各为 03-23、03-24、03-25、09-23，截止前历史与既有评分汇总属于许可范围。V56 选择纯合成密度完成开发与基线，没有读任何真实非目标密度。仅真实读取 V53 观测元数据 CSV。

原生查询内核从合成 NetCDF 读取 36×72 周期网格、4 个 ilev 和随时间变化的 ZG。查询覆盖 30 秒、高纬与经度接缝、时钟端点、逐列高度包围、单位及正密度。**5,040 个有效控制点**，最大绝对误差 **5.0083e−26 kg/m³**，最大相对误差 **4.2188e−15**，相对 P95 **2.8866e−15**。独立按多项式张量计算全量真值。每 lead/高度/截点见 interpolation_error_groups.csv。18 条实际查询拒绝覆盖两端时限、上下高度、极冠及外部零面。计划正例限定在有效范围，最后端点的 +30 秒未进入正例集。

## 毒化和合成基线

12 个截点各冻结历史快照。预测子进程只接收历史路径、SHA、cutoff 和 split。访问严格 [t−3h,t)，均值和尺度从三小时记录计算。评估器在原路径将未来文件（包括 t）替换为 10²⁰ 倍副本后，以全新预测进程重跑。24 次进程执行成对得到相同输入、标准化、预测和允许访问日志。独立验证历史与两个未来 SHA、每条毒化值及历史 UTC。全序列归一化、跨界滚动、滞后索引方向错、未来驱动、预拟合全数据统计、窗口跨 cutoff 和 split 重叠等 13 类负例均实际拒绝，共 **156 条**。独立另外运行 10 项单元测试，包含缺帧、重复、非整点、UTC、边缘域和 CDF 解码前的密度字段拒绝。

Persistence 与历史两帧线性外推共产生 72 条合成预测、12 组 cutoff×lead×方法的 MAE、RMSE、Bias、Relative RMSE，每组 n=6，全部独立复算。18Z+6h 线性外推 RMSE 高于 Persistence，保留原结果。此为合成诊断。隔离保证限于受信任的已测试接口，任意外部代码上线前仍需操作系统级读权限保护。

## 元数据与下一步

两份 V53 元数据按 30 秒 UTC 分配，每窗 120/360/720 行，共 12 个窗组、4,800 行和 2,880 个唯一点 ID。小时括区和时间权重均由绝对 UTC 计算。状态 OBSERVATION_METADATA_TIME_INDEX_VERIFIED，外部 ZG 门禁保持，不授予正式样本准入。

未见 density/density_orbitmean 读数、真实校正拟合、正式评分、GPU、模型积分、真实 AI 训练、DART、轨道传播、外部发送均为 0。V57 优先验收回件；无回件时先用合成测试预测 worker 的系统级只读权限隔离，再在明确许可的既有开发日期验证历史切片。 [V37 矩阵](../experiments/thermosphere_non_target_protocol_v56/V37_admission.csv) · [开发协议](../docs/V56_NON_TARGET_DEVELOPMENT_PROTOCOL.md) · [ID 合同](../docs/V56_MULTIHORIZON_SAMPLE_ID_CONTRACT.md) · [下一阶段决定](../docs/V56_NEXT_STAGE_DECISION.md)
