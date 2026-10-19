# TIE-GCM 2.0最小执行与2023过渡方案

本文件是本阶段最新执行方案；早前docs/TIEGCM_MINIMAL_RUN_PLAN.md保留历史状态，不覆盖。当前真实运行证据见reports/TIEGCM2_ENVIRONMENT.md。

## 已完成的最小链路

完整官方2.0标签源码→项目内GNU12/OpenMPI5/NetCDF/ESMF栈→三个明示源补丁及一个局部F77接口兼容选项→5°/60 s编译链接→4rank的10分钟冒烟→官方2002春分低太阳默认单日→DEN/ZG/温度/风单位、掩码、CF时间和垂直单调性检查。

官方单日只耗152.249秒，returncode0，2个输出文件共226636752字节；没有运行2023场或多年数据。该链路仅验证运行和输出结构，未做发布benchmark逐场回归。不能把当天的2002数值场重新标上2023日期使用。

## 前缀和依赖复现

- 环境.envs/tiegcm，缓存.cache/conda/pkgs，根前缀.local/mamba，MPI临时.tmp/mpi，编译/输出experiments/各独立tag。
- 先source scripts/activate_tiegcm.sh；不要全局安装、不使用原NCAR/csh作业提交脚本。
- 包锁configs/tiegcm-stack-explicit.txt，共74包/约252 MB；原micromamba包元数据及SHA在data/raw/tiegcm_environment/。包已缓存，可用scripts/install_tiegcm_stack.sh对现有项目前缀离线安装。
- 严禁使用micromamba create直接照搬：它曾意外登记/root/.conda/environments.txt。项目脚本手动创建内部conda-meta/history后使用install；这条路径已核对官方源码和外部文件前后SHA。注册行的外部清理仍单独等待用户授权。
- 下载包后先审计post-link脚本和总量/最大单包，再安装。环境变量不重设HOME/CODEX_HOME；不运行shell init。若更换新依赖版本，需要重新审查ABI和短例，不把当前成功推广到任意组合。

## 可重复编译与短例

```bash
cd /workspace/data/20261016
source scripts/activate_tiegcm.sh
python scripts/build_tiegcm2_workspace.py --build-tag tiegcm2_build_next
make -j2 -C experiments/tiegcm2_build_next all > logs/tiegcm2_build_next.log 2>&1
python scripts/run_tiegcm2_smoke.py --build-tag tiegcm2_build_next --run-tag tiegcm2_smoke_next --ranks 4
python scripts/inspect_tiegcm_outputs.py tiegcm2_smoke_next
```

短例模拟10分钟、墙钟上限60秒，原默认物理驱动不改，只缩短STOP并提高诊断输出频率。经资源测量后，官方完整单日命令如下；只在需要复现时执行，不由本计划自动触发：

```bash
python scripts/run_tiegcm2_smoke.py --build-tag tiegcm2_build_next --run-tag tiegcm2_default_next --ranks 4 --minutes 1440
python scripts/inspect_tiegcm_outputs.py tiegcm2_default_next
```

单日上限300墙钟秒，保留原STOP80→81、HIST日输出、SECHIST小时输出；不是把短例5分钟历史频率扩成整天。每次用新tag，防止覆盖和复用不兼容模块。遇到timeout/error先保留日志与部分产物，不能把未完成文件当成功数据。本次单rank60秒限时未完成，默认采用已验证4rank，不假设任意rank都成功。

## 输出读取与插值接口前的门槛

