# Satellite-AI 长期执行规则
## 工作区与隔离
唯一项目根目录 /workspace/data/20261016。所有源码、仓库、数据、权重、虚拟环境、缓存、临时文件、日志、图片、文档、Git记录必须在根目录内。每次写入前检查绝对路径和符号链接真实目标。系统已有软件仅只读使用；不得主动将项目文件写入 /root、/tmp、/workspace 根或其他目录。必须越界的操作先解释并停止，等待用户批准。
优先使用 .venv，运行前 source scripts/activate.sh，将临时目录及各库缓存指向项目内。禁止全局 pip、修改其他 Conda 环境、未经允许 sudo/apt、未经检查的安装脚本、删除覆盖其他项目或原始数据。不得重设 HOME 或 CODEX_HOME。
## 角色与范围
中文解释，代码和专业术语可英文。按“学习原理—代码实现—运行实验—验证结果—记录成果”推进。面向具备 Python/PyTorch 基础、初学轨道动力学和 TIE-GCM 的用户。
仅研究单颗低轨卫星；不开发碰撞预测、碎片管理、自主控制。每天只做用户授权的当天任务，不自动进入后续日期。初始化结束必须停止，不训练、不下载大型数据。
## 科研规则
FourCastDEN转入第二阶段，届时先复现再改进；优先作者权重与测试数据，当前不训练、不用替代网络冒充复现。链接与文件必须实际核验。资源清单存在不等于可运行；区分已编写、可运行、通过测试、经过物理验证。
核对单位、量纲、时间基准、坐标系、网格、边界和误差：DEN 是否 kg/m³，压力层与几何高度关系，ECI/ECEF，地球自转与相对风速，质量/面积/Cd，积分容差。TIE-GCM 拟合精度不得等同观测或真实轨道精度。
模块实现后必须有基础测试：二体周期/能量，J2量级，密度范围/高度变化，AI参考匹配，查询一致性。pymsis/NRLMSIS是第一阶段正式经验大气对照B，需明确版本和驱动，不能冒充FourCastDEN或TIE-GCM。
## 资源与异常
下载大型资源、复杂依赖、训练前检查磁盘、内存、GPU和预计体积/资源。单个超过5 GB的资源、长时间大规模训练必须另获用户批准。保留错误日志、分析原因、提出最小修改，不破坏已有环境。不能复现时仅在用户授权范围推进备用工作。
## 接续与记录
每次先确认路径，阅读 AGENTS.md、STATUS.md、WORKLOG.md，检查现有文件/结果再继续。结束更新 WORKLOG.md（日期、目标、实际内容、命令、文件、环境、结果、验证、问题、下一步）和 STATUS.md（阶段、完成、进行中、问题、入口）。不得只依赖聊天记忆。
每次最终汇报依次使用六节：今日完成情况、关键技术解释、实验结果、遇到的问题、当前项目状态、下一步计划；提供可核查路径及真实指标。
## 核心资源与目标
论文 https://doi.org/10.3390/rs18183134 ，待核验软件 https://doi.org/10.5281/zenodo.22250237 ，数据 https://doi.org/10.5281/zenodo.21859635 。资源状态见 docs/RESOURCES.md。
第一阶段2026-10-19至10-31；具体每日目标见 docs/PROJECT_PLAN.md。日期目标不代表已完成，不得为赶进度夸大结果。

