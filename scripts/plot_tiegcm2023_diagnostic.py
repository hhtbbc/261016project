"""Plot native startup fields only; not an equilibrated 2023 atmosphere."""
from pathlib import Path
import argparse,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from netCDF4 import Dataset
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--run-tag',required=True);a=p.parse_args()
if not a.run_tag or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in a.run_tag):raise ValueError('Bad tag')
folder=ROOT/'experiments'/a.run_tag;image=ROOT/'results/figures'/f'{a.run_tag}_native_fields.png'
if image.exists():raise FileExistsError(image)
with Dataset(next(folder.glob('*sech*.nc'))) as n:
    n['ZG'].set_auto_mask(False);n['DEN'].set_auto_mask(False)
    z=np.asarray(n['ZG'][-1])*0.01;rho=np.asarray(n['DEN'][-1])*1000
    assert np.isfinite(z).all() and np.isfinite(rho).all() and (rho>0).all()
    assert (abs(z)<1e30).all() and (np.diff(z,axis=0)>0).all()
    lon=n['lon'][:];lat=n['lat'][:];top=z[-1]/1000
    valid=(z[0]<=400000)&(z[-1]>=400000)
    mapped=np.full(valid.shape,np.nan)
    for j,i in zip(*np.where(valid)):
        mapped[j,i]=np.exp(np.interp(400000,z[:,j,i],np.log(rho[:,j,i])))
fig,axs=plt.subplots(1,2,figsize=(12,4.6),layout='constrained')
for ax,data,title,label in [(axs[0],top,'Top interface native ZG','Height (km)'),
                           (axs[1],np.log10(mapped),'Density at native ZG = 400 km','log10 density (kg/m³)')]:
    m=ax.pcolormesh(lon,lat,data,shading='auto');fig.colorbar(m,ax=ax,label=label)
    ax.set(xlabel='Model longitude (deg)',ylabel='Model latitude (deg)',title=title)
fig.suptitle('2023-03-18 00:10 UTC | 10-minute startup diagnostic | NOT spun up')
fig.savefig(image,dpi=150);plt.close(fig)
meta={'image':str(image.relative_to(ROOT)),'native_height_m':400000,'valid_columns':int(valid.sum()),
      'total_columns':valid.size,'density_range_kg_m3':[float(np.nanmin(mapped)),float(np.nanmax(mapped))],
      'height_datum':'native ZG only; not asserted equivalent to WGS84','spinup_complete':False}
(folder/'figure_audit.json').write_text(json.dumps(meta,indent=2)+'\n');print(image)
