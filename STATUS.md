# 当前状态

> 最新（2026-10-22）：两日期四模型连续6h完成，48正式forward+1短例、232测试；增强活动窗出现History中段/log末段条件优势，12/24h仅设计。

> 最新（2026-10-22）：五日期四模型统一01时短窗完成，新增16序列32forward、Jan4只读，226测试；6h仅设计，未训练/轨道。

> 最新（2026-10-22）：History首次复现及四模型统一01时基线完成，221测试通过。单窗History未优于Direct，详见末节；无训练或扩窗。

> 最新：五日期官方log-DEN及三模型共同物理评价完成，215测试通过；log全层绝对指标改善但高层相对指标未改善。无训练或扩窗。

> 最新（2026-10-22）：五日期Direct/Flow两小时检查完成，新增8序列/16forward，206测试通过；log-DEN仅静态审查，未训练或扩窗。

> 最新（2026-10-22）：官方Flow两小时复现及Direct/Flow同窗对照完成；198测试通过。尚无总体模型优劣或真实大气/轨道精度结论。

> 最新：第一阶段工程/条件成果已整理，正式科学验收待完成；FourCastDEN Direct两小时自回归已完成，第二阶段A启动，未训练。详见末节。

> 最新：统一H6的C0—C3六小时条件密度对照完成，详见末节及COMMON_FORCE_DENSITY_ORBIT_COMPARISON。正式物理精度门禁仍保留。

> 最新状态：H6六小时数值门禁完成，共同配置仅供PROVISIONAL条件实验；详见本文末节。以下早期摘要保留作历史记录。
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


## 2023首次真实日历启动验证（2026-10-19，最新）
- 用户只授权一次10分钟；已执行且停止：experiments/tiegcm2023_startup_10min_v1，START_YEAR2023/DOY77，SOURCE_START80 0 0只读2002初猜；4rank、60秒、10步、5°，未修改原源码/restart，未下载/安装环境。
- returncode0、NORMAL EXIT，墙钟2.396588s，采样进程树RSS峰987189248字节（共享页重复计入/可能漏瞬时峰），两NetCDF67015120字节；60s超时/16GiB合计RSS/8GiB进程地址/512MiB输出/10GiB余盘门槛未触发，退出无残留模型进程。
- 日历输出2023-03-18 00:00/00:05/00:10，day77/calendar_advance1。apex更新对象实际调用年份2023；GPI首步实际请求2023/77/60s。10个分钟日志/5与10分钟主次历史驱动核对通过，最大double差2.8422e-14，Kp2、POWER27.03880839GW、CTPOTEN48.2kV；00:10 F107137.07058677/F107A161.80066164。
- 关键启动限制：t=0仍继承restart F107/F107A70、POWER18/CTPOTEN30，Kp缺失；从首步60s才用实际2023 GPI。不得将t0当2023驱动/平衡场，也不是固定配置覆盖。原日志CTPOTEN有旧Volts误标签，NetCDF/公式为kV。
- DEN/ZG/TN/UN/VN/主成分基础检查通过：DEN全垂直域1.34999648e-13—1.19784682e-6kg/m³；TN147.773—787.067K；高度递增。5/10分钟顶高449.03812—510.97656/449.09100—512.38628km，仍有Swarm超顶风险。TN/风顶层padding显式掩码；成分顶层有值，不套同一掩码，主要mmr和≈1。
- 相同apex.o独立subsol函数核对Astropy太阳/EOP通过（不是第二次模型运行/不是运行内太阳打点）；最大纬/经差0.00076531/0.00771561deg。原整数年apex初映射/分数年推进和太阳近似保留，未声称完整科学验证。
- 新脚本run_tiegcm2023_diagnostic.py、audit_tiegcm2023_diagnostic.py、check_tiegcm2023_solar.py、plot_tiegcm2023_diagnostic.py；新4项门禁测试，合计35测试通过。一次launch_once拒绝同目录再次启动，所有新产物拒绝覆盖。
- 首次静态错要求restart含N2、首次审计错将温度顶层掩码要求套到成分、太阳探针初次缺src导入路径：均已定位修正并保留失败说明/日志，未重复模型积分。659历史保护文件SHA未变。
- 新报告reports/TIEGCM2023_STARTUP_DIAGNOSTIC.md、决策docs/TIEGCM2023_SPINUP_DECISION.md；原生ZG顶高/400km诊断图results/figures/tiegcm2023_startup_10min_v1_native_fields.png，明确NOT spun up。审计JSON/配置在运行目录；完整小日志和测试可入库，大NetCDF仍本地。
- 决策：短时启动基础工程条件通过，尚未证明跨日/续算/多日稳定性和spin-up收敛；建议另授权有限更长/跨日续算兼容性验证，3/7天仍仅候选。Swarm参数/高度基准/机动风险未解决，不运行真实阻力或spin-up。
- 本次按新增长期GitHub规则安全提交并推送main；最终提交/远端一致性见本地logs/tiegcm2023_startup_github_verification.log，认证/冲突失败必须如实报告。科研范围到此停止。


## 2023跨日/Restart静态阻碍（2026-10-19，最新）
- 本次用户最多授权A连续20分钟+B1十分钟+B2十分钟；**实际启动0次**。原input.F948—960要求START与SOURCE_START时/分一致，只有日可不同。原2002场仅80 0 0，目标77 23 50不合法；将SOURCE_START改80 23 50也没有可读记录。没有修改原源码/重标时间/拼接状态/伪造_NM，也未追加预积分。
- 已检查data/experiments全部13个带mtime NetCDF，无23:50完整primary；logs/tiegcm2023_restart_inventory.json。可执行、GPI与原场SHA匹配前次成功诊断，logs/tiegcm2023_restart_asset_check.json。旧659保护文件与前次2023两NetCDF SHA不变，logs/tiegcm2023_restart_preservation.json。
- primary完整结构34项：当前预报/诊断状态、10个_NM和6个下边界，float64；原文件结构合格不代表续算数值已验证。次历史不够。官方continuation路径是省略SOURCE、从OUTPUT按START检索完整主历史、保留initial_year/day/mtime并append；未来在独立目录使用完整checkpoint字节快照且保留原B1，不能只靠显式SOURCE重置origin就声称严格等价。
- 新增src/atmosphere/restart_validation.py、tests/test_tiegcm2023_restart.py（7测试）；scripts/run_tiegcm2023_restart_validation.py是**仅静态准备入口，没有模型启动功能**，输出experiments/tiegcm2023_restart_static_v1/{static_audit,comparison_rules,tolerance_sensitivity}.json；A/B1/B2均DRAFT_NOT_RUN。全套42测试6.763s通过，logs/tiegcm2023_restart_all_tests.log。
- 预注册float64 rtol1e-10/float32 1e-6及按SI物理量的atol；算术ULP敏感性检查而非模型数值敏感性实测。连续与分段实际DEN/ZG/TN/风/成分误差、跨日稳定性均N/A。只生成状态CSV与输入推导驱动期望CSV，未做伪零差图表。零点期望F107141.04375、F107A161.7550154321、Kp1.5、POWER22.3223714449GW、CTPOTEN39.3kV，尚非模型读取记录。
- 报告reports/TIEGCM2023_RESTART_VALIDATION.md、决策docs/TIEGCM2023_SPINUP_READY.md。阻碍为合法起始状态，不是资源已超限；三段预计约260MiB输出、各数秒，预算已登记但未实测。
- 下一步优先提供/取得合法23:50完整主历史；如需从现有初猜生成，建议另授权一次2002默认00:00→23:50准备运行，1430步/4rank、只存完整主历史初末约34MB、预计151s，墙钟上限申请300s。它是额外准备启动、超过本次最多3次及90s限制，未运行。不能宣布多日spin-up就绪。
- 按长期规则提交/推送本次静态结果；实际HEAD/远端核对见本地logs/tiegcm2023_restart_github_verification.log，失败不得声称成功。本次科研工作停止，等待解除源时刻阻碍；不运行spin-up/Swarm真实阻力。


