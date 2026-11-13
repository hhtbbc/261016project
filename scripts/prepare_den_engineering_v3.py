"""Freeze v3 before any extraction/statistics fitting or GPU task."""
from pathlib import Path
import sys,json,shutil,subprocess,os
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_tiegcm_mar23_2021_longrun import stream_sha
from training.den_engineering import F,O,DATA,LABEL,PHYS,LBC,LENS,CHANNELS,DEN_INDICES
def write(p,j):
 with p.open('x') as out:json.dump(j,out,indent=2)
if __name__=='__main__':
 assert not (F/'protocol.json').exists()
 sources={2021:ROOT/'experiments/tiegcm_2021_spinup_14day_v1/B14',2022:ROOT/'experiments/tiegcm_2022_b14_exploratory_pair_v2/B14'}
 protected={}
 for year,folder in sources.items():
  audit=json.loads((folder/'data_audit.json').read_text());assert audit['engineering_PASS']
  status=json.loads((folder/'run_status.json').read_text());assert status['returncode']==0 and status['normal_exit_count']==4
  for p in folder.rglob('*'):
   if p.is_file():protected[str(p.relative_to(ROOT))]=stream_sha(p)
  source=str(folder.relative_to(ROOT))
 for folder in [ROOT/'data/processed/training_window_mar23_v2',ROOT/'models/checkpoints',ROOT/'data/processed/static']:
  for p in folder.rglob('*'):
   if p.is_file():protected[str(p.relative_to(ROOT))]=stream_sha(p)
 for p in [ROOT/'src/training/pipeline.py',ROOT/'src/training/readonly_interface.py',ROOT/'third_party/FourCastDEN_linux/models/afnonet.py',ROOT/'third_party/FourCastDEN_linux/dataset/dataset_tiegcm.py',ROOT/'third_party/FourCastDEN_linux/dataset/tiegcm_utils.py']:
  protected[str(p.relative_to(ROOT))]=stream_sha(p)
 assert shutil.disk_usage(ROOT).free>22*2**30
 protocol=dict(label=LABEL,sources={str(y):str(p.relative_to(ROOT)) for y,p in sources.items()},
   windows={'2021':['2021-03-23T00:00:00Z','2021-03-26T00:00:00Z'],'2022':['2022-03-23T00:00:00Z','2022-03-25T00:00:00Z']},
   frames={'2021':73,'2022':49},pairs={'2021':72,'2022':48},
   channel_order=PHYS+LBC,lengths=LENS,DEN_output_indices=DEN_INDICES.tolist(),DEN_grid='ilev, all29',native_units='author native CGS, SI evaluation DEN*1000',
   inputs='current171 + next-hour LBC3 / solar1 / magnetic2',conditions='next-hour F107/F107A/Kp affine fixed author bounds + solar sfeps',
   normalization='float64 Welford per variable/layer; population std; only73 training frames2021; spatial/time equally weighted; no logDEN',
   small_std_rule='std<=1e-12*max(abs(mean),maxabs,float64tiny): use abs(mean) if nonzero else1 native unit; never modify raw values',
   relative_error_rule='all finite, strictly positive target DEN; no denominator floor; negative finite predictions remain in RMSE/relative RMS; log only positive predictions with coverage',
   loss='cos(latitude)-weighted normalized DEN29 MSE, equal layer weights',
   scheme='A: original AFNONet171 output, only DEN supervised; other142 NOT trained state; single-step only',
   alternative_B='29 output head changes model and official compatibility; not selected this round',
   statistical_status='ENGINEERING_ONLY; full SCIENCE_TRAINING_READY remains False',
   sample_selection={'train_steps':'first10 chronological training pairs, no shuffle','validation':'all48 independent2022 pairs','display_validation_pair_index':0,'checkpoint_probe_pair_index':0},
   GPU_max_launches=1,GPU_max_updates=10,GPU_wall_limit_s=900,GPU_allocated_limit_bytes=20*2**30,GPU_output_limit_bytes=2*2**30,disk_floor_bytes=20*2**30,
   estimated_dataset_MiB=300,estimated_single_checkpoint_MiB=750,estimated_training_wall_s=120,estimates_not_measurements=True,
   seed=20261113,optimizer=dict(name='AdamW',lr=1e-4,weight_decay=0.0),scheduler=dict(step_size=1,gamma=1.),gradient_clip_norm=1.,
   no_official_weights=True,no_2023_data=True,no_A14_labels=True,no_old_122_replacement=True)
 write(F/'protocol.json',protocol);write(F/'protected_files.json',protected)
 write(F/'resource_preflight_initial.json',dict(free_disk_bytes=shutil.disk_usage(ROOT).free,GPU=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.free','--format=csv'],text=True),processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv'],text=True),CPU_affinity=len(os.sched_getaffinity(0))))
 print('Protocol frozen, protected',len(protected))
