# v13纬度分区校正：数据准入决策

状态BLOCKED_MISSING_HOLDOUT_OBSERVATION；未进入实验，不是方法收益FAIL。

两年3月23日官方0301产品在已验SHA的本地官方目录缓存中列示，但实际ZIP/CDF/HDR均缺。两ZIP缓存合计279668字节；本轮无下载授权，已停止，未运行拟合、未来评价或图表。

下一步只申请这两日A原件（建议新增ZIP总量≤1MiB，安全解压≤2MiB，大小/版本异常即停），详见`experiments/causal_density_latitude_v1/data_acquisition_request.md`。不是申请新模型积分。授权后先补数据、独立CDF质量验证，再检查B14/可选控制目标日模型24Z和八列覆盖，通过后才冻结纬度协议。

3月23日[03,06)的Stale06尚未拟合，不可用3月24日系数替代。所有区域N≥30及unsupported不填补规则不改。当前不能判断局地是否改进低纬、尾部或联合指标，不能借v12常数结果代替局地实测。

科学训练False、EXTERNAL_DATUM_UNVERIFIED、RestartFAIL、DART未准入、真实轨道BLOCKED、2021 A14工程PASS仅敏感性/2022 PARTIAL保留。等待用户下载授权，不自动继续。
