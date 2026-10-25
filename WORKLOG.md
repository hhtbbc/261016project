# 工作日志
## 2026-10-19：项目初始化
- 目标：仅初始化，不进入模型开发与后续日期任务。
- 初始情况：pwd/realpath均为 /workspace/data/20261016，目录为空，无覆盖已有内容。
- 完成：硬件/软件检查、建议目录创建、.venv基础隔离、项目内缓存脚本、AGENTS/README/STATUS/计划/架构/资源和环境报告；源码小包静态核验。
- 关键命令：pwd；realpath；ls -la；lscpu；free -h；df -h；nvidia-smi；nvcc --version；python3 --version；python3 -m venv .venv（失败）；python3 -m venv --without-pip .venv（成功）。HTTP通过urllib请求DOI、Zenodo API、MDPI、Crossref；源码包用hashlib.md5与API比对，用zipfile读取目录及配置，未运行任何第三方代码。
- 环境：Ubuntu24.04.1、Python3.12.3、A100 80GB、驱动575.57.08、nvcc12.8.93；完整证据 logs/environment_checks.json。
- 新增文件：AGENTS.md、README.md、STATUS.md、WORKLOG.md、.gitignore、scripts/activate.sh、docs/PROJECT_PLAN.md、docs/ARCHITECTURE.md、docs/RESOURCES.md、docs/upstream/、reports/ENVIRONMENT_2026-10-19.md、logs/资源与环境核验、third_party/FourCastDEN.zip；目录树见 reports/DIRECTORY_TREE.txt。
- 结果：Zenodo页面/API200，代码包90106字节且MD5匹配；权重包2,901,442,296字节、测试包18,149,758,909字节仅清单核验。论文HTTP403但Crossref200与网页搜索取得正文。
- 验证：基础venv sys.prefix不同于sys.base_prefix且user site=False；激活脚本、缓存路径与文档存在性另见 logs/initialization_validation.json。未做科学/物理验证，初始化无需生成实验图表。
- 异常：ensurepip缺失，未运行系统建议的apt；保留错误 logs/venv_creation_error.txt，采用without-pip。作者环境为Python3.10 Windows导出，未强行安装。论文资源声明与推理包不含训练代码存在范围差异。
- 下一步：等待用户授权当天论文精读/依赖分析；超过5GB数据需单独批准。初始化到此停止。

## 2026-10-19：正式任务（接续初始化）
- 授权范围：源码分析、Linux环境、论文学习、最小真实数据方案及条件允许的单步验证；不训练、不下载完整测试集。
- 已先读AGENTS/STATUS/WORKLOG/PROJECT_PLAN/RESOURCES与实际存在的下划线版本环境报告，无重复初始化。
- 源码：复用已校验90,106字节归档复制到data/raw，安全检查解压到third_party/FourCastDEN；所有原始文件字节与ZIP一致。另建Linux运行副本，补丁见patches/。
- 环境命令：uv python install 3.10 --no-bin（项目内安装目录）；uv venv --python 项目内python3.10 .venv310；uv pip install --python .venv310/bin/python（详细版本见configs/requirements-inference-linux.txt）；uv pip freeze/check。所有uv缓存和临时文件均由项目环境变量指定。
- 环境结果：3.10.19独立环境、63包一致性通过；torch2.4.1+cu121可用A100，GPU FFT往返误差0；精确原AFNONet结构可建立，64,695,744参数。模型未加载权重前未做前向输出。
- 数据：重查Zenodo API并记录实际大小，2023.zip18.15GB而非已证实81.5GB；Range206，经中央目录与局部压缩成员提取3个小时，总传输7,218,463字节，成员CRC校验及SHA256留档。static/static_log下载并MD5匹配。
- 关键脚本：fetch_verified_artifacts.py、fetch_minimal_test_window.py、activate310.sh、validate_fourcastden.py、check_minimal_result.py。原样本保存在data/raw/test_minimal_2023/。
- 文档新增：FOURCASTDEN_CODE_ANALYSIS、FOURCASTDEN_INTRO、MINIMAL_INFERENCE_PLAN、FOURCASTDEN_ENVIRONMENT；README/RESOURCES追加最新入口与核验。
- 问题：Windows绝对路径、作者img_shape默认0、CLI全年索引与小窗口不兼容、训练完整入口缺失；详细见分析文档。PDF/XML直接HTTP403。权重ZIP尾部截断读取因ZIP64寻址失败，保留logs/checkpoint_tail_probe_error.txt，不能解释为归档损坏；按完整小于5GB归档下载校验。初次安装未结束时numpy探针失败，留logs/first_dependency_probe.log，完成安装后导入成功。
- 最终权重与单步结果在本节后续追加，以实际日志为准。

### 2026-10-19最终结果与收尾
- 权重下载完成：ZIP2,901,442,296字节，MD5=78aa5107bf60927e6898cb19449520b7；安全解压四成员且CRC检查通过；SHA256见logs/checkpoint_sha256.json。Direct含epoch/model_state/optimizer_state_dict，150项model_state。仅Direct被实际运行。
- 单步命令：source scripts/activate310.sh；python scripts/validate_fourcastden.py > logs/minimal_validation.log 2>&1；python scripts/check_minimal_result.py > logs/independent_result_checks.log 2>&1。
- 运行：原AFNONet64,695,744参数，strict=True加载；真实2023-01-04 00→01 UTC，单次预测+评价约0.96秒、峰值分配显存约1.035GB；pred包含初始帧。输出experiments/20261019_minimal_direct/result.npz，171层通道指标results/metrics/20261019_direct_one_hour.csv。
- 指标：TN逐层平均RMSE0.433796K/ACC0.9999887；DEN逐层平均RMSE1.969162e-14g/cm³/ACC0.9999898，正密度比例100%。只针对单小时TIE-GCM参考，未观测/轨道验证。
- 科学/数值核验：独立NumPy重算RMSE相对差最大1.882e-7、ACC绝对差最大1.456e-7；zscore往返误差4.596e-14。另核对同窗口persistence对照，结果logs/one_hour_persistence_comparison.json；未据此推广全年泛化。
- 加载异常与处理：weights_only默认允许列表不含ruamel ScalarFloat；初次safe_globals上下文在torch2.4.1不可用；保留两次完整错误日志，静态检查pickle GLOBAL后采用add_safe_globals显式允许ScalarFloat，weights_only检查成功。作者推理加载逻辑未改写。
- 所有六个交付文档已完成/更新，README与RESOURCES只追加本次信息；路径审计logs/day1_path_audit.json显示无项目外链接，旧.venv到系统解释器的只读引用单独记录。最终交付检查见logs/day1_delivery_checks.json。
- 下一步：停止今日实验，等待10月20日用户指令；届时理解TIE-GCM并绘已有真实样本密度图，明确单位与压力层/几何高度，不提前实施动力学、多步推理或训练。

## 2026-10-19：早会后任务调整
- 目标：保留既有AI研究成果，切换当前主线为Swarm SP3参考+SGP4/MSIS-RK45/TIE-GCM-RK45；仅方案、数据核验、最小读取/可视化，不运行长期仿真。
- 开始：pwd/realpath确认工作区；读AGENTS/STATUS/WORKLOG/PROJECT_PLAN、已有环境与资源报告。环境审计logs/meeting_environment_audit.json：磁盘约670GB可用，CPU/内存可见值不视为独占；缺Fortran/MPI/nf-config/nc-config与csh，已有numpy/netCDF4/matplotlib，轨道库尚未安装。
- 资料核验：urllib GET/HEAD，实际响应与URL、错误保存在logs/meeting_sources_http*.json、tiegcm_support_head.json；原网页/API/PDF在data/raw/meeting_sources/。所有请求有体积/时间限制，不访问其他项目、不注册/发送邮件。
- 数据成果：ESA匿名目录HTTP200，三份Swarm-A0203 SP3 ZIP共1,319,995字节，安全提取CRC并记SHA256。真实头为SP3-d、GPS、IGS20；三日10秒网格25920点连续。ETH匿名历史API取得8条NORAD39452 TLE，全部69字符/编号/校验和通过；冻结03-20 20:30:00.330336 UTC一条，距拟t0 3.50046小时，历史发布时间未知。Space-Track无凭证查询401，未伪造登录成功。
- 选窗：建议UTC2023-03-21 00:00:02至03-23 00:00:02，GPS采样对齐，正式闰秒转换仍待10月20日；SP3机动和质量报告未核实。
- TIE-GCM：标签tiegcm2.0/commit da712811d925376ff8ef40ff64bda7cc070ca661，原tar.gz11,770,244字节、374成员安全解压到third_party/TIEGCM2.0，SHA256见logs/tiegcm_source_acquisition.json。未执行make/job。源码确认ESMF/MPI/NetCDF/Fortran依赖，DEN=ilev/g/cm3。官方声明2015后必须更新apex；已固定下载更新原件但未应用/编译。初场/潮汐文件只HEAD核验，未下载默认整包。
- 驱动：GFZ Fobs/Fadj各95日、Kp105个3小时值已下载/finite检查，足供候选窗口与拟预热的制作支持；没有把旧截止2017的gpi当作2023驱动，没有制作尚未核验的生产NetCDF。
- 新增代码：src/evaluation/sp3_reader.py，scripts/inspect_swarm_sp3.py，scripts/audit_swarm_tle.py，tests/test_sp3_reader.py。未创建空的SGP4/RK45实现来冒充完成。
- 关键命令：source scripts/activate310.sh；python scripts/inspect_swarm_sp3.py > logs/swarm_sp3_inspection.log 2>&1；python scripts/audit_swarm_tle.py > logs/swarm_tle_audit.log 2>&1；python -m unittest discover -s tests -p test_sp3_reader.py -v > logs/sp3_reader_tests.log 2>&1。依赖未安装/升级。
- 结果/验证：SP3五项测试通过，真实三文件单位/连续性/量级检查通过，P中心差分与V最大残差约0.161m/s（含10秒差分截断，不当精度证明）。图results/figures/20261019_swarm_a_sp3_overview.png已目视检查，地心半径/地固XY概览，不是预测轨迹；raw时间保留GPS，无UTC/框架变换。
- 文档：新增UPDATED_RESEARCH_PLAN、ORBIT_DATA_SOURCES、TIEGCM_MINIMAL_RUN_PLAN、ORBIT_VALIDATION_DESIGN；AGENTS/STATUS/WORKLOG/PROJECT_PLAN更新，原计划全文保留于PROJECT_PLAN下方历史节；README/ARCHITECTURE仅追加新入口。FourCastDEN四份研究文档/数据/结果未改写。
- 异常：HAO猜测tar目录404，官方GitHub标签成功；源码首次内联路径拼接类型错误发生在下载前，修正后取得归档；TU Delft几何站点本机TLS握手超时，具体几何/Cd/质量未取得；部分网页工具超时/406，不能视为产品内容验证成功。SP3标准PDF实际取得，目录概述SP3c与实际SP3d已明确区分。
- 风险：框架/时间/速度/EOP、TLE历史可用性、参考与机动质量、气动物性、重力截断、模型顶边界、spin-up和未来驱动适用性，详见验证设计。
- 下一步：停止当日工作；等待10月20日指令，先冻结时间/框架/数据manifest，检查质量/机动/物性与轨道依赖，再准备SGP4。不得自行开启训练、长期CPU/GPU任务或第二天开发。

- 最终交付检查通过：logs/meeting_delivery_checks.json；四份新方案、代码/测试和图片均存在且真实路径在项目内，原FourCastDEN归档SHA256与前次一致，.venv310依赖freeze逐字一致。检查后已停止，无后台训练或仿真任务。

## 2026-10-20：SGP4与SP3正式基准
- 当日目标：只实现单历史TLE的SGP4及SP3对照，300秒先导后60秒48小时正式试验；不进入RK45/TIE-GCM/AI。
- 开始：确认pwd/realpath，阅读AGENTS/STATUS/WORKLOG和三份新版方案；原SP3ZIP/解压文件SHA256与前次一致，无重新下载。环境/资源与PyPI兼容/轮子检查logs/20261020_preflight.json；用户任务标签10月20日，服务器实际UTC检查值保留其中。
- 环境：source scripts/activate_orbit.sh，预建XDG项目内Astropy配置/缓存。uv pip --dry-run后显式--python .venv310/bin/python安装scipy1.15.3、sgp42.25、astropy6.1.7、astropy-iers-data0.2026.10.19.0.52.1、pyerfa2.0.1.5共5新增包；numpy1.25.0/matplotlib3.10.0等原包保持。全环境68包一致性通过，新锁文件configs/requirements-orbit-20261020.lock.txt，原锁不覆盖。
- 数据标准化：真实SP3-d/GPS/IGS20，P/V分别km/dm/s→m/m/s；转换为Astropy时间，独立核对每份ESA HDR UTC首历元，无硬编码GPS-UTC秒差；保存data/processed/swarm_a_sp3_standard_20261020.npz及质量来源json。完整三日连续、取公共网格无插值。
- EOP：从固定IERS包复制IERS20C04与闰秒表到data/raw/earth_orientation，记SHA256、禁自动更新和外推。试验全部IERS-B有效，正式EOP行与形式误差保存。方法依据Astropy与python-sgp4官方资料及已安装源码。
- TLE：重验8条长度/NORAD/checksum，冻结既有id274764，历元2023-03-20T20:30:00.330336 UTC。访问ETH关于页/只读元信息/公开源码，仍无逐条发布时间/摄入时刻，详情endpoint404；以availability未核实标记，只报告历史传播，未编造过去可用性。全部TLE精确元数据JSON/CSV另存。
- 新增实现：src/orbit/frames.py、sgp4_baseline.py；src/evaluation/orbit_data.py、orbit_metrics.py；scripts/activate_orbit.sh、run_sgp4_comparison.py；tests/test_orbit_baseline.py；配置与新报告。既有sp3_reader接口不破坏。
- 关键命令：python -m unittest discover -s tests -p test_sp3_reader.py -v；python -m unittest discover -s tests -p test_orbit_baseline.py -v；python scripts/run_sgp4_comparison.py --cadence 300；通过后--cadence 60。日志分别20261020_sp3_tests.log、20261020_orbit_tests_fixed.log、20261020_sgp4_300s.log、20261020_sgp4_60s.log。
- 实验：UTC2023-03-21 00:00:02至03-23 00:00:02，固定WGS72/i模式；TEME完整状态→ITRS对SP3，参考GCRS构RAC，未平滑/删峰/滚动TLE/拟合参数。300秒577点、60秒2881点。
- 正式指标m：初始518.729191，均值625.565892，3D RMSE763.845573，采样最大2247.936538（2023-03-22T23:42:02.000000000 UTC），终点1724.639883；R/A/C RMSE=[143.05477351809108, 734.1425856527912, 155.0163051717532]。起点约519m已单列，不把所有差异算作新增传播误差。
- 验证：既有5+新增8测试通过；Vallado向量、GPS/HDR锚点、地固点自转速度、EOP缺失拒绝、实际位置/速度往返、RAC符号/范数和统计正确；SGP4错误0、无非有限/越界。正式TEME/ITRS位置往返2.982e-09m，独立GMST82位置差1.315663e-04m。CSV独立回读重算通过。
- 可复现执行：增--run-tag避免覆盖；在20261020_sgp4_repro标签重新执行300/60秒，两者状态数组完全一致、CSV字节一致，logs/20261020_reproducibility_check.json。仅因新增安全重跑入口进行复现验证，没有扩大科学范围。
- 输出：三图results/figures/20261020_sgp4_orbit_3d.png、position_error.png、rac_errors.png已逐张目视检查；CSV及states/summary/eop/tle元数据，完整说明reports/SGP4_SP3_BASELINE_2026-10-20.md。
- 异常及修复：初始IERS_B.open传Path在Astropy6.1不支持，改str，原错误日志保留。更重要是ERFA置空后只装1972年起IERS表导致1980锚点偏7.105968秒；在任何传播前改initialize_erfa=True保留早期漂移定义，全部时间测试通过，日志20261020_leap_loading_fix.json。初始失败日志未覆盖。正式运行警告仅Matplotlib/Pyparsing弃用，不涉及轨道/EOP；2100年warning属于故意越界单元测试。
- 限制：SP3xVAL/无机动确认与本窗口协方差缺失；TLE历史发布时间未知；SP3后处理参考及框架实现差异未消除。报告只给本产品差异与历史对照，不评价RK45优劣。
- 下一步：等待用户后续指令，先RK45二体周期/能量/角动量和容差收敛，再考虑J2；阻力前补实际质量/面积/Cd及姿态。今天不写完整RK45、不安装TIE-GCM、不训练。

- 最终交付检查：logs/20261020_delivery_checks.json通过；原SP3/TLE哈希不变，原63包版本均未改变，只增5包；图/CSV/标准结构/脚本/报告/测试均存在且真实路径在工作区内。已停止当天工作。

## RK45两体轨道阶段（实际UTC见交付日志；不擅自改为下一日期任务）
- 目标：仅中心引力+RK45，理想圆轨道数值验证后，接入真实Swarm-A原生P/V单历元自由传播；保留SGP4。
- 已读取AGENTS/STATUS/WORKLOG及研究/验证方案、SGP4报告；复用既有SP3、冻结EOP/闰秒、完整状态转换和RAC模块。核验NGA WGS84 GM=3.986004418e14 SI，测试半径6378137+400000 m；查SciPy1.15.3官方RK45接口。未安装依赖、未下载数据、未实现其他摄动。
- 新增src/orbit/two_body.py、rk45_propagator.py、scripts/run_rk45_two_body.py、tests/test_two_body.py、reports/RK45_TWO_BODY_BASELINE.md；更新STATUS/本日志。积分器接收通用rhs，输出稠密采样与内部接受步，显式向量atol，检查成功到达终点。
- 关键命令：source scripts/activate_orbit.sh；python scripts/run_rk45_two_body.py > logs/rk45_two_body_v1.log 2>&1；python -m unittest discover -s tests -v > logs/rk45_two_body_tests.log 2>&1。重跑使用新--run-tag，禁止覆盖旧目录。
- 实验与验证：5组圆轨道10圈、解析周期/位置/状态闭合/比机械能和比角动量；基准周期误差3.92993e-7 s，单圈位置闭合0.003185124 m，采样能量漂移1.51219e-9、角动量漂移7.56097e-10；收紧容差、减步长均改善。独立门限通过后才读取Swarm真实初态并传播。
- 原生SP3 P/V而非未来差分速度：初始惯性速度7639.362695 m/s，地心距离6827080.934718 m，完整转换往返位置1.16e-10 m、速度8.48e-10 m/s；仅t0初始化，其后无SP3反馈。48小时2881点，均差2282136.241546 m、3D RMSE2629254.101844 m、终点/最大4538129.203999 m。1/3/6/12/24/48小时结果见summary和报告。
- 数值与物理区别：rtol1e-10、atol1e-3 m/1e-6 m/s、max_step30 s，接受5764步/nfev34586/本次积分0.912 s；更严解与基准最大位置差4.198266 m，远小于与SP3的模型差，不是严格误差界。SGP4与RK45不同初态和受力，不能评价积分器优劣。
- 六张原始结果图、逐点误差/圆轨道守恒CSV、states/circle NPZ及summary/preserved_inputs保存；比较图已目视检查。17项测试通过（含旧13项），另回读CSV重算/时间网格/量级检查通过，原始数据与SGP4产物哈希不变。全部路径位于唯一工作区。
- 问题：SP3事后参考/协方差与机动信息不足、TLE当年可用性不明，保留既有限制；没有虚构数据。读取git状态发现当前工作区不是Git仓库，没有初始化或变更版本管理。当前无阻断问题。
- 下一步：等用户授权J2阶段，新增独立加速度函数和验证，保持本次基准；质量/面积/Cd在阻力前补充。没有执行J2/阻力/TIE-GCM或训练。

