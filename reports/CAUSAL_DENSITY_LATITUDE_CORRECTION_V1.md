# 纬度分区因果密度校正 v13-B

日期：2026-11-16 UTC。执行状态 **COMPLETE / 工程核验PASS**；稳定全面收益**未成立**。

身份：**PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED / DATE_HELD_OUT / SAME_CONTINUOUS_TIE_RUN**。
2021/2022-03-23是本轮预先固定的观测日期，区别于v10—v12的03-24；模型场来自旧连续模拟，不能称独立模型运行或全新盲测。

## 1. 数据和执行顺序

B14为主方案，A7/B7为控制，A14排除。两份现有CDF逐字SHA吻合、各2880条UTC严格30秒、flag0=2880，瞬时density kg/m³；原始GRS80大地纬度用于分区。六卷NetCDF逐字SHA吻合v13-A和原审计，原运行returncode0/4 NORMAL EXIT/工程PASS。DEN/ZG在ilev，原单位g/cm³/cm，分别×1000和×0.01。完整多变量科学质量并未因此通过。

本轮先补查同一03-23 B14 [03,06)：每年四真实整点帧，360/360八列查询通过；再冻结协议；随后重新核查六背景15—次日00的十帧、6480/6480实际Map-A查询。总新查询7200，填值/非有限/非正DEN/ZG非单调均0，无垂直外推；包括零权重邻列。18个独立列重建探针满足rtol1e-13/atol0。全部质量有效点进入共同域，没有为了改善删样本。

协议SHA：`bb1346ddbb0bae33fb8678a0b5341d804b627612999fd94e113a7c23ca90941c`。
参数SHA：`723e634fd1644082e387c7789ffb1aeb2a4dd6d299ff127ce70692a2ff5ba732`。
协议在任何系数之前冻结；全部26个系数在未来评分之前写入并计算SHA，之后未来密度×1e20毒化测试系数逐项不变。Stale06只用当天03-23 [03,06)，未借03-24旧系数。

## 2. 唯一改变的因素

历史[15,18)内，GlobalAdaptive18为median(ln(obs)−ln(model))；LatitudeAdaptive18保持同一公式、历史窗口、质量掩码，仅分abs(lat)<30、30≤abs(lat)<60、abs(lat)≥60三组。未来每个点按自身原始观测纬度应用exp(b)，无平滑、借区、插值、缩放、时间衰减、高度拟合或参数搜索。它是沿已知卫星轨迹的密度输出后处理，不更新模型内部状态，不是全球状态同化，也不是已证明的业务未来预报。

每区历史与未来要求N≥30；不足时完整联合评价N/A，不能回退全局。实际历史各背景2021低/中/高=123/122/115，2022=119/117/124，全部支持；所有实际未来区域也满足N≥30，无N/A。累计1/3/6小时N=120/360/720，共同覆盖率100%。

## 3. B14冻结系数

| 年份 | 区域/方法 | 历史N | b | exp(b) |
|---|---|---|---|---|
| 2021 | global | 360 | 0.088226726900 | 1.092235733179 |
| 2021 | low | 123 | 0.206032588600 | 1.228793247994 |
| 2021 | mid | 122 | 0.120913619731 | 1.128527425655 |
| 2021 | high | 115 | 0.070143105772 | 1.072661674348 |
| 2021 | Stale06 | 360 | 0.015904076576 | 1.016031219538 |
| 2022 | global | 360 | 0.119407727516 | 1.126829263935 |
| 2022 | low | 119 | 0.035458583258 | 1.036094735571 |
| 2022 | mid | 117 | 0.071777601412 | 1.074416368807 |
| 2022 | high | 124 | 0.126380433270 | 1.134713769050 |
| 2022 | Stale06 | 360 | 0.077442314975 | 1.080519900843 |

