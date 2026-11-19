# V24：2021秋季16天真实积分与工程验收

## 一、今日完成情况

**2021真实物理积分已完成；本轮最终ENGINEERING_FAIL，原因是主工程验收器的首cold echo身份误判，不能记为完整工程PASS。**

起始本地/远端HEAD均`8f2490cdcc43a01190ebf6e0a85fefc89156f01c`。严格使用原V23发布清单和专用入口，只调用一次2021授权命令，MPI4/OMP1、STEP60；没有Restart/append、重编译、模型重试、删除预约或启动2022。真实run_id：`18726974f5d3450ba61f82c23c8da3a0`。

实际命令（执行前已source scripts/activate_tiegcm.sh）：

```bash
python scripts/execute_tiegcm_autumn_v23.py --year 2021 --authorize-16day-run
```

受控原始运行目录：`experiments/thermosphere_autumn_mareqx_config_v23/2021/actual_run/`。V24轻量证据：`experiments/thermosphere_autumn_2021_formal_run_v24/`。冻结执行器原子建立真实目录和一次性run_id，标记/退出回执/所有原件均保留；没有以换目录取得第二次启动机会。

## 二、关键技术解释

SEED_POLICY=A_MAREQX_APPROVED；mareqx原件SHA `a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7`，原生2002年第80日00:00，SOURCE_START=80 0 0未修改。目标START为2021年第252日00:00，STOP为第268日00:00。源码允许源日和目标日不同但小时分钟相同，显式SOURCE只读冷启动，不使用输出续算。

2021 GPI SHA `d401d0ae525babb343faaa6d1dd9a8d3c4fb1c2ea85beb26d2b0025cdf001b9a`；input SHA `1d73a45b25b0af5c5a70a9e5870e07589153b2789ccb3c9353cc957c742ee121`；模型ELF SHA `f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776`。全部旧源、GFZ、Swarm、GPI、V20协议及2022冻结配置身份不变。

首primary的iter=115200（80×1440）为原生源继承值，不能算作本次更新数。暖态首secondary iter=362940（252×1440+60），终点iter=385920（252×1440+23040）。真实步数同时由四rank完整每10步进度和全部UTC/暖态iter交叉确认。

## 三、实际实验与验收结果

### 真实计算与资源

| 项目 | 实测值 |
|---|---:|
| rank wrapper最早开始UTC | 2026-11-19 07:36:10.316275 |
| rank wrapper最后结束UTC | 2026-11-19 08:16:54.223115 |
| 原监督墙钟 | 2444.204256秒，即40.736738分钟 |
| MPI父进程实际退出码 | 0 |
| 四rank模型子进程退出码 | 0、0、0、0 |
| 完成步数 | 23040 |
| 模型终点 | 2021-09-25 00:00:00 UTC |
| primary记录/卷 | 17 / 17 |
| secondary小时记录/卷 | 384 / 16 |
| NetCDF文件 | 33 |
| NetCDF逻辑字节 | 3,371,588,992（3.140037GiB） |
| 全运行目录逻辑大小 | 3.147853GiB |
| 文件系统报告分配大小 | 3.148056GiB（非独占物理盘占用保证） |
| 峰值采样进程树RSS | 1,070,809,088字节，0.997269GiB |
| 子进程CPU user/system | 9019.942417 / 754.768081秒 |
| 子进程合计CPU | 9774.710498秒，约2.715CPU小时，不能当作墙钟 |
| 最低采样剩余磁盘 | 1254.856445GiB |

监督记录无stop_reason、无采样缺口，cleanup_verified=True。使用原same-UID新session采样/信号机制，shared RSS可能重复计数，不能保证捕获瞬时峰值，也不是OS硬隔离。MPI父直接wait、四rank直接子进程wait、同session身份和唯一PID均独立核验。

### 主验收与独立复核分开记录

| 检查 | 主自动验收 | 独立原始数据复核 |
|---|---|---|
| MPI父进程、四rank与run_id/session | PASS | PASS |
| 23040步完整进度与UTC | PASS | PASS |
| 全33文件、17/384记录与完整时间轴 | 首cold echo处FAIL，未完成全扫描 | PASS，全部原件SHA已保存 |
| 384小时DEN/ZG、TN/UN/VN/组分 | 主全程扫描未完成 | PASS |
| 原始GFZ与实际模型驱动 | 主全程扫描未完成 | PASS，最大差2.842170943040401e−14 |
| 全日Swarm A八列查询 | NOT_RUN | 2880/2880，失败0，检查23040列 |
| 总工程闭环 | FAIL | 原始数据检查PASS，但汇总ENGINEERING_FAIL，不替代主验收 |

独立复核逐文件读取CF/native year/day/mtime与暖态iter，核验精确小时序列和冷echo，并独立扫描全部384帧DEN/ZG的原生填值、有限正DEN、ZG垂直单调性；TN/风/必要组分、顶层合法填值、组分闭合均检查。DEN/ZG维度为time,ilev,lat,lon，单位g/cm³/cm，转SI乘1000/0.01；TN/UN/VN及O1/O2/N2/HE为float32的time,lev,lat,lon，单位分别K、cm/s、mmr。34个primary状态schema/单位/float64及有效数据也独立检查。

