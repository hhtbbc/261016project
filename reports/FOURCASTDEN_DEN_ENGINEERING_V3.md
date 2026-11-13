# DEN专项工程数据集v3与真实训练预检

日期：2026-11-13。Tag：`fourcastden_den_engineering_v3`。

**结果：数据集、训练专用归一化、Persistence与CPU契约PASS；唯一GPU任务在首个forward前失败，实际0次更新。未重试。尚未跑通真实AFNONet梯度训练与独立AI验证。** 不因GPU失败隐去已完成的数据证据，也不以CPU合成网络替代真实训练成果。

## 数据来源与身份

|用途|来源|UTC窗口|小时帧/单步对|工程身份|
|---|---|---|---:|---|
|训练|`experiments/tiegcm_2021_spinup_14day_v1/B14`|2021-03-23 00至03-26 00|73/72|原独立工程PASS|
|验证|`experiments/tiegcm_2022_b14_exploratory_pair_v2/B14`|2022-03-23 00至03-25 00|49/48|v2独立工程PASS|

两年均来自可核验的官方smax完整初态及14天候选预热。选择依据为来源与工程身份，不是Swarm误差排名。本轮不用2022 A14标签，其历史工程PARTIAL不变。旧122帧只读、不替换。新数据同样122帧，但来源、路径、统计、身份全部独立。

身份：`DEN_ONLY / ENGINEERING_RESEARCH / HINDCAST / LIMITED_PHYSICAL_VALIDATION`。原始模拟未改；模型质量混合比残余、外部高度、真实受力等限制未解除。当前真实多变量状态输入也有物理验证局限，DEN专项不等于全部输入物理质量PASS。

产物位于`data/processed/fourcastden_den_engineering_v3/{2021,2022}`，每帧14-key NPZ；manifest保存绝对UTC、原NetCDF/记录号、SHA、bytes。每帧与原NC float32转换逐元素相等，时间连续、无重复/缺失。DEN正、TN正、全部物理值有限/无有限哨兵、ZG列严格递增；不补值、不外推。图与Persistence不要求外部高度登记。

`grid.npz`另存真实lat/lon/lev/ilev；两年网格与作者static纬经网格精确一致。`grid_audit.json`给出所有轴。DEN/WN/Z/ZG在29个ilev，TN/UN/VN仅28个有效lev，顶部缺失层明确去掉。Z为位势高度、ZG为几何高度，绝不互换。DEN原g/cm³，物理评价乘1000得到kg/m³；Z/ZG原cm，几何分组ZG乘0.01成m。

## 数据接口、归一化与损失

直接复用作者`read_var`/`TGCMDataset`/`get_channel_index`及现有`EpochPairs`、`OfficialFrameSource`、`AffineNormalizer`、`DirectTrainer`。不修改`pipeline.py`与`readonly_interface.py`，不读官方权重或替换官方static均值标准差。

171顺序为TN28、UN28、VN28、WN29、Z29、DEN29；作者实际索引证实DEN为零起点142:171。X=[1,177,36,72]：当前171状态+下一小时TLBC/ULBC/VLBC三通道+solar elevation一通道+磁纬/磁经二通道；D=[1,1,4]：下一小时F107、F107A、Kp经作者固定范围变换，及作者sfeps太阳条件。Y=[1,171,36,72]，实际损失只用Y_DEN=[1,29,36,72]。

未来合法辅助/驱动可用，未来TN/风/Z/DEN不能进X。120对逐一作者拼接精确一致、未来全部物理真值毒化不改变X/D；目标Y确实变化。使用实际未来驱动，严格标为HINDCAST。

仅2021的73帧、每通道189216点拟合174通道统计（171物理+3LBC）；float64分批Welford population variance与完整独立两遍算法一致。按变量/层标准化，原物理单位保持，DEN使用线性标准化，没有log变换。太阳/磁场/四条件沿作者独立公式，不能一概标准化。2022只套用2021统计；2023未使用；官方static未改。2022验证分布存在明显偏移：在原生ilev索引18，其DEN均值相对2021训练均值为-3.4221个训练标准差。该描述不用于重拟合统计或调参，不能由两个短窗口推出全年泛化结论。

预先冻结的极小std判据：std≤1e-12×max(|mean|,maxabs,float64tiny)；若成立使用|mean|，mean=0时用1原生单位，不按验证表现调节。实际0个通道触发。最大encode/decode归一化往返误差4.76731e-7，DEN相对往返误差2.40071e-8。`statistics.json`保存73个拟合SHA与174均值/std，CSV亦可公开；NPZ统计留本地。

