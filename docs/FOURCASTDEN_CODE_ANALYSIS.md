# FourCastDEN 源码分析（2026-10-19）
## 来源、保存与安全
使用已下载并由Zenodo MD5校验的90,106字节原包，避免重复下载。按本次要求复制至 data/raw/FourCastDEN.zip；原 third_party/FourCastDEN.zip 保留。检查所有成员：拒绝绝对路径、..、反斜杠、符号链接，限制总解压尺寸，解压至 third_party/FourCastDEN。日志 logs/source_safety.json、logs/source_archive_inventory.txt。
原始源码保持逐字节不变（logs/upstream_integrity.json）；Linux运行副本 third_party/FourCastDEN_linux，补丁 patches/0001-lazy-optional-apexpy.patch。补丁只移除数据加载器未调用的apexpy、绘图、磁坐标生成导入，并将tiegcm_utils的apexpy延迟至实际转换函数内部导入。磁坐标仍读取作者mag.npz，没有替代数值、关闭驱动或改动网络运算。

## 执行入口与调用关系
`eval_tiegcm.py` → `YParams` → `TGCMForecast` → `TGCMDataset` → `AFNONet` → 自回归/评价 → result.npz。
- eval_tiegcm.py：解析yaml_config/config/weights/override_dir，建立输出与日志，选择初始时间索引，调用inference。inference.sh只是启动包装，依赖python3.10且未提供weights；默认override_dir不为None，会触发参数断言，不能直接照抄执行。
- utils/YParams.py：YAML合并、变量排序、通道索引、统计文件与坐标读取；非单纯配置解析器，缺静态文件即不能初始化。
- inference/inference.py：TGCMForecast初始化数据集、均值标准差、气候态、cos纬度权重，实例化网络，读取checkpoint['model_state']严格匹配；forecast按flow决定是否叠加状态；inference执行多步预报。
- dataset/dataset_tiegcm.py：每小时NPZ读取，按固定变量顺序展开垂直层，归一化、太阳高度与地磁辅助通道计算；get_data直接按文件名中的时间读取，不需要DataLoader即可推理。
- models/afnonet.py：实际采用AFNONet；models/__init__.py也导入AFNONeXt，但当前入口未使用该网络。
- utils/weighted_acc_rmse.py：纬度加权RMSE、气候态异常相关ACC及不加权ACC。
- utils/logging_utils.py：日志；utils/tools.py仅日期解析等相关功能进入当前链路。
详细类/函数行号和import清单：logs/source_ast_inventory.json。

## 模型结构与输入输出
配置：patch_size=4、embed_dim=768、depth=12、num_blocks=8、mlp_ratio=4、drop_rate=0。Conv2d将36×72网格变成9×18 patch；加位置嵌入，12个AFNO Block，傅里叶域分块复数线性映射/非线性与软阈值，再逆变换、残差及MLP。
4个一维标量在最终head之前广播到每个patch，与768维特征拼接，用线性head还原171个输出通道。注意源码声明了self.norm，但forward_features未调用；不能为了“标准化实现”擅自补上。
六变量输出顺序TN/UN/VN/WN/Z/DEN：前三个各28层，后三个各29层，共171通道。输入加三个下边界、太阳高度角、地磁纬度和经度，共177二维通道；标量为f107d/f107a/Kp/sfeps，共4个。历史模型n_history=1使二维输入为354通道，不能混用权重。

