# NRLMSIS 2023年驱动核验（HINDCAST）

采用NRLMSIS 2.1 / pymsis 0.13.0。依据[官方calculate API](https://swxtrec.github.io/pymsis/reference/generated/pymsis.msis.calculate.html)及实际安装的msis.py，显式传入全部太阳与地磁参数；geomagnetic_activity=-1启用历史Ap模式。模型不接收Kp代替Ap。

## 冻结输入与时间约定

原GFZ数据不重新下载；太阳Fobs支持2023-01-31—05-05，ap/Ap支持03-12—25。原始文件SHA与已有TIE驱动审计/来源清单逐项相符。冻结文件configs/nrlmsis2023_gfz_frozen.json，SHA256 `66b9242f9e2f356f134c4152b839e2b46b0e72f9860a44872b9e138ef8ba56c4`。原始来源、SHA和32条三小时边界测试见logs/nrlmsis_drivers_audit.json。GFZ来源及许可：[数据说明](https://kp.gfz.de/en/data)、[格式说明](https://kp.gfz.de/app/format/Kp_ap_Ap_SN_F107_format.txt)，CC BY 4.0；原API响应保存在data/raw/，不替换原文件。

- F10.7取目标UTC日的前一日Fobs，保留实际日地距离下观测值，不用1AU调整Fadj。
- F10.7A取目标UTC日D−40至D+40的81个Fobs算术平均，不对异常高值擅自裁剪。居中平均及事后def产品包含未来信息，因此是hindcast。
- 三小时ap为[00,03)、[03,06)等UTC半开区间，整点转入新桶；不做TIE使用的中心时刻线性Kp插值。
- 七项输入依次为：当日Ap、当前三小时ap、3/6/9小时前ap、12—33小时前8桶均值、36—57小时前8桶均值。最长历史57小时；目标03-20—23均完整，日界和03:00边界独立索引测试通过。
- ap及Ap每值均def；每日Ap与八个ap平均之差不超过官方整数舍入的0.5。太阳API无逐值质量标记，仅确认完整、有限、非缺失；不能宣称已独立验证观测质量。

2023-03-21的前日F107=156.1 sfu，F107A=160.79135802469133 sfu。当日Ap=6。00:00:02的历史数组为[6,9,9,5,27,10.125,6.875]；03:00:02为[6,4,9,9,5,12.375,7.375]；06:00:02为[6,6,4,9,9,10.75,8.5]。这与TIE同日自身插值的F107不必相等，不能把差异全归于大气模型结构。

所有调用显式提供F107/F107A/Ap，实验中将pymsis.msis.get_f107_ap替换为立即抛错，证明确实没有使用默认补数路径。缺测、错误数组长度或非有限参数均拒绝；不联网回填、不返回零密度。
