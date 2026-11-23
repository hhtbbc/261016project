# V34 TIE-GCM ZG 外部高度基准与 Swarm 坐标登记

**V34_EVIDENCE_REVIEW_COMPLETE · EXTERNAL_DATUM_UNVERIFIED · FIXED_OFFSET_NOT_ADMITTED**

## NCAR 文档与实物

2026-11-23 UTC 核查 NCAR 2.0 用户文档。高度章节由 Stan Solomon 于 2016 年 4 月编写，诊断页属于同一 2016 年 2.0 文档。V2.1 记录的官方模型树提交为 `da712811d925376ff8ef40ff64bda7cc070ca661`，运行身份另含 apex 覆盖层和 GNU12 兼容补丁。V34 核对 V33 固定的相关源码及两卷真实输出元数据。所核查的高度定义与实际输出一致。 [NCAR 网格与高度](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/grid.html) · [NCAR 诊断量](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/diags.html)

- 压力坐标为 `Zp = ln(P0/P)`，`P0 = 5×10⁻⁵ Pa`。5° 网格的原生接口从 −7 到 +7，间隔 0.5。第一个接口的物理高度由边界场确定。
- `Z` 是用常数重力 870 cm/s² 积分得到的模型位势高度（cm）。`addiag.F:calczg` 令底部 `ZG = Z`，向上以成分、温度和变重力积分得到几何高度（cm）。模型局部重力为 `g₀[ r₀/(r₀+h) ]²`，其中 `g₀` 和有效半径 `r₀` 随模型纬度变化。该半径的源码用途是拟合重力梯度。
- `cons.F` 的缺省背景底高约 96.37229 km；`lbc.F` 允许气候背景与潮汐改变 `z_lbc`。两年秋季 namelist 均配置了 GSWM 日潮和半日潮。内部的底部锚定已确认，文档没有给出锚点到 GRS80/WGS84 或其他地球参考面的登记。
- NCAR 建议定高插值使用几何高度。接口量使用 `ZG`；中间层可使用插值产生的 `ZGMID`。网格章把多数中性量概述为 midpoint，具体的总密度诊断 `DEN` 在文档、`diags.F` 和真实文件中均为 **ilev**，单位 g/cm³，调用者 `dt.F`。两个真实文件的 Z、ZG、DEN 均为 `(time, ilev, lat, lon)`。这是概述范围与具体诊断注册的差异，未发现相应的模型实现矛盾。
- `cons.F` 生成等距地理纬度，5° 单元中心为 −87.5° 到 +87.5°，NetCDF 记为 `degrees_north`。`getapex.F` 传递地理网格角给磁场辅助路径；该路径的椭球约定和球面网格索引本身都不足以判定本体的外部大地或地心纬度身份。3.0 的球面说明仅作线索，不作为 2.0 登记依据。

## Swarm A 0301

