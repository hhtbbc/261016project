# FourCastDEN理想状态更新的跨事件条件轨道实验 V1

## 结论与范围

实际完成2023-01-04 06:30—07:30 UTC四组H6虚拟传播及Base/Tight，共8条轨迹、16个半小时RK45段。07:00只更新大气，不重置卫星；P/V交接逐元素一致。新增5项CPU测试通过，4项单轨及6项配对数值门槛通过。

全程标记：HISTORICAL_SP3_INITIALIZED_VIRTUAL_PROPAGATION / PROVISIONAL_COORDINATE_A / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST / FORCE_MODEL_INCOMPLETE / PROVISIONAL_EPHEMERIS。所有差异是**条件模型间轨道差异**，不是Swarm真实轨道预测误差。正式EXTERNAL_DATUM_UNVERIFIED及真实轨道BLOCKED不解除；SCIENTIFIC_TRAINING_READY=False、122候选不变。

## 冻结输入及方法

读取任务指定AGENTS、STATUS、WORKLOG及5份报告/协议，SHA见`experiments/fourcastden_orbit_update_event_v1/context_read.json`。复用原Direct Jan4预测、6小时更新预测及TIE-GCM参考；未网络forward、训练、TIE积分或下载。完整来源SHA见`protected_runtime_v2.json`，其余初始审计版本保留。

四组：A无阻力；B原Open-loop；C事件更新；D作者参考DEN/ZG。H6为原40阶EGM2008、ERFA日月等既有共同非阻力动力学，不修改核心物理代码。合成质量400kg、面积1m²、Cd2.2、相对地面中性风零，与上一虚拟实验完全相同。相对速度由完整ITRS状态计算，不重复扣地球自转。

SP3 0203原生GPS/IGS20 P/V按冻结闰秒/EOP转ITRS/GCRS。06:30 Hermite括点包含未来06:30:02，是历史平滑初态，不是业务因果预测。传播开始后不再读取SP3修正轨道，不计算或优化SP3残差。

A坐标假设仅通过新增显式实验桥`src/atmosphere/provisional_event_bridge.py`启用，必须传入PROVISIONAL_COORDINATE_A。WGS84纬度/椭球高近似原生纬度/ZG，未声称正式登记。原正式接口仍拒绝外部请求；不外推、不补零、不切换密度。

B/C/D均用原`EventAwareDensity`；C左侧终帧07原预测、右侧首帧07参考分别保留，禁止跨事件时间插值。所有四组在1800s明确分段，用原`propagate_event_segments`传递同一6维状态。RHS左段包括终点采用left，右段包括起点采用right。

Base：rtol=1e-10、位置atol1e-3m、速度1e-6m/s、max_step30s；Tight：1e-12、1e-5m、1e-8m/s、15s。输出60s一次。沿用旧协议：单轨最大差≤0.02m；配对差向量Base/Tight差≤Tight响应最大值的1%。不根据结果改变门槛。

## 覆盖与事件结果

SP3路径预检查1089/1089有效，最小顶高余量115736.484m；不替代在线检查。实际在线加输出/接缝诊断共7182次密度查询全部有效，包含两帧四水平邻点八列检查；A从不调用密度。完整记录`*_queries_local.csv`只保留本地。独立检查所有left时间括点≤07、right≥07，B/C事件前状态位级一致。

Tight C事件同一卫星位置上，密度由8.19264774755e-13变为8.8286168381e-13 kg/m³，跳变7.762681%。阻力加速度模由1.30932284009e-07变为1.4109613923e-07 m/s²；向量跳变量模1.01638552212e-08 m/s²。同一瞬间相对速度连续，阻力与密度同比例变化独立核验通过。全部8条P/V交接差均严格0；无重复/遗漏时间段。

## 实际轨道差异（Tight）

RAC采用共同A无阻力轨迹定义，R径向向外、C沿r×v、A=C×R。三维范数和分量均m；全段RMS是61个等间隔输出点的描述性统计。

|比较|终点m|最大m|全段RMS m|终点R m|终点A m|终点C m|
|---|---:|---:|---:|---:|---:|---:|
|C_Updated minus B_Open|0.016232023|0.016232023|0.005004774|-0.015128119|0.005866434|-0.000451152|
|B_Open minus D_Reference|0.016235424|0.016235424|0.006165150|0.016222532|0.000323152|0.000560389|
|C_Updated minus D_Reference|0.006286545|0.006384909|0.003454081|0.001094412|0.006189586|0.000109238|
|B_Open minus A_NoDrag|2.407080508|2.407080508|0.937921586|-1.056896652|2.162609138|-0.011302781|
|C_Updated minus A_NoDrag|2.419020789|2.419020789|0.940320191|-1.072024772|2.168475573|-0.011753933|
|D_Reference minus A_NoDrag|2.413960689|2.413960689|0.937362857|-1.073119184|2.162285987|-0.011863171|

