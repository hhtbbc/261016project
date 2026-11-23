# V39 夏季原件交接与准入

**V39_ASSET_PARTIAL · RUN_READY=False**

起始 HEAD 和远端 main 均为 `26a28cfbe8ce2e05ba15755618ca411bf841579e`。V38 22 项已发布文件及 4 份本地 GFZ 原始响应的 SHA 一致，V37 10 项清单也一致。服务器持久化工作区未发现三份目标原件，交接目录实际为空。V39 没有重试旧二进制地址、重新查询缺测日或重下已验 2022 GFZ。

## 官方路径与实际结果

| 项目 | 2026-11-23 UTC 核查 | 结果 |
|---|---|---|
| ESA Swarm 根站 | 公开入口探针超时。复用 V38 精确 ZIP URL 的两轮超时收据 | 两份 ZIP 均未取得；不存在确认的 HTTP 状态码。超时阶段不足以区分代理、路由、TLS、服务端等待或后续认证 |
| NCAR junsol | 公开下载页显示表单输入，未提交。保留 V38 精确单文件 HTTP 403 | 未取得。真实 34 项状态、SOURCE_START、原生年月日和时钟、工程兼容性均未知 |
| NCAR 交付说明 | QuickStart 给出邮箱流程、约 1.5 GB 的 5° 数据包。目录说明将目标文件列在 TGCMDATA 下 | 未确认当前可交付的单文件或 tar 的精确内部前缀；整包未下载 |
| NCAR Globus | 官方文档介绍 benchmark 输出的文件传输 | 未证实其中提供同一 5° startup 文件，不将输出历史冒充初始场 |

