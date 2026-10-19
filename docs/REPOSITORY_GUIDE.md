# Git仓库范围与恢复说明

远端https://github.com/hhtbbc/261016project.git，主分支main。Git元数据也位于唯一工作区内部。提交身份使用仓库所有者hhtbbc的GitHub noreply地址，仅配置项目.git/config，未修改全局Git配置。

## 入库范围

- src、scripts、tests：自研实现与实验入口。
- docs、reports、根目录进度文档：研究依据、验证结论及接续记录。
- configs、patches：依赖锁、参数、兼容补丁与外部资产清单。
- results：已有真实图表/误差CSV等轻量结果；experiments仅JSON、inp及独立Fortran检查源；logs保留JSON审计及本次31项测试日志。

不提交.venv/.venv310/.envs、缓存/临时/本机配置、data、third_party、模型权重、大型NetCDF/NPZ、对象/模块/可执行文件。所有文件仍留在原工作区，没有删除。configs/external-assets.json列出外部资产原路径、字节数，较小文件有本次SHA256；大文件未为发布重算哈希，应使用原下载manifest。这是清单，不是下载器或数据备份。

## 恢复与执行前提

本项目固定工作区/workspace/data/20261016；现有激活脚本和部分记录含该绝对路径。不能直接在另一目录运行后就宣称实验可复现。

1. 阅读AGENTS/STATUS/WORKLOG最新段；不要运行历史任务中的长期命令。
2. 恢复对应模块所需外部数据及第三方源码，按docs/RESOURCES.md、ORBIT_DATA_SOURCES.md和相关环境报告中的原始来源/清单核对SHA，不使用当前网页最新文件替换冻结数据而不记录。
3. 轨道测试需要原始SP3/TLE和冻结EOP/闰秒；2023驱动检查需要GFZ原始JSON及生成NetCDF；TIE构建需要官方2.0原树、apex归档、启动文件和项目内编译栈。实际依赖路径见相应脚本，仓库不承诺无数据即可通过全部测试。
4. 依赖由configs中的锁文件固定；Python用scripts/activate_orbit.sh，TIE用scripts/activate_tiegcm.sh。禁止全局安装/擅自micromamba create；仍需遵守外部登记限制。
5. 每次复跑使用新run-tag保留历史输出。没有授权不运行2023长段/spin-up或真实阻力对比。

## 发布检查

本次提交前检查文件大小、外指符号链接和常见凭据模式；详情logs/git_pre_push_audit.json。该模式扫描不能证明不存在任何形式的敏感信息。没有改科研代码或重跑物理实验；已有31项测试记录logs/tiegcm2023_all_tests.log随仓库保存。推送结果用远端分支SHA与本地HEAD比对，记录本地logs/github_push_verification.log。
