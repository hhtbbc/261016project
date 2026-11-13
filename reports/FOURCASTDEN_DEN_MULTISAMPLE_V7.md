# AFNONet 72对真实DEN多样本训练 v7

日期：2026-11-13。实验身份：`fourcastden_den_multisample_v7`；`DEN_ONLY / ENGINEERING_RESEARCH / HINDCAST / LIMITED_PHYSICAL_VALIDATION`。

本轮唯一GPU任务完成200次真实参数更新和321次模型forward，完整评价72对训练样本、48对2022开发验证样本。工程链路通过；模型尚未达到Persistence，不能称为科学预测能力通过。无新TIE-GCM、下载、统计拟合、数据提取、轨道传播或多步反馈。

## 1. 输入、模型与预注册协议

- 起始Git main：`2006ae2579bd36c90c336619ade21ebd7be8b318`，本地与远端一致；保留所有历史未跟踪同步日志。
- 2021 B14：03-23 00至03-26 00 UTC，73帧/72对，用于训练。2022 B14：03-23 00至03-25 00 UTC，49帧/48对，仅最终开发验证。
- 数据直接复用DEN v3，全部122帧SHA、DEN有限正值、ZG逐列递增、120对时间和张量契约通过；所有120对未来物理真值毒化检查不改变X/D。DEN往返转换最大相对误差`2.400706e-8`。
- `X[1,177,36,72]`为当前171通道物理状态与合法下一时刻6辅助；`D[1,1,4]`为作者四驱动标量；`Y[1,171,36,72]`为下一小时物理标签。未来TN/风/Z/DEN不进入输入。条件使用历史已知驱动，属于HINDCAST。
- DEN通道142:171（0-based），29个原生ilev；作者变量次序TN/UN/VN各28，WN/Z/DEN各29。DEN原始g/cm³乘1000转kg/m³；ZG cm乘.01转m，Z位势高度与ZG不混用。原生层评价不代表固定几何高度评价。
- 原始AFNONet64695744参数，177输入/4条件/171输出，FP32，seed20261113。从随机初始化开始，**未加载v4/v5/v6或官方权重**。初始全state SHA与v5/v6初始模型预期逐字相同。
- AdamW lr1e-4、weight_decay0；StepLR step_size1/gamma1；clip前L2记录、clip阈值1；batch1。损失仅DEN29通道的cos纬度面积加权normalized MSE，继续使用2021专用线性归一化。
- `pair_index=(step-1)%72`，更新1—72与73—144各完整一轮，145—200为0—55。前56对各3次，后16对各2次，总200，未改成216。
- 预先冻结forward：训练200+最终训练集72+最终验证48+恢复探针1=321。没有初始完整72对模型评价，也没有中途2022验证；不能声称测得完整训练集初始物理误差下降多少。
- 原始每步loss保留；趋势仅预注册尾随24步算术均值，前23步N/A。各步样本不同，相邻loss不是单样本收敛曲线。

冻结文件：[plan.json](../experiments/fourcastden_den_multisample_v7/plan.json)、[顺序表](../results/fourcastden_den_multisample_v7/frozen_training_order.csv)、[数据审计](../experiments/fourcastden_den_multisample_v7/data_audit.json)。不重建原122帧、不改变A14历史PARTIAL。

## 2. 工程验证

57项CPU测试通过：新增9项顺序/曝光/预算/初始SHA门禁/跨年隔离/验证无更新/重复启动/资源限制测试，原48项恢复、过拟合、CUDA环境、DEN数据、pipeline和真实接口回归。CPU合成夹具不作为真实模型训练证据。

实际GPU初始化全state SHA通过；200次optimizer.step按顺序完成，每次148个有限非零梯度张量、有效head参数确实变化。DEN之外142个输出head行梯度0且参数逐元素不变。共享骨干仍被DEN损失更新，其他142通道并非已训练物理预测；不能用于全状态自回归。作者已有闲置`norm.weight/norm.bias`没有梯度，按原实现保留。

