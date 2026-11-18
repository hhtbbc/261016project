# 2022-03-25 TIE-GCM执行与自动验收审查 V1

研究优先级：OBSERVATION_CONSTRAINED_PHYSICS_FIRST。

**ACTUAL_MODEL_RUN=NOT_RUN。正式模型入口未调用、17天积分未启动、真实密度拟合/评分均0。**

起始本地和远端main均为cd4fe5eb2818194a62e66f3a85cf4b585b57db18。原17天物理input、GPI、历史结果及冻结科学评价协议不变。新目录：experiments/tiegcm_2022_mar25_execution_review_v1/。旧报告保留，不能把其历史准备结论当作本轮真实积分验收。

## 1. 发现的执行风险与最小修复

| 项目 | 旧实现的问题 | 本轮修复/证据 |
|---|---|---|
| 非空工作目录 | 已准备run/input.inp，但supervise要求空目录，启动必然被拒绝 | CPU测试重现；采用原子创建的新actual_run，原监督器input_files暂存原input字节，旧input不移动、不删改 |
| 并发/一次性 | 分离的exists检查不足以互斥；监督器不承担跨调用锁 | 两个独立CPU进程、线程竞态测试；mkdir(exist_ok=False)只有一个赢家，失败/中断后保留预约，不自动重试 |
| 冻结SHA与代码升级 | 修改入口后，旧manifest自检必然拒绝新入口 | 不改旧manifest；execution_overlay明确钉住旧manifest SHA、唯一旧入口旧/新SHA和新执行代码SHA；科学输入仍全量原校验，不放宽 |
| 四rank真实状态 | MPI父退出0、四条NORMAL EXIT都不能单独证明每个模型rank正常退出 | rank包装器直接wait模型子进程，记录0—3 rank/world4、模型/input SHA、实际返回码、启动/结束及SID；与MPI父直接wait联合核验 |
| 丢失/异常退出 | MPI失败可能使部分peer来不及写最终回执 | 缺回执FAIL，不补造0；预约目录存在但无完整wait状态为UNKNOWN/FAIL，不误称NOT_RUN或成功 |
| 退出0但少算/缺文件 | 原入口未把全程完成验收作为返回成功条件 | 自动只读验收必须全部PASS，否则入口非零退出，保留证据；不继续科学评价 |
| 监督范围 | 包装器若不转发日志会破坏原进展/致命日志监控；子进程可能不在采样session | 保留逐rank日志并转发至原stdout；CPU MPI_Init/Finalize实测包装器与子进程SID均属于监督session，实际运行仍再次核对 |

复用src/runtime/supervisor.py，未修改核心监督框架、模型源码或坐标接口。新增的是任务衔接、逐rank回执和只读验收，不是另一套积分/资源框架。

无授权分支使用明确异常/argparse拒绝，不依赖可被python -O关闭的assert。当前任务只在单元测试中测试拒绝函数，没有调用正式启动CLI。

## 2. 证据等级与实际状态

| 证据类别 | 本轮实际支持的结论 | 不支持的结论 |
|---|---|---|
| 已有SHA证据复用 | 旧准备包、官方smax源、GPI、源码/二进制、科学模块身份保持；源码/动态库轻量重验通过 | 不重做81日驱动构建、整套历史数据扫描或模型积分 |
| 当前真实CPU测试 | 普通MPI辅助程序、C MPI_Init/Finalize握手、子进程wait/退出回执、并发抢占及资源监督衔接有效 | 不是TIE-GCM四rank物理演化测试 |
| 模拟数值测试 | 极小NetCDF的填值/NaN/Inf/非正DEN、单位错误、ZG非单调等会拒绝；异常日志、缺文件/回执/状态不会PASS | 不是人工成功日志证明真实积分完成 |
| 已有小样本只读 | 一条旧2022 B14暖态小时记录的DEN/ZG读取有效；旧首primary确实是原生cold echo | 不是重验17天完整数据或物理精度 |
| 等待真实运行 | 五项实际工程检查全部NOT_RUN，见actual_acceptance_status.json | 不得预先宣布17天工程PASS、沿轨覆盖或密度科学收益 |

最终60项不同CPU测试通过：执行/验收22、冻结科学流程5、原纬度14、小时算子8、原晚间11。未重复上一轮整套50项准备测试或原始CDF/驱动重建。测试开发初期曾错误假定MPI失败时一定存在四份最终回执，之后又用空protocol导致失败fixture先触发KeyError；已修正测试预期/fixture，保留失败日志，最终通过证据单列，不抹去错误。

## 3. 运行后自动工程验收

脚本：scripts/audit_tiegcm_2022_mar25_execution_v1.py；模块：src/atmosphere/tiegcm_mar25_acceptance.py。工具只读模型/观测，只有指定的新验收JSON会写入；不存在输出就标NOT_RUN，不创建实际模型目录。

顺序检查如下，每项输出PASS/FAIL/NOT_RUN与证据：

