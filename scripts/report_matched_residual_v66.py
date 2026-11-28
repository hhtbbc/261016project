"""Build a Chinese V66 report from observed receipts and metrics."""
import statistics

from run_validation_events_v66 import OUT,ROOT,write_once,require,load,sha,read_csv

MAIN=ROOT/'reports/THERMOSPHERE_MATCHED_RESIDUAL_TRAINING_V66.md'


def main():
    require(MAIN.resolve()==MAIN and not MAIN.exists(),'Report path')
    c=load(OUT/'checkpoint_manifest.json')
    v=load(OUT/'validation_run_receipts.json')
    audit=load(OUT/'independent_verification.json')
    sealed=load(OUT/'validation_sealing_manifest.json')
    milestone=read_csv(OUT/'training_milestones.csv')
    log=read_csv(OUT/'training_log.csv')
    diagnostics=read_csv(OUT/'train_diagnostic_metrics.csv')
    regional=read_csv(OUT/'regional_metrics.csv')
    layers=read_csv(OUT/'layer_metrics.csv')
    amplitude=read_csv(OUT/'correction_amplitude_analysis.csv')
    require(audit['matched_initial_and_sequence'] and sealed['DEN_reads']==0
            and sealed['targets']==12 and all(r['engineering']=='PASS' for r in v.values()),'Incomplete V66')
    train_rows=[]
    for arm,r in c.items():
        loss=[float(next(x['loss'] for x in milestone if x['arm']==arm and int(x['step'])==i))
              for i in (0,50,100,150,200)]
        dt=statistics.median(float(x['update_s']) for x in log if x['arm']==arm)
        train_rows.append(f"| {arm} | {r['updates']} | {r['supervised_wall_s']:.2f} | "
                          f"{r['sampled_tree_RSS_bytes']/2**20:.1f} | {dt:.4f} | "
                          +" → ".join(f'{a:.6f}' for a in loss)+" |")
    groups=('ALL','quiet','disturbed')
    compare=[]
    for e in groups:
        for lead in ('1','3','6'):
            x={r['method']:r for r in diagnostics if r['event']==e and r['horizon']==lead}
            p,lt=(float(x[a]['log_rmse']) for a in ('Persistence','LocalTimePersistence'))
            pc,lc=(float(x[a+'-Residual-CNN']['log_rmse']) for a in ('P','LT'))
            corr=[float(next(a['ratio'] for a in amplitude if a['arm']==k and a['event']==e
                         and a['horizon']==lead and a['domain']=='global')) for k in ('P','LT')]
            compare.append(f'| {e} | +{lead}h | {p:.6f} | {pc:.6f} | {pc/p-1:+.2%} | {lt:.6f} | '
                           f'{lc:.6f} | {lc/lt-1:+.2%} | {lc/pc-1:+.2%} | {corr[0]:.3f}/{corr[1]:.3f} |')
    cols=('north_polar','south_polar','low_density','ilev_28')
    by_region=[]
    for domain in cols:
        for method,base in [('P-Residual-CNN','P'),('LT-Residual-CNN','LT')]:
            rows=[r for r in regional+layers if r['event']=='ALL' and r['domain']==domain and r['method']==method]
            vals=[float(r[f'log_rmse_change_pct_vs_{base}']) for r in rows]
            by_region.append(f"| {domain} | {method} | "+' | '.join(f'{x:+.2f}%' for x in vals)+' |')
    per_event=[]
    for e in sorted({r['event'] for r in diagnostics}-set(groups)):
        vals=[]
        for method,base in [('P-Residual-CNN','P'),('LT-Residual-CNN','LT')]:
            rows=[r for r in diagnostics if r['event']==e and r['method']==method]
            vals.append('/'.join(f"{float(r[f'log_rmse_change_pct_vs_{base}']):+.2f}%" for r in rows))
        per_event.append('| '+e+' | '+' | '.join(vals)+' |')
    run_rows=[]
    for tag,r in v.items():
        run_rows.append(f"| {tag} / {r['event_id']} | {r['run_id']} | {r['final_step']:,} | {r['elapsed_s']:.1f} | "
                        f"{r['peak_RSS_bytes']/2**20:.1f} | {r['native_bytes']/2**30:.3f} | "
                        f"{r['file_count']} / {r['hourly_frames']} |")
    all_rows=[r for r in diagnostics if r['event']=='ALL' and r['method']=='LT-Residual-CNN']
    lt_more=sum(float(r['log_rmse_change_pct_vs_LT'])<0 for r in all_rows)
    extremes=[]
    for k in ('P','LT'):
        rows=[r for r in amplitude if r['arm']==k]
        r=max(rows,key=lambda x:float(x['ratio']))
        extremes.append(f"- {k} 修正 RMS/真实残差 RMS 最大值 {float(r['ratio']):.3f}，"
                        f"出现在 {r['event']}、+{r['horizon']}h、{r['domain']}。"
                        f"共 {sum(float(t['ratio'])>1 for t in rows)} 个已统计组合高于 1。")
    with MAIN.open('x') as f:
        f.write(f'''# V66 物理启发残差双臂 CPU 训练与验证生产

状态 V66_MATCHED_CPU_TRAINING_AND_VALIDATION_PRODUCTION_VERIFIED。训练与模型选择验证使用严格分离的运行家族。两组最终测试候选保留，未启动。

## 真实 CPU 训练

两臂共用 1027 参数 TinyDirectCNN、同一随机初始化权重、零输出层、同一 200 行抽样顺序、同一余弦纬度加权 log 残差 MAE、Adam 0.001、单截点 batch。V65 TRAIN 132 窗口及 140 唯一历史的逐层归一化保持。CPU 4 线程，固定种子 42。两臂 step 0 精确等于各自背景，所有迈步均完成。恢复 checkpoint 后输出逐元素一致，六个参数张量的 Adam 步计数均为 200。两臂事件曝光 {c['P']['exposure']}。资源监控为采样峰值。

| 臂 | 更新 | 监督墙钟秒 | 采样峰值 RSS MiB | 中位更新秒 | step 0/50/100/150/200 池化训练样本 loss |
|---|---:|---:|---:|---:|---|
{chr(10).join(train_rows)}

## TRAIN_DIAGNOSTIC 比较

以下为 log RMSE，百分比是相对各背景或 P-CNN 的变化，负值表示改善。全滑窗汇总采用面积权重，逐事件指标另单列。LT-CNN 在全窗三个时效中有 {lt_more} 个优于 LT 背景。完整数据中同时保留普通 LogLinear、绝对 RMSE、Relative RMSE 和覆盖率。

| 组 | 时效 | P | P-CNN | P-CNN 对 P | LT | LT-CNN | LT-CNN 对 LT | LT-CNN 对 P-CNN | 修正 RMS/真实残差 RMS，P/LT |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(compare)}

| 事件 | P-CNN 对 P，+1/+3/+6h | LT-CNN 对 LT，+1/+3/+6h |
|---|---|---|
{chr(10).join(per_event)}

| 区域 | 模型 | +1h | +3h | +6h |
|---|---|---:|---:|---:|
{chr(10).join(by_region)}

{chr(10).join(extremes)}

比值高于 1 标记汇总尺度上的幅度偏大。是否损害效果仍须与实测误差一起判断。没有使用模型选择验证数据选择轮次、超参数或模型。两臂都保留用于授权后的隔离验证。历史 V65 三种无训练基线复算最大差 {audit['V65_baseline_max_abs_log_RMS_diff']:.3g}。

## 验证生产与封存

| 事件 | run_id | 步数 | 墙钟秒 | 采样峰值 RSS MiB | NetCDF GiB | 卷 / 整点 |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(run_rows)}

四 rank 和 MPI 父进程全正常退出。已独立核验 68 卷、792 整点、运行时驱动、NetCDF 元数据和 SHA。两组维持相同 mareqx smax 源、Heelis、GSWM 及 60 秒网格。14 日预热与季节代理的物理收敛仍未证明。VAL2 为训练未覆盖的强扰动，只有一个冻结截点。

12 常规历史、12 未来目标、12 日周期历史位置均已登记，涉及 4 个截点。日周期历史有 {len(sealed['periodic_overlap'])} 条与较早截点目标重合。后续仅能在较早预测锁定后定向提取。原生目录密封，降权打开被拒绝，验证 DEN 数值未读取。V67 需先单独授权历史切片及隔离预测，再另行批准可信评价器的 12 个目标提取。

GFZ 回信及独立候选驱动方案见 THERMOSPHERE_GFZ_REPLY_AND_GAP_FILL_DESIGN_V66.md。2021 夏季未启动。V37、外部高度、ESA 原件认证、DART 与轨道门禁保持。无 GPU、额外积分、Swarm 读取、验证或最终测试标签解封。结果属于模型原生压力网格 HINDCAST。

原始积分、两臂 checkpoint、参数包、优化器状态、随机状态和校正数组留服务器。轻量表格、代码、SHA 与图表发布。
''')
    roles=load(ROOT/'experiments/thermosphere_multi_event_training_dataset_v65/event_role_registry.json')
    write_once(OUT/'next_stage_authorization.json',dict(
        V67='Separate history then scoring authorization; both models and comparing untrained backgrounds frozen.',
        labels=12,target_index='validation_target_record_index.csv',history_index='validation_history_record_index.csv',
        daily_index='validation_periodic_history_index.csv',periodic_requires_order=True,
        current_label_state='SEALED',trial_methods=['Persistence','LocalTimePersistence','DailyPersistence',
            'P-Residual-CNN','LT-Residual-CNN','LogLinear'],
        unused_final_tests=roles['LOCKED_INDEPENDENT_TEST'],GFZ_gap_policy_pending=True))
    print(MAIN)


if __name__=='__main__':
    main()