## 2026-10-19早会后的最新长期路线（优先于此前AI主线日程）
最终目标：在可验证精度前提下，用更准确密度改进单星LEO轨道并研究总计算效率。第一阶段为A:历史TLE+SGP4、B:经验大气+RK45、C:TIE-GCM2.0+RK45，统一与Swarm优先的SP3精密参考比较；第二阶段FourCastDEN同数据协议复现/改进，第三阶段AI替代物理模型并验证轨道/效率。现阶段不训练、不生成长期训练数据。
B/C必须同初态、同质量/面积/Cd/共同风场假设、同其他受力、同积分设置，只替换密度。不得预设RK45更准。仅中心引力/J2/阻力属于原型，不代表完整高精度受力。
SP3不是绝对真值；优先LEO Swarm。读取实际文件头中的时间基准/框架，不能依目录概述猜测。区分GPS/UTC/TAI/TT、TEME/ITRS(含具体IGS实现)/GCRS，带速度转换，冻结EOP和闰秒。所有物理单位和垂直网格以实物元数据/源码为准。
必须包含同SP3单t0历元状态的B/C初始化实验及真实历史TLE的A实验，明确两者初始优势。禁止用未来SP3拟合/反复修正初态、Cd、密度系数后又声称独立验证；若校准，另设t0前窗口并冻结。TLE历元与历史实际可用时间分别记录。
TIE-GCM须检查编译器/MPI/NetCDF-Fortran/ESMF、官方2.0的2015后地磁更新、初始完整场/边界/驱动及spin-up；默认短例不代表真实时段可信输出，不得直接把启动瞬态或AI预处理NPZ当重启场。单个>5GB仍需单独批准，不自动运行长时间CPU/GPU任务。
本次最新计划docs/UPDATED_RESEARCH_PLAN.md；资料ORBIT_DATA_SOURCES.md、TIEGCM_MINIMAL_RUN_PLAN.md、ORBIT_VALIDATION_DESIGN.md。10月20日从轨道时间/框架/质量与SGP4基础准备接续，早前10月20日仅TIE数据可视化的日程已由本次调整取代；每日仍等用户指令。

## 轨道基准已验证的环境/时间入口（2026-10-20）
轨道工作使用source scripts/activate_orbit.sh，复用.venv310；该入口预建Astropy项目内config/cache，避免Astropy在目录不存在时回落写HOME。依赖变更锁定于configs/requirements-orbit-20261020.lock.txt，早前AI锁文件保留。
必须通过orbit.frames.configure_time_data加载冻结IERS-B/闰秒与校验SHA256，禁止在线自动更新/静默外推；不要把ERFA闰秒表清空后仅装1972年起的表，这会破坏早期GPS时间锚点，须保留固定ERFA早期定义再更新。正式实验前检查GPS历元和ESA HDR UTC独立锚点。
SGP4单TLE结果为历史传播对照。TLE历元早于t0不代表发布时间已核实；publication/availability未知时不得称严格实时预测。重复实验指定新run-tag保留已有输出，禁止覆盖原SP3/TLE。

## 阻力接口与TIE-GCM环境接续规则
轨道Python仍用scripts/activate_orbit.sh/.venv310；TIE编译/运行用scripts/activate_tiegcm.sh和项目.envs/tiegcm。禁止直接micromamba create：其默认会向HOME/.conda/environments.txt登记前缀，即使环境/缓存另有指定。本项目已审计的方案是项目内手动conda-meta/history后用锁文件install（不创建/注册环境）；安装脚本需审计并复核外部登记文件未改。当前曾意外新增的/root/.conda/environments.txt本项目前缀登记行，尚未获明确外部清理授权，不擅自移除，见logs/tiegcm_registry_incident.json。
Swarm质量优先同期SC_ADYN的m_SC，473 kg仅发射质量；日内范围不等于正式不确定度。截面积向量/Cd/姿态/推进器标志未闭合前，不运行真实阻力精度实验。DNSAPOD为沿轨POD反演并与SP3共享信息，不是独立真值或全球密度预测场。DragForce共转使用完整ITRS状态速度，不重复减omega×r；风为相对地面的中性风。
2.0原始树保留，当前GNU12构建有三个显式源补丁和nchist专用旧F77接口兼容选项。2002默认单日已运行不等于2023场可信；DEN在ilev且g/cm3→kg/m3乘1000，ZG在ilev且cm→m乘0.01。TN/风顶层缺失值必须显式掩码，默认场部分顶高低于Swarm，不外推。2023前仍须官方IGRF更新、真实驱动、完整初始场和独立spin-up验证。最新报告reports/TIEGCM2_ENVIRONMENT.md、DRAG_MODULE_VALIDATION.md；计划docs/TIEGCM2_EXECUTION_PLAN.md、DENSITY_COMPARISON_DESIGN.md。

