# 当前状态
更新时间：阻力接口与TIE-GCM2.0准备阶段完成；实际UTC见logs/drag_tiegcm_delivery.json。
当前阶段：可替换密度/风/气动参数的阻力模块及合成验证完成，28项测试通过；TIE-GCM2.0项目内栈编译链接及4rank官方2002默认单日正常完成。未做真实Swarm阻力对照、未做2023 TIE场；Cd/几何/推进器解释和spin-up等仍待解决。最新记录见末节。

## 初始化时已完成（历史快照）
空目录与路径检查；服务器环境检查；全部规划目录；长期规则/计划/技术路线；本地缓存入口；不含pip的隔离venv；论文与两个Zenodo记录核验；90,106字节源码包下载、MD5校验及静态配置核对。

## 初始化时的问题（历史快照，最新状态见末节）
ensurepip缺失；Python3.12与作者3.10/Windows配置有差异。权重/归一化/测试数据未下载与验证。2023测试集18.15GB，需单独批准或获取小样本。未执行模型推理、训练、真实数据读取、动力学程序或物理实验。模型结果未经过任何项目实测验证。

## 初始化后的入口（历史记录）
先读 AGENTS.md、此文件、WORKLOG.md、docs/RESOURCES.md；source scripts/activate.sh。等待用户下达10月19日后续工作：论文精读与Linux最小依赖方案，明确测试样本获取方式。不得自动推进10月20日或启动训练。

## 2026-10-19正式工作进展（覆盖上文初始化状态）
源码/学习/最小数据/环境文档已建立；.venv310可用、A100 CUDA验证通过、原AFNONet结构构建通过；三个真实小时样本与两套静态包已校验。权重包下载和最终单步验证进行中，最终结果以此文件后续记录及logs/minimal_validation.json为准。原.venv与初始化文档保留，今日没有重训练或完整测试集下载。

## 2026-10-19最终状态：当日任务完成，已停止
- 源码已获取并安全解压，原始代码保持不变，分析及补丁已留档。
- Python3.10.19位于项目内，.venv310可用；torch2.4.1+cu121调用A100成功，63包依赖检查通过。
- 四个权重已下载/校验，Direct严格加载成功；其他三种未运行推理。
- 真实最小样本三帧已通过Range取得，未下载完整18.15GB数据集（81.5GB说法未被当前资源清单证实）。
- Direct在2023-01-04 00→01 UTC单步预测完成，独立指标重算与反归一化检查通过。结果experiments/20261019_minimal_direct/result.npz；逐层指标results/metrics/20261019_direct_one_hour.csv；证据logs/minimal_validation.json、independent_result_checks.json。
- 验证状态：原模型结构/权重/单步运行已验证；多步/全年/磁暴/观测/轨道物理验证未完成。没有训练、动力学开发或10月20日可视化实验。
- 剩余问题：作者训练流程不完整；原配置/索引存在缺陷；Python补丁版本及CUDA runtime与作者环境不同，未跨环境数值比较；原NPZ缺单位元数据，压力层高度映射和ZG用途需核对。测试数据小窗口已取得，不再以“完全无真实数据”作为阻碍。
- 下次入口：先读长期规则与本文件最后一节、WORKLOG最后记录，source scripts/activate310.sh，查看docs/learning_notes/FOURCASTDEN_INTRO.md和logs/data_static_inspection.json。待用户10月20日指令后开展TIE-GCM驱动/变量/坐标/单位学习，读取已有真实样本并绘首张真实密度分布图；暂不新增大规模下载。

## 2026-10-19早会后最终状态（最新）
- 当前主线：第一阶段A=历史TLE/SGP4、B=经验大气/RK45、C=TIE-GCM2.0/RK45，以Swarm精密SP3参考验证；AI复现/改进转第二阶段，替代/效率转第三阶段。
- 今日完成：四份新方案与长期规则/计划更新；Swarm-A三份0203日SP3下载/CRC及SHA256，内部SP3-d/GPS/IGS20，10秒、25920点，连续；8条同星历史TLE取得/校验并冻结t0前最近一条；GFZ小窗口驱动取得；TIE-GCM2.0官方标签源码固定并安全解压，只读检查。
- 最小实验：SP3 reader和概览图完成，5单元测试通过。位置km→m、速度dm/s→m/s已验证；本次无时间尺度/坐标变换、无SGP4/RK45传播、无TIE-GCM编译/仿真、无新包安装和训练。
- 推荐Swarm-A（NORAD39452），48小时候选UTC2023-03-21 00:00:02→03-23 00:00:02；正式GPS/UTC转换、EOP、质量与机动状态仍待核验。TLE来自ETH/CelesTrak归档，Space-Track无凭证401；TLE历元早于t0但当年发布时间未证实。
- 阻碍：Fortran/MPI/NetCDF-Fortran/ESMF与csh工具未就绪；2.0原始IGRF不适用于2015后需官方更新并验证；2023完整驱动/初始场/spin-up未完成；实际质量/姿态面积/Cd和SP3xVAL尚缺。没有凭空填写物理参数。
- 现有FourCastDEN资料、权重、样本、单步结果原样保留，属于已完成工程基础，当前不继续训练/优化。TIE源码third_party/TIEGCM2.0保持原版，更新apex只归档尚未应用。
- 下一次入口：读AGENTS、本文件最新节、WORKLOG早会后记录及四新文档；source scripts/activate310.sh可复查SP3，先查logs/swarm_sp3_inspection.json和swarm_tle_audit.json。待10月20日指令后优先时间/框架/数据质量核验与独立轨道环境准备，不自动沿用旧AI主线日程。