方案A保留原AFNONet171头、随机初始化，只监督DEN29。方案B改29输出头可省少量开销，但改变作者结构与权重兼容性。本轮选A以复用原实现。其他142个头无DEN直接梯度，不能声称被训练；共享表征变化也不能赋予其预测资格，禁止直接全状态自回归。

损失为cos(latitude)归一化面积权重下的29通道normalized MSE；不是物理DEN全层绝对MSE。CPU小模型实际forward/backward、DEN梯度、非DEN头零梯度与参数更新、验证no_grad和可信本地checkpoint恢复通过，但不是完整真实AFNONet的GPU通过证据。

## Persistence实际结果

定义DEN_pred(t+1)=DEN(t)。所有120对、全空间/全层有效、正值与log有效覆盖100%。cos纬度加权，各层等权、小时等权；先逐小时计算，再对RMSE平方等权平均取根。相对误差分母为严格正目标，无人为floor。log RMS使用自然对数p/t；未来AI若负值，仍纳入普通RMSE/相对误差，同时明确log有效域，不能删负预测改善指标。

|年份/组|单步对|RMSE kg/m³|相对RMS|Bias kg/m³|log RMS|
|---|---:|---:|---:|---:|---:|
|2021 全29层|72|3.472136e-9|1.722953%|9.803486e-14|0.01727446|
|2022 全29层|48|3.474371e-9|1.992488%|2.306140e-12|0.01998404|
|2021 上层索引20—28|72|4.528039e-14|1.793025%|−1.185224e-19|0.01804310|
|2022 上层索引20—28|48|4.934252e-14|2.242242%|4.951751e-16|0.02253237|
|2021 顶层28|72|3.256091e-15|2.451758%|2.775869e-17|0.02450688|
|2022 顶层28|48|3.259356e-15|2.909416%|5.882783e-17|0.02900126|
|2021 参考ZG中位数400—500km相关层组|72|8.267787e-15|1.772956%|2.906685e-17|0.01785370|
|2022 同定义相关层组|48|1.735486e-14|2.085079%|2.756619e-16|0.02101501|

全层绝对RMSE由底部高密度主导，不能拿它代表400km误差。最后两行按每个目标帧参考ZG的层中位数筛选，层组可变，不是固定几何高度切片。所有逐层、南高纬/北高纬（|lat|≥60°）、中低纬和逐小时明细见`results/fourcastden_den_engineering_v3/persistence_*csv`；共同完整格点域，无失败删样。独立直接数组求和复核所有120对全层全球指标通过。

这些是相对本项目TIE-GCM标签的持续性预测误差，不是Swarm观测误差。跨年差异同时包含年份环境/驱动/结构差，不能解释为单一因果；120个相邻小时对也不是120次独立天气实验。

## GPU唯一任务与已证实故障

预检A100-SXM4-80GB、PyTorch2.4.1+cu121/CUDA12.1、81153MiB空闲、无其他GPU进程，独立能力探测CUDA可用。冻结计划10更新/48验证，含检查点与固定样本探针合计62次预期forward，不能将额外探针隐去。原AFNONet约64695744参数；计划AdamW1e-4、weight_decay0、batch1、clip1、常数学习率、seed20261113、CuBLAS :4096:8、fp32确定性；原权重不加载。

唯一worker由通用监督器直接Popen并wait，真实退出码1、监督2.927959秒、采样峰值树RSS472109056 bytes（450.238MiB）。**实际模型forward=0、backward=0、optimizer.step=0、checkpoint=0、AI验证=0**；模型构造在CUDA检查之后，没有执行。GPU allocator峰值未取得，不能写为实测0；监督采样GPU占用为0不等于连续峰值测量。

直接调用链：worker先设置CUDA_VISIBLE_DEVICES='0' → 导入Persistence的aggregate/csvout → 原Persistence模块级赋值CUDA_VISIBLE_DEVICES='' → worker的torch.cuda.is_available断言失败。预检未导入同一模块，因此未捕获。`GPU_preflight.json`保留失败时旧代码SHA，`GPU_failure_audit.json`和原stdout/exit status保留真实证据。

最小修复仅将Persistence设备选择移至其独立`__main__`，消除导入副作用；新增子进程import-isolation测试，设备选择保持'0'，PASS，未调用CUDA。修复后的SHA与实际失败执行时SHA分别记录，绝不把修改后文件当作失败时原件。未再次运行GPU、未删启动标记。该可避免的实现错误使本轮未完成真实训练；CPU数据成果仍独立有效。

