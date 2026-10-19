# 轨道预测与验证设计（2026-10-19）
状态：设计与最小SP3读取已完成，SGP4/RK45/大气积分尚未实现。

## 公平比较与两套初始化
|方法|初始来源|传播|密度/阻力|
|---|---|---|---|
|A|t0前冻结的真实历史TLE|官方兼容SGP4实现|SGP4自带解析阻力/B*，不注入外部密度|
|B|SP3单个t0历元的P和V，经完整变换到GCRS|同一RK45|固定版本NRLMSIS经验密度|
|C|与B逐比特相同的t0状态|同一RK45|经过spin-up及单位/高度检验的TIE-GCM密度|

初始化实验I：B/C从同一个SP3采样历元初始化，使用实际V记录，不用t0之后SP3位置差分或平滑拟合初速；之后参考只读作检验，禁止用验证误差反复修初值、Cd、时间偏移或密度比例因子。若要校准，另设t0前训练/校准窗口并冻结，不能重复使用检验区间。
初始化实验II：A使用原历史TLE及其SGP4模型，报告TLE历元、龄期、来源、历史发布时刻是否已知。A在t0有初始误差，B/C在t0被SP3锚定，因此A与B/C总误差的差别混合了初始化优势，不能全部归因大气。额外建议以SGP4(t0)经TEME→GCRS的同一状态初始化B'/C'作同源状态控制组；此组不替代要求的两类实验，也不能把TLE平均根数直接放入二体Kepler公式当振荡初值。
SP3本身由跨时段观测进行reduced-dynamic定轨，单t0参考状态也可能含事后平滑信息；实验I定位为“给定精密初态的历史传播诊断”，而非实时自主系统。SP3并非绝对真值。

