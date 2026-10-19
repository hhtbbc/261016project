# TIE-GCM 2023首次启动诊断

## 结论与授权边界

仅运行**一次**2023-03-18 00:00—00:10 UT模型积分。原5°、4 MPI进程、60秒步长，10步，使用原2002春分smin完整restart作数值初猜；没有改restart日期或物理场，没有额外2002/2023模型运行、没有3/7天spin-up。日历、GPI实际读取、数值推进及基础输出检查通过。**不是平衡2023场，不能用于Swarm-A真实阻力精度评价。**

运行目录`experiments/tiegcm2023_startup_10min_v1`；完整日志`logs/tiegcm2023_startup_10min_v1.log`；本报告中的结论由同目录preflight.json、run_status.json、diagnostic_audit.json、solar_audit.json、input.inp支持。

## 运行前验证

开始时本地/远端main一致于70e9ab09f61f1da6d0b1b51679cfd26da3fb43d3，Git干净。沿用scripts/activate_tiegcm.sh，未安装环境、下载数据或改第三方原树。编译栈版本/可执行SHA见preflight和已有logs/tiegcm2_stack_manifest.json。

apex构建`experiments/tiegcm2_apex2023_v1`原有可执行及对象复用：本地覆盖apex源码SHA与官方provenance一致，Srcfiles只有一个apex.F90、Depends指向本地覆盖层，nm三个关键符号各一次。源码/对象/实际可执行哈希留档，不重新构建。更新为2.0主体+官方apex更新+既有GNU12兼容覆盖层，非纯原始2.0。

GPI SHA256 `60fa18244fcdbd8b1bb5300bda86cde68abcca9a9152539bcdc5fc30377aa9f6`与既有驱动审计一致，14个日值、112个Kp，合法模型日期03-14—23，计划日77及前后两天完整。所有3个官方startup/GSWM资产SHA通过。restart SHA `180475215a4922e9c55a77e80153cf641bc8fbb2b8d52633b4686ddee6942fff`，原记录year=2002、mtime=80 0 0；预报变量及leapfrog前一步变量存在。首次静态检查错误地要求restart含N2，实际N2为主要组分诊断量，已修正为核查真实预报量和_NM；发生于模型启动前。

运行前空闲盘716407046144字节，MemAvailable约1.93e9 KiB；本次资源足够。全部输出/临时路径工作区内，无外指路径。

## 配置及真实语义

| 参数 | 实际值/含义 |
|---|---|
| SOURCE_START | 80 0 0，仅选择2002源文件的记录 |
| START_YEAR / START_DAY | 2023 / 77 |
| START / STOP | 77 0 0 / 77 0 10 |
| CALENDAR_ADVANCE / STEP | 1 / 60秒 |
| HIST / SECHIST | 每5分钟；次历史从00:05开始 |
| POTENTIAL_MODEL | HEELIS |
| GPI_NCFILE | 项目内gpi_20230312_20230325.nc |
| F107/F107A/KP/POWER/CTPOTEN及_TIME | 全部省略，静态门禁拒绝固定/时间序列覆盖 |

rdsource.F只读SOURCE_START选中旧历史；hist.F对有SOURCE的新运行设置目标初始日历。运行日志4rank均打印`init: iyear=2023 iday=77`，apxparm明确start_year=2023；主历史year/day皆2023/77、calendar_advance=1。time实际解码为00:00、00:05、00:10，次历史00:05、00:10。不是仅修改标签：首步getgpi明确请求year=2023、day=77、iutsec=60，随后10个独立时刻均有GPI报告并与独立输入匹配。

## 实际驱动与冷启动记录

| UT | F10.7 (sfu) | F10.7A (sfu) | Kp | POWER (GW) | CTPOTEN (kV) |
|---|---:|---:|---:|---:|---:|
| 00:00初始历史 | 70 | 70 | missing约1e36 | 18 | 30 |
| 00:01首步 | 137.029554832 | 161.800899556 | 2 | 27.038808390 | 48.2 |
| 00:05 | 137.047782765 | 161.800793946 | 2 | 27.038808390 | 48.2 |
| 00:10 | 137.070586770 | 161.800661637 | 2 | 27.038808390 | 48.2 |

**t=0包含继承的源标量/物理场，不是2023驱动结果。** 从首步60秒起调用GPI；5/10分钟主/次历史全部5项驱动与独立计算差<1e-10，最大2.8422e-14。日志每分钟的4项f8.3打印误差<=0.000501，共10个独立时刻、4rank重复记录。独立太阳日值采用原gpi.F正午锚定四点三次插值的通用Lagrange实现；Kp使用前日22:30/本日01:30线性插值。该窗口两相邻Kp均2，所以Kp/功率/电势恒定符合输入，非固定覆盖。

