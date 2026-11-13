# AFNONet固定真实DEN样本累计200步接续收敛v6

日期2026-11-13，tag`fourcastden_den_overfit_continuation_v6`。起始main本地/远端同`4d67a9d385f0df62fc279b80d180d960cdbeb9df`。

**源step100精确恢复后，一次GPU任务新增100次更新至累计200；固定样本全层/上层/顶层均优于Persistence，28/29单层优于Persistence，第24层例外。2022仍远差于Persistence，不能视为可靠泛化或真实大气精度。** 无重试、无超参/数据/网络/损失修改、无新TIE/下载/轨道/多步。

## 1. 冻结恢复身份与外层预算

只使用可信本地源`experiments/fourcastden_den_overfit_v5/step100.pt`，SHA `e5183727e11c487b8f0c964dc5c80220f7e6a8448ecf60f3de5ef28165524eda`；路径真实目标、CPU可信反序列化前SHA、metadata tag/label/统计/manifest/训练pair0、完整config与step100均核验。AdamW有148组有效参数状态，内部step均100；原训练模式True。

**checkpoint原config逐字典保持不变，含max_train_steps=100。** 原`restore_den()`严格相等校验不修改、不降低；独立ContinuationBudget限定start100/additional100/end200，在optimizer前后hook核对累计步数，拒绝第201步。最终step200 payload仍保存原config=100，并用独立metadata保存v6累计预算。不能将陈旧config字段当成本次累计步数，也不能改原checkpoint来绕过恢复。

48项CPU测试通过：新增6项预算/严格恢复/RNG/拒绝用例，原overfit5/environment11/DEN9/pipeline8/interface8/import1。CPU模拟checkpoint仅测试夹具，不冒充真实step100。532项旧资产含v3数据/统计、v4与v5日志/权重/图表/原B14与官方资源SHA最终保持。

## 2. 开始新更新之前的step100门禁

模型、完整AdamW、scheduler、Python/NumPy/Torch/CUDA RNG、训练模式逐项精确核对。RNG检查包括NumPy完整624键数组/位置/缓存值、Torch/CUDA字节状态；不靠重新设seed冒充恢复。新建网络仅作加载容器，实际训练权重来自源checkpoint；恢复model SHA `7dfb2b5d04e871774eafdb3663fed8c080ff7954ca1178e0611a3a95db1119a4` 等于v5最终SHA。

无梯度固定样本前向1次（计入step100检查点）与v5冻结DEN物理数组逐元素精确一致：最大绝对差0.0，normalized loss差0.0，三组relativeRMS/RMSE/Bias实际差均0。开始时新更新计数0。注册规则：model/optimizer/scheduler/RNG/mode exact，DEN数组rtol=atol=0；loss rtol1e-7/atol1e-9，指标rtol1e-10/atol1e-12。实际所有差均为零，最强约束是数组逐位一致，不依赖非零容差获得PASS。

固定2021-03-23 00→01 UTC B14首对，X177/D4/Y171、DEN142:171 ilev29。缓存与v5 X/D/Y SHA一致；100次新forward对象身份核验、训练后缓存hash不变。2021训练统计原SHA `df9a8c2bd31026de0e0ebcae07c6d7a8ff1d56832486d93e11b70fd1bba46bf5` 未拟合/修改；未来物理目标毒化不改输入。DEN g/cm³×1000成kg/m³，Z不是ZG；原生ilev不是固定几何高度。未来合法辅助/驱动维持HINDCAST，其他142输出不监督。

## 3. 新增100次真实更新

原AFNONet64,695,744参数、AdamW1e-4、weight_decay0、StepLR gamma1（常数LR）、clip1、FP32/batch1、原DEN29 cos纬度normalized MSE不变。实际累计101—200逐条日志，新增100个optimizer hook与原AdamW内部step101—200一致；**本轮实际152次forward**：训练100、固定100/150/200检查3、最终恢复探针1、最终验证48；历史v5的153次不计入本轮。

148个梯度张量有限非零，有效头参数每次变化，非DEN142头梯度精确0/参数不变；原作者未调用的末端norm两个参数仍无梯度，如历史报告。新更新clip前L2范围7.914377—16.264854，全部100步触发原clip1规则，没有因震荡改lr或停止。确定性CuBLAS首次torch前设置`:4096:8`，继承原可见设备、不强制外部GPU0。

## 4. 固定样本0—200真实收敛

|累计step|normalized loss|全29层relativeRMS|上层20—28|顶层28|非正数|
|---:|---:|---:|---:|---:|---:|
|0|162.235961914|59.678349%|66.663092%|86.014904%|3312|
|10|8.943881035|14.046070%|15.767940%|20.193869%|9|
|50|0.455307215|3.153300%|3.549186%|3.995043%|0|
|100|0.199936286|2.084117%|2.384187%|3.043031%|0|
|150|0.155578896|1.859141%|2.078698%|2.767925%|0|
|200|0.091136366|1.419518%|1.547587%|2.048351%|0|
|Persistence|N/A|1.673781%|1.748587%|2.372184%|0|


