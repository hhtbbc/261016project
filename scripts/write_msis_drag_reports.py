"""Generate documentation only from a gated completed D5 experiment."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];F=R/'experiments/msis_drag_orbit_v1'
a=json.loads((F/'analysis.json').read_text());s=json.loads((F/'run_summary.json').read_text());c=json.loads((F/'configuration.json').read_text());p=json.loads((F/'precheck.json').read_text())
assert s['numerical_gate_passed'] and a['protected_unchanged']
def write(path,text):
 q=R/path
 if q.exists():raise FileExistsError(q)
 q.write_text(text)
def append(path,text):
 q=R/path;q.write_text(q.read_text()+text)
labels='PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST'
paired=a['pairs'];d=s['runs']['D5'];dt=s['runs']['D5_tight'];density=a['density_on_own_states']['D5'];rn=d['integration'];ft=d['force']
table='\n'.join(f"|{m}|{paired[m+'_D0']['terminal_m']:.6f}|{paired[m+'_D0']['rmse_3d_m']:.6f}|"+' / '.join(f'{x:.6f}' for x in paired[m+'_D0']['terminal_RAC_m'])+'|' for m in ['D0','D1','D2','D3','D4','D5'])
others='\n'.join(f"|D5−{m}|{paired['D5_'+m]['terminal_m']:.6f}|{paired['D5_'+m]['rmse_3d_m']:.6f}|"+' / '.join(f'{x:.6f}' for x in paired['D5_'+m]['terminal_RAC_m'])+'|' for m in ['D1','D2','D3','D4'])
num='\n'.join(f"|{k}|{v['max_m']:.9f}|{v['threshold_m']:.9f}|{'PASS' if v['passed'] else 'FAIL'}|" for k,v in s['convergence'].items())
res='\n'.join(f"|{m}|"+'|'.join(f"{a['SP3_exploratory_residuals'][m]['hours_1_3_6'][str(h)]['norm_m']:.3f}" for h in [1,3,6])+'|' for m in ['D0','D1','D2','D3','D4','D5'])
cost='\n'.join(f"|{x['model']}|{x['offline_field_generation_s']:.3f}|{x['density_query_total_s_RHS_plus_output']:.3f}|{x['mean_query_ms_RHS_plus_output']:.3f}|{x['integration_RHS_s_includes_queries']:.3f}|{x['online_total_with_output_s']:.3f}|{x['from_scratch_generation_plus_online_s']:.3f}|{x['nfev']}|" for x in a['resources'])
common=f'''{labels}

本次仅D5新增4次传播：1h基准/更紧各一次，门禁通过后6h基准/更紧各一次。D0—D4原件复用，未重跑；新TIE-GCM积分0，未训练。原122项保护文件前后SHA一致。主窗口2023-03-21 00:00:02—06:00:02 UTC，361个60秒输出点；单次SP3原生P/V初始化，没有后续参考修正或参数拟合。
'''
write('reports/MSIS_DRAG_ORBIT_EXPERIMENT.md',f'''# NRLMSIS接入RK45的6小时探索实验

{common}
## 动力学链路及冻结条件

新增MsisResearchDrag仅做显式气动参数/标签和逐查询审计，内部仍调用已有DragForce、EarthFixedFrame、MsisDensityProvider及原RK45。每次RHS把当时实际GCRS位置/速度完整变换至ITRS，再由已有Astropy转换为WGS84大地经纬度和椭球高；显式冻结GFZ驱动进入NRLMSIS2.1/pymsis0.13.0，密度kg/m³实时进入a=−0.5ρCdA/m |vrel|vrel。地固风为0，vrel直接取完整v_ITRS，不能再减一次ω×r；物理力向量只旋转回GCRS。不读沿SP3离线密度表。

合成m400kg、Cd2.2、A1m²，β=m/(CdA)=181.8181818kg/m²，与D0—D4相同。中心μ={c['gravity']['mu']:.12e}m³/s²，J2={c['gravity']['J2']}，参考半径{c['gravity']['radius_m']}m，时变地固对称轴60秒网格覆盖21600秒，配置与历史相同。GCRS初态六分量小端float64字节SHA256：`{c['initial_state_sha256_le_float64']}`。配置中的初态与D0—D4逐元素相同。

冻结EOP/闰秒与历史清单SHA匹配。base rtol1e−10、atol位置1e−3m/速度1e−6m/s、max_step30s；tight为1e−12、1e−5m/1e−8m/s、15s。60秒是输出间隔，不是内部步长。

D5使用模型已明确支持的WGS84。TIE A=WGS84近似原生ZG；B=地心纬度/r−6371000m近似ZG，仍PROVISIONAL，正式外部接口仍EXTERNAL_DATUM_UNVERIFIED。该对比并未证明两模型在严格相同物理高度上取值。

## 6小时受控结果

以下均为模型间位置差，不是预测误差。RAC基于共同D0在同历元的GCRS状态，R径向外、C沿r×v、A=C×R，符号为前者减后者。

|组相对D0|终点位移m|全段位移RMS m|终点R / A / C（m）|
|---|---:|---:|---|
{table}

|对比|终点位移m|全段位移RMS m|终点R / A / C（m）|
|---|---:|---:|---|
{others}

全时段及每时刻有符号RAC见results/metrics/msis_drag_orbit_v1_model_differences.csv。D5与TIE最大差为D5−D1（S3/A），终点65.074180m；其余为58.332529/59.255645/52.201839m。差异在本6小时输出内总体累积并在终点达到最大。D5−D0全段均方位移约99.477%在沿轨方向，终点R/A/C为−9.831/+174.385/−0.0648m。将位置投影到共同D0的R/A平面，用atan2(r·A,r·R)得到终点相位领先约25.514微弧度；这是几何投影相位差，不是拟合出的轨道平根数。阻力导致能量与轨道周期变化，因此不能简单认为阻力必使同历元卫星位置落后。沿轨扰动占主导，也不意味着全部SP3残差来自大气。

D5在自身传播状态上的密度范围{density['rho_min_kg_m3']:.8e}—{density['rho_max_kg_m3']:.8e}kg/m³，阻力模{density['drag_min_m_s2']:.8e}—{density['drag_max_m_s2']:.8e}m/s²，相对速度{density['relative_speed_min_m_s']:.3f}—{density['relative_speed_max_m_s']:.3f}m/s。逐点核实力模比=(密度比)×(相对速率平方比)，不同模型沿各自实际状态；不得把不同位置的密度差当纯模型差。同一SP3参考位置的密度对照另复用上一任务nrlmsis2023_60s.csv及其SHA审计，不与本次自身轨迹曲线混用。

## SP3探索残差

|组|1h三维残差m|3h三维残差m|6h三维残差m|
|---|---:|---:|---:|
{res}

逐时刻RAC残差及平均/RMSE/终点在CSV和analysis.json。这些残差在合成气动参数、未验证TIE参考面、不完整引力/推力等条件下计算，不可作为真实轨道精度排名。未把未来SP3用于密度输入或校准。SGP4历史48h基准初始化来源不同，单独列入阶段报告，不混入这张受控排名表。

## 计算及产物

D5基准接受{rn['accepted_steps']}步，nfev={rn['nfev']}，每次RHS实时查询；主积分{rn['elapsed_s']:.3f}s，包含输出诊断{d['wall_with_output_diagnostics_s']:.3f}s。密度查询总{ft['density_queries']}次（含输出），均值{ft['query_mean_ms']:.3f}ms、P95 {ft['query_p95_ms']:.3f}ms。四次运行总墙钟{s['run_phase_wall_s']:.3f}s，运行进程峰{max(x['peak_RSS_MiB'] for x in s['runs'].values()):.3f}MiB；审计/绘图另{a['analysis_wall_s']:.3f}s，低于1200s/2GiB预算，无GPU。费用详细分层见阶段报告。

入口：source scripts/activate_orbit.sh；PYTHONPATH=src python -m unittest discover -s tests -v；python scripts/run_msis_drag_orbit.py --run-tag msis_drag_orbit_v1（静态）；同命令--execute（已完成，不重放）；python scripts/analyze_msis_drag_orbit.py；python scripts/write_msis_drag_reports.py。现有标签/文件拒绝覆盖，未来复现应换新run-tag并将分析产物对应独立命名，不能覆盖原记录。

配置/门禁/逐运行统计/审计：experiments/msis_drag_orbit_v1。状态CSV、模型差/RAC、残差、资源、Ap边界见results/metrics/msis_drag_orbit_v1_*。压缩逐RHS日志及NPZ在data/processed/msis_drag_orbit_v1，留本地不上传。七图见results/figures/msis_drag_orbit_v1_*，均带三重标签。
''')
write('reports/MSIS_DRAG_NUMERICAL_VALIDATION.md',f'''# D5接口与数值验证

{common}
## 运行前测试与时间精度修正

原126项加7项新测试，全133通过，日志logs/msis_drag_all_tests.log。覆盖内部不规则时刻、外部驱动禁止自动获取、版本/来源、WGS84与完整ITRS速度、阻力公式/单位/旋转、零ρ/Cd/面积、缺驱动立即停止、NaN拒绝、三重标签和正式TIE门禁。合成零项测试复用原DragForce；真实MSIS非正密度依旧拒绝，没有补0回退。

发现并修复MsisDensityProvider将Time.isot默认三位小数传入模型导致亚毫秒舍入的问题，改为Astropy原生datetime64，测试02:59:59.9999与03:00:00.0001正确位于边界两侧，驱动Ap分别9与4。旧整秒离线结果不因该格式修正改变。pymsis底层仍按分发的float32秒/空间输入工作，不能承诺纳秒级底层物理计算；记录完整jd1/jd2和驱动来源，没有借此平滑Ap切换。

## 预注册门槛与1小时结果

直接沿用此前D0—D4配置阈值：1h单轨base/tight最大差<0.02m，配对阻力差变化<最大响应1%；6h单轨<0.5m，重要配对变化<max(5mm,最大配对位移的1%)。在运行前写configuration.json，未放宽。

D5单轨差{p['state_max_m']:.9f}m；最大阻力响应{p['drag_effect_max_m']:.9f}m；配对变化{p['paired_change_max_m']:.9f}m，阈值{p['paired_threshold_m']:.9f}m。D0两组参考为原已保存pre_D0与pre_D0_tight，未重跑。门禁通过后才进入6h。

## 6小时收敛

|检查|最大位置/位移变化m|冻结门槛m|结果|
|---|---:|---:|---|
{num}

D0/D1/D2/D4的tight均复用原结果。D3历史未做tight，本次也不重跑，所以D5/D3没有独立配对tight证明，不能泛称所有配对都单独验证。共同数值误差在差分中会抵消；配对变化不能当单轨绝对误差界，也不能证明物理准确度。

## 全量审计

四份压缩日志逐条读取，RHS数与nfev、输出数与61/361时刻完全一致；所有查询有限正值且具有三重标签、模型版本、实际GCRS/ITRS位置速度、WGS84坐标、F107/F107A/Ap及冻结SHA来源。独立按原始Ap桶索引重算7项历史、前日F107和81日值，并检查三小时边界；所有a_ITRS·vrel<0，独立阻力公式及旋转范数通过。抽样再做完整GCRS→ITRS状态和力向量旋转，与保存记录一致。

每次内部评估都会查询密度，不把60秒输出当积分步，不使用未来SP3密度表。RK45可拒步/重复评估，日志按调用次序保留，不强求内部调用时刻单调；接受步和输出网格单调。Ap按三小时UTC桶切换，不平滑；边界记录见msis_drag_orbit_v1_Ap_boundaries.csv。

逐运行最大公式/旋转/历元/状态差和计数见experiments/msis_drag_orbit_v1/analysis.json的query_audits。原122项保护SHA不变，正式接口及RK45/J2/DragForce核心文件未改；唯一既有密度代码修改是前述时间序列化精度修正。
''')
write('reports/PHASE1_ORBIT_DENSITY_COMPARISON.md',f'''# 第一阶段：三路线轨道与密度影响的阶段性总结

{labels}

## 1. 研究背景及目标

按10月19日早会路线，以Swarm-A精密SP3为参考，建立历史TLE/SGP4、经验大气/RK45、TIE-GCM/RK45三条路线，研究密度对轨道结果与完整计算成本的影响。第一阶段先打通可核查链路，后续才研究FourCastDEN及AI提速。本报告区分工程通过、探索性物理现象和未完成的科学验证。

## 2. 为什么密度影响低轨轨道

阻力使卫星与大气相对运动的能量损耗，密度越大，同样Cd、面积、质量和相对速度下阻力越大。轨道能量/半长轴与周期随之改变，长期可表现为沿轨相位差；同一时刻位置差不只反映瞬时减速。位置差也可能来自引力、初态、推力等，不能全部归因于密度。

## 3. 三条预测路线

A：历史TLE→SGP4→TEME→同历元ITRS→SP3。B：单历元SP3完整P/V→GCRS中心+J2+NRLMSIS阻力→RK45。C：相同SP3初态和受力/气动/积分设置，仅替换成TIE S3/S7候选坐标密度。A初态来源不同，单独参考；B/C仅在本次合成参数/候选参考面下进行受控敏感性研究，不作真实优劣排名。

## 4. Swarm-A数据

NORAD39452，ESA SP3 reduced-dynamic后处理参考，原GPS日历、IGS20、10秒P/V；已有冻结GPS/UTC转换、EOP/闰秒、HDR独立日期锚点及单位检查。SP3不是绝对真值。D0—D5只用t0=2023-03-21 00:00:02 UTC的单历元P/V初始化，随后自由传播；6h统一361个60秒输出，后续SP3只算残差，不校准。历史TLE历元2023-03-20 20:30:00.330336 UTC，历史实际发布时间未知。

## 5. TIE-GCM和NRLMSIS的区别

TIE是热层—电离层物理数值模型，先按5°/60秒4MPI连续积分得到时变三维场，在线再做时空插值；S3/S7包含不同候选预热历史，均未证明充分初态无关。NRLMSIS2.1是预先建立的经验模型，给定UTC/WGS84位置和显式空间环境驱动直接求密度。两者还具有不同太阳/地磁驱动约定；相同GFZ来源并不代表同输入作用。

NRL使用前日Fobs、居中81日均值和7项Ap历史；TIE用其自身太阳时间插值与Kp电动力路径。均为事后HINDCAST。TIE原生ZG与外部高度未严格闭合，A/B仍是条件映射，不是严格相同物理高度。

## 6. 动力学与阻力公式

统一中心引力+时变地固轴J2；a_drag=−0.5ρCdA/m |vrel|vrel。完整GCRS→ITRS状态变换包含地球自转影响，零地固风时vrel=v_ITRS，力矢量旋回GCRS。演示质量400kg、Cd2.2、面积1m²不是Swarm真实气动参数。RK45统一base/tight设置并检验数值收敛。

## 7. 已完成基准

SGP4 48h历史基准：平均625.566m、RMSE763.846m、起点518.729m、终点1724.640m，初始化与RK45不同。两体及J2已独立验证，原J2 48h RMSE16.157km、终点33.772km；这不表示SGP4/RK45算法本身的优劣，受力与初始化不同。TIE连续S3/S7及密度接口、条件沿轨查询已完成；本次补齐NRLMSIS D5。原历史结果不覆盖，详见各自报告。

## 8. 六小时受控轨道结果

全部为相对D0的模型扰动，RAC用共同D0惯性基底。

|组相对D0|终点位移m|全段位移RMS m|终点R / A / C（m）|
|---|---:|---:|---|
{table}

|密度条件对比|终点位移m|全段位移RMS m|终点R / A / C（m）|
|---|---:|---:|---|
{others}

相对SP3的探索残差：

|组|1h残差m|3h残差m|6h残差m|
|---|---:|---:|---:|
{res}

D5相对其他阻力模型的差异包含经验/物理模型、驱动约定、TIE预热与坐标假设的条件影响。密度和阻力曲线来自各自传播状态；同位置纯密度诊断另见NRLMSIS_TIEGCM_COMPARISON.md，不能把轨迹变化混在一起解释。所有结果不得直接称正式预测误差排名。

## 9. 计算成本（必须分层）

|组|离线场仿真s|全部密度查询s|平均查询ms|RK45积分s|含输出在线总s|从零场生成+在线s|nfev|
|---|---:|---:|---:|---:|---:|---:|---:|
{cost}

离线成本为历史S3 5天10分钟、S7 9天10分钟各4MPI的墙钟，不是相同工作负载的速度基准。A/B重复使用同一S3或S7场，不能把它计成两次必需仿真；多卫星/多参数也可摊销。若场已存在，本次增量离线生成成本为0。NRL预先经验模型开发/标定成本不在本次计时内，表中0表示本项目无需生成多日全球场，不表示模型开发免费。

密度查询包括RHS及输出，已经包含在RK45和输出总计时中；不能再相加重复计算。在线总还包括框架转换、日志和文件写出。D1—D4是旧任务实测，D5为本次，机器负载不同，不能给未经同机同负载基准的严格加速倍数。单一TIE物理积分与一次NRL点查询更不能直接作速度比。

上一任务同参考轨迹NRL批量361点0.340478s（含驱动构造），标量均值2.026ms/P952.314ms；本次在线标量均值{ft['query_mean_ms']:.3f}ms/P95{ft['query_p95_ms']:.3f}ms，见审计统计。TIE在线查询LRU最多4096列，旧实际缓存约1MB；D5不缓存密度，冻结驱动在内存，底层Fortran复用内部状态。不同任务进程峰RSS是累计峰、TIE MPI聚合RSS共享页可能重计，不能当独占内存差。

## 10. 发现及不能下的结论

经验密度已实际进入RK45每个内部时刻，力公式/驱动/坐标/初态/查询和收敛均可审计；三路线工程原型齐备。给定演示条件下密度差确实对应不同阻力及米至百米的轨道扰动，沿轨成分值得关注。数值精度足以研究当前模型间差值，但不证明初态无关、真实密度准确或真实Swarm精度提高。更小SP3残差不能单独确认某密度更好，也不能推导RK45一定优于SGP4。

## 11. 正式验证缺口

TIE外部高度/纬度基准；可靠Cd及参考面积、几何/姿态四元数约定/质量位、质量不确定度；非零dt_thr与净推力解释；高阶重力/第三体/SRP等；初始场敏感性/预热；10分钟输入场的独立高频验证；与POD共享信息的DNS密度参考相关性。需预先冻结质量/机动筛选和校准区间，不能看未来SP3后拟合本窗口。详见FORMAL_ORBIT_VALIDATION_GAPS.md。

## 12. 后续FourCastDEN衔接

先闭合上述物理/数据门禁并冻结共同参考、受力、气动及密度接口；再以相同TIE训练/验证协议复现原FourCastDEN。架构或训练改进除原生场指标外，还应评估受控轨道影响、域外查询、驱动可用性及离线训练/场生成/在线总成本。当前不训练，也不拿AI拟合TIE的精度当真实轨道精度。

本次四次D5总墙钟{s['run_phase_wall_s']:.3f}s、另离线审计绘图{a['analysis_wall_s']:.3f}s；133测试通过。后续需新指令，不自动扩展24/48h或新TIE预热。
''')
update=f'''\n\n## 2026-10-20最新：D5经验密度轨道接入完成\n\n本次只新增D5的1h基准/tight、6h基准/tight共4次传播，D0—D4没有重跑，133项测试通过。D5对D0六小时终点位移{paired['D5_D0']['terminal_m']:.6f}m，D5与D1/D2/D3/D4终点差分别{', '.join(f"{paired['D5_'+m]['terminal_m']:.6f}" for m in ['D1','D2','D3','D4'])}m；均为PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST模型差，不是正式预测误差。完整共同初态、力、气动/风、容差和输出冻结，NRL使用真实内部状态及WGS84，TIE A/B仍未正式登记。\n\n三路线工程链路已齐备：历史TLE/SGP4、NRLMSIS/RK45、TIE条件密度/RK45；正式Swarm精度比较尚未完成，缺高度/气动/姿态/推力和完整受力、初态与高频场验证。阶段总结reports/PHASE1_ORBIT_DENSITY_COMPARISON.md，D5运行/数值报告MSIS_DRAG_ORBIT_EXPERIMENT.md及MSIS_DRAG_NUMERICAL_VALIDATION.md；实测数据experiments/msis_drag_orbit_v1。四次运行{s['run_phase_wall_s']:.3f}s，峰{max(x['peak_RSS_MiB'] for x in s['runs'].values()):.3f}MiB，原122项保护哈希不变。无新TIE/旧D0-D4运行、无拟合或训练，完成后停止。Git实际提交/远端同步见任务结束核验日志。\n'''
append('STATUS.md',update)
append('WORKLOG.md',update+'''\n关键操作：先读长期规则/研究计划/协议/原运行数值和MSIS报告；核实本地与远端main均为b0c5bd0，非重复提交上一任务。新增msis_drag_provider.py研究审计桥、独立run_msis_drag_orbit.py及7测试；复用原DragForce/EarthFixedFrame/J2/RK45，修正MSIS时间序列化到datetime64避免默认毫秒舍入，未改正式TIE门禁。静态SHA/初态/参数/资源与预算门禁后执行一次运行器，按1h门禁顺序完成4传播，无重试。逐RHS压缩日志/NPZ留data/processed，本次轻量CSV/七图/审计JSON及三报告入库。全量重算驱动/阻力，抽样完整状态/旋转；主要配对tight复用旧D0/D1/D2/D4，D3未做新tight且明确限制。\n\n命令：source scripts/activate_orbit.sh；PYTHONPATH=src python -m unittest discover -s tests -v；python scripts/run_msis_drag_orbit.py --run-tag msis_drag_orbit_v1；OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/run_msis_drag_orbit.py --run-tag msis_drag_orbit_v1 --execute；python scripts/analyze_msis_drag_orbit.py；python scripts/write_msis_drag_reports.py。所有已存在run-tag/输出拒绝覆盖，禁止重放本次授权。下一步待新指令核实真实气动/机动/高度与高阶力，不能自动以本次残差排名或扩窗。\n''')
for name in ['docs/PROJECT_PLAN.md','docs/UPDATED_RESEARCH_PLAN.md']:
 q=R/name;q.write_text('# 当前阶段接续（2026-10-20）\n'+update+'\n---\n以下保留历史计划与当时状态；当前结论以上节及STATUS最后记录为准。\n\n'+q.read_text())
append('docs/FORMAL_ORBIT_VALIDATION_GAPS.md','''\n\n## D5完成后的接续\n\nNRLMSIS/RK45探索性6h软件集成与必要数值收敛已完成，相关“待接入”属于此前状态。三路线工程原型完成不等于正式科学验收；上表其他高度/气动/机动、完整受力、初态独立性与高频输出缺口保持，不因某组SP3残差较小而解除。下一步优先冻结真实参数与质量/推力处理，再逐项物理受力验证；未来正式扩窗须另获授权。\n''')
append('AGENTS.md','''\n\n## D5经验密度接入后的最新门禁\n本次另获授权完成msis_drag_orbit_v1四次D5传播（1h base/tight、6h base/tight），未重跑D0—D4。本次133项测试通过。MsisDensityProvider使用Astropy datetime64保留内部时刻精度，Ap仍按UTC三小时桶切换，不平滑。所有轨道成果仍为PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST，不能以探索残差排名真实精度；TIE正式外部接口仍拒绝。三路线仅工程原型齐备，正式高度/气动/姿态推力/完整受力与独立物理验证尚未完成。后续不自动扩窗、运行新TIE、重放本次标签或训练。参见PHASE1_ORBIT_DENSITY_COMPARISON.md及MSIS_DRAG两报告。\n''')
print('Reports and progress updated')
