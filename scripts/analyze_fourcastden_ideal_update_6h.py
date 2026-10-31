"""Paired physical-space evaluation, no neural model or orbit computation."""
from pathlib import Path
import csv,json,sys,time,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import run_fourcastden_ideal_update_6h as run
from fourcastden.ideal_update import physical_stats,splice_at_seven,improvement_percent
from fourcastden.logden import decode_physical
from fourcastden.validation import NAMES,LENGTHS,SI_FACTORS,SI_UNITS
from atmosphere.fourcastden_density import reconstruct_native_zg
F,O,D=run.F,run.O,run.D


def main():
    started=time.perf_counter();protocol=run.verify();runtime=json.loads((F/'runtime.json').read_text())
    assert runtime['status']=='PASS' and runtime['attempted_forwards']==runtime['effective_forwards']==48
    lat=np.load(ROOT/'data/processed/static/lat.npy');iv=np.load(ROOT/'data/processed/static/ilev.npy')
    masks={'global':np.ones((36,72),bool),'south':np.broadcast_to((lat<=-60)[:,None],(36,72)),
           'north':np.broadcast_to((lat>=60)[:,None],(36,72)),'midlow':np.broadcast_to((abs(lat)<60)[:,None],(36,72))}
    metrics=[];layerrows=[];consistency=[];jump=[];coverage=[];conditions=[]
    for day in run.DATES:
        truth=np.stack([run.reference(day,h)[0].astype(float) for h in range(1,14)])
        zref=np.stack([run.reference(day,h)[1] for h in range(1,14)])
        tlbc=np.stack([run.reference(day,h)[2] for h in range(1,14)])
        for model in run.MODELS:
            old=run.load_old(day,model,('pred','means','stds'))
            p=decode_physical(old['pred'][0],old['means'][:171],old['stds'][:171],model=='LogDEN')
            path=D/f'{day}_{model}.npz';meta=json.loads((F/f'{day}_{model}_runtime.json').read_text());assert run.sha(path)==meta['result_SHA']
            with np.load(path) as z:
                q=decode_physical(z['pred'][0],z['means'][:171],z['stds'][:171],model=='LogDEN')
                history_six=decode_physical(z['full_data'][0,:171],z['means'][:171],z['stds'][:171]) if model=='History' else None
            b=splice_at_seven(p,q);np.testing.assert_array_equal(b[:6],p[:6])
            rheight={};validity={};mass={}
            for label,values in [('Open',p),('Updated',b)]:
                zg,valid,mu=reconstruct_native_zg(values[:,:28],values[:,142:171],values[:,113:142],tlbc,lat,iv)
                rheight[label]=zg;validity[label]=valid;mass[label]=mu
                for lead in range(13):
                    for region,mask in masks.items():
                        d=values[lead];m=mu[lead];v=valid[lead]
                        consistency.append(dict(date=day,model=model,scheme=label,original_lead=lead,target_hour_UTC=lead+1,
                            region=region,column_count=int(mask.sum()),height_invalid_columns=int((~v&mask).sum()),
                            height_valid_fraction=float(v[mask].mean()),mass_outside_4_32_columns=int((((m<4)|(m>32)).any(axis=0)&mask).sum()),
                            mass_min=float(m[:,mask].min()),mass_max=float(m[:,mask].max()),
                            TN_nonpositive=int((d[:28,mask]<=0).sum()),DEN_nonpositive=int((d[142:,mask]<=0).sum()),
                            network_nonfinite=int((~np.isfinite(d[:,mask])).sum()),Z_nonmonotone_columns=int(((np.diff(d[113:142],axis=0)<=0).any(axis=0)&mask).sum()),
                            reconstructed_ZG_nonmonotone_columns=int(((np.diff(zg[lead],axis=0)<=0).any(axis=0)&mask).sum()),
                            max_abs_horizontal_wind_m_s=float(abs(d[28:84,mask]).max()*.01),
                            reset_record_excluded_from_prediction_comparison=bool(label=='Updated' and lead==6)))
            for lead in range(1,13):
                if lead==6: # Keep baseline curve; reset state is not a new forecast.
                    schemes=[('Open',p)]
                else:schemes=[('Open',p),('Updated',b)]
                med=np.median(zref[lead],axis=(1,2))/1000;near=np.flatnonzero((med>=400)&(med<=500))
                groups={'all':np.arange(29),'near400_500':near,'upper20_28':np.arange(20,29),'top':np.array([28])}
                for region,mask in masks.items():
                    for label,values in schemes:
                        off=0
                        for name,n,factor,unit in zip(NAMES,LENGTHS,SI_FACTORS,SI_UNITS):
                            v=values[lead,off:off+n]*factor;t=truth[lead,off:off+n]*factor
                            a=physical_stats(v,t,lat,mask,relative=name=='DEN')
                            metrics.append(dict(date=day,model=model,scheme=label,original_lead=lead,target_hour_UTC=lead+1,
                                hours_since_reset=lead-6 if label=='Updated' and lead>=7 else '',region=region,variable=name,group='all',domain='pressure_valid',SI_unit=unit,
                                native_indices=';'.join(map(str,range(n))),**a))
                            for k in range(n):
                                s=physical_stats(v[k:k+1],t[k:k+1],lat,mask,relative=name=='DEN')
                                layerrows.append(dict(date=day,model=model,scheme=label,original_lead=lead,target_hour_UTC=lead+1,region=region,
                                    variable=name,vertical_grid='lev' if n==28 else 'ilev',layer_index=k,SI_unit=unit,**s))
                            off+=n
                        for group,inds in groups.items():
                            for domain,cc in [('pressure_valid',None),('common_height_valid',validity['Open'][lead]&validity['Updated'][lead])]:
                                if group=='all' and domain=='pressure_valid':continue
                                a=physical_stats(values[lead,142+inds]*1000,truth[lead,142+inds]*1000,lat,mask,cc,relative=True)
                                metrics.append(dict(date=day,model=model,scheme=label,original_lead=lead,target_hour_UTC=lead+1,
                                    hours_since_reset=lead-6 if label=='Updated' and lead>=7 else '',region=region,variable='DEN',group=group,domain=domain,SI_unit='kg/m3',
                                    native_indices=';'.join(map(str,inds)),**a))
                    coverage.append(dict(date=day,model=model,original_lead=lead,target_hour_UTC=lead+1,region=region,total_columns=int(mask.sum()),
                        open_height_invalid=int((~validity['Open'][lead]&mask).sum()),updated_height_invalid=int((~validity['Updated'][lead]&mask).sum()),
                        common_height_valid=int((validity['Open'][lead]&validity['Updated'][lead]&mask).sum())))
            for role,prev,after,ref in [('current07',p[6],q[0],truth[6])]+([('history06',p[5],history_six,truth[5])] if model=='History' else []):
                offset=0
                for name,n,factor,unit in zip(NAMES,LENGTHS,SI_FACTORS,SI_UNITS):
                    sl=slice(offset,offset+n)
                    for region,mask in masks.items():
                        a=physical_stats(after[sl]*factor,prev[sl]*factor,lat,mask)
                        relative_jump=None
                        if name=='DEN':
                            e=(after[sl]-prev[sl])/ref[sl];w=np.broadcast_to(np.cos(np.deg2rad(lat))[:,None],(36,72));relative_jump=float(np.sqrt(np.sum(w[mask]*e[:,mask]**2)/(n*w[mask].sum())))
                        jump.append(dict(date=day,model=model,state_role=role,region=region,variable=name,SI_unit=unit,
                            actual_update_RMSE=a['RMSE'],actual_update_MAE=a['MAE'],actual_update_max_abs=a['max_abs'],actual_update_bias=a['bias'],
                            DEN_jump_relative_RMS_reference_denominator=relative_jump,forecast_score=False))
                    offset+=n
            conditions.append(dict(date=day,model=model,initial_hours=meta['initial_history_hours'],future_targets_feedback=False,
                exact_feedback=meta['feedback']['passed'],poison_check=meta['future_truth_poison_PASS'],post_targets=list(range(8,14))))
            del old,p,q,b,rheight,mass;gc=None
    run.csvout(O/'metrics.csv',metrics);run.csvout(O/'layer_metrics.csv',layerrows);run.csvout(O/'physical_consistency.csv',consistency)
    run.csvout(O/'jump_at_update.csv',jump);run.csvout(O/'paired_height_coverage.csv',coverage);run.dump(O/'feedback_conditions.json',conditions)
    # Every paired comparison uses exactly the same UTC, pressure group, region,
    # mask definition and SI units. No 07 reset score is part of these 6 leads.
    keynames=('date','model','original_lead','region','variable','group','domain')
    lookup={tuple(r[k] for k in keynames)+(r['scheme'],):r for r in metrics}
    pairs=[]
    for row in metrics:
        if row['scheme']!='Updated' or row['original_lead']<7:continue
        base=lookup[tuple(row[k] for k in keynames)+('Open',)]
        pair={k:row[k] for k in keynames};pair.update(target_hour_UTC=row['target_hour_UTC'],native_indices=row['native_indices'],SI_unit=row['SI_unit'])
        for measure in ('RMSE','mean_layer_RMSE','MAE','max_abs','relative_RMS','mean_layer_relative_RMS','relative_P95','log_RMS'):
            a,c=base[measure],row[measure];pair.update({f'open_{measure}':a,f'updated_{measure}':c,f'improvement_pct_{measure}':improvement_percent(a,c)})
        pairs.append(pair)
    run.csvout(O/'paired_changes.csv',pairs)
    end=[x for x in pairs if x['original_lead']==12 and x['region']=='global' and x['variable']=='DEN' and x['domain']=='pressure_valid']
    run.csvout(O/'DEN_12h_key_results.csv',end)
    perf=[]
    for m in runtime['records']:
        perf.append(dict(date=m['date'],model=m['model'],model_load_s=m['model_load_s'],model_reused=m['model_reused'],read_preprocess_s=m['read_preprocess_s'],
            read_decode_s=m['read_decode_s'],normalization_s=m['normalization_s'],reset_state_extraction_s=m['reset_state_extraction_s'],six_step_loop_s=m['six_step_loop_s'],
            first_GPU_forward_ms=m['forward_GPU_ms'][0],later_GPU_forward_mean_ms=float(np.mean(m['forward_GPU_ms'][1:])),six_forwards_GPU_ms=m['network_GPU_total_ms'],
            save_s=m['save_s'],peak_allocated_bytes=m['peak_allocated_bytes'],peak_reserved_bytes=m['peak_reserved_bytes'],process_peak_RSS_KiB=m['process_peak_RSS_KiB']))
    run.csvout(O/'performance.csv',perf)
    statuses=dict(BASELINE_REPRODUCTION_READY='PASS',IDEAL_UPDATE_INFERENCE_READY='PASS',POST_UPDATE_EVALUATION_READY='PASS',
        PHYSICAL_CONSISTENCY_EVALUATED='PASS (evaluated; not a guarantee of physical consistency)',STATE_UPDATE_CONCLUSION_READY='PASS (two-window diagnostic only)',SCIENTIFIC_TRAINING_READY='FAIL (prior release gate unchanged)')
    run.dump(O/'analysis.json',dict(statuses=statuses,metric_rows=len(metrics),layer_rows=len(layerrows),paired_rows=len(pairs),
        current_jump_scored_as_forecast=False,regions=protocol['metric_regions'],physical_coordinate='native pressure; reference-selected 400-500km layer group, not fixed altitude',
        evaluation_wall_s=time.perf_counter()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
    print(json.dumps(end,indent=2))


if __name__=='__main__':main()
