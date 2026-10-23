# Mar23 v2新年份启动诊断

2026-10-23；INDEPENDENT_TIEGCM_DATA_GENERATION / HINDCAST / NOT_TRAINING_DATA。

|年份|实际UTC窗口|启动次数|退出码|墙钟秒|聚合峰值RSS MiB|NetCDF字节|
|---|---|---:|---:|---:|---:|---:|
|2021|03-23 00:00—00:10|1|0|2.632098|946.035|67015128|
|2022|03-23 00:00—00:10|1|0|2.432667|942.391|67015128|

两年均4 MPI、OMP1、60秒步长、10步，日志各4个NORMAL EXIT。单次90秒/16GiB聚合RSS/512MiB输出/20GiB磁盘下限监督通过。RSS每0.1秒进程组及递归子进程求和，包含共享页重复计数，非连续精确峰值。

## 静态门禁

两年DOY82，START_YEAR实际年份、START=82 0 0、STOP=82 0 10；CALENDAR_ADVANCE=1。SOURCE_START=80 0 0只选择2002初始场记录，不能称为当年真实初态。两个GPI分别指向新v2并冻结SHA，无固定F107/Kp/POWER覆盖，原HEELIS、GSWM及完整物理过程保留。

复用原TIE-GCM2.0可执行SHA `f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776`、2002初场SHA `180475215a4922e9c55a77e80153cf641bc8fbb2b8d52633b4686ddee6942fff`、更新apex SHA `7dc94d3826d1b8d555fa6a6dea26e2a3788fbca2a86581aff3bcdefb52c5cdc3`。2020/2025 IGRF覆盖2021/2022，原件和第三方源码不改。历史短例2.3966秒乘8估计19.17秒后启动，预计远低90秒；未运行额外模型预检。

## 实际字段及时间

primary各00:00、00:05、00:10；secondary各00:05、00:10。每分钟实际GPI/POWER/CTPOTEN及NetCDF年份/day/UTC验证通过；未发现新年份或磁坐标错误，无NaN/Inf警告。10分钟不跨午夜，所以不能证明未来跨日长期稳定。

两年secondary全部14键齐全：TN、UN、VN、WN、Z、DEN、ZG、NE、TLBC、ULBC、VLBC、f107d、f107a、Kp。lat36/lon72/lev29/ilev29均与作者普通static逐元素一致。TN/UN/VN顶部全填充层保留掩码，有效28层；WN/Z/DEN等ilev29。有效TN、风、组分通过既有基本范围检查，DEN全部有限且正，ZG垂直严格递增，其他必需字段有限无填充。

原生DEN g/cm³、风cm/s、Z/ZG cm，SI分别乘1000/0.01/0.01；Z位势高度、ZG几何高度不能混同。兼容官方原始NPZ的单位/网格契约不代表已建立WGS84高度登记或与作者物理分布相同。

primary初始00:00含继承初猜/未计算诊断量，N/A不补零；00:05/00:10仅早期暖态。**全部本次记录均禁止作为有效训练样本**，也不比较两年短时差异为太阳活动因果。

11项新窗口测试通过；逐年运行日志、配置、输出SHA在`experiments/tiegcm_mar23_dYEAR_v2`，14字段/作者坐标检查在`experiments/training_window_mar23_v2/fields_YEAR.json`。没有重跑旧2022/2023实验，没有多日积分、真实训练、AI预测或轨道任务。
