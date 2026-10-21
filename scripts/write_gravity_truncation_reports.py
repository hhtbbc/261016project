"""Reports and next-stage decisions based solely on saved actual results."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/gravity_truncation_v1';a=json.loads((F/'analysis.json').read_text());v=json.loads((F/'validation.json').read_text());r=a['run'];pair=a['pairs']['H3_H2'];source=v['source']
text=f'''# 球谐引力截断独立验证

## 源数据与实现

使用GFZ ICGEM同一EGM2008源，仅读{source['bytes_read']}字节，服务器完整Content-Length为252140870字节但没有读取完整文件。SHA256 `{source['sha256']}`，前16384字节逐位匹配旧前缀。所有n≤20/m≤n完整，n=1明确地心零项，20阶共231对C/S；8/12/20系数和GM398600441500000、R6378136.3、fully_normalized/no CS/tide_free完全相同。公开低阶副本configs/egm2008_20x20.json，来源URL/响应/SHA在configs/egm2008_degree20_source.json。

独立扩展模块gravity_truncation.py只扩展初始化，继承原Cartesian实心球谐/梯度，原8×8/框架/RK45源文件保持原样。阶乘/中间多项式在本次20阶和测试位置有限；不声称可以未经验证推广到任意高阶。完整地固Q旋转、包含中心项、不叠J2、无旋转系虚拟力。全部361个历史H1状态上，新8阶GCRS加速度与旧实现逐位相同，另直接势/力比较通过，未重新传播H1。

## SHTOOLS独立Fortran参考

继续使用已冻结pyshtools4.14.1 Fortran扩展和GM/R/C/S，omega=0；原binary SHA复核。100个随机点/级，覆盖约200km至5622km径向高度范围，另赤道/近极/经度接缝测试。纬度为地心球坐标，r为地心半径，不是WGS84高度或TIE ZG。极点无经度除零；SHTOOLS本身不支持精确极点导数，外部仅比较±89.9°，生产精确极点通过有限性/近邻连续性测试。

|阶/次|最大向量绝对差(m/s²)|最大相对差|100个构造点平均/P95纯场耗时(ms)|
|---|---:|---:|---|
'''
for n,s in v['degrees'].items():text+=f"|{n}×{n}|{s['max_absolute_difference_m_s2']:.8e}|{s['max_relative_difference']:.8e}|{s['mean_pure_field_ms']:.3f} / {s['P95_pure_field_ms']:.3f}|\n"
text+='''
预注册逐分量rtol/atol=2e−12/2e−12m/s²及向量相对门槛2e−12未放宽。中心差分势负梯度10km/1km/100m二阶收敛：

|阶|三档相对差|
|---|---|
'''
for n,s in v['degrees'].items():text+=f"|{n}|"+' / '.join(f'{x:.8e}' for x in s['gradient_relative_errors_10km_1km_100m'])+'|\n'
text+=f'''
100m门槛2e−8保持。8项新增引力测试全部通过，传播前全159项通过；离线受力辅助再增4项，最终全163项通过（logs/gravity_truncation_final_tests.log）。没有改变原151测试门槛。外部数值验证是指定截断势的实现检查，不是轨道物理精度验证。

## 资源与积分门禁

唯一10分钟H3预检实测4.214s/146nfev；依据每次RHS耗时及历史nfev并乘1.5安全系数，预计剩余751.451s，小于1795.738s余量后才启动H2/H3/tight。无失败重试、无H1重复积分。新传播累计{r['wall_s']:.3f}s，峰RSS{r['peak_RSS_MiB']:.3f}MiB，小于1800s/2GiB，GPU未用。

H3 base/tight最大位置差{r['convergence_max_m']:.9f}m，低于0.5m预注册门槛；共同初态/输出网格一致。H2本次没有tight，不声称H3−H2配对差值已经有两端独立tight证明；当前单轨数值误差约厘米，应与实际截断差一起判断。

201项历史保护哈希不变；原H1/G0—G2/D0—D5/基础源码不改。新原始NPZ/模型前缀和既有二进制留本地，公开配置、CSV、图、测试与JSON。命令：source scripts/activate_orbit.sh；python scripts/prepare_gravity_degree20.py；PYTHONPATH=src python -m unittest discover -s tests -v；python scripts/validate_gravity_truncation.py；python scripts/run_gravity_truncation.py（静态）及--execute（本次标签已封存，拒绝覆盖/重复）；python scripts/analyze_gravity_truncation.py；python scripts/estimate_missing_force_budget.py（仅离线，最终v2）；python scripts/write_missing_force_budget.py；python scripts/write_gravity_truncation_reports.py。已有输出x模式不可重放；复现需先设计独立run-tag/位置并获得对应传播授权。
'''
(ROOT/'reports/GRAVITY_TRUNCATION_VALIDATION.md').write_text(text)
text='''# 六小时引力截断敏感性比较

PROVISIONAL / HINDCAST / NO_DRAG

## 统一条件

Swarm-A，2023-03-21 00:00:02—06:00:02 UTC，同一冻结单历元SP3完整位置/速度初始化，GCRS积分；相同EGM2008源GM/R、潮汐系统及低阶系数。H1读取旧8×8，H2为12×12、H3为20×20，仅改变截断阶次。没有阻力、日月第三体、SRP等。相同冻结EOP/闰秒、现有完整ITRS框架转换、RK45 base及tight数值配置、361个60s输出；未来SP3仅作诊断，不拟合或筛选系数。

## SP3残差

SP3为后处理参考，并非绝对真值。残差模型减参考，R向外、C沿参考r×v、A=C×R。

|模型|1h(m)|3h(m)|6h终点(m)|全段三维RMSE(m)|R/A/C RMSE(m)|
|---|---:|---:|---:|---:|---|
'''
for n,s in a['residuals'].items():
 h=s['hours_1_3_6_m'];text+=f"|{n}|{h[0]:.6f}|{h[1]:.6f}|{s['terminal_m']:.6f}|{s['rmse_3d_m']:.6f}|"+' / '.join(f'{x:.6f}' for x in s['rac_rmse_m'])+'|\n'
text+='''
不能依据哪个模型SP3残差最小来调阶/调系数、宣布物理最准确；本实验主要判断截断引入的轨道变化。

## 模型之间的位置差

下表模型差在共同H1惯性RAC基底计算，与上面SP3残差的基底不同。

|模型对|终点(m)|全段最大(m)|全段RMS(m)|终点R/A/C(m)|
|---|---:|---:|---:|---|
'''
for n,s in a['pairs'].items():text+=f"|{n}|{s['terminal_m']:.6f}|{s['max_norm_m']:.6f}|{s['rmse_3d_m']:.6f}|"+' / '.join(f'{x:.6f}' for x in s['terminal_RAC_m'])+'|\n'
text+=f'''
预注册12→20六小时终点<5m候选目标：**{'PASS' if pair['endpoint_goal_passed'] else 'NOT MET'}**；全段最大<5m候选目标：**{'PASS' if pair['whole_path_goal_passed'] else 'NOT MET'}**。实际终点{pair['terminal_m']:.3f}m、最大{pair['max_norm_m']:.3f}m、RMS{pair['rmse_3d_m']:.3f}m，均按原定义报告，无事后放宽。

历史不同密度演示差52—65m来自旧J2背景，仅为尺度参照，不是本次共同引力下的新密度实验。当前12→20差与该尺度的关系可由表直接判断；即使差小于5m，也只能说明这两个截断在本窗口相近，不能证明20→更高阶已收敛。IERS2018第6章表6.1低轨7331km半径示例给90阶、20阶示例为LAGEOS，不支持直接称20阶足够Swarm。后续只设计更高阶敏感性/第三体受控验证，本次不自动运行。

## 加速度与计算成本

所有截断在相同H1轨迹状态上计算加速度，避免混入轨迹位置变化：

'''
for k,s in a['acceleration_ranges'].items():text+=f"- {k}：{s['min']:.8e}—{s['max']:.8e}m/s²。\n"
text+='''
|组|积分墙钟(s)|nfev|接受步数|
|---|---:|---:|---:|
'''
for n,s in a['resources'].items():text+=f"|{n}|{s['elapsed_s']:.6f}|{s['nfev']}|{s['accepted_steps']}|\n"
text+=f'''
H1计时为历史实测，不同机器负载下不能解释为严格加速比；纯场微基准独立列于验证报告，在线积分还包括完整框架转换与资源监督。H3 base/tight最大位置差{r['convergence_max_m']:.9f}m，较实际截断差的尺度见表；H2未另运行tight，配对收敛限制保留。

本次新模型启动恰好4次：H3 600s预检、H2/H3各21600s、H3tight21600s。传播流程{r['wall_s']:.3f}s、峰RSS{r['peak_RSS_MiB']:.3f}MiB；201项保护哈希不变。没有新的H1/阻力/TIE/AI/24h或48h传播。

真实曲线results/figures/gravity_truncation_v1_*，逐点CSV results/metrics/gravity_truncation_v1_*，配置/预注册/launch_once/验证/预算/审计experiments/gravity_truncation_v1，原NPZ仅本地data/processed/gravity_truncation_v1。
'''
(ROOT/'reports/GRAVITY_TRUNCATION_ORBIT_COMPARISON.md').write_text(text)
plan=f'''# 下一阶段共同动力学与密度对比门禁

## 本次决策依据

同源12→20终点差{pair['terminal_m']:.3f}m、最大{pair['max_norm_m']:.3f}m、RMS{pair['rmse_3d_m']:.3f}m；5m终点候选目标{'已满足' if pair['endpoint_goal_passed'] else '未满足'}。20阶以上尚未测试，不能声明静态引力已充分收敛。独立加速度验证/163测试/积分收敛通过是工程和数值证据，不等同精密受力完备。

## 推荐的下一项实际实验（仅设计，不执行）

先围绕同一GM/R和系数体系设计更高阶截断对照及日月第三体门禁。若12→20仍明显，应在资源核查后选择预先声明的更高阶候选，不按SP3最小值选择截断；优先形成相邻高阶差<5m且全段最大/RMS足够小的证据，仍不能单凭相邻两组绝对证明极限。可先用更高阶力在历史轨迹的离线加速度预算，再申请有限无阻力传播。不要未经验证将现有未归一化中间量递推直接提升到90阶。

日月差分加速度已显示值得优先加入，下一步先冻结JPL几何星历/GM/时标和GCRS转换，用可靠参考检查地心减项、历元与边界，再在统一引力上开展另授权的无阻力增量。固体潮/低阶世变/潮汐系统并行做规范审查；SRP/遮影需要实际姿态/几何/反射参数。当前本次离线builtin位置不是正式JPL星历精度验证。

## 后续密度矩阵冻结表

|项目|全部组共同要求|
|---|---|
|初态|同SP3单历元完整P/V、相同GCRS/时标与EOP，不用未来SP3拟合|
|引力|同一已验证阶次/GM/R/C/S/潮汐体系及第三体/其他受力版本|
|气动|统一质量、面积、Cd及参考面积定义，真实参数或明确演示标签|
|风|相同共转/风假设；不能TIE用风而NRL零风后归因密度|
|积分|同RK45容差、maxstep、输出网格及失效门禁|
|密度|只改变NRLMSIS或TIE来源；A/B映射条件不得伪装相同正式高度|
|评价|同SP3参考/时间/坐标/RAC，SGP4因初态不同单独报告|
|成本|分别记录离线场生成、在线查询、积分和端到端；共享场不重复计费|

正式Swarm密度精度对比仍缺：Cd/投影面积/气体表面作用、姿态分量和质量标志的0601解释、推力通道/净执行力、TIE ZG外部登记、预热/初态与高频场验证；日月/潮汐和截断也未完全受控。暂不进入正式精度排名。可以设计明确合成参数/高度假设的探索矩阵，但需单独授权，并且所有组共同更新动力学，不混旧D0—D5归因。

本次不启动任何下一阶段实验；阶段一仍聚焦可信轨道与效率，FourCastDEN属于第二阶段。
'''
(ROOT/'docs/NEXT_DENSITY_ORBIT_EXPERIMENT.md').write_text(plan)
print('Three actual-result reports/designs written')
