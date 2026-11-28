"""Produce publication report and lightweight receipts after successful V65 verification."""
from datetime import timedelta
from pathlib import Path

from run_native_density_baselines_v59 import read_csv
from run_training_events_v65 import EVENTS, OUT, ROOT, START, load, require, sha, write_once

REPORT=ROOT/'reports/THERMOSPHERE_MULTI_EVENT_TRAINING_DATASET_V65.md'


def main():
    require(OUT.resolve()==OUT and REPORT.resolve()==REPORT and not REPORT.exists(),'V65 report path')
    q=load(OUT/'data_quality_report.json')
    verified=load(OUT/'independent_verification.json')
    resources=load(OUT/'training_data_resources.json')
    require(verified['all_four_PASS'] and len(list((OUT/'figures').glob('*.png')))==8,'Incomplete dataset')
    raw={}
    total=0
    ranks=0.
    samples=load(OUT/'event_sampling_plan.json')['event_windows']
    reductions=read_csv(OUT/'residual_summary.csv')
    comparisons={(r['event'],int(r['horizon'])):float(r['LT_reduction_pct']) for r in reductions}
    strata=read_csv(OUT/'residual_comparison.csv')
    summary=[]
    lines=[]
    residual_rows=[]
    weak=[]
    for tag,(event,*_) in EVENTS.items():
        path=OUT/'run_receipts'/f'{tag}_run_receipt.json'
        r=load(path)
        total+=r['native_bytes']
        ranks+=r['CPU_user_s']+r['CPU_system_s']
        s={k:v for k,v in r.items() if k not in ('time_index','files','command')}
        s.update(tag=tag,receipt_SHA256=sha(path),primary=sum(f['kind']=='primary' for f in r['files']),
                 secondary=sum(f['kind']=='secondary' for f in r['files']),hours=len(r['time_index']),
                 sample_count=samples[event],target_count=3*samples[event])
        summary.append(s)
        raw[tag]=[r[k] for k in ('elapsed_s','native_bytes')]
        lines.append(f"| {tag} / {event} | {r['run_id']} | {r['final_step']:,} | {r['elapsed_s']:.1f} | "
                     f"{r['peak_RSS_bytes']/2**20:.1f} | {r['native_bytes']/2**30:.3f} | "
                     f"{s['primary']}/{s['secondary']} | {s['hours']} | {s['sample_count']} |")
        residual_rows.append('| '+event+' | '+' | '.join(f'{comparisons[event,h]:+.2f}%' for h in (1,3,6))+' |')
        lt=[x for x in strata if x['event']==event and x['horizon']=='6' and x['method']=='LocalTimePersistence']
        worst=max(lt,key=lambda x:float(x['rms']))
        worst_l=max((x for x in lt if x['domain'].startswith('ilev')),key=lambda x:float(x['rms']))
        weak.append(f"- {event} 的 +6h 残余 RMS 最大分区为 {worst['domain']}（{float(worst['rms']):.5f}），"
                    f"最大原生层为 {worst_l['domain']}（{float(worst_l['rms']):.5f}）。")
    write_once(OUT/'run_receipt_summary.json',summary)
    residual_rows.extend('| '+cls+' | '+' | '.join(f'{comparisons[cls,h]:+.2f}%' for h in (1,3,6))+' |'
                         for cls in ('quiet','disturbed','ALL'))
    wall=sum(v[0] for v in raw.values())
    text=f"""# V65 四个训练事件的真实 CPU 积分和原生 DEN 数据集

状态为 V65_MULTI_EVENT_TRAINING_DATASET_COMPLETE_VERIFIED。起始 Git 提交为 {START}。

## 真正执行的四次积分

| 事件 | run_id | 步数 | 墙钟 s | 采样 RSS MiB | NetCDF GiB | primary/secondary | 整点记录 | 滑窗 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(lines)}

四次独立冷启动，全部工程 PASS，各 4 MPI ranks × 1 OMP 线程，顺序 T1 至 T4。监控以约 0.2 秒为采样间隔，RSS 数值是进程树采样峰值。累计 {wall:.1f} 秒、{ranks/3600:.2f} 实际 CPU 核小时，原生文件 {total/2**30:.3f} GiB。共有 140 卷及 1,632 条暖态整点记录。四组共 97,920 步。运行时官方 observed F10.7 与 definitive Kp 对照已独立复算，保留完整运行收据与 SHA。

四组沿用 V62 已核实的 mareqx smax 第 80 日源初态。官方归档确有 sepeqx 和 decsol 资料，已审查其网格和源时钟，均未进入本次冷启动政策。九月和十一月明确属于用春分初态作季节代理，春季场也无对应事件成熟初态。最短 14 天仅为选窗约束。V65 没有第二初态，不能据此确认完整状态收敛。

## 数据集

原 11 个固定截点全部保留。仅按原生 UTC、事件核心开区间及 14 日起始约束冻结 {q['windows']} 个相关滑窗，含 {q['targets']} 条目标关联。共有 {q['unique_frames']} 个唯一时刻场，唯一历史 {q['unique_history']}、唯一目标 {q['unique_targets']}，双重身份 {q['history_target_overlap']}。历史/目标重合分别占相应唯一集合 {q['shared_fraction_of_history']:.2%}/{q['shared_fraction_of_targets']:.2%}。全部关联中有 {q['repeated_all_links']} 次超出唯一场数的重复关联。独立样本单位为四个事件。

获准核心 DEN 无无效格点。SI 范围 {q['min_kg_m3']:.4g}–{q['max_kg_m3']:.4g} kg/m³。所有原生场、log DEN、索引与两种残差张量保留服务器，合计 {resources['array_bytes']/2**20:.2f} MiB。转换为 float32 的最大相对差为 {resources['max_relative_float32_error']:.3g}。独立复核 {verified['residual_checks']} 个残差场，从 float32 输入重算的最大差为 {verified['max_residual_float32_delta']:.3g}。主归一化使用唯一 TRAIN 历史场，重复曝光统计作为敏感性对照。

## 训练诊断

地方时旋转相对普通 Persistence 的 log 残差 RMS 降幅，正值表示减小。三种无训练基线及南北极、逐层分布、分位数、经向滞后相关和各事件 SSE 份额分别保存。统计仅为 TRAIN_DIAGNOSTIC。

| 事件 | +1h | +3h | +6h |
|---|---:|---:|---:|
{chr(10).join(residual_rows)}

{chr(10).join(weak)}

首选先等概率抽事件，再在事件内均匀抽截点。相同随机采样序列给两个背景模型。四组事件各占 25%，静稳与扰动各占 50%。T3 仅有六个相关滑窗，均衡其曝光不能增加独立扰动事件数。DailyPersistence 未读取额外历史。

## V66 准入与后续数据

本训练数据可供另行授权的 CPU 同结构对照使用。两臂以 V60 1,027 参数 CNN 为起点，3 帧 log DEN、训练逐层归一化、余弦加权 log 残差 MAE、相同随机初始化、Adam 0.001、每臂 200 更新，仅改变 P/LT 残差背景。V60 的 80 步耗时 13.56 秒，线性估算每臂更新约 34 秒，实际还需加载与验证，每臂候选运行上限 600 秒。无本轮训练实测。

下一轮若需模型选择验证，优先申请 quiet_20220301T21、disturbed_20211103T21 两组 CPU 数据生产。最终锁定测试保留 quiet_20231009T21、disturbed_20231105T09。验证及测试尚缺实际输出、身份验收及各自标签授权。强扰动是对中等扰动训练集的分布外挑战。两组 V64 先导结果保持其独立身份。

V37、2021 GFZ Fobs 缺测、ESA 0504 和来源认证、ZG 外部高度、Restart、DART 及轨道门禁保持。四组仅为原生压力网格 HINDCAST。GPU、未授权积分、Swarm 标签读取、验证测试 DEN 读取及正式神经网络训练均为零。V55 staging 记录见执行授权收据。

完整运行收据、数据与图表位于 experiments/thermosphere_multi_event_training_dataset_v65。原始 NetCDF 和训练张量仅保留服务器。
"""
    with REPORT.open('x') as f:
        f.write(text)
    files=[p for p in OUT.rglob('*') if p.is_file() and (OUT/'data_local') not in p.parents]
    files.append(REPORT)
    write_once(OUT/'publication_SHA256.json',{str(p.relative_to(ROOT)):{'SHA256':sha(p),'bytes':p.stat().st_size}
                for p in sorted(files)})
    print(REPORT)


if __name__=='__main__':
    main()