2021低纬系数比全局更大（×1.22879 vs ×1.09224），2022低纬更小（×1.03609 vs ×1.12683）。空间残差差异真实存在，但历史系数幅值并不能保证未来更合理。
控制组完整系数见correction_parameters.json；不跨背景、不跨年份混合。

## 4. B14未来实际误差

RMSE表单位为10⁻¹³ kg/m³；relative RMS与relative P95为百分比，分母固定真实观测密度。MAE/Bias/relativeBias/logRMS/Pearson/max_abs完整值见metrics.csv；不更改swarm_crossyear.metric_row/compare_density。

| 年 | 累计窗口 | 方法 | N | RMSE | relative RMS % | relative P95 % |
|---|---|---|---|---|---|---|
| 2021 | future_1h | Raw | 120 | 1.104573 | 18.002447 | 23.899506 |
| 2021 | future_1h | GlobalAdaptive18 | 120 | 0.767415 | 15.542338 | 28.162221 |
| 2021 | future_1h | LatitudeAdaptive18 | 120 | 0.523589 | 15.554360 | 32.420665 |
| 2021 | future_1h | Stale06 | 120 | 1.042286 | 17.318291 | 22.699756 |
| 2021 | future_3h | Raw | 360 | 0.950340 | 21.456237 | 40.515673 |
| 2021 | future_3h | GlobalAdaptive18 | 360 | 0.745398 | 24.417196 | 53.476239 |
| 2021 | future_3h | LatitudeAdaptive18 | 360 | 0.702785 | 29.934235 | 65.756282 |
| 2021 | future_3h | Stale06 | 360 | 0.907865 | 21.717761 | 42.768311 |
| 2021 | future_6h | Raw | 720 | 0.983220 | 20.795467 | 34.343538 |
| 2021 | future_6h | GlobalAdaptive18 | 720 | 0.781654 | 23.425871 | 46.734813 |
| 2021 | future_6h | LatitudeAdaptive18 | 720 | 0.723062 | 28.354327 | 62.716228 |
| 2021 | future_6h | Stale06 | 720 | 0.941383 | 20.989449 | 36.497229 |
| 2022 | future_1h | Raw | 120 | 2.888452 | 23.344794 | 44.489936 |
| 2022 | future_1h | GlobalAdaptive18 | 120 | 2.052116 | 29.178638 | 62.815488 |
| 2022 | future_1h | LatitudeAdaptive18 | 120 | 2.643534 | 29.384520 | 63.954720 |
| 2022 | future_1h | Stale06 | 120 | 2.301803 | 26.461842 | 56.124251 |
| 2022 | future_3h | Raw | 360 | 2.622546 | 23.170840 | 47.631429 |
| 2022 | future_3h | GlobalAdaptive18 | 360 | 1.988645 | 29.505823 | 66.355415 |
| 2022 | future_3h | LatitudeAdaptive18 | 360 | 2.425445 | 29.040862 | 67.519415 |
| 2022 | future_3h | Stale06 | 360 | 2.157004 | 26.621901 | 59.518697 |
| 2022 | future_6h | Raw | 720 | 2.543348 | 22.196747 | 38.632131 |
| 2022 | future_6h | GlobalAdaptive18 | 720 | 1.916139 | 28.188933 | 56.214742 |
| 2022 | future_6h | LatitudeAdaptive18 | 720 | 2.281684 | 26.318793 | 48.240919 |
| 2022 | future_6h | Stale06 | 720 | 2.078578 | 25.397577 | 49.794776 |

下表正改善率为相对Raw下降，负为恶化。四旗标须全部满足才PASS，无加权综合分数。

