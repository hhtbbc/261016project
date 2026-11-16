# TIE-GCM初始场、Restart与观测约束可行性 v1

2026-11-16；`thermosphere_observation_assimilation_feasibility_v1`。研究优先级改为`OBSERVATION_CONSTRAINED_PHYSICS_FIRST`，暂停后续AI训练，旧成果全部保留。本轮新增模型启动/同化/训练/轨道/校正拟合均0。

## 已有功能—复用文件—实际证据—缺口

|功能|可复用入口|实际证据及资格|剩余缺口|
|---|---|---|---|
|完整初场读取/连续模拟|`src/atmosphere/restart_validation.py`；已有2021/2022八条namelist|合法官方smin/smax，34项读取；两年7/14天连续结果实际存在|完整状态科学收敛未全部通过；2022 A14工程PARTIAL|
|原生Restart审计|`scripts/analyze_tiegcm_runtime_restart_audit.py`；`results/tiegcm_runtime_restart_audit_v1/runtime_state_audit.csv`|标准结构完整，但连续/恢复28项primary+9项secondary超原容差|运行时电动力状态重建一致性FAIL，不是缺检查点|
|Swarm CDF/UTC/质量|`scripts/run_swarm_tiegcm_2022_observation.py:read_observation`；`src/evaluation/swarm_density_comparison.py`|A2021/A2022原件已验证；本轮C0301实际读取通过|POD反演不是真值；跨产品系统误差未知|
|统一观测目录|新`src/observations/density_catalog.py`|复用上述读取器；A/C8640条；B值访问明确拒绝；14新CPU测试|只验证POD0301，ACC/GF读取尚未实现|
|原生密度/小时插值|`tiegcm_density_provider.py`、`hourly_tiegcm_observation.py`、`provisional_coordinate_adapter.py`|已有8邻列/不外推/共同样本验证，小时适配独立于原10min接口|正式外部入口仍EXTERNAL_DATUM_UNVERIFIED|
|经验模型|`src/atmosphere/msis_density_provider.py`|pymsis0.13.0、NRLMSIS2.1工程和2023真实轨迹条件结果|2.0是不同版本；2021/2022公平基线未算，Ap输入尚未整理|
|轨道与参考|`src/evaluation/sp3_reader.py`、`orbit_interpolation.py`、`src/orbit/common_force_model.py`|GPS/IGS20 P/V→UTC/GCRS、H6、RK45/DOP853已实际验证|2021/2022目标日SP3未取得；真实气动/推力/缺失力未闭合|
|真实受力记录|`src/orbit/swarm_force_inputs.py`|2023 Jan4 SC_ADYN/STRAATT0601质量记录、只读研究接口|正式姿态旋转/有效面积/Cd/推力未验证，FORMAL模式拒绝|

不能用早期“未实现H6/MSIS/没有合法检查点”等历史文字覆盖后续成果。上下文SHA与版本见本tag `context_source_audit.json`。

## 1. 初始场实际来自哪里

两年A7/A14原始源：`data/raw/tiegcm2_support/tiegcm_res5.0_mareqx_smin_prim.nc`，SHA：
`180475215a4922e9c55a77e80153cf641bc8fbb2b8d52633b4686ddee6942fff`。

两年B7/B14源：`data/raw/tiegcm_2021_spinup_initial_condition_v1/tiegcm_res5.0_mareqx_smax_prim.nc`，SHA：
`a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7`。

