# NCAR TIE-GCM consultation draft · unsent

**Subject — External height datum and an independent registration test for TIE-GCM 2.0 ZG**

Dear TIE-GCM science support team,

I am reviewing how to register TIE-GCM 2.0 geometric heights to satellite geodetic coordinates. I inspected addiag.F, cons.F and lbc.F. The bottom ZG interface equals Z, with Z anchored by z_lbc. The higher interfaces are integrated with variable gravity, and GSWM can modify the lower boundary.

Could you clarify the physical zero surface and positive direction of ZG, the model latitude convention relative to geodetic or geocentric latitude, and the external reference used by z_lbc and its tide perturbations? Does TIE-GCM 2.0 specify a supported conversion from GRS80 ellipsoidal normal height to ZG for this setup? If available, could you provide a source or documented reference implementation with independent control points and an uncertainty bound over its stated domain?

If no unique external datum is defined, how should users state the resulting limitation and bound the registration error when comparing neutral density along a Swarm orbit? The project is keeping the observational density sealed during this registration work.

Thank you for your time.

## 中文对应草稿

**主题 — 核实 TIE-GCM 2.0 ZG 外部零面并请求独立配准控制点**

NCAR TIE-GCM 技术团队您好：

我们已查阅 addiag.F、cons.F、lbc.F。底接口 ZG 等于由 z_lbc 锚定的 Z，其上按变重力积分，GSWM 可改变下边界。请问 ZG 的物理零面及正方向是什么，模型纬度与大地或地心纬度如何对应，z_lbc 和潮汐扰动采用何种外部参考？能否提供 GRS80 椭球法线高到 ZG 的推荐转换、源码或文档、独立测试点和适用域误差界？若没有唯一外部 datum，请说明沿 Swarm 轨迹使用模型密度时应如何报告登记局限和误差。

发送前从 NCAR 2.0 官方 Contact 页自行核对实际渠道和 moderated list 入口。现有材料没有确认订阅、审核或实际发帖权限。 [NCAR 2.0 官方 Contact](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/contact.html)