| 年 | 窗口 | 方法 | RMSE收益% | relative RMS收益% | 通过项 | JOINT |
|---|---|---|---|---|---|---|
| 2021 | future_1h | GlobalAdaptive18 | 30.5239 | 13.6654 | 3/4 | FAIL |
| 2021 | future_1h | LatitudeAdaptive18 | 52.5981 | 13.5986 | 3/4 | FAIL |
| 2021 | future_1h | Stale06 | 5.6390 | 3.8003 | 4/4 | PASS |
| 2021 | future_3h | GlobalAdaptive18 | 21.5651 | -13.8000 | 1/4 | FAIL |
| 2021 | future_3h | LatitudeAdaptive18 | 26.0491 | -39.5130 | 1/4 | FAIL |
| 2021 | future_3h | Stale06 | 4.4694 | -1.2189 | 1/4 | FAIL |
| 2021 | future_6h | GlobalAdaptive18 | 20.5006 | -12.6489 | 1/4 | FAIL |
| 2021 | future_6h | LatitudeAdaptive18 | 26.4598 | -36.3486 | 1/4 | FAIL |
| 2021 | future_6h | Stale06 | 4.2552 | -0.9328 | 1/4 | FAIL |
| 2022 | future_1h | GlobalAdaptive18 | 28.9545 | -24.9899 | 2/4 | FAIL |
| 2022 | future_1h | LatitudeAdaptive18 | 8.4792 | -25.8718 | 2/4 | FAIL |
| 2022 | future_1h | Stale06 | 20.3102 | -13.3522 | 2/4 | FAIL |
| 2022 | future_3h | GlobalAdaptive18 | 24.1712 | -27.3403 | 2/4 | FAIL |
| 2022 | future_3h | LatitudeAdaptive18 | 7.5157 | -25.3337 | 2/4 | FAIL |
| 2022 | future_3h | Stale06 | 17.7515 | -14.8940 | 2/4 | FAIL |
| 2022 | future_6h | GlobalAdaptive18 | 24.6608 | -26.9958 | 1/4 | FAIL |
| 2022 | future_6h | LatitudeAdaptive18 | 10.2882 | -18.5705 | 2/4 | FAIL |
| 2022 | future_6h | Stale06 | 18.2739 | -14.4203 | 1/4 | FAIL |

**主要结论：LatitudeAdaptive18在B14的6/6累计窗口降低绝对RMSE，但relative RMS仅1/6降低，relative P95为0/6不恶化，低纬Bias绝对值4/6不恶化；共11/24个单项通过，JOINT=0/6。** Global为10/24、0/6。Stale06仅2021首小时JOINT通过（3h/6h不通过）；这不构成纬度方法成功证据。

2021局地方法绝对RMSE三个窗口均优于全局，但相对RMS三个窗口均比全局更差（首小时差异很小）。2022局地方法绝对RMSE三个窗口均差于全局；相对RMS仅3h/6h比全局缓解恶化，仍差于Raw。不能称局地方法稳定优于全局。

## 5. 纬度结构和过校正

B14未来六小时，各区同一有效样本；RMSE单位10⁻¹³ kg/m³，Bias是平均有符号相对偏差百分比。

