# 12小时AI状态更新轨道效应：B/C独立DOP853验证 V1

## 1. 完成范围与核心结论

B/C高阶单轨与配对门槛均通过。本轮实际新增B_Open、C_Updated各DOP853 max30/15秒，共4条Jan4 01—13UTC轨迹、8个6小时积分段，各721个输出。A高阶参考只读复用，D高阶未运行，旧8条RK45未重跑。

DOP15 Updated−Open终点4.69800532185m，全窗RMS1.46181963923m，最大4.69800532185m；旧RK45 Tight终点4.69834666141m。终点**范数**差（DOP15−RK45）-0.00034133955749m；终点**效应差向量**模0.000341740254523m，二者不能混用。

所有结果是HISTORICAL_SP3_INITIALIZED_VIRTUAL_PROPAGATION / PROVISIONAL_COORDINATE_A / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST / FORCE_MODEL_INCOMPLETE / PROVISIONAL_EPHEMERIS下的条件轨道效应，不是真实Swarm轨道预测误差。没有计算相对SP3残差。

## 2. 输入、配置和保护

读取AGENTS、STATUS、WORKLOG及用户指定5份报告/决策/协议和实际代码，context_read.json记录SHA。旧RK458轨、A DOP30/DOP15、FourCastDEN Direct原预测及07理想更新文件和统计保留；输入/旧输出SHA预检、协议protected.json与最终审计形成可追溯链。

初态仍为2023-01-04 01UTC同期SP3 Hermite P/V：原括点00:59:52和01:00:02，使用后验2秒信息，明确历史平滑初始化；同一GCRS6维初态SHA75c16067a16319946d318c93a20f7d44e36dff8d271a189ba74653676a3ba1e1。正式worker只读该已冻结初态，不读取未来SP3修正轨道。

H6（原EGM2008 40阶及日月）、时间/EOP/闰秒、地球常数均不变；气动400kg、1m²、Cd2.2、零ITRS中性风，完整ITRS速度作相对速度，不重复扣自转。正式外部密度协议仍EXTERNAL_DATUM_UNVERIFIED；只由已有显式ProvisionalEventBridge采用A坐标假设。

预测数据直接复用已有Direct13帧与Updated07—13七帧。AI TN/DEN/Z/TLBC按原热力诊断重建ZG；Z不当ZG、未来参考ZG不补入AI。DEN反归一化g/cm³乘1000成kg/m³，原高度cm乘0.01成m，未来辅助/驱动维持作者HINDCAST。B/C每次两帧×四水平邻列都必须有效，时间/纬度/经度周期/局地垂直覆盖严格检查，禁外推、裁边、补零和替代密度。

## 3. 分段DOP853实现及前置验证

新增`src/orbit/dop853_events.py`只提供DOP853单段适配，并在独立globals副本中给已有event_segments函数绑定该求解器。事件函数**原字节码和左右段逻辑直接复用**；原模块globals、RK45模块、H6核心及物理源码不改。3项新CPU测试验证解析加速度跳变、左右端RHS绑定、P/V精确交接、原solver全局对象不变、失败拒绝和坏事件前置拒绝。它们不是重放旧H6短例。

冻结两套：rtol2.5e-13，atol位置1e-6m/速度1e-9m/s，maxstep30或15s；60秒输出721点。四组使用同一旧A_NoDrag RK45 Tight RAC基作当前比较，不通过改变坐标基减少误差；A DOP15另复用于B/C相对无阻力的附加条件响应，未新跑A。

复用既有**真实SP3路径的已保存经纬高**重查当前密度场，不改用固定高度。B/C8646/8646预检有效，最小顶高余量110681.350m。该路径只提供必要条件，在线每次查询仍独立执行。

执行顺序B30→C30→B15→C15，前两条完整性、有限值、事件交接和密度门禁通过后写DOP30_gate，再按实测剩余预算决定DOP15。每条独立积分，不拼接另一组的已完成前缀，不无限重试。

## 4. 实际资源与在线有效性

|组|配置|积分秒|含诊断保存秒|nfev|全部密度查询|
|---|---|---:|---:|---:|---:|
|B_Open|DOP30|1489.5689592398703|1508.6994564533234|21724|22449|
|C_Updated|DOP30|1493.6768737509847|1512.816306591034|21724|22449|
|B_Open|DOP15|2977.071540489793|2996.1697958521545|43309|44034|
|C_Updated|DOP15|2988.196066532284|3007.388308636844|43309|44034|

