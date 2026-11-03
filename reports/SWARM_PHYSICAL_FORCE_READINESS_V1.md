# Swarm-A真实受力参数与轨道预测准入 V1

## 1. 结论与本轮范围

实际取得2023-01-04 SC_ADYN和STRAATT两份官方0601全天产品，完成目标01:00—13:00UTC记录解析、接口开发、28项独立CPU测试和5张真实记录/证据状态图。没有轨道传播、网络推理、训练、TIE-GCM或旧实验重算。

**记录质量可读取，但真实受力模型未闭合。** m_SC单位与记录完整性已核实；正式质量采用仍PARTIAL，姿态旋转、迎风面积、Cd及实际推力未验证。FORMAL_VALIDATED拒绝放行。真实轨道BLOCKED、EXTERNAL_DATUM_UNVERIFIED、科学训练False保持；此前条件数值闭环PASS和旧RK45FAIL均不改。

## 2. 数据获取、时间和许可

通过[ESA公开分发服务](https://swarm-diss.eo.esa.int/)查询具体Sat_A目录，冻结唯一Jan4/0601文件名和大小后下载。ZIP共6332638字节；包括目录等元数据的实际保存响应载荷9329038字节，小于30MiB。解压后逐成员CRC、SHA及原CDF字节一致性验证；发布方独立SHA未提供，本地SHA不是发布方数字签名。

ESA页面说明访问使用受其数据政策及条款约束；未绕过登录或权限，原ZIP/CDF/HDR/DQC及逐记录重打包仅本地保存，不自动公开原始产品，不宣称某个未经核实的CC许可证。

- `SW_OPER_SC_ADYN_1B_20230104T000000_20230104T235959_0601.CDF.ZIP`：3557965字节，SHA256 `7086e3486be13de81b79929c44371915318e19acfcb455ee73a57b44c18cc74b`；来源 `https://swarm-diss.eo.esa.int/?do=download&file=swarm%2FLevel1b%2FLatest_baselines%2FSC_xDYN%2FSat_A%2FSW_OPER_SC_ADYN_1B_20230104T000000_20230104T235959_0601.CDF.ZIP`。
- `SW_OPER_STRAATT_1B_20230104T000000_20230104T235959_0601.CDF.ZIP`：2774673字节，SHA256 `057596c443a245ed9e0b3d7016a23c83d57beb549aec6e0fbf06b4373682101a`；来源 `https://swarm-diss.eo.esa.int/?do=download&file=swarm%2FLevel1b%2FLatest_baselines%2FSTRxATT%2FSat_A%2FSW_OPER_STRAATT_1B_20230104T000000_20230104T235959_0601.CDF.ZIP`。

两产品均全天86400记录；SC_ADYN由ACCELE/03.25于2025-07-19重处理，STRAATT由ORBATT/03.25于2025-07-10重处理，不能声称2023当时可用。CDF_EPOCH与Sensing_Start的UTC头独立对齐，不套GPS偏移。SC_ADYN有约0.757秒采样相位，STRAATT整UTC秒；共同对齐前一原始记录的龄期0.239093750—0.243210938秒，未来最近记录偏移0.756789062—0.760906250秒。接口不重标日期/时间，也不把两轴当作同时采样。

## 3. 质量时间序列与400kg对照

目标窗SC_ADYN共43200记录（01:00:00.756附近至12:59:59.757附近），全部m_SC有限且正值：

|指标|实际值|
|---|---:|
|最小质量|400.712000kg|
|最大质量|400.815000kg|
|平均质量|400.755221713kg|
|相邻记录最大变化|0.002000kg|
|相对400kg的质量差|0.178000%—0.203750%|

这不是称重绝对真值，范围/样本标准差都不是测量不确定度。仅在其他因素固定时，阻力加速度按400/m缩放，相对演示质量改变约-0.203336%至-0.177684%；只是代数灵敏度，没有运行新轨道，也未按SP3拟合。不能用它替代面积/Cd/推力。

SyncStatus原码0有43200条，Flags_Platform原码16有296条。没有获得0601适用的完整码表，因此没有把这些记录全认定为正式有效，也没有按未知标志删点。原始值及所有质量记录保留，完整质量时序在本地mass_timeseries_local.csv，公开小时汇总mass_hourly_summary.csv。

## 4. 姿态与面积

STRAATT目标窗43201条，含13:00终点；非有限q有0条。范数0.999999999131—1.000000000889，最大偏离1约8.892e-10。这只证明基本数值结构，不能证明旋转定义或观测质量合格。

实物q说明为ITRF←S/C；0601分量顺序（xyzw或wxyz）、主动/被动矩阵定义未由适用文件确认。旧5.13概览/详细表方向文字存在不一致；不能套其他MAG产品、其他卫星或通用四元数代码。实际rotation_to_itrs明确拒绝。

Flags_q分布：`{"0": 29542, "1": 46, "3": 394, "4": 14, "6": 10548, "18": 2657}`。SyncStatus原码1有65条；Maneuver_Id原码4有14274条。这些原码意义保留待审，未将全部非零简单判坏，也未将全部有限q判好。

A_head/right/left/down均float64三分量，CDF说明为orbit-frame截面向量、单位m²；它们不是经过核实的完整面元模型。未用向量范数充当迎风面积。仍缺ORB基底/法向、侧面可见性、遮挡、太阳翼及几何完整性、与Cd配套的参考面积。

只实现了显式synthetic_*数学工具：Hamilton主动xyzw正逆转与正交/行列式检查；凸闭合单侧面元无遮挡假设下，A_eff=sum(max(area_vector·v_hat,0))。2×3×4合成箱体沿x投影12m²，xy方向20/sqrt(2)m²，整体旋转后不变。合成通过不代表真实Swarm几何通过，真实面积仍UNVERIFIED。

## 5. Cd的物理证据

[March等2021原始研究](https://doi.org/10.1051/swsc/2021035)及[作者机构摘要](https://repository.tudelft.nl/record/uuid%3A7e1ff16f-85ee-4078-b40c-ed7c44ed22a7)支持：气体表面相互作用、组分与温度会影响气动力和反演密度。文中的能量适应系数不是Cd，不能把0.85当Cd；本轮不借此给Jan4指定常数。

[作者POD密度处理预印本](https://pure.tudelft.nl/ws/portalfiles/portal/71416246/PREPRINTswarmdensityASR.pdf)描述了依赖形状、朝向和气体表面作用的力系数与15面元模型。这是模型链的证据，不是我们已取得完整几何/材料/表温/参考面积参数的证据。需要冻结同一几何、气体温度/组分、相对速度、表面模型及A_ref；也要评估升力/侧向力，而不是默认标量Cd包含全部作用。演示2.2不用于正式数据接口。

## 6. 推力候选与版本问题

目标窗dt_thr十二通道中至少一通道>0的记录82条，形成9个连续**记录段**；最大单记录单通道开启0.110秒，全部通道记录值之和16.862秒。通道可同时开启，因此此和不是净持续时间、完整脉冲数、机动次数或冲量。

f_thr实物单位mN，明确乘1e-3转N；所有目标记录的名义组合力均0，thr_set原码1。但这不能排除执行推力：可能涉及平衡脉冲、未填充/不同语义或其他处理，当前没有证据唯一判断。Maneuver_Id=0也不能单独证明无推力。绝不将原码4直接定性为已知平移机动或按它删轨道。

候选记录段见candidate_event_intervals.csv，逐正开启记录本地thruster_positive_records_local.csv。每段标注CANDIDATE_RECORD_SEGMENT_NOT_CONFIRMED_MANEUVER，actual_impulse保持空。

STRAATT实际处理输入列出了AUXAORBMAN_20140115T115151_20250701T202911_0355，以及AUXAL1BPC_20230101T000000_20230701T000000_0109和AUXAAOC_C_0006等；这是下一步应请求的**具体版本**，不是臆造文件。当前公开L1目录未给AUX目录，未取得这些原件，不尝试认证绕行。SC_ADYN与STRAATT/轨道处理存在共享输入，不能视为独立真值互证。

## 7. 可复用接口及测试

`src/orbit/swarm_force_inputs.py`提供SwarmForceInputProvider.at(UTC,mode=Mode.RESEARCH_PROVISIONAL)。每次核验原CDFSHA，返回质量、原q、名义推力与开启记录、原始质量码、各自记录UTC/龄期、版本和SHA。质量可读但PARTIAL；面积/Cd为空，实际推力未知，缺项不替代400/1/2.2。

当前采用前一观测记录快照，**不声称同刻插值值**；拒绝覆盖外和>1.1秒陈旧记录，不跨缺口、异常或事件做静默插值。此1.1秒是1Hz产品快照陈旧保护，不是物理质量放行标准。不同字段保留不同采样轴。

FORMAL_VALIDATED目前总是因未具备完整证据而拒绝；普通布尔或字符串不能绕过枚举模式。合成旋转工具不绑定实际Swarm q。单位错误、版本不匹配、文件损坏/加载后改变、非正质量、非有限/明显非单位q、未知推力和质量原码均有独立测试。产品q范数平方偏离1超过1e-8只标数值INVALID，不据小偏离标质量PASS，且不静默归一化。

28项CPU测试通过（最终4.545秒）。合成与实物测试分开；测试通过不意味着真实参数已科学验证。例子interface_examples_local.json保留01/07/13时完整返回和溯源。

## 8. TIE-GCM高度登记：有界结果

复用已有源码/数据证据，本轮不重复旧查询。NCAR2.0诊断文档明确DEN位于ilev、ZGMID位于lev；本项目实际DEN/ZG均按ilev接口处理。不能笼统说本项目DEN在lev中点。原生垂直交错定义和几何高度名称不能证明外部零面。

当前公开Swarm定义页仍2013；新定义端点403、Handbook页不可读，未绕过。NCAR2.0原生诊断文档可读，但没有提供我们所需的WGS84/GRS80零面等价证据。新检索到的HAO历史邮件PDF候选未能读取，不作为结论依据，也不臆造回复。EXTERNAL_DATUM_UNVERIFIED保持。

一页结论见docs/TIEGCM_ZG_REGISTRATION_STATUS_20261103.md；原NCAR可发送咨询草稿docs/TIEGCM_ZG_EXTERNAL_REGISTRATION_QUESTIONS.md本轮保持原文，未发送。独立模拟的默认下边界不冒充FourCastDEN作者配置。

## 9. 真实轨道准入矩阵

|项目|状态|来源|剩余问题|
|---|---|---|---|
|SP3 reference|PARTIAL|Official Jan4 SP3ACOM0203 / prior geometry audit|Time/frame/file validated; precise-orbit validation product and accuracy qualification incomplete|
|Initial P/V|PARTIAL|Existing SP3 Hermite frozen initial state|Uses t0+2s: retrospective smoothing, not causal real-time initialization|
|Density fields|PARTIAL|Jan4 DNSAPOD0301, author TIE-GCM, Direct saved states|DNS is POD-derived; source uncertainties and external mapping remain|
|External height datum|BLOCKED|TIE-GCM2.0 native ZG; existing NCAR draft|External zero surface/geographic convention unconfirmed|
|Spacecraft mass|PARTIAL|SC_ADYN0601 m_SC, kg|Record integrity/units checked; version-specific flags and uncertainty not certified|
|Spacecraft attitude|PARTIAL|STRAATT0601 q ITRF <- S/C|Component order and active/passive matrix convention; current flag semantics missing|
|Effective frontal area|BLOCKED|SC_ADYN A_head/right/left/down orbit-frame vectors|Complete macrogeometry, orbit-frame basis, visibility/occlusion and reference area unverified|
|Drag coefficient|BLOCKED|GSI literature identifies model families only|No certified Swarm geometry/GSI/material/environment parameterization|
|Actual thrust|PARTIAL|SC_ADYN dt_thr/f_thr/thr_set; STRAATT Maneuver_Id|Candidate records identified; channel geometry/calibration/code dictionary missing|
|AUXAORBMAN0355|NOT_AVAILABLE|Exact input named in STRAATT global metadata|Not obtained; current public L1 listings do not expose an AUX directory|
|Complete force model|BLOCKED|Existing H6 and high-order numerical qualification|Gravity truncation, tides/radiation/relativity as applicable, real aerodynamic/thrust inputs incomplete|
|Conditional numerical solver|PASS|ABCD DOP853 closure report|Only numerical qualification under frozen conditional assumptions|

这些状态只用于Jan4目标窗。SP3文件及框架解析已通过，不代表精密轨道不确定度、因果初态或受力模型自动合格。DNS是有处理假设的POD密度，不能当作无误差大气观测。当前允许真实参数记录比较、码字/时序和几何单元验证，不允许以未验证A_eff/Cd/推力启动正式轨道精度排名。

## 10. 最关键的三个条件与下一步

1. **实物气动力响应闭环（最高物理影响，中高解决成本）**：确认0601四元数/ORB定义，取得完整几何或经认证气动力查表，匹配GSI、表面/环境参数和参考面积，形成Cd*A/m或完整力系数。质量新数据已取得，但不足以完成这条链。
2. **推力及版本质量码闭环（本窗已有具体风险，优先做的小任务）**：按上述实际AUX输入版本请求机动计划/定标/码表，解释82条dt_thr正值及f_thr全0，冻结事件处理，不按未来SP3残差挑段。已有具体版本和时段，计算成本较低，适合下一轮先实际执行。
3. **外部高度登记（影响密度尺度，计算便宜但依赖维护者证据）**：通过已有NCAR草稿请求版本适用的零面/纬度约定，取得回复后独立验证；不利用同窗观测择优偏移。可与第二项并行准备，但本轮未发送。

下一轮最小建议：先取得0601适用字典及AUXAORBMAN0355、AUXAL1BPC0109、推进器几何/定标的元信息，再决定是否获准下载。预算建议原件≤10MiB（大小未知时先清单/HEAD；超出停止），CPU≤300秒、RSS≤1GiB、输出≤50MiB，不做轨道/训练。目标是生成经版本解释的事件和姿态规则，不再只列未知码。若正式渠道需认证或咨询，应由用户选择渠道，不自动发送邮件。

完整H6还须处理其未验证截断和缺失受力；这些是额外准入，不因本轮辅助数据取得解除。本轮已停止，不自动执行下一阶段。

## 11. 资源、审计与复现

下载主阶段墙钟68.776秒、RSS60.961MiB；主分析8.686秒、RSS129.859MiB；本轮末段绘图/独立核验19.716秒、RSS287.270MiB。各阶段独立统计，不冒充user/systemCPU时间。464保护资产及2346历史资产SHA不变。没有新积分、GPU或TIE。

```bash
source scripts/activate_orbit.sh
python scripts/prepare_swarm_physical_force_v1.py
python scripts/analyze_swarm_physical_force_v1.py
python tests/test_swarm_force_inputs.py
python scripts/finalize_swarm_physical_force_v1.py
```

已完成tag拒绝覆盖，不应直接重放下载/分析；重新执行须独立新tag。只读接口及测试可按原件SHA独立验证。命令、输入/输出/源码SHA及资源见本轮实验目录；五图来源见figure_sources.csv。Git仅同步轻量代码、摘要、图、审计和报告，原产品及逐记录重打包不公开，不强推。

### 原始CDF时间精度核验

本轮发现cdflib默认CDF_EPOCH转datetime会丢弃亚毫秒小数。接口cdf_epoch_utc64分离整数毫秒与原始float64小数部分，独立测试保留750微秒示例；输出ns格式不代表ns观测精度。2023年CDF_EPOCH编码ULP约7.8125微秒，首记录与UTC头相差约2.94微秒，未制造额外时间信息。首版毫秒导出及前版26/27测试记录保留在initial_millisecond_export_local及日志，最终为28项测试通过。质量范围、候选计数、任何旧科学实验均不改变。

本项目FourCastDEN只有TN/UN/VN/WN/Z/DEN六预测场；若GSI依赖物种比例，还须独立组分来源，不能仅凭DEN确定Cd。Swarm问题草稿见docs/SWARM_0601_FORCE_INPUT_QUESTIONS.md，未发送。

### 最小调用示例

```python
from orbit.swarm_force_inputs import SwarmForceInputProvider, Mode
p = SwarmForceInputProvider(dynamics_cdf, attitude_cdf, source_sha256=verified_SHA_map)
r = p.at("2023-01-04T07:00:00Z", mode=Mode.RESEARCH_PROVISIONAL)
# mass.value是kg产品快照；每项source_UTC/age_s和SHA保留在provenance
# q仅返回原值及声明的S/C→ITRF，component_order=None，不生成正式旋转
# effective_area/Cd/actual_force_N保持未知；FORMAL_VALIDATED抛出拒绝异常
```

完整CDF头含原始状态向量，仅本地保留；公开CDF_contract_summary.json只含必要版本/时间/单位/形状摘要，未上传原始轨道向量。
