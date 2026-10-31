# FourCastDEN预测密度到H6/RK45：一小时虚拟卫星条件集成

日期：2026-10-31。实验标签`fourcastden_orbit_integration_v1`。

**范围：PROVISIONAL / VIRTUAL_SATELLITE / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST / CONDITIONAL_HEIGHT_REGISTRATION / FORCE_MODEL_INCOMPLETE。**模型间轨道差不是实际卫星预测误差。没有新GPU推理、训练或TIE-GCM积分；原122帧候选不涉及本实验。

## 1. 本轮完成到哪里

实现了可运行的AI原生高度密度查询，以及仅供显式条件演示的私有轨道桥。首次从已有预测TN/DEN和已知TLBC条件反推平均分子量，再按本项目实际`calczg`重建模型原生ZG；没有把Z当ZG，也没有把未来真实ZG填入AI接口。

**原生高度工程重建与地球外部高度登记是两件事。**本轮不解除ITRS/WGS84→模型ZG的正式门禁。轨道实验选择同一时段的虚拟卫星，显式沿用已有A假设“WGS84大地纬度/椭球高近似模型纬度/原生ZG”，只用于验证工程闭环和条件敏感性。正式`density_kg_m3`仍拒绝外部调用；不能把该演示包装成已正确登记的真实Swarm传播。

运行验收的最终实测数值见本文末节及`results/fourcastden_orbit_integration_v1/`；失败记录原样保留，不重试或修改容差。

## 2. 现存数据和可复用代码

本轮用ZIP内NPY头检查了`data/processed/fourcastden*/`的51个保存文件，均有完整171状态预测数组、匹配means/stds；详细shape、键及路径见`saved_array_inventory.csv`。它们是已完成序列，不是51个独立日期。

|已有结果|起点与日期|可用内容|
|---|---|---|
|历史单步与两小时|Jan4旧00起点；五日期00或共同01起点|各任务原NPZ保留，初始化不同不能拼作同一连续任务|
|五日期四模型共同起点|Jan4/Mar23/Jun21/Sep23/Dec21 01时|各两步；History额外00历史|
|两日期四模型六小时|Jan4/Mar24 01时|完整6步、输入反馈和统计|
|两日期四模型十二小时|Jan4/Mar24 01→13|每套pred shape=(1,13,171,36,72)，含初态；本轮主要复用|

本轮实际读取的12小时原件：

- `data/processed/fourcastden_twelve_hour_jan4_v1/2023-01-04_{Direct,Flow,LogDEN,History}.npz`
- `data/processed/fourcastden_twelve_hour_mar24_v1/2023-03-24_{Direct,Flow,LogDEN,History}.npz`
- 同名`experiments/.../data_view/`中的01—13时原NPZ，真实ZG只进入参考检查和C组。
- 坐标来自`data/processed/static/{lat,lon,lev,ilev}.npy`，原始参考NPZ按14字段契约无自带单位属性，以已验证作者源码为单位证据。

H6复用`src/orbit/common_force_model.py:CommonForceModel`、`rk45_propagator.py:propagate`、`drag.py:DragForce/EarthFixedFrame`，冻结配置为`configs/provisional_common_force_model.json`。EGM2008完整40×40和既有ERFA日月项不改，不叠加额外中心/J2。现有受力截断、星历及漏项限制仍保留。

原真实Swarm对照窗为2023-03-21 00:00:02至03-23 00:00:02；本次01—02时的Mar24不重合，不能移用旧SP3或把旧初态更名为Mar24。选择Mar24是因为已有预测、原始参考和冻结GFZ/MSIS驱动均覆盖，不按误差排名选日期。

## 3. DEN、Z和ZG的真实定义

网络目标TN/UN/VN各28层，WN/Z/DEN各29层，合计171。Z为模型常重力870 cm/s²下的位势高度，DEN与ZG在ilev界面，TN在lev中点。Z不是固定几何层，更不能把索引22一律叫450km。

作者原生DEN为g/cm³，反归一化后乘1000得到kg/m³。Z、ZG原生cm，乘0.01到m。普通模型使用各自保存means/stds；LogDEN先恢复标准化log10值，再以10为底反变换，随后才做密度SI转换。Flow的pred已经是累计后的标准化状态，不能在查询时再加一次增量。

### 3.1 源码驱动的间接ZG重建

源码依据：`third_party/TIEGCM2.0/src/dt.F:220–266`、`addiag.F:90–129,161–203,221–282`、`cons.F:29–32,73–87,356–358`。

`calczg`需要每个中点原始平均摩尔质量M，不直接使用网络没有输出的个别组分时，也可尝试由密度方程恢复M：