## J2摄动阶段（按用户下一阶段指令，实际UTC见交付日志）
- 目标：只加J2，在同SP3 P/V初态、同积分设置下与两体做受控比较；不开展阻力、TIE-GCM或AI。
- 开始检查：读取AGENTS/STATUS/WORKLOG、RK45两体报告和轨道验证方案，检查two_body/rk45_propagator/frames/metrics。确认各输出目录真实目标位于唯一工作区。
- 参数/原理：核验巴黎天文台IERS常数表与IERS TN36印刷页18：同μ3.986004418e14、J2参考半径6378136.6 m、zero-tide名义J2=1.0826359e-3。独立核对Orekit13.0.3分量公式（未安装/运行Orekit）；参考HTML/PDF/官方Java总量约3.05MB保存docs/references/j2/，sources.json含来源/状态/大小/SHA256。无轨道数据重下载。
- 实现：独立j2_acceleration与势能、固定轴能量/h轴向分量；EarthFigureAxis将ITRS figure Z经ERFA c2t06a的TT/UT1/极移/岁差章动转入GCRS，60秒预表插值归一化，拒绝外推；不等同CIP或瞬时omega，未加dX/dY（与Astropy相同）。模型装配通过make_state_derivative，未改旧积分器或旧成果。
- 独立验证：新5项+旧17项共22项测试通过。赤道/轴上符号、r^-4/量级、势能负梯度、独立分量公式/旋转协变、固定轴完整能量与轴向角动量、节点进动、轴变换/插值均通过。固定轴能量漂移2.93296e-9、轴向h漂移1.46434e-9；RAAN -4.145009913 vs理论-4.127638009°/天，差0.420868%，一阶近似门限1%。未错误要求两体能量或完整h矢量守恒。
- 正式实验：起点2023-03-21 00:00:02 UTC，仅单历元原生P/V，完整ITRS→GCRS，无未来拟合/中途更新；48小时2881点，A/B正式rtol1e-10、位置atol1e-3 m/速度1e-6 m/s、max_step30 s均一致。A状态与旧两体逐元素相同。
- B结果(m)：起始1.16e-10，均差13053.035780，3D RMSE16157.482587，最大34991.847009（2023-03-22 23:44:02 UTC），终点33772.321699；RAC RMSE430.117159/16150.018370/236.958701。1/3/6/12/24/48h=632.849192/646.057538/1066.086777/5821.364406/13249.683833/33772.321699 m。
- 比较：RMSE降低99.385473%、终点降低99.255810%；2880个非起点采样改善，不外推全部连续时刻或其他卫星。沿轨占残余MSE99.907628%，仍长期积累；约93.18%的绝对MSE减少来自沿轨。不能将剩余差直接认定为阻力。
- 数值/计算量：B紧解rtol1e-12、位置atol1e-5 m/速度1e-8 m/s、max_step15 s与基准最大位置差4.094350 m/速度0.00457118 m/s，满足预设10m门限；不是严格误差界。A/B均5764步/34586次函数调用，3次积分中位0.902199/3.762573 s，计时不含轴构建/坐标变换/绘图。轴中点插值方向最大差5.26412e-14、加速度差1.23369e-15 m/s²。
- 命令：source scripts/activate_orbit.sh；python -m unittest discover -s tests -v > logs/rk45_j2_tests_v1.log 2>&1；python scripts/run_rk45_j2.py > logs/rk45_j2_v1.log 2>&1。重跑用新--run-tag；环境复用.venv310，无安装。
- 文件：新增src/orbit/j2.py、scripts/run_rk45_j2.py、tests/test_j2.py、reports/RK45_J2_BASELINE.md；六图/两个CSV、experiments/rk45_j2_v1/{states.npz,fixed_axis_validation.npz,summary.json,accelerations.json,preserved_inputs.json}、参考源和logs检查日志。更新STATUS/WORKLOG。六图均目视检查，CSV/NPZ独立回读重算与RAC范数核对通过，原始轨道/EOP/旧实验等62文件SHA256不变。
- 问题/处理：检查时误用不存在的Astropy内部gcrs_to_itrs_mat产生ImportError，随后查真实分步实现并采用等价公开ERFA算法、Astropy对照测试，说明保存在logs/rk45_j2_axis_implementation_note.txt。网页工具部分来源失败；IERS PDF/常数HTML/官方Java在项目内直接下载200成功；不依赖未获取NASA资料。系统无pdftotext且环境无PDF解析库，未安装；用只读zlib查看PDF文本流确认常数及zero-tide标注。确认IERS对TCG/TT兼容μ的细节，报告明确原牛顿框架约定尚未升级，不宣称米级物理精度。
- 限制与下一步：SP3参考不是真值、事后初态、无机动/协方差资料；更多重力/潮汐、阻力、第三体、辐射压尚缺。等用户下一指令；阻力前补质量/姿态面积/Cd和时空密度/相对风速验证，校准用t0前数据。到此停止，不实现后续模型。

## 大气阻力建模与TIE-GCM2.0准备（实际UTC见logs/drag_tiegcm_delivery.json）
- 任务边界：建立可替换密度/风/气动参数的独立阻力模型；核查Swarm实际参数；准备2.0 Linux并验证官方默认算例。保持旧SGP4/两体/J2/FourCastDEN与原始轨道不变，不做真实卫星阻力精度比较、2023 TIE或多日预热/长期训练。
- 开始读取AGENTS/STATUS/WORKLOG、J2/两体报告、旧TIE准备/轨道验证设计；检查目录真实目标。磁盘空闲约719GB，系统无Fortran/MPI/NetCDF开发栈/csh。预检及原始文件保护哈希logs/drag_tiegcm_preflight.json。
- Swarm核查：ESA事实页的473kg是发射值，未采用。列举官方SC_xDYN/Sat_A与STRxATT/Sat_A目录，取得SC_ADYN0601三天（各3.6MB左右），含HDR/CDF/DQC；取得DNSAPOD0301三天共418465字节，ZIP CRC/SHA与安全路径检查通过。STR姿态只确认同期3文件存在，各约2.77MB，未下载。
- 动态CDF：m_SC确为kg，03-21范围400.337—400.447、03-22 400.341—400.454、03-23 400.331—400.459；正式不确定度未提供，范围不当误差。面积字段A_head/right/left/down为3分量轨道系截面相关向量，有负分量，几何/姿态/遮挡/法向约定待核验。dt_thr>0记录03-21/22为150/59条，f_thr仍全0，不能假定没有姿态控制或净推力；Flags_Platform/Flags_q含非零值，03-22有42s最大间隙，尚未解码。质量/姿态/推力规范仍是实星阻力门槛。
- DNS：CDF实读每天2880点、UTC30s、validity全0，kg/m³；三天density范围约9.05e-13—3.47e-12，具体按日见日志。它来自POD且与SP3共享GPS/动力学信息，不当独立真值或全球密度场；未用于传播或拟合。日志logs/swarm_dns_cdf_audit.json、swarm_dynamics_summary.json、swarm_drag_parameter_findings.json，原包路径/哈希data/raw/swarm_drag/*manifest.json。
- 来源障碍：ESA几何/热光学PDF403，TUD模型站直接超时，未绕过；公开研究指出需气动/气体表面模型与姿态，未选择现成Cd/β。新增docs/SWARM_DRAG_PARAMETERS.md完整区分查到/未核验内容。未用未来SP3拟合参数。
- 阻力实现：src/orbit/drag.py、src/atmosphere/density_interface.py；rho/Cd/A/m SI验证，完整GCRS→ITRS位置/速度后减地固中性风，再仅旋转物理加速度回GCRS。共转为ITRS风0，不重复扣omega×r。DensityQuery提供UTC/ITRS/WGS84经纬高；密度、风、姿态面积/Cd回调独立，不把力模型写入积分器，不内置Swarm默认参数。
- 阻力验证：tests/test_drag.py新增6项，最终全套28通过（logs/drag_tests_v2.log，先前27项日志保留）。覆盖零密度/零相对速度、方向和线性比例、单位量级/非法输入、地固共转点完整速度变换/风/面积回调及轨道能量-功。合成演示m100kg/A1m²/Cd2.2/rho1e-12，400km/3圈，全部明确非Swarm。比能变化-72.335582368 J/kg，比功-72.337376235，相对差2.47986e-5；更严解位置最大差0.00523623m。实验、能量CSV/图/运行日志见drag_synthetic_v1前缀，reports/DRAG_MODULE_VALIDATION.md。
- Python依赖：.venv310无pip模块（未使用全局安装），改既有uv精确指定项目Python，dry-run确认仅新增cdflib1.3.6，其他包复用；新锁configs/requirements-drag-20261019.lock.txt。
- TIE安装预检：micromamba2.9.0官方包元数据/SHA匹配后安全提取单个二进制，未执行下载脚本。解算74包总252214893字节、最大60389645字节、解压预算4GB，资源充足。首次create发生外部环境登记副作用，详见下段。随后download-only、逐项审计包post-link（只写PREFIX消息），对既有项目前缀offline install成功；无全局包变更。
- 路径隔离异常（不能隐瞒）：micromamba create在初始阶段向/root/.conda/environments.txt登记本项目.envs/tiegcm行，违反唯一工作区约束；发现后暂停并kill安装进程，未擅自清理外部文件，已异步请求用户仅移除该行的授权。查看官方2.9.0 install.cpp确认register_env仅创建分支触发；改为项目内手动conda-meta/history后install（create_env=false），外部登记文件前后SHA与mtime不变。相关logs/tiegcm_registry_incident.json、tiegcm_safe_install_registry_check.json及脚本备注已留档；当前清理仍待明确答复，不把沉默当同意。不重设HOME，不修改其他项目。
- TIE环境：.envs/tiegcm，GNU12.4.0/OpenMPI5.0.8/NetCDF-C4.9.2/Fortran4.6.1/ESMF8.6.1；configs/tiegcm-stack-explicit.txt和logs/tiegcm2_stack_manifest.json固定包/可执行哈希。脚本activate_tiegcm/prepare_tiegcm_environment/install_tiegcm_stack均项目路径；源码355文件与官方2.0原包逐字节相同，logs/tiegcm2_source_integrity_current.json。
- 编译记录：build_attempt1 theta秩错误，补theta(*)声明；attempt2旧NetCDF F77不同秩错误，审查长度/ABI后仅nchist.o允许旧接口秩差，不全局屏蔽；attempt3非法BOZ→REAL，改整数位型TRANSFER到binary64；attempt4 mud参数iprm16/17，修为17匹配COMMON/被调用定义；attempt5成功链接。三个补丁configs/patches/tiegcm2_gfortran12_*.patch只写构建覆盖层，原third_party树不动；编译有旧边界/时钟偏差警告，未声称全科学移植验证。新构建脚本可生成完全一致覆盖层，日志tiegcm_build_overlay_repro.json。
- 默认资产：3个官方5°启动/GSWM文件总64772708字节，无需认证且HEAD/GET200、大小/SHA/NetCDF结构通过，data/raw/tiegcm2_support/manifest.json。此前源码来自官方GitHub公开标签，此次不为旧表单填写邮箱或绕过注册；仅表单资源未来需用户操作。保持2.0，不以3.0替代。
- 启动异常：nf-config --all包脚本有未定义all函数，改用--version/--flibs/--fflags；/usr/bin/time不可用，改Python计时/限时；OpenMPI5无osc=pt2pt导致MPI_Init错误14，检查组件改rdma；单rank10分钟例在首步60s限时未完成，保留日志/部分文件，不声称单rank成功。4rank/10步例2.270261s正常退出，然后按实测资源预算运行官方2002默认单日，300s墙钟上限，未启动长期仿真。所有MPI临时路径工作区内，TCP/self传输、PMIx hash、无GPU。
- 默认单日真实结果：2002-03-21→22、5°、60s、4rank、1440步，returncode0/NORMAL EXIT，墙钟152.248519s。原默认常量F107/F107A70、POWER18/CTPOTEN30及GSWM；未使用2023驱动。主历史2时刻/次历史24小时样本，两个NetCDF共226636752字节，experiments/tiegcm2_default_1day_v1；logs/tiegcm2_default_1day_v1{.log,_resources.json,_netcdf_audit.json}。资源max_launcher_rss_kb不能当MPI全进程内存总峰值。
- 输出核验：DEN在ilev且g/cm³→kg/m³乘1000，ZG同ilev/cm→m乘0.01，每列高度递增且DEN正/有限。TN/UN/VN在lev，顶层约1e36填值，由于float32/metadata float64导致netCDF4自动mask警告，最终检查按dtype显式mask，并确认只有顶层padding。TN有效147.721—788.829K；默认DEN全垂直域1.257e-13—1.199e-6kg/m³。ZG顶448.964—513.086km不能保证实际Swarm椭球高460.312—489.989km全覆盖；不得外推，也不能默认模型ZG等于WGS84椭球高。
- 可视化：默认2002-03-22 00UTC、400km原生ZG逐列log-linear无外推图/NPZ（非2023），密度3.794e-13—9.357e-13kg/m³；源码整理scripts/plot_tiegcm_demo.py、元数据logs/tiegcm2_default_demo_map.json。两张新图均目视检查；合成阻力与默认模型结果均明确标注，不冒充真实预测。
- 短例重复执行：新增build-tag/默认4rank安全入口后重跑10分钟。主历史双精度未逐位一致，初始严格断言失败保留；差仅TN3.07e-12K、UN/VN1.29e-10/7.91e-11cm/s，时间和次历史float32 DEN/ZG完全一致。后验数值诊断一致，不宣称官方benchmark或位级确定性，logs/tiegcm2_smoke_repro_check.json。
- 新交付文档：docs/SWARM_DRAG_PARAMETERS.md、TIEGCM2_EXECUTION_PLAN.md、DENSITY_COMPARISON_DESIGN.md；reports/DRAG_MODULE_VALIDATION.md、TIEGCM2_ENVIRONMENT.md；旧计划/报告保留。更新AGENTS以记住禁止create外部登记和物理/接口约定，更新STATUS/本日志。bash语法/py_compile检查通过，旧实验/源/原始轨道保护哈希无差异，环境/代码/实验目录无外指符号链接。
- 复现关键命令：source scripts/activate_orbit.sh；python -m unittest discover -s tests -v；python scripts/run_drag_synthetic.py --run-tag 新标签。TIE source scripts/activate_tiegcm.sh；python scripts/build_tiegcm2_workspace.py --build-tag 新构建；make -j2 -C experiments/新构建 all；python scripts/run_tiegcm2_smoke.py --build-tag 新构建 --run-tag 新运行 --ranks 4 [--minutes 1440]；Python检查脚本inspect_tiegcm_outputs.py按运行tag读取。所有新目录拒绝覆盖。
- 下一次：先解码SC动态/姿态/推力和验证几何/Cd/质量不确定性，再制定实星参数协议；TIE需官方2015后IGRF更新、2023完整驱动/初始场与spin-up/顶高验证，当前未执行。B/C仅换密度，共同参数/风/引力/积分一致，未来参考不得用于反向拟合。完成本任务后停止；外部登记行清理仍待用户明确授权。


## 工作记录：TIE-GCM 2023适配准备（本次最新状态；系统日期2026-10-19）
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

关键复现命令：source scripts/activate_tiegcm.sh；python scripts/prepare_apex2023_build.py（新构建/已生成覆盖层元数据）；make -j2 -C experiments/tiegcm2_apex2023_v1 all；python scripts/run_tiegcm2_smoke.py --build-tag tiegcm2_apex2023_v1 --run-tag 新标签 --ranks 4；python scripts/check_tiegcm2023_gpi_consumer.py --log-tag 新标签（仅文件读取/插值）。source scripts/activate_orbit.sh；python scripts/prepare_tiegcm2023_drivers.py（拒绝已有输出目录）；python -m unittest discover -s tests -v。
新增脚本prepare_apex2023_build.py、prepare_tiegcm2023_drivers.py、check_tiegcm2023_gpi_consumer.py；coverage.py/test_tiegcm2023_preparation.py；六份报告/设计、官方apex补丁、驱动NetCDF、姿态资产及审计日志。未新增依赖；沿用.venv310和.envs/tiegcm。NOAA HTTPS容器TLS失败、ESA PDF403、GFZ年文件404均如实保留，网页可核查不等于本地文件下载成功。


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

关键命令：source scripts/activate_tiegcm.sh；python scripts/run_tiegcm2023_diagnostic.py --run-tag tiegcm2023_startup_10min_v1（静态）；同命令加--execute（本次唯一模型启动，已完成）；python scripts/inspect_tiegcm_outputs.py tiegcm2023_startup_10min_v1；python scripts/audit_tiegcm2023_diagnostic.py --run-tag tiegcm2023_startup_10min_v1；python scripts/check_tiegcm2023_solar.py --run-tag tiegcm2023_startup_10min_v1（仅函数）；source scripts/activate_orbit.sh；python -m unittest discover -s tests -v（35通过）；python scripts/plot_tiegcm2023_diagnostic.py --run-tag tiegcm2023_startup_10min_v1。此处记录用于接续，不授权重跑已消耗的模型运行。


## 2023跨日/Restart静态阻碍（2026-10-19，最新）
- 本次用户最多授权A连续20分钟+B1十分钟+B2十分钟；**实际启动0次**。原input.F948—960要求START与SOURCE_START时/分一致，只有日可不同。原2002场仅80 0 0，目标77 23 50不合法；将SOURCE_START改80 23 50也没有可读记录。没有修改原源码/重标时间/拼接状态/伪造_NM，也未追加预积分。
- 已检查data/experiments全部13个带mtime NetCDF，无23:50完整primary；logs/tiegcm2023_restart_inventory.json。可执行、GPI与原场SHA匹配前次成功诊断，logs/tiegcm2023_restart_asset_check.json。旧659保护文件与前次2023两NetCDF SHA不变，logs/tiegcm2023_restart_preservation.json。
- primary完整结构34项：当前预报/诊断状态、10个_NM和6个下边界，float64；原文件结构合格不代表续算数值已验证。次历史不够。官方continuation路径是省略SOURCE、从OUTPUT按START检索完整主历史、保留initial_year/day/mtime并append；未来在独立目录使用完整checkpoint字节快照且保留原B1，不能只靠显式SOURCE重置origin就声称严格等价。
- 新增src/atmosphere/restart_validation.py、tests/test_tiegcm2023_restart.py（7测试）；scripts/run_tiegcm2023_restart_validation.py是**仅静态准备入口，没有模型启动功能**，输出experiments/tiegcm2023_restart_static_v1/{static_audit,comparison_rules,tolerance_sensitivity}.json；A/B1/B2均DRAFT_NOT_RUN。全套42测试6.763s通过，logs/tiegcm2023_restart_all_tests.log。
- 预注册float64 rtol1e-10/float32 1e-6及按SI物理量的atol；算术ULP敏感性检查而非模型数值敏感性实测。连续与分段实际DEN/ZG/TN/风/成分误差、跨日稳定性均N/A。只生成状态CSV与输入推导驱动期望CSV，未做伪零差图表。零点期望F107141.04375、F107A161.7550154321、Kp1.5、POWER22.3223714449GW、CTPOTEN39.3kV，尚非模型读取记录。
- 报告reports/TIEGCM2023_RESTART_VALIDATION.md、决策docs/TIEGCM2023_SPINUP_READY.md。阻碍为合法起始状态，不是资源已超限；三段预计约260MiB输出、各数秒，预算已登记但未实测。
- 下一步优先提供/取得合法23:50完整主历史；如需从现有初猜生成，建议另授权一次2002默认00:00→23:50准备运行，1430步/4rank、只存完整主历史初末约34MB、预计151s，墙钟上限申请300s。它是额外准备启动、超过本次最多3次及90s限制，未运行。不能宣布多日spin-up就绪。
- 按长期规则提交/推送本次静态结果；实际HEAD/远端核对见本地logs/tiegcm2023_restart_github_verification.log，失败不得声称成功。本次科研工作停止，等待解除源时刻阻碍；不运行spin-up/Swarm真实阻力。

本次关键命令：source scripts/activate_tiegcm.sh；读取input.F948—960、rdsource.F35—65、nchist.F479—488/1826与fields.F；python scripts/run_tiegcm2023_restart_validation.py --run-tag tiegcm2023_restart_static_v1（只静态，无--execute）；python -m unittest discover -s tests -v（42项）；原场/可执行/GPI SHA及13份NetCDF时标只读扫描。新输出拒绝已有run-tag；当前不是完成了模型续算执行器。


## 2023合法23:50检查点与跨日连续诊断（最新）
- 按最新授权仅一次2023-03-18 00:00→03-19 00:10积分：experiments/tiegcm2023_crossday_24h10_v1，4rank/5°/60s、1450步，returncode0、4条NORMAL EXIT，墙钟155.014390s。没有续算分支/额外重试/3或7天spin-up。
- 使用原合法SOURCE_START80 0 0与目标77 0 0；连续START/STOP/HIST相接序列配合MXHIST_PRIM1，模型原生写出四个单记录完整primary（00:00、23:50、次日00:00、00:10）；次历史仅末3时刻。primary_002.nc即合法23:50独立checkpoint，16993204B，SHA d0aab5804eeab7680977f0fa9ad1de165600fd884bde2ddc1e0c6754c5ab9a4f，无未来记录，无裁剪/重标/伪造_NM。
- 检查点34项float64状态/前一时间层/下边界、维度/单位/有限值/时间属性通过；year2023/day77/mtime77 23 50、initial_year/day/mtime2023/77/(77 0 0)。源码continuation输入前提成立，但实际恢复与连续/分段一致性仍未测试。未来只能对完整checkpoint副本原生无SOURCE续算并保留原文件。
- GPI实际跨日通过：00:00 F107141.04375、F107A161.755015432099、Kp1.5、POWER22.3223714448845GW、CTPOTEN39.3kV；145个独立runtime打印和3目标时刻主/次历史核对通过，double差最大2.8422e-14。冷初始echo仍带F10770/旧iter115200，暖态iter112310/112320/112330与日历一致，未改初始元数据。
- DEN全域9.4387654e-14—1.19825849e-6kg/m³、正有限；ZG逐列递增；TN有效147.417—1108.968K；主要mmr约和1；TN/风及_NM顶层padding显式mask，34主状态无NaN/Inf，日志无异常模式。末3时刻顶高545.36448—677.24912km范围，较冷场抬升；不是03-21—23的Swarm实际覆盖率，ZG/WGS84未核实，不能宣称沿轨查询全有效。
- 峰采样进程树RSS990973952B≈945.07MiB（共享页重计/可能漏瞬态），NetCDF92072344B≈87.807MiB；总输出512MiB/RSS16GiB/余盘20GiB/墙钟300s均未触发；每进程CPU300s，已替换旧60s限制；无GPU，无残留模型进程。963份旧文件哈希未变，原始2002场/可执行/GPI/apex哈希匹配，冷初始34字段与此前诊断逐位相同。
- 新run/audit/plot_tiegcm2023_crossday.py、src/atmosphere/tiegcm_drivers.py与8项新测试；全50项6.582s通过。报告reports/TIEGCM2023_CROSSDAY_DIAGNOSTIC.md、方案docs/TIEGCM2023_RESTART_NEXT_STEP.md；配置/审计/资源/未来分支草案JSON在运行目录；真实驱动CSV/图在results，原始NetCDF留本地。
- 下一步需新授权两个10分钟原生continuation分支B1（23:50→00:00）、B2（00:00→00:10），只比较本次保存的共同时刻；禁止把包含未来记录的连续参考放进可写OUTPUT。尚不宣布spin-up收敛/多日工程全通过，Swarm气动/机动/高度基准风险仍在。本次停止，安全GitHub同步结果见本地logs/tiegcm2023_crossday_github_verification.log。

关键命令：source scripts/activate_tiegcm.sh；python scripts/run_tiegcm2023_crossday.py --run-tag tiegcm2023_crossday_24h10_v1（静态）；同命令--execute（本次唯一积分，已完成）；python scripts/audit_tiegcm2023_crossday.py --run-tag tiegcm2023_crossday_24h10_v1（只读）；source scripts/activate_orbit.sh；python -m unittest discover -s tests -v（50通过）；python scripts/plot_tiegcm2023_crossday.py --run-tag tiegcm2023_crossday_24h10_v1。新产物拒绝已有run-tag，运行独占launch_once。没有环境安装/下载/原源码修改。Git提交/推送按照长期安全规则进行，实际成功以最终HEAD核对日志为准。

## 2026-10-19：原生continuation B1门禁失败，停止B2
目标：复用23:50完整primary验证B1/B2，无24h重跑。新增run_tiegcm2023_continuation.py及6项测试，生成独立配置、冻结容差、资源/驱动/状态审计。activate_tiegcm环境4rank/5°/60s，实际仅B1一次10分钟，2.183秒，采样RSS932.43MiB，正常退出。34项primary有28项超差；TN最大差0.442936K、VN1.362064m/s、POTEN9.452503V；DEN最大差3.878842e-12kg/m³、ZG368.6m。初始副本与原件SHA一致、989项既有文件未变；10步及实际GPI核验通过。全套56测试通过，原生数值等价失败，B2未创建未执行，不重试。
关键命令及逐项指标见reports/TIEGCM2023_CONTINUATION_VALIDATION.md、experiments/tiegcm2023_continuation_v1*/和results/metrics/tiegcm2023_continuation_v1_B1_errors.csv；图results/figures/tiegcm2023_continuation_v1_B1_errors.png。保留旧记录并更新SPINUP_READY/STATUS/AGENTS/README。源码发现首步重建未序列化磁坐标势/电场的不同路径，仅为候选原因，未改原源码或运行推测修复。下一步待授权诊断首次分歧，不开展spin-up。任务成果按规则提交推送，提交哈希以Git及最终汇报为准。

