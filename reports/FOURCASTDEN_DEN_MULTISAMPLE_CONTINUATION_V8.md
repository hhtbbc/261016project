# AFNONet 72对真实DEN累计720步训练长度对照 v8

2026-11-13。实验标签`fourcastden_den_multisample_continuation_v8`；身份保持`DEN_ONLY / ENGINEERING_RESEARCH / HINDCAST / LIMITED_PHYSICAL_VALIDATION`。

**一次GPU任务从可信v7 step200严格恢复，新增520更新至累计720，642次forward完成；训练全层relative RMS从3.804484%降至2.276034%，开发从10.082082%降至6.725325%，但两者仍未超过Persistence。** 无失败重试、调参、增步、数据重建、统计重拟合或新物理模拟。

## 1. 初始状态、数据和恢复门禁

本地/远端起始main均`d16e3edcafe21757ff1099e1590251898fecd203`，只保留既有无关未跟踪同步记录，不重置仓库。

唯一源：`experiments/fourcastden_den_multisample_v7/step200.pt`，SHA256：
`82483f890db2d20ec00159ff0588217dd71d37889195ca5b77b1b3ac740e722f`。

可信本地路径/SHA核验后反序列化，来源tag、label、v3统计/清单、seed/架构/优化器配置、step200、148组完整AdamW状态及内部step200、scheduler、Python/NumPy/Torch/CUDA RNG、model_training=False均与v7原审计一致。恢复模型SHA：`b8ced924267b8f576bece552c88ef066af33f1e4cd3d84d6935a52faa084060e`。新建网络仅作为加载容器，实际训练权重/优化器来自v7；没有从v6或官方权重开始训练。

原checkpoint/config中`max_train_steps=200`逐字保留，原严格恢复模块不改。独立`ContinuationBudget(start_step=200, additional_updates=520)`在optimizer前后hook核对实际更新，累计720后拒绝721。

GPU更新开始前只有1次eval/no_grad恢复探针，固定2021首对输入：物理DEN数组与v7保存结果**逐元素一致，最大绝对差0**。模型/优化器/scheduler/RNG不因探针变化，新增更新数仍0。严格核对原eval模式之后显式`model.train()`，模式切换不改变参数或RNG；每次训练forward还断言training=True。原`train_step()`本身也先调用train模式，有CPU独立用例及真实运行日志。

**没有验证从step1一次性无中断运行到720的逐位等价性。** 源checkpoint在v7训练和开发评价后生成，本轮是合法checkpoint接续实验，不把它包装为已验证无中断轨迹。

数据只读复用DEN v3：2021 B14 73小时帧/72连续对，03-23 00至03-26 00 UTC；2022 B14 49帧/48对，03-23 00至03-25 00 UTC。122帧SHA/DEN有限正值/ZG逐列递增、120对X-D-Y SHA/时间与未来物理真值毒化检查通过；638项历史资产最终SHA不变。

输入X177为当前真实状态加合法下一时刻辅助，D为4个历史驱动条件；Y171是下一小时标签，仅DEN142:171的29原生ilev层监督。其他142输出不视为可信状态。DEN原始g/cm³乘1000转kg/m³；ZG cm乘.01转m，Z不是ZG。原2021统计直接用于2022，统计来源和数据版本未改。外部高度问题不因原生层训练而解决。

## 2. 冻结配置、顺序和实际执行

原AFNONet64695744参数，FP32、batch1；AdamW lr1e-4/weight_decay0，StepLR step_size1/gamma1，clip L2=1，cos纬度加权normalized DEN MSE。无残差/log/正值参数化、新正则或数据增强。

`pair_index=(cumulative_step-1)%72`。新增201—216为pair56—71，217—720继续原循环；520条新记录与v7只读200条拼接后，72对各访问10次。不重跑历史200步、不补到其他更新数。

实际forward计数：恢复探针1+训练520+最终train72+最终dev48+最终恢复1=**642**，与预注册一致。所有最终评价在累计720后进行，eval/no_grad，完整模型/AdamW hash、步数与空梯度不变；2022只最终一次，不用于选择checkpoint或超参数。

