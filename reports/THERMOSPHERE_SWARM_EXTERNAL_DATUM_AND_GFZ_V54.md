# V54 · Swarm 来源、轨道坐标、模型外部高度与 GFZ 缺测审计

**V54_EXTERNAL_EVIDENCE_PARTIAL**。外部证据审计与独立数值复核完成。本轮新增两份 0301 的 ESA 精确官方目录条目、两个目标日的 MOD 在架版本、当前 GFZ 两日 API 原始响应、IGS SP3-c 规范以及 NCAR 和 VirES 文档快照。状态仍为 **OFFICIAL_PROVENANCE_UNVERIFIED / EXTERNAL_DATUM_UNVERIFIED / GFZ_2021_GAP_UNRESOLVED**。

## 历史身份与访问边界

起始本地、origin/main、远端 main 同为 `9d5b89b6d84b64e00b5d4d1fa82483c5de0a0bdd`。V53 的 16 项、V52 的 33 项发布文件及 V50 冻结清单逐项验 SHA。V51 的 94 卷及 V48 的 66 卷模型输出通过只读复核。V49 发布、V37 协议、上传及 accepted ZIP SHA、CDF/HDR SHA 均保持。保留 STATUS/WORKLOG 原有本地更改。

网络只请求公开说明、目录元数据及 GFZ 数据。请求字节和时间有上界，未追随重定向，未提交注册、条款或登录。ESA 页面明确说明产品访问意味着确认条款，停在目录核验，未请求产品下载。原始公开响应保存在服务器 `public_evidence/`，凭证 JSON 记录 URL、获取 UTC、HTTP、文件 SHA 和体积。GFZ 首轮新响应成功落盘，后处理误将 V38 字典当作列表；修正后使用这两份 V54 原始响应，时间以首次落盘记录，未臆造当次 HTTP 头。独立复核共校验 25 份实际公开响应和 14 项 CPU 测试。只读取 Swarm 经纬和高度，审计守卫在调用解码器前拒绝 density 与 density_orbitmean。没有读取 DEN 值、启动新模型、GPU、正式评分、校正拟合、AI、DART、轨道传播或外部联系。 [ESA 公开入口及条款](https://swarm-diss.eo.esa.int/)

## ESA 0301 目录与来源

ESA 档案 Sat_A 目录精确返回本地两份 0301 ZIP 的名称及字节数，并返回明确的存档条目时间戳。时间戳仅解释为目录修改属性。两份 0301 HDR 引用 `SW-DS-DTU-GS-0001`、当日 ACCAPOD 0401 与 MODA_SC 0504，也记录 SC_ADYN 0502 和 STRAATT 0504。2021、2022 HDR 分别于 2024-09-25 13:25:05 UTC 和 2024-09-22 18:11:15 UTC 生成。发布日期和版本变更日志尚未核实。VirES 目录和实际 /info 对应 Swarm A 的 POD 热层密度产品族，flag 0 为 nominal、1 为 anomalous，Height_GD 单位为米。型号族说明与本地字段相容。直达 ESA handbook 返回 406，目录链接的 L1b 规格与算法 PDF 返回 403。与 0301 实际处理版对应的 L2 规范修订未取得。 [ESA DNS 档案](https://swarm-diss.eo.esa.int/#swarm/Level2daily/Latest_baselines/DNS/POD/Sat_A) · [VirES 产品元数据](https://disc.vires.services/hapi/info?dataset=SW_OPER_DNSAPOD_2_) · [VirES 字段定义](https://disc.vires.services/hapi/)

| 目标日期 | 官方 0301 条目字节数 | 官方目录修改 UTC | 本地 ZIP SHA256 |
|---|---:|---|---|
| 2021-06-21 | 140229 | 2024-09-26 07:23:11 | `eb94bafaf753c1986ff610caf10d03bea361f2a8c1f248eaa5c67f702cb2a48a` |
| 2022-06-21 | 138722 | 2024-09-23 21:39:04 | `c899ddab110a82e65c70531acba396149ac156dbc267459a99a3566d1c84c23c` |

现已取得独立官方目录登记。字节认证仍欠官方校验和、签名或合规重取的同一交付件。目录的名称、体积、时间不足以认证本地字节。可由账户持有人按网站要求完成授权及下载，并交接不含认证信息的收据和同版原件，或提交与精确条目关联的官方校验和。账号、密码、Cookie、签名链接和访问令牌无需交接。

## 对应轨道和坐标

从原生 HDR 逐字提取的参考文件：

- `SW_OPER_MODA_SC_1B_20210621T000000_20210621T235959_0504.sp3`
- `SW_OPER_MODA_SC_1B_20220621T000000_20220621T235959_0504.sp3`

本地有界检索未找到精确文件。官方 `Latest_baselines` 与 `Entire_mission_data` 两目录的目标日页都只列 0601，2021 日包 4,333,349 字节、2022 日包 4,330,938 字节。该结论仅覆盖实际查询的公开页，旧版仍可能由 ESA 归档另行交付。未下载 0601 或任何 SP3，未以不同产品替代。 [ESA MOD 产品目录](https://swarm-disc.github.io/product-catalogue-tools/SW_MODx_SC_1B.html) · [ESA 完整任务轨道目录](https://swarm-diss.eo.esa.int/#swarm/Level1b/Entire_mission_data/MODx_SC/Sat_A)

**SP3_FORMAT_DOCUMENTED / SP3_EXACT_PRODUCT_NOT_ACQUIRED**。ESA MOD 属于 ITRF 地固的中精度轨道产品，采用 SP3-c。SP3-c 标准约定 XYZ 位置为 km，速度为 dm/s，头部独立声明 frame、首历元、间隔和时间系统。VirES MOD 元数据是已改成 UTC 和 ITRF 球坐标的派生输出，不能作为历史 0504 头。两份具体 0504 的时间系统、采样粒度、ITRF 实现、框架参考历元及质心或天线参考点均待确认。任何参考点修正都要有产品定义、对应姿态和原点偏移证据。同历元真实轨道与 CDF 配对样本数为 0，时间差、残差 P95/最大值及实际轨道误差界均不可报告。 [IGS SP3-c 标准，2010-08-17](https://files.igs.org/pub/data/format/sp3c.txt) · [VirES MOD 派生元数据](https://disc.vires.services/hapi/info?dataset=SW_OPER_MODA_SC_1B)

暂按产品族支持的 GRS80 法线高解释，把两年共 5,760 个真实 CDF 几何点转换为 XYZ，再交叉验证 ERFA 与独立迭代法。另有 5 个合成控制点，含两极及经度边界。真实轨迹输入上的独立迭代 XYZ 往返最大值为 2021 **3.40e−9 m**、2022 **3.73e−9 m**，P95 分别 **1.92e−9 m、1.93e−9 m**。独立高度最大往返误差均约 **2.79e−9 m**。保持 XYZ 不变，仅改用 WGS84 参数时，高度改变量最大 **约 0.105 mm**。大地／地心纬度差最大 **0.1801°、0.1794°**。ERFA 闭式反解加独立正算的 XYZ 回代最大约 **5.54e−7 m**。这些是数值验证结果，外部轨道与 datum 误差没有由此得到约束。

## TIE-GCM ZG 外部定义

- `addiag.F:161` 以 `z_lbc` 为底层 Z，按常重力建立位势高度。 `addiag.F:267` 给出 **ZG(底接口)=Z(底接口)**。`lbc.F:110–136,153–159` 提供背景状态或默认 zbound 及 GSWM 水平和时间扰动。`cons.F:315` 的默认背景底高约 96.37229 km。底边界是模型输入和内部锚点，外部 ZG=0 的球面或椭球身份没有独立证据。
- `addiag.F:254–273` 将温度、组分平均质量和纬度依赖的变重力用于接口几何高度积分。有效重力半径用于拟合重力梯度，按实码赤道约 6334.94 km，87.5° 约 6377.74 km。它不是已有证据证明的地理基准半径。主网格由 `cons.F:551` 给出等距地理角度，5° 网格纬度中心 ±87.5°。源码及文件明确地理网格，但缺少本体纬度与外部大地／地心定义的明确登记。
- 真实 V51 A/B 目标日每组 25 帧、64,800 个底接口值上，Z 与 ZG 完全相等，底高 **95.784–97.003 km**；独立再次检验两个完整 24 帧卷共 124,416 个底接口值。Z、ZG、DEN 维度同为 time×ilev×lat×lon。ZG cm、DEN g/cm³。原生垂直质量、温度和重力决定内部高度场，低边界与潮汐可随时间及位置变化。该验证表明内部锚点实现成立，未引入任意高度偏移，也未建立外部零面。
- 独立外部高度控制点数 **0**，外部物理误差上界 **未知**。V53 ZG 八列数字包围仅作为内部工程覆盖证据。外部 provider 仍拒绝未登记高度。 [NCAR 2.0 网格与高度](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/grid.html) · [NCAR 2.0 诊断字段](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/diags.html)

独立控制点设计分两关。先使用精确 0504 SP3 和配套产品说明，在冻结闰秒及已知参考点下作同 UTC 交集、明确 km→m、核对是否需框架/参考点变换，再从原坐标反解 GRS80 并汇报纬、经、高残差和覆盖。其次要求 NCAR 2.0 权威给出物理零面、垂直方向、角度定义和真实下边界配准，并取得独立的同时间地固 XYZ↔原生模型高度控制点。按纬度、时间及高度分层，事前冻结控制点和域，记录原始误差和最大值。高度预算应分列轨道、时间配对、参考点、框架、零面、坐标与插值误差。未知关键项不能置零；在未证明独立性时使用保守上界求和。没有这类证据前继续外部门禁。

## 2021 GFZ 记录

按 GFZ 官方 API 两个独立日窗请求 Fobs，2021-05-09 与 2021-06-16 均为 **−1.0 sfu 缺测码**，原始响应 SHA 与 V38 完全一致。UTC 00:00 是服务日标签，不是遥测观测时刻。GFZ 格式说明分别定义 DRAO/NRCan 的本地正午 observed 与 adjusted 值。被冻结的 GFZ 年表两日 Fobs 和 Fadj 均为 −1，D=2 是 Kp/SN 字段的状态。独立年度复查 HTTPS 档案尝试返回 404，年度 FTP 路径的 HTTPS 探针 TLS 握手超时，年度新文件未获得。当前可确认的更新状态来自实际 GFZ API。 [GFZ 数据与 API](https://kp.gfz.de/en/data) · [GFZ 年表格式](https://kp.gfz.de/app/format/Kp_ap_Ap_SN_F107_format.txt)

V39 原件证据仍成立。05-09 加拿大原表无当日行。06-16 有 17Z observed 76.9、23Z observed 77.1 sfu，20Z 无记录，adjusted 为 79.4 和 79.6 sfu。NOAA 两日整数汇编值 76 sfu 缺少逐日原仪器时刻、精度和质量来源。若改用其他观测时刻，可能改变日值和预热驱动，跨来源日值映射需另行验证。**决策 C**，两日均未取得同定义官方 observed 更新。06-16 异时刻观测可作 B 类研究证据，单日候选不足以消除双缺口。没有写 GPI 或替代原值。 [加拿大 NRCan 原始档案入口](https://www.spaceweather.gc.ca/forecast-prevision/solar-solaire/solarflux/sx-5-en.php) · [NOAA 日汇编原表](https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/annual_reports/daily_solar_indices_summaries/daily_solar_data/2021Q2_DSD.txt)

## V55 最短路径

优先让 GFZ/DRAO 确认 05-09、06-16 是否存在符合现行定义的观测修订，因为这是 2021 正式积分的前置硬门槛。同时准备独立的高度登记证据，因它也是正式评分的硬门槛。用户可在 ESA 开放条款允许的浏览器会话中取得两份 DNS ZIP 的可信交付记录，并向 ESA 归档团队询问两个精确 0504 旧版文件及匹配 L1b/L2 规范。当前公开页面的 0601 可留作来源线索，不用其替代 0504。若公开资料仍无外部定义，请 NCAR 明示 2.0 ZG 零面、垂直方向及下边界基准，附可独立复核的控制点。此前外部咨询材料保持草稿；本轮未发邮件。

V37 准入逐项见 CSV。观测字节、内部身份、采样、2022 官方驱动及历史规则已核验。仍须取得来源、坐标与独立高度证据、解决 2021 驱动并批准共用种子和冻结输入，随后经逐阶段授权按 2021→2022 完成工程验收、两截点历史冻结与未来毒化、共同样本及正式一次性解封，最后独立科学复核。使用异源值或更改日期等政策须在标签封存时作前瞻审查和用户审批。V51 工程结果、V52 科学态与原科学门禁保持。
