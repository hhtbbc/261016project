# DART/TIE-GCM同化接口与复现性审查 v1

2026-11-16。本轮只做官方资料、源码和本地静态/CPU检查；未安装/编译DART、未改TIE源码、未运行集合或EnKF。结论：**有直接外部接口与论文依据，本地不能直接开箱同化，正式循环仍BLOCKED。**

## 1. 实际查到的资料与版本

- [官方TIEGCM接口文档](https://docs.dart.ucar.edu/en/latest/models/tiegcm/readme.html)：本次网页工具读取为DART11.25.4；服务器urllib对该页403，不把本地未存页面说成下载成功。
- 官方NCAR/DART源码固定commit `df5b08d03aa44c3a6b2b561a903b00b7193611ca`。保存`models/tiegcm/model_mod.f90`、`work/input.nml`、`quickbuild.sh`及`observations/forward_operators/obs_def_upper_atm_mod.f90`；来源/字节/SHA见download_receipts与DART_pinned_revision。GitHub连接器先成功读源码，原始固定revision另行归档用于SHA，不是完整clone/安装。
- [2024论文](https://doi.org/10.1029/2023SW003811)，作者Kosary等；2024-03-31正式发表，版本记录见[作者机构OA PDF](https://vbn.aau.dk/ws/portalfiles/portal/709792548/Space_Weather_-_2024_-_Kosary_-_Assimilating_Space_Based_Thermospheric_Neutral_Density_TND_Data_Into_the_TIE_GCM_Coupled.pdf)。正文通过网页PDF解析核验；服务器两个PDF路径403，原件未下载，不能声称本地拥有PDF SHA。
- [Zenodo10731921](https://zenodo.org/records/10731921)为v1；其[新版本10732144](https://zenodo.org/records/10732144)是v2，增加Code.rar。三个mat结果约2.55GB，未下载。237372字节Code.rar下载成功，官方MD5匹配，RAR5头CRC/成员清单读取通过；无本地解压器，**未解压/未读取或执行程序内容**。成员名显示5个MATLAB/csh集合脚本和1个GPI NetCDF，不代表完整DART namelist/观测转换器已公开。清单、限制与SHA保留。
- 目录描述E3写“3015”，与正式论文2015矛盾，按论文识别真实实验日期，原始描述不修改。

## 2. 接口不是一个可以直接运行的同化按钮

DART与TIE-GCM是独立可执行程序。`model_mod`读取restart/secondary模板、网格和时间，构造状态域并提供`model_interpolate`、位置、时间和垂直坐标接口；实际advance由外部脚本/模型程序完成。filter与模型各自MPI任务数、编译模板和调度必须明确。

`input.nml/model_nml`按每变量6项配置NAME/QTY/MIN/MAX/FILE/UPDATE。FILE区分restart与secondary，`UPDATE`允许写回，`NO_COPY_BACK`阻止该变量写回**文件**，不等于禁止其在DART内部被分析更新。变量列表、文件起源、上下限和当前/前时层策略都需要自行冻结。

本次所取work示例：9个表项全在本地文件中找到，NE/OP/TI/TE/OP_NM/O2/TN为UPDATE，O1及secondary ZG为NO_COPY_BACK；文档展示的例子又与此不同。**默认示例不是论文更新TN/O/O2/U/V/Ne的设置，不能照抄就称论文复现。**详见`DART_example_variable_compatibility.csv`。

默认示例ens_size20、assimilation_period_seconds3600；官方要求周期为模型步长的整数倍且可用整分钟表示。默认窗口以模型时间为中心，前后观测都可能参与；未来预测必须按最新被使用观测的时间登记截止，不把中心之后15分钟的信息称为中心时刻已知。

## 3. 密度观测算子：本轮新增兼容性发现

固定源码`obs_def_upper_atm_mod.f90:213—265`先尝试QTY_DENSITY；若没有直接密度，使用O/O2的质量混合比、压力与TN：

`rho = p / [wO/16 + wO2/32 + (1-wO-wO2)/28] / T / 8314`，输出kg/m³。

这是明确的O/O2/N2三组分EOS，并不显式包含本地CALC_HELIUM=1的He。`model_mod`从p0[mb]×exp(-lev)×100得到Pa，ZG cm→m；nlev从29个存储层减为28个有效中点层。不能将原生DEN(ilev,g/cm³)按同索引与中点EOS直接相比，也不能简单把DEN加进变量表就忽略×1000。

本轮在**2021/2022 B14 Mar23 00暖primary**真实O/O2/HE上，只计算同压同温四组分EOS密度/三组分EOS密度比值：native lev索引24的绝对相对变化P95为13.1445%/14.0320%。这是He遗漏假设的**条件敏感性**，不是实际DART预测误差、不是沿Swarm的误差，也不包含Ar/其他组分影响。末存储层28不在DART有效lev插值域，不能用其较大差异解释实际接口误差。

独立CPU解析测试核对纯N2 SI密度、无He比值=1、有He同P/T降低密度、非法分数/温度拒绝。新模块`src/atmosphere/dart_density_audit.py`只用于审计，不提供正式density provider。没有运行或修补DART算子。

## 4. 本地静态兼容矩阵

|项|事实|资格/缺口|
|---|---|---|
|版本/分辨率|本地2.0基线+既有GNU/apex覆盖层，5°/36×72/29ilev|结构匹配官方2.0/5°支持；本轮未编译联调|
|文件|NETCDF3_CLASSIC primary含34核心状态，secondary有ZG/TN/O1/O2等|示例9变量都存在；存在不等于安全写回/一致恢复|
|工具链|实际版本查询GNU Fortran12.4、OpenMPI5.0.8、NetCDF-C4.9.2/Fortran4.6.1；已有ESMF8.6.1|TIE单模型已跑通；DART mkmf、模块/精度/MPI ABI未测试|
|高度/网格|本地DEN/ZG在ilev，TN/组分在lev；DART压力/ZG单位换算可查|GRS80/WGS84到ZG零面仍未知，不因代码除100解除|
|组分/算子|本地He可达显著水平，示例三组分EOS不含He|需定义全组分算子或与原生DEN同点独立核验|
|状态/历史|34字段结构齐全，部分_NM在示例NO_COPY_BACK|分析增量与滤后历史/边界一致性、隐藏电动力状态未放行|
|原生Restart|连续/恢复超严格阈值已实测|DART反复循环会遇到同一问题，BLOCKED|
|集合|目前是smin/smax敏感性配对，不是已校准概率集合|不能复制同一场或随意抖动_NM声称合法协方差|
|观测|已有UTC/0301解析，A/C实物质量可用|obs_seq转换、观测方差/相关性/稀疏化未配置；nominal不等于零误差|
|安装状态|仅源码快照，未完整安装DART|可做静态准备，不能宣称filter可运行|

## 5. 论文复现要点（外部案例，不是本项目预期成绩）

正式论文§2—3的技术事实如下；它们与当前真实GPI方案并非相同物理协议：

|项目|论文设置/限制|
|---|---|
|模型|TIE-GCM2.0，5°，29压力面/每标高2层|
|同化数据|CHAMP ACC：2008-03-04—08、2004-08-13—16；Swarm C POD：2015-02-04—08|
|非同化评价|GRACE、Swarm B密度；COSMIC电子密度|
|集合/预热|90成员、15天；扰动F10.7/HP/CP，以分情景常数均值和高斯spread运行|
|更新状态|TN/O/O2/U/V/Ne，并讨论分析后几何高度变化|
|窗口|1800秒、中心前后各15min；forecast主要是下一同化循环先验，不是本项目1/3/6h长窗自由预报验证|
|局地化|Gaspari–Cohn，测试0.2/1/3rad水平半宽，无垂直局地化；不能把其最优值直接搬到2022|
|观测处理|有月度分布尺度校正；低太阳活动GRACE还用NRLMSISE00移到400km，改变验证依赖性|
|指标|RMSE、Bias、相关、Nash、相对/比例类指标；须核对各自定义，不能与本项目relative RMS混同|
|未完整复现项|确切DART revision/全input.nml、obs_seq构造、R数值与相关性、成员初始化与平衡处理仍需作者材料核对|

“验证卫星未被同化”不等于处理链完全独立。论文的跨星月度尺度校正和高度映射带有模型依赖，本项目不利用保留Swarm B或未来时段拟合这些尺度。论文改善百分比不作为本项目承诺或门槛，尚未验证其轨道效益。

## 6. 完整循环与最小部署门禁

1. 每成员同UTC完整primary+一致的secondary/驱动/网格，来自物理合法集合，而非重标时间或补_NM。
2. 观测UTC/产品质量/单位、外部高度登记、算子范围全部通过；obs误差含反演与代表性误差，处理时间相关性。
3. 每成员背景观测H(x)成功，成员异常不可补0；算子与原生DEN同点/层/单位独立核验。
4. filter计算有限集合协方差，经事前局地化/误差/膨胀设置得到分析增量。
5. 只在独立副本按UPDATE写回，检查温度/物种/质量分数、前时层、边界及高度重建；范围界限不等于平衡保证。
6. 零更新file round-trip和短连续/分段一致性先通过，再检查非零增量后可稳定继续；本地这一步当前受阻。
7. 后续自由预报切断未来观测更新，分析误差和未来1/3/6h误差分别报告。

最小有用成员数没有固定已证明答案。数学上样本协方差需至少2个不同成员，但这不等于科学有效；先以**官方20成员例子**为工程规划目标，论文90是外部研究选择，不能认定20足够或90必要。先做无积分的状态读写/观测转换测试，再另授权短恢复资格实验；不直接90成员生产。

## 7. 基于本地实测的成本外推

2022 B14：23040步/16天、4MPI，实际2429.788秒、约3.14GiB输出、采样RSS约0.922GiB。线性估计每成员6h约37.97秒、15天约2277.93秒；模型启动/I/O/成员差异和DART开销另计，不是已测集合速度。

|规划|4MPI串行成员模型墙钟下限外推|按既有输出频率的15天体积外推|
|---|---:|---:|
|20成员15天准备|约12.66小时|约58.9GiB|
|90成员15天准备|约56.95小时|约264.9GiB|
|20成员6h模型推进|约759秒，另加循环filter/I/O|由新输出协议决定|

内存/并行不能简单用裸机CPU数量保证：同时20×4MPI会产生80rank与成员I/O竞争，单成员测量不能证明并发成本。每成员合法集合和误差模型未具备，以上仅资源申请依据；本轮没有集合运行授权。

建议：保留DART为中期内部状态同化路线；近期先做观测算子/坐标与简单输出校正，随后闭合Restart资格，再部署DART最小工程实验。
