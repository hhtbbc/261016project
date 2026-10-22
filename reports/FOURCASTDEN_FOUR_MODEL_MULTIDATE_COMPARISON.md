# 五日期四模型统一01起点比较（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 共同目标与统计单位

每日期01→02→03，Jan4历史只读，另4日期新运行；模型/归一化不同、History额外真实00信息，非严格训练消融。五日期为等权窗口，n=5小规模诊断，无全年/显著性结论。所有模型反变换到同raw TIE-GCM物理参考、同普通physical climatology及相同01持续性；各自native指标另保留。平均层RMSE指先逐层cos纬度加权RMSE后层间等权平均，不混不同变量单位。

## 主要回答

History全层DEN绝对RMSE、高层（参考中位ZG400—500km组与固定upper20—28）相对RMS在两个时效5/5窗均未优于Direct，也未优于Flow。第一小时Flow两项主要DEN指标均5/5最低；第二小时近400—500组Flow3窗最低（Jun/Sep/Dec）、Direct2窗最低（Jan/Mar）。第二小时绝对DEN：log3窗最低（Mar/Jun/Sep）、Direct Jan最低、Flow Dec最低。不能按一项指标选最终模型。

|模型|时效h|全层DEN绝对RMSE均值 kg/m3|同指标中位数|近400—500组相对RMS均值 %|同指标中位数 %|
|---|---:|---:|---:|---:|---:|
|Direct|1|1.7296338e-11|1.7086819e-11|0.054415|0.048558|
|Flow|1|1.4204068e-11|1.4382263e-11|0.044831|0.038673|
|LogDEN|1|1.6166206e-11|1.6201723e-11|0.063477|0.055076|
|History|1|2.8649026e-10|2.6420129e-10|0.098430|0.099647|
|Direct|2|3.4830649e-11|2.4112988e-11|0.135726|0.072132|
|Flow|2|3.5584672e-11|2.5601547e-11|0.136720|0.073178|
|LogDEN|2|3.4039383e-11|2.3809585e-11|0.147042|0.088589|
|History|2|4.228927e-10|3.9700032e-10|0.282377|0.258639|


均值/中位数可能排序不同；第二小时高层相对RMS等窗均值Direct0.135726%、Flow0.136720%很接近，受Jan4影响，不能仅用“Flow赢3窗”或仅用全窗均值宣布架构优越。每项min/max见density_aggregate.csv；其他变量同样有aggregate.csv逐变量分单位均值/中位/min/max。

## 第二小时逐窗：高层相对与全层绝对

以下近400—500按参考ZG全球中位选择原生ilev层组，每个目标实际索引/中位高度在windows.csv；不是固定几何450km，不是实际卫星沿轨误差。

|日期|Direct %|Flow %|log-DEN %|History %|最低|
|---|---:|---:|---:|---:|---|
|2023-01-04|0.249564|0.308047|0.267308|0.355315|Direct|
|2023-03-23|0.072132|0.073178|0.088589|0.258639|Direct|
|2023-06-21|0.068397|0.059746|0.078761|0.227202|Flow|
|2023-09-23|0.065373|0.060039|0.076406|0.248519|Flow|
|2023-12-21|0.223163|0.182590|0.224146|0.322208|Flow|


|日期|Direct kg/m3|Flow kg/m3|log-DEN kg/m3|History kg/m3|最低|
|---|---:|---:|---:|---:|---|
|2023-01-04|4.9955885e-11|5.8503842e-11|5.1200574e-11|3.9700032e-10|Direct|
|2023-03-23|2.4112988e-11|2.5601547e-11|2.3809585e-11|4.7385052e-10|LogDEN|
|2023-06-21|2.1064973e-11|2.0066088e-11|1.9869914e-11|3.6609898e-10|LogDEN|
|2023-09-23|2.1673621e-11|2.3795742e-11|2.0789117e-11|4.9470231e-10|LogDEN|
|2023-12-21|5.7345776e-11|4.995614e-11|5.4527724e-11|3.8281139e-10|Flow|


全部第一小时和第二小时、固定上层、P95/log差、顶部和极区误差完整CSV，不挑有利日期/层。History绝对密度误差较大在五日期重现；最低5原生层贡献其各层RMSE之和的约97.5%—99.2%，这是RMSE加和的构成比例，不是总MSE贡献/统计方差。低层密度量级大，不能用绝对指标替代上层相对指标；History上层指标同样未改善。

## History额外信息是否有价值

