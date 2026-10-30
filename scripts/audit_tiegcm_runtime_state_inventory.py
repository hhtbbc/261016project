"""Effective-source runtime inventory; distinguishes review from syntactic candidates."""
from pathlib import Path
import sys,json,re,csv
from netCDF4 import Dataset
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import run_tiegcm_runtime_restart_audit as m
OUT=m.OUT;SRC=R/'third_party/TIEGCM2.0/src';BUILD=m.EXE.parent

def csvout(name,rows):
 with (OUT/name).open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def main():
 effective={}
 for name in (BUILD/'Srcfiles').read_text().splitlines():
  p=BUILD/name if (BUILD/name).is_file() else SRC/name
  assert p.is_file(),p;effective[name]=p
 # Whole module declarations and explicit saved/data locals are a search index,
 # not a claim of complete static dependency or compiled-branch analysis.
 inventory=[]
 for name,p in effective.items():
  lines=p.read_text(errors='replace').splitlines();module=False;inhead=False;buf='';start=0
  for i,line in enumerate(lines,1):
   stripped=line.strip();code=line.split('!')[0].strip()
   if re.match(r'module\s+(?!procedure)',code,re.I):module=True;inhead=True
   if module and code.lower()=='contains':inhead=False
   if inhead and (re.match(r'(real|integer|logical|character|type\s*\()',code,re.I) or (buf and code.startswith('|'))):
    if not code.startswith('|'):
     if buf:inventory.append(dict(file=str(p.relative_to(R)),line=start,scope='module_declaration_candidate',statement=buf,review_status='syntactic_only_not_proof_of_cross_step_use'))
     buf=code;start=i
    else:buf+=' '+code.lstrip('|').strip()
   elif buf:
    inventory.append(dict(file=str(p.relative_to(R)),line=start,scope='module_declaration_candidate',statement=buf,review_status='syntactic_only_not_proof_of_cross_step_use'));buf=''
   if not inhead and (re.search(r'\bsave\b',code,re.I) or re.match(r'data\s+',code,re.I)):
    inventory.append(dict(file=str(p.relative_to(R)),line=i,scope='explicit_saved_or_data_local_candidate',statement=code,review_status='manual_lifecycle_review_needed'))
  if buf:inventory.append(dict(file=str(p.relative_to(R)),line=start,scope='module_declaration_candidate',statement=buf,review_status='syntactic_only_not_proof_of_cross_step_use'))
 csvout('runtime_declaration_search_index.csv',inventory)
 rows=[]
 def add(v,f,loc,meaning,grid,dim,unit,role,persist,rebuild,impact):
  p=effective[f];rows.append(dict(variable=v,source=str(p.relative_to(R)),routine_lines=loc,physical_meaning=meaning,grid=grid,dimensions=dim,unit=unit,state_type=role,persisted=persist,exact_reconstruction=rebuild,missing_impact=impact,source_SHA256=m.sha(p)))
 aliases={'OMEGA':'w','Z':'z','POTEN':'poten'}
 with Dataset(m.SEED) as n:
  text=effective['fields.F'].read_text().splitlines()
  for k in m.REQUIRED:
   name=aliases.get(k,k.lower());line=next((i for i,l in enumerate(text,1) if re.search(r'short_name\s*=\s*\(?["\']'+k+r'["\']',l,re.I)),None)
   line='170-175/962-975; nchist.F:752-763' if k in ['TLBC','ULBC','VLBC','TLBC_NM','ULBC_NM','VLBC_NM'] else line
   meaning=n[k].long_name;dims='file:'+','.join(n[k].dimensions)+'; runtime: (levd,lon halo,lat halo,2)' if k not in ['TLBC','ULBC','VLBC','TLBC_NM','ULBC_NM','VLBC_NM'] else 'file:'+','.join(n[k].dimensions)+'; runtime: horizontal boundary arrays'
   add(name,'fields.F',f'field allocation/descriptor around line {line}',meaning,n[k].dimensions[1] if len(n[k].dimensions)>3 else 'horizontal lower boundary',dims,n[k].units,'persisted current or filtered previous state (_NM); POTEN is output-mapped potential','primary:'+k,'value loaded; all runtime equivalents NOT guaranteed','missing destroys initial/current/previous state or boundary continuity')
 for v in ['phim3d','ephi3d','elam3d','emz3d']:
  meaning={'phim3d':'magnetic-grid 3-D electric potential','ephi3d':'coordinate-scaled eastward electric-field component','elam3d':'coordinate-scaled equatorward electric-field component','emz3d':'vertical magnetic-level potential difference (not physical V/m)'}[v]
  add(v,'pdynamo.F','module lines 48-55; alloc_pdyn 1180-1197; pthreed 2031-2520; pefield 2596-2707',meaning,'magnetic subdomain; mlev interfaces','(mlon0:mlon1,mlat0:mlat1,mlev0:mlev1)','V for potential or coordinate potential derivative; metric conversion in ionvel.F:72-95','cross-step electrodynamics auxiliary; SAVE allocatable','not in primary/secondary; initialized zero','phim reconstructed by geo2mag(POTEN), exact inverse not demonstrated; E rederived on first step','first restored step consumes different electrostatic state from uninterrupted step')
 for v in ['ed13d','ed23d','zpotm3d']:
  add(v,'pdynamo.F','module 48-55; pthreed/current callers','covariant current-field components or magnetic geopotential','magnetic','(mlon0:mlon1,mlat0:mlat1,mlev0:mlev1)','field-specific native metric scaling; needs separate component-unit qualification','auxiliary cache','not primary','computed in pthreed; exact lifecycle dependency not fully qualified','candidate hidden dependency; do not assume four arrays exhaust missing state')
 for v in ['ex','ey','ez']:
  add(v,'pdynamo.F','module 57-60; pefield 2722-2740','regridded coordinate electric-field component, consumed by ionvel','geographic interfaces with longitude halo','(nlevp1,lon0-2:lon1+2,lat0:lat1)','native potential-coordinate derivative; physical V/cm only after ionvel metric division','diagnostic input to dynamics','not primary','regrid preceding magnetic components each step','error in missing magnetic fields propagates to ion drifts/ion drag/heating')
 for v,meaning,unit in [('n2','1-o2-o1-he','mmr'),('zg','geometric height','cm')]:
  add(v,'addiag.F','78; calczg 221-279','diagnostic '+meaning,'n2 midpoint; den/zg interfaces','(lev,lon,lat) local blocks',unit,'diagnostic','secondary; N2/zg/den not required primary state','recomputed from saved prognostics and geometry; masks and order required','must not restore diagnostic outputs as if full model state')
 add('rho (history DEN)','dt.F','244-266; diags.F:mkdiag_DEN','total neutral mass density diagnostic','geographic interfaces','rho(lev0:lev1,lon0:lon1), per latitude','g/cm3','step diagnostic','secondary DEN; not primary','recomputed during dt from native pressure/TN/mean mass','must not treat diagnostic density as full restart state')
 for v in ['barm','vc']:
  add(v,'fields.F','indices/declarations 59-75; advance.F:362-383','mean molecular mass / dynamics auxiliary','geographic mixed grid','(levd,lon halo,lat halo,2)','native physical definition per descriptor; not assumed SI','diagnostic auxiliary','excluded from first28 f4d primary histories','addiag recomputes; precise ordering required','inconsistent derivation influences dynamics and diffusion')
 for v in ['itp','itc']:
  add(v,'fields.F','154-158;476-479; advance.F swaps','pointers selecting current and next storage slots','not spatial','scalar integer','index','time-buffer selector','not as buffer-slot indices in primary','reset 1/2; restored physical fields must occupy correct slots','wrong slots corrupt two-time-layer integration')
 for v in ['istep','iter','iyear','iday','uthr','secs','sin_sundec','cos_sundec']:
  add(v,'init.F','10-55; advance.F:125,198 and calendar updates','integration clock/counter or solar geometry','global','scalar','integer steps/year/day or seconds/hour; solar trig dimensionless','control/forcing state','iter/year/day/ut persisted; istep reset, solar geometry recomputed','calendar/iter reconstructable; istep first-step dispatch is not preserved','first-step-only branches differ despite matching absolute UTC')
 for v in ['gpi_iyd','gpi_f107d','gpi_f107a','gpi_kp','fkp']:
  add(v,'gpi.F','44-57;rdgpi;getgpi:238-345','historical forcing table or interpolated Kp','none','table (50000),kp(8,50000), fkp scalar','year-day; sfu; Kp dimensionless','external deterministic table/interpolation','GPI file, not full table in primary; instantaneous forcing is saved','reload identical SHA and evaluate at exact year/day/seconds','same forcing demonstrated; cached print counter is not physical interpolation state')
 for v in ['gswm_mi_di_t','gswm_mi_di_u','gswm_mi_di_v','gswm_mi_di_z','t_mi_di','t_mi_sdi']:
  add(v,'gswm.F','33-48;getgswm:50-101;mkgswm:285 onward','migrating tide current fields / monthly hourly reference caches','horizontal boundary','current (lon,lat), reference (lon,lat,12,24)','K;cm/s;cm as applicable','external-table auxiliary','GSWM files; TLBC/ULBC/VLBC saved','first step reload; UTC/year seasonal/hour interpolation recomputes','wrong file or time changes lower boundary; old-source identity alone insufficient')
 for v in ['fs','rk1','beta1','rkm12']:
  add(v,'chemrates.F','10-16;56-91;alloc_tdep/rates_tdep','coupled major-species chemistry matrix / temperature dependent rates','geographic midpoint-based calculation','fs(i,k,3,0:3,j);rates(lev,lon,lat)','fs matrix s^-1; fs source mmr/s; raw reaction-rate units reaction specific','step-local chemistry workspace','not primary; physical species and _NM already listed','rates updated every latitude every step; fs from comp_o2o','do not confuse recomputed coefficients with missing chemical history; exact reset completeness still reviewable')
 for v in ['sflux','rj','qtotal']:
  add(v,'qrj.F','14-29;56-68;init_sflux/qrj','solar spectrum / dissociation / heating workspace','spectral or geographic','sflux(37), rj/qtotal local 3-D','spectral bins; rj s^-1; native heating convention per consumers','forcing/diagnostic','tables external, instantaneous derived workspace not primary','recomputed from clock,forcing,state each step','not valid independent historic budget without per-step capture')
 for v in ['fnrh','fkmh']:
  add(v,'hdif.F','15-18;hdif1/2/3','horizontal diffusion coefficients derived from previous state','geographic with extended halo','(nlevp1,0:nlonp4+1,-2:nlat)','native coefficient convention; do not infer SI from name','step-derived work arrays','not primary','hdif1 recomputes before hdif2/3','halo/execution ordering needed; not evidence of a missing independent forecast state')
 for v in ['trigs','ifax','kut','difk','shapiro','dtsmooth']:
  f='filter.F' if v in ['trigs','ifax'] else 'cons.F'
  add(v,f,'module declarations;init/setfft or init_cons','FFT factors/cutoff/eddy diffusion/filter constants','nonspatial or latitude/vertical-day','trigs(109),ifax(13),kut(nlat),difk(nlev+1,ndays),scalar','algorithmic factors; difk s^-1 pressure convention','derived constant/table','source/config; not primary full arrays','same build/config deterministically initializes; floating implementation still controls bitwise behavior','changed compile/FFT/grid would invalidate equivalence')
 for v in ['b','fb']:
  add(v,'lbc.F','29-36;init_lbc:39-58;bndcmp:520 onward','coupled composition boundary matrices','lower boundary','b(nlonp4,3,3),fb(nlonp4,3)','mixed derivative-condition coefficients','constant boundary operator','not primary matrices; source fixed','bndef constants -> bndcmp on init','must preserve equations, not infer separately fixed O1/O2 values')
 for v in ['modeltime','nstep','nhist','isechist']:
  add(v,'hist.F','module declarations/hist_init','calendar/history scheduling and output bookkeeping','not spatial','scalar/arrays per series','model minutes/steps/counts','run control','some time attributes persisted; history bookkeeping rebuilt','scheduled from START/STOP/HIST/SECHIST; not all control bits serialized','affects output and restart metadata; distinguish from physical field state')
 for v in ['phim3d','emphi3d','emlam3d','emz3d']:
  add('fields_module::'+v,'fields.F','132-136;advance.F:nodynamo','legacy full-domain array; distinct scope from active pdynamo_module','global magnetic','(nmlonp1,nmlat,mlev0:mlev1)','legacy coordinate scaling','legacy conditional auxiliary','not primary','nodynamo zero branch; not active pdynamo array','name collision must not be confused with true next-step state')
 for v in ['mag_phi3d','mag_ephi3d','mag_elam3d','mag_emz3d','geo_phi3d','geo_ephi3d','geo_elam3d','geo_emz3d']:
  add('my_esmf::'+v,'esmf.F','46-47;ESMF grid/field setup','ESMF regridding field object','magnetic/geographic','derived type hosting grid buffer','hosted-data unit convention','auxiliary regridding object','not primary','recreated; exact inverse mapping not proved','does not replace serialized native physical arrays')
 for v,unit in [('f107','sfu'),('f107a','sfu'),('power','GW'),('ctpoten','Volts: native input/nchist convention retained')]:
  add('input_module::'+v,'input.F','67-76;gpi.F:getgpi','instantaneous external forcing','none','scalar',unit,'external forcing','instantaneous history value; full forcing in GPI','same UTC and GPI; no fixed overrides','different forcing could cause divergence; not observed here')
 csvout('runtime_state_audit.csv',rows)
 manifest={'effective_source_files':{str(p.relative_to(R)):m.sha(p) for p in effective.values()},'Make_env_SHA256':m.sha(BUILD/'Make.env'),'Make_workspace_SHA256':m.sha(BUILD/'Make.workspace'),'executable_SHA256':m.sha(m.EXE),'reviewed_table_rows':len(rows),'syntactic_candidate_declarations':len(inventory),'scope_limit':'module declarations and SAVE/DATA search is not whole-program liveness proof; inactive CPP branches may appear; unknown lifecycles explicitly retained','original_sources_modified':False}
 m.save(OUT/'effective_source_manifest.json',manifest);print(json.dumps({k:v for k,v in manifest.items() if k!='effective_source_files'},indent=2))
if __name__=='__main__':main()
