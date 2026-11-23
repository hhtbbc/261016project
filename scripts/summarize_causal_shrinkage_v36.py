"""Publish V36 descriptive comparisons and CPU-only figures from verified CSVs."""
from collections import Counter
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
from matplotlib import font_manager
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'experiments/thermosphere_causal_shrinkage_development_v36'
METHODS=('Raw','Global','ShrinkageHalf')
COLORS=('#607180','#376b99','#c86b38')
FUTURE=('future_1h','future_3h','future_6h')
BLOCKS=('block_0_1h','block_1_3h','block_3_6h')
FLAGS=('RMSE_BENEFIT','RELATIVE_RMS_BENEFIT','TAIL_NONWORSENED',
       'LOW_LATITUDE_BIAS_NONWORSENED')
COMPARISONS=('Global_vs_Raw','ShrinkageHalf_vs_Raw','ShrinkageHalf_vs_Global')
DIRECTIONS={'RMSE_change_pct':'all','relative_RMS_change_pct':'all',
            'relative_P95_change':'all','abs_relative_bias_change':'low'}


def rows(path):
    with (OUT/path).open(newline='') as f:
        return list(csv.DictReader(f))


def main():
    assert OUT.resolve()==OUT and json.loads((OUT/'independent_verification.json').read_text())['verified']
    metrics={(r['date'],int(r['cutoff']),r['window'],r['method'],r['region']):r for r in rows('metrics.csv')}
    joint={(r['date'],int(r['cutoff']),r['window'],r['method']):r for r in rows('joint.csv')}
    delta={(r['date'],int(r['cutoff']),r['window'],r['comparison'],r['region']):r for r in rows('comparisons.csv')}
    dates=sorted({k[0] for k in metrics})
    panel=[(d,h) for d in dates for h in (6,18)]
    panel_titles=[f'{d} {h:02d}Z' for d,h in panel]
    scopes={**{d:[d] for d in dates},'spring':[d for d in dates if d[5:]=='03-25'],
            'autumn':[d for d in dates if d[5:]=='09-23'],'all':dates}
    distribution={}
    for label,ds in scopes.items():
        distribution[label]={}
        for method in METHODS[1:]:
            match=[row for (d,_,w,m),row in joint.items() if d in ds and w in FUTURE and m==method]
            counts=Counter(x['JOINT_NO_REGRET'] for x in match)
            distribution[label][method]=dict(PASS=counts['PASS'],FAIL=counts['FAIL'],
                    NA=sum(v for k,v in counts.items() if k.startswith('N/A')),
                    flag_pass={f:sum(x[f]=='True' for x in match) for f in FLAGS})
    overlap={}
    for d,h in panel:
        for w in FUTURE:
            key='/'.join(joint[d,h,w,m]['JOINT_NO_REGRET'] for m in METHODS[1:])
            overlap.setdefault(key,[]).append(dict(date=d,cutoff=h,window=w))
    direction={}
    for name in COMPARISONS:
        direction[name]={}
        for label,ws in [('cumulative',FUTURE),('nonoverlap',BLOCKS)]:
            direction[name][label]={}
            for field,region in DIRECTIONS.items():
                values=[float(r[field]) for (*_,w,cmp,g),r in delta.items()
                        if cmp==name and g==region and w in ws and r[field]!='']
                direction[name][label][field]=dict(improved=sum(x<0 for x in values),
                    equal=sum(x==0 for x in values),worse=sum(x>0 for x in values),unavailable=24-len(values))
    conflicts={}
    masking={}
    for name in COMPARISONS:
        conflicts[name]={}
        masking[name]={}
        for label,ws in [('cumulative',FUTURE),('nonoverlap',BLOCKS)]:
            a,b=[],[]
            for d,h in panel:
                for w in ws:
                    r=delta[d,h,w,name,'all']
                    rm,rr=float(r['RMSE_change_pct']),float(r['relative_RMS_change_pct'])
                    item=dict(date=d,cutoff=h,window=w,RMSE_change_pct=rm,relative_RMS_change_pct=rr)
                    if rm<0<rr:
                        a.append(item)
                    if rr<0<rm:
                        b.append(item)
            conflicts[name][label]=dict(RMSE_better_Relative_RMS_worse=a,Relative_RMS_better_RMSE_worse=b)
        for field,region in DIRECTIONS.items():
            items=[]
            for d,h in panel:
                full=float(delta[d,h,'future_6h',name,region][field])
                late=float(delta[d,h,'block_3_6h',name,region][field])
                if full<0<late:
                    items.append(dict(date=d,cutoff=h,cumulative=full,block_3_6h=late))
            masking[name][field]=items
    summary=dict(status='DEVELOPMENT_EVALUATION_COMPLETE_VERIFIED',
        joint_cumulative=distribution, joint_overlap_Global_then_ShrinkageHalf=overlap,
        joint_nonoverlap={m:dict(Counter(row['JOINT_NO_REGRET'] for (*_,w,method),row in joint.items()
                                      if method==m and w in BLOCKS)) for m in METHODS[1:]},
        directions=direction, conflicts=conflicts, cumulative_improvement_late_degradation=masking)
    path=OUT/'descriptive_summary.json'
    if path.exists():
        assert json.loads(path.read_text())==summary
    else:
        with path.open('x') as f:
            json.dump(summary,f,indent=2)
            f.write('\n')

    font=ROOT/'data/presentation_assets/noto_sans_sc/NotoSansSC-400.ttf'
    font_manager.fontManager.addfont(font)
    plt.rcParams.update({'font.family':font_manager.FontProperties(fname=font).get_name(),
                         'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False})
    figs=OUT/'figures'
    figs.mkdir(exist_ok=True)
    assert not any(figs.iterdir())
    tags=['1 h','3 h','6 h']
    label='开发集 HINDCAST / PROVISIONAL Map-A / EXTERNAL_DATUM_UNVERIFIED'

    def save(fig,name,title):
        fig.suptitle(title)
        fig.text(.5,.015,label,ha='center',fontsize=8)
        fig.tight_layout(rect=(0,.055,1,.94))
        fig.savefig(figs/name,dpi=155,facecolor='white')
        plt.close(fig)

    for metric, scale, unit, name, title in [
        ('RMSE',1e14,r'$10^{-14}$ kg/m$^3$','01_cumulative_rmse.png','未来累计窗口 · 绝对 RMSE'),
        ('relative_RMS',100,'百分比','02_cumulative_relative_rms.png','未来累计窗口 · Relative RMS')]:
        fig,axs=plt.subplots(2,4,figsize=(13,6),sharey=True)
        for ax,(d,h),name_title in zip(axs.flat,panel,panel_titles):
            for method,color in zip(METHODS,COLORS):
                vals=[scale*float(metrics[d,h,w,method,'all'][metric]) for w in FUTURE]
                ax.plot(tags,vals,color=color,marker='o',label=method)
            ax.set_title(name_title)
            ax.set_ylim(0,None)
            ax.grid(axis='y',alpha=.2)
        for ax in axs[:,0]:
            ax.set_ylabel(unit)
        handles,names=axs.flat[0].get_legend_handles_labels()
        fig.legend(handles,names,loc='lower center',bbox_to_anchor=(.5,.032),ncol=3,frameon=False)
        save(fig,name,title)

    def heat(ax, arrays, xlabels, title, barlabel, fmt):
        lim=max(abs(np.asarray(arrays)).max(),1e-12)
        im=ax.imshow(arrays,cmap='RdBu_r',vmin=-lim,vmax=lim,aspect='auto')
        ax.set_xticks(range(len(xlabels)),xlabels)
        ax.set_yticks(range(8),panel_titles)
        ax.set_title(title)
        for i,row in enumerate(arrays):
            for j,x in enumerate(row):
                ax.text(j,i,format(x,fmt),ha='center',va='center',fontsize=7,
                        color='white' if abs(x)>.65*lim else '#161616')
        ax.figure.colorbar(im,ax=ax,label=barlabel,shrink=.82)

    fig,axs=plt.subplots(2,2,figsize=(11,9))
    for col,cmp in enumerate(COMPARISONS[1:]):
        for row,(field,region,title) in enumerate([
            ('relative_P95_change','all','全域 Relative P95'),
            ('abs_relative_bias_change','low','低纬绝对 Relative Bias')]):
            heat(axs[row,col],[[100*float(delta[d,h,w,cmp,region][field]) for w in FUTURE]
                   for d,h in panel],tags,title+' · '+cmp.split('_vs_')[-1]+' 对照','变化 / 百分点','+.1f')
    save(fig,'03_relative_tail_low_latitude.png','ShrinkageHalf 尾部与低纬偏差：正值为恶化')

    fig,axs=plt.subplots(1,2,figsize=(10,4.7))
    for ax,method in zip(axs,METHODS[1:]):
        outcomes=[[joint[d,h,w,method]['JOINT_NO_REGRET'] for w in FUTURE] for d,h in panel]
        ax.imshow([[{'FAIL':0,'PASS':2}.get(x,1) for x in row] for row in outcomes],
                  cmap=ListedColormap(['#e9a28f','#cccccc','#8cc8bb']),vmin=0,vmax=2,aspect='auto')
        ax.set_xticks(range(3),tags)
        ax.set_yticks(range(8),panel_titles)
        ax.set_title(method)
        for i,row in enumerate(outcomes):
            for k,x in enumerate(row):
                ax.text(k,i,x if x in ('PASS','FAIL') else 'N/A',ha='center',va='center')
    save(fig,'04_joint_matrix.png','累计窗口 · V20 四项联合判据')

    fig,axs=plt.subplots(1,2,figsize=(12,5.1))
    for ax,cmp in zip(axs,COMPARISONS[:2]):
        x=('future_6h', *BLOCKS)
        heat(ax,[[float(delta[d,h,w,cmp,'all']['RMSE_change_pct']) for w in x] for d,h in panel],
             ['累计 6 h','0–1 h','1–3 h','3–6 h'],cmp.split('_vs_')[0],'相对 Raw 的 RMSE 变化 / %','+.1f')
    save(fig,'05_cumulative_vs_blocks.png','累计与非重叠窗口 · 绝对 RMSE 改善和恶化')

    fig,axs=plt.subplots(1,2,figsize=(11,5.1))
    for ax,field,title in zip(axs,('RMSE_change_pct','relative_RMS_change_pct'),('绝对 RMSE','Relative RMS')):
        heat(ax,[[float(delta[d,h,w,'ShrinkageHalf_vs_Global','all'][field]) for w in FUTURE]
                 for d,h in panel],tags,title,'相对 Global 的变化 / %','+.1f')
    save(fig,'06_shrinkage_vs_global.png','ShrinkageHalf 相对 Global 的收益与损失')


if __name__=='__main__':
    main()