1. 由TN构造界面温度：底层TLBC、内部相邻TN平均、顶层最后有效TN。
2. 界面压力`p=5e-4 exp(−ilev)`，单位dyn/cm²；**按dt.F原式，最顶压力重复次顶值**，不自行修正成另一压力公式。
3. 界面平均摩尔质量`B=rho·R·T_interface/p`，R=8.314e7 cgs。
4. 原代码从中点质量M构造界面质量：`B0=1.5M0−0.5M1`，`Bk=(M(k−1)+Mk)/2`。因此`M0=(B0+B1)/2`，后续`Mk=2Bk−M(k−1)`。这是代数反演，不拟合测试数据。
5. 以预测Z底层为ZG底层，用`g0=980.616(1−0.0026373 cos(2φ))`及源码有效重力半径，逐层积分`ΔZG=kB·dz·TN/(M/NA·g)`，重力按源码混合ZG/Z估计更新，顶ZG沿用源码的线性构造。最后转换到m。

所需静态信息是模型纬度、ilev、0.5的压力步长和源码常数；动态输入是预测TN/DEN/Z及允许的目标时刻TLBC。**不需要未来真实O1/O2/He或真实ZG。**TLBC是作者HINDCAST已有辅助条件，必须披露，不能称为完全无未来条件的自主预测。

该代数反演会传播DEN/TN预测不一致及交错层误差，误差可随垂直递推放大。若反推M越出该四物种闭合的4—32范围、出现非正/非有限量或高度不递增，保留失败并拒绝整列，不裁剪、平滑、改分母或补真值。

这构成一个**热力诊断一致性假设下的原生高度工程重建**，不等于AI准确预测了真实几何高度。当前网络分别预测TN/DEN/Z，并未强制满足该完整物理约束。

### 3.2 独立验证及限制

11项CPU测试包含独立逐列前向`calczg`参考、已知原始中点质量的反演、单位、格点、垂直/水平/时间插值、周期缝合、无效域和零权重邻列检查；将合成文件中的参考ZG全部毒化为NaN后，AI密度和重建高度仍逐元素相同。合成相容状态的重建按1e-13相对/1e-8m绝对进行比对，不用观察误差调公式。

26个实际参考小时场再与其保存ZG独立比较：Jan4各帧绝对高度差P95最大2.136m、全点最大26.825m；Mar24各帧P95最大7.239m、全点最大119.146m。**这些非零残差明确说明它不是原参考ZG的精确复制**；离散输出/时层和输入精度一致性尚需进一步资格验证，不能将全部残差未经证实归因于float32。

直接把Z当ZG时，这批参考场高度差P95约13.35—13.46km，远大于上述重建残差。

在正式目标Mar24 01/02两帧、450km所有5184个参考格点，固定同一参考DEN，只改变高度为重建/保存ZG，造成的密度绝对相对差P95=0.0040393%、最大0.0133544%。通过启动前冻结的0.1% P95/1%局部最大**工程诊断门槛**；它只限定该高度/该两帧的重建影响，不是大气或轨道准确度门槛，也不证明未来AI高度残差有同样上界。

完整13帧预测质量检查：Jan4四模型和Mar24 Direct/LogDEN/History均无失败列；Mar24 Flow有29/33696列时刻反推质量超界（最大33.532），原DEN仍为正。这是预测多场在该诊断约束下不相容的证据，不能改写成“出现负密度”，也不能悄悄删除。本次轨道固定Direct工程基线，不据此宣布最终模型优劣。

Direct的全部13帧重建有效域：Jan4最低顶高580.417km，Mar24最低顶高616.362km；各列和时刻不同。每次查询仍检查真实八列共同覆盖，不能用一个全局顶高替代局地门禁。

## 4. 查询接口与防误用设计

模块：`src/atmosphere/fourcastden_density.py`。

```python
result = provider(utc, model_lat_deg, east_lon_deg, native_zg_m,
                  datum="TIEGCM_NATIVE_ZG")
if not result.valid:
    raise ValueError(result.reason)
rho_kg_m3 = result.rho_kg_m3
```

返回有效性、密度、模型、两个时间端点、邻列、共同高度覆盖、顶层余量、单位和高度来源。`from_saved`核对预测文件SHA，并用文件自身统计反归一化。`query_pressure`另支持原生ilev索引上的时间/水平密度查询，不隐含几何高度。

几何查询先各时间/水平邻列做log密度垂直插值，再做密度的双线性水平和线性时间插值。经度360°周期；纬度超中心网格域明确拒绝；只容许已存在相邻小时，缺小时/重复/越时失败。时间端点仅吸收小于0.1微秒的表示舍入，不允许物理外推。

两帧×四邻点全部需有效，即使某个权重为0也检查。非正DEN、NaN/Inf不进入插值；推断质量不合法的列返回明确原因。高度超模型有效域立即中止轨道，不补0。