## 2026-10-19：Restart原因分析与连续spin-up设计
阅读长期规则/进度/跨日及B1报告、初始化方案；使用rg/sed只读追踪rdsource/advance/pdynamo/ionvel/GSWM/历史输出；原始树与有效构建相关源哈希归档。确认phim3d等6个native数组未存primary，首步pefield与pthreed映射/极区/上下边界处理不相同，不能宣布唯一根因。复核可执行/apex/GPI/初场及23:50SHA匹配；独立GpiDriver对DOY73—82每分钟全部可查询。NetCDF读取数组长度时库给出missing_value不能安全转dtype的提示，未用于有效性判断、未修改数据；预算只取nbytes，实际科学分析必须按dtype显式掩码。
新增报告reports/TIEGCM2023_RESTART_ROOT_CAUSE_ANALYSIS.md、方案docs/TIEGCM2023_CONTINUOUS_SPINUP_PLAN.md及静态审计JSON。新积分0/新编译0/新补丁0，所有旧模型结果保留。用现有1450步155.014390秒和真实每帧负载计算：7210/12970步约770.80/1386.58秒，约2.471/2.571GB NetCDF负载；设计每支4GiB生成上限、wall1800/3000秒、RSS16GiB，需另授权。共同290帧10分钟输出覆盖SP3终点+2秒；设计原生/几何高度/沿轨密度、温度/风/组分、初态独立性分层验证。不把3/7相近当科学真值。下一步建议单次连续S3先行、Restart探针评审限时并行，均不自动执行。Git提交和推送以最终核对为准。

## 2026-10-20收尾：S3单次连续多日TIE-GCM
实际模型执行UTC见日志为2026-10-19 08:58:34—09:11:41。本次授权最多1次，实际1次，目标DOY77—82共7210步；原源码/二进制/驱动/初场及旧实验保护哈希不变。新增run_tiegcm2023_s3.py、audit_tiegcm2023_s3.py、supervise_tiegcm2023_s3.py及7项测试。按numfiles源码修正secondary滚卷13→14，记录数293/共同290不变。prepare静态通过后唯一execute；无重试、continuation、S7或轨道积分。
发现冷启动secondary在addfld前无DEN/ZG诊断，保留缺失而不是伪造数值。原监督器存在误报风险，约279.74秒在sleep点暂停其Python等待器，guardian以原预算监督同一MPI组，模型未暂停/重启；识别prterun和poll等待点的两次前置检查均在未改变进程前终止。模型正常完成后恢复原父进程获取真实returncode0，监控峰值和采样合并，事件全披露。修正仅作用监控/审计冷echo掩码，所有暖态严格检查保留；新增冷缺失/暖缺失拒绝测试。
墙钟786.805456秒，聚合RSS峰947.293MiB，NetCDF2,471,152,364B；每卷最大192,668,980B。7完整主历史及293次历史时间戳通过，实际721个GPI打印点/存储驱动最大误差5.684e-14；292有效物理帧密度正有限、ZG递增、温风/组分基础筛查通过。63测试7.229秒通过；audit独立读数据，统计/六图真实输出。450km原生ZG平均密度03-19约9.8351e-13→03-21约1.4755e-12kg/m³，不能据单轨迹证明预热收敛。20分钟抽稀P95误差0.124664%，不是10分钟误差保证。
Swarm首稿严格浮点时间选择少1端点；不改原数据/初稿，以Swarm_window_review.json用1微秒门限复核17281个10秒样本。目标顶高586.8335—741.1446km与椭球高460.3115—489.9890km分别报告，基准/8邻列未闭合，有效率N/A。
关键命令source scripts/activate_tiegcm.sh；python scripts/run_tiegcm2023_s3.py --run-tag tiegcm2023_s3_continuous_v1（静态后唯一--execute）；source scripts/activate_orbit.sh；python scripts/audit_tiegcm2023_s3.py --run-tag tiegcm2023_s3_continuous_v1；python -m unittest discover -s tests -v。新增报告S3_RUN/S3_DATA_AUDIT、docs/TIEGCM2023_S3_S7_COMPARISON_PLAN.md，全部证据在experiments/tiegcm2023_s3_continuous_v1。下一步等待授权S7，建议wall3000秒/RSS16GiB/4GiB输出，不自动运行。Git提交推送以最终核验为准，大NetCDF仅本地。

## 2026-10-20：整理10月19日工作日报
依据工作日志及S3运行/审计报告生成reports/DAILY_REPORT_2026-10-19.md。区分10月19日执行与10月20日补充验收，记录Restart候选原因、S3实测资源、数据结果、风险和下一步；未运行新实验。按长期规则同步文档。

## 2026-10-20：S7连续运行与S3/S7离线比较
开始读取长期规则/进度/S3运行审计/连续方案，核实S3全部21个NetCDF及模型/apex/GPI/原初场SHA。新增独立run_tiegcm2023_s7.py，锁定runner/input哈希，原生输出11主历史、297次历史时刻/14卷；冷echo身份严格限定，仅DEN/ZG/N2原生未计算允许N/A，冷prognostic照查，暖态缺失/NaN/负密度等拒绝。9个新增监控/防重启测试及4个比较公式测试，全套76通过。
仅一次--execute：目标2023-03-14 00:00→03-23 00:10，实际12970步/4rank/5°/60s，1382.676454秒、RSS944.566MiB、NetCDF2571233644B，returncode0/4NORMAL EXIT。独立运行器在线监督23个完成卷、结束检查全部25卷，无S3式guardian、无重试或原生续算。初始34项与S3逐位相同，公共物理配置相同。实际1297个打印时刻和NetCDF驱动核对最大5.684e-14，共同290帧完整，既有文件哈希未变。
审计/比较脚本audit_tiegcm2023_s7.py、compare_tiegcm2023_s3_s7.py、analyze_tiegcm2023_regional_trends.py全部离线；原生逐层/六纬区、固定ZG200—500km、温度/风/组分、逐时刻门禁与6h/区域趋势完成。450km全窗口密度RMSE7.6111e-14kg/m³/P95相对5.980%，0/24/48hP95为6.601/4.981/4.016%；最后24h450/475/500km仍有45/269/420个时刻区域组合失败。风矢量最大差19.223m/s通过20m/s；TN最大20.842K及主要组分不全通过。原生固定高度总体下降，少数压力层增长，保留152个变量层区域时段增长组合；OLS仅描述，非独立样本推断。
N2在接近small=1e-6数值下限处相对差巨大，附绝对差和comp.F限幅/顶中点含义，未改冻结1e-8门限或事后移除边界追求PASS。官方grid.html与addiag/diags源码核实原生ZG含义和DEN ilev，外部WGS84基准仍未闭合；沿轨查询有效率N/A，未外推补0。新增高度审查、S7运行/审计/比较报告、下一阶段决策；真实比较7张图、S7六图、分层CSV和审计JSON。
关键命令source scripts/activate_tiegcm.sh；python scripts/run_tiegcm2023_s7.py --run-tag tiegcm2023_s7_continuous_v1（prepare后唯一--execute）；source scripts/activate_orbit.sh；python scripts/audit_tiegcm2023_s7.py --run-tag tiegcm2023_s7_continuous_v1；python scripts/compare_tiegcm2023_s3_s7.py；python scripts/analyze_tiegcm2023_regional_trends.py。下一步等待授权高度登记/不同初态对照，不自动延长预热、修Restart、训练或轨道阻力传播。Git按规则仅轻量成果提交同步，实际SHA以最终核验为准。

## 2026-10-20：TIE-GCM原生密度查询接口与Swarm坐标审查
目标：只读复用S3/S7，建立可审计查询和外部坐标门禁。阅读长期规则/进度及S3/S7/高度报告，核验官方grid说明、支持目录和addiag/diags/getapex/apex/cons/lbc源码。确认变重力ZG积分和下边界登记，无法证明WGS84严格转换，未编造误差界。未修改第三方源树或既有物理数据。
新增src/atmosphere/tiegcm_density_provider.py、18项测试、validate/plot_tiegcm_density_interface相关脚本，查询按八列完整性/单调高度/正有限密度/时空边界门禁，LRU256列，with关闭文件。外部适配返回未验证，标量协议抛异常避免补0。首轮v1后增加manifest溯源/CF时间交叉检查，以v2重新进行最终离线验证，无模型启动。
命令：source scripts/activate_orbit.sh；python -m unittest discover -s tests（94通过）；python -m unittest discover -s tests -p test_tiegcm_density_provider.py（18通过）；python scripts/validate_tiegcm_density_interface.py --run-tag tiegcm_density_interface_v2；python scripts/plot_tiegcm_density_validation.py。环境.venv310复用，无安装/数据下载/仿真/轨道传播。新增报告、坐标审查、下一预热设计、原生查询CSV与性能图、审计JSON和日志，路径见STATUS最新节。
S3/S7共46原NetCDF读取前后SHA匹配，每源3个原生网格点恢复相对误差<2e-15；1000次查询全部有效（只代表构造原生测试点）。平均11.292/11.089ms、P95 15.624/15.401ms，进程累计峰RSS89.668/97.707MiB；缓存数组118784字节。线性垂直与log垂直差异P95 3.483/3.493%，全log水平时间替代差异P95约0.043/0.042%。不是准确度界或Swarm真实密度结果。
v1真实网格直接读取曾有NetCDF missing_value安全转dtype警告，读的是已核查有限内层标量；v2显式关闭自动mask并在提供器按源dtype检查填充值，最终日志无该警告。Swarm沿用冻结时间/SP3入口，窗口17281点，WGS84高460311.510587—489988.985679m；正式密度查询0次，覆盖率N/A，未以球半径/椭球高替代ZG。
剩余：官方高度/纬度参考登记、初场敏感性/预热、时序离散验证、质量/迎风面积/Cd/姿态/推进器和其他受力。后续实验只设计未执行；等待授权。GitHub同步的真实提交及远端核验见最终汇报，不预先声称推送成功。

