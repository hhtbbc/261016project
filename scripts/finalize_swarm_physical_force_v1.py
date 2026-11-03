"""Actual-record figures, evidence matrix, independent audit and Chinese report."""
from pathlib import Path
import sys,json,csv,time,resource,zipfile,hashlib,re
import numpy as np
import cdflib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from orbit.swarm_force_inputs import cdf_epoch_utc64
from prepare_swarm_physical_force_v1 import F,O,D
from prepare_fourcastden_swarm_observation_v1 import dump,sha
from analyze_fourcastden_swarm_observation_v1 import table

def main():
    begin=time.perf_counter();s=json.loads((F/'summary.json').read_text());contracts=json.loads((F/'CDF_contracts.json').read_text());manifest=json.loads((F/'download_manifest.json').read_text());eventrows=list(csv.DictReader((O/'candidate_event_intervals.csv').read_text().splitlines()));samples={};sources=[]
    for c in contracts:
        with cdflib.CDF(ROOT/c['path']) as raw:
            t=cdf_epoch_utc64(raw.varget('Timestamp'));sel=(t>=np.datetime64('2023-01-04T01:00:00'))&(t<=np.datetime64('2023-01-04T13:00:00'));v={k:raw.varget(k)[sel] for k in raw.cdf_info().zVariables if k!='Timestamp'};samples[c['product']]=(t[sel],v)
    td,vd=samples['SC_ADYN'];tq,vq=samples['STRAATT'];xd=1+(td-np.datetime64('2023-01-04T01:00:00'))/np.timedelta64(1,'h');xq=1+(tq-np.datetime64('2023-01-04T01:00:00'))/np.timedelta64(1,'h')
    matrix=[
      ('SP3 reference','PARTIAL','Official Jan4 SP3ACOM0203 / prior geometry audit','Time/frame/file validated; precise-orbit validation product and accuracy qualification incomplete'),
      ('Initial P/V','PARTIAL','Existing SP3 Hermite frozen initial state','Uses t0+2s: retrospective smoothing, not causal real-time initialization'),
      ('Density fields','PARTIAL','Jan4 DNSAPOD0301, author TIE-GCM, Direct saved states','DNS is POD-derived; source uncertainties and external mapping remain'),
      ('External height datum','BLOCKED','TIE-GCM2.0 native ZG; existing NCAR draft','External zero surface/geographic convention unconfirmed'),
      ('Spacecraft mass','PARTIAL','SC_ADYN0601 m_SC, kg','Record integrity/units checked; version-specific flags and uncertainty not certified'),
      ('Spacecraft attitude','PARTIAL','STRAATT0601 q ITRF <- S/C','Component order and active/passive matrix convention; current flag semantics missing'),
      ('Effective frontal area','BLOCKED','SC_ADYN A_head/right/left/down orbit-frame vectors','Complete macrogeometry, orbit-frame basis, visibility/occlusion and reference area unverified'),
      ('Drag coefficient','BLOCKED','GSI literature identifies model families only','No certified Swarm geometry/GSI/material/environment parameterization'),
      ('Actual thrust','PARTIAL','SC_ADYN dt_thr/f_thr/thr_set; STRAATT Maneuver_Id','Candidate records identified; channel geometry/calibration/code dictionary missing'),
      ('AUXAORBMAN0355','NOT_AVAILABLE','Exact input named in STRAATT global metadata','Not obtained; current public L1 listings do not expose an AUX directory'),
      ('Complete force model','BLOCKED','Existing H6 and high-order numerical qualification','Gravity truncation, tides/radiation/relativity as applicable, real aerodynamic/thrust inputs incomplete'),
      ('Conditional numerical solver','PASS','ABCD DOP853 closure report','Only numerical qualification under frozen conditional assumptions')]
    table(O/'real_orbit_admission.csv',[dict(item=a,status=b,source=c,remaining=d) for a,b,c,d in matrix])
    evidence=[
      dict(topic='Official product acquisition',URL='https://swarm-diss.eo.esa.int/',version='0601',evidence='Exact Jan4 files, ZIP CRC and CDF metadata checked',proves='Actual record availability and self-described units',does_not_prove='Complete force calibration or public redistribution permission'),
      dict(topic='Current public definition page',URL='https://www.esa.int/Applications/Observing_the_Earth/FutureEO/Swarm/Documents_publications',version='linked2013 issue5.13',evidence='Page still links 9October2013 definition',proves='Older definition remains a public reference',does_not_prove='Full0601 quality or quaternion convention applicability'),
      dict(topic='Newer definition endpoint',URL='https://earth.esa.int/eogateway/documents/20142/37627/swarm-level-1b-product-definition-specification.pdf',version='unread',evidence='HTTP403; no bypass attempted',proves='Access blocked in bounded check',does_not_prove='Definition unavailable to authorized users'),
      dict(topic='Handbook SC/STR',URL='https://swarmhandbook.earth.esa.int/catalogue/',version='unread',evidence='Specific SCxDYN/STRxATT pages inaccessible to browsing tool',proves='No new readable dictionary obtained',does_not_prove='No authoritative definition exists'),
      dict(topic='Aerodynamic GSI',URL='https://doi.org/10.1051/swsc/2021035',version='2021',evidence='Primary author repository abstract https://repository.tudelft.nl/record/uuid%3A7e1ff16f-85ee-4078-b40c-ed7c44ed22a7',proves='GSI, composition and temperature assumptions affect density retrieval; accommodation is not Cd',does_not_prove='A specific Jan42023 Cd or matched reference area'),
      dict(topic='Swarm POD-density aerodynamics',URL='https://pure.tudelft.nl/ws/portalfiles/portal/71416246/PREPRINTswarmdensityASR.pdf',version='author preprint',evidence='Source describes geometry/orientation/GSI dependent force coefficient and15-panel model',proves='Physical model chain is needed',does_not_prove='Our four area vectors form that full model'),
      dict(topic='TIE-GCM native vertical grid',URL='https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/diags.html',version='2.0',evidence='DEN levels=ilev; ZGMID levels=lev, geometric height cm',proves='Native variable staggering and units',does_not_prove='ZG zero equals GRS80/WGS84'),
      dict(topic='HAO archived height discussion candidate',URL='https://fpi.hao.ucar.edu/hao/aim3/stans/ben/benhome/tgcm_issues/mozilla51.pdf',version='unverified',evidence='New search candidate inaccessible; not used as a scientific assertion',proves='Nothing beyond candidate existence in search',does_not_prove='Version applicability or external datum')]
    table(O/'official_evidence_review.csv',evidence)
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    def save(fig,name,data):
        fig.subplots_adjust(top=.88,bottom=.20,hspace=.43);fig.suptitle('Swarm-A actual auxiliary records |2023-01-04 01-13UTC |0601',y=.98)
        fig.text(.5,.02,'Product records, not independently error-free truth | current quality-code semantics incomplete\nFormal physical orbit prediction BLOCKED; no new trajectory propagation',ha='center',fontsize=8)
        p=O/(name+'.png');assert not p.exists();fig.savefig(p,dpi=160,bbox_inches='tight');plt.close(fig);sources.append(dict(figure=p.name,data=data,SHA256=sha(p)))
    def axis(ax,y,title):ax.set(xlabel='2023-01-04 UTC hour',ylabel=y,title=title);ax.set_xlim(1,13);ax.grid(alpha=.2)
    fig,axes=plt.subplots(2,1,figsize=(12,7));axes[0].plot(xd,vd['m_SC'],lw=.4);axis(axes[0],'Reported mass (kg)','All43200 actual SC_ADYN records; range is NOT uncertainty');axes[1].plot(xd,100*(400/vd['m_SC']-1),lw=.4);axis(axes[1],'Mass-only drag change (%)','Analytical400/m scaling, holding all other inputs fixed; no orbit run');save(fig,'mass_and_mass_only_sensitivity','mass_timeseries_local.csv; SC_ADYN.m_SC')
    fig,axes=plt.subplots(4,1,figsize=(12,10));axes[0].plot(xq,(np.linalg.norm(vq['q'],axis=1)-1)*1e9,lw=.4);axis(axes[0],'Norm deviation (1e-9)','Norm near1 does not certify convention or attitude quality')
    for ax,k in zip(axes[1:],['Flags_q','SyncStatus','Maneuver_Id']):ax.step(xq,vq[k],where='post',lw=.5);axis(ax,k+' raw code','Raw categorical code;0601 meaning not inferred from other products')
    save(fig,'attitude_quality_and_codes','attitude_quality_local.csv; STRAATT.q/flags')
    fig,axes=plt.subplots(3,1,figsize=(12,8));axes[0].plot(xd,vd['dt_thr'].sum(axis=1),lw=.6);axis(axes[0],'Sum channel on-time (s)','82 positive records; sum over12 channels, not elapsed firing duration');axes[1].plot(xd,np.linalg.norm(vd['f_thr'],axis=1));axis(axes[1],'Nominal f_thr norm (mN)','All zero nominal-force records do NOT prove no actual thrust');axes[2].step(xd,vd['Flags_Platform'],where='post',lw=.5);axis(axes[2],'Platform raw code','296 records with code16; no unverified bit decoding');save(fig,'thruster_candidates','SC_ADYN.dt_thr/f_thr/Flags_Platform; candidate_event_intervals.csv')
    bins=[]
    for h in range(1,13):
        a=(xd>=h)&(xd<h+1);b=(xq>=h)&(xq<h+1);bins.append(dict(UTC_hour=h,mass_records=int(a.sum()),attitude_records=int(b.sum()),finite_q=int(np.isfinite(vq['q'][b]).all(axis=1).sum()),raw_q_flag0=int((vq['Flags_q'][b]==0).sum()),positive_on_time_records=int(np.any(vd['dt_thr'][a]>0,axis=1).sum()),raw_maneuver4_records=int((vq['Maneuver_Id'][b]==4).sum())))
    table(O/'hourly_availability.csv',bins);fig,axes=plt.subplots(2,1,figsize=(12,7));h=np.arange(1,13)
    for key in ['mass_records','attitude_records','raw_q_flag0']:axes[0].plot(h,[x[key] for x in bins],'o-',label=key)
    axes[0].set(ylabel='Records per fixed UTC hour',title='Finite/data coverage and raw code0 are distinct;13UTC endpoint separately retained');axes[0].legend();axes[0].grid(alpha=.2)
    for key in ['positive_on_time_records','raw_maneuver4_records']:axes[1].plot(h,[x[key] for x in bins],'o-',label=key)
    axes[1].set(xlabel='UTC hour bin start',ylabel='Raw record count',title='No interpretation as confirmed impulse or maneuver count');axes[1].legend();axes[1].grid(alpha=.2);save(fig,'hourly_coverage_and_candidates','hourly_availability.csv')
    fig,ax=plt.subplots(figsize=(12,7));colors={'PASS':'teal','PARTIAL':'goldenrod','BLOCKED':'crimson','NOT_AVAILABLE':'grey'}
    ax.barh(np.arange(len(matrix)),np.ones(len(matrix)),color=[colors[x[1]] for x in matrix]);ax.set_yticks(np.arange(len(matrix)),[x[0] for x in matrix]);ax.invert_yaxis();ax.set_xticks([])
    for i,row in enumerate(matrix):ax.text(.02,i,row[1],va='center',color='white' if row[1]!='PARTIAL' else 'black')
    ax.set_title('Evidence-based admission matrix, NOT a measured accuracy score');save(fig,'physical_readiness_matrix','real_orbit_admission.csv')
    table(O/'figure_sources.csv',sources)
    # Independent CRC/byte identity check and direct record arithmetic.
    for rec in manifest:
        with zipfile.ZipFile(ROOT/rec['path']) as z:
            assert z.testzip() is None
            for member in rec['members']:
                data=z.read(Path(member['path']).name);assert hashlib.sha256(data).hexdigest()==member['SHA256']==sha(ROOT/member['path'])
    assert len(td)==43200 and len(tq)==43201 and np.isfinite(vd['m_SC']).all();np.testing.assert_allclose(float(sum(vd['m_SC'])/len(td)),s['SC_ADYN']['mass_mean_kg'],rtol=1e-13)
    assert int(np.count_nonzero(np.sum(vd['dt_thr']>0,axis=1)))==s['SC_ADYN']['dt_thr_positive_records'];assert int(sum(int(row['sample_count']) for row in eventrows if row['kind']=='dt_thr_any_channel_positive'))==82
    protected=json.loads((F/'protected.json').read_text());assert all(sha(ROOT/k)==v for k,v in protected.items());hist=json.loads((ROOT/'experiments/tiegcm_runtime_restart_audit_v1/protected_files.json').read_text());assert all(sha(ROOT/k)==v for k,v in hist.items())
    logs=(ROOT/'logs/swarm_physical_force_v1_tests_precise_time_final.log').read_text();assert 'Ran28 tests'.replace('Ran28','Ran 28') in logs and logs.rstrip().endswith('OK')
    payload=sum(p.stat().st_size for p in D.iterdir() if p.is_file());assert payload<30*2**20
    audit=dict(status='PASS',protected_unchanged=len(protected),historical_unchanged=len(hist),new_ODE=0,new_GPU=0,new_TIE=0,new_raw_ZIP_bytes=sum(x['bytes'] for x in manifest),all_downloaded_payload_bytes=payload,ZIP_CRC_and_extracted_identity_verified=True,source_products=2,tests=28,figures=5,wall_s=time.perf_counter()-begin,RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,formal_orbit='BLOCKED',science_training=False)
    dump(F/'independent_audit.json',audit)
    write_reports(s,contracts,manifest,matrix,audit,eventrows)
    print(json.dumps(audit,indent=2))

