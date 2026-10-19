"""Static-only restart validation plan. Never edits or launches TIE-GCM.

The installed input.F rejects the requested 23:50 start with a 00:00 source.
Do not turn this into an executor by deleting that gate or relabeling fields.
"""
from pathlib import Path
import argparse,sys,json,hashlib,shutil
import numpy as np
from netCDF4 import Dataset
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from atmosphere.restart_validation import check_source_clock,inspect_restart

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-tag',required=True)
    a=p.parse_args()
    if not a.run_tag or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in a.run_tag):raise ValueError('Bad tag')
    out=ROOT/'experiments'/a.run_tag
    if not out.resolve().is_relative_to(ROOT):raise ValueError('Outside workspace')
    out.mkdir(exist_ok=False)
    source=ROOT/'data/raw/tiegcm2_support/tiegcm_res5.0_mareqx_smin_prim.nc'
    asset=json.loads((ROOT/'logs/tiegcm2023_restart_asset_check.json').read_text())
    expected=json.loads((ROOT/'experiments/tiegcm2023_startup_10min_v1/preflight.json').read_text())
    for name,path in [('gpi_sha256',ROOT/'data/processed/tiegcm2023/gpi_20230312_20230325.nc'),
                      ('executable_sha256',ROOT/'experiments/tiegcm2_apex2023_v1/tiegcm2.0'),
                      ('restart_sha256',source)]:
        if not path.resolve().is_relative_to(ROOT):raise ValueError('Outside workspace asset')
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected[name]
    issues=[]
    try:check_source_clock([77,23,50],[80,0,0])
    except ValueError as e:issues.append(str(e))
    inventory=json.loads((ROOT/'logs/tiegcm2023_restart_inventory.json').read_text())
    if not any(x['has_2350'] and x['complete_primary_candidate'] for x in inventory):
        issues.append('No existing complete primary restart at 23:50 in local inventory')
    with Dataset(ROOT/'data/processed/tiegcm2023/gpi_20230312_20230325.nc') as n:
        assert n.yearday_beg<=2023077 and n.yearday_end>=2023078
    # Save explicit draft values, not invalid runnable namelists.
    cases={'A_continuous':{'start':[77,23,50],'stop':[78,0,10],'minutes':20},
           'B1_first':{'start':[77,23,50],'stop':[78,0,0],'minutes':10},
           'B2_resume':{'start':[78,0,0],'stop':[78,0,10],'minutes':10}}
    for key,c in cases.items():
        c.update(start_year=2023,start_day=c['start'][0],calendar_advance=1,step_s=60,mpi_ranks=4,
                 history_interval_minutes=5,potential_model='HEELIS',fixed_driver_overrides=False,
                 source_start=None if key=='B2_resume' else [80,0,0],
                 source=None if key=='B2_resume' else str(source.relative_to(ROOT)),
                 executable_launch_authorized_now=False,status='DRAFT_NOT_RUN')
        if key=='B2_resume':
            c.update(restart_mode='native continuation: omit SOURCE; search OUTPUT at START',
                     output='independent byte-identical copy of B1 complete primary (not created)',
                     checkpoint_copy_sha_must_match=True,original_B1_must_remain_read_only=True,
                     source_evidence=['rdsource.F:35-65','nchist.F:479-488','hist.F:210-218'])
    rules={'float64_rtol':1e-10,'float32_rtol':1e-6,
           'SI_atol':{'DEN_kg_m3':1e-25,'ZG_m':1e-5,'TN_K':1e-8,'wind_m_s':1e-8,'composition_mmr':1e-12},
           'time_and_grid':'exact agreement required','mask':'typed fill masks must match; any NaN/Inf fails',
           'pass':'max abs delta/(atol+rtol*max(abs(a),abs(b))) <= 1',
           'relative_error':'abs(delta/reference); zero reference excluded from relative maximum and counted',
           'basis':'prior 2002 repeated-run double TN diff 3.07e-12 K, wind 1.29e-12 m/s; float32 rtol ~8.4 eps; never relax after observing restart mismatch'}
    sensitivity=[]
    for name,value in [('TN_K',800.),('ZG_m',500000.),('DEN_kg_m3',1e-12),('wind_m_s',300.),('composition_mmr',.5)]:
        for typ in [np.float32,np.float64]:
            v=typ(value);ulp=float(np.nextafter(v,typ(np.inf))-v)
            rtol=rules['float32_rtol'] if typ==np.float32 else rules['float64_rtol']
            limit=rules['SI_atol'][name]+rtol*value
            sensitivity.append({'field':name,'dtype':np.dtype(typ).name,'representative_value':value,'one_ulp_SI':ulp,'allowed_error_SI':limit,'one_ulp_passes':ulp<=limit,'scope':'arithmetic sensitivity, not model experiment'})
    (out/'comparison_rules.json').write_text(json.dumps(rules,indent=2)+'\n')
    (out/'tolerance_sensitivity.json').write_text(json.dumps(sensitivity,indent=2)+'\n')
    report={'status':'BLOCKED_STATIC_PRECONDITION','model_launches':0,'cases':cases,'blocking_issues':issues,
            'source_structure':inspect_restart(source,[80,0,0]),'asset_hash_checks':asset,
            'source_rule':{'file':'third_party/TIEGCM2.0/src/input.F','lines':[948,960]},
            'resources':{'free_disk_bytes':shutil.disk_usage(ROOT).free,
                         'meminfo':Path('/proc/meminfo').read_text().splitlines()[:3],
                         'wall_limit_per_launch_s':90,'total_output_limit_bytes':512*1024**2,
                         'aggregate_rss_soft_stop_bytes':16*1024**3,'disk_floor_bytes':20*1024**3,
                         'estimated_three_run_netcdf_bytes':260*1024**2,
                         'output_estimate_basis':'conservative ~260 MiB: primary ~17 MB/frame, A 5 frames, B1/B2 3 each, secondary 4+2+2 frames; not measured'},
            'scope':'configuration/structure/arithmetic only; no continuous-versus-split physical metrics exist'}
    assert report['resources']['free_disk_bytes']>20*1024**3
    (out/'static_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'blocking_issues':issues,'model_launches':0,'output':str(out)},indent=2))
if __name__=='__main__':main()
