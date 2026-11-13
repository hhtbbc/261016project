# CUDA环境修复与首次真实DEN GPU训练v4

日期：2026-11-13。Tag：`fourcastden_den_gpu_smoke_v4`。基线本地与远端main均`1e9d0740c456add606449a1754847c97d2a1cabb`。本轮无新TIE、Swarm下载、数据提取、统计拟合、轨道或多步预测。

**首次实现本项目自主TIE-GCM数据 → 原AFNONet真实GPU forward → DEN-only loss → backward → optimizer.step，共10次更新。完整48对2022验证、checkpoint恢复通过。当前AI显著劣于Persistence，存在非正密度，不能认定预测模型或科学训练通过。**

## 1. 根因、修复与实际调用链

历史v3在第一次forward之前退出码1。核对原`gpu_job/stdout.log`、`GPU_preflight.json`旧SHA及`import_fix.patch`可还原实际代码：worker把CUDA_VISIBLE_DEVICES设0，随后导入Persistence的aggregate/csvout，其旧模块级赋值清空该变量，导致torch.cuda.is_available断言失败。上一轮只将清空移到Persistence main，消除了该次导入污染，但仍保留若干CPU入口的可见性赋值和旧launcher/worker强制0。

本轮去掉DEN v3构建、后处理、Persistence以及旧worker/launcher中对CUDA_VISIBLE_DEVICES的赋值；不重新执行旧tag、不改旧失败JSON。旧源码版本仍由Git和历史SHA追溯。新增`runtime/gpu_environment.py`只在显式调用时设置CuBLAS，普通导入无设备修改；拒绝显式禁GPU/异常配置，不扩展用户/调度分配。设备选择是继承分配内的逻辑cuda:0，绝不把外部GPU编号改成0。

新worker流程：configure_determinism（第一次torch导入前CUBLAS=:4096:8）→ torch/真实DEN/Persistence相同依赖顺序 → assert_visibility → 实际require_cuda → GPU张量检查 → 随机原AFNONet。launcher的能力检查使用相同导入顺序、0个模型forward，不启动第二个训练任务。parent不改设备；实际继承CUDA_VISIBLE_DEVICES未设置、单个A100可见，与启动前后完全一致。明确禁用时CPU/Mock测试证实不进入CUDA/模型初始化。

11项新增环境测试覆盖None/空/-1/单设备编号/UUID、不同顺序、CPU密度评价、子进程隔离、调度分配保留、异常拒绝、CuBLAS冲突与CUDA不可用。另DEN9、pipeline8、真实接口8、import1通过，共**37项CPU测试**。此前“246项”实际是保护文件SHA数量，不是246项测试；不混用计数。

## 2. 数据、通道与归一化只读验收

2021 B14训练73帧/72对、2022 B14验证49帧/48对，来自v3原NPZ与原NetCDF；同smax来源/各自工程PASS。不使用2022A14标签，A14历史PARTIAL不变。2021窗口03-23 00至03-26 00，2022至03-25 00；本轮仅2021前10对（目标03-23 01至10 UTC）做梯度，2022全部48对独立验证。

只读审计412项冻结资产（含原246项、v3数据/统计/报告/结果/失败身份与历史日志），最终SHA全部一致。未提取/重写数据、未拟合统计。原统计SHA：`df9a8c2bd31026de0e0ebcae07c6d7a8ff1d56832486d93e11b70fd1bba46bf5`。2021训练73帧统计按变量/层float64拟合的历史记录保留；2022/2023未进拟合。

作者`get_channel_index`再次证实顺序TN28/UN28/VN28/WN29/Z29/DEN29，DEN零起点142:171；DEN/WN/Z为ilev，TN/UN/VN有效28lev。X=[1,177,36,72]、D=[1,1,4]、Y=[1,171,36,72]、Y_DEN=[1,29,36,72]。当前171真状态+目标时刻合法LBC/太阳/磁坐标辅助及四标量条件，保持作者契约。使用实际未来驱动故为HINDCAST；120对完整物理目标毒化不改X/D，120对形状/有限值、122帧DEN正/ZG单调与encode/decode复核通过。Z不作ZG，DEN g/cm³×1000到kg/m³，ZG cm×0.01到m。

## 3. 原AFNONet与实际DEN-only监督

保留作者网络64,695,744参数，177输入/4条件/171输出，patch4、embed768、depth12、blocks8、mlp4、drop0，FP32、不加载官方权重。seed20261113、AdamW lr1e-4、weight_decay0、StepLR gamma1（常数LR）、batch1、clip1，与v3预注册相同。

