# Satellite-AI
基于 AI 热层物理场预测的单颗低轨卫星轨道预测研究原型。
唯一工作区：`/workspace/data/20261016`。

## 接续入口
依次阅读 AGENTS.md、STATUS.md、WORKLOG.md；环境报告见 reports/ENVIRONMENT_2026-10-19.md，资源核验见 docs/RESOURCES.md，日程见 docs/PROJECT_PLAN.md。

```bash
cd /workspace/data/20261016
source scripts/activate.sh
python --version
```
当前 .venv 为 Python 3.12.3 的隔离基础环境，不含 pip 和科学计算包，不是 FourCastDEN 运行环境。作者环境为 Python 3.10.14，需后续分析兼容方案。没有执行推理、训练或轨道实验。
项目按“学习原理—代码实现—运行实验—验证结果—记录成果”推进；初始化完成后等待用户下一条指令。

## 2026-10-19正式工作新增入口
已建立项目内Python3.10环境：`source scripts/activate310.sh`。旧.venv保留作初始化记录。源码分析、学习笔记、最小数据方案及环境报告分别见docs/FOURCASTDEN_CODE_ANALYSIS.md、docs/learning_notes/FOURCASTDEN_INTRO.md、docs/MINIMAL_INFERENCE_PLAN.md、reports/FOURCASTDEN_ENVIRONMENT.md。最新运行状态以STATUS.md最后一节为准。

## 2026-10-19早会路线更新（当前入口）
第一阶段已调整为Swarm-A SP3参考下的SGP4、经验大气+RK45、TIE-GCM2.0+RK45对比。此前FourCastDEN成果保留，训练不启动；详见docs/UPDATED_RESEARCH_PLAN.md和STATUS.md末节。
已取得同星SP3/TLE，并提供src/evaluation/sp3_reader.py、scripts/inspect_swarm_sp3.py与概览图。当前没有轨道传播或TIE-GCM仿真结果；不要把数据读取图当预测轨迹。

## 2026-10-20：已完成SGP4/SP3基准
轨道环境入口：`source scripts/activate_orbit.sh`。实验入口scripts/run_sgp4_comparison.py先`--cadence 300`再`--cadence 60`，复跑指定新的`--run-tag`以保留输出。报告reports/SGP4_SP3_BASELINE_2026-10-20.md，完整运行说明/限制和文件路径见报告；当前基准为历史单TLE对照，尚无RK45/TIE-GCM实验。


## 当前版本与GitHub交付

最新进展以STATUS.md末节为准：已完成SGP4、两体RK45、J2、合成阻力测试，以及TIE-GCM2.0默认2002算例和2023适配准备；尚未运行2023真实场/spin-up，也未闭合Swarm真实Cd/面积参数。上文各日期入口保留为历史记录。

仓库：https://github.com/hhtbbc/261016project

仓库包含自研代码、配置/补丁、文档、实验图表和轻量审计结果。环境、缓存、模型权重、外部数据/第三方完整源码、编译产物和大型实验状态文件留在原工作区；克隆仓库不是完整数据备份。资产清单见[configs/external-assets.json](configs/external-assets.json)，恢复要求见[docs/REPOSITORY_GUIDE.md](docs/REPOSITORY_GUIDE.md)。本项目未为既有第三方资料重新授予许可证，沿用各原始来源的许可条件。


## 最新：跨日/Restart验证在静态阶段受阻

2023十分钟启动通过后，23:50跨日计划发现原源码要求START与SOURCE_START时/分一致，而现有完整restart没有23:50记录。因此本次0模型启动，未验证跨日/续算；42项单元/静态测试通过不代表Restart工程门禁通过。见[阻碍报告](reports/TIEGCM2023_RESTART_VALIDATION.md)和[spin-up就绪决策](docs/TIEGCM2023_SPINUP_READY.md)。需合法23:50主历史或另授权额外准备运行；不自动执行多日spin-up。


## 最新：合法2023检查点已生成，连续跨日通过

已完成唯一一次2023-03-18 00:00→03-19 00:10诊断，1450步/155.01秒，模型原生生成23:50单记录完整checkpoint，解决此前缺少合法源时刻的静态阻碍。实际跨日驱动/基础字段检查通过、50测试通过；尚未运行Restart分支或验证连续/分段一致性，更不是spin-up收敛。详见[跨日报告](reports/TIEGCM2023_CROSSDAY_DIAGNOSTIC.md)和[后续续算方案](docs/TIEGCM2023_RESTART_NEXT_STEP.md)。大型NetCDF仍在原工作区，Git不包含检查点本体。

最新验证：原生continuation B1正常退出，但连续/分段状态超过预注册容差，B2未运行，正式分段spin-up仍暂停。详见[续算验证报告](reports/TIEGCM2023_CONTINUATION_VALIDATION.md)。新增56项测试通过，不能据此声称模型数值续算等价。
