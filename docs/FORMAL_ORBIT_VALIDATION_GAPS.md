# 正式轨道验证缺口及本次复核

本次仅PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST集成演示，不能替代以下正式门禁；没有安装经验模型、获取新的大气仿真或利用SP3/DNS拟合参数。

## 1. 模型高度与纬度登记

重新核查[NCAR官方ZCoordinates.pdf](https://download.hao.ucar.edu/pub/stans/tgcm/ZCoordinates.pdf)，并复用已归档PDF及原addiag/lbc/getapex源码。DEN在ilev、ZG用于几何高度登记已明确；默认zbound加GSWM下边界与WGS84零面/整个模型纬度的严格可逆关系仍未给出。A/B仍是独立假设，正式原生提供器的外部入口必须EXTERNAL_DATUM_UNVERIFIED，不因本次积分运行成功放开。

原生几何登记的数学实现已验证，不等于外部参考面准确度。详细证据、PDF SHA和默认半径的区别见TIEGCM_SWARM_COORDINATE_DATUM.md。

## 2. 真实气动、姿态和机动

复用已取得SC_ADYN/STRAATT，而非重新下载。专门检查本次2023-03-21 00:00:02至06:00:02窗口，结果存experiments/provisional_drag_orbit_v1/window_parameter_review.json：

- SC_ADYN有21600记录，m_SC约400.338—400.447kg，SyncStatus均0；这不是正式质量不确定度。本次力模型仍固定合成400kg，未将实物记录用于校准。
- 同窗口dt_thr至少一通道非零的记录22条，最大单条0.106s，f_thr仍全0；Flags_Platform有0和16。不能据此推断净Δv、排除姿控推力或把22条当22次独立机动。
- STRAATT有21601记录，有限四元数范数约0.999999999148—1.000000000875，无NaN；Maneuver_Id均0。但SyncStatus有26条非零、Flags_q含多种值，且未取得可靠位定义。Maneuver_Id=0与非零dt_thr并不构成已解释的“无推力”证据。
- q属性只明确ITRF <- S/C，仍缺四元数标量顺序、主动/被动约定与产品具体旋转公式；A_head/right/left/down为orbit frame向量，需要明确ORB基底、遮挡/面积投影及与姿态的关系。不能将向量绝对值求和或重复旋转。
- 未落实与几何、参考面积及气体表面相互作用一致的Cd/弹道参数。合成Cd=2.2、A=1m²不构成真实Swarm参数。

CDF_EPOCH按产品UTC日历解释，并与HDR Sensing_Start核对：SC_ADYN相差−0.804ms（原CDF毫秒表达与HDR微秒表达），STRAATT为0；不套GPS偏移。以上仅用于资料核查，不改SP3初态或力模型。

本次尝试的Swarm产品目录入口未能通过网页工具访问，搜索也未得到可核验的机动码/面积定义正文；不能宣称已读到新的官方定义，更不能把未访问的猜测URL当证据。继续复用此前产品规范HTTP403/几何资料访问阻碍记录，后续应以实际Ref_Doc SW-RS-DSC-SY-0007和同期辅助机动表为准。

## 3. 经验大气对照的明确输入

本次可访问[pymsis作者API文档](https://swxtrec.github.io/pymsis/reference/generated/pymsis.msis.calculate.html)，文档标识0.12.0：输入为WGS84大地经纬度与km高度，输出质量密度kg/m³；F107取前一日，F107A为当日居中81日平均，通量按日地距离而非归一到1AU；暴时Ap模式需要当前及历史3小时值和较早区间均值。缺省驱动会触发历史数据下载/缓存，正式实验应改为显式输入和项目内冻结。模型版本（0/2.0/2.1）和开关必须另行固定。本次未安装或运行，不能称已通过接口/物理验证。

已有TIE-GCM的Kp不能直接作为MSIS的Ap；原始GFZ可能包含所需信息，但须独立检查Ap字段、57小时历史、时滞和质量。现有居中81日和事后驱动使后续对照仍为hindcast。经验模型的坐标定义可明确，并不能反向证明TIE-GCM的ZG严格等同WGS84。

## 4. 初始场、分辨率及完整受力

S3/S7不同预热历史的差异不是外部准确度误差；S7也未证明充分初态无关。优先同起日不同合法官方完整初场；更早启动须扩展真实驱动padding，不自动使用未验证Restart。10分钟保存场需同一连续仿真的高频参考，现有时间插值方案差小并非时间欠采样误差已小。

中心+J2仍缺高阶重力、日月引力、辐射压及潜在推力等。当前GCRS/IGS20→ITRS实现、未加实测dX/dY和完整坐标时缩放的既有原型约定也应与目标精度一致复核。SP3是有质量限制的后处理参考，不是绝对真值。

## 5. 何时可以开展正式对比

需冻结可信参考登记/覆盖策略、实际参数与质量掩码、机动/推力处理、密度版本与驱动、共同风场、受力和数值设置。然后用单历元SP3初态、独立后续参考做同源条件对比；历史TLE/SGP4另报初始化区别。任何校准必须在验证前窗口并冻结，不能利用未来SP3后再评价同一窗口。当前演示只支持软件集成和条件动力学敏感性结论。
