# V16：2022-03-25 TIE-GCM正式17天积分与工程验收

**总状态：ENGINEERING_FAIL。物理模型已完成；冻结自动验收被日志门禁终止，未形成完整工程PASS。**

本报告区分模型积分成功、独立数据专项通过和自动工程验收未完成。不得将前两项替代第三项。未进行密度误差计算、校正拟合、DART、AI或轨道传播。

## 1. 实际授权、运行身份和时间

起始本地/远端main：bd651d995c55f7f8691cd03d6522482d18e188db，冻结科学配置和执行覆盖层SHA通过；真实二进制、官方完整smax源、扩展GFZ GPI及2022-03-25 Swarm A原件存在并验SHA。资源达标，无旧预约或活动模型。未修改冻结代码，未重新编译。

实际仅调用一次：

```bash
source scripts/activate_tiegcm.sh
python scripts/execute_tiegcm_2022_mar25_v1.py --authorize-17day-run
```

- run_id：094fcac3949c4e2e981d3baac1a5d8bf。
- 物理输出目录：experiments/tiegcm_2022_mar25_execution_review_v1/actual_run/。
- 新V16证据目录：experiments/tiegcm_2022_mar25_formal_run_v1/。
- 首rank调用模型前记录：**2026-11-18 09:03:27.709261 UTC**。
- 末rank模型子进程直接wait完成：**2026-11-18 09:46:46.653681 UTC**。
- 模型时间轴：**2022-03-09 00:00—2022-03-26 00:00 UTC**。
- MPI4/OMP1，STEP60秒，24480步；合法完整冷源，不使用Restart/append。

服务器实际执行日期与模型历史日期不同。聊天在运行途中跨日接续，2026-11-19先读取原任务真实结束记录，未重新启动。原监督进程全程保存9950次资源采样、采样缺口0；交互暂停时间不计入43.32分钟模型耗时。原工具会话最终退出1，原因是自动验收失败，不是MPI模型进程返回非零。

## 2. 真实退出状态与积分完整性

| 层级 | 实际结果 | 意义 |
|---|---|---|
| MPI父进程 | returncode=0，qualification=PASS，cleanup verified | direct Popen.wait及事件日志一致 |
| 模型rank0/1/2/3 | 0/0/0/0，各一条NORMAL EXIT | 同一run_id/world4，子进程PID各异、SID与监督session相符 |
| 每rank进度 | 10—24480，每10步记录完整，终点day85 00:00 | 不只检查最大日志编号，排查缺失/重复 |
| 暖态计数 | 最终iter=122400，基点97920，差24480 | 不用冷echo继承的源计数推断更新 |
| 正式入口脚本 | 最终returncode=1 | 模型完成后自动验收失败，入口按设计拒绝返回成功 |

rank_exit_summary.csv保留四rank的实际退出码、时间及回执SHA。独立复核直接读原rank日志、回执和父监督事件，不复述原验收PASS；主验收本轮没有PASS文档。

## 3. 实际资源与预算

- 模型监督墙钟：**2599.228584秒 = 43.320476分钟**。
- 监督进程记录的子进程CPU：user 9591.877862秒，system 803.120079秒；合计10394.997941 CPU秒，约173.25 CPU分钟，包含MPI/包装器开销，不等于单rank物理计算时间。
- 峰值采样进程树RSS：**1015971840字节 = 968.90625 MiB = 0.94620 GiB**。这是采样值，共享页可能重复计数，不是连续峰值或OS隔离保证。
- NetCDF：**3581251512字节 = 3.33530 GiB**。
- 整个实际模型运行目录（含日志/监督记录）：**3590165254字节，约3.344 GiB**。
- 最低采样空闲磁盘：**1259.91992 GiB**，高于20 GiB门槛。
- 未触发模型超时、RSS、输出或磁盘资源门限；单个secondary卷约183.74 MiB，低于256 MiB门限。
- 主自动验收9.82893秒即被终止，峰值采样RSS约268.47 MiB；不是600秒超时或4 GiB内存超限。
- 独立只读核验5.93127秒，峰值进程RSS156.93 MiB；补充独立驱动核验0.41922秒。主自动验收与两项独立只读核验累计约16.18秒，不含跨日等待、编辑和Git。

历史估计42.6—43.0分钟是估计而非上界；本次43.32分钟仍远低于4800秒授权。资源原始日志仅本地保留，resource_audit.json及派生采样CSV/PNG不包含原始观测或完整日志。

## 4. NetCDF与输入SHA独立复核

独立流式计算全部35个NetCDF SHA，保存model_output_manifest.csv，并直接读取CF时间/year/mtime/iter。