复用独立DenTrainer.loss，只对142:171计算cos纬度面积加权normalized MSE，不调用通用171损失。加权方案来自v3冻结协议，物理评价另解码；不能把normalized loss与相对RMS混为同一量。每步非DEN头142通道梯度精确0、对应头参数精确不变；148个梯度张量全部有限且非零，head有效参数变化L2为0.05984至0.03224。其余142输出未监督，不能当可靠物理场或用于全状态自回归。

每步报告无梯度参数`norm.weight`/`norm.bias`：作者AFNONet在321行声明最终norm，354—384行forward_features/forward没有调用它；这是未改网络中的闲置参数，不是所有参数都应有梯度。block内norm1/norm2确实使用且有梯度。完整源码冻结SHA保留。

## 4. 实际训练与checkpoint

|实际step|normalized DEN loss|clip前梯度L2|
|---:|---:|---:|
|1|162.235962|294.416887|
|2|96.244850|165.086726|
|3|66.824501|134.253970|
|4|49.529663|106.489520|
|5|38.626747|88.221802|
|6|31.266232|76.109812|
|7|25.575634|64.300448|
|8|21.333300|57.756074|
|9|18.174831|53.093830|
|10|15.630704|48.144026|

各步使用不同的连续训练对，故另外对**同一个固定训练对0**比较：before162.2359619 → after14.35879993，下降91.15%；不是仅凭不同样本逐步曲线证明下降。2022全48对normalized loss36.12092574。训练与验证不是同分布样本，不能直接将差值解释为泛化精度。

唯一真实任务10次optimizer hook、10次更新、62次实际forward：10训练+2固定训练对前后探针+2checkpoint探针+48验证。所有额外forward事先冻结，不隐瞒。无额外优化器更新、无失败重试、未搜索参数。训练前后全模型SHA变化记录于GPU_result.json；2022 no_grad、梯度None、模型和optimizer state逐字节hash不变，step维持10。

第5步保存完整模型/AdamW/StepLR/RNG/config/输入代码SHA；释放旧模型后同一任务内恢复。模型、optimizer、scheduler精确一致，GPU固定输入输出逐元素精确一致，恢复step5后只执行6—10步；未重复更新。最终step10另存。两份可信本地checkpoint每份776596618 bytes，不加载外部pickle，不上传权重。

- step5 SHA：`f30aeba7bd553661ea6b9a14afd5665b64d66e24bc35db1be0327cb14c878dcd`
- step10 SHA：`ebe4056f0cfb4256fb2d31d542af3545ea20c8c4064dee3d44a6c7b69f808ce1`

## 5. 2022公平物理验证与Persistence

相同48目标时刻、相同格点/层/纬度、相同cos纬度与小时等权、同kg/m³解码。完整48对Persistence重新计算，与v3全部层/区原指标逐值一致；没有更换评估范围。普通RMSE/Bias/relativeRMS保留所有有限预测，分母严格正目标，无floor。保存的float32输出由独立直接数组求和复核全部48对指标，容差rtol5e-6仅用于输出序列化复算，不修改任何科学门槛。

|范围|AI相对RMS|Persistence相对RMS|AI RMSE kg/m³|Persistence RMSE kg/m³|
|---|---:|---:|---:|---:|
|全29层|31.851231%|1.992488%|4.638778e-8|3.474371e-9|
|上层20—28|38.221614%|2.242242%|8.897947e-13|4.934252e-14|
|顶层28|37.463726%|2.909416%|4.144891e-14|3.259356e-15|

AI Bias依次−5.118068e-9、+1.690660e-13、+1.176545e-14 kg/m³；Persistence依次+2.306140e-12、+4.951751e-16、+5.882783e-17。全部29个单层的相对RMS均劣于Persistence，不能挑层宣布模型有效。全层绝对RMSE由低层较高密度主导，不能当400km误差。

3608064个AI预测，非有限0，非正1316；数值有限覆盖100%、物理正值率99.963526%。上层正值率99.945434%、顶层99.971065%；不是物理有效率100%。原值保留，不裁剪/补值/删普通误差样本。对应逐层/区域/逐小时CSV包含正值与log覆盖率。

log在非正值处无定义：原AI conditional logRMS全层0.3315203、上层0.3911851、顶层0.3889139，并披露覆盖，不能与Persistence全域log直接当完全同域比较。因此新增**相同AI正值子域**配对log审查：AI0.3315203/0.3911851/0.3889139，Persistence0.0199782/0.0225207/0.0290006；该限制仅用于log，不删普通误差。仍显著更差，无经验分母下限。

这些是相对TIE-GCM标签的单步替代误差，不是Swarm真实密度/轨道精度。10步只说明优化与实现成功；数据小、跨年分布偏移、尚未充分学习是候选解释，不据两个窗口证明具体因果或泛化机制。

## 6. 资源、图表与审计

