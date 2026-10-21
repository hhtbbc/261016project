"""Generate reports only from saved independent checks and actual trajectories."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/gravity_third_body_v1';v=json.loads((F/'validation.json').read_text());a=json.loads((F/'analysis.json').read_text());run=a['run'];conf=json.loads((F/'configuration.json').read_text());g=v['gravity40'];third=v['third_body'];p4=a['pairs']['H4_H3'];p5=a['pairs']['H5_H3']
text=f'''# 40×40地球引力独立验证

## 源与向后兼容

同一GFZ EGM2008源仅取262144字节前缀，SHA `{conf['source40']['sha256']}`；前65536字节逐字节匹配20阶源，未下载完整252MB模型。完整n≤40、m≤n共861对C/S（地心一阶零项明确记录）；GM398600441500000m³/s²、R6378136.3m、fully_normalized/no CS、tide_free与H3相同，完整包含非带谐项。轻量系数configs/egm2008_40x40.json及来源清单可追溯。

独立gravity_degree40.py只扩展初始化，继承原Cartesian势/梯度；未改旧8/20阶或历史H3。40阶中间阶乘80!约7e118、双阶乘约1e59，在本次近地测试范围内尚有float64余量。仍必须经过独立测试，不据阶乘有限就宣布高阶准确；仅验证至40，不允许直接推广80/100。精确极点不除水平半径，生产极点连续性通过；SHTOOLS不支持精确极点求导，外部使用近极点。

## 独立数值结果

SHTOOLS4.14.1 Fortran，同C/S、omega=0，对100个固定随机点、赤道/±89.9°近极和经度接缝对照。最大向量绝对差{g['max_abs_difference_m_s2']:.9e}m/s²、相对差{g['max_relative_difference']:.9e}，低于固定rtol/atol2e−12/2e−12m/s²。负梯度三档10km/1km/100m相对差：{g['gradient_errors_10km_1km_100m']}，二阶收敛且细步<2e−8。

新类20阶与原ExtendedEarthGravity在全部361个历史H3状态经完整GCRS/ITRS旋转后的加速度逐位相同，低阶8/12/20系数与势/力也核对；没有重新积分H3。5项新引力测试和8项新第三体测试，全176项通过。核心源码/系数/测试和预注册阈值有审计SHA，229项历史文件保持不变。

100个构造点的纯引力计算平均{g['mean_pure_field_ms']:.3f}ms、P95 {g['P95_pure_field_ms']:.3f}ms；不含框架转换，不是实际轨道积分的单步耗时，也不与历史不同负载计时作严格加速比。

## 数值积分范围

H4短例base/tight最大差{a['short_checks']['H4']['state_max_m']:.9f}m，低于预注册0.02m。H4六小时只运行base一次，没有六小时tight对照；**全窗状态及配对收敛PENDING**，不能将短例0.257mm当六小时误差界。旧H3的base/tight约0.0584m也不能直接当H4误差界。结果只用于有清晰限制的条件模型研究。

复现入口source scripts/activate_orbit.sh；PYTHONPATH=src python -m unittest discover -s tests -v；python scripts/validate_h4h5.py；python scripts/run_h4h5.py（静态）与--execute（本次已执行，x模式拒绝重复）。原始前缀/参考库/NPZ本地不入Git，已有标签不重放。完整配置与launch/验证/资源在experiments/gravity_third_body_v1。
'''
(ROOT/'reports/GRAVITY_40X40_VALIDATION.md').write_text(text)
text='''# 日月第三体引力独立验证

## 模型和坐标精度范围

新增third_body_gravity.py，以当前RK45时间和GCRS卫星位置实时计算太阳/月球地心差分，不读取未来SP3位置、不从SP3拟合参数。采用已独立核对的稳定差分核，包含地心参考减项：

`a = μ[(R-r)/|R-r|³ - R/|R|³]`。

每次RHS实时计算时变位置；无运行时网络、未知大核或轨道插值。月球ERFA moon98输入TT，原生GCRS；太阳取ERFA epv00在TDB的日心地球矢量相反数，以Newtonian阶GCRS对齐几何使用。不是含光行时/恒星像差的apparent坐标。完整相对论BCRS/GCRS空间及GM时标缩放未实现，因此保留PROVISIONAL_EPHEMERIS，不能叫完整精密GCRS星历实现。UTC→TT/TDB由既有Astropy和冻结闰秒处理，不手动加减常数。

日月GM从已归档NASA NAIF gm_de440.tpc读取，km³/s²乘1e9。仅GM来自DE440，位置不来自DE440。本次预注册精度层次为Newtonian机制研究，未闭合时标缩放不允许被隐藏为完全统一的相对论模型。

## 独立位置和加速度检查

NASA Horizons小样本采用地心500@399、ICRF FRAME、TDB、VEC_CORR=NONE、KM-S，返回源DE441，0/3/6小时各一次，无顶点/光行时/日心位置混用。原始响应和查询清单存data/raw/third_body_validation，精简位置/查询/SHA在validation.json。

|天体|最大位置差(m)|冻结位置门槛(m)|同H3状态最大差分加速度相对差|
|---|---:|---:|---:|
'''
for b,r in third['independent_references'].items():text+=f"|{b}|{r['max_position_difference_m']:.6f}|{r['position_gate_m']:.0f}|{max(x['differential_accel_relative_difference'] for x in r['checks']):.9e}|\n"
text+=f'''
太阳GM={third['GM_m3_s2']['sun']:.16e}、月球GM={third['GM_m3_s2']['moon']:.16e}m³/s²。Sun20km/Moon40km门槛来自ERFA已知精度的保守工程范围，并非本窗口置信界。内置epv00在1900—2100相对DE405日心位置文档RMS/最大3.7/11.2km，moon98在1950—2100相对ELP为6.1/31.7km；2023在适用区间，但文档范围不是本窗口实际误差界。

实际三点位置与力对照支持当前PROVISIONAL量级/机制实验，不证明全六小时星历误差传播界，更不能用H5残差较小替代独立验证。几何ICRF与GCRS在本模型只作Newtonian阶对齐；完整坐标/时标问题留在正式门禁中。后续若需要严格星历精度，应冻结JPL核及规范空间/GM缩放并做轨道级独立误差检查。

8项新增测试覆盖GM/单位、独立位置、地心零点、稳定式与独立直接式、趋地心线性极限、关太阳恢复月球/全关恢复原20阶RHS、时间连续、极端方向/越界拒绝、重复查询及量级。原离线数学测试的线性潮汐对照仍通过。关闭项只做精确RHS恢复，未额外重跑六小时H3；不能声称执行了额外关闭轨道实验。

H5短例base/tight最大差{a['short_checks']['H5']['state_max_m']:.9f}m<0.02m；六小时base只一次，**全窗及配对tight收敛仍PENDING**，不把全部轨道差认定已数值隔离的物理贡献。无SRP/推力/潮汐/阻力加入本次RHS。
'''
(ROOT/'reports/THIRD_BODY_GRAVITY_VALIDATION.md').write_text(text)
text='''# H3/H4/H5六小时受控比较

PROVISIONAL / HINDCAST / NO_DRAG；H5额外PROVISIONAL_EPHEMERIS；FULL6H_CONVERGENCE_PENDING。

同一冻结SP3单历元状态，2023-03-21 00:00:02—06:00:02 UTC，GCRS、60秒输出361点、相同原RK45 base/分量atol/maxstep30s及EOP/闰秒。H3历史20阶只读；H4仅改40阶；H5仅加日月。H6不执行。原8/12/20/G0—G2/D0—D5和基础源码保留。

## SP3残差

参考为有自身误差的后处理SP3，不是绝对真值。残差=模型−参考，R向外、C沿参考r×v、A=C×R。

|模型|1h(m)|3h(m)|6h终点(m)|全段3D RMSE(m)|R/A/C RMSE(m)|
|---|---:|---:|---:|---:|---|
'''
for n,s in a['residuals'].items():
 h=s['hours_1_3_6_m'];text+=f"|{n}|{h[0]:.6f}|{h[1]:.6f}|{s['terminal_m']:.6f}|{s['rmse_3d_m']:.6f}|"+' / '.join(f'{x:.6f}' for x in s['rac_rmse_m'])+'|\n'
text+='''
## 受控模型差

下表共同历史H3惯性RAC基底，与上面的SP3残差基底不同。模型间位移不叫预测误差；H4−H5同时改变两因素，不作单项归因，也不简单相加预测未运行H6。

|模型对|6h终点(m)|全段最大(m)|全段RMS(m)|终点R/A/C(m)|
|---|---:|---:|---:|---|
'''
for n,s in a['pairs'].items():text+=f"|{n}|{s['terminal_m']:.6f}|{s['max_norm_m']:.6f}|{s['rmse_3d_m']:.6f}|"+' / '.join(f'{x:.6f}' for x in s['terminal_RAC_m'])+'|\n'
text+=f'''
20→40六小时终点5m候选目标：{'PASS' if p4['candidate_5m_endpoint_passed'] else 'NOT MET'}，实际{p4['terminal_m']:.3f}m；仍需报告最大/RMS且不能由两个截断证明40以上收敛。相比旧J2背景密度条件终点差52—65m，两种本次模型差只能作量级参照，不能混用新旧轨迹归因密度。

## 加速度量级和成本

以下均在相同历史H3状态计算，避免混入轨迹位置差：

'''
for k,s in a['acceleration_ranges'].items():text+=f"- {k}：{s['min']:.9e}—{s['max']:.9e}m/s²。\n"
text+='''
|模型|积分墙钟(s)|nfev|接受步数|
|---|---:|---:|---:|
'''
for n,s in a['resources'].items():text+=f"|{n}|{s['elapsed_s']:.6f}|{s['nfev']}|{s['accepted_steps']}|\n"
text+=f'''
H3计时为旧任务实测，不同负载下不作严格加速比。全部新传播共{run['wall_s']:.3f}s、峰RSS{run['peak_RSS_MiB']:.3f}MiB，低于1800s/2GiB。4短例耗时用于带1.5安全系数的预算门禁后才执行2次六小时；无失败重试或额外H6。

## 数值结论的限制

H4/H5短例base/tight均约0.257mm，原2cm门槛通过。独立力公式/位置/40阶参考及176自动测试通过，但本次没有H4/H5六小时tight：**所有六小时状态与重要配对差的完整收敛状态仍为PENDING**。因此图/CSV只展示条件模型差，不能将全部差异认定为已完全分离的物理贡献，也不能把旧H3约5.84cm差直接当新两组误差界。

图results/figures/gravity_third_body_v1_*，CSV results/metrics/gravity_third_body_v1_*；完整配置、预注册、launch、运行及审计experiments/gravity_third_body_v1，NPZ本地data/processed/gravity_third_body_v1。完整差异/RAC/残差/加速度/费用/短收敛曲线均来自实际数据，无平滑或拟合。
'''
(ROOT/'reports/GRAVITY_THIRD_BODY_ORBIT_COMPARISON.md').write_text(text)
plan=f'''# 下一阶段共同动力学模型选择规则

## 本次证据

20→40观察终点差{p4['terminal_m']:.3f}m、最大{p4['max_norm_m']:.3f}m、RMS{p4['rmse_3d_m']:.3f}m；5m候选终点目标{'满足' if p4['candidate_5m_endpoint_passed'] else '未满足'}。20阶+日月相对历史20阶终点差{p5['terminal_m']:.3f}m、最大{p5['max_norm_m']:.3f}m。公式/外部位置/截断数值验证通过，短例收敛通过；六小时完整tight收敛仍待验证，内置星历保留Newtonian几何/GM时标限制。

## 选择规则

1. 不按哪组SP3残差最小选择模型，不调阶数/GM/星历拟合。截断应根据预注册敏感性目标、独立验证、成本及待测密度效应尺度判断。
2. 若20→40仍显著，不得宣称40阶收敛；下一步只设计更高阶离线预算/规范稳定算法与另授权对照，不本次扩80/100。即使差<5m，也只是两级相近，不是全阶收敛证明。
3. 日月差分若达到当前重要位移尺度，后续全部组应一致采用经独立验证的同一日月实现和星历。当前builtin可用于标注限制的探索机制研究；正式冻结还需星历/坐标/GM时标与轨道级误差审查。
4. 40阶+日月组合H6本次未运行，不能当已验证的共同模型。H4/H5全窗收敛补齐、候选组合经另授权验证后，才讨论冻结共同版本。缺少6h收敛证据不能默认视作0误差。
5. 潮汐/时变低阶、SRP、相对论及可能真实推力仍缺；f_thr名义mN不代表实测执行力。不得将剩余残差唯一归因日月或大气。

## 是否进入经验/TIE公平对照

当前可以设计统一引力背景的PROVISIONAL矩阵，但正式物理精度对比条件仍不具备，且本次不执行新阻力传播。未来所有NRLMSIS/TIE组必须共同冻结同GM/R/C/S/截断、日月/其他力、初态、EOP、数值、风与气动；TIE A/B继续独立条件标签，不宣称严格同高度。

当前待取得的具体资料见FORMAL_PARAMETER_EVIDENCE_REQUESTS.md：0601/ACCELE03.25和ORBATT03.25产品定义及q/标志/推进器生成解释、几何/Cd参考面积、NCAR ZG外部登记、预热/高频输出验证。现阶段合成参数或坐标假设不能升格正式参数。计算效率需区分离线场生成、密度查询、积分和端到端成本。

本次任务结束后停止，不自动执行H6/更高阶/阻力矩阵/TIE/AI/长窗。
'''
(ROOT/'docs/COMMON_FORCE_MODEL_DECISION.md').write_text(plan)
print('H4/H5 reports and common-model decision written')
