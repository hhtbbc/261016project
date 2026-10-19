# Swarm-A气动与姿态补充核查

保留docs/SWARM_DRAG_PARAMETERS.md。本次复用SC_ADYN和DNSAPOD，没有重下载这些数据。新增ESA STRAATT三天ZIP及安全提取文件在data/raw/swarm_attitude_2023，大小/CRC/路径/SHA清单manifest.json；处理审计logs/swarm_attitude2023_audit.json、flags_intervals.json。是2025重处理0601，不是2023时点可用版本。

## 质量与面积

同期SC_ADYN m_SC：03-21 400.337—400.447kg，03-22 400.341—400.454kg，03-23 400.331—400.459kg。不能将范围当正式sigma，不使用473kg发射质量。SyncStatus、Flags_Platform、Flags_q需联合解码；质量逐条可信度/正式不确定度仍未闭合。

CDF对A_head/A_right/A_left/A_down说明为orbit frame中的front/right/left/down截面向量，单位m²。不能把它们视为四个直接相加的标量迎风面积；还需确认有向面积定义、遮挡/重叠及相对流方向。现有四元数是S/C→ITRF，而面积向量已在orbit frame，不能重复旋转；需明确ORB基底及CDF向量的生成方法。官方SC_xDYN.txt实际是全档案文件清单，不是产品定义，不能用于证明几何公式。

## 姿态真实检查

每个STRAATT日86400个1秒样本。q变量明确`Quaternion, transformation: ITRF <- S/C`；**该属性没有声明标量先后或主动/被动矩阵符号**。参考其他Swarm磁场产品的标量末尾惯例不能自动套到此产品，尚不执行真实迎风面积转换。03-21四元数范数0.999999999123—1.000000000886；其他日含坏标志，详细全量极值见审计，不能只凭范数认定全部姿态有效。

Flags_q出现0/1/2/3/5/17/34/255；SyncStatus含非零；尚缺可靠逐位定义，不把全部非零简单解释成机动，也不宣布0以外全坏。Maneuver_Id出现0与4，已生成全部连续区间：03-21 12:21:07起code4持续至午夜；03-22 00:00—00:56:50及13:21:07起code4；03-23 00:00—00:26:50及12:51:07—23:56:50 code4。代码4的物理定义未确认，不能据此断言长时间推轨。HDR引用AUXAORBMAN等辅助文件，下一步应获取官方定义与同期辅助表核对。

SC_ADYN dt_thr>0的记录数150/59/128（3天），f_thr却全零；可能涉及姿控/配对抵消/产品定义，但没有证据不能任选解释。原平台值0/16及thr_set须解码，不能把记录行数当独立机动次数。48h窗口内上述code4/非零推进器记录需暂列待审区间，正式误差报告按解码后机动/正常段分别统计，不能事后为了降低误差筛选。

## Cd与访问阻碍

没有落实与此几何/气体成分/姿态配套的可靠Cd或弹道系数；DNSAPOD是POD反演的沿轨密度，不是可直接替代全局模型的独立预测产品，不能用其与未来SP3反向拟合Cd再复验同窗口。

ESA Level1b产品定义PDF请求HTTP403已记录，不绕过访问。公开CDF给出部分物理定义，尚不足以闭合四元数顺序、面积投影、平台位/机动码、推力计数含义和气体-表面Cd。真实阻力精度实验仍暂停。可另设显式假设参数敏感性试验，但不能冒充真实Swarm性能。

实际NaN补充：[{'file': 'SW_OPER_STRAATT_1B_20230321T000000_20230321T235959_0601_MDR_SAT_AT.cdf', 'nonfinite_quaternion_rows': 0, 'finite_norm_min': 0.9999999991231159, 'finite_norm_max': 1.0000000008859053}, {'file': 'SW_OPER_STRAATT_1B_20230322T000000_20230322T235959_0601_MDR_SAT_AT.cdf', 'nonfinite_quaternion_rows': 80, 'finite_norm_min': 0.9999999991023214, 'finite_norm_max': 1.0000000008590402}, {'file': 'SW_OPER_STRAATT_1B_20230323T000000_20230323T235959_0601_MDR_SAT_AT.cdf', 'nonfinite_quaternion_rows': 10, 'finite_norm_min': 0.9999999991369439, 'finite_norm_max': 1.0000000008627532}]。3月22、23日存在真实非有限四元数，不能仅归因于标志。原audit中这两天未掩码范数min/max为NaN，补充有限样本统计在logs/swarm_attitude2023_finite_quality.json；所有NaN须拒绝使用，不能线性穿越无效姿态段。