1. 用CF time.units、year和mtime独立核对UTC年/日/时分，检查连续性、结束时刻与输出频率。不能仅看文件名日期。
2. DEN为(time,ilev,lat,lon)，g/cm³乘1000→kg/m³；ZG同ilev，cm乘0.01→m。Z为位势高度，不等于ZG。lev/ilev是无量纲压力坐标，不是km。
3. TN/UN/VN通常在lev；TN K，UN/VN cm/s→m/s。填充值按变量dtype正确掩码，不能把约1e36当有效值；本次次历史顶层标记存在dtype问题，自动掩码不可靠，已经用显式检查处理。
4. density_interface提供WGS84经纬高，但TIE-GCM采用其模型地理网格和ZG约定；必须核对纬度/高度基准。建立独立坐标适配，并记录模型几何高度与椭球高的差异，不在当前通用接口中偷换概念。
5. 横向经度周期处理，极区有规则；时间插值不越界。垂直按每个时空列的ZG寻找包围层，在明确有效区间内可对正密度取log-linear，并用保留样本检验；风速不能取对数插值。
6. 检查每个查询的可用顶层。默认2002场部分列顶约449 km，低于Swarm-A约460—490 km，因此本次不能完成全窗口有效密度查询。禁止把顶层值沿高度常数延伸或无说明指数外推。
7. 若超顶，先研究官方网格/顶边界及适用性：改变顶层会影响模型状态/稳定性与spin-up，必须新配置验证；不能临时补一个无依据密度公式冒充TIE-GCM。

## 转向2023-03-21—23之前

- 按[HAO官方通知](https://www.hao.ucar.edu/modeling/tgcm/index.php)更新2.0的2015后IGRF问题。此前已保存官方更新apex文本，尚未应用。本次2002算例不受该未来年份问题支配。
- 在新工作副本/覆盖层核对更新apex.F90接口及依赖、所含IGRF有效年份；若替代原apex.F，Srcfiles必须仅保留一个版本，避免同名模块/对象重复。记录提交SHA、补丁与编译/时标测试，不能直接把master或3.0称为纯2.0。
- 准备完整restart/初始场，不能用FourCastDEN预处理NPZ替代。默认低太阳2002启动场与2023实际太阳/地磁/成分不匹配；即使起始年设2023也不意味着已达到真实环境。
- 制作覆盖spin-up和窗口边缘的GPI驱动，匹配src/gpi.F实际变量year_day、f107d、f107a、kp(8,ndays)和时间插值需求。现有旧GPI文件只到2017，不可用于2023。
- 可复用已取得的GFZ支持数据：Fobs/Fadj 2023-01-31—05-05，Kp 03-12—25；路径/质量见logs/meeting_driver_audit.json。需先选择正确太阳通量约定、81日均值、Kp/Ap映射/时滞和缺测策略，再生成NetCDF；没有静默混用Fobs/Fadj或Kp/Ap。
- Heelis若由GPI/Kp驱动，则不能保留固定POWER/CTPOTEN掩盖时变地磁条件。GSWM为气候态下边界，不等于实际下层天气，研究中应明示。
- 居中81日均值和未来真实驱动使实验成为给定事后驱动的hindcast，而非自主运营预测；不得利用未来SP3校准气动参数。

## Spin-up：验证而不是规定一个万能天数

官方默认场即使可读/正常启动，也不是2023平衡场。可设计3天/7天作为后续资源受控候选，二者在同一评价起点使用相同实际驱动；比较密度、温度、主要成分/风场和沿轨密度的差异及全局量趋势。不能因为真实地磁活动使场随时间变化就强迫其平稳，也不能把一日自然变化小当作初态记忆已消失的证明。

最好增加两种合理初始场、相同驱动的收敛对照；例如预先设定沿轨密度差5%为待验证工程门限（不是官方保证或本次已通过指标），并报告统计量与相对观测误差的敏感性。根据结果决定是否需要更长预热；未评估墙钟、内存和输出前不自动延长或生成长期数据。评价窗口只使用spin-up后记录，并与初始化/校准区间隔离。

## 下一次最小工作顺序

先完成Swarm参数/推进器/姿态质量的解释，同时对当前默认例做基准回归/必要的重启一致性验证；再单独授权2.0官方地磁更新与2023驱动制作。之后才申请有限spin-up/真实日期试验、检查高度覆盖并开发TIE密度适配器。不得跳过这些步骤直接把默认2002场输入2023轨道并声称精度改善。
