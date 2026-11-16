"""Acquisition/coverage report only. No correction coefficients or science scores."""
from pathlib import Path
import sys,json,csv,re,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
from observations.bounded_swarm_acquisition import sha
F=ROOT/'experiments/causal_density_latitude_acquisition_v1'
def write(p,s):
 assert p.resolve().is_relative_to(ROOT)
 with p.open('x') as f:f.write(s)
def mdtable(rows,keys):return '|'+ '|'.join(keys)+'|\n|'+'|'.join(['---']*len(keys))+'|\n'+'\n'.join('|'+ '|'.join(str(r[k]) for k in keys)+'|' for r in rows)+'\n'
def main():
 result=json.loads((F/'result.json').read_text());ind=json.loads((F/'supervised_independent_verification.json').read_text());assert result['state']=='COMPLETE' and ind['PASS'];download=json.loads((F/'download_manifest.json').read_text());model=list(csv.DictReader((F/'model_coverage.csv').open()));quality=list(csv.DictReader((F/'quality_audit.csv').open()));counts=list(csv.DictReader((F/'latitude_window_counts.csv').open()));contracts=json.loads((F/'CDF_contracts.json').read_text());stages={}
 for n in ['logs/worker/status.json','logs/local_verify/status.json','logs/final_audit/status.json']:stages[n]=json.loads((F/n).read_text())
 assert stages['logs/final_audit/status.json']['qualification']=='PASS' and stages['logs/final_audit/status.json']['returncode']==0
 tests=[]
 for name in ['latitude_acquisition_v1_transport_tests.log','latitude_acquisition_v1_transport_tests_v2.log','latitude_acquisition_v1_quality_tests.log','latitude_acquisition_v1_hourly_tests.log','latitude_acquisition_v1_native_tests.log']:
  text=(ROOT/'logs'/name).read_text();m=re.search(r'Ran (\d+) tests in ([\d.]+)s',text);assert text.strip().endswith('OK');tests.append(dict(log=name,tests=int(m[1]),wall_s=float(m[2]),superseded=name=='latitude_acquisition_v1_transport_tests.log'))
 measured=sum(v['elapsed_s'] for v in stages.values())+json.loads((F/'independent_verification.json').read_text())['wall_s']+sum(t['wall_s'] for t in tests);peak=max(v['peak_sampled_tree_rss_bytes'] for v in stages.values());outputs=sum(p.stat().st_size for p in F.rglob('*') if p.is_file());assert measured<600 and peak<4*2**30 and outputs<150*2**20;assert download['actual_network_body_bytes']==279668<2**20 and download['verified_extracted_bytes']==388878<2*2**20
 resource=dict(measured_core_task_wall_sum_s=measured,definition='Sum of both acquisition/local-verification supervisors INCLUDING failed qualification records, final successful supervised audit, initial standalone independent audit and all5 test-suite invocations; preparation/interactive file/report commands not individually timed; not total conversation elapsed time',stages={n:{k:s.get(k) for k in ['returncode','qualification','stop_reason','elapsed_s','peak_sampled_tree_rss_bytes','cleanup_verified']} for n,s in stages.items()},peak_sampled_tree_RSS_MiB=peak/2**20,worker_peak_rusage_MiB=result['peak_RSS_MiB'],RSS_definition='sampled launched same-UID session, not guaranteed continuous global peak',network_actual_body_bytes=279668,extracted_verified_bytes=388878,raw_directory_bytes=668546,public_and_local_audit_directory_bytes_before_report=outputs,raw_metadata_downloads=0,HTTP_product_requests=2,network_retries=0,offline_validation_resume_requests=0,tests=tests,distinct_current_tests=52,test_executions_including_superseded_suite=63,correction_fits=0,future_error_scores=0,joint_assessments=0,GPU=0,TIE=0,DART=0,orbit=0,limits=dict(network_bytes=2**20,extract_bytes=2*2**20,CPU_wall_s=600,RSS_GiB=4,public_output_MiB=150))
 write(F/'resource_audit.json',json.dumps(resource,indent=2)+'\n')
 ziprows=[];memberrows=[]
 for prod in download['products']:
  ziprows.append(dict(year=prod['year'],bytes=prod['bytes'],SHA256=prod['SHA256'],HTTP=prod['HTTP'],ContentLength=prod['Content_Length'],ZIP_CRC='PASS'))
  for x in prod['extracted_members']:memberrows.append(dict(year=prod['year'],member=Path(x['path']).suffix,bytes=x['bytes'],ZIP_CRC32=x['CRC32'],SHA256=x['SHA256']))
 qrows=[dict(year=x['year'],records=x['records'],flag0=x['flag0'],flag1=x['flag1'],unknown=x['unknown_flags'],invalid_density=x['invalid_density'],invalid_coords=x['invalid_coordinates'],valid=x['valid_samples']) for x in quality]
 history=[]
 for y in ['2021','2022']:history.append(dict(year=y,all=next(x['valid_N'] for x in counts if x['year']==y and x['window']=='history15_18' and x['region']=='all'),**{r:next(x['valid_N'] for x in counts if x['year']==y and x['window']=='history15_18' and x['region']==r) for r in ['low','mid','high']}))
 modelrows=[dict(year=x['year'],case=x['case'],role=x['role'],frames=x['static_target_frames'],queries=x['total_queries'],success=x['successful'],failures=x['failed'],eight_columns=x['eight_column_complete'],status=x['status']) for x in model]
 report='''# v13-A：独立日期观测获取与目标日模型覆盖预检

2026-11-16。`CAUSAL_DENSITY_LATITUDE_ACQUISITION=COMPLETE`，`CAUSAL_DENSITY_LATITUDE=READY_FOR_V13_PROTOCOL_FREEZE`。**只完成数据/质量/覆盖门禁，不是纬度算法实验完成或科学收益PASS。未拟合任何系数、未计算RMSE/relativeRMS/联合评价。**

身份：PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED。只读保留原`experiments/causal_density_latitude_v1/`全部阻碍审计；其原状态不重写。新证据和当前状态写入本轮新目录与STATUS/WORKLOG。

## 1. 缓存记录和实际网络获取分别记录

本轮之前两目标只在旧ESA listing缓存中列示，目标ZIP/CDF/HDR不在本地。本轮明确授权后，只请求指定两日A0301 ZIP：HTTPS默认证书/主机校验，25秒超时，实际HTTP200、最终仍为swarm-diss.eo.esa.int，Content-Length及流式实收都与冻结大小一致。没有账号、Cookie、凭据；没有下载完整1.45MB目录或B/C/其他日期。旧元数据从SHA核验的本地HAPI及已提交official_service_contract复用，元数据新增网络下载0。

'''+mdtable(ziprows,list(ziprows[0]))+'''
实际应用层响应体合计279668字节，非缓存估计；原始下载预算1MiB。完整URL/始末时间/HTTP/TLS/大小/SHA见download_manifest.json。失败HTTP/HTML/大小变化/非官方跳转都会停止，无自动网络重试。

## 2. ZIP安全与原件完整性

两ZIP都以PK本地文件头及zipfile.testzip()==None验证。每个恰有同stem的CDF和HDR，无目录、绝对/穿越路径、符号链接、重复成员或加密。先检查聚合解压体积，再流式写独占临时文件，校验CRC/SHA后以同目录硬链接原子发布最终路径、删除临时文件；已有文件拒绝覆盖或独立验证复用。

全部CDF/HDR合计388878字节，小于2MiB。两ZIP加解压原件共668546字节，仅本地保存且.gitignore确认保护。

'''+mdtable(memberrows,list(memberrows[0]))+'''
ZIP没有单独一个“整体CRC”字段；上表是成员CRC-32，两档archive CRC检查均PASS。CDF还与HDR中Tot_Size精确一致。

## 3. CDF/HDR独立质量验证

两CDF均2880条；UTC00:00:00—23:59:30，严格30秒，无缺失/重复/倒序。time数据类型CDF_EPOCH，TIME SYSTEM=UTC；TITLE、文件stem、HDR File_Name/File_Type=DNSAPOD_2_/Mission=Swarm/File_Version0301一致，确认A产品。瞬时density单位kg/m3，纬经度deg、高度m，未以density_orbitmean替代。GRS80来自已验SHA的官方服务合同，未据此解除模型ZG门禁。

'''+mdtable(qrows,list(qrows[0]))+'''
质量由原quality_mask精确flag0/1/未知码规则以及有限正密度/坐标界限计算，非假定。坐标约束abs(lat)<=90、abs(lon)<=180、0<h<2000km；异常只拒绝、不补0。2021实际高度431.540—461.531km，2022为425.309—454.802km。

两套读取入口结果一致；原始CDF直接epoch解析与独立5760条记录/坐标/flag复核通过。完整选择的产品单位和时间合同保存在CDF_contracts.json。

## 4. 分区样本量，只计数不拟合

历史窗口[15,18)：

'''+mdtable(history,list(history[0]))+'''
各区都达到30条门槛，无UNSUPPORTED_INSUFFICIENT_HISTORY。未来[18,19)、[18,21)、[18,24)各有120/360/720个质量有效记录；逐区数量见latitude_window_counts.csv。这些是相关沿轨样本，不是独立重复实验。没有计算任何b或exp(b)。

## 5. 原模型静态覆盖与真实沿轨覆盖分别验收

复用已生成两年B14主背景、A7/B7控制；A14完全不参与。按历史source_manifest、各组data_audit/run_status/年份inputs核对原NetCDF/source/GPI/inputSHA。真实退出码均0、4NORMAL EXIT、工程PASS。科学多变量验收未由此升级。

实际NetCDF/模型日历和CF时间核对后，每组确有目标日15/16/17/18/19/20/21/22/23及次日00共10帧。末帧真实存在，可支持23:59:30，不外推。DEN/ZG均ilev29×36×72，DEN g/cm3×1000为kg/m3，ZG cm×.01为m。目标帧显式_FillValue/missing_value/NaN/Inf/极大哨兵/DEN非正扫描均0，ZG逐列严格递增。

'''+mdtable(modelrows,list(modelrows[0]))+'''
每组首末有效查询为15:00—23:59:30。每点仍要求两个时间帧×四邻列全部有效，权重0不跳过。垂直log密度、水平密度双线性、时间密度线性均复用成熟算子。6480查询全部成功，无垂直外推，无替代密度；B14最小模型顶高余量约2021 33.667km、2022 94.944km，仅表示**Map-A条件下模型内部覆盖**，不是外部高度误差界。

独立逐条检查6480条缓存的8列和时间包围，并对18固定点直接从原NetCDF列重建模型密度，1e-13相对容差通过；这是数值一致性检查，不是模型对观测预测误差。完整缓存仅本地，不上传。

## 6. 工程异常：保留错误证据，不改原数据或门槛

1. 首次获取任务在两ZIP已下载/CRC验证成功后，错误把HDR的CRC数值当作ZIP/zlib CRC-32，因此中止。原worker真实退出1、failure.json和源快照保留。
2. 独立检查发现HDR数值分别为2091013208/1035431957，精确等于GNU POSIX cksum；ZIP CDF成员CRC-32则为d2325e04/c73622a7。新Python POSIX CRC（含长度）与GNU实现和真实HDR再次一致，ZIP/zlib校验仍单独保留。**这是算法混用修复，不是放宽校验或接受损坏文件。**
3. 后续只读本地验证未重发任何HTTP请求、未修改原件，CDF及全部模型查询通过。但末尾“NO FIT OR ERROR METRICS”的负面陈述含ERROR，触发通用TIE日志解析器误报；进程真实退出0。原local_verify监督资格FAIL/stop_reason及日志均保留，没有改成PASS。
4. 修正未来控制台措辞，另建最终受监督的独立只读审计（无网络/新模型查询），真实退出0、监督PASS、清理成功。最终数据资格基于全部原件CRC/SHA、CDF、模型覆盖及独立审计，而非推测退出码。首次和中间异常未删除。

52项当前测试通过（传输/解压12，质量14，hourly8，native18；初版11测试另保留），涵盖POSIX和ZIP区别、危险成员/跳转/截断/不覆盖与既有数值拒绝。独立审计5760CDF记录、6480缓存、18模型列重建全部通过。

## 7. 资源与执行边界

'''+f"已计量核心任务合计{measured:.3f}秒，包含首次失败、中间资格误报、最终受监督审计、首次独立审计和全部测试调用；峰值采样树RSS{peak/2**20:.3f}MiB，报告前审计目录{outputs/2**20:.3f}MiB。准备/交互文件操作未逐任务计时，不冒称会话自然墙钟或连续全局RSS峰值。网络279668字节、解压388878字节，预算未扩大。\n"+'''
没有系数估计、未来误差/联合指标、科研结论或算法图表。无新TIE/DART/GPU/轨道/训练。原阻碍审计目录全部SHA保持，v10—v12/权重/原物理场不改；公开只含轻量代码、合同、来源、计数、覆盖和审计记录。commands/sha256_manifest提供复核入口，不能盲目重放已有执行目录。

## 8. 是否可继续

两日数据和两年主背景/控制覆盖门槛满足，**具备下一轮正式冻结v13纬度分区协议的数据条件**。本轮没有冻结或执行校正算法。3月23日Stale06系数尚未建立，必须下一轮按同日[03,06)估计并预先冻结，不借用3月24日值。

科学训练False、EXTERNAL_DATUM_UNVERIFIED、Restart一致性FAIL、DART未准入、真实轨道BLOCKED保持。2021A14工程PASS仅敏感性/2022 A14 PARTIAL历史不改。DART条件没有因下载和查询覆盖成功而满足。本轮停止，等待明确指令。
'''
 write(ROOT/'reports/CAUSAL_DENSITY_LATITUDE_ACQUISITION_V1.md',report)
 decision='''# v13-A获取与覆盖：下一轮准入决策

状态：CAUSAL_DENSITY_LATITUDE_ACQUISITION=COMPLETE；CAUSAL_DENSITY_LATITUDE=READY_FOR_V13_PROTOCOL_FREEZE。原v13缺失数据阻碍审计目录不可改写；新状态来自本轮新证据。

## 已具备

两份指定0301ZIP实际取得（合计279668字节），安全解压388878字节，ZIP CRC/SHA、HDR POSIX cksum与独立GNU数值、CDF身份/UTC/2880×30秒/单位/flags和坐标均验证。每年有效2880，历史低/中/高纬2021=123/122/115、2022=119/117/124。两年B14及A7/B7均真实10小时帧、6480查询/八列全有效，物理字段无无效或外推。

## 本轮没有做

没有b、全球/纬区/Stale系数、未来误差、联合评价、密度模型准确性结论或v13算法实验。原监督异常和校验算法混用已透明保留，最终受监督独立审计PASS；没有重试下载、没有改原件、没有放宽门槛。

## 下一轮必须先冻结

等用户明确授权后，沿用既定候选03-23/18Z、三纬区30/60、3h过去/1/3/6h未来、相同估计器和四项联合标准。各区N<30仍UNSUPPORTED，不借全局或其他区补系数。3月23日Stale06尚未计算，只能从同日[03,06)独立估计并在未来评价前冻结。保持A/B控制角色，不用A14补位，不以未来收益更换背景。

所有参数在未来指标前保存，毒化测试必须通过。数据已取得可只读复用，不再下载，不重跑TIE。资源可沿用600秒/4GiB/150MiB候选上限，但需新协议确认；不能把本轮完成等同下一轮自动授权。

DART不准入：RestartFAIL、外部高度、状态/观测算子和误差、合法集合/版本实测/独立验证仍缺；真实轨道BLOCKED、科学训练False与A14历史资格保持。本轮停止。
'''
 write(ROOT/'docs/CAUSAL_DENSITY_LATITUDE_ACQUISITION_NEXT_DECISION_V1.md',decision)
 write(F/'commands.json',json.dumps(dict(environment='source scripts/activate_orbit.sh; CPU subprocess CUDA_VISIBLE_DEVICES empty; project-only cache/temp',executed=['python -m unittest discover -s tests -p test_bounded_swarm_acquisition.py -v (initial11, corrected12 suite)','python scripts/acquire_causal_density_latitude_v1.py prepare','python scripts/launch_latitude_acquisition_v1.py (2 downloads success, additional HDR CRC algorithm assertion stopped)','cksum data/raw/causal_density_latitude_v1/*.cdf','python scripts/verify_local_latitude_acquisition_v1.py (offline; child0 but log-parser negative-wording false positive)','python scripts/audit_latitude_acquisition_result_v1.py','python scripts/confirm_latitude_acquisition_v1.py (final supervised independent PASS)','python -m unittest discover -s tests -p test_observation_feasibility_v1.py -v','python -m unittest discover -s tests -p test_hourly_tiegcm_observation.py -v','python -m unittest discover -s tests -p test_tiegcm_density_provider.py -v','python scripts/finalize_latitude_acquisition_v1.py'],network_requests=2,no_network_retry=True,no_fit_or_science_scores=True,warning='Immutable prior blocked audit and this run files; no blind replay or automatic next experiment'),indent=2)+'\n')
 write(F/'completion_audit.json',json.dumps(dict(acquisition='COMPLETE',latitude='READY_FOR_V13_PROTOCOL_FREEZE',original_blocked_audit_preserved=True,final_supervised_audit_PASS=True,original_worker_returncode=1,offline_verification_returncode=0,offline_verification_original_qualification='FAIL due log false positive, retained',actual_HTTP_products=2,network_bytes=279668,extract_bytes=388878,CDF_records=5760,CDF_valid=5760,model_queries=6480,model_queries_valid=6480,tests_current=52,correction_fits=0,science_error_scores=0,joint_assessments=0,external_datum='EXTERNAL_DATUM_UNVERIFIED',Restart='FAIL',DART='NOT_ADMITTED',real_orbit='BLOCKED',training=False),indent=2)+'\n')
 p=ROOT/'STATUS.md';s=p.read_text();entry='> 最新（2026-11-16，v13-A独立日期数据获取）：CAUSAL_DENSITY_LATITUDE_ACQUISITION=COMPLETE；CAUSAL_DENSITY_LATITUDE=READY_FOR_V13_PROTOCOL_FREEZE。指定2021/2022-03-23 A0301 ZIP已实际HTTP200取得140271/139397字节，总279668<1MiB，解压388878<2MiB；ZIP CRC/SHA、CDF/HDR身份/UTC2880×30秒/单位与质量通过，两日flag0各2880、异常/未知/无效0。历史低/中/高纬2021=123/122/115，2022=119/117/124。两年B14/A7/B7实际15—次日00十帧与6480 Map-A八列查询全通过；52测试、5760CDF/6480缓存/18列重建独立核验通过。HDR CRC误用ZIP算法及监督器负面日志ERROR误报均保留，校正为POSIX/ZIP分开核验后只读续检、最终监督审计PASS，无新网络请求/原件修改。原v13阻碍审计目录SHA不改。没有b、未来误差/联合评价或算法实验；须下一轮明确授权后冻结v13协议，03-23 Stale06仍未建立。报告reports/CAUSAL_DENSITY_LATITUDE_ACQUISITION_V1.md；科学训练False/高度未验证/RestartFAIL/DART未准入/真实轨道BLOCKED/A14历史资格不改。\n\n';p.write_text(s.replace('# 当前状态\n\n','# 当前状态\n\n'+entry,1))
 p=ROOT/'WORKLOG.md';p.write_text(p.read_text()+f'''\n\n## 2026-11-16：v13-A独立日期获取及目标模型覆盖预检\n- 授权范围：仅两份03-23 A0301 ZIP下载≤1MiB、解压≤2MiB、CDF/模型覆盖；无拟合/未来误差/联合评价、TIE/DART/GPU/轨道/训练。起始本地/远端477c6a8...一致；旧experiments/causal_density_latitude_v1全目录SHA保留，不改历史BLOCKED审计。\n- 下载：复用旧缓存精确URL/大小；HTTPS证书+主机、25秒超时、HTTP200/Content-Length/最终官方host、流式计数/ZIP头、独占临时文件与原子不覆盖发布。2021 140271字节SHA74008af3...，2022 139397字节SHA8c7bb8e3...；实际2请求合计279668字节，0元数据新下载/0重试。HAPI原文件SHA17ccced1...与已提交官方合同一致。\n- 归档：ZIP各恰好CDF+HDR，testzip/成员CRC/安全路径/无符号链接重复通过，解压合计388878字节；CDF各191682、HDR各2757。CRC详细见download_manifest/CDF_contracts，原件仅data/raw/causal_density_latitude_v1且Git忽略。\n- 质量：0301 TITLE/HDR身份、CDF_EPOCH/UTC00至23:59:30、2880条严格30秒、density瞬时kg/m3/经纬deg/高度m独立核验。两日flag0各2880，flag1/未知/无效密度/无效坐标0，最终各2880。过去[15,18)低/中/高2021 123/122/115，2022 119/117/124；仅计数、没有b。\n- 模型：原source/GPI/input/NetCDF历史SHA及退出0/4NORMAL EXIT核验，两年B14/A7/B7目标03-23 15—03-24 00真实10帧，DEN/ZG ilev29/单位/填值/有限正性/ZG严格单调通过。6480质量有效Map-A查询全成功，全部八列、无外推；支持末23:59:30。B14最小模型顶高余量33.667/94.944km不是正式高度误差界。\n- 异常真实保留：两ZIP完整后首次worker因把HDR CRC误等同ZIP/zlib CRC而退出1。独立GNU cksum与Python POSIX(含长度)验证HDR2091013208/1035431957，ZIP成员CRC d2325e04/c73622a7单独通过。无下载或解压重试，后续verify-local只读既有SHA原件。该进程实际rc0，却因末尾NO FIT OR ERROR METRICS触发通用TIE日志ERROR误报；其qualificationFAIL/日志保留不改。改未来措辞，最终独立受监督审计rc0/PASS，不重新查询模型、不改原件或质量阈值。\n- 测试：52当前CPU项通过（12传输/安全/CRC、14质量、8hourly、18native），初版11项另留。独立5760CDF、6480查询缓存及18原列重建探针通过，CRC/SHA/HTTP/样本计数再次核验，无科学误差指标。\n- 资源：已计量核心含失败/误报监督和最终审计/独立核验/全部测试合计{measured:.3f}秒，峰值采样RSS{peak/2**20:.3f}MiB，报告前审计目录{outputs/2**20:.3f}MiB；准备与交互文件操作不逐项计时，不冒称对话墙钟/连续RSS峰值。网络/解压/600秒/4GiB/150MiB均未扩张。\n- 交付：reports/CAUSAL_DENSITY_LATITUDE_ACQUISITION_V1.md，docs/CAUSAL_DENSITY_LATITUDE_ACQUISITION_NEXT_DECISION_V1.md，protocol/download/CDF合同/质量/样本计数/model coverage/资源/原始异常/独立审计/命令/SHA。状态获取COMPLETE，纬度任务READY_FOR_V13_PROTOCOL_FREEZE；算法未执行，等待下一轮，不自动算Stale06/局地b或任何未来误差。科学训练False、EXTERNAL_DATUM_UNVERIFIED、RestartFAIL、DART未准入、真实轨道BLOCKED与两年A14资格保持。Git仅轻量审计，实际同步以远端HEAD独立核验为准。\n''')
 print('ACQUISITION REPORT AND STATE COMPLETE; WAIT FOR NEXT TASK',flush=True)
if __name__=='__main__':main()
