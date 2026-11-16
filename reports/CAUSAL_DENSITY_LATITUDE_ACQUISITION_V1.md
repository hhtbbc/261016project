# v13-A：独立日期观测获取与目标日模型覆盖预检

2026-11-16。`CAUSAL_DENSITY_LATITUDE_ACQUISITION=COMPLETE`，`CAUSAL_DENSITY_LATITUDE=READY_FOR_V13_PROTOCOL_FREEZE`。**只完成数据/质量/覆盖门禁，不是纬度算法实验完成或科学收益PASS。未拟合任何系数、未计算RMSE/relativeRMS/联合评价。**

身份：PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED。只读保留原`experiments/causal_density_latitude_v1/`全部阻碍审计；其原状态不重写。新证据和当前状态写入本轮新目录与STATUS/WORKLOG。

## 1. 缓存记录和实际网络获取分别记录

本轮之前两目标只在旧ESA listing缓存中列示，目标ZIP/CDF/HDR不在本地。本轮明确授权后，只请求指定两日A0301 ZIP：HTTPS默认证书/主机校验，25秒超时，实际HTTP200、最终仍为swarm-diss.eo.esa.int，Content-Length及流式实收都与冻结大小一致。没有账号、Cookie、凭据；没有下载完整1.45MB目录或B/C/其他日期。旧元数据从SHA核验的本地HAPI及已提交official_service_contract复用，元数据新增网络下载0。

|year|bytes|SHA256|HTTP|ContentLength|ZIP_CRC|
|---|---|---|---|---|---|
|2021|140271|74008af37c37cd7b58f89c0c2c452b485d7df7c2f4e9c197e4bcbabff7645145|200|140271|PASS|
|2022|139397|8c7bb8e3bfcb3a2e016936dff9459ca8afa0d80d49d3ed26c49c6c6a47e5fefe|200|139397|PASS|

实际应用层响应体合计279668字节，非缓存估计；原始下载预算1MiB。完整URL/始末时间/HTTP/TLS/大小/SHA见download_manifest.json。失败HTTP/HTML/大小变化/非官方跳转都会停止，无自动网络重试。

## 2. ZIP安全与原件完整性

两ZIP都以PK本地文件头及zipfile.testzip()==None验证。每个恰有同stem的CDF和HDR，无目录、绝对/穿越路径、符号链接、重复成员或加密。先检查聚合解压体积，再流式写独占临时文件，校验CRC/SHA后以同目录硬链接原子发布最终路径、删除临时文件；已有文件拒绝覆盖或独立验证复用。

全部CDF/HDR合计388878字节，小于2MiB。两ZIP加解压原件共668546字节，仅本地保存且.gitignore确认保护。

|year|member|bytes|ZIP_CRC32|SHA256|
|---|---|---|---|---|
|2021|.HDR|2757|8b35744a|273e39d4984eb61d3b88e88dae273b53828ab1e8f4ea18a54ae03a0714c2ff4c|
|2021|.cdf|191682|d2325e04|e6a03398dda6efedfb4cfc3aa8646daabc19f976911698330b41b8a6ef571b0d|
|2022|.HDR|2757|eec5461d|c0c5534a571b048eb5243dd44a52e9065cb14339139d22a1c3478b8bf51f2d53|
|2022|.cdf|191682|c73622a7|7b37f210c9b202d99212eff0fc329918b71532d4b79932655340859bd5847398|

ZIP没有单独一个“整体CRC”字段；上表是成员CRC-32，两档archive CRC检查均PASS。CDF还与HDR中Tot_Size精确一致。

## 3. CDF/HDR独立质量验证

两CDF均2880条；UTC00:00:00—23:59:30，严格30秒，无缺失/重复/倒序。time数据类型CDF_EPOCH，TIME SYSTEM=UTC；TITLE、文件stem、HDR File_Name/File_Type=DNSAPOD_2_/Mission=Swarm/File_Version0301一致，确认A产品。瞬时density单位kg/m3，纬经度deg、高度m，未以density_orbitmean替代。GRS80来自已验SHA的官方服务合同，未据此解除模型ZG门禁。

|year|records|flag0|flag1|unknown|invalid_density|invalid_coords|valid|
|---|---|---|---|---|---|---|---|
|2021|2880|2880|0|0|0|0|2880|
|2022|2880|2880|0|0|0|0|2880|

质量由原quality_mask精确flag0/1/未知码规则以及有限正密度/坐标界限计算，非假定。坐标约束abs(lat)<=90、abs(lon)<=180、0<h<2000km；异常只拒绝、不补0。2021实际高度431.540—461.531km，2022为425.309—454.802km。

两套读取入口结果一致；原始CDF直接epoch解析与独立5760条记录/坐标/flag复核通过。完整选择的产品单位和时间合同保存在CDF_contracts.json。

## 4. 分区样本量，只计数不拟合

历史窗口[15,18)：

|year|all|low|mid|high|
|---|---|---|---|---|
|2021|360|123|122|115|
|2022|360|119|117|124|

