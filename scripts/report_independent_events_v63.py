"""Publish measured engineering outcomes only, with scientific gates kept distinct."""
import json
from pathlib import Path

from run_independent_events_v63 import ROOT,OUT,EVENTS,load,require,sha,G,BASE


def main():
    # Use durable run and verification receipts, not expected counts as measurements.
    verification=load(OUT/'independent_verification.json') if (OUT/'independent_verification.json').is_file() else {}
    reports=ROOT/'reports'
    report=reports/'THERMOSPHERE_INDEPENDENT_EVENT_CPU_EXECUTION_V63.md'
    require(report.resolve()==report and OUT.resolve()==OUT,'Unsafe release destination')
    text=[
      '# V63 独立静稳和扰动事件 CPU 积分',
      '',
      f'起始本地 HEAD、origin/main 与远端 main 为 {BASE}。本轮只承接用户授权的两个 CPU 冷启动。'
      '各次采用 4 MPI × 1 OMP，没有 GPU、备用事件、Restart、重试、训练或预测。',
      '',
      '## 实际结果',
      '',
      '| 事件 | 工程状态 | run_id | 模型 UTC | 实测步数 | MPI rank | 耗时 | 峰 RSS | 原始 NetCDF | 主/次卷 | 整点 |',
      '|---|---|---|---|---:|---|---:|---:|---:|---:|---:|',
    ]
    details=[]
    accepted=[]
    for key,(event,*_) in EVENTS.items():
        path=OUT/f'{key}_run_receipt.json'
        if not path.is_file():
            failed=OUT/f'{key}_failure.json'
            details.append(f'- {event} 未取得工程通过收据。'+
                           (f'失败记录为 {failed.name}。' if failed.is_file() else '无失败收据。'))
            stage=OUT/f'{key}_claim.json'
            runtime=OUT/'data_local'/EVENTS[key][1]/'status.json'
            if stage.is_file() and runtime.is_file():
                c=load(stage)
                r=load(runtime)
                text.append(f"| {event} | {r['qualification']} | {c['run_id']} | — | — | — | "
                            f"{r['elapsed_s']:.1f} s | {r['peak_sampled_tree_rss_bytes']} B | — | — | — |")
                details.append(f"- {event} 监督器退出码 {r['returncode']}，停止原因 {r['stop_reason']}。")
            else:
                text.append(f'| {event} | 无通过收据 | — | — | — | — | — | — | — | — | — |')
            continue
        r=load(path)
        accepted.append(r)
        n=sum(x['kind']=='primary' for x in r['files'])
        m=sum(x['kind']=='secondary' for x in r['files'])
        t=len(r['time_index'])
        ranks='/'.join(str(x['returncode']) for x in r['ranks'])
        text.append(f"| {event} | {r['engineering']} | {r['run_id']} | {r['datetime_start']} 至 {r['datetime_end']} | "
                    f"{r['final_step']:,} | {ranks} | {r['elapsed_s']:.1f} s | "
                    f"{r['peak_RSS_bytes']/2**20:.1f} MiB | {r['native_bytes']/G:.3f} GiB | {n}/{m} | {t} |")
        details.append(f"- {event} 编排启动/退出 UTC {r['launch_UTC']} / {r['exit_UTC']}。MPI 父进程退出 {r['parent_exit']}。"
                       f"CPU user/system {r['CPU_user_s']:.1f}/{r['CPU_system_s']:.1f} 秒，"
                       f"整个运行目录 {r['total_workdir_bytes']/G:.3f} GiB。"
                       f"原始日志与输出在 {r['directory']}，身份见 {path.name}。")
        if r['warnings_unique']:
            details.append(f"  记录 {r['warning_line_count']} 条带警告/注意字样日志，保留在收据，未修改模型配置。")
        else:
            details.append('  各 rank 日志没有匹配 warning/caution 字样，已验收时间轴无缺口。')
    text.extend(['','## 过程、索引和封存','',*details,''])
    if verification:
        text.append(f"独立核对 {verification['native_volumes']} 卷、{verification['native_time_rows']} 条整点、"
                    f"{verification['cutoffs']} 个截点及 {verification['target_records']} 个目标记录。"
                    '原生纬经度、ilev、单位及 DEN 维度检查仅使用允许的元数据。'
                    '对 scalar GPI 输出独立重算，DEN 数值读取为零。')
        text.extend(['','运行根为 root 0700，事件目录为 0500，输出为 0400。'
                     '独立降权至 UID 65534 的进程尝试打开真实次历史卷并收到 EACCES，测试不读取内容。'
                     '特权保管账户仍有访问能力，后续 worker 必须使用最小权限及历史副本。'])
    text.extend([
      '', '## 科学准入与 V64 两阶段申请','',
      '静稳与扰动均使用相同 mareqx smax 春分代理初态和各自的官方 GPI。模型 ELF、Heelis、GSWM 和源时钟保持冻结。'
      '14 日预热仅为筛选下限，相同初态不会自动抵消非线性初态影响，工程通过不建立物理收敛或外部高度配准。',
      '',
      '两个事件均保持 LOCKED_INDEPENDENT_TEST_CANDIDATE。先单独授权可信提取器只读取冻结的 21 个历史场，'
      '在隔离进程中生成、锁定预测和评价配置，再单独授权可信评价器读取索引中的 21 个未来目标。'
      '日周期基线的 21 个 t+h−24h 额外历史记录在单独索引中，禁止并入主授权。',
      '',
      '冻结对照为 Persistence、两帧原值线性、两帧对数、三帧 OLS、固定衰减、地方时旋转及 V60 TinyDirectCNN。'
      '地方时旋转保持东移源采样 15° × (h+1)，对应 +1/+3/+6h 的 6/12/21 个网格格点。'
      '两个事件只能给出描述结果。任何据此修改方法或选模型的使用均将两事件记为已暴露先导，并另留新的最终锁定事件。',
      '',
      '仅当地方时旋转在新事件具有合理表现，才优先申请同结构对照普通 Persistence 残差和 z_LT + fθ(X)。'
      '可用特征为截至预测时刻的历史 log 密度、变化、原生 ilev、历史 Kp、F10.7 和地方时。'
      '最终事后驱动属于 HINDCAST，不能当作实时可用特征。这里未进行任何预测或训练。',
      '',
      'V55 交接状态见 handoff.json（如已验收）。GFZ Fobs 原缺失、ESA 精确 0504 与原件认证、'
      'ZG/GRS80、V37 正式评分、2022 夏季完整状态 FAIL、DART 及真实轨道门槛保持。',
      '',
      '资源限制由既有监督器按 0.2 秒采样和进程会话执行，RSS 是采样峰值，'
      '不将其描述为通用内核 cgroup 瞬时硬配额。墙钟在 5990 秒提前触发清理给 6000 秒预算留余量。'
    ])
    with report.open('x') as f:
        f.write('\n'.join(text)+'\n')


if __name__=='__main__':
    main()
