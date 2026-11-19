# V17：既有真实积分成果保护、NetCDF告警诊断与工程验收闭环

**V17总状态：ENGINEERING_PASS。V16_ORIGINAL_ENGINEERING_STATUS=FAIL。**

本轮仅CPU只读复验，TIE-GCM物理模型启动0次，未修改原始35个NetCDF、CDF、GPI、二进制、初态、积分配置、旧失败记录或冻结科学评价协议。未进行任何真实密度误差评分、校正拟合、DART、AI或轨道传播。

## 1. 原始成果保护

起始本地与远端main均为a902fa44add0ed02a53b2991078753213ac70b75。实际run_id为094fcac3949c4e2e981d3baac1a5d8bf。逐文件对照V16模型manifest验证35个NetCDF SHA，全部一致；原MPI父及四rank均退出0，四rank日志10—24480每10步记录完整，NORMAL EXIT各一条，同一session及直接wait回执一致。原始一次预约、失败验收记录和V16缺失acceptance.json的历史事实保持。

原CDF/ZIP/HDR、GPI、原input和二进制SHA也核实。复验结束再次核对35输出与全部2506个受保护文件SHA，全部不变。保护证据见asset_protection_before.json和asset_protection_after.json。

保护方式是应用层一次预约拒绝重跑、原始数据只读打开及前后SHA核对。原文件模式仍0644，不宣称具有root也无法写入的OS immutable保护；本轮未擅自chmod或修改属性。

## 2. 根因及属性风险

实际17个secondary文件的DEN/ZG共34个变量实例均为float32，missing_value以float64保存为1e36，未提供显式_FillValue。将1e36转为float32得到9.999999616903162e35，不能精确往返。NetCDF4因无法安全转换而告警，并可能不使用该missing_value自动掩码。

V16警告格式附带冻结读取器源码行，包含np.ma.filled(..., np.nan)。原监督器在统一stdout/stderr上以词法匹配NaN，匹配了这段源码上下文，而非观察到数组NaN。因此只读验收被SIGTERM终止，未生成正式结论。警告不是数据损坏的充分证据，也不是可无条件忽略的提示。

风险实际存在：极小反例把一个正且有限、但声明为missing_value的数值写入float32变量，默认自动掩码可能遗漏它；原始显式原生检查仍会按变量dtype识别并拒绝。真正NaN/Inf、填充值、非正DEN和非单调ZG同样拒绝。

对本次真实数据，原规则全408帧检查与独立原生读取都未发现这些无效值。这是本次工程PASS的数据依据。没有修改原属性或把缺失补零，也不把本次有效数据推广为任意未来文件都能仅靠默认自动掩码安全处理。未来仍需先严格原生检查，再做查询。

## 3. 修复边界与新代码身份

没有修改src/runtime/supervisor.py、src/atmosphere/hourly_tiegcm_observation.py、src/atmosphere/tiegcm_mar25_acceptance.py或其他旧冻结算法。旧物理积分入口和模型阶段致命监控语义逐字不变。

新增src/runtime/readonly_audit_warning_channel.py，仅在新只读CPU审计子进程上下文中生效：

- 必须通过Python Warning API发出、category恰为UserWarning、完整文案为已核实NetCDF missing_value cast告警，而且来源文件路径及SHA与原冻结小时读取器一致，才分流原始警告和源码上下文。
- 完整警告格式、原文、来源、行号及序号写本地raw journal；控制stdout只输出不含自由文本的结构化事件。50条告警来自25目标帧×DEN/ZG两处来源，原31/32行各25条。
- 不是删除NaN/Inf规则，不是丢弃stderr，不是全局关闭Warning。任意自由文本np.nan不在自动白名单内；未知已发出的告警fail-closed，真正Traceback/异常/非零退出仍失败，普通stdout/stderr仍通过原监督器。
- UserWarning重复告警全部记录，其余既有Python过滤基线保留；离开上下文恢复原handler。

新主入口scripts/launch_tiegcm_v17_readonly.py只允许固定Python只读批处理，没有模型命令或授权参数。新批处理复用原accept_run，随后顺序执行独立读取算法；原科学数值、转换、网格、插值和容差不变。代码版本/SHA在audit_protocol.json和source_manifest.json，旧V16路径及失败仍可追溯。

## 4. 测试及唯一一次完整复验

最终35项不同测试通过：18项针对性正反例、9项原验收回归、8项小时算子回归。

覆盖：真实NetCDF告警与源码np.nan正例、有效值读取前后完全一致、实际NaN/Inf、大小两类missing marker/_FillValue、非正DEN/ZG顺序、真实Traceback、非零和信号退出、监控失效、原模型NaN/Inf/ERROR/MPI_ABORT仍失败、来源SHA伪造拒绝、handler恢复、禁止模型子进程、目录/输出保护、进度和时间轴。包含零权重列的原八列拒绝测试及正式科学模块SHA测试。

