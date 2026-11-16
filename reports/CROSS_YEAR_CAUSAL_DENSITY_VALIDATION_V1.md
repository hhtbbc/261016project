# 跨年份因果密度校正验证 v1

2026-11-16。`CROSS_YEAR_CAUSAL_DENSITY_VALIDATION=COMPLETE`指冻结方案执行及审计完成，**不是科学泛化PASS**。实验身份`CROSS_YEAR_METHOD_REPLICATION / PROVISIONAL Map-A / HINDCAST`。数据以前用于原始密度对照，并非全新盲测。

## 1. 目标、输入和工程身份

使用既有2021-03-24 Swarm A DNSAPOD0301（2880条、30秒、flag0），只读复用。CDF SHA与v9原始记录一致，字段UTC/密度kg/m³/角度deg/高度m由原读取器检查。输入清单`experiments/swarm_tiegcm_2021_spinup_observation_v1/inputs.json`中8卷NetCDF SHA与实际文件、各组历史data_audit逐项一致，不能用另造清单替代。四组DEN及ZG均为ilev29；DEN g/cm³×1000，ZG cm×.01；原生有效小时数据10帧03—12。

2021 A7/B7/A14/B14的真实运行退出码均为0、4个NORMAL EXIT，工程审计均PASS。2021 A14仍按研究角色仅敏感性；**不是2022 A14的历史PARTIAL**。2022 A14 PARTIAL保持，不跨年份套用工程身份。2021 O1/O2/N2科学门禁失败以及完整大气状态未通过不变。工程PASS、DEN可查询、多变量科学资格分别记录。

B14主背景按事前来源/工程身份选定，A7/B7对照，A14敏感性；不根据本轮未来RMSE排序。原始CDF/NetCDF、v10代码/报告/系数保持，未下载观测、未运行物理积分、DART、GPU或轨道。启动前本地/远端HEAD均c469f9c...，未重复推送；历史未跟踪同步日志保留。

## 2. 冻结时间、方法与因果隔离

2021-03-24 06:00 UTC截止，历史严格[03,06)360点；未来[06,07)120、[06,09)360、[06,12)720点。另列不重叠[06,07)、[07,09)、[09,12)。这些窗口在模型查询/估计前已冻结。

- Raw：原始Map-A背景，b=0。
- Transfer：**仅B14**，原样使用v10的b2022=0.1261252775057784、exp(b)=1.1344242772252575，不用2021历史拟合。
- Adaptive：各背景只对自己的过去A观测估计median(ln(obs)-ln(model))，未来统一乘exp(b2021)。不混合背景，不使用C/B，不搜索核、趋势、学习率或高度偏移。

系数文件在未来误差计算前写入并链接frozen_protocol SHA。未来A密度毒化20个数量级，各背景系数逐位不变。新模块显式接收日期，复用v10标量应用/质量/误差函数；旧v10硬编码日期入口保持只读，单元测试确认2022调用等价。Transfer只允许B14且拒绝其他背景或修改系数。

## 3. 观测算子及数值检查

复用GRS80地理位置→ITRS→DensityQuery WGS84→显式Map-A→hourly provider。每列log密度垂直、水平密度双线性、时间密度线性插值不变，8邻列即使零权重也必须有效。4320次查询（四背景各1080）全部有效，各自与共同域覆盖100%，无补零/裁边/外推/备用密度。逐点时空权重/垂直层/源文件/质量/拒绝原因存本地query_trace_local.jsonl。

本次用到的原始DEN/ZG帧显式_FillValue/missing_value、非有限、极大哨兵及DEN非正检查均为0；12个真实八列加权重建在1e-13相对容差内通过。独立CDF直读1080条UTC/密度/标志/坐标与匹配数组精确一致。独立54个全窗指标行重算MAE/RMSE/Bias/relativeRMS/P95/logRMS通过1e-13相对容差，未放宽旧门槛。48个CPU测试通过，原始数据与旧产物SHA保持。

## 4. 真实2021历史系数