## 2023合法23:50检查点与跨日连续诊断（最新）
- 按最新授权仅一次2023-03-18 00:00→03-19 00:10积分：experiments/tiegcm2023_crossday_24h10_v1，4rank/5°/60s、1450步，returncode0、4条NORMAL EXIT，墙钟155.014390s。没有续算分支/额外重试/3或7天spin-up。
- 使用原合法SOURCE_START80 0 0与目标77 0 0；连续START/STOP/HIST相接序列配合MXHIST_PRIM1，模型原生写出四个单记录完整primary（00:00、23:50、次日00:00、00:10）；次历史仅末3时刻。primary_002.nc即合法23:50独立checkpoint，16993204B，SHA d0aab5804eeab7680977f0fa9ad1de165600fd884bde2ddc1e0c6754c5ab9a4f，无未来记录，无裁剪/重标/伪造_NM。
- 检查点34项float64状态/前一时间层/下边界、维度/单位/有限值/时间属性通过；year2023/day77/mtime77 23 50、initial_year/day/mtime2023/77/(77 0 0)。源码continuation输入前提成立，但实际恢复与连续/分段一致性仍未测试。未来只能对完整checkpoint副本原生无SOURCE续算并保留原文件。
- GPI实际跨日通过：00:00 F107141.04375、F107A161.755015432099、Kp1.5、POWER22.3223714448845GW、CTPOTEN39.3kV；145个独立runtime打印和3目标时刻主/次历史核对通过，double差最大2.8422e-14。冷初始echo仍带F10770/旧iter115200，暖态iter112310/112320/112330与日历一致，未改初始元数据。
- DEN全域9.4387654e-14—1.19825849e-6kg/m³、正有限；ZG逐列递增；TN有效147.417—1108.968K；主要mmr约和1；TN/风及_NM顶层padding显式mask，34主状态无NaN/Inf，日志无异常模式。末3时刻顶高545.36448—677.24912km范围，较冷场抬升；不是03-21—23的Swarm实际覆盖率，ZG/WGS84未核实，不能宣称沿轨查询全有效。
- 峰采样进程树RSS990973952B≈945.07MiB（共享页重计/可能漏瞬态），NetCDF92072344B≈87.807MiB；总输出512MiB/RSS16GiB/余盘20GiB/墙钟300s均未触发；每进程CPU300s，已替换旧60s限制；无GPU，无残留模型进程。963份旧文件哈希未变，原始2002场/可执行/GPI/apex哈希匹配，冷初始34字段与此前诊断逐位相同。
- 新run/audit/plot_tiegcm2023_crossday.py、src/atmosphere/tiegcm_drivers.py与8项新测试；全50项6.582s通过。报告reports/TIEGCM2023_CROSSDAY_DIAGNOSTIC.md、方案docs/TIEGCM2023_RESTART_NEXT_STEP.md；配置/审计/资源/未来分支草案JSON在运行目录；真实驱动CSV/图在results，原始NetCDF留本地。
- 下一步需新授权两个10分钟原生continuation分支B1（23:50→00:00）、B2（00:00→00:10），只比较本次保存的共同时刻；禁止把包含未来记录的连续参考放进可写OUTPUT。尚不宣布spin-up收敛/多日工程全通过，Swarm气动/机动/高度基准风险仍在。本次停止，安全GitHub同步结果见本地logs/tiegcm2023_crossday_github_verification.log。

## 最新任务：2023原生continuation验证（2026-10-19会话）
B1仅启动1次，2.183秒正常退出，时间/驱动/10步通过；完整primary 28/34超差，6项下边界相同，共同secondary 9/9超差。B2按门禁未运行。原23:50检查点及989项既有科学文件核验未变。56项自动化测试通过。当前不具备正式分段spin-up等价性条件；下一入口为reports/TIEGCM2023_CONTINUATION_VALIDATION.md与docs/TIEGCM2023_SPINUP_READY.md，等待授权定位原生电动力内部状态重建差异。未做spin-up/Swarm阻力实验。

## 最新：Restart源码定位与连续spin-up备用方案（2026-10-19）
仅只读分析，新增模型积分0次、编译0次。已确认磁势/POTEN映射、istep首步电场重建及上下边界赋值路径不同，尚未证明唯一根因。B1失败与B2未运行保持不变。新报告TIEGCM2023_RESTART_ROOT_CAUSE_ANALYSIS.md，备用docs/TIEGCM2023_CONTINUOUS_SPINUP_PLAN.md；模型/源/数据哈希及驱动覆盖静态复核见experiments/tiegcm2023_restart_analysis_v1/static_audit.json。推荐C：优先另授权S3连续5天10分，Restart限时诊断并行。S3/S7线性墙钟约771/1387秒，输出约2.47/2.57GB，均非实测；本次未生成运行器、补丁或运行命令。等待下一条授权。

## 最新：S3连续多日运行完成（2026-10-20收尾）
实际一次S3，2023-03-18 00:00→03-23 00:10，7210步/4rank/5°/60s，正常退出；墙钟786.805456秒，合并监控峰RSS947.293MiB，NetCDF2471152364B，最大卷192668980B。完整7主历史、293次历史时间记录，共同窗口290帧通过独立审计；冷00:00诊断未计算标N/A，292有效物理统计帧。721个runtime GPI打印/存储驱动核验通过，既有科学文件哈希未变。监控接管原因为冷echo误报风险，模型同一进程组连续运行，未重新启动。
63项测试通过，六张真实图及CSV完成。目标原生顶层ZG586.8335—741.1446km，Swarm WGS84高460.3115—489.9890km，基准未统一，精确沿轨有效率N/A。Swarm窗口浮点端点已用1微秒门限复核为17281样本，Swarm_window_review.json取代初稿相关字段。报告reports/TIEGCM2023_S3_RUN.md与S3_DATA_AUDIT.md；下次入口docs/TIEGCM2023_S3_S7_COMPARISON_PLAN.md。可以申请S7作敏感性对照，未证明3天收敛，未运行S7/轨道阻力/Restart修复。

日报入口：reports/DAILY_REPORT_2026-10-19.md，已区分当日执行与次日补充验收；科研状态不变。