1. 原MPI监督进程returncode=0、qualification=PASS、无采样缺口、cleanup已核实、direct Popen.wait真实拥有子进程退出码。未获得退出状态不当成0。
2. 四rank均有同一run_id的started/exit回执，模型和input SHA正确，子进程实际wait返回0，无异常/终止信号。包装器与模型子进程SID必须等于监督根session。NORMAL EXIT计数不替代回执。
3. 每个rank一条NORMAL EXIT，无致命日志；按实际util.F time2print规则核对10—24480每10步日志、总步数与日历，输出暖态iter再与经过分钟数交叉核验。日志不是逐步独立物理真值，但结合真实进程和输出证明工程步数完整。
4. 18个primary卷各1记录，17个secondary卷各24小时记录，总计18/408。primary从03-09 00至03-26 00，secondary从03-09 01至03-26 00，逐卷/跨卷精确日历无缺失、重复、错序；CF时间、year/day/mtime一致，STEP60和calendar_advance不变，网格与原static一致。
5. 复用既有2022 basic_file完整primary/暖态变量校验；DEN/ZG必须time,ilev,lat,lon，单位g/cm3/cm，正值/有限/填值/垂直单调性全部合格。逐暖态secondary记录核对实际GPI驱动（显式拒绝masked/NaN/Inf，防止max误差聚合吞掉NaN；沿用1e-10门槛），保存全部输出SHA、记录数和时段、输入来源。
6. 合法冷echo仅首个primary初始身份：其iter继承源场，不用于计算已完成更新；不要求primary凭空具备非restart诊断DEN/ZG。所有secondary按本协议均为暖态，禁止以cold例外放过缺失/填值。没有修改字段、掩码或物理门槛。
7. 对已取得的2022-03-25 Swarm A全部质量合格样本执行原Map-A查询，加载目标日25帧。每点两时间×四水平共八列，零权重列也检查；禁止时间、极冠水平和垂直外推。任何失败输出原因并FAIL，不改共同掩码掩盖。只记录覆盖和失败原因，不计算密度误差。

未来模型若失败，不自动重试；只读验收也不得通过删除不利样本变PASS。只有全部检查PASS，正式入口才返回成功；即使工程PASS，科学门禁仍不解除。

## 4. 科学评价协议审查

原frozen_evaluation_protocol.json及其引用算法SHA不变。保留06/18Z、过去3小时半开历史窗、未来累计1/3/6小时及非重叠块；06全局，18全局/纬度/Stale06，三个纬区与N≥30不变。Stale仅用同日03—06历史系数，不借03-23/24旧系数。

仅对合成数组进行了历史拟合→独占冻结文件→future poison→共同样本评分流程测试。没有拟合真实2022-03-25或重拟合2021参考。无效密度拒绝、缺区域/不足样本N/A且不得PASS，四项联合判据和relative RMS分母都未变化。三个累计窗口与30秒点不是独立重复，不做普通IID显著性。

边界需明确：metric_row/compare_density能检查数组对齐和无效值，但不能阻止调用者故意传不同日期/掩码。未来调度必须先固定共同sample IDs，记录SHA，并对所有方法使用同一掩码；不能因为单个方法较差就另删样本。已有模块可复用，但旧V14-A入口硬编码2021和旧目录，不能直接改年份重跑；2022实际评价路径接入须在未来获准的评价任务完成，按冻结步骤检查，不新造方法。

2022-03-25是预注册额外日期，已经读取过产品质量，且相邻日期参与开发；NOT_BLIND。模型与Swarm是物理背景—沿轨POD反演观测对照，不能称完全独立大气真值。Map-A数值有效不等于ZG外部零面正确。

## 5. 资源与未闭合风险

历史2553.40秒（17天）、2429.79秒（16天）是实测；42.56—43.03分钟、约3.34GiB是线性历史估计，不是置信上界。4770秒是监督停止触发阈值，另留30秒清理，目标不超过4800秒；RSS16GiB/输出5GiB/余盘20GiB为采样阈值，启动时要求至少25GiB以留输出余量，MPI4/OMP1，一次预约、无自动重试。

监督是同UID新session的进程树采样与信号清理，不是cgroups/严格操作系统隔离；共享页可能重复计RSS，采样间峰值未必观测。SIGKILL、系统故障或断电可留下未知状态，不能保证任何故障下都写出完整日志或精确4800秒内结束；预约保留并按UNKNOWN处理。当前无明显磁盘/内存/库工程阻碍，实际数值见resource_review.json，正式启动时再核。

自动工程验收是单独CPU阶段，计划额外≤600秒、RSS4GiB、产物150MiB；不是把它隐含算入旧4800秒积分预算。下一轮授权应明确包含一次积分及该只读验收，合计监督预算最多约5400秒加必要调度清理，实际预计远低此值。没有开展真实模型性能估计。最终执行CPU测试的实际墙钟与自报峰RSS见resource_audit.json；此为测试进程，不是完整任务连续进程树峰值。资源分项和定义见resource_audit.json。

未闭合：包装后的真实Fortran积分行为及全部工程输出尚未实测；17天积分/全目标日沿轨覆盖待授权；Restart一致性FAIL；14天候选预热不等同完整多变量科学收敛；ZG外部登记、真实气动/姿态/推力、正式轨道门禁均未解除。

## 6. 下一步与人工决策

本轮不需要人工补数据或处理环境缺口。若要实际启动，用户必须在下一轮明确授权一次17天连续冷启动及只读自动工程验收；本轮没有该授权。

新命令仍为既有execute_tiegcm_2022_mar25_v1.py --authorize-17day-run，但必须加载本轮execution_overlay和新代码SHA，新工作目录独立，不使用Restart或append。旧冻结input/GPI逐字节保持不变。任何预约残留、输出存在、SHA变化、活动模型或资源不足都拒绝，不删除预约重试。

工程验收PASS后停止；另获评价授权后，按清单先系数历史冻结、poison再未来指标及2021旧结果对照。不能以首小时RMSE下降代替四项联合标准或推广全年。SCIENCE_TRAINING_READY=False、EXTERNAL_DATUM_UNVERIFIED、RestartFAIL、DARTNOT_ADMITTED、REAL_ORBITBLOCKED和A14历史身份全部保持。