Updated−Open终点16.232023mm。相对D条件轨道，Open终点16.235424mm，Updated终点6.286545mm。上述表同时给出全段，不能把终点更接近外推成所有时刻更优，也不等同观测精度改善。

Updated−Open终点R/A/C分别为−15.1281/+5.8664/−0.4512mm，本短窗径向分量最大；这并不意味着阻力直接沿径向作用，轨道耦合会改变位置差方向。相对于D，更新后的终点差缩小约61.28%，仅为本窗口条件结果。

## 数值独立核验

|轨迹/配对|最大Base/Tight差m|冻结限值m|通过|
|---|---:|---:|---|
|A_NoDrag|0.00148451112|0.02|True|
|B_Open|0.00147392645|0.02|True|
|C_Updated|0.00147387936|0.02|True|
|D_Reference|0.00147548839|0.02|True|
|A_NoDrag minus B_Open|3.24955905e-05|0.0240708051|True|
|A_NoDrag minus C_Updated|3.22592283e-05|0.0241902079|True|
|A_NoDrag minus D_Reference|2.80854858e-05|0.0241396069|True|
|B_Open minus C_Updated|2.76713147e-07|0.000162320235|True|
|B_Open minus D_Reference|4.41590462e-06|0.000162354243|True|
|C_Updated minus D_Reference|4.1891466e-06|6.38490941e-05|True|

单轨4项、配对6项全部PASS；独立脚本从原保存状态重新计算配对向量差，不读取汇总范数替代计算。数值差不能解释为大气误差；这里模型间条件响应通过原1%分辨门槛。

## 资源与命令

|组/精度|实际积分s|求解器nfev|全部密度查询数|
|---|---:|---:|---:|
|A_NoDrag base|33.158|772|0|
|B_Open base|52.914|772|837|
|C_Updated base|52.966|772|837|
|D_Reference base|53.113|772|837|
|A_NoDrag tight|64.187|1492|0|
|B_Open tight|102.507|1492|1557|
|C_Updated tight|102.490|1492|1557|
|D_Reference tight|103.232|1492|1557|

监督墙钟580.941s；准备7.411s；截至独立审计记录的预算耗时606.502s <1800s。监督进程树峰值RSS359.586MiB；实验目录约2.12MB、结果约0.89MB（文档写入前），远低于4GiB/200MiB。实际内存和磁盘见`supervision.json`/`worker_complete.json`，未增加GPU/MPI任务。查询数包括求解器调用、分段接口2次事件RHS、61输出及2接缝诊断；A为0，未隐瞒额外诊断调用。

初始监督脚本发现环境无psutil，正式传播启动前改为只读/proc进程树监控，不安装依赖；保留初版SHA、异常说明及运行版SHA。此时模型启动0，之后正式worker仅启动一次，无重试。

可复现入口（旧标签已完成，不覆盖重放；若经新授权复现必须使用独立标签）：

```bash
source scripts/activate_orbit.sh
python -m unittest discover -s tests -p test_provisional_event_bridge.py
python scripts/run_fourcastden_orbit_update_event_v1.py prepare
python scripts/run_fourcastden_orbit_update_event_v1.py supervise
python scripts/analyze_fourcastden_orbit_update_event_v1.py
python scripts/plot_fourcastden_orbit_update_event_v1.py
python scripts/audit_fourcastden_orbit_update_event_v1.py
```

历史2346项及任务冻结92项SHA不变。5张PNG完整性通过，来源见`results/fourcastden_orbit_update_event_v1/figure_sources.csv`。报告/图为新增，不覆盖旧实验。原始轨迹、初态和逐查询位置表本地忽略，不公开。

## 12小时准入与下一步

短时跨事件机制PASS；完整12小时条件传播仅PARTIAL/需另授权，正式真实轨道BLOCKED。四组Base/Tight按本次实测外推约6893.8s，1.5安全系数10340.6s；A/B两坐标假设共用无阻力的7组Base/Tight约12618.9s。它们不是已测12h耗时，超过当前1800s预算。

Jan4 Direct分支现有帧及重建列支持见`twelve_hour_data_support.csv`，不等于12h自由积分路径100%覆盖；未来须先冻结12h初态/覆盖、独立预算并在线拒绝无效列。A/B可用于条件敏感性，不能择优当正式坐标；本轮不重跑历史A/B查询。其他模型/日期热力无效列问题不能套用本次Jan4 Direct成功，不能静默补洞。

真实Swarm轨道仍缺：ZG外部参考面登记、同期可靠质量/有效面积/姿态/Cd/推力条件、完整受力及独立参考评价。不得用本窗口未来SP3拟合Cd/密度比例/高度偏移。当前最有价值的下一实验是经授权、冻结预算的Jan4 Direct长窗条件传播与独立数值收敛，同时继续解决外部登记；不是立即声称真实精度或开展训练。本轮完成即停止。