## 2023适配准备后的长期门禁
用户明确要求保留/root/.conda/environments.txt既有登记，不自动清理。TIE2023入口见STATUS最新段及reports/TIEGCM2023_*；只能使用已记录官方apex覆盖层，原2.0树不改。GPI为Fobs/中心81日平均及def Kp的hindcast，禁用固定KP/POWER/CTPOTEN等覆盖；实际util公式优先于旧注释，日期不可越界/传86400秒。2023-03-18一次10分钟日历/驱动诊断已通过，报告TIEGCM2023_STARTUP_DIAGNOSTIC.md；尚未完成spin-up。t0继承旧源标量、首步60s启用GPI；进一步短段/跨日验证与3/7天均须新授权，不自动执行。姿态NaN、code4/推力/面积/Cd未闭合，实际2023顶高/高度基准未确认，不运行真实阻力精度实验，不外推。

## 每次科研任务结束后的GitHub同步（长期规则）
用户已授权每次完成科研任务后安全同步到https://github.com/hhtbbc/261016project.git的main。先检查分支、工作区、正确remote和远端新提交；仅提交本任务的代码、文档、配置及适合公开的小型验证产物。检查.gitignore、文件大小、敏感信息/私人路径与凭据；环境、权重、原始大数据、大型NetCDF、缓存和凭据不得入库。已有实验不覆盖。推送前重新检查远端；遇到并发新提交/冲突停止报告，不强推。推送后逐字核对本地HEAD与远端main，记录提交与核验日志。认证失败保留本地提交并如实报告，不能声称成功，不将令牌/密码写文件、日志、URL。VS Code旧socket失效时可仅在Git进程环境使用同用户有效认证通道，不改全局配置、不存储或打印凭据。新会话必须读本规则并执行，无需再次询问是否同步。

## 跨日Restart的新增门禁
原2.0 input.F948—960强制START与SOURCE_START的小时/分钟相同（仅日可不同），现有源只有00:00，不能直接按23:50启动。当前跨日任务0次模型启动，报告TIEGCM2023_RESTART_VALIDATION.md；须取得合法23:50完整primary或新授权额外准备运行。严禁重标时间/拼接次历史/伪造_NM绕过。原生continuation省略SOURCE，从OUTPUT读取完整主历史并保留初始时间属性；只能在独立完整checkpoint快照续算、保护原B1，必须实测连续/分段一致性后才认定可用。42测试仅静态/算法通过，不代表模型跨日/Restart通过。

## 合法23:50检查点后的最新门禁（覆盖此前“没有23:50记录”的历史状态）
已获新授权完成一次2023实际GPI的24h10连续诊断。experiments/tiegcm2023_crossday_24h10_v1/primary_002.nc为模型原生单记录23:50完整primary，SHA见checkpoint_2350_audit.json，无未来记录，不再需要之前建议的额外2002准备运行。不能修改或在原文件上append；下一次获准续算时复制完整文件到独立目录，核验SHA、时间/记录最大值<=START，省略SOURCE走原生continuation。原00:00 echo的iter/F107等仍继承冷源，暖态计数和驱动已核实，不手改元数据。当前仅跨日/基础场/检查点结构通过，未运行恢复/连续分段一致性/3或7天spin-up，后续必须等新授权。末段顶高545—677km只是本例原生ZG，不是目标Swarm日期实际覆盖率；高空基准/气动参数/机动问题仍须闭合。

## 原生continuation最新门禁
合法23:50检查点已解决；B1原生续算正常退出但28/34 primary及9/9 secondary超过预注册容差，B2未执行。当前阻碍为运行时状态恢复一致性，不是缺少检查点。34项primary完备不代表未序列化电动力内部数组已无损恢复。禁止放宽容差、重试、执行B2或spin-up；须新授权诊断和独立补丁验证。见reports/TIEGCM2023_CONTINUATION_VALIDATION.md。