A100-SXM4-80GB、PyTorch2.4.1+cu121、CUDA12.1。真实监督exit0/PASS、38.743094秒；worker35.954204秒，含SHA与IO。纯更新平均0.156330秒、中位0.126887秒；模型/optimizer构造1.846713秒，样本读取/预处理合计2.083007秒，48对验证5.854184秒，第5步保存恢复5.167960秒，末次保存/输出1.833085秒。forward GPU事件中位31.686ms、62次合计2164.774ms。不同计时包含关系不同，不强行相加为端到端加速比。

allocated峰值1648030208 bytes=1.535GiB，reserved1.709GiB；监督进程GPU采样峰值2.260GiB（含上下文等，不等于allocated）。CPU自身ru_maxrss2091.582MiB，监督采样RSS1845.582MiB，采样不是连续峰值；采样缺口0。实际产物约1567526626 bytes（1.46GiB，后处理另增几MiB），两份checkpoint占主体，满足2GiB与20GiB GPU/900秒限制。盘余约1.3TiB。

只读审计43.056秒；完整后处理21.041秒/CPU峰值566.652MiB，单独记录，不冒充模型训练耗时。37项CPU测试、120对真实毒化/契约检查、412项冻结输入及v3数据/统计/失败资产最终SHA通过。原v3失败结果不更改；本轮新工程PASS不追溯修改原FAIL。

结果`results/fourcastden_den_gpu_smoke_v4/`：

1. `01_actual_training_loss.png`：实际10次更新、注明连续不同训练对。
2. `02_training_validation_separate_metrics.png`：固定训练对前后与2022 normalized loss，另面板物理relativeRMS，不混量纲。
3. `03_AI_persistence_by_layer.png`：完整29层AI与Persistence，全部劣势保留。
4. `04_frozen_real_DEN_prediction.png`：预先固定2022第0对/ilev24，三图同物理色标，不挑样。
5. `05_GPU_resources.png`：实际更新墙钟、allocator和监督采样。

训练/验证指标CSV、matched_positive_log_hourly.csv与独立物理复算CSV可公开；完整预测NPZ、两checkpoint、原始NPZ/NC保留本地。所有代码/输入/输出SHA见preflight/protected_inputs/GPU_result与delivery_sha256，实际退出与资源见gpu_job/status（另轻量复制）。

## 7. 状态和下一步

|项目|结论|
|---|---|
|CUDA_ENVIRONMENT_READY|PASS：继承设备、相同导入链、真实CUDA张量与任务|
|REAL_DEN_GPU_UPDATE_READY|PASS：10次真实更新、148个有限非零梯度张量|
|CHECKPOINT_RECOVERY_READY|PASS：第5步真实GPU精确恢复|
|INDEPENDENT_2022_EVALUATION_READY|PASS：48对no_grad且状态不变|
|AI_BEATS_PERSISTENCE|FAIL：三主要分组及全部单层均更差|
|PHYSICAL_POSITIVITY_READY|FAIL：1316个非正密度|
|SCIENCE_TRAINING_READY|False：工程成功不等于科学预测资格|

真实轨道仍BLOCKED，EXTERNAL_DATUM_UNVERIFIED、A14工程PARTIAL与旧数值实验FAIL均保留。下一轮优先100步固定2021样本过拟合，独立新tag、300秒/20GiB/2GiB预算候选；不自动执行。详细配置、200步后续候选与季节/活动覆盖及防止验证反复调参方案见`docs/FOURCASTDEN_DEN_GPU_V4_NEXT_TRAINING_PLAN.md`。

## 8. 实际命令与复现边界

```bash
cd /workspace/data/20261016
source scripts/activate_orbit.sh
CUDA_VISIBLE_DEVICES='' python -m unittest discover -s tests -p test_den_gpu_environment_v4.py
CUDA_VISIBLE_DEVICES='' python -m unittest discover -s tests -p test_den_engineering_v3.py
CUDA_VISIBLE_DEVICES='' python -m unittest discover -s tests -p test_training_pipeline.py
CUDA_VISIBLE_DEVICES='' python -m unittest discover -s tests -p test_fourcastden_real_data_interface.py
CUDA_VISIBLE_DEVICES='' python -m unittest discover -s tests -p test_den_import_isolation.py
python scripts/prepare_den_gpu_smoke_v4.py
python scripts/launch_den_gpu_smoke_v4.py  # 唯一已完成任务，不允许重放本tag
python scripts/finalize_den_gpu_smoke_v4.py
```

CPU测试空可见性仅限对应子进程，不改变GPU任务继承的父环境。prepare不重新构建数据/统计；launcher独占启动标记、直接Popen.wait、890秒监督/资源限额，无自动重试。重放已有tag会拒绝，未来复现须新授权新tag，不删除标记。原官方权重/模型/统计、原始B14/旧122帧均不改。
