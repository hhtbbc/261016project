# V17后续决策：申请既有2022-03-25真实密度误差评价

V17完整工程验收与独立复核通过；V16原ENGINEERING_FAIL和失败记录保留。原35个NetCDF、原CDF/GPI、输入、初态、二进制及所有冻结代码不变，没有新积分。

可以申请下一轮在显式Map-A假设下进行固定协议误差评价。工程方面无需重跑17天模型，也不需要修改原始missing_value属性。当前新审计入口是既有结果的独立只读版本，不能据此自动改造或重跑旧物理启动入口。

下一轮须另获明确授权，依次：

1. 核验V17验收/代码与原始输出SHA；载入2022-03-25 B14及Swarm A共同合法样本ID。
2. 保持原frozen_evaluation_protocol.json不动；06Z历史[03,06)，18Z历史[15,18)，未来累计1/3/6h和不重叠块。
3. Raw、GlobalAdaptive06/18、LatitudeAdaptive18、同日06Z Stale按原协议。低/中/高纬abs(lat)<30、30≤abs(lat)<60、≥60；历史/评价区域N≥30，无系数fallback，无新估计器/参数。
4. 所有真实系数只从历史生成，先独占写入并冻结SHA，再future poison。06和18的毒化分别按各自截点，不能污染18历史再误判泄漏。
5. 全方法共同样本ID/掩码，完整报告绝对RMSE、relative RMS、relative P95和低纬relativeBias四项联合判据。不能挑时段、删不利点、改阈值或以RMSE单项宣布成功。
6. 2021-03-25已有B14结果只读对照，不重拟合；2022为已预注册额外研究日期，不是盲测。保留沿轨相关性和跨季节覆盖不足限制。

后续科学高度登记、组分/预热充分性、观测产品独立性等问题仍未闭合。SCIENCE_TRAINING_READY=False、EXTERNAL_DATUM_UNVERIFIED、RestartFAIL、DARTNOT_ADMITTED、REAL_ORBITBLOCKED不变。不自动进入评价、校正、DART、AI或轨道。
