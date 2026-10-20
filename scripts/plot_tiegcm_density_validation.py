"""Plot recorded native-query latency and interpolation sensitivity, no simulation."""
import argparse,csv
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-tag',default='tiegcm_density_interface_v2');a=p.parse_args()
 if not a.run_tag.replace('_','').isalnum():raise ValueError('Unsafe run tag')
 with (ROOT/f'results/metrics/{a.run_tag}_queries.csv').open() as f:rows=list(csv.DictReader(f))
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for source in ['S3','S7']:
  rr=[r for r in rows if r['source']==source]
  axes[0].hist([float(r['seconds'])*1000 for r in rr],bins=35,alpha=.5,label=source)
  axes[1].plot(np.arange(len(rr)),[float(r['linear_vertical_relative_difference'])*100 for r in rr],label=source,alpha=.8)
 axes[0].set(xlabel='Native query latency (ms)',ylabel='Query count',title='1000 native queries per source')
 axes[1].set(xlabel='Native test query index',ylabel='(Linear / log vertical - 1) (%)',title='Interpolation method sensitivity at native ZG 450 km')
 for ax in axes:ax.legend();ax.grid(alpha=.2)
 fig.tight_layout();fig.savefig(ROOT/f'results/figures/{a.run_tag}_performance.png',dpi=160);plt.close(fig)
if __name__=='__main__':main()