各区都达到30条门槛，无UNSUPPORTED_INSUFFICIENT_HISTORY。未来[18,19)、[18,21)、[18,24)各有120/360/720个质量有效记录；逐区数量见latitude_window_counts.csv。这些是相关沿轨样本，不是独立重复实验。没有计算任何b或exp(b)。

## 5. 原模型静态覆盖与真实沿轨覆盖分别验收

复用已生成两年B14主背景、A7/B7控制；A14完全不参与。按历史source_manifest、各组data_audit/run_status/年份inputs核对原NetCDF/source/GPI/inputSHA。真实退出码均0、4NORMAL EXIT、工程PASS。科学多变量验收未由此升级。

实际NetCDF/模型日历和CF时间核对后，每组确有目标日15/16/17/18/19/20/21/22/23及次日00共10帧。末帧真实存在，可支持23:59:30，不外推。DEN/ZG均ilev29×36×72，DEN g/cm3×1000为kg/m3，ZG cm×.01为m。目标帧显式_FillValue/missing_value/NaN/Inf/极大哨兵/DEN非正扫描均0，ZG逐列严格递增。

|year|case|role|frames|queries|success|failures|eight_columns|status|
|---|---|---|---|---|---|---|---|---|
|2021|B14|PRIMARY|10|1080|1080|0|1080|PASS|
|2021|A7|CONTROL|10|1080|1080|0|1080|PASS|
|2021|B7|CONTROL|10|1080|1080|0|1080|PASS|
|2022|B14|PRIMARY|10|1080|1080|0|1080|PASS|
|2022|A7|CONTROL|10|1080|1080|0|1080|PASS|
|2022|B7|CONTROL|10|1080|1080|0|1080|PASS|

每组首末有效查询为15:00—23:59:30。每点仍要求两个时间帧×四邻列全部有效，权重0不跳过。垂直log密度、水平密度双线性、时间密度线性均复用成熟算子。6480查询全部成功，无垂直外推，无替代密度；B14最小模型顶高余量约2021 33.667km、2022 94.944km，仅表示**Map-A条件下模型内部覆盖**，不是外部高度误差界。

独立逐条检查6480条缓存的8列和时间包围，并对18固定点直接从原NetCDF列重建模型密度，1e-13相对容差通过；这是数值一致性检查，不是模型对观测预测误差。完整缓存仅本地，不上传。

## 6. 工程异常：保留错误证据，不改原数据或门槛

1. 首次获取任务在两ZIP已下载/CRC验证成功后，错误把HDR的CRC数值当作ZIP/zlib CRC-32，因此中止。原worker真实退出1、failure.json和源快照保留。
2. 独立检查发现HDR数值分别为2091013208/1035431957，精确等于GNU POSIX cksum；ZIP CDF成员CRC-32则为d2325e04/c73622a7。新Python POSIX CRC（含长度）与GNU实现和真实HDR再次一致，ZIP/zlib校验仍单独保留。**这是算法混用修复，不是放宽校验或接受损坏文件。**
3. 后续只读本地验证未重发任何HTTP请求、未修改原件，CDF及全部模型查询通过。但末尾“NO FIT OR ERROR METRICS”的负面陈述含ERROR，触发通用TIE日志解析器误报；进程真实退出0。原local_verify监督资格FAIL/stop_reason及日志均保留，没有改成PASS。
4. 修正未来控制台措辞，另建最终受监督的独立只读审计（无网络/新模型查询），真实退出0、监督PASS、清理成功。最终数据资格基于全部原件CRC/SHA、CDF、模型覆盖及独立审计，而非推测退出码。首次和中间异常未删除。

52项当前测试通过（传输/解压12，质量14，hourly8，native18；初版11测试另保留），涵盖POSIX和ZIP区别、危险成员/跳转/截断/不覆盖与既有数值拒绝。独立审计5760CDF记录、6480缓存、18模型列重建全部通过。

## 7. 资源与执行边界

已计量核心任务合计25.973秒，包含首次失败、中间资格误报、最终受监督审计、首次独立审计和全部测试调用；峰值采样树RSS296.570MiB，报告前审计目录17.269MiB。准备/交互文件操作未逐任务计时，不冒称会话自然墙钟或连续全局RSS峰值。网络279668字节、解压388878字节，预算未扩大。

没有系数估计、未来误差/联合指标、科研结论或算法图表。无新TIE/DART/GPU/轨道/训练。原阻碍审计目录全部SHA保持，v10—v12/权重/原物理场不改；公开只含轻量代码、合同、来源、计数、覆盖和审计记录。commands/sha256_manifest提供复核入口，不能盲目重放已有执行目录。

## 8. 是否可继续

两日数据和两年主背景/控制覆盖门槛满足，**具备下一轮正式冻结v13纬度分区协议的数据条件**。本轮没有冻结或执行校正算法。3月23日Stale06系数尚未建立，必须下一轮按同日[03,06)估计并预先冻结，不借用3月24日值。

科学训练False、EXTERNAL_DATUM_UNVERIFIED、Restart一致性FAIL、DART未准入、真实轨道BLOCKED保持。2021A14工程PASS仅敏感性/2022 A14 PARTIAL历史不改。DART条件没有因下载和查询覆盖成功而满足。本轮停止，等待明确指令。
