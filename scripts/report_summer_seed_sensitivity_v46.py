"""Compose the lightweight V46 release from durable receipts."""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from verify_summer_seed_sensitivity_v46 import frame, hash_file, row_metrics
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'experiments/thermosphere_summer_seed_sensitivity_v46'
RESULT=OUT/'comparison'
GROUPS=('run_A_mareqx','run_B_junsol')
REPORT=ROOT/'reports/THERMOSPHERE_SUMMER_SEED_SENSITIVITY_V46.md'


def read(path):
    return json.loads(path.read_text())


def csv_read(name):
    with (RESULT/f'{name}.csv').open() as f:
        return list(csv.DictReader(f))


def fmt(v,scale=1):
    return f'{float(v)*scale:.6g}' if v != '' and v is not None else 'N/A'


def utc(value):
    return datetime.fromtimestamp(value,timezone.utc).isoformat()


def summarize():
    assert not REPORT.exists()
    plan=read(OUT/'frozen_pair.json')
    runs=[]
    for key in GROUPS:
        claim_path=OUT/f'{key}_claim.json'
        if not claim_path.exists():
            continue
        claim=read(claim_path)
        proc=OUT/key/'status.json'
        out=OUT/f'{key}_acceptance.json'
        status=read(proc) if proc.exists() else None
        acceptance=read(out) if out.exists() else None
        run=dict(group=key, **claim)
        if status:
            ranks=[read(p) for p in sorted((OUT/key).glob('rank_*_exit.json'))]
            run.update(wall_s=status['elapsed_s'],mpi_exit=status['returncode'],
                       peak_RSS_bytes=status['peak_sampled_tree_rss_bytes'],
                       cpu_user_s=status['children_cpu_user_s'],cpu_sys_s=status['children_cpu_system_s'],
                       stop_reason=status['stop_reason'],rank_exit=[r['returncode'] for r in ranks],
                       rank_start_UTC=utc(min(r['started_unix'] for r in ranks)) if ranks else None,
                       rank_end_UTC=utc(max(r['ended_unix'] for r in ranks)) if ranks else None)
            samples=status['samples']
            if samples:run['minimum_free_disk_bytes']=min(x['free_disk_bytes'] for x in samples)
        if acceptance:
            run.update(engineering=acceptance['overall'], model_UTC=acceptance['final_UTC'],
                       max_GPI_abs=acceptance['max_GPI_abs'],steps=acceptance['progress'][0]['final_step'],
                       NetCDF_file_count=len(acceptance['files']),
                       NetCDF_bytes=sum(x['bytes'] for x in acceptance['files']),
                       inventory=acceptance['files'])
        runs.append(run)
    fail=read(OUT/'failure.json') if (OUT/'failure.json').exists() else None
    analysis_error=read(OUT/'analysis_failure.json') if (OUT/'analysis_failure.json').exists() else None
    both=len(runs)==2 and all(r.get('engineering')=='PASS' for r in runs)
    verified=(RESULT/'independent.json').is_file()
    science=read(RESULT/'summary.json') if (RESULT/'summary.json').is_file() else None
    if both: engineer='V46_BOTH_RUNS_ENGINEERING_PASS'
    elif fail and runs: engineer='V46_ENGINEERING_FAIL' if len(runs)==1 else 'V46_PARTIAL_RUN'
    elif not runs: engineer='V46_NOT_LAUNCHED'
    else: raise ValueError('Running pair, publication must wait')
    verdict=science['status'] if verified and science else 'SEED_SENSITIVITY_INCONCLUSIVE'
    record=dict(engineering=engineer,sensitivity=verdict,runs=runs,scientific_analysis_verified=verified,
                runtime_failure=fail,analysis_failure=analysis_error,scope=plan['scope'],
                unchanged_V37_day_order=True,lambda_shrinkage_half=.5,unseen_density_reads=0,GPU=0)
    with (OUT/'result.json').open('x') as f: json.dump(record,f,indent=2)
    lines=['# V46 夏季双初态工程对照','',f'**{engineer} / {verdict}**。','',
           '本轮执行范围为经授权的 2022 夏季两组物理工程研究。各自最多一次启动，A 工程验收通过才可启动 B。V37 正式验证门禁和日期先后保持。',
           '','## 配置与原件','',
           '2022-06-07 00Z 至 06-23 00Z，60 s、23040 步。两组唯一配置差异为 SOURCE 与 SOURCE_START，统一使用 MPI=4、OMP=1、GPU=0、HEELIS、氦和冻结 GSWM。',
           '',f"- mareqx SHA256 `{plan['protocols'][GROUPS[0]]['source']['SHA256']}`，SOURCE_START=80 0 0。",
           f"- junsol SHA256 `{plan['protocols'][GROUPS[1]]['source']['SHA256']}`，SOURCE_START=172 0 0。",
           f"- 两组相同 GPI SHA256 `{plan['protocols'][GROUPS[0]]['GPI']['SHA256']}`。",
           '', '## 执行与工程验收','',
           '| 组别 | run_id | 墙钟分钟 | 峰值 RSS GiB | MPI / rank | 步数 | NetCDF |',
           '|---|---|---:|---:|---|---:|---:|']
    for r in runs:
        rs=r.get('peak_RSS_bytes')
        lines.append(f"| {r['group']} | {r['run_id']} | {fmt(r.get('wall_s'),1/60)} | {fmt(rs,2**-30)} | "
                     f"{r.get('mpi_exit','待验')} / {r.get('rank_exit','待验')} | {r.get('steps','待验')} | {r.get('NetCDF_file_count','待验')} |")
    if fail: lines+=['',f"执行阻碍为 `{fail['failure']}`。保留所有原件、进程收据和日志。"]
    if analysis_error: lines+=['',f"分析或图表阶段记录异常 `{analysis_error['error']}`。"]
    if both:
        lines+=['','逐组检查 17 primary、16 secondary 卷及 384 条暖态小时记录，首个 primary 通过冷源回显身份审查。',
                f"暖态模型驱动与冻结 GPI 的最大绝对差分别为 {runs[0]['max_GPI_abs']:.3g} 与 {runs[1]['max_GPI_abs']:.3g}。",
                '资源、时间戳、MPI 退出和 66 个原始输出 SHA 见 result.json。']
    source=read(OUT/'source_comparison.json')
    lines+=['','## 初态及日龄敏感性','',
            f"两份初态都无原生诊断 DEN。初态 TN 差 B–A 的面积加权平均 {fmt(source['TN']['bias'])} K、RMSE {fmt(source['TN']['RMSE'])} K，共同有效样本 {source['TN']['n']}。"]
    if science and verified:
        x,y=frame(1)
        first=row_metrics(x['DEN'],y['DEN'],np.cos(np.deg2rad(x['lat']))[None,:,None],0.,True)
        lines+=['',f"首个暖态诊断小时（06-07 01Z）原生 DEN 相对 P95 为 {fmt(first['relative_P95'],100)}%，RMSE {fmt(first['RMSE'])} g/cm3，n={first['n']}。"]
        lines+=['','| 日龄 | 原生 DEN 相对 P95 (%) | 450 km 共同 DEN 相对 P95 (%) | TN RMSE (K) | 风矢量差 RMS (m/s) | O1/O2/N2/HE 相对 P95 (%) |',
                '|---:|---:|---:|---:|---:|---|']
        hourly=csv_read('hourly')
        height=csv_read('height')
        for day in (1,3,7,14):
            rows={r['variable']:r for r in hourly if int(r['hour'])==day*24 and r['region']=='global'}
            ref=next(r for r in height if int(r['hour'])==day*24 and r['region']=='global' and r['height_km']=='450')
            comp='/'.join(fmt(rows[k]['relative_P95'],100) for k in ('O1','O2','N2','HE'))
            lines.append(f"| {day} | {fmt(rows['DEN']['relative_P95'],100)} | {fmt(ref['relative_P95'],100)} | {fmt(rows['TN']['RMSE'])} | {fmt(rows['WIND_VECTOR']['RMSE'],.01)} | {comp} |")
        rows=[r for r in hourly if int(r['hour'])==336 and r['variable']=='DEN' and r['region']!='global']
        order=sorted(rows,key=lambda r:float(r['relative_P95']))
        lines+=['',f"第 14 天 DEN 分区相对 P95 范围为 {fmt(order[0]['relative_P95'],100)}%（{order[0]['region']}）至 {fmt(order[-1]['relative_P95'],100)}%（{order[-1]['region']}）。"]
        vertical=[r for r in csv_read('levels') if int(r['hour'])==336 and r['variable']=='DEN' and r['region']=='global']
        worst=max(vertical,key=lambda r:float(r['relative_P95']))
        lines+=['',f"原生层第 14 天最大相对 P95 出现在 ilev 序号 {worst['level']}，为 {fmt(worst['relative_P95'],100)}%。"]
        gates=csv_read('gates')
        var=list(dict.fromkeys(r['variable'] for r in gates))
        lines+=['','末 24 小时（06-22 00Z 至 06-23 00Z，含两端）逐区域×时刻×层位严格按既有阈值评定。',
               f"评估单元 {science['evaluated_cells']} 个，未达格点通过比例要求 {science['failed_cells']} 个；另有 {science['excluded_empty_cells']} 个无有效样本的单元。",
               '',
               '| 变量 | 未通过单元 | 参与单元 | 最差格点通过比例 (%) |','|---|---:|---:|---:|']
        for k in var:
            rows=[r for r in gates if r['variable']==k and r['passed']!='']
            lines.append(f"| {k} | {sum(r['passed']=='False' for r in rows)} | {len(rows)} | {min((float(r['passed_fraction']) for r in rows),default=float('nan'))*100:.4g} |")
        lines+=['','共同 ZG 高度的末 24 小时 log 密度 RMS 线性斜率每小时为']
        lines+=['',*['- '+str(t['height_km'])+' km：'+fmt(t['last24h_log_RMSE_slope_per_hour']) for t in science['trend']]]
        lines+=['',f"独立复核 {read(RESULT/'independent.json')['independent_checks']} 项。区域、分层、局地太阳时和共同域覆盖详见 CSV。原生 DEN/ZG 在 ilev，其他对照变量在 lev。共同高度逐柱 log 密度插值，不外推。"]
    else:
        lines+=['','两次工程验收及独立数值复核完整通过前，日龄差异及预热结论保留待定。']
    lines+=['','## 门禁与下一步','',
           '本轮未读取未见 Swarm 密度、未评分、未拟合、未使用 GPU。2021-05-09 与 2021-06-16 Fobs 缺口保留。两份 ESA 0301 原件仍待交接。V37 正式验证仍为 2021 优先。',
           '后续优先定位仍有较大差异的变量、区域和高度，再决定是否单独授权延长预热。正式验证先补真实 GFZ 数据和 Swarm 身份。']
    with REPORT.open('x') as f: f.write('\n'.join(lines)+'\n')
    files=[p for p in OUT.iterdir() if p.is_file() and p.suffix in ('.json','.namelist') and p.name!='publication_SHA256.json']
    if RESULT.is_dir(): files.extend(p for p in RESULT.iterdir() if p.is_file())
    files.extend((REPORT,*ROOT.glob('scripts/*summer_seed_sensitivity_v46.py')))
    with (OUT/'publication_SHA256.json').open('x') as f:
        json.dump({str(p.relative_to(ROOT)):hash_file(p) for p in sorted(files)},f,indent=2)


if __name__=='__main__':
    summarize()