两天 CDF 的 `latitude`、`longitude` 分别为 geodetic degrees，`altitude` 为 m，时间为 UTC。VirES 的 `Latitude_GD`、`Longitude_GD` 指定 GRS80；页面把 `Height_GD` 误标为 latitude，冻结 HAPI 元数据单位是 m，原始 CDF 将其定义为 Altitude。三者共同支持在 Swarm 产品合同下，将其作为以 GRS80 椭球法线度量的高度使用。对高度字段的精确框架实现、参考点和不确定度仍缺产品修订级证据。 [VirES HAPI](https://vires.services/hapi/)

两份 HDR 均注明版本 0301、参考文件 `SW-DS-DTU-GS-0001`，并列出当日 `ACCAPOD 0401` 与 `MODA_SC 0504` SP3 输入。前者支持 POD 导出加速度的密度反演；后者给出可追溯的地理登记上游文件。ESA 的 MOD 产品声明其产品族使用 ITRF 和 SP3c。对应两天的 0504 文件头在项目内未定位，因此具体 ITRF 实现、历元、SP3 时间基准及产品算法中的卫星点位仍未独立核实。CDF UTC 采样、HDR 处理时刻与框架历元是不同字段。HDR 生成时间分别是 2024-09-25 和 2024-09-22，且没有运营发布时间证明。GNSS 轨道和空气动力反演的误差描述无法直接换算成位置高度误差或 ZG 的系统偏差。手册请求返回 406，保留失败记录，另以 ESA Swarm DISC 产品目录和本地原件交叉核对；未取得与本批次匹配的 L2 完整规范修订。 [ESA MOD 产品目录](https://swarm-disc.github.io/product-catalogue-tools/SW_MODx_SC_1B.html) · [POD 密度产品方法](https://research.tudelft.nl/en/publications/thermosphere-densities-derived-from-swarm-gps-observations/)

## 坐标链与适用条件

| 环节 | 操作和物理条件 | 证据结论 |
| --- | --- | --- |
| 原始 POD → 地固 XYZ | 使用准确 SP3 的头部、时间系统、实现和卫星参考点；公里转米，取同历元状态。不同实现如需对齐，应采用来源匹配的变换、速度参数与历元 | ITRF 产品族确认，两个具体 SP3 未验证 |
| 地固 XYZ ⇄ GRS80 地理坐标 | 对同原点、同轴、同框架的 XYZ，以 GRS80 椭球反解 `(φ, λ, h)`；从 CDF 可按公式反算 XYZ 作为几何重建 | 确定性椭球几何成立，观测框架实现仍须另查 |
| GRS80 → WGS84 参数表达 | Map-A 按相同 XYZ 改用 WGS84 椭球反解，取大地纬度及法线高。地心经纬用 `atan2(Z,hypot(X,Y))` 和 `atan2(Y,X)`；一般纬度值与大地纬度不同 | 现有 Map-A 数字可以复现；参数换椭球不会执行 ITRF 实现间时变对齐 |
| 外部地固坐标 → 模型水平角及 ZG | 需要模型零面、垂直量测方向、经度基准和纬度定义。有效重力半径仅属于重力公式 | 关系未闭合，Map-A 依旧 PROVISIONAL |
| 原生 ZG → DEN | ZG ×0.01 为 m；同接口 DEN ×1000 为 kg/m³。每列按高度插值 log 密度，时间与水平合成密度；八列均需合法包围 | V33 已验证原生数值路径，含零权重列 |

设椭球长半轴为 `a`、离心率平方为 `e²`、`N=a/sqrt(1−e²sin²φ)`。则 `X=(N+h)cosφcosλ`、`Y=(N+h)cosφsinλ`、`Z_cart=[N(1−e²)+h]sinφ`。该式可用于卫星源端控制点核验。只有当模型参考面及角度定义得到独立证实，才能继续做无需密度拟合的模型端登记。观测时间与变换参数历元需分别保存。

## 控制点与核验

起始本地和远端为 `4e1829b3bfaf99abc166db3a99893fc52be8f9f3`。独立脚本对照 V33 Git 清单与原始 SHA，重建四窗样本索引和 UTC 哈希，检查 CSV 的 240 个固定标识，并读取两原卷和两份 CDF/HDR 的元数据。源文件散列按字节核验；未解码 CDF 观测值、模型场值或重新计算梯度。320 项检查全部通过，涉及 152 个独立资产，包含 7 项准入门禁正反例。首次运行遭遇 Python 版本缺少 file_digest，第二次遭遇旧版 ISO 纳秒字符串解析限制。改为分块 SHA 和显式整数纳秒编码后全部通过，约 0.95 秒 CPU、58.7 MiB 峰值 RSS。

可复核 V33 的 240 个 Map-A 数值样本身份、既有包围和裕量。具备版本匹配外部物理映射的控制点目前为 0，本轮未执行任何新映射查询或新评分。无 GPU、TIE-GCM、AI、DART、传播、外部联络或新科研原始数据下载。

## 准入与 V35 决策

**路线 A，物理登记。** 可由用户提供 NCAR 2.0 权威定义或独立匹配控制点，至少说明 ZG 的绝对零面、垂直测量方向、下边界和 GSWM 如何继承同一基准、网格地理纬度登记、适用高度/纬度/时间和误差界。同时需要这两天的 MODA_SC 0504 SP3 头及 0301 的对应规范修订，核实参考框架、历元、时间系统、卫星参考点和处理链。控制点须包含 UTC、可追溯的地固 XYZ 与外部高度、独立的对应模型高度及不确定度。若证据齐备，先在冻结样本控制点上只读核对坐标、层位和八列共同域，再为另轮预注册转换和同 ID 对照。偏移常数只有在证据明确支持其物理含义和适用范围时才可采用。

**路线 B，受限统计研究。V35 推荐先走 B。** 下一轮首先冻结设计，原 Global 为必选基线。只在两年春季历史开发数据及两年秋季已评分开发数据上设计低参数收缩方案。把按整日外留的开发诊断与独立测试严格区分，保留夏冬未见目标。预先锁定候选、复杂度、超参数规则、相同观测 ID、无外推与失败条件，保持 V20 四项联合无退化标准。先做 CPU 截点/可用性与泄漏测试。真实历史样本时刻和实际发布时戳分别核验，无法证明截点可用时只允许声明事后 HINDCAST，实时分支应拒绝该输入。设计冻结后再另行授权实验。本轮没有开始统计方法训练。

没有必须现在处理的人工步骤。若已有上述来源，可并行推进路线 A；无需因此停下路线 B。当前保留 `SEED_POLICY=A_MAREQX_APPROVED`、`AUTUMN_ADAPTATION_UNVERIFIED`、`FOURTEEN_DAY_SPINUP_NOT_PROVEN_CONVERGED`、`EXTERNAL_DATUM_UNVERIFIED`、`Restart=FAIL`、`SCIENCE_TRAINING_READY=False`、`DART=NOT_ADMITTED`、`REAL_ORBIT=BLOCKED`。
