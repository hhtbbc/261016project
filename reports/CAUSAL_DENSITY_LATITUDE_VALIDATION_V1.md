# v13纬度分区校正：独立日期观测门禁审计（未运行实验）

状态：`CAUSAL_DENSITY_LATITUDE=BLOCKED_MISSING_HOLDOUT_OBSERVATION`。本轮没有生成局地/全局/Stale系数、误差指标、联合通过率或科研图。

## 已核实

- 起始本地与远端main均b3e4fc1a31dbc5a6c674be8915e3dd356ce74bbc。
- v10/v11/v12及下一阶段计划已读取；v12公开产物SHA保持。历史未跟踪同步日志不覆盖。
- 全工作区文件名扫描没有找到两年3月23日目标0301 ZIP/CDF/HDR；已检查用户指定raw目录。
- 两份旧listing.json的SHA与各自历史HTTP200下载凭证精确匹配；它们列出目标两产品及官方路径。这里只证明**已有官方目录缓存中的存在记录**，未联网确认当前存在性，不把缓存大小当新下载实测。
- 目标CDF未取得，不能核验其UTC、采样、单位、flag、经纬高、2880有效记录或生成CDF SHA。3月24日数据不是3月23日的替代。

## 当前缺口

- 2021-03-23：`SW_OPER_DNSAPOD_2__20210323T000000_20210323T235930_0301.ZIP`，缓存ZIP140271字节；CDF/HDR及ZIP本地均缺。
- 2022-03-23：`SW_OPER_DNSAPOD_2__20220323T000000_20220323T235930_0301.ZIP`，缓存ZIP139397字节；CDF/HDR及ZIP本地均缺。

## 停止边界

按本轮2.2条款，观察数据门禁失败后即停止，不进入第二阶段冻结，不对原NetCDF做目标日查询或拟合/评价。不自动换日期、不下载，不使用2023场。模型记录提示候选日可能覆盖，但本轮**未完成其目标日24Z/字段/8列沿轨验收，不能写PASS**。

预定三纬区边界/中位数/联合四标准仅保留用户设计，尚未冻结执行；无校正参数可回答局地收益。本轮A—H科学问题全部NOT_EVALUATED；DART仍NOT_ADMITTED，RestartFAIL、外部高度未验证、科学训练False、真实轨道BLOCKED、2021/2022 A14历史资格不改。

## 交付和下一步

实际交付为preflight、candidate_holdout_audit、source_manifest、data_acquisition_request、resource/commands/SHA及本阻碍报告。不存在frozen_protocol、correction_parameters、metrics或图表，避免用空壳/合成数据冒充验证结果。

待用户授权仅取得两日A产品，完成SHA/CRC/CDF质量，再做模型门禁及协议冻结。区域N不足30仍拒绝，3月23日Stale06不得借用3月24日系数。具体预算和来源见实验目录data_acquisition_request.md。历史数据/代码/结果不改。