监督墙钟9033.128s，峰值树RSS350.797MiB，低于13620秒/4GiB；实际预检、离线分析另行记录，不混同纯积分耗时。查询计数包含每步求解及DOP连续输出阶段调用、2次事件RHS、721次输出及2次显式极限，共132966次，全部有效。nfev包含DOP连续输出所需额外3阶段，未隐瞒调用。全部逐次查询日志和状态NPZ保留本地。

八邻列共同高度余量与左右时间括点独立核验见independent_query_accounting.csv。所有left上括点≤07、right下括点≥07，未把07右状态提前插值到06—07。

## 5. 单轨与效应差向量收敛

单轨门槛仍为全窗最大位置差≤0.02m；速度差仅报告，没有临时发明新的速度门槛。

|单轨比较|最大位置差m|终点m|全窗RMS m|最大速度差m/s|
|---|---:|---:|---:|---:|
|B_Open DOP30 minus DOP15|0.00032041784080280204|0.00012828301714783494|0.00011051692389756502|2.9513878517120036e-07|
|C_Updated DOP30 minus DOP15|0.0008509143698082298|0.0008509143698082298|0.0002489716984960641|9.56410006538603e-07|

效应定义Δ30=C30−B30、Δ15=C15−B15，数值差δ=Δ30−Δ15。必须先减向量，再取模。全窗最大δ模0.000979184418557m、终点0.000979184418557m；DOP15最大响应4.69800532185m，冻结1%限值0.0469800532185m，相对敏感性0.0208425566059%。

两套DOP之差是数值设置敏感性，不是DOP15相对精确解的严格误差上界；两算法也共用H6，不能验证其共同系统物理误差。

## 6. 旧RK45 Tight独立对照

|旧轨道−新DOP15|全窗最大位置差m|终点m|全窗RMS m|最大速度差m/s|
|---|---:|---:|---:|---:|
|B_Open RK45_Tight minus DOP15|0.008554114825280257|0.008554114825280257|0.003896890941090405|9.547372363431834e-06|
|C_Updated RK45_Tight minus DOP15|0.008212375395777663|0.008212375395777663|0.003802290685816122|9.16312055583179e-06|

旧RK45 B/C效应差向量−DOP15效应差向量，全窗最大0.000341740254523m、终点0.000341740254523m。旧RK45是否落在独立0.02m范围见下方实际门禁；不把相减后的共模抵消反过来当单轨通过证据。历史旧Base/Tight约0.24m的FAIL原样保留。

accepted_rejected_steps.csv记录DOP实际接受/推算拒绝步。密度小时/空间分片插值可改变平滑性，07硬更新靠显式分段处理；只有本轮直接数值差支持本窗口的稳定性，不根据NoDrag结果预先宣布B/C合格，也不能单凭差异将残余唯一归因为密度插值。

补充按时段的离线复核：07前B/C两组数值差完全相同，最大约0.07884mm；07后B/C的最大数值差分别约0.32042/0.85091mm。相对NoDrag两DOP约0.001278mm的差异，加入阻力/密度查询后存在更明显的步长敏感性，但本轮不能唯一分配密度分片插值、非线性轨道反馈和浮点求值各自贡献。07首10分钟两组数值差仍约0.0606mm，未见由P/V重置造成的阶跃。详见period_sensitivity.csv。

小效应也单独保留绝对数值差：07:01更新效应约1.89697e-5m，两DOP效应差向量约1.04125e-9m；零效应点不强行定义百分比、不加分母下限。逐时敏感性见per_time_effect_sensitivity.csv，事件检查点见event_response_checkpoints.csv。

## 7. 更新轨道效应与07事件

两配置下B/C更新前361个状态逐元素一致，07左终点和右起点P/V严格相同，四条轨迹均0跳变。C DOP15事件同状态密度8.19152726739e-13→8.82741891305e-13kg/m³（7.76279715%），阻力加速度向量跳变量模1.01625993547e-08m/s²。位置速度不瞬变，后续密度变化造成加速度差，经积分及共同动力学耦合积累为速度和位置差。

