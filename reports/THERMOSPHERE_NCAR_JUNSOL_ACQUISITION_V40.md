# V40 NCAR 5° 数据包交付核查与 junsol 定向提取

**V40_NCAR_ACQUISITION_BLOCKED · NCAR_DOWNLOAD_REGISTRATION_REQUIRED · RUN_READY=False**

## 交付核查与实际资产

2026-11-24 UTC 起始本地 HEAD 与远端 main 一致，均为 `4da58915638aa3c8e0f2f912799803406f1f7d7b`。项目持久化目录、V39 staging/accepted 及相关数据目录未发现完整 TAR、部分文件、夏至初态或两份 ESA ZIP。项目挂载约 1.22 TiB 可用，满足 5 GiB 的传输前检查。

对用户提供的精确注册交付链接两次有限 HEAD（首次探查及正式留证）均返回 **HTTP 302**，TLS 请求成功，Location 指向官方 `hao-reg_email.php`。Content-Type 为 `text/html; charset=UTF-8`，未声明 Content-Length、Content-Disposition、Accept-Ranges、ETag 或 Last-Modified。登记重定向未跟随，没有提交邮箱、注册、访问直接文件路径规避登记或启动数据传输。官方文档说明下载流程需要邮箱，并将唯一目标列为 5° startup 文件。 [NCAR 下载流程](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/quickstart.html) · [NCAR 初态文件目录](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/dirstruct.html)

**实际 TAR 和 junsol 均未取得。** TAR 正文字节 0，提取文件 0。真实 TAR 大小、SHA、实际目标成员及内部路径尚未知；junsol 文件大小、SHA、34 项状态、原生年月日/时钟、SOURCE_START 和模型兼容性也未验证。合成结果中的成员路径及日期只属于夹具。

V39 官方导入和独立复核命令已运行，两份精确 Swarm ZIP 和 junsol 均报告 `NOT_ACQUIRED`，真实验收文件为零。未重试 ESA 旧请求，未切换 baseline。

## 可执行交接与验收

用户自行打开原 NCAR 注册交付链接，在正式页面按要求填写邮箱并遵守发布条款，取得 `tiegcm2.0_res5.0_data.tar`。保持官方文件原样，上传至：

`data/raw/thermosphere_ncar_junsol_acquisition_v40/tiegcm2.0_res5.0_data.tar`

保留公开发布路径、交付日期及提供方校验和（如提供）。勿上传账号、Cookie、凭据或签名链接。下载后的上传和验收不要求解开完整包。在项目根执行下列命令，日期应替换为实际下载或交接日期：

```bash
source scripts/activate_tiegcm.sh
export CUDA_VISIBLE_DEVICES=''
python -B scripts/extract_ncar_junsol_v40.py \
  data/raw/thermosphere_ncar_junsol_acquisition_v40/tiegcm2.0_res5.0_data.tar \
  --date YYYY-MM-DD
python -B scripts/import_summer_handoff_v39.py --inspect
python -B scripts/verify_summer_handoff_v39.py --accepted-only
python -B scripts/verify_ncar_junsol_v40.py --accepted-only
```

提取器仅接受项目 data/raw 中的普通非符号链接文件；按头部结构判断未压缩 TAR。逐成员验路径和边界，拒绝路径穿越、绝对路径、软硬链接、特殊或稀疏成员、重复目标和损坏结尾。计算整个 TAR SHA；唯一目标不超过 20 MiB，独立临时目录仅写入该成员。禁止覆盖原件。原生预检后，将原始字节和 V39 兼容声明交给 staging；单独的 V40 收据绑定 TAR SHA、内部路径与成员 SHA。获取途径的声明、文件字节身份、原生兼容性及政策准入分别记录。V39 静态通过后，独立验收重新读取 34 个状态、变量维度与单位、时钟和原生填充及极值。

仅当未来官方流程直接提供同一 TAR 二进制，`scripts/download_ncar_v40.py --download` 才开始流式写 `.part`。下载前需 ≥5 GiB 可用空间，正文上限 2 GiB。续传要求同 URL、长度、强 ETag 和 byte ranges，核验 206 Content-Range；中断保留部分文件和版本收据。HEAD 不受支持时只接受严格的 512 字节 Range 响应。完整结构和 SHA 验证后才发布最终文件。本轮未对真实下载执行续传。

两份 ESA 文件仍需通过官方归档交接至 `data/raw/thermosphere_summer_data_handoff_v39/staging/`：

- `SW_OPER_DNSAPOD_2__20210621T000000_20210621T235930_0301.ZIP`
- `SW_OPER_DNSAPOD_2__20220621T000000_20220621T235930_0301.ZIP`

## 保护、验收与政策

56 项 CPU 测试通过（40 项 V39/V38 回归、16 项 V40 新增），覆盖 TAR 格式、截断、恶意路径、链接、重复成员、目标大小、目标缺失、HTML 和错误的范围续传。历史保护复核包括 V37 的 10 项、V38 22 项发布文件及 4 份 GFZ 原始响应、V39 的 8 项，以及 mareqx smax 的 SHA。独立审核约 0.40 秒墙钟、76.7 MiB 峰值 RSS。原件下载、积分、GPU、GPI/input、校正拟合、未见目标解码、评分、AI、DART 和轨道传播均为零。

| 日期 | 驱动 | Swarm | 夏至初态 | 配置 |
|---|---|---|---|---|
| 2021-06-21 | GFZ_BLOCKED，两个 Fobs 缺测仍在 | 未取得 | 未取得，政策待审 | 未准入 |
| 2022-06-21 | GFZ_COMPLETE，复用 101 日 Fobs、168 Kp 桶 | 未取得 | 未取得，政策待审 | 未准入 |

既有 mareqx smax 为春分 2002-03-21 00:00，SOURCE_START=`80 0 0`，工程校验参照 SHA `a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7`。junsol smax 预期季节更贴近夏至，太阳高活动背景仍是初态属性，不能取代对应年份的真实驱动。其真实日期、模式字段及 SHA 待实物确定。V41 优先处理用户交付的原 TAR 和两份 Swarm ZIP，再提交两年份共用同一通过验收的 junsol SHA 的政策草案供审核。验证 34 状态只建立静态兼容性，14 天预热仍未证明收敛。当前不足以冻结夏季初态政策或 2022 物理配置，2021 Fobs 缺口继续阻断两年份正式计划。

V37 日期、夏季顺序、Raw/Global、固定 λ=0.5 和夏冬未见目标保持。所有高度、重启、实时 as-of、科学训练、DART 及真实轨道门禁保持。
