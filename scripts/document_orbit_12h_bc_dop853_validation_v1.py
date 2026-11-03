"""Write completed B/C qualification and a bounded D-reference next decision."""
from pathlib import Path
import sys,json,csv
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_orbit_12h_bc_dop853_validation_v1 import F,O

def read(n):return list(csv.DictReader((O/n).open()))
def main():
    audit=json.loads((F/'independent_audit.json').read_text());assert audit['audit_status']=='PASS';analysis=json.loads((F/'analysis.json').read_text());effect=json.loads((F/'effect_assessment.json').read_text());sup=json.loads((F/'supervision.json').read_text());g=analysis['gates'];passed=all(g[x]=='PASS' for x in ['B_SINGLE_ORBIT_CONVERGENCE_READY','C_SINGLE_ORBIT_CONVERGENCE_READY','BC_PAIR_EFFECT_CONVERGENCE_READY']);s=effect['DOP15_effect'];old=effect['RK45_terminal_norm'];events=read('event_limits.csv');ev=next(r for r in events if r['group']=='C_Updated' and r['mode']=='DOP15');performance=read('performance.csv');summary=read('comparison_summary.csv');single=[r for r in summary if 'DOP30 minus DOP15' in r['comparison'] and r['comparison'].startswith(('B_Open','C_Updated'))];rk=[r for r in summary if 'RK45_Tight minus DOP15' in r['comparison'] and r['comparison'].startswith(('B_Open','C_Updated'))];d_est=sum(float(r['total_s']) for r in performance)/2
    def md(rows,keys):return '\n'.join('|'+'|'.join(str(r[k]) for k in keys)+'|' for r in rows)
    gate_rows=[dict(gate=k,status=v) for k,v in g.items()];qual='B/C高阶单轨与配对门槛均通过' if passed else 'B/C高阶门槛未全部通过，以下轨道响应仍未完成数值资格'
    report=f'''# 12小时AI状态更新轨道效应：B/C独立DOP853验证 V1

## 1. 完成范围与核心结论

{qual}。本轮实际新增B_Open、C_Updated各DOP853 max30/15秒，共4条Jan4 01—13UTC轨迹、8个6小时积分段，各721个输出。A高阶参考只读复用，D高阶未运行，旧8条RK45未重跑。

DOP15 Updated−Open终点{ s['terminal_m']:.12g}m，全窗RMS{s['RMS_m']:.12g}m，最大{s['max_position_m']:.12g}m；旧RK45 Tight终点{old:.12g}m。终点**范数**差（DOP15−RK45）{effect['terminal_norm_difference_DOP15_minus_RK45']:.12g}m；终点**效应差向量**模{effect['RK45_effect_delta']['terminal_m']:.12g}m，二者不能混用。

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
{md(performance,['group','mode','integration_s','total_s','nfev','all_density_queries'])}

监督墙钟{sup['wall_s']:.3f}s，峰值树RSS{sup['peak_tree_RSS_bytes']/2**20:.3f}MiB，低于13620秒/4GiB；实际预检、离线分析另行记录，不混同纯积分耗时。查询计数包含每步求解及DOP连续输出阶段调用、2次事件RHS、721次输出及2次显式极限，共{audit['all_queries']}次，全部有效。nfev包含DOP连续输出所需额外3阶段，未隐瞒调用。全部逐次查询日志和状态NPZ保留本地。

八邻列共同高度余量与左右时间括点独立核验见independent_query_accounting.csv。所有left上括点≤07、right下括点≥07，未把07右状态提前插值到06—07。

## 5. 单轨与效应差向量收敛

单轨门槛仍为全窗最大位置差≤0.02m；速度差仅报告，没有临时发明新的速度门槛。

|单轨比较|最大位置差m|终点m|全窗RMS m|最大速度差m/s|
|---|---:|---:|---:|---:|
{md(single,['comparison','max_position_m','terminal_m','RMS_m','max_velocity_m_s'])}

效应定义Δ30=C30−B30、Δ15=C15−B15，数值差δ=Δ30−Δ15。必须先减向量，再取模。全窗最大δ模{effect['paired_delta']['max_position_m']:.12g}m、终点{effect['paired_delta']['terminal_m']:.12g}m；DOP15最大响应{s['max_position_m']:.12g}m，冻结1%限值{effect['paired_gate_m']:.12g}m，相对敏感性{100*effect['paired_fraction']:.12g}%。

两套DOP之差是数值设置敏感性，不是DOP15相对精确解的严格误差上界；两算法也共用H6，不能验证其共同系统物理误差。

## 6. 旧RK45 Tight独立对照

|旧轨道−新DOP15|全窗最大位置差m|终点m|全窗RMS m|最大速度差m/s|
|---|---:|---:|---:|---:|
{md(rk,['comparison','max_position_m','terminal_m','RMS_m','max_velocity_m_s'])}

旧RK45 B/C效应差向量−DOP15效应差向量，全窗最大{effect['RK45_effect_delta']['max_position_m']:.12g}m、终点{effect['RK45_effect_delta']['terminal_m']:.12g}m。旧RK45是否落在独立0.02m范围见下方实际门禁；不把相减后的共模抵消反过来当单轨通过证据。历史旧Base/Tight约0.24m的FAIL原样保留。

accepted_rejected_steps.csv记录DOP实际接受/推算拒绝步。密度小时/空间分片插值可改变平滑性，07硬更新靠显式分段处理；只有本轮直接数值差支持本窗口的稳定性，不根据NoDrag结果预先宣布B/C合格，也不能单凭差异将残余唯一归因为密度插值。

## 7. 更新轨道效应与07事件

两配置下B/C更新前361个状态逐元素一致，07左终点和右起点P/V严格相同，四条轨迹均0跳变。C DOP15事件同状态密度{float(ev['rho_left']):.12g}→{float(ev['rho_right']):.12g}kg/m³（{100*float(ev['density_jump_fraction']):.8f}%），阻力加速度向量跳变量模{float(ev['drag_vector_jump']):.12g}m/s²。位置速度不瞬变，后续密度变化造成加速度差，经积分及共同动力学耦合积累为速度和位置差。

DOP15终点Updated−Open的R/A/C={s['terminal_R_m']:.12g}/{s['terminal_A_m']:.12g}/{s['terminal_C_m']:.12g}m，终点速度差模{s['terminal_velocity_m_s']:.12g}m/s。所有RAC用同一冻结基；沿轨位置响应不等于阻力直接只有沿轨分量。完整721点及1/3/6左右/7/9/12h见comparison_curves、lead_time_summary，既报告全窗RMS也报告终点。

**本轮没有D高阶轨道。**因此只验证状态更新对B/C条件轨道的影响及与旧RK45的一致程度，不宣布Updated更接近高阶TIE-GCM条件参考。旧9.177625m/4.482435m只能保留为旧RK45历史值，未在本轮补齐高阶数值资格，更不能称真实Swarm精度改善。

## 8. D组决策

若B/C门槛通过，值得下一轮单独补D30/D15，以完成Open−D、Updated−D以及“终点与全窗是否都改善”的高阶闭环。按本次B/C实际单组成本均值，D两条约{d_est:.1f}s，1.5安全预算{d_est*1.5:.1f}s；内存预估<1GiB、硬上限4GiB，输出预估<50MiB。

D参考DEN/原ZG在旧Jan4路径与RK45在线检查曾有效；仍需新一轮输入SHA/局地高度/极区/UTC预检及逐RHS100%有效，不直接将旧路径通过视为DOP自由轨迹的完整覆盖保证。保持同H6、初态、气动、A假设、07分段及30/15+严格容差；单轨≤0.02m、所有与B/C/A同配置配对差向量≤最大效应1%，门槛不放宽。D若未运行则D_REFERENCE_HIGH_ORDER_READY绝不能PASS。

如果B/C本轮未通过，先定位数值问题再谈D，不能依据报告模板擅自启动。无论是否有剩余预算，本轮D新增传播为0。

## 9. 实际验收

|门禁|实际状态|
|---|---|
{md(gate_rows,['gate','status'])}

独立审计不重新积分，直接从原状态重算单轨、配对向量、旧新效应差，核对查询总数、八列高度域、左右时间括点及保存rho/v_rel/阻力模方程。冻结{audit['protected_SHA_unchanged']}任务资产和{audit['historical_SHA_unchanged']}历史资产SHA不变，A参考两数组SHA不变。真实轨道BLOCKED、科学训练False、旧RK45 FAIL保持。

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

旧标签完成后拒绝重放；若独立复现需新授权和run-tag，不删除旧目录。原始状态NPZ、位置查询日志、SP3/DNS/权重仅本地；公开轻量派生指标、图表、代码、协议和SHA，不提交凭据、不强推。完成后停止，不执行D、24h、多日期、多模型或训练。
'''
    path=ROOT/'reports/ORBIT_12H_BC_DOP853_VALIDATION_V1.md';assert not path.exists();path.write_text(report)
    talk=f'''# 三分钟中文组会稿：状态更新轨道效应的独立高阶验证

上一次十二小时传播得到，大气在第六小时理想更新后，终点轨道会与不更新方案相差约4.698米。但旧Base和Tight单轨相差二十四厘米，我们不能仅凭两条轨道相减后很稳定，就认定整个实验数值合格。

本轮不重跑旧矩阵，只对原预测B组和更新C组，各做三十秒、十五秒两套DOP853高阶积分，共四条轨迹。初态、力模型、密度场、合成质量面积和阻力系数完全不变，七点仍只更新大气，绝不重置卫星位置和速度。

实际验收结果是：{qual}。两套高阶设置下，B、C单轨的位置差及配对效应向量差都在报告中单独核验，没有把两个位置差范数相减当作向量收敛。配对效应的最大数值差为{effect['paired_delta']['max_position_m']:.6g}米。

十五秒DOP853给出的十二小时末更新效应为{s['terminal_m']:.6f}米，与原RK45 Tight终点范数相差{effect['terminal_norm_difference_DOP15_minus_RK45']:.6g}米。新旧效应差向量的全窗最大值为{effect['RK45_effect_delta']['max_position_m']:.6g}米。主要沿轨分量为{s['terminal_A_m']:.6f}米，径向为{s['terminal_R_m']:.6f}米，法向为{s['terminal_C_m']:.6f}米。

这条物理链路是：大气密度变化让卫星阻力改变，先积累为速度差，再经轨道动力学耦合变成位置差。七点左右卫星位置、速度严格连续；本轮全部密度查询都经过时间、八邻列和高度域检查，没有补零、外推或偷用未来轨道纠正。

但本轮验证的是B与C之间的条件效应，不是真实Swarm轨道预测误差。外部高度仍采用A假设，气动参数仍是演示值；D组参考密度轨道还没有高阶结果，所以不能说已独立证明更新轨道更接近高阶TIE-GCM参考，更不能等同真实大气或真实卫星精度提升。

如果本轮门槛通过，下一步值得单独补D组两套高阶参考，完成三个密度方案之间的数值比较；预计预算另行申请。本轮到此停止，不会因为预算剩余就自动继续D或更长实验。
'''
    q=ROOT/'docs/ORBIT_12H_BC_DOP853_TALK.md';assert not q.exists();q.write_text(talk)
    print('report/talk saved',g)
if __name__=='__main__':main()