## S3连续路线最新结果与门禁
用户新授权的一次S3连续7210步已完成，7主历史/293次历史时刻（共同窗口290帧），原生冷echo诊断缺失单独标N/A；不能要求冷echo已有DEN/ZG，也不能跳过暖态缺失检查。此次曾由guardian接管同一MPI进程监控，无额外启动，详见S3_RUN报告。S3基础工程验收通过但不代表预热收敛；当前不自动运行S7、Restart修复或Swarm阻力。精确高度基准/沿轨8邻列门禁仍未闭合，禁止外推。S7需新授权，14个secondary卷按源码调度生成。

## S7完成后的长期门禁
已新授权完成一次S7连续12970步，无guardian/续算/重试。S3/S7共同290帧比较表明3天候选预热不满足全部预注册标准，S7也非真值/未证明初态无关。DEN/ZG/N2仅在已核实冷echo身份下允许原生未计算，暖态缺失必须拒绝，冷TN/风/O1/O2/HE仍检查。当前不自动增加预热或轨道积分。原生ZG内部高度共同有效率不是Swarm沿轨有效率；未统一参考面保持N/A。N2近small=1e-6处巨大相对差须连同绝对差/顶边界一起报告，不改冻结1e-8相对统计门限求PASS。当前GPI起日03-14，更早启动需新驱动和授权。入口reports/TIEGCM2023_S3_S7_COMPARISON.md及docs/TIEGCM2023_NEXT_STAGE_DECISION.md。

## 原生密度接口最新门禁
TiegcmDensityProvider仅对显式TIEGCM_NATIVE_ZG和模型地理纬度提供已测试查询；外部ITRS/WGS84关系未闭合，必须返回EXTERNAL_DATUM_UNVERIFIED或抛异常，禁止静默近似、密度补0和高度外推。每次要求两时间帧×四水平邻点八列全部有效，即使权重为0亦检查；极冠超出±87.5°原生中心域明确拒绝。使用前核验原NetCDF与审计清单SHA，查询元数据中的清单哈希本身不是逐次数据验证。接口验证/1000原生点全有效不等于Swarm覆盖率，见TIEGCM_SWARM_COORDINATE_DATUM及DENSITY_INTERFACE_VALIDATION。当前没有新的模型或真实阻力授权。

## 探索性坐标实验与正式接口分离
用户已授权完成独立PROVISIONAL坐标/高度偏移离线分析，不能将这些映射写入正式外部接口。provisional_coordinate_adapter无density_kg_m3协议，只能显式选择假设并调用query_provisional；A/B及人为偏移的条件查询100%有效，不等于正式沿轨有效率或参考面已验证。偏移不是置信区间/误差界；S3/S7、坐标和插值差不能直接相加成总误差。正式接口仍EXTERNAL_DATUM_UNVERIFIED，当前没有模型或真实RK45阻力积分授权。详见reports/SWARM_PROVISIONAL_DENSITY_ANALYSIS.md。

## 六小时合成气动阻力集成完成后的门禁
用户已单独授权并完成provisional_drag_orbit_v1：4次1h预检/收敛、5组6h主实验、4次6h必要tight，共13次真实初态探索传播；不是正式精度评估。所有成果保留PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST三重标记，正式外部密度仍EXTERNAL_DATUM_UNVERIFIED。私有桥仅显式构造，不可自动启用。结果是模型间差异，不叫预测误差；当前参数m400kg/Cd2.2/A1m²为演示，不能冒充实物。查询失败必须中止。当前授权已完成，不自动追加传播/延长窗口/新TIE-GCM或训练。见PROVISIONAL_DRAG_ORBIT_EXPERIMENT及NUMERICAL_VALIDATION。


