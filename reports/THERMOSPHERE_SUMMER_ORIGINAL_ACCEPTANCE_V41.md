# V41 夏季科研原件交接状态

**V41_NO_NEW_ORIGINALS · RUN_READY=False**

检查了 V40 数据目录、V39 staging 和 accepted，并按目标文件名搜索项目内的 data、experiments。未发现 NCAR 完整 TAR、.part、junsol 或任何一份指定 ESA ZIP。没有重新联网探测或重跑旧测试。

V37、V38、V39、V40 发布清单逐项核验通过，涵盖 V38 四份本地 GFZ 原始响应和 V40 七项发布成果。既有 mareqx smax SHA 一致。检查起始本地与远端 main 均为 `f209127841bc88c22e498addd45343e1dc154eaa`。

| 日期 | GFZ | Swarm ZIP/CDF/HDR | 初态和配置 |
|---|---|---|---|
| 2021-06-21 | GFZ_BLOCKED。99/101 Fobs，缺 05-09、06-16；168/168 definitive Kp，0/21 中心窗 | NOT_ACQUIRED / NOT_VERIFIED | junsol 未取得，配置未准入 |
| 2022-06-21 | GFZ_COMPLETE。101/101 Fobs、168/168 definitive Kp、21/21 中心窗 | NOT_ACQUIRED / NOT_VERIFIED | junsol 未取得，配置未准入 |

TAR 完整性、字节数、SHA 与内含成员待真实文件核验。junsol 提取为零，其大小、SHA、34 状态、SOURCE_START、原生 UTC 和兼容性均未验证。V39 静态验收及独立原件复核没有实物可运行。夏季初态政策保持 `SUMMER_SEED_POLICY_PENDING`，等真实 junsol 验收后再形成政策草案。V37 日期、2021 优先顺序、Raw/Global 与固定 λ=0.5 均不变。未见密度解码、GPI/input、积分、GPU、拟合及评分均为零。

## 仍需交接的文件

在用户提供的 NCAR 注册交付入口自行完成邮箱步骤，将原始 `tiegcm2.0_res5.0_data.tar` 上传至 `data/raw/thermosphere_ncar_junsol_acquisition_v40/`。无需预先解包。保留实际下载日期及官方来源说明。

从 ESA 官方渠道取得原始 ZIP，上传至 `data/raw/thermosphere_summer_data_handoff_v39/staging/`，附无凭据的来源说明：

- `SW_OPER_DNSAPOD_2__20210621T000000_20210621T235930_0301.ZIP`
- `SW_OPER_DNSAPOD_2__20220621T000000_20220621T235930_0301.ZIP`

下一轮以收到的真实文件为入口，复用 V40 单成员提取、V39 静态验收和独立复核。若 junsol 通过，再审议两年共用同一 SHA 的方案。即使三件原件都通过，2021 两日真实 GFZ 缺测及初态政策仍是独立准入条件。