65 CPU测试通过：新增8项v8顺序/原config/拒绝v6与错SHA/原eval模式/恢复探针无状态变化/train_step切train/520预算与642forward检查，57项既有训练、恢复、CUDA、数据与隔离回归。实际GPU一任务exit0/PASS，520次有限非零梯度和有效head更新；每次148个有效梯度张量。非DEN head行梯度0且参数逐元素未变；共享骨干由DEN损失训练，原闲置norm.weight/bias照实记录。

clip前L2=11.629607—16.521229，520/520触发clip1；没有非有限或不更新。只能证明裁剪持续生效，不能单凭此认定梯度爆炸、学习率错误或裁剪必然是主要瓶颈。

## 3. 损失与访问轮次诊断

每个完整72步遍历的pre-update loss均值：

| 遍历 | 累计step | 描述性均值 |
|---|---|---:|
| 1 | 1—72 | 10.034221 |
| 2 | 73—144 | 0.802052 |
| 3 | 145—216（跨v7/v8） | 0.509115 |
| 4 | 217—288 | 0.375271 |
| 5 | 289—360 | 0.312443 |
| 6 | 361—432 | 0.271111 |
| 7 | 433—504 | 0.239297 |
| 8 | 505—576 | 0.213519 |
| 9 | 577—648 | 0.192064 |
| 10 | 649—720 | 0.175885 |

第10次访问中，72/72对pre-update loss均低于其第9次，也均低于第3次；最后一轮均值较前一轮低8.423658%，范围0.137599—0.262253。下降收益递减但仍有下降，**未证实明确平台**，不能据此宣布直接DEN已达能力上限。

每一步模型权重都不同；上述轮次均值不是统一checkpoint的72样本评价。最终模型在全部训练对的normalized MSE均值为0.233667（v7为0.653466，降低64.241967%），开发均值1.469681（v7为3.359030）。最后一轮运行中均值与最终统一模型均值不同，不代表统计矛盾，也不应称为最终epoch loss。

逐层标准化MSE也已独立反算：训练范围0.190467（层1）—0.276263（层16），开发0.742861（层10）—2.577217（层20）。物理relative误差最高的层并不完全相同，说明标准化MSE与相对物理误差不可互换；本轮没有改变损失权重来追求有利指标。

## 4. 完整物理评价与Persistence

同v7：每小时cos(latitude)面积权重、经度均匀、所选原生层等权；relative RMS为`√weighted_mean(((prediction-target)/target)^2)`，目标严格正值，无额外分母下限；跨小时等小时平方平均再开方。普通误差保留全部有限预测，不裁剪/不删负值；自然对数比RMS另列，必要时仅在共同正值域评价并报覆盖率。累计更新步数、forward次数以及压力层索引与实际高度分别登记。

| 评价域 | 范围 | v7 step200 | v8 step720 | Persistence | v8相对v7降低 |
|---|---|---:|---:|---:|---:|
| 2021全部72 | 全29层 | 3.804484% | **2.276034%** | 1.722953% | **40.174961%** |
| 2021全部72 | 上层20—28 | 4.347241% | 2.597529% | 1.793025% | 40.248791% |
| 2021全部72 | 顶层28 | 5.609567% | 3.485630% | 2.451758% | 37.862754% |
| 2022全部48 | 全29层 | 10.082082% | **6.725325%** | 1.992488% | **33.294283%** |
| 2022全部48 | 上层20—28 | 12.401138% | 8.435358% | 2.242242% | 31.979165% |
| 2022全部48 | 顶层28 | 13.167300% | 10.315506% | 2.909416% | 21.658158% |

2021训练72/72对、2022开发48/48对全层relative RMS均比v7改善；两年逐层29/29也均改善，并非只改善少数时间或高度。**但训练0/72对胜过同对Persistence，两个年份的29层中均0层胜过各自Persistence。**

训练各对范围1.892739%—2.826061%；开发6.352296%—7.150970%。训练全层仍是P的1.321倍、开发3.375倍。开发与训练相差4.449291个百分点（v7差6.277598个百分点）；不能只凭此差距将全部问题归于过拟合或数据量。

