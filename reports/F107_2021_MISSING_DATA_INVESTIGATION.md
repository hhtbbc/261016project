# 2021-05-09 F10.7缺测调查

日期：2026-10-23。结论：**DATA_GAP_UNRESOLVED**。没有满足当前门禁的替代观测值；没有新GPI或模型启动。不能由档案缺记录断言当天世界上不存在任何观测。

## 1. 原GFZ证据复核

原始响应`data/raw/tiegcm_training_years_v1/2021_Fobs.json`保持不变，SHA256为`d44f1d2041345e4e38d0777c06e1b3bc524c024ef35407ddcc479335523cf56b`。95个UTC日时间唯一且连续，2021-02-15至05-20，仅05-09为−1；05-08为75.9、05-10为76.5 sfu。没有重复/时区/字段解析错误。原URL和完整保护SHA见上一轮审计。

本次再次请求GFZ 05-07至05-11 Fobs，HTTP200仍为74.5、75.9、−1、76.5、76.1。另从其正式FTP路径取得2021年度ASCII（61,627字节），并非多年总档案；其中05-09 Fobs与Fadj都为−1，全部95日Fobs与既有JSON逐值相等。不能把−1解释为有效值。

[GFZ格式定义](https://kp.gfz.de/app/format/Kp_ap_Ap_SN_F107_format.txt)说明observed/adjusted来自加拿大当地正午记录，−1为缺测；质量列D指Kp/SN，不能据D=2声称Fobs已通过观测质量认证。Fobs和Fadj始终分开。

预定GPI原始日期03-27至04-10，合法域03-29至04-08；中心81日计算总需02-15至05-20，04-05本日平均需02-24至05-15。缺测会影响原始GPI中03-30至04-10的12个日平均；不能只看诊断日没有直接Fobs缺失而忽略F107A。

## 2. 各来源实际结果

|来源|取得的记录|定义与质量|处置|
|---|---|---|---|
|GFZ JSON、年度ASCII|05-09均−1|Fobs、Fadj分列；缺测|保留缺测，不填补|
|加拿大官方fluxtable|连续字节片段覆盖2020-11-30至2021-06-25；05-08后直接05-10，05-09任意时刻均0条|fluxobsflux与fluxadjflux分列，含观测时刻；表中无逐行质量字段|没有目标日原始记录|
|NOAA SWPC/NCEI 2021Q2 DSD|05-09为76 sfu，05-08=76、05-10=77|文档定义约20UT、未订正日地距离的Penticton观测，整sfu；没有该条估算/质量标志|作为候选报告，但跨源门禁失败，不采用|
|CelesTrak 2021 CSV片段|05-09 OBS字段76.2，ADJ77.7，DATA_TYPE=INT|INT明确是线性插值，不是实测|拒绝作为原始观测|

加拿大门户本次工具超时/本地TLS证书校验失败，未关闭TLS验证；通过已公开链接的`https://spaceweather.gc.ca/solar_flux_data/daily_flux_values/fluxtable.txt`取得HTTP206片段。先4096字节头，再两次4096字节二分定位，最后56,001字节邻域，逐次核对Content-Range与长度，保留每片SHA和范围。表总长2,189,096字节，未下载全表。来源中出现03-02 20UT重复且数值不同的两行，全部保留，不挑选更接近GFZ的一行。95条重叠20UT记录中94条与GFZ完全相同，另1条差0.9；该异常不影响目标日没有记录这一事实。

[加拿大数据门户索引](https://data.asc-csa.gc.ca/en/dataset/cfd2331e-6d68-41c0-9cf2-f2e9c4d68eb7)列发布方及Open Government Licence–Canada；本次未取得许可全文。原始片段仅本地保存。

[NOAA产品定义](https://www.ncei.noaa.gov/products/space-weather/partners/swpc-products-and-data)与其[2021Q2原始文件](https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/annual_reports/daily_solar_indices_summaries/daily_solar_data/2021Q2_DSD.txt)分别保留链接/数据SHA。它是观测类型汇编，不等同于取得加拿大原始仪器记录；整数76不应伪称精确到0.1sfu的原始读数。未找到该文件独立许可声明，保留本地原件，仅公开审计数字。

[CelesTrak文档](https://celestrak.org/spacedata/SpaceWx-format.php)解释OBS/INT差别及加拿大来源。其76.2恰等于(75.9+76.5)/2；实际标志也是INT，不能只因字段名含OBS就当观测。取得CSV前25,000字节，HTTP206；无必要下载整表。其来源与加拿大/GFZ并非独立仪器，不能当作多份独立观测投票。未核实独立数据许可全文，原片段仅本地。

## 3. 跨源门禁与结果

在计算NOAA重叠差异前保存`comparison_preregistered.json`：NOAA整sfu的±0.5加GFZ0.1sfu的±0.05，逐日最大允许差0.550000001 sfu；比较全部可用GFZ 04-01至05-20有效日期，不排除不利记录。

49个重叠日中23日失败，最大差8.8 sfu，显著超过仅发布精度所能解释的范围。可能涉及报告版本、观测时刻/选择、太阳射电事件或后续修订，但目前没有足够来源证据分解原因。**不能靠放宽门槛或只比较05-08/05-10来接受76**。完整49日表见`noaa_overlap.json`。

因此：加拿大目标日缺行，CelesTrak明确插值，NOAA候选跨源差异未闭合。既不能宣布原始观测绝对不存在，也不能宣布已可靠修复。

## 4. 敏感性仅用于方法分析

单点候选差异对81日算术平均的贡献严格为ΔFobs/81；1 sfu对应0.012345679 sfu。它不等于模型大气响应，也不构成真实误差界。

|假设缺测值 sfu|04-05条件F107A sfu|性质|
|---:|---:|---|
|75.9|74.85802469135803|前一日保持假设|
|76.0|74.85925925925926|NOAA候选，未通过来源门禁|
|76.2|74.86172839506173|邻日线性插值，CelesTrak INT|
|76.5|74.86543209876544|后一日保持假设|

76与76.2仅令平均相差0.002469136 sfu，不能因此省略观测真实性要求。75.9—76.5只是方法情景，不是置信区间、上下界或推荐填充值。未写入GPI，未调用模型测试这些情景。

## 5. 可追溯性

来源URL、HTTP/FTP状态、文件大小及SHA见`experiments/f107_2021_recovery_v1/source_requests.json`、`gfz_requests.json`、`canada_range_requests.json`、`canada_range_head.json`、`celestrak_request.json`。原始文件在`data/raw/f107_2021_recovery_v1`只读保存。最终审计为`recovery_audit.json`；无来源变更、无模型启动、无数据归一化变更。
