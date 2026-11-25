"""CPU-only figures from independently checked V46 CSVs."""
import csv
import json
from pathlib import Path
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.dates import DateFormatter
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'experiments/thermosphere_summer_seed_sensitivity_v46'
RESULT=OUT/'comparison'
START=datetime(2022,6,7)
FONT=ROOT/'data/presentation_assets/noto_sans_sc/NotoSansSC-400.ttf'


def table(name):
    with (RESULT/f'{name}.csv').open() as f:
        return list(csv.DictReader(f))


def load(path):
    return json.loads(path.read_text())


def label(figure,title,caption):
    figure.suptitle(title)
    figure.text(.02,.02,caption,fontsize=8)
    figure.tight_layout(rect=(0,.045,1,.95))


def figure(n, title, caption, plot):
    f,ax=plt.subplots(figsize=(9.6,4.5))
    plot(ax)
    label(f,title,'2022 夏季 junsol − mareqx｜纯物理工程 HINDCAST｜'+caption)
    f.savefig(RESULT/f'{n:02d}.png',dpi=130)
    plt.close(f)


def main():
    assert load(RESULT/'independent.json')['verified']
    font_manager.fontManager.addfont(FONT)
    plt.rcParams['font.family']=font_manager.FontProperties(fname=FONT).get_name()
    plt.rcParams['axes.unicode_minus']=False
    hourly=table('hourly')
    heights=table('height')
    levels=table('levels')
    gates=table('gates')
    days={24,72,168,336}
    points=lambda field:[r for r in hourly if r['variable']==field and r['region']=='global']
    def plot_time(ax,rows,key,scale,label_text):
        series=[r for r in rows if r[key]!='']
        t=[START+timedelta(hours=int(r['hour'])) for r in series]
        ax.plot(t,[float(r[key])*scale for r in series],marker='.',label=label_text)
        ax.xaxis.set_major_formatter(DateFormatter('%m-%d\n%HZ'))
        ax.set_xlabel('UTC')
    def single(field,metric,scale,axis,count):
        def plot(ax):
            plot_time(ax,points(field),metric,scale,field)
            ax.set_ylabel(axis)
            ax.grid(alpha=.25)
        return plot
    for i,title,field,key,scale,axis in [
        (1,'总密度差异随日龄变化','DEN','relative_P95',100,'相对绝对差 P95 (%)'),
        (2,'中性温度差异随日龄变化','TN','RMSE',1,'温度 RMSE (K)'),
        (3,'水平风差异随日龄变化','WIND_VECTOR','RMSE',.01,'风矢量差 RMS (m/s)')]:
        series=points(field)
        figure(i,title,f"{'ilev' if field=='DEN' else 'lev'}；每小时有效样本 {series[0]['n']}；全球面积加权",single(field,key,scale,axis,0))
    def composition(ax):
        for k in ('O1','O2','N2','HE'):
            plot_time(ax,points(k),'relative_P95',100,k)
        ax.set_ylabel('相对绝对差 P95 (%)')
        ax.legend(ncol=4)
    figure(4,'组分差异随日龄变化',f"lev；每帧共同状态样本 {points('O1')[0]['n']}；参考分母 floor=1e-8",composition)
    def regional(ax):
        for region in ('south_polar','south_mid','tropics','north_mid','north_polar'):
            rows=[r for r in hourly if r['variable']=='DEN' and r['region']==region and int(r['hour']) in days]
            plot_time(ax,rows,'relative_P95',100,f"{region} (n={rows[0]['n']})")
        ax.set_ylabel('DEN 相对绝对差 P95 (%)')
        ax.legend(fontsize=8)
    figure(5,'纬度分区密度差异','原生 ilev；日龄 1、3、7、14',regional)
    def vertical(ax):
        for hour in sorted(days):
            rows=[r for r in levels if int(r['hour'])==hour and r['variable']=='DEN' and r['region']=='global']
            ax.plot([float(r['relative_P95'])*100 for r in rows],[int(r['level']) for r in rows],
                    label=f"第{hour//24}天 (每层n={rows[0]['n']})")
        ax.set_xlabel('相对绝对差 P95 (%)')
        ax.set_ylabel('原生 ilev 序号')
        ax.legend()
    figure(6,'原生压力层密度差异','第 1、3、7、14 天 00Z；全球',vertical)
    def by_height(ax):
        m=[r for r in table('day14_map') if r['height_km']=='450']
        image=ax.scatter([float(r['longitude']) for r in m],[float(r['latitude']) for r in m],
                         c=[float(r['signed_relative'])*100 for r in m],s=8,cmap='coolwarm')
        ax.set_xlabel('经度 (°)')
        ax.set_ylabel('纬度 (°)')
        ax.figure.colorbar(image,label='有符号相对差 (%)')
        ax.text(.02,.95,f'共同 n={len(m)}',transform=ax.transAxes)
    figure(7,'第14天共同 ZG 高度密度差异','2022-06-21 00Z；450 km，逐柱对数内插，无外推',by_height)
    def final(ax):
        for h in (200,300,400,450,475,500):
            plot_time(ax,[r for r in heights if r['height_km']==str(h) and r['region']=='global'
                        and int(r['hour'])>=360],'log_RMSE',1,f'{h} km')
        ax.set_ylabel('log(DEN 比值) RMS')
        ax.legend(ncol=3)
    sel=[int(r['n']) for r in heights if int(r['hour'])>=360 and r['region']=='global']
    figure(8,'末24小时共同高度密度差异',f"2022-06-22 00Z 至 06-23 00Z；各时高共同 n={min(sel)}–{max(sel)}",final)
    def acceptance(ax):
        kinds=list(dict.fromkeys(r['variable'] for r in gates))
        data=[[r for r in gates if r['variable']==k and r['passed']!=''] for k in kinds]
        ax.bar(kinds,[100*sum(r['passed']=='True' for r in rows)/len(rows) for rows in data])
        for i,rows in enumerate(data): ax.text(i,1,f'n={len(rows)}',ha='center',fontsize=7)
        ax.set_ylabel('达到单元标准的比例 (%)')
        ax.set_ylim(0,104)
    figure(9,'末24小时预注册门槛通过比例','相对 5%／10 K／20 m/s；每个区域×时刻×层位至少 95% 格点通过',acceptance)
    def resource_plot(ax):
        rows=[load(OUT/k/'status.json') for k in ('run_A_mareqx','run_B_junsol')]
        ax.bar(['mareqx','junsol'],[s['elapsed_s']/60 for s in rows])
        ax.set_ylabel('墙钟 (分钟)')
        other=ax.twinx()
        other.plot(['mareqx','junsol'],[s['peak_sampled_tree_rss_bytes']/2**30 for s in rows],'o-',color='#a45')
        other.set_ylabel('采样峰值 RSS (GiB)')
    figure(10,'两次 CPU 物理积分资源','MPI=4，OMP=1；两组各一次串行。',resource_plot)


if __name__=='__main__':
    main()
