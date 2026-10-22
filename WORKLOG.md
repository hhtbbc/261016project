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
