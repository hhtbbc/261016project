# V66 GFZ 回信与缺测候选方案

状态为 GFZ_MISSING_REASON_CLARIFIED、GFZ_REFERENCE_VALUES_RECEIVED、ORIGINAL_20Z_OBSERVATIONS_NOT_RECOVERED、GAP_FILL_POLICY_PENDING_REVIEW。原 GFZ_2021_GAP_UNRESOLVED 保持。

## 观测身份

根据用户转述的 GFZ Oliver Bronkalla 回信，由 Jürgen Matzka 转交，GFZ 再发布加拿大 Penticton 的 20:00 UTC F10.7。回信中本地加拿大副本在 2021-05-09 无记录，在 2021-06-16 缺 20Z，存在 17Z 76.9、23Z 77.1 sfu 两个未做日地距离调整的同日观测。未取得任何原始 20Z 恢复记录、GFZ 修订件或认证签名。用户未提供原件日期和邮件头，公开产物仅保存技术摘要。V55 staging 校验为收到声明、待权威审查。ESA 与 NCAR 未收到新证据。 [GFZ 数据入口](https://kp.gfz.de/en/data) · [加拿大记录入口](https://spaceweather.gc.ca/solar_flux_data/daily_flux_values/fluxtable.txt)

一次有界 HTTPS 核查中，XRAS 参考返回 HTTP 403，加拿大原始文件直连 TLS 超时。NOAA SWPC 的季度日表确有 5 月 9 日 76 sfu，6 月 16 日也列 76 sfu。两项都是日表整数，表中这两行无法提供观测时刻、原始值或处理标志。XRAS 所列 76 的实际定义尚未核实。ARRL 页面成功获取，明确将 6 月 16 日的 77 sfu 说明为两侧观测的均值，正好对应 20Z 等间距线性插值。NOAA 6 月 16 日的 76 与该估计相差 1 sfu，未强行合并。 [XRAS 回信所附入口](https://xras.ru/magnetic_storms.html/cambridge_bay/?m=5&d=9&y=2021) · [NOAA 季度日表](https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/annual_reports/daily_solar_indices_summaries/daily_solar_data/2021Q2_DSD.txt) · [ARRL 2021-06-18 日报](https://www.arrl.org/news/view/the-k7ra-solar-update-685)

## 研究者补值候选

| 候选 | 2021-05-09 sfu | 2021-06-16 sfu | 定义 |
|---|---:|---:|---|
| A，建议送审 | 76.00 | 77.00 | NOAA 整数日表旁证与同日等距插值 |
| B，较宽敏感性对照 | 76.20 | 80.25 | 对每个缺测日取前后一天的官方 observed F10.7 均值 |

GFZ 相邻 observed 值分别为 75.9/76.5 和 75.5/85.0。A 对 6 月 16 日使用仅间隔 ±3 小时的测量。B 穿过次日 85.0 的跳升，适合给出替代政策敏感性。5 月 9 日测试 75.9–76.5，6 月 16 日测试 76.9、77.0、77.1。这些只是有数据依据的试验范围，无统计置信区间意义。原始 observed、adjusted 与 Kp 全部保留，仍保留缺测码。CelesTrak 的插值规则可供标记参考，不能视为 GFZ 对本方案的批准。 [CelesTrak 公开格式](https://celestrak.org/spacedata/spacewx-format.php)

## GPI 对比

六个候选仅标记为研究者补值 HINDCAST。候选积分窗 2021-05-31 00Z 到 06-23 00Z，GPI 日节点 05-29 至 06-25，共 28 个。5 月 9 日只通过中心 81 日 F107A 进入该积分。其日均支持影响 03-30 至 06-18，6 月 16 日影响 05-07 至 07-26，均含端点。二者共同进入均值时，B−A 的日节点差为 3.45/81 ≈ 0.04259 sfu。运行时太阳驱动由源码等价的四点插值计算，日期标签与 20Z 原始观测时刻分别记录。

对 33,121 个 60 秒时点计算，B 相对 A 的最大 F107D 差 3.25 sfu，最大 F107A 差 0.042751 sfu。6 月 16 日改用 76.9 或 77.1，F107D 峰差 0.10 sfu，F107A 峰差约 0.001235。5 月 9 日测试范围在预约积分中只使 F107A 峰差至多 0.006569 sfu。所有候选 Kp、hpower 和 ctpoten 完全相同，整点与半点的独立驱动核查最大绝对差 4.27×10⁻¹⁴。GPI 差异不能直接换算为密度误差。原 GFZ 源文件 SHA 已在计算前后核对不变。

## 运行及科学门禁

建议先单独审议并明确批准 GFZ_FOBS_GAP_FILL_V1 与 A 候选，建立前瞻协议版本，注明两行人工估计、取值证据与替代方案，再另行批准 2021 夏季 CPU 冷启动。建议沿 V51 的同季历日与耗时设计，05-31 00Z 至 06-23 00Z，21 天预热，目标 06-21，mareqx smax 与 junsol smax 做双初态。单次 33,120 步，按 V65 实测约 0.97 小时、4.51 GiB。若另授权敏感性，可先固定同一初态作 B 对 A，再视结果决定是否补齐第二初态交互对照。候选驱动或初态的选择不得查看 Swarm 评分。ESA 0504、官方交付来源、ZG/GRS80、V37 正式评分及轨道门禁均保持。V66 未用候选驱动启动任何模型。