ESA 的 Swarm 官方说明列出浏览器获取、EO Sign In 和产品条款。未建立已认证的 ESA 会话，未猜测两份 0301 的当前远端可用性。NCAR 2.0 模型的学术研究许可另有条件，实际数据交付和使用条款由提供方确认。没有提交个人信息、使用他人凭据、访问第三方镜像或自动接受条款。 [ESA Swarm Data Access](https://lps25.esa.int/lps25-presentations/presentations/305/_305.pdf) · [NCAR 下载入口](https://www.hao.ucar.edu/modeling/tgcm/download.php) · [NCAR QuickStart](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/quickstart.html) · [NCAR 初态目录](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/dirstruct.html) · [NCAR 2.0 许可说明](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/release/html/release_notes.html)

## 2021 缺测来源证据

重新核验本地保存的 56,001 字节加拿大官方原表连续片段、NOAA 2021 Q2 DSD 及 GFZ 年表 SHA。V38 对 GFZ 两日的 `−1` 实测响应保持。公开资料查阅确认 observed、adjusted 与 URSI 分列；本轮未发现可以纳入 V37 的正式 GFZ 修订。

| 日期 | GFZ Fobs | 加拿大观测原表 | NOAA SWPC DSD |
|---|---:|---|---:|
| 2021-05-09 | −1 | 缓存连续片段中 05-08 后直接到 05-10，无当日行 | 76 sfu |
| 2021-06-16 | −1 | 17:00 UTC observed 76.9 sfu（adjusted 79.4），23:00 UTC observed 77.1 sfu（adjusted 79.6）；20:00 缺行 | 76 sfu |

04-26 至 06-24 范围内，存在唯一加拿大 20:00 observed 原记录且 GFZ 有效的 **58/58 日逐值完全一致**。这支持两份缓存对普通日期的对应关系，不能推定 06-16 缺失的 20:00 读数。NOAA 日汇编给出的整数 76 无当行独立原仪器记录和质量细节，既有重叠对比未通过等价门槛。历史 CelesTrak 05-09 的 `INT` 属插值。加拿大 06-16 是真实观测候选，但更换观测时刻或供应商会改变输入定义，且 05-09 仍无同口径原始观测。保持 `GFZ_BLOCKED`，不写入任何正式驱动，不建议现在仅凭这些候选申请修订。若以后拟采用异源数据，须在解封目标前取得两日可辩护的原始证据，另行进行前瞻性协议审查与授权。 [加拿大官方观测档案](https://www.spaceweather.gc.ca/forecast-prevision/solar-solaire/solarflux/sx-5-en.php) · [观测、订正及单位定义](https://www.spaceweather.gc.ca/forecast-prevision/solar-solaire/solarflux/sx-3-en.php) · [NOAA Q2 DSD 原始文件](https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/annual_reports/daily_solar_indices_summaries/daily_solar_data/2021Q2_DSD.txt)

## 三份文件的人工交接

1. 从 ESA Swarm 归档入口使用自己的 EO Sign In，按网站提示处理条款。在 `Level2daily/Latest_baselines/DNS/POD/Sat_A` 下找精确文件；若当前只展示其他 baseline，保留失败或请 ESA 支持确认 0301 归档，切勿替换版本。
   - `SW_OPER_DNSAPOD_2__20210621T000000_20210621T235930_0301.ZIP`
   - `SW_OPER_DNSAPOD_2__20220621T000000_20220621T235930_0301.ZIP`
2. 在 NCAR 官方入口自行填写邮箱（如提示），请求 **`tiegcm_res5.0_junsol_smax_prim.nc`** 官方发布单文件及来源说明。若只提供约 1.5 GB 整包，先确认获取授权或向提供方请求单独交付；本轮不会下载整包。
3. 将原始文件放到 **`data/raw/thermosphere_summer_data_handoff_v39/staging/`**。建议为每份提供 `<原文件名>.source.json`，包含无凭据的 HTTPS `download_url`、`YYYY-MM-DD` 的 `download_date`、`source_note`，可选 `file_sha256`。请勿放账号、邮箱、令牌或签名访问链接。需要保留下载服务提供的发布版本、校验和来源时，将其公开引用写入说明。
4. 从项目根运行：

```bash
source scripts/activate_tiegcm.sh
CUDA_VISIBLE_DEVICES='' python -B scripts/import_summer_handoff_v39.py --inspect
CUDA_VISIBLE_DEVICES='' python -B scripts/verify_summer_handoff_v39.py --accepted-only
```

通过静态审查的副本原字节保存在 `accepted/<原文件名>/`，文件只读。staging 不覆盖、不移动原上传。接受标准包括类型、上限、SHA、同名冲突拒绝、ZIP CRC/安全成员、CDF/HDR 身份、允许字段的 UTC 与坐标/标志、或夏至单主记录的 34 状态/网格/时钟。工具只允许读取五个观测变量，目标密度和轨均密度禁止解码。生成的 receipt 明确区分 **BYTE_INTEGRITY_VERIFIED**、**PRODUCT_IDENTITY_VERIFIED** 与 **OFFICIAL_PROVENANCE_VERIFIED**。后者需要独立发布方证据；用户声明和自行计算的 SHA 只保留为交接线索。当前可信发行方 SHA 清单为空，任何静态接受都不会自动具备官方来源或科学运行准入。

## 验证和下一阶段

40 项 CPU 测试全部通过，含 31 项已冻结规则回归和 9 项新增交接测试。新增端到端使用完整的合成 ZIP/CDF/HDR，独立拦截变量访问，确认观测密度未被读取，并检查重复、同名冲突、只读副本和来源分级。真实已交接资产独立复核数为零。程序无模型、GPI、input、GPU、评分或目标解封路径。独立测试和来源核验约 0.38 秒、峰值 RSS 约 76.1 MiB。

| 日期 | GFZ | Swarm | junsol 与政策 | 准入 |
|---|---|---|---|---|
| 2021-06-21 | BLOCKED，99/101 Fobs、168/168 Kp | 未取得 | 未取得、政策待审 | SUMMER_ASSET_BLOCKED |
| 2022-06-21 | COMPLETE，101/101 Fobs、168/168 Kp、21/21 中心窗 | 未取得 | 未取得、政策待审 | SUMMER_ASSET_PARTIAL |

既有可执行文件 SHA 再验通过，仅为复用候选。V40 优先验收三份人工交接原件，核对独立官方来源凭据。即便三份齐备，**2021 两日 GFZ 缺测和夏季初态政策仍不会自动解除**。保留 2022 驱动；不跳过 2021、不切换冬季、不冻结模型配置。V37 日期、Raw/Global、固定 λ=0.5、所有目标封存及原科研门禁保持，Map-A 仍为 PROVISIONAL/HINDCAST。
