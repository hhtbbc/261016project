"""Saved AI fields -> bounded, explicitly PROVISIONAL virtual-satellite experiment.

No GPU, inference, TIE-GCM, training, downloads, or real SP3 accuracy claims.
"""
from pathlib import Path
import argparse,csv,hashlib,json,resource,sys,time,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from astropy.time import Time
from atmosphere.fourcastden_density import FourCastDENDensity,reconstruct_native_zg,HEIGHT_SOURCE
from atmosphere.tiegcm_density_provider import DATUM
from fourcastden.logden import decode_physical

F=ROOT/'experiments/fourcastden_orbit_integration_v1'
O=ROOT/'results/fourcastden_orbit_integration_v1'
DAY='2023-03-24'
LABELS='PROVISIONAL / VIRTUAL_SATELLITE / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST / CONDITIONAL_HEIGHT_REGISTRATION / FORCE_MODEL_INCOMPLETE'


def sha(path):
    p=Path(path).resolve();p.relative_to(ROOT);h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
    return h.hexdigest()


def dump(path,data):
    path.resolve().relative_to(ROOT)
    with path.open('x') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n')


def table(path,rows):
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def paths(day):
    folder='fourcastden_twelve_hour_jan4_v1' if day=='2023-01-04' else 'fourcastden_twelve_hour_mar24_v1'
    return ROOT/'data/processed'/folder, ROOT/'experiments'/folder


def raw(day,hour):
    _,folder=paths(day)
    with np.load(folder/'data_view'/f'{day.replace("-","_")}_{hour:02d}0000.npz',allow_pickle=False) as n:
        return {k:n[k].astype(float) for k in ('TN','DEN','Z','ZG','TLBC')}


def prepare():
    for p in (F,O):p.resolve().relative_to(ROOT);p.mkdir(exist_ok=False)
    frozen=json.loads((ROOT/'configs/provisional_common_force_model.json').read_text())
    protected={}
    for key in ('implementation_sha256','legacy_code_sha256','code_sha256'):
        for path,h in frozen.get(key,{}).items():
            if sha(ROOT/path)!=h:raise ValueError('H6 source modified: '+path)
            protected[path]=h
    inventory=[]
    for folder in sorted((ROOT/'data/processed').glob('fourcastden*')):
        if folder.is_dir():
            for p in sorted(folder.glob('*.npz')):
                inventory.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size))
    for day in ('2023-01-04',DAY):
        data,exp=paths(day)
        for model in ('Direct','Flow','LogDEN','History'):
            p=data/f'{day}_{model}.npz';expected=json.loads((exp/f'{day}_{model}_runtime.json').read_text())['result_sha256']
            if sha(p)!=expected:raise ValueError('Saved result SHA mismatch')
            protected[str(p.relative_to(ROOT))]=expected
        for hour in range(1,14):
            p=(exp/'data_view'/f'{day.replace("-","_")}_{hour:02d}0000.npz').resolve()
            protected[str(p.relative_to(ROOT))]=sha(p)
    for path in ('configs/nrlmsis2023_gfz_frozen.json','configs/provisional_common_force_model.json',
                 'third_party/TIEGCM2.0/src/addiag.F','third_party/TIEGCM2.0/src/dt.F','third_party/TIEGCM2.0/src/cons.F'):
        protected[path]=sha(ROOT/path)
    for p in (ROOT/'data/processed/static').glob('*.npy'):protected[str(p.relative_to(ROOT))]=sha(p)
    dump(F/'protected.json',protected);dump(O/'inventory.json',inventory)
    dump(F/'protocol.json',dict(labels=LABELS,virtual=True,start=DAY+'T01:00:00',stop=DAY+'T02:00:00',duration_s=3600,
        models=['A_no_drag','B_NRLMSIS21','C_TIE_reference','D_AI_Direct'],new_forward_count=0,
        coordinate_assumption='EXPLICIT A_WGS84_AS_NATIVE_ZG for virtual demonstration only; NOT validated Earth height registration',
        AI_height='source-derived molecular-mass inversion then calczg; only predicted TN/DEN/Z and allowed TLBC conditions',
        geometry_qualification=dict(reference_density_difference_due_only_to_reconstructed_height_p95_limit=.001,
                                    reference_density_difference_due_only_to_reconstructed_height_max_limit=.01,
                                    rationale='engineering interpolation error budget 0.1% P95/1% local maximum, not scientific atmospheric accuracy; frozen before full target validation'),
        convergence=dict(single_trajectory_max_m=.02,paired_drag_response_fraction=.01),
        controls=dict(mass_kg=400,area_m2=1,Cd=2.2,wind='zero ITRS neutral wind',inclination_deg=60,
                      initial_GCRS_radius_m=6378137+450000,initial_speed='sqrt(EGM2008_GM / radius)',
                      gravity='unchanged H6 EGM2008 40x40 + ERFA Sun/Moon',
                      base=dict(rtol=1e-10,atol=[1e-3]*3+[1e-6]*3,max_step=30.),
                      tight=dict(rtol=1e-12,atol=[1e-5]*3+[1e-8]*3,max_step=15.)),
        limits=dict(propagation_wall_s=600,process_RSS_MiB=1536,new_files_MiB=100,minimum_free_GiB=20,max_propagations=8,no_retry=True),
        expected=dict(wall_s=400,memory_MiB=350,new_files_MiB=20),
        SP3_overlap=False,source_SP3_window='2023-03-21 00:00:02 to 2023-03-23 00:00:02; not reused for new date'))
    print('Prepared independent protocol; no model runs',flush=True)


