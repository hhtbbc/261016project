# V23：mareqx受限政策、秋季双年份配置冻结与执行门禁

## 一、今日完成情况

起始本地HEAD与远端main均为`b655314c59a2208568c2673cbcbe3f414d97805c`。保留已有不相关未跟踪同步日志，没有重下载或改写历史目录。

在`experiments/thermosphere_autumn_mareqx_config_v23/`新建独占收据、两年份独立input.inp、启动协议、配置差异表、执行代码与冻结SHA清单。2021与2022分别为 **CONFIG_FROZEN_READY_FOR_RUN_AUTHORIZATION**。**ACTUAL_MODEL_RUN=NOT_RUN，真实工程验收=NOT_RUN**，模型二进制未调用，未生成真实预约/actual_run目录。

用户明确批准A路线，收据`seed_policy_receipt.json`冻结 **SEED_POLICY=A_MAREQX_APPROVED**。这是本轮政策授权，不包含模型启动授权。收据独占创建、权限0444、冻结SHA检测改动，并非宣称root无法改写。V22原政策待定历史记录不修改。

## 二、关键技术解释与真实初态

mareqx SHA：`a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7`。本轮重新只读核验实际NETCDF3_CLASSIC、primary单记录、原生year=2002、mtime=[80,0,0]，36lat×72lon，lev/ilev各29，34原生状态及其双精度schema、单位、有限性、合法顶层填值和基本数值均通过既有严格检查器。同时对照2021 B14历史`initial_state_audit.json`的相同SHA/完整34状态证据；没有将结构完备称为Restart恢复一致性通过。

冷启动语义证据：

- `input.F:948–960`要求START和SOURCE_START小时、分钟相同，明确允许日不同。
- `rdsource.F`在显式SOURCE分支只读选择该文件的SOURCE_START记录，不从OUTPUT续算；无SOURCE的另一个分支才搜索输出并可能append。
- `init.F`以目标START计算初始iter，目标START_YEAR/START_DAY负责实际模型日历；源记录年仍为2002，不改写。
- 春季成功配置同样SOURCE_START=80 0 0、目标START=68 0 0。秋季合法设START=252 0 0、STOP=268 0 0，SOURCE_START仍80 0 0。首primary继承cold echo的iter不用于累计步数，暖态从目标252日起独立核对。

公开配置采用`$PROJECTROOT`替代本机绝对路径。原Fortran `expand_path`把下划线视为变量名分隔符，因此不使用含下划线的环境变量名。只将原expand_path子程序逐字复制到独立小探针编译，对两年份SOURCE、GPI、两GSWM共8字段实测展开等于原件真实路径；没有重编译模型或修改物理源码。

## 三、配置与测试结果

| 项目 | 2021 | 2022 |
|---|---|---|
| 积分UTC | 09-09 00:00—09-25 00:00 | 同月日 |
| 目标日 | 09-23 | 09-23 |
| SOURCE_START | 80 0 0，同一原件SHA | 相同 |
| 模型STEP / 更新数 | 60秒 / 23040 | 相同 |
| MPI / OMP | 4 / 1 | 相同 |
| 预期primary | 17记录、17卷（含首cold echo） | 相同 |
| 预期secondary | 384小时、16卷×24记录 | 相同 |
| 总NetCDF | 33文件 | 33文件 |
| 实际模型/验收 | NOT_RUN / NOT_RUN | NOT_RUN / NOT_RUN |

时间轴来自原生HIST=1天、MXHIST_PRIM=1、SECSTART=252 1 0、SECHIST=1小时、MXHIST_SECH=24及output.F分卷规则；并只读引用已成功16天春季B14的17/384记录审计，不照搬17天的18/408。完整预期UTC在`expected_timelines.json`，包括目标日和09-24 00:00查询边界，运行终点09-25 00:00。

| 冻结资产 | SHA256 |
|---|---|
| 2021 input | `1d73a45b25b0af5c5a70a9e5870e07589153b2789ccb3c9353cc957c742ee121` |
| 2022 input | `f01f3913f9f15b79132fe8f824c7ce9f5ce7c4c1b6591c9622be184ee7b0fa49` |
| 2021 GPI | `d401d0ae525babb343faaa6d1dd9a8d3c4fb1c2ea85beb26d2b0025cdf001b9a` |
| 2022 GPI | `7d43db220fe7fbaded6b2182db8db32ee09cedf99dc5760815824ccf8298ebb2` |
| 模型二进制 | `f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776` |

与春季成功17天配置实际差异仅：目标年份（2021）、START_DAY/START/STOP、SECSTART/SECSTOP、GPI、17/16卷输出列表及准确的秋季LABEL。SOURCE和两GSWM仅路径书写改用变量，展开后同一文件。STEP、SOURCE_START、HEELIS、CALC_HELIUM=1、SECFLDS及其余显式参数相同；默认ibgrddata=0、zbound及GSWM机制继续复用同源码/覆盖层，未人为改变。完整逐字段差异见`configuration_diff.csv`，独立解析未发现未预期差异。

必须披露：新秋季目标09-23距起点14天，而March25参照距March09实际16天。B14名称不意味着每个历史目标只有14天适应。日历、真实驱动、季节适应和目标时刻的已运行时长共同改变，不是严格单因素季节因果实验。

