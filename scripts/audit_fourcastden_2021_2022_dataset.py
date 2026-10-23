"""Read-only joint dataset diagnostics: no normalization fitting, models or training."""
import json,csv,hashlib,sys
from pathlib import Path
from datetime import datetime,timedelta,timezone
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from fourcastden.multidate import validate_npz,KEYS
F=R/'experiments/tiegcm_training_mar23_v2_2022_longrun';OUT=R/'results/fourcastden_2021_2022_dataset_v2'
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
 return h.hexdigest()
def main():
 OUT.mkdir(exist_ok=False);summaries={};epochs={};allrows=[];phys={};configs={}
 for y,count in [(2021,73),(2022,49)]:
  folder=R/f'experiments/tiegcm_training_mar23_v2_{y}_longrun';c=json.loads((folder/'candidate_audit.json').read_text());audit=json.loads((folder/'data_audit.json').read_text());pre=json.loads((folder/'preflight.json').read_text())
  assert c['count']==count and c['continuous_pairs']==count-1 and not c['training_approved']
  assert c['official_input_exact'] and c['future_target_poison_checks']==count-1
  assert not any(c[k] for k in ['training_statistics_fitted','model_instantiated','model_forwards','backward','optimizer_steps'])
  assert ('TRAINING_CANDIDATE_ONLY' if y==2021 else 'VALIDATION_CANDIDATE_ONLY') in c['labels']
  for entry in audit['files']:assert sha(folder/entry['file'])==entry['SHA256']
  for entry in c['frames']:
   p=R/entry['file'];assert sha(p)==entry['SHA256'];validate_npz(p)
  epochs[y]=[datetime.fromisoformat(e['UTC']) for e in c['frames']]
  assert epochs[y]==[datetime(y,3,23,tzinfo=timezone.utc)+timedelta(hours=i) for i in range(count)]
  for k in ['lat','lon','lev','ilev']:
   p=R/f'data/processed/training_window_mar23_v2/candidates_{y}/{k}.npy';assert sha(p)==c['grid_sidecars'][k];np.testing.assert_array_equal(np.load(p),np.load(R/f'data/processed/static/{k}.npy'))
  phys[y]={k:(v['unit'],v['dimensions'],v['dtype']) for k,v in audit['fields'].items()}
  configs[y]={k:pre[k] for k in ['executable_sha256','restart_sha256','apex_sha256']}
  with (R/f'results/tiegcm_training_mar23_v2_{y}_longrun/hourly_diagnostics.csv').open() as f:rows=list(csv.DictReader(f))
  rows=[r for r in rows if r['stage'] in ['TRAINING_CANDIDATE_ONLY','VALIDATION_CANDIDATE_ONLY']];assert len(rows)==count
  keys=['DEN450_mean_kg_m3','TN_mean_K','horizontal_wind_RMS_m_s','f107d','f107a','Kp']
  # Summaries of physical hourly diagnostics, NOT per-channel normalization statistics.
  summary={}
  for k in keys:
   x=np.array([float(r[k]) for r in rows]);summary[k]={'min':float(x.min()),'median':float(np.median(x)),'max':float(x.max())}
  summaries[y]={'role':'TRAINING_CANDIDATE_ONLY' if y==2021 else 'VALIDATION_CANDIDATE_ONLY','frames':count,'pairs':count-1,'diagnostics_only':summary,'NPZ_bytes':sum(e['bytes'] for e in c['frames']),'first_UTC':c['frames'][0]['UTC'],'last_UTC':c['frames'][-1]['UTC'],'gpi_SHA256':pre['gpi_sha256']}
  for h,row in enumerate(rows):allrows.append({'year':y,'lead_hour_in_candidate_window':h,**{k:float(row[k]) for k in keys}})
 assert not set(epochs[2021])&set(epochs[2022]);assert phys[2021]==phys[2022];assert configs[2021]==configs[2022]
 with (OUT/'candidate_hourly_comparison.csv').open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=list(allrows[0]),lineterminator='\n');w.writeheader();w.writerows(allrows)
 result={'status':'ENGINEERING_CANDIDATE_DATASET_PASS','years':summaries,'total_frames':122,'total_continuous_pairs':120,'epochs_disjoint':True,'identical_grid_units_padding_and_model':True,'physical_contract':phys[2021],'common_input_hashes':configs[2021],'training_statistics_fitted':False,'scientific_training_READY':False,'spinup_status':'SPINUP_SUFFICIENCY_UNVERIFIED','statistical_limit':'Hours are serially correlated; no independent grid-point replicas or significance claims','comparison_scope':'Two different hindcast years/drivers, NOT initial-condition sensitivity or observational truth'}
 (F/'joint_dataset_audit.json').write_text(json.dumps(result,indent=2,allow_nan=False))
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,axes=plt.subplots(3,2,figsize=(11,9))
 units=['kg/m3','K','m/s','sfu','sfu','1']
 for ax,k,u in zip(axes.flat,keys,units):
  for y in [2021,2022]:
   rows=[a for a in allrows if a['year']==y];ax.plot([a['lead_hour_in_candidate_window'] for a in rows],[a[k] for a in rows],label=str(y))
  ax.set_title(k,fontsize=9);ax.set_ylabel(u);ax.set_xlabel('Hours since each Mar23 00 UTC');ax.grid(alpha=.25);ax.legend()
 fig.suptitle('INDEPENDENT / HINDCAST / SPINUP UNVERIFIED / CANDIDATES ONLY',fontsize=10);fig.tight_layout();fig.savefig(OUT/'two_year_physical_diagnostics.png',dpi=130);plt.close(fig)
 print('JOINT DATASET READ-ONLY PASS 73 + 49; SCIENTIFIC READY FALSE')
if __name__=='__main__':main()
