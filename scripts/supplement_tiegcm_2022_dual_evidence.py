"""Additional small-value diagnostics and report clarification from saved results."""
from pathlib import Path
import sys,json,csv
import numpy as np
from netCDF4 import Dataset
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from audit_tiegcm_2021_14day_acceptance import index
from run_tiegcm_mar23_2022_longrun import field
from prepare_fourcastden_swarm_observation_v1 import dump
from observe_tiegcm_2022_dual_initial import table
TAG='tiegcm_2022_dual_initial_spinup_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG

def read(path):
 with path.open() as f:return list(csv.DictReader(f))
def main():
    ai=index(ROOT/'experiments/tiegcm_training_mar23_v2_2022_longrun');bi=index(F);rows=[]
    for t in range(82*86400,84*86400+1,3600):
        values=[]
        for p,i in [ai[t],bi[t]]:
            with Dataset(p) as n:values.append(np.asarray(field(n['N2'])[i],float))
        a,b=values;valid=np.isfinite(a)&np.isfinite(b)&(abs(a)>1e-8)
        for name,mask in [('near_small_le_1e-5',valid&(a<=1e-5)),('above_1e-5',valid&(a>1e-5))]:
            x,y=b[mask],a[mask];delta=abs(x-y);rel=delta/abs(y)
            rows.append(dict(time_doy_seconds=t,subset=name,n=int(mask.sum()),max_abs_mmr=float(delta.max()),max_relative=float(rel.max()),relative_P95=float(np.percentile(rel,95)),outside_5pct=int((rel>=.05).sum()),reference_min=float(y.min()),reference_max=float(y.max())))
    table(O/'N2_small_extended.csv',rows)
    with (ROOT/'reports/TIEGCM_2022_DUAL_INITIAL_SPINUP_V1.md').open('a') as f:
        f.write('\n## 压力层与几何高度的区别\n\n原生层DEN全候选加权相对P95约1.9312%，逐时/层/区域95%点规则通过；但450km固定原生ZG的P95为8.9311%，不能据前者宣布高层密度初态不敏感。同一压力面ZG差的全候选加权RMS约2379.94m、绝对P95约5155.76m，证明两者压力面高度结构仍不同；这不是WGS84外部零面偏差，也不是对密度差的完整因果分解。\n\n')
        f.write('TN最大局地差可达10.3904K，但不足以使任何原门槛时间/层/区域单元低于95%点，故TN判据PASS；水平风最大向量差33.7054m/s，候选572格/最后24h340格失败，主要在14—27层与高纬。终点风场通过不能替代整个窗口通过。\n\n')
        f.write('候选窗组分失败层范围（原生lev，自下向上）为O1 0—19、O2 5—28、N2 11—28、HE 5—28，详细区域矩阵保留。N2近small子集多数点可能同被下限约束，P95为0仍可能存在少量大差异；因此增加N2_small_extended.csv同时报告最大相对/绝对差和超5%点数，不能只看P95。原floor1e-8和small未改。\n')
    gates=read(O/'joint_native_matched_gates.csv')
    with (ROOT/'reports/TIEGCM_2021_2022_DUAL_INITIAL_COMPARISON_V1.md').open('a') as f:
        f.write('\n## 匹配49帧窗口的原生多变量失败格\n\n|变量|2021 7天|2021 14天|2022 7天|\n|---|---:|---:|---:|\n')
        for k in ['DEN','TN','WIND_VECTOR','O1','O2','N2','HE']:
            nums=[next(r['failed_cells'] for r in gates if r['case']==c and r['variable']==k and r['period']=='matched_candidate49') for c in ['2021_7day','2021_14day','2022_7day']];f.write('|'+k+'|'+'|'.join(nums)+'|\n')
        f.write('\n这些是03-23至03-25同长度/同相对候选时刻窗口的重新离线统计，未修改2021原73帧结果。450km全域覆盖均100%，2022双初态差异8.9311%比2021 7天6.0595%更大；仍属同一百分数量级。500km在不同案例的有效域不同，表中保留覆盖率，不按不同有效集合直接排名科学准确性。\n')
    p=ROOT/'docs/TIEGCM_2022_14DAY_SPINUP_DECISION.md';s=p.read_text().replace('以检验仍存在的密度/温度/风初态敏感性','以检验仍超限的固定几何高度密度和水平风敏感性，并同时审查组分；TN本轮已通过冻结规则')
    s=s.replace('按现有驱动消费约定，待精确代码核算的候选raw GPI日期03-07至03-27，其中心81日Fobs支持01-26至05-06','本轮已按既有生成器的起止±2天/中心±40天规则计算：raw GPI日期2022-03-07至03-27，中心81日Fobs支持2022-01-26至05-06')
    s+='\n## 已有原始驱动缺口（只读清点，未下载）\n\n当前GPI声明合法模型域2022 DOY75—84，不能从03-09直接使用。未来16天方案需要101天Fobs/168个Kp桶；本地缺2022-01-26至02-01共7天Fobs，以及03-07 00至03-13 21共56个Kp桶。详见future14_support_inventory.json；已存在值还须逐条核查def Kp与来源，不把“文件中有值”等同驱动质量通过。\n\n建议待另行批准的监督门槛为每组4800秒、两组合计9600秒、每组5GiB/合计12GiB新增、16GiB聚合RSS及余盘20GiB；这是下一轮建议而非本轮授权。按本轮速度的1.5倍单组安全估计约3666秒，已略高于本轮3600秒门槛，不能自动沿用。\n'
    p.write_text(s)
    obs=read(O/'observation/metrics.csv')
    with (ROOT/'reports/SWARM_TIEGCM_2022_DUAL_INITIAL_OBSERVATION_V1.md').open('a') as f:
        f.write('\n## 同共同域的实际变化\n\n')
        for ma in 'ABDE':
            a=next(r for r in obs if r['mapping']==ma and r['group']=='A7' and r['region']=='all');b=next(r for r in obs if r['mapping']==ma and r['group']=='B7' and r['region']=='all')
            f.write(f"- Map{ma}：B7相对A7的RMSE降低{100*(1-float(b['RMSE'])/float(a['RMSE'])):.4f}%，相对RMS降低{100*(1-float(b['relative_RMS'])/float(a['relative_RMS'])):.4f}%（负值为恶化）。\n")
        f.write('\n实际8组合查询均有效，共同样本2880/2880；B7新增11520查询，A7只读复用，未下载新观测。Map-A下B7的低估偏差较小，但不能据此选定“正确初态”；Map-B/E下绝对与相对指标方向不同，所有反例保留。\n')
    annotate_figures()
    print('Supplementary native/composition and decision evidence saved')

