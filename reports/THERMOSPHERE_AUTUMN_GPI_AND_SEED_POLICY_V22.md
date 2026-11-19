# V22：2021/2022秋季GPI生成、独立验收与初态路径审查

## 一、今日完成情况

基于实际main `d3ead6ebf77e7068fcec9cad60ca5ce3b42caf81`，本地与远端起始一致；已有不相关未跟踪同步日志保留。新证据位于`experiments/thermosphere_autumn_gpi_seed_policy_v22/`。两年份均为 **GPI_READY**，整体为 **GPI_READY_SEED_POLICY_PENDING**，模型仍非RUN_READY。

已核对V21八份Swarm/GFZ原件、2021全年GFZ及受保护旧协议/报告身份。正式生成前分别独占写入`input_sources_2021.json`、`input_sources_2022.json`和`protocol.json`。未重新下载数据、启动模型、建立新积分配置、拟合参数或评分。

## 二、关键技术解释

复用原春季成功入口`scripts/prepare_tiegcm_training_drivers.py`的`arrays/write_gpi`，代码SHA仍为`82fdbf2c4d39f04041013de0b3e5a16bd9d9bbeedd7ee31b6c1c0f9eb7465675`。2021只增加按旧归档列定义提取的适配层：Fobs第26列、八Kp第8—15列、质量第28列=2。2022复用严格JSON解码器，不使用Fadj或非def Kp，不填补/平滑/裁剪。

原生文件为NETCDF3_CLASSIC：`year_day(int32,ndays,YYYYDDD)`、`f107d/f107a(float64,ndays,sfu)`、`kp(float64,ndays×8,1)`。每份只有21个日节点和168个Kp桶；不是把23,041个运行分钟节点写成新的数据格式。两份各2556 bytes，本地只读0444，均不提交GitHub。

F107A为每日前后40天的中心81日观测Fobs平均；运行时复用既有四日正午节点三次插值、三小时Kp中心线性插值。hpower/ctpoten在查询时由Kp派生，未添加为新的GPI变量：Kp≤7时power=16.82 exp(0.32Kp)−4.86，否则153.13+(Kp−7)(300−153.13)/2；ctpoten=15+15Kp+0.8Kp²。公式和HEELIS背景没有改变。未来真实驱动仅适用于HINDCAST，不代表可用于实时预报。

独立复核重新解析原始文件，用`math.fsum/81`、显式三次多项式权重、UTC时间中心括区和标量数学复算，未调用生成器的`arrays`或`GpiDriver`计算参考值。原门槛不变：中心均值绝对差严格<1e−12，运行驱动严格<1e−10。原始桶节点逐值相等，结构与2022春季已实跑GPI相同。

## 三、实际验收结果

| 项目 | 2021秋季 | 2022秋季 |
|---|---:|---:|
| Fobs原始支撑 | 07-29—11-06，101日 | 同月日，101日 |
| Kp/GPI原始支撑 | 09-07—09-27，21日/168桶 | 同月日，21日/168桶 |
| 候选模型区间 | 09-09 00:00—09-25 00:00 UTC | 同月日UTC |
| 运行分钟节点 | 23,041 | 23,041 |
| 额外边界秒节点 | 112 | 112 |
| 中心81日均值最大绝对差 | 1.4210854715202004e−14 | 2.842170943040401e−14 |
| F107d插值最大绝对差 | 2.842170943040401e−14 | 5.684341886080802e−14 |
| F107A插值最大绝对差 | 4.263256414560601e−14 | 5.684341886080802e−14 |
| Kp插值最大绝对差 | 1.7763568394002505e−15 | 8.881784197001252e−16 |
| hpower最大绝对差 | 5.684341886080802e−14 | 2.842170943040401e−14 |
| ctpoten最大绝对差 | 4.263256414560601e−14 | 4.263256414560601e−14 |
| 缺失/重复 | 0/0 | 0/0 |
| 驱动工程状态 | GPI_READY | GPI_READY |

GPI SHA256：

- 2021：`d401d0ae525babb343faaa6d1dd9a8d3c4fb1c2ea85beb26d2b0025cdf001b9a`
- 2022：`7d43db220fe7fbaded6b2182db8db32ee09cedf99dc5760815824ccf8298ebb2`

准确原生覆盖/合法查询域见`gpi_structure_comparison.json`：yearday_beg/end分别252/268，查询器按完整日判域，而本次计划积分只到第268日00:00。没有因此延长候选积分。额外检查正午、Kp中心、日界前后秒及越界拒绝，无日期/插值边界错误被发现。

原GFZ身份：2021归档`f969f23b0b0d4aba80dca6f35d3e95c2d35a7e482457bc1812e5c0827090caae`；2022Fobs `fcfd9d337597aeca2b59c79c189680f0363ca8bcddd3bdd88725f33ac3524744`；2022Kp `df6aff3f776881803f4d01227a8dd7593367d43271f50b43341b8297e6af99fb`。两份Swarm CDF以及ZIP/HDR SHA均与V21一致，见`preflight.json`和`asset_protection_after.json`。本轮不重新读取未来观测密度分布；V21各2880有效及各窗口样本证据只读复用。

