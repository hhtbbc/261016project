"""Render reports from completed, independently audited research results."""
from pathlib import Path
import json,csv
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'experiments/provisional_drag_orbit_v1'
def main():
 analysis=json.loads((P/'analysis.json').read_text());matrix=json.loads((P/'matrix_summary.json').read_text());pre=json.loads((P/'precheck.json').read_text());audit=json.loads((P/'independent_audit.json').read_text())
 with (ROOT/'results/metrics/provisional_drag_orbit_v1_model_differences.csv').open() as f:last=list(csv.DictReader(f))[-1]
 report='''# PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST
# TIE-GCM密度驱动的RK45探索性轨道实验

## 已完成的范围

已将每次RK45内部评估的GCRS状态，经已有完整ITRS状态转换、显式候选坐标映射、真实S3/S7原生密度查询和零地固风阻力公式接到积分器。没有事后把阻力追加到无阻力轨道，没有沿SP3表查密度替代实际传播状态。正式外部接口仍EXTERNAL_DATUM_UNVERIFIED；原RK45、J2、阻力、坐标及原生插值模块未改。没有新的TIE-GCM仿真、训练或24/48小时传播。

实际完成4次1小时预检（D0、D2及各自tight），随后5次6小时主传播，另4次6小时tight对照（D0/D1/D2/D4），共13次真实单历元初态的探索传播。D3未追加tight；严格数值对照覆盖源变化D1/D2、映射变化D2/D4及加入阻力D2/D0，不声称所有组合均单独做了tight。独立单元测试另含短时合成状态传播，不是额外Swarm实验。无失败重试。

## 冻结协议

- t0=2023-03-21 00:00:02 UTC，主实验终点06:00:02；输出60秒，共361点。完整SP3原生P/V只在t0初始化，ITRS→GCRS带速度转换；与既有J2初态逐元素相同，无参数/初态拟合、中途重置或未来SP3校准。
- 演示m=400kg、Cd=2.2、A=1m²；β=m/(Cd A)=181.8181818kg/m²，倒数0.0055m²/kg。全部是显式合成气动参数，不代表2023 Swarm真实参数；各组完全一致。
- 固定共转大气、零ITRS中性风。相对速度直接采用完整变换后的v_ITRS，不再重复减ω×r。a_ITRS=−0.5ρCdA/m |vrel|vrel，物理力矢量由同一旋转Qᵀ转回GCRS，不加坐标系虚拟力。
- 相同中心μ、时变地固轴J2、冻结IERS/闰秒，复用EarthFigureAxis的60秒轴网格和原RK45。基准rtol1e−10、atol位置1e−3m/速度1e−6m/s、max_step30s；tight为1e−12、1e−5m/1e−8m/s、15s。
- A假设WGS84大地纬度/椭球高近似模型纬度/ZG；B假设地心纬度与r−6371000m高度。两者仍未获严格参考面验证。10分钟场间隔不是RK45步长，内部连续时刻均实时插值。

|组|密度来源|映射|阻力|
|---|---|---|---|
|D0|无|无|不加入，密度值N/A而非伪造0|
|D1|S3|A|合成参数|
|D2|S7|A|同上|
|D3|S3|B|同上|
|D4|S7|B|同上|

D1/D2、D3/D4只改变密度来源；D1/D3、D2/D4只改变映射。D1/D4同时改变两因素，不用于单因素结论。

## 预检门禁

1小时D2−D0终点/最大位移2.937451m。基准与tight的最大状态位置差D0约0.001524m、D2约0.001539m；配对阻力位移变化仅0.0000341m。按运行前冻结的2cm状态和阻力响应1%门槛通过后，才执行矩阵。预检实测推算矩阵上界约1560.57秒（规划估算，不是实测），在当时剩余约1692秒内获程序门禁通过。

## 6小时模型间位移（不是预测误差）

统一GCRS历元，差值左组减右组。RMSE是整个361点位置差范数的RMS，不代表对真实轨道的预测精度。

|比较|唯一改变因素|终点位置差m|全时段位置差RMS m|
|---|---|---:|---:|
'''
 factors={'D1_D2':'S3/S7，映射A','D3_D4':'S3/S7，映射B','D1_D3':'A/B，来源S3','D2_D4':'A/B，来源S7','D1_D0':'加入S3/A演示阻力','D2_D0':'加入S7/A演示阻力','D3_D0':'加入S3/B演示阻力','D4_D0':'加入S7/B演示阻力'}
 for name,v in analysis['pairs'].items():report+=f"|{name}|{factors[name]}|{v['terminal_m']:.6f}|{v['rmse_3d_m']:.6f}|\n"
 report+='''
这些差异随本窗口累计增长，不能称为位置预测误差。S3/S7场约6%的条件密度差在本参数和6小时窗口下体现为约6.7—7.1m终点差；先前A/B密度P95约24%，不意味着轨道位移相差24%，因为阻力沿时空轨迹积分、存在周期变化和动力学反馈。

## RAC扰动及阻力数量级

RAC基于同历元D0的GCRS状态：R向外，C沿r×v，A=C×R，各组减D0；不是用地固速度构造惯性沿轨基。终点：

|组−D0|R m|A m|C m|
|---|---:|---:|---:|
'''
 for n in ['D1','D2','D3','D4']:report+=f"|{n}|{float(last[n+'_D0_R_m']):.6f}|{float(last[n+'_D0_A_m']):.6f}|{float(last[n+'_D0_C_m']):.6f}|\n"
 report+='''
本例主要为沿轨相位变化，径向为米量级，法向约厘米量级。阻力作用不只是速度瞬时减小，也会改变轨道能量和后续相位，因此长期沿轨扰动符号不能仅凭某一时刻减速方向判断。

|组|60秒输出点密度范围kg/m³|阻力模范围m/s²|
|---|---|---|
'''
 for n,v in analysis['density_diagnostics'].items():report+=f"|{n}|{v['density_min_kg_m3']:.6e}—{v['density_max_kg_m3']:.6e}|{v['drag_min_m_s2']:.6e}—{v['drag_max_m_s2']:.6e}|\n"
 report+='''
相对地固大气速度为每次完整状态转换所得，具体范围在各组JSON。密度曲线对应各组自己的积分轨迹，不能将不同轨迹上的逐时刻密度比直接当严格同位置场差；同一状态的S3/S7阻力比例已在独立测试中验证。

## 探索性SP3残差（禁止据此判定真实方法优劣）

仅作参考诊断，使用相同历元的SP3完整ITRS→GCRS转换；SP3不是绝对无误差真值。真实受力不完整、气动参数合成、参考面未知、驱动hindcast且S7不是真值，以下终点残差变小不能证明真实轨道精度提高：

|组|6小时终点相对SP3残差m|
|---|---:|
'''
 for n,v in analysis['exploratory_SP3_residuals'].items():report+=f"|{n}|{v['terminal_m']:.6f}|\n"
 report+=f"\nD0与保留旧J2基准共同时间段最大位置差{analysis['D0_vs_preserved_J2_max_m']:.9f}m；有限终点和轴样条边界不同会产生微小数值差，旧基准文件未覆盖。\n"
 report+='''
## 资源与查询审计

模型阶段总墙钟1389.205秒，峰进程RSS182.559MiB，CPU环境/单线程、无GPU，均低于1800秒/2GiB。计算完成后会话有等待，后续审计元数据单独记录包含空闲时间的monotonic差，不把用户等待算作模型耗时。独立流式审计另耗19.579秒。

|主组|接受步|nfev|积分秒|含输出诊断秒|原生密度调用总数|
|---|---:|---:|---:|---:|---:|
'''
 for n in ['D0','D1','D2','D3','D4']:
  v=matrix['runs'][n];st=v['integration'];force=v['force'];report+=f"|{n}|{st['accepted_steps']}|{st['nfev']}|{st['elapsed_s']:.3f}|{v['wall_with_output_diagnostics_s']:.3f}|{force['density_queries'] if force else 'N/A'}|\n"
 report+='''
每个有阻力主组4346次RHS查询+361次输出诊断=4707次。含预检和tight共45594次内部密度查询、2649次输出查询，全部有效，失败0；密度失败的强制中止行为由单元测试验证。求解器内部时刻可重复或非单调（RK阶段/试步），不能当成输出时间轴去重；接受步和60秒输出时间分别保存。

每个主阻力组原生列读取2122次、缓存2122列，容量4096列有界，按需读取且文件with关闭；密度查询累计约8.82—8.94秒，而整个变换/力评估约125.7—126.4秒（含原生查询）。该差值包含时间/坐标变换和封装开销，不是单独测出的纯框架耗时；当前效率瓶颈主要在这些外围计算，未来优化须另验证完整速度及力矢量精度。一次运行的墙钟不构成跨平台性能排名。

审计重算力公式、旋转范数、抽样重新查询原生密度及完整框架往返。最大位置/速度往返约2.98e−9m/5.40e−9m/s，抽样密度相对差0；45594次RHS每条均有完整来源/映射/权重/状态。所有a_ITRS·vrel≤0。含41次周期接缝邻列查询、2614次|模型纬度|>=85°查询；均未发生索引或覆盖错误。60秒输出ln密度最大步差约0.039—0.048，是沿移动轨迹样本变化，不是模型每60秒场已被独立验证。

原NetCDF、原核心模块及旧J2结果保护哈希不变，三份SP3匹配旧清单。压缩逐查询日志和NPZ约26.85MB留data/processed/provisional_drag_orbit_v1，不入Git；目录配置及independent_audit.json将每个本地文件与标签/来源/哈希关联。公共CSV每行含三重状态标记，所有图有完整三重标签。

## 产物与复现

- scripts/run_provisional_drag_orbit.py：独立precheck/matrix门禁，旧run-tag禁止覆盖，matrix独占启动标志，失败不重试。
- scripts/summarize_provisional_drag_orbit.py：只读模型差/RAC/SP3残差与6张图。
- scripts/audit_provisional_drag_orbit.py：逐查询独立审计，不启动传播。
- scripts/audit_provisional_drag_window_parameters.py：仅读已有ESA CDF，未将结果用于力模型。
- results/metrics/provisional_drag_orbit_v1_*_states.csv、model_differences.csv、resources.csv。
- results/figures/provisional_drag_orbit_v1_{position_differences,density_drag,source_sensitivity,mapping_sensitivity,RAC_perturbations,convergence}.png。
- experiments/provisional_drag_orbit_v1：冻结参数/阈值、precheck、各组与矩阵JSON、分析与独立审计。

```bash
source scripts/activate_orbit.sh
python -m unittest discover -s tests
python scripts/run_provisional_drag_orbit.py --run-tag NEW_TAG --phase precheck --execute
# 读precheck和预算，门禁通过后才可执行；当前授权的v1已完成，不自动重放。
python scripts/run_provisional_drag_orbit.py --run-tag NEW_TAG --phase matrix --duration-hours 6 --execute
python scripts/summarize_provisional_drag_orbit.py --run-tag NEW_TAG
```

辅助独立审计/参数复核当前固定v1，以独占写入保护已有结果，不直接重放覆盖。114项全套测试通过，新增6项物理/接口测试通过，日志logs/provisional_drag_all_tests.log及provisional_drag_unit_tests.log。当前没有额外预热/48小时评估或正式参数集成授权，任务完成后停止。

## 未解决的问题

正式参考面、Cd/面积/四元数/质量位、推进器定义、经验密度对照、高阶重力/第三体等仍未闭合。此次新检查的6小时内仍有22条非零dt_thr记录而f_thr均0；姿态Maneuver_Id全0不能用来排除推进器影响，相关数据没有被用于拟合。具体见docs/FORMAL_ORBIT_VALIDATION_GAPS.md。10分钟时间场仍无独立高频参考，数值收敛只证明当前离散场下的积分一致性，不约束场欠采样或真实物理误差。
'''
 (ROOT/'reports/PROVISIONAL_DRAG_ORBIT_EXPERIMENT.md').write_text(report)
 numerical='''# PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST
# 数值与物理集成验证

正式外部密度接口保持拒绝；新增私有桥接仅由显式acknowledge_provisional、候选adapter和带合成来源说明的气动参数启用。零地固风固定，无TIE风与其他零风的混用。

## 积分前独立测试

新增6项测试：缺失参数/未标记参数拒绝及状态保留；零密度/Cd/面积各与无阻力短时合成积分逐元素相同；反向性、密度倍增和独立SI量级；无效/NaN/负密度在首次RHS立即抛错；已知ITRS状态完整转换后的相对速度和Qᵀ力矢量；同一真实初态S3/S7阻力比例及正式接口拒绝。测试覆盖多个断言，不以6项冒充6个真实传播实验。基础模块原有的相对静止/能量功验证继续通过。

全套114测试通过，主6小时实验前已执行；没有为追求通过修改任何既有核心代码或容差。

## 冻结数值标准

基准rtol1e−10、atol位置1e−3m/速度1e−6m/s、max_step30s；tight为1e−12、1e−5m/1e−8m/s、15s。主图共同60秒输出不代表内部步长。1小时状态差门槛2cm、配对阻力位移变化<其最大响应1%；6小时抽查单轨状态差<0.5m，重要配对差变化<max(5mm,该对比最大位移的1%)。阈值在预检运行前写configuration.json，没有事后放宽。

1小时D0/D2的状态最大差分别0.001523720/0.001539214m，D2−D0位移变化0.000034087m，门禁通过。

## 6小时状态收敛

|组|基准/tight最大位置差m|门槛m|结果|
|---|---:|---:|---|
'''
 for n in ['D0','D1','D2','D4']:
  v=matrix['convergence'][n];numerical+=f"|{n}|{v['max_position_difference_m']:.9f}|0.5|{'PASS' if v['passed'] else 'FAIL'}|\n"
 numerical+='''
D3没有另跑tight，不把代表性检查冒充逐组全面数值证明。四组状态差均约5.8cm，显示共同积分误差；它不是严格全局误差界。

## 配对差值收敛

|配对|最大差值变化m|冻结门槛m|结果|
|---|---:|---:|---|
'''
 for n in ['D1_D2','D2_D4','D2_D0']:
  v=matrix['convergence'][n];numerical+=f"|{n}|{v['max_difference_m']:.9f}|{v['threshold_m']:.9f}|{'PASS' if v['passed'] else 'FAIL'}|\n"
 numerical+='''
即S3/S7(A)对比变化约0.025mm，S7(A/B)对比约0.050mm，S7/A加入阻力的响应变化约0.158mm，均远小于对应米至百米响应。共同中心/J2积分偏差高度相关，在差分中部分抵消，因此不能把配对收敛精度当成单轨绝对准确度，也不证明物理模型或坐标假设正确。

## 独立审计

流式检查9份压缩逐查询日志：45594个内部RHS和2649个输出查询均有三重状态、实际GCRS状态、实际ITRS坐标/相对速度、候选模型坐标、源文件/邻点/时间垂直权重和气动参数。没有缺失补0。逐条用保存的ρ和vrel独立重算阻力公式（差0），旋转加速度范数最大差约7.94e−23m/s²；抽样从真实原生文件重新查询密度，相对差0。

完整ITRS→GCRS反向检验最大位置2.98e−9m、速度5.40e−9m/s；力向量重转检查通过。每条a_ITRS·vrel≤0。RK45内部可能重复同一时刻，按评估序列保留；接受步t严格递增，输出按预定60秒对齐。原始GCRS初态完全相同。

D0对旧J2基准的最大差约8.18e−5m，原文件哈希不变。核心模块、46个NetCDF与旧J2文件保护通过，三份SP3匹配既有SHA；正式外部接口仍EXTERNAL_DATUM_UNVERIFIED。

## 限制

以上验证当前给定离散TIE-GCM场及演示参数的数学链路、数值收敛和可追溯性；不是高频真实大气、真实Cd/面积、推力或完整重力模型的验证。6小时残差不能替代正式轨道预测精度试验。更高频场、参考登记、初态敏感性和真实气动/机动定义仍需后续独立研究。当前不再启动任何传播。
'''
 (ROOT/'reports/PROVISIONAL_DRAG_NUMERICAL_VALIDATION.md').write_text(numerical)
if __name__=='__main__':main()