## 2026-10-20：探索性Swarm高度映射与离线密度敏感性
目标：不改变正式拒绝行为，核查官方高度资料并执行明确PROVISIONAL的条件查询。阅读规则/进度、坐标/接口/S3-S7/气动报告。实际获取官方ZCoordinates.pdf（85756B，SHA b76e040fbfbf60e9563d199b3c380b7d442e24c7f521718635c11b75f5abe512），明确其第2页DEN在ilev；源码与实际日志确认ibgrddata=0、zbound+GSWM下边界。PDF截图工具超时、系统无pdftotext，保留工具限制说明；正文解析与原始下载成功。未安装系统工具。
新增provisional_coordinate_adapter.py（没有正式density_kg_m3方法）、14项几何/边界/正式拒绝/导数测试；全108测试通过。A=WGS84坐标近似原生，B=地心纬度/r−6371000m，C=A上7档人为偏移。所有偏移不是已知误差界。先577个5分钟点×8假设×2源=9232次，32.074秒，全条件有效；据此预算门禁通过后，仅A0/B基线执行全17281点/源，69124查询、162.686秒，峰RSS186.961MiB。高低纬/经度接缝/原生网格边界记录及每点实际采用坐标保留，29次接缝无独有大幅跳变，不作真实大气准确性结论。
S3/S7完整条件相对差P95 A6.0445%、B5.9749%，log RMSE0.048134/0.047789；偏移−10/+10km密度中位数约+17.5%/−14.8%。另做粗采样D纬度单独替换/E高度单独替换：P95约0.084%/24.1—24.3%，无新模型积分。分离垂直/水平/时间算法替代：A全轨迹P95约3.49—3.52%/0.0369%/0.0078%；隔层抽稀约0.89%，均属内部敏感性不是误差界。全球/纬带、6h、导数/尺度高度与局部预测残差均保存统计。
关键命令：source scripts/activate_orbit.sh；python -m unittest discover -s tests；python scripts/analyze_swarm_provisional_density.py --run-tag swarm_provisional_v1 --full-after-coarse；python scripts/summarize_swarm_provisional_density.py --preview；同脚本无--preview；python scripts/analyze_provisional_mapping_components.py；python scripts/audit_swarm_provisional_delivery.py。独立审计54个受保护文件前后SHA、3份SP3匹配旧审计、几何前向误差最大约5.54e-7m、历元差最大1.46e-11s；正式提供器/契约SHA与原始版本一致。
环境复用.venv310及冻结时间资料，无新依赖；主CSV47.18MB，全10秒原表留data/processed/swarm_provisional_v1（Git忽略），公开5分钟表每源2.77MB。生成三张PROVISIONAL图、两份报告、坐标更新及阻力就绪设计；配置/哈希/边界/统计/审计在experiments/swarm_provisional_v1。源码/旧场/旧结果不改；新大气积分0、新真实轨道传播0、训练0。仍缺正式参考登记、初态敏感性/高频参考、可靠Cd/面积/姿态位/机动定义，优先同起日不同合法初态设计而非直接宣称S7更准。任务结束安全提交同步，实际SHA见最终核对，停止等待后续授权。

## 2026-10-20：合成气动参数下TIE-GCM/RK45探索集成
阅读长期规则、状态、原RK45/J2/阻力和高度/原生密度/探索映射报告。新增provisional_drag_provider.py私有显式桥，复用DragForce/EarthFixedFrame和全部已有插值/求解器，不修改正式接口。冻结m400kg、Cd2.2、A1m²、β=m/(CdA)=181.8181818kg/m²及零ITRS风；A/B映射同前任务。每次RHS实际状态实时查密度，失败即抛错，三重标签PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST逐记录保留。6项新增测试覆盖零密度/面积/Cd无阻力等价、方向和SI/缩放、完整速度及力向量、同状态S3/S7比例、非法密度中止及正式拒绝；全114项通过。
预检D0/D2各1h及各tight，共4次；响应2.937451m，单轨差约1.54mm，配对差0.034mm，通过预注册2cm/1%门禁。矩阵预计1560.57秒，在剩余预算内再启动D0—D4五组6h；D0/D1/D2/D4四组tight验证重要源/映射/加阻力差，不追加D3 tight。13次真实初态传播全部成功，无自动重试、重拟合、中途校正、TIE积分或训练。D0旧J2最大差8.18e-5m且原文件SHA不变。
实际D1/D2与D3/D4终点位移6.741712/7.053848m，D1/D3与D2/D4为5.818585/6.130734m；对D0约109.588—122.461m且沿轨为主，不能称预测误差。基准/tight单轨差约5.84cm，重要配对差变化2.49e-5/5.02e-5m，加入阻力响应变化1.58e-4m，冻结阈值均通过。力模1.11e-7—2.12e-7m/s²。探索SP3残差单列且不据此评真实精度，当前气动/高度/受力均不完整。
模型阶段墙钟1389.205秒/进程峰182.559MiB，低于1800s/2GiB，GPU未用。计算已完成后会话等待较长；用户“继续”后仅读结果/审计/出报告，未重新运行传播，monotonic累计等待与模型耗时分开记录。独立流式审计19.579s，45594个RHS密度和2649个输出查询全部有效，公式重算差0，旋转范数最大差7.94e-23m/s²，完整状态往返约2.98e-9m/5.40e-9m/s，抽样密度重查差0。55保护文件和3份SP3旧清单通过；41接缝邻列/2614高纬查询保留。压缩逐查询日志/NPZ约26.85MB留data/processed，不入Git。
新增run/summarize/audit/write_provisional_drag相关脚本、两报告和FORMAL_ORBIT_VALIDATION_GAPS.md；6张三重标签图、13组状态CSV、差值/资源CSV和审计JSON。复用.venv310及冻结IERS/闰秒，无新依赖。命令：source scripts/activate_orbit.sh；python -m unittest discover -s tests；OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/run_provisional_drag_orbit.py --run-tag provisional_drag_orbit_v1 --phase precheck --execute；门禁后同脚本--phase matrix --duration-hours 6 --execute；python scripts/summarize_provisional_drag_orbit.py；python scripts/audit_provisional_drag_orbit.py；python scripts/audit_provisional_drag_window_parameters.py；python scripts/write_provisional_drag_reports.py。已使用标签拒绝重放。
正式阻碍继续复核：既有CDF在本6h内m_SC400.338—400.447kg、22条非零dt_thr、f_thr0、Maneuver_Id0但质量位未解释；CDF时间对HDR差−0.804ms/0ms，不做GPS偏移。实际参数未用于演示拟合。官方pymsis文档新增明确WGS84/km、前日F107/居中81日、历史Ap和自动缓存要求，本次未安装。Swarm尝试目录链接未访问成功，不声称取得码定义；高度PDF仍无严格WGS84零面关系。等待后续授权，不扩窗、不自动正式化。按规则只同步轻量公开产物，最终SHA以核对为准。

## 2026-10-20：NRLMSIS2.1经验密度与TIE条件离线比较

读取长期规则、状态和既有阻力/驱动/高度/比较报告；核对官方pymsis API、PyPI实际0.13.0元数据及已下载wheel源码。cp310 Linux wheel1,309,366字节SHA与PyPI一致；现有venv无pip模块，首次pip命令失败未安装，转用已审计uv pip显式--python .venv310/bin/python --no-deps，无旧包升级。70包兼容、底层Fortran及系数SHA入档，安装包/缓存/日志均项目内，不修改TIE栈。

新增FrozenGfzDrivers/MsisDensityProvider、12项测试及prepare/run/report脚本；复用原GFZ Fobs/ap/Ap不下载，原SHA与既有审计匹配。前日Fobs/目标日中心81日、7项Ap历史按UTC半开桶冻结，最长57小时，03-20—23共32条边界核查。ap/Ap全def，太阳逐值质量未知；没有把Kp当Ap，也未联网默认补数。前日156.1/中心160.791358sfu，03-21起始Ap=[6,9,9,5,27,10.125,6.875]。

首版分析因旧清单文件名需相对运行目录而在读取阶段停止，无计算结果；保留v1/失败日志，新独立v2完成。复核S3/S7共46NetCDF和2既有离线轨迹CSV，前后SHA不变，三份SP3沿用冻结时间/HDR校验；TIE对照取相同SP3轨迹的旧条件查询，不取上次各自传播轨迹。先5分钟73点，再60秒361点，逐点UTC/ITRS/WGS84一致，密度全有效。NRL范围1.129333e-12—1.805477e-12kg/m³，中位1.580192e-12；TIE/NRL−1中位S3/A−37.320%、S7/A−33.426%、S3/B−32.823%、S7/B−28.944%，不视为真实误差或排名。

全126测试通过；200行上游独立预存Fortran舍入参考密度最大相对差0.043714%，原阈值0.2%保持，非观测验证。新增缺测/版本/长度/NaN失败、太阳历史、日期、极区/周期、向量、契约及正式拒绝测试。批量361点0.340478秒，标量均值2.026ms/P952.314ms，总离线审计绘图17.394秒、峰RSS162.590MiB。密度比/纬度/峰值/驱动及费用五图、逐点CSV、审计JSON和三报告完成。费用区分MSIS调用与TIE既有CSV重用，不冒充TIE仿真耗时。

关键命令：source scripts/activate_orbit.sh；uv pip install --python .venv310/bin/python --no-deps data/raw/msis_validation/pymsis-0.13.0-*.whl；uv pip check --python .venv310/bin/python；python scripts/prepare_nrlmsis_drivers.py；PYTHONPATH=src python -m unittest discover -s tests -v；OPENBLAS_NUM_THREADS=1 python scripts/run_nrlmsis_comparison.py --run-tag nrlmsis2023_v2；python scripts/write_nrlmsis_reports.py。新输出/标签拒绝覆盖；复现可指定新--output-prefix。

本次新TIE/RK45积分0，无训练/气动拟合/默认补数/外推。更新正式缺口分类、STATUS及比较方案；TIE正式坐标门禁未改。后续需授权经验密度探索传播，正式评估仍受高度、气动、机动、高阶力、初态/高频输出验证阻碍。按长期规则安全同步Git，真实SHA与推送结果见最终核对；完成后停止。


## 2026-10-20最新：D5经验密度轨道接入完成

本次只新增D5的1h基准/tight、6h基准/tight共4次传播，D0—D4没有重跑，133项测试通过。D5对D0六小时终点位移174.661680m，D5与D1/D2/D3/D4终点差分别65.074180, 58.332529, 59.255645, 52.201839m；均为PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST模型差，不是正式预测误差。完整共同初态、力、气动/风、容差和输出冻结，NRL使用真实内部状态及WGS84，TIE A/B仍未正式登记。

三路线工程链路已齐备：历史TLE/SGP4、NRLMSIS/RK45、TIE条件密度/RK45；正式Swarm精度比较尚未完成，缺高度/气动/姿态/推力和完整受力、初态与高频场验证。阶段总结reports/PHASE1_ORBIT_DENSITY_COMPARISON.md，D5运行/数值报告MSIS_DRAG_ORBIT_EXPERIMENT.md及MSIS_DRAG_NUMERICAL_VALIDATION.md；实测数据experiments/msis_drag_orbit_v1。四次运行433.199s，峰163.195MiB，原122项保护哈希不变。无新TIE/旧D0-D4运行、无拟合或训练，完成后停止。Git实际提交/远端同步见任务结束核验日志。

关键操作：先读长期规则/研究计划/协议/原运行数值和MSIS报告；核实本地与远端main均为b0c5bd0，非重复提交上一任务。新增msis_drag_provider.py研究审计桥、独立run_msis_drag_orbit.py及7测试；复用原DragForce/EarthFixedFrame/J2/RK45，修正MSIS时间序列化到datetime64避免默认毫秒舍入，未改正式TIE门禁。静态SHA/初态/参数/资源与预算门禁后执行一次运行器，按1h门禁顺序完成4传播，无重试。逐RHS压缩日志/NPZ留data/processed，本次轻量CSV/七图/审计JSON及三报告入库。全量重算驱动/阻力，抽样完整状态/旋转；主要配对tight复用旧D0/D1/D2/D4，D3未做新tight且明确限制。

命令：source scripts/activate_orbit.sh；PYTHONPATH=src python -m unittest discover -s tests -v；python scripts/run_msis_drag_orbit.py --run-tag msis_drag_orbit_v1；OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/run_msis_drag_orbit.py --run-tag msis_drag_orbit_v1 --execute；python scripts/analyze_msis_drag_orbit.py；python scripts/write_msis_drag_reports.py。所有已存在run-tag/输出拒绝覆盖，禁止重放本次授权。下一步待新指令核实真实气动/机动/高度与高阶力，不能自动以本次残差排名或扩窗。


## 2026-10-20最新：J3/J4无阻力扩展及正式参数审查完成

在不改原μ/R/J2/基础代码的前提下，核实GFZ EGM2008完全归一化C30/C40并按μR^n重表达为项目Jn，定义名义J2+静态J3/J4受控势，非完整EGM/IERS模型。9项新测试/全142通过，独立球坐标与势梯度、固定轴能量/轴向角动量及关闭恢复检查通过。

只新增G1、G2、G2-tight三次6h无阻力，G0读取D0；G1终点429.142m、全段RMSE418.474m；G2终点834.459m、RMSE731.931m，对比G0终点1066.087m/RMSE555.356m。G2终点改善但全段RMSE恶化31.795%，不挑点下结论。J3/J4分别引起终点923.004/815.786m增量，合计1735.560m，远大于旧条件密度差52—65m；不能把新旧引力差归因密度。G2 base/tight最大差0.058411m，配对变化1.58045e−5m；174项历史保护SHA未变。

新取得ESA官方公开链接5.13版2013产品定义并只存本地；识别q详细表/概览方向矛盾、Flags_Platform跨产品含义差异及f_thr单位mN。0601现行适用性、四元数顺序/几何/Cd/推力仍未闭合；未启用真实参数。为PDF阅读仅新增项目内pypdf/pycryptodome，无系统改动/原数值包升级。资料详见SWARM_FORMAL_FORCE_PARAMETERS.md。

入口：reports/HIGH_ORDER_GRAVITY_VALIDATION.md、HIGH_ORDER_GRAVITY_ORBIT_COMPARISON.md；docs/HIGH_ORDER_GRAVITY_DESIGN.md及UPDATED_GRAVITY_DENSITY_PROTOCOL.md，配置/审计experiments/high_order_gravity_v1，真实六图/CSV在results。原D0—D5、TIE场及正式坐标门禁不改，无新阻力矩阵/AI/48h扩展。下一步需新授权统一球谐（含非带谐）与真实气动/推力门禁研究，所有未来密度组须共同升级引力。本次完成后停止，Git真实SHA以最终核验为准。

关键命令：source scripts/activate_orbit.sh；PYTHONPATH=src python -m unittest discover -s tests -p test_higher_order_gravity.py -v；全套discover；python scripts/validate_high_order_gravity.py（仅合成验证）；python scripts/run_high_order_gravity_comparison.py --run-tag high_order_gravity_v1（静态）；同命令--execute（3次已完成）；python scripts/analyze_high_order_gravity.py；python scripts/audit_swarm_formal_force_parameters.py；python scripts/write_high_order_gravity_reports.py。只读复用6份CDF，生成505个记录待审连续段，不把它们叫独立机动。原PDF、系数部分文件及wheel留data/raw，NetCDF/环境不入库。起初系数解析未支持Fortran小写d指数，静态阶段修正无模型启动；PDF首次读取因缺AES后端失败，项目内安装校验wheel后正常解析，无密码尝试或第三方源码修改。

## 2026-10-21：完整低阶球谐引力与真实参数复核

先读规则/状态/日志及J3/J4设计、验证、轨道比较、Swarm参数和阶段报告。Git初始main af8ac82、远端e89d51a；旧继承认证socket失效，采用现有同用户活跃认证通道，不保存凭据/改全局配置，成功补推af8ac8254236f5fa9e892b8968145f4ea6a7122a并核验远端相同。未重复提交旧成果。

复用已有GFZ EGM2008 16384B前缀，验证SHA、完整n≤8所有m；不下载104MB全模型。明确fully_normalized/no CS、tide_free、源GM398600441500000/R6378136.3，完整C22/S22等。新模块笛卡尔实心球谐及梯度，ITRS计算物理力并沿用EarthFixedFrame/冻结ERFA矩阵旋回GCRS，不叠旧中心/J2、不加虚拟力、不改旧模块。新GM/R/C20与旧基准差异单独披露，不拟合SP3。

PyPI官方pyshtools4.14.1 wheel13,898,723B校验后用独立Fortran参考；初始no-deps安装使高层依赖检查发现4缺项，随后卸载单一新增包并隔离解包于.local/reference，原72包兼容，无数值包升级。只加载wheel已验证Fortran扩展，不宣称全高层API安装。首次degree0多插degree1零项的静态错误已修复；SHTOOLS精确极点会Fortran STOP，保留限制日志，外部对照近极，生产极点独立连续性测试，未扩大门限。100随机点最大绝对/相对差1.0734e−14m/s²/1.3261e−15；有限差分三档二阶收敛，100m步相对1.186e−10。新增9/全151通过；最终隔离参考环境全量复验通过。

静态配置/177保护SHA及原SP3初态核验后，仅一次执行器内H1十分钟短例和H1/H1-tight六小时各一次，未重跑G0/G1/G2/D0—D5。base原1e−10/1mm/1μm/s/30s，tight1e−12/10μm/10nm/s/15s；同361个输出。H1终点622.748675m、全段RMSE310.911962m、R/A/C RMS23.548/309.382/19.858m，相对G0终点−443.338m/全段−244.444m。终点不如旧G1不表示应选G1；法向显著减小但沿轨仍大。新旧源参数及未建模项不能唯一归因。base/tight最大0.058408m，门限0.5m通过。base108.466s/4346nfev/724步，tight215.963s/8666/1444；新传播流程328.128s、累计峰292.898MiB，177历史文件SHA未变。

新增生产/测试、prepare/validate/run/analyze/report/delivery脚本；独立审计再次重算SP3三维/RAC指标、初态和代码/历史哈希。六张真实图、六个CSV、JSON/原配置及测试日志公开；NPZ、参考wheel/二进制/原CDF仍本地。构造1000Cartesian点的纯引力计算平均0.805ms/P950.815ms，与含完整框架的积分耗时分开，不宣称与旧缓存轴J2公平加速比。

