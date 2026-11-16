# TIE-GCM外部高度登记：有界官方证据更新 v1

2026-11-16；本轮正式外部接口仍为`EXTERNAL_DATUM_UNVERIFIED`。没有拟合高度偏移、发送邮件或取得维护者回复。

## 本轮实际增量与没有解决的内容

本轮重新读取[NCAR 2.0 grid/altitude说明](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/grid.html)及[VirES官方HAPI定义](https://vires.services/hapi/)，并搜索官方ZG/GRS80登记依据。NCAR文档作者Stan Solomon，April 2016；明确要求观测比较使用几何ZG、用calczg将位势高度与纬度/高度相关重力结合；下边界高度可由潮汐和气候下边界改变。**这些说明没有明确给出ZG零面与GRS80/WGS84椭球面的严格关系，也没有提供两者等价的证明。**

VirES与已有实际0301产品记录支持GRS80大地坐标合同；`Height_GD`网页描述中“latitude”的笔误仍保留，不能因字段名自行补充精度依据。Map-A沿用既有处理：GRS80大地位置构建ITRS，再由现有DensityQuery转换为WGS84大地纬度及椭球高，显式近似为模型纬度与ZG。每次查询记录原始和映射后坐标，**这是条件假设，不是正式外部登记**。

未新增能解除零面门禁的独立官方证据。官方文档的一般中点/界面表不能覆盖本地实际NetCDF DEN变量：本次文件DEN维度为ilev、ZG维度为ilev，严格按实物元数据和既有源码审计配对；TN/组分的lev定义不能套用到DEN。无新物理源码修改。

## 本轮不重复的已有证据

既有`zbound`、calczg底部及逐层积分源码审计、apex磁坐标辅助椭球与热力高度区分，以及默认下边界来源，继续引用`docs/TIEGCM_ZG_REGISTRATION_STATUS_20261103.md`与`docs/TIEGCM_SWARM_COORDINATE_DATUM.md`。不再重复抄录源码或把地心距离减常数半径当作高度转换。

## 仍需官方确认的四项问题

1. 模型地理纬度是否规定为大地、地心或球面约定；适用的外部椭球是什么？
2. 默认zbound及ZG的外部零面是椭球、海平面/大地水准面、参考球还是近似高度？
3. 潮汐/气候下边界与apex辅助椭球是否影响外部登记，如何量化？
4. 对TIE-GCM2.0原生DEN/ZG与GRS80卫星位置，维护者推荐的沿轨比较步骤和误差限制是什么？

## 可发送咨询草稿

复用已准备的`docs/TIEGCM_ZG_EXTERNAL_REGISTRATION_QUESTIONS.md`完整英文草稿；无需猜测收件人或重复改写。建议实际发送时补充本轮2022-03-24、B14、DEN/ZG均ilev、Map-A具体定义以及SHA附件。**本轮未发送**，没有官方回复。收到回复后仍需版本适用性、单位、数学变换和独立样例验证，不能自动升级门禁。
