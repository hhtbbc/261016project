"""Build evidence-linked Chinese report from finished high-order results."""
from pathlib import Path
import sys,json,csv
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_orbit_12h_abcd_dop853_closure_v1 import F,O
from prepare_fourcastden_swarm_observation_v1 import sha,dump

def main():
    a=json.loads((F/'analysis.json').read_text());e=json.loads((F/'effect_assessment.json').read_text());s=json.loads((F/'supervision.json').read_text());rows=list(csv.DictReader((O/'performance.csv').open()));p=json.loads((F/'protocol.json').read_text())
    report='''# 12小时四组DOP853高阶数值闭环 V1

## 1. 目的与实际范围

本轮只新增D_TIE-GCM Reference两条12小时DOP853轨道（max_step30/15秒），A/B/C六条高阶轨道只读复用，旧RK45八条轨道未改。所有结果仅是冻结假设下的条件模型响应，TIE-GCM条件轨道不是真实轨道真值。

2023-01-04 01:00—13:00UTC，每60秒输出，共721时刻；四组统一07:00分段。只更新大气，不重置卫星位置速度。A NoDrag不使用密度；B为原Direct连续预测；C在07以未来TIE-GCM参考全状态离线理想重初始化；D为作者参考DEN与**原生ZG**。这不是观测同化，也不能确定最佳更新周期。

## 2. 冻结输入、物理和数值配置

GCRS共同初态仍为原SP3历史HermiteP/V（00:59:52、01:00:02括点，含起点后2秒信息），仅作历史平滑初始化；传播后没有未来SP3反馈。初态SHA：'''+p['initial_SHA']+'''。

原H6、EGM2008既有40阶、日月第三体、时间/EOP/闰秒/常数、完整ITRS相对速度均不变；合成质量400kg、面积1m²、Cd2.2、零ITRS中性风。标签保留HISTORICAL_SP3_INITIALIZED_VIRTUAL_PROPAGATION / PROVISIONAL_COORDINATE_A / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST / FORCE_MODEL_INCOMPLETE / PROVISIONAL_EPHEMERIS。

D使用现有作者参考DEN（g/cm³乘1000转kg/m³）及原始ZG（cm乘0.01转m）；B/C仍使用各自TN/DEN/Z/TLBC热力诊断重建ZG。Z不当ZG，未用未来参考ZG补AI失效列。因此最终差异包含密度及高度表示来源差异，不能唯一归因于AI密度误差。正式外部接口仍EXTERNAL_DATUM_UNVERIFIED，实验仅显式A假设。

DOP853 rtol2.5e-13，分量atol位置1e-6m/速度1e-9m/s，max_step30/15秒。原单轨≤0.02m、配对差向量最大敏感性≤DOP15最大响应1%门槛不改。全部RAC使用冻结的旧A_NoDrag RK45 Tight共同基，不调整坐标系降低差异。

## 3. 前置检查与运行

A两条与B/C四条高阶原数组SHA逐条核对，旧97项输出和输入保护清单核验。读取已保存SP3真实路径的A假设经纬高，D预检4323/4323有效，最小顶部余量111616.158m；没有用固定高度代替轨道高度。实际积分仍逐RHS检查两时间帧×四水平邻列、纬度域/周期经度、原生ZG高度、DEN正值/有限性；禁止补零/外推/替换。

顺序D30→工程完整性及剩余预算门禁→D15。D30和D15各独立两段；无重试，不重用另一条轨迹前缀。监督上限6800秒、RSS4GiB、输出50MiB、磁盘余量20GiB。实际资源如下。

|配置|积分秒|含保存/诊断秒|nfev|全部密度查询|峰值单进程RSS MiB|
|---|---:|---:|---:|---:|---:|
'''
    for r in rows:report+=f"|{r['mode']}|{float(r['integration_s']):.3f}|{float(r['total_s']):.3f}|{r['nfev']}|{r['all_density_queries']}|{float(r['peak_RSS_MiB']):.3f}|\n"
    report+=f"\n监督墙钟{s['wall_s']:.3f}秒，峰值进程树RSS{s['peak_tree_RSS_bytes']/2**20:.3f}MiB；新增查询{a['total_new_queries']}次全部有效。查询数含DOP连续输出额外阶段、2次事件RHS、721输出及2显式极限；不等同于纯nfev。预检和离线后处理另列记录，不混同纯积分成本。\n"
    report+='''
## 4. D单轨收敛与RK45独立对照

|比较|最大位置差m|终点差m|全窗RMS m|最大速度差m/s|
|---|---:|---:|---:|---:|
'''
    for label,r in [('DOP30−DOP15',a['singles']['D_Reference']),('旧RK45 Tight−DOP15',a['D_RK45_Tight_vs_DOP15'])]:report+=f"|{label}|{r['max_position_m']:.12g}|{r['terminal_m']:.12g}|{r['RMS_m']:.12g}|{r['max_velocity_m_s']:.12g}|\n"
    report+='''
两DOP设置差表示数值敏感性，不是严格误差上界；共用力模型不能验证共同物理误差。旧Base/Tight约0.24m的FAIL不追溯改写。D与高阶参考的比较为既有较大步长累计截断误差解释增加独立证据，不替代此前因果限制。

## 5. 四组与六配对统一结果

|配对DOP15|终点m|全窗RMS m|最大m|终点R/A/C m|
|---|---:|---:|---:|---|
'''
    summaries=list(csv.DictReader((O/'comparison_summary.csv').open()))
    for r in summaries:
        if r['comparison'].endswith('DOP15') and ' minus ' in r['comparison'] and not any(x in r['comparison'] for x in ['DOP30','RK45']):report+=f"|{r['comparison']}|{float(r['terminal_m']):.9f}|{float(r['RMS_m']):.9f}|{float(r['max_position_m']):.9f}|{float(r['terminal_R_m']):+.9f}/{float(r['terminal_A_m']):+.9f}/{float(r['terminal_C_m']):+.9f}|\n"
    report+='\n|配对|效应差向量最大数值差m|相对敏感性%|1%门槛m|状态|\n|---|---:|---:|---:|---|\n'
    for r in a['pairs']:report+=f"|{r['comparison']}|{r['max_effect_vector_sensitivity_m']:.12g}|{100*r['relative_sensitivity_fraction']:.9g}|{r['limit_m']:.9g}|{r['gate']}|\n"
    report+='''
先在每个时刻减完整向量，再对两种配置的效应向量作差并求模；未用两个范数之差替代。零/小效应不加分母下限，逐点绝对差保留。

## 6. 状态更新全过程效果

|指标|Open相对D|Updated相对D|相对缩小|
|---|---:|---:|---:|
'''
    for k,label,red in [('terminal_m','12h终点','endpoint_reduction_percent'),('RMS_m','全窗RMS','full_RMS_reduction_percent'),('post6h_RMS_m','07后严格>07的6h RMS','post6h_RMS_reduction_percent')]:report+=f"|{label}|{e['open'][k]:.12g}m|{e['updated'][k]:.12g}m|{e[red]:.8f}%|\n"
    report+=f"\n旧RK45终点9.177625127m→4.482434833m、缩小51.15909867%，新高阶结果见上表。终点相对旧值分别变化{e['open']['terminal_m']-9.177625127182976:+.12g}m、{e['updated']['terminal_m']-4.4824348326751995:+.12g}m。\n\n07之后360个60秒采样点：更近{e['closer_samples']}、更远{e['farther_samples']}、相等{e['equal_samples']}。这些沿轨点存在时间相关性，不是独立重复实验。恶化区间：{json.dumps(e['farther_intervals'],ensure_ascii=False)}。没有删除反向时段；因此不能说更新后每个时刻都更接近D。全窗/后窗RMS与终点分别报告，不用终点替代全过程。\n"
    report+='''
## 7. 物理解释与07事件

密度改变→同相对速度下阻力加速度改变→速度差累积→位置差，并由共同轨道引力动力学耦合形成RAC响应。阻力沿相对气流反向，不等于位置响应仅沿该方向。C事件同状态密度约增加7.762797%，阻力同比改变；P/V逐元素连续，所有组均分段。事件后短时反向变化不能仅由瞬时密度大小判断，既有位置/速度历史及后续密度共同参与。

差异主要表现为沿轨位置响应，终点RAC详见六配对表与完整曲线。该结论是条件模型差异，不是相对SP3的真实精度，也不能证明模拟大气就是真实大气。

## 8. 验收与限制

|指标|实际状态|
|---|---|
'''
    for k,v in a['gates'].items():report+=f'|{k}|{v}|\n'
    report+=f"\n冻结任务资产{a['protected_unchanged']}项、历史科学资产{a['historical_unchanged']}项SHA保持；A/B/C未重跑、原始数组不改。科学训练READY=False、正式高度EXTERNAL_DATUM_UNVERIFIED、真实Swarm验证BLOCKED继续保留。\n"
    report+='''
## 9. 下一步决策

本窗口的四组高阶数值闭环完成后，应优先补齐外部ZG零面登记、真实气动质量/迎风面积/Cd、姿态与推进器及完整受力证据，再设计真实卫星独立验证。多日期条件重复可检验窗口依赖，但不能代替这些物理准入；本轮不自动扩展。若任何高阶门槛FAIL，先解释该失败，不以条件终点改善掩盖。

## 10. 文件与复现

主结果results/orbit_12h_abcd_dop853_closure_v1/，实验/审计experiments/orbit_12h_abcd_dop853_closure_v1/。10图及来源SHA见figure_sources.csv，逐分钟向量/RAC见comparison_curves.csv（公开无损xz），六配对见pair_convergence.csv，改善/恶化见update_benefit_timeseries.csv。原始轨道NPZ、查询位置日志只留本地，不上传SP3/DNS/权重。

```bash
source scripts/activate_orbit.sh
python scripts/run_orbit_12h_abcd_dop853_closure_v1.py prepare
python scripts/run_orbit_12h_abcd_dop853_closure_v1.py supervise
python scripts/analyze_orbit_12h_abcd_dop853_closure_v1.py
python scripts/plot_orbit_12h_abcd_dop853_closure_v1.py
python scripts/document_orbit_12h_abcd_dop853_closure_v1.py
```

已完成tag拒绝重放；复现需独立新授权与新tag。旧结果和FAIL记录不覆盖，Git只同步轻量代码/报告/摘要/图，不强推。
'''
    target=ROOT/'reports/ORBIT_12H_ABCD_DOP853_CLOSURE_V1.md';assert not target.exists();target.write_text(report)
    talk=f'''# 3分钟组会汇报稿：四组12小时高阶数值闭环

李总，这轮我们补齐了最后一组TIE-GCM参考密度驱动轨道，并没有重跑原来的AI预测或前三组轨道。现在四组轨道在同样初态、同样受力和两套高阶数值配置下，能够统一比较。

此前我们发现，普通积分设置之间单条轨道相差约24厘米，虽然AI状态更新产生的配对差异比较稳定，但不能据此宣布所有数值验证通过。因此我们依次给无阻力、AI连续预测、AI理想更新建立独立高阶参考，这轮最后补上TIE-GCM条件参考。

本轮D组两套步长的最大位置差为{a['singles']['D_Reference']['max_position_m']*1000:.6f}毫米，原冻结门槛是20毫米。六组轨道配对也独立检查了差向量，结果见验收表。旧普通积分配置未通过的历史结论仍然保留，没有改写。

高阶计算中，12小时末连续预测轨道与TIE-GCM条件轨道相差{e['open']['terminal_m']:.6f}米，理想更新后相差{e['updated']['terminal_m']:.6f}米，终点缩小{e['endpoint_reduction_percent']:.4f}%。全程RMS缩小{e['full_RMS_reduction_percent']:.4f}%。这为之前约51.16%的条件终点改善提供了独立高阶数值支持。

但更新不是每一刻都有利。07点后有{e['farther_samples']}个一分钟采样时刻反而更远，具体区间全部保留。大气更新会立即改变阻力加速度，但不会让卫星位置或速度跳变；随后的速度和位置响应会随轨道动力学累积，主要体现为沿轨差异。

最重要的限制是，这不是实际Swarm预测精度。我们仍然使用临时坐标假设和合成气动参数，而且更新用的是未来TIE-GCM参考全状态，不是实时观测同化。数值闭环解决了“这个条件效应是不是积分误差”的问题，没有解决“真实大气和卫星参数是否正确”的问题。下一步应优先补齐高度基准和真实气动、姿态与推力证据，再进入真实卫星精度验证。本轮停止，不自动追加模拟或训练。
'''
    q=ROOT/'reports/ORBIT_12H_ABCD_DOP853_CLOSURE_V1_TALK.md';assert not q.exists();q.write_text(talk)
if __name__=='__main__':main()