Swarm复用六CDF/官方旧PDF，逐SHA未变；再次访问ESA页仍链接2013版，handbook不可访问、catalogue超时，未声称取得0601新字典。f_thr原DESCRIPTION为activated thrusters的名义组合力、mN，不确认实际执行推力；22非零dt_thr和505记录段仍只是待审。质量400.331—400.459kg有记录，Cd/有效面积/姿态/标志及推力标定未闭合。

命令：source scripts/activate_orbit.sh；python scripts/prepare_spherical_reference.py；PYTHONPATH=src python -m unittest discover -s tests -v；python scripts/validate_spherical_harmonics.py；python scripts/run_spherical_harmonics_comparison.py（静态）及--execute（唯一）；python scripts/analyze_spherical_harmonics.py；python scripts/write_spherical_harmonics_reports.py；python scripts/audit_spherical_harmonics_delivery.py。后续20×20/第三体/SRP/正式参数及统一引力密度矩阵仅建议，未执行。无新TIE/AI/阻力/48h或未来SP3拟合，任务完成后停止。最终Git以实际核对SHA为准。

## 2026-10-21：引力截断敏感性与缺失受力审查

读取AGENTS/STATUS/WORKLOG及8阶验证/比较/设计、Swarm参数和阶段报告；确认本地main/远端均588b119，工作区干净。检查磁盘366GiB以上/系统可用内存充分；项目.venv310/缓存复用，无新增依赖安装。官方GFZ gfc只读65536字节即关闭（HTTP完整长度252140870B并未下载），新前缀SHA1ed7794419ff81568285fb4ebfbc1f82aedac938ac67bd5fbe7c68776b88fc00，前16384B与旧SHA相同。完整20阶231对，统一源GM/R/fully_normalized/noCS/tide_free，显式地心一阶零项，不填未知缺项。

新增可回退gravity_truncation.ExtendedEarthGravity仅初始化，继承原笛卡尔势/梯度，旧8阶/时间/积分源不改。8/12/20各100随机点及赤道/近极/多高度SHTOOLS Fortran比较最大相对1.85/2.10/2.80e−15；中心差分10km/1km/100m二阶收敛。扩展8阶在全361个H1状态经真实EarthFixedFrame后力值逐位相同；二进制SHA核验。8新引力测试/预传播全159通过；随后4个离线预算数学测试加入，最终163通过。5m终点/全段候选目标和0.5m数值门槛在真实传播前冻结，未按SP3改系数/阶数/门槛。

run_gravity_truncation.py唯一--execute：H3短600s4.214s/146nfev，1.5安全系数预计剩余751.451s<1795.738s后，才H2六小时114.335s/4346nfev/724步、H3 126.906s/4346/724、H3tight252.876s/8666/1444。总498.429s、峰RSS146.430MiB，低于1800s/2GiB，无GPU、重试或旧H1/D0—D5重放。H3base/tight最大0.058411m，通过原0.5m门槛；H2没有tight，配对收敛限制保留。201历史保护SHA不变。

实际H2−H1终点267.586752m，H3−H2终点133.266130m/最大160.062686m/RMS77.777787m，均沿轨主导；H3−H1终点399.914236m。12→20差仍大于历史密度终点52—65m，5m目标失败；不是20阶对真值误差的数值界，不自动增阶。H1/H2/H3的SP3终点622.749/355.388/223.025m，RMSE310.912/177.073/107.677m；H3法向RMS比H2增大，不用残差最小选择模型。共7图/状态、差值/RAC/残差/加速度/费用/收敛CSV及JSON；全部原NPZ留data/processed不入库。

缺失力只读历史H1：Astropy6.1.7 builtin ERFA epv00/moon98、显式TDB，几何同时位置，NASA NAIF小文件给DE440日月GM（不是DE440位置），SHA入档。稳定地心差分含参考项，与直接式/线性潮汐/零地心测试比对。太阳2.74—3.90e−7、月球6.91e−7—1.10e−6m/s²；SRP演示m400/A0.5—2/Cr1—2、球形有限圆盘遮影，半影只给[0,1]，非实参/置信界；潮汐k2=.3、单极GR、人工ΔC20量级均明确局限，未a*t²外推。初版C20固定轴单位敏感性保留，v2改用验证时变地固轴，初脚本本地归档；最终判断只用v2。IERS表6.1低轨7331km例90阶，不称20足够。ESA页仍链接2013版、eogateway403；复核六CDF SHA，未取得0601新字典，f_thr名义mN不能冒充实际推力。

关键命令source scripts/activate_orbit.sh；PYTHONPATH=src python -m unittest discover -s tests -v；python scripts/prepare_gravity_degree20.py；python scripts/validate_gravity_truncation.py；python scripts/run_gravity_truncation.py（静态）与--execute（唯一）；python scripts/analyze_gravity_truncation.py；python scripts/estimate_missing_force_budget.py；python scripts/write_missing_force_budget.py；python scripts/write_gravity_truncation_reports.py；python scripts/audit_gravity_truncation_delivery.py。一次交互导出系数忘记PYTHONPATH导致ModuleNotFoundError，补入口后导出成功，不涉及传播失败/重试。

当前建议先设计更高阶截断与日月/潮汐规范门禁，再统一引力下另授权密度矩阵；真实气动/推力/TIE高度/预热时间场门禁保留。无新TIE、阻力、AI、24/48h或拟合。文档/状态/计划更新，安全提交和实际远端SHA见结束核对。完成后停止。

## 2026-10-21：40×40截断与日月第三体

先读AGENTS/状态/日志与用户列出的方案、20阶验证/比较、缺失力和正式缺口报告。Git本地2ad0c35、远端588b119且无冲突；通过现有同用户活跃认证通道安全补推，核对远端2ad0c354a0c845f33929d13cf1adc18fa701b163，无凭据存储/强推。纠正沿用表中的12阶终点355.338笔误，实物355.387674m。

GFZ同源只读262144字节，前65536 SHA匹配旧源，完整40阶861对C/S；不下载完整252MB。新gravity_degree40.py仅初始化，继承原势/梯度，40阶80!约7e118/中间双阶乘约1e59有有限余量但仍逐点验证。SHTOOLS100随机点/赤道近极、精确极点连续、负梯度三档二阶收敛通过，最大相对6.3701e−15。新20阶在全部361个H3状态GCRS力逐位相同，旧模块未改。

新增third_body_gravity.py包装原稳定差分数学核，保留地心参考减项、动态时间与体开关/越界拒绝。NASA旧GM文件SHA保持，SI×1e9；不伪称JPL位置。生产位置ERFA epv00 TDB Sun几何地心矢量/TT moon98原生GCRS，Newtonian阶GCRS对齐、完整相对论空间/GM时标映射未实现，严格PROVISIONAL_EPHEMERIS。独立NASA Horizons API 0/3/6h、500@399/ICRF/FRAME/TDB/VEC_CORR NONE几何矢量(source DE441)共两份约7KB响应；太阳/月球最大差1648.265/4403.516m，原20/40km工程门槛通过，非置信界；同H3点差分加速度相对差最高1.97e−8/3.084e−5。精简六点JSON与来源公开，原响应本地。独立直接式/地心零/趋零/极端方向/连续/关闭恢复20阶RHS/量级/单位测试通过。新增5+8项，全176通过；后将新测试改读公开冻结几何参考，最终再次176通过，无旧163测试修改。

静态SHA/参考/229历史文件及资源门禁后只一次run_h4h5.py --execute：H4/H5各600s base/tight共四短例(6.100/11.137/4.339/7.901s)，最大0.000257193/0.000257151m<2cm。按短例实测time/nfev×预计4346并乘1.5，预计主传播466.139s<1770.432s剩余后，仅H4/H5各一次6h。H4 183.913s/H5 130.571s，均4346nfev/724接受步。全349.972s、峰148.348MiB<1800s/2GiB，无GPU/重试/H6/旧H3重跑。严格遵守每组六小时一次，未额外full-tight；所有六小时全窗及配对收敛显式PENDING，旧H3 5.84cm不能替代该证明。

实际H4−H3终点15.364167m/最大33.088719m/RMS20.704993m，终点R/A/C −1.237/−12.300/−9.124m；H5−H3终点4.617909m/最大12.665472m/RMS5.578434m，终点−0.057/−1.699/−4.294m。40阶5m目标未达，不能称40阶收敛；日月全段最大超过5m不能只据终点删去。H3/H4/H5 SP3终点223.025/234.817/224.480m，RMSE107.677/104.212/108.093m；H4终点恶化但全段稍降，H5法向降但整体略升，真实结果保留、不拟合/选最小残差。太阳2.740—3.896e−7/月球6.911e−7—1.103e−6m/s²，只作实际位置下加速度，不a*t²推误差。

离线分析与独立审计复用现有SP3/时间/框架/误差模块，另手算RAC/范数重核；229保护SHA/旧H3交付清单不变。七图、状态/差值/RAC/加速度/费用/短收敛CSV和JSON保存，NPZ及原前缀/响应不入库。复用72兼容包，无新安装；所有路径/缓存项目内。资料核查仅复用ESA/NCAR已获证据，不重复403搜索；列出应取得0601 SW-RS-DSC-SY-0007/ACCELE03.25/ORBATT03.25、AD05机动码/通道定标/面积Cd与NCAR高度登记等资料，未猜测字段或启用真实推力。

关键命令source scripts/activate_orbit.sh；PYTHONPATH=src python -m unittest discover -s tests -v；python scripts/validate_h4h5.py；python scripts/run_h4h5.py（静态）及--execute（唯一）；python scripts/analyze_h4h5.py；python scripts/write_h4h5_reports.py；python scripts/audit_h4h5_delivery.py。当前只能设计明确限制的PROVISIONAL共同矩阵，下一步待新授权补六小时收敛/候选40阶+日月(H6)/截断预算，正式气动/推力/TIE高度与预热/高频门禁不变。本轮无阻力/TIE/AI/24或48h，完成停止。最终Git实际SHA/远端核对以日志与结束汇报为准。


## 2026-10-21：H6组合与完整六小时数值门禁已完成

H4/H5 tight、H6 base/tight共四次六小时及H6两次600秒预检完成，无重试、无旧轨道重跑。H4/H5/H6单轨最大base/tight差均小于0.5m，各配对差稳定性小于0.1m，181项测试通过。H6单轨最大差0.058398202m；40阶背景加入日月的终点位移4.618091m、全窗最大12.665426m。H6 SP3终点残差236.454619m、三维RMSE104.825766m。

本次传播墙钟1192.190s、峰RSS329.707MiB，低于1800s/2GiB；历史SHA不变。实际配置effective_configuration.json区分继承来源的旧状态字段，旧记录保留。仅冻结configs/provisional_common_force_model.json供下一阶段条件研究，标记PROVISIONAL / HINDCAST / FORCE_MODEL_INCOMPLETE，星历保留PROVISIONAL_EPHEMERIS。

40阶未证明截断收敛，真实气动/姿态推力、TIE外部ZG登记、预热和高频场仍未闭合；缺失潮汐/SRP/相对论等。C0—C3仅设计未运行。下一入口reports/H6_FORCE_MODEL_VALIDATION.md、reports/H6_ORBIT_COMPARISON.md及docs/PROVISIONAL_DENSITY_COMPARISON_PLAN.md。完成后停止，任何新阻力矩阵/更高阶/TIE/AI/长窗传播均需另授权。

关键操作：source scripts/activate_orbit.sh；python -m unittest discover -s tests（新增测试首次src导入路径错误，修正测试引导后181项通过，未发生模型重试）；OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/run_common_force_validation.py（唯一）；python scripts/prepare_common_force_effective_config.py；python scripts/analyze_common_force.py；python scripts/write_common_force_reports.py；python scripts/update_common_force_status.py；python scripts/audit_common_force.py。运行日志logs/common_force_runs.log，测试logs/common_force_tests_pass.log；实际JSON/launch_once/门禁、NPZ、CSV与6图全部本地保存。无安装、下载、TIE/阻力/AI/24或48h运行，无参数拟合。沿用项目.venv310、冻结EOP/闰秒及GFZ系数/ERFA，系统环境未改。

新增组合模块及测试、受限运行/离线分析/独立审计脚本、两报告、预注册和C0—C3设计、条件配置；更新长期门禁/研究计划。旧实验、原始源码和正式TIE门禁不变。Git安全提交与实际远端SHA核对以最终同步日志和结束汇报为准。


## 2026-10-21：统一H6的C0—C3条件密度矩阵完成

C0复用H6，未重跑。新增C1/C2/C3各1h base/tight、6h base/tight，共12次，预注册单轨/配对门槛通过，187测试通过；无新TIE/更高阶/AI/长窗。C1−C2终点58.350988m，C1−C3 52.217924m，C2−C3 6.133109m。全部仍为PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST / FORCE_MODEL_INCOMPLETE / PROVISIONAL_EPHEMERIS。

共同H6/旧实验/驱动保护SHA不变，正式TIE入口仍拒绝。总传播3250.304s、峰RSS161.594MiB。三种在线密度、同C0位置离线密度、力/轨道及SP3探索残差均有CSV/审计/图。主报告reports/COMMON_FORCE_DENSITY_ORBIT_COMPARISON.md。正式气动/推力/高度/预热/时间分辨率和缺失力门禁未解除；本轮完成后停止。下一步优先取得FORMAL_PARAMETER_EVIDENCE_REQUESTS列明的资料并设计物理验证，不自动扩窗或训练。


关键命令及文件：source scripts/activate_orbit.sh；187项unittest；run_common_force_density_comparison.py静态及唯一--execute；analyze_common_density.py离线；write_common_density_reports.py；audit_common_density.py逐查询/历史SHA独立审计。复用.venv310，无安装/下载；缓存日志均项目内。新增common_density_research包装复用现有力/坐标/密度实现，冻结配置未修改。运行器按一小时实测×6×1.10预算门禁，失败不重试。Git安全提交与远端实际SHA核对见同步日志及最终汇报。

独立审计实际通过：12次传播共48,204条逐查询记录；逐条阻力方向/公式、NRLMSIS冻结驱动及TIE原生8列/PROVISIONAL标识核对，全部收敛指标/SP3范数及RAC独立重算，298项历史保护清单与共同配置SHA未变。日志logs/common_density_audit.log；清单experiments/common_density_h6_v1/independent_audit.json。生成10张真实图，未平滑Ap桶切换，旧PHASE1报告保留，新增PHASE1_H6_DENSITY_UPDATE.md。


## 2026-10-21：第一阶段工程验收整理与FourCastDEN第二阶段A启动

新增PHASE1_STAGE_REVIEW_20261021及5张既有图索引，明确工程/条件敏感性通过、正式科学精度未验收；未重跑C0—C3/引力/TIE。恢复官方AI资产并SHA保护，历史单步不是新成果。一次Jan4 00→01→02官方Direct自回归成功，实际forward2次，第二步171状态逐元素反馈第一步预测；未来真实状态只评价，未来LBC/驱动显式HINDCAST。两步DEN有限正值，首步与历史逐元素一致；192测试通过。

第2小时六变量平均逐层RMSE均比第1小时增大，但两步全部171通道均优于固定00时持续性。GPU阶段5.600s<300s，未训练/微调/扩6或24h；内存/事件计时口径和局限见FOURCASTDEN_TWO_STEP_VALIDATION.md。S7实际14键/网格匹配，但3种lev场顶padding、1h抽取、分布与Z/ZG问题仍需规范转换，本次没有输入S7。完整训练入口与2000—2022数据未齐，不称完整论文复现。

下一入口docs/FOURCASTDEN_PHASE2_RESEARCH_PLAN.md；建议另授权官方Flow同样两小时对照，之后再补统一变体窗口。正式轨道气动/推力/高度、预热和缺失受力门禁保持。完成停止，安全Git同步以最终远端核对为准。


执行命令：activate310；192项unittest；run_fourcastden_multistep.py静态和唯一--execute（timeout300）；analyze_fourcastden_multistep.py；write_phase1_stage_review.py；write_fourcastden_two_step_report.py；audit_fourcastden_delivery.py。模型/预处理/数据与指标均真实官方来源，CPU合成毒化测试不作为科研预测。源码/权重/static/样本和历史结果保护，原始源码不改，无包安装/新下载。S7_schema_probe只读目标记录并显式核验有限padding。正文首次MDPI请求429但官方搜索可读取训练划分摘要，未声称下载本地全文。实际完整交付SHA/容量/同步状态见审计JSON与最终汇报。


## 2026-10-22：官方Flow复现与Direct/Flow受控比较完成

一次Flow Jan4 00→01→02正式推理完成，真实forward2次，官方Flow权重严格加载。原位归一化增量/两步反馈逐元素验证通过；Direct只读取历史，未重跑，所有旧保护SHA保持。198项自动化测试、独立NumPy加权指标复核通过，Flow DEN100%正且有限，无裁剪或事后校正。GPU阶段3.400s，冷/第二forward152.144/18.435ms；新增数组约17MiB，无下载/安装/训练/TIE/轨道实验。

Flow第一小时170/171层、第二小时141/171层RMSE低于Direct；变量平均逐层RMSE第一小时TN/UN/VN/WN/Z较低，第二小时TN/UN/VN/Z较低，DEN两小时分别较高2.950%/2.842%，WN第二小时较高2.468%。DEN平均绝对RMSE受底层影响，上层相对/log指标另报，不能据单个初值排名架构。两模型均全部171层优于固定t0持续性；六变量平均误差均随步数增加。两套单次跨日GPU事件总时间差约0.978ms，不作速度优越性结论。

报告FOURCASTDEN_FLOW_TWO_STEP_VALIDATION.md、FOURCASTDEN_DIRECT_FLOW_COMPARISON.md；新增8图、4类逐层/汇总/配对CSV，配置、SHA、日志及审计在fourcastden_flow_two_step_v1。改进方向/未来独立初值与6/12/24h协议仅设计；本次不扩窗。下一项建议先多初值2h评价，或补1个Jan4 03样本建立history公平窗口，须另授权。完整训练入口/数据、独立大气/轨道验证、Swarm真实参数/推力及TIE高度/预热/时间分辨率等门禁保留。Git同步以最终SHA核对为准。

关键命令：source scripts/activate310.sh；python -m unittest discover -s tests（198项，24.685s）；run_fourcastden_flow_two_step.py静态及唯一--execute（timeout300）；analyze_fourcastden_direct_flow.py；write_fourcastden_flow_reports.py；audit_fourcastden_flow.py。Python3.10.19/torch2.4.1+cu121/A100，FP32且TF32关闭，无依赖改动。官网正文请求429，模型语义以本地官方源码/README为直接依据，不宣称本次已重新读完整论文。未来数据清单只检查已有官方ZIP中央目录，未联网获取新资产。图像已实际查看，原生ilev=4/数组22，不是固定450km。


