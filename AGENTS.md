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