## 2026-10-20最终状态：SGP4基准完成，已停止（最新）
- 已实现SGP4/TEME传播、冻结IERS与GPS/UTC、带速度的TEME/ITRS/GCRS转换、SP3 SI标准结构、RAC与位置差统计；仅今日授权范围，无RK45/TIE-GCM/训练。
- 同一TLE（归档id274764，历元2023-03-20 20:30:00.330336 UTC，起点前3.5004638小时），48小时2023-03-21 00:00:02→03-23 00:00:02 UTC。300秒577点先导通过，60秒2881点正式通过。
- 正式位置差：初始518.729191m，平均625.565892m，3D RMSE763.845573m，采样最大2247.936538m，终点1724.639883m。相对指定SP3产品，不是绝对真值或纯传播误差。
- 13项自动测试通过；IERS-B全覆盖、无SGP4错误/时间错配/非有限点；独立恒星时公式、坐标往返、RAC范数/CSV重算通过。新run-tag重复两采样结果数组及CSV一致。
- 三图results/figures/20261020_sgp4_{orbit_3d,position_error,rac_errors}.png；CSV results/metrics/20261020_sgp4_60s_errors.csv；标准化参考data/processed/swarm_a_sp3_standard_20261020.npz；主报告reports/SGP4_SP3_BASELINE_2026-10-20.md；汇总experiments/20261020_sgp4_60s/summary.json。
- 限制：8条TLE的逐条历史发布时间/抓取时间仍未知，当前仅历史历元前置对照；SP3xVAL/机动情况与参考协方差仍缺；IGS20按ITRF2020对齐ITRS使用，未估计实现偏差，不做厘米级精度声明。
- 复用.venv310，仅新增5个兼容包，无系统安装；入口scripts/activate_orbit.sh。原始SP3/TLE未重下载、未覆盖，既有AI研究不改。发现并在传播前修复ERFA早期闰秒表加载问题，初始失败日志保留。
- 下一次入口：读本节与WORKLOG最新节，先看技术报告和结果汇总；待用户指令再设计RK45二体与守恒/容差验证。加入阻力前需补有来源的质量/姿态迎风面积/Cd，不能自动用经验常数冒充实物参数。今天到此停止。

## RK45两体阶段最终状态（最新，用户授权的下一阶段）
- 完成two_body.py、通用rk45_propagator.py、run_rk45_two_body.py及4项新增测试；全套17项测试通过，复用.venv310，无安装、下载或全局修改。
- 400 km理想圆轨道：理论5553.624271252228 s，计算5553.624271645221 s；单圈闭合0.003185124 m，速度闭合2.95437e-6 m/s；10圈最大采样能量漂移1.51219e-9、角动量向量漂移7.56097e-10。五组容差/步长实验验证收敛。
- Swarm-A原生SP3单历元P/V于2023-03-21 00:00:02 UTC完整ITRS→GCRS转换，无未来拟合和中途修正。连续48小时、60秒2881点：起始约1.16e-10 m，均差2282136.241546 m，RMSE2629254.101844 m，最大/终点4538129.203999 m。
- 基准rtol1e-10，atol位置1e-3 m/速度1e-6 m/s，max_step30 s；5764接受步、34586次函数调用。更严容差/15秒步长的48小时轨迹最大差4.198266 m，是数值收敛证据，不是严格误差界。长时大误差主要反映两体物理不足，不能当作积分算法失败。
- 六图results/figures/rk45_two_body_v1_*.png，轨道/守恒CSV results/metrics/rk45_two_body_v1_*.csv；状态/完整统计experiments/rk45_two_body_v1/；报告reports/RK45_TWO_BODY_BASELINE.md；测试logs/rk45_two_body_tests.log。原始数据与SGP4正式产物SHA256不变。
- 限制：SP3是事后参考，协方差/机动验证缺失；IGS20作为ITRS实现的假设未作额外校准；SGP4历史TLE与RK45 SP3初态不同，不能将对照图解释为积分器排名。
- 下一入口：source scripts/activate_orbit.sh，阅读新报告/summary。等待用户授权后才增加独立J2力项，保持积分器/初始化/评价一致并检查对称轴及进动。当前不开发J2/阻力/TIE-GCM；阻力前仍需质量/姿态面积/Cd来源。到此停止。

