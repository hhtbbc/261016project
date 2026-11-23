# V30 两年秋季真实密度评价与独立复核

**SCIENTIFIC_EVALUATION_COMPLETE_VERIFIED**。2021-09-23 和 2022-09-23 各完成一次正式 CPU 评分，保留全部正负结果。两年累计联合判据分别为 **8/12** 和 **6/12** 通过。交叉日期与既有春季参考均显示收益随截点、时长及误差指标变化。

身份为 DATE_HELD_OUT_PREREG / HINDCAST / PROVISIONAL Map-A / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED。观测为 Swarm A DNSAPOD_2 0301 的 30 秒瞬时 POD 反演密度。Bias 定义为模型减观测；相对指标按逐点观测密度归一化。

## 准入、冻结与独立复核

核实 V26/V29 工程闭环、run_id、两份冻结输入、66 卷完整 SHA、两份 V21 CDF 与 GRS80 合同、V20 冻结科学源。历史拟合进程仅解析每个日期的 [03:00,06:00) 和 [15:00,18:00) 密度记录，各 360 点。CDF 文件哈希是字节级身份检查；历史阶段未解析未来密度字段。两个不可覆盖参数文件先落盘，再形成双年份收据。未来毒化在评分前独立执行，2021/2022 的 06Z 与 18Z 共四个独立副本，分别乘 1e20 后重查历史拟合，同日 Stale06 引用冻结全局06Z。全部逐值一致。

按原 V18 浮点合同，保留历史窗口起点独立查询得到的精确历史 Raw 输入，全天查询的对应值先通过 1e-13 / 0 核对。Raw 表写出后才应用冻结校正。所有方法使用相同 UTC/产品 ID，无按误差筛样、fallback 或外推。累计 1/3/6 小时 N 分别为 120/360/720，非重叠块分别为 120/240/360，仅累计组纳入联合通过数。

独立程序再次哈希 66 卷，从两份原 CDF 和各 25 帧原始 NetCDF 重建坐标及模型值，每年 2,880 点和 23,040 列，最大相对查询差 4.44e-16。独立验证后以正式 Raw 数组作为算术合同，使用冻结乘数重算预测，避免插值舍入跨越近零 Bias 容差。十个 sorted median 与 NumPy 指数核验通过，乘数与正式预测逐值一致。各年 172 行指标、172 个 ID 组、24 行联合表全部复核，共 **6,882 项数值字段、0 失败**，rtol=1e-13、atol=0。早期输入、原协议及两份既有春季记录保持原样。

## 整日原始误差

绝对指标单位均为 10⁻¹⁴ kg/m³；相对指标用百分比。整日及整日纬区结果仅为描述，不参与滚动窗口联合判断。

| 年份 | 纬区 | N | MAE | RMSE | Bias | Relative RMS % | Relative P95 % |
|---|---|---:|---:|---:|---:|---:|---:|
| 2021 | 全域 | 2880 | 2.833 | 3.437 | 1.527 | 8.25 | 15.58 |
| 2021 | 低纬 | 959 | 3.224 | 3.771 | 2.628 | 8.61 | 15.49 |
| 2021 | 中纬 | 965 | 2.806 | 3.375 | 1.662 | 7.82 | 14.66 |
| 2021 | 高纬 | 956 | 2.467 | 3.135 | 0.286 | 8.31 | 17.94 |
| 2022 | 全域 | 2880 | 8.808 | 10.708 | 6.730 | 31.25 | 64.22 |
| 2022 | 低纬 | 979 | 9.464 | 11.874 | 6.459 | 42.60 | 106.07 |
| 2022 | 中纬 | 928 | 8.836 | 10.195 | 7.372 | 23.14 | 48.16 |
| 2022 | 高纬 | 973 | 8.123 | 9.921 | 6.392 | 23.52 | 47.79 |

