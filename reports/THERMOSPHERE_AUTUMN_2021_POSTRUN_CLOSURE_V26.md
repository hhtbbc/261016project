# V26 2021 秋季 TIE-GCM 只读工程验收闭环

2026-11-23 UTC。**V26_POSTRUN_VERIFICATION=ENGINEERING_PASS**，**V24_ORIGINAL_ENGINEERING_STATUS=FAIL**。2021 原 run_id 为 `18726974f5d3450ba61f82c23c8da3a0`。2022 秋季仍为 `NOT_RUN`。本轮未启动物理模型、MPI rank、GPU、DART、AI 或轨道计算，未计算密度误差或校正参数。

## 资产和元数据

沿用 V25 已核实的 NVMe 项目根 `/workspace/data/20261016` 和原 Python 3.10 环境。V25 本地报告、751 项资产 CSV 和失败记录保留。V25 因 NetCDF 属性定位错误丢失 SHA 核查输出。V26 的 SHA 工具只用 Python 标准库和 1 MiB 二进制块，先独占写出逐卷证据，再进入 NetCDF 阶段。V24 发布清单 SHA 为 `8b44a39cc94962a99caee875451f7a4597ca9052864b6f92d11261b9e725a056`。当期 **33/33 卷、3,371,588,992 字节**的文件名、大小和 SHA 全部匹配，无缺卷、额外卷或读期身份变化。独立复核从实际目录重新核对数量、文件大小和 SHA。

新验收器读取 `time` 变量的 `initial_year`、`initial_day`、`initial_mtime` 和 `units`，读取全局 `history_type` 和 `run_type`，并与原生 `year`、`day`、`mtime`、`iter` 变量交叉核对。缺属性显式失败。V25 误认为两个日历字段位于全局的记录仍保留。

## 首卷例外和源码依据

`rdsource.F:40–55` 显式 SOURCE 分支按 SOURCE_START 读原源；`init.F:122–133` 将模型钟置为目标日历和步数。首步 `output.F:169–195` 使用 `hist.F:562–587` 的 `copyhist` 复制已选源历史结构，并拨到目标年、日及模型时刻，跳过常规 `define_hist` 的 `run_type='initial'` 赋值。`hist.F:202` 初始化为空白，`nchist.F:1966–1967` 用 trim 后长度序列化字符串。V24 原 rank 日志保留 copied source history 证据，V16 春季真实首卷也读到空串。源文件本身的全局 run_type 为 initial。

例外只适用于匹配发布 SHA 的 `primary_001.nc` 首记录。进入扫描前验证原始一次性预约、run_id、MPI 父直接 wait 和退出日志、四 rank 启动与直接退出回执、冻结 input/GPI/源/ELF、原主 FAIL SHA。显式 SOURCE 指向已冻结 mareqx；SOURCE_START 为 80 0 0，原生源为 2002 年 DOY80 00:00，iter 115200。首卷 CF UTC 和原生时钟为 2021-09-09 00:00，year 2021、day 252、mtime [252,0,0]，另须继承 iter 115200 并满足 34 个双精度原生状态及源结构、单位检查。每个暖态记录强制 `run_type='initial'`，按目标起点加累计步数检验 iter，末步为 385920。全程未放宽科学阈值或修改冻结代码。

## 工程结果

| 项目 | 单次主验收 | 独立复核 |
|---|---|---|
| 运行身份 | 父/四 rank 均 0，每 rank 2304 条进度，23040 步至 2021-09-25 00:00 UTC | 独立解析 direct-wait 日志、回执和进度，一致 |
| 输出与原生物理 | 17 primary / 384 secondary，384 小时 DEN/ZG、TN、UN/VN、O1/O2/N2/HE，网格、单位、填充值和物理检查通过 | 独立扫描 33 卷、原生时间轴、schema、物理场及 SHA，一致 |
| 驱动 | 实际字段与冻结 GPI 最大绝对差 2.842170943040401e-14，阈值保持 1e-10 | 由 GFZ 原件重建，最大绝对差相同 |
| Swarm A | 2880 合格、2880 八列有效、0 失败，含零权重列，无外推 | 独立 CDF、坐标、按时间与高度重建查询，2880/2880，实查 23040 列 |

50 条已知的 NetCDF cast 元数据警告按冻结读者 SHA 进入专用轨道并保留原文；未知警告仍失败。初版 26 项 CPU 测试通过，覆盖错误源、日期、暖态身份、步数、rank、真实 NetCDF NaN/Inf/填值、SHA、只读权限与并发目录。主验收只执行了一次，7.844 秒。初次独立原件读取完成后，汇总器把 CSV 字节数字符串与整数直接比较，错误拒绝了清单衔接，收据保留。修复仅归一化 CSV 数值字段，新增回归后 27 项全部通过。随后单独重取独立证据，保存原始证据再汇总。独立工具内部旧 overall 字段始终对应历史 V24，独立 raw PASS 和 V26 主验收 PASS 通过新证据合并。历史原件、运行预约、FAIL、V25 索引与冻结资产均保留。

SHA 独立阶段 3.993 秒，峰值 18,372 KiB。两个受监督验收进程共 23.576 秒，最大采样 RSS 282,046,464 字节，设有 4 GiB 地址空间上限。新审计目录约 212 KiB。主验收初版 SHA `83b274c74024b5b4384388f67591f8a45cb27c36bf6de04edf4c91396daadc29`，修正后 SHA `deda3382885d7f13ea518fa09df863ca5548f5f55ae824040849b733bb318a92`，独立 SHA 工具 `57f765d74360ed72541eccc2760c33e41d3b54bf264ab19abe21b3e2038a6207`。原独立读者 SHA `e7e9aac2f51b0d100b5d0bffb3ef00e09efe645c196716fd4ece1ad37626a2d2`。

## 证据与下一轮

- [33 卷 SHA 证据](../experiments/thermosphere_autumn_2021_postrun_closure_v26/sha_verification.json)、[首次测试](../experiments/thermosphere_autumn_2021_postrun_closure_v26/tests.json)、[修正后测试](../experiments/thermosphere_autumn_2021_postrun_closure_v26/recovery_tests.json)
- [主验收](../experiments/thermosphere_autumn_2021_postrun_closure_v26/formal_once/main_acceptance.json)、[首次独立汇总失败](../experiments/thermosphere_autumn_2021_postrun_closure_v26/formal_once/failure.json)
- [独立原件复核](../experiments/thermosphere_autumn_2021_postrun_closure_v26/independent_recovery_once/independent_review.json)、[最终闭环](../experiments/thermosphere_autumn_2021_postrun_closure_v26/independent_recovery_once/result.json)

2022 冻结配置和 GPI 保持原 SHA。V23 执行器仍绑定 V24 的原 FAIL 路径。下一轮在独立覆盖层中绑定上述 V26 闭环及主/独立证据的 SHA，给 2022 建立按自身日期、真实源身份和首次预约约束的只读 cold echo 验收，并先做 CPU 反例。真实启动需另授权，并确认 CPU 队列、会话时长与原挂载重新绑定。当前用户无需手动恢复资产、路径或依赖。

`SEED_POLICY=A_MAREQX_APPROVED`、`AUTUMN_ADAPTATION_UNVERIFIED`、`FOURTEEN_DAY_SPINUP_NOT_PROVEN_CONVERGED`、`EXTERNAL_DATUM_UNVERIFIED`、`Restart=FAIL`、`SCIENCE_TRAINING_READY=False`、`DART=NOT_ADMITTED`、`REAL_ORBIT=BLOCKED` 均保留。工程通过只适用于原 2021 秋季积分的完整性和覆盖。