## J2阶段最终状态（最新，用户授权范围已完成）
- 新增src/orbit/j2.py、scripts/run_rk45_j2.py、tests/test_j2.py及reports/RK45_J2_BASELINE.md；复用原通用RK45、时间/完整状态转换和评价模块，无已有动力学代码变更、无依赖安装。IERS参数μ=3.986004418e14 SI（不变）、R=6378136.6 m、J2=1.0826359e-3；原文/哈希归档docs/references/j2/。
- 地固ITRS重力对称轴以ERFA c2t06a转入GCRS，冻结IERS-B/闰秒、TT/UT1/xp/yp；不假设GCRS Z恒等地球轴。起点倾角0.128182408°。60秒轴网格插值、中点直接计算及Astropy独立变换核对通过，拒绝越界。
- 22项测试通过（原17+新5），正式传播前门禁通过。赤道J2向内0.012475493 m/s²，轴上向外0.024950986 m/s²（r=6778137 m）；r^-4、势能负梯度、Orekit分量公式和旋转协变通过。固定轴48小时能量/轴向角动量相对漂移2.93296e-9/1.46434e-9；RAAN实测-4.145009913°/天，对比一阶-4.127638009°/天，相差0.420868%。
- Swarm-A同一SP3 t0 P/V、同窗口2023-03-21 00:00:02→03-23 00:00:02 UTC、60秒2881点、同容差/30秒max_step。A数组与保留的两体基准完全一致。B=中心+J2：平均13053.035780 m、3D RMSE16157.482587 m、最大34991.847009 m、终点33772.321699 m；RMSE降低99.385473%，终点降低99.255810%。全部非起点采样改善，仅限本窗口/采样。
- B R/A/C RMSE=430.117159/16150.018370/236.958701 m；残余沿轨MSE占99.907628%，仍有长期负沿轨偏差。不能将未建模残差直接归因于阻力。
- rtol1e-10与1e-12、max_step30/15秒对照：48小时最大状态位置差4.094350 m、速度差0.00457118 m/s，收敛通过。A/B均5764接受步、34586函数调用；各3次积分中位时长约0.902199/3.762573 s（不含EOP/变换/绘图）。
- 六图results/figures/rk45_j2_v1_*.png；逐点误差/收敛和耗时CSV results/metrics/rk45_j2_v1_*.csv；状态/验证/完整汇总experiments/rk45_j2_v1/；测试/主运行/独立重算日志logs/rk45_j2_*。原始轨道、EOP和既有实验/报告/图等62个受保护文件哈希不变。
- 限制：SP3后处理参考、协方差和机动资料不足、框架实现差异；无实测dX/dY修正（与原Astropy保持一致）；牛顿原型尚未处理高精度TCG/TT兼容缩放；静态J2不是完整重力场。下一阶段前先读报告。
- 下一入口：source scripts/activate_orbit.sh；新run-tag可复现。等待用户授权；后续阻力需卫星质量/姿态面积/Cd来源、相对风速及密度单位/时间/高度接口验证，校准和评价区间隔离。当前停止，不自动进入阻力/TIE-GCM/FourCastDEN。

