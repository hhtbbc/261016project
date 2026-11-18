# 新日期因果密度校正复现 V14-A

身份：NEW_DATE_REPLICATION / SAME_CONTINUOUS_TIE_RUN / HINDCAST / PROVISIONAL Map-A / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED。

## 数据、协议与实际执行

2021-03-25 Swarm A DNSAPOD_2 0301仅下载一次，140187 bytes。ZIP CRC、安全解压、HDR校验和CDF合同通过；2880条、严格30秒UTC、00:00—23:59:30、flag=0为2880条，密度正且有限。采用瞬时density（kg/m³）和既有质量规则。下载及每个原始成员SHA见observation_acquisition_audit.json；本地SHA不是发布方独立校验和。

B14、A7、B7均有00时至次日00时25个连续整点帧，实际primary边界存在。DEN/ZG位于ilev，原单位g/cm³、cm，转换乘1000、0.01。目标帧填充值、有限性、正密度、ZG单调性检查通过；6480/6480真实沿轨查询满足八列完整、禁止外推，包括零权重列。18个独立插值探针通过。源码和输入SHA可由source_manifest.json追溯。

先数据准入，再冻结协议，再历史估计全部参数并冻结SHA，再future poison test，最后评分。两个截点及全部窗口按原方案执行；18Z Stale06在每个背景单独使用当天该背景03—06时系数，不跨背景借用。每区历史N：低124、中124、高112，均满足30门槛。未来样本N=120/360/720，共同样本身份一致。未添加新算法、未改纬区或阈值。

## B14真实未来结果

正改善率表示误差下降；负值表示恶化。

|截点|方法|窗口|RMSE改善%|relative RMS改善%|联合评价|
|---|---|---|---:|---:|---|
|6Z|GlobalAdaptive06|future_1h|-2.2604|-68.9298|FAIL|
|6Z|GlobalAdaptive06|future_3h|9.3498|-50.0248|FAIL|
|6Z|GlobalAdaptive06|future_6h|12.8436|-49.5759|FAIL|
|18Z|GlobalAdaptive18|future_1h|28.0709|11.0308|FAIL|
|18Z|LatitudeAdaptive18|future_1h|46.7707|28.9818|PASS|
|18Z|Stale06|future_1h|40.1241|0.1043|FAIL|
|18Z|GlobalAdaptive18|future_3h|24.3019|-6.9908|FAIL|
|18Z|LatitudeAdaptive18|future_3h|36.0706|-15.3258|FAIL|
|18Z|Stale06|future_3h|30.4517|-33.7346|FAIL|
|18Z|GlobalAdaptive18|future_6h|24.4733|-8.9646|FAIL|
|18Z|LatitudeAdaptive18|future_6h|35.0861|-16.1989|FAIL|
|18Z|Stale06|future_6h|30.6674|-33.6428|FAIL|

B14联合评价1/12；Latitude18为1/3，只有首小时PASS。控制组A7为2/12，B7为1/12；全部背景合计4/36，仅作描述，不是36次独立实验。三个背景Latitude18首小时均PASS，3/6小时均FAIL。完整绝对指标、尾部、Bias、Pearson、log RMS及点级改善数见metrics.csv、region_metrics.csv和pointwise_diagnostics.csv。非重叠时块见time_block_metrics.csv，不能把累计窗口当独立重复。

B14系数：Global06 b=0.18989491524790836（乘数1.2091225306395847）；Global18 b=0.11627769769983942（1.1233077688083657）；低/中/高纬b=0.20197732181886607、0.1382123402349773、0.08228617552619255（乘数1.2238202537792597、1.1482193375542802、1.085766485168805）。完整三背景参数、历史身份和协议SHA见correction_parameters.json。

## 代表性及局部误差解释

06Z历史b=0.189895，未来1/3/6小时中位数=-0.011120/0.077441/0.000571，存在符号翻转或明显漂移。18Z历史b=0.116278，未来为0.128702/0.047106/0.064851，短时较接近但3/6小时漂移。未来中位数仅用于事后诊断，不参与预测。

18Z六小时低纬Raw relative Bias=-9.3378%，Global=+1.8416%，Latitude=+10.9543%；低纬relative RMS由23.1810%升至28.1820%。中高纬Latitude relative Bias也由-8.5987%/-1.5963%变为+4.9487%/+6.8434%。低纬未来残差中位数0.225127甚至高于历史0.201977，仍出现相对均值过校正，说明历史中位数偏高并非唯一机制：残差分布、估计目标与相对平方误差目标的差异仍需区分。不能从沿轨诊断分离坐标、物理结构及产品偏差的独立因果贡献。

相比3月23/24日，新日期再现“部分绝对RMSE改善而相对RMS恶化”，但增加首小时有限联合收益。3月24日未运行Latitude，图中保留N/A，不补造对照。日期相邻且同一连续运行，B14在本日06/18Z实际已积分16.25/16.75天，A7/B7为9.25/9.75天；背景标签不意味着此刻恰好14/7天。不能视为跨季节、独立模型实现或全年泛化证据。

## 独立验证与资源

37项既有测试通过（纬区14、晚间11、下载12）；独立复核15个系数、504指标行、84联合评价行（含分析和非重叠时块），rtol=1e-13、atol=0。future poison、样本隔离、原始SHA及2979个受保护旧文件SHA不变检查通过。独立验证不重新进行因果实验。

监督进程38.466秒；worker CPU23.902秒，峰值RSS331.223MiB，采样进程树峰值328.859MiB。独立核验已计入worker成本，不重复相加。实际日志及资源见resource_audit.json；新增积分/GPU/DART/轨道均0。

## 2022缺口及科学状态

2022 B14现有真实输出截至03-25 00时。完整新日缺少01时至次日00时24帧，两个注册查询跨度直接需要其中20帧，次日primary也缺失。Restart一致性FAIL，禁止未经验证续算。跨季节方案及资源依据见docs/THERMOSPHERE_MULTIDATE_DATA_EXPANSION_PLAN_V1.md，均未执行。

NEW_DATE_VALIDATION=COMPLETE只表示工程执行完成；SCIENCE_TRAINING_READY=False，EXTERNAL_DATUM_UNVERIFIED，Restart=FAIL，DART=NOT_ADMITTED，REAL_ORBIT=BLOCKED。O1/O2/N2等历史多变量门禁不变，A14不参与。Map-A有效覆盖率不是外部高度登记证明。
