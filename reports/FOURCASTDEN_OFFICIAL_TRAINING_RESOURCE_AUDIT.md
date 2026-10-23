# FourCastDEN官方训练资源核查（2026-10-23）

## 实际访问与身份

本次直接HTTP API读取[软件概念记录22250237](https://zenodo.org/api/records/22250237)最终跳转[版本22250238](https://zenodo.org/records/22250238)，HTTP200；[数据21859635](https://zenodo.org/records/21859635)HTTP200。resource_http.json保存实际URL/HTTP/字节与SHA，原JSON随审计保留。软件概念DOI不等于版本号；两记录metadata.version都未提供字符串，不杜撰v1，version关系index0/is_last=true是此次API返回快照。

软件标题AFNO Software for TIE-GCM-Based Multivariable Thermospheric State Forecasting，作者Zhou, shuyang与He, Changyong，发布日期2026-09-02；数据标题2023 TIE-GCM Simulation Dataset for AFNO Inference Evaluation，作者He, Changyong与Shuyang, Zhou，2026-08-09。软件说明明确用途为模型实现、推理、评价和配套权重/统计，配合2023测试数据；数据说明明确是模拟参考，不是独立观测验证。两个API未列论文DOI的related_identifiers，不能声称元数据双向绑定已完整证明。

论文DOI[10.3390/rs18183134](https://doi.org/10.3390/rs18183134)直接MDPI页面及XML实际HTTP403，网页工具另遇429，均不伪称全文已读；Crossref官方登记API HTTP200，标题与用户所指一致，作者Shuyang Zhou/Changyong He/Dunyong Zheng/Dongfang Lin，与Zenodo前两作者对应，abstract说明2000—2023模拟/四变体/2023给定驱动测试，支持资源与研究主题一致。Crossref主资源和PDF链接仅指MDPI，未提供另一训练仓库。全文其他资源声明因访问限制未重新核实，不能断言不存在任何其他官方训练地址。

## 当前公开文件完整清单

|记录|文件|字节|官方checksum|
|---|---|---:|---|
|软件22250238|static.zip|2378058|md5:11c1f8f7bd2295d765151a2d0f88d028|
|软件22250238|FourCastDEN.zip|90106|md5:8d8fd015f933455c74e0610d864664f0|
|软件22250238|static_log.zip|2296512|md5:31df713b0b31502d02c37ddf24a0c937|
|软件22250238|checkpoint_files.zip|2901442296|md5:78aa5107bf60927e6898cb19449520b7|
|数据21859635|2023.zip|18149758909|md5:0117ddd388ae162798fa460502f4c93c|


本次只获取小元数据/文本，没有下载上述大型档案或任何训练数据。软件Apache-2.0、数据CC BY4.0、access_right=open来自当日API。source zip本地原件MD5与当前官方清单完全一致（official_source_inventory.json），实际检查归档全部成员和已解压源码，无train_tiegcm.py/完整训练入口/四变体活动训练YAML/学习曲线。普通static/static_log及四checkpoint是既有官方资源，继续只读；checkpoint_files.zip本次不重取，不能用仅检查内部checkpoint SHA等同重新验整个2.9GB归档MD5。

原包README_inference_2023明确不提供训练/验证数据及重训说明。models/model_module.py保留training_step/optimizer片段，但forward要求(value, flow)+warp，与已验证AFNONet(x,4scalar)直接171输出不兼容；config/AFNO.yaml有注释训练配置和活动推理项，不能当作四checkpoint的完整实际训练协议；dataset注释指向缺失train_tiegcm.py/SAMPLER_PERCENT。NVlabs AFNO仅为架构来源，不冒充TIE专用训练入口。

## 分级结论

A：没有取得并验证完整官方训练主程序；B：论文/登记摘要支持多年数据训练与2023独立测试描述，但2000—2021及2022数据、完整协议不在当前文件清单，不能声称可下载；C：已读推理包中的残留训练片段；D：本次自有src/training为独立重建工程，合成测试成功，不称完整论文训练复现。

当前记录没有公开非2023小时文件/训练数据清单或专门申请入口；需要向作者取得许可、精确版本及小样本位置，本次没有发送联系消息。记录公开并不等于训练集可取得或可拿2023替代。缺四变体实际损失/纬度或通道权重、优化器/调度、采样/seed、统计年份与掩码、AMP/裁剪/恢复、原学习曲线和数据SHA。其他未知项保持未知。

## 许可与代码复用

官方软件记录声明Apache2.0，数据CC BY4.0；原源码包根目录未找到LICENSE，afnonet.py引用NVlabs/AFNO-transformer，后续再分发完整第三方代码需确认原始文件及notice链。本次不复制或修改作者代码，只导入已有只读Linux副本。独立工程使用现有torch2.4.1(BSD-3)、numpy1.25.0(BSD-3-Clause)、timm1.0.13(Apache-2.0)、einops0.8.0(MIT)，许可证字段来自已安装包metadata；未新增依赖。数据许可不自动扩展到尚未提供的训练资料，未来先确认。
