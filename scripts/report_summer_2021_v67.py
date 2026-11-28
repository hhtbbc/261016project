"""Render V67 summer report and separate next-run proposal from real receipts."""
from collections import Counter

from run_summer_2021_v67 import OUT,ROOT,V51,load,require,write_once
from run_native_density_baselines_v59 import read_csv,table

REPORT=ROOT/'reports/THERMOSPHERE_SUMMER_2021_RESEARCH_FILL_EXECUTION_V67.md'


def main():
    require(REPORT.resolve()==REPORT and not REPORT.exists(),'Report path')
    rec=load(OUT/'summer_run_receipts.json')
    result=load(OUT/'initial_condition_summary.json')
    a=read_csv(OUT/'initial_condition_sensitivity_metrics.csv')
    heights=read_csv(OUT/'height_metrics.csv')
    b=read_csv(V51/'future_analysis/hourly.csv')
    bh=read_csv(V51/'future_analysis/height.csv')
    global_at=lambda rows,key,agecol: {r[key]:r for r in rows if r[agecol]=='504' and r['region']=='global'}
    left=global_at(a,'variable','hour')
    right=global_at(b,'variable','hour_V50')
    fixed1=global_at(heights,'height_km','hour')
    fixed2=global_at(bh,'height_km','hour_V50')
    comparisons=[]
    for k in ('DEN','TN','WIND_VECTOR','O1','O2','N2','HE','ZG','DEN_ZG_450km'):
        a0,b0=(fixed1['450'],fixed2['450']) if k=='DEN_ZG_450km' else (left[k],right.get(k))
        relative=k in ('DEN','O1','O2','N2','HE','DEN_ZG_450km')
        metric='relative_P95' if relative else 'RMSE'
        scale=100 if relative else .01 if k in ('ZG','WIND_VECTOR') else 1
        value=lambda x:float(x[metric])*scale if x and x[metric] else None
        comparisons.append(dict(variable=k,comparison_metric='relative_P95_percent' if relative else
                                'RMSE_m' if k=='ZG' else 'RMSE_m_s' if k=='WIND_VECTOR' else 'RMSE_K',
                                V67_2021=value(a0),V51_2022=value(b0),
                                V67_coverage=float(a0['coverage']),V51_coverage=float(b0['coverage']) if b0 else None))
    table(OUT/'cross_year_target_comparison.csv',comparisons)
    run_lines=[]
    for role,r in rec.items():
        run_lines.append(f"| {role} | {r['run_id']} | {r['final_step']:,} | {r['elapsed_s']:.1f} | "
                         f"{r['peak_RSS_bytes']/2**20:.1f} | {r['native_bytes']/2**30:.3f} | {r['volumes']} / {r['hourly']} |")
    lines=[]
    for r in comparisons:
        b0=r['V51_2022']
        lines.append(f"| {r['variable']} | {r['comparison_metric']} | {r['V67_2021']:.5g} | "
                     f"{'—' if b0 is None else format(b0,'.5g')} | {r['V67_coverage']:.2%} |")
    gate=read_csv(OUT/'native_gate_cells.csv')+read_csv(OUT/'height_gate_cells.csv')
    fail=Counter((r['variable'],r['region'],r['level']) for r in gate if r['passed']=='False')
    most=fail.most_common(8)
    wall=sum(r['elapsed_s'] for r in rec.values())
    cpu=sum(r['CPU_user_s']+r['CPU_system_s'] for r in rec.values())
    size=sum(r['native_bytes'] for r in rec.values())
    gpi_diff=max(max(r['runtime_GPI_max_abs'].values()) for r in rec.values())
    target_budget=rec['A2']['elapsed_s']
    target_storage=rec['A2']['native_bytes']
    physical_followup=('全状态未通过，保留分层失效分析。先做固定初态驱动对照，再依据科学目的评估是否延长预热，避免两因素同时变更。'
                if result['FULL_STATE_SEED_SENSITIVITY']=='FAIL' else
                '现有门槛结果不支持自动延长预热。先隔离补值驱动差异，仍需另一授权。')
    with REPORT.open('x') as f:
        f.write(f'''# V67 2021 夏季方案 A 补值驱动双初态积分

2021-05-31 00Z 至 06-23 00Z，21 日预热加两日目标期，60 秒步长。独立两次 CPU 冷启动，4 MPI × 1 OMP 串行，无重试；A1 为 mareqx smax，A2 为 junsol smax。复用 V51 核实过的源时钟、物理模型和输出策略。2021 双初态运行为 PHYSICS_SENSITIVITY_ONLY，独立于 AI 数据集。

| 臂 | run_id | 步数 | 墙钟 s | 进程树采样峰值 RSS MiB | NetCDF GiB | 卷 / 暖态小时 |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(run_lines)}

合计 {wall:.1f} 秒、{cpu/3600:.2f} 实际 CPU 核小时、{size/2**30:.3f} GiB 原生文件。两组四 rank 和父进程正常退出。94 卷及 1,104 暖态小时通过独立工程核验。两组实际运行时太阳与地磁驱动相对 GFZ+批准方案 A 重算最大绝对差 {gpi_diff:.3g}。研究者补值仅 05-09 的 76.0 与 06-16 的 77.0 sfu，原始 GFZ 快照不变，原观测仍缺测。A 文件与 V66 冻结候选 SHA 一致。

## V51 门槛和跨年参照

在读取物理字段前冻结了 {result['unique_UTC']} 个 V51 同历日同小时的采样位置，列为两臂逐条清单。允许 DEN、TN、UN/VN、O1/O2/N2/HE、ZG，原生单位和字段校验保留。最后 25 时次采用原 V51 的区域层位 95% 门槛，DEN 和组分严格 <5%，TN <10 K，矢量风 <20 m/s，组分 1e−8 floor，共同内部 ZG 无外推及末期全域 log RMSE OLS 趋势。ZG 本身为附加诊断，无外部登记或新验收门槛。

21 日目标时刻 06-21 00Z 的全球对照如下。2022 来自 V51 已冻结结果，2021 含研究者补值，差异不能单独归因于太阳活动。

| 字段 | 指标 | 2021 方案 A | 2022 V51 | 2021 有效覆盖 |
|---|---|---:|---:|---:|
{chr(10).join(lines)}

2021 全状态 **{result['FULL_STATE_SEED_SENSITIVITY']}**，有限密度初态不敏感 **{result['DENSITY_LIMITED_INSENSITIVITY']}**。失败计数 {result['failed_cells_by_variable']}，有效验收单元 {result['evaluated_gate_cells']:,}，空单元 {result['empty_gate_cells']:,}。最集中失败组合和计数 {most}。固定高度末期斜率为 {result['late_slopes']}。V51 2022 保持全状态 FAIL、有限密度 SUPPORTED，失败 118 单元。新结果的独立统计、门槛及固定高度检查共 {result['independent_checks']:,} 项。

{physical_followup}

## 最小 A/B 驱动对照

建议后续独立授权，以 A2 的 junsol smax 固定初态，复用 A2 输出，只另运行一次方案 B。选择依据是夏至附近季节匹配，并避免把初态差异引入驱动对照。预计约 {target_budget/3600:.2f} 小时、{target_storage/2**30:.2f} GiB，比较同一冻结字段和 UTC，报告 DEN、TN、组分和内部 ZG。若确需识别初态与补值交互，再另授权 B/mareqx，一共两条新增 B 运行。当前没有启动 B。

未发生 Swarm 标签读取、评分、GPU、模型训练、额外积分或 Restart。2021 原始 GFZ observed 缺测、外部高度登记、ESA SP3 和来源认证、DART 及真实轨道门禁保持。
''')
    write_once(OUT/'next_stage_authorization.json',dict(
        approved_and_completed='A1+A2 with GFZ_FOBS_GAP_FILL_V1 candidate A only',
        candidate_B_run_authorized=False,minimum_extra_runs=1,fixed_seed='V67 A2 junsol smax',
        matched_A_run=rec['A2']['run_id'],estimated_seconds=target_budget,estimated_GiB=target_storage/2**30,
        scientific_scope='same V51 79 UTC and native internal DEN/TN/UN/VN/O1/O2/N2/HE/ZG',
        optional_interaction='an additional B/mareqx after separate authorization',
        gates_unchanged=True))
    print(REPORT)


if __name__=='__main__':
    main()
