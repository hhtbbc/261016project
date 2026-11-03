"""Jan4 actual auxiliary record audit. No orbit, neural or TIE-GCM execution."""
from pathlib import Path
import sys,json,csv,time,resource
import numpy as np
import cdflib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from prepare_swarm_physical_force_v1 import F,O,D
from prepare_fourcastden_swarm_observation_v1 import sha,dump
from analyze_fourcastden_swarm_observation_v1 import table
from orbit.swarm_force_inputs import SwarmForceInputProvider,Mode,cdf_epoch_utc64
START=np.datetime64('2023-01-04T01:00:00');STOP=np.datetime64('2023-01-04T13:00:00')
def counts(a):
    u,n=np.unique(a,return_counts=True);return {str(x):int(v) for x,v in zip(u,n)}
def intervals(t,mask,label,source):
    ix=np.flatnonzero(mask);rows=[]
    if len(ix):
        for v in np.split(ix,np.flatnonzero((np.diff(ix)>1)|((np.diff(t[ix])/np.timedelta64(1,'s'))>1.5))+1):rows.append(dict(kind=label,source=source,first_UTC=str(t[v[0]])+'Z',last_sample_UTC=str(t[v[-1]])+'Z',sample_count=len(v),semantic_status='CANDIDATE_RECORD_SEGMENT_NOT_CONFIRMED_MANEUVER',actual_impulse_N_s=None))
    return rows

