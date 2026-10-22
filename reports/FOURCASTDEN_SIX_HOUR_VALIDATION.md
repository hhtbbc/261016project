# FourCastDEN两日期连续6小时执行验证（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 范围和数据门禁

固定2023-01-04与03-24，01初始化、目标02—07，每序列6步。新增8序列48正式forward，加唯一Jan4 Direct单forward短例。旧2h数组、官方源码/Linux副本、4权重、static/static_log/旧审计等533项SHA不变；没有训练、微调、12/24h、TIE或RK45。首检本地及远端main均a1b474481155d252281ec3ff7751351f82b4d18a。

已存ZIP目录先确认12成员与压缩字节25,019,661，网络中央目录再核CRC/尺寸/真实偏移。仅新增Jan4 04—07四帧、Mar24 00—07八帧。第一次第8成员文件名Range收到HTTP500（未读body），前7成员已CRC/SHA通过；保留ranges.json/失败日志，另一次有界补取只取剩5成员，共用40MiB预算，未重取成功帧、没有绕过CRC或200整包。最终累计响应体26985595字节=25.735MiB，保守预留26985662字节<40MiB。所有成功数据Range均206/Content-Range/长度匹配，ZIP CRC与zlib复核，SHA和14键/shape/dtype/finite/有限哨兵/正DEN/TN/ZG单调校验通过，新raw0444。各文件实际min/max及单位契约、原压力网格见*_download.json/preflight；NPZ无独立坐标/单位/时间属性，不冒称外部高度验证。

## 任意步反馈与实际作者流程

新autoregression.check_autoregression支持任意正长度、H0/H1，逐步对比真实hooks的177/354通道、171输出、历史顺序、逐块下一小时6辅助和目标4标量。H1：[real00,real01]→[real01,pred02]→[pred02,pred03]→…→[pred05,pred06]。第三步开始两个状态均为预测。H0每步反馈前次预测；Flow逐步normalized delta相加；log始终匹配static_log、log10(g/cm3)、pow10逆变换，DEN乘1000转kg/m3。

6项新CPU测试调用实际作者inference循环与合成网络，对四模式的6步未来真值毒化均不改变预测，错误后期teacher forcing/aux/scalar/Flow直接状态被拒绝；任意1/3/7步合成也检查，不是额外真实模型预测。全232测试25.416s通过，旧ERFA合成测试dubious-year及focused扩展导入warning原样保留，未安装环境或屏蔽检查。

严格官方权重load_state_dict、原AFNONet，History66,870,720参数/354输入，其余64,695,744/177，均171输出。232测试与全部静态门禁先通过，再唯一Direct真实短例（146.803ms）验证有限/正密度及shape，之后正式第一步与其逐元素一致。每序列独立初始化，不跨日期传状态。实际174物理/LBC通道从原NPZ重建匹配标准化逐元素一致。新6步全部hooks通过；Jan4前2步与全部4模型既有2h结果逐元素一致，旧网络未重跑。

全部48预测状态finite、DEN100%正、TN正，无指数溢出/裁剪/补0/重试。网络、驱动、输入、补丁SHA与每序列配置/反馈/输出SHA在实验目录，原始第三方不改。已知未来条件为HINDCAST，不是实时自主预报。

## 公共物理与native评价

float64匹配逆变换、同raw目标02—07、普通physical climatology、固定real01持续性。密度kg/m3、温度K、风m/s、Z位势高度m；native作者log ACC/dex另表。cos纬度加权RMSE和ACC、无效分母N/A；独立加权求和实现复核8208个模型通道时效rtol1e-12。native normalized RMSE最大相对差2.38e-07、ACC最大绝对差2.29e-07，沿用rtol2e-5/atol1e-25/ACC2e-6，没有放宽。每模型每lead171/171通道均优于共同持续性，仍不是观测精度验证。

DEN全球/极区/非极区逐层RMSE、相对RMS/P95/max、自然ln差/偏差、固定upper20—28、参考ZG中位400—500组全保留。Jan4 near组21/22/23，Mar24 +1/+2h为20/21/22、+3—6h为20/21（22层中位高出500km）。因此跨lead近高组成员变化也会影响曲线，不能称固定几何高度误差；固定upper和全逐层结果提供补充。

## 运行资源与独立计时

|日期/模型|加载s（复用为0）|读取解码ms|标准化ms|其余预处理ms|6次forward合计ms|native指标事件ms|loop s|保存s|显存allocated峰MiB|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|2023-01-04 Direct|1.3177|89.321|4.301|23.186|109.741|546.599|0.8132|2.1868|295.063|
|2023-03-24 Direct|0.0000|91.079|4.246|20.721|113.419|1.931|0.2556|2.2397|295.063|
|2023-01-04 Flow|1.1155|88.792|4.136|19.969|110.574|1.915|0.2475|2.1640|295.130|
|2023-03-24 Flow|0.0000|90.000|3.982|20.443|109.743|1.804|0.2458|2.2217|295.130|
|2023-01-04 LogDEN|1.1595|90.044|4.218|17.861|112.629|116.391|0.4071|2.3851|296.279|
|2023-03-24 LogDEN|0.0000|90.099|3.923|16.067|110.724|2.419|0.2544|2.3258|296.279|
|2023-01-04 History|1.1719|101.368|4.624|19.713|113.082|1.940|0.2723|2.7464|308.760|
|2023-03-24 History|0.0000|103.160|4.148|19.422|111.300|1.942|0.2759|2.8306|308.760|


总监督39.700139s（含GPU worker启动和SHA等），GPU阶段30.840975s含CPU I/O/压缩/评价；纯网络事件合计另列，不能用总墙钟当纯网络。短例先冷调用，正式NN已warm；各模型各加载一次复用两窗，未做额外吞吐warm-up。首次native指标事件546.599ms、log新分支116.391ms，含首次编译/派发及CUDA区间中的等待，并非纯kernel剖析；随后native指标区间约2ms。指标call墙钟与事件分别存储，不能据此给稳健速度排名。

DatasetTimer仅透传计时load_variables与_normalize，保留原返回值、原算术和原源文件；读取解码包含NPZ解压/字段抽取，其余预处理含solar/geomagnetic/拼接/张量转换。作者loop内部另有读取，不将前置独立读取与loop简单加总作总推理。MetricTimer透传三原指标函数，另存每次call wall/GPU events，无新增NNforward；独立raw重建、前缀完全一致与native指标复核证明所用数值路径通过。

监督峰RSS1.316GiB，CUDAallocated峰约295—309MiB（reserved含缓存/加载，不等于活跃张量）；CPU分析10.554s、峰635.707MiB。初审新增391.486MiB<800MiB，网络<40MiB、GPU<600s/RSS<4GiB；原始和预测大NPZ只本地。实际GFZ与作者NPZ驱动分别记录，不以替换输入强行相等。

## 复现实验入口

source scripts/activate310.sh；unittest discover；run_fourcastden_six_hour.py --fetch（初次500留档）；同脚本--resume-fetch（一次剩余补取）；无参静态；supervise_fourcastden_six_hour.py；analyze_fourcastden_six_hour.py；audit_fourcastden_six_hour.py；write_fourcastden_six_hour_reports.py；最终audit --final。均once-only，不删除launch重试。新标签experiments/fourcastden_six_hour_v1，raw/processed同标签，logs/fourcastden_six_hour*。这里只证明工程/数值/对TIE参考的条件预测，不等于完整论文训练复现、真实大气或最终轨道准确性。
