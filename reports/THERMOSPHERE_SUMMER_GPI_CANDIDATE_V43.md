# V43 2022 夏季隔离 GPI 工程候选

**V43_PARTIAL**。2022 候选为 **GPI_ENGINEERING_CANDIDATE_VERIFIED**，原件交接仍待完成。起始 HEAD 与远端 main 同为 `13f2dc4ac4ff43903f6f35cf39e695f5b436e825`。V42 发布清单四项及 V37–V41 53 项按 SHA256 前后核验一致。V22 清单及两份秋季 GPI 共 32 项一致，四份真实 GFZ 源亦逐项复核一致。核对现有 ELF 和 Fortran 源文件的冻结身份，未执行 ELF。

## 执行与复核

在项目根从冻结环境运行 `CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python -B scripts/prepare_summer_gpi_candidate_v43.py`。先记录四份 GFZ 原件、写入器、独立验收代码和 ELF 的 SHA，再复用冻结生成逻辑写入新候选。候选原件留在服务器，文件只读。

- 原件 `experiments/thermosphere_summer_gpi_candidate_v43/gpi_2022_summer_candidate_v43.nc`，2656 字节，SHA256 `d1e5cd2211a0ec6dd7e2c882341e3a2756626aa9ec4df74b8461ab4cc5d1a860`。
- 独立解析核对 101 个 Fobs 日、168 个 definitive Kp 和 UTC。API 原件如未明示单位，则沿用 V38/V42 的 GFZ 合同，Fobs 为 sfu、Kp 无量纲。
- NETCDF3_CLASSIC，`ndays=21`、`nkp=8`。`year_day` 为 int32，`f107d`、`f107a` 和 `kp` 为 float64。`kp(ndays,nkp)` 对应 Fortran 的桶内索引优先。逐节点核对 21 个日值和 168 个 Kp 全部相同。21 个中心均值独立用 `math.fsum` 复算，最大绝对差 2.842170943040401e-14 sfu，低于 V22 的 1e-12 sfu。无掩码缺测或非有限驱动。
- 原始支持 2022-06-05 至 06-25，前后各有两日填充。候选积分区间为 06-07 00:00 至 06-23 00:00 UTC，年积日 2022158–2022174，60 秒步长共 23040 步。
- 冻结 Python 读取器与 V22 标量独立插值在 23041 个分钟时点及 128 个额外边界时点逐值对照。f107d 和 f107a 最大绝对差 5.684341886080802e-14 sfu，Kp 为 1.3322676295501878e-15，其他派生量见验收 JSON。各字段均通过 V22 的 1e-10 绝对容差。已核对 Fortran 字段、维度、日期属性及 Kp 桶中心合同。状态为 GPI_NUMERIC_VERIFIED，GPI_MODEL_RUNTIME_VERIFIED 待实际授权运行。
- 16 项 CPU 检查通过，覆盖 SHA、缺日/缺桶、错误索引、非法 UTC、闰年、维度、中心均值、非有限值、越界与目标密度访问拦截。另有发布与运行入口静态审计，见 admission.json。

## 交接与准入

| 项目 | 2021 夏季 | 2022 夏季 |
|---|---|---|
| GFZ | GFZ_BLOCKED，05-09 与 06-16 原始 Fobs 均为 −1 | GFZ 完整，GPI 工程候选通过 |
| ESA 0301 | NOT_ACQUIRED | NOT_ACQUIRED |
| NCAR junsol | NOT_ACQUIRED | NOT_ACQUIRED |
| 初态政策 / RUN_READY | PENDING / False | PENDING / False |

开始及收尾扫描交接目录，未见 TAR、部分包、junsol 或 ZIP。本轮未调用验收器处理虚拟原件，未重新探测网络。未见密度、校正拟合、科学评分、正式 input、运行预约、TIE-GCM 积分、GPU、AI、DART 和轨道传播均为零。V37 日期顺序和 λ=0.5 保持。

V44 优先处理真实到件。Chrome 下载完成后，将原始 TAR 放入 `data/raw/thermosphere_ncar_junsol_acquisition_v40/`。将两份原始 ESA ZIP 和来源说明放入 `data/raw/thermosphere_summer_data_handoff_v39/staging/`。用 V40/V39 工具提取并验收，必要时据真实 junsol 提出政策草案。2021 的同产品 Fobs 缺口仍需合法解决，正式配置和运行另行授权。