## D5经验密度接入后的最新门禁
本次另获授权完成msis_drag_orbit_v1四次D5传播（1h base/tight、6h base/tight），未重跑D0—D4。本次133项测试通过。MsisDensityProvider使用Astropy datetime64保留内部时刻精度，Ap仍按UTC三小时桶切换，不平滑。所有轨道成果仍为PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST，不能以探索残差排名真实精度；TIE正式外部接口仍拒绝。三路线仅工程原型齐备，正式高度/气动/姿态推力/完整受力与独立物理验证尚未完成。后续不自动扩窗、运行新TIE、重放本次标签或训练。参见PHASE1_ORBIT_DENSITY_COMPARISON.md及MSIS_DRAG两报告。


## J3/J4完成后的最新门禁
已单独授权完成high_order_gravity_v1三次无阻力6h（G1、G2、G2-tight），G0读取旧D0。新势为保留名义J2+按μR^n重表达EGM2008 J3/J4，不能称完整标准球谐。G2终点改善但全段RMSE恶化，不能按参考残差拟合或挑点宣布精度提升。未来升级引力必须所有密度组共同更新，不混旧TIE-J2与新经验组归因。ESA旧5.13 q/平台标志有产品与概览/详细定义差异，0601适用性仍需确认；f_thr单位mN，Cd/有效面积未知。新阻力矩阵、48h、TIE/AI运行均须新授权。本次142项测试，真实参数/高度/完整受力门禁不因通过数值测试而解除。

## 统一8×8球谐完成后的门禁

已另获授权完成spherical_harmonics_v1十分钟预检、H1六小时base/tight；EGM2008完整n≤8所有m、源GM/R/fully_normalized/tide_free，含中心项，不再叠central/J2。地固完整旋转，不仅轴向。独立SHTOOLS Fortran与151测试通过，但8×8不等于精密完整受力。旧G0/G1/G2及D0—D5不改，今后密度矩阵必须共同使用同一冻结引力/初态/数值/气动，不混旧新归因。真实Cd/面积/姿态/推进器与TIE高度等门禁不因残差降低解除；f_thr名义mN不是已确认实测推力。20×20/第三体/SRP/阻力矩阵均待新授权。外部参考仅隔离Fortran扩展，prepare_spherical_reference.py可准备，不安装/升级原数值包。

## 12/20阶截断敏感性后的最新门禁

已另获授权完成gravity_truncation_v1：一次H3十分钟预检及H2/H3六小时base、H3tight，原H1只读；163测试通过。12→20终点差133.266m/最大160.063m，5m目标未达到，不得称20阶充分或将差当真值误差。扩展类继承旧8阶递推，已验证仅至20阶，不可未经验证直接升90阶。日月/SRP/潮汐/GR仅历史H1离线预算，builtin位置不是DE440星历，任何新增受力传播/更高阶/密度矩阵均需新授权。真实气动/推力/正式TIE高度等旧门禁不变，未来密度组仍须共同冻结引力和其他设置。

## 40阶与日月完成后的最新门禁

gravity_third_body_v1已另获授权完成H4/H5各两次600s短例及各一次6h，H3只读，H6未运行。176测试、SHTOOLS/三点Horizons几何检查通过；40−20终点15.364m/最大33.089m，5m目标仍未达。短例收敛不等于全6h，H4/H5全窗与配对tight为PENDING，不能全部差异视作已隔离物理贡献。ERFA builtin保留PROVISIONAL_EPHEMERIS与Newtonian坐标/GM时标限制；GM来自DE440不代表位置是DE440。后续H6/全窗tight/更高阶/密度矩阵均需新授权，不用SP3残差最小选力；正式气动/推力/TIE高度等门禁继续。


## H6完成后的最新门禁

common_force_validation_v1已按单独授权完成H4/H5六小时tight与H6六小时base/tight、两次600s预检；单轨0.5m和配对0.1m门禁通过，181测试通过。旧报告H6未运行/全窗PENDING属于历史状态，最新看H6两报告和本轮审计。仅冻结provisional_common_force_model.json作下一阶段条件背景，PROVISIONAL/HINDCAST/FORCE_MODEL_INCOMPLETE与PROVISIONAL_EPHEMERIS保留；40阶未证明截断收敛，真实气动/推力/高度/预热等门禁不变。C0—C3只有设计，尚未执行；新矩阵/长窗/更高阶/TIE/AI均需新授权，不能重复本次传播或混用旧J2密度组解释新力场。每次任务结束仍安全同步GitHub，不强推。