- 18个primary卷、18个记录：03-09 00至03-26 00，各日一条。
- 17个secondary卷、408个小时记录：03-09 01至03-26 00，每卷24条。
- 无重复、缺失或错序；目标日03-25 00至03-26 00共25个整点帧，包括23:59:30查询所需的次日边界。
- 目标日全部25帧DEN/ZG独立检查：维度time,ilev,lat,lon；DEN原单位g/cm³，ZG为cm；转换到kg/m³和m分别乘1000和0.01。拒绝填值、NaN、Inf和非正DEN；ZG逐列单调。未裁剪或补零。
- 固定检查时刻为03-25 00、01、12及03-26 00，不挑选有利时刻；原生全压力层DEN范围和ZG范围见independent_verification.json，不能当作Swarm高度处误差。
- 独立重算408条暖态记录的f107d/f107a/Kp/hpower/ctpoten，共2040次比较，最大绝对差**5.68434e-14**，小于冻结1e-10门槛。

关键输入SHA：

| 输入 | SHA256 |
|---|---|
| 原冻结input | 56d13f1dd08e2ba3b1fd223eb4b7c0075e4b429c0eaa4d077065357342cbe100 |
| 扩展GPI | 5834bf48ebb6d024d5e3e0f8fe407649608699ba5b9091cd61ffdb2eb51223d4 |
| 模型二进制 | f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776 |
| 官方完整smax源 | a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7 |
| Swarm A CDF | d2f647f723f774a446e6c07c9b1108c1dc521b76bb21a2d524d321d379b440a8 |

冷启动首primary为原生完整状态echo，其计数继承源场，不能直接相减；primary本来不要求凭空补造DEN/ZG诊断。完整17天暖态多变量主验收没有形成落盘PASS；目标日独立专项通过不替代全流程正式验收。

## 5. Swarm A沿轨覆盖

主自动验收在加载HourlyTiegcmObservation时被停止，没有落盘完整查询数量。不得宣称主验收已经2880/2880通过。

独立复核直接解析CDF，确认2880条UTC30秒/flag0/正且有限密度及有效坐标；从GRS80同一XYZ独立转WGS84，按原Map-A假设自行重建时间和水平邻点、垂直log密度插值。

- 合格观测：2880。
- 独立查询成功：**2880**。
- 独立查询失败：**0**。
- 八列检查：**23040**，零权重列不跳过。
- 无时间、水平或垂直外推，未剔除失败样本以改善覆盖率。

只验证查询与数值有效性，没有计算AI/物理模型与观测的RMSE、relative RMS或任何校正系数。仍为PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED。

## 6. 自动验收为什么失败

自动验收监督记录：CONTROLLED_STOP、returncode=-15、fatal_log_pattern、cleanup verified。未生成acceptance.json。

原始警告说明NetCDF的missing_value属性不能安全转换为变量类型；Python随后附带显示两行源码，其中包含`np.nan`。冻结监督器统一致命日志正则（不区分大小写）恰好匹配这两个源码片段，将验收进程终止。原日志SHA和结构化诊断见postrun_failure_analysis.json、source_manifest.json，完整日志留本地。

**源码中出现np.nan不等于数组内存在NaN。** 目标日独立显式填值/有限性检查通过；但不能因此忽略属性告警、放宽检查或强行将主验收改为PASS。程序顺序显示中止发生在查询阶段，然而未形成完整落盘验收文档，所以不以执行顺序推断代替正式验收结论。

本轮未改冻结执行器/监督器/坐标接口，未重新调用主验收或重跑模型，所有一次性标记、失败记录和原始输出保留。独立脚本exit0表示独立检查已执行完，JSON总状态仍为ENGINEERING_FAIL；这不构成主验收重试，也不覆盖主失败。

## 7. 当前状态与人工处置建议

- ACTUAL_MODEL_RUN=COMPLETED；24480步、模型MPI/四rank退出0。
- AUTOMATED_ENGINEERING_ACCEPTANCE=FAIL_INCOMPLETE。
- INDEPENDENT_TARGET_DATA_AND_COVERAGE_CHECK=PASS。
- **总状态ENGINEERING_FAIL**：针对冻结工程验收链未闭合，并非断言物理积分失败。
- NEXT_DENSITY_EVALUATION=BLOCKED_PENDING_ACCEPTANCE_CLOSURE。

下一轮建议只授权：最小NetCDF告警复现、只读验收阶段日志分类修复/审查、针对已有35个输出重跑一次只读完整工程验收。**不需要、也不建议重新进行17天积分**；不删除任何预约。

修复必须区分Python源码提示文字与真实NaN/Inf/致命数值异常，保持原模型日志监控及NetCDF掩码、有限性、正值和所有容差；不能直接忽略NaN或压制警告来获取PASS。新只读审计使用独立目录和新批准的代码身份，保留本轮失败记录。

在完整工程验收闭合前，不直接开始2022-03-25正式误差评价。之后仍须单独授权，沿用冻结历史窗口、方法、参数先冻结/poison、共同样本及四项联合指标，2021结果只读比较。

SCIENCE_TRAINING_READY=False，EXTERNAL_DATUM_UNVERIFIED，RestartFAIL，DARTNOT_ADMITTED，REAL_ORBITBLOCKED及A14历史身份不变。真实模型完成不证明观测精度、充分预热、ZG零面或校正跨年收益；本轮完成整理后停止。
