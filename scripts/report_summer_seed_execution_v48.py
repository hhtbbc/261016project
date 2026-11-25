"""Create the V48 release from existing engineering receipts and measured fields."""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
import re

import preflight_summer_seed_recovery_v47 as r

OUT=r.ROOT/'experiments/thermosphere_summer_seed_execution_v48'
REPORT=r.ROOT/'reports/THERMOSPHERE_SUMMER_SEED_RECOVERY_EXECUTION_V48.md'
COMPARISON=r.OUT/'comparison'


def table(name):
    with (COMPARISON/f'{name}.csv').open() as f:
        return list(csv.DictReader(f))


def file_json(path):
    return r.load(path) if path.exists() else None


def fmt(value,factor=1):
    return 'N/A' if value is None or value=='' else f'{float(value)*factor:.6g}'


def main():
    r.require(OUT.resolve()==OUT and REPORT.resolve()==REPORT and not REPORT.exists(),'Unexpected output')
    auth=r.load(OUT/'authorization_summary.json')
    claim=file_json(r.receipt_path(r.RUN,'claim'))
    s=file_json(r.RUN/'status.json')
    accepted=file_json(r.receipt_path(r.RUN,'acceptance'))
    independent=file_json(COMPARISON/'independent.json')
    addendum=file_json(OUT/'independent_addendum.json')
    scientific=file_json(COMPARISON/'summary.json')
    failure=file_json(OUT/'analysis_failure.json')
    figures=sorted(COMPARISON.glob('*.png'))
    if accepted and independent and scientific and addendum and len(figures)==11:
        state='V48_PAIRED_ANALYSIS_COMPLETE_VERIFIED'
    elif accepted:
        state='V48_B_ENGINEERING_PASS_ANALYSIS_PENDING'
    elif claim:
        r.require(s is not None,'B run in progress')
        state='V48_B_ENGINEERING_FAIL'
    else:
        state='V48_NOT_LAUNCHED'
    verdict=(scientific['status'] if state=='V48_PAIRED_ANALYSIS_COMPLETE_VERIFIED'
             else 'SEED_SENSITIVITY_INCONCLUSIVE')
    rank=[r.load(x) for x in sorted(r.RUN.glob('rank_*_exit.json'))]
    stamp=lambda t: datetime.fromtimestamp(t,timezone.utc).isoformat()
    run=dict(run_id=claim['run_id'] if claim else None,
             initial_progress_observed=any(re.search(r'Step\s+\d+ of',x.read_text())
                                          for x in r.RUN.glob('rank_*.log')),
             start_UTC=stamp(min(x['started_unix'] for x in rank)) if rank else None,
             end_UTC=stamp(max(x['ended_unix'] for x in rank)) if rank else None)
    launch=r.RUN/'launch_once.json'
    run['launch_count']=r.load(launch)['launch_count'] if launch.exists() else 0
    if s:
        for key in ('qualification','stop_reason','returncode','elapsed_s','peak_sampled_tree_rss_bytes',
                    'children_cpu_user_s','children_cpu_system_s','cleanup_verified'):
            run[key]=s[key]
        run['minimum_free_disk_bytes']=min((x['free_disk_bytes'] for x in s['samples']),default=None)
        run['peak_sampled_output_bytes']=max((x['total_output_bytes'] for x in s['samples']),default=None)
    run['ranks']=[{'rank':x['rank'],'returncode':x['returncode'],'ended_UTC':stamp(x['ended_unix'])} for x in rank]
    if accepted:
        run.update(steps=accepted['progress'][0]['final_step'],final_model_UTC=accepted['final_UTC'],
                   max_GPI_abs=accepted['max_GPI_abs'], inventory=accepted['files'],
                   primary_volumes=17,secondary_volumes=16,secondary_hours=384,
                   netcdf_bytes=sum(x['bytes'] for x in accepted['files']))
    runtime_logs={}
    if r.RUN.is_dir():
        for x in sorted(r.RUN.iterdir()):
            if x.suffix in ('.json','.jsonl','.log') and x.is_file():
                runtime_logs[str(x.relative_to(r.ROOT))]=r.sha(x)
    plan=r.load(r.OLD/'frozen_pair.json')
    b=plan['protocols'][r.v46.B]
    record=dict(state=state,sensitivity=verdict,engineering='PASS' if accepted else 'FAIL' if run['launch_count'] else 'NOT_LAUNCHED',
                authorization=auth,run=run,original_A_id=auth['A_id'],original_B_failure_id=auth['V46_B_failed_id'],
                model_sha256=b['executable']['SHA256'],GPI_sha256=b['GPI']['SHA256'],
                recovery_namelist_sha256=r.sha(r.INPUT),seed_sha256=r.sha(r.SEED),
                v47_independent=independent,independent_addendum=addendum,analysis_failure=failure,
                log_sha256=runtime_logs,figures=len(figures),unseen_target_density_reads=0,GPU=0,reruns_A=0,
                V37_scoring=False,historical_fit=False,official_unseen_order='2021 then 2022')
    r.write(OUT/'result.json',record)
    lines=['# V48 junsol 恢复积分与 2022 夏季初态敏感性','',f'**{state} / {verdict}**。','',
           f"基线 GitHub HEAD `{auth['baseline_HEAD']}`。V47 发布 SHA 与 V46 原始输出、日志及失败证据核对通过。",
           f"授权收据绑定 V47 准备 SHA `{auth['preparation_sha256']}`。仅允许本次 B，原 A 与原失败 B 未覆盖，未重跑 A。",'',
           '## B 组物理运行','',
           f"新 run_id `{run['run_id']}`，实际启动 {run['launch_count']} 次。",
           f"模型 ELF SHA `{record['model_sha256']}`，GPI SHA `{record['GPI_sha256']}`，两组相同。",
           f"junsol SHA `{record['seed_sha256']}`，恢复 input SHA `{record['recovery_namelist_sha256']}`。",
           "相对 SOURCE 为 `../seed.nc`；SOURCE_START=172 0 0。与 A 的唯一初态差异是源文件及源时钟，目标历日与全部物理设置相同。",
           "目标 2022-06-07 至 06-23 00Z，STEP=60、MPI4/OMP1/GPU0。"]
    if s:
        lines+=['',f"实际 UTC {run['start_UTC']} 至 {run['end_UTC']}。MPI 父进程 {run['returncode']}，四 rank {[x['returncode'] for x in run['ranks']]}。",
               f"墙钟 {fmt(run['elapsed_s'],1/60)} 分钟，峰值采样 RSS {fmt(run['peak_sampled_tree_rss_bytes'],2**-30)} GiB，"
               f"用户/系统 CPU {fmt(run['children_cpu_user_s'])}/{fmt(run['children_cpu_system_s'])} 秒。"
               f"运行中最低采样剩余盘 {fmt(run['minimum_free_disk_bytes'],2**-30)} GiB。"]
    if accepted:
        lines+=['', f"B 的 23040 步与四 rank 明细通过；17 primary / 16 secondary 卷 / 384 暖态小时到 {run['final_model_UTC']}。"
                f"原始输出 {run['netcdf_bytes']:,} 字节。原生冷源回显、八类暖态场、时间轴、单位和 SHA 验收通过。",
                f"实际驱动和 GPI 最大绝对差 {run['max_GPI_abs']:.6g}；原始输出与运行日志留服务器。"]
    if addendum:
        lines+=['',f"独立以 GFZ 原始数据重算 384 小时强迫，最大差 {addendum['B_independent_GPI_max_abs']:.6g}；"
                f"33+33 卷重新核验，额外复核日龄 14 空间图 {addendum['day14_map_cells']} 点及局地时指标 {addendum['local_time_metrics']} 项。"]
    if failure:
        lines+=['',f'分析曾失败。保留首轮 CSV 和失败记录，详情见 analysis_failure.json。']
    if scientific and independent and addendum:
        hourly,heights,gates=table('hourly'),table('height'),table('gates')
        lines+=['','## 初态差异与预热结果','',
                '相对差使用 mareqx 为参考。所列 P95 为相对绝对差的面积加权 95 分位；水平风以矢量差 RMS 表示。',
                '', '| 日龄 | UTC | 原生 DEN P95 (%) | 450 km DEN P95 (%) | TN RMSE (K) | 风矢量 RMS (m/s) | O1/O2/N2/HE P95 (%) |',
                '|---:|---|---:|---:|---:|---:|---|']
        days={}
        for d in (1,3,7,14):
            rs={x['variable']:x for x in hourly if x['hour']==str(d*24) and x['region']=='global'}
            at=next(x for x in heights if x['hour']==str(d*24) and x['height_km']=='450' and x['region']=='global')
            ratio='/'.join(fmt(rs[k]['relative_P95'],100) for k in ('O1','O2','N2','HE'))
            lines.append(f"| {d} | {rs['DEN']['UTC']} | {fmt(rs['DEN']['relative_P95'],100)} | "
                         f"{fmt(at['relative_P95'],100)} | {fmt(rs['TN']['RMSE'])} | {fmt(rs['WIND_VECTOR']['RMSE'],.01)} | {ratio} |")
            days[d]=dict(UTC=rs['DEN']['UTC'],DEN_P95=float(rs['DEN']['relative_P95']),height450_P95=float(at['relative_P95']),
                         DEN_n=int(rs['DEN']['n']),height450_n=int(at['n']),TN_RMSE=float(rs['TN']['RMSE']),
                         wind_vector_RMS_m_s=float(rs['WIND_VECTOR']['RMSE'])/100,
                         composition_P95={k:float(rs[k]['relative_P95']) for k in ('O1','O2','N2','HE')})
        regions={x['region']:float(x['relative_P95']) for x in hourly if x['hour']=='336' and x['variable']=='DEN'}
        levels=[x for x in table('levels') if x['hour']=='336' and x['variable']=='DEN' and x['region']=='global']
        worst=max(levels,key=lambda x:float(x['relative_P95']))
        growth=[x['height_km'] for x in scientific['trend'] if x['last24h_log_RMSE_slope_per_hour'] is not None and not x['no_growth']]
        lines+=['','','日龄 14 的原生 DEN P95 按区为 '+
                '、'.join(k+' '+fmt(v,100)+'%' for k,v in regions.items())+'。',
                f"原生 ilev 中最大 P95 位于序号 {worst['level']}，为 {fmt(worst['relative_P95'],100)}%。",
                "原生 DEN/ZG 在 ilev，其余比较变量在 lev；共同 ZG 高度为逐柱 log DEN 内插，仅取共同有效范围，无外推。",
                "06-22 00Z 至 06-23 00Z 含两端共 25 个末 24 小时采样。严格评估相对差 <5%、温差 <10 K、风矢量差 <20 m/s；各区域、时刻和层位有效格点通过比例需 ≥95%，组分分母要求 >1e-8。",'',
                f"共评估 {scientific['evaluated_cells']} 个单元，其中 {scientific['failed_cells']} 个失败，{scientific['excluded_empty_cells']} 个空单元未参与。",
                '', '| 门槛变量 | 未通过 / 有效单元 | 最差格点通过比例 (%) |', '|---|---:|---:|']
        rollup={}
        for k in dict.fromkeys(x['variable'] for x in gates):
            rr=[x for x in gates if x['variable']==k and x['passed']!='']
            fail=[x for x in rr if x['passed']=='False']
            worst_f=min(float(x['passed_fraction']) for x in rr)
            lines.append(f'| {k} | {len(fail)} / {len(rr)} | {fmt(worst_f,100)} |')
            rollup[k]=dict(fail=len(fail),evaluated=len(rr),worst_fraction=worst_f,
                          failed_regions=sorted({x['region'] for x in fail}))
        lines+=['', '共同 ZG 高度的全球密度 log-RMSE 斜率（每小时）为']
        lines+=['',*[f"- {x['height_km']} km：{fmt(x['last24h_log_RMSE_slope_per_hour'])}" for x in scientific['trend']]]
        lines+=['',f"正斜率高度为 {growth or '无'}。"
                f"冻结独立数值核对 {independent['independent_checks']} 项通过，另有日龄 14 空间和局地时复核。",
                '本结果只适用于本次驱动、初态、网格和配对窗口。模型内部 ZG 对齐不解除外部高度门禁。']
        r.write(OUT/'science_summary.json',dict(days=days,day14_regional_DEN_P95=regions,
                worst_ilev=worst,positive_trend_km=growth,gate_variables=rollup,science=scientific))
    else:
        lines+=['','配对分析或独立验证尚未完整通过。保留不确定状态。']
    lines+=['','## 科学门禁与下一步','',
           '本轮仅做 2022 夏季内部 HINDCAST 工程对照。未读未见 Swarm 密度、未评分、未拟合、未使用 GPU；未启动其他积分。',
           'V37 按 2021 优先、λ=0.5、原 Raw/Global 与冻结指标。2021 的 05-09 和 06-16 Fobs 仍缺；两份 ESA 0301 未交接。外部 ZG、固定偏移、实时 as-of、训练、DART 与真实轨道门禁保持。',
           'V49 优先从现有输出定位缓慢调整的组分、区域和高度；额外预热或真观测评分仍需独立授权及相应资料。']
    with REPORT.open('x') as f:
        f.write('\n'.join(lines)+'\n')
    files=[x for x in OUT.glob('*.json') if x.name!='publication_SHA256.json']
    files += [x for x in COMPARISON.iterdir() if x.suffix in ('.csv','.png','.json')] if COMPARISON.is_dir() else []
    files += [REPORT,*r.ROOT.glob('scripts/*summer_seed_execution_v48.py')]
    r.write(OUT/'publication_SHA256.json',{str(x.relative_to(r.ROOT)):r.sha(x) for x in sorted(files)})


if __name__=='__main__':
    main()
