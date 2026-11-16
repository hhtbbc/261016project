"""Exactly two authorized A ZIPs plus CDF and target-day coverage only. No fitting."""
from pathlib import Path
import sys,json,csv,time,resource,datetime,subprocess,urllib.parse,xml.etree.ElementTree as ET,zlib,warnings,shutil,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np,cdflib
from observations.bounded_swarm_acquisition import Budget,download_zip,extract_members,sha,inside,posix_cksum
from observations.density_catalog import read_swarm_pod
from evaluation.swarm_density_comparison import quality_mask
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from atmosphere.causal_observation_operator import map_a_queries,observe_map_a
from run_swarm_tiegcm_2022_observation import read_observation
F=ROOT/'experiments/causal_density_latitude_acquisition_v1';D=ROOT/'data/raw/causal_density_latitude_v1'
def dump(n,x):
 with inside(F/n).open('x') as out:json.dump(x,out,indent=2,allow_nan=False)
def table(n,rows):
 with inside(F/n).open('x',newline='') as out:w=csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def prepare():
 assert not F.exists();F.mkdir();(F/'logs').mkdir();inside(D);D.mkdir(exist_ok=True)
 assert subprocess.run(['git','check-ignore',str(D/'sentinel.ZIP')],cwd=ROOT,capture_output=True).returncode==0
 context={};protected={}
 for n in ['AGENTS.md','STATUS.md','WORKLOG.md','reports/CAUSAL_DENSITY_LATITUDE_VALIDATION_V1.md','docs/CAUSAL_DENSITY_LATITUDE_NEXT_DECISION_V1.md','experiments/causal_density_latitude_v1/data_acquisition_request.md','experiments/causal_density_latitude_v1/source_manifest.json','experiments/causal_density_late_day_v1/source_manifest.json']:
  t=(ROOT/n).read_text();context[n]=dict(SHA256=sha(ROOT/n),bytes=len(t.encode()))
 # Preserve the entire old blocked audit directory byte-for-byte, including local logs.
 for p in (ROOT/'experiments/causal_density_latitude_v1').rglob('*'):
  if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 official=ROOT/'experiments/fourcastden_swarm_observation_v1/official_service_contract.json';committed=subprocess.check_output(['git','show','HEAD:'+str(official.relative_to(ROOT))],cwd=ROOT);assert __import__('hashlib').sha256(committed).hexdigest()==sha(official);j=json.loads(official.read_text());raw=ROOT/j['request']['path']
 if raw.exists():assert sha(raw)==j['request']['SHA256'];assert json.loads(raw.read_text())==j['contract'];hapi=raw;protected[str(raw.relative_to(ROOT))]=sha(raw)
 else:hapi=F/'HAPI_contract.json';hapi.write_text(json.dumps(j['contract'],indent=2)+'\n')
 protected[str(official.relative_to(ROOT))]=sha(official)
 cached=json.loads((ROOT/'experiments/causal_density_latitude_v1/source_manifest.json').read_text())['cached_official_receipts'];targets=[]
 for y,size in [(2021,140271),(2022,139397)]:
  rec=next(e for e in cached if e['year']==y);listing=ROOT/rec['cached_listing_source']['path'];assert sha(listing)==rec['cached_listing_source']['SHA256'];protected[str(listing.relative_to(ROOT))]=sha(listing);item=rec['item'];stem=f'SW_OPER_DNSAPOD_2__{y}0323T000000_{y}0323T235930_0301';assert item['name']==stem+'.ZIP' and item['size']==size
  targets.append(dict(year=y,stem=stem,name=item['name'],official_path=item['path'],URL='https://swarm-diss.eo.esa.int/?'+urllib.parse.urlencode(dict(do='download',file=item['path'])),expected_bytes=size))
 protocol=dict(task='ACQUISITION_AND_COVERAGE_ONLY',identity='PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED',targets=targets,network_limit_bytes=2**20,extracted_limit_bytes=2*2**20,request_timeout_s=25,automatic_retries=0,expected_network_bytes=279668,CPU_wall_s=600,RSS_GiB=4,public_output_limit_MiB=150,extra_metadata_download_bytes=0,hapi=dict(path=str(hapi.relative_to(ROOT)),SHA256=sha(hapi),source=str(official.relative_to(ROOT)),source_SHA256=sha(official)),allowed_model_cases=['B14','A7','B7'],A14='EXCLUDED',target_model_time='15:00 to next-day00:00, ten actual hourly frames',observe_window='[15:00,24:00) quality-valid A only',strict_stop='any download/archive/CDF or B14 coverage gate failure stops; controls may be unavailable, never substituteA14',no_correction_fit=True,no_future_error_metrics=True,no_joint_assessment=True,no_v13_algorithm_freeze=True,no_GPU_TIE_DART_orbit_training=True,created_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
 assert shutil.disk_usage(ROOT).free>20*2**30
 dump('protocol.json',protocol);dump('input_protection.json',dict(protected=protected,context=context));print('ACQUISITION ONLY PROTOCOL FROZEN; 2 official requests max',flush=True)
def main(offline=False):
 start=time.perf_counter();pr=json.loads((F/'protocol.json').read_text());budget=Budget();downloads=[];phase='download';data={}
 if offline:
  original=json.loads((F/'download_manifest.json').read_text());downloads=original['products'];budget.network_bytes=original['actual_network_body_bytes'];budget.extracted_bytes=original['verified_extracted_bytes']
  assert len(downloads)==2
  for prod in downloads:
   assert sha(ROOT/prod['path'])==prod['SHA256']
   for member in prod['extracted_members']:assert sha(ROOT/member['path'])==member['SHA256']
 def warning(message,category,filename,lineno,file=None,line=None):
  with (F/'logs/python_warnings_local.jsonl').open('a') as out:out.write(json.dumps(dict(message=str(message),category=category.__name__,filename=filename,line=lineno))+'\n')
 warnings.showwarning=warning
 def ledger(final=False):
  payload=dict(products=downloads,actual_network_body_bytes=budget.network_bytes,verified_extracted_bytes=budget.extracted_bytes,network_limit=budget.network_limit,extraction_limit=budget.extract_limit,final=final,phase=phase)
  dest=F/('local_verification_manifest.json' if offline else 'download_manifest.json');tmp=dest.with_name(dest.name+'.new');tmp.write_text(json.dumps(payload,indent=2)+'\n');tmp.replace(dest)
 try:
  ledger()
  for target in ([] if offline else pr['targets']):
   receipt=download_zip(target['URL'],D/target['name'],target['expected_bytes'],target['stem'],budget);receipt['year']=target['year'];downloads.append(receipt);ledger();receipt['extracted_members']=extract_members(D/target['name'],target['stem'],budget,D);ledger();print('DOWNLOADED AND CRC VERIFIED',target['year'],receipt['bytes'],flush=True)
  phase='CDF';ledger();contracts={};quality=[];counts=[];candidate=[]
  assert sha(ROOT/pr['hapi']['path'])==pr['hapi']['SHA256']
  for target in pr['targets']:
   y=str(target['year']);stem=target['stem'];prod=next(p for p in downloads if p['year']==target['year']);cdf=D/(stem+'.cdf');hdr=D/(stem+'.HDR');cdfsha=next(x['SHA256'] for x in prod['extracted_members'] if x['path'].lower().endswith('.cdf'));rows,a,contract=read_swarm_pod(cdf,ROOT/pr['hapi']['path'],cdfsha,satellite='A');b,_=read_observation(cdf)
   for key in ['utc','density','validity_flag','latitude','longitude','altitude']:np.testing.assert_array_equal(a[key],b[key])
   tree=ET.parse(hdr);root=tree.getroot();fixed=root.find('Fixed_Header');assert fixed.findtext('File_Name')==stem and fixed.findtext('Mission')=='Swarm' and fixed.findtext('File_Type')=='DNSAPOD_2_' and fixed.findtext('File_Version')=='0301';assert fixed.findtext('Validity_Period/Validity_Start')=='UTC='+y+'-03-23T00:00:00' and fixed.findtext('Validity_Period/Validity_Stop')=='UTC='+y+'-03-23T23:59:30'
   rawcrc=0
   with cdf.open('rb') as inp:
    for block in iter(lambda:inp.read(65536),b''):rawcrc=zlib.crc32(block,rawcrc)
   hdrcrc=int(root.findtext('Variable_Header/MPH/CRC'));posixcrc,length=posix_cksum(cdf);independent=subprocess.check_output(['cksum',str(cdf)],text=True).split();assert posixcrc==hdrcrc==int(independent[0]) and length==int(independent[1]);zipcrc=int(next(x['CRC32'] for x in prod['extracted_members'] if x['path'].lower().endswith('.cdf')),16);assert rawcrc==zipcrc;assert int(root.findtext('Variable_Header/MPH/Tot_Size'))==cdf.stat().st_size
   with cdflib.CDF(cdf) as c:
    ti=c.varinq('time');assert ti.Data_Type==31 and ti.Data_Type_Description=='CDF_EPOCH';direct_time=cdflib.cdfepoch.to_datetime(c.varget('time'));np.testing.assert_array_equal(direct_time,a['utc'])
   assert len(a['utc'])==2880 and not np.isnat(a['utc']).any() and np.all(np.diff(a['utc'])==np.timedelta64(30,'s'));assert a['utc'][0]==np.datetime64(y+'-03-23T00:00:00') and a['utc'][-1]==np.datetime64(y+'-03-23T23:59:30')
   for k,u in [('density','kg/m3'),('latitude','deg'),('longitude','deg'),('altitude','m')]:assert contract['variables'][k]['UNITS']==u
   density_valid,flags=quality_mask(a['density'],a['validity_flag']);coord=np.isfinite(a['latitude'])&np.isfinite(a['longitude'])&np.isfinite(a['altitude'])&(abs(a['latitude'])<=90)&(abs(a['longitude'])<=180)&(a['altitude']>0)&(a['altitude']<2e6);a['quality']=density_valid&coord
   flagdist={str(k):int(n) for k,n in zip(*np.unique(a['validity_flag'],return_counts=True))};quality.append(dict(year=y,date=y+'-03-23',product='SW_OPER_DNSAPOD_2_',version='0301',records=len(a['utc']),cadence_s=30,first_UTC=str(a['utc'][0])+'Z',last_UTC=str(a['utc'][-1])+'Z',flag0=int((a['validity_flag']==0).sum()),flag1=int((a['validity_flag']==1).sum()),unknown_flags=int(flags['unknown'].sum()),invalid_density=int(flags['invalid_density'].sum()),invalid_coordinates=int((~coord).sum()),valid_samples=int(a['quality'].sum()),valid_fraction=float(a['quality'].mean()),height_min_m=float(a['altitude'][a['quality']].min()),height_max_m=float(a['altitude'][a['quality']].max()),CDF_SHA256=cdfsha))
   hour=(a['utc']-np.datetime64(y+'-03-23'))/np.timedelta64(1,'h');regions={'low':abs(a['latitude'])<30,'mid':(abs(a['latitude'])>=30)&(abs(a['latitude'])<60),'high':abs(a['latitude'])>=60};windows={'history15_18':(hour>=15)&(hour<18),'future18_19':(hour>=18)&(hour<19),'future18_21':(hour>=18)&(hour<21),'future18_24':(hour>=18)&(hour<24)}
   for wn,wm in windows.items():
    for rn,rm in {'all':np.ones(len(hour),bool),**regions}.items():
     n=int((wm&rm&a['quality']).sum());counts.append(dict(year=y,window=wn,region=rn,raw_N=int((wm&rm).sum()),valid_N=n,status='UNSUPPORTED_INSUFFICIENT_HISTORY' if wn=='history15_18' and rn!='all' and n<30 else 'COUNT_ONLY_NO_COEFFICIENT'))
   contracts[y]=dict(file=str(cdf.relative_to(ROOT)),SHA256=cdfsha,global_attributes={k:contract['global_attributes'][k] for k in ['TITLE','TIME SYSTEM']},required_variable_units={k:contract['variables'][k].get('UNITS') for k in ['time','density','latitude','longitude','altitude','validity_flag']},time_data_type=ti.Data_Type_Description,density_field='density, never density_orbitmean',coordinate_reference='GRS80 geodetic per SHA-verified prior HAPI contract; formal model datum still unverified',HDR=dict(file=str(hdr.relative_to(ROOT)),SHA256=sha(hdr),File_Name=stem,File_Type='DNSAPOD_2_',File_Version='0301',Mission='Swarm',CDF_CRC32=f'{rawcrc:08x}',ZIP_CDF_CRC32=f'{zipcrc:08x}',ZIP_zlib_equal=True,HDR_reported_CDF_cksum=hdrcrc,POSIX_cksum=posixcrc,independent_GNU_cksum=int(independent[0]),HDR_POSIX_equal=True))
   candidate.append(dict(year=y,date=y+'-03-23',ZIP=str((D/target['name']).relative_to(ROOT)),CDF=str(cdf.relative_to(ROOT)),HDR=str(hdr.relative_to(ROOT)),ZIP_SHA256=prod['SHA256'],CDF_SHA256=cdfsha,HDR_SHA256=sha(hdr),CDF_identity_PASS=True,UTC2880_30s_PASS=True,valid_samples=int(a['quality'].sum()),quality_flag_distribution=json.dumps(flagdist),height_reference='GRS80 product contract; PROVISIONAL Map-A only',status='ACQUIRED_AND_CDF_VERIFIED'))
   data[y]=a;print('CDF VERIFIED',y,len(a['utc']),'valid',int(a['quality'].sum()),flush=True)
  dump('CDF_contracts.json',contracts);table('quality_audit.csv',quality);table('latitude_window_counts.csv',counts);table('candidate_holdout_audit.csv',candidate)
  phase='model_coverage';ledger();source=json.loads((ROOT/'experiments/causal_density_late_day_v1/source_manifest.json').read_text());model=[];queryaudit=[];inputhash={};native_scan=[]
  with (F/'model_queries_local.jsonl').open('x') as cache:
   for y,a in data.items():
    hour=(a['utc']-np.datetime64(y+'-03-23'))/np.timedelta64(1,'h');selection=(hour>=15)&(hour<24)&a['quality'];indices=np.flatnonzero(selection);queries=map_a_queries(a['utc'][indices],a['latitude'][indices],a['longitude'][indices],a['altitude'][indices])
    if not len(queries):raise ValueError('No quality-valid target-window observations')
    for case in ['B14','A7','B7']:
     state='PASS';reason='';start_case=time.perf_counter();success=0;failed={};first=None;last=None;minmargin=None;frames=0;files=[]
     try:
      s=source['cases'][y][case];folder=ROOT/s['folder'];auditpath=folder/'data_audit.json';runpath=folder/'run_status.json';audit=json.loads(auditpath.read_text());run=json.loads(runpath.read_text());assert audit['engineering_PASS'] and run['returncode']==0 and run['normal_exit_count']==4
      config=s['source_config']
      for n,h in [(config['input'],config['input_SHA256']),(config['source'],config['source_SHA256']),(config['GPI'],config['GPI_SHA256'])]:assert sha(ROOT/n)==h,n;inputhash[n]=h
      for path in [auditpath,runpath]:inputhash[str(path.relative_to(ROOT))]=sha(path)
      legacy_input=ROOT/('experiments/swarm_tiegcm_2021_spinup_observation_v1/inputs.json' if y=='2021' else 'experiments/swarm_tiegcm_2022_observation_v1/inputs.json');legacy=json.loads(legacy_input.read_text());inputhash[str(legacy_input.relative_to(ROOT))]=sha(legacy_input)
      files=[e for e in s['files'] if any(t.startswith(y+'-03-23') or t.startswith(y+'-03-24T00:00') for t in e['UTC'])];assert files
      for e in files:
       p=folder/e['file'];assert sha(p)==e['SHA256'];assert next(x for x in audit['files'] if x['file']==e['file'])['SHA256']==e['SHA256'];inputhash[str(p.relative_to(ROOT))]=e['SHA256']
       if case=='A7':assert next(x for x in (legacy['A7']['files'] if y=='2021' else legacy['files']) if x['file']==e['file'])['SHA256']==e['SHA256']
      provider=HourlyTiegcmObservation([folder/e['file'] for e in files],{e['file']:e['SHA256'] for e in files},y+'-03-23T15:00:00',y+'-03-24T00:00:00',y+'_'+case);frames=len(provider.records);assert frames==10 and provider.records[-1][0].utc.isot==y+'-03-24T00:00:00.000'
      from netCDF4 import Dataset
      for e in files:
       with Dataset(folder/e['file']) as n:
        n.set_auto_mask(False);mt=np.asarray(n['mtime'][:]);used=np.where(((mt[:,0]==82)&(mt[:,1]>=15))|((mt[:,0]==83)&(mt[:,1]==0)))[0]
        for variable in ['DEN','ZG']:
         var=n[variable];assert var.dimensions==('time','ilev','lat','lon') and var.units==('g/cm3' if variable=='DEN' else 'cm');badcount=0;nonmono=0;total=0
         for k in used:
          raw=np.asarray(var[int(k)]);bad=~np.isfinite(raw)|(abs(raw)>1e30)
          for attr in ['_FillValue','missing_value']:
           if hasattr(var,attr):bad|=raw==np.asarray(getattr(var,attr),dtype=raw.dtype)
          if variable=='DEN':bad|=raw<=0
          else:nonmono+=int((np.diff(raw,axis=0)<=0).sum())
          badcount+=int(bad.sum());total+=raw.size
         native_scan.append(dict(year=y,case=case,file=e['file'],variable=variable,units=var.units,dimensions=list(var.dimensions),used_records=len(used),values_scanned=total,invalid=badcount,nonmonotonic_ZG_pairs=nonmono));assert badcount==0 and nonmono==0
      complete8=0
      for index,q in zip(indices,queries):
       result,coord=observe_map_a(provider,q)
       if result.valid:
        assert len(result.metadata['columns'])==8;complete8+=1;success+=1;utc=str(a['utc'][index])+'Z';first=first or utc;last=utc;margin=result.metadata['top_margin_m'];minmargin=margin if minmargin is None else min(minmargin,margin)
       else:failed[result.reason]=failed.get(result.reason,0)+1
       cache.write(json.dumps(dict(year=y,case=case,index=int(index),UTC=str(a['utc'][index])+'Z',valid=result.valid,reason=result.reason,model_density_kg_m3=result.rho_kg_m3,coordinate=coord,metadata=result.metadata))+'\n')
      provider.close();assert success==len(queries) and not failed
     except Exception as e:
      state='NOT_EVALUABLE';reason=type(e).__name__+': '+str(e)
      if case=='B14':
       dump('model_coverage_failure.json',dict(year=y,case=case,reason=reason,new_fit_count=0));raise
     model.append(dict(year=y,case=case,role='PRIMARY' if case=='B14' else 'CONTROL',static_target_frames=frames,target_start_UTC=y+'-03-23T15:00:00Z',boundary_frame_UTC=y+'-03-24T00:00:00Z',total_queries=len(queries),successful=success,failed=len(queries)-success,coverage=success/len(queries) if len(queries) else None,eight_column_complete=success,first_valid_UTC=first,last_valid_UTC=last,min_top_margin_m=minmargin,status=state,reason=reason,failed_reasons=json.dumps(failed)))
     queryaudit.append(dict(year=y,case=case,state=state,folder=str(folder.relative_to(ROOT)),files=files,grid=[29,36,72] if frames else None,engineering_returncode=run['returncode'] if frames else None,wall_s=time.perf_counter()-start_case));print('MODEL COVERAGE',y,case,state,success,'/',len(queries),flush=True)
  table('model_coverage.csv',model);dump('model_query_audit.json',dict(identity=pr['identity'],cases=queryaudit,NetCDF_input_SHA256=inputhash,explicit_native_scan=native_scan,query_scope='quality-valid A[15,24); no prediction-error computation',density_unit='g/cm3 *1000 to kg/m3',height_unit='cm *.01 to m',no_extrapolation=True,eight_columns_including_zero_weights_required=True))
  for n,h in json.loads((F/'input_protection.json').read_text())['protected'].items():assert sha(ROOT/n)==h,n
  for n,h in inputhash.items():assert sha(ROOT/n)==h,n
  phase='COMPLETE';ledger(True);dump('result.json',dict(state='COMPLETE',latitude_state='READY_FOR_V13_PROTOCOL_FREEZE',two_CDFs_verified=True,two_B14_coverage_PASS=True,model_queries=sum(x['total_queries'] for x in model),successful_queries=sum(x['successful'] for x in model),calibration_coefficients=0,future_errors=0,joint_assessments=0,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,network_bytes=budget.network_bytes,extracted_bytes=budget.extracted_bytes));print('ACQUISITION AND COVERAGE COMPLETE; SCIENCE SCORES NOT COMPUTED',flush=True)
 except Exception as e:
  ledger(True);dump('failure_verify_local.json' if offline else 'failure.json',dict(phase=phase,error=type(e).__name__,message=str(e),traceback=traceback.format_exc(),network_bytes=budget.network_bytes,extracted_bytes=budget.extracted_bytes,latitude_state='BLOCKED_TIE_TARGET_DAY_COVERAGE' if phase=='model_coverage' else 'BLOCKED_MISSING_HOLDOUT_OBSERVATION',no_retries=True,no_fits=True,no_future_metrics=True));print('ACQUISITION_STOP',type(e).__name__,str(e),flush=True);raise SystemExit(1)
if __name__=='__main__':
 if sys.argv[1:] == ['prepare']:prepare()
 elif sys.argv[1:] == ['execute']:main()
 elif sys.argv[1:] == ['verify-local']:main(offline=True)
 else:raise SystemExit('Explicit prepare or execute required')