clip前梯度L2范围12.1643—294.4169，200次均触发clip1；没有非有限损失/梯度或未更新。全程常数lr，无重试或调参。训练loss首步162.235962、末步0.669284，样本不同，不能把该比值解释为同一样本学习率。72对各自最后一次访问的pre-update loss均低于其第一次访问；首访均值10.03422、末访0.563178。这是不同模型时刻的描述，不是初始/最终整训练集同一评价。

最终step200 eval normalized loss：72训练均值0.653466，48开发验证均值3.359030；它们与下表物理relative RMS不是同一种量。

所有最终评价均eval/no_grad，模型/AdamW SHA、step200及空梯度保持不变。真实forward hook计数为200/72/48/1，GPU结果与监督器exit0/PASS相互核验。完整checkpoint恢复模型/AdamW/scheduler/Python-NumPy-Torch-CUDA RNG和模式，通过171通道输出逐元素一致探针；未执行201步。

## 3. 物理评价与Persistence

定义：每小时cos(latitude)权重、经度均匀、所选层等权；relative RMS=`sqrt(weighted_mean(((pred-target)/target)^2))`，目标严格正值，无事后分母下限；跨小时平方后等小时平均再开方。RMSE/Bias单位kg/m³。原生DEN跨度很大，跨层绝对RMSE受低层大密度影响，应同时读逐层和relative指标。log RMS为自然对数比误差，另列，不混为普通relative RMS。

| 年份/样本 | 范围 | v7 relative RMS | Persistence | v7 RMSE kg/m³ | v7 Bias kg/m³ |
|---|---|---:|---:|---:|---:|
| 2021训练72 | 全29层 | 3.804484% | 1.722953% | 6.914421e-9 | -1.229574e-11 |
| 2021训练72 | 上层20—28 | 4.347241% | 1.793025% | 1.100659e-13 | 6.106602e-16 |
| 2021训练72 | 顶层28 | 5.609567% | 2.451758% | 7.362872e-15 | -1.787919e-16 |
| 2022开发48 | 全29层 | 10.082082% | 1.992488% | 1.356177e-8 | -1.267293e-9 |
| 2022开发48 | 上层20—28 | 12.401138% | 2.242242% | 2.791978e-13 | 7.834357e-14 |
| 2022开发48 | 顶层28 | 13.167300% | 2.909416% | 1.407793e-14 | 5.261776e-15 |

2021全72对误差范围3.250987%—4.217717%，没有只拟合好第一对的现象；第一对3.757451%，其余71对合并约3.8051%。**72对中0对胜过同对Persistence，全年聚合29层中0层胜过Persistence。** 三次曝光组3.750731%、两次曝光组3.986916%，与时间/驱动/顺序混杂，不能归因于曝光次数本身。

2022各对全层误差范围9.527256%—10.746636%，29层中0层胜过Persistence。训练与验证全层误差差6.277598个百分点；验证约为训练2.65倍，约为验证Persistence5.06倍。存在开发集性能差距，但不能仅凭差距认定唯一原因是过拟合或样本量。

| 区域（全29层） | 2021 AI/P relative RMS | 2022 AI/P relative RMS |
|---|---:|---:|
| \|lat\|<60° | 3.42449 / 1.79203% | 10.14650 / 2.08683% |
| 北高纬≥60° | 5.74979 / 1.20627% | 9.86857 / 1.25038% |
| 南高纬≤-60° | 5.60373 / 1.15893% | 9.43719 / 1.18367% |

2021原生层1最低2.081215%、顶层28最高5.609567%；2022层1最低4.315675%、层27最高15.402624%，高层误差更明显。该索引不是固定高度。

最终2021的5412096个、2022的3608064个预测均有限且正：非正数均0，正值率/普通覆盖/log有效域均100%。普通指标没有裁剪或删除差样本。全层log RMS为0.0382602/0.0951513（无量纲）；在AI正值共同域上另算Persistence配对log，不将正值域结果冒充无条件指标。

