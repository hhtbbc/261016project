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
