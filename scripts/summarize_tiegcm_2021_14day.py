from pathlib import Path
import json,csv,numpy as np
R=Path('/workspace/data/20261016');C=R/'experiments/tiegcm_2021_spinup_14day_v1';O=R/'results/tiegcm_2021_spinup_14day_v1';OLD=R/'results/tiegcm_2021_spinup_initial_condition_v1/comparison'
def rows(p):return list(csv.DictReader(p.open()))
def one(rr,**kw):return next(x for x in rr if all(x[k]==str(v) for k,v in kw.items()))
def val(x,k,scale=1):return float(x[k])*scale if x.get(k) not in ['',None] else None
def fmt(x):return 'N/A' if x is None else f'{x:.7g}'
def fresh(path,text):
 p=R/path;assert p.resolve().is_relative_to(R);p.open('x').write(text)
def main():
 assert json.loads((C/'analysis_status.json').read_text())['PASS']
 old=json.loads((OLD/'summary.json').read_text());new=json.loads((O/'delta14/summary.json').read_text());resources={g:json.loads((C/g/'run_status.json').read_text()) for g in ['A14','B14']};audits={g:json.loads((C/g/'data_audit.json').read_text()) for g in resources}
 oldh=rows(OLD/'native_ZG_density.csv');newh=rows(O/'delta14/native_ZG_density.csv');oldn=rows(OLD/'native_summary.csv');newn=rows(O/'delta14/native_summary.csv');rr=[]
 for typ,aa,bb,keys in [('native',oldn,newn,['variable','period','region']),('native_ZG',oldh,newh,['height_km','period','region'])]:
  for x in aa:
   y=one(bb,**{k:x[k] for k in keys})
   for metric in ['RMSE','abs_P95','relative_P95','max_abs','max_relative','log_RMSE','coverage','pass_fraction']:
    v,w=val(x,metric),val(y,metric)
    rr.append({'type':typ,**{k:x[k] for k in keys},'metric':metric,'seven_day':v,'fourteen_day':w,'fourteen_minus_seven':w-v if w is not None and v is not None else None,'reduction_percent':100*(v-w)/v if w is not None and v not in [None,0] else None})
 keys=list(dict.fromkeys(k for x in rr for k in x));p=O/'seven_vs_fourteen_summary.csv'
 with p.open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');w.writeheader();w.writerows(rr)
 lines=['# 2021年14天预热双初场连续积分工程验收','','A14、B14分别从2021-03-09 00至03-26 00连续积分，14天候选预热+3天共同评价窗。两组仅更换官方完整SOURCE，SOURCE_START均80 0 0；2002历史身份只代表数值初猜，不代表实际2021大气。旧A7/B7及122帧候选只读。','','|组别|步数|墙钟秒|MPI树RSS MiB|NetCDF字节|主/次历史记录|退出|','|---|---:|---:|---:|---:|---|---|']
 for g,x in resources.items():lines.append(f"|{g}|24480|{x['elapsed_s']:.6f}|{x['peak_sampled_tree_rss_bytes']/2**20:.3f}|{x['netcdf_bytes']}|18/408|{x['returncode']}/4 NORMAL EXIT|")
 lines+=['',f"两组模型监督墙钟合计{sum(x['elapsed_s'] for x in resources.values()):.6f}秒；每组4800秒/5GiB、总9600秒/12GiB、16GiB聚合RSS/每卷256MiB/磁盘余量20GiB均未触发。采样RSS重复计算共享页且可能漏瞬时峰值，非独占物理内存。每组35个NetCDF卷，18个单记录primary、17个24记录secondary。未重试、Restart拼接或额外短例。",'', '## 配置和数值检查','', '同一TIE-GCM可执行文件、apex/IGRF、HEELIS、GSWM、60秒、4MPI/OMP1。新GPI完整来源及独立插值验证见驱动报告。namelist的旧LABEL保留历史“ten-day”字样，不作为积分时长证据；实际START68/STOP85、24480步、完整输出及日历共同确认17天。','']
 for g,a in audits.items():lines.append(f"- {g}：工程PASS；逐小时14字段、units、mask/顶层padding、DEN有限正、TN/风宽数值范围及ZG逐列递增通过；实际驱动日志{a['driver_verified_unique_minutes']}个十分钟节点，NetCDF与GPI最大差{a['NetCDF_driver_max_abs_difference']:.6g}。冷primary未计算诊断仅标N/A，暖态不豁免。")
 lines+=['','源码、初场、GPI和每卷SHA见每组preflight/data_audit及最终保护审计。完整stdout和大NetCDF留本地，不上传。科学预热验收另见7vs14报告，工程正常退出不代表科学PASS。','']
 fresh('reports/TIEGCM_2021_14DAY_LONGRUN_VALIDATION.md','\n'.join(lines))
 lines=['# 2021年7天与14天双初场预热敏感性比较','','Δ7=B7−A7，Δ14=B14−A14，参考各自A。相同03-23至26候选窗口，不将A视为大气真值。cos纬度加权P95与原95%有效点计数门槛分开报告。','','## 450km共同原生ZG密度差异','','|时窗|7天P95 %|14天P95 %|降低比例 %|14天覆盖率 %|','|---|---:|---:|---:|---:|']
 for period in ['candidate','last24h','endpoint']:
  a=one(oldh,height_km=450,period=period,region='global');b=one(newh,height_km=450,period=period,region='global');v,w=val(a,'relative_P95',100),val(b,'relative_P95',100);lines.append(f"|{period}|{v:.7g}|{w:.7g}|{100*(v-w)/v:.7g}|{val(b,'coverage',100):.7g}|")
 lines+=['','## 最后24小时原门槛逐时/层/区域验收','','|变量|7天失败格数|14天失败格数|14天最差满足比例|14天结果|','|---|---:|---:|---:|---|']
 for k,v in new['strict_last24h_native_gates'].items():lines.append(f"|{k}|{old['strict_last24h_native_gates'][k]['failed_cells']}|{v['failed_cells']}|{v['worst_fraction']:.7g}|{'PASS' if v['passed'] else 'FAIL'}|")
 lines+=['','## 共同几何高度与有效域','','|原生ZG km|14天候选密度P95 %|最后24h失败格|候选覆盖率 %|最后24h logRMSE斜率/小时|','|---|---:|---:|---:|---:|']
 for tr in new['no_growth']:
  h=tr['height_km'];q=one(newh,height_km=h,period='candidate',region='global');lines.append(f"|{h}|{val(q,'relative_P95',100):.7g}|{new['strict_last24h_height_gates'][str(h)]['failed_cells']}|{val(q,'coverage',100):.7g}|{tr['last24h_log_RMSE_slope_per_hour']:.7g}|")
 lines+=['','共同高度按双方各列原生ZG作logDEN插值，无外推；500km覆盖不足时只能解释共同有效域，不宣布完整全球通过。压力层与固定几何高度不是同一比较，A中位ZG选层还可能随时间/预热方案变化，固定upper20—28和逐层结果另存。沿轨WGS84高度关系仍N/A。','',f"原生多变量验收：{'PASS' if new['native_multivariable_pass'] else 'FAIL'}；共同高度验收：{'PASS' if new['fixed_height_pass'] else 'FAIL'}。无增长判据还须单列，不能凭450km单项下降宣布所有变量通过。",'', '## 交叉诊断与成本','']
 for kind in ['A14_A7','B14_B7']:
  q=one(rows(O/kind/'native_ZG_density.csv'),height_km=450,period='candidate',region='global');lines.append(f"- {kind}：共同候选窗450km密度P95 {val(q,'relative_P95',100):.7g}%，绝对RMSE {val(q,'RMSE'):.7g}kg/m³。这是更早启动和额外历史的条件差异，不直接称初态误差。")
 baseline=sum(json.loads((r/'run_status.json').read_text())['elapsed_s'] for r in [R/'experiments/tiegcm_training_mar23_v2_2021_longrun',R/'experiments/tiegcm_2021_spinup_initial_condition_v1/B']);newtime=sum(x['elapsed_s'] for x in resources.values());lines.append(f"\n新两组实测监督墙钟/旧两组约{newtime/baseline:.6g}倍；预热长度翻倍但总积分17/10天，不能预设总成本翻倍。2022无新增运行，原122候选未提取/替换。")
 lines+=['','## 完整结果索引','','- delta14/：14天240? 原始408个小时完整配对（以实际summary.hourly_frames为准），逐时、逐层、6区域、3时窗及200—500km全部统计/覆盖/最大差。','- A14_A7/、B14_B7/：共同时间域交叉统计，不作为双初态质量替代。','- seven_vs_fourteen_summary.csv：统一指标逐窗口/变量/区域配对，保留绝对值、差及降低比例。','- figures/：同候选时窗7/14逐时对照，全部来自真实NetCDF统计。','']
 lines=[x.replace('14天240? 原始408','14天原始408') for x in lines];fresh('reports/TIEGCM_2021_SPINUP_7VS14_COMPARISON.md','\n'.join(lines))
 lines=['# 2021年14天预热：组分与极区审查','','O1/O2/N2/HE为无量纲质量混合比，不是数密度。相对差分母为A，参考下限1e-8原样保留；N2接近模型small=1e-6的巨大相对差必须连同绝对差/顶层边界解释，不能提高floor求PASS。','','|变量|候选绝对RMSE SI|候选绝对P95 SI|候选相对P95 %|候选最大绝对差 SI|','|---|---:|---:|---:|---:|']
 for k in ['TN','WIND_VECTOR','O1','O2','N2','HE','Z','ZG']:
  q=one(newn,variable=k,period='candidate',region='global');lines.append('|'+k+'|'+'|'.join(fmt(val(q,c,100 if c=='relative_P95' else 1)) for c in ['RMSE','abs_P95','relative_P95','max_abs'])+'|')
 lines+=['','TN单位K、风矢量m/s、Z/ZG为m，组分无量纲；不同单位不合并RMSE。Z位势高度不能当作ZG几何高度。','','## 未通过格的层和区域','']
 for k,v in new['strict_last24h_native_gates'].items():
  from collections import Counter
  regions=Counter(z['region'] for z in v['failures']);levels=sorted({z['level'] for z in v['failures']});lines.append(f"- {k}：{v['failed_cells']}个失败时刻/层/区域格；区域计数{dict(regions)}；涉及原生层{levels}。")
 lines+=['','精确每格时间索引、比例及逐层/区域统计保存在delta14/summary.json、native_profiles.csv；日志未因结果不利删除。完整掩码和覆盖率不变，不裁剪异常或事后修补。','', '若DEN指标改善而其他变量仍失败，只能提出以密度为重点的后续研究问题，不能擅自删去预测变量、放宽完整训练质量门槛或将旧7天候选改标科学READY。','']
 fresh('reports/TIEGCM_2021_COMPOSITION_POLAR_ANALYSIS.md','\n'.join(lines))
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 figdir=O/'figures';figdir.mkdir()
 for name,variables,metric,scale in [('density_heights',[200,300,400,450,475,500],'relative_P95',100),('native_variables',['DEN','TN','WIND_VECTOR','O1','O2','N2','HE'],'RMSE',1)]:
  fig,axes=plt.subplots(3,3,figsize=(13,10))
  for ax,k in zip(axes.flat,variables):
   for label,base,style in [('7 days',OLD,'--'),('14 days',O/'delta14','-')]:
    data=rows(base/('native_ZG_density_hourly.csv' if name=='density_heights' else 'native_hourly.csv'));q=[x for x in data if int(x['time_doy_seconds'])>=82*86400 and (x.get('height_km')==str(k) and x.get('region')=='global' if name=='density_heights' else x['variable']==k)];ax.plot([(int(x['time_doy_seconds'])-82*86400)/3600 for x in q],[val(x,metric,scale) for x in q],style,label=label)
   ax.set(title=str(k),xlabel='Hours from March 23',ylabel='P95 (%)' if scale==100 else 'RMSE (variable SI)');ax.legend()
  for ax in axes.flat[len(variables):]:ax.set_visible(False)
  fig.tight_layout();fig.savefig(figdir/(name+'.png'),dpi=135);plt.close(fig)
 print('Reports and 7/14 plots rendered')
if __name__=='__main__':main()