## 最新：S7与S3/S7预热敏感性（2026-10-20）
一次S7从03-14 00:00至03-23 00:10，12970步、4rank/5°/60s；墙钟1382.676454秒，RSS峰944.566MiB，NetCDF2571233644B，11主历史/297次历史时刻（共同290）独立验收通过。无guardian、重试、continuation或新增轨道积分。冷echo DEN/ZG/N2限制性掩码逻辑经测试，76项测试通过。
S3/S7初始34物理字段逐位相同、26输出字段/公共网格和驱动一致。450km原生ZG全窗口密度RMSE7.6111e-14kg/m³、P95相对差5.980%；0→48h全球P95从6.601%降至4.016%。最后24h固定高度200—400km分区门槛通过，450/475/500km仍失败；TN/组分压力层门槛亦未通过，风矢量20m/s通过。3天预热未满足全部工程判据，不能称7天是真值。
两组目标原生顶高约587—741km/592—750km，Swarm椭球高约460—490km；高度基准仍未闭合，精确沿轨查询有效率N/A。数据/图/趋势/门禁详见reports/TIEGCM2023_S7_RUN.md、S7_DATA_AUDIT.md、S3_S7_COMPARISON.md。下一入口docs/TIEGCM2023_NEXT_STAGE_DECISION.md：优先高度登记与同起日不同合法初态设计；不自动更长预热/Restart修复/AI训练/真实阻力实验。

## 最新：原生ZG密度查询接口与外部坐标门禁（2026-10-20）
新增TiegcmDensityProvider，S3/S7共同290帧通过同一接口按需读取，八个时空列保守检查、垂直log密度/水平及时间线性密度、经度周期、极冠拒绝、单位转换和有界缓存。18项新测试通过，全套94项通过；46个原NetCDF前后SHA均匹配。每源1000次实际原生查询：S3平均11.292ms/P95 15.624ms，S7平均11.089ms/P95 15.401ms；进程峰RSS89.668/97.707MiB。线性垂直相对log方案差异P95约3.483%/3.493%，不是实际密度误差。
Swarm窗口17281点和WGS84坐标已复用原入口核对，但ZG下边界零面/纬度与WGS84严格关系仍未闭合，外部查询显式EXTERNAL_DATUM_UNVERIFIED，真实沿轨有效率/顶层裕量/密度曲线N/A。没有模型积分、真实阻力传播、训练或新依赖。工程接口完成，不代表物理适配完成。
入口reports/TIEGCM_DENSITY_INTERFACE_VALIDATION.md、SWARM_TIEGCM_COVERAGE_AUDIT.md，理论docs/TIEGCM_SWARM_COORDINATE_DATUM.md，离线证据experiments/tiegcm_density_interface_v2/audit.json。后续优先官方参考面澄清与同起日不同合法完整初场设计，具体见TIEGCM_NEXT_SPINUP_EXPERIMENT.md；任何新模型/轨道积分均待授权。本次结束后按规则同步GitHub并停止。

## 最新：PROVISIONAL Swarm坐标与沿轨密度敏感性（2026-10-20）
新增独立探索适配器及14项测试，正式密度/外部查询代码SHA保持不变，外部仍EXTERNAL_DATUM_UNVERIFIED；全套108项通过。官方ZCoordinates.pdf新增明确证据DEN在ilev，下边界实际为默认zbound+GSWM，仍没有严格WGS84零面转换。
粗采样577点×8假设×S3/S7共9232次，全部条件有效；通过后仅A0/B两映射完成17281个10秒点/源，共69124次，均条件有效，正式覆盖率仍N/A。S3/S7相对密度差P95为A6.0445%、B5.9749%，log RMSE0.048134/0.047789；这些不改变预热未全部通过的结论。A上−10/+10km人为扰动使密度中位数约+17.5%/−14.8%，不是已知高度误差范围。
完整A/B映射密度差P95约24%；粗采样拆分显示高度替换约24.1—24.3%，纬度替换约0.084%。A条件全轨迹垂直线性相对log插值P95约3.49/3.52%，不能当真实插值误差。29次经度接缝和高纬记录保留，未外推/补零/平滑。
粗/完整离线阶段32.074/162.686秒，累计峰RSS186.961MiB，主CSV47.18MB（全10秒表留data/processed，不上传）。54文件前后保护、3份SP3与旧审计哈希、独立前向WGS84几何/时间校验通过。报告SWARM_PROVISIONAL_DENSITY_ANALYSIS.md、TIEGCM_DENSITY_UNCERTAINTY.md，集成门禁ORBIT_DRAG_INTEGRATION_READINESS.md，证据experiments/swarm_provisional_v1。未启动新大气/轨道积分或训练。下一步优先官方登记、不同合法初场和气动/机动定义；任何新积分等待授权。按规则同步GitHub后停止。

## 最新：TIE-GCM密度接入RK45的探索实验完成（2026-10-20）
新增隔离ProvisionalDragForce，复用全部原时间/完整速度/J2/RK45/密度插值，正式外部接口拒绝行为和核心文件SHA不变。显式合成参数m400kg/Cd2.2/A1m²、共转零地固风，三重标记PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST。新增6项测试，全套114项通过。
1h D0/D2及各tight门禁通过：最大阻力响应2.937451m，配对收敛差3.4087e-5m。随后D0—D4五组6h完成，另D0/D1/D2/D4四组tight；共13次真实初态探索传播，无失败重试或新大气积分。D1/D2终点差6.741712m，D3/D4差7.053848m；D1/D3映射差5.818585m，D2/D4差6.130734m。D1—D4对D0终点扰动109.588/116.330/115.407/122.461m，沿轨为主，均不是预测误差。阻力模约1.11e-7—2.12e-7m/s²。
6h抽查单轨基准/tight差约0.0584m，源/映射配对差收敛变化2.49e-5/5.02e-5m，冻结门槛通过；D3未单独tight，不泛化全面证明。45594次内部及2649次输出密度查询全有效、失败0；41次接缝邻列/2614次高纬查询通过审计。模型阶段1389.205s，峰RSS182.559MiB；计算后会话等待不计模型耗时，离线审计另19.579s。55项保护文件及旧SP3 SHA核验通过，原J2结果不覆盖。
交付报告PROVISIONAL_DRAG_ORBIT_EXPERIMENT.md、PROVISIONAL_DRAG_NUMERICAL_VALIDATION.md，缺口FORMAL_ORBIT_VALIDATION_GAPS.md，6张三重标签图、状态/模型差/资源CSV及experiments/provisional_drag_orbit_v1审计。原始逐查询压缩日志和NPZ约26.85MB留本地data/processed不上传。新核查6h窗口有22条非零dt_thr、f_thr全0、Maneuver_Id全0但质量位未解释；未用于拟合。正式高度登记、Cd/面积/姿态/推力、完整受力及高频场/初态敏感性仍未闭合。同步GitHub后停止，不继续48h或新的模型任务。

## 2026-10-20最新：NRLMSIS经验密度离线基准完成，等待指令

