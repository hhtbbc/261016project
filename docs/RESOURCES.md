# 资源核验：2026-10-19 UTC

## 论文
https://doi.org/10.3390/rs18183134 ，题名与用户提供一致；Crossref API返回200，网页搜索读取到MDPI全文与数据可用性声明；本机直接访问DOI和MDPI返回403。网页工具直接打开DOI也失败，不能把这一失败解释为论文不存在。
原文：https://www.mdpi.com/2072-4292/18/18/3134 。原文声明公开源码、配置、权重、预处理、训练/推理脚本和测试集，但实际归档的范围必须另行检查。

## Zenodo实际清单
软件概念DOI https://doi.org/10.5281/zenodo.22250237 重定向至 https://zenodo.org/records/22250238 ，页面/API均200。
数据 https://doi.org/10.5281/zenodo.21859635 页面/API均200。

| 文件 | 字节 | 核验级别 |
|---|---:|---|
|FourCastDEN.zip|90106|实际下载，MD5与Zenodo一致，ZIP目录/README/配置静态检查|
|static.zip|2378058|API列出，未下载，内容未验证|
|static_log.zip|2296512|API列出，未下载，内容未验证|
|checkpoint_files.zip|2901442296|API列出权重包，未下载/未加载，内部文件与兼容性未验证|
|2023.zip|18149758909|API列出测试集，未下载/未打开；超过5 GB，需单独批准|

代码原包 third_party/FourCastDEN.zip；完整清单 logs/source_archive_inventory.txt；原始HTTP结果 logs/resource_checks.json；API响应 logs/resource_3.txt、resource_4.txt；Crossref logs/resource_6.txt。README和配置保留在 docs/upstream/，均未执行。

## 实际发现与复现风险
- 源码包存在模型、数据加载、推理/评估目录及配置；README明确只支持2023推理，不包含训练代码、训练/验证数据和重训练说明。因此与论文广义资源声明有范围差异，不可称训练过程已可复现。
- environment.yaml 为 Windows 导出的 Python 3.10.14 / PyTorch 2.4.1 / CUDA 12.4 环境，带win-64构建、D盘prefix及大量其他包。不能在Linux原样安装。当前3.12基础环境兼容性尚未验证。
- AFNO.yaml含Windows绝对路径，默认flow=True；Direct基线需对应修改flow=False，并匹配权重、history、log_DEN及归一化文件。
- README指出两个可选绘图/比较模块缺失；需后续逐项核对import和最小修复，不在初始化运行源码。
- README说明 --weights 与 best_checkpoint_path 应保持一致，实际加载来自配置。
- 权重和数据只核验到归档清单，没有进行内容校验、加载或推理，不能宣称直接复现成功。
- 论文结果基于TIE-GCM参考与已给定的未来外部驱动，不构成真实热层观测或轨道预测精度验证。

## 2026-10-19正式任务增量核验
此前清单级状态仅代表初始化时刻。现已保留原包于data/raw并安全解压；源码含训练相关片段和数据预处理脚本，但缺完整训练入口。可选绘图模块缺失的导入在当前eval入口已经注释。
Range请求实测206，已提取三个连续小时真实样本并校验成员CRC，未下载完整测试集。当前测试归档为18,149,758,909字节，未核实81.5GB说法。static/static_log已下载并通过MD5；权重最终状态见logs/artifact_downloads.json。更多分析见FOURCASTDEN_CODE_ANALYSIS.md与MINIMAL_INFERENCE_PLAN.md。

正式任务最终状态：static/static_log/checkpoint_files三包全部MD5匹配；四个权重成员SHA256保留，Direct结构加载与一次真实推理通过，其余变体未运行。初始“未下载/未验证”表格为初始化历史状态，当前以logs/artifact_downloads.json、checkpoint_inspection.json、minimal_validation.json为准。