def write_reports(s,c,manifest,matrix,audit,eventrows):
    test_elapsed=float(re.search(r'Ran 28 tests in ([0-9.]+)s',(ROOT/'logs/swarm_physical_force_v1_tests_precise_time_final.log').read_text()).group(1))
    m=s['SC_ADYN'];q=s['STRAATT'];events=[v for v in eventrows if v['kind']=='dt_thr_any_channel_positive'];mins=100*(400/m['mass_max_kg']-1);maxs=100*(400/m['mass_min_kg']-1)
    text=f'''# Swarm-A真实受力参数与轨道预测准入 V1

## 1. 结论与本轮范围

实际取得2023-01-04 SC_ADYN和STRAATT两份官方0601全天产品，完成目标01:00—13:00UTC记录解析、接口开发、28项独立CPU测试和5张真实记录/证据状态图。没有轨道传播、网络推理、训练、TIE-GCM或旧实验重算。

**记录质量可读取，但真实受力模型未闭合。** m_SC单位与记录完整性已核实；正式质量采用仍PARTIAL，姿态旋转、迎风面积、Cd及实际推力未验证。FORMAL_VALIDATED拒绝放行。真实轨道BLOCKED、EXTERNAL_DATUM_UNVERIFIED、科学训练False保持；此前条件数值闭环PASS和旧RK45FAIL均不改。

## 2. 数据获取、时间和许可

通过[ESA公开分发服务](https://swarm-diss.eo.esa.int/)查询具体Sat_A目录，冻结唯一Jan4/0601文件名和大小后下载。ZIP共{audit['new_raw_ZIP_bytes']}字节；包括目录等元数据的实际保存响应载荷{audit['all_downloaded_payload_bytes']}字节，小于30MiB。解压后逐成员CRC、SHA及原CDF字节一致性验证；发布方独立SHA未提供，本地SHA不是发布方数字签名。

ESA页面说明访问使用受其数据政策及条款约束；未绕过登录或权限，原ZIP/CDF/HDR/DQC及逐记录重打包仅本地保存，不自动公开原始产品，不宣称某个未经核实的CC许可证。

'''
    for x in manifest:text+=f"- `{Path(x['path']).name}`：{x['bytes']}字节，SHA256 `{x['SHA256']}`；来源 `{x['URL']}`。\n"
    text+='\n两产品均全天86400记录；SC_ADYN由ACCELE/03.25于2025-07-19重处理，STRAATT由ORBATT/03.25于2025-07-10重处理，不能声称2023当时可用。CDF_EPOCH与Sensing_Start的UTC头独立对齐，不套GPS偏移。SC_ADYN有约0.757秒采样相位，STRAATT整UTC秒；共同对齐前一原始记录的龄期0.239093750—0.243210938秒，未来最近记录偏移0.756789062—0.760906250秒。接口不重标日期/时间，也不把两轴当作同时采样。\n'
    text+=f'''
## 3. 质量时间序列与400kg对照

目标窗SC_ADYN共{m['records']}记录（01:00:00.756附近至12:59:59.757附近），全部m_SC有限且正值：

|指标|实际值|
|---|---:|
|最小质量|{m['mass_min_kg']:.6f}kg|
|最大质量|{m['mass_max_kg']:.6f}kg|
|平均质量|{m['mass_mean_kg']:.9f}kg|
|相邻记录最大变化|{m['largest_adjacent_mass_step_kg']:.6f}kg|
|相对400kg的质量差|{m['mass_relative_to_400_percent_min']:.6f}%—{m['mass_relative_to_400_percent_max']:.6f}%|

这不是称重绝对真值，范围/样本标准差都不是测量不确定度。仅在其他因素固定时，阻力加速度按400/m缩放，相对演示质量改变约{mins:.6f}%至{maxs:.6f}%；只是代数灵敏度，没有运行新轨道，也未按SP3拟合。不能用它替代面积/Cd/推力。

SyncStatus原码0有43200条，Flags_Platform原码16有296条。没有获得0601适用的完整码表，因此没有把这些记录全认定为正式有效，也没有按未知标志删点。原始值及所有质量记录保留，完整质量时序在本地mass_timeseries_local.csv，公开小时汇总mass_hourly_summary.csv。

## 4. 姿态与面积

STRAATT目标窗{q['records']}条，含13:00终点；非有限q有{q['quaternion_nonfinite_rows']}条。范数{q['quaternion_norm_min']:.12f}—{q['quaternion_norm_max']:.12f}，最大偏离1约{q['norm_max_abs_deviation']:.4g}。这只证明基本数值结构，不能证明旋转定义或观测质量合格。

实物q说明为ITRF←S/C；0601分量顺序（xyzw或wxyz）、主动/被动矩阵定义未由适用文件确认。旧5.13概览/详细表方向文字存在不一致；不能套其他MAG产品、其他卫星或通用四元数代码。实际rotation_to_itrs明确拒绝。

Flags_q分布：`{json.dumps(q['Flags_q'])}`。SyncStatus原码1有65条；Maneuver_Id原码4有14274条。这些原码意义保留待审，未将全部非零简单判坏，也未将全部有限q判好。

A_head/right/left/down均float64三分量，CDF说明为orbit-frame截面向量、单位m²；它们不是经过核实的完整面元模型。未用向量范数充当迎风面积。仍缺ORB基底/法向、侧面可见性、遮挡、太阳翼及几何完整性、与Cd配套的参考面积。

只实现了显式synthetic_*数学工具：Hamilton主动xyzw正逆转与正交/行列式检查；凸闭合单侧面元无遮挡假设下，A_eff=sum(max(area_vector·v_hat,0))。2×3×4合成箱体沿x投影12m²，xy方向20/sqrt(2)m²，整体旋转后不变。合成通过不代表真实Swarm几何通过，真实面积仍UNVERIFIED。

## 5. Cd的物理证据

[March等2021原始研究](https://doi.org/10.1051/swsc/2021035)及[作者机构摘要](https://repository.tudelft.nl/record/uuid%3A7e1ff16f-85ee-4078-b40c-ed7c44ed22a7)支持：气体表面相互作用、组分与温度会影响气动力和反演密度。文中的能量适应系数不是Cd，不能把0.85当Cd；本轮不借此给Jan4指定常数。

[作者POD密度处理预印本](https://pure.tudelft.nl/ws/portalfiles/portal/71416246/PREPRINTswarmdensityASR.pdf)描述了依赖形状、朝向和气体表面作用的力系数与15面元模型。这是模型链的证据，不是我们已取得完整几何/材料/表温/参考面积参数的证据。需要冻结同一几何、气体温度/组分、相对速度、表面模型及A_ref；也要评估升力/侧向力，而不是默认标量Cd包含全部作用。演示2.2不用于正式数据接口。

## 6. 推力候选与版本问题

目标窗dt_thr十二通道中至少一通道>0的记录{m['dt_thr_positive_records']}条，形成{len(events)}个连续**记录段**；最大单记录单通道开启{m['max_record_channel_on_time_s']:.3f}秒，全部通道记录值之和{m['total_channel_on_time_s']:.3f}秒。通道可同时开启，因此此和不是净持续时间、完整脉冲数、机动次数或冲量。

f_thr实物单位mN，明确乘1e-3转N；所有目标记录的名义组合力均0，thr_set原码1。但这不能排除执行推力：可能涉及平衡脉冲、未填充/不同语义或其他处理，当前没有证据唯一判断。Maneuver_Id=0也不能单独证明无推力。绝不将原码4直接定性为已知平移机动或按它删轨道。

候选记录段见candidate_event_intervals.csv，逐正开启记录本地thruster_positive_records_local.csv。每段标注CANDIDATE_RECORD_SEGMENT_NOT_CONFIRMED_MANEUVER，actual_impulse保持空。

STRAATT实际处理输入列出了AUXAORBMAN_20140115T115151_20250701T202911_0355，以及AUXAL1BPC_20230101T000000_20230701T000000_0109和AUXAAOC_C_0006等；这是下一步应请求的**具体版本**，不是臆造文件。当前公开L1目录未给AUX目录，未取得这些原件，不尝试认证绕行。SC_ADYN与STRAATT/轨道处理存在共享输入，不能视为独立真值互证。

## 7. 可复用接口及测试

`src/orbit/swarm_force_inputs.py`提供SwarmForceInputProvider.at(UTC,mode=Mode.RESEARCH_PROVISIONAL)。每次核验原CDFSHA，返回质量、原q、名义推力与开启记录、原始质量码、各自记录UTC/龄期、版本和SHA。质量可读但PARTIAL；面积/Cd为空，实际推力未知，缺项不替代400/1/2.2。

当前采用前一观测记录快照，**不声称同刻插值值**；拒绝覆盖外和>1.1秒陈旧记录，不跨缺口、异常或事件做静默插值。此1.1秒是1Hz产品快照陈旧保护，不是物理质量放行标准。不同字段保留不同采样轴。

FORMAL_VALIDATED目前总是因未具备完整证据而拒绝；普通布尔或字符串不能绕过枚举模式。合成旋转工具不绑定实际Swarm q。单位错误、版本不匹配、文件损坏/加载后改变、非正质量、非有限/明显非单位q、未知推力和质量原码均有独立测试。产品q范数平方偏离1超过1e-8只标数值INVALID，不据小偏离标质量PASS，且不静默归一化。

28项CPU测试通过（最终{test_elapsed:.3f}秒）。合成与实物测试分开；测试通过不意味着真实参数已科学验证。例子interface_examples_local.json保留01/07/13时完整返回和溯源。

## 8. TIE-GCM高度登记：有界结果

复用已有源码/数据证据，本轮不重复旧查询。NCAR2.0诊断文档明确DEN位于ilev、ZGMID位于lev；本项目实际DEN/ZG均按ilev接口处理。不能笼统说本项目DEN在lev中点。原生垂直交错定义和几何高度名称不能证明外部零面。

当前公开Swarm定义页仍2013；新定义端点403、Handbook页不可读，未绕过。NCAR2.0原生诊断文档可读，但没有提供我们所需的WGS84/GRS80零面等价证据。新检索到的HAO历史邮件PDF候选未能读取，不作为结论依据，也不臆造回复。EXTERNAL_DATUM_UNVERIFIED保持。

一页结论见docs/TIEGCM_ZG_REGISTRATION_STATUS_20261103.md；原NCAR可发送咨询草稿docs/TIEGCM_ZG_EXTERNAL_REGISTRATION_QUESTIONS.md本轮保持原文，未发送。独立模拟的默认下边界不冒充FourCastDEN作者配置。

## 9. 真实轨道准入矩阵

|项目|状态|来源|剩余问题|
|---|---|---|---|
'''
    for row in matrix:text+='|'+'|'.join(row)+'|\n'
    text+='''
这些状态只用于Jan4目标窗。SP3文件及框架解析已通过，不代表精密轨道不确定度、因果初态或受力模型自动合格。DNS是有处理假设的POD密度，不能当作无误差大气观测。当前允许真实参数记录比较、码字/时序和几何单元验证，不允许以未验证A_eff/Cd/推力启动正式轨道精度排名。

## 10. 最关键的三个条件与下一步

1. **实物气动力响应闭环（最高物理影响，中高解决成本）**：确认0601四元数/ORB定义，取得完整几何或经认证气动力查表，匹配GSI、表面/环境参数和参考面积，形成Cd*A/m或完整力系数。质量新数据已取得，但不足以完成这条链。
2. **推力及版本质量码闭环（本窗已有具体风险，优先做的小任务）**：按上述实际AUX输入版本请求机动计划/定标/码表，解释82条dt_thr正值及f_thr全0，冻结事件处理，不按未来SP3残差挑段。已有具体版本和时段，计算成本较低，适合下一轮先实际执行。
3. **外部高度登记（影响密度尺度，计算便宜但依赖维护者证据）**：通过已有NCAR草稿请求版本适用的零面/纬度约定，取得回复后独立验证；不利用同窗观测择优偏移。可与第二项并行准备，但本轮未发送。

下一轮最小建议：先取得0601适用字典及AUXAORBMAN0355、AUXAL1BPC0109、推进器几何/定标的元信息，再决定是否获准下载。预算建议原件≤10MiB（大小未知时先清单/HEAD；超出停止），CPU≤300秒、RSS≤1GiB、输出≤50MiB，不做轨道/训练。目标是生成经版本解释的事件和姿态规则，不再只列未知码。若正式渠道需认证或咨询，应由用户选择渠道，不自动发送邮件。

完整H6还须处理其未验证截断和缺失受力；这些是额外准入，不因本轮辅助数据取得解除。本轮已停止，不自动执行下一阶段。

## 11. 资源、审计与复现

'''
    dr=json.loads((F/'download_complete.json').read_text());ar=json.loads((F/'analysis_resource.json').read_text());text+=f"下载主阶段墙钟{dr['wall_s']:.3f}秒、RSS{dr['peak_RSS_MiB']:.3f}MiB；主分析{ar['wall_s']:.3f}秒、RSS{ar['peak_RSS_MiB']:.3f}MiB；本轮末段绘图/独立核验{audit['wall_s']:.3f}秒、RSS{audit['RSS_MiB']:.3f}MiB。各阶段独立统计，不冒充user/systemCPU时间。{audit['protected_unchanged']}保护资产及{audit['historical_unchanged']}历史资产SHA不变。没有新积分、GPU或TIE。\n"
    text+='''
```bash
source scripts/activate_orbit.sh
python scripts/prepare_swarm_physical_force_v1.py
python scripts/analyze_swarm_physical_force_v1.py
python tests/test_swarm_force_inputs.py
python scripts/finalize_swarm_physical_force_v1.py
```

已完成tag拒绝覆盖，不应直接重放下载/分析；重新执行须独立新tag。只读接口及测试可按原件SHA独立验证。命令、输入/输出/源码SHA及资源见本轮实验目录；五图来源见figure_sources.csv。Git仅同步轻量代码、摘要、图、审计和报告，原产品及逐记录重打包不公开，不强推。
'''
    p=ROOT/'reports/SWARM_PHYSICAL_FORCE_READINESS_V1.md';assert not p.exists();p.write_text(text)
    doc='''# TIE-GCM ZG外部登记：一页状态（2026-11-03）

|关系|已知事实|不能据此证明|
|---|---|---|
|本项目原生变量|实际DEN/ZG按ilev界面；组分和TN在lev；ZGMID可给中点高度|不能将同数组索引混作同高度|
|高度名称|Z是位势高度，ZG是模型几何高度|几何不等于WGS84/GRS80椭球高|
|下边界/重力|已有zbound/calczg及apex源码证据保留|有效重力半径不是正式地球椭球或零面|
|外部观测|DNS使用GRS80，SP3时间/框架与其已对齐|观测之间一致不解决模型ZG零面|
|新增有界检查|NCAR2.0诊断文档再次确认DEN ilev及ZGMID lev；HAO邮件候选不可读|没有新增可放行外部零面证据|

结论：EXTERNAL_DATUM_UNVERIFIED不变。没有重复旧577点或完整沿轨查询，没有调整高度偏移。正式外部接口仍拒绝；PROVISIONAL A/B仅是假设敏感性。

证据：https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/diags.html；完整有界来源表见results/swarm_physical_force_readiness_v1/official_evidence_review.csv。

NCAR草稿复用[原稿](TIEGCM_ZG_EXTERNAL_REGISTRATION_QUESTIONS.md)，仍仅草稿，未发送、无维护者回复。关键待答：地理纬度定义、ZG下边界零面、与GRS80/WGS84的推荐登记方法及精度限制。须区分本项目独立默认下边界与作者2023配置，不以其默认值替代作者证据。
'''
    p=ROOT/'docs/TIEGCM_ZG_REGISTRATION_STATUS_20261103.md';assert not p.exists();p.write_text(doc)
    talk=f'''# 3分钟组会汇报：从数值准确走向真实物理输入

李总，上一轮四组12小时高阶数值闭环已经通过，但那还是在临时高度和合成气动参数下的条件实验。这一轮我们没有再积分，而是实际获取了同一天的Swarm动力学和姿态辅助数据，检查真实卫星受力输入。

我们从ESA取得1月4日两份0601产品，原始压缩文件约6.04MiB。目标12小时内有43200条质量记录和43201条姿态记录。产品报告质量400.712到400.815公斤，比演示400公斤高约0.18%到0.20%。仅替换质量、其他参数固定时，阻力加速度变化也约为这个量级。但质量记录的范围不等于测量不确定度，完整质量码仍需当前版本字典。

最值得重视的新发现是，本窗口有82条推进器开启时长非零记录，同时名义力字段却全是零；姿态产品还有14274条机动码4。我们不能据零名义力宣布没有推力，也不能猜码4的含义。现在已保存具体时间表，并找到了实际处理链使用的机动辅助文件版本，下一步可以有针对性地请求解释。

姿态四元数全都有限，范数非常接近1，但这并不等于已经知道如何旋转。实物说明方向是从本体系到ITRF，可分量顺序和矩阵约定尚未完成版本确认。面积字段是轨道坐标中的三分量截面向量，不能把它的长度直接当迎风面积。Cd也需要几何、表面和大气环境配套，2.2仍然只是演示常数。

工程上，我们已建立可复用接口，研究模式返回原记录、时间、单位、标志和SHA；未知面积、Cd和实际推力明确留空，正式模式会拒绝放行。28项CPU测试通过，其中合成旋转和面元测试只证明程序数学正确，不冒充真实卫星物理验证。

目前最关键的三件事是，完成姿态到几何和气动力的链路，解释推进器与当前质量码，以及确认模型高度零面。下一轮最适合先处理已有具体版本的机动和姿态字典，成本较低，又能直接排除本窗口的推力混淆。真实Swarm轨道精度实验仍然阻塞，本轮不自动追加轨道或训练。
'''
    p=ROOT/'reports/SWARM_PHYSICAL_FORCE_READINESS_V1_TALK.md';assert not p.exists();p.write_text(talk)
if __name__=='__main__':main()
