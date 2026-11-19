"""Document V21 data checks and the retained initial-source403; no further requests."""
from pathlib import Path
import sys,json,csv,hashlib
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src')]
from observations.bounded_swarm_acquisition import sha
F=R/'experiments/thermosphere_autumn_data_acquisition_v21';V20=R/'experiments/thermosphere_independent_date_validation_plan_v20'
def load(p):return json.loads(Path(p).read_text())
def rows(p):return list(csv.DictReader(Path(p).open()))
def put(n,v):
 with (F/n).open('x') as f:json.dump(v,f,indent=2,allow_nan=False)
def table(n,rr):
 with (F/n).open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rr[0]),lineterminator='\n');w.writeheader();w.writerows(rr)
def md(h,rr):return '| '+' | '.join(h)+' |\n| '+' | '.join(['---']*len(h))+' |\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rr)+'\n'
def main():
 result=load(F/'result.json');sup=load(F/'supervision_result.json');ind=load(F/'independent_verification.json');net=load(F/'network_budget_audit.json');zp=load(F/'ZIP_budget_audit.json');assets=load(F/'download_manifest.json');obs=load(F/'Swarm_audit.json');windows=rows(F/'Swarm_window_latitude_counts.csv');quality=rows(F/'Swarm_quality.csv');activity=rows(F/'activity_conditions.csv');driver=load(F/'driver_completeness.json');receipt=load(F/'initial_http_receipt.json')
 assert sup['returncode']==0 and sup['qualification']=='PASS';assert result['status']=='DATA_PARTIAL' and receipt['requests'][0]['HTTP']==403;assert not (R/'data/raw/thermosphere_autumn_data_acquisition_v21/tiegcm_res5.0_sepeqx_smax_prim.nc').exists();assert all(ind['observations'][y]['PASS'] and ind['drivers'][y]['PASS'] for y in ['2021','2022'])
 assert net['charged_bytes']['small']<=2**20 and net['charged_bytes']['initial']<=20*2**20 and net['total_charged_bytes']<=21*2**20 and zp['verification_and_extraction_decompressed_upper_bound_bytes']<=2*2**20
 initial=dict(status='NOT_ACQUIRED_HTTP403',file='tiegcm_res5.0_sepeqx_smax_prim.nc',HTTP=403,requests=1,automatic_retries=0,same_origin_redirects=0,raw_file_saved=False,SHA256=None,NetCDF_format='NOT_RUN',actual_year_day_mtime='NOT_RUN',SOURCE_START=None,complete_34_states='NOT_RUN',grid_units_values='NOT_RUN',engineering_compatibility='UNKNOWN_NOT_TESTED',scientific_seasonal_sufficiency='UNVERIFIED',not_a_claim_of_missing_or_corrupt_official_file=True,no_fallback_to_mareqx=True,origin_or_route_denial_cause='UNKNOWN; hostname-verified HTTPS request returned403 via existing transport route; no additional probe or alternative source used',evidence_SHA256=sha(F/'initial_http_receipt.json'))
 put('initial_source_admission.json',initial)
 policies=[dict(route='A_mareqx',actual_asset='Existing official5deg mareqx_smax complete primary',source_SHA256='a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7',native_clock='2002 DOY80 00:00 from prior verified source',engineering='Prior structure/grid34state contract and currentSHA available; autumn run not executed',science='Retains March seed identity; does not prove autumn adaptation in14days',paired_year_effect='Use same immutable source for both2021/22 if expressly approved',comparison_to_March='Same seed source, actual seasons/drivers differ; not proof of seasonal convergence',risk='Spring initial condition and source high-solar state may require adjustment; no newrun proves it',decision='USER_POLICY_REQUIRED; no automatic fallback after403'),dict(route='B_sepeqx',actual_asset='Official exact URL requested once; HTTP403; no actualNetCDF',source_SHA256='NOT_ACQUIRED',native_clock='UNKNOWN; never infer from filename',engineering='UNKNOWN; 34states/time/grid/units not tested',science='Potential season-appropriate source rationale only, cannot claim scientifically preferable without source evidence',paired_year_effect='Same new seedSHA must be frozen for both years if later verified/approved',comparison_to_March='Changes initial-background identity; cannot call a pure date-only factor against March',risk='File version/state/time unknown and14day sufficiency unverified',decision='Obtain legitimate official artifact or authorize later controlled availability review; policy still unapproved')]
 table('seed_policy_comparison.csv',policies)
 put('resource_audit.json',dict(supervised_wall_s=sup['elapsed_s'],worker_wall_s=result['wall_s'],worker_CPU_s=result['CPU_s'],supervised_children_CPU_user_s=sup['children_cpu_user_s'],supervised_children_CPU_system_s=sup['children_cpu_system_s'],sampled_peak_tree_RSS_bytes=sup['peak_sampled_tree_rss_bytes'],worker_peak_self_RSS_KiB=result['peak_self_RSS_KiB'],successful_saved_body_bytes=result['saved_body_bytes'],received_TCP_stream_bytes=net['total_received_bytes'],sent_TCP_stream_bytes=net['total_sent_bytes'],conservative_budget_charged_bytes=net['total_charged_bytes'],small_budget_charged_bytes=net['charged_bytes']['small'],initial_budget_charged_bytes=net['charged_bytes']['initial'],failed_initial_attempt_included=True,ZIP_unique_extracted_bytes=zp['unique_extracted_member_bytes'],ZIP_all_verification_extraction_upper_bound_bytes=zp['verification_and_extraction_decompressed_upper_bound_bytes'],network_limits=dict(small=2**20,initial=20*2**20,total=21*2**20),ZIP_limit=2*2**20,wall_limit=600,RSS_limit_GiB=4,physical_model_runs=0,new_GPI=0,new_scores=0,new_fits=0,GPU=0,DART=0,orbit=0,automatic_file_retries=0,actual_redirects=0,budget_definition=net['definition'],sampling_not_OS_peak_or_packet_guarantee=True))
 put('tests_final.json',dict(PASS=True,unique_targeted_tests=17,rerun_after_static_guard_additions=True,initial_log_SHA256=sha(R/'logs/v21_autumn_tests.log'),final_log_SHA256=sha(R/'logs/v21_autumn_tests_final.log'),tests_are_synthetic_not_seasonal_initial_PASS=True))
 request=dict(status='NEXT_TASK_REQUIRES_USER_DECISION',already_complete='Do not redownload the2Swarm ZIP/CDF/HDR or2022Fobs/Kp; all SHA verified',missing='Official sepeqx_smax original blocked byHTTP403; current SOURCE_START/34states unknown',option1='User obtains the exact official original through a legitimate authorized channel and places it inside the project root, then authorizes read-only SHA/34states/grid/time/units review. No mirror or external correspondence is attempted here.',option2='Explicit later authorization for one bounded official-source availability review/retry after addressing access conditions; retain this403 and no automatic source substitution.',option3='Explicitly approve routeA same mareqx source with autumn adaptation limitations; this is a user policy decision, not an automatic response to403.',after_policy='Prepare new independent16day GPI/config, check exact source identity, drive compatibility and resources, then request one formal integration authorization. Nothing starts from this data task.',model_periods=['2021-09-09T00:00:00Z to2021-09-25T00:00:00Z','2022-09-09T00:00:00Z to2022-09-25T00:00:00Z'],proposed_model_parameters_not_written=dict(STEP_s=60,steps=23040,MPI=4,OMP=1,primary_records=17,secondary_hourly_records=384),new_model_or_GPI_authorized=False)
 put('next_decision.json',request)
 lines=[
 '# V21：2021/2022秋季真实数据获取及季节初态准入审查',
 '**总状态：DATA_PARTIAL。两份Swarm与2022 GFZ原件取得并通过主/独立审查；官方sepeqx初态请求HTTP403，未取得，已停止该文件获取且没有重试。两年份均不是RUN_READY。**',
 '## 1. 今日完成情况及范围',
 '起始本地/远端main均为153c840d77de4c2bc80199765891a9f329aca9ae。严格读取V20 next_acquisition_request_final.json秋季请求，不执行夏季草案。新原件只保存data/raw/thermosphere_autumn_data_acquisition_v21/，新证据位于experiments/thermosphere_autumn_data_acquisition_v21/。V20核心协议SHA保持eb27a080199d656f6018f47834cc9eaef07897009360ca184d6511e4d3aeb2c4。',
 '只发起5个官方指定GET，全部使用默认TLS证书/主机名验证、既有网络路由、无账号/Cookie/凭据；HTTP状态和头在正文写入前审查。4次200成功、1次403；重定向0、文件重试0，未访问镜像或其他日期/卫星。没有启动TIE-GCM/GPU/DART/轨道、没有新GPI、校正拟合或密度评分。',
 '## 2. Swarm原件和质量证据',
 md(['日期','ZIP实际字节','ZIP SHA256','ZIP CRC'],[[y+'-09-23',assets['Swarm'+y]['bytes'],assets['Swarm'+y]['SHA256'],'主/独立testzip和成员CRC通过'] for y in ['2021','2022']]),
 md(['日期','CDF SHA256','记录/有效','flag0/flag1/未知','无效密度/坐标'],[[x['date'],x['source_SHA256'],x['records']+'/'+x['valid'],x['flag0']+'/'+x['flag1']+'/'+x['unknown_flags'],x['invalid_density']+'/'+x['invalid_coordinates']] for x in quality]),
 '两份均UTC00:00:00—23:59:30，CDF_EPOCH，严格30秒2880条，无缺失/重复/倒序。瞬时density为kg/m³，未用density_orbitmean；经纬度deg、椭球高m，复用SHA验证的GRS80 HAPI合同及既有read_swarm_pod/quality_mask。卫星身份由DNSAPOD及HDR明确。两个HDR匹配日期、版本0301和CDF，POSIX cksum分别524889775、3357783377，由Python实现和独立系统cksum交叉验证。所有原始CDF值只用于质量掩码，未计算或展示未来密度范围、均值、趋势或模型残差。',
 '### 全部正式窗口/纬区质量有效数量',
 ]
 windowtable=[]
 for day in ['2021-09-23','2022-09-23']:
  for h in [6,18]:
   for win in ['history','future_1h','future_3h','future_6h']:
    d={x['region']:x['quality_valid'] for x in windows if x['date']==day and x['cutoff']==str(h) and x['window']==win};windowtable.append([day,f'{h:02d}Z',win,d['all'],d['low'],d['mid'],d['high']])
 lines.extend([md(['日期','截点','窗口','全部','低纬','中纬','高纬'],windowtable),
 '区间均左闭右开，06Z历史[03,06)、未来[06,07/09/12)；18Z历史[15,18)、未来[18,19/21/24)。低/中/高按原始GRS80绝对纬度<30、30≤abs<60、≥60。所有区域N均≥30，最小31，未借用系数、删点或更换日期。这里仅证明观测时间/质量支持；没有新季节模型场，所以沿轨模型查询NOT_RUN，不能把观测计数冒充模型覆盖PASS。',
 '## 3. GFZ驱动和太阳/地磁条件',
 '2021只读复用GFZ全年官方缓存，SHA=f969f23b0b0d4aba80dca6f35d3e95c2d35a7e482457bc1812e5c0827090caae，不重下全年数据。2022按正式URL取得Fobs2022-07-29—11-06共101日（3000正文bytes）、def Kp2022-09-07—09-27共168桶（5859正文bytes），两次200。原始JSON/SHA、准确缺口/额外/重复/非法值审查见GFZ2022_raw_contract_audit.json及download_manifest.json，缺口均0。',
 '所有UTC日/三小时桶严格对齐，Fobs为原请求的observed通量而非Fadj，Kp status全部def；无NaN、非法值、重复或替代年份。两年份都支持Sep07—27全部21个GPI日的中心81日平均；NumPy原构造均值与独立math.fsum核对差<1e-12，未放宽原门槛。center81_static_check.csv仅为只读支撑审查，不是新GPI文件。未运行旧builder.main/write_gpi，也没有新驱动NetCDF。',
 md(['日期','Fobs sfu','中心81日均值 sfu','最大def Kp','V20分类'],[[x['date'],x['Fobs_sfu'],x['Fobs_center81_sfu'],x['Kp_max'],x['geomagnetic_class']] for x in activity]),
 '固定规则为完整8def桶max≤2安静、max≥5增强，其余INTERMEDIATE，缺失UNKNOWN。本次两日均INTERMEDIATE，不能包装成安静/扰动对照；不同活动类别最低独立日期数不满足，分类对照N/A。Fobs数值不同不自动等于已构成预注册高/低太阳组。中心81日含未来40日，未来驱动为历史观测，本任务仍为HINDCAST准备而非实时预报驱动。',
 '## 4. 官方秋分smax请求及未完成项目',
 '精确URL：https://download.hao.ucar.edu/pub/tgcm/data/tiegcm2.0/tiegcm_res5.0_sepeqx_smax_prim.nc 。一次GET经主机名验证TLS收到HTTP403；Content-Type=text/html，Content-Length=199，正文未作为NetCDF保存。失败请求已计入网络预算。没有使用其他URL/用户代理重试，没有下载目录、请求认证、发邮件或使用镜像。',
 '403是访问失败，不是文件不存在、损坏或内部状态不兼容的证明。也无法仅凭该响应区分源站权限/WAF/路由策略，未作额外网络探测。初态原文件未取得，所以原始SHA、NetCDF格式、版本、year/day/mtime、真实SOURCE_START、34状态、网格/单位/数值与季节来源均NOT_RUN或UNKNOWN。绝不从sepeqx文件名推断记录日期或伪造新文件。静态检查工具已编写并有小型反例测试，但不冒充真实初态验收。',
 md(['初态路线','当前可证事实','科学与可比性风险','需要用户决定'],[['A：既有mareqx','既有官方5°smax完整34状态、原生2002DOY80 00:00、SHA不变；本轮不重新运行','保持旧源身份，但秋季适应性/14天充分性未证明','是否明确批准这一受限背景；不得因403自动采用'],['B：新sepeqx','官方指定URL请求403；没有实物，无法证明结构兼容','有季节来源设计动机但尚未实物确认；即使取得也改变初态身份，不能与March称纯日期单因素','取得合法原件并审查，再冻结同季两年相同seedSHA与真实SOURCE_START']]),
 '科学建议是先闭合B的官方实物身份再作政策判断；不能宣布B比A更准或工程可用。若用户选择A，应明确这是保留春分源的秋季适应性受限实验；若选择B，同季2021/22必须冻结同一初态SHA，跨季节结果需披露种子变化。两路线均未证明14天预热充分；不使用Restart/append、重标时间或拼接_NM。当前积分配置完全未修改。',
 '## 5. 独立复核、资源和逐年准入',
 '独立程序直接重新读取ZIP/CD F/HDR和原始GFZ，不复制主PASS：两ZIP CRC及成员字节、两个CDF UTC/flag/质量和64条窗口纬区记录通过；系统cksum独立验证HDR；GFZ各101/168、共42个中心均值交叉通过。初态独立检查NOT_ACQUIRED，明确未通过而非全包PASS。V20冻结SHA及全部受保护旧资产不变。',
 '17项不同合成测试通过，含官方HTTPS/请求身份、错误版本/日期、额外ZIP成员、非法路径、预算溢出、失败发送计额、HTTP缓冲接口、缺失/重复/非def驱动、未知质量标志及错误初态/时钟。补充静态守卫后在新fixture目录复跑相同17项，不把重复测试计为34项。',
 md(['计量项','实际字节'],[['成功保存4个HTTP正文',result['saved_body_bytes']],['实际socket接收（含TLS/HTTP/CONNECT及403传输）',net['total_received_bytes']],['实际发送',net['total_sent_bytes']],['保守计额合计（接收+发送）',net['total_charged_bytes']],['小数据保守计额 / 上限',str(net['charged_bytes']['small'])+' / '+str(2**20)],['初态失败保守计额 / 上限',str(net['charged_bytes']['initial'])+' / '+str(20*2**20)],['唯一解压CDF/HDR',zp['unique_extracted_member_bytes']],['含所有真实ZIP CRC验证/解压pass的保守解码量 / 上限',str(zp['verification_and_extraction_decompressed_upper_bound_bytes'])+' / '+str(2*2**20)]]),
 '网络计额不是只用Content-Length：所有本次请求、握手、头、失败403接收与发送都经同一计数层；无重试和重定向。本应用记录实际消耗的TCP字节流，发送也保守计入；IP/TCP包头、协议栈重传无法由此应用精确观测，不冒称OS抓包或网络隔离保证。所有计额远低授权。ZIP上界包含主CRC1次、主提取内CRC/实际提取2次、独立CRC/逐成员读取2次，避免只数最终写盘量。',
 f"唯一获取/静态验收监督墙钟{sup['elapsed_s']:.6f}秒，主worker CPU{result['CPU_s']:.6f}秒；含启动和子进程CPU user/system={sup['children_cpu_user_s']:.6f}/{sup['children_cpu_system_s']:.6f}秒。采样树峰RSS={sup['peak_sampled_tree_rss_bytes']/2**20:.3f}MiB，worker自报峰值={result['peak_self_RSS_KiB']/1024:.3f}MiB，统计定义不同，采样不代表连续峰值。监督退出0仅说明有界获取及PARTIAL结果整理正常结束，不表示初态数据成功或物理模型通过。",
 md(['年份','Swarm质量/窗口','GFZ','季节初态','政策','总状态'],[[y,'通过，2880有效','101/168完整','未取得403','待用户审定','DATA_PARTIAL'] for y in ['2021','2022']]),
 '因此当前还不是DATA_READY_SEED_POLICY_PENDING，更不是RUN_READY：不仅政策待定，指定季节初态实物审查也缺失。未发现已取得Swarm/GFZ的数据质量异常；明确异常是初态HTTP访问拒绝。',
 '## 6. 下一步最小任务和科学门禁',
 '无需重下已通过的Swarm/GFZ。需要用户先决定：①从合法官方渠道人工取得精确sepeqx原件并放在项目根内，再授权只读34状态/时间/网格审查；或②另明确授权未来一次受控官方可获取性复查，保留本次403，不在本轮自动重试；或③明确批准受限路线A。当前不通过镜像/认证或外部联系绕过限制。',
 '源政策审定且输入静态准入后，才能另准备2021/22独立Sep09—25各16天GPI与运行配置，固定STEP60、23040步、MPI4OMP1、17primary/384secondary等；再以新授权决定是否执行一次正式积分。本轮不能直接申请已经RUN_READY的一键积分，也不自动生成GPI。',
 'SCIENCE_TRAINING_READY=False、EXTERNAL_DATUM_UNVERIFIED、Restart=FAIL、DART=NOT_ADMITTED、REAL_ORBIT=BLOCKED全部保持。Swarm POD并非无误差独立真值，Map-A不是正式ZG外部零面登记，两个INTERMEDIATE日期不提供完整活动条件组。取得数据不代表密度、轨道或AI科学资格。本轮整理并同步后停止。',
 '### 领导汇报（300字以内）',
 '两年9月23日Swarm A原件均取得，2880条有效观测及全部历史/未来纬区样本支持检查通过；2022年101日Fobs与168个def Kp桶完整，两日均属中间地磁条件，不能当作安静/扰动对照。官方秋分初态URL返回403，已停止且未重试，因此两年均DATA_PARTIAL，SOURCE_START及34状态尚不能确认。建议先取得合法官方初态并由用户审定A/B政策，再准备GPI和单次16天配置；本轮未积分或评分。'
 ])
 with (R/'reports/THERMOSPHERE_AUTUMN_DATA_ACQUISITION_V21.md').open('x') as f:f.write('\n\n'.join(lines)+'\n')
 with (R/'docs/THERMOSPHERE_V21_SEED_POLICY_NEXT_DECISION.md').open('x') as f:f.write('# V21下一步：官方秋分初态身份和源政策\n\n本轮DATA_PARTIAL：两Swarm及GFZ通过，sepeqx官方URL403停止、无重试。不要重下已通过数据。\n\n请先通过合法官方渠道提供精确初态原件至项目内，或另授权一次受控可获取性复查；本任务不联系外部、不换镜像。取得后只读确认原生year/day/mtime/SOURCE_START、34状态、网格和数值。\n\nA现有mareqx源结构可信但秋季适应未证；B季节动机合理但实物未知，不能宣布更准。需用户明确批准源政策，B改变与March初态身份，同季两年须固定相同SHA。403不自动触发A回退。\n\n源政策及输入审查闭合后，再授权生成GPI和独立16天配置并审查运行资源；真实积分仍另需明确授权。所有科学门禁保留。\n')
 state=f'''\n\n## 2026-11-19 V21：秋季真实数据取得与初态403阻碍\n\nTHERMOSPHERE_AUTUMN_DATA_ACQUISITION_V21=DATA_PARTIAL，两年份均DATA_PARTIAL。两份指定Swarm A0301ZIP实际139634/140142bytes，CRC/HDR/CDF独立通过；各2880条UTC30秒flag0有效，异常/未知/无效密度坐标均0，历史各360、未来1/3/6h各120/360/720，各纬区最小31≥30。仅质量计数，未展示未来密度分布或计算残差/误差。2021原GFZ复用；2022Fobs101日3000bytes、defKp168桶5859bytes完整，21+21中心均值独立通过，未生成GPI。两年Fobs=89.7/146.3，81均值86.94814814814815/131.76666666666668sfu，Kpmax3.667/3.333均INTERMEDIATE，活动分组对比N/A。\n\n官方sepeqx_smax精确URL一次请求返回HTTP403（TLS主机名已验证，html声明199bytes），停止该文件，未重试/换源/认证/镜像/自动使用mareqx。无初态原件与SHA，真实SOURCE_START、34状态、版本/网格/数值均NOT_RUN，不能猜测或声称初态损坏。A/B政策仍需用户审定，当前非RUN_READY。\n\n成功保存正文288635bytes，全部实际TCP接收319773bytes、发送9598bytes，保守计额329371bytes含失败403/TLS/HTTP/CONNECT（小数据320272/1MiB，初态9099/20MiB），未宣称IP层抓包额度。ZIP唯一解压388878bytes，含所有验证/读取pass保守解码1944390<2MiB。17项不同测试通过；监督10.543813秒、workerCPU0.799568秒、采样树峰84.453MiB，退出0意味着PARTIAL处理完成而非全包成功。原V20协议SHA与受保护旧文件不变。\n\n报告reports/THERMOSPHERE_AUTUMN_DATA_ACQUISITION_V21.md；决策docs/THERMOSPHERE_V21_SEED_POLICY_NEXT_DECISION.md；原件仅data/raw/thermosphere_autumn_data_acquisition_v21/。下一步先合法取得并审查初态/政策，不重下已通过数据；未生成GPI/改积分配置/启动模型/评分/拟合/AI/DART/轨道/外部联系。SCIENCE_TRAINING_READY=False/EXTERNAL_DATUM_UNVERIFIED/RestartFAIL/DARTNOT_ADMITTED/REAL_ORBITBLOCKED保持。本轮同步后停止。\n'''
 for n in ['STATUS.md','WORKLOG.md']:
  with (R/n).open('a') as f:f.write(state)
 for n,h in load(F/'preflight.json')['protected_SHA256'].items():assert sha(R/n)==h,n
 print('V21 DATA_PARTIAL DOCUMENTED; NO FURTHER REQUEST OR MODEL',flush=True)
if __name__=='__main__':main()
