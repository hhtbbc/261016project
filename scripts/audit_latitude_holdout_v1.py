"""Local-only acquisition gate. Never downloads, fits, queries a model or evaluates."""
from pathlib import Path
import os,json,csv,time,resource,hashlib,datetime,urllib.parse
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/causal_density_latitude_v1'
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def write(p,s):
 assert p.resolve().is_relative_to(ROOT)
 with p.open('x') as f:f.write(s)
def main():
 start=time.perf_counter();assert Path.cwd().resolve()==ROOT and not F.exists();F.mkdir();context={};protected={}
 for n in ['AGENTS.md','STATUS.md','WORKLOG.md','reports/CAUSAL_DENSITY_CORRECTION_PILOT_V1.md','reports/CROSS_YEAR_CAUSAL_DENSITY_VALIDATION_V1.md','reports/CAUSAL_DENSITY_LATE_DAY_VALIDATION_V1.md','docs/CAUSAL_DENSITY_LATE_DAY_NEXT_DECISION_V1.md']:
  text=(ROOT/n).read_text();context[n]=dict(bytes=len(text.encode()),SHA256=sha(ROOT/n))
 prior=json.loads((ROOT/'experiments/causal_density_late_day_v1/sha256_manifest.json').read_text())
 for n,h in prior['public_files_SHA256'].items():assert sha(ROOT/n)==h,n;protected[n]=h
 stems={y:f'SW_OPER_DNSAPOD_2__{y}0323T000000_{y}0323T235930_0301' for y in [2021,2022]};found={y:[] for y in stems};count=0;linkdirs=[]
 for base,dirs,files in os.walk(ROOT,followlinks=False):
  for d in dirs:
   p=Path(base)/d
   if p.is_symlink():linkdirs.append(str(p.relative_to(ROOT)))
  for n in files:
   count+=1
   for y,stem in stems.items():
    if n.lower() in {stem.lower()+s for s in ['.zip','.cdf','.hdr']}:
     p=Path(base)/n;assert p.resolve().is_relative_to(ROOT),p;found[y].append(str(p.relative_to(ROOT)))
 # Explicitly record directory symlinks; inspect only project-contained targets.
 for rel in linkdirs:
  p=ROOT/rel
  if p.resolve().is_relative_to(ROOT):continue # target is already scanned in root traversal
  # No outside project reads; any target cannot be accepted as a legal project input.
  pass
 rows=[];receipts=[];total=0
 for y,stem in stems.items():
  tag='swarm_tiegcm_2021_spinup_observation_v1' if y==2021 else 'swarm_tiegcm_2022_observation_v1';listing=ROOT/'data/raw'/tag/'listing.json';receipt=json.loads((ROOT/'experiments'/tag/'downloads.json').read_text())['listing'];assert sha(listing)==receipt['SHA256'];protected[str(listing.relative_to(ROOT))]=receipt['SHA256'];protected[str((ROOT/'experiments'/tag/'downloads.json').relative_to(ROOT))]=sha(ROOT/'experiments'/tag/'downloads.json')
  items=json.loads(listing.read_text())['results'];matches=[x for x in items if x['name']==stem+'.ZIP'];assert len(matches)==1;item=matches[0];assert item['is_readable'] and not item['is_dir'];total+=item['size'];receipts.append(dict(year=y,cached_listing_source=receipt,item=item))
  cdf=[p for p in found[y] if p.lower().endswith('.cdf')];zipf=[p for p in found[y] if p.lower().endswith('.zip')];hdr=[p for p in found[y] if p.lower().endswith('.hdr')]
  rows.append(dict(date=f'{y}-03-23',satellite='A',product_id='SW_OPER_DNSAPOD_2_',product_version='0301',expected_stem=stem,listed_product=item['name'],official_path=item['path'],cached_ZIP_bytes=item['size'],listing_SHA256=receipt['SHA256'],listing_receipt_HTTP=receipt['HTTP'],cached_listing_confirms_product=True,live_server_rechecked=False,local_ZIP=';'.join(zipf) or 'MISSING',local_CDF=';'.join(cdf) or 'MISSING',local_HDR=';'.join(hdr) or 'MISSING',CDF_SHA256='NOT_AVAILABLE' if not cdf else sha(ROOT/cdf[0]),UTC_coverage='NOT_VERIFIED_NO_CDF',record_count='NOT_VERIFIED_NO_CDF',cadence='NOT_VERIFIED_NO_CDF',density_units='NOT_VERIFIED_NO_CDF',quality_flag_distribution='NOT_VERIFIED_NO_CDF',latitude_longitude_height='NOT_VERIFIED_NO_CDF',status='BLOCKED_MISSING_HOLDOUT_OBSERVATION' if not cdf else 'PRESENT_REQUIRES_CDF_AUDIT'))
 assert all(x['local_CDF']=='MISSING' and x['local_ZIP']=='MISSING' and x['local_HDR']=='MISSING' for x in rows),'Unexpected acquired product: stop this audit; do not fit automatically'
 with (F/'candidate_holdout_audit.csv').open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 write(F/'source_manifest.json',json.dumps(dict(context=context,protected_inputs=protected,cached_official_receipts=receipts,workspace_filename_scan=dict(files=count,follow_symlink_directories=False,symlink_directories=linkdirs,target_matches=found),observation_index='results/thermosphere_observation_assimilation_feasibility_v1/observation_file_index.csv'),indent=2)+'\n')
 state='BLOCKED_MISSING_HOLDOUT_OBSERVATION';wall=time.perf_counter()-start
 write(F/'preflight.json',json.dumps(dict(state=state,observation_gate_PASS=False,missing_dates=['2021-03-23','2022-03-23'],both_official_products_in_cached_listing=True,current_official_availability='NOT_RECHECKED',target_CDFs_found=0,target_ZIPs_found=0,target_HDRs_found=0,known_Mar24_data_not_substituted=True,TIE_target_day_static_or_eight_column_gate='NOT_RUN: stopped at earlier observation gate; do not infer PASS from March24 audit',phase2_protocol_frozen=False,correction_parameters_computed=0,model_density_queries=0,future_metric_evaluations=0,figures_generated=0,new_observation_download_bytes=0,wall_s=wall),indent=2)+'\n')
 request='''# v13独立日期观测获取申请（未执行）

2026-11-16。两年目标CDF/ZIP/HDR均不在本地；已有官方目录缓存能确认其曾列示，未联网复查当前可用性。**本轮下载量0，拟合/评价0，按用户门禁停止。**

|日期|精确ZIP产品|缓存大小 bytes|
|---|---|---:|
'''+''.join(f"|{x['date']}|{x['listed_product']}|{x['cached_ZIP_bytes']}|\n" for x in rows)+f'''\n两ZIP缓存合计 **{total}字节（{total/2**20:.6f}MiB）**。这是目录记录值，不是当前实测下载量或解压体积。

## 官方路径与本地缺口

'''+''.join(f"- `{x['official_path']}`\n  预期本地原件：`data/raw/causal_density_latitude_v1/{x['listed_product']}`，解压后同stem的`.cdf`和`.HDR`；三者均缺。\n  未来授权后可用官方HTTPS入口：[产品下载](https://swarm-diss.eo.esa.int/?do=download&file={urllib.parse.quote(x['official_path'],safe='')})。本轮未发起请求。\n" for x in rows)+'''
## 建议下一轮最小授权

只申请以上两日Swarm A0301 ZIP及必要小元数据，新增原始下载上限建议1MiB（不重新拉取整份约1.45MB目录）；若官方大小/版本变化或文件超预算则停止。解压安全预算建议2MiB，不能写出项目。下载后记录HTTP来源、实际大小、ZIP CRC、所有成员SHA，CDF读取前核验SHA与产品身份。不得下载B/C或改变日期。

两CDF均须独立验证UTC00:00—23:59:30、2880记录/30秒、字段和原始单位、flag分布及有效性；上述只是目标条件，当前没有实测值。只有两日均合格，才能继续候选日期原NetCDF SHA/15—24Z/次日00边界/显式填值/八列覆盖预检，再冻结v13协议。

**3月23日的Stale06尚无冻结系数。** 不可使用3月24日v10/v11系数冒充；应在同日全天观测取得后，仅用3月23日[03,06)估计并在18Z评价前冻结。区域[15,18)N<30必须UNSUPPORTED，不能借其他区域或全局填补。

本申请不是下载授权，不启动下载、拟合、查询或评价。等待用户明确批准后继续同一数据门禁；不得把本轮BLOCKED记录改为已经完成。
'''
 write(F/'data_acquisition_request.md',request)
 write(F/'resource_audit.json',json.dumps(dict(local_audit_wall_s=wall,process_peak_rusage_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,definition='single local audit process; interactive checks and Git network time not individually counted',workspace_files_examined=count,output_bytes_before_final_docs=sum(p.stat().st_size for p in F.rglob('*') if p.is_file()),new_download_bytes=0,model_queries=0,fits=0,future_evaluations=0,GPU=0,TIE=0,DART=0,orbit=0),indent=2)+'\n')
 write(F/'commands.json',json.dumps(dict(workspace=str(ROOT),environment='source scripts/activate_orbit.sh',executed=['pwd','realpath .','git status --short --branch','git log -1 --oneline','git ls-remote origin refs/heads/main',"rg --files --hidden --no-ignore /workspace/data/20261016 | rg 'SW_OPER_DNSAPOD_2__202(1|2)0323'",'python scripts/audit_latitude_holdout_v1.py'],not_executed=['download','CDF target-day parsing (absent)','NetCDF target-day query','protocol freeze phase2','fit','future metrics','plots'],rerun_warning='Immutable audit folder; new authorization requires explicit continuation record, never overwrite this blocked audit'),indent=2)+'\n')
 report='''# v13纬度分区校正：独立日期观测门禁审计（未运行实验）

状态：`CAUSAL_DENSITY_LATITUDE=BLOCKED_MISSING_HOLDOUT_OBSERVATION`。本轮没有生成局地/全局/Stale系数、误差指标、联合通过率或科研图。

## 已核实

- 起始本地与远端main均b3e4fc1a31dbc5a6c674be8915e3dd356ce74bbc。
- v10/v11/v12及下一阶段计划已读取；v12公开产物SHA保持。历史未跟踪同步日志不覆盖。
- 全工作区文件名扫描没有找到两年3月23日目标0301 ZIP/CDF/HDR；已检查用户指定raw目录。
- 两份旧listing.json的SHA与各自历史HTTP200下载凭证精确匹配；它们列出目标两产品及官方路径。这里只证明**已有官方目录缓存中的存在记录**，未联网确认当前存在性，不把缓存大小当新下载实测。
- 目标CDF未取得，不能核验其UTC、采样、单位、flag、经纬高、2880有效记录或生成CDF SHA。3月24日数据不是3月23日的替代。

## 当前缺口

'''+''.join(f"- {x['date']}：`{x['listed_product']}`，缓存ZIP{x['cached_ZIP_bytes']}字节；CDF/HDR及ZIP本地均缺。\n" for x in rows)+'''
## 停止边界

按本轮2.2条款，观察数据门禁失败后即停止，不进入第二阶段冻结，不对原NetCDF做目标日查询或拟合/评价。不自动换日期、不下载，不使用2023场。模型记录提示候选日可能覆盖，但本轮**未完成其目标日24Z/字段/8列沿轨验收，不能写PASS**。

预定三纬区边界/中位数/联合四标准仅保留用户设计，尚未冻结执行；无校正参数可回答局地收益。本轮A—H科学问题全部NOT_EVALUATED；DART仍NOT_ADMITTED，RestartFAIL、外部高度未验证、科学训练False、真实轨道BLOCKED、2021/2022 A14历史资格不改。

## 交付和下一步

实际交付为preflight、candidate_holdout_audit、source_manifest、data_acquisition_request、resource/commands/SHA及本阻碍报告。不存在frozen_protocol、correction_parameters、metrics或图表，避免用空壳/合成数据冒充验证结果。

待用户授权仅取得两日A产品，完成SHA/CRC/CDF质量，再做模型门禁及协议冻结。区域N不足30仍拒绝，3月23日Stale06不得借用3月24日系数。具体预算和来源见实验目录data_acquisition_request.md。历史数据/代码/结果不改。
'''
 write(ROOT/'reports/CAUSAL_DENSITY_LATITUDE_VALIDATION_V1.md',report)
 decision='''# v13纬度分区校正：数据准入决策

状态BLOCKED_MISSING_HOLDOUT_OBSERVATION；未进入实验，不是方法收益FAIL。

两年3月23日官方0301产品在已验SHA的本地官方目录缓存中列示，但实际ZIP/CDF/HDR均缺。两ZIP缓存合计279668字节；本轮无下载授权，已停止，未运行拟合、未来评价或图表。

下一步只申请这两日A原件（建议新增ZIP总量≤1MiB，安全解压≤2MiB，大小/版本异常即停），详见`experiments/causal_density_latitude_v1/data_acquisition_request.md`。不是申请新模型积分。授权后先补数据、独立CDF质量验证，再检查B14/可选控制目标日模型24Z和八列覆盖，通过后才冻结纬度协议。

3月23日[03,06)的Stale06尚未拟合，不可用3月24日系数替代。所有区域N≥30及unsupported不填补规则不改。当前不能判断局地是否改进低纬、尾部或联合指标，不能借v12常数结果代替局地实测。

科学训练False、EXTERNAL_DATUM_UNVERIFIED、RestartFAIL、DART未准入、真实轨道BLOCKED、2021 A14工程PASS仅敏感性/2022 PARTIAL保留。等待用户下载授权，不自动继续。
'''
 write(ROOT/'docs/CAUSAL_DENSITY_LATITUDE_NEXT_DECISION_V1.md',decision)
 print('OBSERVATION GATE BLOCKED; cached ZIP bytes',total,'workspace files',count,'wall_s',wall,flush=True)
if __name__=='__main__':main()