|变量|History优于Direct窗口数 +1h|+2h|
|---|---:|---:|
|TN|0/5|0/5|
|UN|0/5|1/5|
|VN|0/5|1/5|
|WN|1/5|1/5|
|Z|0/5|0/5|
|DEN|0/5|0/5|


第一小时仅Dec WN优于Direct；第二小时仅Dec UN/VN/WN优于Direct。不能说History完全没有任何局部或变量优势，但未显示TN/Z/DEN跨窗优势。所有日期/层的ACC、偏差、极值保留，不将不同单位变量投票合成“总精度”。

已专门检查History与Direct训练mean/std相同、当前初态相同、real目标与aux相同、354输入顺序与预测反馈正确，checkpoint SHA/150项维度严格加载且ordinary static匹配；没有在这些已核查路径找到真实代码错误。较差结果是现有官方模型在该条件协议下的实际残差，保留不修补；尚无原始训练数据/完整训练配置，不能保证排除所有上游模型问题，更不能从一次或五次运行宣布唯一根因。

## 增长和日期依赖

每模型5窗×6变量共30项平均层RMSE均从1h增加到2h，120/120。History DEN绝对RMSE倍率约1.456—1.505；Direct1.373—3.188，Flow1.686—3.622，log1.419—3.167。History在Jan/Dec等窗倍率较小，但其起始绝对误差高约一个数量级，不能说已缓解漂移；在Mar/Jun/Sep，History DEN倍率反而略高于Direct。高层相对增长History约2.56—3.42倍，通常比Mar/Jun/Sep其他模型更高；倍率与绝对误差必须一起看。只有两个目标不支持长期稳定性结论。

## 00/01起点条件敏感性

旧三模型00起点目标01/02，新01起点目标02/03；相同lead不是相同目标，不能称完全同任务。另提供共同目标02的旧+2h/新+1h配对，但其初始信息/lead不同，不能排名纯架构或归因特定驱动。History无合法00起点对照，不作此比较。

新+2h近400—500组相对RMS对旧+2h的倍率：Jan4 Direct/Flow/log约3.186/4.246/2.558，Dec21约2.591/2.275/2.297；Mar23约1.046/1.148/1.089，Jun21约0.964/0.957/0.954，Sep23约1.013/1.032/1.041。因此不是所有01时都更难，不同日期依赖明显。旧Flow两时效5/5高层较低，在新第二小时Jan/Mar被Direct超越；log旧第二小时5/5绝对最低在新窗口变成3/5。

逐日期原始F107/F107A/Kp四帧见drivers.csv，原参考相邻小时物理变化见reference_changes.csv。未凭误差变化宣称地磁因果，未更换原NPZ驱动或平滑输入。Mar23早期不是强磁暴样本；不同UT/目标时效、状态/驱动和参考演变相互混杂。无NaN/Inf/负DEN/异常修补或额外重跑，不能因大残差推定数据损坏。

## 成本与成果索引

新32forward监督42.575s/峰RSS1.222GiB，四模型各加载一次；History参数66.87M，比64.70M多3.36%，输入354vs177。推理allocated约295vs282MiB；单次warm事件不能给严格速度排名。详细读取/加载/首次/后续forward/loop含评价hooks/保存/RSS/CUDA表见performance.csv，Jan4来源单列。CPU分析10.557s、峰约364MiB。不能把GPU phase墙钟当网络forward耗时，不能把本次计时等同端到端AI替代TIE仿真效率。

- layers.csv8550行、summary.csv300行、density_layers.csv4350行、windows.csv50行（含Persistence）；author_native.csv6840行，log dex/ACC空间明确。
- aggregate.csv48行、density_aggregate.csv40行，5窗均值/中位/min/max；pairs.csv360行、density_pairs.csv300行；rankings.csv50行；growth.csv120行。
- initialization.csv360行，明确同lead异目标/同目标异lead；performance.csv20行；drivers.csv20行；reference_changes.csv90行。
- 统一前缀results/metrics/fourcastden_four_model_multidate_v1_；7图在results/figures同前缀high_DEN、absolute_DEN、variables、growth、history_pairs、initialization、performance。
- experiments/fourcastden_four_model_multidate_v1/analysis.json、History_interface_diagnostics.json、delivery_audit.json/最终审计，所有原始大数组仅本地。

226测试、6840共同物理通道独立复核、422历史保护SHA通过；以日期为样本，不能把格点增加当显著性证据。当前不足以选择最终模型或确定训练超参数；值得提出相对/分层损失、多步训练及History训练协议核查假设，但必须用独立训练/验证数据而非2023调参。下一步仅设计Jan4和基于外部GFZ预选Mar24的6h连续实验，不执行；真实大气/轨道精度门禁不变。
