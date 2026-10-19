# TIE-GCM 2023跨日与Restart验证：静态阻碍报告

## 结论

**本次0次模型启动；跨日与连续/分段一致性均未验证。** 用户允许最多3次，不代表必须消耗3次。静态检查发现原始源码不接受现有初始场与目标23:50组合，因此没有运行一个明知会失败的MPI任务，也没有扩展授权范围生成额外初始场。短例已有35项测试不等于Restart验证；本次全套42项测试通过仅包含静态/比较算法新增测试。

本次状态/配置草案/容差在experiments/tiegcm2023_restart_static_v1/{static_audit,comparison_rules,tolerance_sensitivity}.json。run_tiegcm2023_restart_validation.py是**静态准备入口，没有模型启动功能**；不能把该脚本存在当成三段执行器已完成。未来拿到合法状态后仍需完成受限执行及逐段审计入口。

## 决定性的源码约束

third_party/TIEGCM2.0/src/input.F第948—960行（原始未改）：

```fortran
if (start(2,1) /= source_start(2) .or.
    start(3,1) /= source_start(3)) then
  ...
  call shutdown('START')
endif
```

注释明确小时/分钟必须相同，只有日可以不同。现有2002春分restart只有mtime=(80,0,0)，year2002。SOURCE_START=80 0 0与目标START=77 23 50违反该条件；改成SOURCE_START=80 23 50虽然满足时钟检查，但文件中没有这条记录，rdsource/nc_rdhist仍然不能读取。前次00:00→00:10成功只验证了同UTC时刻、不同年月日的重新初始化，不能推导为任意UT都可重定位。

扫描全部data/experiments的13个带mtime的NetCDF：没有任何23:50完整主历史；默认2002单日主历史仅00:00和次日00:00，次历史虽有23:00等小时场，也没有完整_NM状态。清单logs/tiegcm2023_restart_inventory.json。未改时间标签、未用次历史拼接物理场、未造_NM、未跳过源检查。

## 资产与资源检查

可执行、2023 GPI、原2002场SHA均与已通过首次诊断的preflight一致，logs/tiegcm2023_restart_asset_check.json。GPI完整覆盖DOY77/78及日插值边界；未下载或重装环境。静态审计保存实时空闲盘和MemAvailable。本次运行许可预算90s/启动、总512MiB输出、RSS16GiB、余盘20GiB已记录。

理论三段输出约260MiB（依据约17MB主历史一帧、约8MB次历史一帧，加余量），原十分钟实测约2.4s，20分钟预计数秒。它们均是**估算**；本次阻碍是初始记录，不是已观察到的资源不足。尚无实际模型资源/稳定性指标。

## 完整主历史与正确续算路径

nchist.F 1826起为primary写全部nf4d_hist，float64；2257及2275附近注明主历史始终双精度、_NM为n−1时间层。fields.F注册TN_NM/UN_NM/VN_NM/O2_NM/O1_NM/N4S_NM/NO_NM/OP_NM/HE_NM/AR_NM；再保存TLBC/ULBC/VLBC及_NM下边界。结构检查包括当前TN/UN/VN、主要成分及离子/电子状态、OMEGA/Z/POTEN、十个_NM和六个下边界变量，共34项。N2是诊断组分，不以其缺席判定原始prim不完整。

现有2002文件的主历史类型、34项变量和float64结构合格；这仅证明结构与原完整restart相符，**不证明某个未运行续算数值正确**。选中year/day/mtime、lev/ilev、UT、时间属性、变元值/mask/哈希仍须在真正checkpoint产生后逐项检查。

原代码分两条路径：

- 显式SOURCE/SOURCE_START：rdsource.F 45—50只读指定记录，属于initial/new-source路径；hist.F 210—218设置新的initial_year/day等。可合法读取完整主场，但不得仅因读取成功就认为等同原生continuation。
- 省略SOURCE：rdsource.F 53—64从OUTPUT搜索START记录，并以reopen_append=.true.打开；nchist.F 479—488仅在nsource<=0时读取原initial_year/day/mtime，保留起始时间基准。这是严格续算的优先源码支持路径。