## 数据读取与推理细节
NPZ另含ZG、NE，尽管模型不用，_get_files_stats仍遍历ALL_TIEGCM_VARS，最小样本也需保留这些键。样本时间从文件名解析。过滤每年1月1—3日，预测时间连续性需要自行检验，不能仅依赖文件排序。
标准变量按训练统计逐层zscore；标量F10.7按中心190/尺度110，Kp按中心4.5/尺度4.5；sfeps=(sfeps-1)/0.04；SEA白昼归一到0—1、夜侧置零；地磁纬度/90、经度/180。
单步使用当前171通道状态与目标时刻下边界/太阳/磁坐标和标量，预测下一小时171通道。多步把预测状态反馈，辅助条件仍来自各未来时刻真实数据。故必须提供未来驱动；并非完全自由演化。
get_data读取H+L+1个时刻，H=n_history，L=n_prediction。Direct/Flow单步理论需2帧；原CLI默认初值循环还受__len__额外减1影响，需3帧才产生一个初值。验证脚本直接调用inference(0)，避免错误日期偏移；仍使用作者模型/预处理/预测流程。
输出pred包含初始化帧，首个预测为时间索引1；real还包含辅助二维通道，不能直接对两个完整数组做RMSE。

## 推理必需与其他文件
|类别|文件/包|说明|
|---|---|---|
|必需|eval_tiegcm.py、inference/inference.py、models/afnonet.py|原入口或等效调用脚本、预测和网络|
|必需|dataset_tiegcm、YParams、tiegcm_utils、tiegcm2、tools、weighted_acc_rmse、logging_utils|数据/太阳位置/统计/评价|
|必需外部资产|匹配权重、static、连续小时NPZ|模型参数、训练统计、气候态/磁坐标/经纬度|
|数据准备|data_process/get_data_tiegcm.py、get_stats_tiegcm.py、get_maglatlon.py、get_train_dataset.py|NetCDF转换、统计、磁坐标与数据组织；已有处理数据推理不需执行|
|训练片段|models/model_module.py、utils/losses.py、训练参数与sampler|存在Lightning training_step、Lamb等片段，但不是完整训练复现入口|
|其他/未用|forecast.py、fourcastnet.py、ensemble、plot_demo、afnonext、multifiles|含其他框架/天气模型残留，不能据此安装mindspore/ai-models等全部包|

## 缺失与不兼容风险
没有requirements.txt；仅Windows完整Conda导出。README明确不提供训练流程；虽然包内有训练片段/预处理脚本，缺train_tiegcm.py、完整训练主程序、训练验证数据，无法复现论文训练。
可选error_plt与dif_model_comparison确实缺失，但当前eval入口的相关导入和调用已注释，不应把它们误报为活动入口的必需依赖。
Windows路径需要在项目自己的配置中覆盖。inference.py硬编码reshape(1,-1,36,72)，本次只测试匹配的5°网格。datetime初值硬编码减72小时，小窗口不能沿用全年索引；step_con分支引用条件变量stop，存在潜在未定义问题，不测试该分支。
--weights并不决定TGCMForecast实际加载路径，实际路径为best_checkpoint_path。多个初值循环会覆盖result字典，因此不能把当前输出当全年完整汇总。log_DEN分支存在NumPy与CUDA tensor混用风险，今日不运行该变体。
UNIT_VARS声明cgs单位，read_var的SI换算被注释；不能把函数docstring里的SI表述当作实际已转换。

## 验证边界
今日只做最小Direct单步验证，结果以 logs/minimal_validation.json 为准；源码可导入、权重匹配和单窗口执行不代表完整论文复现，不证明多步/磁暴/真实轨道准确性。

### 补充：网格尺寸配置缺陷
YParams的img_shape_x/y类默认值为0，原AFNO.yaml没有指定，TGCMForecast从dataset获得尺寸却未回填params，而load_model用的是params尺寸。自有最小配置必须显式填入从真实样本核验的36、72，否则位置嵌入尺寸/权重加载失败。此处通过配置修正，不修改作者模型。

## 今日执行验证补充
logs/model_construction.json确认64,695,744参数；logs/checkpoint_inspection.json确认Direct model_state150项；logs/minimal_validation.json确认严格加载和一次真实单步运行成功。原始源码完整性检查通过；当前修正为可选导入补丁和自有配置，不涉及AFNO参数结构、归一化规则、目标时刻驱动或预测更新方程。
