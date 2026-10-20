# S3连续多日TIE-GCM运行报告

## 结论

本次仅启动一次S3模型：2023-03-18 00:00→2023-03-23 00:10 UTC，7210个60秒步长，连续推进DOY77—82，4 MPI/5°/单rank单线程/无GPU。returncode0，4条NORMAL EXIT，无自动重试、continuation、S7或卫星轨道积分。已取得3天候选预热后48小时10分钟的290帧共同窗口物理场；不是已证明收敛或观测准确的大气产品。

真实运行UTC为run_status.json所记2026-10-19 08:58:34.581542至09:11:41.387085；会话于2026-10-20继续收尾，不能把模型目标2023历元当成执行日期。

## 环境、配置与门禁

source scripts/activate_tiegcm.sh，复用.envs/tiegcm及原TIE-GCM2.0+已验证官方apex/IGRF覆盖构建；原第三方源码未改。可执行、apex、GPI和2002初场SHA逐项匹配连续基线，见preflight.json。SOURCE_START80 0 0选原合法完整场，START_YEAR2023、START_DAY77，CALENDAR_ADVANCE1，GPI/HEELIS、无固定F107/F107A/KP/POWER/CTPOTEN及_TIME覆盖。2002场只是数值初猜。

START/STOP/HIST两组相接调度仅控制输出，不中断advance循环。原生SOURCE冷启动只在开始使用一次，没有使用失败的Restart路径。预计并实际得到7个primary文件、14个secondary卷；旧方案13卷估算已纠正：numfiles.F在新输出序列开始时另开卷，第一卷4帧，第二序列289帧分13卷。secondary共293时间记录，3月21日起共同窗口290帧；无重复/缺失或超终点记录。

## 资源实测

|项目|实测|授权限制|
|---|---:|---:|
|墙钟|786.805456秒（13分6.805秒）|1800秒|
|聚合RSS采样峰|993308672字节，947.293MiB|16GiB|
|children user CPU|2872.702240秒|每进程2100秒未触发|
|children system CPU|264.704853秒|同上|
|NetCDF总量|2471152364字节（2.3014GiB）|本任务产物4GiB|
|最大NetCDF卷|192668980字节（183.743MiB）|256MiB目标|

CPU为原MPI等待进程的RUSAGE_CHILDREN报告，不能冒称精确逐rank核算。RSS为进程树加总，包含共享页重计且可能漏瞬时峰。effective_resource_status.json合并原监控和guardian峰值；不能只用原run_status.json里接管前的较小峰值。最终全部本次产物占用见final_safety.json，未触发4GiB/余盘20GiB等限制。

## 运行监督中的修正（完整披露）

output.F302—306说明首次secondary输出前addfld尚未调用，初始诊断量没有定义。实际3月18日00:00的DEN/ZG等是填充值，不能视为数值发散，更不能填作实际2023密度。原监督器把该记录也要求全域正有限，是监督器的缺陷。发现后仅修正读取/分类逻辑，保留冷记录及其缺失掩码，不改NetCDF、物理状态、模型可执行或积分流程。

为避免已启动监督器随后误停有效模型，在同一MPI进程组持续运行下，于约279.74秒将原Python监督器暂停在sleep等待点，独立guardian接管原有墙钟/RSS/磁盘/文件与温度/风/组分门禁；模型进程没有暂停或重启，原CPU/文件限制继续生效。guardian正常结束后恢复原Python父进程，取得真实退出码。supervision_handoff.json记录PID及接管时刻；原监督器检查1个完成卷，guardian检查19卷（有重叠），全部输出最终独立复核。

接管识别前两次检查分别因MPI实际进程名prterun及Python睡眠等待名poll_schedule_timeout与最初预期不同而终止，均未启动模型或改变进程；确认真实进程后才完成接管。这些是监控工程事件，不是模型自动重试。新交付运行器已在启动前处理冷echo缺失，并有“冷echo允许标缺失、暖态缺失必须拒绝”的测试；通常不再需要guardian。

## 实际时间、驱动与数据审计

721个唯一Step打印点覆盖10、20…7210，四rank各有同样的721个打印点；全部五次日界切换被日志确认。7个primary原生时间和293个secondary时间与独立调度完全一致。721个实际runtime GPI打印时刻按其小数位核对；模型存储的F107/F107A/Kp/POWER/CTPOTEN与独立源码约定插值最大差5.684e-14。没有以配置值推算代替实际读取证据；冷初始标量回显单列，不用于真实2023驱动结论。驱动含事后def Kp和中心81日均值，本实验是hindcast。

## 复现入口与证据

```bash
source scripts/activate_tiegcm.sh
python scripts/run_tiegcm2023_s3.py --run-tag tiegcm2023_s3_continuous_v1
python scripts/run_tiegcm2023_s3.py --run-tag tiegcm2023_s3_continuous_v1 --execute
source scripts/activate_orbit.sh
python scripts/audit_tiegcm2023_s3.py --run-tag tiegcm2023_s3_continuous_v1
```

以上为已消耗授权的记录，不可对已有目录重放；prepare拒绝已有目录，execute以独占launch_once防重启。此次监督接管使用scripts/supervise_tiegcm2023_s3.py，仅附着已有进程，绝不启动模型，不需在完成后再次调用。完整模型日志logs/tiegcm2023_s3_continuous_v1.log；配置、preflight、run_status、guardian_status、数据清单/哈希及审计在experiments/tiegcm2023_s3_continuous_v1。自动化63项通过，日志logs/tiegcm2023_s3_delivery_tests.log。

## 下一步

工程结果支持另行申请S7连续对照，不能说明3天预热足够。按此次墙钟简单按步数线性估计S7约1415.4秒（23.59分钟），非实测；候选wall3000秒/CPU3300秒/4GiB输出/RSS16GiB，可保留26字段/10分钟共同输出与14卷设计。先完成独立S7静态门禁和授权；不运行S7、修复Restart或传播真实阻力轨道。
