"""Separate inherited provenance fields from the actual six authorized runs."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/common_force_validation_v1'
def main():
 p=F/'configuration.json';old=json.loads(p.read_text());keys=['t0_utc','initial_state','initial_sha256','base','tight','GM','radius_m','time_data','source40','source20','code_sha256','new_code_sha256','single_gate_m','paired_gate_m','short_gate_m','labels'];c={k:old[k] for k in keys}
 c.update(schema_version=1,provenance_configuration='experiments/common_force_validation_v1/configuration.json',provenance_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),inherited_fields_are_historical_not_active=True,actual_runs={n:dict(degree=d,order=d,third_bodies=tb,duration_s=duration,tight=tight) for n,d,tb,duration,tight in [('H4_tight',40,False,21600,True),('H5_tight',20,True,21600,True),('H6_short',40,True,600,False),('H6_short_tight',40,True,600,True),('H6',40,True,21600,False),('H6_tight',40,True,21600,True)]},output_step_s=60,wall_limit_s=1800,RSS_limit_GiB=2,physics='No drag, no extra central/J2; complete earth harmonics once plus optional third-body differential force',ephemeris='ERFA builtin; PROVISIONAL_EPHEMERIS')
 p=F/'effective_configuration.json'
 if p.exists():assert json.loads(p.read_text())==c
 else:
  with p.open('x') as f:json.dump(c,f,indent=2)
 print('Effective configuration checked; inherited legacy provenance is not an active force setting.')
if __name__=='__main__':main()