未来B2应在独立目录使用**完整B1 prim的字节相同副本**作为OUTPUT、校验复制前后SHA后走官方continuation；原B1 checkpoint保持不变。整文件快照供官方读取与手工复制/拼接变量、补造_NM不同，不能用于绕过本次23:50缺记录的问题。此处仅设计，未复制任何不存在的B1产物。

## 三段草案及执行门禁

A：2023/77、START77 23 50→STOP78 0 10（20步）。B1：同起点→78 0 0（10步）。B2：2023/78、START78 0 0→78 0 10（10步），原生continuation。共同5°/STEP60/4rank/HEELIS/GPI、禁固定F107/F107A/KP/POWER/CTPOTEN及_TIME；主次历史5分钟输出。

A/B1目前同受23:50源记录缺失阻碍。B2必须等A/B1静态和输出基础审计通过、B1 midnight完整checkpoint与A同历元主状态一致、其_NM/下边界/时标/驱动核验通过后才能运行。本次不保存可误用的非法namelist，保存明确DRAFT_NOT_RUN草案JSON；没有实际配置/运行日志或NetCDF结果可供冒充。

## 预注册比较与敏感性

comparison_rules.json在模型运行前冻结，统一SI：DEN×1000、ZG×0.01、风×0.01；时间和网格必须精确对齐，原始字段单位严格核对。同历元数组shape一致后，显式按dtype处理已知填值，mask必须相同；任何NaN/Inf失败。报告最大绝对/最大相对/RMSE、非有限数、共同有效比例和mask失配数；相对值分母为|reference|，零参考另计、不偷偷加任意地板。

float64 rtol1e-10、float32 rtol1e-6；SI atol：TN1e-8K、风1e-8m/s、ZG1e-5m、DEN1e-25kg/m³、质量混合比1e-12。判据max|delta|/(atol+rtol max(|A|,|B|))<=1。内部其他状态需按自己的真实单位扩展门槛，不能随便套用温度容差。

依据已有2002重复运行，双精度TN差约3.07e-12K、风约1.29e-12m/s。预设阈值有舍入余量且仍非常小；float32相对阈值约8.4 eps。tolerance_sensitivity.json用代表量级计算nextafter单ULP，检查预设门槛能容纳单精度量化；这只是**算术敏感性**，未做MPI数值敏感性传播实验。真正运行后如明显偏差必须调查初始化重执行、时间错位、leapfrog/未保存内部状态或MPI，不得事后调大容差。

新增7测试：源小时不匹配拒绝、仅日不同允许、原prim结构与缺23:50记录、手算误差/单位、NaN及mask不一致失败、shape/零参考、明显状态偏差失败。全套42项6.763s通过，logs/tiegcm2023_restart_all_tests.log。没有为假装比较成功创建空白误差CSV或零差图；连续/分段DEN/ZG/TN/风/成分的真实误差均N/A。

## 后续与停止

优先取得合法23:50完整主历史，再按原3启动预算准备执行器。若只能由现有00:00初猜生成，则需**额外一次准备运行**：建议2002默认场00:00→23:50、1430步、4rank，只保存完整主历史初末两帧，预期约34MB；依据旧默认单日152.25s估计约151s，建议另申请300s墙钟上限。它超过本次3次启动/90s限制，故未执行，也不称为2023spin-up。未来确认原配置与输出预算后再实施；之后A/B1同取生成的23:50初猜，仍是工程实验，不是2023平衡场。

本次没有跨日驱动/状态连续性/稳定性结果，不建议宣布具备正式多日spin-up条件。Swarm顶高/高度基准、气动参数和机动风险未解决。已保留以前实验，记录并同步本次静态阻碍，等待下一条指令。


## 仅输入推导的跨日驱动期望（不是仿真结果）

results/metrics/tiegcm2023_restart_expected_drivers.csv列出23:50—00:10的21个UTC分钟：太阳f107d/f107a按正午锚定四点三次Lagrange，Kp按前日22:30与次日01:30之间线性插值，POWER/CTPOTEN按实际util.F。03-19零点期望F107=141.04375sfu、F107A=161.755015432099sfu、Kp=1.5、POWER=22.3223714448845GW、CTPOTEN=39.3kV。CSV每行scope都明确input-derived expectation only; no model run。这些值只供未来核对，不能宣称模型实际读到它们或跨日已通过。