| 评价域 | 范围 | v8 RMSE kg/m³ | v8 Bias kg/m³ | log RMS |
|---|---|---:|---:|---:|
| 2021 | 全层 | 3.977386e-9 | -3.809397e-11 | 0.022811 |
| 2021 | 上层20—28 | 6.266093e-14 | -1.924927e-15 | 0.026061 |
| 2021 | 顶层28 | 4.602203e-15 | -5.229134e-16 | 0.035043 |
| 2022 | 全层 | 8.818626e-9 | -4.076754e-10 | 0.064524 |
| 2022 | 上层20—28 | 1.916481e-13 | 5.661007e-14 | 0.079621 |
| 2022 | 顶层28 | 1.094225e-14 | 5.078391e-15 | 0.095952 |

绝对RMSE跨层由低层大密度主导，不能只按全层绝对误差解释高空效果。

| 全29层纬区 | 2021 v8/P relative RMS | 2022 v8/P relative RMS |
|---|---:|---:|
| 中低纬\|lat\|<60° | 2.08110 / 1.79203% | 6.73545 / 2.08683% |
| 北高纬≥60° | 3.16998 / 1.20627% | 6.81826 / 1.25038% |
| 南高纬≤-60° | 3.36043 / 1.15893% | 6.49682 / 1.18367% |

训练层1最小1.160227%、顶层最大3.485630%；开发层10最小2.803998%、层27最大10.464691%。高层仍较难；原生ilev不是固定几何高度，也不能据此称沿卫星轨迹预测已验证。

2021的5412096与2022的3608064个最终预测均正且有限：非正0、非有限0，普通覆盖/正值率/log覆盖均100%。保留按纬区/层的完整统计，不将有限率替代正值率；本次0非正不是全域正值保证。

独立CPU从保存预测与原标签直接加权复算120对全层指标，并用统一模块复算全部逐层/纬区AI指标；Persistence120对与v3冻结值逐项一致。标准化逐层损失反算与实际GPU评价均值一致；无额外模型forward。2022已多次开发查看，不是盲测；两年短三月窗口及格点并非独立全年实验，不能据此宣布跨季节/太阳活动泛化。

## 5. 资源、checkpoint与SHA

监督131.596228秒，worker128.747013秒；新增520步纯更新61.846914秒（均值0.118936秒/中位0.117721秒），训练循环73.859106秒。CPU缓存2.882023秒，容器构造1.931383秒，初始严格恢复4.653986秒，最终72训练评价5.999296秒、48开发评价5.976961秒，保存/恢复7.328037秒，数组保存3.262770秒；计时有包含/未分项审计部分，不机械相加。

A100-SXM4-80GB，torch2.4.1+cu121/CUDA12.1，原GPU可见性继承（未设置CUDA_VISIBLE_DEVICES且仅1设备），torch前CuBLAS`:4096:8`，FP32确定性不变。allocated峰值1.520779GiB/reserved1.708984GiB，进程GPU采样2.259766GiB，CPU树RSS2.458340GiB，128次采样、0监控缺口。worker记录输出0.790223GiB；300秒/20GiB GPU/8GiB RSS/2GiB产物与至少20GiB空闲均满足。

独立CPU后处理39.095241秒、666.75MiB，不包含在GPU训练开销内。

只保存最终完整`experiments/fourcastden_den_multisample_continuation_v8/step720.pt`（776768010字节），SHA256：
`04a4d9fc45a35c375ac9d4c1528c3ecc23b33cddace68ba62d157bcc900afd1f`。

最终模型state SHA：`fbc2fbeb14311ce37cee83af5c52cc0e74026d5d4f0e28cd26f7841d070c8cab`。

原统计SHA：`df9a8c2bd31026de0e0ebcae07c6d7a8ff1d56832486d93e11b70fd1bba46bf5`；原manifest SHA：`c94f251b092422b45fd96f46ccf90a22e457fbe386e0cc424b997a9c552a787b`。

