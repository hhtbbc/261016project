"""Bounded source evidence and existing-slope/correlation diagnostics only."""
from pathlib import Path
import csv,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from prepare_fourcastden_swarm_observation_v1 import sha,dump
from analyze_fourcastden_swarm_observation_v1 import table
F=ROOT/'experiments/swarm_coordinate_orbit_readiness_v1';O=ROOT/'results/swarm_coordinate_orbit_readiness_v1'
PRIOR=ROOT/'results/fourcastden_swarm_observation_v1'


def main():
    rows=[];p=ROOT/'experiments/tiegcm2_apex2023_v1/apex.F90'
    expected=json.loads((ROOT/'experiments/tiegcm2023_s7_continuous_v1/preflight.json').read_text())['apex_sha256'];assert sha(p)==expected
    for day in ['2023-01-04','2023-03-24']:
        g=list(csv.DictReader((O/(day+'_geometry_local.csv')).open()))
        interp=[r for r in csv.DictReader((PRIOR/'interpolation_sensitivity_local.csv').open()) if r['date']==day]
        lookup={int(r['sample']):r for r in interp}
        effect=np.array([np.expm1(float(lookup[int(r['sample'])]['local_dlnrho_dh_per_m'])*float(r['height_difference_GRS80_m'])) for r in g])
        rows.append(dict(date=day,metric='conditional_vertical_density_response_from_actual_SP3_DNS_height_difference',absolute_P95=float(np.quantile(abs(effect),.95)),
            max_abs=float(abs(effect).max()),units='relative',interpretation='existing reference local slope; not total uncertainty or a new density query'))
        with np.load(PRIOR/(day+'_aligned_local.npz')) as z:co=z['coordinates'];lat=co[:,0,0]
        phi=np.deg2rad(lat);a=6378160.;e2=(2-1/298.25)/298.25;n=a/np.sqrt(1-e2*np.sin(phi)**2)
        aw=6378137.;ew=(2-1/298.257223563)/298.257223563;nw=aw/np.sqrt(1-ew*np.sin(phi)**2)
        difference=np.hypot((n-nw)*np.cos(phi),(n*(1-e2)-nw*(1-ew))*np.sin(phi))
        rows.append(dict(date=day,metric='legacy_apex_vs_WGS84_same_numeric_lat_height_cartesian_difference',absolute_P95=float(np.quantile(difference,.95)),
            max_abs=float(difference.max()),units='m',interpretation='constant geometry diagnostic; does not identify calczg datum'))
    table(O/'bounded_coordinate_diagnostics.csv',rows)
    dump(F/'height_evidence_scope.json',dict(actual_apex_path=str(p.relative_to(ROOT)),actual_apex_SHA=expected,legacy_apex_a_m=6378160,legacy_apex_inverse_flattening=298.25,
        applied_electrodynamic_altitude_hs_m=130000,source_lines=['apex.F90:68,358,1041-1075','getapex.F:125-145','cons.F:133,138,315','lbc.F:105-150','addiag.F:257-278'],
        evidence_scope='apex helper geodetic ellipsoid; no established chain equating pressure-grid calczg ZG to that ellipsoid',formal_release=False,
        public_doc_reused='NCAR2.0 grid.html and existing ZCoordinates PDF; no unbounded further search',new_authoritative_external_registration_found=False))
    acf=list(csv.DictReader((O/'descriptive_ACF.csv').open()));out=[]
    for day in ['2023-01-04','2023-03-24']:
        for mp in ['A','B']:
            for model in ['Direct','Flow','LogDEN','History']:
                for scheme in ['Open','Updated']:
                    rr=[r for r in acf if r['date']==day and r['mapping']==mp and r['model']==model and r['scheme']==scheme]
                    out.append(dict(date=day,mapping=mp,model=model,scheme=scheme,lag30s_correlation=float(rr[0]['correlation']),
                        first_cross_1_over_e_seconds=next((r['lag_seconds'] for r in rr if float(r['correlation'])<=np.exp(-1)),''),
                        first_cross_zero_seconds=next((r['lag_seconds'] for r in rr if float(r['correlation'])<=0),''),
                        interpretation='descriptive finite-window nonstationary correlation; no CI/significance/effective N'))
    table(O/'ACF_scale_description.csv',out)
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