测试开发首轮的子进程fixture使用了Astropy不接受的短时刻字符串，修正fixture为完整ISO时刻后通过；保留原失败日志。没有改算法、放宽容差或提前消费正式复验次数。

唯一完整复验命令：

```bash
source scripts/activate_tiegcm.sh
python scripts/launch_tiegcm_v17_readonly.py
```

新目录experiments/tiegcm_2022_mar25_postrun_acceptance_v17/audit_once_local保留一次标记，不自动重试。该监督进程内原主验收调用1次，独立算法调用1次，物理模型调用0次。

- 真实直接wait返回0，qualification=PASS，cleanup verified，采样缺口0。
- 整个主验收及独立核验墙钟22.630436秒，低于600秒。
- 峰值采样进程树RSS273186816字节，约260.53 MiB；进程自报历史峰值269.20 MiB，定义不同，不能把采样当连续峰值。
- 子进程CPU user18.171919秒、system4.051981秒。
- 独立核验部分10.223363秒，已含在22.63秒中，不能重复相加。
- 新产物远低150MiB；NetCDF没有复制到新目录。原35个约3.335GiB模型场留原位置。

## 5. 正式工程验收和独立复核结果

| 项目 | 新主验收 | 独立复核 |
|---|---|---|
| 原MPI父和四rank真实退出/身份 | PASS，0/0/0/0/0，同一run_id/session | 原始回执、wait事件和rank日志交叉核对 |
| 积分步数/终点 | 24480步，暖态iter与日历一致 | 完整进度序列及所有输出time/mtime/iter重新读出 |
| 输出SHA及记录 | 35文件、18主/408小时次记录 | 全35 SHA与主结果及V16保护清单一致 |
| 时间覆盖 | 03-09至03-26，目标日25整点帧 | 精确重建18日序列和408小时序列，无缺失/重复/错序 |
| 冷echo | 仅首primary，继承计数不用于算更新 | 独立不将cold计数计入暖态更新 |
| 全408帧DEN/ZG | 原生ilev、g/cm³/cm，填值/掩码/有限性/正值/单调性PASS | 自行关闭隐式自动掩码后按原生dtype识别标记，完整408帧复算，异常0 |
| 全暖态实际驱动 | 最大差2.84217e-14 | 独立四节点/UTC三小时插值重算，最大差5.68434e-14；均低于原1e-10 |
| Swarm A | 合格2880，成功2880，失败0 | 直接CDF+独立邻点/垂直重建，2880/2880，23040列检查 |

两套结果在身份、SHA、时间轴、记录数、原生数据和覆盖上相符。浮点代数顺序导致驱动最大残差略不同，均在冻结容差内，不是放宽标准。主验收的TN/风原生顶层padding、组分等旧basic_file内部规则也原样执行，工程合法性不等于充分预热或真实观测准确性。

全408帧每场约30668544个原生DEN/ZG值经过合法性检查，未用V16仅目标25帧专项替代全程正式验收。主/独立均使用全部质量合格Swarm点，不删失败、不外推、零权重列仍检查。

主与独立在同一个CPU批处理进程中顺序执行；独立JSON写出时批处理父wait尚未完成，因此其该字段为pending。正式最终退出码取后续direct wait的status和result/resource文件，真实为0，不伪造提前的退出状态。

正式轻量acceptance.json、独立结果、属性明细、告警摘要及保护证据位于新实验目录；完整原始日志/告警/测试夹具仅本地保留。V16原失败文件和报告未变；V17的新PASS没有覆盖历史FAIL。

## 6. 状态与下一轮

V17=ENGINEERING_PASS；V16_ORIGINAL_ENGINEERING_STATUS=FAIL；新物理启动0。已解除2022-03-25这组既有物理场的工程验收阻碍，可以申请下一轮真实密度误差评价，但本轮未执行。

下一轮保持冻结方案：2022-03-25新B14主背景、2021-03-25冻结B14只读对照；06Z/18Z、过去3小时半开历史窗、未来1/3/6小时累计及不重叠块；Raw/Global/Latitude/Stale06按原协议，N≥30、三纬区和无fallback不变。参数先历史估计并写SHA冻结，再future poison与共同样本评分，保留四项联合无退化条件，不以相邻30秒点或重叠窗口作独立IID论证。

数据与此前相邻窗口用于开发，仍是HINDCAST / PROVISIONAL Map-A / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED。工程PASS不证明密度误差收益、跨季节泛化、充分预热或外部ZG零面。SCIENCE_TRAINING_READY=False、RestartFAIL、DARTNOT_ADMITTED、REAL_ORBITBLOCKED保持。

当前无需要重跑模型或手工修改原始文件的工程问题。需要用户下一轮明确授权评价；原属性不一致仍作为已知数据接口风险保留，未来不可绕过严格原生合法性预检。本轮整理和安全同步后停止。
