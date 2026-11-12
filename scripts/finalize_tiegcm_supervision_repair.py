"""Reports from completed mock jobs + read-only audit, never a model launch."""
from pathlib import Path
import json,hashlib,csv,re,time
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/tiegcm_supervision_repair_v1';O=ROOT/'results/tiegcm_supervision_repair_v1'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def write(name,text):
 with (ROOT/name).open('x') as f:f.write(text.strip()+'\n')
def main():
 tests=json.loads(max(O.glob('test_runs_*.json'),key=lambda p:p.stat().st_mtime).read_text());assert tests['success'] and tests['tests']==23
 a=json.loads((F/'A14_evidence.json').read_text());b=json.loads((F/'B14_static_preflight.json').read_text());hist=json.loads((F/'history_preservation.json').read_text())
 root='''# TIE-GCM监督故障定位与修复

本轮仅短时Python子进程和只读数据审计，真实TIE-GCM启动0。不修改历史监督脚本/第三方模型，不重跑A14，不启动B14。

## 已证实的故障链

1. `scripts/run_tiegcm2023_crossday.py:54–61`中，try仅包住`read_text`等循环体；第56行`Path('/proc').glob('[0-9]*/stat')`的迭代器推进发生在try外。实际Traceback从pathlib.exists/stat抛ProcessLookupError，目标是/proc/1797841/stat，而不是MPI主PID1794822。
2. `scripts/run_tiegcm_2021_14day.py:170–201`启动独立会话后，在172行采RSS，异常越过整个while及201行`proc.wait()`；没有外层try/finally保护子进程所有权、清理和退出记录。2022隔离适配沿用了此路径。`logs/tiegcm_2022_14day_A14_supervisor.log`是直接证据。
3. pair的subprocess.run(check=True)因此收到监督器异常而退出，但不是模型返回码。`start_new_session=True`且未执行进程组终止，使原MPI继续运行；历史guardian记录和连续输出支持此事实。
4. guardian是后来附着的观察者，不是原MPI父进程，没有原Popen.wait持有的直接子进程等待关系。/proc zombie exit_code只有在可观察窗口内才可能读到；实际记录raw status=null、launcher_disappeared_without_observable_exit_status，不能将预设launcher_exit_source文字当作观察成功。
5. resume在A14资格断言处停止，B14启动0。这是原门禁实际生效，不能绕过。

## 推断与不可恢复项

Linux进程被回收后，当前/proc同PID可能是另一进程，不能用其状态追认历史运行。guardian未观察到zombie的具体微秒级先后没有记录；“被系统回收而错过观察窗口”符合机制与现有记录，不是假装有waitpid证据。项目现存日志/状态/清单未发现其他可靠退出记录；历史真实退出码、缺口内逐时RSS和最终waitrusage不可从留存证据恢复。NORMAL EXIT及完整文件不能代替退出码。监控异常不是模型数值异常的证据。

## 新实现

`src/runtime/supervisor.py`不含TIE物理或年份源码替换。直接Popen启动、父进程wait回收；所有采样、解析、验证异常有独立处理，finally再次等待/清理。正常0、非零、信号、超时、启动异常、UNKNOWN分别记录；rc已知与监控资格分别记录，采样缺口不插值。

/proc采用一次列出PID名、逐PID捕获预期竞态；读取stat前后比较出生ticks，选取同UID的专属新session，保留PID/start_ticks/PGID/SID。目标不可读返回RSS=None，不把缺失当0。无关PID瞬逝计数记录。终止时先开pidfd固定进程，再复核出生身份及会话，拒绝复用PID/异UID；对整个已核实会话逐进程TERM/KILL，且真实wait退出码仍保留。不依赖未经验证的killpg数值PID回退。

当前Python3.10未导出pidfd接口，系统libc的pidfd_open/pidfd_send_signal可用；实现显式ctypes签名与errno检查，实测通过。首次测试暴露此兼容性问题，失败日志保留。随后测试还发现验证回调失败计数提前清零，已移到全部采样/校验成功后重置；不放宽测试。

资源控制含单调墙钟、RSS、余盘、单卷NC大小、组输出/总输出、追加日志异常/停滞和闭卷验证回调。事件JSONL逐条flush/fsync；日志写失败也不跳过子进程等待。资源是离散采样，不是瞬时RSS上界。CPU是本监督进程RUSAGE_CHILDREN差值，不是系统总CPU或保证所有已逃逸孙进程均被计入。

```mermaid
flowchart LR
 I[新目录+一次启动标记] --> P[直接Popen创建专属会话]
 P --> W[父进程wait循环]
 W --> S[采样与只读闭卷检查]
 S -->|异常| G[记录缺口/持续失败则受控停止]
 G --> W
 W --> F[finally: 身份核验清理+wait]
 F --> R[真实退出码或UNKNOWN / 独立资源资格]
```

## 验证范围和边界

23项实际短子进程/故障注入测试通过，覆盖A—H、PID复用/异UID拒绝、未知RSS、原生信号、监督器SIGTERM、错误日志、验证回调异常和禁止覆盖。不是16天或真实MPI端到端验收。测试使用同服务器本地session；远程MPI、主动逃逸session的守护进程不在当前支持范围。未来仅允许本机4MPI/OMP1并核对实际拓扑。

父监督器遭SIGKILL、主机断电、内核故障或存储永久阻塞，不能承诺还能写最终JSON或回收状态；必须UNKNOWN/PARTIAL，不能宣传软件可保证所有故障下退出状态。墙钟检查与TERM/KILL清理有有限调度/清理开销，未来4800秒总预算须为清理留余量。独立外部watchdog可作为未来增强，但本轮不以旁观者替代直接父进程wait。
'''
 write('reports/TIEGCM_SUPERVISION_REPAIR_V1.md',root)
 write('reports/TIEGCM_A14_EVIDENCE_AUDIT_V1.md',f'''# A14历史证据独立审计

|检查对象|结果|
|---|---|
|日志步数最大值|{a['steps_log_max']}；不是声称每一步都有单独日志|
|NORMAL EXIT|{a['normal_exit_count']}|
|primary / hourly secondary|{a['primary_records']} / {a['secondary_records']}|
|NetCDF及SHA|33卷全部一致|
|时间/网格/字段/单位/填充值/密度温度风组分工程检查|PASS；源冷echo及primary未输出诊断按原协议N/A，不伪造字段|
|实际驱动最大绝对差|{a['driver_max_abs_difference']:.4e}|
|资源采样缺口|{a['sampling_gap_s']:.6f}秒（{a['previous_rss_sample_s']:.6f}至{a['first_guardian_sample_s']:.6f}秒）|
|真实MPI退出状态|UNKNOWN；留存证据中不可恢复|
|有限离线科研分析|允许，明确PARTIAL/PROVISIONAL身份|
|原冻结完整工程验收|PARTIAL，不能改PASS|

本轮只读前后共{hist['files']}项历史文件SHA相同，包括33卷、原状态、原输入、日志等。真实退出码仍null；没有重写旧审计/旧日志、没有重新生成输出。实际完整数据检查与主/次历史schema见experiments/tiegcm_supervision_repair_v1/A14_evidence.json。首次独立审计错误地假定所有primary都含DEN，读取阶段IndexError；改为逐文件显式列出实际字段和缺失诊断、沿用原物理检查，保留失败日志，未修改原数据。

当前项目未保存额外可靠的原wait/wait4或系统进程记账结果。当前/proc列表、输出完整性和4 NORMAL EXIT都不能证明原launcher返回0。数据完整性与真实退出/全程资源监督资格是不同证据链。
''')
 write('docs/TIEGCM_B14_PRELAUNCH_PROTOCOL_DECISION_V1.md',f'''# B14启动前协议决策：本轮不启动

|项目|方案A：原冻结协议|方案B：另立探索性v2草案|
|---|---|---|
|A14资格|必须完整工程PASS，目前不满足|保留PARTIAL，作为数据完整的受限输入|
|现在能否启动B14|不能|不能；须用户单独授权、启动前冻结|
|是否修改历史判定|不修改|不修改|
|后续可宣称|只有按原协议取得完整证据后才可完整闭环|仅新协议下的有条件双初态比较，不能称原协议PASS|
|科学训练门禁|不解除|不解除|

推荐方案B供用户决定：现有A14物理文件证据完整，有研究利用价值，可避免仅为丢失退出码重跑整条轨迹。但它不是已采用的协议，不能补写A14 rc0，也不能在未来B14合格后追认原双轨完整工程PASS。若用户坚持严格完整工程证据，采用方案A并另行决定是否需要新版本A14；本轮不授权任何重跑。

## 当前静态预检

smax源34项状态、2002 DOY80 00:00合法记录、网格/单位/掩码与既有smin相容；源、GPI、apex和可执行SHA重新核验。B14候选namelist与原A14仅SOURCE不同，原START/STOP/输出/HEELIS/GSWM/IGRF等不变。现有扩展GPI23041分钟节点有效，不新增下载。

当前CPU亲和核{b['cpu_affinity_count']}，可用内存{b['current_available_memory_bytes']/2**30:.2f}GiB，磁盘余量{b['current_free_disk_bytes']/2**30:.2f}GiB，无运行中TIE进程，静态资源PASS。此检查有时效，未来启动前必须重查。

按A14实测2433.814729秒乘历史B7/A7耗时比，B14外推约{b['estimated_wall_s']:.2f}秒，1.5倍约{b['safety_wall_s']:.2f}秒；这不是B14实测。输出外推{b['estimated_NetCDF_bytes']/2**30:.4f}GiB。参考上限单次4800秒、16GiB树RSS、5GiB输出、单卷256MiB、余盘20GiB。原两轨9600秒/12GiB不自动重置成新增授权；v2必须明确新单次预算和既有A14占用。

## 未来启动前必须完成

1. 用户选择协议并授权新B14，冻结v2标签和A14 PARTIAL身份，明确无重试。
2. 新独立输出目录（候选experiments/tiegcm_2022_b14_exploratory_pair_v2/B14）不得存在；不得复用或改写旧A14/B14身份。
3. 核对B14_static_preflight.json中所有SHA及当前资源，冻结监督器/闭卷验证器/env/namelist SHA、总监督预算和清理余量。
4. 使用runtime.supervisor.supervise直接启动本机mpirun；通过input_files将冻结input.inp逐字节放入新空目录，env保留既有MPI设置和OMP1，禁止旧字符串适配监督路径。输入暂存、exclusive launch_once、失败不自动重试。
5. 闭卷校验回调复用已有2022物理字段/时间/单位检查，仅检查已关闭卷；最后在真实wait返回0后审计全部33卷、23040步、17主/384小时、4日志退出、实际驱动和网格。日志不能替代返回码。
6. 总文件预算同时计入旧A14和新B14：可将新协议目录限额冻结为12GiB减去既有A14实际生成字节；不可把整个experiments作为计数根。每组仍≤5GiB。
7. 监督/退出/清理/数据任一资格不完整则保留PARTIAL/FAIL，不替换122候选、不解除科学门槛。真实MPI端到端路径本轮未运行，不能称已验证。

本轮交付的是可复用监督模块和完整静态启动清单，不提供自动绕过协议的执行入口。B14_STATIC_PRECHECK=PASS；B14_LAUNCH_ADMISSION=BLOCKED_PENDING_PROTOCOL_AUTHORIZATION；B14_ENGINEERING=NOT_RUN。
''')
 write('docs/TIEGCM_2022_A14_STAGE_BRIEF_V1.md','''# 一页阶段结论

- 已有Map-A下，同一2880观测点，A7/A14 RMSE=2.915160/2.739357×10⁻¹³kg/m³，降低6.03066%；相对RMS=20.549745/19.892541%，降低3.19811%。
- Map-B/E下，绝对RMSE虽降低，部分相对误差反而恶化，相对RMS分别增0.62390%/0.62777%；保留所有映射，不择优认定真实高度。
- A7/A14比较同时涉及起始日期及额外驱动历史，不能替代A14/B14双初态收敛；2022十四天是否充分目前未知。
- A14数据完整性PASS、物理字段工程检查PASS，但原完整工程资格PARTIAL：退出码无法从留存记录恢复。本轮新监督器通过短子进程测试，不追溯改写历史。
- 外部ZG高度登记未验证，Swarm DNS是反演产品而非无误差真值；SCIENCE_TRAINING_READY=False，原122帧不改。
- 复用图：results/tiegcm_2022_spinup_14day_v1/partial_swarm_density_timeseries.png、partial_observation_map_sensitivity.png。未下载、未重跑查询。

向领导说明：我们已把“程序是否正常运行”“模拟对初态是否稳定”和“是否接近卫星反演密度”分开验收。监控故障已定位并以真实短任务验证修复，但历史退出码不能补造。下一步建议经单独授权，建立明确标记A14部分工程资格的新探索协议补B14，而不是悄悄放宽旧协议。
''')
 with (O/'test_coverage.csv').open('x',newline='') as f:
  writer=csv.writer(f);writer.writerow(['requirement','evidence','status'])
  for key,evidence in [('A','normal wait rc0'),('B','nonzero rc7'),('C','deterministic proc disappearance and12 real short-lived helpers'),('D','real timeout TERM'),('E','mock5 resource limits and real200-byte NC'),('F','one and persistent sampler error; model validator failure'),('G','child signal; process-group KILL; unrelated process alive; supervisor SIGTERM'),('H','real child wait result fault injection -> UNKNOWN; nonchild waitpid failure')]:writer.writerow([key,evidence,'PASS'])
 files=[ROOT/'src/runtime/supervisor.py',ROOT/'src/runtime/__init__.py',ROOT/'tests/test_runtime_supervisor.py',ROOT/'scripts/audit_tiegcm_supervision_repair.py',Path(__file__).resolve()]
 files+=list((ROOT/'logs').glob('tiegcm_supervision_repair_v1*'))
 with (F/'source_logs_SHA256.json').open('x') as out:json.dump({str(p.relative_to(ROOT)):sha(p) for p in files},out,indent=2)
 with (F/'final_states.json').open('x') as out:json.dump(dict(supervisor_tests='PASS_23_SHORT_CPU_CASES',real_TIEGCM_integration='NOT_RUN',A14_ENGINEERING='PARTIAL',A14_DATA_INTEGRITY='PASS',A14_PHYSICAL_FIELDS='PASS',A14_EXIT='UNKNOWN',B14_ENGINEERING='NOT_RUN',B14_STATIC_PRECHECK='PASS',B14_LAUNCH_ADMISSION='BLOCKED_PENDING_PROTOCOL_AUTHORIZATION',DUAL14_SENSITIVITY='NOT_AVAILABLE',SCIENCE_TRAINING_READY=False,EXTERNAL_DATUM='EXTERNAL_DATUM_UNVERIFIED',real_model_launches=0),out,indent=2)
 print('Reports generated; historical status preserved; no model launch')
if __name__=='__main__':main()