独立CPU直接从保存数组与原标签逐点加权复算全部120个全层RMSE/relative RMS/Bias；Persistence120对全部区域/逐层指标与v3冻结CSV逐值一致。共586个历史数据、统计、代码、checkpoint与历史产物SHA保持一致。逐层/纬区详细值见[AI_vs_Persistence.csv](../results/fourcastden_den_multisample_v7/AI_vs_Persistence.csv)、[逐点数组独立汇总](../results/fourcastden_den_multisample_v7/independent_array_metrics.csv)。

## 4. 与单样本v6的受控比较

| 同一评价域 | 范围 | v6单样本200 | v7多样本200 | Persistence |
|---|---|---:|---:|---:|
| 首对2021 00→01 UTC | 全层 | 1.419518% | 3.757451% | 1.673781% |
| 首对2021 | 上层20—28 | 1.547587% | 4.322009% | 1.748587% |
| 首对2021 | 顶层28 | 2.048351% | 5.653223% | 2.372184% |
| 2022全部48 | 全层 | 19.711886% | 10.082082% | 1.992488% |
| 2022全部48 | 上层20—28 | 23.897766% | 12.401138% | 2.242242% |
| 2022全部48 | 顶层28 | 26.411914% | 13.167300% | 2.909416% |

v7的2022全层误差较v6下降48.852777%，且v6的13个非正预测变为v7的0个。模型不再仅反复适应一个时刻，但每对只有2—3次访问，首对拟合弱于v6。相同更新总数下梯度样本组织不同，是训练策略对照，不能称单纯时间消融。v6没有全72对训练评价，保持NOT_AVAILABLE；本轮未加载v6权重，也未额外推理。

2022已被多轮开发查看，不是盲测。两年都仅三月短窗口，时间样本高度相关，格点数量不是独立科学实验次数。2022相对2021训练统计存在分布差异，不能因误差下降宣布跨季节/跨太阳活动可靠泛化。

## 5. 实际资源、SHA和复现

唯一任务监督79.098605秒，worker76.279626秒；纯200次更新24.545047秒（均值0.122725秒/中位0.119255秒），训练循环29.189485秒；CPU缓存2.848311秒、建模1.950818秒、最终训练72评价5.984823秒、开发48评价5.979260秒、保存/恢复7.211193秒、数组保存3.236812秒。部分计时存在包含关系，不能简单相加为总耗时。

A100-SXM4-80GB，PyTorch2.4.1+cu121/CUDA12.1。CUDA_VISIBLE_DEVICES原环境未显式设置且只有1个可见设备，继承未改；torch导入前CuBLAS`:4096:8`，FP32确定性算法。峰值allocated1.521465GiB/reserved1.710938GiB，nvidia-smi进程采样2.261719GiB，CPU树RSS采样2.385857GiB；77次资源样本、0监控缺口。worker统计产物0.789264GiB，checkpoint与预测数组均仅本地。所有资源低于300秒/20GiB GPU/8GiB RSS/2GiB输出门槛，磁盘余量远大于20GiB。独立CPU后处理30.261631秒/633.004MiB。

关键SHA256：

- 初始模型：`b3c177d26245e7be75f25995f243318b47f8a44148645010f6a3d4cfe16a68e7`。
- 最终模型state：`b8ced924267b8f576bece552c88ef066af33f1e4cd3d84d6935a52faa084060e`。
- v3统计：`df9a8c2bd31026de0e0ebcae07c6d7a8ff1d56832486d93e11b70fd1bba46bf5`。
- v3清单：`c94f251b092422b45fd96f46ccf90a22e457fbe386e0cc424b997a9c552a787b`。
- 最终本地`experiments/fourcastden_den_multisample_v7/step200.pt`：`82483f890db2d20ec00159ff0588217dd71d37889195ca5b77b1b3ac740e722f`。

