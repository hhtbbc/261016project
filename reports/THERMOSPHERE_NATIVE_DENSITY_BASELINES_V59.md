# V59 秋季 TIE-GCM 模拟密度场三基线

**V59_NATIVE_DENSITY_BASELINES_COMPLETE_VERIFIED**。完成 24 个真实模型目标评价，2021/2022 各 12 个。结果用于原生压力网格内的工程 HINDCAST。Swarm 观测、外部高度和轨道精度仍未评价。

## 数据身份与范围

起始 HEAD 和远端 8a8616d4562a98452cd82e38992f2bbbece59114。V58 发布收据、两组 ELF/GPI/启动收据/输入身份和 32 卷次历史 SHA 均匹配。2021 run_id 为 18726974f5d3450ba61f82c23c8da3a0，2022 为 4a89e99eaee548f28240ea47f4b98e47。

两年均使用 09-23/24 的 06Z、18Z。每截点输入 t−3h、t−2h、t−1h，预测 t+1h、t+3h、t+6h。09-24 18Z 的 +6h 指向冻结表中已获准的 09-25 00Z。8 个截点、24 个输入和 24 个目标，合计 48 个不同 DEN 场。独立复核在相同记录范围内重读，额外不同记录为零。V37 夏冬目标和夏季驱动家族未访问。数据保持 independent_science_test=NO。

NETCDF3_CLASSIC 使用单个时间记录切片。实际网格 29×36×72，共 75,168 格点/场；纬度 −87.5° 至 87.5°，周期经度 5°。原始 g/cm³ 乘 1000 得 kg/m³，填充值、非有限和非正值先屏蔽。48 场共 3,608,064 个格点，均有效。ZG 仅读维度。ilev 是 ln(p0/p) 的压力接口，与几何高度的对应随时间和地点变化；固定 ilev 的误差不能当成固定 450 km 误差。EXTERNAL_DATUM_UNVERIFIED 保持。[读取记录](../experiments/thermosphere_native_density_baselines_v59/den_read_ledger.csv)

## 隔离和独立复核

每个截点的 worker 只得到三个历史场，使用独立 chroot、UID/GID 65534、no_new_privs 及 seccomp 白名单。固定公式无归一化、外部驱动或标签接口。12 项探针测试路径穿越、链接、两个原始运行路径、proc、网络与输入写入。替换沙箱外的合成标签后输出逐字相同。全部 24 组预测的档案与 SHA 锁定后才开始读目标。评价侧使用 Linux 内核密封的 memfd，24 次写入尝试均被拒绝，磁盘预测档案评价前后 SHA 一致。

首次启动因当前 CPython 没有 memfd 和文件封条绑定而停止，目标目录为空。保留现场，使用已安装 libc 和 Linux 头文件常量继续，同样要求内核写保护。独立复核以幂形式重新计算对数外推，独立计算面积加权统计及 P95，复核 **1,782 行**，最大指标相对差约 7.45e−13。独立读取提示部分文件的 missing_value 属性类型不能安全自动转换；本组原值无填充值，48 帧独立转换 SHA 均与主程序显式掩码结果一致。主实验约 19.1 秒、峰值 RSS 267 MiB、CPU 亲和性 4 核。[预测锁](../experiments/thermosphere_native_density_baselines_v59/prediction_lock.json) · [独立收据](../experiments/thermosphere_native_density_baselines_v59/independent.json)

## 全球误差

各方法自身有效掩码，单位 kg/m³。权重为 cos(latitude)；全层汇总使用各层同样的纬度权重，层间没有物理体积权重。相对 RMSE 为逐点相对误差加权 RMS，log RMSE 使用自然对数差，P95 为面积加权的逆经验分位。Bias 为预测减标签。

| 方法 | 时效 | MAE | RMSE | Bias |
|---|---:|---:|---:|---:|
| Persistence | 1h | 2.0610e−9 | 7.1279e−9 | +7.4647e−12 |
| Persistence | 3h | 3.7346e−9 | 1.3042e−8 | +1.3467e−11 |
| Persistence | 6h | 5.0344e−9 | 1.8182e−8 | +1.8124e−11 |
| 原值线性 | 1h | 1.3338e−9 | 4.4637e−9 | −1.4336e−12 |
| 原值线性 | 3h | 4.0063e−9 | 1.3464e−8 | −4.3300e−12 |
| 原值线性 | 6h | 8.7674e−9 | 2.9706e−8 | −1.3020e−11 |
| 对数线性 | 1h | 1.3270e−9 | 4.4484e−9 | +6.6371e−11 |
| 对数线性 | 3h | 3.9801e−9 | 1.3416e−8 | +2.2076e−10 |
| 对数线性 | 6h | 8.7095e−9 | 2.9679e−8 | +6.1413e−10 |

按全球绝对 MAE/RMSE，+1h 对数线性领先，+3/+6h Persistence 领先。+1h 原值线性的相对和 log RMSE 略低于对数线性。三种方法的误差均随时效增长。对数线性输出全正且无溢出或下溢，正 Bias 随时效增加。原值线性 11 个非正值全在 +6h（0.001829%），保留原值。Persistence、对数线性自身覆盖率均 100%；原值线性 +6h 99.998171%。+6h 共同有效为 601,333/601,344，按 Persistence、原值、对数顺序的 RMSE 为 1.81825e−8、2.97062e−8、2.96796e−8，排名不变。其余时效共同掩码等于自身掩码。

各方法各时效的绝对 RMSE 最大层均为索引 0（ilev=−7），相对 RMSE 最大均为索引 28（ilev=7）。Persistence 的绝对 RMSE 在低纬最大，两个外推在中纬最大；三方法最大相对 RMSE 均在低纬。纬区以绝对纬度划分为 <30°、[30°,60°)、≥60°。2022 全域 RMSE 一致略高，约 0.24%–0.46%，两年时效排名一致。两个历史秋季块无法支持跨季节或跨地磁事件的推广。[分层指标](../experiments/thermosphere_native_density_baselines_v59/metrics.csv) · [统计图](../experiments/thermosphere_native_density_baselines_v59/baseline_comparison.png) · [场图](../experiments/thermosphere_native_density_baselines_v59/native_field_example.png)

## V60 设计与门槛

申请小型 CPU Direct 工程演示。三帧输入并行输出三个时效；建议各压力层共享 3×3 卷积、8–16 隐藏通道，可用原生层位坐标，周期经度与反射纬度。自然 log-density 的中心和尺度只由 2021 训练侧有效格估计。预注册各时效 cos(latitude) 加权 log-MAE，使用相同掩码及原值空间指标，2022 验证侧不得参与训练、归一化或模型挑选。固定种子、批量 1–2 与步数上限，工程预算 4 CPU、4 GiB、30 分钟，启动前测量单批，保留与三基线同样本的对照。

只有 4 个截点可用于拟议训练，另外 4 个用于历史工程核对，独立科学测试数为 0。最低需要一个未参与选择的外部测试块；跨地磁研究需预先定义至少两档活动水平、各有多个独立事件，再按事件方差做功效分析，当前无法给出充分样本量。Direct 训练、标签再用或扩大、新独立测试块以及任何观测标签访问均需另行授权。本轮没有外部回件，GFZ、ESA、0504、ZG 与 V37 正式评分门禁保持。Swarm 读取、真实训练、GPU、新积分、正式评分、DART 及轨道传播均为零。
