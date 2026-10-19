"""Plot saved native crossday samples, without smoothing or extrapolation."""
from pathlib import Path
import argparse,csv,json
from datetime import datetime,timezone
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from netCDF4 import Dataset,num2date
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--run-tag',required=True);a=p.parse_args()
if not a.run_tag or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in a.run_tag):raise ValueError('Bad tag')
folder=ROOT/'experiments'/a.run_tag;png=ROOT/'results/figures'/f'{a.run_tag}_summary.png'
if png.exists():raise FileExistsError(png)
with (ROOT/'results/metrics'/f'{a.run_tag}_drivers.csv').open() as f:rows=[r for r in csv.DictReader(f) if r['file'].startswith('primary')]
t=[datetime.fromisoformat(r['utc']).replace(tzinfo=timezone.utc) for r in rows]
with Dataset(folder/'secondary_001.nc') as n:
    n['ZG'].set_auto_mask(False);n['TN'].set_auto_mask(False)
    z=np.asarray(n['ZG'][:])*0.01;tn=np.asarray(n['TN'][:])[:,:-1]
    assert np.isfinite(z).all() and np.isfinite(tn).all()
    low=z[:,-1].min(axis=(1,2))/1000;high=z[:,-1].max(axis=(1,2))/1000
    tnlow=tn.min(axis=(1,2,3));tnhigh=tn.max(axis=(1,2,3))
fig,axs=plt.subplots(2,2,figsize=(11,7),layout='constrained')
ax=axs[0,0]
ax.plot(t,[float(r['f107d']) for r in rows],'o-',label='NetCDF F10.7')
ax.plot(t,[float(r['f107d_expected']) for r in rows],'x--',label='Independent GPI')
ax.set(ylabel='Solar flux (sfu)',title='Saved F10.7 across midnight');ax.legend()
ax=axs[0,1]
ax.plot(t,[float(r['Kp']) for r in rows],'o-',label='NetCDF Kp')
ax.plot(t,[float(r['Kp_expected']) for r in rows],'x--',label='Independent GPI')
ax.set(ylabel='Kp (dimensionless)',title='Saved Kp across midnight');ax.legend()
ax=axs[1,0];ax.plot(t,low,'o-',label='Global minimum top');ax.plot(t,high,'o-',label='Global maximum top')
ax.set(ylabel='Native ZG (km)',title='Top interface height');ax.legend()
ax=axs[1,1];ax.plot(t,tnlow,'o-',label='Global minimum TN');ax.plot(t,tnhigh,'o-',label='Global maximum TN')
ax.set(ylabel='Temperature (K)',title='Valid temperature extrema');ax.legend()
for ax in axs.flat:
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d\n%H:%M',tz=timezone.utc))
    ax.xaxis.set_major_locator(mdates.MinuteLocator(byminute=[50,0,10]));ax.set_xlabel('UTC, 2023');ax.grid(alpha=.3)
fig.suptitle('2023 cold-start crossday diagnostic | 3 saved samples | NOT spun up')
fig.savefig(png,dpi=150);plt.close(fig)
(folder/'figure_audit.json').write_text(json.dumps({'file':str(png.relative_to(ROOT)),'times_UTC':[x.isoformat() for x in t],
    'top_height_min_km':low.tolist(),'top_height_max_km':high.tolist(),'TN_min_K':tnlow.tolist(),'TN_max_K':tnhigh.tolist(),
    'note':'Only saved points; connecting lines are not additional simulation samples.'},indent=2)+'\n')
print(png)