## 时间、框架与SI约定
- 内部状态：地心GCRS位置m、速度m/s，积分独立变量为从t0起的连续SI秒；时间尺度以TAI/TT等连续时间表示并明确映射UTC，不直接跨闰秒用朴素datetime减法。
- SP3：实际GPS标签、IGS20；t0拟为GPS2023-03-21 00:00:20，对应UTC00:00:02，48小时后结束。正式运行前用冻结闰秒表确认；当前reader没有做转换。IGS20对齐ITRF2020，但理想ITRS和具体实现误差需列入预算，不作厘米级无依据宣称。
- A：SGP4返回TEME、km/km/s，经带速度的TEME→ITRS或GCRS转换；按每个实际obstime传完整CartesianDifferential，检查SGP4错误码，禁止TEME直接与SP3相减。
- B/C：SP3的位置和速度同时ITRS→GCRS；不得只旋转速度向量而漏掉时变旋转导数（Omega×r）。比较时统一转IGS20对应ITRS近似或共同GCRS，并清楚标注实现级近似。
- frames采用Astropy/SOFA/ERFA经过验证的转换，冻结IERS EOP（UT1-UTC、xp/yp，必要dX/dY）和闰秒表到工作区。无EOP覆盖则停止或显式列降级实验，不能静默零极移/外推。TEME转换不是简单固定J2000旋转；地理纬度、椭球高、地心纬度与TIE-GCM几何高分别管理。
依据[Astropy卫星说明](https://docs.astropy.org/en/stable/coordinates/satellites.html)、[IGS框架](https://igs.org/wg/reference-frame/)、已下载真实SP3头。

## 状态方程与共同受力
状态y=[r,v]，dy/dt=[v,a]。第一原型a=中心引力+J2+阻力；后续如需高精度，统一增加高阶非球形引力、日月、SRP/地球辐射等，而不是只给C增加。J2在地球固定/地轴一致框架计算后旋回GCRS，不把GCRS的Z轴永久等同瞬时地球自转轴。
阻力a=-0.5*rho*(Cd*A/m)*|v_rel|*v_rel。相对速度两种一致实现二选一：
1. 在ITRS求相对速度v_ITRS-wind_ITRS后计算阻力向量，再旋回GCRS；v_ITRS已是状态变换后的旋转系速度，不能再次减Omega×r。
2. 在GCRS求v-(Omega×r+共同风场)，但精密版本需完整时变转动关系；不要混用两套处理。
B/C最初共享共转零风假设，仅比较rho。Cd、面积和质量必须有来源/时间/姿态定义。当前仅有ESA发射质量473kg这一背景信息，不等于2023质量；没有已核实的Cd与迎风面积，不能把2.2或矩形面积当实际物性。TLE B*也不是可直接使用的CdA/m。

## RK45设置与误差控制
采用scipy.integrate.solve_ivp(method='RK45')。[官方文档](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html)定义局部控制，低容差不自动消除物理模型偏差。
初始工程候选（需验证，今天未运行）：rtol=1e-10，atol_r=1e-3m、atol_v=1e-6m/s，max_step=30s；在公共SP3历元输出。B/C固定完全相同设置，但自适应接受步序因密度不同可自然不同。以更严容差/更小max_step作收敛对照，要求数值差显著小于所研究的B/C差异；否则先解决数值误差，不能挑容差使某一方法获胜。
记录nfev、接受步数、密度查询数、缓存命中、墙钟/CPU时间、RSS、退出状态。先短弧通过验证，再按1/3/6/12/24/48小时展开；候选48小时不等于一开始必须直接长弧运行。

## 模块结构（除SP3读取器外均为待实现设计）
|模块|职责/接口|最低验证|
|---|---|---|
|src/orbit/sgp4_baseline.py|冻结TLE→TEME状态/错误码/元数据|Vallado官方测试向量、单位、龄期|
|src/orbit/rk45_propagator.py|状态/力组合/统一采样、运行统计|二体周期/能量角动量、容差收敛|
|src/orbit/force_models.py|中心引力/J2/阻力纯函数，SI常数|量纲、J2极赤道极限/RAAN量级、零密度与相对动能耗散|
|src/orbit/frames.py|带速度与time scale的TEME/ITRS/GCRS变换|已知参考、往返位置/速度、地固点速度、EOP缺失失败|
|src/atmosphere/tiegcm_reader.py|按NetCDF维度/单位读DEN/ZG/时间，输出合法网格|维度错序、缺值、时间覆盖、同位高度|
|src/atmosphere/density_interface.py|density(time_utc,lat,lon,height)->kg/m³+来源/质量；MSIS/TIE两实现|周期、极区、正密度、无外推、确定性|
|src/evaluation/sp3_reader.py|真实SP3-c/d单星P/V，保留原时间尺度|今日5测试通过；不把此reader说成通用完整SP3库|
|src/evaluation/orbit_metrics.py|共同历元/框架的XYZ、速度、RAC及汇总|零差、已知RAC偏移、缺点掩码、单位|

建议另有configs/orbit_experiment.yaml、实验manifest和入口scripts/run_orbit_comparison.py；今天不创建未实现的空函数冒充可运行程序。

## 软件依赖审计与环境隔离
现有.venv310可用numpy/netCDF4/matplotlib，未安装scipy、astropy、sgp4、xarray、pymsis（logs/meeting_environment_audit.json），今天未添加任何依赖。
- A最小：numpy+sgp4，框架/时间用astropy（间接ERFA/IERS数据）；绘图用已有matplotlib。
- B/C积分：另需scipy；经验大气优先评估pymsis并显式固定MSIS2.0或NRLMSISE-00版本/输入约定，不靠默认版本。pymsis官方说明默认可能自动下载驱动，必须显式传入已归档驱动或审计缓存位置，不能写包目录/项目外。
- TIE字段读取：已有netCDF4即可最小实现；xarray为维度标注便利层，可待必要时安装，不要求dask/全套天气模型。
- 模型编译：独立Fortran/MPI/NetCDF-Fortran/ESMF栈，与Python数据读取依赖分开。
建议新建项目内.venv-orbit复用已下载Python3.10，保留FourCastDEN .venv310冻结；先看选定版本requires-python/NumPy约束、manylinux轮子和下载体积，再uv pip dry-run/安装。今天没有确定未经检查的全部最新版本，也没有升级原推理环境。

## 评价指标与实验冻结
共同10秒参考历元，先取真实有效覆盖交集，禁止用跨长缺口插值填验证参考。可向公共历元插值积分输出，SP3已在该历元无需再次平滑。记录每个掩码、剔除原因、产品版本、数据SHA256、TLE选择规则和预先定好的阈值。
位置差delta_r=r_pred-r_ref；报告XYZ偏差、3D RMSE=sqrt(mean(|delta_r|²))、中位数/P95/最大/末端范数；速度同样报告，注明参考V及转换。
RAC以共同GCRS参考状态构建：R=r/|r|，C=(r×v)/|r×v|，A=C×R；投影delta_r。不能用未加自转的ECEF速度随意构RAC后当惯性沿轨。报告各时效误差曲线与初始误差，解释B/C的0误差锚点。
同时记录B-C轨道差以及各自对SP3误差；前者隔离共同设置下更换密度的影响，后者仍包含重力截断、气动物性、坐标/参考与初值误差。不能保证换TIE-GCM就比MSIS或SGP4更好。

## 参考不确定性、泄漏与风险
SP3 reduced-dynamic产品可能吸收经验加速度与动力学先验，应取同期SP3xVAL/质量旗标及独立产品作后续交叉检验；官方总体厘米描述不等于本窗口精度。机动/姿态变更未确认前，不签发最终无机动验证窗。
不反复观察验证误差再调整起点、TLE、Cd、密度标度、spin-up或容差；如必须调整，另设新留出窗口并保留试验历史。凡使用未来实际太阳/地磁或最终EOP，标为历史给定驱动实验，另行讨论运营可用性。
主要风险：只有中心引力+J2不足以保证高精度；质量/面积/Cd/风假设与密度耦合；TIE-GCM在Swarm高度上可能超模型顶；极区插值；官方2.0的2015后IGRF问题；spin-up未收敛；时间和速度变换错误；TLE历史发布时间未知。遇边界不得悄悄以经验密度补C，须停止或清楚单列混合模型。

## 效率比较
A/B/C报告相同弧长、采样、硬件/线程和质量要求。分别计一次性环境/模型启动、TIE-GCM spin-up及场生成、离线IO/插值预处理、传播/密度查询、总成本和多卫星/多次预测时摊销情形；不以现成场查询耗时与SGP4全流程混比。AI阶段另计训练成本、推理与场生成、物理预测条件，只有满足明确误差要求才讨论速度提升。
