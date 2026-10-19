# Swarm-A：SGP4与SP3的48小时历史传播基准
任务日期：2026-10-20（按用户任务标签）；实际服务器UTC检查时间见logs/20261020_preflight.json，与2023年轨道历元分别记录。

## 结论及适用范围
固定一条历史TLE的SGP4已运行成功，先300秒577点流程验证，再60秒2881点完成48小时对照。全部SGP4错误码为0；单位、GPS/UTC、同历元匹配、地球定向、完整位置/速度变换及误差计算通过验证。不是RK45实验，也没有TIE-GCM或AI训练。
TLE历史发布时间/抓取时刻没有逐条证据，因此本报告明确是“历元早于起点的固定历史TLE传播对照”，不能宣称该TLE在当时已实际公开，更不是严格复现实时运营预测。API及源码核查未消除这一限制。
结果是对选定ESA reduced-dynamic SP3产品的差异，不是对绝对真值的误差。IGS20以与ITRF2020对齐的ITRS实现使用，未拟合Helmert变换；不主张厘米级绝对坐标精度。

## 数据、窗口与TLE
卫星Swarm-A、NORAD39452/COSPAR2013-067B；SP3单星标识L47。既有三份0203版ZIP及解压SP3已按前次SHA256复查，一份都没有重新下载或改写。

|SP3文件的UTC文件名时间部分（前缀SW_OPER_SP3ACOM_2__，后缀_0203.sp3）|内部GPS日期|历元数|
|---|---|---:|
|20230320T235942_20230321T235942|2023-03-21|8640|
|20230321T235942_20230322T235942|2023-03-22|8640|
|20230322T235942_20230323T235942|2023-03-23|8640|

原路径data/raw/orbits/swarm_a/extracted/。实际头#dV、GPS、IGS20、P/V10秒网格，总25920点连续。P原单位km乘1000，V原单位dm/s乘0.1，标准化后为m/m/s。
评价开始2023-03-21T00:00:02.000000000 UTC，结束2023-03-23T00:00:02.000000000 UTC，持续172800连续SI秒。对应GPS标签两端均00:00:20。参考取既有原始10秒网格的完全同历元样本，没有SP3空间/时间插值、平滑或未来位置差分拟合初速。
固定TLE：
```text
SWARM A
1 39452U 13067B   23079.85417049  .00009090  00000+0  26056-3 0  9998
2 39452  87.3552 125.6726 0003403  90.7088 269.4554 15.35742261524299
```
历元字段23079.85417049，即2023-03-20 20:30:00.330336 UTC；距起点3.500463796小时。WGS72重力常数、improved(i)模式。按t0前最新历元选择，与10月19日冻结的同一条一致；没有依据SP3误差再选最佳TLE，也没有滚动换用未来TLE。
8条TLE的行长度、编号、校验和与历元重新检查；完整高精度历元及publication_time=null见experiments/20261020_tle_metadata.json和results/metrics/20261020_tle_metadata.csv。
额外访问ETH关于页、只读API元信息及公开源码，序列化字段只给id/norad_str/satellite；模型timestamp不能当发布时间，源码另有epoch_to_timestamp。逐记录元信息GET返回404，未发现公开抓取时间。不能因归档按小时运行就虚构每条实际可用时间。保留原Space-Track401记录，没有伪造认证。

## 时间系统与地球定向
SP3 GPS日历标签先按连续日历计算GPS秒数，再交给Astropy Time(format='gps')得到物理历元并转UTC；没有写死GPS-UTC=18秒。每份SP3首时刻与独立ESA.HDR中的UTC Validity_Start逐一核对，通过<1微秒阈值；另检查GPS起始历元1980-01-06 UTC锚点。实验期间由ERFA/IERS得到TAI-UTC=37秒，GPS/UTC18秒差是验证结果。
IERS 20 C04（IERS-B）与闰秒表从已固定的astropy-iers-data包复制到data/raw/earth_orientation/，不使用在线自动更新。完整文件信息和SHA256在logs/20261020_frozen_time_data.json。
- EOP文件SHA256：6fc2c9d9a7cd7e9a1f597866545bb75baab292f5d51ca9358d5c64c0ce2fa64f
- 闰秒文件SHA256：6cb6f5d4b819f2e568e25db4b0b26d89dedf031fdffb18bc94d40f4e94e268d7
- 包版本astropy-iers-data 0.2026.10.19.0.52.1；IERS-B覆盖MJD37665—61294，试验内UT1及极移状态全部为FROM_IERS_B，无外推/预报替代。
- 闰秒表有效期2027-06-28。加载时保留固定pyerfa的1972年前漂移定义，再以本地IERS表更新；有效ERFA表摘要保存在summary.json。

