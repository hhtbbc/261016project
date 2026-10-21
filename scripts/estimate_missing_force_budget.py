"""Offline historical H1 force budget, NO solve_ivp or trajectory propagation."""
import sys,json,csv,re,hashlib
from pathlib import Path
import numpy as np
import astropy,erfa,astropy.units as u
from astropy.time import Time,TimeDelta
from astropy.coordinates import get_body_barycentric,solar_system_ephemeris
from astropy.constants import au,c,L_sun,R_sun
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data
from orbit.force_budget_estimates import third_body_differential,spherical_shadow_class,schwarzschild_monopole
from orbit.j2 import j2_acceleration,terrestrial_z_in_gcrs
from orbit.spherical_harmonics_gravity import GM,RADIUS_M
F=ROOT/'experiments/gravity_truncation_v1';D=ROOT/'data/processed/spherical_harmonics_v1';configure_time_data();conf=json.loads((ROOT/'experiments/spherical_harmonics_v1/configuration.json').read_text())
with np.load(D/'H1_states.npz') as z:states=z['states'];sec=z['seconds']
times=Time(conf['t0_utc'],scale='utc')+TimeDelta(sec,format='sec');text=(ROOT/'data/raw/gravity_sources/gm_de440.tpc').read_text()
mu={key:float(re.search(r'BODY'+str(code)+r'_GM\s*=\s*\(\s*([^\s)]+)',text).group(1).replace('D','E'))*1e9 for key,code in [('sun',10),('moon',301)]}
with solar_system_ephemeris.set('builtin'):
 earth=get_body_barycentric('earth',times);bodies={key:(get_body_barycentric(key,times)-earth).xyz.to_value(u.m).T for key in ['sun','moon']}
P=float((L_sun/(4*np.pi*au**2*c)).to_value(u.N/u.m**2));rows=[];shadow_counts={};stats={};axes=terrestrial_z_in_gcrs(times)
for i,(t,y) in enumerate(zip(sec,states)):
 r=y[:3];v=y[3:];forces={key:third_body_differential(r,bodies[key][i],mu[key]) for key in mu};shadow,lo,hi=spherical_shadow_class(r,bodies['sun'][i],RADIUS_M,float(R_sun.value));shadow_counts[shadow]=shadow_counts.get(shadow,0)+1
 # Deliberate scenario, NOT Swarm confidence interval: A=0.5..2 m², m=400 kg, Cr=1..2.
 scale=(float(au.value)/np.linalg.norm(bodies['sun'][i]-r))**2
 rel=schwarzschild_monopole(r,v,GM);tides=np.zeros(3)
 for key in mu:
  R=bodies[key][i];dist=np.linalg.norm(R);k=R/dist;k2=.3
  j2_induced=-k2*mu[key]/GM*(RADIUS_M/dist)**3
  tides+=j2_acceleration(r,axis=k,mu=GM,radius_m=RADIUS_M,j2=j2_induced)
 # Unit coefficient perturbation only, not measured 2023 C20 change.
 delta_c20=j2_acceleration(r,axis=axes[i],mu=GM,radius_m=RADIUS_M,j2=-np.sqrt(5)*1e-10)
 rows.append({'status':'OFFLINE_FORCE_SCALE_ONLY / HINDCAST','utc':times[i].isot,'elapsed_s':t,'sun_distance_m':np.linalg.norm(bodies['sun'][i]),'moon_distance_m':np.linalg.norm(bodies['moon'][i]),**{f'{key}_third_body_m_s2':np.linalg.norm(a) for key,a in forces.items()},'combined_third_body_m_s2':np.linalg.norm(sum(forces.values())),'spherical_shadow':shadow,'SRP_scenario_min_m_s2':P*scale*.5/400*1*lo,'SRP_scenario_max_m_s2':P*scale*2/400*2*hi,'SRP_sunlit_max_m_s2':P*scale*2/400*2,'Schwarzschild_monopole_m_s2':np.linalg.norm(rel),'isotropic_k2_0p3_solid_tide_scale_m_s2':np.linalg.norm(tides),'delta_C20_1e10_time_axis_scale_m_s2':np.linalg.norm(delta_c20)})
for key in rows[0]:
 if key.endswith('m_s2'):stats[key]={'min':float(min(x[key] for x in rows)),'median':float(np.median([x[key] for x in rows])),'max':float(max(x[key] for x in rows))}
with (ROOT/'results/metrics/gravity_truncation_v1_missing_forces_v2.csv').open('x') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
out={'status':'OFFLINE_FORCE_SCALE_ONLY / HINDCAST','new_integrations':0,'trajectory':'Historical H1 361 frozen states','ephemeris':'Astropy builtin ERFA epv00 and moon98, NOT JPL DE440 positions','astropy_version':astropy.__version__,'erfa_version':erfa.__version__,'time':'Astropy explicitly TDB for builtin API; ERFA moon98 accepts TT or TDB within algorithm uncertainty','frame':'Geometric simultaneous barycentric differences in ICRS-oriented axes, aligned to GCRS for leading Newtonian budget only; no light-time/apparent directions; relativistic BCRS/GCRS transformations omitted','GM_m3_s2':mu,'GM_source':json.loads((ROOT/'configs/missing_force_sources.json').read_text()),'ephemeris_documented_accuracy_not_actual_error_bound':{'Sun_Earth_epv00_1900_2100_vs_DE405_heliocentric_RMS_max_km':[3.7,11.2],'moon98_1950_2100_vs_ELP_RMS_max_km':[6.1,31.7]},'SRP_nominal_pressure_N_m2':P,'SRP_pressure_reference':str(L_sun.reference),'SRP_scenario':{'A_m2':[.5,2.],'mass_kg':400,'Cr':[1.,2.],'status':'Arbitrary sensitivity scenario, not verified Swarm values or confidence limits','shadow':'Spherical finite Sun/Earth disks; penumbra illumination unknown interval [0,1]','shadow_sample_counts':shadow_counts},'tides':'Degree2 isotropic k2=0.3 scale only, not full IERS complex/frequency-dependent Love response, ocean/pole tides or secular update','C20':'Artificial coefficient perturbation 1e-10, verified time-varying ITRS Z expressed in GCRS, unit sensitivity only; NOT actual 2023 secular coefficient correction','force_statistics_m_s2':stats,'no_position_error_extrapolation':True,'source_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
with (F/'missing_forces_v2.json').open('x') as f:json.dump(out,f,indent=2)
print(json.dumps(out,indent=2))
