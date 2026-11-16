# TIE-GCM ZG外部高度登记：咨询准备包 V2

2026-11-16 UTC；tag `tiegcm_zg_external_registration_v2`。**资料准备完成，未发送咨询，外部登记未解决。** 起始本地/远端main均30671bd15d2712361e77d230cd7162349925809b；无覆盖旧实验。原旧英文草稿、历史证据报告及正式/临时坐标接口均逐字保留。

## 1. 本轮实际增量

复核有限源码段、实际编译搜索路径/apex覆盖层、两个B14原卷元数据与历史启动SHA、真实边界日志。未重做大规模场扫描或沿轨查询。将旧草稿扩展为四组正式英文问题，补充真实版本、运行配置、附件和收到回复后的验收矩阵。无新观测下载、物理积分、密度查询、校正拟合、GPU、DART、轨道传播或邮件/表单提交。

交付：docs/TIEGCM_ZG_EXTERNAL_REGISTRATION_REQUEST_V2.md；本实验目录的protocol、official_source_inventory、model_configuration_manifest、question_evidence_matrix、response_acceptance_matrix、response_validation_checklist、source_chain_excerpts、runtime_boundary_evidence、review_validation、source_preservation、commands、resource_audit及SHA清单。

## 2. 真正的高度计算链（全部为已核实的实现事实）

1. `init.F:182–185`依bgrddata文件名设置ibgrddata；0表示无该背景文件，不是椭球/大地基准选项。`lbc.F:105–115`在0时将背景t/u/v/z分别取默认温度/0/0/zbound。
2. `cons.F:315`默认zbound=136.291/sqrt(2.)×1e5 cm，数学值约96.3722903 km，日志有限位数回显0.963723E+07 cm。这个常数是背景下边界Z值，不是已验证的椭球面或全球恒定实际下边界。
3. `lbc.F:128–159`把启用的GSWM高度扰动加入z_lbc；其他下边界选项也可能改变它。两年B14启用相同两份迁移日潮/半日潮文件，非迁移潮未用，因此走相同配置算法，但不同日期/驱动下的瞬时下边界数值不必相同。
4. `addiag.F:157–202`底Z=z_lbc，再按常重力定义的静力关系向上延伸。`cons.F`中的TIE常重力为870 cm/s²；不能混作标准地表重力位势高。
5. `calczg`以c2=cos(2×1.74533e−2×glat)，g0=980.616(1−0.0026373c2)，r0=2g0/(3.085462e−6+2.27e−9c2)，按中性温度和O/O2/He/N2平均粒子质量向上积分。底ZG=底Z；重力逐层用经验逆平方形式更新。源码重力更新使用当前ZG和下一Z的均值，不能静默改写成另一套解析地球几何公式。顶ZG=2×次顶−再次顶，是模型构造边界。
6. **calczg局部r0是重力梯度匹配的有效半径，不是GRS80/WGS84椭球半径。** cons中的动力学re、磁映射re_dyn、另一个模块级r0与该局部r0也不能混为同一个参考面。
7. 原始getapex把规则模型ylatg转成角度直接送入apex_mall；实际官方更新apex入口注释为geodetic，内部req6378.160km/逆扁率298.25，convrt说明其高度相对辅助参考椭球。实际getapex输入的映射高度hs=130km。**这是磁坐标模块约定；没有发现calczg调用这个椭球来定义ZG零点的证据。** 不从模块注释推导全模型大地基准。

源码行段及完整SHA见source_chain_excerpts.csv；原始源码不修改。四个核心高度/映射例程由Make.env的DIRS顺序解析到原2.0树，apex解析到实际覆盖层，所有选择已静态核验。

## 3. 版本、补丁与真实B14配置

- 原始官方tiegcm2.0标签commit da712811d925376ff8ef40ff64bda7cc070ca661，原包SHA4c9c43cd…，完整值见manifest。
- 官方apex更新commit84185ee0b97307567c78e32ce85643b48a5cc1a9；实际apex SHA7dc94d38…；统一补丁SHA336086a8…；原apex文件保留。
- GNU12兼容覆盖sphpac/util/mud与Make.workspace单列SHA，不把编译覆盖称为未经修改的官方二进制。高度cons/lbc/addiag/getapex来自未修改原树。两次历史启动记录的apex和可执行SHA均吻合实际文件，未重新编译。
- 两年B14：5°、72×36、29个ilev、28个内部midpoint/29个存储lev坐标；step60s，4MPI/OMP1，HEELIS，完整smax源SOURCE_START80/00/00。2021从03-09到03-26，2022到03-25；原始源文件来自2002背景，实际模拟日历及驱动另列，未重标源时间。
- 实际ibgrddata0、GSWM迁移日/半日1/1，非迁移0/0；两份输入文件以及原source/GPI/GSWM SHA完整列出。没有把默认zbound当作外部零面证据。
- 两卷v13-B原始secondary_015 SHA再次匹配。DEN/ZG尺寸均(time24,ilev29,lat36,lon72)，单位g/cm3/cm，输出单位换算×1000/×0.01。lev从−6.75到7.25，ilev从−7到7，均间隔0.5且lev=ilev+0.25；同为29不代表同一层。DEN不是TN那样的中点变量。
- NetCDF中model_version=tiegcm_trunk、svn_revision=tiegcm2.0。历史label仍带ten-day/nine-day等旧模板文字，未修改；实际运行身份由输入/日志/审计说明，不根据label猜运行时长。输出私有host/logname属性不公开。

上述是本项目独立运行，**不能推断FourCastDEN作者2023原运行具有同样边界配置**。作者配置差异仍为NOT_ESTABLISHED。

## 4. 外部产品与Map-A

