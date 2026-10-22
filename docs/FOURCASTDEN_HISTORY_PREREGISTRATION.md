# 官方History与共同01时四模型协议（2026-10-22，推理前）

仅Jan4 2023，History00/01初始化，其他模型01初始化，共同预测02/03。History官方n_history1、354输入、171输出、4标量；普通static、flowfalse/logfalse；其余分别原checkpoint与匹配static，严格load_state_dict。额外历史信息和不同权重/统计不构成单因素训练消融。原171物理通道永不由未来真值反馈，辅助与标量按作者循环，HINDCAST。

唯一允许新增原始数据03时NPZ；HTTP206/Content-Range/CRC/SHA/14键/finite/正DEN/ZG单调检查，网络总预算10MiB，拒绝200。4帧仅链接到独立data_view，原00—02不改。

先CPU合成实际作者循环、反馈/毒化测试，再History一次真实forward预检；通过后四模型各一个两步序列（8正式forward，另1History预检）。独立目录fourcastden_history_comparison_v1，失败不重试；log-DEN复用上次经SHA验证隔离覆盖层，不改第三方。GPU含预检监督<=600秒、RSS<=4GiB、新增文件<=150MiB；磁盘<20GiB停止；大数组压缩本地，不入库。

物理评价沿用三模型协议：float64各自匹配逆归一化，log以10为底恢复g/cm3，再乘1000为kg/m3；其他变量转SI。共同目标为原NPZ02/03物理场；共同普通物理气候态；固定真实01物理场为持续性，cos纬度RMSE/ACC（无效分母N/A）。全层逐层RMSE再平均、每层相对RMS/P95/自然ln误差、极区、顶部、参考ZG全球中位400—500km原生层组，非固定高度。作者log原生指标分开。不用单窗挑架构/训练超参、不将TIE拟合当观测或轨道准确度。

反馈必须逐元素一致，native指标float64复核沿用rtol2e-5/atol1e-25，ACC绝对2e-6；共同指标第二实现rtol1e-12。输出finite、DEN>0/TN>0，失败不裁剪/补0。仅工程门禁，不以模型优于其他作为PASS条件。计时区分读取、加载、首次/后续forward、指标/hooks/保存，不能根据不同CUDA预热次序直接排名吞吐。