独立驱动参考值重新读取2021真实GFZ归档，重算中心81日Fobs均值、显式三次太阳节点插值、Kp中心线性插值及派生量，不调用主验收的最终PASS逻辑。最大绝对差：F107d/F107A/hpower/ctpoten各2.842170943040401e−14、Kp 8.881784197001252e−16，均严格小于原1e−10，未填补/平滑原驱动。

独立Swarm检查直接解析原CDF的UTC/质量及坐标；2880条均合格。按原Map-A假设独立构造GRS80→同一位置向量→WGS84及两时间×四水平邻点×垂向log插值，零权重列也检查，2880成功/0失败，无外推或删点。没有计算观测—模型误差、残差分布或拟合任何校正系数。该结果不能声称原主覆盖检查已经执行。

主审计进程退出2，墙钟0.688965秒，采样RSS约58.04MiB；冻结入口随后因审计失败退出1。这两个码不是物理MPI退出码。独立worker的原始数据检查全部通过，但因主验收未PASS而主动以2退出，监督qualification=FAIL、stop_reason=None；其自身wall=7.601326秒，监督8.242262秒，采样树峰约160.78MiB。主+独立监督合并10.250303秒；包括后续有限header诊断的只读窗口150.514647秒，低于总600秒。没有第二次主验收或模型运行。

新增只读复核器经6项合成/静态小测试验证（含NaN/Inf/填值拒绝、无启动调用、secondary单位schema正反例），不是重复V23的50项，也不是模拟日志冒充真实积分通过。版本1只读工具副本本地保留，版本2在真实审计前增加既定schema检查，代码SHA变更收据独立保存；V23冻结工具未修改。

## 四、遇到的问题：首cold echo的run_type空属性

唯一主失败项：`Illegal cold-echo exemption`。实际首primary只有一条2021-09-09 00:00记录，history_type=primary，初始year/day/mtime和CF时间全部正确，但global **run_type=''**。冻结V23代码同时要求volume=1、record=0和`n.run_type=='initial'`，因此在首卷失败，后续主全扫描与主查询未执行。没有NaN告警误杀，此次warning_count=0。

实物对照：

- 本轮primary_001：run_type空，mtime252 0 0，cold iter115200。
- 本轮暖态primary_002、primary_017及secondary卷：run_type=initial，暖态iter与日历一致。
- V16旧春季primary_001同样run_type空；原mareqx源文件自身run_type=initial。

源码证据：hist.F的hist_initype初始化run_type为空；output.F首步走copyhist源结构，绕过常规define_hist，而后者才显式设run_type='initial'；nchist.F按结构写属性。由此可见首echo和普通暖态输出的元数据路径不同。空属性本身不证明模型是非法续算，也不能只用该字符串判定完整cold身份。

这些是只读诊断依据，**本轮未修改判据、原文件、冻结工具或结果以求PASS**。第一份acceptance和所有失败/预约完整保留。独立原始检查PASS与主FAIL不一致，最终按授权规则记ENGINEERING_FAIL。

`result.json`最初汇总只从主全扫描取记录数，因此记录数为空，含义是主检查未完成；保留它，并以`result_final.json`明确引用独立真实17/384记录，不伪造主验收成功。V23静态admission及执行器验收前NOT_RUN阶段收据也保留，不改历史。

## 五、当前项目状态

- 2021物理积分：COMPLETED，单次、23040步、真实终点正确。
- 2021正式工程闭环：ENGINEERING_FAIL，待新的只读修复任务。
- 2022物理配置保持原SHA，未启动；原执行门禁要求2021主验收PASS，因此当前不能直接运行2022。
- 原161项受保护资产不变，33输出SHA详见model_output_manifest.csv。所有NetCDF、CDF、完整日志仅保留本地。
- SEED_POLICY=A_MAREQX_APPROVED有效。AUTUMN_ADAPTATION_UNVERIFIED、FOURTEEN_DAY_SPINUP_NOT_PROVEN_CONVERGED、EXTERNAL_DATUM_UNVERIFIED、Restart=FAIL、SCIENCE_TRAINING_READY=False、DART=NOT_ADMITTED、REAL_ORBIT=BLOCKED保持。

模型工程数据的独立检查通过不证明14天预热充分、外部ZG零面正确、密度精度达标或观测校正有效。本轮没有密度评分/历史系数计算，没有GPU、AI、DART、轨道传播或数据下载。

## 六、下一步计划

建议下一轮先明确授权**保护V24原件的只读冷echo验收修复与一次复验**，不需重新积分。版本化适配应综合源SHA、冷启动配置、真实退出、首记录初始日历、原生继承iter及状态身份，不可把所有空run_type/暖态缺失一律放行；增加真实冷echo最小fixture和伪造身份/暖态异常反例，原数值门槛不变。

2021主验收与独立复核闭环后，再单独申请2022秋季16天积分，并先审查其执行器绑定的同类验收问题；不能直接用旧工具重现相同误判，不能改2022物理input/GPI或根据2021密度误差调方法。原执行器硬编码读取旧2021验收路径，因此新覆盖层还须绑定新版闭环证据路径/SHA，不能改写V24旧FAIL。具体下一步见[处置决策](../docs/THERMOSPHERE_AUTUMN_V24_POSTRUN_DECISION.md)。本轮停止，不自行修复或启动后续计算。
