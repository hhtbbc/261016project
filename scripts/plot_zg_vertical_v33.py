"""Chinese engineering plots from the frozen V33 aggregate and verification tables."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

from zg_vertical_v33 import ROOT, OUT, IDENTITY, load, rows, table


def main():
    assert OUT.resolve()==OUT and load(OUT/'independent_verification.json')['PASS']
    frames=[r for r in rows(OUT/'query_gradients.csv') if r['status']=='OK']
    fd=[r for r in rows(OUT/'finite_difference.csv') if r['status']=='PASS_MATH_ONLY']
    font=ROOT/'data/presentation_assets/noto_sans_sc/NotoSansSC-400.ttf'
    font_manager.fontManager.addfont(font)
    plt.rcParams.update({'font.family':font_manager.FontProperties(fname=font).get_name(),
                         'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False})
    directory=OUT/'figures';directory.mkdir()
    notes=[]
    def save(fig,name,title,caption):
        fig.suptitle(title)
        fig.text(.5,.01,IDENTITY+' · 2021/2022-09-23 · UTC 历史固定抽样',ha='center',fontsize=8)
        fig.tight_layout(rect=(0,.055,1,.94))
        fig.savefig(directory/name,dpi=180,facecolor='white')
        plt.close(fig)
        notes.append(dict(file='figures/'+name,title_zh=title,caption_zh=caption))
    fig,ax=plt.subplots(figsize=(8,4.5))
    bins=np.linspace(-2.3,-1.5,17)
    for y,color in [('2021','#3a6483'),('2022','#d1754d')]:
        ax.hist([1e5*float(r['dlnrho_dh_per_m']) for r in frames if r['year']==y],
                bins=bins,histtype='step',lw=2,color=color,label=y+'（120 点）')
    ax.set(xlabel=r'$d\ln\rho/dh$ / $10^{-5}$ m$^{-1}$',ylabel='样本数',ylim=(0,None))
    ax.legend()
    save(fig,'01_gradients.png','两个秋季历史日的原生局部梯度','密度加权八列梯度；不同日期和轨道高度共同变化。')
    fig,ax=plt.subplots(figsize=(8,4.5))
    groups=[[float(r['H_m'])/1000 for r in frames if r['height_stratum']==k] for k in ('1','2')]
    ax.boxplot(groups,tick_labels=['400–450 km（94）','450–500 km（146）'])
    ax.set(xlabel='原始 GRS80 高度分层',ylabel='局部有效尺度高度 / km',ylim=(0,None))
    save(fig,'02_scale_heights.png','不同原始高度区间的局部尺度高度','仅负梯度定义尺度高度；高度分层与年份存在混杂。')
    fig,axs=plt.subplots(1,2,figsize=(10,4.5))
    for ax,key,label in zip(axs,['bottom_margin_m','top_margin_m'],['共同下边界裕量','共同上边界裕量']):
        gs=[[float(r[key])/1000 for r in frames if r['year']==y] for y in ('2021','2022')]
        ax.boxplot(gs,tick_labels=['2021','2022'])
        ax.set(ylabel=label+' / km',ylim=(0,None))
    save(fig,'03_common_margins.png','八列同时有效的高度边界裕量','几何裕量不用于确定物理扰动幅度；含零权重列。')
    fig,axs=plt.subplots(1,2,figsize=(10,4.5))
    first=[r for r in fd if r['step_number']=='1']
    analytic=np.array([float(r['analytic_per_m']) for r in first])*1e5
    finite=np.array([float(r['finite_difference_per_m']) for r in first])*1e5
    axs[0].plot([-2.3,-1.5],[-2.3,-1.5],color='#888',lw=.7)
    axs[0].scatter(analytic,finite,s=7,alpha=.55)
    axs[0].set(xlabel=r'解析 / $10^{-5}$ m$^{-1}$',ylabel=r'中心差分 / $10^{-5}$ m$^{-1}$',
               xlim=(-2.3,-1.5),ylim=(-2.3,-1.5))
    hist=[[float(r['absolute_error_per_m'])*1e15 for r in fd if r['step_number']==k] for k in ('1','2','3')]
    axs[1].boxplot(hist,tick_labels=['步长 h','h/2','h/4'])
    axs[1].set(ylabel=r'绝对数值差 / $10^{-15}$ m$^{-1}$',ylim=(0,None))
    save(fig,'04_finite_difference.png','解析梯度与独立有限差分','所有数学步长留在原八列活动层内；细步长舍入略大。')
    table(OUT/'figure_captions.csv',notes)


if __name__=='__main__':
    main()
