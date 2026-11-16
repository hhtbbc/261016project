"""Bounded official metadata/source audit; at most one new Swarm-C day, no B values."""
from pathlib import Path
import sys,json,urllib.parse,zipfile,time,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from prepare_fourcastden_swarm_observation_v1 import bounded_get,sha,dump
TAG='thermosphere_observation_assimilation_feasibility_v1';F=ROOT/'experiments'/TAG;D=ROOT/'data/raw'/TAG;O=ROOT/'results'/TAG
LIMIT=10*2**20
class Fetcher:
 def __init__(self):self.receipts=[];self.failures=[]
 @property
 def total(self):return sum(x['bytes'] for x in self.receipts)
 def get(self,url,path,cap=2**20,expected=None):
  remaining=LIMIT-self.total
  if remaining<=0:raise RuntimeError('New raw/reference bytes exhausted')
  try:
   r=bounded_get(url,path,min(cap,remaining),expected);self.receipts.append(r);return r
  except Exception as e:
   self.failures.append(dict(URL=url,path=str(path.relative_to(ROOT)),error=type(e).__name__+': '+str(e)));return None
 def save(self):dump(F/'download_receipts.json',dict(receipts=self.receipts,failures=self.failures,total_saved_download_bytes=self.total,limit_bytes=LIMIT,Swarm_B_density_values_read=False))
def main():
 start=time.perf_counter();assert not (F/'download_started.json').exists();assert shutil.disk_usage(ROOT).free>20*2**30
 dump(F/'download_started.json',dict(raw_and_references_limit_bytes=LIMIT,one_new_observation='Swarm C DNSCPOD 2022-03-24 only',Swarm_B='metadata only; reserved untouched',no_GPU=True,no_models=True,no_fitting=True))
 protected=json.loads((ROOT/'experiments/fourcastden_den_multisample_continuation_v8/protected_inputs.json').read_text())
 for base in [ROOT/'experiments/fourcastden_den_multisample_continuation_v8',ROOT/'results/fourcastden_den_multisample_continuation_v8']:
  for p in base.rglob('*'):
   if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 for n,h in protected.items():assert sha(ROOT/n)==h,n
 dump(F/'protected_inputs.json',protected)
 fetch=Fetcher();official=D/'official'
 urls={
 'DART_tiegcm.html':'https://docs.dart.ucar.edu/en/latest/models/tiegcm/readme.html',
 'quickstart.html':'https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/quickstart.html',
 'output.html':'https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/output.html',
 'diags.html':'https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/diags.html',
 'DART_commit.json':'https://api.github.com/repos/NCAR/DART/commits/main',
 'DART_directory.json':'https://api.github.com/repos/NCAR/DART/contents/models/tiegcm',
 'zenodo_v1.json':'https://zenodo.org/api/records/10731921',
 'zenodo_latest.json':'https://zenodo.org/api/records/10732144',
 'TU_Delft.html':'https://thermosphere.tudelft.nl/',
 'HAPI_catalog.json':'https://vires.services/hapi/catalog',
 }
 for name,url in urls.items():fetch.get(url,official/name,400*1024)
 if (official/'DART_commit.json').exists():
  commit=json.loads((official/'DART_commit.json').read_text())['sha']
  for path,name in [('models/tiegcm/model_mod.f90','model_mod.f90'),('observations/forward_operators/obs_def_upper_atm_mod.f90','obs_def_upper_atm_mod.f90'),('models/tiegcm/work/input.nml','input.nml'),('models/tiegcm/work/quickbuild.sh','quickbuild.sh')]:fetch.get('https://raw.githubusercontent.com/NCAR/DART/'+commit+'/'+path,official/name,250*1024)
  dump(F/'DART_pinned_revision.json',dict(commit=commit,source='NCAR/DART official main; static source snapshot, not installed or compiled'))
 # Product metadata only; never query B /data endpoint.
 products=['SW_OPER_DNSAPOD_2_','SW_OPER_DNSBPOD_2_','SW_OPER_DNSCPOD_2_','SW_OPER_DNSAACC_2_','SW_OPER_DNSBACC_2_','SW_OPER_DNSCACC_2_','GF_OPER_DNS1ACC_2_','GR_OPER_DNS1ACC_2_','CH_OPER_DNS_ACC_2_']
 for product in products:fetch.get('https://vires.services/hapi/info?'+urllib.parse.urlencode(dict(id=product)),official/(product+'_info.json'),32*1024)
 # Verify exact target-day C and B filenames independently from HAPI year range.
 matches={}
 for sat in ['C','B']:
  folder=f'swarm/Level2daily/Latest_baselines/DNS/POD/Sat_{sat}';p=D/f'Sat_{sat}_listing.json'
  rec=fetch.get('https://swarm-diss.eo.esa.int/?'+urllib.parse.urlencode(dict(do='list',maxfiles=10000,pos=0,file=folder)),p,2*2**20)
  if rec:
   items=json.loads(p.read_text())['results'];matches[sat]={day:[x for x in items if day+'T000000' in x['name']] for day in ['20210324','20220324']}
 dump(F/'product_availability.json',matches)
 candidates=matches.get('C',{}).get('20220324',[])
 if len(candidates)==1:
  item=candidates[0];assert item['name'].endswith('_0301.ZIP') and item['size']<512*1024
  dump(F/'Swarm_C_download_plan.json',dict(product=item,remaining_bytes=LIMIT-fetch.total,budget_bytes=LIMIT,prior_saved_bytes=fetch.total))
  if item['size']<LIMIT-fetch.total:
   rec=fetch.get('https://swarm-diss.eo.esa.int/?'+urllib.parse.urlencode(dict(do='download',file=item['path'])),D/item['name'],item['size'],item['size'])
   if rec:
    members=[]
    with zipfile.ZipFile(D/item['name']) as z:
     assert z.testzip() is None and sum(x.file_size for x in z.infolist())<4*2**20
     for m in z.infolist():
      assert Path(m.filename).name==m.filename and not m.is_dir();out=D/m.filename;out.resolve().relative_to(ROOT)
      with out.open('xb') as f:f.write(z.read(m))
      members.append(dict(path=str(out.relative_to(ROOT)),SHA256=sha(out),bytes=m.file_size,CRC32=f'{m.CRC:08x}'))
    dump(F/'Swarm_C_download_complete.json',dict(product=rec,members=members,archive_CRC_PASS=True))
 # Author repository provides final published OA PDF. Never download2.6GB Zenodo result files.
 pdf='https://vbn.aau.dk/files/709792548/Space_Weather_-_2024_-_Kosary_-_Assimilating_Space_Based_Thermospheric_Neutral_Density_TND_Data_Into_the_TIE_GCM_Coupled.pdf'
 if LIMIT-fetch.total>4*2**20:fetch.get(pdf,official/'Kosary_2024_published.pdf',4*2**20)
 fetch.save();dump(F/'preparation_done.json',dict(PASS=True,wall_s=time.perf_counter()-start,total_saved_download_bytes=fetch.total,old_assets_verified=len(protected),new_C_downloaded=(F/'Swarm_C_download_complete.json').exists(),B_values_read=False,model_launches=0))
 print('OFFICIAL AUDIT COMPLETE',fetch.total,len(fetch.failures),(F/'Swarm_C_download_complete.json').exists(),time.perf_counter()-start)
if __name__=='__main__':main()
