"""Independent package and preservation checks; no model or observation queries."""
from pathlib import Path
import hashlib,json,csv,time,resource
R=Path(__file__).resolve().parents[1];F=R/'experiments/tiegcm_zg_external_registration_v2'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(2**20),b''):h.update(x)
 return h.hexdigest()
def main():
 t=time.perf_counter();cpu=time.process_time();p=json.loads((F/'protocol.json').read_text());s=json.loads((F/'source_preservation.json').read_text());m=json.loads((F/'model_configuration_manifest.json').read_text())
 for n,h in s['before_SHA256'].items():
  path=R/n;path.resolve().relative_to(R);assert sha(path)==h,n
 for n,h in p['history_protected_SHA256'].items():assert sha(R/n)==h,n
 q=list(csv.DictReader((F/'question_evidence_matrix.csv').open()));a=list(csv.DictReader((F/'response_acceptance_matrix.csv').open()));assert len(q)==7 and len(a)==7
 assert sum(x['status']=='PARTIALLY_VERIFIED' for x in q)==5 and sum(x['status']=='UNVERIFIED' for x in q)==2
 assert all(x['automatic_interface_release']=='False' for x in a)
 for y in ['2021','2022']:
  c=m['B14_cases'][y];n=m['NetCDF_metadata'][y];assert c['ibgrddata']==0 and c['GSWM_migrating_diurnal'] and c['GSWM_migrating_semidiurnal'];assert n['variables']['DEN']['dimensions']==n['variables']['ZG']['dimensions']==['time','ilev','lat','lon'];assert n['variables']['DEN']['attributes']['units']=='g/cm3' and n['variables']['ZG']['attributes']['units']=='cm';assert sha(R/n['file']['path'])==n['file']['SHA256']
 for field in ['messages_sent','GPU','DART','model_integrations','density_queries','correction_fits']:assert p[field if field!='messages_sent' else 'sent_messages']==0
 email=(R/'docs/TIEGCM_ZG_EXTERNAL_REGISTRATION_REQUEST_V2.md').read_text();assert all(x in email for x in ['[Name]','[Affiliation]','[Email]','NOT SENT','**A.','**B.','**C.','**D.','do not regard query coverage','DELIVERY_AND_CURRENT_OWNERSHIP_UNVERIFIED']);assert m['author_2023_run'].startswith('Separate author')
 assert json.loads((F/'response_validation_checklist.json').read_text())['all_satisfied'] is False
 result=dict(PASS=True,protected_files_checked=len(s['before_SHA256']),question_count=7,PARTIALLY_VERIFIED=5,UNVERIFIED=2,VERIFIED_complete_external_questions=0,response_types=7,automatic_release_rows=0,actual_NetCDF_metadata_cases=2,sent=False,external_gate='EXTERNAL_DATUM_UNVERIFIED',wall_s=time.perf_counter()-t,CPU_s=time.process_time()-cpu,peak_process_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
 with (F/'independent_verification.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result))
if __name__=='__main__':main()
