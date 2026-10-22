# FourCastDEN Jan4连续12小时验证（2026-10-22）

HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 实际范围与门禁

仅2023-01-04 01→13 UTC，目标02—13，四模型各一段完整12步，合计4序列48正式forward、0额外GPU预检，无失败重试。未拼接两个6h、未在中间回灌真值，未运行Mar24/24h、训练/TIE/RK45。先恢复历史提交9447e7856d1eae07dc47834b93cee29b8038c0a1推送成功，实际远端核对相同，日志logs/git_twelve_hour_recovery.log（本地）。

docs/FOURCASTDEN_TWELVE_HOUR_PREREGISTRATION.md在正式GPU前冻结：checkpoint/static/代码/数据SHA、FP32/TF32关闭、同原作者AFNONet、History354输入/其他177、输出171、History额外真实00。新增5项测试，全237项27.861秒通过；原有ERFA合成测试dubious-year警告保留，无依赖更改。12步CPU真实作者循环+合成网络对四模式未来真值毒化预测不变，最后History两个预测状态正确，后期teacher forcing/scalar错位拒绝，12步与6步合成前缀精确一致。

只新增08—13六NPZ。已存中央目录与远端目录逐成员比尺寸/CRC/offset；成功206/Content-Range、ZIP和zlib CRC、SHA、14键、shape/dtype/finite/哨兵/正DEN与TN/ZG逐层递增全部通过，raw0444。网络响应体13442650字节=12.8199MiB<25MiB，无失败下载/整包响应。00—07复用原件，无原始文件覆盖。NPZ时间由官方文件名、网格/单位由作者静态和代码契约确定，NPZ自身不含完整坐标/单位元数据。

## 前六步历史一致性

四模型前6次真实hooks将input/scalar/raw output/生成state与历史六小时数组逐元素比较，全部最大归一化差0；means/stds亦精确一致。门禁在第6次hook立即写prefix_gate，若失败会终止并保存失败前缀。执行完独立比较完整pred前7帧（含初始化）亦相同。24个模型时效的六变量summary与原DEN组指标全字段精确一致，prefix_metrics_gate.json；未修改历史6h。

全部12步通用check_autoregression检查匹配逐步state与未来aux/scalar；Flow normalized delta相加，log匹配static_log/log10/pow10，History [real00,real01]→[real01,pred02]→[pred02,pred03]→…，无未来物理真值反馈。所有权重严格load，无strict=False。log沿用既有隔离兼容包装器，原树与权重不变。

## 评价、物理与资源

所有48输出finite、DEN100%正，TN 150.666—1400.071K；最大绝对风分量760.988m/s，Z位势高度95.709—730.765km。未发现数值溢出/非正密度/明显发散，不表示真实物理预测已经准确；完整每lead范围见runtime。

公共物理目标为同原始NPZ02—13、普通physical climatology、真实01持续性；DEN乘1000为kg/m3，风/Z乘.01为SI。独立NumPy加权求和复核8208个物理通道时效，rtol1e-12；作者native normalized RMSE最大相对差2.24e-07、ACC最大绝对差2.375e-07，沿用rtol2e-5/RMSEatol1e-25/ACCatol2e-6。log native ACC在log空间、std-scaled DEN为dex，分表不混排。没有放宽门槛。所有raw/代码/四权重/统计/历史保护628项SHA不变。

|模型|加载s|读取解码s|标准化s|其他预处理s|首forward ms|其余均值ms|12forward合计ms|作者loop s|保存s|CUDA allocated MiB|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|Direct|1.2869|0.1661|0.0070|0.0440|154.032|18.550|358.082|1.2755|4.1831|315.701|
|Flow|1.0905|0.1638|0.0067|0.0376|18.956|18.086|217.901|0.5193|4.1408|315.701|
|LogDEN|1.0818|0.1640|0.0070|0.0299|19.387|18.183|219.404|0.6931|4.5562|316.849|
|History|1.1582|0.1772|0.0079|0.0357|20.937|18.595|225.480|0.5824|5.2278|329.248|


监督总墙钟39.435960s，GPU worker内部30.077811s含加载/I/O/指标/保存；峰RSS1.3873GiB，独立CPU分析9.1605s、峰827.547MiB。新增数据初审361.049MiB<800MiB。GPU事件只计网络区间，Direct首forward含CUDA冷启动，其他模型运行时已warm；不能由本次单次计时作稳定速度排名。作者native指标首次编译/派发等待也不是纯kernel性能。

12h与旧6h网络次数各组12对6，warm单步基本约18ms；总I/O/保存/初始化非线性，不能把总墙钟简单视为网络推理。四组只各加载一次，12步内无重复加载，无证据显示资源泄漏；ru_maxrss/CUDA峰不能证明任意长序列不会增长，未作专门长时内存测试。后续严格吞吐应另授权固定warm-up/同步/重复计时。

## 复现入口和产物

source scripts/activate310.sh；unittest discover；run_fourcastden_twelve_hour_jan4.py --fetch；无参preflight；supervise_fourcastden_twelve_hour_jan4.py；analyze_fourcastden_twelve_hour_jan4.py；audit_fourcastden_twelve_hour_jan4.py；write_fourcastden_twelve_hour_reports.py；audit --final。once-only目录不可删除标记后重试。指标CSV和8图前缀fourcastden_twelve_hour_jan4_v1；配置/反馈/范围/哈希/监督/指标审计在experiments同标签，大NPZ只本地。最终交付体积/哈希以final_delivery_audit.json为准。