2022 秋季低纬整日 Relative RMS 为 42.60%、P95 为 106.07%，高于该日中高纬的描述性数值。2021 秋季各纬区整日 Relative RMS 在 7.82%–8.61%，高纬相对 P95 仍为三区最高。误差以 Swarm 反演密度为参考，不能将偏差完全归因于 TIE-GCM。

## 冻结历史系数

| 年份 | 截点及拟合域 | N | b | exp(b) |
|---|---|---:|---:|---:|
| 2021 | Global06 | 360 | -0.046386663 | 0.954672754 |
| 2021 | Global18 | 360 | -0.060395357 | 0.941392274 |
| 2021 | low | 122 | -0.070822270 | 0.931627456 |
| 2021 | mid | 114 | -0.052791493 | 0.948577777 |
| 2021 | high | 124 | -0.060987051 | 0.940835422 |
| 2022 | Global06 | 360 | -0.154062040 | 0.857218837 |
| 2022 | Global18 | 360 | -0.066037288 | 0.936095958 |
| 2022 | low | 113 | -0.018613016 | 0.981559136 |
| 2022 | mid | 119 | -0.075982783 | 0.926832164 |
| 2022 | high | 128 | -0.085538069 | 0.918018195 |

Stale06 使用各自日期的 Global06。两年秋季 10 个乘数全部小于 1。2022 Global06 向下校正幅度较大，同日 Global18 与低纬18Z 的幅度明显更小，因而不能把早间系数视作全天固定偏差。

## 累计窗口对照

单元格为 RMSE（10⁻¹⁴ kg/m³） / Relative RMS（%）。完整 MAE、RMSE、Bias、Relative RMS、P95、Relative Bias、Log RMS、Pearson 和最大绝对误差见逐年 CSV。各时标非重叠块及低中高纬均在表中。

| 日期 | 截点 | 方法 | +1 h | +3 h | +6 h |
|---|---|---|---:|---:|---:|
| 2021-09-23 | 06Z | Raw | 3.021 / 7.59 | 2.940 / 7.51 | 3.453 / 8.24 |
| 2021-09-23 | 06Z | GlobalAdaptive06 | 2.037 / 5.09 | 2.815 / 6.86 | 3.263 / 7.86 |
| 2021-09-23 | 18Z | Raw | 2.286 / 5.78 | 3.990 / 10.78 | 3.904 / 9.67 |
| 2021-09-23 | 18Z | GlobalAdaptive18 | 2.758 / 5.72 | 2.739 / 7.02 | 3.515 / 8.00 |
| 2021-09-23 | 18Z | LatitudeAdaptive18 | 2.751 / 5.65 | 2.720 / 6.99 | 3.492 / 7.97 |
| 2021-09-23 | 18Z | Stale06 | 2.408 / 5.15 | 2.864 / 7.58 | 3.437 / 8.01 |
| 2022-09-23 | 06Z | Raw | 9.203 / 16.07 | 12.728 / 49.40 | 10.416 / 36.93 |
| 2022-09-23 | 06Z | GlobalAdaptive06 | 7.336 / 8.89 | 10.477 / 36.41 | 10.186 / 28.02 |
| 2022-09-23 | 18Z | Raw | 10.385 / 22.07 | 9.990 / 19.86 | 8.823 / 16.57 |
| 2022-09-23 | 18Z | GlobalAdaptive18 | 8.851 / 15.98 | 10.413 / 15.43 | 9.687 / 13.18 |
| 2022-09-23 | 18Z | LatitudeAdaptive18 | 7.785 / 16.05 | 9.402 / 15.14 | 8.676 / 13.21 |
| 2022-09-23 | 18Z | Stale06 | 10.472 / 11.28 | 13.968 / 13.79 | 13.775 / 13.60 |

