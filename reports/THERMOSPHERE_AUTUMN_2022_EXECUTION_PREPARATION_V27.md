# V27 2022 秋季 TIE-GCM 正式积分准备

2026-11-23 UTC。**2022_CONFIG_READY_FOR_RUN_AUTHORIZATION**，**2022_ACTUAL_MODEL_RUN=NOT_RUN**。V27 启动覆盖层、只读验收和发布证据均已冻结。启动所需的 CPU 会话和队列确认及研究运行授权待下一轮。2022 正式 actual_run、一次性预约及事后验收目录均未创建。

## V26 准入与原件保护

起始本地 HEAD、origin/main 和实查 GitHub main 均为 `bd46914e2c3aca83c6b5bca95d91994336432365`。V27 逐一验证 V26 发布索引、报告、主验收、独立原始复核、最终闭环和 33 卷 SHA 收据。路径与 SHA 有固定锚点，再检查内部字段。与 V24 发布清单交叉复核 33 卷的名称、大小和 SHA，发布字节合计 3,371,588,992。此次复核对象为 V26 两次读取原件留下的证据，未另扫 2021 大型 NetCDF。

主/独立共享原 run_id `18726974f5d3450ba61f82c23c8da3a0`，23040 步、2021-09-25 00:00 UTC、父和四 rank 均退出 0、17/384、2880 个查询。重新检查 V24 直接 wait 日志、预约和运行回执身份。V24 原 FAIL 的 SHA `3859b363b92f6f5cfb3d10a125db8d83356cfe91d557f72f6b64ad285b998271` 保留。V27 用 V26 工程闭环决定准入资格，并用 V24 原 FAIL 证明历史未改。V23 冻结启动器仍保留其原行为。

## 2022 冻结配置

| 项 | 核对结果 |
|---|---|
| input.inp | `f01f3913f9f15b79132fe8f824c7ce9f5ce7c4c1b6591c9622be184ee7b0fa49` |
| 2022 秋季 GPI | `7d43db220fe7fbaded6b2182db8db32ee09cedf99dc5760815824ccf8298ebb2` |
| mareqx 初始场 | `a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7` |
| TIE-GCM ELF | `f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776` |
| mpirun | `7b6c839e5d90310bf741efe3f9cbba68460083c74721513d5f3697b158119639` |
| 冷启动和时钟 | 原源 2002 DOY80 00:00，SOURCE_START=80 0 0。目标 2022-09-09 00:00 至 09-25 00:00 UTC。步长 60 秒，23040 步，无 Restart 或 append。 |
| GPI 覆盖 | 原始节点 2022250–2022270，合法 2022252–2022268。按冻结解释器核对含首尾 23041 个分钟节点。 |
| 分卷与路径 | 17 个 primary 卷、16 个 secondary 卷共 384 小时记录。直接运行既有 V23 Fortran expand_path 小探针，SOURCE、GPI 和两份 GSWM 共四条实际展开匹配。2021 和 2022 的实际目录完全隔离。 |

## 启动和只读验收

2022 入口先检查年份、独立一次性授权和 CPU 会话确认，再取得与 V23 共享的非阻塞文件锁。验证发布、资源及不存在旧预约后，原子创建 2022 actual_run 与独占预约，生成新 UUID。MPI 父由现有 supervisor 直接等待，四个子 rank 各自留下直接退出回执。监控异常、非零退出或未知结果均拒绝续行并保留现场，自动重试为零。第二个监督调用仅在模型正常退出后执行对应只读 Python 验收。V27 只读入口无模型进程创建调用。

只读适配复用 V26 的原生元数据读法和 mareqx 源身份检查。分支仅在完整 V27 预约、父/四 rank 原生退出、全部进度、显式源和 native echo 输出行验证后应用。2022 首 primary 须为 2022-09-09 00:00 UTC，year 2022、DOY252、mtime [252,0,0]，首记录继承从真源读出的 iter 115200，34 项双精度状态的原生 schema 与源一致。暖态必须为 initial，iter 随累计步数增加。DEN/ZG、TN、UN/VN、组分、填值、NaN/Inf、GPI 差 <1e-10，以及 2022 Swarm A 合格样本的 Map-A 八列规则仍复用冻结检查。

