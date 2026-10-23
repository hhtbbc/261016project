# 2022九天连续TIE-GCM工程验收

INDEPENDENT_TIEGCM_DATA_GENERATION / HINDCAST / SPINUP_SUFFICIENCY_UNVERIFIED / VALIDATION_CANDIDATE_ONLY。

一次mpirun从2022-03-16 00:00至03-25 00:00 UTC连续积分，4MPI/OMP1、60秒、12960步。没有Restart拼接、冷启动短例重跑或2021重跑。每日primary10记录/10文件、逐小时secondary216记录/9文件，全部时刻有序唯一、无跳帧；验证候选起点03-23 00含在49个整点记录内，预热167个小时记录未提取入候选目录。

## 资源与运行

|指标|实测|
|---|---:|
|监督端到端墙钟（含最终轻量卷检查）|1355.167537 秒|
|采样聚合树RSS峰值|946.609 MiB|
|子进程user+system CPU|5413.352 秒|
|NetCDF|1903952612 字节|
|运行目录与stdout生成量（提取前）|1905257784 字节|
|MPI退出/正常退出数|0 / 4|

3600秒/16GiB树RSS/5GiB新增/每卷256MiB/磁盘余量20GiB监督均未触发；单次launch_once且无重试。RSS0.1秒采样并重复计算共享页，可能漏瞬时峰值。运行时仅检查已关闭卷，最后逐卷复核；进度采样与在线已验卷数完整保留。

## 输入、日历及驱动

GPI `9bf83f53133a9290002d72300705681fc9da9ee89b2d2ed712271cdc799ec6f7`；可执行 `f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776`；2002初场 `180475215a4922e9c55a77e80153cf641bc8fbb2b8d52633b4686ddee6942fff`；apex `7dc94d3826d1b8d555fa6a6dea26e2a3788fbca2a86581aff3bcdefb52c5cdc3`。完整namelist/输入/代码SHA见preflight及configuration.json。START_YEAR2022、START_DAY75、STOP85，SOURCE_START80仅选择2002初猜记录。HEELIS、GSWM、更新IGRF14/apex及原SECFLDS均未裁减。

实际每10分钟驱动日志1296个唯一节点通过打印精度0.000501核验；所有暖态NetCDF驱动最大标量差2.84e-14<1e-10。F107范围94.212346—111.98125 sfu、F107A 118.98525—119.684 sfu、Kp 0—3.2775。与既有GpiDriver/新GPI独立插值门禁一致。逐分钟合法域静态计算检查12961节点，不能冒称逐分钟内部观测trace。全部8次午夜及最终第9日端点连续推进，无驱动越界。

## 物理字段

|字段|原生单位|有效最小|有效最大|掩码数|
|---|---|---:|---:|---:|
|TN|K|146.85373|1021.4897|559872|
|UN|cm/s|-56562.066|56406.152|559872|
|VN|cm/s|-59163.848|60644.84|559872|
|WN|cm/s|-570.56091|912.29218|0|
|Z|cm|9566623|64068180|0|
|DEN|g/cm3|9.0488245e-17|1.2009058e-09|0|
|ZG|cm|9566623|63318088|0|
|NE|cm-3|1055.8395|1988550.4|0|
|TLBC|K|157.86171|198.09871|0|
|ULBC|cm/s|-5738.9087|4378.6475|0|
|VLBC|cm/s|-6406.4517|6622.3213|0|
|f107d|1.e-22 W/m2/Hz|94.212346|111.98125|0|
|f107a|1.e-22 W/m2/Hz|118.98525|119.684|0|
|Kp|None|0|3.2775|0|

14键逐卷齐备、有限；DEN正、ZG逐列垂直严格递增；TN/UN/VN仅lev顶层全填充，保留28个有效层。WN/Z/DEN/ZG/NE等ilev29。TN100—5000K、水平风绝对值<2000m/s和组分0—1/质量分数和的既有宽工程范围通过，不能据此认定所有物理偏差已解决。

lat36/lon72/lev29/ilev29与作者普通static坐标逐元素一致。DEN原生g/cm³转SI乘1000，风cm/s乘0.01，Z/ZG cm乘0.01；Z是位势高度，ZG是几何高度。原生ZG450km诊断无外推，报告有效覆盖率0.99691358—1；不等同WGS84 450km或Swarm沿轨密度。

global all-level密度均值受低层大密度主导，只作结构监控；另绘制原生450km全球/纬带及P95、TN、风、组分、ZG中位剖面及驱动。最大全球450km相邻小时变化9.4560%（2022-03-16T01:00:00+00:00→2022-03-16T02:00:00+00:00），这是自然时间变化的诊断，不是初始化误差、模型精度或因果判定。不能只凭均值平稳宣布收敛。

primary起点含继承初猜，未计算诊断N/A不补零，不参与验证候选。次历史虽为暖态诊断，预热充分性尚未证实。没有非有限/非正DEN或基本温度工程门禁失败。

## 图与审计

results/tiegcm_training_mar23_v2_2022_longrun：density.png、latitude_bands.png、temperature_wind.png、drivers.png、composition.png、ZG_structure.png；hourly_diagnostics.csv包含216小时及候选/预热分类。全部图来自本次实际输出。NetCDF每卷SHA/UTC/字段与每帧NPZ SHA分别在data_audit.json/candidate_audit.json，大数组只保留本地。

本轮最终11项聚焦测试通过。实际NetCDF格式/dtype及每卷SHA见data_audit.json；原始stdout、配置和日志完整保留，候选不上传Git。原生有效范围工程PASS不能代替真实大气或卫星轨道精度验证。
