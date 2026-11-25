# V44 NCAR 夏至初态真实验收

## 原件和验收

**V44_JUNSOL_ACCEPTED_VERIFIED / JUNSOL_SEED_STATIC_COMPATIBLE。** 2026-11-25 接收根目录 `tiegcm2.0_res5.0_data.tar`。原件为普通文件，mtime 07:00:23 UTC；复制前后 inode、长度、mtime 和 ctime 一致。实际 **1,565,061,120 字节**与 NCAR 既有 HTTP 长度一致。可用空间约 1,247 GiB。以支持 reflink 的复制命令写入临时文件，分别计算 SHA 后原子发布只读副本到 `data/raw/thermosphere_ncar_junsol_acquisition_v40/`，保留了上传原件。

- TAR SHA256 `d93c93886ad7fc8ef5c1505168f782ed204b666b6f9d89bd873b7313aa15300f`。V40 扫描 35 条目录项和归档终止块，完整性及安全检查通过。
- 唯一提取成员 `tiegcm_res5.0_data/tiegcm_res5.0_junsol_smax_prim.nc`，普通文件，**16,993,144 字节**，在现有 20 MiB 限制内。
- 成员、暂存文件、接受文件及独立 GNU tar 标准输出的 SHA256 一致，均为 `baed93b59dee7f8e6355c8d0224bd2335cf355bd0d632c9d2327aa7d0227475e`。
- V39 静态验收、V39 接受文件独立核验和 V40 原生复核均通过。文件身份与用户来源声明、既有官方长度相符；NCAR 发布 SHA 无独立认证，官方来源独立证实仍未完成。

## 原生身份

| 项目 | junsol smax | mareqx smax |
|---|---|---|
| 单条 primary 记录 UTC | 2002-06-21 00:00:00 | 2002-03-21 00:00:00 |
| year / day / mtime | 2002 / 172 / [172,0,0] | 2002 / 80 / [80,0,0] |
| SOURCE_START | 172 0 0 | 80 0 0 |
| 原生 f107d / f107a | 200 / 200 sfu | 200 / 200 sfu |
| 发行和网格 | 2.0 数据包身份；文件属性 tiegcm_trunk、SVN 1249；36×72、lev/ilev 各 29 | 原生属性、网格、34 项状态维度及单位匹配 |

junsol 为 NETCDF3_CLASSIC，history_type=primary、run_type=initial。原生时间坐标 28800 分钟，基准为 2002-06-01 00:00。34/34 必需状态通过；有效值有限，填充布局与 mareqx 相同。TN 有效范围 153.026–1564.340 K；完整变量、单位、有效计数、填充计数及极值见提取收据。初态原件不含诊断 DEN，两份旧新初态均如此；不能据本验收声称已验证积分输出密度。现有 ELF SHA 及动态解析到的 NetCDF-Fortran 库 SHA 与冻结清单一致，静态接口匹配。本轮无实际模型读取验证。

## 待批政策及准入

**SUMMER_SEED_POLICY_B_JUNSOL_PROPOSED**。建议两年夏季使用同一已验 junsol SHA 和原生 SOURCE_START，保留各自真实 GFZ 驱动。夏至初态在季节身份上与夏季实验更直接对应，原秋季 mareqx 条件不变。两年采用同一文件在静态工程上可行。14 天预热充分性和外部 ZG 基准仍未证明；后续如要判断初态敏感性，需另行授权同年同驱动的配对 CPU 检验。

2022 GFZ 与候选 GPI 已通过工程验收，仍待初态政策批准和正式配置授权；ESA 观测原件仍缺。2021 的 05-09、06-16 Fobs 缺口未变。ESA 两份 ZIP 均未交接。V37 的 2021 优先顺序、方法和 λ=0.5 保持。两年 RUN_READY=False。本轮未下载、未读取未见目标密度、未生成正式 GPI/input、未启动 GPU、TIE-GCM、AI、DART 或轨道传播。下一轮优先审阅并决定 junsol 政策，同时接收 ESA 两份 0301 原件并解决 2021 GFZ 缺口。
