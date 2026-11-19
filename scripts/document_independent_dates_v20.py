"""Render and independently check offline V20 planning receipts; no new experiment."""
from pathlib import Path
import sys,json,csv,datetime,math,subprocess
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src')]
from evaluation.independent_date_planning import CANDIDATES
F=R/'experiments/thermosphere_independent_date_validation_plan_v20'
def load(p):return json.loads(Path(p).read_text())
def rows(p):return list(csv.DictReader(Path(p).open()))
def sha(p):
 import hashlib
 return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(n,v):
 with (F/n).open('x') as f:json.dump(v,f,indent=2,allow_nan=False)
def table(n,rr):
 with (F/n).open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rr[0]),lineterminator='\n');w.writeheader();w.writerows(rr)
def md(header,rr):return '| '+' | '.join(header)+' |\n| '+' | '.join(['---']*len(header))+' |\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rr)+'\n'
def main():
 obs=rows(F/'observation_data_requirements.csv');dr=rows(F/'driver_requirements.csv');activity=rows(F/'activity_conditions.csv');cost=rows(F/'resource_requirements.csv');inventory=rows(F/'existing_model_inventory_updated.csv');initial=load(F/'initial_field_and_configuration_audit.json');protocol=load(F/'preregistered_protocol.json');core=protocol['fixed_scientific_core'];base=load(R/'experiments/tiegcm_2022_mar25_preparation_v1/frozen_evaluation_protocol.json')
 assert all(base[k]==v for k,v in core.items());assert [x['date'] for x in dr]==[x[2] for x in CANDIDATES]
 # Independent date/count and cost arithmetic; no density arrays or new GPI.
 for row in dr:
  day=datetime.date.fromisoformat(row['date']);a=day-datetime.timedelta(days=14);b=day+datetime.timedelta(days=2);lo=a-datetime.timedelta(days=2);hi=b+datetime.timedelta(days=2)
  assert str(a)==row['start'] and str(b)==row['stop'] and (b-a).days*86400//60==int(row['steps'])==23040
  assert (hi-lo).days+1==21 and (hi-lo).days*8+8==int(row['Kp_buckets'])==168
  assert str(lo-datetime.timedelta(days=40))==row['solar_start'] and str(hi+datetime.timedelta(days=40))==row['solar_stop'];assert int(row['Fobs_days'])==101
 evidence=load(F/'resource_estimation_evidence.json')['historical_runs']
 for x in cost:
  count=int(x['runs']);estimate=[e['wall_s']/e['steps']*23040 for e in evidence];vol=[e['output_bytes']/e['days']*16 for e in evidence]
  assert math.isclose(float(x['total_wall_s_min']),min(estimate)*count,rel_tol=1e-13,abs_tol=0);assert math.isclose(float(x['total_wall_s_max']),max(estimate)*count,rel_tol=1e-13,abs_tol=0);assert math.isclose(float(x['total_output_bytes_max']),max(vol)*count,rel_tol=1e-13,abs_tol=0)
 # Directly check cached year values and driver-gap assertions using the documented column contract.
 archive={}
 for line in (R/'data/raw/f107_2021_recovery_v1/gfz_year.txt').read_text().splitlines():
  a=line.split()
  if a and a[0]=='2021':archive[datetime.date(*map(int,a[:3]))]=a
 assert float(archive[datetime.date(2021,5,9)][25])==-1 and float(archive[datetime.date(2021,6,16)][25])==-1
 for x in activity:
  d=datetime.date.fromisoformat(x['date'])
  if d.year==2021:
   a=archive[d];assert float(x['Fobs_sfu'])==float(a[25]);assert float(x['Kp_max'])==max(map(float,a[7:15])) and a[27]=='2'
 assert next(x for x in dr if x['date']=='2021-06-21')['Fobs_invalid_or_disputed']=='2'
 assert next(x for x in dr if x['date']=='2021-09-23')['status']=='COMPLETE_RAW_NO_GPI_GENERATED'
 assert all(x['local_actual_status']=='NOT_ACQUIRED' and x['quality_status']=='NOT_VERIFIED' for x in obs)
 dates=rows(F/'existing_date_coverage.csv');assert len(dates)==6 and all(x['new_run_needed']=='False' for x in dates);march=next(x for x in dates if x['date']=='2022-03-25');assert 'actual_run' in march['model'] and 'V19' in march['scoring']
 # Final next-task recommendation is based on driver gaps, not density. Original summer draft retained.
 autumn=[x for x in obs if x['season']=='autumn'];request=dict(status='REQUEST_ONLY_NOT_EXECUTED',recommended_packet='AUTUMN_PAIR_DATA_AND_SEED_AUDIT',why='2021autumn raw drivers complete; summer2021 has two invalid official Fobs and cannot currently form a complete pair. This is feasibility ordering, not error-driven date selection.',original_six_dates_and_methods_unchanged=True,summer_draft_retained='next_acquisition_request.json is the reviewed summer alternative, not the final recommended packet',dates=['2021-09-23','2022-09-23'],Swarm=[{k:x[k] for k in ['date','product','cached_bytes','official_download_URL']} for x in autumn],Swarm_total_bytes=sum(int(x['cached_bytes']) for x in autumn),GFZ2021='Reuse cached full2021 archive; no new2021driver download',GFZ2022=dict(Fobs='101daily values2022-07-29 through2022-11-06',Fobs_URL='https://kp.gfz.de/app/json/?start=2022-07-29T00:00:00Z&end=2022-11-06T23:59:59Z&index=Fobs',Kp='168def3h bins2022-09-07 through2022-09-27',Kp_URL='https://kp.gfz.de/app/json/?start=2022-09-07T00:00:00Z&end=2022-09-27T23:59:59Z&index=Kp&status=def'),initial_candidate=dict(file='tiegcm_res5.0_sepeqx_smax_prim.nc',URL='https://download.hao.ucar.edu/pub/tgcm/data/tiegcm2.0/tiegcm_res5.0_sepeqx_smax_prim.nc',size='cached approx16M; actual Content-Length/SHA/native state must be verified',purpose='Acquire/audit only. Does not automatically replace the original mareqx seed or authorize model use.'),requested_network_small_MiB=1,requested_initial_separate_MiB=20,requested_total_network_MiB=21,requested_ZIP_extraction_MiB=2,CPU_s=600,RSS_GiB=4,model_runs=0,GPI_generation=0,density_scores=0,no_other_satellite_or_date=True,stop_on='version/size/source/SHA/CRC/CDF contract/source-clock mismatch; badFobs; no imputation',required_outputs='bounded receipts, CDF quality/window/band counts, raw GFZ101/168 coverage, actual seasonal34-state primary identity and clock, seed-policy proposal. Do not score/model or auto-use seasonal source.')
 put('next_acquisition_request_final.json',request)
 priorities=[dict(execution_acquisition_order=1,pair='autumn2021/22',dates='2021-09-23;2022-09-23',status='DATA_ACQUISITION_RECOMMENDED_NOT_RUN_READY',reason='2021rawdrivers complete;2022drivers small,seasonal source indexed; no observed-density error access'),dict(execution_acquisition_order=2,pair='summer2021/22',dates='2021-06-21;2022-06-21',status='HIGH_SCIENTIFIC_VALUE_BLOCKED_2021_FOBS',reason='Keep original first-review/high seasonal-increment role; resolveMay09/June16 first; summer2022 alone could later be assessed with explicit authorization, not called a complete pair'),dict(execution_acquisition_order=3,pair='winter2021/22',dates='2021-12-21;2022-12-21',status='LATER_DATA_AND_SEED_GATES',reason='Crossyear Fobs support25/97missingdays plus2022Kp168; no need to approve all6runs now')]
 table('execution_priority.csv',priorities)
 put('execution_priority_addendum.json',dict(original_protocol_preserved=True,original_calendar_review_pair_order=['summer','autumn','winter'],data_acquisition_recommendation='autumn pair first because2021summer measured official driver gaps',dates_methods_or_scoring_rules_changed=False,target_density_values_accessed=0,requires_explicit_user_authorization_to_acquire=True,all_pairs_remain_in_registered_panel=True,interpretation='fixed_pair_order in original preregistration is calendar review/reporting order, not permission to run an ineligible summer pair. Physical execution remains subject to new task and frozen actual seed/driver identity.',final_next_request_SHA256=sha(F/'next_acquisition_request_final.json')))
 put('independent_verification.json',dict(PASS=True,scope='offline plan dates/index/coverage/cost/core protocol check, not physics or density validation',candidate_supports_checked=6,resource_batches_checked=3,oldMarch25gap_closed=True,observations_all_index_only=True,seasonal_seed_identity_pending=True,actual_Fobs_missing2021=['2021-05-09','2021-06-16'],original_core_fields_unchanged=len(core),no_new_density_access=True,no_GPI_generation=True))
 oldsup=load(F/'supervision_result.json');sup=load(F/'supervision_importfix.json');put('resource_audit.json',dict(supervised_analysis_wall_s=oldsup['elapsed_s']+sup['elapsed_s'],successful_worker_wall_s=sup['elapsed_s'],initial_static_failure='Wildcard helper import shadowed datetime module, before inventory generation. Fixed to explicit imports and added namespace regression; old logs and empty partial receipt retained.',sampled_peak_tree_RSS_bytes=max(oldsup['peak_sampled_tree_rss_bytes'],sup['peak_sampled_tree_rss_bytes']),test_count=12,test_log_SHA256=sha(R/'logs/v20_planning_tests_final.log'),CPU_user_s=oldsup['children_cpu_user_s']+sup['children_cpu_user_s'],CPU_system_s=oldsup['children_cpu_system_s']+sup['children_cpu_system_s'],wall_budget_s=600,RSS_budget_GiB=4,new_public_limit_MiB=150,density_CDF_values_read=0,large_NetCDF_physical_values_read=0,new_network_download_bytes=0,new_model_runs=0,new_GPI_files=0,new_density_scores=0,new_fits=0,GPU=0,DART=0,orbit=0,OS_strict_isolation_claim=False))
 lines=['# V20：跨季节与太阳/地磁条件独立验证方案',
 '**规划状态：PARTIALLY_READY。六个日期、方法、指标、窗口及操作性地磁分类规则已冻结；观测实物、部分驱动、季节初态身份及其使用政策仍待准入。当前RUN_READY日期为0。本轮没有下载、积分、GPI生成、密度评分或拟合。**',
 '## 1. 今日完成情况：更新已有覆盖，而非重做V16—V19',
 '起始本地和远端main均为05bb7f95e479699e83b04b24d2d438e76c35cb12。V19已正式数值闭环VERIFICATION_CLOSED_PASS，9051检查零失败；V18历史INCONCLUSIVE保留。2022主评分累计联合0/12、单项19/48；2021冻结B14联合1/12。不能把数值闭环当成校正普适科学收益。',
 '2022-03-25的新B14已经完成24480步/18primary/408secondary，工程V17PASS、观测2880点匹配和V18单次评分、V19独立复核。旧计划“缺模型24小时、待下载Mar25观测、建议再跑17天”的三项均已过时；必须停止引用这些内容作为新运行理由。旧计划文件不改，新覆盖表记录关闭状态。',
 md(['日期集合','模型身份','当前数据角色','是否提供新季节检验'],[['2021-03-23/24/25','2021 B14连续17天Mar09—26','已用于开发/日期复现，均非未来holdout','否'],['2022-03-23/24','旧探索性B14连续16天Mar09—25','已用于开发/验证','否'],['2022-03-25','新V16 B14连续17天Mar09—26','额外预注册日期已评价且V19数值闭环','否']]),
 '原23组模型覆盖索引只读复用，仅为新V16目录读取首/末secondary的year/mtime端点；没有重扫大型DEN/ZG数值场。所有现有合格B14成熟日期已用完，预热期不能冒充新的合格验证日；2023 S3/S7或作者AI数据不是该双年份同身份B14。旧A7/B7仍是已使用控制背景，A14历史身份不升级；本轮没有启动新控制组。',
 '三种B14采用相同官方春分smax完整源和已记录物理框架；年驱动不同，新2022运行是独立冷启动执行身份，不是旧输出append或Restart。原共同驱动已在准备阶段核验，本轮不再比较原密度数值，也不宣称旧/新整轨迹逐位相同。多个相邻日期共享连续物理运行，不能算独立模型实现。',
 '## 2. 候选日期、观测和驱动实际缺口',
 '原日历候选保持2021/22夏06-21、秋09-23、冬12-21；两年同季可形成配对。夏冬相对已有3月有更明显季节跨度；秋季仍有新增独立日期价值，但不能替代夏冬覆盖。没有读取任何候选Swarm密度或候选预测误差来调整日期。',
 md(['日期','0301 ZIP缓存字节','实物/质量','Fobs支持缺口','Kp缺口'],[[x['date'],x['cached_bytes'],'未取得/NOT_VERIFIED',next(d['Fobs_invalid_or_disputed']+'个无效、'+d['Fobs_not_acquired']+'天未取得' for d in dr if d['date']==x['date']),next(d['Kp_missing']+'桶' for d in dr if d['date']==x['date'])] for x in obs]),
 '六个产品都存在于SHA验证的ESA Sat_A历史目录缓存，仅能标INDEX_CONFIRMED_ONLY。当前服务器是否仍提供同版本、ZIP实物、CDF质量、UTC连续性和目标窗口均未验证；不能把文件名当成2880条质量有效观测。六ZIP缓存合计838238bytes，夏季两份278951bytes，秋季两份279776bytes；这是缓存精确大小，不是新HTTP Content-Length证明。不得下载完整约1.45MB目录或自动换版本。',
 '复用read_swarm_pod、原0301 quality_mask和GRS80产品合同。后续逐文件核验TLS/HTTP/大小/SHA/ZIP CRC/安全解压、HDR/CDF身份、UTC00—23:59:30/30秒/无重复、瞬时density kg/m³、经纬度/椭球高、flag0/1/未知拒绝、正有限密度与合理坐标；有效数以实际CDF为准。模型端08列全有效/无外推，不能剔除不利误差点。Swarm B/C不进入本批读取。',
 '### 夏季驱动的实质阻碍',
 '2021全年官方GFZ缓存有365日，但Fobs在2021-05-09和2021-06-16为-1。原夏季运行Jun07—23、保留±2日驱动缓冲Jun05—25，需要Apr26—Aug04的101日Fobs和168个def Kp桶。Kp已全，Fobs仅99日有效；Jun16缺测影响全部21个GPI日的中心81日平均，目标Jun21的平均同样缺Jun16。不能只看目标日Fobs=79.1就宣布驱动完整。May09旧未解决问题也不能用常数、Fadj、INT或未审定替代站填补。',
 '2022夏季已有Apr26—May19共24个所需Fobs，缺May20—Aug04共77日及Jun05—25全部168Kp桶。2021秋季101Fobs/168Kp已完整，可只读复用，不需要重下全年表；2022秋季缺101Fobs/168Kp。2021冬季缺2022Jan01—25共25个Fobs；2022冬季缺2022Oct26—2023Jan30共97日，已有2023Jan31—Feb03四日可以复用。所有候选尚未生成新GPI。',
 '## 3. 太阳/地磁条件与因果身份',
 md(['日期','Fobs sfu','中心81日均值 sfu','Kp日最大值','操作性分类'],[[x['date'],x['Fobs_sfu'] or 'UNKNOWN',x['F107A_center81_sfu'] or 'UNKNOWN',x['Kp_max'] or 'UNKNOWN',x['Kp_day_class']] for x in activity]),
 '分类在任何目标密度误差访问前冻结：需要UTC全天8个def Kp桶，最大值≤2记QUIET，≥5记ENHANCED，其余INTERMEDIATE；缺测、未定值或非有限值一律UNKNOWN。这是本研究操作性分层规则，不冒称新的官方磁暴强度定义。2021三日已有可信Kp记录；2022三日没有本地相应桶，不能凭年份或季节猜测。',
 '太阳条件仅报告真实Fobs与中心81日平均连续数值，不凭印象划“高/低太阳活动”，本轮不新增太阳阈值组。太阳分组若另需研究，必须在看新密度误差前另冻结规则。当前六固定日期并不保证提供增强地磁样本；安静/增强对比至少每类2个不同日期且覆盖两年份，否则分组比较N/A，仅保留单日描述，不能从30秒点数虚增证据。不得用未来误差挑替代日期凑组。',
 '驱动仍为GFZ历史Fobs、中心81日平均和def Kp；现有getgpi太阳4日节点插值、Kp3小时中心插值及hpower/ctpoten派生公式不变。HEELIS/GSWM等原设定不变，不加入固定KP/F107/POWER覆盖。真正实时预报时未来Kp及中心平均后40日Fobs并不可知；本方案是HINDCAST物理背景上的因果观测校正，不是已验证的实时未来驱动预报。',
 '## 4. 合法初态及物理场身份门禁',
 '本地合法完整5°smax源为tiegcm_res5.0_mareqx_smax_prim.nc，SHA=a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7，实际2002年DOY80 00:00、34个完整原生状态，历史结构审计STATIC_COMPATIBLE。其内部版本字段tiegcm_trunk，不能把官方2.0支持资产内部字段改写成2.0。该文件不是2021/22真实观测重建初态，也未证明适合夏冬14天调整。',
 '缓存NCAR官方目录确有5°junsol_smax、sepeqx_smax、decsol_smax及climatology文件，约16M，但本地未取得季节源。不能按文件名推断内部记录、SOURCE_START、全部_NM、00:00可选记录、网格或状态合法性。需要后续实际下载只读审查；当前各季节源状态NOT_ACQUIRED/NOT_VERIFIED。',
 '严格区分两项政策：保持原mareqx同SHA可维持初始化因素固定，但季节适应充分性未证；换成官方季节smax可能更匹配季节，却改变原背景初态身份。后者只能作为待审候选，不能静默替换后仍称纯日期单因素。必须在新模型及目标误差访问前获得明确批准，冻结同季两年份相同seed SHA、原生SOURCE_START、配置差异和比较局限。跨季节如用不同源，应分身份报告，不能把全部差异归于季节本身。',
 '可复用TIE-GCM2.0二进制及官方apex/IGRF14覆盖层、5°网格、原GSWM/HEELIS配置。本轮仅静态核验二进制SHA与旧配置相符，不重新编译或启动环境探针。14天是候选预热身份，06/18截点实际14.25/14.75天；不预先证明收敛或取消多变量科学失败。Restart=FAIL，所有方案必须独立完整冷启，不允许伪造时间、重命名源、拼_NM或原输出append。',
 '## 5. 资源、分批执行与执行优先级',
 '每日期16天/23040步/MPI4OMP1，预期17 primary及384 secondary小时记录，通常33个NetCDF文件；目标日后2天结束确保次日00插值边界。夏季运行Jun07—23，秋季Sep09—25，冬季Dec07—23；精确GPI/Fobs支持区间见driver_requirements.csv。',
 md(['规模','积分步数','历史比例墙钟估计','软规划模型时间','CPU核时估计','预计NetCDF','顺序内存预算','输出全预留+20GiB空闲'],[[int(x['runs']),x['total_steps'],f"{float(x['total_wall_s_min'])/60:.2f}—{float(x['total_wall_s_max'])/60:.2f}分钟",f"{float(x['total_soft_planning_s'])/60:.2f}分钟",f"{float(x['CPU_core_hours_total_min']):.2f}—{float(x['CPU_core_hours_total_max']):.2f}",f"{float(x['total_output_bytes_max'])/2**30:.2f}GiB",'16GiB',x['disk_available_if_reserving_all_output_caps_GiB']+'GiB'] for x in cost]),
 '估算依据为历史2021 17天2553.40秒、旧2022 16天2429.79秒和V16新17天2599.23秒；按真实秒/步、字节/天及实际children user+system CPU比例计算。每次16天约40.05—40.77分钟，1.5倍最大历史比例为61.16分钟软规划，不是置信区间或未来保证。单次拟申请硬墙钟4800秒、RSS16GiB、输出5GiB、启动余盘至少25GiB、运行剩余至少20GiB，1次不自动重试；监测预算不是OS严格隔离。顺序执行两日期不需要同时32GiB内存，六日期也不意味着同时96GiB。',
 '模型之外另申请每日期工程验收600秒/RSS4GiB、单次冻结评分600秒/RSS4GiB、独立复核600秒/RSS4GiB，均分阶段授权。历史V17工程22.63秒、V18单评分链11.81秒（独立环节曾失败，不冒称完整成功时长）、V19两段独立复核16.64秒仅作量级依据；新季节必须实测。模型输出预计单次3.14、两次6.28、六次18.84GiB，单次5GiB输出cap与实际预计量分列；驱动小文件、每对约0.27MiB观测ZIP、每个季节额外约16MiB初态及日志空间另计。',
 md(['执行/获取建议','理由','本轮状态'],[['首先：秋季两年份数据与初态审查','2021原驱动完整；2022缺失易明确；避免夏季2021两处已知缺测','需要新授权，只获取/审查'],['保留夏季为高价值目标','季节跨度强，但2021Fobs缺口实质阻碍配对','不强推为最优可运行组'],['后续冬季','需跨年Fobs及季节初态；逐批处理','不一次授权六次模型']]),
 '原协议fixed_pair_order保留夏/秋/冬的日历审查与报告顺序；execution_priority_addendum明确数据可执行性顺序可先申请秋季，不删改任何候选日期/方法，也不依据密度误差择优。秋季是工程更可达的先导配对，科学季节跨度不替代夏冬。若夏季缺口未解决，不自动换日期或宣布双年份夏季结果；任何切换均由下一轮明确任务授权。',
 '## 6. 预注册协议、失败条件与下一轮具体任务',
 'preregistered_protocol.json及SHA收据已冻结可确定核心：B14主背景、原Raw/GlobalAdaptive06/GlobalAdaptive18/LatitudeAdaptive18/Stale06组合、06/18Z、各自过去3小时、未来1/3/6h及非重叠0—1/1—3/3—6h；原GRS80纬度边界30/60°、历史/未来地区最低30条、无fallback、原指标及四项联合无退化判据、先冻结后未来评分、分截点1e20毒化、完全共同ID。逐字段与原准备协议一致，不另造综合分数或IID显著性。V19冻结乘数数值合同及rtol1e-13/atol0保留。',
 '预注册尚未完整的部分为实际观测覆盖/质量、缺失驱动、精确初态身份与其季节使用政策、14天适应科学局限，以及活动样本分组是否有足够支持。故总体PARTIALLY_READY，不标PRE_REGISTRATION_READY或RUN_READY。六新日期密度值均未访问；未来任何日期如被用于算法改进，须永久降级为开发数据，不能继续当独立验证。',
 '三个阶段顺序不可颠倒：①新授权取得缺失观测/官方驱动/季节初态，完成真实性、质量、时间、状态及驱动准入；②另授权一次独立16天连续场，固定初态/驱动/科学配置后才能启动，工程完整验收；③工程PASS后再授权一次按冻结方法的历史系数冻结与未来评分、毒化及独立复核。科学负结果完整保留，不在同一日期调参后重称独立验证。',
 '### 建议下一轮直接授权的最小任务：秋季配对数据获取及初态静态审查',
 '只取得2021-09-23与2022-09-23 Swarm A DNSAPOD0301两份ZIP（缓存279776bytes）、2022-07-29—11-06的101个Fobs和09-07—09-27的168个def Kp桶；2021GFZ全年原表复用不重复下载。小数据网络总cap1MiB、ZIP解压2MiB。另单独允许取得官方5°sepeqx_smax完整初态一个文件，cap20MiB，实际Content-Length不符或超cap即停。合计网络授权cap21MiB，CPU600秒/RSS4GiB。',
 '精确文件名与URL、限制和停止条件见next_acquisition_request_final.json。检查只读34完整主状态、原生记录及00:00时钟、网格、单位、SHA和季节身份；不预设SOURCE_START、不自动采用新源。输出两日CDF质量与窗口/纬区数量、2022驱动完整性、初态政策待审结论。该任务不启动模型、不生成GPI、不计算密度误差。后续是否采用原mareqx或新季节源、是否申请一次2022秋季16天积分，由用户审查新证据后决定。',
 '人工授权事项：新网络数据/初态额度；初态政策及背景身份；数据全通过后的单次物理积分；再后的科学评分。当前授权仅规划，以上均未执行。',
 '## 科学限制与本轮执行记录',
 'Swarm POD密度为反演产品而非无误差真值，且并不独立于POD/SP3信息。Map-A数学/查询自洽不证明ZG外部零面；SOURCE季节适应和14天预热充分性未证。新日期也不自动具备充分统计独立性；日期/种子/驱动必须分身份，密度改善不直接证明轨道改善。SCIENCE_TRAINING_READY=False、EXTERNAL_DATUM_UNVERIFIED、Restart=FAIL、DART=NOT_ADMITTED、REAL_ORBIT=BLOCKED保持。',
 '12项低成本测试通过，覆盖支持日期/跨年、Kp边界与缺失、Fobs不填补、顺序资源、初态时钟、固定候选及导入命名空间。本轮首次静态worker因通配符导入遮蔽datetime而在输出库存前失败，改为显式导入并加回归测试；原0.2996秒失败日志和保护清单保留，成功metadata worker0.4344秒。没有发生模型、下载或评分重试，也没有改历史结果。只读取新V16两个端点文件的year/mtime及初态元数据，DEN/ZG物理数值读取0、候选CDF打开0。资源见resource_audit.json，报告编排为额外轻量CPU。',
 '本轮结束停止；next_acquisition_request.json是夏季审查备选草案，next_acquisition_request_final.json为当前明确推荐任务，不能把两者同时执行。'
 ]
 report=R/'reports/THERMOSPHERE_INDEPENDENT_DATE_VALIDATION_PLAN_V20.md'
 with report.open('x') as f:f.write('\n\n'.join(lines)+'\n')
 with (R/'docs/THERMOSPHERE_V20_NEXT_ACQUISITION_TASK.md').open('x') as f:f.write('# 下一轮：秋季配对小批数据取得及季节初态静态审查\n\n'+lines[lines.index('### 建议下一轮直接授权的最小任务：秋季配对数据获取及初态静态审查')+1]+'\n\n'+lines[lines.index('### 建议下一轮直接授权的最小任务：秋季配对数据获取及初态静态审查')+2]+'\n\n新目录、原件只读、版本0301、来源TLS/HTTP/大小/CRC/SHA、既有质量规则不变。失败保留现场，不补值、不换日期、不下载目录，不启动任何TIE-GCM/GPU/DART/轨道或评分。取得后停止。\n')
 state='''\n\n## 2026-11-19 V20：独立季节/活动条件验证规划\n\nTHERMOSPHERE_INDEPENDENT_DATE_VALIDATION_PLAN_V20=PARTIALLY_READY。确认V19数值闭环，2022累计联合0/12、2021冻结1/12，非方法科学收益PASS。旧2022Mar25缺模型/观测和建议重跑17天已过时，V16—V19身份纳入新6日期已用覆盖矩阵，旧计划不改。六个夏秋冬候选均无目标模型场；Swarm0301仅缓存目录确认，实际CDF均未取得/未验证，未读候选密度。\n\n2021夏季101日Fobs有May09/June16两处-1，168Kp完整但GPI不能生成；2022夏季缺77日Fobs/168Kp。2021秋季101Fobs/168Kp已齐，是优先可执行备选；2022秋季缺101/168。冬季2021/22缺Fobs25/97日，2022Kp缺168。官方目录有junsol/sepeqx/decsol5°smax约16M，但均未取得，不能猜SOURCE_START/34状态；现有mareqx原生2002DOY80合法结构不等于夏冬适用。初态政策待批准，换季节源须显式背景身份，不伪称纯日期因素。\n\n方法/窗口/指标/六日期与Kp操作性分类（全8def桶max<=2安静、>=5增强，其余中间，缺失UNKNOWN）已冻结。太阳指标连续报告；2021Jun21 Kpmax1.333安静，Sep23/Dec21均3.667中间，2022未知；不根据密度选阈值/日期。每次16天23040步预计40.05—40.77分钟、约3.14GiB；两次80.11—81.54分钟/约6.28GiB、顺序RSS预算16GiB，模型每次拟4800秒/5GiB，另分工程/评分/复核授权，不一次跑六组。\n\n下一轮明确建议先授权秋季两份A0301ZIP共279776bytes、2022Fobs101/Kp168及一个官方sepeqx_smax初态（小数据1MiB、初态20MiB，合计21MiB网络cap），只取得并静态验收，不积分/生成GPI/评分。保留夏季高科学价值目标及缺口，不自动切换执行。12CPU测试通过；初次datetime通配符遮蔽已修正，错误日志保留，metadata复跑无物理数值扫描。报告reports/THERMOSPHERE_INDEPENDENT_DATE_VALIDATION_PLAN_V20.md；精确下一任务docs/THERMOSPHERE_V20_NEXT_ACQUISITION_TASK.md和新目录next_acquisition_request_final.json。核心预注册成功但数据/初态身份未闭合，不宣称全方案RUN_READY。旧科学/高度/Restart/DART/真实轨道门禁保持；新下载/积分/GPI/评分/拟合/GPU/DART/轨道均0。本轮停止。\n'''
 for n in ['STATUS.md','WORKLOG.md']:
  with (R/n).open('a') as f:f.write(state)
 for n,h in load(F/'protected_before.json').items():assert sha(R/n)==h,n
 print('V20 PARTIALLY_READY REPORT AND PRECISE NEXT TASK DOCUMENTED',flush=True)
if __name__=='__main__':main()
