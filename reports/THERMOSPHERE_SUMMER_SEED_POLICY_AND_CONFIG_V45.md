# V45 夏季初态政策与离线配置

**V45_CONFIG_DESIGN_COMPLETE**。隔离草案通过静态验收；夏季 B 政策待批准；所有年份 RUN_READY=False。基线 HEAD 与远端 main 均为 `6e5c574fcabd8a3a355a4db980dda7ea9604191e`。

## 科学建议

**SUMMER_SEED_POLICY_B_JUNSOL_RECOMMENDED / SUMMER_SEED_POLICY_RECOMMENDED_PENDING_APPROVAL**。建议两年夏季统一使用 V44 junsol SHA，使初态条件一致，各年继续使用独立真实 GFZ。确认无覆盖本轮夏季 junsol 的既有用户批准。junsol 与 mareqx 均为 2002 年 smax，原生太阳通量均为 200/200 sfu。同为 5° 网格及 34 项 native 状态，两者主要差别是夏至与春分原生日历及对应物理状态。junsol 季节标签更匹配。两年份即使共用一份夏至初态，也可能出现共同初态偏差及依赖各年强迫的不同调整速率。高太阳活动初态可能产生温度、密度、风和成分的调整瞬态；200 sfu 属于种子背景。2022 起始 GPI 独立参考为 f107d=97.1625、f107a=127.6911265 sfu、Kp=2.3335。2021 真驱动仍缺两日，未生成该年 GPI。

待批范围与验收条件见 policy_proposal.json。NCAR 无独立发布 SHA，V44 的本地完整性及产品身份结论保持。

## 配置和时间迁移

草案 `2022_summer_offline.namelist.draft` SHA256 `851f33b2fb69389bc62b28f194e93691a5b8e49f3c1be1d5afcf7ca0e774eef9`。只替换 V23 模板标签、夏季日期和两项数据路径。原物理设置（HEELIS、氦、5° GSWM、输出字段）保持。未来工作目录单列，当前未创建；通过 `PROJECTROOT=/workspace/data/20261016` 展开源和 GPI，相对输出卷仅允许在新工作目录中解析。预期 17 个逐日 primary、16 个 secondary 卷共 384 小时记录；首 primary 是冷源回显。科学目标 06-21 00Z 前有 14 天，连续积分从 06-07 00Z 到 06-23 00Z，UTC。STEP=60、23040 步、MPI=4、OMP=1、GPU=0。

`SOURCE_START=172 0 0` 选择原件中 2002-06-21 00Z 的记录。目标 `START_YEAR=2022`、`START_DAY=158`、`START=158 0 0`、`STOP=174 0 0`、`CALENDAR_ADVANCE=1`。input.F 948–960 要求小时和分钟匹配，允许日序不同。init.F 用 START_YEAR/START_DAY 建立目标日历，hist.F 分别登记目标和源时钟。advance.F 在设置 GPI 且未用常量覆盖时调用 getgpi，以目标日历更新太阳与地磁强迫；冷源回显可能仍保有源标量。保持原生 year/day/mtime；使用显式 SOURCE 的冷启动，不做续算，不重标初态时钟。真机首次读源、冷回显、步进强迫更新及完整输出仍待验证。

## 静态验收

冻结 V37–V44 的 68 个发布及原始条目逐项核对，四份 2022 GFZ 原件、原/副本 TAR、junsol、V43 GPI 和 V23/27 模型与库合同均匹配。Python 检查 34 项状态并解码原生 UTC。独立调用冻结 NetCDF-Fortran ABI 对真实原件只读获得 year=2002、day=172、mtime=[172,0,0]。冻结模型 ELF 和 65 项解析到的动态库 SHA 一致。MPI 版本 Open MPI 5.0.8，仅查询版本；无 rank 运行。容量快照约 14 等效 CPU、275 GiB 可用内存、1245 GiB 可用盘，超过本方案最低容量。运行前仍须核对实时资源、队列/监督、工作目录和授权凭据。

16 项 CPU 负例均拒绝；另外从 CLI 请求运行实测拒绝。未创建运行目录、启动模型、使用 GPU 或解封夏冬密度。V37 方法、λ=0.5、日期顺序保持。正式 GPI/input、校正拟合、科学打分、AI、DART 及轨道均未执行。

## 预热敏感性和下一步

最小设计为另行获批的 2022 同驱动、同物理参数、同窗口的两路连续 16 日纯工程配对。仅改变源 SHA 和 SOURCE_START，A=mareqx、B=junsol，逐个执行，每路至多一次。比对日龄 1、3、7、14 的同小时 DEN、TN、水平风与 O1/O2/N2/HE，报告公共原生层、共同原生 ZG 高度、纬区覆盖和 6 小时演变。沿用既有 A14/B14 冻结比较限度（DEN/组分 5%、TN 10 K、水平风 20 m/s、区域时层至少 95% 通过，组分参考 floor 1e-8），事前冻结窗口和末 24h 非增长诊断。稳定性不达或覆盖不足继续保持未收敛；有限对照即使通过也仅支持配对条件下的初态不敏感。禁止外推与用未来 Swarm 密度择优。

V37 正式 integration 阶段需要 Swarm 身份证据，并要求 2021 先独立验收。两份 ESA 0301 ZIP 均未取得。2021-05-09 和 06-16 Fobs 缺口保留，禁补值。2022 纯物理工程方案在科学验证流程之外可单独审查，未来须先获明确范围批准及一次性 CPU 执行授权；如拟计入 V37，必须走现有顺序和全套门禁，变更须另行做前瞻性协议审查。建议 V46 先决定 B 政策，并在解决真实 GFZ 缺口和交接两份 ESA 原件的同时决定是否单独授权 2022 纯工程配对。RUN_READY 仍为 False，外部 ZG、固定偏移、实时 as-of、Restart、训练、DART、真实轨道门禁保持。
