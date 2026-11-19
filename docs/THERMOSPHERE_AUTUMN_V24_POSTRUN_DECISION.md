# V24下一步：保护已完成积分，先修复只读工程验收

本轮2021秋季真实冷启动已完成23040步，MPI父/四rank均0，33文件17/384记录，原始结果不得重跑或覆盖。当前总状态ENGINEERING_FAIL，原因是主验收器的cold echo身份条件不符合实际首primary元数据。

实际`primary_001.nc`的global run_type为空字符串；year=2021、mtime=[252,0,0]、CF时间/initial_year/day/mtime正确，iter=115200为原生源继承值。暖态primary/secondary的run_type是initial，暖态iter与目标START及经过分钟数相符。旧V16春季首primary同样为空。output.F首echo使用copyhist源结构而非常规define_hist；不应把两条路径的属性赋值习惯直接等同。

冻结V23验收器要求`n.run_type=='initial'`，因此在第一卷报Illegal cold-echo exemption，主全程输出检查未完成，主Swarm覆盖NOT_RUN。独立扫描已经验证33原件SHA、全部384小时DEN/ZG及TN/风/组分、真实GFZ驱动和2880点八列覆盖；独立原始数据检查PASS不能替代主验收闭环，V24原FAIL必须保留。

建议下一轮明确授权一项**只读验收修复与复验**，不是新模型积分：

1. 保护V24全部33原件、真实run_id/回执、首失败acceptance与V23冻结代码SHA，禁止删除一次性标记。
2. 新建版本化审计适配/覆盖层，审查首primary的综合冷启动证据：显式SOURCE及冻结SHA、实际source记录、run_id/session/真实退出、首记录UTC与initial日历、原生cold iter与34状态等；不能仅把空run_type全局放行。
3. 增加首echo空属性的真实最小fixture、伪造cold身份/错误时间/错误source/暖态空属性及数值异常等反例。原浮点容差、数值检查与Map-A规则不放宽，不修改任何NetCDF元数据。
4. 新目录一次完整只读验收并独立复核；原V24失败保留，由新证据决定是否闭环。需要新的明确授权，不在本轮实施。
5. 同时审查未来2022使用的审计版本绑定：V23执行器仍引用旧验收器，若直接启动2022将面临同类误判。只能在单独审查的执行覆盖层中钉住修复后只读工具；2022物理input/GPI/初态SHA不改变。原执行器还硬编码读取2021/postrun_audit_local/acceptance.json；该V24原FAIL必须保留，新执行覆盖层须显式绑定新版2021闭环证据的路径和SHA，不能覆盖旧FAIL来通过门禁。

2021主验收闭环前，不建议直接申请启动2022。闭环后再单独授权2022一次16天冷启动及只读验收；不得用2021密度评分结果重选日期、调整源或方法。本轮两日期均未开展新密度评分。

A_MAREQX_APPROVED继续有效；AUTUMN_ADAPTATION_UNVERIFIED、FOURTEEN_DAY_SPINUP_NOT_PROVEN_CONVERGED、EXTERNAL_DATUM_UNVERIFIED、RestartFAIL、SCIENCE_TRAINING_READY=False、DARTNOT_ADMITTED、REAL_ORBITBLOCKED均保持。