def main():
    start=time.perf_counter();contracts=[];series={};stats={};events=[];geometry=[];gaps=[]
    for kind in ['SC_ADYN','STRAATT']:
        path=next((D/'extracted').glob('*'+kind+'*cdf'))
        with cdflib.CDF(path) as c:
            g=c.globalattsget();variables={k:dict(attributes=c.varattsget(k),dtype=c.varinq(k).Data_Type_Description,dimensions=c.varinq(k).Dim_Sizes) for k in c.cdf_info().zVariables};t=cdf_epoch_utc64(c.varget('Timestamp'));mask=(t>=START)&(t<=STOP);tw=t[mask];v={k:c.varget(k)[mask] for k in c.cdf_info().zVariables if k!='Timestamp'};series[kind]=(tw,v);dt=np.diff(t)/np.timedelta64(1,'s');contracts.append(dict(product=kind,path=str(path.relative_to(ROOT)),SHA256=sha(path),globals=g,variables=variables,full_day_records=len(t),target_records=int(mask.sum()),target_first_UTC=str(tw[0]),target_last_UTC=str(tw[-1]),cadence_min_s=float(dt.min()),cadence_max_s=float(dt.max()),time_scale='CDF_EPOCH with fractional ms preserved, anchored to UTC Sensing_Start',serialized_epoch_ULP_s=float(np.spacing(c.varget('Timestamp')[0])/1000),version_applicability='CDF self-description verified; external0601 codebook NOT acquired'))
            for i in np.flatnonzero(dt>1.5):gaps.append(dict(product=kind,before_UTC=str(t[i]),after_UTC=str(t[i+1]),gap_s=float(dt[i])))
            stat=dict(records=len(tw),SyncStatus=counts(v['SyncStatus']),Flags_q=counts(v['Flags_q']),finite_timestamp=True)
            if kind=='SC_ADYN':
                m=v['m_SC'];on=np.any(v['dt_thr']>0,axis=1);stat.update(mass_min_kg=float(m.min()),mass_max_kg=float(m.max()),mass_mean_kg=float(m.mean()),mass_std_descriptive_kg=float(m.std()),mass_range_NOT_uncertainty=True,mass_relative_to_400_percent_min=float((m.min()/400-1)*100),mass_relative_to_400_percent_max=float((m.max()/400-1)*100),largest_adjacent_mass_step_kg=float(abs(np.diff(m)).max()),mass_finite_positive=bool(np.isfinite(m).all() and (m>0).all()),dt_thr_positive_records=int(on.sum()),max_record_channel_on_time_s=float(v['dt_thr'].max()),total_channel_on_time_s=float(v['dt_thr'].sum()),nominal_force_nonzero_records=int(np.any(v['f_thr']!=0,axis=1).sum()),Flags_Platform=counts(v['Flags_Platform']),thr_set=counts(v['thr_set']))
                table(O/'mass_timeseries_local.csv',[dict(UTC=str(t)+'Z',mass_kg=float(x),SyncStatus=int(sync),Flags_Platform=int(flag),Flags_q=int(fq)) for t,x,sync,flag,fq in zip(tw,m,v['SyncStatus'],v['Flags_Platform'],v['Flags_q'])])
                table(O/'mass_hourly_summary.csv',[dict(UTC_hour=h,records=int((sel:=(tw>=START+np.timedelta64(h-1,'h'))&(tw<START+np.timedelta64(h,'h'))).sum()),min_kg=float(m[sel].min()),max_kg=float(m[sel].max()),mean_kg=float(m[sel].mean()),quality='RECORDS_VERIFIED_QUALITY_SEMANTICS_UNVERIFIED') for h in range(1,13)])
                events+=intervals(tw,on,'dt_thr_any_channel_positive',kind);events+=intervals(tw,v['Flags_Platform']!=0,'Flags_Platform_nonzero_UNDECODED',kind)
                table(O/'thruster_positive_records_local.csv',[dict(UTC=str(tw[i])+'Z',dt_thr_s=v['dt_thr'][i].tolist(),f_thr_mN=v['f_thr'][i].tolist(),thr_set=int(v['thr_set'][i]),Flags_Platform=int(v['Flags_Platform'][i])) for i in np.flatnonzero(on)])
                for key in ['A_head','A_right','A_left','A_down']:geometry.append(dict(field=key,definition=variables[key]['attributes'],shape=list(v[key].shape),all_finite=bool(np.isfinite(v[key]).all()),component_min_m2=float(np.nanmin(v[key])),component_max_m2=float(np.nanmax(v[key])),effective_frontal_area_computed=False))
            else:
                q=v['q'];finite=np.isfinite(q).all(axis=1);norm=np.linalg.norm(q[finite],axis=1);stat.update(quaternion_nonfinite_rows=int((~finite).sum()),quaternion_norm_min=float(norm.min()),quaternion_norm_max=float(norm.max()),norm_max_abs_deviation=float(abs(norm-1).max()),Maneuver_Id=counts(v['Maneuver_Id']),actual_rotation_enabled=False)
                events+=intervals(tw,v['Maneuver_Id']!=0,'Maneuver_Id_nonzero_UNDECODED',kind);events+=intervals(tw,~finite,'nonfinite_q_REJECT',kind)
                table(O/'attitude_quality_local.csv',[dict(UTC=str(tw[i])+'Z',q_finite=bool(finite[i]),norm=float(np.linalg.norm(q[i])) if finite[i] else None,Flags_q=int(v['Flags_q'][i]),SyncStatus=int(v['SyncStatus'][i]),Maneuver_Id=int(v['Maneuver_Id'][i])) for i in range(len(tw))])
            stats[kind]=stat
    dump(F/'CDF_contracts.json',contracts);dump(F/'summary.json',stats);dump(F/'geometry_evidence.json',geometry)
    if events:table(O/'candidate_event_intervals.csv',events)
    dump(F/'gap_audit.json',dict(gaps=gaps,full_day_records={x['product']:x['full_day_records'] for x in contracts},no_missing_records_detected=not gaps))
    sources={x['product']:x for x in contracts};provider=SwarmForceInputProvider(ROOT/sources['SC_ADYN']['path'],ROOT/sources['STRAATT']['path'],source_sha256={k:x['SHA256'] for k,x in sources.items()});snapshots=[]
    from dataclasses import asdict
    for h in [1,7,13]:snapshots.append(asdict(provider.at(f'2023-01-04T{h:02d}:00:00Z')))
    dump(F/'interface_examples_local.json',snapshots)
    alignment=[]
    tq=series['STRAATT'][0];td=series['SC_ADYN'][0];ix=np.searchsorted(td,tq);use=(ix>0)&(ix<len(td));j=ix[use];tt=tq[use];age=(tt-td[j-1])/np.timedelta64(1,'s');future=(td[j]-tt)/np.timedelta64(1,'s')
    dump(F/'time_alignment.json',dict(method='Separate actual UTC axes retained; previous-record snapshots, no interpolation',common_pairs=len(age),past_age_min_s=float(age.min()),past_age_max_s=float(age.max()),nearest_future_offset_min_s=float(future.min()),nearest_future_offset_max_s=float(future.max()),different_axes_not_relabelled=True))
    perf=dict(wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,new_ODE=0,new_GPU=0,new_TIE=0,full_window_mass_records=stats['SC_ADYN']['records'],attitude_records=stats['STRAATT']['records'],formal_orbit='BLOCKED')
    dump(F/'analysis_resource.json',perf);print(json.dumps(stats,indent=2));print(json.dumps(perf,indent=2))
if __name__=='__main__':main()
