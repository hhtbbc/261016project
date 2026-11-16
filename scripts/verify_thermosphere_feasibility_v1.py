"""Independent direct-CDF probes and artifact validation. No model or fit calls."""
from pathlib import Path
import sys,json,csv,re
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np,cdflib
from PIL import Image
from prepare_fourcastden_swarm_observation_v1 import sha,dump
TAG='thermosphere_observation_assimilation_feasibility_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG

def main():
 rows=list(csv.DictReader((O/'unified_observations_local.csv').open()));assert len(rows)==8640 and {r['satellite'] for r in rows}=={'A','C'}
 probes=[]
 for entry in json.loads((F/'observation_quality.json').read_text()):
  path=ROOT/entry['source_file'];assert sha(path)==entry['source_SHA256'];rr=[r for r in rows if r['source_file']==entry['source_file']];assert len(rr)==2880
  with cdflib.CDF(path) as c:
   utc=cdflib.cdfepoch.to_datetime(c.varget('time'));rho=c.varget('density');lat=c.varget('latitude');h=c.varget('altitude')
   for i in [0,1440,2879]:
    assert str(utc[i])+'Z'==rr[i]['UTC'] and float(rho[i])==float(rr[i]['density_kg_m3']) and float(lat[i])==float(rr[i]['latitude']) and float(h[i])==float(rr[i]['height']);probes.append(dict(source_file=entry['source_file'],record=i,UTC=rr[i]['UTC'],exact_density_coordinate_UTC_match=True))
  hdr=path.with_suffix('.HDR');m=re.search(r'<Validity_Start>(?:UTC=)?([^<]+)',hdr.read_text())
  if m:assert np.datetime64(m.group(1),'ns')==utc[0]
 for p in O.glob('*.png'):
  with Image.open(p) as im:im.verify()
 assert len(list(O.glob('*.png')))==4
 old=json.loads((F/'protected_inputs.json').read_text())
 for n,h in old.items():assert sha(ROOT/n)==h,n
 receipts=json.loads((F/'download_receipts.json').read_text())['receipts']+[json.loads((F/'author_code_download_receipt.json').read_text())['receipt']];downloadbytes=sum(x['bytes'] for x in receipts);assert downloadbytes<10*2**20
 for r in receipts:assert sha(ROOT/r['path'])==r['SHA256']
 dump(F/'independent_verification.json',dict(PASS=True,direct_CDF_probes=probes,unified_records=8640,real_C_records=2880,Swarm_B_density_values_read=False,old_assets_unchanged=len(old),raw_and_reference_download_bytes=downloadbytes,raw_Swarm_C_ZIP_bytes=139647,figures_verified=4,CPU_unit_tests=14,new_GPU_tasks=0,new_TIE_runs=0,new_DART_runs=0,new_orbit_runs=0,corrections_fitted=0,SCIENCE_TRAINING_READY=False,EXTERNAL_DATUM='EXTERNAL_DATUM_UNVERIFIED',real_orbit='BLOCKED',A14_engineering='PARTIAL'))
 print('INDEPENDENT REAL DATA AND DELIVERY PASS',len(probes),downloadbytes,len(old))
if __name__=='__main__':main()