**28 项 CPU 测试通过**，其中 20 项覆盖 V27 门禁和 2022 fixture，8 项复用冻结科学与 rank 反例。覆盖伪造 V26 PASS、证据缺失或换 SHA、run_id、物理资产和 MPI/库漂移、错误目录和年份、无授权、并发和重复预约、模型未知退出后保留现场、非法冷/暖记录、缺漏或重复时轴、非零或缺失 rank、NaN/Inf/填值、非正 DEN 和非单调 ZG。另单独执行真实无授权 CLI，退出 2，未产生预约。独立静态审查对照 Git 基线、源代码 SHA、无模型调用的验收执行图和输出约定。fixture 通过仅用于代码验证，2022 原件主验收及独立复核均为 NOT_RUN。

## CPU 资源和下一轮授权

当前 112 逻辑 CPU affinity，cgroup 配额约 **14 CPU 等效**，负载快照 9.04/8.70/8.62。cgroup 内存 288 GiB，按使用量折算可用约 283.8 GiB，磁盘剩约 1,252 GiB，2022 父目录可写，无活动 TIE-GCM。Open MPI 5.0.8，65 个动态库 SHA 与历史一致，ELF 重定位检查无错误。A100、GPU、CUDA 调用均为零。没发现常见队列客户端。是否必须走站点 CPU 队列以及当前会话是否可覆盖整个监督窗口仍待平台确认。MPI4 启动后的真实资源可用性需启动前重查。

下一轮需明确授权一次 2022 冷启动并确认 CPU 会话和队列。使用 MPI4/OMP1/OpenBLAS1/GPU0，模型监督预算 4800 秒（4770 秒触发停止、30 秒清理预留）、RSS 16 GiB、输出 5 GiB、磁盘启动余量 25 GiB、运行余量 20 GiB。监督为采样与信号控制。以下命令仅为冻结模板，本轮未执行。

```bash
source scripts/activate_tiegcm.sh
export CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python -B scripts/execute_tiegcm_autumn_2022_v27.py --year 2022 --check-only
python -B scripts/execute_tiegcm_autumn_2022_v27.py --year 2022 --authorize-2022-single-16day-run --confirm-cpu-session
```

后续独立工程复核另以 2022 原始文件检验父/四 rank 直接 wait、23040 步、所有卷 SHA 和 17/384 时间、物理场、从 2022 GFZ 原件独立重建驱动以及 2880 个 Swarm A 查询。完成独立复核前，仅报告主验收状态。任何新密度评分需独立授权。

## 证据

- [执行发布](../experiments/thermosphere_autumn_2022_execution_preparation_v27/execution_release.json) · [CPU 资源](../experiments/thermosphere_autumn_2022_execution_preparation_v27/resource_review.json) · [测试](../experiments/thermosphere_autumn_2022_execution_preparation_v27/tests.json)
- [独立静态复核](../experiments/thermosphere_autumn_2022_execution_preparation_v27/independent_static_review.json) · [独立代码复核](../experiments/thermosphere_autumn_2022_execution_preparation_v27/independent_code_review.json)
- [执行入口](../scripts/execute_tiegcm_autumn_2022_v27.py) SHA256 `09a81eb4df7ddaebf01e915616502c494d7012af76c218d56818943ae4eaf431`
- [只读验收](../scripts/audit_tiegcm_autumn_2022_v27.py) SHA256 `d277f46244c468df1d2d9fd47fd3be0369b225d34b99bbe42e2ed22d1f31397f`

保留 SEED_POLICY=A_MAREQX_APPROVED、AUTUMN_ADAPTATION_UNVERIFIED、FOURTEEN_DAY_SPINUP_NOT_PROVEN_CONVERGED、EXTERNAL_DATUM_UNVERIFIED、Restart=FAIL、SCIENCE_TRAINING_READY=False、DART=NOT_ADMITTED、REAL_ORBIT=BLOCKED。
