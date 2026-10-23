"""Read-only bounded range search of the linked Canadian measurement archive."""
import hashlib,json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/f107_2021_recovery_v1';RAW=ROOT/'data/raw/f107_2021_recovery_v1'
URL='https://spaceweather.gc.ca/solar_flux_data/daily_flux_values/fluxtable.txt'
def get(lo,hi):
 req=urllib.request.Request(URL,headers={'Range':f'bytes={lo}-{hi}'})
 with urllib.request.urlopen(req,timeout=20) as r:
  assert r.status==206;content=r.headers['Content-Range'];assert content.startswith(f'bytes {lo}-{hi}/');b=r.read(hi-lo+2);assert len(b)==hi-lo+1
 p=RAW/f'canada_bytes_{lo}_{hi}.txt'
 with p.open('xb') as f:f.write(b)
 return b,dict(URL=URL,HTTP=206,Content_Range=content,SHA256=hashlib.sha256(b).hexdigest(),bytes=len(b),path=str(p.relative_to(ROOT)))
def rows(b):
 result=[]
 for line in b.decode().splitlines():
  x=line.split()
  if len(x)==7 and re.fullmatch(r'20\d{6}',x[0]):result.append(x)
 return result
def fetch_canada():
 audit=[];low=4096;high=2189096-4096
 try:
  for i in range(12):
   mid=(low+high)//2;b,a=get(mid,mid+4095);audit.append(a);r=rows(b);assert r
   print(mid,r[0][0],r[-1][0],flush=True)
   if int(r[0][0])<=20210509<=int(r[-1][0]):
    # Nearby months in the same source, for all available overlap comparisons.
    b,a=get(max(0,mid-40000),min(2189095,mid+16000));audit.append(a);r=rows(b)
    (F/'canada_measurement_rows.json').write_text(json.dumps(r,indent=2));break
   if int(r[-1][0])<20210509:low=mid+4096
   else:high=mid-1
  else:raise ValueError('Date not bracketed')
 finally:(F/'canada_range_requests.json').write_text(json.dumps(audit,indent=2))


def candidate_gate(value,kind,overlap_ok,observed_definition_verified):
 """No estimated/adjusted values and no unexplained source mismatch."""
 import math
 return (math.isfinite(value) and value>0 and kind=='OBS'
         and overlap_ok and observed_definition_verified)

def sensitivity(delta):
 """Conditional contribution to the arithmetic mean, never model response."""
 return delta/81.0

def audit():
 from datetime import date,datetime,timedelta
 import math,collections
 original=ROOT/'data/raw/tiegcm_training_years_v1/2021_Fobs.json'
 payload=json.loads(original.read_text());times=payload['datetime'];flux=payload['Fobs']
 assert len(times)==len(set(times))==95 and len(flux)==95
 gfz={t[:10]:float(v) for t,v in zip(times,flux)}
 missing=[t for t,v in gfz.items() if v<=0];assert missing==['2021-05-09']
 assert all(datetime.fromisoformat(t.replace('Z','+00:00')).utcoffset()==timedelta(0) for t in times)
 yearly={}
 for line in (RAW/'gfz_year.txt').read_text().splitlines():
  a=line.split()
  if a and a[0]=='2021':
   assert len(a)==28;day='-'.join(a[:3]);assert day not in yearly;yearly[day]=a
 assert float(yearly['2021-05-09'][25])==float(yearly['2021-05-09'][26])==-1
 assert all(float(yearly[t][25])==v for t,v in gfz.items())
 kp={}
 for i in range(15):
  d=(date(2021,3,27)+timedelta(days=i)).isoformat();a=yearly[d]
  assert a[27] in ['1','2'];values=[float(x) for x in a[7:15]]
  assert len(values)==8 and all(0<=x<=9 for x in values);kp[d]=values
 (F/'kp_window_audit.json').write_text(json.dumps({'status':'PASS','source':'GFZ official 2021 yearly ASCII','Kp_is_definitive':True,'day_count':15,'bucket_count':120,'dates':list(kp),'kp':kp,'source_sha256':hashlib.sha256((RAW/'gfz_year.txt').read_bytes()).hexdigest(),'GPI_generated':False},indent=2))
 canadian=json.loads((F/'canada_measurement_rows.json').read_text());assert not any(x[0]=='20210509' for x in canadian)
 # All overlapping 20 UTC rows retained; no selection among duplicate records.
 comparisons=[];counts=collections.Counter((x[0],x[1]) for x in canadian)
 for x in canadian:
  day=f'{x[0][:4]}-{x[0][4:6]}-{x[0][6:]}'
  if day in gfz and gfz[day]>0 and x[1]=='200000':comparisons.append({'date':day,'GFZ':gfz[day],'Canadian_obs':float(x[4]),'Canadian_adj':float(x[5]),'difference':float(x[4])-gfz[day]})
 noaa=json.loads((F/'noaa_overlap.json').read_text());cel=json.loads((F/'celestrak_request.json').read_text())
 target=next(x for x in cel['may_dates'] if x['DATE']=='2021-05-09');assert target['F10.7_DATA_TYPE']=='INT'
 scenarios=[];base=None
 for v in [75.9,76.,76.2,76.5]:
  center=date(2021,4,5);vals=[]
  for i in range(-40,41):
   day=(center+timedelta(days=i)).isoformat();vals.append(v if day in missing else gfz[day])
  mean=math.fsum(vals)/81
  if v==76.:base=mean
  scenarios.append({'hypothetical_missing_Fobs':v,'conditional_F107A_Apr5':mean,'status':'SCENARIO_ONLY_NOT_DRIVERS'})
 for row in scenarios:row['difference_from_76_scenario']=row['conditional_F107A_Apr5']-base
 result={'status':'DATA_GAP_UNRESOLVED','original_SHA256':hashlib.sha256(original.read_bytes()).hexdigest(),'missing':missing,'neighbor_values':{k:gfz[k] for k in ['2021-05-08','2021-05-10']},'required_source_dates':['2021-02-15','2021-05-20'],'GPI_raw_dates':['2021-03-27','2021-04-10'],'valid_dates':['2021-03-29','2021-04-08'],'target_Apr5_center81_dates':['2021-02-24','2021-05-15'],'GFZ_API_ASCII_all_original_values_identical':True,'canada_missing_day_row_count':0,'canada_20UTC_comparisons':comparisons,'canada_duplicate_timekeys':[{"date":key[0],"time":key[1],"count":n} for key,n in counts.items() if n>1],'NOAA_candidate':76.,'NOAA_overlap_count':noaa['count'],'NOAA_failed_days':sum(r['absolute_difference']>.550000001 for r in noaa['rows']),'NOAA_max_difference':noaa['max_difference'],'NOAA_gate':candidate_gate(76.,'OBS',noaa['all_pass'],True),'CelesTrak_candidate':target,'CelesTrak_gate':candidate_gate(float(target['F10.7_OBS']),target['F10.7_DATA_TYPE'],True,True),'scenarios':scenarios,'delta_F107A_per_1sfu':sensitivity(1),'GPI_generated':False,'model_launches':0,'reason':'No Canadian original record; NOAA overlap definition/version mismatch unexplained; CelesTrak explicitly interpolated'}
 assert not result['NOAA_gate'] and not result['CelesTrak_gate']
 (F/'recovery_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['canada_20UTC_comparisons','CelesTrak_candidate']},indent=2))

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--fetch-canada',action='store_true');args=parser.parse_args()
 if args.fetch_canada:fetch_canada()
 else:audit()
