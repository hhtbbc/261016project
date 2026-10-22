# 五日期四模型共同起点：执行验证（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 授权与资产

五日期固定Jan4/Mar23/Jun21/Sep23/Dec21，统一01起点、02/03目标。Jan4四模型仅从既有npz读取并核对SHA及原指标，不执行网络；新增4日期×4模型=16序列、32forward，0额外真实预检forward。History额外00/01初态、其他仅01，不能称训练单因素消融。无训练/微调/6h/新TIE/轨道。启动前本地main和远端均58c35d9dee2bf15145d2cd85a47235eaa723f7ac，工作区干净。

422个历史保护文件（原始树/Linux副本/4权重/static/static_log/旧结果/日志）SHA不变。四套官方checkpoint分别见preflight.json，与历史官方校验表一致，严格load_state_dict，不使用strict=False。History354输入/171输出、66,870,720参数；其他177/171、64,695,744。log复用已验证隔离覆盖层，原统计/权重不改。

## 最小数据

先从官方2023.zip中央目录核对四成员均存在，随后仅Range提取四个03。HTTP响应全部206，Content-Range与长度精确相符，ZIP校验CRC32及独立zlib复核。总响应体9274427字节=8.845MiB，低于20MiB；未重取其他数据或整包。新文件验证后只读0444。

- 2023_03_23_030000.npz: SHA256 `39509750dacb5e2e25e3f8d2239fd4df5f06e448624b5c28618fd83c9bbfd51a`，CRC32 `2639742619`。
- 2023_06_21_030000.npz: SHA256 `6c58418ebbebfc30db2360c551dda1c766655f52d656e1c4dab83d9157dd393d`，CRC32 `1367278244`。
- 2023_09_23_030000.npz: SHA256 `f928df1dc67ca1b23be19a2142b3949a492161f11a9af31032fd8b7cc960d790`，CRC32 `2063670726`。
- 2023_12_21_030000.npz: SHA256 `d80a4095f7e5068d38916e7390d5eec2cefc8ae419992c094f9ce20b59b7861b`，CRC32 `2680684579`。

14键、变量shape、float32、finite/有限哨兵、正DEN/TN、ZG垂直顺序及训练网格契约检查通过；各字段min/max/unit完整保留*_download.json和preflight。NPZ无独立时间/经纬度/单位属性，日期来自成员名，单位/网格来自作者源码与不变static，不能冒称WGS84/ZG登记已验证。原样本物理范围及预报极值均可复核，不因模型误差大删除日期。

## 时序、反馈与匹配统计

window_indices拒绝Jan4/未注册日期、缺帧/重复/错序/非法history，保证4小时是同日连续00/01/02/03，不能跨季节连接。作者dataset日志“16 hours of past history”是总文件数描述，不是实际n_history；配置History=1，其余0。

复用作者inference：History第一次[real00+aux01,real01+aux02]→pred02，第二次[real01+aux02,pred02+aux03]→pred03，目标标量02/03；其他单状态；Flow normalized delta加当前state，log在原g/cm3做log10、对应static_log标准化，输出10**(norm*std+mean)×1000转kg/m3。真实hooks核对完整输入和反馈、每序列恰好2forward；实际174物理/LBC通道独立从raw重建归一化逐元素一致。未来真实171状态仅评价，给定未来驱动保留HINDCAST。

CPU原有毒化测试继续通过，新5项批量窗口测试加入后共226项（24.779s）。新推理全finite、DEN100%正/TN正，无补0/裁剪/重试。正式后另查History：与Direct普通mean/std逐元素相同，当前01初始171通道和返回real完全一致；未在检查路径发现归一化、checkpoint维度、时间或反馈错误，不能因此排除未公开训练协议或认定唯一误差根因。

## 独立指标

