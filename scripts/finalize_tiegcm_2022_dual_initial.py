"""Final actual-data figures, reports and bounded next-stage decision."""
from pathlib import Path
import sys,json,csv,time,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from prepare_fourcastden_swarm_observation_v1 import sha,dump
TAG='tiegcm_2022_dual_initial_spinup_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def read(p):
    with p.open() as f:return list(csv.DictReader(f))
def main():
    started=time.perf_counter();run=json.loads((F/'run_status.json').read_text());audit=json.loads((F/'data_audit.json').read_text());assert audit['engineering_PASS']
    acceptance=json.loads((O/'acceptance_by_period.json').read_text());summary=json.loads((O/'comparison/summary.json').read_text())
    native=read(O/'comparison/native_summary.csv');heights=read(O/'comparison/native_ZG_density.csv');hourly=read(O/'comparison/native_ZG_density_hourly.csv');profiles=read(O/'comparison/native_profiles.csv')
    obsrows=read(O/'observation/metrics.csv');joint=read(O/'joint_matched_native_ZG.csv');coverage=read(O/'observation/coverage.csv');figdir=O/'figures';figdir.mkdir(exist_ok=False);figs=[]
    def nrow(var,period='candidate',region='global'):return next(r for r in native if r['variable']==var and r['period']==period and r['region']==region)
    def hrow(height,period='candidate',region='global'):return next(r for r in heights if r['height_km']==str(height) and r['period']==period and r['region']==region)
    def orow(group,mapping='A'):return next(r for r in obsrows if r['group']==group and r['mapping']==mapping and r['region']=='all')
    def save(fig,name):
        fig.suptitle('2022 smin / smax | same drivers | fixed thresholds | native-ZG or explicit PROVISIONAL Map A',fontsize=10);fig.tight_layout(rect=[0,0,1,.94]);fig.savefig(figdir/name,dpi=160);plt.close(fig);figs.append(name)
    fig,ax=plt.subplots(figsize=(10,4));rr=[r for r in hourly if r['height_km']=='450' and r['region']=='global'];ax.plot([float(r['hours_after_start'])/24 for r in rr],[100*float(r['relative_P95']) for r in rr]);ax.axvline(7,color='gray',ls='--',label='Mar23 candidate start');ax.axhline(5,color='red',ls=':',label='5% target');ax.set(xlabel='Days since Mar16 00 UTC',ylabel='450km density absolute relative P95 (%)');ax.legend();save(fig,'DEN450_evolution.png')
    variables=['DEN','TN','WIND_VECTOR','O1','O2','N2','HE'];periods=['candidate','last24h','endpoint'];matrix=np.array([[acceptance[p][k]['failed_cells'] for p in periods] for k in variables]);fig,ax=plt.subplots(figsize=(7,5));im=ax.imshow(np.log1p(matrix),aspect='auto',cmap='YlOrRd');ax.set_xticks(range(3),periods);ax.set_yticks(range(7),variables)
    for i in range(7):
        for j in range(3):ax.text(j,i,str(matrix[i,j])+(' PASS' if matrix[i,j]==0 else ' FAIL'),ha='center',va='center',fontsize=9)
    fig.colorbar(im,ax=ax,label='log(1 + failed time/level/region cells)');save(fig,'multivariable_acceptance.png')
    z=np.load(O/'observation/aligned_local.npz');times=z['utc'];hours=(times-times[0])/np.timedelta64(1,'h');vals=z['values'];ob=z['observed'];common=z['common']
    fig,ax=plt.subplots(figsize=(12,4));ax.plot(hours,ob*1e13,color='black',lw=.8,label='Swarm DNSAPOD0301 instantaneous')
    for i,label in enumerate(['A7 smin','B7 smax']):ax.plot(hours,vals[0,i]*1e13,lw=.8,label=label+' / Map A')
    ax.set(xlabel='2022-03-24 UTC hour',ylabel='Density (1e-13 kg/m3)',title='Same common observation sample N='+str(int(common.sum())));ax.legend();save(fig,'Swarm_density_timeseries.png')
    fig,axs=plt.subplots(1,3,figsize=(12,4))
    for ax,k,scl,label in zip(axs,['RMSE','bias','relative_RMS'],[1e13,1e13,100],['RMSE (1e-13 kg/m3)','Bias (1e-13 kg/m3)','Relative RMS (%)']):ax.bar(['A7','B7'],[float(orow(g)[k])*scl for g in ['A7','B7']]);ax.set_title(label+' / Map A')
    save(fig,'Swarm_metrics.png')
    cases=['2021_7day','2021_14day','2022_7day'];fig,axs=plt.subplots(1,2,figsize=(11,4))
    for ax,height in zip(axs,[450,500]):
        rr=[next(r for r in joint if r['case']==c and r['height_km']==str(height) and r['region']=='global' and r['period']=='matched_49h_frames') for c in cases];ax.bar(cases,[100*float(r['relative_P95']) for r in rr]);ax.axhline(5,color='red',ls=':');ax.set_title(f'{height} km / shared Mar23-Mar25 window');ax.set_ylabel('Internal B/A absolute relative P95 (%)');ax.tick_params(axis='x',rotation=15)
    save(fig,'crossyear_internal_comparison.png')
    old=read(ROOT/'results/swarm_tiegcm_2021_spinup_observation_v1/metrics.csv');fig,axs=plt.subplots(1,2,figsize=(12,4));internal=[100*float(next(r for r in joint if r['case']==c and r['height_km']=='450' and r['region']=='global' and r['period']=='matched_49h_frames')['relative_P95']) for c in cases];axs[0].bar(cases,internal);axs[0].set(ylabel='Internal 450km B/A P95 (%)',title='Simulation sensitivity / matched 49-frame domain')
    for i,group in enumerate(['A','B']):
        errors=[100*float(next(r for r in old if r['mapping']=='A' and r['group']==group+suffix and r['region']=='all')['relative_RMS']) for suffix in ['7','14']]+[100*float(orow(group+'7')['relative_RMS'])]
        axs[1].bar(np.arange(3)+(i-.5)*.36,errors,width=.36,label=group+' initial')
    axs[1].set_xticks(range(3),cases);axs[1].set(ylabel='External relative RMS vs DNS (%)',title='Mar24 observation / PROVISIONAL Map A');axs[1].legend()
    for ax in axs:ax.tick_params(axis='x',rotation=15)
    save(fig,'internal_vs_external.png')
    fig,axs=plt.subplots(1,3,figsize=(12,5))
    for ax,k in zip(axs,['O1','O2','N2']):
        for period in periods[:2]:
            rr=[r for r in profiles if r['variable']==k and r['period']==period and r['region']=='global' and r['relative_P95']];ax.plot([100*float(r['relative_P95']) for r in rr],[int(r['level']) for r in rr],label=period)
        ax.axvline(5,color='red',ls=':');ax.set(title=k+' mass mixing ratio',xlabel='Relative difference P95 (%)',ylabel='Native lev index (bottom -> top)');ax.legend()
    save(fig,'composition_profiles.png')
    fig,ax=plt.subplots(figsize=(9,4))
    for ma in 'ABDE':ax.plot(['A7','B7'],[100*float(orow(g,ma)['relative_RMS']) for g in ['A7','B7']],'o-',label='Map '+ma)
    ax.set(ylabel='Relative RMS vs DNS (%)',title='All maps use same common observation IDs');ax.legend();save(fig,'observation_map_sensitivity.png')
    # Reports derive directly from saved tables, with all failures retained.
    init=json.loads((F/'initial_state_audit.json').read_text());pre=json.loads((F/'preflight.json').read_text())
    eng=['# 2022 smax九天连续积分工程验收','','标签：'+TAG+'。独立B7对照场，不替换原49帧验证候选，不新增训练NPZ。','','|项目|实测|','|---|---:|',f"|积分步数|{audit['model_steps']}|",f"|监督墙钟秒|{run['elapsed_s']:.6f}|",f"|峰值采样进程树RSS MiB|{run['peak_sampled_tree_rss_bytes']/2**20:.3f}|",f"|NetCDF字节|{run['netcdf_bytes']}|",f"|primary/secondary记录|{audit['primary_records']}/{audit['secondary_records']}|",f"|正常MPI退出数|{run['normal_exit_count']}|",'', '全程从2022-03-16 00至03-25 00，一次启动、4MPI/OMP1/60秒，无续算或重试。预估和实测分离；3600秒/16GiB/总新增5GiB/每卷256MiB/余盘20GiB门槛未扩大。实际CPU user/system见run_status.json；采样RSS包含重复共享页且可能漏瞬时峰值。','', f"可执行SHA `{pre['executable_sha256']}`；smax SHA `{init['SHA256']}`；GPI SHA `{pre['gpi_sha256']}`。",'', 'smax来自既有NCAR官方2.0分发目录，文件内部保留trunk/历史1.95来源身份，不能单凭文件名认定物理条件；实际34项double当前/NM/下边界、网格、2002年DOY80 00:00记录全部核验，与smin掩码/单位相容。没有改写时间戳。原namelist只更改SOURCE，输出身份由独立cwd区分，LABEL保留历史文字。','', '原始冷echo继承smin/smax各自源标量，因此t0源F107并不相等；不是固定参数覆盖。暖态输出与实际GPI日志核验，各同历元F107/F107A/Kp/hpower/ctpoten完全一致，冷echo不作为物理诊断样本。','', '全部19个NetCDF卷SHA、时间/网格/单位/掩码、DEN正性、ZG逐列递增及温度风场/组分宽工程范围通过；14必要字段保留。没有以工程范围通过代替科学预热通过。完整逐卷审计见data_audit.json。']
    (ROOT/'reports/TIEGCM_2022_SMAX_LONGRUN_VALIDATION.md').open('x').write('\n'.join(eng)+'\n')
    spin=['# 2022双初态预热敏感性','','B−A以smin A为数值参考，A不是真实大气。DEN/ZG为ilev，TN/风/中性质量混合比按lev登记；Z非ZG。','','## 冻结门槛下失败格数','','DEN5%、TN10K、风矢量20m/s、组分5%，每UTC/层/区域至少95%有效点；实际代码使用严格小于误差门槛，与2021一致。组分相对分母下限1e-8不变，N2 small1e-6仅单独诊断。表为原6区域，不把新增聚合区域重复计入原门槛。','','|变量|全候选49帧|最后24h 25帧|终点|','|---|---:|---:|---:|']
    for k in variables:spin.append('|'+k+'|'+'|'.join(str(acceptance[p][k]['failed_cells']) for p in periods)+'|')
    spin+=['','## 固定共同原生ZG高度','','|km|候选加权P95 %|候选覆盖率 %|最后24h加权P95 %|终点加权P95 %|','|---|---:|---:|---:|---:|']
    for height in [200,300,400,450,475,500]:
        rr=hrow(height);spin.append(f"|{height}|{100*float(rr['relative_P95']):.5f}|{100*float(rr['coverage']):.4f}|{100*float(hrow(height,'last24h')['relative_P95']):.5f}|{100*float(hrow(height,'endpoint')['relative_P95']):.5f}|")
    spin+=['','多变量相对差/绝对差、RMSE、P95、最大值及逐层区域覆盖见comparison/native_summary.csv、native_profiles.csv及acceptance_region_level_matrix.csv；N2接近small的绝对/相对误差见N2_small_diagnostics.csv，不提高floor。缺失padding N/A不算PASS或实测FAIL。','', '最后24h固定高度logRMSE趋势见comparison/last24h_trends.csv，负斜率不是逐时单调下降，也不能外推20/30天必然收敛。共同高度只在双方覆盖列插值，不外推；覆盖不足不能宣称全域通过。','', '7天为候选窗口起点03-23的预热方案名。03-24实际已运行8—9天，终点运行9天。全候选窗49整点含两端，最后24h25整点。SCIENCE_TRAINING_READY=False保持。']
    (ROOT/'reports/TIEGCM_2022_DUAL_INITIAL_SPINUP_V1.md').open('x').write('\n'.join(spin)+'\n')
    obsreport=['# 2022双初态与同期Swarm A反演密度条件对照','','2022-03-24 00:00—23:59:30 UTC，30秒DNSAPOD0301；原观测与旧A7数组SHA核验后复用，不重新下载、不重跑A7查询。Map-A预先指定，A/B/D/E均PROVISIONAL/HINDCAST。','','RMSE、MAE和Bias单位1e-13 kg/m³，平均有符号相对偏差=mean((model−DNS)/DNS)。','','|Map|轨迹|共同N|MAE|RMSE|Bias|相对RMS %|有符号相对Bias %|Pearson|','|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for ma in 'ABDE':
        for g in ['A7','B7']:
            r=orow(g,ma);obsreport.append(f"|{ma}|{g}|{r['n']}|{float(r['MAE'])*1e13:.5f}|{float(r['RMSE'])*1e13:.5f}|{float(r['bias'])*1e13:.5f}|{float(r['relative_RMS'])*100:.4f}|{float(r['relative_bias'])*100:.4f}|{float(r['Pearson']):.5f}|")
    obsreport+=['','全部方案统一quality∩A/B两轨迹∩四映射共同域；各自有效点与拒绝原因见observation/coverage.csv。如果B额外失效，A也在同一共同域重算。没有按结果择优坐标/高度、没有拟合密度/气动参数。','', 'B−DNS=(B−A)+(A−DNS)只对同单位有符号逐点残差成立，已独立检查；RMSE/P95不能相加。内部双初态差异与外部观测残差是不同统计对象，不能从某初态更接近DNS认定其科学初态正确。','', 'DNS为POD相关反演而非无误差真值；30秒样本时间相关，只一天不作独立显著性。EXTERNAL_DATUM_UNVERIFIED保持，不将沿轨条件覆盖等同正式高度已验证。']
    (ROOT/'reports/SWARM_TIEGCM_2022_DUAL_INITIAL_OBSERVATION_V1.md').open('x').write('\n'.join(obsreport)+'\n')
    jointreport=['# 2021/2022双初态联合诊断','','统一使用各年03-23 00至03-25 00的49整点，候选2天匹配，2021原73帧统计不覆盖。2021 7/14方案的目标日距启动不同；年份驱动、IGRF和大气历史不同，不作单因素因果归因。','','|方案|450km内部加权P95 %|450km覆盖率 %|500km内部加权P95 %|500km覆盖率 %|','|---|---:|---:|---:|---:|']
    for c in cases:
        rr=[next(r for r in joint if r['case']==c and r['height_km']==str(height) and r['region']=='global' and r['period']=='matched_49h_frames') for height in [450,500]]
        jointreport.append(f"|{c}|{float(rr[0]['relative_P95'])*100:.5f}|{float(rr[0]['coverage'])*100:.4f}|{float(rr[1]['relative_P95'])*100:.5f}|{float(rr[1]['coverage'])*100:.4f}|")
    aobs,bobs=orow('A7'),orow('B7');jointreport+=['',f"2022 Map-A A/B观测RMSE={float(aobs['RMSE']):.8e}/{float(bobs['RMSE']):.8e} kg/m³，相对RMS={100*float(aobs['relative_RMS']):.4f}/{100*float(bobs['relative_RMS']):.4f}%。",'', '2021延长预热缩小内部差异但观测误差并非统一改善，这项历史证据仍成立。2022只有同起日双初态结果，尚未做14天；不能从本轮宣称2022也已证明“延长预热改善/恶化观测”。本轮只能比较两初态残余影响及其对观测符合程度的条件响应。','', '现有全部主要组分/层/区域失败保留；可据此定位初态敏感性、定义下一轮研究与训练质量审查，不得删变量求PASS或重标原122帧。若设计仅DEN工程研究须独立授权和局限协议，非完整171状态科学训练资格。']
    (ROOT/'reports/TIEGCM_2021_2022_DUAL_INITIAL_COMPARISON_V1.md').open('x').write('\n'.join(jointreport)+'\n')
    failures=acceptance['candidate'];dynamic=any(failures[k]['failed_cells'] for k in ['DEN','TN','WIND_VECTOR'])
    decision='A' if dynamic else 'B'
    estimate=run['elapsed_s']*16/9
    plan=['# 2022年14天双初态预热后续决策','','本轮主建议：'+decision+'。'+('值得开展有界的2022双初态14天实验，以检验仍存在的密度/温度/风初态敏感性；不能预设延长后全部通过。' if dynamic else '先分析仍未达标的组分/层/区域，再决定是否延长；当前密度/温度/风是否已在本次两初态上达标，应与组分完整门禁分开。'),'', '方案C仅可作为另行设计的受限工程研究：不能删掉失败变量后宣称完整科学数据PASS。正式训练与真实轨道门禁不解除。','', '## 如果下一轮批准14天配对','', '- 两条独立连续轨迹：2022-03-09 00至03-25 00，各16天；14天候选预热+2天共同评价。smin/smax、模型和物理设置保持，禁止Restart拼接。','- 现有GPI未证明覆盖03-09，必须新建版本。按现有驱动消费约定，待精确代码核算的候选raw GPI日期03-07至03-27，其中心81日Fobs支持01-26至05-06；必须逐日核验真实Fobs/def Kp，不填补/Fadj替代，不把日期估算当已取得数据。',f"- 本轮实测外推每条约{estimate:.1f}秒，两条约{2*estimate:.1f}秒；1.5安全预算两条{3*estimate:.1f}秒。16天每条NetCDF约{run['netcdf_bytes']*16/9/2**30:.3f}GiB，两条约{2*run['netcdf_bytes']*16/9/2**30:.3f}GiB。资源均是外推，不是下一轮实测。",f"- 本轮采样峰值RSS{run['peak_sampled_tree_rss_bytes']/2**20:.1f}MiB；下一轮仍需重查CPU/内存/磁盘及单卷、文件总量/安全余量，不能自动沿用或扩大单次3600秒预算。",'- 放行前检查扩展驱动支持、SOURCE合法性、所有静态SHA、所有物理开关和输出规则、全过程监督；比较全候选/最后24h/终点、原生层及200—500km有效域、Swarm共同样本。冻结现有5%/10K/20m/s/95%及floor1e-8。','', '本轮未生成扩展GPI、未启动14天或其他模型积分，待用户另行授权。']
    (ROOT/'docs/TIEGCM_2022_14DAY_SPINUP_DECISION.md').open('x').write('\n'.join(plan)+'\n')
    dump(F/'finalization.json',dict(main_next_decision=decision,figure_files=figs,wall_s=time.perf_counter()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,science_training_ready=False,external_datum='EXTERNAL_DATUM_UNVERIFIED'))
    print('Final reports and figures completed. Decision',decision)
if __name__=='__main__':main()
