# V29 2022 秋季 TIE-GCM 正式积分与独立验收

**ENGINEERING_PASS**。2022-09-09 00:00 至 2022-09-25 00:00 UTC 连续冷启动完成。正式启动一次，run_id 为 `4a89e99eaee548f28240ea47f4b98e47`，无续算、无重试。V27 主验收及 V29 独立原件复核均通过。GPU/A100 查询、调用、占用均为 0，无新密度评分、拟合、训练、DART 或轨道传播。

## 技术条件与单次执行

用户已授权节点 CPU 直用和 MPI4。当前 Pod 运行时 PID 1 已存活 8,265 秒，未发现明确临近终止信号。项目目录位于 ext4 挂载。V27 在非 PTY 托管命令中运行，屏蔽终端 SIGHUP，模型 MPI 由直接父监督器控制，原始日志以持久文件写入。原监督器处理 SIGINT/SIGTERM，保留子进程直接 wait 和可核实的清理结果。Pod 销毁仍可中止进程；发生时按原身份、预约、现存进程和直接退出证据判断，已有预约禁止再次启动。运行期间持续跟踪，未出现掉线、回收、采样缺口或中止。

使用既有冻结激活脚本，CUDA_VISIBLE_DEVICES 为空，OMP 和 OpenBLAS 各 1。V27 check-only 通过，14 CPU 等效、288 GiB 内存限额、Open MPI 5.0.8 和 65 个冻结模型库匹配，正式目录与预约不存在且无活动模型。随后一次执行：

```bash
source scripts/activate_tiegcm.sh
export CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python -B scripts/execute_tiegcm_autumn_2022_v27.py --year 2022 --check-only
python -B scripts/execute_tiegcm_autumn_2022_v27.py --year 2022 \
  --authorize-2022-single-16day-run --confirm-cpu-session
```

## 真实运行和资源

| 项目 | 实测 |
|---|---|
| 最早 rank 启动 UTC | 2026-11-23T04:50:32.682992+00:00 |
| 最晚 rank 退出 UTC | 2026-11-23T05:31:14.321660+00:00 |
| 模型监督墙钟 | 2441.927307 秒，40.698788 分钟 |
| 父和四 rank 退出 | 0；0、0、0、0，直接 wait，无监督缺口，清理通过 |
| 采样峰值进程树 RSS | 980,705,280 字节 |
| 子进程 CPU user / system | 8999.151648 / 768.103823 秒 |
| 运行中最少剩余磁盘 | 1,341,150,089,216 字节（1249.04 GiB） |
| 原始运行目录逻辑大小 | 3,381,291,807 字节 |
| NetCDF 逻辑大小 | 3,371,588,992 字节 |

RSS 和磁盘为采样统计，资源控制通过监督与信号。原始运行目录为 `experiments/thermosphere_autumn_mareqx_config_v23/2022/actual_run/`，原始 NetCDF 和完整运行日志留在服务器。一次性预约与原输入 SHA 保留。

## 主验收与独立复核

| 验收项 | 结果 |
|---|---|
| 进度和日历 | 四 rank 各 2,304 个间隔 10 步的进度记录，累计 23,040 步。终点 2022-09-25 00:00 UTC。 |
| 原生输出 | 17 条 primary、384 条 secondary、33 卷，逐卷 SHA、大小与主验收相同，精确校验全轴无重复无缺漏。 |
| 首 cold echo | 2022-09-09 00:00 UTC，run_type 为空，DOY252、mtime [252,0,0]；显式 mareqx SOURCE、SOURCE_START [80,0,0]、iter 115200 与原生源及 34 项状态匹配。暖态身份和 iter 全部通过。 |
| 物理场 | 全部 384 帧 DEN/ZG、TN、UN/VN、O1/O2/N2/HE 通过原生维度、单位、填值、有限性、正密度、ZG 单调、格点及组分闭合检查。 |
| 驱动 | 主验收实际字段对冻结 GPI 的最大绝对差 5.684341886080801e-14。独立从 101 天 GFZ Fobs 和 168 个 definitive Kp 桶重建，最大绝对差 5.684341886080801e-14。原门槛 <1e-10。 |
| Swarm A | 主、独立均 2880/2880 成功，0 失败。独立重建实际检查 23,040 列，含零权重列，无外推、补值或密度误差计算。 |

主验收由 V27 监督 11.848 秒，按冻结告警通道留存 50 项已知 cast 警告。独立复核 7.350 秒、峰值 RSS 167,924 KiB。独立工具按 V24 的只读算法适配到 2022，先重查原件及直接回执，再比对公开主结果与逐卷 SHA。独立验证 161 项原科学资产和 25 项 V24/V26/V27/V28 证据哈希。未修改模型、原始历史输出或任何冻结阈值。

## 证据与下一轮

- [最终状态](../experiments/thermosphere_autumn_2022_formal_run_v29/result.json) · [主验收](../experiments/thermosphere_autumn_2022_formal_run_v29/main_acceptance_snapshot.json) · [独立复核](../experiments/thermosphere_autumn_2022_formal_run_v29/independent_review.json)
- [33 卷 SHA 与时间清单](../experiments/thermosphere_autumn_2022_formal_run_v29/model_output_manifest.csv) · [四 rank 退出](../experiments/thermosphere_autumn_2022_formal_run_v29/rank_exit_summary.json) · [独立复核代码](../experiments/thermosphere_autumn_2022_formal_run_v29/independent_review_v29.py)

秋季科学评价的工程前置条件已满足。后续须另行授权并沿用冻结预注册，保留 SEED_POLICY=A_MAREQX_APPROVED、AUTUMN_ADAPTATION_UNVERIFIED、FOURTEEN_DAY_SPINUP_NOT_PROVEN_CONVERGED、EXTERNAL_DATUM_UNVERIFIED、Restart=FAIL、SCIENCE_TRAINING_READY=False、DART=NOT_ADMITTED、REAL_ORBIT=BLOCKED。此结果确认工程完整性与沿轨覆盖，密度精度尚未评分。