|case|role|b_2021|multiplier|N|
|---|---|---|---|---|
|B14|PRIMARY|0.093990767|1.098549603|360|
|A7|CONTROL|0.116661872|1.123739397|360|
|B7|CONTROL|0.069664886|1.072148829|360|
|A14|SENSITIVITY_ONLY|0.108798450|1.114937612|360|

B14 2021历史log残差mean=0.048994247、median=0.093990767、P05=-0.383838061、P95=0.364801430、std=0.240566806。2022 mean=0.122461744、median=0.126125278、P05=-0.110067201、P95=0.334887601、std=0.147903160。2021分布明显更宽，均值与中位数也不同。高度相关2021+0.062992/2022-0.328126、纬度相关2021-0.093108/2022+0.312349；均为描述相关，不是高度或太阳活动因果证明。

完整逐背景两年均值/中位数/乘数/P05/P95及相关见historical_residual_comparison.csv。2022只读复用v10真实残差与参数，未重新拟合或运行2022查询。

## 5. B14未来结果：绝对与相对误差结论分歧

RMSE单位10^-13 kg/m³；改善率正=改善，负=恶化。所有方法使用同一ID集合。

|window|method|N|RMSE_e13|RMSE_gain_pct|relative_RMS_pct|relative_RMS_gain_pct|
|---|---|---|---|---|---|---|
|future_1h|Raw|120|1.081733|—|19.4645|—|
|future_1h|Transfer|120|0.705375|34.7921|21.4994|-10.4539|
|future_1h|Adaptive|120|0.783045|27.6119|20.2005|-3.7810|
|future_3h|Raw|360|1.097941|—|25.0234|—|
|future_3h|Transfer|360|0.824448|24.9096|29.6053|-18.3103|
|future_3h|Adaptive|360|0.873176|20.4714|27.8326|-11.2265|
|future_6h|Raw|720|1.252631|—|24.0041|—|
|future_6h|Transfer|720|0.927541|25.9526|26.2255|-9.2541|
|future_6h|Adaptive|720|0.997089|20.4004|25.0208|-4.2356|

**按绝对RMSE，Transfer和Adaptive都改善；按relative RMS，二者三个累计窗口均恶化。** 因而用户给出的四种解释情形必须按指标区分：RMSE符合“情况1”，relative RMS符合“情况4”。不能挑RMSE宣布整体泛化成功，也不能说2022系数完全没有迁移作用。

Transfer的RMSE在三个窗口均低于Adaptive，但Adaptive的relative RMS均优于Transfer。没有跨全部指标的单一赢家。2021自适应使用较小乘数，减轻了迁移尺度的部分过校正，却未恢复到Raw的整体relative RMS水平。

六小时Raw/Adaptive/Transfer的relative P95为41.0294%/54.9278%/59.9872%；log RMS为0.248409/0.224725/0.225218。可见log RMS与绝对RMSE改善，同时相对尾部和relative RMS恶化。Pearson三者均0.953325，因为恒定正乘数不改变相关性。

这不是指标实现错误：RMSE²=mean[rho_obs²×relative_error²]，relativeRMS²=mean[relative_error²]。绝对密度幅值大的点在前者中权重更大；某些相对误差的放大可被绝对RMSE改善掩盖。中位log偏差是log残差L1意义的尺度估计，不保证最小化物理RMSE或relative RMS。**本轮未根据此结果更换估计器。**

## 6. 背景敏感性、逐点和区域诊断

六小时Adaptive：

|case|role|RMSE_gain_pct|relative_RMS_gain_pct|
|---|---|---|---|
|A7|CONTROL|24.3654|-4.2488|
|B7|CONTROL|15.9371|-4.0263|
|A14|SENSITIVITY_ONLY|22.8699|-4.0157|

不同背景上复现了RMSE改善、relative RMS恶化的方向。A14不进入主背景结论。B14未来720点，Adaptive470改善/250恶化、Transfer455改善/265恶化，无不变点，没有删除不利点。多数点改善也不保证平方相对误差降低。