## 大气阻力与TIE-GCM2.0准备阶段（最新，已停止）
- 新增orbit/drag.py、atmosphere/density_interface.py，接口分离密度、相对地面中性风、卫星参数/姿态面积回调；真实框架用冻结EOP的完整GCRS/ITRS速度，不重复扣地球自转；积分器/原引力/J2未改。全套28测试通过，含rho/速度为零、方向/比例/SI/非法值、完整框架共转和轨道能量做功。
- 合成演示（不是Swarm）：m100 kg、A1 m²、Cd2.2、rho1e-12 kg/m³，400 km/3圈，能量变化-72.335582 J/kg、阻力比功-72.337376 J/kg，相对差2.48e-5；更严解最大位置差0.00523623 m。图/CSV/日志/summary保存在drag_synthetic_v1前缀目录，报告reports/DRAG_MODULE_VALIDATION.md。
- Swarm同期官方SC_ADYN 0601三天与DNSAPOD0301三天已取得/CRC/SHA/CDF读取；SC m_SC：03-21为400.337—400.447 kg、03-22为400.341—400.454 kg，正式不确定度未知，不能用473 kg发射质量。A_head/right/left/down是3分量截面相关向量，未核实全部几何/姿态含义；STR同期文件可下载列表已证实但未下载。仍无可直接采用的Cd或β(t)。
- SC_ADYN 03-21/22分别150/59条记录dt_thr>0，f_thr却全0，平台/姿态位标志和03-22的42秒空隙尚待解释，不能断言无机动/净推力。DNS每天2880点/30s，三天validity0，kg/m³；是沿轨事后POD密度、与SP3相关，不是全球预测或独立真值。参数报告docs/SWARM_DRAG_PARAMETERS.md及logs/swarm_*dynamics*、swarm_dns_cdf_audit.json。
- TIE栈在.envs/tiegcm，GNU12.4/OpenMPI5.0.8/NetCDF-C4.9.2/Fortran4.6.1/ESMF8.6.1；74包252.2MB，锁configs/tiegcm-stack-explicit.txt。源355文件与原包逐一相同，3个补丁只放构建覆盖层；nchist局部F77兼容选项已审查。4rank/5°/60s的2002默认单日1440步，returncode0，墙钟152.248519s，两个NetCDF共226636752字节；没有运行2023或多日spin-up。
- DEN实际ilev/g cm^-3、ZG ilev/cm已核验并显式换SI；次历史TN/UN/VN顶层fill dtype导致自动掩码失败，最终检查显式掩码且确认仅顶层。默认场顶448.964—513.086 km，不能保证Swarm460.312—489.989 km全覆盖。400km密度示例图明确2002默认低太阳场，不是2023。短例重跑主双精度有约1e-12K/1e-10cm/s舍入差，次历史DEN/ZG逐位一致；不声称官方benchmark回归。
- 依赖安装异常：初次micromamba create意外登记/root/.conda/environments.txt一行，已终止并改为经源码审查的既有prefix install路径；第二路径前后外部文件SHA/mtime不变。没有擅自外部清理，等待用户对仅删除该登记行的明确授权。事件logs/tiegcm_registry_incident.json。不能宣称本次从未越界。
- 其他初始失败均保留：旧GNU接口/BOZ/iprm尺寸、OpenMPI5无pt2pt组件、单rank60秒限时；4rank短例/单日成功，无运行中进程。cdf只新增cdflib1.3.6于.venv310，不改系统/其他项目/FourCastDEN；历史实验与原始轨道哈希保持不变。
- 新文档：reports/TIEGCM2_ENVIRONMENT.md、DRAG_MODULE_VALIDATION.md；docs/TIEGCM2_EXECUTION_PLAN.md、SWARM_DRAG_PARAMETERS.md、DENSITY_COMPARISON_DESIGN.md。旧TIE方案保留历史状态，当前以新报告为准。
- 下一入口：先读本节/WORKLOG/新报告；等指令处理SC标志/推力/姿态几何及Cd来源，TIE2.0官方2015后IGRF更新和2023驱动/初态/spin-up设计。B/C仅密度替换，共同气动参数/风/引力/积分不改，禁止未来SP3反向拟合。不自动开展真实阻力或2023/长期TIE仿真。