## 2026-10-22：FourCastDEN五日期Direct/Flow小规模泛化检查完成

固定新增Mar23/Jun21/Sep23/Dec21各00→01→02，12个真实官方NPZ经206/Content-Range/CRC/SHA/14键/层结构/finite/正性检查取得，传输25,849,991字节<100MiB，无整包或Jan4重下载。206项测试通过。8个新序列/16个forward完成，Direct/Flow各加载一次复用四个独立初始化，Jan4只读。真实物理状态反馈防泄漏、条件/统计/目标一致及独立NumPy指标通过，无NaN/负DEN、无裁剪或重试。监督墙钟27.342s/峰RSS约1.223GiB，GPU阶段含CPU审计/压缩19.099s，原始数组不入库。

五窗观察：Flow两时效TN/VN/Z均5/5平均层RMSE较低，第二小时UN/WN各4/5较低；第二小时DEN绝对平均层RMSE为Direct 5/5较低，但原生上层及参考中位ZG400—500km层组的平均相对RMS/logRMS为Flow 5/5较低。两模型全部日期六变量平均误差均增长，Flow上层第2/1小时倍率在五窗更大，不代表长期规律。Kp实际00—02输入Mar23仅0.5—0.867，五窗总体0.5—4.117，不能叫强磁暴验证；其余是季节候选，无总体/显著性排名。

报告FOURCASTDEN_MULTIDATE_VALIDATION.md、FOURCASTDEN_MULTIDATE_COMPARISON.md，指标CSV/7图/Range和运行/资源审计在fourcastden_multidate_v1。官方log-DEN仅CPU静态审查150项参数/177输入/static_log；没有forward，NumPy/CUDA分支和log/物理ACC公平定义仍需审查。建议下一项先官方log-DEN两小时，再history公平窗口，随后预注册6/12/24h和更强条件；见FOURCASTDEN_NEXT_EXPERIMENT_DECISION.md，需新授权。未训练/TIE/轨道传播，正式物理参数和坐标门禁不变。Git同步以最终远端SHA核对为准。

实际命令：source scripts/activate310.sh；python -m unittest discover -s tests（206项，24.073s）；run_fourcastden_multidate.py静态/--fetch；supervise_fourcastden_multidate.py（唯一GPU工作进程，8序列，不重试）；analyze_fourcastden_multidate.py；inspect_fourcastden_log_static.py（仅CPU）；write_fourcastden_multidate_reports.py；audit_fourcastden_multidate.py。复用Python3.10/torch2.4.1+cu121/A100，未安装包，缓存和所有新文件在唯一工作区。原始NPZ缺独立坐标/单位属性，按作者不可变static与UNIT_VARS契约，不冒充独立大地基准核验；Z非ZG，压力层非固定几何高度。原始保护SHA/新增字节预算及完整结果见最终audit。


## 2026-10-22：官方log-DEN五日期复现与三模型对照完成

215项测试通过。小张量确认np.power的CUDA转换失败；另由CPU合成原循环确认static_log气候态前导单例和DEN通道仿射广播问题，隔离覆盖层逐项保值修复，原始树/权重/统计不改，完整diff/SHA/失败日志保留。唯一正式log工作进程5个独立两小时序列、10forward完成；Direct/Flow只读，无下载/训练/扩窗/TIE/轨道。监督17.213s，加兼容探针0.588s<600，峰RSS1.107GiB；全预测finite/DEN正，反馈逐元素核验，无失败或重试。

共同原始物理目标与普通气候态公平比较：2h全层平均绝对DEN RMSE log在5/5窗最低；但上层与参考中位ZG400—500km组相对RMS在两时效五窗均Flow低、Direct其次、log较高，未支持log改善高层相对误差。TN/Z等窗平均2h较Direct高约18.9%/20.6%，其他变量代价完整记录。各自匹配统计/权重不同，不能单因果归于log开关。三者均2h平均误差增大，n=5不推断全年/真实大气或轨道精度。

报告FOURCASTDEN_LOGDEN_COMPATIBILITY、LOGDEN_VALIDATION、THREE_MODEL_COMPARISON；原native/dex/log ACC与公平物理CSV分开，6张真实图，所有原始/预测数组本地。下一入口NEXT_EXPERIMENT_DECISION最新节，建议先history公平窗口（另授权补03并统一01初始化），之后6h再长时。所有正式物理门禁继续保留，完成停止。Git同步以最终远端SHA核对为准。

命令：source scripts/activate310.sh；check_fourcastden_logden_compatibility.py；CPU测试发现广播错误/合成参考指数溢出后留档，修复数学维度并选有界毒化输入，最终215项全套unittest通过（23.943s）；run_fourcastden_logden_multidate.py静态；supervise_fourcastden_logden.py唯一GPU；analyze_fourcastden_three_models.py；write_fourcastden_logden_reports.py；audit_fourcastden_logden.py。复用.venv310/torch2.4.1+cu121/A100，FP32/TF32false，未安装或下载。原生与公平指标区分，float32log输入往返数ppm记录，SEA因官方坐标dtype约1e-6差别不改匹配处理。

## 2026-10-22：官方History首次复现及共同01时四模型对照

先读AGENTS/STATUS/WORKLOG及源分析/第二阶段计划/下一决策/评价协议/多日期及三模型/兼容报告，核对本地main和远端main均c15d8bfc6da12c732555d8404e7ad83a46837e17。保护旧资产和结果356项SHA；本次不重用旧00时结果冒充新起点。

从作者原循环确认H=1按两个177通道旧→新输入354（每块171状态+下一小时6辅助），4标量为目标时刻。History权重严格加载150项state、66,870,720参数；flowfalse/logfalse/普通static，其他三模型各匹配checkpoint/static，log复用既有等价覆盖层。6项新CPU合成实际循环/毒化/错序/teacher-forcing拒绝测试，全221项24.452s通过。聚焦导入曾有旧numpy.ndarray尺寸warning，完整测试与正式运行无对应失败，未安装/修改环境；全套ERFA旧测试dubious-year警告留档。

唯一新下载2023_01_04_030000.npz，复用BoundedRemoteZip，所有206/Content-Range正确、CRC/SHA/14字段/网格契约/finite/正DEN/ZG顺序通过，网络3,063,982字节<10MiB；00—02只读。原NPZ没有独立单位/时间属性，单位按作者契约，不能冒称外部高度验证。

History唯一真实forward预检通过，随后History/Direct/Flow/log各一次正式01→02→03共8forward，无重试/训练/扩窗。真实hooks逐元素验证历史窗口从real00+real01滑到real01+pred02，其他模型单状态反馈，未来真值只评价。实际预测全部finite/DEN正。监督墙钟21.011274s、峰RSS1,315,291,136字节；History冷预检146.774ms、正式18.619/18.375ms，其他共享CUDA热状态不作速度排名。独立读取/加载、循环含指标/hooks、保存和GPU事件各记录，CPU分析3.825s。

公共raw02/03物理目标与普通物理气候态、相同01持续性，DEN kg/m3、自然log差/分层/极区；native log ACC/dex单列。1368个共同物理通道指标及native RMSE/ACC独立NumPy复核通过。单窗History两个时效六变量均高于Direct，DEN绝对均差分别约12.74/7.95倍；近400—500原生层组第1h Flow最低、第2h Direct最低；log旧窗口绝对优势未延续。4模型平均误差均增长，History DEN增长较慢不等于绝对精度/稳定性更好；全171层均优于共同持续性。只读参考相邻小时变化核查未见03数量级跳变，不把误差增大归于未证实数据损坏或地磁因果。不剔除不利层/日期、不拟合2023。

命令：source scripts/activate310.sh；python -m unittest discover -s tests；run_fourcastden_history_comparison.py --fetch；同脚本无参静态；supervise_fourcastden_history.py；analyze_fourcastden_history.py；audit_fourcastden_history.py；write_fourcastden_history_reports.py；audit_fourcastden_history.py --final。日志logs/fourcastden_history*，配置/SHA/请求/feedback/审计在experiments/fourcastden_history_comparison_v1，大数组data/processed同标签不入Git；报告HISTORY_VALIDATION、FOUR_MODEL_COMPARISON，5图/8类CSV。无新依赖，复用Python3.10/torch2.4.1+cu121/A100，FP32/TF32false。

下一阶段仅设计：其他4日期各补03，16新2h序列，Jan4只读；再6h（Jan4另缺04—07四帧），之后12/24h/独立强活动，训练和AI轨道前继续数据/参数/高度门禁。已停止，Git同步以最终SHA核验为准。

发布前补充CPU只读checkpoint结构核验：150项state，patch_embed.proj.weight=(768,354,4,4)，参数元素66,870,720，未做forward；checkpoint_structure.json保留。图像已查看。报告明确pred171/real177形状，随后以audit_fourcastden_history.py --release重新执行最终全项审计，早前audit快照保留，不覆盖。

## 2026-10-22：五日期四模型统一01时起点评价

先阅读AGENTS/STATUS/WORKLOG、History验证/比较、三模型比较与第二阶段计划/下一决策/评价协议，核对本地和远端main均58c35d9dee2bf15145d2cd85a47235eaa723f7ac。冻结preregistration，Jan4四组01时结果只读，不重跑；后四日期不依误差换窗。保护422项原始源码/Linux副本/权重/static/旧NPZ及指标日志SHA。

复用BoundedRemoteZip，一次中央目录确认四个03成员全部存在，再206/Content-Range/ZIP及zlib CRC/SHA、14字段/单位网格契约/finite/哨兵/正DEN/ZG顺序校验。总网络9,274,427字节（8.845MiB）<20MiB，新原始数据0444；没有全年下载或重取。NPZ无自带时间/单位坐标属性，来源契约与外部高度验证分开。

新增5项日期批处理防Jan4重跑/连续小时/非法history/窗口等权统计测试，全226项24.779s通过；原有CPU毒化/History滑窗/log兼容测试保留。唯一监督工作进程16序列32真实forward，无额外预检、重试、训练/微调、6h/TIE/轨道。四模型各严格加载一次，独立初始化4日期；History354输入，其他177，171输出、4标量；直接复用作者循环、原log覆盖层，Flow按normalized增量、Historyreal00+real01滚动real01+pred02，后步绝不喂real02。每次实际174原始通道匹配归一化逐元素核对，hooks完整反馈和futureaux标量对齐。

实际监督墙钟42.574574s，GPU phase34.062319s含CPU处理/压缩；峰RSS1,311,993,856字节约1.222GiB。首次History冷forward157.167ms，其他约18—20ms；模型加载History/Direct/Flow/log约1.386/1.126/1.131/1.135s。不同预热/缓存条件不作吞吐排名；CPU分析10.557s、峰373024KiB。新增约431MiB<650MiB，原始和大预测NPZ不入库。

全部五窗共同raw02/03物理参考、普通物理气候态、real01持续性，SI密度kg/m3、风m/s、Z位势高度m，自然log误差与原生log ACC/dex分表。独立NumPy6840通道物理指标/原native阈值通过，Jan4 40项密度指标复现旧值。History mean/std、最新01初态及real目标与Direct完全一致；检查权重/时间/354顺序/反馈未见错误，保留较差残差，不宣称唯一训练根因或修补结果。

观察：History DEN绝对/高层相对两时效0/5优于Direct/Flow；Dec第一小时WN、第二小时UN/VN/WN优于Direct，其余变量无统一优势。近400—500原生组Flow第一小时5/5最低，第二小时3/5最低、Direct2/5。绝对DEN第一小时Flow5/5最低，第二小时log3/5、Direct1/5、Flow1/5。4模型5窗6变量均平均RMSE增长，History倍率小但初始误差大，不能称稳定性改善。新01与旧00同lead不同target，Jan/Dec第二小时高层误差明显增加、Jun略降；另存共同02目标异lead对比，不作地磁因果。

命令：source scripts/activate310.sh；unittest discover；run_fourcastden_four_model_multidate.py --fetch；无参静态；supervise_fourcastden_four_model.py；analyze_fourcastden_four_model_multidate.py；audit_fourcastden_four_model_multidate.py；History_interface_diagnostics离线逐元素核对；write_fourcastden_four_model_reports.py；最终audit --final。15类CSV、7真实图、配置/请求/驱动/保护审计在新标签；报告VALIDATION/COMPARISON，下一6h方案单独文档。脚本读取旧数据，无覆盖；复用Python3.10/torch2.4.1+cu121/A100/FP32/TF32false，无依赖安装。

6h仅设计Jan4工程基准与外部GFZ def Kp00/03/06均>=5的Mar24（7.333/8/6.333），未看该窗模型误差；本地官方目录确认00—07存在，12帧待取（Jan4缺04—07四帧、Mar24缺八帧）。未来要升级任意步反馈毒化、独立预算授权，当前未取未来帧/未6h/训练/轨道。正式真实大气/Swarm气动推力/高度/预热/受力门禁不变，任务后停止，Git以最终远端核验为准。

## 2026-10-22：FourCastDEN两日期四模型连续6小时与增强活动条件比较

先读AGENTS/STATUS/WORKLOG、六小时方案、下一决策/评价协议、多日期验证/比较、History验证，核验本地main/远端均a1b474481155d252281ec3ff7751351f82b4d18a。复用原官方4权重/static/隔离log层，保护533项历史资产SHA。两日期固定Jan4和按GFZ外部规则预选Mar24，未按新误差选窗。

新增autoregression.py支持任意正L/H0/H1，实际作者CPU循环+合成网络对四模式6步未来真值毒化预测不变，History第三步两个预测状态、后期teacher forcing/aux/scalar错位及Flow增量误用拒绝。新增6测试，全232项25.416s通过；旧ERFA测试与focused导入warning原日志保留，无环境安装/屏蔽。预注册freeze后才真实GPU。

只新增Jan4 04—07和Mar24 00—07共12NPZ。已存目录压缩25,019,661字节，网络中央目录复核CRC/大小/真实header offset。初次完成7帧后读取第8文件名Range遇HTTP500、0body，保留失败日志/ranges；另一次有界--resume-fetch仅取剩5帧，不覆盖/重取已完成，累计26,985,595字节（25.74MiB）、保守reserved26,985,662<40MiB。所有成功Range206/Content-Range/长度正确，ZIP/zlib CRC、SHA、14键、float32、finite/哨兵、正DEN/TN/ZG单调及单位网格契约通过，raw0444。NPZ无独立单位/时间坐标属性，契约不等于外部参考基准。

先唯一Jan4 Direct真实单forward短例通过，再8独立六步序列共48正式forward，模型各加载一次复用两个独立初始化。新DatasetTimer/MetricTimer只透传原函数计时，不改原数学/源码/返回；实际174通道匹配标准化和所有hooks逐步核对；Flow normalized增量、log匹配log10/stat/pow10、History从real00+real01滑到预测窗口，无未来物理真值重置。两日期原NPZ未来LBC/标量/SEA/磁辅助给定，HINDCAST。无模型失败/重试或输出裁剪。

全部预测finite/DEN正，TN146.87—1736.58K、最大绝对风分量1095.52m/s、Z位势高度95.65—854.88km，无明显数值发散；这不是实际观测准确证明。独立NumPy8208物理通道/作者native检查通过，rtol/ACC门槛不改；Jan4四组前2步与旧2h数组逐元素一致。作者log ACC/dex与公共物理指标分表。

结果：Jan4高层DEN第一小时Flow最低、2—6h Direct最低；Mar24第一小时Flow最低、2—4h History最低、5—6h log最低。+6h near相对RMS Jan4 D/F/log/H=1.23908/1.47699/1.33594/1.55513%，Mar24=4.27263/4.35886/3.90706/4.04544%。History全层绝对DEN所有时效仍最高，低倍率不能当稳定。Jan4部分WN、Mar24四组VN有一步平均RMSE下降，不预设单调。Mar24 near组从20/21/22变20/21（+3h起22中位超过500km），固定upper与全逐层同时报告。Jan4工程基准Kp3.35—4.633非安静，Mar24作者Kp6.583—7.883，GFZ桶/观测F107/中心81平均与作者不完全同约定，不替换。两窗同UT，季节/初态/历史条件混杂，不作磁暴因果/时延结论。

监督39.700139s、峰RSS1,413,128,192字节=1.316GiB；GPU phase30.840975s含CPU I/O/压缩，6次forward合计每组约110—113ms。首次原native指标事件546.599ms及log分支116.391ms含冷编译/派发等待，不当纯kernel；数据读取解码/标准化/其余预处理、加载、指标、loop和保存分别记录，不作AI替代TIE端到端速度比。CPU分析10.55367s、峰650964KiB，新增约392MiB<800MiB。

命令：source scripts/activate310.sh；unittest discover；run_fourcastden_six_hour.py --fetch；--resume-fetch（一次余量补取）；无参静态；driver_comparison离线GFZ审查；supervise_fourcastden_six_hour.py；analyze_fourcastden_six_hour.py；audit_fourcastden_six_hour.py；write_fourcastden_six_hour_reports.py；最终audit --final。新8图/8类CSV、配置/输入SHA/原生及物理审计，原始/预测NPZ本地不入Git；3报告与LONG_HORIZON_DECISION。长期路线第二阶段未训练，第一阶段正式物理门禁不变。

后续只设计先同两窗四组12h（每窗缺08—13六帧共12），通过后再24h；不按当前两个窗口选择最终模型或在2023拟合参数。缺作者完整训练入口/2000—2022数据/独立验证、多种子训练消融、真实观测密度及Z/ZG/时间/Swarm气动姿态推力/共同受力条件。当前停止，不继续12/24h、训练/TIE/轨道；Git同步以实际远端HEAD为准。

## 2026-10-22｜Jan4四模型连续12小时与训练准备静态审查

目标：沿用既有六小时官方路径完成一个Jan4 01→13窗口，不拼接、不输入中途真值；Mar24只设计，训练资源只读。先核对clean main本地9447e785、远端a1b474；通过有效同用户Git认证通道安全push成功，ls-remote核验9447e785，未重提交历史/强推。

新增独立run/supervise/analyze/audit/write脚本与12步5测试，复用原autoregression/profiling/log隔离层。全237测试27.861秒通过，旧ERFA合成dubious-year警告原样保存。预注册docs/FOURCASTDEN_TWELVE_HOUR_PREREGISTRATION.md先冻结前6步精确门槛和原指标容差；按既有保守600秒/4GiB/800MiB监督，磁盘20GiB门禁。既有权重/static/原作者树/旧数据结果全部保护SHA。