def grid():
    p=ROOT/'data/processed/static'
    return tuple(np.load(p/f'{name}.npy') for name in ('lat','lon','ilev'))


def chosen_providers():
    lat,lon,iv=grid();frames=[raw(DAY,h) for h in (1,2)]
    epochs=[DAY+f'T{h:02d}:00:00' for h in (1,2)]
    data,_=paths(DAY);p=data/f'{DAY}_Direct.npz'
    expected=json.loads((F/'protected.json').read_text())[str(p.relative_to(ROOT))]
    ai=FourCastDENDensity.from_saved(p,expected_sha256=expected,model='Direct',epochs=epochs,lat=lat,lon=lon,ilev=iv,tlbc=np.stack([x['TLBC'] for x in frames]))
    ref=FourCastDENDensity(epochs,lat,lon,np.stack([x['DEN'] for x in frames]),np.stack([x['ZG']*.01 for x in frames]),source='TIEGCM_REFERENCE',height_source='REFERENCE_ZG')
    return ai,ref


def analyze():
    started=time.monotonic();lat,lon,iv=grid();rows=[];prediction=[];geometry_effect=[]
    for day in ('2023-01-04',DAY):
        for hour in range(1,14):
            x=raw(day,hour)
            h,valid,mass=reconstruct_native_zg(x['TN'][None],x['DEN'][None],x['Z'][None],x['TLBC'][None],lat,iv)
            difference=h[0]-x['ZG']*.01
            rows.append(dict(date=day,hour=hour,invalid_columns=int((~valid).sum()),height_abs_P95_m=float(np.percentile(abs(difference),95)),
                height_abs_max_m=float(abs(difference).max()),Z_as_ZG_abs_P95_m=float(np.percentile(abs(x['Z']-x['ZG'])*.01,95)),
                inferred_mass_min=float(mass.min()),inferred_mass_max=float(mass.max())))
            if day==DAY and hour in (1,2):
                for j in range(len(lat)):
                    for i in range(len(lon)):
                        zref=x['ZG'][:,j,i]*.01;zr=h[0,:,j,i];rho=x['DEN'][:,j,i]
                        if valid[0,j,i] and max(zref[0],zr[0])<=450000<=min(zref[-1],zr[-1]):
                            a=np.exp(np.interp(450000,zref,np.log(rho)));b=np.exp(np.interp(450000,zr,np.log(rho)))
                            geometry_effect.append(abs(b/a-1))
                        else:raise ValueError('Target geometry reference has invalid 450km columns')
        data,_=paths(day)
        tlbc=np.stack([raw(day,h)['TLBC'] for h in range(1,14)])
        for model in ('Direct','Flow','LogDEN','History'):
            p=data/f'{day}_{model}.npz'
            with np.load(p) as n:physical=decode_physical(n['pred'][0],n['means'][:171],n['stds'][:171],model=='LogDEN')
            height,valid,mass=reconstruct_native_zg(physical[:,:28],physical[:,142:171],physical[:,113:142],tlbc,lat,iv)
            prediction.append(dict(date=day,model=model,invalid_reconstruction_columns=int((~valid).sum()),
                total_columns=int(valid.size),mass_min=float(mass.min()),mass_max=float(mass.max()),
                valid_bottom_min_m=float(height[:,0][valid].min()),valid_top_min_m=float(height[:,-1][valid].min()),
                valid_top_max_m=float(height[:,-1][valid].max())))
    table(O/'reference_height_validation.csv',rows);table(O/'prediction_height_coverage.csv',prediction)
    protocol=json.loads((F/'protocol.json').read_text());limits=protocol['geometry_qualification']
    effect=np.array(geometry_effect)
    gate=dict(status='ENGINEERING_NATIVE_RECONSTRUCTION_ONLY',relative_density_height_effect_P95=float(np.percentile(effect,95)),
        relative_density_height_effect_max=float(effect.max()),samples=len(effect),
        passed=bool(np.percentile(effect,95)<=limits['reference_density_difference_due_only_to_reconstructed_height_p95_limit'] and effect.max()<=limits['reference_density_difference_due_only_to_reconstructed_height_max_limit']),
        WGS84_to_ZG_registration_solved=False,future_AI_height_accuracy_proven=False)
    dump(F/'height_gate.json',gate)
    ai,ref=chosen_providers()
    if not ai.valid.all():raise ValueError('Selected AI frames have invalid mass/height columns')
    # Exact original grid-point round trip (with all-eight-column coverage checked).
    checks=[]
    for j,i,k in ((10,20,20),(18,36,21),(25,60,22)):
        q=ai(ai.epochs[0],lat[j],lon[i],ai.height[0,k,j,i],datum=DATUM)
        assert q.valid
        ratio=q.rho_kg_m3/ai.rho[0,k,j,i];assert abs(ratio-1)<1e-12
        checks.append(dict(lat_index=j,lon_index=i,ilev_index=k,relative_error=ratio-1))
    table(O/'real_grid_point_checks.csv',checks)
    # Same UTC, native pressure layers: no geometric interpretation involved.
    with np.load(paths(DAY)[0]/f'{DAY}_Direct.npz') as n:
        ph=decode_physical(n['pred'][0,:2],n['means'][:171],n['stds'][:171])
    truth=raw(DAY,2)['DEN'];ratio=ph[1,142:171]/truth-1
    layer=[]
    for k in range(29):layer.append(dict(ilev_index=k,ilev=float(iv[k]),relative_RMS=float(np.sqrt(np.mean(ratio[k]**2))),absolute_relative_P95=float(np.percentile(abs(ratio[k]),95))))
    table(O/'native_layer_comparison.csv',layer)
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,2,figsize=(12,4))
    maps=[]
    for p in (ref,ai):
        field=np.full((len(lat),len(lon)),np.nan)
        # Grid-point columns directly; full stencil queries qualified separately.
        for j in range(len(lat)):
            for i in range(len(lon)):
                h=p.height[1,:,j,i]
                if p.valid[1,j,i] and h[0]<=450000<=h[-1]:field[j,i]=np.exp(np.interp(450000,h,np.log(p.rho[1,:,j,i])))
        maps.append(field)
    vmin=min(np.nanmin(m) for m in maps);vmax=max(np.nanmax(m) for m in maps)
    for ax,z,title in zip(axs,maps,['TIE-GCM reference ZG','AI Direct reconstructed native ZG']):
        im=ax.pcolormesh(lon,lat,z,vmin=vmin,vmax=vmax,shading='auto');ax.set(title=title,xlabel='Longitude (deg)',ylabel='Model latitude (deg)');fig.colorbar(im,ax=ax,label='kg/m3')
    fig.suptitle(DAY+' 02 UTC | native 450 km | external datum unverified');fig.tight_layout();fig.savefig(O/'global_density.png',dpi=150);plt.close(fig)
    np.savez_compressed(F/'global_density_fields.npz',reference=maps[0],AI=maps[1],lat=lat,lon=lon)
    fig,ax=plt.subplots(figsize=(7,4));ax.plot([r['relative_RMS']*100 for r in layer],iv,'o-');ax.set(xlabel='DEN relative RMS (%)',ylabel='Native ilev (not fixed altitude)',title='Mar24 Direct +1h: original pressure interfaces');fig.tight_layout();fig.savefig(O/'native_layer_error.png',dpi=150);plt.close(fig)
    # Reuse complete historical curves; never fit a curve through sampled leads.
    curve=[]
    for day,prefix in [('2023-01-04','fourcastden_twelve_hour_jan4_v1'),(DAY,'fourcastden_twelve_hour_mar24_v1')]:
        with (ROOT/f'results/metrics/{prefix}_windows.csv').open() as f:
            for row in csv.DictReader(f):curve.append({k:row[k] for k in ('date','model','hour','near400_500_mean_relative_RMS','upper20_28_mean_relative_RMS','top_relative_RMS')})
    table(O/'existing_error_growth.csv',curve)
    fig,axs=plt.subplots(1,2,figsize=(12,4))
    for ax,day in zip(axs,('2023-01-04',DAY)):
        for model in ('Direct','Flow','LogDEN','History'):
            c=sorted([v for v in curve if v['date']==day and v['model']==model],key=lambda v:int(v['hour']))
            ax.plot([int(v['hour']) for v in c],[100*float(v['near400_500_mean_relative_RMS']) for v in c],label=model)
        ax.set(title=day,xlabel='Lead (hour)',ylabel='Reference 400-500km layer-group relative RMS (%)');ax.legend()
    fig.tight_layout();fig.savefig(O/'existing_12hour_error_growth.png',dpi=150);plt.close(fig)
    dump(F/'analysis.json',dict(height_gate=gate,analysis_wall_s=time.monotonic()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,prediction_height_records=prediction))
    print(json.dumps(gate),flush=True)