- pymsis0.13.0安装于既有.venv310，NRLMSIS固定2.1；70包依赖兼容，TIE环境未改。新接口支持显式冻结GFZ驱动、WGS84/ITRS和批量查询，失败报错；正式TIE外部门禁保持拒绝。
- 前日Fobs、目标日中心81日平均及7项Ap历史完整，ap/Ap均def，太阳API逐值质量未知；32条03-20—23边界审计通过，HINDCAST，不用Kp代替Ap，不走默认联网路径。
- 6小时SP3离线诊断：先73个300秒点，后361个60秒点，全有效；NRLMSIS密度1.129333e-12—1.805477e-12kg/m³，中位1.580192e-12。
- TIE相对NRLMSIS中位差S3/A−37.320%、S7/A−33.426%、S3/B−32.823%、S7/B−28.944%；全部TIE条件比较PROVISIONAL，不排名真实性。原46个NetCDF及2个查询CSV前后SHA相符。
- 全套126测试通过（新增12）；上游预存Fortran参考200行密度相对差最大0.043714%，低于其原0.2%舍入标准，不是观测精度。361点批量0.3405秒，标量均值2.026ms/P952.314ms，分析进程峰162.590MiB。
- 入口：reports/NRLMSIS_2023_DRIVERS.md、NRLMSIS_DENSITY_VALIDATION.md、NRLMSIS_TIEGCM_COMPARISON.md；audit在experiments/nrlmsis2023_v2，轻量CSV/五图nrlmsis2023_*。原初次脚本路径错误发生在读取阶段并保留日志，独立v2修正完成，未覆盖历史。
- 新TIE积分0、新RK45积分0；经验接口具备后续探索接入的软件条件，正式实验仍缺TIE参考登记、Cd/面积/姿态/推力及完整受力/初态与时间分辨率验证。停止等待新授权。Git实际同步以最终核对日志为准。


## 2026-10-20最新：D5经验密度轨道接入完成

本次只新增D5的1h基准/tight、6h基准/tight共4次传播，D0—D4没有重跑，133项测试通过。D5对D0六小时终点位移174.661680m，D5与D1/D2/D3/D4终点差分别65.074180, 58.332529, 59.255645, 52.201839m；均为PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST模型差，不是正式预测误差。完整共同初态、力、气动/风、容差和输出冻结，NRL使用真实内部状态及WGS84，TIE A/B仍未正式登记。

三路线工程链路已齐备：历史TLE/SGP4、NRLMSIS/RK45、TIE条件密度/RK45；正式Swarm精度比较尚未完成，缺高度/气动/姿态/推力和完整受力、初态与高频场验证。阶段总结reports/PHASE1_ORBIT_DENSITY_COMPARISON.md，D5运行/数值报告MSIS_DRAG_ORBIT_EXPERIMENT.md及MSIS_DRAG_NUMERICAL_VALIDATION.md；实测数据experiments/msis_drag_orbit_v1。四次运行433.199s，峰163.195MiB，原122项保护哈希不变。无新TIE/旧D0-D4运行、无拟合或训练，完成后停止。Git实际提交/远端同步见任务结束核验日志。


## 2026-10-20最新：J3/J4无阻力扩展及正式参数审查完成

在不改原μ/R/J2/基础代码的前提下，核实GFZ EGM2008完全归一化C30/C40并按μR^n重表达为项目Jn，定义名义J2+静态J3/J4受控势，非完整EGM/IERS模型。9项新测试/全142通过，独立球坐标与势梯度、固定轴能量/轴向角动量及关闭恢复检查通过。

只新增G1、G2、G2-tight三次6h无阻力，G0读取D0；G1终点429.142m、全段RMSE418.474m；G2终点834.459m、RMSE731.931m，对比G0终点1066.087m/RMSE555.356m。G2终点改善但全段RMSE恶化31.795%，不挑点下结论。J3/J4分别引起终点923.004/815.786m增量，合计1735.560m，远大于旧条件密度差52—65m；不能把新旧引力差归因密度。G2 base/tight最大差0.058411m，配对变化1.58045e−5m；174项历史保护SHA未变。

新取得ESA官方公开链接5.13版2013产品定义并只存本地；识别q详细表/概览方向矛盾、Flags_Platform跨产品含义差异及f_thr单位mN。0601现行适用性、四元数顺序/几何/Cd/推力仍未闭合；未启用真实参数。为PDF阅读仅新增项目内pypdf/pycryptodome，无系统改动/原数值包升级。资料详见SWARM_FORMAL_FORCE_PARAMETERS.md。

入口：reports/HIGH_ORDER_GRAVITY_VALIDATION.md、HIGH_ORDER_GRAVITY_ORBIT_COMPARISON.md；docs/HIGH_ORDER_GRAVITY_DESIGN.md及UPDATED_GRAVITY_DENSITY_PROTOCOL.md，配置/审计experiments/high_order_gravity_v1，真实六图/CSV在results。原D0—D5、TIE场及正式坐标门禁不改，无新阻力矩阵/AI/48h扩展。下一步需新授权统一球谐（含非带谐）与真实气动/推力门禁研究，所有未来密度组须共同升级引力。本次完成后停止，Git真实SHA以最终核验为准。

## 2026-10-21最新：统一完整低阶8×8引力完成

上一af8ac82已安全补推并核验远端一致。新增EGM2008自身GM/R/C/S的静态tide_free 8×8（包括非带谐），完整地固旋转至GCRS，仅一个包含中心项的力，不叠加旧J2。独立SHTOOLS Fortran最大相对差1.3261e−15；新增9项、全151测试通过。原环境72包兼容，外部Fortran参考独立存.local/reference，未升级数值包。

本次仅十分钟预检+一次H1六小时base+一次tight，G0/G1/G2与D0—D5只读。H1终点622.748675m、全段RMSE310.911962m，R/A/C RMSE23.548/309.382/19.858m；相对G0终点与全段降低，但不能按终点选择G1，也不证明完整物理精度。H1 base/tight最大差0.058408m，预注册0.5m门槛通过；328.128s、累计峰RSS292.898MiB、177项历史SHA不变。模型GM/R/C20也不同，不能把全部变化只归因于增阶。

入口：reports/SPHERICAL_HARMONICS_VALIDATION.md、SPHERICAL_HARMONICS_ORBIT_COMPARISON.md、docs/SPHERICAL_HARMONICS_GRAVITY_DESIGN.md；配置与审计experiments/spherical_harmonics_v1，六图/CSV在results对应前缀。原始NPZ/wheel本地不上传。

真实质量记录有来源，但Cd/有效面积/姿态分量与0601标志/推进器实际力仍未确认；f_thr是名义mN字段，不能解释为实测推力。TIE正式高度门禁不变。下一步等待授权截断敏感性、日月/SRP/潮汐及真实参数核查；未来密度对照必须共同升级同一引力，当前不新增大气/阻力/AI/48h。Git最终SHA与实际同步见本次核验日志/汇报，不预先声称最终提交已推送。

## 2026-10-21最新：12/20阶截断与主要缺失受力审查完成