**50项低成本检查通过**：43项新秋季/V17单元与回归，4项补充SHA/网格反例，1项原Fortran路径探针，2项逐年份冻结包+不启动子进程的NOT_RUN探针。43项中包含两次普通C MPI_Init/Finalize辅助作业（正常及rank2退出7）；验证四rank直接wait/SID和异常不能冒充成功，不是TIE-GCM积分。测试中的故意异常Traceback、MPI非零退出均为反例证据，不代表真实模型失败。

测试覆盖政策、源/GPI SHA及年份、SOURCE_START、日历越界、格点不兼容、目录混用/旧春季路径、物理参数改动、原子线程/进程抢占、全局锁、重复预约、无授权拒绝、缺文件/时间轴错误、原协议不变、NaN/Inf/填值/非正DEN/ZG非单调、告警隔离等。V17测试仅将fixture基目录指向V23，原测试源码与旧fixture不改。新增静态独立解析器没有调用配置生成函数，核对每个字段、UTC、物理路径、SHA和分卷数量。

## 四、执行风险、资源和验收边界

春季执行器/验收器绑定2022-03-25、24480步和18/408记录，不能直接用于秋季。本轮新增秋季薄适配：`runtime/tiegcm_autumn_execution.py`及`atmosphere/tiegcm_autumn_acceptance.py`，复用原supervisor、rank直接wait、V17原生DEN/ZG检查、进度与退出检查、Map-A八列算子和窄WarningChannel；不改春季冻结代码，也不全局改变NaN/Inf致命监控。

每年独立actual_run原子mkdir和永久失败现场；跨年份非阻塞flock覆盖整段执行。无授权在任何验证/子进程前拒绝，重复/并发预约、SHA变化、库漂移、活动模型、资源不足都拒绝。中断/失败不得删除预约或自动重试，SIGKILL/断电可能无法写最终回执，此时只能UNKNOWN。四rank与MPI父进程必须有真实直接wait、同session证据，NORMAL EXIT文本不是独立退出证明。

未来自动验收检查完整33文件/17主/384次、精确日历/暖态iter、全程原生数据、1e-10冻结驱动门槛和2880质量合格观测的八列Map-A覆盖。零权重列也检查，不外推、不删失败点。窄告警通道只用于只读阶段，原警告完整保存在本地；未知警告/真正异常仍fail-closed。当前无实际秋季输出，所有真实验收均NOT_RUN；静态测试不替代未来原件独立复核。

当前快照：Open MPI5.0.8，CPU affinity112；MemAvailable约1817.23GiB，剩余磁盘约1259.49GiB，活动TIE-GCM进程0。全部动态库SHA与春季记录一致，两实际运行目录及预约均不存在，独立父目录写探针成功。内存为主机可见余量，不是独占承诺；标准cgroup v2限制路径未暴露，不虚称OS已硬隔离。真实启动仍须重查资源、依赖及会话持续监督能力。

历史16天墙钟40.05—40.77分钟、约3.14GiB为估算依据，不是保证。未来每次提议4800秒、RSS16GiB、输出5GiB、启动余盘25GiB/运行余盘20GiB、一次启动无重试；另需600秒/RSS4GiB只读验收及独立复核授权。监督器4770秒触发停止并名义留30秒清理，是采样/信号机制，不保证系统故障下严格4800秒结束。

本轮准备0.878秒（CPU0.733秒）、43测试2.813秒（CPU0.526秒），其余小探针分列resource_audit；自进程高水位876.77MiB，并非整任务连续树峰值。无新下载、GPI重建、模型编译、模型积分、评分/拟合、GPU/DART/轨道。只编译普通MPI和路径探针辅助程序。

## 五、当前项目状态

两年份均 **CONFIG_FROZEN_READY_FOR_RUN_AUTHORIZATION**，状态只表示政策/配置/启动门禁及独立静态检查通过。下一次真实执行仍未授权，未生成MODEL_RUN_COMPLETED，未宣称秋季科学评价PASS。

V20预注册SHA `eb27a080199d656f6018f47834cc9eaef07897009360ca184d6511e4d3aeb2c4`不变，保持06/18Z、3小时历史、未来1/3/6小时与非重叠块、同日Stale06、30/60纬界、N≥30、不fallback、参数/乘数先冻结、future poison、共同IDs和四项联合无退化条件。V21两日各2880有效及分区窗口证据只读复用。本轮未读秋季目标密度误差或拟合参数，新日期仍未评分。

继续保持AUTUMN_ADAPTATION_UNVERIFIED、FOURTEEN_DAY_SPINUP_NOT_PROVEN_CONVERGED、SEPEQX_SOURCE_NOT_ACQUIRED；A政策不再受B源403阻碍，但不能消除A季节风险。SCIENCE_TRAINING_READY=False、EXTERNAL_DATUM_UNVERIFIED、Restart=FAIL、DART=NOT_ADMITTED、REAL_ORBIT=BLOCKED不变。

## 六、下一步计划及用户决策

下一轮优先申请 **2021-09-09至09-25单次16天积分**，同时明确一次只读主验收和基于原件的独立复核预算。具体入口、顺序和失败处置见[执行建议](../docs/THERMOSPHERE_AUTUMN_V23_NEXT_EXECUTION.md)。本轮不执行该命令。

2021工程验收后停止，2022需另一次明确授权；不依据2021密度误差改变2022配置、方法或日期。模型与独立工程验收完成后，另授权按V20冻结协议评价真实密度；不自动接续评分、DART、训练或轨道传播。