B14六小时区域relative RMS（%）：

|region|N|raw_relative_RMS_pct|transfer_relative_RMS_pct|adaptive_relative_RMS_pct|
|---|---|---|---|---|
|low|231|33.6145|40.6025|38.3469|
|mid|241|19.8620|18.7834|18.3022|
|high|248|15.3945|10.8791|11.0607|
|height_430_440km|343|28.1525|32.6746|30.9701|
|height_440_450km|194|22.6543|22.1487|21.6234|
|height_450_460km|126|16.3262|14.4648|13.9829|
|height_460_470km|57|13.1552|11.4470|10.6112|

2021低纬raw平均有符号相对Bias仅+0.4502%，Adaptive后+10.3495%、Transfer后+13.9532%，低纬过校正明显重复且更严重；2022低纬A由-9.3877%到+2.7928%。同时中高纬relative RMS改善。430—440km组恶化、其他高度组改善，但高度和纬度沿轨相互关联，不能把组间差异直接归因于高度。所有预注册区域N及N/A保留在region_metrics.csv，未事后重划区域。

不重叠时间窗：

|window|method|N|RMSE_gain_pct|relative_RMS_gain_pct|
|---|---|---|---|---|
|future_1h|Transfer|120|34.7921|-10.4539|
|future_1h|Adaptive|120|27.6119|-3.7810|
|incremental_1_3h|Transfer|240|20.6162|-20.2140|
|incremental_1_3h|Adaptive|240|17.2735|-13.0299|
|incremental_3_6h|Transfer|360|26.6107|2.6134|
|incremental_3_6h|Adaptive|360|20.3561|4.7493|

相对收益在1—3h恶化、3—6h改善，不呈单调时间衰减。累计窗口相互重叠，30秒点相关；未做IID显著性检验，也不将720个样本称720次独立实验。

## 7. 两年联合解释、限制与高度

2022 B14自适应A的六小时relative RMS19.1526→14.6187%，与本轮2021的24.0041→25.0208%方向不同。绝对RMSE收益在两日复现，但“绝对和相对同时改善”没有跨年份稳定复现。仅两个日期，不能宣布年度泛化或单一太阳/地磁活动因果；太阳地磁驱动、轨道高度、物理场和观测处理条件不同。

本轮有限重读[NCAR官方grid/altitude页](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/grid.html)仍标April2016，未发现新增ZG零面与GRS80/WGS84严格等价定义；仓库没有新维护者回复，不发送邮件。继续引用reports/HEIGHT_DATUM_OFFICIAL_EVIDENCE_UPDATE_V1.md，不重复历史搜索或编造误差界。正式接口EXTERNAL_DATUM_UNVERIFIED；Map-A不因为某个指标更小而升级。b可能混合模型、坐标及POD反演尺度偏差。未来真实GPI为HINDCAST，未验证实时驱动不确定性。

## 8. 资源、复现与准入

预检/受监督匹配-拟合-评价-7图/独立核验/5测试套件已计量墙钟合计19.135秒；监督任务14.143秒，峰值采样进程树326.027MiB。目录在报告前12.902MiB。轻量交互文件检查未逐项计时，不冒称整个对话自然墙钟。无失败重试，600秒/4GiB/150MiB预算未扩大。

入口source scripts/activate_orbit.sh；具体命令见commands.json。已有运行目录、参数及输出以独占创建保护，不能盲目在原tag重跑。CPU监督器真实wait返回0、清理通过，完整资源/输入输出/code SHA保存。只公开派生残差/指标/图表，原始CDF/NetCDF、完整匹配和逐点查询数组本地。

CROSS_YEAR_CAUSAL_DENSITY_VALIDATION=COMPLETE只代表实验执行完成；总体稳定收益证据不足。SCIENCE_TRAINING_READY=False、DART未准入、Restart一致性FAIL、真实轨道BLOCKED、外部高度未验证及两年各自A14工程状态保持。不根据本轮结果调整系数、扩展模型、增加截点或运行同化。
