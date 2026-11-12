# 2022 smax九天连续积分工程验收

标签：tiegcm_2022_dual_initial_spinup_v1。独立B7对照场，不替换原49帧验证候选，不新增训练NPZ。

|项目|实测|
|---|---:|
|积分步数|12960|
|监督墙钟秒|1374.713820|
|峰值采样进程树RSS MiB|949.137|
|NetCDF字节|1903953476|
|primary/secondary记录|10/216|
|正常MPI退出数|4|

全程从2022-03-16 00至03-25 00，一次启动、4MPI/OMP1/60秒，无续算或重试。预估和实测分离；3600秒/16GiB/总新增5GiB/每卷256MiB/余盘20GiB门槛未扩大。实际CPU user/system见run_status.json；采样RSS包含重复共享页且可能漏瞬时峰值。

可执行SHA `f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776`；smax SHA `a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7`；GPI SHA `9bf83f53133a9290002d72300705681fc9da9ee89b2d2ed712271cdc799ec6f7`。

smax来自既有NCAR官方2.0分发目录，文件内部保留trunk/历史1.95来源身份，不能单凭文件名认定物理条件；实际34项double当前/NM/下边界、网格、2002年DOY80 00:00记录全部核验，与smin掩码/单位相容。没有改写时间戳。原namelist只更改SOURCE，输出身份由独立cwd区分，LABEL保留历史文字。

原始冷echo继承smin/smax各自源标量，因此t0源F107并不相等；不是固定参数覆盖。暖态输出与实际GPI日志核验，各同历元F107/F107A/Kp/hpower/ctpoten完全一致，冷echo不作为物理诊断样本。

全部19个NetCDF卷SHA、时间/网格/单位/掩码、DEN正性、ZG逐列递增及温度风场/组分宽工程范围通过；14必要字段保留。没有以工程范围通过代替科学预热通过。完整逐卷审计见data_audit.json。
