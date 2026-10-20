# S7连续9天10分钟运行报告

## 实际执行结论

一次S7从2023-03-14 00:00（DOY73）连续积分至2023-03-23 00:10（DOY82），12970个60秒步长，4MPI、5°、每rank单线程、无GPU。返回码0、4个NORMAL EXIT、无停止原因。未重试、未使用continuation、未暂停模型或接管监控；未修复Restart、未训练AI或执行轨道传播。

实际执行UTC：2026-10-20T00:55:51.087861+00:00至2026-10-20T01:18:53.764356+00:00，不是模型2023目标日期。

## 实测资源

|项目|实际|授权上限|
|---|---:|---:|
|墙钟|1382.676454秒，23分2.676秒|3000秒|
|聚合RSS采样峰|990449664字节，944.566MiB|16GiB|
|children user/system CPU|5081.152858/437.268517秒|每进程3300秒|
|NetCDF|2571233644字节（约2.571GB）|本任务产物4GiB|
|最大卷|192668980字节，183.743MiB|256MiB目标|

RSS为进程组与递归子进程相加，可能重计共享页、漏瞬时峰。CPU由RUSAGE_CHILDREN报告，不是独立逐rank计量。原生监督器在线检查23个已完成卷，运行结束检查全部25个NetCDF；最后独立审计不依赖模型退出码。墙钟/CPU/输出/余盘/内存门禁未触发。模型已全部退出，最终证据见final_safety.json。

## 配置与资产

使用与S3相同TIE-GCM2.0+官方apex更新可执行、GPI、GSWM、HEELIS、CALC_HELIUM1、STEP60和5°网格，原源树未改，未重新编译或安装环境。SOURCE_START80 0 0读取原2002春分smin完整场作为初猜；目标START_YEAR2023、START_DAY73，CALENDAR_ADVANCE1。所有固定太阳/地磁覆盖项禁用。相接输出序列不重启advance循环。

S3/S7冷初始34项物理场逐位相同，公共物理配置相同，见controlled_initial_state_check.json。预热起日及早期驱动历史不同；比较是两种预热历史的敏感性实验，不是独立观测精度检验。

preflight.json核验S3原21个NetCDF全部哈希/结构、可执行/apex/GPI/原始初场SHA、12971个分钟节点驱动、磁盘/CPU亲和/MPI/内存及调度。其基础工具继承的expected_drivers是旧03-18烟雾检查点，不当成S7起始驱动；S7起日的明确独立期望在startup_driver_and_cold_policy.json，最终结论以实际运行/NetCDF逐时刻驱动核查为准。

## 冷启动监控与测试

从S3实物及源码确认冷echo中DEN、ZG、N2尚未生成；N2是诊断组分。S7仅在年份2023、DOY73 00:00、首记录、run_type initial、initial_year/day/mtime一致时允许这些原生未计算字段为N/A。冷TN、UN、VN、O1、O2、HE仍执行正常检查；任何暖态填充值、NaN、负密度、垂直倒序、温风越界或组分异常都拒绝。

启动前9项新增测试覆盖冷/暖缺失区别、冷TN异常、NaN/负密度、错误冷身份、调度与配置、防重复启动等。全套76项通过（logs/tiegcm2023_s7_all_tests.log）。没有依赖S3临时guardian机制，运行器自始至终独立监督。监控对已完成输出卷做物理检查，日志门禁持续；不声称每个未保存积分步都有完整场审计。

## 原生输出

primary每天00:00及最终00:10共11个单记录文件。secondary第一序列含03-14至03-21每日共8记录，第二相接序列去重后289记录，每卷最多24记录，分13卷，因此合计14卷/297时刻。共同03-21 00:00至03-23 00:10正好290帧。依据numfiles.F核验，不直接照搬预估文件数。

26个字段与S3一致，DEN/ZG在ilev，TN/风/主要组分在lev；完整primary保留规定34状态，但不宣称严格无损Restart。

## 复现入口（本次启动许可已消耗）

```bash
source scripts/activate_tiegcm.sh
python scripts/run_tiegcm2023_s7.py --run-tag tiegcm2023_s7_continuous_v1
python scripts/run_tiegcm2023_s7.py --run-tag tiegcm2023_s7_continuous_v1 --execute
source scripts/activate_orbit.sh
python scripts/audit_tiegcm2023_s7.py --run-tag tiegcm2023_s7_continuous_v1
python scripts/compare_tiegcm2023_s3_s7.py
```

prepare拒绝已有目录，独占launch_once拒绝第二次启动；执行前锁定runner SHA和input SHA，运行中没有修改监督算法。后两条命令为离线读数据，不触发积分；已有审计和对比标签拒绝覆盖。

工程验收通过不代表7天已收敛，也不意味着S7优于S3；科学敏感性结论另见S3_S7_COMPARISON报告。