同源EGM2008仅读64KiB，完整20阶231对C/S、前16KiB与H1相同；源GM/R/归一化/无潮统一。新可回退gravity_truncation.py继承旧势/梯度，未改8阶原文件。三种截断与SHTOOLS独立Fortran最大相对差≤2.81e−15，扩展8阶在全部361个历史H1状态上的GCRS力逐位相同。传播前159测试、最终163测试通过。

仅一次H3十分钟预检、H2/H3六小时各一次、H3-tight一次；H1只读。8→12终点位移267.586752m、12→20为133.266130m（全段最大160.062686m、RMS77.777787m），5m候选目标未达到，不能认定20阶足够或把133m当20阶真实误差。SP3终点/RMSE：H1 622.749/310.912m、H2 355.388/177.073m、H3 223.025/107.677m；不按残差选最优阶。H3 base/tight最大0.058411m，通过0.5m门槛。流程498.429s、峰RSS146.430MiB，201项历史SHA不变，旧H1交付清单另行核验。

只在历史H1离线评估日月差分，太阳约2.74—3.90e−7/月球6.91e−7—1.10e−6m/s²；builtin ERFA位置而非JPL DE440，GM另有NASA来源。SRP/潮汐/单极GR仅显式条件量级，没有加入RHS或用a*t²推轨道误差。f_thr名义mN/真实气动与推力、TIE高度及预热等仍未闭合。

入口：reports/GRAVITY_TRUNCATION_VALIDATION.md、GRAVITY_TRUNCATION_ORBIT_COMPARISON.md；docs/ORBIT_MISSING_FORCE_BUDGET.md、NEXT_DENSITY_ORBIT_EXPERIMENT.md；experiments/gravity_truncation_v1；results同前缀CSV/图。下一步待授权更高阶截断/可靠星历第三体门禁，不进入正式密度精度排名，不自动新增阻力/大气/AI/长窗。Git实际SHA及远端核对见结束汇报。

## 2026-10-21最新：40阶与日月第三体受控实验完成

先安全补推上一提交2ad0c35并核对远端相同。本轮同源EGM2008只读取256KiB，完整40阶861对系数，前64KiB与20阶相同；新初始化模块复用旧势/梯度而不改历史实现。SHTOOLS最大相对差6.37e−15，新20阶在全部361历史H3状态上的GCRS力逐位相同；原176项最终测试通过。日月模块明确ERFA builtin，不自动下载；Moon TT原生GCRS/Sun TDB几何矢量Newtonian阶对齐，完整相对论空间/GM时标映射未闭合。NASA Horizons DE441三点独立检查最大位置差太阳1648m、月球4404m，保留PROVISIONAL_EPHEMERIS。

仅四次600s短例(base/tight各两组)和H4/H5各一次六小时，无H6/H3重跑。短例最大差约0.257mm，通过2cm门槛；六小时没有完整tight对照，FULL6H_CONVERGENCE_PENDING不可隐藏。H4−H3终点15.364167m/最大33.088719m/RMS20.704993m，5m截断目标未达；H5−H3终点4.617909m/最大12.665472m/RMS5.578434m，法向为主。SP3终点/RMSE：H3 223.025/107.677m、H4 234.817/104.212m、H5 224.480/108.093m，未预设新增力必改善。全新传播349.972s、峰148.348MiB，229项历史SHA不变，旧H3交付清单另核。

入口：reports/GRAVITY_40X40_VALIDATION.md、THIRD_BODY_GRAVITY_VALIDATION.md、GRAVITY_THIRD_BODY_ORBIT_COMPARISON.md；docs/COMMON_FORCE_MODEL_DECISION.md、FORMAL_PARAMETER_EVIDENCE_REQUESTS.md。数据/图/CSV同gravity_third_body_v1前缀，原NPZ/星历响应/模型前缀本地不上传。

尚不正式冻结40阶收敛或“40阶+日月”组合（H6未运行）；下一步须另授权补全窗收敛/候选组合及截断预算。仅可设计明确假设的统一动力学PROVISIONAL密度矩阵，真实气动/推力/TIE高度/预热和时间场门禁仍在。当前任务完成后停止，不自动H6/更高阶/阻力/TIE/AI/长窗。Git最终SHA与同步结果见结束核对。


## 2026-10-21：H6组合与完整六小时数值门禁已完成

H4/H5 tight、H6 base/tight共四次六小时及H6两次600秒预检完成，无重试、无旧轨道重跑。H4/H5/H6单轨最大base/tight差均小于0.5m，各配对差稳定性小于0.1m，181项测试通过。H6单轨最大差0.058398202m；40阶背景加入日月的终点位移4.618091m、全窗最大12.665426m。H6 SP3终点残差236.454619m、三维RMSE104.825766m。

本次传播墙钟1192.190s、峰RSS329.707MiB，低于1800s/2GiB；历史SHA不变。实际配置effective_configuration.json区分继承来源的旧状态字段，旧记录保留。仅冻结configs/provisional_common_force_model.json供下一阶段条件研究，标记PROVISIONAL / HINDCAST / FORCE_MODEL_INCOMPLETE，星历保留PROVISIONAL_EPHEMERIS。

40阶未证明截断收敛，真实气动/姿态推力、TIE外部ZG登记、预热和高频场仍未闭合；缺失潮汐/SRP/相对论等。C0—C3仅设计未运行。下一入口reports/H6_FORCE_MODEL_VALIDATION.md、reports/H6_ORBIT_COMPARISON.md及docs/PROVISIONAL_DENSITY_COMPARISON_PLAN.md。完成后停止，任何新阻力矩阵/更高阶/TIE/AI/长窗传播均需另授权。


## 2026-10-21：统一H6的C0—C3条件密度矩阵完成

C0复用H6，未重跑。新增C1/C2/C3各1h base/tight、6h base/tight，共12次，预注册单轨/配对门槛通过，187测试通过；无新TIE/更高阶/AI/长窗。C1−C2终点58.350988m，C1−C3 52.217924m，C2−C3 6.133109m。全部仍为PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST / FORCE_MODEL_INCOMPLETE / PROVISIONAL_EPHEMERIS。

共同H6/旧实验/驱动保护SHA不变，正式TIE入口仍拒绝。总传播3250.304s、峰RSS161.594MiB。三种在线密度、同C0位置离线密度、力/轨道及SP3探索残差均有CSV/审计/图。主报告reports/COMMON_FORCE_DENSITY_ORBIT_COMPARISON.md。正式气动/推力/高度/预热/时间分辨率和缺失力门禁未解除；本轮完成后停止。下一步优先取得FORMAL_PARAMETER_EVIDENCE_REQUESTS列明的资料并设计物理验证，不自动扩窗或训练。


## 2026-10-21：第一阶段工程验收整理与FourCastDEN第二阶段A启动

新增PHASE1_STAGE_REVIEW_20261021及5张既有图索引，明确工程/条件敏感性通过、正式科学精度未验收；未重跑C0—C3/引力/TIE。恢复官方AI资产并SHA保护，历史单步不是新成果。一次Jan4 00→01→02官方Direct自回归成功，实际forward2次，第二步171状态逐元素反馈第一步预测；未来真实状态只评价，未来LBC/驱动显式HINDCAST。两步DEN有限正值，首步与历史逐元素一致；192测试通过。

