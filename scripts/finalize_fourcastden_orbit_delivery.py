"""Independent post-run checks and comparisons. No orbit or neural model runs."""
from pathlib import Path
import csv,hashlib,itertools,json,sys,time,zipfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import run_fourcastden_orbit_integration_v1 as task
from atmosphere.fourcastden_density import reconstruct_native_zg
from atmosphere.tiegcm_density_provider import DATUM
from fourcastden.logden import decode_physical


def main():
    started=time.monotonic();F,O=task.F,task.O
    protocol=json.loads((F/'protocol.json').read_text());integration=json.loads((F/'integration.json').read_text())
    assert integration['completed_propagations']==8 and integration['wall_s']<=600
    # Independently reproduce the lightweight array inventory without loading fields.
    with (O/'saved_array_inventory.csv').open() as f:inventory=list(csv.DictReader(f))
    for entry in inventory:
        with zipfile.ZipFile(ROOT/entry['path']) as z, z.open('pred.npy') as stream:
            version=np.lib.format.read_magic(stream)
            shape,order,dtype=np.lib.format._read_array_header(stream,version)
            assert str(shape)==entry['prediction_shape']
            assert 'means.npy' in z.namelist() and 'stds.npy' in z.namelist()
    state={};rows=[]
    for name in protocol['models']:
        for mode in ('base','tight'):
            with np.load(F/f'{name}_{mode}_states.npz') as n:
                assert np.array_equal(n['seconds'],np.arange(0,3601,60))
                state[name,mode]=n['states'].copy()
    for a,b in itertools.combinations(protocol['models'],2):
        tight=state[a,'tight'][:,:3]-state[b,'tight'][:,:3]
        base=state[a,'base'][:,:3]-state[b,'base'][:,:3]
        error=float(np.linalg.norm(base-tight,axis=1).max());response=float(np.linalg.norm(tight,axis=1).max())
        rows.append(dict(comparison=a+' minus '+b,response_max_m=response,vector_convergence_max_m=error,
                         relative_limit=.01,passed=bool(error<=.01*response)))
    task.table(O/'all_pair_convergence.csv',rows)
    # Same no-drag path, to distinguish path differences from input field differences.
    from orbit.frames import configure_time_data
    from orbit.drag import EarthFixedFrame
    from astropy.time import Time
    ai,ref=task.chosen_providers();configure_time_data();frame=EarthFixedFrame(Time(protocol['start']))
    sample=[]
    for sec,y in zip(np.arange(0,3601,60),state['A_no_drag','tight']):
        epoch,r,v,q=frame.state_to_itrs(sec,y[:3],y[3:])
        from atmosphere.density_interface import DensityQuery
        location=DensityQuery.from_itrs(epoch,r)
        values=[]
        for p in (ref,ai):
            result=p(epoch,location.latitude_deg,location.longitude_deg,location.height_wgs84_m,datum=DATUM)
            if not result.valid:raise ValueError('Common path query failed: '+result.reason)
            values.append(result.rho_kg_m3)
        sample.append(dict(seconds=int(sec),UTC=epoch.isot,latitude_deg=location.latitude_deg,longitude_deg=location.longitude_deg,
            conditional_native_ZG_m=location.height_wgs84_m,reference_kg_m3=values[0],AI_kg_m3=values[1],AI_reference_ratio=values[1]/values[0]))
    task.table(O/'common_A_path_density.csv',sample)
    from atmosphere.msis_density_provider import FrozenGfzDrivers
    weather=FrozenGfzDrivers(ROOT/'configs/nrlmsis2023_gfz_frozen.json');drivers=[]
    for hour in (1,2):
        p=task.paths(task.DAY)[1]/'data_view'/f'2023_03_24_{hour:02d}0000.npz'
        with np.load(p) as n:values={k:float(n[k].item()) for k in ('f107d','f107a','Kp')}
        d=weather.at(Time(f'{task.DAY}T{hour:02d}:00:00'))
        drivers.append(dict(hour=hour,**values,MSIS_previous_F107=d.f107_previous_day,MSIS_F107A=d.f107a_centered81,MSIS_Ap_7=str(d.ap)))
    task.table(O/'actual_drivers.csv',drivers)
    lat,lon,iv=task.grid();data,_=task.paths(task.DAY)
    with np.load(data/f'{task.DAY}_Flow.npz') as n:ph=decode_physical(n['pred'][0],n['means'][:171],n['stds'][:171])
    tlbc=np.stack([task.raw(task.DAY,h)['TLBC'] for h in range(1,14)])
    _,valid,mass=reconstruct_native_zg(ph[:,:28],ph[:,142:171],ph[:,113:142],tlbc,lat,iv)
    bad=[]
    for t,j,i in np.argwhere(~valid):
        levels=np.flatnonzero((mass[t,:,j,i]<4)|(mass[t,:,j,i]>32))
        bad.append(dict(hour_UTC=int(t+1),lead_hour=int(t),latitude=float(lat[j]),longitude=float(lon[i]),
                        invalid_mass_indices=';'.join(map(str,levels)),mass_min=float(mass[t,:,j,i].min()),mass_max=float(mass[t,:,j,i].max())))
    if bad:task.table(O/'flow_invalid_height_columns.csv',bad)
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8,4))
    for key,label in [('reference_kg_m3','TIE reference'),('AI_kg_m3','AI Direct')]:ax.plot([x['seconds']/3600 for x in sample],[x[key] for x in sample],label=label)
    ax.set(xlabel='Elapsed hour',ylabel='Density (kg/m3)',title='Same virtual no-drag path | conditional height registration');ax.legend();fig.tight_layout();fig.savefig(O/'common_path_density.png',dpi=150);plt.close(fig)
    with (O/'existing_error_growth.csv').open() as f:curves=list(csv.DictReader(f))
    fig,axs=plt.subplots(2,3,figsize=(14,7))
    for j,day in enumerate(('2023-01-04',task.DAY)):
        for k,field in enumerate(('near400_500_mean_relative_RMS','upper20_28_mean_relative_RMS','top_relative_RMS')):
            for model in ('Direct','Flow','LogDEN','History'):
                z=sorted([x for x in curves if x['date']==day and x['model']==model],key=lambda v:int(v['hour']))
                axs[j,k].plot([int(v['hour']) for v in z],[100*float(v[field]) for v in z],label=model)
            axs[j,k].set(title=day+' | '+['ref 400-500km layers','fixed upper20-28','native top'][k],xlabel='Lead hour',ylabel='Relative RMS (%)')
    axs[0,0].legend();fig.tight_layout();fig.savefig(O/'layer_dependent_error_growth.png',dpi=150);plt.close(fig)
    old=json.loads((ROOT/'experiments/tiegcm_runtime_restart_audit_v1/protected_files.json').read_text())
    changed=[p for p,h in old.items() if task.sha(ROOT/p)!=h];assert not changed,changed
    new_input=json.loads((F/'protected.json').read_text());assert all(task.sha(ROOT/p)==h for p,h in new_input.items())
    task.dump(O/'independent_delivery_checks.json',dict(historical_scientific_SHA_verified=len(old),changed=changed,
        task_input_SHA_verified=len(new_input),all_six_pair_convergence_pass=all(x['passed'] for x in rows),
        common_path_queries=len(sample)*2,common_path_AI_reference_relative_P95=float(np.percentile([abs(x['AI_reference_ratio']-1) for x in sample],95)),
        invalid_Flow_columns_preserved=len(bad),first_invalid_Flow_lead=min(x['lead_hour'] for x in bad) if bad else None,
        workflow_source_SHA={str(p.relative_to(ROOT)):task.sha(p) for p in (ROOT/'src/atmosphere/fourcastden_density.py',ROOT/'scripts/run_fourcastden_orbit_integration_v1.py',Path(__file__).resolve())},
        inventory_headers_verified=len(inventory),postprocess_wall_s=time.monotonic()-started,new_propagations=0,new_GPU_forwards=0))
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