| 年 | 纬区 | 方法 | N | RMSE | relative RMS % | relative Bias % |
|---|---|---|---|---|---|---|
| 2021 | low | Raw | 248 | 1.305398 | 25.673555 | 1.449542 |
| 2021 | mid | Raw | 246 | 0.875417 | 17.654369 | -4.689528 |
| 2021 | high | Raw | 226 | 0.612945 | 17.752973 | -4.741145 |
| 2021 | low | GlobalAdaptive18 | 248 | 1.069898 | 30.010173 | 10.806815 |
| 2021 | mid | GlobalAdaptive18 | 246 | 0.653645 | 19.037082 | 4.101503 |
| 2021 | high | GlobalAdaptive18 | 226 | 0.474679 | 19.118984 | 4.045125 |
| 2021 | low | LatitudeAdaptive18 | 248 | 0.969370 | 40.002655 | 24.660512 |
| 2021 | mid | LatitudeAdaptive18 | 246 | 0.600943 | 20.642100 | 7.560482 |
| 2021 | high | LatitudeAdaptive18 | 226 | 0.491300 | 18.480374 | 2.180523 |
| 2021 | low | Stale06 | 248 | 1.257964 | 26.224536 | 3.075902 |
| 2021 | mid | Stale06 | 246 | 0.830535 | 17.579623 | -3.161585 |
| 2021 | high | Stale06 | 226 | 0.579606 | 17.677079 | -3.214030 |
| 2022 | low | Raw | 247 | 3.472357 | 23.371713 | -1.913064 |
| 2022 | mid | Raw | 242 | 2.227490 | 19.228206 | -1.994276 |
| 2022 | high | Raw | 231 | 1.439288 | 23.754434 | 5.024853 |
| 2022 | low | GlobalAdaptive18 | 247 | 2.483892 | 28.279971 | 10.527229 |
| 2022 | mid | GlobalAdaptive18 | 242 | 1.564626 | 23.943872 | 10.435718 |
| 2022 | high | GlobalAdaptive18 | 231 | 1.510703 | 31.952535 | 18.345078 |
| 2022 | low | LatitudeAdaptive18 | 247 | 3.147886 | 24.188854 | 1.627358 |
| 2022 | mid | LatitudeAdaptive18 | 242 | 1.767459 | 21.219948 | 5.298954 |
| 2022 | high | LatitudeAdaptive18 | 231 | 1.535753 | 32.582872 | 19.173147 |
| 2022 | low | Stale06 | 247 | 2.789525 | 25.870645 | 5.984886 |
| 2022 | mid | Stale06 | 242 | 1.737500 | 21.489394 | 5.897135 |
| 2022 | high | Stale06 | 231 | 1.408321 | 28.479333 | 13.481444 |

2021低纬Raw +1.450%→Global +10.807%→Latitude +24.661%，局地反而显著加重过校正；低纬relative RMS25.674%→40.003%。2022低纬Raw−1.913%→Global+10.527%→Latitude+1.627%，局地缓解Bias，但relative RMS23.372%→24.189%仍恶化。
2021中纬Bias−4.690%翻转为+7.560%，relative RMS17.654%→20.642%；高纬虽Bias较接近零，relative RMS仍17.753%→18.480%。2022中/高纬Bias分别+5.299%/+19.173%，relative RMS19.228%→21.220%与23.754%→32.583%。因此并未消除空间过校正，也不能从一项Bias改善推断整区误差改善。

## 6. 时间块、点级与背景对照

非重叠块与累计窗分别报告，不把重叠累计窗当独立重复。30秒点有时间相关性，本轮无IID显著性检验。

| 年 | 非重叠块 | 方法 | RMSE收益% | relative RMS收益% |
|---|---|---|---|---|
| 2021 | block_1_3h | GlobalAdaptive18 | 14.926 | -20.978 |
| 2021 | block_1_3h | LatitudeAdaptive18 | 9.955 | -52.127 |
| 2021 | block_1_3h | Stale06 | 3.522 | -2.709 |
| 2021 | block_3_6h | GlobalAdaptive18 | 19.579 | -11.324 |
| 2021 | block_3_6h | LatitudeAdaptive18 | 26.822 | -32.656 |
| 2021 | block_3_6h | Stale06 | 4.068 | -0.606 |
| 2021 | block_0_1h | GlobalAdaptive18 | 30.524 | 13.665 |
| 2021 | block_0_1h | LatitudeAdaptive18 | 52.598 | 13.599 |
| 2021 | block_0_1h | Stale06 | 5.639 | 3.800 |
| 2022 | block_1_3h | GlobalAdaptive18 | 21.089 | -28.526 |
| 2022 | block_1_3h | LatitudeAdaptive18 | 6.867 | -25.058 |
| 2022 | block_1_3h | Stale06 | 16.059 | -15.674 |
| 2022 | block_3_6h | GlobalAdaptive18 | 25.220 | -26.582 |
| 2022 | block_3_6h | LatitudeAdaptive18 | 13.543 | -9.929 |
| 2022 | block_3_6h | Stale06 | 18.871 | -13.851 |
| 2022 | block_0_1h | GlobalAdaptive18 | 28.954 | -24.990 |
| 2022 | block_0_1h | LatitudeAdaptive18 | 8.479 | -25.872 |
| 2022 | block_0_1h | Stale06 | 20.310 | -13.352 |