原stdout某处CTPOTEN文字误写Volts，而NetCDF单位kV及util公式/HEELIS定义是kV；本报告采用kV。不根据这个旧打印标签错误将数值再除1000。Kp由输出保存为2，初始missing保持缺失，不当成真实磁暴值。f107a为中心81日平均，属于hindcast。

## 太阳与地磁路径

原tgcm.F以real(start_year)=2023.0建立apex映射；advance.F每步调用sunloc_apex(iyear,iday,secs)，magfield.F再调更新对象中的subsol与cofrm分数年。保留该原实现，未暗中将映射初始化改成分数年，也未消除其年度映射近似。

为独立检查日历太阳例程，单独链接同一apex.o调用subsol（**不是模型积分**）并与Astropy get_sun→ITRS、冻结IERS-B比对。0/5/10分钟最大纬差0.00076531°、经差0.00771561°，在源码给定0.01°/0.025°算法精度内。审计solar_audit.json。实际积分未增加太阳坐标打点：其证据是实际年/日/UT+原调用链+相同对象函数核对，不宣称直接记录了运行内每个太阳坐标。初始温度/光化学几何也采用原init.F随DOY的太阳赤纬近似，尚非高精度天文改造。

## 退出、资源与物理场

returncode=0，4条NORMAL EXIT，10步，墙钟2.396588秒；0.1秒采样进程树/进程组合计RSS峰约941.46MiB（共享页重复计入、可能漏采瞬时峰值，不是精确物理驻留总量）。NetCDF总67015120字节，约63.91MiB。墙钟上限60s、单进程CPU60s/地址空间8GiB/单文件512MiB、总输出512MiB、采样RSS16GiB、剩余盘10GiB停止门槛均未触发；core禁用。原restart SHA前后不变；退出后没有残留该模型进程。

| 场 | 实际定义/有效范围 |
|---|---|
| DEN | 次历史(time,ilev,lat,lon)=(2,29,36,72)，g/cm³；全垂直域SI 1.34999648e-13—1.19784682e-6 kg/m³，全部有限正值 |
| ZG | 同ilev，cm→m乘0.01，所有列严格递增；5分钟顶449.03812—510.97656km，10分钟顶449.09100—512.38628km |
| TN | (time,lev,lat,lon)，有效147.7730—787.0666K |
| UN/VN | cm/s，有效UN约-317.433—301.117m/s、VN -299.791—309.853m/s |
| O1/O2/N2/HE | mmr质量混合比，次历史均存在/无mask/范围0—1；四者和0.999999881—1.000000119，符合float32舍入 |

TN/UN/VN的最高lev是已知整层padding，主历史各7776、次历史各5184个填值；显式将marker转换为变量dtype后掩码，没有内部有效层缺失。组分顶层实际有值，不应套用温度/风的padding要求。审计脚本首次误将该要求套到所有组分而断言失败，已按真实变量修正，原失败日志logs/tiegcm2023_startup_audit.log保留；修正后验证通过，**未重跑模型**。

stdout无NaN/Inf/ERROR/WARNING模式，场检查无未掩码NaN/Inf；有效温度100—5000K、风绝对值<2000m/s是宽松启动筛查，不是精密物理认证。全域密度范围不能当作Swarm高度密度范围。原生ZG与WGS84基准未闭合，仍不能统计实际Swarm有效查询率；此日期也早于03-21轨道窗口。

图`results/figures/tiegcm2023_startup_10min_v1_native_fields.png`展示00:10原生顶高和ZG=400km log密度插值，标题明确NOT spun up，不做高度外推、不作Swarm查询；已目视检查。2002与本例共用同一冷初猜，目标日历、地磁场及驱动不同；短时差异不能作为真实太阳活动响应实验。

## 测试、保护及复现

4项新增静态门禁、全套35项测试通过（6.739s），logs/tiegcm2023_startup_all_tests.log。旧659个受保护文件SHA不变，logs/tiegcm2023_startup_preservation.json。模型仅一次launch_once.json；太阳函数探针和只读审计不计额外模型仿真。

```bash
source scripts/activate_tiegcm.sh
python scripts/run_tiegcm2023_diagnostic.py --run-tag 新标签
# 静态PASS后，仅在再次获准运行时执行下一行；本次授权已经使用
python scripts/run_tiegcm2023_diagnostic.py --run-tag 新标签 --execute
# 本次已有输出可直接检查，审计输出存在时脚本会拒绝覆盖
python scripts/audit_tiegcm2023_diagnostic.py --run-tag 新标签
```

脚本固定日期/长度/4rank，不支持自动延长；同目录launch_once使用独占创建拒绝第二次启动。未来新的run-tag并不代表自动获得新授权。本次原始NetCDF继续本地，Git只同步脚本、配置、审计、完整小日志、测试和图。
