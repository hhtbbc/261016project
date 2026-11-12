# A14历史证据独立审计

|检查对象|结果|
|---|---|
|日志步数最大值|23040；不是声称每一步都有单独日志|
|NORMAL EXIT|4|
|primary / hourly secondary|17 / 384|
|NetCDF及SHA|33卷全部一致|
|时间/网格/字段/单位/填充值/密度温度风组分工程检查|PASS；源冷echo及primary未输出诊断按原协议N/A，不伪造字段|
|实际驱动最大绝对差|2.8422e-14|
|资源采样缺口|739.822638秒（441.227638至1181.050276秒）|
|真实MPI退出状态|UNKNOWN；留存证据中不可恢复|
|有限离线科研分析|允许，明确PARTIAL/PROVISIONAL身份|
|原冻结完整工程验收|PARTIAL，不能改PASS|

本轮只读前后共76项历史文件SHA相同，包括33卷、原状态、原输入、日志等。真实退出码仍null；没有重写旧审计/旧日志、没有重新生成输出。实际完整数据检查与主/次历史schema见experiments/tiegcm_supervision_repair_v1/A14_evidence.json。首次独立审计错误地假定所有primary都含DEN，读取阶段IndexError；改为逐文件显式列出实际字段和缺失诊断、沿用原物理检查，保留失败日志，未修改原数据。

当前项目未保存额外可靠的原wait/wait4或系统进程记账结果。当前/proc列表、输出完整性和4 NORMAL EXIT都不能证明原launcher返回0。数据完整性与真实退出/全程资源监督资格是不同证据链。
