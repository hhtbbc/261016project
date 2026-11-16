"""Independent recursive export redaction audit; never sends or subscribes."""
from pathlib import Path
import csv,json,hashlib,re,time,resource,socket,getpass
R=Path(__file__).resolve().parents[1];F=R/'experiments/tiegcm_zg_external_registration_v2_1'
ALLOWED={'technical_summary_external.md','question_evidence_matrix_external.csv','configuration_summary_external.json','SENDING_GUIDE.md'}
OFFICIAL_EMAILS={'tgcmgroup@mailman.ucar.edu','tgcmgroup@ucar.edu'}
DENIED_KEYS={'host','hostname','logname','username','user_name','source_file','initial_file','runtime_log','input_path','output_path','password','passwd','token','credential','credentials','private_key','home','cwd','path'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def scan_text(s,where,private_terms=()):
 issues=[]
 # Public source URLs are allowed; absolute/local paths are not.
 without_urls=re.sub(r'https?://[^\s<>"\)]+','<PUBLIC_URL>',s)
 patterns={'unix_absolute_path':r'(?<![\w:])/(?:[\w.~-]+/)+[\w.~-]*','forbidden_absolute_prefix':r'/(?:workspace|root|home|tmp)(?:/|\b)','windows_or_UNC_path':r'(?:\b[A-Za-z]:[\\/]|\\\\[A-Za-z])','project_relative_path':r'\b(?:experiments/|data/raw/|logs/|third_party/|\.venv/)', 'credential_assignment':r'\b(?:password|passwd|secret|access_token|api_key|authorization)\s*[:=]\s*\S+', 'known_token_pattern':r'(?:github'+'_pat_|gh'+'p_|sk-'+'[A-Za-z0-9]{12})', 'original_data_filename':r'(?i)(?:secondary_\d+|primary_\d+)\.nc|SW_[A-Z0-9_]+\.(?:cdf|zip|hdr)'}
 for k,p in patterns.items():
  if re.search(p,without_urls,re.I):issues.append(dict(location=where,category=k))
 for email in re.findall(r'[A-Za-z0-9_.+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',s):
  if email.lower() not in OFFICIAL_EMAILS:issues.append(dict(location=where,category='nonapproved_email'))
 for term in private_terms:
  if term and re.search(r'(?<![\w])'+re.escape(term)+r'(?![\w])',s,re.I):issues.append(dict(location=where,category='actual_host_or_account_value'))
 return issues

def scan_json(x,where='$',private_terms=()):
 out=[]
 if isinstance(x,dict):
  for k,v in x.items():
   if str(k).lower() in DENIED_KEYS:out.append(dict(location=where+'.'+k,category='sensitive_JSON_key'))
   out+=scan_text(str(k),where+'.key',private_terms);out+=scan_json(v,where+'.'+str(k),private_terms)
 elif isinstance(x,list):
  for i,v in enumerate(x):out+=scan_json(v,where+f'[{i}]',private_terms)
 elif isinstance(x,str):out+=scan_text(x,where,private_terms)
 return out

def validate_names(names):return set(names)==ALLOWED

def main():
 start=time.perf_counter();cpu=time.process_time();E=F/'external_share';names=[p.name for p in E.iterdir()];assert validate_names(names),'Unexpected/missing external file';private=(socket.gethostname(),getpass.getuser());findings=[];checks=[]
 for p in E.iterdir():
  assert p.is_file() and not p.is_symlink() and p.stat().st_size<65536;p.resolve().relative_to(E.resolve());text=p.read_text();problems=scan_text(text,p.name,private)
  if p.suffix=='.json':problems+=scan_json(json.loads(text),p.name,private)
  if p.suffix=='.csv':
   rs=list(csv.DictReader(p.open()));assert len(rs)==7
   for i,row in enumerate(rs):
    for key,val in row.items():problems+=scan_text(key,p.name+'.header',private)+scan_text(val,p.name+f'.row{i}.{key}',private)
  findings+=problems;checks.append(dict(file=p.name,SHA256=sha(p),bytes=p.stat().st_size,findings=len(problems)))
 # Draft is independently checked too, in addition to all four attachments.
 draft=R/'docs/TIEGCM_ZG_EXTERNAL_REGISTRATION_REQUEST_V2_1.md';findings+=scan_text(draft.read_text(),'V2.1 email draft',private)
 protocol=json.loads((F/'protocol.json').read_text())
 for n,h in protocol['preserved_history_SHA256'].items():assert sha(R/n)==h,n
 old=(R/'docs/TIEGCM_ZG_EXTERNAL_REGISTRATION_REQUEST_V2.md').read_text();body=old.split('## Formal English email\n\n')[1].split('## Suggested lightweight attachments')[0];new=draft.read_text().split('## Formal English email\n\n')[1].split('## Sanitized attachments only')[0];assert body==new
 assert all('**'+q+'.' in new for q in ['A','B','C','D']);assert all(x in draft.read_text() for x in ['[Name]','[Email]','[Affiliation]','To: tgcmgroup@mailman.ucar.edu','administrator approval','not independently verified'])
 orig=json.loads((R/'experiments/tiegcm_zg_external_registration_v2/model_configuration_manifest.json').read_text());out=json.loads((E/'configuration_summary_external.json').read_text());assert out['official_source']['commit']==orig['base_release']['commit'] and out['apex_update']['commit']==orig['apex_update']['commit']
 for y in ['2021','2022']:
  for k in ['ibgrddata','STEP_s','MPI','OMP','zbound_formula','zbound_approx_km','GSWM_migrating_diurnal','GSWM_migrating_semidiurnal','GSWM_nonmigrating_diurnal','GSWM_nonmigrating_semidiurnal']:assert out['runs'][y][k]==orig['B14_cases'][y][k]
  for k in ['DEN','ZG']:assert out['variables'][y][k]['dimensions']==orig['NetCDF_metadata'][y]['variables'][k]['dimensions'] and out['variables'][y][k]['units']==orig['NetCDF_metadata'][y]['variables'][k]['attributes']['units']
 evidence=json.loads((F/'contact_route_evidence.json').read_text());assert evidence['official_pages'][1]['status']=='CURRENT_MAILMAN_POLICY_NOT_VERIFIED';assert evidence['official_pages'][1]['original_excerpts']==[];assert evidence['user_supplied_claims']['status']=='USER_SUPPLIED_PENDING_OFFICIAL_REVALIDATION';assert evidence['prepared_sending_workflow']['To']=='tgcmgroup@mailman.ucar.edu';assert all(evidence[k]==0 for k in ['emails_sent','subscriptions','forms_submitted'])
 manifest=json.loads((F/'external_share_manifest.json').read_text())
 for c in checks:assert manifest['files'][c['file']]['SHA256']==c['SHA256']
 result=dict(redaction_PASS=not findings,file_checks=checks,findings=findings,JSON_recursive_scanned=True,CSV_every_field_scanned=True,Markdown_full_text_scanned=True,email_draft_scanned=True,original_history_SHA_unchanged=True,technical_email_body_exactly_unchanged=True,model_configuration_whitelist_values_match=True,source_hashes_preserved=True,raw_data_or_full_logs_present=False,sent=False,subscribed=False,form_submitted=False,contact_route_fully_verified=False,independent_posting_and_subscription_policy_verification='BLOCKED_HTTP404',manual_sending_ready=False,readiness='ATTACHMENTS_SANITIZED_CONTACT_ROUTE_UNVERIFIED' if not findings else 'REDACTION_FAILED',wall_s=time.perf_counter()-start,CPU_s=time.process_time()-cpu,peak_process_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
 with (F/'external_share_validation.json').open('x') as f:json.dump(result,f,indent=2)
 assert not findings,findings;print(json.dumps(result))
if __name__=='__main__':main()
