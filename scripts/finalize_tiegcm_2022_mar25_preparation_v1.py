"""V14-B lightweight final records; no downloads, model calls or evaluation."""
from pathlib import Path
import json,hashlib,re,subprocess
R=Path(__file__).resolve().parents[1];F=R/'experiments/tiegcm_2022_mar25_preparation_v1'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as s:
  for b in iter(lambda:s.read(2**20),b''):h.update(b)
 return h.hexdigest()
def load(n):return json.loads((F/n).read_text())
def dump(n,x):
 with (F/n).open('x') as s:json.dump(x,s,indent=2,ensure_ascii=False);s.write('\n')
def entry(p):return dict(path=str(p.relative_to(R)),SHA256=sha(p),bytes=p.stat().st_size)
def main():
 assert R==R.resolve() and F.resolve().is_relative_to(R);assert load('independent_verification.json')['PASS'];model=load('model_configuration_manifest.json');build=R/'experiments/tiegcm2_apex2023_v1';inventory=[]
 for name in (build/'Srcfiles').read_text().split():
  p=build/name if (build/name).exists() else R/'third_party/TIEGCM2.0/src'/name;assert p.resolve().is_relative_to(R) and p.is_file();inventory.append(entry(p))
 src=dict(base_release=model['base_release'],apex_update=model['apex_update'],compiled_source_inventory=inventory,compiled_resolution='Make.env DIRS order: build overlay first, original2.0 src second; actual binary unchanged from historical run. Current source hashes are not a new recompilation.',verified_history_manifest=entry(R/'experiments/tiegcm_zg_external_registration_v2/model_configuration_manifest.json'),old_model_and_assets=model['verified_assets'],new_GPI=load('gpi_coverage_audit.json')['GPI'],new_CDF=load('observation_acquisition_audit.json')['CDF'],mpirun=load('environment_audit.json')['mpirun'],preparation_code=[entry(R/n) for n in ['scripts/prepare_tiegcm_2022_mar25_v1.py','scripts/verify_tiegcm_2022_mar25_preparation_v1.py','scripts/execute_tiegcm_2022_mar25_v1.py','scripts/finalize_tiegcm_2022_mar25_preparation_v1.py','tests/test_tiegcm_mar25_preparation.py']],history_protected_files=len(load('protected_assets_local.json')))
 dump('source_manifest.json',src)
 (F/'input.template.inp').open('x').write((F/'run/input.inp').read_text().replace(str(R),'${PROJECT_ROOT}'))
 status=load('logs/preparation/status.json');result=load('preparation_result.json');iv=load('independent_verification.json');test_times={};test_counts={}
 for tag in ['static','supervisor','acquisition','driver']:
  txt=(R/f'logs/mar25_preparation_{tag}_tests.log').read_text();assert txt.rstrip().endswith('OK');hit=re.search(r'Ran (\d+) tests in ([\d.]+)s',txt);test_counts[tag]=int(hit[1]);test_times[tag]=float(hit[2])
 assert sum(test_counts.values())==50
 dump('resource_audit.json',dict(PASS=True,supervised_preparation_wall_s=status['elapsed_s'],worker=result,independent_verification_wall_s=iv['wall_s'],independent_verification_CPU_s=iv['CPU_s'],test_body_times_s=test_times,test_counts=test_counts,measured_compute_wall_s=status['elapsed_s']+iv['wall_s']+sum(test_times.values()),sampled_preparation_tree_peak_bytes=status['peak_sampled_tree_rss_bytes'],limits=dict(wall_s=600,RSS_bytes=4*2**30,network_bytes=2**20,public_bytes=150*2**20),network_download_bytes=139665,driver_download_bytes=0,new_TIEGCM_starts=0,GPU=0,DART=0,orbit=0,correction_fits=0,future_density_metrics=0,scope='Measured CPU test/preparation/verification, not continuous monitoring of editing/Git; nested MPI/helper probe included in preparation'))
 dump('commands.json',dict(completed=['source scripts/activate_tiegcm.sh','PYTHONPATH=project/src:project python -m unittest discover -s tests -p test_tiegcm_mar25_preparation.py -v','Existing test_runtime_supervisor.Supervision via unittest import with BASE redirected to this new experiment/supervisor_tests_local (no old result write)','python -m unittest discover -s tests -p test_bounded_swarm_acquisition.py -v','python -m unittest discover -s tests -p test_tiegcm_training_drivers.py -v','runtime.supervisor supervised python scripts/prepare_tiegcm_2022_mar25_v1.py:550s/4GiB/150MiB','python scripts/verify_tiegcm_2022_mar25_preparation_v1.py','python scripts/finalize_tiegcm_2022_mar25_preparation_v1.py'],test_logs=[f'logs/mar25_preparation_{tag}_tests.log' for tag in test_counts],future_only_NOT_EXECUTED='source scripts/activate_tiegcm.sh; python scripts/execute_tiegcm_2022_mar25_v1.py --authorize-17day-run',future_requires_new_explicit_user_authorization=True))
 report='''# 2022-03-25 TIE-GCM正式运行准备 V14-B

## 结论与执行边界

TIEGCM_2022_MAR25=RUN_READY_NOT_LAUNCHED。仅代表当前静态输入、环境和资源准入，不代表物理科学精度。真实TIE-GCM启动0，校正拟合0，密度评价0，GPU/DART/轨道0。下一轮需要用户明确授权一次17天积分。本轮没有用首小时模型积分替代环境检查。

## 指定真实观测

仅下载2022-03-25 Swarm A DNSAPOD_2 0301 ZIP一次：139665bytes、HTTP200，TLS/官方终点/Content-Length/流式大小检查通过。复用SHA验收的本地ESA listing（目标大小139665），未下载目录或其他观测。ZIP CRC、成员路径/重复/符号链接限制、安全提取、HDR产品身份及POSIX CRC通过；提取194439bytes。

ZIP SHA256：345cddeabe8f315ffc720197660dd6025bfa13e06312a7f807b1bd0d35d1af5a。
CDF SHA256：d2f647f723f774a446e6c07c9b1108c1dc521b76bb21a2d524d321d379b440a8。

CDF为2880条、严格30秒、UTC00:00:00—23:59:30，瞬时density单位kg/m³，GRS80大地坐标产品合同。flag0=2880、flag1=0、未知0，全部2880条通过原quality_mask及坐标质量检查。03—06/06—12/15—18/18—24有效N=360/720/360/720；03—06低中高纬122/113/125，15—18为124/117/119，均满足30门槛。原始数据只保存在项目data/raw目录，不入库；记录本地SHA不等于发布方独立校验和。

## 驱动真实性与新GPI

复用六份已验收GFZ原始JSON；旧builder截取后的集合不代表原始响应覆盖上限。旧2022_Fobs.json实际延伸至05-19，旧2022_Kp.json含03-28，所以扩展所需102天Fobs（01-26—05-07）和176个def Kp桶（03-07—03-28）均已存在，无新增驱动下载、无常数补缺、无插值补缺、无Fadj替代。重复、UTC、正值、有限性、Kp def及三小时桶检查通过。

新gpi_2022_extended.nc为NETCDF3_CLASSIC，22天、176桶，valid03-09—03-26，F107A为完整中心81日Fobs均值。与旧GPI的21天f107d/f107a/kp逐元素完全一致；共同分钟驱动最大差0。24481个注册分钟节点有限且范围合规；独立81日fsum平均最大差2.84217e-14sfu，独立插值最大差1.27898e-13（旧容差1e-10未放宽）。GPI SHA256为5834bf48ebb6d024d5e3e0f8fe407649608699ba5b9091cd61ffdb2eb51223d4。

GPI覆盖核验、共同区间、原始来源路径和SHA分别见driver_source_audit.json、gpi_coverage_audit.json、gpi_common_interval_comparison.json。日期及桶均由独立程序复算。全部是历史hindcast驱动，不等同实时可用预报驱动。

## 模型、初态与唯一配置变化

保持旧2022 B14科学身份：官方TIE-GCM2.0基础commit da712811d925376ff8ef40ff64bda7cc070ca661；官方apex更新commit 84185ee0b97307567c78e32ce85643b48a5cc1a9，已记录GNU12兼容覆盖层。二进制SHA f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776，与旧启动清单一致；源码、构建文件、补丁、apex、GSWM及全部旧B14 NetCDF均验SHA。实际源码覆盖顺序及每个源文件SHA见source_manifest.json，不新编译、不修改源码。

使用同一官方5°smax完整primary：源年2002/day80，SOURCE_START=80 0 0，34个当前/前一步/下边界状态齐全，网格和原生掩码保留；不将其冒充真实2022分析状态。新起算2022-03-09 00时，连续至03-26 00时，STEP60s，共24480步。合法冷源结构不等于原生continuation恢复一致性已解决，RestartFAIL保持。

ibgrddata=0为旧实际派生默认，无背景文件；zbound约96.372290km，迁移GSWM昼/半昼开启，非迁移关闭；HEELIS、CALC_HELIUM=1、所有物理/输出变量/历史频率保持。唯一5项变化是STOP、SECSTOP从day84改85，OUTPUT增加primary018，SECOUT增加secondary017，以及GPI路径。预计18份primary/408小时secondary/17份secondary卷。旧LABEL中的nine-day遗留字样原样保留以避免无关改动；实际17天身份以START/STOP及run_protocol为准，绝不按该旧标签报告时长。

实际可运行input在新目录run/input.inp，原件SHA已冻结，本地不公开内部绝对路径；公开input.template.inp使用PROJECT_ROOT占位符，不替代实际冻结input。configuration.json给出项目相对引用；configuration_diff.json逐项列变更。新run目录可独占写入、无NetCDF、无launch_once，不覆盖旧模型。

## 环境、资源和监督

Open MPI5.0.8及NetCDF-Fortran动态库全部可链接；运行栈与旧B14兼容。4个普通Python MPI rank独立启动/退出0，监督cleanup通过；另一个普通sleep进程实际被超时终止，returncode=-15并确认清理。它们不是模型启动，也不证明新模型积分必然成功。实际动态库SHA和CPU探针证据见environment_audit.json。未来入口拒绝无明确授权参数的执行、重验冻结文件/源码/二进制/依赖/资源，supervisor新session、pidfd/进程身份校验、direct wait、一次标记、不重试。

当前磁盘空闲约1264.37GiB，MemAvailable约1826.32GiB，CPU affinity112，未发现活动TIEGCM。资源会变化，正式启动前必须再验。历史实测17天2553.40s与16天2429.79s支持估计新17天约42.56—43.03分钟、3.34GiB NetCDF；1.5倍时间规划约64.54分钟，不是确定上界。拟授权硬门槛4800s/16GiB/5GiB、至少20GiB剩余、MPI4/OMP1、一次启动/零重试；监督在4770s触发停止预留30s清理。抽样资源门槛不是操作系统瞬时硬隔离保证。

50项CPU测试通过（配置7、监督23、下载12、驱动8）；独立复核原始CDF、102天Fobs/176桶、中心平均、共同数组、34字段、新旧输入差异、2372受保护历史文件及全部旧B14原卷SHA不变。准备监督26.135s、workerCPU8.852s/峰RSS90.254MiB；完整资源分项见resource_audit.json。交互编辑/Git不冒充连续采样。

## 下一轮执行与科学门禁

用户另行批准后，使用已冻结配置执行一次；成功退出后还必须核24480步、4进程正常退出、18primary/408secondary完整时间、冷echo专属例外与暖态字段、DEN/ZG ilev及单位、原始SHA、目标全天至次日00边界，再对真实观测实施全部八列查询、禁止外推。当前还没有新目标模型场，不能提前声称Map-A覆盖已通过。

之后才可按frozen_evaluation_protocol进行历史系数冻结、future poison和1/3/6小时共同样本评价；只对照2021-03-25已冻结B14，不能重拟合旧结果或按未来表现选参数。SCIENCE_TRAINING_READY=False、EXTERNAL_DATUM_UNVERIFIED、RestartFAIL、DARTNOT_ADMITTED、REAL_ORBITBLOCKED保持；旧2022 A14PARTIAL不升格。本轮完成停止。
'''
 (R/'reports/TIEGCM_2022_MAR25_RUN_PREPARATION_V1.md').open('x').write(report)
 (R/'docs/TIEGCM_2022_MAR25_EXECUTION_DECISION_V1.md').open('x').write('''# 下一轮2022 Mar25执行决策

当前RUN_READY_NOT_LAUNCHED，真实模型启动0。指定Swarm A产品已验收；扩展GPI完全由既有真实GFZ数据生成，旧共同数组精确一致；只有结束日期、输出卷数及GPI引用5项最小变化。

需要用户下一轮明确授权一次MPI4/OMP1的17天独立连续冷启动，预算4800秒、RSS16GiB、输出5GiB、磁盘至少余20GiB，不重试。候选命令（本轮未执行）：先source scripts/activate_tiegcm.sh，再python scripts/execute_tiegcm_2022_mar25_v1.py --authorize-17day-run。冻结文件或输入SHA变化、资源不足或已有一次性标记时拒绝启动；不得删除标记绕过。

不采用Restart/append；旧Restart一致性FAIL是未解决风险，但该方案用合法原始完整冷源重新连续积分，避免依赖原生恢复。14天候选预热不是全物理收敛或观测精度PASS。新运行与旧共同轨迹仍需实测才能声称一致。

模型完成后先独立工程审计：真实退出码/24480步/18主记录408次记录、暖态有效性、全天边界、DEN/ZG ilev、原SHA、真实沿轨八列与无外推；才允许另授权2022-03-25固定算法评价。参数必须历史估计并冻结后才评分，无未来信息选参、无新算法。DART/轨道/AI继续禁止，外部高度登记不变。完成本轮后停止。
''')
 for n in ['STATUS.md','WORKLOG.md']:
  p=R/n;p.write_text(p.read_text()+'''\n\n## 2026-11-18 V14-B：2022 Mar25正式运行准入准备\n
TIEGCM_2022_MAR25=RUN_READY_NOT_LAUNCHED。真实模型启动0、密度拟合/评价0。仅下载指定Swarm A0301ZIP139665bytes，2880条UTC30秒、flag0/质量有效2880，CRC/SHA通过。复用六份GFZ原始响应，扩展GPI22天/176桶/102天Fobs，21共同日逐元素一致、共同分钟差0，24481分钟边界通过。保留旧smax完整34状态、二进制/apex/GSWM及物理设置；独立新input只变STOP/SECSTOP/两输出卷列表/GPI路径，17天24480步，18primary/408secondary。MPI4 Python探针和监督终止清理通过；50CPU测试及独立复核通过，2372旧文件和全部旧B14原卷SHA不变。准备监督26.135秒，workerCPU8.852秒、RSS90.254MiB。\n
入口：experiments/tiegcm_2022_mar25_preparation_v1/launch_protocol.json；报告reports/TIEGCM_2022_MAR25_RUN_PREPARATION_V1.md；决策docs/TIEGCM_2022_MAR25_EXECUTION_DECISION_V1.md；实际input/GPI仅本地，公共配置脱敏。后续拟4800s/16GiB/5GiB/MPI4OMP1、一次不重试，须新授权；本轮不启动首小时/17天积分。新目标日八列覆盖尚待真实模型输出后验，不提前声称通过。科学训练False/外部高度未验证/RestartFAIL/DART未准入/真实轨道BLOCKED/A14历史身份全部保持。执行结束停止，不自动进入正式运行或评价。\n''')
 for n,h in load('protected_assets_local.json').items():assert sha(R/n)==h,n
 # Exclude full input, GPI, raw/helper logs and protected long asset list from publication.
 files=[p for p in F.iterdir() if p.is_file() and p.suffix in ['.json','.csv','.inp'] and '_local' not in p.name and p.name!='sha256_manifest.json']+list((F/'run').glob('input.inp'))+[F/'gpi_2022_extended.nc']+[R/n for n in ['scripts/prepare_tiegcm_2022_mar25_v1.py','scripts/execute_tiegcm_2022_mar25_v1.py','scripts/verify_tiegcm_2022_mar25_preparation_v1.py','scripts/finalize_tiegcm_2022_mar25_preparation_v1.py','tests/test_tiegcm_mar25_preparation.py','reports/TIEGCM_2022_MAR25_RUN_PREPARATION_V1.md','docs/TIEGCM_2022_MAR25_EXECUTION_DECISION_V1.md']]
 dump('sha256_manifest.json',{str(p.relative_to(R)):sha(p) for p in files})
 print('Final frozen configuration/evidence package complete; no model launched.')
if __name__=='__main__':main()