复用SHA验证的VirES HAPI JSON和v13-A实际CDF合同：SW_OPER_DNSAPOD_2_、0301、UTC、瞬时density kg/m³，GRS80大地纬经度及米制高度。HAPI的Height_GD描述“GRS80 latitude”原文笔误保留，不能只根据字段名扩展出其精确框架实现或不确定度。

真实Map-A代码流：原GRS80大地坐标→EarthLocation(GRS80)地心XYZ→名义ITRS位置→DensityQuery.to_geodetic(WGS84)→显式假设WGS84纬度=模型纬度、WGS84椭球高=原生ZG（offset0）→八列内时空/垂直log密度插值。椭球数学转换与热力ZG外部登记是两个问题；GRS80也不等于已经指定ITRF实现。

此前选定时段100%查询有效只表明插值域与输入有效，**不证明零点/纬度假设正确**。本轮没有新增查询或用密度残差反推零点；正式DensityProvider和临时adapter SHA保持。

## 5. 官方问题证据矩阵

状态针对完整问题，而非代码是否可读：7项中5项PARTIALLY_VERIFIED、2项UNVERIFIED，没有完整外部登记问题达到VERIFIED。实现事实在单独review_validation记录通过，不与外部定义混淆。

|问题|状态|当前结论|
|---|---|---|
| 模型纬度定义 | PARTIALLY_VERIFIED | 辅助入口为geodetic已明确，但全模型外部纬度约定仍待维护者确认 |
| ZG零点 | UNVERIFIED | 未找到可靠外部零面定义，不解除门禁 |
| zbound参考面 | PARTIALLY_VERIFIED | 默认计算及潮汐影响已核实，外部参考面未核实 |
| apex椭球关系 | PARTIALLY_VERIFIED | apex常数不能作为ZG外部登记公式 |
| GRS80/WGS84转换 | PARTIALLY_VERIFIED | 两椭球数学转换可追溯，不能推出模型ZG等价关系 |
| 官方沿轨登记方法 | PARTIALLY_VERIFIED | 一般几何高度建议已明确，产品专用严格登记流程未找到 |
| 登记误差范围 | UNVERIFIED | 没有可应用到本项目的官方总登记误差界 |

优先复用[官方2.0网格/高度说明](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/grid.html)、已存Altitude Coordinates PDF、官方NCAR固定源码与[VirES官方HAPI](https://vires.services/hapi/)。官方文档支持用几何ZG及按层登记，并未在本轮核查内容中给出所需的外部零面转换或总误差界。PDF的DEN接口说明与实际文件/源码相符；旧网页笼统“中性密度在中点”不能覆盖实际DEN变量。不能将搜索未找到提升为“官方永远不存在定义”。

本轮少量新增官方网页核查：grid、manual index、HAPI landing、contact成功；ESA Handbook产品页HTTP406未获取正文，未绕过/反复请求。未下载原始观测/大资料。网页传输未逐字节计量，零新数据下载不等于零网页流量。

**联系人增量**：[官方Contact页](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/contact.html)明确列示tgcmgroup@ucar.edu作为moderated list。可确认官方旧版文档记载，不能确认2026当前负责人/投递成功。状态OFFICIAL_DOCUMENTED_CHANNEL / DELIVERY_AND_CURRENT_OWNERSHIP_UNVERIFIED；邮件收件人仍为用户确认占位符，无猜测邮箱、无发送/订阅/表单。

## 6. 咨询内容与回复验收

V2邮件从旧稿演进，四组问题为：A全模型地理纬度/外部椭球；B ZG及默认zbound的外部零面、底层等置和GSWM影响；C DNSAPOD GRS80/WGS84至DEN/ZG的官方流程；D若仅有近似，适用域、示例与有根据误差。姓名/单位/邮件均占位，不添加个人信息。可附轻量矩阵、配置manifest和有限源码/回显，不附NetCDF/CDF/完整轨迹。

预注册7种回复类型：明确零面和椭球、明确有界近似、只说明纬度、只说几何高度、只给apex信息、未回复/不可确认、其他版本不匹配。任一回复都**不自动放行**。即使明确完整关系，也须独立经过版本适用性、数学/单位转换、坐标样例、登记误差预算、沿轨共同有效域五项，再另获任务审查正式接口。

只解决纬度就只关闭纬度子问题；“几何高度”或apex椭球单独不足以关闭ZG零面。不伪造不存在的官方精度范围。

## 7. 验证、资源、状态

本轮实际CPU脚本对版本、源码解析、历史二进制SHA、日志边界、NetCDF维度/坐标/单位、HAPI SHA和旧文件保护执行断言，全部通过；这是静态溯源与元数据核验，不是新坐标物理验证。独立包验证再检查证据矩阵/验收矩阵及88份受保护文件SHA，通过；实测墙钟0.995463秒、CPU0.973781秒、峰RSS18.285MiB。两项受测过程CPU合计2.557229秒。prepare遇已有目录立即拒绝。

准备进程实测墙钟1.617804秒、CPU1.583448秒、进程峰RSS794.992MiB；轻量独立验证另记resource_audit，远低600CPU秒/4GiB。浏览/Git/交互编辑没有伪装成连续采样。新公开包为轻量JSON/CSV/Markdown/脚本，无原始数据/权重/完整缓存。所有关键文件SHA在sha256_manifest。

状态保持EXTERNAL_DATUM_UNVERIFIED、SCIENCE_TRAINING_READY=False、RestartFAIL、DART_NOT_ADMITTED、REAL_ORBIT_BLOCKED及历史A14身份。本轮唯一完成的是外部登记咨询的证据闭合准备，不是登记本身。下一步由用户确认收件渠道、姓名单位后决定发送；收到实际官方回复再按预注册矩阵另任务验证。停止，不进入历史代表性诊断、v14或DART。
