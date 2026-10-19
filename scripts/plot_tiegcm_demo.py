"""Plot a model-default 400 km diagnostic; never re-label as 2023 data."""
from pathlib import Path
import argparse,json
import numpy as np
from netCDF4 import Dataset,num2date
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--run-tag',default='tiegcm2_default_1day_v1');p.add_argument('--output-prefix',default='tiegcm2_default_2002_400km_demo');a=p.parse_args()
for value in [a.run_tag,a.output_prefix]:
    if not value or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in value):raise ValueError('Bad tag')
file=ROOT/'experiments'/a.run_tag/'tiegcm2.0_res5.0_mareqx_smin_sech_001.nc'
outputs=[ROOT/f'data/processed/{a.output_prefix}.npz',ROOT/f'results/figures/{a.output_prefix}.png',ROOT/f'logs/{a.output_prefix}.json']
for target in outputs:
    assert target.resolve().is_relative_to(ROOT)
    if target.exists():raise FileExistsError(target)
with Dataset(file) as ds:
    for name in ['DEN','ZG']:ds[name].set_auto_mask(False)
    rho=ds['DEN'][-1].astype(float)*1000;z=ds['ZG'][-1].astype(float)*.01
    assert ds['DEN'].units=='g/cm3' and ds['ZG'].units=='cm'
    assert np.isfinite(rho).all() and (rho>0).all() and (np.diff(z,axis=0)>0).all()
    height=400000.;assert np.all(z[0]<height) and np.all(z[-1]>height)
    mapped=np.empty(rho.shape[1:])
    for j in range(rho.shape[1]):
        for i in range(rho.shape[2]):mapped[j,i]=np.exp(np.interp(height,z[:,j,i],np.log(rho[:,j,i])))
    lon=ds['lon'][:];lat=ds['lat'][:];date=str(num2date(ds['time'][-1],ds['time'].units))
np.savez_compressed(outputs[0],longitude_deg=lon,latitude_deg=lat,density_kg_m3=mapped,height_geometric_m=height,date=date,source=str(file))
plt.figure(figsize=(10,4.5));plt.pcolormesh(lon,lat,np.log10(mapped),shading='auto');plt.colorbar(label='log10 neutral density (kg/m³)');plt.xlabel('Model geographic longitude (deg)');plt.ylabel('Model geographic latitude (deg)');plt.title('TIE-GCM 2.0 default LOW-SOLAR demo, 400 km geometric height\n'+date+'; NOT the 2023 Swarm atmosphere');plt.tight_layout();plt.savefig(outputs[1],dpi=160);plt.close()
outputs[2].write_text(json.dumps({'source':str(file.relative_to(ROOT)),'date':date,'geometric_height_m':height,'vertical_method':'columnwise log-linear density vs native ZG, no extrapolation','minimum_kg_m3':float(mapped.min()),'maximum_kg_m3':float(mapped.max()),'not_2023_density':True},indent=2))