class VirtualBridge:
    """Explicit private assumption, never installed in the formal density API."""
    def __init__(self,provider,record):self.provider,self.records=provider,record
    def density_kg_m3(self,q):
        tick=time.perf_counter()
        result=self.provider(q.utc,q.latitude_deg,q.longitude_deg,q.height_wgs84_m,datum=DATUM)
        if not result.valid:raise ValueError('Virtual query invalid: '+result.reason)
        self.records.append(dict(utc=q.utc.isot,lat=q.latitude_deg,lon=q.longitude_deg,virtual_native_height_m=q.height_wgs84_m,
            rho_kg_m3=result.rho_kg_m3,query_s=time.perf_counter()-tick,top_margin_m=result.metadata['top_margin_m']))
        return result.rho_kg_m3


def integrate():
    from orbit.frames import configure_time_data
    from orbit.common_force_model import CommonForceModel
    from orbit.drag import DragForce,DragProperties,EarthFixedFrame
    from orbit.rk45_propagator import propagate
    from orbit.two_body import make_state_derivative
    from atmosphere.msis_density_provider import MsisDensityProvider,FrozenGfzDrivers
    from unittest.mock import patch
    import pymsis.utils,shutil
    protocol=json.loads((F/'protocol.json').read_text());assert json.loads((F/'height_gate.json').read_text())['passed']
    if (F/'integration_once.json').exists():raise FileExistsError('No model/sequence retry allowed')
    assert shutil.disk_usage(ROOT).free>20*1024**3
    for p,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==h,p
    dump(F/'integration_once.json',dict(max_propagations=8,no_retry=True))
    started=time.monotonic();configure_time_data();epoch=Time(protocol['start'],scale='utc')
    force=CommonForceModel(epoch,3600);frame=EarthFixedFrame(epoch)
    ai,ref=chosen_providers();props=DragProperties(400,1,2.2,'SYNTHETIC / VIRTUAL_SATELLITE / not Swarm parameters')
    msis=MsisDensityProvider(FrozenGfzDrivers(ROOT/'configs/nrlmsis2023_gfz_frozen.json'),version='2.1')
    radius=protocol['controls']['initial_GCRS_radius_m'];speed=np.sqrt(398600441500000./radius)
    initial=np.array([radius,0.,0.,0.,speed*.5,speed*np.sqrt(3)/2])
    np.save(F/'initial_GCRS_state.npy',initial)
    all_states={};runs=[]
    def deny_download(*args,**kwargs):raise RuntimeError('Weather download forbidden')
    with patch.object(pymsis.utils,'get_f107_ap',deny_download):
        for mode in ('base','tight'):
            for name in protocol['models']:
                if time.monotonic()-started>600:raise RuntimeError('Propagation wall budget')
                marker=F/f'{name}_{mode}_launch.json';dump(marker,dict(name=name,mode=mode,labels=LABELS))
                records=[];drag=None
                provider=msis if name=='B_NRLMSIS21' else (VirtualBridge(ref,records) if name=='C_TIE_reference' else VirtualBridge(ai,records))
                if name!='A_no_drag':drag=DragForce(frame,provider,props)
                rhs=make_state_derivative([force] if drag is None else [force,drag])
                def guarded(t,y):
                    if time.monotonic()-started>600:raise RuntimeError('Propagation wall budget')
                    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>1536*1024:raise RuntimeError('RSS budget')
                    if shutil.disk_usage(ROOT).free<20*1024**3:raise RuntimeError('Disk floor')
                    return rhs(t,y)
                options=protocol['controls'][mode]
                print('BEGIN',name,mode,flush=True)
                solution=propagate(guarded,initial[:3],initial[3:],(0,3600),np.arange(0,3601,60),**options)
                samples=[]
                for t,y in zip(solution.times_s,solution.states):
                    result=drag.evaluate(t,y[:3],y[3:]) if drag else None
                    samples.append(dict(model=name,mode=mode,seconds=float(t),rho_kg_m3=0. if result is None else result['density_kg_m3'],drag_norm_m_s2=0. if result is None else float(np.linalg.norm(result['acceleration_gcrs_m_s2']))))
                table(O/f'{name}_{mode}_samples.csv',samples)
                if records:table(F/f'{name}_{mode}_native_queries.csv',records)
                np.savez_compressed(F/f'{name}_{mode}_states.npz',seconds=solution.times_s,states=solution.states)
                all_states[name+'_'+mode]=solution.states
                summary=dict(model=name,mode=mode,**solution.statistics,native_query_count=len(records),
                    native_query_time_s=sum(x['query_s'] for x in records),peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
                runs.append(summary);dump(F/f'{name}_{mode}_runtime.json',summary)
                print('END',name,mode,solution.statistics['elapsed_s'],flush=True)
                if sum(p.stat().st_size for p in F.rglob('*') if p.is_file())>100*1024**2:raise RuntimeError('Output budget')
    table(O/'performance.csv',runs)
    converged=[]
    for name in protocol['models']:
        delta=all_states[name+'_base'][:,:3]-all_states[name+'_tight'][:,:3]
        error=float(np.linalg.norm(delta,axis=1).max())
        converged.append(dict(type='single',comparison=name,max_position_m=error,limit_m=.02,passed=error<=.02))
    for name in protocol['models'][1:]:
        b=all_states[name+'_base'][:,:3]-all_states['A_no_drag_base'][:,:3]
        t=all_states[name+'_tight'][:,:3]-all_states['A_no_drag_tight'][:,:3]
        error=float(np.linalg.norm(b-t,axis=1).max());limit=.01*float(np.linalg.norm(t,axis=1).max())
        converged.append(dict(type='pair',comparison=name+' minus A',max_position_m=error,limit_m=limit,passed=error<=limit))
    table(O/'convergence.csv',converged)
    dump(F/'integration.json',dict(labels=LABELS,completed_propagations=len(runs),wall_s=time.monotonic()-started,
        peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,convergence_pass=all(r['passed'] for r in converged),
        real_SP3_accuracy_evaluation=False,AI_future_reference_ZG_used=False,formal_external_interface_enabled=False))


def finalize():
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    protocol=json.loads((F/'protocol.json').read_text());data={}
    for name in protocol['models']:
        with np.load(F/f'{name}_tight_states.npz') as n:data[name]=n['states'].copy();seconds=n['seconds'].copy()
    baseline=data['A_no_drag'];radial=baseline[:,:3]/np.linalg.norm(baseline[:,:3],axis=1)[:,None]
    normal=np.cross(baseline[:,:3],baseline[:,3:]);normal/=np.linalg.norm(normal,axis=1)[:,None]
    along=np.cross(normal,radial);rows=[]
    fig,axs=plt.subplots(1,2,figsize=(12,4))
    for name in protocol['models'][1:]:
        d=data[name][:,:3]-baseline[:,:3]
        for k in range(len(seconds)):
            rows.append(dict(comparison=name+' minus A',seconds=float(seconds[k]),norm_m=float(np.linalg.norm(d[k])),R_m=float(d[k]@radial[k]),A_m=float(d[k]@along[k]),C_m=float(d[k]@normal[k])))
        axs[0].plot(seconds/3600,np.linalg.norm(d,axis=1),label=name)
        with (O/f'{name}_tight_samples.csv').open() as f:s=list(csv.DictReader(f))
        axs[1].plot(seconds/3600,[float(x['rho_kg_m3']) for x in s],label=name)
    axs[0].set(xlabel='Elapsed hour',ylabel='Position difference to no drag (m)',title='Virtual orbit; model differences, not accuracy')
    axs[1].set(xlabel='Elapsed hour',ylabel='Density on each own trajectory (kg/m3)',title='Conditional WGS84-as-native-ZG assumption')
    for ax in axs:ax.legend()
    fig.tight_layout();fig.savefig(O/'orbit_differences_and_density.png',dpi=150);plt.close(fig)
    table(O/'position_RAC_differences.csv',rows)
    fig,axs=plt.subplots(1,3,figsize=(13,4))
    for ax,key in zip(axs,('R_m','A_m','C_m')):
        for name in protocol['models'][1:]:
            z=[x for x in rows if x['comparison']==name+' minus A'];ax.plot(seconds/3600,[x[key] for x in z],label=name)
        ax.set(xlabel='Elapsed hour',ylabel=key,title='Virtual orbit difference')
    axs[0].legend();fig.tight_layout();fig.savefig(O/'orbit_RAC.png',dpi=150);plt.close(fig)
    fig=plt.figure(figsize=(7,6));ax=fig.add_subplot(projection='3d')
    for name,states in data.items():ax.plot(*states[:,:3].T/1000,label=name)
    ax.set(xlabel='GCRS X (km)',ylabel='Y (km)',zlabel='Z (km)',title='1h virtual orbit (curves nearly overlap)');ax.legend();fig.tight_layout();fig.savefig(O/'virtual_orbits_3d.png',dpi=150);plt.close(fig)
    # D versus C is the conditional AI/reference trajectory difference.
    dc=data['D_AI_Direct'][:,:3]-data['C_TIE_reference'][:,:3]
    summary=dict(AI_minus_reference_end_m=float(np.linalg.norm(dc[-1])),AI_minus_reference_max_m=float(np.linalg.norm(dc,axis=1).max()),
        AI_minus_reference_RMS_m=float(np.sqrt(np.mean(np.sum(dc**2,axis=1)))),
        model_difference_not_real_prediction_error=True,
        end_differences={name:float(np.linalg.norm(states[-1,:3]-baseline[-1,:3])) for name,states in data.items()})
    dump(O/'orbit_summary.json',summary)
    protected=json.loads((F/'protected.json').read_text());changed=[p for p,h in protected.items() if sha(ROOT/p)!=h]
    assert not changed,changed
    dump(O/'delivery_audit.json',dict(protected_inputs_verified=len(protected),changed=changed,
        new_GPU_forwards=0,new_TIE_integrations=0,new_training_steps=0,
        outputs_SHA256={str(p.relative_to(ROOT)):sha(p) for p in list(F.glob('*'))+list(O.glob('*')) if p.is_file()}))
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','analyze','integrate','finalize']);args=parser.parse_args()
    try:globals()[args.phase]()
    except Exception:
        traceback.print_exc()
        if F.exists():
            path=F/f'{args.phase}_failure_{time.time_ns()}.json'
            dump(path,dict(phase=args.phase,error=traceback.format_exc(),no_retry=True))
        raise