- **2021 秋季 8 PASS、4 FAIL、0 N/A。** 06Z 全局三窗皆降 RMSE，但累计 3 h 的低纬绝对相对偏差恶化。18Z 三种校正在 +1 h 全部提高绝对 RMSE，同时降低 Relative RMS 和 P95；+3、+6 h 三种均过联合门槛。纬区方案在 +3 h 的 RMSE/RMS 最低，+6 h 的最低 RMSE 发生在 Stale06，纬区 Relative RMS 略低。
- **2022 秋季 6 PASS、6 FAIL、0 N/A。** 06Z 全局三窗降低 RMSE，+1 h 因低纬偏差未通过。18Z 纬区三窗均过联合门槛，绝对 RMSE 均低于同截点全局法；全局法 +3、+6 h 的 RMSE 恶化，Stale06 三窗皆恶化。Stale06 在 +1、+3 h 的 Relative RMS 低于当时重新拟合的两个方案。18Z +6 h 的全局 Relative RMS 略低于纬区。
- **全部 24 个秋季全域累计校正 Relative RMS 与 P95 均下降，16 个降低绝对 RMSE。** 区域和非重叠结果保留了相反方向。2021 年 06Z 全局低纬累计 +3 h 的 RMSE 下降时，Relative RMS 上升约 0.078 个百分点，P95 上升约 2.371 个百分点。该年 06Z 全域非重叠 +3–6 h 的 RMSE 下降 6.26%，P95 上升约 0.90 个百分点。2022 的全域累计窗未出现绝对改善同时相对恶化。
- 两年共有的稳健描述是 06Z 全局绝对 RMSE 均下降，18Z 纬区在两日的 +3/+6 h 均符合联合标准。Stale06 的 18Z 联合通过为 2/3 与 0/3。累计窗嵌套，各窗口与纬区结果仅作描述。

## 春秋比较

| 年份与季节 | 06Z Raw RMSE / Relative RMS | 18Z Raw RMSE / Relative RMS | 联合通过 |
|---|---:|---:|---:|
| 2021春 | 12.799 / 22.81% | 11.677 / 18.64% | 1/12 |
| 2021秋 | 3.453 / 8.24% | 3.904 / 9.67% | 8/12 |
| 2022春 | 20.978 / 16.30% | 22.478 / 19.11% | 0/12 |
| 2022秋 | 10.416 / 36.93% | 8.823 / 16.57% | 6/12 |

累计 +6 h 的对照显示，秋季四个绝对 Raw RMSE 都低于同年同截点的春季冻结值。然而 2022 年 06Z 秋季 Relative RMS 由春季 16.30% 升至 36.93%，其中低纬由 16.35% 升至 57.58%，低纬相对 Bias 从 −2.68% 变为 +30.81%。绝对与相对量受密度水平和分母共同影响。春季累计联合为 1/12 和 0/12，存在多项绝对 RMSE 改善而相对 RMS 或 P95 恶化。春季十个历史乘数中九个大于 1；秋季十个均小于 1。逐窗改进百分比、低纬 Relative Bias 和相对 P95 可在跨季节 CSV 同键对照。

两秋季日期均为 INTERMEDIATE，2021 Fobs/中心81日均值/最大 def Kp 为 89.7/86.95 sfu/3.667，2022 为 146.3/131.77 sfu/3.333。可描述连续太阳通量差异，当前设计未形成预注册高低太阳活动组或安静/扰动对照。两年均以 mareqx 春分源冷启动，秋季目标距模型启动 14 天。部分春季背景有不同预热时间，例如 2022-03-25 距 03-09 启动 16 天。季节、驱动、预热和初态适应共同变化，现有四日期无法分离单因素因果或支持跨季节稳定有效。未做 IID 显著性检验。

## 下一步及边界

优先研究校正机制，再扩大独立日期。现有证据指向同日系数漂移及相对误差分母的影响：2022 年 Stale06 在三窗均恶化 18Z 绝对误差，该日低纬与中高纬的误差结构差异明显，且 2021 年同一绝对改善可同时增加区域尾部误差。下一轮若授权，可先在明确标记的开发集诊断历史到未来的残差分布、低密度分母及纬区下的失效种类，再冻结改法并预注册新的日期。若使用本轮秋季结果选择方法，这两日须转为开发用途。扩大日期应覆盖按事前标准可用的更多独立活动类别和可比初态/预热条件。本轮没有重调方法。

