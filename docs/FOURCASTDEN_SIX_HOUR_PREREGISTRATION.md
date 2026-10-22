# 两日期四模型6h执行协议（2026-10-22，正式推理前）

Jan4和Mar24 2023共同01初始化、目标02—07，每小时6步；History真实00/01额外信息，其他仅01，保留官方checkpoint及对应static，log用原等价隔离层。HINDCAST/TIEGCM_REFERENCE_ONLY，不称纯训练消融。日期按既有外部GFZ预注册，不根据新模型误差换窗。

仅12新NPZ：Jan4 04—07、Mar24 00—07。已有官方目录静态核对成员/压缩字节/CRC，网络再核对中央目录真实偏移，全部206/Content-Range/CRC/SHA/14键、float32、finite/哨兵、DEN正/TN正、ZG单调、时间/网格契约，预算40MiB，200整包立即拒绝。NPZ无自带时间/单位坐标属性，成员名与作者static/UNIT_VARS只是契约，不冒称外部高度验证。作者驱动与GFZ单独比较，不能替换。

GPU预算600s、RSS4GiB、新文件800MiB，磁盘余20GiB。先CPU任意长度原作者循环/未来物理毒化与静态预检。真实短例仅一组Jan4 Direct单forward（额外1次，不计48正式），与之后正式第一步逐元素核对；其余8序列共48正式forward，失败不重试。原n_prediction=6，不能拼接2h/中途重置。每步hook核验状态、History第三步起两个预测状态、逐块未来辅助/目标标量，Flow原normalized增量，log原log10与pow10。不得修补异常密度。

硬数值门禁：normalized/物理字段非finite、DEN<=0、TN<=0立刻失败，无补0/裁剪/重试；其他TN/风/Z范围完整记录以识别风险，不以残差大小为失败或删窗依据。逐步真实输出保存，若失败保留已完成前缀与实际日志，不增加forward。粗量级筛查只排明显数值故障，不是物理科学准确度。

评价共raw物理目标02—07、普通physical climatology、固定真实01持续性，float64、DEN kg/m3/风m/s/Z位势高度m；原生lev/ilev与目标ZG中位400—500组、固定upper20—28，不称固定450km/沿轨误差。全部lead1—6逐层cos RMSE/ACC、偏差/极值、相对RMS/P95/自然ln、极区/顶部、positive/finite。native log ACC/dex另存。native复核沿用rtol2e-5/atol1e-25、ACC绝对2e-6，共同物理第二实现rtol1e-12；无按结果调门槛。

比较误差曲线/绝对量与倍率，不预设单调，不因较高起始误差使倍率小就称更稳定。只两窗，活动/季节/初态与条件混杂，不给地磁因果/全年/观测或轨道准确度结论。先独立记录加载/读取/预处理/网络/原指标/hooks/保存与CUDA/RSS，不能按冷暖不同单事件给速度排名，更不能给AI替代TIE端到端加速比。12/24h、训练/TIE/RK45均不在授权内。任务后安全Git同步并停止。
