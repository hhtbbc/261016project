"""Check the linked apex solar routine; no TIE-GCM integration or MPI launch."""
from pathlib import Path
import argparse,subprocess,json,sys
import numpy as np
from astropy.coordinates import get_sun,ITRS
from astropy.time import Time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data,check_eop
p=argparse.ArgumentParser();p.add_argument('--run-tag',required=True);a=p.parse_args()
if not a.run_tag or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in a.run_tag):raise ValueError('Bad tag')
out=ROOT/'experiments'/a.run_tag
if not out.resolve().is_relative_to(ROOT) or not out.exists():raise ValueError('Missing existing run')
source=out/'solar_probe.f90'
with source.open('x') as f:f.write('''program solarprobe
use apex,only: subsol
implicit none
real :: lat,lon
integer :: minute
do minute=0,10,5
 call subsol(2023,77,0,minute,0.0,lat,lon)
 write(*,*) minute,lat,lon
enddo
end program
''')
b=ROOT/'experiments/tiegcm2_apex2023_v1';exe=out/'solar_probe'
subprocess.run(['mpifort','-fdefault-real-8','-I'+str(b),str(source),str(b/'apex.o'),'-o',str(exe)],check=True,capture_output=True)
text=subprocess.check_output([str(exe)],text=True);(out/'solar_probe.txt').write_text(text)
values=np.array([list(map(float,line.split())) for line in text.splitlines()])
times=Time(['2023-03-18T00:00:00','2023-03-18T00:05:00','2023-03-18T00:10:00'],scale='utc')
table,meta=configure_time_data();eop=check_eop(times,table)
sun=get_sun(times).transform_to(ITRS(obstime=times)).spherical
lat=sun.lat.deg;lon=sun.lon.deg
dlon=(values[:,2]-lon+180)%360-180;dlat=values[:,1]-lat
assert abs(dlat).max()<.01 and abs(dlon).max()<.025
report={'kind':'separate function probe, not runtime instrumentation and not a model rerun',
        'dates':times.isot.tolist(),'apex_lat_deg':values[:,1].tolist(),'apex_lon_deg':values[:,2].tolist(),
        'astropy_geocentric_lat_deg':lat.tolist(),'astropy_lon_deg':lon.tolist(),
        'latitude_difference_deg':dlat.tolist(),'longitude_difference_deg':dlon.tolist(),
        'eop_check':eop,'passed':True,
        'runtime_evidence':'actual year/day/UT output + original advance.F -> sunloc_apex -> subsol/cofrm call path; solar coordinates not explicitly logged inside model'}
(out/'solar_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
