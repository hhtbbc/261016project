# Swarm-A大气阻力参数核查

## 结论

找到同期ESA官方SC_ADYN动态产品的质量和截面积相关向量，并取得DNSAPOD密度。质量正式不确定度、截面积向量的完整几何/姿态约定、可直接采用的Cd与推进器活动解释尚未闭合。因此本次不运行Swarm-A阻力精度实验，不用未来SP3反向拟合参数。

## 质量：已取得2023同期产品，不采用发射质量

[ESA任务事实页](https://www.esa.int/Applications/Observing_the_Earth/FutureEO/Swarm/Facts_and_figures)列发射质量473 kg（含106 kg推进剂）。这是2013年发射条件，不能替代2023年实际质量。

通过[ESA公开数据服务](https://swarm-diss.eo.esa.int/)实际列举Level1b/Latest_baselines/SC_xDYN/Sat_A，下载2023-03-21、22、23的0601版SC_ADYN ZIP，分别约3.58、3.56、3.62 MB，CRC与SHA256已核验。CDF字段m_SC明确标注Actual mass of S/C，单位kg；不是本项目猜测值。

|日期|记录数|m_SC最小(kg)|最大(kg)|首记录质量(kg)|
|---|---:|---:|---:|---:|
|20230321|86400|400.337|400.447|400.383|
|20230322|86319|400.341|400.454|400.399|
|20230323|86390|400.331|400.459|400.358|

这些是事后重处理动态产品的记录值，非质量校准真值；CDF未给出可直接采用的m_SC标准不确定度。日内变化范围不能冒充误差条，也不能据此解释真实质量非单调变化。质量数据不是t0前冻结的运营预测参数，后续使用必须标注回溯实验条件。完整CDF属性、质量/标志/推进器统计见logs/swarm_dynamics_summary.json、swarm_drag_parameter_findings.json；原始产品路径、SHA见data/raw/swarm_drag/dynamics_attitude_manifest.json。

## 几何、姿态及迎风面积

ESA事实页列外形总长9.1 m（含4 m展开杆）、宽1.5 m、高0.85 m。不能把外包络矩形面积当作实际迎风面积。

官方动态CDF含A_head、A_right、A_left、A_down，均为N×3，单位m²，说明为orbit frame中front/right/left/down截面。存在负分量，显然不能把某个分量的最大值或绝对值直接作为标量A。这些字段可作为下一步几何计算的线索，但本次未核实完整面元朝向、遮挡和表面气动约定，不将它们直接接到阻力程序。

同服务已确认2023-03-21—23的STRAATT_1B 0601 ZIP存在，各约2.77 MB；只核验了列表，未下载或解析四元数。运行姿态应以同期星敏姿态、质量标志和姿态模式为依据，不能假定全年固定LVLH指向。动态产品有非零Flags_Platform/Flags_q，位定义尚待任务产品规范解释。03-22动态记录存在3段>1.5秒空隙（最大42 s），不得静默跨越后当连续已验证姿态。

已知面元面积S_i、卫星本体系外法向n_i、正确方向的姿态四元数后，应先把相对流速转入本体系，再计算暴露面的投影。对不自遮挡的理想凸面元，几何迎风面积为Σ S_i max(0,n_i·vhat_rel)。复杂面元需考虑遮挡；有升力/切向气动力时，一个标量Cd*A模型本身是近似。四元数顺序、旋转方向、本体系/轨道系定义必须先核实。

[ESA几何与热光学文档](https://earth.esa.int/eogateway/documents/20142/37627/swarm-thermo-optical-properties-and-external-geometry.pdf)本次HTTP403，未读到正文，不声称已取得几何模型。[TU Delft模型站点](https://orbits.tudelft.nl/)说明有公开几何/气动模型，但本次直接连接超时，模型未下载，许可和具体模型版本仍需核实。没有绕过访问限制。

## Cd与弹道系数

[Swarm密度与风反演原始研究](https://link.springer.com/article/10.5047/eps.2013.08.003)明确需要卫星姿态、几何及自由分子流气体表面相互作用模型；[高保真几何研究](https://www.sciencedirect.com/science/article/pii/S0273117718305714)进一步讨论几何模型对气动系数一致性的影响。Cd不是只由卫星名称决定的常数，还依赖相对速度、温度、组成、壁温和表面动量/能量交换假设。

本次未核验一个适用于2023本窗口、与指定参考面积配套的Cd时间序列或固定Cd。演示代码中的2.2只用于合成验证。也未取得可直接采用的公开β(t)产品；应明确β=m/(Cd*A)，单位kg/m²，而有些资料使用其倒数。CDF质量/截面字段本身不提供Cd。TLE BSTAR是SGP4有效拟合参数，不能未经模型/单位转换直接当本力模型的物理弹道系数。

## 同期DNSAPOD：取得并读到真实数据

来源：ESA Level2daily/Latest_baselines/DNS/POD/Sat_A；0301版三个ZIP共418465字节，CRC/SHA和解压成员已记录在data/raw/swarm_drag/dns_manifest.json。CDF实际读取成功，新增cdflib1.3.6于项目.venv310，未改变原numpy等依赖，锁文件configs/requirements-drag-20261019.lock.txt。

每天2880点，time字段CDF_EPOCH，UTC日界00:00:00—23:59:30，间隔30秒；density与density_orbitmean单位kg/m³，validity_flag三天均0（nominal）。真实属性、范围和时间见logs/swarm_dns_cdf_audit.json。03-21 density约9.805e-13—1.666e-12 kg/m³；03-22约1.032e-12—1.782e-12；03-23约9.048e-13—3.467e-12。完整第三天主要用于公共窗口右端支持，不把其整天当作48小时评价区间。

[产品说明](https://swarm-disc.github.io/product-catalogue-tools/SW_DNSxPOD_2_.html)说明密度由POD非引力加速度反演，并依赖MODx_SC、STRxATT、SC_xDYN等输入。它与SP3轨道共享GPS/POD信息，不能作为完全独立的密度/轨道真值，也不能把轨迹上一维事后密度插值冒充任意位置的三维预测大气。可用于后续密度诊断，但未用于本次传播、拟合或所谓真实阻力精度结论。

## 推力/姿态变化：不能假定没有

03-21、03-22的dt_thr（单位s、12通道）分别有150与59条记录至少一个通道>0，最大单记录0.109/0.122 s。03-23全日另有128条，不能把全部算入本次48小时窗口。记录数不等于独立机动次数；可能包括姿态控制，不能直接推断轨道净Δv。f_thr三个分量均为0，与非零开启时间存在需核实的解释问题，故不能据此排除推力，也不能直接积分出净推力。

下一步需解码平台/姿态/推进器标志，核对任务机动日志或产品DQC，区分实际推力、姿态控制和记录质量。当前不擅自删点、调整初态或根据未来SP3估计脉冲。

## 对后续实验的影响

阻力幅值含rho*Cd*A/m，参数偏差与密度偏差高度混淆。必须先解决Cd/几何/姿态与推力污染，给出可追溯参数和不确定性/敏感性范围，再做真实A/B/C轨道比较。缺失项以null/未核验记录，不用“常见值”补齐。若校准，只用t0前独立数据并冻结，验证窗口不得反复利用。
