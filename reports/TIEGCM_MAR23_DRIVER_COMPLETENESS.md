# Mar23 v2驱动完整性

2026-10-23；INDEPENDENT_TIEGCM_DATA_GENERATION / HINDCAST。

|年份|模型候选合法域|原GPI记录日|Fobs支持日|Fobs条数|def Kp桶数|缺测|
|---|---|---|---|---:|---:|---:|
|2021|03-16至03-26|03-14至03-28|02-02至05-07|95|120|0|
|2022|03-16至03-25|03-14至03-27|02-02至05-06|94|112|0|

边界由date/timedelta代码按模型起止±2日、再±40日计算，不直接使用人工估算。两年完整集合、UTC、重复、有限性/正值及Kp状态检查均通过后才写任何新GPI；没有插值Fobs、Fadj替换、跨年复用、改时间标签或候选观测填补。

2021全部复用既有GFZ正式年度ASCII，SHA `f969f23b0b0d4aba80dca6f35d3e95c2d35a7e482457bc1812e5c0827090caae`，只提取Fobs和D=2的Kp，不取SN。2022复用旧原始Fobs与Kp，只补02-02至02-14每日13条Fobs，以及03-14至03-26的104个def Kp桶；HTTP200，新增网络正文共4110字节，无重下载旧文件。

GFZ来源[说明与API](https://kp.gfz.de/en/data)、[格式与许可](https://kp.gfz.de/app/format/Kp_ap_Ap_SN_F107_format.txt)。Fobs/Kp为CC BY4.0；年度SN有不同许可，但未提取。Kp均definitive；Fobs没有逐日质量旗，有限/正值/完整仅为工程质量门禁，不等于独立标定审核。2022-03-31 Fobs=239.5 sfu为本支持区间最大值，保留原值，不擅自解释、裁剪或平滑；尚未独立判断是否受射电事件/发布修订影响。2021范围69.5—82.9，2022范围92.3—239.5 sfu。

支持区间没有−1、NaN、Inf、重复或缺日；这不消除观测系统/修订及真实未来驱动不可得性。中心平均含未来40日，仍属HINDCAST。

完整来源路径/URL/时间域/许可/SHA、计数和范围见`experiments/training_window_mar23_v2/completeness.json`及`data/raw/training_window_mar23_v2/*_source.json`；复用来源URL可追至旧`experiments/tiegcm_training_years_v1/2022/driver_audit.json`。原4月方案和05-09缺测继续DATA_GAP_UNRESOLVED，不覆盖或宣称修复。