Swarm POD 密度带反演误差；Map-A 的数值一致性仍保留外部 ZG 高度零面未验证。使用真实历史 GFZ 的 HINDCAST 不代表业务预报。冷源适应、14 天收敛、误差来源分离及跨季节泛化仍待验证。保留 SEED_POLICY=A_MAREQX_APPROVED、AUTUMN_ADAPTATION_UNVERIFIED、FOURTEEN_DAY_SPINUP_NOT_PROVEN_CONVERGED、EXTERNAL_DATUM_UNVERIFIED、Restart=FAIL、SCIENCE_TRAINING_READY=False、DART=NOT_ADMITTED、REAL_ORBIT=BLOCKED。

## 资源与成果

准入 8.09 秒；双年份历史冻结 4.41 秒；毒化 0.18 秒；正式评分分别 4.42 和 4.33 秒；独立复核 9.47 秒。各阶段峰值 RSS 均低于 268 MiB。GPU/A100 调用、模型积分、新下载、模型预约、AI/DART/轨道运行均为 0。观测和模型逐点缓存留在本地，发布只含汇总和来源证据。

- 参数与防泄漏 · [2021_parameters.json](../experiments/thermosphere_autumn_density_validation_v30/2021_parameters.json) · [2022_parameters.json](../experiments/thermosphere_autumn_density_validation_v30/2022_parameters.json) · [dual_freeze_receipt.json](../experiments/thermosphere_autumn_density_validation_v30/dual_freeze_receipt.json) · [future_poison_test.json](../experiments/thermosphere_autumn_density_validation_v30/future_poison_test.json)
- 原始及校正评分 · [2021_raw.csv](../experiments/thermosphere_autumn_density_validation_v30/2021_raw.csv) · [2022_raw.csv](../experiments/thermosphere_autumn_density_validation_v30/2022_raw.csv) · [2021_metrics.csv](../experiments/thermosphere_autumn_density_validation_v30/2021_metrics.csv) · [2022_metrics.csv](../experiments/thermosphere_autumn_density_validation_v30/2022_metrics.csv) · [2021_joint.csv](../experiments/thermosphere_autumn_density_validation_v30/2021_joint.csv) · [2022_joint.csv](../experiments/thermosphere_autumn_density_validation_v30/2022_joint.csv)
- 跨季节与复核 · [cross_season_metrics.csv](../experiments/thermosphere_autumn_density_validation_v30/cross_season_metrics.csv) · [cross_season_coefficients.csv](../experiments/thermosphere_autumn_density_validation_v30/cross_season_coefficients.csv) · [independent_verification.json](../experiments/thermosphere_autumn_density_validation_v30/independent_verification.json) · [independent_numeric_checks.csv](../experiments/thermosphere_autumn_density_validation_v30/independent_numeric_checks.csv)
- 图册 · [figure_captions.csv](../experiments/thermosphere_autumn_density_validation_v30/figure_captions.csv) · [figures/01_raw_time_series.png](../experiments/thermosphere_autumn_density_validation_v30/figures/01_raw_time_series.png) · [figures/02_correction_time_series.png](../experiments/thermosphere_autumn_density_validation_v30/figures/02_correction_time_series.png) · [figures/03_rmse.png](../experiments/thermosphere_autumn_density_validation_v30/figures/03_rmse.png) · [figures/04_relative_errors.png](../experiments/thermosphere_autumn_density_validation_v30/figures/04_relative_errors.png) · [figures/05_latitude_errors.png](../experiments/thermosphere_autumn_density_validation_v30/figures/05_latitude_errors.png) · [figures/06_multipliers.png](../experiments/thermosphere_autumn_density_validation_v30/figures/06_multipliers.png) · [figures/07_joint_matrix.png](../experiments/thermosphere_autumn_density_validation_v30/figures/07_joint_matrix.png) · [figures/08_spring_autumn.png](../experiments/thermosphere_autumn_density_validation_v30/figures/08_spring_autumn.png)
