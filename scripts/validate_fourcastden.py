"""Validate dependencies, CUDA, real input and an author Direct checkpoint; no training."""
from pathlib import Path
import sys,json,time,importlib,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'third_party/FourCastDEN_linux'))
OUT=ROOT/'experiments/20261019_minimal_direct'; OUT.mkdir(exist_ok=True)
report={'status':'started','stages':{}}
def save(): (ROOT/'logs/minimal_validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
try:
    import numpy as np,torch
    for name in ['torch','torchvision','numpy','timm','einops','ruamel.yaml','netCDF4','ppigrf','matplotlib','cartopy','sympy']:
        m=importlib.import_module(name);report['stages'].setdefault('imports',{})[name]=getattr(m,'__version__','imported')
    report['python']=sys.version;report['prefix']=sys.prefix
    assert torch.cuda.is_available()
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    torch.backends.cudnn.benchmark=False
    x=torch.arange(16,device='cuda',dtype=torch.float32).reshape(4,4)
    error=(torch.fft.irfft2(torch.fft.rfft2(x),s=x.shape)-x).abs().max().item()
    assert error<1e-5
    report['stages']['cuda']={'device':torch.cuda.get_device_name(0),'torch_cuda':torch.version.cuda,'fft_max_error':error,'fp32_tf32_disabled':True};save()
    # Actual archive values, never synthetic thermospheric inputs.
    data_checks={}
    for p in sorted((ROOT/'data/raw/test_minimal_2023').glob('*.npz')):
        with np.load(p,allow_pickle=False) as f:
            data_checks[p.name]={k:{'shape':list(f[k].shape),'dtype':str(f[k].dtype),'finite':bool(np.isfinite(f[k]).all()),'min':float(f[k].min()),'max':float(f[k].max())} for k in f.files}
            assert all(i['finite'] for i in data_checks[p.name].values())
            assert (f['DEN']>0).all()
    report['stages']['real_data']=data_checks
    static=ROOT/'data/processed/static'
    report['stages']['coordinates']={}
    for name in ['lat','lon','lev','ilev']:
        a=np.load(static/(name+'.npy'),allow_pickle=False)
        report['stages']['coordinates'][name]={'shape':list(a.shape),'values':a.tolist()}
    from ruamel.yaml import YAML
    yaml=YAML();cfg=yaml.load((ROOT/'third_party/FourCastDEN/config/AFNO.yaml').read_text())
    config=cfg['afno_inference']
    checkpoint_dir=ROOT/'models/checkpoints/author'
    candidates=[p for p in checkpoint_dir.rglob('*') if p.is_file() and 'direct' in p.name.lower()]
    assert len(candidates)==1,[str(p) for p in candidates]
    ckpt=candidates[0]
    shape=data_checks['2023_01_04_000000.npz']['TN']['shape'][-2:]
    config.update(img_shape_x=shape[0],img_shape_y=shape[1],device='gpu',test_data_path=str(ROOT/'data/raw/test_minimal_2023'),static_data_path=str(static),best_checkpoint_path=str(ckpt),flow=False,n_history=0,log_DEN=False,n_prediction=1,pre_day=1,ics_type='default',perturb=False,step_con=False,result_save=True,pre_resultname='direct_one_hour',num_workers=0)
    conf=ROOT/'configs/fourcastden_direct_minimal.yaml'
    with conf.open('w') as f:yaml.dump({'afno_inference':config},f)
    from utils.YParams import YParams
    params=YParams(str(conf),'afno_inference');params['experiment_dir']=str(OUT)
    from inference.inference import TGCMForecast
    start=time.time();forecast=TGCMForecast(params)
    report['stages']['model']={'parameters':sum(p.numel() for p in forecast.model.parameters()),'in_channels':params.n_in_channels,'out_channels':params.n_out_channels,'scalar_inputs':params.n_in_indices,'checkpoint':str(ckpt.relative_to(ROOT)),'strict_loading':True,'seconds_to_load':time.time()-start}
    # Ensure all relevant normalization scales are positive and finite.
    assert torch.isfinite(forecast.means).all() and torch.isfinite(forecast.stds).all() and (forecast.stds>0).all()
    assert (forecast.dataset.means_sw.shape==(3,))
    inp,sw=forecast.dataset.get_data([0])
    assert tuple(inp.shape)==(1,177,36,72) and tuple(sw.shape)==(1,4)
    report['stages']['input']={'fields':list(inp.shape),'scalars':list(sw.shape),'finite':bool(torch.isfinite(inp).all() and torch.isfinite(sw).all())};save()
    start=time.time();real,pred,rmse,acc,acc_u,last_time,stds,means=forecast.inference(0);torch.cuda.synchronize()
    assert np.isfinite(pred).all() and np.isfinite(rmse).all() and np.isfinite(acc).all()
    np.savez_compressed(OUT/'result.npz',real=real,pred=pred,rmse=rmse,acc=acc,acc_unweighted=acc_u,means=means,stds=stds)
    summaries={}
    for name in forecast.out_variables:
        idx=params.index[name];summaries[name]={'rmse_mean':float(rmse[0,0,idx].mean()),'rmse_max':float(rmse[0,0,idx].max()),'acc_mean':float(acc[0,0,idx].mean()),'acc_min':float(acc[0,0,idx].min())}
    den_idx=params.index['DEN']; physical_den=pred[0,1,den_idx]*stds[den_idx]+means[den_idx]
    summaries['DEN']['predicted_g_cm3_min']=float(physical_den.min());summaries['DEN']['predicted_g_cm3_max']=float(physical_den.max());summaries['DEN']['positive_fraction']=float((physical_den>0).mean())
    report['stages']['one_hour_inference']={'initial_time_utc':'2023-01-04T00:00:00Z','target_time_utc':'2023-01-04T01:00:00Z','returned_last_loaded_time':str(last_time),'seconds':time.time()-start,'real_shape':list(real.shape),'pred_shape':list(pred.shape),'note':'pred includes initialization at index0; compare index1. real includes auxiliary fields. Metrics are against TIE-GCM only.','metrics':summaries,'gpu_peak_allocated_bytes':torch.cuda.max_memory_allocated()}
    report['status']='passed_execution_checks_not_physical_validation'
except Exception:
    report['status']='failed';report['traceback']=traceback.format_exc();print(report['traceback']);save();raise
save();print(json.dumps(report,indent=2,ensure_ascii=False))