## H6密度矩阵完成后的门禁

common_density_h6_v1已单独授权完成C1/C2/C3各1h和6h base/tight共12次，C0读取既有H6，187测试及单轨/配对数值门槛通过。所有结果PROVISIONAL/SYNTHETIC_AERODYNAMIC_PARAMETERS/HINDCAST/FORCE_MODEL_INCOMPLETE，加PROVISIONAL_EPHEMERIS。旧J2 D0—D5仅历史条件；不得混旧新排名。共同配置SHA、旧源码/驱动/数据保持，正式TIE仍EXTERNAL_DATUM_UNVERIFIED。真实参数/推力/高度/预热/时间分辨率及截断/缺失力门禁继续。任务结束停止；任何新增传播/长窗/TIE/更高阶/AI须新授权。


## 第二阶段启动后的最新规则

用户已授权并完成阶段一报告整理和一次官方Direct两小时自回归（fourcastden_two_step_v1，Jan4 00→01→02，192测试）。历史单步保留，不当作新成果。预测反馈与未来辅助/驱动区分，HINDCAST；未来真实物理状态不得反馈。四权重不等于完整训练复现，原训练入口与2000—2022数据仍缺。AI输出Z非ZG、1h非S7的10min；未经规范转换不得输入S7或取消正式高度门禁。阶段一工程和条件敏感性通过，正式气动/推力/高度/预热/受力门禁仍开放。此任务已结束，Flow/扩6或24h/训练/新轨道/TIE均需另授权，所有新成果继续安全同步GitHub。


## 官方Flow两步完成后的规则（2026-10-22）

fourcastden_flow_two_step_v1已单独授权执行一次Flow两步，Direct历史只读，198测试通过；Flow为normalized delta加当前normalized state，不能当直接状态或光流。预测反馈/辅助条件区分并保留HINDCAST；一个初值两步不能排名总体架构。DEN层间绝对/相对权重差需同时报告，Z非ZG。官方权重/static/旧结果不改；更长窗口、更多初值、history/log变体、训练、轨道/TIE均须新授权。本次完成后停止，安全同步GitHub规则继续。


## 五日期两小时检查后的门禁

fourcastden_multidate_v1已单独授权新增4固定日期Direct/Flow各2h共8序列16forward，Jan4历史只读，206测试通过。n=5初值不能用格点作独立重复，不能宣称全年/强磁暴/真实大气或轨道精度；Mar23整日增强不代表00—02强驱动，必须用实际NPZ条件。模型与数据原件/归一化统计不改。log-DEN本次仅静态CPU检查，无forward，numpy/CUDA和公平物理ACC门禁待解。新的history/log、更多日期、长时、训练、TIE和轨道均需另授权，完成后停止并安全Git同步。


## 官方log-DEN完成后的门禁

fourcastden_logden_multidate_v1已另授权完成5个两步序列/10forward，215测试通过，Direct/Flow历史不重跑。源码隔离副本修正气候态单例形状、逐层仿射广播及np.power/CUDA，原件/权重/统计保留。native DEN ACC在log空间，不能与普通物理指标混排；公平评价使用共同原始物理目标、普通物理气候态及kg/m3。static_log非DEN统计也不同，不称纯log开关消融；本次log绝对指标改善但高层相对误差未改善。新history/长时/训练/TIE/轨道须新授权，正式物理参数和坐标门禁继续，结束安全Git同步。

## 官方History首次公平基线后的门禁

