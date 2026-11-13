# 2022 B14探索性v2连续模拟工程验收

协议在启动前冻结；用户本轮明确选择方案B。没有调用旧B14入口，没有重跑A14，无Restart/自动重试。4-rank非物理MPI短测试0.622844秒、父wait rc0、四rank均同会话、清理通过；不是物理模拟预热证据。

|项|实际结果|
|---|---|
|真实TIE-GCM启动|1次|
|积分|2022-03-09至25，23040步，60秒/4MPI/OMP1|
|监督墙钟|2429.787854秒|
|真实退出码|0，direct subprocess.Popen.wait|
|监控资格/缺口/清理|PASS / 0 / True|
|采样进程会话RSS峰值|943.871MiB，非瞬时严格上界|
|CPU user/system|8965.414/749.588秒，子进程rusage差值|
|NetCDF|3371589248字节|
|主/小时次记录|17/384|
|实际驱动最大差|2.8422e-14|

每卷≤256MiB，B14新增≤5GiB、聚合会话采样RSS≤16GiB、余盘≥20GiB，计入既有A14后的总输出≤12GiB。监督运行截止4770秒，为4800秒总上限预留30秒清理/最终检查，预算未扩大。
全部33卷SHA/绝对日历/DOY/步长/网格/原生单位/填充、DEN正性、ZG递增、温度风及组分工程检查通过。2304个实际10分钟驱动日志节点及384暖态记录核验；冷echo继承源标量不当作实际驱动差。
可执行SHA `f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776`。
完整输入/协议/代码SHA见input_manifest.json、protocol.json及B14/data_audit.json；原status.json保留直接父子等待证据，派生run_status.json明确引用其SHA。

工程身份：2022 A14数据完整PASS、历史工程PARTIAL、真实退出码UNKNOWN；B14按本轮独立工程审计PASS。仅探索性v2条件比较，不是原v1双轨完整工程PASS。SCIENCE_TRAINING_READY=False、EXTERNAL_DATUM_UNVERIFIED保留，原122帧不改。

运行端日志四rank一致记载实际执行2026-11-12 09:21:42—10:02:11（环境Etc/UTC）；2026-11-13按用户继续指令接续整理。文件系统launch marker的mtime与运行端钟存在约85秒差异，原因未独立确认，原始记录均保留；监督预算使用monotonic，不用文件mtime计时或追认冻结顺序。协议冻结次序由启动代码的SHA校验及父进程事件链证明。