17项CPU测试通过（2.887秒），含缺日、NaN/Inf/负Fobs、非法Kp、非def/重复时间、错误单位、日期偏移、均值及插值端点损坏、覆盖拒绝；并覆盖既有初态审查器的完整34状态合成正例、缺状态、非有限、错误网格/单位、非法初始化时钟。合成正例仅验证程序，不是实际sepeqx验收。

## 四、遇到的问题与官方初态获取

V21单文件403历史回执保留，本轮未重请求。项目文件名与45份归档的成员元数据检索未发现精确初态原件或匹配成员；未解压、反序列化权重。四个PyTorch`.tar`实际为ZIP容器，传统tar读取报错不意味着权重损坏，已另存元数据澄清。软件环境目录排除，不宣称检索了服务器其他项目。

[官方QuickStart](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/quickstart.html)说明下载流程需要邮箱、不需要账号密码，并列出约1.5GB的`tiegcm_res5.0_data.tar`；[官方目录说明](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/dirstruct.html)列出目标`tiegcm_res5.0_sepeqx_smax_prim.nc`。当前[下载入口](https://www.hao.ucar.edu/modeling/tgcm/download.php)经网页读取器仅解析出两个Input元素，不能据此证明表单交付仍正常。没有发现经核实、当前可成功获取的替代单文件入口；没有证明必须只能下载整包。许可/访问资格和当前交付需用户人工确认，不推断更多条款。

结论：**SEPEQX_SOURCE_NOT_ACQUIRED**。原生年/日/mtime、SOURCE_START、34状态及兼容性仍NOT_RUN，不能从文件名猜测。[人工操作说明](../docs/THERMOSPHERE_V22_SEED_ACQUISITION_AND_POLICY.md)列出官方入口、精确成员和导入要求。若用户已合法持有官方数据包，可另任务安全提取该成员；无需再次下载大包。官方Globus说明针对benchmark历史场，不能自动当作同一启动文件。

准备监督时`psutil`不可用，在任何worker启动前退出；随后使用只读procfs监测，未安装依赖。一次GPI生成worker监督5.414462秒，进程CPU5.235911秒；树峰采样57.797MiB，自进程高水位71.551MiB（采样可能错过峰值）。搜索另计1.144330秒，测试另计2.887秒。资源表不把交互会话耗时当CPU总量，也不把采样监控说成OS隔离。新GPI共5112 bytes；无原始数据下载，仅查询官方公开网页，网页工具不提供传输字节计量，未声称所有HTTP流量为0。

## 五、当前项目状态与A/B政策

| 路线 | 已有事实 | 合理性与比较限制 | 后续准入 |
|---|---|---|---|
| A：旧mareqx smax | SHA `a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7`，本轮header确认2002年第80日00:00、36×72×29网格，34状态历史证据保留 | 可控制初态来源；春分源的秋季适应性、14天候选预热充分性均未证；同SHA不消除两年真实驱动差异 | 用户显式批准季节风险，单独冻结配置；不能因403自动回退 |
| B：官方sepeqx smax | SOURCE_IDENTITY_PENDING，无实物 | 季节动机合理，但不能预称更准确；换源改变与春季B14背景身份。同季两年若采用须固定同SHA | 先合法取得，独立审查实际SOURCE_START/34状态/网格/数值，再用户批准 |

官方[季节benchmark说明](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/release/html/benchmarks.html)显示季节smax基准使用恒定太阳条件。这说明官方季节基准有其构造背景，不是2021/2022真实初始场；即便取得季节源，也存在向真实GFZ驱动适应的风险。不能将其benchmark日期范围推断为未取得文件的实际记录时间。

2021、2022分别为：Swarm与GFZ原件有效、GPI_READY、sepeqx未取得、初态政策未批准、14天充分性未证、原TIE-GCM程序身份仅历史复用；均非RUN_READY。本轮未改变物理源码、模型配置或评价协议。

持续保持SCIENCE_TRAINING_READY=False、EXTERNAL_DATUM_UNVERIFIED、Restart=FAIL、DART=NOT_ADMITTED、REAL_ORBIT=BLOCKED。驱动工程通过不等于密度科学验证通过。

## 六、下一步计划

先人工处理初态获取及A/B政策，再准备正式配置。推荐下一任务仅“合法导入精确sepeqx原件并只读审查，提供A/B政策审批依据”，不启动模型。如果用户明确选择A，也应显式记录该政策，不能混称季节初态已经取得。

政策闭合后，分别准备2021/2022独立16天配置，保持MPI4/OMP1、60秒、23040步，不使用Restart/append。历史每次估计40.05—40.77分钟/约3.14GiB；逐次拟申请4800秒、16GiB RSS、5GiB输出、启动余量25GiB/运行余量20GiB，实际资源审查届时重做。模型工程验收及冻结评价均另需授权，本轮停止。
