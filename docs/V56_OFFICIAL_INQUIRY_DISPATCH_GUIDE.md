# V56 官方咨询人工提交清单

**优先提交 GFZ，ESA 与 NCAR 可并行。** 2026-11-27 定向核对了官方入口。下表补充 V55 草稿的发送材料。

| 机构 | 手动渠道与主题 | 发送前核对及最小附件 |
|---|---|---|
| GFZ | 官方 Kp 联系表单或该页公布的业务联系人。*Historical observed F10.7 missing on 2021-05-09 and 2021-06-16* | 两日 Fobs 均 −1，单位 sfu，要求 observed。附 V54 两份 106 字节响应或给出日期、查询 URL 和返回值。 |
| ESA | 官方 Swarm 目录与账户持有人核对的 EO 支持入口。*Exact Swarm-A MODA 0504 inputs and DNSAPOD 0301 delivery verification* | 附两份 0301 的完整名、字节数、HDR 引用和 V54 官方目录对照。只要求精确 0504，保留 0601 为不同版本。 |
| NCAR | 从 2.0 Contact 页核对 moderated list 或科学技术联系入口。*TIE-GCM 2.0 ZG external datum and independent control points* | 附 V54 的 addiag.F、cons.F、lbc.F 行段及底接口范围。请求权威几何定义和独立控制点。 |

[GFZ Kp 联系页](https://kp.gfz.de/en/contact) · [ESA Swarm 归档及条款](https://swarm-diss.eo.esa.int/) · [NCAR 2.0 Contact](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/contact.html)

## 可直接复制的英文摘要

- **GFZ** — Could you verify whether the missing public GFZ Fobs records on 2021-05-09 and 2021-06-16 have a traceable revision under the same observed F10.7 definition? Please provide the observation time, quality record and revision identifier in sfu, or your recommendation for retaining the gaps. [V55 完整草稿](V55_GFZ_INQUIRY_EN.md)
- **ESA** — Could the archive provide the exact two MODA_SC 0504 inputs cited in the attached DNSAPOD 0301 HDR references? Please include the applicable L1b and L2 definitions, terrestrial realization and reference epoch, clock and spacecraft reference point, and an independently verifiable delivery record for the 0301 products. [V55 完整草稿](V55_ESA_INQUIRY_EN.md)
- **NCAR** — Could you document the external zero surface and positive direction of TIE-GCM 2.0 ZG, the latitude convention, and the z_lbc and GSWM reference? We seek an independently reproducible GRS80-to-ZG registration with control points and an uncertainty bound. [V55 完整草稿](V55_NCAR_INQUIRY_EN.md)

用户应核对并手动发送。若网站要求登录或接受条款，由账户持有人处理。将可共享 TXT、PDF、原件或规范与本地 SHA256 放入 data/raw/thermosphere_external_handoff_v55/staging/，按 V55 合同填写声明 JSON。精确 0504 另附对应 .source.json。不要交接个人邮箱、Cookie、账号、令牌、签名 URL 或私密正文。已有 0301 无需再上传。

从项目根启用 scripts/activate_tiegcm.sh，将 src 和 scripts 加入 PYTHONPATH，设置 CUDA_VISIBLE_DEVICES 为空，运行 **python -B scripts/check_external_evidence_v55.py**。需要发布合格 SP3 字节收据时才显式加 --accept-sp3。声明仍需权威复核。无回件时继续合成或明确授权的非目标准备。 [V55 完整交接合同与流程](V55_MANUAL_HANDOFF_GUIDE.md)