第2小时六变量平均逐层RMSE均比第1小时增大，但两步全部171通道均优于固定00时持续性。GPU阶段5.600s<300s，未训练/微调/扩6或24h；内存/事件计时口径和局限见FOURCASTDEN_TWO_STEP_VALIDATION.md。S7实际14键/网格匹配，但3种lev场顶padding、1h抽取、分布与Z/ZG问题仍需规范转换，本次没有输入S7。完整训练入口与2000—2022数据未齐，不称完整论文复现。

下一入口docs/FOURCASTDEN_PHASE2_RESEARCH_PLAN.md；建议另授权官方Flow同样两小时对照，之后再补统一变体窗口。正式轨道气动/推力/高度、预热和缺失受力门禁保持。完成停止，安全Git同步以最终远端核对为准。


## 2026-10-22：官方Flow复现与Direct/Flow受控比较完成

一次Flow Jan4 00→01→02正式推理完成，真实forward2次，官方Flow权重严格加载。原位归一化增量/两步反馈逐元素验证通过；Direct只读取历史，未重跑，所有旧保护SHA保持。198项自动化测试、独立NumPy加权指标复核通过，Flow DEN100%正且有限，无裁剪或事后校正。GPU阶段3.400s，冷/第二forward152.144/18.435ms；新增数组约17MiB，无下载/安装/训练/TIE/轨道实验。

Flow第一小时170/171层、第二小时141/171层RMSE低于Direct；变量平均逐层RMSE第一小时TN/UN/VN/WN/Z较低，第二小时TN/UN/VN/Z较低，DEN两小时分别较高2.950%/2.842%，WN第二小时较高2.468%。DEN平均绝对RMSE受底层影响，上层相对/log指标另报，不能据单个初值排名架构。两模型均全部171层优于固定t0持续性；六变量平均误差均随步数增加。两套单次跨日GPU事件总时间差约0.978ms，不作速度优越性结论。

报告FOURCASTDEN_FLOW_TWO_STEP_VALIDATION.md、FOURCASTDEN_DIRECT_FLOW_COMPARISON.md；新增8图、4类逐层/汇总/配对CSV，配置、SHA、日志及审计在fourcastden_flow_two_step_v1。改进方向/未来独立初值与6/12/24h协议仅设计；本次不扩窗。下一项建议先多初值2h评价，或补1个Jan4 03样本建立history公平窗口，须另授权。完整训练入口/数据、独立大气/轨道验证、Swarm真实参数/推力及TIE高度/预热/时间分辨率等门禁保留。Git同步以最终SHA核对为准。


## 2026-10-22：FourCastDEN五日期Direct/Flow小规模泛化检查完成

固定新增Mar23/Jun21/Sep23/Dec21各00→01→02，12个真实官方NPZ经206/Content-Range/CRC/SHA/14键/层结构/finite/正性检查取得，传输25,849,991字节<100MiB，无整包或Jan4重下载。206项测试通过。8个新序列/16个forward完成，Direct/Flow各加载一次复用四个独立初始化，Jan4只读。真实物理状态反馈防泄漏、条件/统计/目标一致及独立NumPy指标通过，无NaN/负DEN、无裁剪或重试。监督墙钟27.342s/峰RSS约1.223GiB，GPU阶段含CPU审计/压缩19.099s，原始数组不入库。

五窗观察：Flow两时效TN/VN/Z均5/5平均层RMSE较低，第二小时UN/WN各4/5较低；第二小时DEN绝对平均层RMSE为Direct 5/5较低，但原生上层及参考中位ZG400—500km层组的平均相对RMS/logRMS为Flow 5/5较低。两模型全部日期六变量平均误差均增长，Flow上层第2/1小时倍率在五窗更大，不代表长期规律。Kp实际00—02输入Mar23仅0.5—0.867，五窗总体0.5—4.117，不能叫强磁暴验证；其余是季节候选，无总体/显著性排名。

报告FOURCASTDEN_MULTIDATE_VALIDATION.md、FOURCASTDEN_MULTIDATE_COMPARISON.md，指标CSV/7图/Range和运行/资源审计在fourcastden_multidate_v1。官方log-DEN仅CPU静态审查150项参数/177输入/static_log；没有forward，NumPy/CUDA分支和log/物理ACC公平定义仍需审查。建议下一项先官方log-DEN两小时，再history公平窗口，随后预注册6/12/24h和更强条件；见FOURCASTDEN_NEXT_EXPERIMENT_DECISION.md，需新授权。未训练/TIE/轨道传播，正式物理参数和坐标门禁不变。Git同步以最终远端SHA核对为准。


## 2026-10-22：官方log-DEN五日期复现与三模型对照完成

215项测试通过。小张量确认np.power的CUDA转换失败；另由CPU合成原循环确认static_log气候态前导单例和DEN通道仿射广播问题，隔离覆盖层逐项保值修复，原始树/权重/统计不改，完整diff/SHA/失败日志保留。唯一正式log工作进程5个独立两小时序列、10forward完成；Direct/Flow只读，无下载/训练/扩窗/TIE/轨道。监督17.213s，加兼容探针0.588s<600，峰RSS1.107GiB；全预测finite/DEN正，反馈逐元素核验，无失败或重试。

共同原始物理目标与普通气候态公平比较：2h全层平均绝对DEN RMSE log在5/5窗最低；但上层与参考中位ZG400—500km组相对RMS在两时效五窗均Flow低、Direct其次、log较高，未支持log改善高层相对误差。TN/Z等窗平均2h较Direct高约18.9%/20.6%，其他变量代价完整记录。各自匹配统计/权重不同，不能单因果归于log开关。三者均2h平均误差增大，n=5不推断全年/真实大气或轨道精度。

报告FOURCASTDEN_LOGDEN_COMPATIBILITY、LOGDEN_VALIDATION、THREE_MODEL_COMPARISON；原native/dex/log ACC与公平物理CSV分开，6张真实图，所有原始/预测数组本地。下一入口NEXT_EXPERIMENT_DECISION最新节，建议先history公平窗口（另授权补03并统一01初始化），之后6h再长时。所有正式物理门禁继续保留，完成停止。Git同步以最终远端SHA核对为准。

## 2026-10-22：官方History首次真实自回归与四模型共同01时对照完成

- 只新增Jan4 03时NPZ（HTTP206/Content-Range/CRC/SHA，传输3,063,982字节）；00—02不重取。4个模型都以01初始化新执行，History额外00真实历史，统一目标02/03；旧00起点结果保持。
- 官方History严格加载、354输入/171输出、66,870,720参数；独立CPU毒化测试和真实hooks确认第二步real01+pred02。4序列8正式forward，加唯一History预检1次；无训练/微调/扩窗/TIE/轨道，221项测试通过。
- 单窗新结果：History两时效六变量平均层RMSE均高于Direct；400—500km相关原生组第1h Flow最低、第2h Direct最低。第二小时DEN平均层绝对RMSE Direct4.99559e-11、Flow5.85038e-11、log5.12006e-11、History3.97000e-10 kg/m3。不能挑旧/新起点混排名。
- 4模型均finite/DEN正，误差均有增长；History DEN倍率较小但起点误差高，不证明更稳定。独立NumPy1368通道指标复核/356保护SHA通过。监督21.011s、峰RSS1.225GiB，新增约109MiB<150MiB。
- 报告FOURCASTDEN_HISTORY_VALIDATION.md、FOURCASTDEN_FOUR_MODEL_COMPARISON.md；5图/逐层物理与原native CSV、配置/审计/日志保留，大数组本地。下一阶段先补另外4日期03并统一01短窗，再6h；当前未执行。真实大气/轨道精度门禁不变。Git以最终远端HEAD核验为准。

