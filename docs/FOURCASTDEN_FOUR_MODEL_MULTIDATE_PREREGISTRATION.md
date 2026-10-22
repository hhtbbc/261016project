# 五日期四模型共同01时协议（2026-10-22，新增推理前冻结）

日期固定Jan4/Mar23/Jun21/Sep23/Dec21 2023，统一01起点、目标02/03。Jan4官方四模型既有结果严格SHA只读，新增后四日期16序列32forward，无额外真实forward预检。History真实00+01起始，第二步real01+pred02；其他模型real01->pred02->pred03。History多历史信息、模型/统计不同，不称单因素训练消融。

只取后四日期03 NPZ，总HTTP预算20MiB；必须先核对4成员全存在，206/Content-Range/CRC/SHA/14字段/单位契约/finite/哨兵/正DEN/ZG单调。原00—02不重取，Jan4 03不重取，不下载整包。原NPZ无自带时间/单位/坐标元数据，成员名和官方不可变static/UNIT_VARS是数据契约，不冒称独立高度或观测核验。

严格官方checkpoint，Direct/Flow/History普通static，log配套static_log/原等价隔离层；FP32/TF32false、HINDCAST。作者循环不变，每两次真实hook逐元素核验物理反馈、增量/指数、目标辅助和驱动；future physical truth仅评价，future条件给定。保护全部历史结果、原模型/统计/权重，不调参/修补异常密度。非finite或DEN<=0停止该正式任务，不重试。

共同评价延用raw物理NPZ目标、普通物理气候态、真实01固定持续性；float64统一单位DEN kg/m3、风m/s、TN K、Z位势高度m。cos纬度RMSE/ACC、层/极区与DEN相对RMS/P95/自然ln差，固定upper20—28和参考ZG全球中位400—500km原生层组；不称固定几何450km/卫星沿轨密度误差。native log ACC/dex另存，独立复核沿用rtol2e-5/atol1e-25、ACC绝对2e-6，共同第二实现rtol1e-12，不按结果放宽。

跨窗统计以5日期等权，均值/中位数/min/max/配对差/逐窗排序与增长，无显著性或全年结论。初始化00旧与01新仅条件敏感性：目标时段不同，不把lead相同但目标不同时刻当相同任务；另保留共同02目标的旧+2h/新+1h配对。History没有合法00对照。

运行前预算按旧4模型21s/约110MB保守估计4新窗<=200s、输出<=500MiB；硬限制GPU监督600s/RSS4GiB/新增650MiB/磁盘余20GiB。模型各加载一次，4日期独立初始化；加载、冷forward、warmforward、读取、原循环含指标/hooks、保存分记，不按非受控单次计时排吞吐。新tag fourcastden_four_model_multidate_v1；不训练/新TIE/RK45/6h，任务后安全Git同步并停止。
