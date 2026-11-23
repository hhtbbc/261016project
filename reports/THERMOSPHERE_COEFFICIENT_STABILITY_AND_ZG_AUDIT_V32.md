# V32 历史系数因果可用性与 ZG 高度证据链审查

整轮 **V32_RESEARCH_DESIGN_COMPLETE**。任务 A **STABILITY_DESIGN_INCONCLUSIVE**，现有历史特征足以描述稳定性，日期及 as-of 证据不足以冻结可信门控。任务 B **ZG_EVIDENCE_REVIEW_COMPLETE**，外部零面仍为 **EXTERNAL_DATUM_UNVERIFIED**。V33 优先 ZG 外部证据与条件敏感性，保留原 Global 基线。

## 数据角色与保护

V30、V31 发布清单、历史预测本地缓存、V20 及 V2/V2.1 外部咨询资料按各自锚点核验。V30 联合结果仍为春季 1/12、0/12 和秋季 8/12、6/12。V31 的 32,008 项历史复核证据保持。未重做大规模沿轨查询、物理场扫描或历史评分。

开发来源为 2021/2022-03-23、03-24、03-25 和 2021/2022-09-23，共八日。两秋日已用于开发证据，其 V30 首次预注册验证历史按原身份保留。2021/2022-06-21 与 2021/2022-12-21 继续为未见候选，仅处理元数据；本轮未设新方法验证日期，未读取夏冬目标密度或误差。未来先冻结公式、估计规则、可用输入、超参数策略、角色、指标、排除和门禁。 [数据角色](../experiments/thermosphere_coefficient_stability_zg_audit_v32/data_roles.json)

## 历史计算与信息可用性

16 窗各 360 条原 UTC 30 秒记录，左闭右开 [03,06) 或 [15,18)，按固定三个 120 样本小时块。输出残差中位数、极差、相邻变化、标准差、MAD、P05/P25/P75/P95、正负比例、纬区样本数及比例、观测/背景密度水平与经度、纬度、南北半球、GRS80 高度覆盖。纬区 N<30 标记无效。先冻结角色、代码、历史特征和 SHA，再连接已经存在的未来标签。NPZ 数值字段严格解析记录范围；UTC 索引及字节级身份核查可涉及全文件。历史中位数只作统计，没有生成预测乘数。

| 日期 | 截点 | 三个历史小时块中位数 | 极差 |
|---|---:|---|---:|
| 2021-03-24 | 06Z | +0.25798 / −0.09316 / +0.03947 | **0.35114**（最大） |
| 2021-03-25 | 18Z | +0.30971 / −0.01542 / +0.04432 | 0.32513 |
| 2021-03-25 | 06Z | −0.04915 / +0.26546 / +0.16908 | 0.31461 |
| 2022-09-23 | 06Z | −0.11761 / −0.14281 / −0.21992 | 0.10231（秋季最大） |
| 2022-09-23 | 18Z | −0.05746 / −0.06056 / −0.07733 | 0.01987（全组最小） |

真实预测还要求每条观测、质量旗标、坐标解和背景帧的 as-of 发布时间不晚于截点。终版 Swarm POD 及真实驱动下的背景只证明 HINDCAST 事件时间成立。插值若需要截点整点背景帧，须另外验证该帧当时已经发行。18Z 可以回看已发布的同日 06Z 摘要，06Z 不能读 18Z。GFZ 仅记录最晚封闭 Kp 桶，[03,06) 或 [15,18)，def Kp/Fobs 发布和回修未核实，中心 81 日均值含后 40 天。所有终版 GFZ 数值均排除出实时特征。 [信息矩阵](../experiments/thermosphere_coefficient_stability_zg_audit_v32/information_availability.csv) · [三小时统计](../experiments/thermosphere_coefficient_stability_zg_audit_v32/history_stability.csv) · [小时和纬区](../experiments/thermosphere_coefficient_stability_zg_audit_v32/history_groups.csv)

## 事后关系与门控证据

14 个已发布 +6h 漂移标签覆盖 7 日，小时极差与绝对 Δb 的描述 Pearson 为 **+0.131**。2021-03-25 缺同口径已发布 b_F，保留缺口。2022 秋季 06Z 后 3–6 h 的既有 Δb 为 **+0.11104**，其历史极差在全组并不靠前。

四个主日期的 8 个当截点全局 +6 h 结果，历史 MAD 与 Relative RMS 收益的描述 Pearson 为 **−0.443**。2021-03-25 06Z 历史 P95−P05=0.759、MAD=0.152，Relative RMS 恶化 49.58% 且 P95 恶化。2022-03-25 18Z MAD 仅 0.070，Relative RMS 仍恶化 31.40%，P95 也恶化。历史分位宽度无法单独决定尾部结果。

2022 秋季 18Z 可事前察觉旧系数迁移风险。早 b=−0.154062，晚 b=−0.066037，差 **+0.088025**；晚窗自身极差 **0.01987** 很小，但早窗下调幅度更强。事后 Stale06 +6 h 绝对 RMSE **+56.11%**、相对 RMS **−17.90%**。2022 春季 b 差更大（+0.1399），Stale06 的绝对误差却只恶化 6.54%。差值是候选风险信号，不能确定将来的失败或其幅度。

