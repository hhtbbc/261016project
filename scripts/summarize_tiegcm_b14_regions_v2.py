"""Reproduce the descriptive layer/region breakdown from the frozen gate matrix."""
from pathlib import Path
import csv,json
ROOT=Path(__file__).resolve().parents[1]
O=ROOT/'results/tiegcm_2022_b14_exploratory_pair_v2'
def summarize(matrix, summary):
 rows=[]
 for variable in ['DEN','TN','WIND_VECTOR','O1','O2','N2','HE']:
  for period in ['candidate','last24h','endpoint']:
   selected=[r for r in matrix if r['variable']==variable and r['period']==period]
   failed=[r for r in selected if int(r['failed_hours'])>0];gate=summary['gates'][period][variable]
   rows.append(dict(variable=variable,period=period,failed_cells=gate['failed_cells'],evaluated_cells=gate['evaluated_time_level_region_cells'],failed_fraction=gate['failed_cells']/gate['evaluated_time_level_region_cells'],failed_level_min=min([int(r['level']) for r in failed],default=None),failed_level_max=max([int(r['level']) for r in failed],default=None),**{region+'_failed_cells':sum(int(r['failed_hours']) for r in failed if r['region']==region) for region in ['south_polar','south_mid','tropics','north_mid','north_polar']}))
 return rows
if __name__=='__main__':
 with (O/'delta14/acceptance_region_level_matrix.csv').open() as inp:matrix=list(csv.DictReader(inp))
 rows=summarize(matrix,json.loads((O/'delta14/summary.json').read_text()))
 with (O/'variable_region_failure_summary.csv').open('x',newline='') as out:
  writer=csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