def annotate_figures():
    import hashlib
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    draft=F/'figure_draft_local';draft.mkdir(exist_ok=False);changes=[]
    joint=read(O/'joint_matched_native_ZG.csv');cases=['2021_7day','2021_14day','2022_7day']
    for name in ['crossyear_internal_comparison.png','multivariable_acceptance.png']:
        p=O/'figures'/name;changes.append(dict(file=name,old_SHA256=hashlib.sha256(p.read_bytes()).hexdigest()));p.rename(draft/name)
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    for ax,height in zip(axs,[450,500]):
        rr=[next(r for r in joint if r['case']==c and r['height_km']==str(height) and r['region']=='global' and r['period']=='matched_49h_frames') for c in cases]
        yy=[100*float(r['relative_P95']) for r in rr];ax.bar(cases,yy);ax.axhline(5,color='red',ls=':');ax.set_title(f'{height} km / matched Mar23-Mar25');ax.set_ylabel('Internal B/A absolute relative P95 (%)');ax.tick_params(axis='x',rotation=15)
        for i,r in enumerate(rr):ax.text(i,yy[i]*.5,f"coverage\n{100*float(r['coverage']):.2f}%",ha='center',va='center',color='white',fontsize=9)
    fig.suptitle('Matched 49-frame windows | native ZG | 500km valid domains differ; no extrapolation',fontsize=10);fig.tight_layout(rect=[0,0,1,.95]);fig.savefig(O/'figures/crossyear_internal_comparison.png',dpi=160);plt.close(fig)
    acceptance=json.loads((O/'acceptance_by_period.json').read_text());variables=['DEN','TN','WIND_VECTOR','O1','O2','N2','HE'];periods=['candidate','last24h','endpoint'];matrix=np.array([[acceptance[p][k]['failed_cells'] for p in periods] for k in variables])
    fig,ax=plt.subplots(figsize=(7,5));im=ax.imshow(np.log1p(matrix),aspect='auto',cmap='YlOrRd');ax.set_xticks(range(3),periods);ax.set_yticks(range(7),['DEN (ilev)','TN (lev)','WIND (lev)','O1','O2','N2','HE'])
    for i in range(7):
        for j in range(3):ax.text(j,i,str(matrix[i,j])+(' PASS' if matrix[i,j]==0 else ' FAIL'),ha='center',va='center',fontsize=9)
    fig.colorbar(im,ax=ax,label='log(1 + failed time/level/region cells)');fig.suptitle('2022 native pressure-level gates ONLY | fixed-ZG density evaluated separately',fontsize=10);fig.tight_layout(rect=[0,0,1,.94]);fig.savefig(O/'figures/multivariable_acceptance.png',dpi=160);plt.close(fig)
    for item in changes:item['final_SHA256']=hashlib.sha256((O/'figures'/item['file']).read_bytes()).hexdigest()
    dump(F/'figure_annotation_revision.json',dict(reason='Explicit pressure-level DEN label and per-case height coverage; numerical data unchanged',files=changes))

if __name__=='__main__':main()
