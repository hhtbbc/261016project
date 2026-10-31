"""Document verified actual event experiment, without launching propagation."""
from pathlib import Path
import csv,json
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/fourcastden_orbit_update_event_v1';O=ROOT/'results/fourcastden_orbit_update_event_v1'
def rows(name):return list(csv.DictReader((O/name).open()))
def main():
 a=json.loads((F/'independent_delivery_audit.json').read_text());assert a['status']=='PASS'
 analysis=json.loads((F/'analysis.json').read_text());sup=json.loads((F/'supervision.json').read_text());estimate=json.loads((F/'twelve_hour_estimate.json').read_text())
 pair={r['comparison']:r for r in rows('pair_summary.csv') if r['mode']=='tight'};j=next(r for r in rows('event_density_drag_jump.csv') if r['mode']=='tight' and r['group']=='C_Updated')
 conv=rows('numerical_convergence.csv');performance=rows('performance.csv');c=pair['C_Updated minus B_Open'];bd=pair['B_Open minus D_Reference'];cd=pair['C_Updated minus D_Reference']
 table='\n'.join('|'+r['comparison']+'|'+ '|'.join(f"{float(r[k]):.9f}" for k in ['terminal_m','max_m','RMS_m','terminal_R_m','terminal_A_m','terminal_C_m'])+'|' for r in pair.values())
 cv='\n'.join(f"|{r['comparison']}|{float(r['error_max_m']):.9g}|{float(r['limit_m']):.9g}|{r['passed']}|" for r in conv)
 perf='\n'.join(f"|{r['group']} {r['mode']}|{float(r['integration_s']):.3f}|{r['nfev']}|{r['all_density_queries']}|" for r in performance)
 report=f'''# FourCastDEN理想状态更新的跨事件条件轨道实验 V1

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

SP3路径预检查1089/1089有效，最小顶高余量115736.484m；不替代在线检查。实际在线加输出/接缝诊断共{a['all_online_density_queries']}次密度查询全部有效，包含两帧四水平邻点八列检查；A从不调用密度。完整记录`*_queries_local.csv`只保留本地。独立检查所有left时间括点≤07、right≥07，B/C事件前状态位级一致。

Tight C事件同一卫星位置上，密度由{float(j['rho_left_kg_m3']):.12g}变为{float(j['rho_right_kg_m3']):.12g} kg/m³，跳变{100*float(j['density_jump_relative']):.6f}%。阻力加速度模由{float(j['drag_left_norm_m_s2']):.12g}变为{float(j['drag_right_norm_m_s2']):.12g} m/s²；向量跳变量模{float(j['drag_jump_vector_norm_m_s2']):.12g} m/s²。同一瞬间相对速度连续，阻力与密度同比例变化独立核验通过。全部8条P/V交接差均严格0；无重复/遗漏时间段。

## 实际轨道差异（Tight）

RAC采用共同A无阻力轨迹定义，R径向向外、C沿r×v、A=C×R。三维范数和分量均m；全段RMS是61个等间隔输出点的描述性统计。

|比较|终点m|最大m|全段RMS m|终点R m|终点A m|终点C m|
|---|---:|---:|---:|---:|---:|---:|
{table}

Updated−Open终点{float(c['terminal_m'])*1000:.6f}mm。相对D条件轨道，Open终点{float(bd['terminal_m'])*1000:.6f}mm，Updated终点{float(cd['terminal_m'])*1000:.6f}mm。上述表同时给出全段，不能把终点更接近外推成所有时刻更优，也不等同观测精度改善。

## 数值独立核验

|轨迹/配对|最大Base/Tight差m|冻结限值m|通过|
|---|---:|---:|---|
{cv}

单轨4项、配对6项全部PASS；独立脚本从原保存状态重新计算配对向量差，不读取汇总范数替代计算。数值差不能解释为大气误差；这里模型间条件响应通过原1%分辨门槛。

## 资源与命令

|组/精度|实际积分s|求解器nfev|全部密度查询数|
|---|---:|---:|---:|
{perf}

监督墙钟{sup['wall_s']:.3f}s；准备7.411s；截至独立审计记录的预算耗时{a['recorded_compute_budget_used_s']:.3f}s <1800s。实际内存和磁盘见`supervision.json`/`worker_complete.json`，未增加GPU/MPI任务。查询数包括求解器调用、分段接口2次事件RHS、61输出及2接缝诊断；A为0，未隐瞒额外诊断调用。

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

历史{a['historical_assets_SHA_unchanged']}项及任务冻结{a['task_assets_SHA_unchanged']}项SHA不变。5张PNG完整性通过，来源见`results/fourcastden_orbit_update_event_v1/figure_sources.csv`。报告/图为新增，不覆盖旧实验。原始轨迹、初态和逐查询位置表本地忽略，不公开。

## 12小时准入与下一步

短时跨事件机制PASS；完整12小时条件传播仅PARTIAL/需另授权，正式真实轨道BLOCKED。四组Base/Tight按本次实测外推约{estimate['assumption_A_4_groups_base_tight_estimated_s']:.1f}s，1.5安全系数{estimate['assumption_A_1point5_safety_s']:.1f}s；A/B两坐标假设共用无阻力的7组Base/Tight约{estimate['assumptions_A_B_7_groups_base_tight_estimated_s']:.1f}s。它们不是已测12h耗时，超过当前1800s预算。

Jan4 Direct分支现有帧及重建列支持见`twelve_hour_data_support.csv`，不等于12h自由积分路径100%覆盖；未来须先冻结12h初态/覆盖、独立预算并在线拒绝无效列。A/B可用于条件敏感性，不能择优当正式坐标；本轮不重跑历史A/B查询。其他模型/日期热力无效列问题不能套用本次Jan4 Direct成功，不能静默补洞。

真实Swarm轨道仍缺：ZG外部参考面登记、同期可靠质量/有效面积/姿态/Cd/推力条件、完整受力及独立参考评价。不得用本窗口未来SP3拟合Cd/密度比例/高度偏移。当前最有价值的下一实验是经授权、冻结预算的Jan4 Direct长窗条件传播与独立数值收敛，同时继续解决外部登记；不是立即声称真实精度或开展训练。本轮完成即停止。
'''
 p=ROOT/'reports/FOURCASTDEN_ORBIT_UPDATE_EVENT_V1.md';assert not p.exists();p.write_text(report)
 talk=f'''# 3分钟组会汇报：大气更新如何影响轨道

本轮我们把前期的大气预测更新真正接入了轨道积分。实验选取2023年1月4日06:30到07:30，在07点设置一次理想大气状态更新。四组分别不加阻力、采用原AI预测密度、采用更新后的AI密度，以及采用TIE-GCM参考密度。各组卫星初态、动力学和气动参数完全相同。

这里的卫星初态来自历史精密轨道插值，但质量400公斤、面积1平方米、阻力系数2.2是冻结的演示参数，因此它是虚拟条件实验，不是真实Swarm精度验证。外部高度映射也仍然是假设。

大气更新为什么影响轨道？阻力与密度成正比，同时受迎风面积、质量和相对速度影响。07点同一个卫星位置上，更新使密度增加约{100*float(j['density_jump_relative']):.2f}%，阻力加速度也同比增加，变化量约{float(j['drag_jump_vector_norm_m_s2']):.3g}米每二次方秒。这并不会让卫星位置突然跳一下，只有加速度可以跳变。我们让积分器在07点停下，再用完全相同的位置速度接着积分，左右状态逐元素一致。

之后阻力差逐渐积累为速度差，再积累为位置差。一小时末更新组与原预测组相差约{float(c['terminal_m'])*1000:.3f}毫米。与参考密度驱动的条件轨道相比，原预测组终点差{float(bd['terminal_m'])*1000:.3f}毫米，更新组为{float(cd['terminal_m'])*1000:.3f}毫米。请注意，参考轨道也是模型计算，不能把这些毫米数叫作真实预测误差。

为确认不是积分误差，我们做了Base和Tight两套设置，共八条轨迹。四项单轨和六项配对收敛门槛全部通过；所有实际密度查询有效，事件前更新组和原预测组完全一致，没有未来状态提前泄漏。

这次证明的是：大气更新、阻力变化和连续轨道状态之间的数值链路能正确工作。下一步可以在另行预算和覆盖检查后扩展长窗，观察误差累积。但正式真实卫星验证还需要解决高度登记、气动面积、姿态、Cd和推力条件；本轮没有训练模型，也没有开展十二小时传播。
'''
 q=ROOT/'docs/FOURCASTDEN_ORBIT_UPDATE_EVENT_TALK.md';assert not q.exists();q.write_text(talk)
 print('report and talk written')
if __name__=='__main__':main()
