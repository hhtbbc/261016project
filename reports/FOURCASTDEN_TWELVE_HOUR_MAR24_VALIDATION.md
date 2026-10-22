# FourCastDEN Mar24连续12小时执行验证（2026-10-22）

HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 实际执行与来源

固定Mar24 01→13，4官方模型各12步，48正式forward，无额外GPU预检，无失败模型/自动重试。Direct/Flow/log真实01，History真实00/01；后续全部来自预测。没有重新运行Jan4、六小时、TIE、RK45、24h或训练/微调。开始确认本地及远端main为b081de700089634221381d9ee4aad2eb6e2355b9。

先冻结MAR24_TWELVE_HOUR_PREREGISTRATION.md，239测试27.884秒通过（复用四模式12步CPU作者循环毒化、History最后双预测和前缀检查，加2日期隔离/门禁测试）。旧ERFA合成dubious-year警告保持，不修改依赖。AFNONet严格加载，Direct/Flow/log64,695,744参数，History66,870,720；177/354输入、171输出、FP32、TF32关闭。四权重/对应普通static/static_log/隔离log兼容层SHA及原作者树与旧实验保护696项不变。

官方目录先确认08—13六成员，压缩合计12,469,476字节，远端目录CRC/尺寸/offset复核；网络实际13452428字节=12.8292MiB<25MiB。全Range206/Content-Range/长度、ZIP和zlib CRC/SHA、14键/shape/dtype/有限哨兵/正DEN/TN/ZG递增通过，raw0444，00—07只读复用。文件时间来自官方名称、网格/单位来自源码和static契约，不冒称NPZ有完整独立坐标元数据。

## 前六小时与反馈门禁

逐step hook精确比较旧Mar24六小时input/scalar/raw network/state，means/std精确；全部最大差0。执行后pred初始化+前6帧逐元素一致，24模型时效六变量summary与旧DEN指标全部相同，见prefix_metrics_gate.json。原六小时文件不改，门禁失败会保存失败前缀并停止，不放宽阈值。

12步完整作者inference而非两个6h拼接；History [real00,real01]→[real01,pred02]→[pred02,pred03]→…；Flow normalized delta加当前state；log使用匹配log10(g/cm3)统计与pow10反变换，DEN乘1000为kg/m3，风/Z乘.01为SI。每步未来aux/scalar与目标对齐，真实171物理场只评价。已知未来外部条件仍HINDCAST，非实时自主预测。

## 独立评价与数值状态

公共raw目标02—13、普通physical climatology、真实01持续性一致；cos纬度加权RMSE/有效ACC、偏差/极值、逐层/极区/顶部/固定upper/near组均保存。独立NumPy加权求和复核8208物理通道时效rtol1e-12，作者native normalizedRMSE最大相对差2.377e-07、ACC最大绝对差2.291e-07，沿用rtol2e-5/RMSEatol1e-25/ACCatol2e-6。log native ACC/dex与公共物理指标分表，未更改容差。

48输出finite、DEN100%正，TN范围143.069—1736.580K，最大绝对风分量1095.519m/s，Z位势高度95.651—854.883km。无指数溢出/非正密度/明显数值发散，不等于真实物理准确。所有模型每lead171通道RMSE均优于真实01持续性；仍只是对TIE参考。

## 计算成本

|日期/模型|加载s|读取解码s|标准化s|其余预处理s|首forward ms|其余均值ms|12forward合计ms|loop s|保存s|物理解码hook s|CUDA峰MiB|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
|2023-01-04 Direct|1.2869|0.1661|0.0070|0.0440|154.032|18.550|358.082|1.2755|4.1831|N/A, not separately timed|315.701|
|2023-01-04 Flow|1.0905|0.1638|0.0067|0.0376|18.956|18.086|217.901|0.5193|4.1408|N/A, not separately timed|315.701|
|2023-01-04 LogDEN|1.0818|0.1640|0.0070|0.0299|19.387|18.183|219.404|0.6931|4.5562|N/A, not separately timed|316.849|
|2023-01-04 History|1.1582|0.1772|0.0079|0.0357|20.937|18.595|225.480|0.5824|5.2278|N/A, not separately timed|329.248|
|2023-03-24 Direct|1.2962|0.1663|0.0077|0.0467|148.814|18.524|352.574|1.2621|4.3178|0.02880038321018219|315.701|
|2023-03-24 Flow|1.1133|0.1658|0.0066|0.0373|18.984|18.097|218.047|0.5217|4.2415|0.018987122923135757|315.701|
|2023-03-24 LogDEN|1.0948|0.1639|0.0073|0.0304|18.810|17.772|214.306|0.6779|4.4736|0.03308195061981678|316.849|
|2023-03-24 History|1.2592|0.1770|0.0077|0.0321|20.623|18.199|220.807|0.5699|5.3856|0.021478228271007538|329.248|


本次监督39.969886s、worker内部30.514212s含加载/CPU I/O/指标/保存，峰RSS1.3923GiB；独立CPU分析9.1257s、峰827.422MiB。初审新增359.228MiB（最终以final_delivery_audit.json为准）<800MiB；GPU600s、RAM4GiB内。

物理解码hook单独计时是独立float64物理检查成本，属于作者loop的一部分；作者native log反变换还包含于native指标调用区间，不能把二者相加当纯解码。Jan4没有同项独立计时记N/A不是0。首次Direct冷CUDA，后续模型已warm；网络事件/native指标事件/loop/读写分别记录，不能按本次冷启动排序速度或与TIE完整仿真声称端到端加速。

## 复现与交付

source scripts/activate310.sh；unittest discover；run_fourcastden_twelve_hour_mar24.py --fetch；无参preflight；supervise_fourcastden_twelve_hour_mar24.py；analyze_fourcastden_twelve_hour_mar24.py；compare_fourcastden_twelve_hour_mar24.py；audit；write_reports；audit --final。所有run/下载/launch输出exclusive，原数据不覆盖。预测大NPZ只本地；CSV/图/配置/审计/日志公开轻量部分。Jan4只读SHA验证，无重新推理。当前仅完成工程/条件参考场实验，未完成训练复现、独立真实大气或正式轨道精度验证。