## TIE-GCM 2023适配准备（本次最新状态；系统日期2026-10-19）
- 官方固定提交84185ee0b97307567c78e32ce85643b48a5cc1a9 apex覆盖层已编译链接，experiments/tiegcm2_apex2023_v1；源码实际本来为apex.F90，首次文件名断言失败保留后修正。来源/新旧源/补丁SHA在apex_provenance.json，原third_party树不变，链接无重复apex符号。
- 官方更新含2020/2025主场及2025—2030SV；2023系数插值可用，NCAR的2020系数精度与NOAA DGRF2020小数位不完全一致，不宣称逐项完全相等。独立球谐势梯度核对feldg最大1.956e-5 nT差，验证算法而非独立观测/系数认证。
- 新10分钟2002默认4rank例正常退出2.269776s，不是2023结果；新旧DEN最大差6.939e-18g/cm³、ZG4cm，未要求逐位一致。报告reports/TIEGCM2023_APEX_VALIDATION.md。
- 2023驱动data/processed/tiegcm2023/gpi_20230312_20230325.nc：14日/112条Kp，valid03-14—23，Fobs及中心81日F107A，全部Kp/ap/Ap definitive，太阳API无逐条质量旗标。静态/NetCDF回读及实际rdgpi/getgpi消费者通过，未积分。报告reports/TIEGCM2023_DRIVERS.md，audit/sourcehash在logs；Ap日均一致。使用未来中心平均、事后地磁/姿态/IGRF资料，全部标hindcast。
- 实际util功率/电势公式不同于gpi旧开头注释；真实配置要禁用固定KP/F107/F107A/POWER/CTPOTEN覆盖，GPI日期越界主动拒绝。首次消费者忘设rd_kp、传86400秒日志保留并修正；重复独立读取通过，不是2023仿真。
- 初始化源码支持SOURCE_START选择旧源记录、START_YEAR/DAY设置目标初始日历；尚未实测2023日历适配/启动。3/7天方案docs/TIEGCM2023_INITIALIZATION_SPINUP.md待授权，未运行。当前可准备有限2023启动诊断，不能认为已有可信2023密度。
- 高度风险docs/SWARM_TIEGCM_HEIGHT_COVERAGE.md：真实2023覆盖率N/A；WGS84与ZG基准未闭合、可能超顶，禁止外推。新增保守8角stencil覆盖率检查，不是完整读场/坐标接口。
- 新取得3天STRAATT，保留CRC/SHA清单；3月22日80条/23日10条NaN四元数；q明确S/C→ITRF但标量顺序/符号/机动code4未核实。质量约400.3—400.5kg有记录，无正式sigma；面积投影、Cd和平台/推进器定义仍缺。补充docs/SWARM_DRAG_PARAMETERS_SUPPLEMENT.md。
- A/B/C/D新协议docs/ORBIT_DENSITY_EXPERIMENT_PROTOCOL.md；C/D只换密度，共同风/其他力/参数/初态，不用未来SP3拟合。当前不能开展真实阻力精度结论。
- 本次31项自动测试通过logs/tiegcm2023_all_tests.log；659既有源/实验/数据/报告文件SHA未变logs/tiegcm2023_preservation_check.json；无环境安装、无3/7天spin-up、无2023模型积分、未触碰外部登记记录。
- 下一入口：阅读六份新文档和日志；待用户授权后仅运行有资源上限的2023日历/驱动短段验证，再决定spin-up；并索取/核实ESA产品定义、Cd和面积/机动。当前任务结束停止。


## GitHub仓库提交准备（2026-10-19，最新）
- 按用户要求在唯一工作区内建立.git，分支main，origin=https://github.com/hhtbbc/261016project.git；无强推、无其他仓库改动。
- 已提交自研代码/测试、文档/报告、配置/补丁、图表/CSV、轻量实验与审计记录；.gitignore排除环境/缓存/临时、原始数据、第三方完整树、模型权重及编译/大状态文件，全部原文件仍在本地。资产清单configs/external-assets.json列出566文件共6221218821字节；并非完整数据备份。
- 增加docs/REPOSITORY_GUIDE.md、README最新入口与Orekit官方原LICENSE/NOTICE；Git提交身份仅项目内配置hhtbbc/254247411+hhtbbc@users.noreply.github.com，无全局Git配置修改。
- 首次push失败：VS Code认证socket ECONNREFUSED、GitHub No anonymous write access / Authentication failed；本地日志logs/github_push_initial.log。没有可用SSH客户端/agent工具。**尚未推送成功**，等待用户在服务器/VS Code恢复GitHub写入认证，不能将公开只读访问当作写权限。
- 完成常见凭据模式/文件体积/外指链接扫描，未发现命中；仅为发布检查，未重跑物理仿真，现有31项测试日志保留。归档参考及原始补丁有既存空白告警，未改写原资料。
- 下一入口：恢复认证后source scripts/activate_orbit.sh；git push -u origin main；比对git ls-remote origin refs/heads/main与git rev-parse HEAD，然后补记成功状态。当前科研阶段和未解决物理条件不变。


## GitHub推送成功（2026-10-19，最新）
- 用户恢复登录后，旧会话仍引用失效认证socket；只在本次Git进程环境中改用同一用户的当前有效VS Code认证通道，未修改全局配置/存储凭据。
- git push -u origin main返回0；首次成功的本地与远端main均为b6c284cb181a83b48688f4bdbc18e8b4132ac69f，已实际比对。目标https://github.com/hhtbbc/261016project。
- 本条及仓库说明补记一并提交推送；最终HEAD/远端一致性记录本地logs/github_push_verification.log。科研代码/数据/实验未改，原始数据、模型、环境等继续留在本地。
- 推送已完成，后续科研任务仍等待用户指令。