正式`provider.density_kg_m3(query)`仍抛出`EXTERNAL_DATUM_UNVERIFIED`。本次私有`VirtualBridge`仅由实验脚本显式构造，不写入既有正式外部接口。它采用已披露的A假设，不声称物理登记完成。

## 5. H6+RK45条件实验

|设置|本次冻结值|
|---|---|
|时间|2023-03-24 01:00—02:00 UTC，1小时|
|卫星|受控虚拟卫星，非Swarm；GCRS起点半径6378137+450000m，名义60°倾角，初速sqrt(EGM2008 GM/r)|
|非阻力受力|原H6，未修改核心代码|
|气动|质量400kg、迎风面积1m²、Cd2.2，明确合成；共同零ITRS中性风|
|A/B/C/D|无阻力 / NRLMSIS2.1 / 作者同UTC参考DEN+ZG / 官方Direct预测DEN+重建原生ZG|
|共同坐标|B按已有WGS84原生接口；C/D在相同WGS84位置下显式采用A近似；正式登记仍未验证|
|base|rtol1e-10，位置atol1e-3m、速度1e-6m/s，maxstep30s|
|tight|rtol1e-12，位置1e-5m、速度1e-8m/s，maxstep15s|
|输出|每60秒61个状态；每个RHS实时在自身预测位置查询，不沿参考轨道查表|

4种密度定义各一次base和一次必要tight，共最多8次传播，未扩展2/6/24小时。事前预算600秒传播墙钟、RSS1536MiB、新文件100MiB、余盘20GiB，不自动重试。

单轨base/tight最大位置差≤0.02m；每个阻力组相对无阻力组的**差向量收敛差**≤tight响应最大模的1%。这沿用已有一小时工程目标，不是SP3误差界。误差必须比较向量，不能用两个位移模相减代替。

实际驱动：作者NPZ在01/02时f107d=152.9545/153.2731 sfu，f107a=157.8683/157.8429，Kp=7.25/7.41667。NRLMSIS按冻结GFZ使用前日Fobs151.0、中心81日158.67654、七项Ap=(73,154,132,94,39,26.125,13.375)。各模型约定不同，未用GFZ替换作者条件。B/C差包括模型和驱动约定，不能全归因AI。

## 6. 图表、指标与解释范围

图表均由实际保存场/本次CPU计算生成，无概念图冒充结果：

|图表|含义|
|---|---|
|global_density.png|Mar24 02时，参考ZG/AI重建ZG的原生450km全球密度；非WGS84全球精度图|
|native_layer_error.png|同一原生ilev的AI/参考密度误差，无固定高度含义|
|existing_12hour_error_growth.png|读取完整已有两日期四模型1—12小时CSV，不拟合造曲线|
|orbit_differences_and_density.png|本次各自虚拟轨迹上的密度，以及相对A的位置差|
|orbit_RAC.png|R外向、C沿r×v、A=C×R，基于共同A轨迹；不是SP3误差|
|virtual_orbits_3d.png|实际积分的四条虚拟轨道，差异小而几乎重合|
|common_path_density.png|统一在无阻力虚拟轨迹查询AI和参考，隔离取样路径变化|
|layer_dependent_error_growth.png|完整已有12小时的相关层组/固定上层/顶部误差，不另运行模型|

来源目录`results/fourcastden_orbit_integration_v1/`，原状态数组和逐RHS查询仅本地`experiments/fourcastden_orbit_integration_v1/`保留。沿轨密度包含各模型不同轨迹位置的影响；后续若要分离纯密度场差应在同一固定轨迹再查询，不将两者混称。

D−C是“AI/参考密度场与各自高度表示，经同一条件桥导致的轨道差”，不是真实预测误差，也不纯是DEN单变量误差；D还涉及预测TN/Z及热力重建。A/B/C/D均未与同日期SP3比较，真实卫星精度指标为N/A。

## 7. 更新周期与下一步

已有12小时表能研究误差积累和层间差异，但不能据两日期给出最优6/12小时修正周期。下一项最有价值的是：复用连续12小时轨迹，在+6h处用真实TIE参考全状态做一次**离线理想重初始化**，只重算后6小时，比较同目标时刻。它不是业务观测同化，需要单独GPU授权，本轮未执行。12小时更新后的效果需更长共同任务，当前资料不足。

计划：`docs/FOURCASTDEN_STATE_UPDATE_EXPERIMENT_PLAN.md`。正式AI→真实轨道仍需可信外部高度/纬度登记、未来AI高度重建误差资格、同期真实气动/姿态/推进器参数和独立轨道参考/完整共同受力协议。本轮工程闭环不解除任何科学训练门禁，也不回到Restart修复或长预热。