局地2021仅首小时两RMS同时改善，后两块相对RMS恶化；2022三个块相对RMS都恶化。收益并非固定随时长单调衰减，不能据此拟合未经授权的时间衰减。
点级改善/恶化/不变及全部区域统计见pointwise_diagnostics.csv，未仅保留改善点。

| 控制年 | 背景 | 窗口 | 方法 | RMSE收益% | relative RMS收益% | JOINT |
|---|---|---|---|---|---|---|
| 2021 | A7 | future_1h | GlobalAdaptive18 | 36.833 | 18.704 | FAIL |
| 2021 | A7 | future_1h | LatitudeAdaptive18 | 54.963 | 18.792 | FAIL |
| 2021 | A7 | future_3h | GlobalAdaptive18 | 26.419 | -15.960 | FAIL |
| 2021 | A7 | future_3h | LatitudeAdaptive18 | 29.281 | -39.872 | FAIL |
| 2021 | A7 | future_6h | GlobalAdaptive18 | 25.131 | -14.565 | FAIL |
| 2021 | A7 | future_6h | LatitudeAdaptive18 | 29.429 | -36.612 | FAIL |
| 2021 | B7 | future_1h | GlobalAdaptive18 | 26.450 | 9.760 | FAIL |
| 2021 | B7 | future_1h | LatitudeAdaptive18 | 49.810 | 9.282 | FAIL |
| 2021 | B7 | future_3h | GlobalAdaptive18 | 17.165 | -12.394 | FAIL |
| 2021 | B7 | future_3h | LatitudeAdaptive18 | 21.491 | -35.846 | FAIL |
| 2021 | B7 | future_6h | GlobalAdaptive18 | 16.082 | -11.697 | FAIL |
| 2021 | B7 | future_6h | LatitudeAdaptive18 | 22.128 | -33.238 | FAIL |
| 2022 | A7 | future_1h | GlobalAdaptive18 | 37.110 | -28.628 | FAIL |
| 2022 | A7 | future_1h | LatitudeAdaptive18 | 16.544 | -29.939 | FAIL |
| 2022 | A7 | future_3h | GlobalAdaptive18 | 32.209 | -32.488 | FAIL |
| 2022 | A7 | future_3h | LatitudeAdaptive18 | 15.374 | -30.292 | FAIL |
| 2022 | A7 | future_6h | GlobalAdaptive18 | 32.722 | -31.314 | FAIL |
| 2022 | A7 | future_6h | LatitudeAdaptive18 | 18.238 | -21.622 | FAIL |
| 2022 | B7 | future_1h | GlobalAdaptive18 | 25.952 | -23.189 | FAIL |
| 2022 | B7 | future_1h | LatitudeAdaptive18 | 5.165 | -23.739 | FAIL |
| 2022 | B7 | future_3h | GlobalAdaptive18 | 21.110 | -25.060 | FAIL |
| 2022 | B7 | future_3h | LatitudeAdaptive18 | 4.356 | -22.925 | FAIL |
| 2022 | B7 | future_6h | GlobalAdaptive18 | 21.430 | -25.012 | FAIL |
| 2022 | B7 | future_6h | LatitudeAdaptive18 | 7.118 | -16.728 | FAIL |

A7/B7的局地方法均6/6降低RMSE但只1/6降低relative RMS，尾部0/6不恶化；12个控制局地联合评价全部FAIL，支持“空间分区未带来稳定全面收益”，不能按更好的背景替换B14。