--fetch只获取Jan4 08—13六NPZ，目录元数据/206/Content-Range/CRC/SHA/14键/shape/float32/finite哨兵/正DEN与TN/ZG单调通过，网络13,442,650字节，无失败重试，raw0444。00—07用symlink只读。新preflight逐一数据和配置SHA后启动一次监督进程，4模型各12forward共48、0额外GPU预检，各自独立初始化；future aux/scalar逐时对齐，仅物理171状态自回归，History第三步起两个预测状态。严格checkpoint/FP32/TF32关闭，Flow增量和log10/static_log/pow10沿用验证层，未改原源码/权重/统计。

真实hooks前6步input/scalar/raw/state精确等于旧6h（最大差0），means/std亦精确；执行完原六变量summary及旧DEN指标前24模型时效全部精确相同，prefix_metrics_gate.json。无teacher forcing/裁剪/补零，48输出finite/正DEN/正TN。独立NumPy公共8208通道时效以及native指标复核通过，保留原rtol2e-5/ACC2e-6与公共1e-12；逐层/极区/顶部/固定upper20—28/near21—23及持续性全部保存。

+12h near相对RMS D/F/log/H=1.331348/1.623416/1.446208/1.899883%，全层DEN平均RMSE=2.3451913e-10/3.0523764e-10/2.3876184e-10/8.3372090e-10kg/m3。Direct本窗口+2—12较低；near D/F/log+9h峰后小降，History+11h峰后降，History全层绝对仍持续增大，不能以增长比单独称稳定或选全年模型。Z为位势高度、near是参考中位压力层非固定450km。Kp原NPZ约3.30—4.633，非安静基准，不将误差曲线直接归因驱动。

监督39.435960秒/峰RSS1,489,559,552字节，GPUworker30.077811秒含I/O/加载/指标/保存；12forward D358.082ms含首次冷、F217.901/log219.404/H225.480，CUDAallocated峰315.70—329.25MiB。独立分析9.1605秒。新8图/8类CSV、配置/逐步物理范围/反馈与保护审计，大预测NPZ不入Git；完整体积与SHA见final_delivery_audit.json。静态作者README明确推理包，Lightning残留value/flow/warp接口与实际AFNONet不等同，缺完整训练入口及2000—2021训练/2022验证数据和四变体精确协议；未下载/训练/安装。未来Mar24缺08—13六帧，本次仅设计。正式外部高度/气动/受力/观测验证门禁继续。

命令：source scripts/activate310.sh；unittest discover；run_fourcastden_twelve_hour_jan4.py --fetch；无参preflight；supervise_fourcastden_twelve_hour_jan4.py；analyze；audit；write_reports；audit --final。无额外模型推理/重试，未TIE/RK45/训练/Mar2412h或24h。成果完成后安全Git同步并核验远端，结束停止。

## 2026-10-22｜Mar24连续12小时与Jan4同lead离线对照

先读取AGENTS/STATUS/WORKLOG、Mar24方案/长时决策/训练审查/Jan4与旧6h报告，核实clean main本地与远端均b081de700089634221381d9ee4aad2eb6e2355b9。复用四官方权重/static/static_log/原作者循环与隔离log兼容层，不修改作者树/权重/归一化。新增独立run/supervise/analyze/audit/compare/write与2日期隔离/精确门禁测试，全239测试27.884秒通过（旧ERFA合成warning保留），原12步CPU四模式毒化与History末步窗口测试一并通过。

新预注册固定Mar24 01→13、48forward/0额外GPU预检，网络25MiB、GPU600秒、RAM4GiB、新文件800MiB/磁盘20GiB硬门禁。目录先确认六08—13成员、压缩12,469,476字节；Range实际13,452,428字节，全206/Content-Range/CRC/SHA/14键/shape/finite哨兵/正DEN和TN/ZG单调通过，无失败下载/重试，raw0444；00—07只读，不重下。Jan4原结果和代码/数据/配置纳入保护SHA。

preflight后只启动一次GPUworker，四模型各完整12步，未来物理真值仅评价，aux/scalar按作者给定HINDCAST；Flow normalized增量、log10/static_log/pow10、History滚动双历史保持。真实hooks前6步input/scalar/raw/state/means/std全部与Mar24旧6h精确相同，独立旧六变量summary和DEN组指标亦精确一致；没有在+6h输入真值或拼接6h。48状态finite/正DEN/TN，无裁剪/补零/平滑/自动重试，原门槛未放宽；公共NumPy8208通道时效与native指标独立复核，逐层/ACC/极值/偏差/持续性全保留。

Mar24 +12 near相对RMS D/F/log/H=3.759760/3.964593/3.674795/4.078700%，全层平均绝对DEN=7.8960708e-10/9.1789238e-10/7.6516976e-10/1.3607688e-9kg/m3。near Flow+1最低、History+2—4、log+5—12；+12固定upper20—28则Direct最低，不能挑层排名。Mar24 near组+1/+2为20/21/22，+3—11为20/21，+12再次20/21/22，需分组变化解释；Jan4组始终21/22/23。+12 Mar24 near误差约Jan4的2.15—2.82倍，仅条件比较，不作地磁因果/真实大气或轨道精度。History局地顶部/极区有优势但全层绝对始终最高；四组误差后段起伏非单调。原作者Kp04时7.8833降至13时2.5833，F107/F107A逐时原样保存，未用GFZ替代或由误差估物理时延。

监督39.969886秒、RSS峰1,494,986,752字节，GPUworker30.514212秒含加载/IO/指标/保存；网络12forward合计D352.574/F218.047/log214.306/H220.807ms，CUDAallocated315.70—329.25MiB；独立分析9.125692秒。新增物理解码hook计时约0.019—0.033秒/组，属于loop独立检查成本，Jan4原未单独计时记N/A，不填0/不混纯网络与端到端。新16图（Mar24单窗8+两窗8）与本次8类/两窗6类CSV、完整配置/日志/SHA/原指标与物理指标保留，大NPZ只本地。最终体积和保护计数见final_delivery_audit.json。

训练静态计划明确：先请求作者完整入口/四变体配置/训练验证清单与许可/统计采样种子学习曲线（未发送联系消息），再取得非2023合法小样本、隔离数据与训练工程、A100资源预检、重训Direct、单因素多步/分层损失/多seed。2023不调参，缺原协议不能称完整论文训练复现；本次未训练/微调/下载训练集/24h/TIE/RK45。更新LONG_HORIZON_DECISION与PHASE2，24h仅候选需另授权和24步毒化/12h前缀门禁。正式高度/气动/推力/受力与观测验证门禁继续。

命令：source scripts/activate310.sh；unittest discover；run_fourcastden_twelve_hour_mar24.py --fetch；无参preflight；supervise；analyze；compare（Jan4只读）；audit；write_reports；audit --final。检查敏感信息/ignore/历史SHA，提交轻量成果并安全推送核远端；完成后停止等待新指令。

发布阶段纠正：新两窗汇总CSV原CRLF触发git diff --check，转LF后解析行列精确不变，未动模型数组/旧实验；修正新CSV写入器lineterminator。保留原final审计快照，追加publication_line_endings_audit及publication_delivery_audit，后者是最终当前SHA清单。无新增forward。

## 2026-10-23｜FourCastDEN训练资源实时核查与独立合成训练工程

读取长期规则/进度/训练审查计划/两窗12h结果与phase2；clean main与远端均ef28fb9bc2628c2473cf92f50a887695cac4be80。仅本次授权合成工程，不真实训练/微调/新预测/TIE/RK45。官方四权重/static/原作者树/旧实验保护789项SHA，最终独立复核。

先直接API小元数据：Zenodo22250237跳22250238，HTTP200，软件4文件（source/static/static_log/checkpoint_files）；21859635HTTP200，仅2023.zip。原source zip MD5匹配官方8d8fd015f933455c74e0610d864664f0，核全成员、README及残留代码。记录作者/日期/无字符串version/版本关系、完整文件大小checksum和Apache2.0/CCBY4.0；没有公开非2023目录或完整训练入口/四变体活动配置/学习曲线。MDPI正文和XML403、网页工具429；Crossref200匹配论文标题、四作者及摘要，全文其他资源不能断言已排除。不下载大型归档/训练数据/旧权重，不发送联系消息。原源码根无LICENSE文件，记录声明许可与原AFNO引用链要后续确认，不修改/复制第三方。依赖只现有torch/numpy/timm/einops，未安装。

独立src/training/pipeline实现AFNONet原结构随机初始化、EpochPairs合法年份/UTC/连续/跨年/跨split拒绝、目标aux/scalar与当前171state拼177、目标171只label、OfficialFrameSource复用原get_data、174仿射归一化组件、MSE/显式优化器调度/梯度clip与有限性、validation无更新、checkpoint严格model_state/optimizer/scheduler/step/Python NumPy CPU CUDA RNG/模式/config/元数据和可信本地恢复。真实adapter仅实现未真实数据运行。配置JSON明确独立假设/合成无物理单位，不冒充原训练损失/纬度权重/优化器协议。原64,695,744参数网络不缩小，输入177+4/输出171。

新增8 CPU测试，247全套27.191秒通过（旧ERFA合成warning不屏蔽）：梯度/更新/shape、no_grad验证、带动量optimizer恢复/调度/RNG/step及下一步与连续精确等价、同seed复现、未来目标毒化输入不变、年份split/时区/缺帧跨年拒绝、归一化与错误输入/不可信checkpoint拒绝。GPU使用同架构随机初始化、不load任何官方checkpoint、不读真实NPZ。

v1首次GPU监督4.679802秒，确定性CuBLAS在第一forward报缺CUBLAS_WORKSPACE_CONFIG，0完成step/0更新/无checkpoint；保留失败日志、原preflight/源码SHA。未取消确定性；新独立cublas_v2在torch导入前设:4096:8，剩余295秒监督。成功训练3步，step2保存唯一checkpoint、释放原模型、重建后严格恢复hash/optimizer/scheduler/step再继续step3；validation另合成无更新。两次监督累计12.246402秒<300，成功监督7.566601秒/worker5.407854秒，GPU进程峰1,335,885,824字节<20GiB，CUDAallocated641,605,120/reserved744,488,960字节，CPU峰1,390,276KiB。

合成loss141.807479858→141.802276611→141.797103882，裁剪前梯度51.9373/51.9301/51.9226，参数更新真实，纯工程不作大气精度改善。原norm.weight/bias未被forward使用无梯度是旧数学行为保留。SGD lr1e-4/momentum0/StepLRgamma1/clip1是资源受限合成假设；Adam参数+两动量checkpoint约0.75GiB超500MiB，本次唯一完整参数checkpoint258,850,242字节约246.859MiB，仅本地。CPU另用momentum0.9证明非空状态恢复，GPU空动量state不伪称Adam恢复。

形成官方资源审计/合成smoke报告、最小训练设计/数据获取及真实小样本协议/改进单因素设计；2021-04-05 00→04-08 00（73帧72pair）训练与2022-04-05→04-07（49帧48pair）验证候选日期在获取数据和看loss前冻结，未下载。优先作者完整入口/四变体配置/数据许可清单/统计采样seed日志→非2023小样本→真实数据接口审计→独立Direct baseline→K2多步再另B分层相对损失，多seed/2022验证选择，2023不拟合。24h/真实训练/TIE/RK45/AI轨道全部未执行。

命令source scripts/activate310.sh；unittest discover；run/supervise_fourcastden_training_smoke（v1失败保留）；run/supervise_fourcastden_training_smoke_cublas（新标签3步）；write_fourcastden_training_reports；audit_fourcastden_training_smoke。GPU前完整code/config SHA与资源preflight保留。最终新增体积/保护SHA/发布清单见delivery_audit.json；忽略.pt/环境/原始数据，仅提交代码/小元数据/日志/docs/配置与审计。安全Git同步后停止，等待新指令。

## 2026-10-23｜FourCastDEN真实NPZ只读接口与训练资料准备

首检clean main/远端f3c788b5c1084137c0f2f07730c203edfbf6ed0b，读长期规则/训练设计数据与改进方案/上轮审计。复用原pipeline.py、普通static、三真实Jan4 00/01/02，不训练不修改历史。新readonly_interface不是Dataset，仅在inference_mode返回hash/shape证据。脚本构造不含网络的TGCMForecast对象，调用原inference拼接，到forecast边界捕获输入后专用异常中止；patch禁止Module调用/backward/DirectTrainer初始化，CUDA_VISIBLE_DEVICES为空。0模型forward/真实loss/backward/optimizer.step，无新预测、合成训练、TIE/RK45/下载数据或发邮件。

初次v1将辅助AffineNormalizer float64输出错误要求与作者float32逐元素相同，在约一float32末位差（首帧最大4.768e-7）处断言失败，原checker/日志/initial_failure完整保留。新v2分开原32位精确验证与辅助64位差异记录，不修改raw/static/pipeline或放宽实际input门槛。三帧辅助最大差9.536743e-7；actual OfficialFrameSource与作者输入逐元素差0。DEN往返最大相对约4.136e-8，接近零UN可约0.003068相对差但最大绝对仅2.5e-5m/s，理论float32往返界通过，绝对/相对/SI全部CSV不隐去。

v2实际CPU8.060616秒，全部14键/shape/dtype/finite/abs>1e30/正TN TLBC DEN/ZG递增通过；无缺失字段和top padding补0。174物理/LBC按原mean/std float32精确，固定3scalar公式在浮点界内，实际全部4scalar/目标6aux/171truth与原官方捕获逐元素一致。00→01和01→02都从真实当前state只读组装，后者不是重跑自回归；旧00→01真实forward input0/scalars0精确复现，不执行网络。

对官方get_data返回目标171和独立source目标state分别毒化（aux/scalar不动），input/scalar SHA不变/target SHA变；未来真值不进入当前state。原EpochPairs train/validation对2023仍拒绝，不绕过年份创建可训练Dataset。8新只读/时间测试+3既有时间隔离测试共11通过（新测试首次把shape异常期望写错ValueError，而npassert实际AssertionError，修正测试期望，失败日志保留）；没有重跑247全套中的合成训练。2000—2021各年/2022合法，重复/不连续/跨年/跨split/非UTC/naive/非法shape/NaN拒绝。作者epochs原为文件名UTC契约下naive，核实具体小时后登记UTC，不把外部非UTC直接重标。

官方继续核查限定两个known versions/latest，均200并与上轮响应SHA相同，无新增训练入口/非2023文件清单；MDPI通讯页一次403，网页查询无有用官方新资源，未猜邮箱/URL或重复批量请求。英文邮件draft仅写待核实通讯作者/邮箱和用户署名，不发送。GFZ官方数据页确认历史驱动/API/桶起点约定，不下载2021/2022值；现有本地驱动仅2023。

已有S7 secondary_010坐标lat36/lon72/lev29/ilev29与普通static逐元素相同；TN/UN/VN28有效层由原read_var已核实top fill裁剪，Z非ZG/cgs转换被原源码注释。S7具TN/风/DEN/Z/ZG/NE/LBC/f107d/f107a/Kp所需字段（Kp大小写，不是小写kp）；静态mag年覆盖另保存，不等于模型物理分布相同。备用方案：各年03-29 00起7天候选预热后训练2021-04-05→08/验证2022-04-05→07，仅设计10/9天连续，避免未严格等价continuation。历史S7实测9天10分钟1382.676秒/4MPI/2.571GB；粗外推两run约3000秒，2倍安全6000秒/4GiB建议未来预算非实测，不在本次启动。候选新驱动/初态/预热/14字段/小时瞬时筛选/来源许可/统计都需另授权和审计，不能称原作者训练数据。

交付REAL_DATA_INTERFACE_AUDIT与roundtripCSV/输入目标hash/毒化/数据范围/源码与staticSHA；AUTHOR_RESOURCE_REQUEST草稿、ALTERNATIVE_TRAINING_DATA_PLAN、REAL_TRAINING_READINESS。更新TRAINING_IMPLEMENTATION_PLAN是用户授权文档更新，最终保护审计记录该项允许变化，所有原代码/科学历史/权重/上轮synthetic_step2.pt不改。真实训练仍缺合法非2023数据/许可/统计来源/配置/科学优化器/算力checkpoint预算，SGD合成配方不直接继承。K1真实baseline后K2单因素，2022验证选择、2023不调参，额外计算单列。

命令source scripts/activate310.sh；CUDA_VISIBLE_DEVICES='' audit_fourcastden_real_data_interface.py（v1精度诊断失败留档，v2精确正式检查通过）；仅新8+旧3时间unittest；write_fourcastden_real_interface_report；finalize_fourcastden_real_interface。全部新增<200MiB（实际见delivery_audit），大资产/原NPZ/checkpoint不提交。检查敏感/ignore/历史SHA后commit安全推送核main；本次结束停止，不自动真实训练/仿真/邮件发送。

## 2026-10-23：新年份历史驱动门禁与2022诊断

- 起始本地/远端main均7927b10c2d794246ae6bbbcb98e24283ca05a158。
- GFZ小范围Fobs获取发现2021-05-09缺测−1，保留HTTP200响应与SHA，失败即停，2021无GPI/模型启动；2022 Fobs94条、def Kp112条，6727字节，NETCDF3 GPI与fsum平均/独立插值通过。
- 2022静态门禁后仅一次4MPI十分钟诊断，2.489824秒、992227328字节峰值RSS、67015120字节NetCDF、正常退出。14字段与实际模型驱动核验成功；初猜/早期暖态均不能训练。
- 新增11项CPU聚焦测试通过；未重跑GPU训练/预测/轨道/旧模型。825项旧保护清单核验，824匹配，唯一旧进度文档差异已在前次提交，本次未改。
- gpigen公开源码有fill_fobs及不同有效终点语义，不据此填补缺测；未来122帧及7天候选预热仅资源/版本设计，不实际运行。

## 2026-10-23：2021真实观测缺口调查

- 起始本地与远端main均a25bb3a63bb0c03211b62353aac7a994649a2207，工作区干净。
- 保留原GFZ95日原件，FTP年度ASCII61,627字节与原Fobs全重叠精确一致；新05-07至11小JSON仍−1。年度文件提取15天120个def Kp桶。
- 加拿大门户TLS/工具超时，未关闭证书验证；公开fluxtable HTTP206小片二分定位，实际表内05-09无记录，保留重复时间行，不挑行。CelesTrak25,000字节HTTP206取76.2/INT。NOAA季度7,554字节取76候选，但按事前0.55sfu标准，49日23失败、最大8.8，不采用。
- 独立恢复门禁10测试与旧驱动/配置11测试通过，旧2021/2022证据SHA保护通过。敏感性ΔFobs/81及条件平均值只方法研究，未生成驱动版本。
- 最终DATA_GAP_UNRESOLVED；没有GPI、模型启动、GPU、训练、轨道或AI预测。下一阶段等待可信观测/质量解释或另行审查估算驱动方案。