均为[NCAR官方2.0支持目录](https://download.hao.ucar.edu/pub/tgcm/data/tiegcm2.0/)提供的完整初始化资产，**原记录是2002-03-21 00UTC（DOY80）**。内部版本字段/上游含trunk、svn1249、1.95资产历史，不能伪称“2021/2022真实观测初场”。实际内容而非文件名证明网格/字段兼容，原文件未重标日期。

本轮实际重读两源、2021/2022 B14暖态primary及secondary共6个文件，全部与既有SHA匹配，输出568行真实变量元数据。源和暖primary均NETCDF3_CLASSIC、lat36/lon72/lev29/ilev29且34核心字段完整；secondary结构检查明确不通过完整Restart资格。

八轨来源、SOURCE/SOURCE_START、START_YEAR/START/STOP、STEP、GPI及SHA见`results/thermosphere_observation_assimilation_feasibility_v1/eight_trajectory_provenance.csv`。7天候选从Mar16起；14天候选从Mar09起。2021停止Mar26，2022停止Mar25；共同候选从Mar23起。Mar24观测时实际已运行约8—9天或15—16天，不把整日都称精确7/14天。

SOURCE_START仍为80 0 0，与模拟实际年/日分开；`input.F:948—960`要求起始小时/分钟相同、日可以不同，这是原生支持的初猜读取，不是把2002记录改成现代日期。两年使用同一实际exe/apex覆盖层、STEP60、4MPI/OMP1、HEELIS、GSWM、CALC_HELIUM=1，同年同方案GPI一致。冷echo继承源F107不能当后续实际强迫，暖态按真实GPI验收。

## 2. 实际34项状态与诊断区别

|类别|字段|
|---|---|
|18当前持久化场|TN UN VN O2 O1 N4S NO HE AR OP N2D TI TE NE O2P OMEGA Z POTEN|
|10滤后前时层|TN_NM UN_NM VN_NM O2_NM O1_NM N4S_NM NO_NM OP_NM HE_NM AR_NM|
|6下边界及历史|TLBC ULBC VLBC TLBC_NM ULBC_NM VLBC_NM|

当前持久化场不等于18个完全独立预报自由度：TN/风/中性组分等由相应方程演化，NE/TI/TE/O2P/OMEGA/Z/POTEN涉及耦合/诊断或重映射。逐变量意义、单位、网格和运行时持久化见既有107行runtime_state_audit.csv及本轮actual_variable_inventory.csv，不把诊断变量直接算成自由可任意改的预报量。

TN/风/主要组分主要在lev中点，实际文件保留29个存储层，AI使用28个有效TN/UN/VN层；DEN/ZG实际在ilev，DEN g/cm³×1000、ZG cm×.01为SI。Z为位势高度、ZG为几何高度，不混用。UN/VN原cm/s、TN K、物种mmr、离子/电子密度cm^-3；按实际字段表逐项处理。

DEN、ZG、N2、WN、TEC等secondary诊断不足以替代primary。N2在本实现由1−O1−O2−He诊断；模型在压力坐标上由温度/组分/高度共同产生密度，不是以卫星DEN格点作为独立完整状态。

## 3. Restart的真实资格

[官方用户指南](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/output.html)支持primary状态作为后续初始化/继续积分载体，secondary用于诊断输出。但本地严格数值验证是更具体的证据：2021同exe/驱动短连续与分段恢复，在00:20时TN最大差0.214774K、POTEN6.802985V、ZG254.28m；28项核心primary+9项secondary超既有阈值，只有6个边界历史量通过。

源码查到pdynamo中原生磁坐标phim3d/ephi3d/elam3d/emz3d等SAVE数组未直接存盘，POTEN地理输出再geo2mag/首步pefield走不同重建路径。已证实不同路径和标准恢复超差；**未证明四数组是全部或唯一根因**，不能把原PRIMARY填成完整RAM快照。本轮不再重做源码审计、不修补第三方、不运行模型。

现有完整暖primary可作为合法新的物理背景初猜，在复制、SHA、时间和全部边界校核后使用；这不等于与前一连续轨迹无损接续。不能伪造_NM、改SOURCE_START、把secondary改名或在旧文件上append。DART频繁循环读取分析场也要经过同样验证，不能因存在DART接口跳过。

## 4. 观测构造更好初态的A—F结论

A：指定日期有合法完整primary且时钟、网格、驱动一致时，可以启动新的模型初始值问题；已有连续模拟证明结构读取可用。任意日期没有对应完整状态时不能凭密度补造。

B：可把既有合法暖primary作为物理背景；当前不能声称其精确恢复全部内部记忆。

C：Swarm沿轨密度是对三维状态的稀疏非线性观测H(x)，涉及位置/高度、温度、组分、压力及插值，尚受外部ZG登记限制。

D：单条沿轨密度不能唯一恢复全三维温度、风、组分、电离层及前时间层/边界；不同状态可产生相同局部密度。

E：未观测自由度需物理背景、合法集合协方差、空间/垂直局地化、观测误差与平衡约束；不能把经验相关当唯一反演。

F：输出层log残差只改最终查询密度，不改模型内部演化；DART/EnKF可以更新指定内部状态，但需正确写回、边界/前时层/守恒与高度重建、合法重启和未来积分验证。

**更接近真实观测的初始状态，不等于把卫星密度直接填进TIE-GCM网格。**

## 5. 三路线与成本

|路线|数据/状态|当前身份|改动与资源|验证/风险|
|---|---|---|---|---|
|A 合法背景+物理预热|完整primary+GPI/边界|连续路线已实现；严格Restart一致性受阻|已有代码复用，单16天4MPI约2430秒/3.14GiB历史量级|内部趋同不等于外部准确；反复Restart可能引入人工调整|
|B 观测修正输出|已有场+过去沿轨密度，有限局部log残差|本轮仅方案；数据/查询已实现，正式高度受阻|不改物理模型，CPU约数分钟小对照可设计|不能称分析状态/全球真实场；外部登记与反演偏差进入残差|
|C DART/EnKF更新状态|多成员完整primary/secondary、观测算子/误差/协方差|有外部案例，本地静态PARTIAL、运行BLOCKED|需单独构建/调度/集合；20或90是外部示例非已证明最小数|Restart、He算子、成员平衡/误差局地化、算力与样本秩限制|

路线B可在PROVISIONAL声明下先研究，不必无限等待全部正式门禁；路线C应先解决接口/恢复的小型资格实验，不能直接部署大集合。具体因果切分和门禁见两份后续实验计划。
