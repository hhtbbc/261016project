# V42 夏季原件交付与 GFZ 只读工程预检

## 结果

**V42_PARTIAL**。2022 驱动接口通过。NCAR 等待合法交付，ESA 两份原件均未取得。两年份 RUN_READY=False。起始 HEAD 与远端 main 均为 `def64e24e26d56b2c027797eca9526b2bf78fbb2`。V37–V41 五份发布清单与基线 Git 对照，53 个条目经 SHA256 前后复核，包括 V38 四份本地原始响应。保留本地既有修改与未跟踪文件。

| 日期 | GFZ | ESA 0301 | 夏至初态与配置 |
|---|---|---|---|
| 2021-06-21 | GFZ_BLOCKED。99/101 Fobs，168/168 definitive Kp；05-09、06-16 仍为 −1 | NOT_ACQUIRED | junsol 未取得，政策待审 |
| 2022-06-21 | GFZ_PREFLIGHT_VERIFIED。101/101 Fobs，168/168 definitive Kp，21/21 中心平均 | NOT_ACQUIRED | junsol 未取得，政策待审 |

## NCAR 合法服务器交付

`NCAR_AWAITING_DELIVERY`，细项 `NCAR_SERVER_DOWNLOAD_AWAITING_AUTHORIZED_DELIVERY`。V40 实测登记入口 HTTP 302 至官方邮箱登记页。V42 沿用该证据。服务器交接区未见 TAR、.part 或 junsol。Chrome 下载继续由用户控制。

服务器若另行下载，需 NCAR 授权可用于服务器的最终文件交付及二进制响应；浏览器交付是否绑定 Cookie 或会话尚未核实。不要在聊天或 Git 分享授权 URL、Cookie 或凭据。V40 下载器只支持既定公开 URL 和允许的官方交付路径；若官方提供独立授权且需要新传输方式，先在服务器私有渠道审核其授权和响应合同。HEAD 核验类型、长度及可见的附件名称。可用空间约 1250 GiB，超过 5 GiB 门槛；正文限 2 GiB。续传要求同 URL、同字节长度、同强 ETag、byte ranges 和精确 206 Content-Range，真实交付的对应响应头目前未取得。合成测试验证 HTML 拒绝、版本变化拒绝和续传的长度检查。

现有 Chrome 下载完成后，把完整未改写的 `tiegcm2.0_res5.0_data.tar` 上传至 `data/raw/thermosphere_ncar_junsol_acquisition_v40/`。可沿用 [V40 单成员提取、静态验收与独立验收命令](THERMOSPHERE_NCAR_JUNSOL_ACQUISITION_V40.md)。保留公开来源、实际交付日期和官方校验和（若有）。本轮 TAR 与成员大小、SHA、34 项状态及原生 UTC 均待核验。

## ESA 官方原件

归档首页仅做一次有界 HEAD。curl 28，DNS、TCP 和 TLS 完成，TLS 约 1.48 秒，12 秒内收到 0 字节，HTTP 状态 000。当前路径无法确认这两份 0301 的目录可用性、实际身份或下载方式。ESA 资料介绍 EO Sign In 及 HTTP/FTP；精确条目仍需在归档核实。两份 ZIP 均未交接，保留未见目标密度封存。[ESA Swarm 归档](https://swarm-diss.eo.esa.int/) · [ESA 数据分发说明](https://lps25.esa.int/lps25-presentations/presentations/305/_305.pdf)

1. 用能访问 ESA 的浏览器打开归档。若页面要求，使用自己的 Earth Online Sign In，在官方页面处理条款。
2. 进入 `Level2daily/Latest_baselines/DNS/POD/Sat_A`，按日期核对并只下载下面两个精确 ZIP。若仅出现其他 baseline，向 ESA 归档支持询问这两个精确 0301 产品的官方交付。
   - `SW_OPER_DNSAPOD_2__20210621T000000_20210621T235930_0301.ZIP`
   - `SW_OPER_DNSAPOD_2__20220621T000000_20220621T235930_0301.ZIP`
3. 将原始 ZIP 和不含凭据的来源说明放入 `data/raw/thermosphere_summer_data_handoff_v39/staging/`。随后运行 V39 `import_summer_handoff_v39.py --inspect` 和 `verify_summer_handoff_v39.py --accepted-only`，校验 CRC、HDR/CDF、UTC、坐标、质量标志及 SHA。

## 2022 驱动预检

三份 Fobs 原件分别贡献 24、70、7 日。逐日 UTC 覆盖 2022-04-26 至 08-04，Kp 为 06-05 00Z 至 06-25 21Z，每三小时一个 definitive 桶。Fobs 使用 sfu，Kp 无量纲。生产数组仅在内存构建，独立路径用 Decimal 重算中心 81 日均值，最大差 2.842170943040401e-14 sfu；2022-06-21 Fobs 138.7 sfu，中心平均 126.175308642 sfu。候选 16 天区间为 06-07 00Z 至 06-23 00Z，模型日历 2022158 至 2022174，若 STEP=60 则共 23040 步。

V22 秋季入口与本地 Fortran gpi.F SHA 已绑定。后续适用公共 GFZ 数组与写入逻辑；夏季需要独立入口和配置冻结，不能直接执行秋季专用 CLI。合成 NetCDF 临时夹具检查两端填充、午夜 Kp 插值与桶中心约定、越界及 24:00 拒绝。临时夹具已移除。15 项 CPU 测试通过，墙钟约 0.58 秒。未生成正式 GPI/input 或运行预约，未解码任何未见观测密度，未启动 TIE-GCM、GPU、AI、DART 或轨道传播。

## V43 最小执行范围

真实交接到件后立即提取唯一 junsol 并静态复核，独立验收两份 ESA 原件。junsol 通过后提出同 SHA 夏季初态政策草案，待单独授权。完整双年配置还需要 2021 GFZ 同产品合法修订，或在目标解封前单独审查前瞻性协议修订。V37 夏季 2021 优先、冬季封存、Raw/Global、λ=0.5、截点、窗口和联合判据均保持。
