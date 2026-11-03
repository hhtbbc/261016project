"""Write evidence-based report and Chinese talk after independent audit."""
from pathlib import Path
import csv,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_fourcastden_orbit_update_12h_v1 import F,O
from prepare_fourcastden_swarm_observation_v1 import dump,sha

def read(n):return list(csv.DictReader((O/n).open()))
def main():
    audit=json.loads((F/'independent_audit.json').read_text());assert audit['audit_status']=='PASS'
    a=json.loads((F/'analysis.json').read_text());effect=json.loads((F/'update_effect.json').read_text());supervisor=json.loads((F/'supervision.json').read_text());protocol=json.loads((F/'protocol.json').read_text());initial=np.load(F/'initial_GCRS_local.npy');passed=a['gates']['ORBIT_NUMERICAL_CONVERGENCE_READY']=='PASS'
    pair={r['comparison']:r for r in read('pair_summary.csv') if r['mode']=='tight'};ev=next(r for r in read('event_density_drag_jump.csv') if r['group']=='C_Updated' and r['mode']=='tight');c=pair['C_Updated minus B_Open'];b=pair['B_Open minus D_Reference'];d=pair['C_Updated minus D_Reference']
    def md(rows,keys):return '\n'.join('|'+'|'.join(str(r[k]) for k in keys)+'|' for r in rows)
    summary=md(pair.values(),['comparison','terminal_m','max_m','RMS_m','terminal_speed_m_s','terminal_R_m','terminal_A_m','terminal_C_m'])
    conv=md(read('numerical_convergence.csv'),['comparison','max_position_m','max_speed_m_s','limit_m','passed'])
    leads=md([r for r in read('lead_time_summary.csv') if r['mode']=='tight' and r['comparison'] in list(pair)[:3]],['comparison','lead_h','event_side','position_m','speed_m_s','R_m','A_m','C_m'])
    perf=md(read('performance.csv'),['group','mode','integration_s','total_s','nfev','all_density_queries'])
    gates=md([dict(gate=k,status=v) for k,v in a['gates'].items()],['gate','status'])
    intervals='；'.join(f"{1+lo/3600:.4f}—{1+hi/3600:.4f} UTC小时" for lo,hi in effect['farther_intervals_seconds_since01']) or '无（仅按60秒保存点判断）'
    qual='全部冻结数值门槛通过' if passed else '冻结数值门槛未全部通过；不放宽阈值、不重跑，以下数值仅为尚未完成数值资格确认的条件计算'
    report=f'''# FourCastDEN六小时理想更新驱动12小时条件轨道传播 V1

## 1. 实验结论与限定

实验日期2023-01-04，01:00—13:00 UTC，07:00更新，Direct模型；四组Base与Tight共8条12小时传播、16个6小时积分段，各721个60秒输出。{qual}。

全程保留：HISTORICAL_SP3_INITIALIZED_VIRTUAL_PROPAGATION / PROVISIONAL_COORDINATE_A / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST / FORCE_MODEL_INCOMPLETE / PROVISIONAL_EPHEMERIS。

本轮是**指定坐标与合成气动参数下的条件模型间轨道差异**。TIE-GCM密度驱动轨道也不是观测真值；无SP3预测残差评分、气动/高度拟合、未来SP3轨道反馈、新GPU、TIE积分或网络训练。原122帧科学训练门禁保持False。

## 2. 冻结控制、初态与数据

A NoDrag、B Open-loop、C Ideal Update、D TIE-GCM Reference。共同H6非阻力力场为原EGM2008 n/m≤40与ERFA几何日月第三体，原源码和设置不变；40阶截断未证明充分，SRP、潮汐、相对论和实际推力等仍缺失。只改变大气密度源。

气动质量400kg、面积1m²、Cd2.2、零相对地固中性风，完全继承前一小时实验，不代表Swarm实物。完整ITRS速度转换用于大气相对速度，不重复扣除地球自转。A不调用密度，绝不把NoDrag画成零密度大气。

初态来自官方SP3ACOM0203，文件SHA52e9b1d540c09511dc814bf8ad2957d71cef4a55f3c079f446533e683b48205e。实际SP3-d、L47、GPS、IGS20、10秒原生P/V，速度单位dm/s转m/s。冻结GPS/UTC闰秒及IERS-B/EOP，完整P/V从ITRS转GCRS；IGS20作为ITRF2020/ITRS对齐实现是显式框架约定。

01:00 Hermite括点00:59:52与01:00:02，使用后验2秒信息，是历史平滑初始化。GCRS初始位置m：`{initial[:3].tolist()}`；速度m/s：`{initial[3:].tolist()}`。初态文件SHA：`{sha(F/'initial_GCRS_local.npy')}`。插值及SP3路径预检结束后，正式worker只读该初态，不从未来SP3修正位置/速度。初始数组及逐点位置表仅本地保存。

读取已有Jan4 Direct13帧Open-loop、07—13更新7帧及作者同UTC参考场；源码`run_fourcastden_orbit_update_event_v1.providers`复用，不重跑任何forward。各自统计反归一化；原DEN g/cm³→kg/m³乘1000，Z/TIE ZG cm→m乘0.01。AI Z不是ZG，仍采用已验证的TN/DEN/Z/TLBC热力诊断重建原生ZG；参考使用作者ZG，未来参考ZG未补入AI。TLBC与作者未来辅助/驱动维持HINDCAST。

覆盖检查保存`field_coverage.csv`：所有分支时间连续、密度有限正、重建列有效；八列共同高度域及极区中心纬度范围逐查询检查。A假设为WGS84大地纬度/椭球高近似模型纬度/原生ZG，只在显式ProvisionalEventBridge中使用；正式接口仍EXTERNAL_DATUM_UNVERIFIED。

## 3. 资源门禁及实际执行

启动前实际可用内存、CPU任务与磁盘见`resource_preflight.json`。旧一小时实测外推6893.766秒，1.5系数10340.65秒，冻结总监督上限10500秒、RSS4GiB、输出200MiB、余盘20GiB；留120秒用于末尾验收。没有新下载或并发MPI/GPU任务。

SP3只读路径按10秒查询，加07左右极限，共12969/12969有效，最小顶部余量110681.350m。它仅是必要预检，不替代实际积分轨迹检查。

先A/B/C/D Base；完整721时刻、有限P/V、左右交接和查询验收后写入`base_gate.json`，再用实测Base时间估计剩余Tight预算，见`tight_budget_gate.json`，通过才开始Tight。每条轨迹只启动一次，不自动重试/恢复。所有四组都在07切成两段。

|组|精度|积分秒|含诊断秒|nfev|全部密度查询|
|---|---|---:|---:|---:|---:|
{perf}

监督墙钟{supervisor['wall_s']:.3f}秒，进程树峰值RSS{supervisor['peak_tree_RSS_bytes']/2**20:.3f}MiB；准备{json.loads((F/'preflight.json').read_text())['prepare_wall_s']:.3f}秒，含独立离线验收记录计算耗时{audit['recorded_compute_s']:.3f}秒，低于10500秒。精确存储清单见delivery inventory（轨迹数组与逐查询日志本地保留）。

## 4. 07事件与在线有效性

既有EventAwareDensity和event_segments核心均未修改。C左端07原预测、右端07更新参考状态分别独立保存；左段RHS不能使用右分支，即使恰好在07。B和D也绑定各自左/右截断时间序列；无跨事件插值。

全部8条轨迹位置、速度交接逐元素相同，跳变量严格0；B/C前361个状态位级一致。实际密度查询含RHS、接口两次事件RHS、721输出及两次显式极限，共{audit['all_queries']}次全部有效；A为0。逐查询时间括点、两帧四水平邻点、局地高度域均通过独立核对；无填零、外推、裁边或备用密度。

Tight C事件：密度{float(ev['rho_left_kg_m3']):.12g}→{float(ev['rho_right_kg_m3']):.12g} kg/m³（{float(ev['density_jump_fraction'])*100:.6f}%）；阻力加速度模{float(ev['drag_left_m_s2']):.12g}→{float(ev['drag_right_m_s2']):.12g} m/s²，向量跳变量模{float(ev['drag_vector_jump_m_s2']):.12g}m/s²。P/V不跳，后续速度与位置差逐步积累。该数值来自本轮自由轨迹，不沿用06:30初始化短例的7.762681%。

## 5. 全窗配对结果（Tight）

位置m、速度m/s；RMS是721个等间隔输出的描述统计，非观测精度、非独立重复试验。共同RAC参考为Tight NoDrag，R外向、C沿r×v、A=C×R。位置差方向不能直接当作阻力方向。

|比较|终点m|最大m|全窗RMS m|终点速度m/s|终点R m|终点A m|终点C m|
|---|---:|---:|---:|---:|---:|---:|---:|
{summary}

Updated−Open终点{float(c['terminal_m']):.9f}m。Open−D终点{float(b['terminal_m']):.9f}m，Updated−D终点{float(d['terminal_m']):.9f}m，终点差变化{effect['terminal_reduction_fraction']*100:.6f}%（正值为减小）。全窗RMS Open{effect['full_RMS_open_m']:.9f}m、Updated{effect['full_RMS_updated_m']:.9f}m；更新后RMS分别{effect['post_RMS_open_m']:.9f}/{effect['post_RMS_updated_m']:.9f}m。

07后360个输出点中，Updated更接近D有{effect['post_closer_samples']}点，更远有{effect['post_farther_samples']}点。更远的时间段为{intervals}。这是60秒采样判断，不证明两个输出间不存在短时反转，不删除不利时刻。事件前两方案相同，07点P/V相同，不把即刻参考大气零误差当作轨道改善。

### 分时效与事件左右

|比较|lead小时|事件侧|位置m|速度m/s|R m|A m|C m|
|---|---:|---|---:|---:|---:|---:|---:|
{leads}

六小时左右是同一轨道状态，仅大气/加速度不同；完整逐分钟数据及速度/RAC/分块RMS见`pair_curves.csv`、`lead_time_summary.csv`、`time_block_summary.csv`。

## 6. 冻结数值收敛

Base rtol1e-10，位置atol1e-3m/速度1e-6m/s，maxstep30s；Tight rtol1e-12，1e-5m/1e-8m/s，15s。共同输出60秒。沿用单轨最大位置差≤0.02m、六种配对差向量数值差≤Tight最大响应1%；速度差另报，没有捏造新的速度门槛。

|轨迹/配对|最大位置数值差m|最大速度数值差m/s|位置冻结限值m|通过|
|---|---:|---:|---:|---|
{conv}

独立脚本直接读取Base/Tight数组，以分量平方和复算四单轨和六配对。比较的是差向量，不是两个范数相减。{qual}。若某个模型响应与数值差相近，应报告当前分辨率不能可靠区分；不能用配对通过替代失败的单轨门槛，也不把数值差解释为大气模型误差。所有图自动标明整体数值门槛状态。

## 7. 物理含义与局限

密度变化通过`a_drag=−0.5 rho Cd A/m |v_rel|v_rel`影响阻力；零地固风下v_rel采用完整ITRS速度。密度和阻力曲线来自各自积分轨迹，每一步重新查询，不在SP3轨迹上查表后强行套入。07同一状态上阻力与密度同比变化；之后轨迹位置变化又改变查询位置，非阻力引力对位移的响应也参与耦合，所以RAC位置响应不能简单等同某方向受力。

更新使用未来TIE-GCM全球全状态，是离线理想重初始化，不是真实观测同化。不据单日Direct结果认定6小时最佳更新周期、不选择最优模型，也不推断全年、真实卫星或业务预测性能。AI热力高度重建与作者参考ZG表示差、小时/5°插值、ZG未知外部零面、实际气动/推力及漏项仍限制结论。

## 8. 验收、图表与复现

|门禁|状态|
|---|---|
{gates}

新增6项CPU阶段门禁测试通过：有效721帧放行、缺帧/NaN/事件重置/失败查询/错误时间拒绝Tight；未重复旧短时实验或旧事件单测。独立审计本身PASS不等于数值门槛PASS。冻结{audit['protected_assets_unchanged']}任务资产、{audit['historical_assets_unchanged']}历史科学资产SHA不变，原一小时结果包含在保护清单。

8张实际结果图：density_12h、drag_12h、updated_minus_open、reference_orbit_differences、RAC_12h、event_07UTC_detail、time_block_statistics、numerical_convergence。均在`results/fourcastden_orbit_update_12h_v1/`；`figure_sources.csv`含数据来源和PNG SHA。坐标/气动/参考不是观测真值等限制写入图注。

```bash
source scripts/activate_orbit.sh
python tests/test_fourcastden_orbit_update_12h.py
python scripts/run_fourcastden_orbit_update_12h_v1.py prepare
python scripts/run_fourcastden_orbit_update_12h_v1.py supervise
python scripts/analyze_fourcastden_orbit_update_12h_v1.py
python scripts/plot_fourcastden_orbit_update_12h_v1.py
python scripts/audit_fourcastden_orbit_update_12h_v1.py
python scripts/document_fourcastden_orbit_update_12h_v1.py
```

正式已用标签禁止重放；需复现应在新授权下使用新独立标签，不能删除历史目录。CPU分析不执行forward或轨道积分。输入与输出SHA、每组runtime/nfev/事件记录保留在实验目录，原始状态与逐查询位置表仅本地，不上传SP3/DNS/模型权重/凭据。

## 9. 下一步与停止

优先完善真实高度登记、同期气动/姿态/推力来源和受力准入，不直接扩展多日期大矩阵。若数值门槛失败，先独立设计数值误差定位/更严设置预算，需另授权，不能通过新指标替换旧门槛。多日期条件实验可在问题明确后预注册，不能替代真实物理准入。本轮结束停止，不追加24小时、多模型、真实轨道精度实验或训练。
'''
    path=ROOT/'reports/FOURCASTDEN_ORBIT_UPDATE_12H_V1.md';assert not path.exists();path.write_text(report)
    talk=f'''# 约3分钟组会讲稿：大气理想更新的12小时轨道影响

这次我们把此前已经通过的一小时跨事件接口，推进为真正的十二小时条件轨道传播。使用一月四日凌晨一点到下午一点已有的Direct大气预测，七点进行一次理想大气更新。四组分别无阻力、原预测密度、更新密度和TIE-GCM参考密度；卫星初态、力模型和合成气动参数完全一致。

实验不是重新训练网络，也没有使用未来精密轨道纠正卫星。初态来自事后精密轨道插值，随后十二小时完全积分。七点只改变大气场，位置速度严格连续。相同卫星位置上的密度跳变约{float(ev['density_jump_fraction'])*100:.2f}%，对应阻力加速度变化约{float(ev['drag_vector_jump_m_s2']):.3g}米每二次方秒。

阻力变化先累积成速度差，再在轨道动力学耦合下形成位置差。十二小时末更新与原预测轨道相差{float(c['terminal_m']):.3f}米。相对于TIE-GCM条件参考轨道，原预测终点差{float(b['terminal_m']):.3f}米，更新后为{float(d['terminal_m']):.3f}米。全窗RMS分别是{effect['full_RMS_open_m']:.3f}与{effect['full_RMS_updated_m']:.3f}米。我们还检查了中间时刻：更新后360个一分钟采样中有{effect['post_farther_samples']}个点更新组反而更远，因此要同时看全过程和终点，不能只挑有利结果。

为了判断差异是不是积分器造成的，我们按事前冻结的Base和Tight设置各做四组，共八条轨迹，并直接比较六种配对差向量。数值结论是：{qual}。未通过的结果会保留并明确标注，不为了获得通过而修改阈值。

所有密度查询均通过有效域检查；07点未跨分支插值，没有补零或换模型。但坐标映射仍采用披露的A假设，质量、面积和Cd仍是演示参数，TIE-GCM参考轨道也是模拟结果。因而这次测量的是大气输入变化对条件轨道的影响，不是实际Swarm轨道预测精度。

下一步应优先解决外部高度登记和真实气动、姿态与推力条件。如果需要进一步数值验证或多日期实验，也应先冻结预算和准入标准，不自动扩展计算。这样才能把工程链路逐步推进成可验证的真实卫星应用。
'''
    q=ROOT/'docs/FOURCASTDEN_ORBIT_UPDATE_12H_TALK.md';assert not q.exists();q.write_text(talk)
    print('report and talk saved; numeric gates retained',a['gates'])
if __name__=='__main__':main()