0/10/50/100引用原v5记录，不重新执行旧网络或重算旧指标；本轮恢复100与历史100一致，拼接图只保留一个100时点，150/200为新证据。更新日志是更新前loss，检查点是更新后eval/no_grad，不能混淆step200日志0.118660与实际step200模型0.091136。

100→200 normalized loss下降54.417296%，全层relativeRMS下降31.888771%，从2.084117%降至1.419518%；上层2.384187→1.547587%、顶层3.043031→2.048351%。全层相对Persistence1.673781%更低，但**不是所有单层胜出**：28/29层优于Persistence，原生level24为1.595718%对1.592990%，略差约0.002729个百分点。全部29层相对step100都有改善，未删除该不利层。

step200固定全层RMSE2.597495e-9、Bias+3.475180e-13kg/m³，Persistence对应3.486639e-9、−3.160833e-12。上层RMSE3.931489e-14、Bias+3.888276e-16；顶层RMSE2.688339e-15、Bias+2.964687e-17。所有固定100/150/200非正值0、正值率100%。

前100步全层relativeRMS绝对下降57.594232个百分点，后100步下降0.664599个百分点：大幅初期收益减弱，但后100的相对下降31.89%仍可见，不应称停止改善。100/150/200三个检查点均下降，不能代表每个中间步都单调。

新100步99个相邻loss变化中44次上升；最后20条更新前loss均值0.111417808、范围0.097198583—0.119171746，明显低于历史v5最后20条均值0.231769。仍有震荡，但没有足够证据判定不可降低平台。固定数据与确定性条件排除了换样本造成的曲线变化，具体优化机制仍需单因素试验，不能由大梯度或震荡直接断言梯度爆炸/lr错误。

## 5. normalized与物理指标的独立审查

仅对v6新100/150/200保存数组重算各层物理指标，并用实际float32目标独立重算normalized MSE；与GPU记录一致。旧0—100数据只读引用。层/区域全保留，普通误差分母为正真实目标，无新floor、无补值/外推/取abs。

normalized MSE与relativeRMS不是同量：本轮分别下降54.42%与31.89%。`(pred−truth)/truth = ((pred−truth)/std_SI)×std_SI/truth`，层和位置的std/target不同。Bias也可不同步，例如固定上层Bias100为−9.027888e-17，150为−6.859821e-16，200为+3.888276e-16kg/m³，绝对Bias并非随RMS单调下降。没有因此事后更换损失。

## 6. 仅最终step200的2022开发验证

100次接续更新全部完成、最终checkpoint恢复后才创建验证dataset，完整48对只一次no_grad。模型/optimizer hash、step200/预算100前后不变，梯度None；不在150查验证，不选最好checkpoint。

|范围|v5 step100历史|v6 step200|Persistence|step200 RMSE kg/m³|step200 Bias kg/m³|
|---|---:|---:|---:|---:|---:|
|all|20.706686%|19.711886%|1.992488%|2.569451537e-08|-2.908423671e-09|
|upper20_28|25.205819%|23.897766%|2.242242%|5.353548657e-13|9.739293447e-14|
|top28|27.530085%|26.411914%|2.909416%|2.903997736e-14|5.168739465e-15|


2022全层relativeRMS20.706686→19.711886%，降低约4.80%；上层25.205819→23.897766%、顶层27.530085→26.411914%。这里同一模型轨迹严格恢复、训练/损失不变，比较是受控的训练长度延长结果，但仅两个短窗、开发验证已多次使用，不能称新盲测或可靠泛化。全部29个验证层仍劣于Persistence。

3608064个预测全部有限，13个非正均顶层（历史step100为18），正值率99.999640%；普通RMSE/Bias/relativeRMS保留所有有限预测，不裁剪或删难样本。log只在正值处定义，覆盖另报并在AI正值共同子域配对Persistence。共同正值域的AI/Persistence logRMS分别为：全层0.1887091/0.0199838、上层0.2242676/0.0225316、顶层0.2683872/0.0289968；不改变普通误差的全点统计。各层/纬区/小时指标、共同log域与独立数组求和复核保存CSV。2022物理标签来自TIE-GCM，不是真实Swarm真值。

Persistence完整48对同时间/网格/权重/单位独立复算，与历史v5/v3逐值一致；历史step100验证只读CSV，不重新运行其模型。单样本能拟合并不意味着不同输入都能预测，也不保证线性DEN输出恒正。

