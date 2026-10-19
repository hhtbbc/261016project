# TIE-GCM 2023原生continuation验证：B1状态不一致，B2未执行

## 结论与运行范围

仅启动一次B1（2023-03-18 23:50→2023-03-19 00:00），正常退出但未通过预注册数值容差，因此未创建或执行B2，不重试、不重复24小时积分、不开展spin-up。合法23:50检查点已在前任务生成，过去“缺少23:50状态”的阻碍已解决；当前阻碍是续算数值一致性。

## 配置、保护和资源

执行器scripts/run_tiegcm2023_continuation.py，复用原apex更新构建、2023 GPI、5°网格、60秒步长、4 MPI。input.inp省略SOURCE/SOURCE_START，从独立OUTPUT副本走原生continuation。原primary_002.nc的SHA256为d0aab5804eeab7680977f0fa9ad1de165600fd884bde2ddc1e0c6754c5ab9a4f，复制前后完全一致，原件未修改。保存的初始34状态记录在append后也保持一致。

B1墙钟2.183236秒，采样聚合RSS峰值977723392字节（约932.43MiB），返回码0、4个NORMAL EXIT；实验目录约40.23MiB，未达到512MiB预算。wall90秒、CPU120秒/进程、RSS16GiB、余盘20GiB门禁已启用。989项既有文件在新增文档更新前重算哈希，全部未变，见preservation_check.json。没有额外模型启动。

## 时间、驱动和输出

primary时间为DOY77 23:50、DOY78 00:00，iter112310→112320，恰好10步。全部10个实际运行GPI读数与独立计算符合日志精度，无固定F107/F107A/KP/POWER/CTPOTEN覆盖、无未来记录。初始回显与真正积分驱动分开核查。具体时间与驱动证据见failure_diagnostics.json和原始运行日志。

DEN/ZG只在共同secondary中比较；不声称primary保存了DEN/ZG或N2。34项完整primary的形状、类型、单位、时间、缺失掩码检查通过；其中28项数值超差，只有TLBC/ULBC/VLBC及其_NM六项逐点相同。共同secondary的9项均数值超差。

## 误差（SI单位，2023-03-19 00:00 UTC）

|变量|最大绝对差|RMSE|
|---|---:|---:|
|primary TN|0.442935691 K|0.033388915 K|
|primary UN|0.581426754 m/s|0.058849019 m/s|
|primary VN|1.362063746 m/s|0.091313940 m/s|
|primary POTEN|9.452502539 V|3.605753892 V|
|secondary DEN|3.878841692e-12 kg/m³|2.040392301e-13 kg/m³|
|secondary ZG|368.6 m|14.550117549 m|

DEN最大相对差0.0835143%。相对误差在参考接近零时会变大，必须与绝对误差和RMSE一起看。完整43行结果见results/metrics/tiegcm2023_continuation_v1_B1_errors.csv，列出覆盖率、非有限值、掩码、最大归一化容差指标。所有检查采用运行前冻结的frozen_comparison_rules.json：float64 rtol1e-10，float32 rtol1e-6，按单位atol；未事后放宽。差异远大于门限，不能认定为可忽略的MPI舍入。

## 稳定性与科学边界

共同输出有效点无NaN/Inf，DEN为正，ZG垂直顺序通过。TN范围147.43—1108.52K，风速分量最大绝对值约459.33m/s；DEN原生范围9.44e-17—1.1983e-9 g/cm³。缺失顶层显式掩码，不把它当异常数值。正常退出、基础场检查通过不等于连续/分段一致，更不等于2023热层已经平衡。

## 源码故障定位与最小修复建议（尚未证明唯一原因）

源码路径third_party/TIEGCM2.0：advance.F将新运行istep重置；rdsource.F恢复后调用define_phim3d。pdynamo.F的prepare_phig3d（2931—2968）将磁坐标内部势转换为地理POTEN输出，define_phim3d（2970—3002）每次启动反向重建；pefield（2596—2707）在istep==1重建电场，而连续运行后续步使用前一步pthreed得到的电场。检查点不含PHIM3D/EPHI3D/ELAM3D/EMZ3D这些内部数组。

这证明存在不同启动计算路径，是可信候选原因，但未做逐语句状态探针，不能宣称已确定唯一根因。34项primary完整不等于全部运行时内部状态无损序列化。已排除用户复制损坏、缺_NM、时间错位、明显GPI错读及漏步等证据；也未证明其他缓存/初始化逻辑完全等价。

后续需单独授权独立覆盖构建的诊断：在读取、坐标回映射和首步电场前后记录内部状态，定位首次分歧；若确认缺少原生内部状态，设计版本化restart字段与精确恢复，保持旧格式兼容并明确旧路径近似性质。不可拟合物理初态、放宽容差或手工伪造_NM。本次未改原源码、未应用推测性补丁。旧检查点缺失的内部量不能凭空恢复。

## 复现与测试

已执行命令（勿不经新授权重放模型）：

```bash
source scripts/activate_tiegcm.sh
python scripts/run_tiegcm2023_continuation.py --suite-tag tiegcm2023_continuation_v1 --stage B1
python scripts/run_tiegcm2023_continuation.py --suite-tag tiegcm2023_continuation_v1 --stage B1 --execute
python scripts/run_tiegcm2023_continuation.py --suite-tag tiegcm2023_continuation_v1 --stage B1 --audit
```

审计因数值不一致返回失败是预期门禁行为。全项目自动化56项测试通过（6.690秒）；包括B1失败禁止B2、配置禁止SOURCE/固定驱动、完整检查点和冻结容差测试。测试通过不代表物理等价通过。日志logs/tiegcm2023_continuation_all_tests.log；实际运行logs/tiegcm2023_continuation_v1_B1.log。B1配置、运行状态、审计JSON在experiments/tiegcm2023_continuation_v1_B1，冻结规则和B2_skipped在experiments/tiegcm2023_continuation_v1。

## 决策

分段spin-up尚未工程就绪。先授权诊断首次状态分歧和独立补丁验证，再以同起点连续20分钟/两段10分钟受控对照建立等价性；不需要重跑现有24小时参考。当前不启动3/7天，初始场收敛、Swarm目标日期高度/高度基准、Cd/有效面积及机动问题仍未闭合。