DOP15终点Updated−Open的R/A/C=-0.369591949489/4.68344194788/0.00522645933779m，终点速度差模0.00525777820327m/s。所有RAC用同一冻结基；沿轨位置响应不等于阻力直接只有沿轨分量。完整721点及1/3/6左右/7/9/12h见comparison_curves、lead_time_summary，既报告全窗RMS也报告终点。

**本轮没有D高阶轨道。**因此只验证状态更新对B/C条件轨道的影响及与旧RK45的一致程度，不宣布Updated更接近高阶TIE-GCM条件参考。旧9.177625m/4.482435m只能保留为旧RK45历史值，未在本轮补齐高阶数值资格，更不能称真实Swarm精度改善。

本次更新是用未来TIE-GCM参考全状态进行的离线理想重初始化，不是真实观测同化，也不能据此确定业务最优更新周期。

## 8. D组决策

若B/C门槛通过，值得下一轮单独补D30/D15，以完成Open−D、Updated−D以及“终点与全窗是否都改善”的高阶闭环。按本次B/C实际单组成本均值，D两条约4512.5s，1.5安全预算6768.8s；内存预估<1GiB、硬上限4GiB，输出预估<50MiB。

D参考DEN/原ZG在旧Jan4路径与RK45在线检查曾有效；仍需新一轮输入SHA/局地高度/极区/UTC预检及逐RHS100%有效，不直接将旧路径通过视为DOP自由轨迹的完整覆盖保证。保持同H6、初态、气动、A假设、07分段及30/15+严格容差；单轨≤0.02m、所有与B/C/A同配置配对差向量≤最大效应1%，门槛不放宽。D若未运行则D_REFERENCE_HIGH_ORDER_READY绝不能PASS。

如果B/C本轮未通过，先定位数值问题再谈D，不能依据报告模板擅自启动。无论是否有剩余预算，本轮D新增传播为0。

## 9. 实际验收

|门禁|实际状态|
|---|---|
|BC_DOP853_30_READY|PASS|
|BC_DOP853_15_READY|PASS|
|B_SINGLE_ORBIT_CONVERGENCE_READY|PASS|
|C_SINGLE_ORBIT_CONVERGENCE_READY|PASS|
|BC_PAIR_EFFECT_CONVERGENCE_READY|PASS|
|RK45_TIGHT_INDEPENDENT_REFERENCE_READY|PASS|
|D_REFERENCE_HIGH_ORDER_READY|NOT_RUN|
|SCIENTIFIC_REAL_ORBIT_VALIDATION_READY|BLOCKED|

独立审计不重新积分，直接从原状态重算单轨、配对向量、旧新效应差，核对查询总数、八列高度域、左右时间括点及保存rho/v_rel/阻力模方程。冻结326任务资产和2346历史资产SHA不变，A参考两数组SHA不变。真实轨道BLOCKED、科学训练False、旧RK45 FAIL保持。

## 10. 交付与复现

8图：single_orbit_convergence、update_effect_12h、update_effect_RAC、RK45_DOP853_comparison、density_and_drag、event_07UTC、paired_effect_convergence、runtime_and_evaluations。全部来自完成轨迹，来源与PNG SHA见figure_sources.csv；图注保留坐标/气动/旧门禁/D未跑等限制。若本轮数值失败，图标题自动标FAIL，结果不隐藏。

```bash
source scripts/activate_orbit.sh
python tests/test_dop853_events.py
python scripts/run_orbit_12h_bc_dop853_validation_v1.py prepare
python scripts/run_orbit_12h_bc_dop853_validation_v1.py supervise
python scripts/analyze_orbit_12h_bc_dop853_validation_v1.py
python scripts/plot_orbit_12h_bc_dop853_validation_v1.py
python scripts/audit_orbit_12h_bc_dop853_validation_v1.py
python scripts/document_orbit_12h_bc_dop853_validation_v1.py
```

旧标签完成后拒绝重放；若独立复现需新授权和run-tag，不删除旧目录。完整派生comparison_curves.csv公开为无损comparison_curves.csv.xz，解压SHA逐字节一致见compressed_result_manifest.json；原始状态NPZ、位置查询日志、SP3/DNS/权重仅本地；公开轻量派生指标、图表、代码、协议和SHA，不提交凭据、不强推。完成后停止，不执行D、24h、多日期、多模型或训练。