## 2026-10-22：五日期四模型共同01时对照完成

- 后4固定日期03时合法补取，HTTP206/Content-Range/CRC/SHA/14字段/finite/正DEN及网格契约通过；网络9,274,427字节<20MiB，Jan4和已有数据不重取。新增16序列32forward，Jan4四组旧01时结果严格SHA只读，五窗四模型全部具备。
- 226项测试、6840个共同物理通道独立复核、422历史保护SHA通过；History354/其他177输入、171输出，归一化/增量/log/滑窗和未来辅助对齐，全部finite/DEN正。无训练/重试/扩窗/TIE/轨道。
- History DEN全层绝对与高层相对在两时效均0/5优于Direct、也0/5优于Flow；History在Dec第一小时WN及第二小时UN/VN/WN优于Direct。Flow近400—500组第1h5/5最低，第2h3/5最低，Direct2/5；第2h绝对DEN log3/5最低、Direct1/5、Flow1/5。所有模型六变量平均误差均增长，不能用增长倍率较低掩盖较高初始误差。
- 01相对00起点的第二小时高层误差增长在Jan/Dec突出，但Jun略降，不能说01总更难或归因某个驱动。History接口专查与Direct mean/std、01初态和real目标完全一致，已查路径无代码错误，不推断上游训练唯一根因。
- 监督42.5746s、峰RSS1.222GiB；新增约431MiB<650MiB，CPU分析10.557s/约364MiB。新7图/15类CSV/配置与审计，原始大数组本地。报告FOURCASTDEN_FOUR_MODEL_MULTIDATE_VALIDATION/COMPARISON；6小时仅设计Jan4+Mar24（外部GFZ预选，尚无该窗预测），最少12新帧，未下载/执行。
- 当前不能选最终模型或给真实大气/卫星轨道精度结论。下一入口FOURCASTDEN_SIX_HOUR_EXPERIMENT_PLAN.md；所有正式物理参数/高度门禁保留。Git同步以实际远端SHA核对为准。

## 2026-10-22：四模型两日期连续6小时完成

- Jan4 01→07、Mar24 01→07，8独立序列48正式forward+唯一Direct单forward短例；无训练/微调/12或24h/TIE/RK45。12新NPZ成功，初次7帧后HTTP500，保留日志并一次有界补取余5，累计26,985,595字节<40MiB，全CRC/SHA/14字段/范围/网格契约通过。
- 232项测试、8208物理通道独立复核、533历史保护SHA通过。六步状态/辅助/标量准确，History第三步起全预测窗口，Jan4前2步与既有四模型2h逐元素一致。全部finite/DEN正、TN约146.9—1736.6K，无明显数值发散，无结果修补/失败重试。
- +6h近400—500参考中位ZG原生组相对RMS：Jan4 Direct1.2391%、Flow1.4770%、log1.3359%、History1.5551%；Mar24依次4.2726%、4.3589%、3.9071%、4.0454%。Jan4 Direct2—6h最低；Mar24 History2—4h、log5—6h最低。History绝对DEN仍最高，不能按局部优势选最终模型。
- 作者Mar24小时Kp6.583—7.883，Jan4 3.35—4.633并非地磁安静。作者F107/Kp与GFZ约定/插值不完全一致，原样保留；两窗同UT、季节/初态/历史驱动混杂，不作因果。Mar24 near组+3h起22层中位超过500km被剔除，固定upper/逐层补充。
- 监督39.700s、峰RSS1.316GiB、GPU阶段30.841s含CPU处理；网络事件每序列约110—113ms，读取/标准化/原指标/保存单列，不等同端到端加速比。新增约392MiB<800MiB；8图/8类CSV，原始和大NPZ本地。
- 报告SIX_HOUR_VALIDATION、SIX_HOUR_COMPARISON、GEOMAGNETIC_WINDOW_COMPARISON；下一决策LONG_HORIZON_DECISION只设计先12h再24h，缺训练入口/2000—2022数据与独立观测/轨道接口条件。当前停止，Git以最终远端核验为准。

## 2026-10-22：Jan4四官方模型连续12小时完成

新增fourcastden_twelve_hour_jan4_v1，固定01→13，Direct/Flow/log/History各12步，共48正式forward，无额外GPU预检/重试。新增08—13六NPZ，206/CRC/SHA/14字段等通过，网络13,442,650字节<25MiB；原00—07只读。237测试通过。真实hooks前6步input/scalar/raw/state及统计全部与历史6h逐元素一致；公共六变量/旧DEN指标前缀亦精确相同，历史结果未改。

全部输出finite/正DEN/正TN。+12h参考中位ZG400—500km相关原生组相对RMS：Direct1.331348%、Flow1.623416%、log1.446208%、History1.899883%；全层DEN逐层绝对RMSE平均分别2.3451913e-10/3.0523764e-10/2.3876184e-10/8.3372090e-10kg/m3。Direct+2—12本窗口较低；高层误差并非单调，不能以单窗口选最终模型。HINDCAST/TIE参考拟合不等于观测或轨道精度。

监督39.43596秒、峰RSS1.387GiB，GPU worker30.07781秒含I/O/加载/评价/保存；网络12forward合计Direct358.082ms（首调用冷）、Flow217.901、log219.404、History225.480，不能作严格吞吐排名。独立NumPy8208通道时效复核，全部门槛保持。大数组只本地。

入口scripts/run_fourcastden_twelve_hour_jan4.py与supervise/analyze/audit同标签；报告FOURCASTDEN_TWELVE_HOUR_JAN4_VALIDATION/COMPARISON，训练静态审查docs/FOURCASTDEN_TRAINING_READINESS.md；Mar2412h仅方案docs/FOURCASTDEN_MAR24_TWELVE_HOUR_PLAN.md。当前缺完整作者训练入口/训练验证数据/原配置；不训练、不24h/TIE/RK45。旧9447e785已恢复推送核验，本次提交同步以实际远端核验为准。任务结束停止，下一项建议另授权Mar24同协议12h，不自动执行。

## 2026-10-22：Mar24四模型12小时与两窗口对照完成

fourcastden_twelve_hour_mar24_v1已完成固定01→13四组连续12步/48forward，0额外GPU预检/失败重试。239测试通过；六个新08—13样本全206/CRC/SHA/14键等校验，网络13,452,428字节<25MiB，旧00—07与Jan4只读。前6步input/scalar/raw/state/统计及原六变量与DEN指标逐元素一致，独立NumPy8208通道时效复核，原门槛不变。

