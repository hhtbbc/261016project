"""Write static force-budget/review from actual archived outputs."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/gravity_truncation_v1';j=json.loads((F/'missing_forces_v2.json').read_text());s=j['force_statistics_m_s2']
text='''# 主要缺失受力预算与实现优先级

## 范围与方法

本次只在历史H1的361个实际状态上离线评估加速度，没有新增含这些力的轨道积分。加速度大并不等于六小时位置效应一定大，方向、周期抵消与共振都重要；不使用a×t²推算轨道误差，不把量级表当真实残差归因。

## 日月位置、时间与地心差分

显式Astropy6.1.7 `solar_system_ephemeris='builtin'`，不自动下载JPL核。其实际源码调用ERFA epv00（Earth/Sun，TDB）和moon98（月球，TT/TDB均可在算法精度内；Astropy使用TDB），取同一瞬时几何位置而非含光行时的apparent位置。月球算法原生GCRS，太阳地心BCRS/ICRS轴向差作为低阶GCRS对齐预算近似，尚未实现精密相对论BCRS/GCRS位置变换。

[Astropy星历说明](https://docs.astropy.org/en/stable/coordinates/solarsystem.html)和本地ERFA文档表明：epv00在1900—2100与DE405比的日心位置RMS/最大差3.7/11.2km；moon98在1950—2100与ELP/MPP02比为6.1/31.7km。这是原算法跨时段测试，不是本窗口实际误差或置信界。2023在适用时段，足以用于初步力学量级；正式传播应另选冻结JPL DE440s等几何核，核实许可/日期覆盖/哈希/时间及参考框架并独立对照，不宣称本次使用DE440位置。

太阳/月球GM取[NASA NAIF gm_de440.tpc](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/gm_de440.tpc)，文件单位km³/s²乘1e9到SI；仅GM来自DE440，不能据此称位置也是DE440。文件与SHA在configs/missing_force_sources.json。地心第三体必须是

`a_B = μ_B [(R_B-r)/|R_B-r|³ - R_B/|R_B|³]`。

实现采用代数等价的稳定差分式避免远距离相减，另与直接式/线性潮汐极限比较，地心r=0时严格为0。绝不能省掉第二项直接使用太阳绝对引力。4项离线数学测试通过，与本次不含第三体的RHS隔离。

## 实际加速度量级（H1沿轨，m/s²）

|项|最小|中位|最大|可信范围|
|---|---:|---:|---:|---|
'''
for key,label,scope in [('sun_third_body_m_s2','太阳差分引力','builtin位置量级预算'),('moon_third_body_m_s2','月球差分引力','builtin位置量级预算'),('combined_third_body_m_s2','日月差分向量和','不等于各模直接相加'),('isotropic_k2_0p3_solid_tide_scale_m_s2','简化固体潮响应','球形/实数k2=0.3，只是量级'),('Schwarzschild_monopole_m_s2','地球Schwarzschild单极项','不是完整IERS相对论模型'),('SRP_scenario_max_m_s2','SRP演示情景上端（含食）','非真实气动/光学参数界'),('delta_C20_1e10_time_axis_scale_m_s2','人为ΔCbar20=1e−10','单位敏感性，非2023系数估值')]:
 v=s[key];text+=f"|{label}|{v['min']:.6e}|{v['median']:.6e}|{v['max']:.6e}|{scope}|\n"
text+=f'''
## SRP、姿态与地球遮影

压强从IAU2015名义太阳光度L_sun/(4πAU²c)计算，1AU约{j['SRP_nominal_pressure_N_m2']:.9e}N/m²，按日距平方缩放。仅声明演示m=400kg、A=0.5—2m²、Cr=1—2；不是Swarm实参、置信区间或物理总上界。实际受力需要随姿态变化的太阳投影面积、表面吸收/漫反射/镜反射及Cr参考面积的一致性，不能从Cd直接得到Cr。

采用球形地球/有限太阳圆盘只分类全照、半影、本影：本例361个一分钟采样为{j['SRP_scenario']['shadow_sample_counts']}；它们是采样点数，不是精确食时长。半影仅给照明因子[0,1]区间，没有伪造连续遮挡系数；本影为0，全照为1。后续须测试有限圆盘重叠、地球椭球/大气边缘与姿态。地球反照/红外辐射压另需辐射与表面模型，本次未给无证据的精确值。

## 地球潮汐、世变、相对论及其他项

[IERS第6章](https://iers-conventions.obspm.fr/content/chapter6/icc6.pdf)把静态场与固体潮、海潮、固体/海洋极潮区分。本文k2=0.3球形二阶潮响应只算数量级，不包含复杂/频率相关Love数、相位、海洋负载及极潮。低阶时变不能从任意“2008年”直接外推：必须核对各系数参考历元、零潮/无潮转换和实际产品，不能将旧静态C20与IERS零潮C20直接相减后称2023误差。

仅另算人为ΔCbar20=1e−10的加速度敏感性，使用已验证随时变化的地固Z方向；不是实际2023变化范围。初版固定轴单位敏感性输出保留在missing_forces.json，最终判断采用missing_forces_v2.json。单极Schwarzschild预算采用`GM/(c²r³)[(4GM/r−v²)r+4(r·v)v]`；没有将其称为包含de Sitter、Lense–Thirring及完整时空缩放的IERS模型。

Swarm推进器：f_thr是名义mN组合字段，实际执行净力未知；dt_thr非零不能直接转为加速度。也不能把f_thr全0当没有推力。本次仍无可信推力上界；待审区间由独立产品记录给出，不依据SP3残差筛选。热辐射反冲/带电效应等若进入更小误差预算还需额外参数，现阶段不编造可忽略证明。

## 优先级与下一步成本

|优先级|项目|依据与实现成本|下一步门禁|
|---|---|---|---|
|P0|静态引力截断|本次H1/H2/H3真实位移与5m候选目标决定；IERS低轨实例的建议远高于20|若12→20仍明显，设计更高阶对照，不自动运行|
|P0|真实推力/质量与机动解释|可能显著但净力未知，资料成本高，优先并行核查|取得0601字段/通道/定标与独立筛选规则|
|P1|日月第三体|实测静态量级约1e−7—1e−6，大于/相当历史演示阻力；几何公式实现成本低|冻结可靠星历、GM时标约定、独立差分验证后另授权传播|
|P1|固体潮/低阶时变|约化量级不能忽略，正式模型成本中等|统一潮汐系统/历元、IERS规范与参考软件比对|
|P2|SRP/地球辐射及相对论|本情景SRP与单极GR约1e−8；SRP真实姿态参数缺失|独立几何/表面/遮影，GR时标与完整参考方案|

这是按当前量级与可用证据排序，不是经过轨道增量实验的误差贡献排名。必须继续保持NRLMSIS/TIE组共同引力、第三体、风及气动条件。所有预算和CSV为离线结果，不等同正式轨道预测精度。
'''
(ROOT/'docs/ORBIT_MISSING_FORCE_BUDGET.md').write_text(text)
old=json.loads((ROOT/'experiments/high_order_gravity_v1/swarm_parameter_audit.json').read_text());audit={'product_definition_0601_confirmed':False,'f_thr_actual_executed_force_confirmed':False,'new_Swarm_downloads':0,'products':[],'official_check':'ESA page still links 2013-10-09 definition; eogateway requested PDF returns HTTP403; no bypass'}
for p in old['products']:
 q=ROOT/p['file'];assert hashlib.sha256(q.read_bytes()).hexdigest()==p['sha256'];audit['products'].append({'file':p['file'],'sha256':p['sha256'],'unchanged':True})
with (F/'swarm_review.json').open('x') as f:json.dump(audit,f,indent=2)
print('Force budget and Swarm provenance review written')
# Reproducible static comparison figure; no propagation performed.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
keys=['sun_third_body_m_s2','moon_third_body_m_s2','isotropic_k2_0p3_solid_tide_scale_m_s2','Schwarzschild_monopole_m_s2','SRP_sunlit_max_m_s2']
labels=['Sun differential','Moon differential','Solid tide (k2=0.3 scale)','Earth monopole GR','SRP scenario sunlit upper']
fig,ax=plt.subplots(figsize=(10,4));ax.bar(labels,[s[k]['max'] for k in keys]);ax.set_yscale('log');ax.set(ylabel='Maximum acceleration magnitude (m/s²)',title='OFFLINE H1 force budget; not trajectory displacement or verified Swarm forces');ax.tick_params(axis='x',labelsize=8,rotation=10);fig.tight_layout();plot=ROOT/'results/figures/gravity_truncation_v1_missing_force_scales.png'
if plot.exists():raise FileExistsError(plot)
fig.savefig(plot,dpi=150);plt.close(fig)