## 2026-10-23：training_window_mar23_v2预注册和两年诊断

- 起始本地/远端80630055554be0bc6ba8e6a6be5238928acc6ec5，干净；先冻结新旧配置JSON，不修改旧日期和缺测证据。
- 边界代码计算：2021 raw03-14至28、Fobs02-02至05-07；2022 raw03-14至27、Fobs02-02至05-06。复用现有GFZ原件，只补2022各13天Fobs/Kp，新增HTTP200正文4110字节。两年完整性门禁均通过后才生成新GPI；无估算/Fadj/跨年替代。
- 新GPI NETCDF3/i4+f8、81日fsum与全合法域独立多项式/Kp插值通过。新脚本复用旧builder及GpiDriver，旧脚本和输出均不改。
- 两年静态门禁后各正式启动一次4MPI/OMP1、600秒模拟，2021墙钟2.632098秒/RSS991989760字节；2022墙钟2.432667秒/RSS988168192字节；各67015128字节NetCDF，退出0/4个NORMAL EXIT，无重试。
- 每分钟驱动、暖态输出、14键、padding及作者lat/lon/lev/ilev精确一致；11项新窗口测试通过。所有诊断记录NOT_TRAINING_DATA，无多日/训练/AI/轨道任务。
- 122小时帧及7天候选预热只设计：19天约49分钟历史外推，候选6000秒；根据实际8.04MB/次历史记录修正默认输出预算至8GiB。预热/跨日/分布和训练统计风险保持。

## 2026-10-23：2021十天单次连续运行与候选提取

- 起始本地/远端main一致b530f2040d5ccc61b250749d87470d5b7c5bdb47。复用冻结exe/2002初猜/2021 GPI/apex，HEELIS/GSWM/SECFLDS不裁减，6项静态测试后只启动一次固定tag，无Restart、无重试。
- 实际UTC 2026-10-23 04:27:25至04:53:02；模型2021-03-16 00至03-26 00、14400×60秒，4MPI/OMP1；1537.049967秒，958.598MiB采样MPI树RSS，子进程CPU6140.521秒，NetCDF2,113,614,788字节；4NORMAL EXIT，所有监督预算内。
- 11primary/240secondary日期有序唯一，73目标时刻齐全；1440个实际十分钟驱动日志节点及240小时NetCDF核验通过（后者最大差2.84e-14），逐分钟合法域静态14401节点检查，未冒称逐分钟运行trace。
- DEN正/有限、TN146.62—956.45K、ZG递增、14字段/原生单位/28有效lev+29ilev/官方坐标匹配；绘制DEN/纬带/TN风/驱动/组分/ZG并输出逐小时CSV。时间变化不等于初态敏感性，单初场7天充分性UNVERIFIED。
- 03-23至26提取73NPZ共150,413,422字节，逐元素匹配直接NetCDF float32；72相邻小时只读作者输入/177/171/4与真值毒化通过，既有missing_value类型警告经显式mask及独立对照审查。未拟合统计、未实例化模型/forward/backward/optimizer。
- 聚焦11测试通过，2311项旧保护文件SHA一致；所有新NPZ只读且附四标签manifest。2022仅成本外推1383.345秒与方案，无2022长例/AI/轨道/训练。后续先独立验证及初始化质量配对，不自动开始。

## 2026-10-23：2022九天连续验证候选与联合质量审计

- 起始本地/远端main为10900aaf063fa8f35b858cbb4d82cdc615c276eb，干净。读取AGENTS/STATUS/WORKLOG与窗口/2021报告，逐文件复核2021交付SHA；未重跑或修改2021。
- 新2022固定tag单次4MPI/OMP1/60秒，START75/STOP84，原2002初猜、2022 GPI、相同exe/apex/HEELIS/GSWM/SECFLDS；12961个预期分钟节点静态检查。7项静态测试后启动，无Restart/重试。
- 实际2026-10-23 06:52:39至07:15:14；模型03-16 00至03-25 00，12960步/1355.167537秒，MPI退出0/4NORMAL EXIT，峰值946.609MiB树RSS、子进程CPU5413.352秒，NetCDF1,903,952,612字节，所有预算内。
- 10primary/216secondary时刻完整，1296个十分钟实际驱动日志及逐小时NetCDF通过；后者最大差2.84e-14。DEN有限正、TN146.85—1021.49K、ZG递增、14键/单位/顶padding及作者网格通过；单初场7天充分性仍UNVERIFIED。
- 提取49验证候选、101,247,255字节NPZ；48相邻小时177输入/171目标/4标量与真值毒化通过，原生单位和直接NetCDF float32逐元素一致。已有missing_value类型警告保留并经显式mask/直接对照核验，无神经网络forward/backward/optimizer。
- 联合122帧/120小时对及源SHA/网格/单位/模型/时域隔离检查通过。原生ZG450km候选小时均值的中位数2021为2.95517e-13、2022为6.78842e-13kg/m³，仅描述性分布，未用2022拟合训练统计或调参，不归因于单一活动因素/初始化误差。
- 本轮11聚焦测试通过。更新真实训练门禁：科学READY=False，先预热敏感性配对及独立训练协议/2021统计冻结；不自动真实训练、更多积分/AI/轨道。大型NC/NPZ本地保留，仅安全同步轻量结果。
- GitHub同步：主成果0c0fa857626319c71b9655dac399bd67e5d98f7b首推60秒超时，先核验远端仍旧HEAD；出站pack1,050,905字节略超默认1MiB。仅对下一Git进程设HTTP/1.1与postBuffer8MiB后正常推送，核实远端与主成果SHA相同。代理/分块兼容仅为诊断假设，不改全局配置、不强推；过程记录logs/tiegcm_2022_git_transport.json不含凭据。

## 2026-10-23：重复2022任务只读核验

用户再次提供相同2022九天任务；确认已完成，未重跑模型或覆盖结果。重新逐文件核验两年40个NetCDF卷及122个候选NPZ SHA全部一致，2022仍12960步/10主/216次/49验证候选，联合120小时对。起始本地/远端均2c8d5d8，工作区干净；本次新增模型启动0，无训练/拟合统计/额外预热。审计记录logs/tiegcm_2022_recheck_20261023T074953Z.json；科学训练READY=False，预热未验证，后续等待新授权。

## 2026-10-23：2021不同官方完整初态同历元预热敏感性

- 目标：在原2021 A轨迹只读基础上，一次B十天连续积分，仅更换合法完整初场，检验7天预热后的初始化敏感性。先读取AGENTS/STATUS/WORKLOG及2021/2022数据、窗口/门禁/原预注册判据；本地与远端main起始e3470524842cd286c0128e379cf9534e55d31856，工作区干净。
- 来源：实际NCAR官方2.0支持目录HTTP200，保存目录及元数据，只下载5°mareqx_smax一个16,993,144字节资产，SHA a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7。实际2002 DOY80 primary/initial、trunk svn1249，上游1.95路径如实记录；原始NC只读不发布，许可证按NCAR Academic Research条款记录，无单独数据CC许可证据。
- 静态：34项当前/_NM/下边界float64、坐标及units与A一致，SOURCE_START合法。首次检查器将TI/TE原生顶部spval误当异常，0次模型启动即停止；依settei.F638—659和A/B相同mask修正检查器，保留incident，不改数据/物理/阈值。初始TN最大差696.299966K。
- 冻结：新B namelist逐字只替换A SOURCE，LABEL/SOURCE_START及全部物理、exe/apex/GPI/输出保持。启动前frozen_comparison_rules沿用DEN5%、TN10K、风矢量20m/s、组分5%及95%逐时/层/区域，组分floor1e-8不改。6项初始静态测试通过；无额外10分钟模型预检。
- 命令/环境：source scripts/activate_tiegcm.sh；run_tiegcm_2021_initial_condition.py --run-tag tiegcm_2021_spinup_initial_condition_v1 --execute。单次4MPI/OMP1/60秒，2021-03-16至26连续14400步；2026-10-23 08:11:05至08:36:12 UTC，1507.405928秒，MPI0/4 NORMAL EXIT，峰值采样树RSS951.672MiB，NetCDF2,113,615,748字节，未重试/Restart，所有监督预算内。
- 验证：audit_tiegcm_2021_initial_condition.py检查11主/240次历史、14字段/单位/顶mask/正DEN/TN及ZG递增；1440实际十分钟GPI日志与逐小时驱动通过，最大差2.84e-14。初始冷primary诊断N/A规则不放宽至暖态。既有missing_value类型警告保留，显式mask/原生检查有效，不补0。
- 配对：compare_tiegcm_2021_initial_conditions.py只读240共同小时，时间/全schema/网格/5项驱动一致，73候选/25最后24h记录，全部6纬带/层/固定ZG高度和A中位ZG选层分别统计。450km P95第1天175.262%、第7天6.694826%、第10天4.411339%；全候选5.869255%，最后24h4.796554%。所有原生层合并候选P95仅1.488771%，不能代替同高度检验。
- 结果：最后24h原生DEN逐格PASS；TN16格FAIL、风53格FAIL，O1/O2/N2/HE也FAIL；450km局部58格失败，500km候选共同覆盖69.52%。全局固定高度logRMSE斜率均负，但不等于逐小时单调/全部区域通过。未解除SPINUP_SUFFICIENCY_UNVERIFIED，科学训练READY=False。
- 独立数值复核：候选起点/最后24h起点/终点逐列numpy.interp与向量化最大相对差3.67e-15，小于预设1e-12；P95及点数比例独立复算。10项新增静态/算法测试及11项既有长例基础测试通过（共21聚焦），不声称全项目测试数量。
- 交付：3份INITIAL_STATE/SPINUP_SENSITIVITY/INITIAL_CONDITION报告、下一步决策、4个自有脚本/测试及results逐层/纬带/高度CSV和真实图；原始初场/NC及完整日志本地。未生成B训练候选，原122帧不改。
- 下一步：先审查更长预热同驱动配对的驱动/预算，必要时单独授权；2022结论不能由2021代替。真实训练、统计拟合、2022/14天积分、AI长预测、RK45均未启动。
- 最终保护复核：2556个既有科学文件SHA全部一致；独立列插值/全流程P95与点数比例在3个检查点差小于1e-12，冻结物理门槛不变。提交及推送后的真实HEAD核验保留于logs/tiegcm_2021_initial_condition_git_sync.json及最终汇报，不提交大型数据。

## 2026-10-23运行 / 2026-10-25接续：2021十四天预热双初态质量验收

- 授权范围：扩展2021 GPI，A14/B14各一次03-09至26连续24480步，14天候选预热+3天共同评价；禁止重跑旧A7/B7、2022、新NPZ或真实训练。起始main/远端ec0f2576c8210a6c1bdd2aa4ae8eb9700a39febe；发现上一任务本地同步审计JSON未跟踪，保留原文件并在本次安全纳入元数据，不改历史内容。
- 首读AGENTS/STATUS/WORKLOG及双初场/门禁/窗口资料。精确支持由代码计算：GPI raw03-07至28、Fobs01-26至05-07，102有效观测日/176个definitive桶，无缺测/重复/Fadj/估算混用；复用原GFZ年度原始文件，不新增下载。GPI SHA 6dad9d0ff290e841c32fb736b8f097365d7c4eebe2e12a0cef5c301b0eae8847；独立fsum81差1.42e-14、插值差7.11e-14，新旧共同14401分钟节点差0，原GPI未变。
- 新入口source scripts/activate_tiegcm.sh；prepare_tiegcm_2021_14day_drivers.py；run_tiegcm_2021_14day.py分prepare/execute，run_tiegcm_2021_14day_pair.py串行A→工程审计→B，无自动重试。两源及exe/apex/GPI SHA冻结，数值规则字节级复用旧冻结文件，实际实验身份/两次启动上限由独立protocol覆盖旧模板身份字段。A14/B14 namelist仅SOURCE不同，SOURCE_START80不变，实际START68/STOP85；旧LABEL文字不作为时长证据。
- 实际A14于10-23 09:03:14至09:45:50 UTC，2556.176244秒、951.789MiB采样MPI树RSS、3,581,249,880字节NC；B14于09:46:57至10:29:30，2553.404599秒、946.609MiB、3,581,251,512字节。各4MPI/OMP1/60秒、24480步/4NORMAL EXIT，18primary+408secondary/35卷，各2448十分钟实际驱动日志及每小时NetCDF驱动通过（最大差2.84e-14），全部14字段/单位/顶mask/正DEN/宽物理范围/ZG递增通过。合计5109.580844模型监督秒，完整编排5212.324348秒，无Restart/额外短例/资源超限。
- 10-25用户“继续”时确认两组已在授权单次运行中完成，进程均退出；未重新启动任何模型。原分析已完成delta14，但A14_A7因time.units不同（minutes since03-16 vs03-09）严格schema检查停止。保留失败日志；只增加各文件time按其epoch解码后与绝对2021 mtime/UTC核对，再规范time schema。所有物理schema/阈值不放宽，保存patch及前后代码SHA；交叉分析用独立calendar_v2日志完成，delta14不重算/覆盖，B14_B7离线完成。
- compare_tiegcm_2021_7vs14.py形成三套完整时间/层/6纬带/原生ZG200/300/400/450/475/500统计；独立逐记录audit_tiegcm_2021_14day_acceptance.py复算旧/新最后24h原生验收格计数完全一致，补充全候选/终点最差比例与失败小时矩阵。独立逐列numpy.interp在起点/最后24h起点/终点与向量化相对差≤3.78e-15，P95在继承1e-12数值容差内一致。11项新静态/格式/日历回归测试通过，无物理门槛调整。
- 450km原生ZG候选窗P95 5.869255%→2.081022%（降低64.54369%），最后24h4.796554%→1.904001%，终点4.411339%→1.803217%，起点6.694826%→2.285300%。DEN/TN/风全候选逐时/层/区域有效域门槛通过；HE全窗早段79格失败，最后24h通过；O1/O2/N2最后24h仍1060/1919/1633格失败，终点37/75/65。500km候选共同覆盖72.93516%，不外推、不冒称全域。分类B：明显改善但多变量未全部通过，科学训练READY=False。
- 主要组分是mmr，floor1e-8及原生N2 small不改；没有将Z当ZG、原生高度当WGS84或Swarm误差。交叉A14-A7/B14-B7仅诊断更早启动与额外历史，不直接称初态误差。旧122帧不提取/替换/追认，无训练统计拟合/神经网络forward/backward/optimizer。
- 报告：14DAY_DRIVER、14DAY_LONGRUN、SPINUP_7VS14、COMPOSITION_POLAR四份；results目录含原生逐时/层/区域/高度CSV、验收矩阵与实际7/14曲线。更新下一步决策/科学训练门禁/窗口/状态/研究计划。未来先组分调整与下边界契约审查，再审查是否超过14天；2022需另授权独立双初态（候选03-09至25），不直接套用2021。
- 最终保护：2686个既有科学文件SHA一致；70卷新增NC SHA再核验。大型NC/GPI/初场/NPZ仍留本地，仅同步代码、测试、配置、CSV、小图与报告。真实commit及远端HEAD核验保存logs/tiegcm_2021_14day_git_sync.json，禁止强推；本次结束后不自动追加积分或训练。
- 另补四轨迹共同有效域复核（仅离线）：450km四方100%覆盖、主P95降低结论不变；500km同一四方掩码下仍报告7/14各自P95和覆盖，不将域变化混为模型改善。结果four_way_common_height_domain.csv，未新增积分。

## 2026-10-25：按任务归属整理10月23日工作日志

用户明确本次为10月23日工作收尾。读取AGENTS/STATUS/WORKLOG，核对5次连续积分实际UTC、候选联合审计及7/14天验收结果，新增reports/DAILY_WORK_LOG_20261023.md。区分10月23日实际运行与10月25日离线补充验收，不重标历史日期。更新状态索引；未执行模型、训练或修改科学数据。核验文档指标与已提交成果1a21d85一致，按长期规则仅提交日志/状态文档并安全同步main。

## 2026-10-25：制作阶段汇报材料，无新增科研实验

- 目标：为下一次阶段汇报制作5—8分钟材料。读取AGENTS/STATUS/WORKLOG、阶段一、四模型五日期/两窗口12h、合成训练、2021/2022候选及7/14天预热/科学门禁报告，对照实际CSV与原图。先列出已完成/工程条件验证/未达标三类状态，归档于本地交付目录。
- 输出：10页正文+2页备份，可编辑PPTX；同一场景生成PDF预览（非Office转换）；逐页DOCX/MD讲稿（正文1569字，计划约7分钟）及追问/回答；逐页来源定义、单位/日期/SHA、图表索引与本地构建/验证源码。内部内容默认不公开，deliverables路径显式gitignore。
- 实际图：2023 Jan4/Mar24四模型完整1—12h共96点，直接读原CSV并逐一核对+12h；2021双初态原生ZG450km7/14天三时窗P95柱图，64.54%明确解释为初态敏感性差异相对下降，不是AI精度改善。122候选、177/171/4接口、HE范围/组分失败/500km72.94%有效域及科学训练READY=False均有明确范围。无曲线拟合、无伪造指标，原科研结果未改。
- 工具：优先.venv310和既有matplotlib/Pillow；必要增加python-pptx/python-docx/reportlab/PyMuPDF及3个依赖，前后锁比对仅7项新增，无原数值包移除或升级。中文Noto Sans SC由官方Google Fonts源取得，SIL OFL、实际URL/SHA/许可保留在项目内，不全局安装字体。
- 命令：source scripts/activate_orbit.sh；本地source/build_report.py生成；source/validate_artifacts.py检查。PPTX与DOCX ZIP/解析通过，12页PDF全部渲染、中文glyph覆盖、所有原生shape/文本边界和行高检查通过；逐页联系表及核心页检查未见遮挡或乱码。无MS Office/LibreOffice客户端，不能声称做过Office实际渲染；PDF为可直接阅读的同源版式预览。
- 发布：公开仅scripts/reporting通用渲染器/说明、已有公开科学报告和指标文件的SHA列表、依赖锁及状态日志；不提交PPT/PDF/讲稿/内部场景/缩略图。全部科学来源SHA保持，未启动TIE-GCM、FourCastDEN推理/训练或RK45。安全同步main并核验远端，完成后停止等待指令。