Mar24 +12高层相关组相对RMS：Direct3.759760%、Flow3.964593%、log3.674795%、History4.078700%；全层平均绝对DEN RMSE分别7.8960708e-10/9.1789238e-10/7.6516976e-10/1.3607688e-9kg/m3。near Flow+1、History+2—4、log+5—12较低；固定upper20—28在+12为Direct较低，History顶部/极区有条件优势，不能据单组排名。near索引前2步20/21/22、中间3—11步20/21、+12重新20/21/22；Jan4为21/22/23，非固定450km或Swarm沿轨误差。两窗不作地磁因果/全年结论。

48输出finite/正DEN/TN，无数值发散；监督39.969886秒、峰RSS1,494,986,752字节，GPUworker30.514212秒含加载/IO/指标/保存。12forward网络事件D352.574/F218.047/log214.306/H220.807ms，首Direct冷调用，不作吞吐排名。原数组只本地。

报告FOURCASTDEN_TWELVE_HOUR_MAR24_VALIDATION与TWELVE_HOUR_TWO_WINDOW_COMPARISON；新训练实施计划docs/FOURCASTDEN_TRAINING_IMPLEMENTATION_PLAN.md明确P0作者材料/训练验证样本→隔离入口→资源预检→Direct基线→多步/分层损失。当前不训练/调参/24h/TIE/RK45，正式真实大气/轨道门禁未解除。下一项建议先取得完整训练协议与非2023合法小样本；24h仅另授权候选。Git以最终远端核验为准，结束停止。

## 2026-10-23：官方训练资源核查与独立最小训练工程

实时Zenodo软件概念22250237→版本22250238及数据21859635 API均200。软件仅源码/权重/普通static/static_log，数据仅2023.zip；本地原源码zip MD5与当日清单一致，原包无完整train_tiegcm.py。Apache2.0/CCBY4.0来自metadata，未取得非2023训练验证目录/许可/文件。MDPI正文/XML403（网页工具429），Crossref200核题目作者和摘要；不能宣称全文其他资源已全部查清。

已新增src/training独立Direct接口，复用不改原AFNONet，显式177+4→171、时间pair/年份split、归一化、loss/梯度/更新、validation、checkpoint/RNG恢复；不称官方完整训练复现。247全测试通过。首次GPU因缺CuBLAS确定性环境在首forward失败，零完成step；保留v1，独立cublas_v2预先设置:4096:8后完整官方结构随机初始化完成3合成SGD step，第2步唯一checkpoint保存/严格恢复后第3步成功。没有真实样本/官方权重训练，无新预测/TIE/RK45。

合成loss141.80748→141.80228→141.79710仅工程意义。GPU allocated峰641,605,120字节、进程峰1,335,885,824字节，2次监督合计12.2464秒<300/20GiB。唯一checkpoint258,850,242字节本地不提交；GPU用SGD0动量控制500MiB预算，CPU用非零动量验证完整optimizer恢复。norm两参数无梯度符合原forward未用的已知行为。

报告OFFICIAL_TRAINING_RESOURCE_AUDIT/TRAINING_SMOKE_TEST，MINIMAL_TRAINING_DESIGN/DATA_ACQUISITION_PLAN/IMPROVEMENT_EXPERIMENT_DESIGN。真实候选工程样本预注册2021-04-05→04-08和2022-04-05→04-07，未下载/执行。下一优先作者协议与合法小样本→真实adapter审计→基线训练；改进优先K2多步单因素，另行研究高层损失，2023不调参。正式大气/轨道门禁保留，任务后停止，Git以最终远端SHA为准。

## 2026-10-23：真实数据接口只读验证完成

Jan4三帧2023真实NPZ仅CPU读取，00→01与01→02两对的177输入/4scalar/171目标和官方原inference输入构建逐元素相同，历史input0复现；官方forecast边界捕获即中止，没有创建网络/执行forward、真实loss/backward/optimizer或GPU。未来目标171毒化输入不变，原2023训练/验证拒绝规则保留。8新+3既有时间检查共11通过，旧247为历史证据，不重跑合成训练。

原174归一化float32逐元素相同，单位/往返误差与原padding/哨兵检查通过。辅助AffineNormalizer float64与原32位有≤9.5367e-7差异，初次误要求位级相同的诊断失败已保留；精确实际输入门槛不变。普通static统计原来源年份仍未知，不能证明训练分布匹配。

官方latest API与旧元数据SHA相同，仍无2000—2021/2022数据或完整训练入口；MDPI403，邮件草稿完成但通讯人邮箱未核实/未发送。已有S7坐标与官方static精确相同且14字段可取得，但2021/2022需新驱动/日历短诊断、物理配置/预热/统计另审，不称作者原训练集。新增REAL_DATA_INTERFACE_AUDIT、AUTHOR_RESOURCE_REQUEST、ALTERNATIVE_TRAINING_DATA_PLAN、REAL_TRAINING_READINESS，实际训练BLOCKED于合法样本/协议/统计/科学优化器与预算。候选2021-04-05→08和2022-04-05→07未下载，未TIE/RK45/新预测/训练。完成后Git核验同步并停止。

## 2026-10-23：2021/2022历史驱动与最小诊断

2022 GFZ/GPI及新年份10分钟诊断通过，4MPI运行2.49秒、峰值约946MiB，14字段齐备；11项聚焦测试通过。2021因05-09 Fobs=-1（影响目标中心81日平均）阻断，未生成GPI/未启动，不补缺。所有10分钟冷启动/早期暖态场均NOT_TRAINING_DATA；122帧+候选7天预热仅估算，不执行。详见两份TIEGCM_2021_2022报告及独立数据生成决策。

## 2026-10-23：2021 F10.7缺测追查

缺测未可靠修复：GFZ两格式与复查JSON均确认−1，加拿大表缺目标日，CelesTrak76.2为INT；NOAA76候选跨源49日中23日超过预注册精度门槛，未采用。2021 def Kp120桶已取，但无新GPI/无模型启动。10项新增恢复测试及11项既有驱动测试通过；2022SHA保护通过、不重跑。多天生成/真实训练仍BLOCKED。见F107_2021_MISSING_DATA_INVESTIGATION及TIEGCM_2021_DRIVER_RECOVERY。

## 2026-10-23：Mar23新窗口v2启动门禁通过

用户另授权注册training_window_mar23_v2（2021训练03-23至26/2022验证03-23至25，7天候选预热），旧apr05_v1缺测状态保持。真实GFZ两年Fobs95/94条、def Kp120/112桶完整，新GPI与全合法域独立插值通过；两个年份各一次10分钟诊断通过，耗时2.63/2.43秒，14键及作者四坐标逐元素一致，11项新测试通过。全部10分钟记录NOT_TRAINING_DATA，未多日积分/训练。已具备v2候选多日运行输入条件，预热充分性/跨日稳定/作者分布/统计仍未证明。详见FOURCASTDEN_TRAINING_WINDOW_V2及三份TIEGCM_MAR23报告。