checkpoint包含完整model/AdamW/scheduler/RNG/累计720、原config max200、source SHA、独立预算、520实际记录和顺序、数据代码SHA及保存时资源快照；最终监督记录另由伴随清单绑定。可信本地恢复148组AdamW内部step720、全部状态与模式相同，完整171输出逐元素一致，无第721次更新。原v3—v7数据、统计、checkpoint与历史资格不改。

## 6. 文件、命令与图表

核心文件位于`experiments/fourcastden_den_multisample_continuation_v8/`与`results/fourcastden_den_multisample_continuation_v8/`：

- plan/preflight/source_checkpoint_audit/initial_restore_gate/checkpoint_restore/engineering_gate/GPU_result/final_audit。
- training_updates.csv（520条）；combined_training_updates_1_720.csv（历史只读200+新增520）；cumulative_exposures.csv（每对10）；pair10_visits_loss.csv。
- AI_2021/2022_hourly及summary；v7_v8_Persistence.csv；逐层标准化损失、独立物理复算和共同正域log指标。

实际入口（已执行，启动标记禁止同tag重放）：

```bash
source scripts/activate_orbit.sh
CUDA_VISIBLE_DEVICES='' python -m unittest discover -s tests -p test_den_multisample_continuation_v8.py
CUDA_VISIBLE_DEVICES='' python scripts/prepare_den_multisample_v8.py
python scripts/launch_den_multisample_v8.py
CUDA_VISIBLE_DEVICES='' python scripts/finalize_den_multisample_v8.py
```

CPU禁用GPU只作用于各自子进程，不改变训练可见性。完整9组测试与实际命令/日志见本tag commands.json。全部文件/缓存/日志/临时位置在项目内。

实际9张图（同结果目录）：

1. `01_loss_1_720.png`：历史与新520步损失、完整72访问轮次描述。
2. `02_pair10_visit_losses.png`：全部72对10次访问，不择优样本。
3. `03_2021_v7_v8_Persistence.png`：全部训练集聚合。
4. `04_2022_v7_v8_Persistence.png`：全部开发集，非盲测。
5. `05_all29_layer_errors.png`：完整29层，无筛层。
6. `06_all72_training_pair_errors.png`：全部72对小时误差。
7. `07_fixed2022_pair0_ilev24.png`：预固定pair0/ilev24，共物理色标，TIE标签不是卫星观测。
8. `08_physical_validity.png`：年份/层/纬区非正与正值率。
9. `09_actual_training_resources.png`：实际更新/进程GPU与CPU/分项成本。

## 7. 判断和停止条件

A：增加训练长度使训练全层relative RMS降低40.174961%，全部72对、29层都改善，说明v7存在可由更多更新改善的优化不足。

B：没有达到Persistence，0/72对、0/29层胜过P。不能称训练标签已充分掌握；末轮仍降低8.42%，也不能宣称明确平台。

C：开发相对RMS降低33.294283%，仍为P3.375倍，未接近基线。归入“训练与开发同步改善，但尚无预测优势”，不是可靠跨年泛化。

D：下一轮建议优先预注册**残差式DEN单因素对照**，不是继续无限加步；强Persistence与高层剩余误差使“小变化量”建模值得实际检验。但直接DEN尚未平台，不能预先认定残差更好或否定继续优化的潜力。520次持续裁剪与normalized/relative层分布不一致是诊断线索，不是已证实根因。详细受控对照与资源方案见`docs/FOURCASTDEN_DEN_MULTISAMPLE_V8_NEXT_DECISION.md`，本轮未执行。

工程恢复/更新/评价/可信checkpoint=PASS；Persistence优势=FAIL；`SCIENCE_TRAINING_READY=False`、`EXTERNAL_DATUM_UNVERIFIED`、`SCIENTIFIC_REAL_ORBIT_VALIDATION_READY=BLOCKED`、A14工程PARTIAL与历史FAIL不变。Git只公开轻量代码/审计/CSV/PNG/报告，不上传checkpoint、全预测或原始数据。同步结果以本tag本地核验记录为准。完成即停止。