fourcastden_history_comparison_v1已单独授权完成Jan4同01起点4模型各2h（8正式forward），另1History真实预检；221测试。History额外00真实帧，两个177块按旧→新/各自下一小时辅助拼接354，第二步real01+pred02，非teacher forcing。log复用原隔离层，原件/统计/旧数组不改。单窗口History没有优于Direct，Flow/log旧五日期00起点排序不能直接沿用新起点。未来其他4日期03补帧及16序列、6/12/24h、训练/轨道都需新授权；HINDCAST/TIE参考不代表观测或轨道准确度，所有既有物理门禁保留。每次结束安全同步GitHub。

## 五日期四模型共同01时评价后的门禁

fourcastden_four_model_multidate_v1已另授权完成后4日期03补帧及16序列32forward，Jan4只读复用，无额外真实预检；226测试。History DEN两个时效5/5不优于Direct/Flow，Dec部分风场例外；高层Flow第1h5/5最低、第2h3/5，不能按胜窗数或均值单独挑最终模型。00/01的同lead目标不同，共同02目标lead和初态信息又不同，不作纯驱动因果。原统计/权重/旧数组不改，不放宽门槛修补较差结果。下一项6h仅设计（Jan4与按外部GFZ预选Mar24），需要新数据/任意步反馈测试及新授权；不自动6/12/24h、训练/TIE/轨道，真实大气与轨道门禁不变，任务后安全Git同步。

## 两日期四模型连续6小时完成后的门禁

fourcastden_six_hour_v1已单独授权完成Jan4/Mar24各4组6步（48正式forward）加1次Direct短例，232测试。任意步检查与真实hooks确认History第三步起两个预测状态、Flow normalized增量及log匹配表示，无未来物理真值重置；Jan4前2步与旧数组逐元素一致。数据初次HTTP500后有界只补剩5帧，合计12新样本/25.74MiB，旧文件不改。Jan4高层2—6h Direct较低；Mar24 History2—4h、log5—6h较低，不以两窗定总体架构/地磁因果；near组随参考ZG可变，固定upper与逐层另报。12/24h仅设计、不自动执行/训练/TIE/RK45；真实大气与轨道参数/高度门禁不变。任务后安全同步GitHub。

## Jan4四模型连续12小时后的门禁

fourcastden_twelve_hour_jan4_v1另授权完成4×12共48forward，无额外GPU预检/重试，237测试。所有模型前6步inputs/scalars/raw/state及公共指标与旧6h精确一致；History12步滑窗/四模式毒化通过，原checkpoint/static/source不改。Jan4高层Direct+2—12较低，后期误差非单调；单窗口不作全年架构排名/观测或轨道精度。Mar2412h只设计，24h/训练/TIE/RK45不自动执行；2023不调参，训练完整入口和2000—2022数据缺口见TRAINING_READINESS。结束安全Git同步，下一步等用户授权。

## 两窗口12小时完成后的门禁

fourcastden_twelve_hour_mar24_v1已另授权完成4×12/48forward，无额外GPU预检/失败重试，239测试。Mar24前6h input/scalar/raw/state与旧6h精确一致、旧指标精确复现，Jan4仅只读对照。near Mar24 log+5—12较低但+12固定upper Direct较低、History顶部/极区有条件优势，near层组+12变化须披露；不按两窗挑最终架构或作地磁因果/观测/轨道精度。训练计划仅静态，2023不调参，24h/训练/TIE/RK45均需新授权；原作者/权重/统计/旧结果不改。结束安全Git同步后停止。

## 独立训练工程合成预检后的规则

用户新授权建立src/training并仅合成验证，非官方完整训练复现。247测试；首GPU v1缺CuBLAS确定性环境在首forward失败0step，保留记录；独立cublas_v2设置:4096:8后完整原AFNONet随机初始化3step、step2保存恢复后step3成功，两次监督累计约12.25秒，无官方权重/真实数据训练。今后CUDA确定性运行必须在torch导入前设置该环境，勿自动重放已完成标签。SGD0动量仅合成资源假设，不能视作作者协议或科学训练效果。原件/权重/历史SHA不改，真实2000—2021/2022样本与协议/许可仍缺，2023不调参；真实训练/24h/TIE/RK45均等新授权。结束安全Git同步，停止。