## 7. checkpoint与资源

只保存最终`experiments/fourcastden_den_overfit_continuation_v6/step200.pt`，776610058bytes，SHA `3ec6eaeed7427924fbcae2b5ae50c12554da0a41ff7a37d103e6a46a4bd7e80f`。包含完整model/AdamW/scheduler/RNG、累计step200、原config、source checkpoint SHA、独立接续预算、数据/代码SHA。加载到新容器后全部状态/RNG/mode精确一致，固定GPU171输出逐元素一致，没有第201次更新。原v5 step100保持源SHA，不覆盖、不上传权重。 新增100条更新记录以updates.jsonl及training_updates.csv伴随保存，未重复嵌入pickle；checkpoint_bundle_manifest.json将最终checkpoint SHA、更新日志/CSV、原配置协议与恢复证据的SHA绑定，形成完整可追溯checkpoint包。

硬件NVIDIA A100-SXM4-80GB、PyTorch2.4.1+cu121、CUDA12.1；监督真实exit0/PASS，65.083723秒（上限300），worker62.230206秒。纯新更新12.246442秒，均值0.122464秒、中位0.119643秒；初始完整恢复6.447578秒，固定评价6.436304秒，最终保存/恢复8.222694秒，最终48对验证5.909815秒，保存数组1.356527秒。包含关系不同，不机械相加。

allocated峰值1.520432GiB，reserved1.708984GiB，进程GPU采样峰值2.259766GiB；CPU树采样2162.277MiB（限8GiB）、自身峰值2168.926MiB。资源采样缺口0，采样不冒充连续峰值。新GPU产物807230732bytes，约0.752GiB<2GiB，余盘约1.3TiB。CPU后处理24.367972秒/606.773MiB单独记录，不当训练成本。

## 8. 实际图表与验收

`results/fourcastden_den_overfit_continuation_v6/`：

1. `01_loss_0_200_and_late_detail.png`：v5/v6来源区分、完整log曲线与末段原始值。
2. `02_fixed_relative_RMS_0_200.png`：六个真实检查点及Persistence，不补造中间物理评价。
3. `03_fixed_layer_100_200.png`：全部29层RMS/RMSE、含level24例外。
4. `04_fixed_density_100_200.png`：预先固定ilev24，step100/200共同物理色标。
5. `05_positivity_and_clipping.png`：真实物理检查点与新增每步梯度记录。
6. `06_2022_step100_step200_Persistence.png`：历史100只读引用与本轮最终200，注明开发验证非盲测。
7. `07_new_training_resources.png`：新增更新、恢复、评价与文件成本分开。

恢复身份/配置/RNG、精确step100输出、一次新增100更新、step200保存恢复、48对最终验证、资源与输入完整性均有实际PASS证据。物理学习结论不按事后门槛强行二元化：固定三组聚合胜Persistence，但不是全部层；开发验证仍失败于Persistence。SCIENCE_TRAINING_READY=False、EXTERNAL_DATUM_UNVERIFIED、正式真实轨道BLOCKED、A14工程PARTIAL/旧v3FAIL保持。

**A：** 继续至200后，固定样本确实更接近标签，全部29层较100改善。**B：** 三个聚合指标胜过Persistence，但level24例外，不能说每层都胜。**C：** 有震荡、收益减弱，但三个检查点仍改善，未证明明确平台。**D：** 可以保持原网络/损失进入受限72对多样本工程研究；不继承单样本权重、从同seed随机初始化、同200更新预算，暂不同时换log/残差/正值约束。详细321forward和300秒候选资源见`docs/FOURCASTDEN_DEN_CONTINUATION_V6_NEXT_PLAN.md`，本轮不执行。

## 9. 实际命令与保护

```bash
cd /workspace/data/20261016
source scripts/activate_orbit.sh
CUDA_VISIBLE_DEVICES='' python -m unittest discover -s tests -p test_den_continuation_v6.py
# 同CPU子进程方式执行原overfit5/environment11/DEN9/pipeline8/interface8/import1，共48项
python scripts/prepare_den_continuation_v6.py
python scripts/launch_den_continuation_v6.py  # 本轮唯一任务已完成，不能重放本tag
python scripts/finalize_den_continuation_v6.py
python scripts/write_den_continuation_v6_report.py
```

所有新文件/缓存在项目，.venv310 via activate_orbit；新tag独占标记、直接Popen.wait、不自动重试。输入/配置/代码/输出SHA、原始资源与门禁记录在本tag，命令日志索引commands.json。原始NC/NPZ、预测数组、完整checkpoint、环境和凭据不公开；仅轻量代码/协议/CSV/PNG/报告/审计安全同步GitHub，保留旧提交与无关未跟踪文件、不强推。结束不自动继续。
