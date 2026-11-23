# V28 2022 秋季 TIE-GCM 单次积分门禁记录

2026-11-23 UTC。**V28 工程状态 `NOT_RUN`，实际启动 0 次。** 用户提供了附条件的单次积分授权。`--check-only` 通过，当前节点或 CPU 队列的 MPI4 长作业许可，以及容器会话持续监督能力，均未得到实际确认。依照授权边界停止于预检。正式命令和 `--confirm-cpu-session` 均未使用，无后台包装。

## 现场核查与阻碍

工作区为 `/workspace/data/20261016`，起始本地与实查远端 main 均为 `1fd01541b18fd21a86ed917a2e0128e089add3a8`。项目在 ext4 挂载上，当前进程位于 Kubernetes 容器的 cgroup。未发现 sbatch、srun、qsub、bsub、kubectl 或常见调度分配变量。检查范围未得到站点放行当前容器直接跑 MPI4 长作业的依据，也未得到断线、容器回收及任务上限方面的持续监督保证。导师允许 CPU 资源的既有说明仍适用。平台执行许可和会话留存需分别确认。

所需时间至少为模型 4,800 秒加只读验收 600 秒，即 90 分钟，另加必要控制开销。cgroup 配额仅用于核对资源门槛。当前站点是否必须经调度系统未知。若站点要求提交队列，先审查一个由批准的 CPU 分配启动 V27、保留真实直接 wait 和一次性预约语义的最小配置，再提交正式任务。

## 冻结预检

2026-11-23 04:42:43 UTC 使用现有 `activate_tiegcm.sh`，CUDA_VISIBLE_DEVICES 为空，OMP 和 OpenBLAS 各 1。V27 `--year 2022 --check-only` 退出 0，stderr 为空，墙钟约 0.624 秒。V26 闭环、V24 原 FAIL、V27 发布与代码哈希、2022 input、GPI、mareqx、ELF、MPI 与 65 个模型动态库通过身份检查。两份 2022 GFZ 原件 SHA 同时匹配 V22 来源及 V24 保护清单。本轮核对证据和来源，实际驱动残差尚无。

- affinity 112 逻辑 CPU，cgroup 配额 1,400,000/100,000 微秒，即 14 CPU 等效。
- 内存限额 288 GiB，估算当前有效余量约 283.7 GiB。磁盘剩约 1,252.2 GiB。Open MPI 5.0.8。
- 当前活动 TIE-GCM 进程 0。预检前后均无 2022 actual_run、一次性预约、V27 或旧版验收目录。
- 2021 原件、V24 原 FAIL、V26 工程 PASS、V27 发布和冻结物理数据保持原样。GPU、A100 和模型进程调用均为 0。

[预检收据](../experiments/thermosphere_autumn_2022_formal_run_v28/check_only.json) · [运行决策及证据](../experiments/thermosphere_autumn_2022_formal_run_v28/execution_decision.json)

## 实际模型与工程验收

预定目录 `experiments/thermosphere_autumn_mareqx_config_v23/2022/actual_run/` 尚未创建。实际 run_id、起止时间、积分分钟数、MPI 父与四 rank 退出回执均无。此次执行 0 个模型步，生成 0 个 NetCDF。17 primary、384 小时 secondary、33 卷 SHA、首 cold echo、物理场、实际 GPI 差、2,880 点沿轨覆盖、主验收与独立复核均未执行。成功查询数无测量值。无模型失败、异常退出或 UNKNOWN 运行。实测资源数值仅对应预检。

## 接续条件

请提供当前容器的站点长作业许可与会话留存依据，或提供可用且获准的 CPU 队列与分配信息。正式执行前再次核对 V27、现场资源与预约状态。完成唯一一次 16 天积分、主验收和独立复核后，另行授权方可进入秋季科学评分。保留 SEED_POLICY=A_MAREQX_APPROVED、AUTUMN_ADAPTATION_UNVERIFIED、FOURTEEN_DAY_SPINUP_NOT_PROVEN_CONVERGED、EXTERNAL_DATUM_UNVERIFIED、Restart=FAIL、SCIENCE_TRAINING_READY=False、DART=NOT_ADMITTED、REAL_ORBIT=BLOCKED。