试验内UT1-UTC为-0.0238876至-0.0220007秒（min/max）；xp/yp范围及逐日EOP、形式误差见summary.json与eop_rows.ecsv。选取相邻支撑日的最大形式误差：xp6.3e-5角秒、yp6.0e-5角秒、UT1-UTC1.67e-5秒。这些是产品形式误差，不是独立证明绝对精度。
一次预检查发现清空ERFA再仅载入1972年起的表会使1980锚点偏7.105968秒；已在任何传播前修正并通过完整测试。初始失败及修复日志保留于20261020_orbit_tests.log、20261020_leap_loading_fix.json、20261020_orbit_tests_fixed.log。另修正Astropy6.1 IERS_B.open需字符串路径的兼容问题，未修改冻结原数据。

## 坐标与RAC定义
SGP4以UTC两部分JD逐历元计算TEME位置/速度（km/km/s），统一换SI后用Astropy完整CartesianRepresentation/CartesianDifferential变换至相同时刻ITRS。TEME→ITRS采用Vallado一致GMST82及IERS UT1/极移，不直接比较TEME与地固SP3，也不遗漏速度的时变旋转项。
主比较delta_r=r_SGP4_ITRS-r_SP3_ITRS。e=norm(delta_r)。均值为采样位置差范数的算术平均，3D RMSE=sqrt(mean(e²))，不是XYZ三个RMSE的简单算术平均。最大值只指60秒采样网格，连续时间峰值可能不同。
RAC使用同历元SP3状态先完整变换到GCRS：R=r/|r|，C=(r×v)/|r×v|，A=C×R。以共同GCRS的预测减参考差向量投影；R正向外、A沿参考运动、C右手轨道法向。未用漏掉地球自转的ECEF速度构建惯性沿轨基。GCRS使用Astropy6.1默认变换；不宣称包含全部测地实现修正，IERS dX/dY形式误差只记录而非声称额外加校。

## 48小时结果
|统计量|300秒先导（m）|60秒正式（m）|
|---|---:|---:|
|起始位置差|518.729191|518.729191|
|平均位置差范数|626.216131|625.565892|
|三维RMSE|764.708337|763.845573|
|采样最大位置差|2244.390863|2247.936538|
|终点位置差|1724.639883|1724.639883|

最大位置差时刻2023-03-22T23:42:02.000000000 UTC。R/A/C分量RMSE分别为143.054774、734.142586、155.016305m，主导分量为沿轨；不是将全部差异归因于大气阻力。
初始R/A/C约[0.631504,-507.746677,-106.173849]m；终点约[-399.729286,-1677.623755,13.332625]m。起始已有约519m差异，未将其清零或扣去后称为纯传播误差。末端误差减起始范数也不等于完整动力学误差分解。
误差有非单调/周期结构，三维图中两轨在地球尺度上接近重合是正常现象；差异以误差图和CSV读数评估，无平滑、删峰或人为放大轨道差。

## 验证与异常检查
- 既有SP3 reader5测试，加新增轨道8测试，共13项通过；覆盖GPS锚点/HDR、精确采样及越界拒绝、SI量级、TLE规则/校验和、Vallado标准向量、IERS覆盖、地固点自转速度、状态往返、RAC符号/退化/统计。
- TEME—ITRS往返最大位置差2.982e-09m、速度差5.935e-09m/s；参考ITRS—GCRS往返位置差4.662e-09m、速度差9.236e-09m/s。均满足1mm/1e-4m/s测试阈值。此为数值闭合，绝非纳米级物理精度声明。
- 独立GMST82多项式+极移矩阵位置核对最大差1.315663e-04m（约0.132mm），低于1cm阈值；RAC模长与ITRS三维范数闭合差2.105e-09m。
- 参考/预测时间最大错配9.592e-12秒，SGP4非零错误码0，无非有限状态、越界、缺采样或量级异常。
- 先导/正式公共历元差完全一致；独立CSV回读重算范数、RMSE、采样步长通过。新run-tag重复执行两种采样的状态数组和CSV逐字节一致，见logs/20261020_reproducibility_check.json。
- 正式运行警告仅Matplotlib/Pyparsing弃用提示，不涉及IERS/时间/轨道。测试中2100年是故意构造越界拒绝用例，其ERFA警告不属于2023实验。

