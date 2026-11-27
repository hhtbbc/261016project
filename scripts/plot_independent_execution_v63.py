"""Plot only model execution logs, cited forcing scalars and UTC index metadata."""
import json
import os
import re
from datetime import datetime
from pathlib import Path

from run_independent_events_v63 import ROOT,OUT,EVENTS,load,require


def main():
    output=OUT/'figures'
    require(output.resolve()==output and not output.exists(),'Unsafe figure path')
    output.mkdir()
    cache=OUT/'data_local'/'mpl_local'
    require(cache.resolve()==cache,'Unsafe matplotlib cache')
    os.environ['MPLCONFIGDIR']=str(cache)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(11,6.5),layout='constrained')
    fig.suptitle('V63 CPU engineering receipt | log and forcing metadata only')
    for key in EVENTS:
        path=OUT/f'{key}_run_receipt.json'
        if not path.exists():
            continue
        r=load(path)
        run=ROOT/r['directory']
        status=load(run/'status.json')
        s=status['samples']
        minutes=[x['wall_s']/60 for x in s]
        axes[0,0].plot(minutes,[x['rss_bytes']/2**30 for x in s],label=key)
        axes[0,1].plot(minutes,[x['output_bytes']/2**30 for x in s],label=key)
        rank=(run/'rank_000.log').read_text()
        steps=[int(t) for t in re.findall(r'(?m)^Step\s+(\d+) of',rank)]
        axes[1,0].plot(steps,range(1,len(steps)+1),label=key)
        from netCDF4 import Dataset,num2date
        with Dataset(run/'gpi.nc') as n:
            days=[datetime.strptime(str(int(x)),'%Y%j') for x in n['year_day'][:]]
            axes[1,1].plot(days,n['kp'][:].max(axis=1),label=key)
    for ax,title,x,y in zip(axes.flat,['Process tree RSS','Sampled directory bytes','Rank 0 log sequence',
        'Definitive GFZ driver'],['Wall minutes','Wall minutes','Model step','2023 UTC'],
        ['GiB','GiB','Progress lines','Daily peak Kp']):
        ax.set(title=title,xlabel=x,ylabel=y)
        ax.legend(fontsize=8)
        ax.grid(alpha=.25)
    fig.autofmt_xdate(rotation=25)
    fig.savefig(output/'runtime_and_driver.png',dpi=145)


if __name__=='__main__':
    main()
