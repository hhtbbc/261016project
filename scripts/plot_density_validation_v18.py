"""Real-data figures; Chinese titles, explicit identity, no favorable-window selection."""
from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'scripts'),str(R/'src'),str(R)]
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from run_density_validation_v18 import F,OLD,DAY,IDENTITY,rows,load,table

def plot():
 font=R/'data/presentation_assets/noto_sans_sc/NotoSansSC-400.ttf';font_manager.fontManager.addfont(font);plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name();plt.rcParams['axes.unicode_minus']=False
 out=F/'figures';out.mkdir();a=np.load(F/'matched_local.npz');hours=(a['utc']-np.datetime64(DAY))/np.timedelta64(1,'h');metrics=rows(F/'metrics.csv');regions=rows(F/'region_metrics.csv');j=rows(F/'joint_assessment.csv');old=load(OLD/'correction_parameters.json')['parameters']['B14'];cur=load(F/'correction_parameters.json')['parameters'];captions=[]
 def save(fig,name,title,description):
  fig.suptitle(title+'（独立复核未闭合）',fontsize=12);fig.text(.5,.006,IDENTITY,ha='center',fontsize=7);fig.tight_layout(rect=(0,.04,1,.95));fig.savefig(out/name,dpi=150);plt.close(fig);captions.append(dict(file='figures/'+name,Chinese_title=title,definition_and_interpretation=description))
 fig,ax=plt.subplots(figsize=(12,4));ax.plot(hours,a['density']*1e12,label='Swarm A POD观测');ax.plot(hours,a['raw']*1e12,label='TIE-GCM Raw');ax.set(xlabel='2022-03-25 UTC小时',ylabel='密度 / 10^-12 kg/m^3',xlim=(0,24),ylim=(0,None));ax.legend();save(fig,'01_raw_density.png','图1：真实观测与原始TIE-GCM全天密度','全天曲线仅作描述，正式指标按固定截点未来窗口分别报告。')
 fig,axs=plt.subplots(2,1,figsize=(12,8))
 for ax,h in zip(axs,[6,18]):
  m=(hours>=h)&(hours<h+6);ax.plot(hours[m],a['density'][m]*1e12,color='black',label='Swarm A POD')
  for met in (['Raw','GlobalAdaptive06'] if h==6 else ['Raw','GlobalAdaptive18','LatitudeAdaptive18','Stale06']):ax.plot(hours[m],a[f'{h}_{met}'][m]*1e12,label=met)
  ax.set(title=f'{h:02d}Z截点，全部未来6小时',xlabel='UTC小时',ylabel='密度 / 10^-12 kg/m^3',ylim=(0,None));ax.legend(fontsize=8)
 save(fig,'02_corrected_density.png','图2：冻结历史系数后的未来密度对照','校正参数仅取各自历史3小时；局地系数按未来样本自身原始大地纬度应用。')
 fig,axs=plt.subplots(2,2,figsize=(12,8))
 for i,h in enumerate([6,18]):
  for ax,key,scale,label in [(axs[i,0],'RMSE',1e13,'RMSE / 10^-13 kg/m^3'),(axs[i,1],'relative_RMS',100,'Relative RMS / %')]:
   methods=['Raw','GlobalAdaptive06'] if h==6 else ['Raw','GlobalAdaptive18','LatitudeAdaptive18','Stale06']
   for met in methods:
    v=[next(float(x[key])*scale for x in metrics if int(x['cutoff'])==h and x['window']==f'future_{lead}h' and x['method']==met) for lead in [1,3,6]];ax.plot([1,3,6],v,'o-',label=met)
   ax.set(title=f'{h:02d}Z',xlabel='累计预测时长 / h',ylabel=label,ylim=(0,None),xticks=[1,3,6]);ax.legend(fontsize=7)
 save(fig,'03_horizon_errors.png','图3：绝对RMSE与相对RMS的完整窗口结果','RMSE在原始密度尺度计算；相对误差逐点除以观测密度，二者权重不同。')
 fig,axs=plt.subplots(2,2,figsize=(12,8))
 for i,h in enumerate([6,18]):
  for ax,key,scale,label in [(axs[i,0],'relative_RMS',100,'Relative RMS / %'),(axs[i,1],'relative_bias',100,'有符号Relative Bias / %')]:
   for met in (['Raw','GlobalAdaptive06'] if h==6 else ['Raw','GlobalAdaptive18','LatitudeAdaptive18','Stale06']):
    vals=[next(float(x[key])*scale for x in regions if int(x['cutoff'])==h and x['window']=='future_6h' and x['region']==reg and x['method']==met) for reg in ['low','mid','high']];ax.plot([0,1,2],vals,'o-',label=met)
   ax.axhline(0,color='gray',lw=.6);ax.set(title=f'{h:02d}Z累计6小时',xticks=[0,1,2],xticklabels=['低纬','中纬','高纬'],ylabel=label);ax.legend(fontsize=7)
 save(fig,'04_latitude_errors.png','图4：各纬区相对误差与有符号偏差','分区仅用原始GRS80大地纬度。正Bias表示高估，负值表示低估；包含全部共同样本。')
 fig,axs=plt.subplots(1,2,figsize=(12,4));keys=['GlobalAdaptive06','GlobalAdaptive18','low','mid','high'];labels=['Global06','Global18','低纬18','中纬18','高纬18']
 for ax,field,label in [(axs[0],'b','中位log偏差 b'),(axs[1],'multiplier','密度乘数 exp(b)')]:
  for year,par,offset in [(2021,old,-.17),(2022,cur,.17)]:
   vals=[par[k][field] if k.startswith('Global') else par['LatitudeAdaptive18'][k][field] for k in keys];ax.bar(np.arange(5)+offset,vals,width=.34,label=str(year))
  ax.set(xticks=np.arange(5),xticklabels=labels,ylabel=label);ax.axhline(0 if field=='b' else 1,color='gray',lw=.6);ax.legend()
 save(fig,'05_coefficients_crossyear.png','图5：2021与2022年3月25日冻结历史系数','2021参数只读引用，Stale06精确复用各年同日Global06；未跨年迁移系数。')
 cj=[x for x in j if x['window'].startswith('future_')];flags=['RMSE_BENEFIT','RELATIVE_RMS_BENEFIT','TAIL_NONWORSENED','LOW_LATITUDE_BIAS_NONWORSENED'];fig,ax=plt.subplots(figsize=(11,6));mat=np.array([[x[k]=='True' for k in flags] for x in cj],int);ax.imshow(mat,aspect='auto',vmin=0,vmax=1,cmap='RdYlGn');ax.set(xticks=range(4),xticklabels=['RMSE严格改善','相对RMS严格改善','P95不恶化','低纬绝对Bias不恶化'],yticks=range(len(cj)),yticklabels=[f'{x["cutoff"]}Z {x["method"]} {x["window"]}' for x in cj]);
 for i in range(len(cj)):
  for k in range(4):ax.text(k,i,'通过' if mat[i,k] else '失败',ha='center',va='center',fontsize=8)
 save(fig,'06_joint_criteria.png','图6：四项联合无退化判据逐项结果','绿色满足，红色失败；同一行四项全部满足才记联合PASS，累计窗口相关，不能视作独立实验。')
 fig,axs=plt.subplots(1,2,figsize=(12,4));e=np.log(a['density'])-np.log(a['raw'])
 for ax,h in zip(axs,[6,18]):
  m=(hours>=h)&(hours<h+6);sc=ax.scatter(a['latitude'][m],e[m],c=a['density'][m]*1e12,s=8,cmap='viridis');ax.axhline(0,color='gray');ax.set(title=f'{h:02d}Z未来6小时',xlabel='GRS80大地纬度 / °',ylabel='ln(观测密度/Raw密度)');fig.colorbar(sc,ax=ax,label='观测密度 / 10^-12 kg/m^3')
 save(fig,'07_residual_structure.png','图7：原始残差与纬度、观测密度的关系','空间采样、高度和密度变化相互关联；图中相关性不是已分离的因果贡献。')
 table('figure_captions.csv',captions)