## SP3参考质量限制
HDR Quality_Indicator=000按原文记录，不在缺少定义时擅自解释为零误差。精度指数为0，未取得可量化协方差/本窗口SP3xVAL；短P记录没有可用机动旗标，不能证明无机动。部分文件为2026年发布的2023年重处理轨道，允许作事后参考但不是实时信息。
当前结果仅说明相对于此版参考的差异；不能判断峰值全部源自SGP4而非定轨/机动等，也不能将单窗口统计推广到所有Swarm日期。未发现计算流程异常，不等于所有物理和参考质量问题已排除。

## 可重复执行与文件
```bash
cd /workspace/data/20261016
source scripts/activate_orbit.sh
python -m unittest discover -s tests -p test_sp3_reader.py -v
python -m unittest discover -s tests -p test_orbit_baseline.py -v
# 指定全新的run-tag，保留已有结果；60秒运行会检查同tag先导是否通过。
python scripts/run_sgp4_comparison.py --cadence 300 --run-tag my_sgp4_check
python scripts/run_sgp4_comparison.py --cadence 60 --run-tag my_sgp4_check
```
已验证的本次重复执行tag为20261020_sgp4_repro。既有输出目录和图/CSV禁止覆盖；标准化SP3若已存在只比对内容，不覆盖。运行前须source以确保Astropy配置/缓存在项目内，所有路径真实目标经过检查。
依赖复用.venv310：numpy1.25.0、scipy1.15.3、sgp42.25、astropy6.1.7、pyerfa2.0.1.5、matplotlib3.10.0及固定IERS数据包。只新增5包，无原包升级/降级；minimal要求configs/requirements-orbit-20261020.txt，全环境锁configs/requirements-orbit-20261020.lock.txt。首次元数据/dry-run、安装、一致性检查均有日志。
源模块：orbit/sgp4_baseline.py、orbit/frames.py、evaluation/orbit_data.py、evaluation/orbit_metrics.py；既有sp3_reader.py不破坏。配置configs/sgp4_swarm_a_20261020.json。
标准化参考：data/processed/swarm_a_sp3_standard_20261020.npz（UTC双JD、SI P/V、原框架及来源元数据），旁侧.json保留质量信息。
正式状态/汇总：experiments/20261020_sgp4_60s/states.npz、summary.json、tle_metadata.json、eop_rows.ecsv。逐时刻CSV：results/metrics/20261020_sgp4_60s_errors.csv；先导CSV同目录300s版本。
三图：results/figures/20261020_sgp4_orbit_3d.png、20261020_sgp4_position_error.png、20261020_sgp4_rac_errors.png，均已目视检查坐标轴/单位/图例/标题。

## 下一步（今天不执行）
先利用已验证的时标/框架和同一SP3单点P/V设计RK45二体测试，检查周期、能量、角动量和容差收敛，再增加共同J2。中心引力测试本身无需卫星质量/面积/Cd；在加入阻力与比较两种密度前，必须补有来源的实际质量/姿态迎风面积/Cd，并记录不确定性。不能用未来SP3反复调初值/气动参数。今天不创建RK45或安装/运行TIE-GCM。

## 官方方法参考
- Astropy卫星/TEME完整状态：https://docs.astropy.org/en/stable/coordinates/satellites.html
- Astropy IERS策略：https://docs.astropy.org/en/stable/utils/iers.html
- python-sgp4接口与校验资料：https://pypi.org/project/sgp4/ （另核对已安装源码tests.py和tcppver.out）
- SP3格式与来源、IGS20实现说明见docs/ORBIT_DATA_SOURCES.md及本地SP3-d规范。