不绘制不存在的loss曲线、AI/Persistence验证或AI预测面板；无下降/超越Persistence/跨年泛化结论。GPU checkpoint恢复仍NOT_TESTED，CPU小模型恢复PASS不能代替。

## 实际图与测试/资源

`results/fourcastden_den_engineering_v3/`：

1. `01_density_distribution.png`：两年全部候选DEN中位数和空间/时间P05—P95（描述性分布，不是置信区间）。
2. `02_normalization.png`：2021拟合均值/std及两年encoded描述统计；2022未拟合。
3. `03_persistence.png`：逐层、上层不同纬度区域相对RMS。
4. `04_fixed_real_DEN_sample.png`：预先冻结2022首对00→01 UTC、ilev24的真实标签/Persistence/有符号误差，未事后挑样。AI不存在，未画AI曲线。

CPU训练前25项测试（9新增DEN、8原训练pipeline、8原真实接口）通过；失败修复后新增1项导入环境隔离通过，共26。另120对真实契约/毒化检查及122帧原值/SHA审计通过。原246个保护资产SHA全部不变，含两年B14、旧候选、官方权重/static与原代码。

提取/独立统计/契约成功阶段31.197秒、CPU进程峰值1095.340MiB；Persistence4.904秒、467.105MiB；最终独立审计与绘图46.394秒、743.527MiB。GPU监督2.928秒，与上述CPU耗时分开，非模型训练速度。新数据约241MiB、结果约3.9MiB；未产生checkpoint，未接近2GiB训练输出上限。

CPU阶段两次失败保留：①单位字符串断言sfu对实际1.e-22 W/m2/Hz，修正为明确等价单位后重做，未改物理数值；②统计独立校验脚本ROOT[...]路径拼写错，修复后只读核验已提取NPZ继续，不覆盖旧数据。均未启动GPU/TIE。全部日志含原错误及最终PASS，见日志清单。

## 验收与后续

|项目|状态|依据|
|V3_DATASET_READY|PASS|73/49原值、时间、字段和SHA|
|TRAIN_ONLY_NORMALIZATION_READY|PASS|73帧独立两法复核、2022未拟合|
|PERSISTENCE_READY|PASS|120对物理指标与独立求和复核|
|CPU_INPUT_AND_LOSS_READY|PASS|25+1测试、120对无泄漏|
|REAL_GPU_TRAINING_PREFLIGHT_READY|FAIL|唯一任务首forward前rc1，0更新|
|REAL_AI_VALIDATION_READY|NOT_RUN|无模型预测|
|GPU_CHECKPOINT_RECOVERY_READY|NOT_TESTED|无真实模型checkpoint|
|SCIENCE_TRAINING_READY|False|完整物理/规模资格未通过|

下一步优先新tag重新申请同配置≤10更新工程预检，再根据实际成本申请固定样本过拟合/72对小规模训练。现在不直接申请正式全状态或多步训练。详细可执行配置、1800秒候选预算、季节覆盖与分层评价见`docs/FOURCASTDEN_DEN_V3_NEXT_TRAINING_DECISION.md`。EXTERNAL_DATUM_UNVERIFIED、真实Swarm轨道BLOCKED、2022A14 PARTIAL、历史数值FAIL均不改变。

## 命令与重放限制

```bash
cd /workspace/data/20261016
source scripts/activate_orbit.sh
python scripts/prepare_den_engineering_v3.py
python scripts/build_den_engineering_v3.py
python scripts/persistence_den_engineering_v3.py
python -m unittest discover -s tests -p test_den_engineering_v3.py
python -m unittest discover -s tests -p test_training_pipeline.py
python -m unittest discover -s tests -p test_fourcastden_real_data_interface.py
python scripts/launch_den_engineering_v3.py  # 本轮唯一启动已消耗，禁止重放
python -m unittest discover -s tests -p test_den_import_isolation.py
python scripts/finalize_den_engineering_v3.py
```

以上是实际执行入口，不是允许再次执行已有tag的指令。构建/统计/报告多数采用独占创建，旧产物保留；要复现生成流程须另授权新tag，不能删除旧启动标记。现有数据可只读运行测试。关键SHA见`dataset_manifest.json`、`statistics.json`、`protected_files.json`、`GPU_preflight.json`和最终`delivery_sha256.json`。原始NPZ/NC、统计NPZ、GPU原日志与未来checkpoint不上传公开仓库；公开轻量指标、代码、报告和图。
