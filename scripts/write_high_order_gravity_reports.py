"""Reports from audited G1/G2 results and static force-parameter review."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];F=R/'experiments/high_order_gravity_v1'
a=json.loads((F/'analysis.json').read_text());s=json.loads((F/'run_summary.json').read_text());v=json.loads((R/'logs/high_order_gravity_independent_validation.json').read_text());c=json.loads((F/'configuration.json').read_text());sw=json.loads((F/'swarm_parameter_audit.json').read_text());params=c['higher_order_parameters'];assert v['passed'] and s['convergence']['passed']
def write(p,t):
 q=R/p
 if q.exists():raise FileExistsError(q)
 q.write_text(t)
def append(p,t):
 q=R/p;q.write_text(q.read_text()+t)
res='\n'.join(f"|{m}|"+'|'.join(f"{a['residuals'][m]['hours_1_3_6'][str(h)]['norm_m']:.6f}" for h in [1,3,6])+f"|{a['residuals'][m]['rmse_3d_m']:.6f}|" for m in ['G0','G1','G2'])
rac='\n'.join(f"|{m}|"+' / '.join(f'{x:.6f}' for x in a['residuals'][m]['rac_rmse_m'])+'|'+' / '.join(f'{x:.6f}' for x in a['residuals'][m]['terminal_RAC_m'])+'|' for m in ['G0','G1','G2'])
pert='\n'.join(f"|{k}|{x['terminal_m']:.6f}|{x['max_norm_m']:.6f}|{x['rmse_3d_m']:.6f}|" for k,x in a['perturbations'].items())
acc='\n'.join(f"|{k}|{x['min_m_s2']:.9e}|{x['max_m_s2']:.9e}|" for k,x in a['acceleration'].items())
num='\n'.join(f"|J{n}|{x['independent_spherical_max_relative_error']:.4e}|{x['complex_gradient_relative_error']:.4e}|"+' / '.join(f"{d['relative_error']:.4e}" for d in x['finite_difference'])+'|' for n,x in v['terms'].items())
cost='\n'.join(f"|{m}|{x['integration']['elapsed_s']:.6f}|{x['integration']['nfev']}|{x['integration']['accepted_steps']}|{x['peak_RSS_MiB']:.3f}|" for m,x in a['resources'].items())
write('reports/HIGH_ORDER_GRAVITY_VALIDATION.md',f'''# J3/J4独立数值验证

## 模型定义与范围

采用configs/higher_order_gravity.json冻结的PROJECT_NOMINAL_J2_PLUS_EGM2008_ZONAL34。保留原μ/R/J2；GFZ文件C30/C40先非归一化再按μR^n重表达，不直接混用归一化系数。不是完整EGM2008或完整IERS2023模型，也没有校准SP3。来源、势函数与预注册门槛见docs/HIGH_ORDER_GRAVITY_DESIGN.md。

当前项目非归一化J3={params['terms']['3']['Jn_project']:.17e}，J4={params['terms']['4']['Jn_project']:.17e}。源Cbar30={params['terms']['3']['Cbar_n0']:.17e}、Cbar40={params['terms']['4']['Cbar_n0']:.17e}；原始部分文件SHA {params['source_sha256']}，本次仅16384字节前缀，不声称完整EGM文件已下载。

## 测试与独立公式

新增9项测试，全套142项通过。包括极区/赤道/中纬、J3偶加速度与奇势/J4奇加速度与偶势、r^−5/r^−6衰减、旋转协变、关闭项恢复旧J2的逐元素状态、叠加、非法参数、固定轴能量/轴向角动量和数值收敛。

独立球坐标参考使用[GFZ STR09/02 §4.1](https://icgem.gfz-potsdam.de/docs/str-0902.pdf)正引力势及[ IERS式6.1—6.3](https://iers-conventions.obspm.fr/content/chapter6/icc6.pdf)归一化关系，用源μ/R/Cbar、scipy Legendre及径向/纬向导数转Cartesian；不调用生产加速度公式。生产模型用显式向量多项式。100个固定随机点逐项比较，另做复步长负梯度及中心差分，不以同一个函数自比冒充独立验证。这是独立数学路径，不是另一完整轨道软件或观测精度验证。

|项|球坐标参考最大相对差|复步长负梯度相对差|差分h=10000 / 1000 / 100m相对差|
|---|---:|---:|---|
{num}

固定门槛为独立/复步长相对2e−12、绝对1e−18m/s²；差分减步需显示二阶收敛，100m相对差<2e−7。全部通过，未放宽阈值。归档的poliastro v0.17 J3参考源也明确自称未完全验证，因此不作为唯一权威测试依据，没有安装/执行该下载源码。

## 固定轴保守合成验证

只用合成初态[6850000,0,0]m、[0,5400,5400]m/s，6000s；不是额外Swarm实验。能量包括中心、J2、J3、J4完整势，轴向角动量守恒，不要求角动量矢量不变。

base能量相对漂移{v['fixed_axis_conservation']['base']['specific_energy_max_relative_drift']:.6e}，轴向角动量{v['fixed_axis_conservation']['base']['axial_angular_momentum_max_relative_drift']:.6e}；tight分别{v['fixed_axis_conservation']['tight']['specific_energy_max_relative_drift']:.6e}、{v['fixed_axis_conservation']['tight']['axial_angular_momentum_max_relative_drift']:.6e}。两解最大位置差{v['fixed_axis_state_difference_max_m']:.9f}m。严容差收敛；不能把固定轴守恒判据强加到真实时变轴模型。

## 六小时G2收敛与保护

G2 base/tight最大位置差{s['convergence']['G2_state_max_m']:.9f}m，小于预注册0.5m；G2−G0配对变化{s['convergence']['G2_G0_pair_change_max_m']:.9f}m，小于max(5mm,最大扰动1%)={s['convergence']['pair_threshold_m']:.9f}m。复用已保存G0 tight，未重跑G0。G1没有另加tight，不能声称逐组完整数值误差证明。配对误差中的抵消也不等于单轨绝对准确。

174项保护文件前后SHA不变，含D0—D5和原基础模型；初态小端float64 SHA `{c['initial_sha256_le_float64']}`与既有D5相同。原RK45、J2、时间/坐标模块未改。原始SP3逐SHA与HDR锚点匹配，冻结EOP/闰秒沿用。没有NaN/Inf、拒绝或异常积分状态。

环境复用.venv310、numpy/scipy/Astropy。仅为读取公开ESA PDF新增项目内pypdf6.21.1和pycryptodome4.1.0，原numpy等数值包未升级；PDF原有AES格式最初缺后端，安装官方PyPI wheel后用普通空口令阅读路径解析，没有破解或尝试访问密码。下载SHA/依赖检查在logs/high_order_pdf_*，环境锁configs/requirements-gravity-20261020.lock.txt。原PDF/全文提取不入Git，第三方模型源码不改。

复现：source scripts/activate_orbit.sh；PYTHONPATH=src python -m unittest discover -s tests -v；python scripts/validate_high_order_gravity.py；python scripts/run_high_order_gravity_comparison.py --run-tag high_order_gravity_v1（静态）；同命令--execute。已有标签/验证输出拒绝覆盖；复现需显式使用独立产物位置，不重放本次授权。
''')
write('reports/HIGH_ORDER_GRAVITY_ORBIT_COMPARISON.md',f'''# 六小时J3/J4无阻力受控比较

PROVISIONAL / HINDCAST / NO_DRAG。只执行G1、G2、G2-tight三次六小时真实初态传播，G0读取原D0，未使用气动参数，未新增阻力、TIE或AI实验。

## 设置

Swarm-A，2023-03-21 00:00:02—06:00:02 UTC，共361个60秒输出。单历元SP3原生P/V完整ITRS→GCRS初始化，随后自由传播；未来SP3只用于残差，不拟合初态/系数。base rtol1e−10、位置atol1e−3m/速度1e−6m/s、max_step30s；tight为1e−12、1e−5m/1e−8m/s、15s。相同μ/名义J2、时变轴、冻结EOP/闰秒、坐标和指标接口。新增Jn的源归一化及μR重表达见设计文档，不能将本模型称为完整EGM2008。

## SP3位置残差

SP3为有自身误差的后处理参考；这里不是独立观测真值误差。RAC基于同历元SP3的GCRS位置/速度，R向外、C沿r×v、A=C×R，残差为模型减参考。

|模型|1h残差m|3h残差m|6h终点残差m|全时段三维RMSE m|
|---|---:|---:|---:|---:|
{res}

|模型|全时段R / A / C RMSE m|终点R / A / C残差m|
|---|---|---|
{rac}

G1相对G0：终点减少636.945m（59.746%），RMSE减少136.883m（24.648%）。改善主要在沿轨：A RMSE487.816→315.094m；R RMSE72.180→103.401m反而增大，C约255m基本未变。因此不能说所有方向都改善。

G2相对G0：终点减少231.628m（21.727%），但全时段RMSE增加176.575m（31.795%）。相对G1终点又增大405.317m。G2沿轨残差由G0终点−998.697m变为+734.745m，存在过补偿现象；全段A RMSE680.524m，R105.957m，C247.757m。只挑终点会误判整体表现。

现有公式/符号/单位/归一化/轴方向已经独立检查，数值收敛变化远小于这些残差。部分项之间与未建模项的抵消、非带谐引力、初态/参考限制及缺失非引力项可能影响表现；本次不能唯一归因，也不为降低残差改初态或系数。J4真实存在不意味着在不完整力模型里加入它后每段残差必降。

## 新增引力扰动及历史密度尺度

位移差使用共同G0惯性RAC基底，与上面的SP3残差RAC不同。

|配对|6h终点位移m|全段最大位移m|位移RMS m|
|---|---:|---:|---:|
{pert}

历史J2条件下D5−D0终点174.662m；经验/TIE候选条件终点差52.202—65.074m。本次单加J3、再加J4的终点影响各约0.8—0.9km，合计约1.736km，大于此前几十米密度模型差。这只说明未建模引力可能淹没当前密度差异，不能把新引力轨迹与旧密度轨迹差直接归因于大气。

## 加速度与成本

下表各项均在同一G2轨迹状态上评估：

|项|最小加速度m/s²|最大加速度m/s²|
|---|---:|---:|
{acc}

地心半径6850km赤道合成点：中心约8.494868m/s²，J2约1.196015e−2，J3约2.604904e−5（向南），J4约1.939360e−5（径向内）。不是大气高度基准转换。J3/J4瞬时值比先前演示阻力1.8—2.9e−7m/s²大，但长期轨道效果还取决于方向、周期抵消与相位，不能直接乘时间平方当预测值。

|组|积分墙钟s|nfev|接受步数|运行进程累计峰RSS MiB|
|---|---:|---:|---:|---:|
{cost}

G0为旧测量，其他为本次，不据不同运行的微小计时差宣称严格加速比。总新传播阶段{s['wall_s']:.3f}s，离线分析{a['analysis_wall_s']:.3f}s；没有GPU、MPI或密度查询。G2数值状态差0.058411m、配对变化1.58045e−5m，见独立验证报告。174项保护SHA不变。

## 交付与下一步门禁

配置、launch_once、保护SHA、运行/分析JSON在experiments/high_order_gravity_v1；原NPZ在data/processed/high_order_gravity_v1不上传；状态、逐时刻残差/RAC、模型差、共同状态加速度、收敛及资源CSV在results/metrics/high_order_gravity_v1_*。六图在results/figures/high_order_gravity_v1_*。所有原D0—D5产物保留。

未来应核验包含非带谐项的统一球谐模型，再让所有密度组共同升级；本次只提交方案，不自动新阻力矩阵或更长传播。真实气动/机动、TIE高度、预热和时间采样门禁均未解除。
''')
mass='\n'.join(f"|{Path(x['file']).name.split('202303')[1][:2]}日|{x['mass_min_kg']:.3f}—{x['mass_max_kg']:.3f}|{x['samples']}|{x['thruster_on_records']}|" for x in sw['products'] if 'mass_min_kg' in x)
write('docs/SWARM_FORMAL_FORCE_PARAMETERS.md',f'''# Swarm-A正式受力参数静态审查

本次只核查既有2023年3月21—23日SC_ADYN/STRAATT及官方资料，没有将这些值用于本次无阻力传播，没有反演Cd或弹道系数。

## 新取得的官方证据与版本边界

从[ESA公开文档页](https://www.esa.int/Applications/Observing_the_Earth/FutureEO/Swarm/Documents_publications)取得其直接链接的SW-RS-DSC-SY-0007 **Issue5.13，2013-10-09**（81页），PDF SHA `{sw['official_document']['sha256']}`。正常阅读解析成功；原文带项目使用标识，PDF与全文提取只保留本地，不上传。本次报告仅概括必要字段，不复制整表。

当前实物均File_Version0601，SC_ADYN由ACCELE/03.25在2025-07-23重处理，STRAATT由ORBATT/03.25在2025-07-08重处理；Ref_Doc只给编号，未给issue。因此2013版不能自动视为0601的完全适用字典。详细CDF字段属性/6份SHA和505个待审时间段见experiments/high_order_gravity_v1/swarm_parameter_audit.json及轻量区间CSV。

## 参数核查表

|项目|当前证据|正式可用性/仍缺什么|
|---|---|---|
|质量m_SC|实物CDF明确kg和实际质量，三日范围见下表|记录值已核实；sigma未提供，日内范围不是不确定度；需质量标志规则|
|几何/面积|CDF A_head/right/left/down为orbit frame截面向量，单位m²、每点3分量；旧文§4.4.3/§6.17也有面积法向说明|缺ORB基底、面元投影/遮挡与Cd参考面积配套，不得把向量范数或外包络矩形当有效迎风面积|
|姿态q|旧文§6.14详细表与CDF均指ITRF←S/C；但概览表4-13文字反向|方向有相互支持的详细记录证据，同时存在文档内部矛盾；分量顺序/矩阵约定仍缺，不能直接用来算面积|
|姿态质量|旧表6-1：0为名义，255为不足样本；其余包含星敏CHU缺测等类别|不能把Flags_q泛化为普通位掩码，也不能仅凭四元数范数判定好；需确认0601延续定义|
|同步质量|旧附录D给出GPS同步与其他状态，0为GPS同步|0601需版本确认；时间同步状态不等于全部物理质量|
|平台标志|同一旧PDF中，MAG表6-1和ACC表6-5对Flags_Platform=16解释不同|不能跨产品套位义；需SC_xDYN当前版本字典，不能直接将本CDF的16断言为某类事件|
|推进器|CDF dt_thr为s、12通道；f_thr是组合名义力向量，单位**mN**；thr_set为活动支路标志|不能把mN当N；f_thr全0不能排除推力。仍缺支路/方向/脉冲/质量与产品生成规则|
|机动码|旧§5的机动信息指向AD05（Level0文档），没有给本次code4映射|code4仅列待审；不能视为已知净推轨或简单删段|
|Cd/弹道参数|既有CDF及本次资料未给出和当前几何/参考面积匹配的可靠Cd/β|Cd、有效面积及标准不确定度仍null；2.2/1m²只是旧演示假设，BSTAR不是本力模可直接采用的物理β|

以上旧文摘要仅作为版本线索；完整适用性尚未确认，不在本次编写“正式有效”质量筛选器。

## 三日质量和可能推力区间

|日期（2023年3月）|m_SC范围kg|记录数|dt_thr>0记录数|
|---|---:|---:|---:|
{mass}

这些为2025重处理后的历史资料，不能宣称2023当时已可获得；也不能用质量范围充当sigma。各日还保存SyncStatus、Flags_q/Platform及thr_set值分布。三日姿态非有限行分别0/80/10；必须拒绝非有限四元数，不能插值穿越坏段，但“有限”并不等于姿态质量已好。

目标六小时窗口有22条dt_thr至少一通道非零，STRAATT Maneuver_Id均0；不能因此称无推力。更晚的code4段以及所有非零开启记录、平台16区间、NaN段都输出原始UTC起末采样和样本数，**这些是记录连续段，不是已认定的独立机动次数或净Δv**。没有根据SP3残差选择剔除区间。

当前能做的是基于独立证据预先列待审段；正式排除/建模应取得0601适用的产品定义、AD05机动码、辅助机动文件及推进器几何/定标。官方网页可获取旧版不等于已解决此前新版访问阻碍；没有猜测或绕过认证。

## 是否已有独立可靠弹道参数

尚无可直接采用的Cd*A/m。质量记录本身不足，姿态方向说明不等于几何投影完成。DNSAPOD与SP3共享POD/气动信息，不可用未来密度或轨道反推参数后再评价同窗口。正式路线应先取得几何、气体表面相互作用及参考面积一致的气动模型，冻结验证前规则；如校准必须另设t0前窗口并冻结，不能在本窗口拟合。
''')
write('docs/UPDATED_GRAVITY_DENSITY_PROTOCOL.md','''# 更新引力后的后续密度实验门禁（仅设计，不执行）

1. 当前G1/G2只验证J3/J4增量，G2全段RMSE恶化说明不能把它当已验收最佳引力模型。下一步优先采用来源统一、归一化/潮汐/历元/μR明确的球谐场，包含C22/S22等非带谐项。先独立力函数与坐标旋转验证，再设计逐阶截断收敛；不认为只继续增加J5就足够。
2. 可以设计8×8、20×20等原型截断对照，再依据目标精度提高并检验收敛；这些只是候选测试级别，不是已证明适合Swarm的最终阶数。IERS第6章表6.1的Starlette示例也不能直接当Swarm的保证。完整场需正确的地固经度旋转，时变轴 alone只适用于m=0，不能照搬本次带谐简化。
3. 同时评估日月第三体、SRP/阴影及可能推力。先用有来源参数给出量级，不把缺失项的残差一股脑归因密度；坐标时/尺度与潮汐/世变也须按目标精度统一。
4. 获得可靠质量/几何/Cd参考面积、姿态顺序/方向和质量筛选、机动/推力处理后，冻结版本、初态和验证区间。当前0601字段字典、Cd/面积尚未闭合，不能宣布正式实验就绪。
5. TIE原生ZG外部登记仍未闭合，S3/S7不证明初态无关，10分钟场没有独立高频精度界。需取得相应证据；否则只允许另授权、清楚标记的探索性映射与参数实验。
6. 若未来升级引力，必须重新生成统一新重力的无阻力、NRLMSIS、S3/A、S7/A、S3/B、S7/B等对照；全部保持同新引力、同初态、气动/风、积分和时间条件。不能拿旧J2的TIE轨迹与新J3/J4的经验轨迹作密度归因。旧D0—D5只作历史留档/量级参考。
7. SGP4仍是独立历史TLE初始化基准，不参加同SP3初态的积分算法排名。每组同时报起始偏差、RAC/全段/分时段残差、查询有效性、数值收敛及场生成/在线/全流程成本。

本次没有授权上述后续传播或密度矩阵；完成本次最多3组无阻力实验后停止。
''')
update=f'''\n\n## 2026-10-20最新：J3/J4无阻力扩展及正式参数审查完成\n\n在不改原μ/R/J2/基础代码的前提下，核实GFZ EGM2008完全归一化C30/C40并按μR^n重表达为项目Jn，定义名义J2+静态J3/J4受控势，非完整EGM/IERS模型。9项新测试/全142通过，独立球坐标与势梯度、固定轴能量/轴向角动量及关闭恢复检查通过。\n\n只新增G1、G2、G2-tight三次6h无阻力，G0读取D0；G1终点429.142m、全段RMSE418.474m；G2终点834.459m、RMSE731.931m，对比G0终点1066.087m/RMSE555.356m。G2终点改善但全段RMSE恶化31.795%，不挑点下结论。J3/J4分别引起终点923.004/815.786m增量，合计1735.560m，远大于旧条件密度差52—65m；不能把新旧引力差归因密度。G2 base/tight最大差0.058411m，配对变化1.58045e−5m；174项历史保护SHA未变。\n\n新取得ESA官方公开链接5.13版2013产品定义并只存本地；识别q详细表/概览方向矛盾、Flags_Platform跨产品含义差异及f_thr单位mN。0601现行适用性、四元数顺序/几何/Cd/推力仍未闭合；未启用真实参数。为PDF阅读仅新增项目内pypdf/pycryptodome，无系统改动/原数值包升级。资料详见SWARM_FORMAL_FORCE_PARAMETERS.md。\n\n入口：reports/HIGH_ORDER_GRAVITY_VALIDATION.md、HIGH_ORDER_GRAVITY_ORBIT_COMPARISON.md；docs/HIGH_ORDER_GRAVITY_DESIGN.md及UPDATED_GRAVITY_DENSITY_PROTOCOL.md，配置/审计experiments/high_order_gravity_v1，真实六图/CSV在results。原D0—D5、TIE场及正式坐标门禁不改，无新阻力矩阵/AI/48h扩展。下一步需新授权统一球谐（含非带谐）与真实气动/推力门禁研究，所有未来密度组须共同升级引力。本次完成后停止，Git真实SHA以最终核验为准。\n'''
append('STATUS.md',update);append('WORKLOG.md',update+'''\n关键命令：source scripts/activate_orbit.sh；PYTHONPATH=src python -m unittest discover -s tests -p test_higher_order_gravity.py -v；全套discover；python scripts/validate_high_order_gravity.py（仅合成验证）；python scripts/run_high_order_gravity_comparison.py --run-tag high_order_gravity_v1（静态）；同命令--execute（3次已完成）；python scripts/analyze_high_order_gravity.py；python scripts/audit_swarm_formal_force_parameters.py；python scripts/write_high_order_gravity_reports.py。只读复用6份CDF，生成505个记录待审连续段，不把它们叫独立机动。原PDF、系数部分文件及wheel留data/raw，NetCDF/环境不入库。起初系数解析未支持Fortran小写d指数，静态阶段修正无模型启动；PDF首次读取因缺AES后端失败，项目内安装校验wheel后正常解析，无密码尝试或第三方源码修改。\n''')
for name in ['docs/PROJECT_PLAN.md','docs/UPDATED_RESEARCH_PLAN.md']:
 q=R/name;q.write_text('# 当前接续：J3/J4受控审查完成\n'+update+'\n---\n以下为保留的历史计划；当前状态以上节及STATUS最后记录为准。\n\n'+q.read_text())
append('docs/FORMAL_ORBIT_VALIDATION_GAPS.md','''\n\n## J3/J4任务后的新增证据与限制\n\n名义J2+重表达EGM2008 J3/J4已独立验证并完成3次无阻力6h。G1部分改善，G2终点较G0降低但全时段RMSE升高，不能选G1当“最佳真实模型”或按SP3拟合系数。下一步应统一完整球谐来源和非带谐项，检查潮汐/世变、坐标时尺度及第三体/SRP/推力。未来所有密度组一并升级，禁止旧TIE-J2/新MSIS-J3J4归因对比。\n\n公开ESA Issue5.13取得并解析，§6.14详细q方向与当前CDF相符，但其概览表反向；标量顺序仍未落实。Flags_Platform在MAG/ACC表中同值不同义，不能给SC_xDYN0601套用旧表；f_thr为mN。现行版本映射/AD05机动码、Cd与几何面积仍缺。TIE外部高度及初态/时间分辨率缺口不变。详见SWARM_FORMAL_FORCE_PARAMETERS及UPDATED_GRAVITY_DENSITY_PROTOCOL。\n''')
append('AGENTS.md','''\n\n## J3/J4完成后的最新门禁\n已单独授权完成high_order_gravity_v1三次无阻力6h（G1、G2、G2-tight），G0读取旧D0。新势为保留名义J2+按μR^n重表达EGM2008 J3/J4，不能称完整标准球谐。G2终点改善但全段RMSE恶化，不能按参考残差拟合或挑点宣布精度提升。未来升级引力必须所有密度组共同更新，不混旧TIE-J2与新经验组归因。ESA旧5.13 q/平台标志有产品与概览/详细定义差异，0601适用性仍需确认；f_thr单位mN，Cd/有效面积未知。新阻力矩阵、48h、TIE/AI运行均须新授权。本次142项测试，真实参数/高度/完整受力门禁不因通过数值测试而解除。\n''')
append('README.md','''\n\n## J3/J4受控无阻力比较\n已完成原J2基线上的J3/J4增量验证；J3组部分残差下降，J3+J4组终点下降但全段RMSE增大，不能视作完整引力或密度精度结论。[运行比较](reports/HIGH_ORDER_GRAVITY_ORBIT_COMPARISON.md)、[独立验证](reports/HIGH_ORDER_GRAVITY_VALIDATION.md)、[真实参数审查](docs/SWARM_FORMAL_FORCE_PARAMETERS.md)。旧D0—D5保留，后续密度组须统一升级引力。\n''')
print('Reports written; progress updated')