| 背景 | 方法 | 未来评价数 | RMSE通过 | relativeRMS通过 | 尾部通过 | 低纬Bias通过 | JOINT通过 |
|---|---|---|---|---|---|---|---|
| B14 | GlobalAdaptive18 | 6 | 6 | 1 | 0 | 3 | 0 |
| B14 | LatitudeAdaptive18 | 6 | 6 | 1 | 0 | 4 | 0 |
| B14 | Stale06 | 6 | 6 | 1 | 1 | 3 | 1 |
| A7 | GlobalAdaptive18 | 6 | 6 | 1 | 0 | 3 | 0 |
| A7 | LatitudeAdaptive18 | 6 | 6 | 1 | 0 | 4 | 0 |
| B7 | GlobalAdaptive18 | 6 | 6 | 1 | 0 | 3 | 0 |
| B7 | LatitudeAdaptive18 | 6 | 6 | 1 | 0 | 3 | 0 |

以上42个未来方法×年份×背景×累计窗口联合评价共1项PASS，来自B14 Stale06的2021首小时；纬度方法0/18。不能把42项视为42个独立科研重复。98行联合文件还包含历史分析与非重叠块，不能把其总数当主要未来评价数。

## 7. 独立验证、资源与复现

14项新CPU测试及既有11项联合/14项观测可行性/8项小时查询/18项原生密度测试，共65项不同测试全部通过。边界±30/±60、N29拒绝/N30支持、NaN/Inf/零/负密度拒绝、缺区不借用、未来毒化、同样本ID、已有目录拒绝覆盖均覆盖。
独立程序使用排序取中位数、math.exp、直接NumPy物理公式，复算26个系数、560行区域/总体指标、98行联合判定，容差rtol1e-13/atol0不放宽；两份原CDF和全部原NetCDF再SHA核验、205个受保护文件逐字保持、8张PNG解码通过。
独立核验脚本初次把latitude字段误写为lat，KeyError退出；仅修正核验器字段映射后重跑核验成功。失败日志保留，正式拟合/未来评价没有重跑、参数不变。

实际预检3.424746s；正式直接父子监督15.439902s，returncode0/qualificationPASS，worker14.366274s；独立核验4.075124s。worker自报峰RSS318.047MiB，进程树采样峰317.379MiB，两者定义不同，采样峰不能冒充连续树峰。正式监督无采样缺口。独立失败耗时与测试日志另列resource_audit.json；编辑/交互检查未伪装成完整逐秒监控。无下载/GPU/新TIE/DART/轨道，产物远低150MiB，进程内存远低4GiB。

入口：source scripts/activate_orbit.sh；先测试，再prepare（目录必须不存在），最后launch（一次性标记）。verify仅独立复核。具体命令和停止保护见commands.json。现目录保留不得原地重新prepare/launch，复现应先另行授权独立tag，不能删除本结果。

## 8. 科研结论和限制

本轮证明历史纬度残差存在差异，未证明三段常数空间校正能在两个年份稳定改善未来联合指标。2021低纬更大历史系数放大未来过校正，2022低纬系数虽缓解Bias，却把相对误差风险留在中高纬。空间代表性不是唯一已证实的误差原因；历史窗口代表性、纬度与高度/地方时/轨道位置耦合、POD反演偏差和高度登记仍是待验证解释，不能从本实验分离因果。
RMSE²=mean(obs²×relative_error²)，relativeRMS²=mean(relative_error²)，故绝对与相对指标仍可反向；纬度分区并未改变这种目标权重差异。不能通过重新分区/缩放/挑窗把本轮改成PASS。
Map-A仍是临时条件假设，未新增正式高度证据；日期数量只有两天、同一来源POD且同一连续物理运行，沿轨结果不能外推全球。科学训练False、RestartFAIL、DART未准入、真实轨道BLOCKED、2021A14工程PASS仅历史敏感性/2022A14PARTIAL均保持。

下一步：先只读研究历史窗口对未来同纬区的代表性及高度登记，预注册更多日期/截点再申请独立验证；不直接推广局地方法，不通过增加DART复杂度掩盖当前相对误差与尾部恶化。本轮完成即停。