raw物理02/03共同目标、普通physical climatology、固定real01持续性；全部float64反变换、DEN kg/m3、风m/s、Z位势高度m。原压力层、lev/ilev、相对RMS/P95/自然ln指标不当固定450km或Swarm沿轨误差。log作者原生ACC和dex另表，不与共同physical ACC/RMSE混排。

独立NumPy加权求和实现复核6840个模型通道时效，rtol1e-12；native normalized RMSE最大相对差2.13e-07，ACC最大绝对差2.22e-07，沿用rtol2e-5、atol1e-25/ACC2e-6；未放宽。Jan4共同物理DEN40项复算与既有数值一致。所有5日期等权均值/中位/min/max、6模型配对组合、增长与排序保留CSV，不把格点数当独立实验数。

## 实际资源

GPU监督墙钟42.574574s，进程峰RSS1.222GiB；内部GPU阶段34.062319s含CPU读取/指标/hooks/SHA/保存，不是纯forward。第一次冷History157.167ms，其他forward约17.92—20ms；各模型各加载一次后复用四日期，加载时间分别约1.386/1.126/1.131/1.135s（History/Direct/Flow/log）。Jan4旧计时来自另一独立进程且有冷预检，性能表明确区分来源，不能作严格吞吐排名。

|新序列|独立读取ms|loop含指标/hooks s|forward 1/2 ms|保存s|推理allocated峰MiB|
|---|---:|---:|---|---:|---:|
|2023-03-23 History|67.640|0.8157|157.167/18.608|1.5585|294.489|
|2023-06-21 History|66.629|0.1114|19.513/18.282|1.5489|294.727|
|2023-09-23 History|65.990|0.1102|18.684/17.918|1.5434|294.727|
|2023-12-21 History|64.721|0.1082|18.898/18.085|1.5608|294.727|
|2023-03-23 Direct|47.101|0.1039|23.045/20.993|1.3892|281.179|
|2023-06-21 Direct|52.339|0.1031|21.906/20.958|1.3867|281.179|
|2023-09-23 Direct|50.949|0.0937|18.831/18.181|1.2959|281.179|
|2023-12-21 Direct|49.488|0.0929|18.960/18.197|1.3186|281.179|
|2023-03-23 Flow|48.463|0.0927|19.105/18.441|1.3023|281.179|
|2023-06-21 Flow|49.159|0.0894|18.807/18.149|1.2968|281.179|
|2023-09-23 Flow|49.262|0.0904|18.844/18.301|1.2899|281.179|
|2023-12-21 Flow|49.596|0.0910|19.221/18.084|1.3035|281.179|
|2023-03-23 LogDEN|47.037|0.2405|18.816/18.181|1.4169|282.328|
|2023-06-21 LogDEN|49.794|0.0947|18.870/18.192|1.3954|282.328|
|2023-09-23 LogDEN|50.232|0.0957|18.946/18.190|1.4145|282.328|
|2023-12-21 LogDEN|53.255|0.0970|19.247/18.441|1.3869|282.328|


CPU分析10.557s，分析进程峰RSS364.281MiB；每次显存allocated/reserved与CPU累计ru_maxrss分别记录。初审新增文件430.866MiB<650MiB，大型NPZ只本地。新显存History约295MiB、普通约282MiB，历史输入翻倍并不意味着总网络成本翻倍。没有把首个cold event与随后warm事件作模型加速比。

## 文件与命令

入口source scripts/activate310.sh；unittest discover；run_fourcastden_four_model_multidate.py --fetch；同脚本静态；supervise_fourcastden_four_model.py；analyze_fourcastden_four_model_multidate.py；audit_fourcastden_four_model_multidate.py；write_fourcastden_four_model_reports.py；最终audit --final。once-only标签不能删除launch后重试，未来需新授权/标签。配置/请求/CRC/SHA/监督/实际反馈审计在experiments/fourcastden_four_model_multidate_v1，压缩大数组data/processed同标签，日志logs/fourcastden_four_model*。本报告是工程验证，不是完整论文训练复现、独立真实大气或轨道准确度证明。
