# 新年份最小诊断

2026-10-23；INDEPENDENT_TIEGCM_DATA_GENERATION / HINDCAST / NOT_TRAINING_DATA。

| 年份 | GPI/静态门禁 | 正式启动 | 结果 |
|---|---|---:|---|
| 2021 | Fobs缺测阻断 | 0次 | 未验证新年份数值运行性 |
| 2022 | 通过 | 1次 | 00:00—00:10正常完成 |

采用现有4 MPI、OMP1、60秒步长，共10步；EGM/卫星轨道和AI均未运行。独立目录`experiments/tiegcm_training_d2022_v1`，一次性launch_once保护；没有重试、编译、修改第三方源码或任何历史模型场。

## 静态及实际日历

2022 START_YEAR=2022，START_DAY/START=95/95 0 0，STOP=95 0 10，CALENDAR_ADVANCE=1。SOURCE_START=80 0 0只选2002初猜记录，绝不代表2022实际大气。HEELIS/原GSWM/完整物理配置保留，删除固定太阳地磁覆盖，GPI路径冻结SHA。2021同为DOY95，但未通过驱动门禁，不把日历静态支持当作已运行成功。

复用更新apex/IGRF14的2020/2025历元覆盖2021/2022；原作者旧apex不改。可执行文件SHA `f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776`；初始场SHA `180475215a4922e9c55a77e80153cf641bc8fbb2b8d52633b4686ddee6942fff`；apex SHA `7dc94d3826d1b8d555fa6a6dea26e2a3788fbca2a86581aff3bcdefb52c5cdc3`。模型前后初始场一致。

历史同配置10分钟2.3966秒，乘8估计19.17秒后启动；磁盘>20GiB。监督限制60秒/16GiB聚合RSS/512MiB输出；实际2.489824秒、MPI退出码0、4个NORMAL EXIT、峰值992227328字节RSS（约946.26MiB，0.1秒采样含共享页重复计数），NetCDF67015120字节。所有限制内正常退出。

## 输出检查

primary为00:00/00:05/00:10三帧，secondary为00:05/00:10两帧。实际年份2022、DOY95，模型读取2022 GPI，10个每分钟驱动日志及两类暖态NetCDF标量通过独立核验；无新年份/apex错误或日志NaN/Inf/警告。

secondary含全部14键：TN/UN/VN/WN/Z/DEN/ZG/NE/TLBC/ULBC/VLBC/f107d/f107a/Kp。lat36/lon72，lev29含TN/UN/VN顶部padding，实际有效28层；ilev29。缺测mask保留，不补0；DEN正值、ZG垂直严格递增，TN/风和主要组分通过既有诊断范围检查。字段形状、单位、掩码、有效最值见`fourteen_fields.json`，每个输出SHA见`diagnostic_audit.json`。

保持作者原生契约：DEN g/cm³到SI乘1000，风cm/s到SI乘0.01，Z为位势高度cm，ZG为几何高度cm，二者不能混用；没有生成NPZ或套用WGS84转换。

00:00为继承初猜，诊断量可未计算，标N/A；00:05/00:10仅短时暖态数值记录，**不是充分预热场，所有本次输出均禁止作为训练或科学验证样本**。未经历跨午夜，所以本次不证明多年日界及长期物理稳定性。

11项聚焦自动化测试通过（8驱动+3配置），非重新运行全部247项，也没有重复GPU合成训练。历史保护825项中824项SHA匹配；唯一旧清单差异为上一任务已提交的`docs/FOURCASTDEN_TRAINING_IMPLEMENTATION_PLAN.md`进度更新，本次git diff证实未改。科学资产/权重/旧S3/S7均无变化。