2022 秋季 06Z 负残差比例为 100%，历史的下调方向明确，后 3 小时绝对误差仍恶化。其两个截点历史纬区最大计数差为 14、15；2021 秋季 06Z 的差仅 6，+3 h 仍有低纬 Bias 恶化。历史观测均值 2022 秋日早晚从 5.721 变 7.203 ×10⁻¹³ kg/m³，和采样与系数同时变化；能描述权重背景，尚无法给出分母或区域覆盖的风险阈值。少日期、嵌套累计窗及沿轨相关性限制这些关联，没有阈值选择、IID 检验或新预测。 [漂移关联](../experiments/thermosphere_coefficient_stability_zg_audit_v32/drift_descriptive_join.csv) · [冻结结果对照](../experiments/thermosphere_coefficient_stability_zg_audit_v32/frozen_outcome_descriptive_join.csv)

## A/B/C 设计对照

| 候选 | 输入和开销 | 收益与代价 |
|---|---|---|
| A 原 Global | 仅三小时历史 log 中位数，0 新参数，CPU 极轻 | V20 公平基线，保留漂移和尾部风险。 |
| B 收缩 | 概念为 b_new=λb_H，至少一个事前固定参数或规则，CPU 极轻 | 撤回过调，也可能减弱有效收益。缺真实可用输入、历史支持不足、需依赖未来选 λ 时停用。 |
| C 稳定性门控 | 历史 UTC、发布凭证、波动、分区支持和旧系数的新鲜度，至少一个状态阈值 | 可区分迁移风险与幅度风险，日期少时易过拟合。当前只设计输入接口。 |

合法输入要求冻结事件时间、质量、发布时戳、历史支持和算法。异常拒绝，不按误差裁剪、不补样或跨区 fallback。仅在有效场景的预注册动作中可考虑弱化或不校正。所有候选必须保持共同观测 ID，保留绝对 RMSE、Relative RMS、P95、低纬绝对 Bias 四项。阈值和 λ 只能在开发数据选定并锁定，然后由新日期检验。本轮未实现收缩、门控或新预测。

## ZG 审查

- NCAR 2.0 源码、官方缓存和原文件头确认 **Zp=ln(P0/P)**，P0=5×10⁻⁵ Pa。接口 ilev 与中点 lev 相差 0.25、间隔 0.5。两份秋季代表暖卷 **ZG/cm 与 DEN/g·cm⁻³ 同在 (time,ilev,lat,lon)**，分别乘 0.01 和 1000 转 SI。
- addiag 由 z_lbc 起算常重力 Z；calczg 以底 Z 为锚，按温度、O/O2/N2/He 平均粒子质量与变重力向上积分，顶层线性外接。ZG 的源输出名为 **Geometric Height ZG**，部分旧注释沿用变重力 geopotential 描述。现有证据确认计算和输出身份。原 mareqx 有接口 Z、无 ZG，压力网格与暖态一致；暖态另外诊断 ZG。
- 默认下边界 **96.37229 km** 是背景 Z；配置的 GSWM 扰动可改变实际下边界。局部重力有效半径与 apex 辅助椭球分别服务各自算法。未确认模型纬度相对于外部大地或地心纬度、ZG 零面相对于任一外部椭球的版本适用关系。
- Swarm A 0301 GRS80 高度合同已核实，其框架精确实现与反演不确定度仍需独立证据。Map-A 的 GRS80→XYZ→WGS84 变换后，以 WGS84 地理纬度及椭球高条件性登记到模型纬度及原生 ZG。既有八列一致性说明数值和覆盖，**不提供物理零面证明**。正式外部接口仍拒绝。 [四级证据矩阵](../experiments/thermosphere_coefficient_stability_zg_audit_v32/zg_evidence_matrix.csv) · [原生文件头](../experiments/thermosphere_coefficient_stability_zg_audit_v32/zg_native_headers.json)

## 复核、预算与决定

历史特征墙钟 0.133 s / CPU 0.509 s / 峰 RSS 72.9 MiB；ZG 墙钟 0.561 s / CPU 0.900 s / 峰 80.4 MiB；共享独立复核 1.061 s / 峰 82.8 MiB。**1,570 项独立数值核对、19 项正反检查全部通过**。首次独立核验写 JSON 遇 NumPy bool 类型，保留局部收据并仅改序列化后复核，未改科学输入或结果。GPU/A100、物理积分、新预测/评分、训练、DART、轨道和外部联系均为零。 [独立复核](../experiments/thermosphere_coefficient_stability_zg_audit_v32/independent_verification.json)

V33 首先做 ZG 外部高度证据及现有列梯度的小批次核查。若可独立给出物理支持的幅度，再预注册固定正负偏移、零偏移和共同有效域；否则停止于证据，不拟合最佳偏移、不改正式接口。收缩和门控暂缓。当前无需用户立即操作。有版本匹配的外部证据或独立基准时可另行提供，是否人工联系由用户决定。 [V33 方案](../docs/THERMOSPHERE_V33_ZG_SENSITIVITY_AND_CAUSAL_INPUT_PLAN.md)

保留 SEED_POLICY=A_MAREQX_APPROVED、AUTUMN_ADAPTATION_UNVERIFIED、FOURTEEN_DAY_SPINUP_NOT_PROVEN_CONVERGED、EXTERNAL_DATUM_UNVERIFIED、Restart=FAIL、SCIENCE_TRAINING_READY=False、DART=NOT_ADMITTED、REAL_ORBIT=BLOCKED。