## 8. 复现入口

```bash
source scripts/activate_orbit.sh
python tests/test_fourcastden_density.py
python scripts/run_fourcastden_orbit_integration_v1.py prepare
python scripts/run_fourcastden_orbit_integration_v1.py analyze
python scripts/run_fourcastden_orbit_integration_v1.py integrate
python scripts/run_fourcastden_orbit_integration_v1.py finalize
python scripts/finalize_fourcastden_orbit_delivery.py
```

本次标签已存在，prepare和正式积分重放会拒绝，不覆盖旧结果。需要复现实验时应审查后使用新独立标签，不删除本次目录；现存数据可直接只读检查。分析/运行日志保留在`logs/fourcastden_orbit_v1_*.log`。

## 9. 一句话讲清从密度到位置

先把网络标准化结果恢复为物理密度，再为每个压力层建立经过核查的原生高度；轨道积分每次需要加速度时，把当前卫星位置转换到大气坐标，按时空邻点查询密度，用`−0.5 rho Cd A/m |v_rel|v_rel`计算阻力，与H6其他受力相加，RK45推进速度和位置。**本次高度到地球坐标的那一步仍是显式条件假设，所以闭环是虚拟工程演示，而非真实卫星精度证明。**

## 10. 最终实际验收

四组base和tight共8次均完成3600秒，无失败重试。每组61个输出点，base各746次RHS，tight各1466次RHS。所有真实查询成功，没有高度外推、负密度补零或未来参考ZG替代。

|组别|tight终点相对无阻力位置差 m|base积分墙钟 s|tight积分墙钟 s|
|---|---:|---:|---:|
|A 无阻力|0|31.668|62.048|
|B NRLMSIS2.1|9.848619|51.427|101.415|
|C TIE参考|7.536932|50.349|99.672|
|D AI Direct|7.541792|50.443|99.520|

D−C终点/最大差0.005396859m、全窗RMS0.001705155m。统一A路径上的AI/参考密度绝对相对差P95=1.14465%；密度差随路径积分、方向、时间变化，不应从该百分比直接线性推断终点位移或长期精度。

四个单轨base/tight最大位置差均约0.00154—0.00155m，小于0.02m；六组配对差向量均满足原1%门槛。C/D配对收敛差最大3.635693e-6m，相对于5.396859e-3m响应可分辨。它不是严格全局误差界，更不是毫米级真实轨道准确度。

正式传播阶段总墙钟556.789秒（预算600秒），峰值进程RSS207.801MiB。各积分墙钟已包含实时密度查询；不可再把查询时间加一次。C/D base记录807次查询、tight1527次，包含RHS与另外61个输出点；表中`native_query_time_s`是二者合计，不能据此反推纯RHS查询耗时。B走独立MSIS接口，其native_query_count=0不表示没有密度调用。

离线场读取/重建/检查/绘图约3.993秒，独立后处理/历史SHA审查约13.599秒，都不是纯神经网络推理时间。本轮新网络加载/forward为0，复用原预测场；因此不能据此宣称AI相对TIE-GCM有多少端到端加速。

51个保存预测数组头、59项本任务输入SHA及2346项历史科学资产SHA全部核对通过；旧模型、122候选、A7/B7/A14/B14和历史CSV未改。11项CPU测试全部通过；后处理另从状态数组独立检查全部6组配对、122次共同路径查询。29个Flow无效重建列均保留在`flow_invalid_height_columns.csv`，首次出现于+4h，不隐藏不利结果。

|门禁|判定|
|---|---|
|有有效原生高度列时的AI密度查询工程|PASS，接口提供拒绝/覆盖元数据|
|从AI输出获得精确、独立真实几何高度|未证明；仅模型原生热力诊断工程重建|
|一小时虚拟卫星条件H6/RK45闭环|PASS，严格限定A坐标假设与合成气动参数|
|正式ITRS/WGS84到ZG登记|仍未通过，正式接口未启用|
|真实Swarm轨道预测精度|N/A，无同时间SP3对照，未验证|
|科学训练READY|仍False；本轮未训练|

### 独立数据核查命令（不运行模型）

```bash
source scripts/activate_orbit.sh
cat experiments/fourcastden_orbit_integration_v1/integration.json
cat results/fourcastden_orbit_integration_v1/orbit_summary.json
cat results/fourcastden_orbit_integration_v1/all_pair_convergence.csv
cat results/fourcastden_orbit_integration_v1/independent_delivery_checks.json
```

新任务成果仅作本地安全提交，保留前两条未推送提交及任务开始时已有未跟踪日志；继承此前远端同步限制，不push、不强推。实际提交号/远端HEAD/工作区状态在任务Git日志记录，不将本地完成误报为GitHub同步成功。