[preflight.json](../experiments/fourcastden_den_multisample_v7/preflight.json)冻结启动时全部输入/关键代码/作者实现SHA；[checkpoint_restore.json](../experiments/fourcastden_den_multisample_v7/checkpoint_restore.json)保存实际恢复证明；checkpoint伴随包清单绑定完整checkpoint、顺序、更新日志、协议和恢复记录。完整状态包含model/AdamW/scheduler/RNG/步数/索引序列/源数据与代码SHA/资源快照，最终监督资源另由伴随文件绑定，不追写旧权重。

```bash
source scripts/activate_orbit.sh
# 每个测试独立CPU子进程；完整列表见commands.json
CUDA_VISIBLE_DEVICES='' python -m unittest discover -s tests -p test_den_multisample_v7.py
python scripts/prepare_den_multisample_v7.py
python scripts/launch_den_multisample_v7.py  # 本轮已执行；一次性标记禁止重放
CUDA_VISIBLE_DEVICES='' python scripts/finalize_den_multisample_v7.py
```

实际重定向命令和全部8组CPU日志见[commands.json](../experiments/fourcastden_den_multisample_v7/commands.json)。上述CPU显式禁用只作用于各自子进程；GPU进程不继承该临时禁用。

## 6. 科研图表

均为实际计算，模型评价仅最终step200，固定展示开发pair0/ilev24，未挑选优样本。

1. [实际loss与样本顺序](../results/fourcastden_den_multisample_v7/01_training_loss_and_order.png)
2. [全部72对训练误差](../results/fourcastden_den_multisample_v7/02_all72_training_pairs.png)
3. [训练/开发集与Persistence](../results/fourcastden_den_multisample_v7/03_train_development_validation.png)
4. [同首对v6/v7](../results/fourcastden_den_multisample_v7/04_v6_v7_first_pair.png)
5. [29层完整对比](../results/fourcastden_den_multisample_v7/05_layer_relative_RMS.png)
6. [冻结2022 pair0/ilev24地图](../results/fourcastden_den_multisample_v7/06_fixed_validation_pair0_ilev24.png)
7. [非正密度与有效域](../results/fourcastden_den_multisample_v7/07_physical_validity.png)
8. [实际资源与成本](../results/fourcastden_den_multisample_v7/08_actual_training_resources.png)

## 7. 结论与门禁

A：模型已学习全部72对，误差分布较均匀、各对访问损失改善，但最终训练全层仍为Persistence的2.21倍，不能称已充分拟合或具有预测优势。

B：2022误差较v6显著下降，但仍为Persistence的5.06倍；不是可靠泛化证据。

C：训练预算仅2—3次访问，训练集也未达到Persistence，支持优先检验训练不足；两年短窗口和统计偏移是覆盖风险证据，但不能证明它们解释了全部误差。高层误差提示线性DEN目标和normalized loss与relative误差可能不匹配，仍是待单因素验证的假设；本轮没有比较残差/log/正值参数化，不能断言当前直接预测方法已被否定。没有看到仅首对拟合、其他训练对全坏的现象。

D：建议下一轮先做同72对、相同方法的训练长度单因素接续至累计720步；仅建议，未执行。若训练集达基线后开发误差仍大，优先残差DEN，再独立研究log-DEN；正值参数化作为结构约束单独对照，不能因本轮0非正认为全域保证正值。详见[下一步决策](../docs/FOURCASTDEN_DEN_MULTISAMPLE_V7_NEXT_DECISION.md)。

`MULTISAMPLE_GPU_ENGINEERING=PASS`；`PERSISTENCE_ADVANTAGE=FAIL`；`SCIENCE_TRAINING_READY=False`；`EXTERNAL_DATUM_UNVERIFIED`；`SCIENTIFIC_REAL_ORBIT_VALIDATION_READY=BLOCKED`；A14历史PARTIAL与所有旧FAIL不改。没有许可将未监督142通道用于多步反馈。全部成果本地先保存，Git同步结果另见本tag同步审计，原数据/权重不公开。
