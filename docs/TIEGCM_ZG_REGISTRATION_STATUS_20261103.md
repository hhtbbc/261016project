# TIE-GCM ZG外部登记：一页状态（2026-11-03）

|关系|已知事实|不能据此证明|
|---|---|---|
|本项目原生变量|实际DEN/ZG按ilev界面；组分和TN在lev；ZGMID可给中点高度|不能将同数组索引混作同高度|
|高度名称|Z是位势高度，ZG是模型几何高度|几何不等于WGS84/GRS80椭球高|
|下边界/重力|已有zbound/calczg及apex源码证据保留|有效重力半径不是正式地球椭球或零面|
|外部观测|DNS使用GRS80，SP3时间/框架与其已对齐|观测之间一致不解决模型ZG零面|
|新增有界检查|NCAR2.0诊断文档再次确认DEN ilev及ZGMID lev；HAO邮件候选不可读|没有新增可放行外部零面证据|

结论：EXTERNAL_DATUM_UNVERIFIED不变。没有重复旧577点或完整沿轨查询，没有调整高度偏移。正式外部接口仍拒绝；PROVISIONAL A/B仅是假设敏感性。

证据：https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/diags.html；完整有界来源表见results/swarm_physical_force_readiness_v1/official_evidence_review.csv。

NCAR草稿复用[原稿](TIEGCM_ZG_EXTERNAL_REGISTRATION_QUESTIONS.md)，仍仅草稿，未发送、无维护者回复。关键待答：地理纬度定义、ZG下边界零面、与GRS80/WGS84的推荐登记方法及精度限制。须区分本项目独立默认下边界与作者2023配置，不以其默认值替代作者证据。
