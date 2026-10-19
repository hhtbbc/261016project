# 合法23:50检查点后的续算方案（待新授权）

## 当前已具备

一次2023连续24h10min诊断已成功，1450步，实际155.0144s、采样RSS945.07MiB、NetCDF87.807MiB。合法checkpoint位于experiments/tiegcm2023_crossday_24h10_v1/primary_002.nc，2023-03-18 23:50；34项完整float64状态及_NM/下边界、时间属性检查通过；SHA `d0aab5804eeab7680977f0fa9ad1de165600fd884bde2ddc1e0c6754c5ab9a4f`。模型直接以MXHIST_PRIM=1写单记录文件，无未来记录、无裁剪/重标/补造。相邻primary_003/004分别是午夜和00:10连续参考。

这些原生primary满足源码continuation的格式/选中记录前提；**尚未实际恢复，不称已通过连续/分段一致性**。当前完整primary已解决上次缺23:50源时刻的静态阻碍，不能继续使用旧报告的“无23:50”作为最新状态。

## 建议下次只申请两个短分支

B1：独立新目录，将primary_002.nc整文件字节复制为branch_primary_001.nc，核对源/副本SHA一致；原checkpoint不改。省略SOURCE与SOURCE_START，START_YEAR2023、START_DAY77、START77 23 50、STOP78 0 0、HIST0 0 10、STEP60、MXHIST_PRIM3，OUTPUT指向副本。模型原生readsource会在OUTPUT找START记录并APPEND，initial_year/day/mtime保留77 0 0。

B2：B1完成并通过场/驱动/完整性与连续午夜状态核查后，独立新目录复制其完整主历史。只有当最大记录时间<=START78 0 0时允许恢复；START_YEAR2023、START_DAY78、START78 0 0、STOP78 0 10，其余共同设置，仍省略SOURCE。B1副本可含23:50和00:00两条过去/当前记录，但不能含00:05或00:10未来记录。

两段均复用同一可执行/GPI/网格/受力无关物理配置/4rank/60s，禁止固定F107/F107A/KP/POWER/CTPOTEN。SOURCE显式读取属于initial/new-source语义，不以其成功代替严格continuation。不要把连续参考primary_003/004复制进可写OUTPUT列表，否则可能引入未来记录或覆盖参考。

模型写原始独立checkpoint的副本，只能更改副本以追加后续记录；保留原文件SHA，结束重验。副本应为可写模式，原物理变量、_NM、时间属性和dtype在复制时必须逐项/哈希不变。全文件复制不是重构物理状态或伪造_NM。

## 比较与门禁

- 在恢复前查source结构/经纬度/lev/ilev/单位/time.initial_*，所有预报/前一层/下边界齐全，精确选中START，不允许未来记录。
- B1起点与primary_002完全对齐；终点与primary_003比较；B2起点与B1午夜/primary_003比较；终点与primary_004比较。连续参考只保存上述三个共同历元，不能声称可比较未保存的00:05逐点状态。
- 比较34项完整主状态，及实际双方都保存的DEN/ZG/TN/风/组分；先统一SI和时标，正确掩码，不对不同历元求差。沿用experiments/tiegcm2023_restart_static_v1/comparison_rules.json预注册阈值，内部其他变量需按真实单位补充门槛后再启动。
- 特别检查_NM、init/restart两条路径重新初始化、apex映射/太阳/GSWM/电势等派生量；明显偏差停止调查，不能事后加大容差通过。
- 记录边界初始驱动来自暖checkpoint还是后续GPI更新；本例冷00:00 echo带旧iter115200/F10770，不作为跨日步数误差依据。目标暖checkpoint iter112310正确，午夜/末点112320/112330应连续。

## 资源候选与后续spin-up

两个10分钟分支预计各数秒、4rank/RSS约1GiB，建议90s/次、聚合RSS16GiB、余盘20GiB、总输出512MiB。预算需包含checkpoint副本，按本例17MB单帧与约8MB诊断帧，初步预留不超过约200MiB；实际配置确定后重新估算。没有在本任务启动任何分支。

通过续算门禁后再申请3/7天候选预热与共同48h评价；旧单日预算可作为初估，但输出频率改变会大幅影响文件量，不能用本次稀疏87.8MiB简单乘多日。应重新核定检查点/必要字段的时间分辨率、资源上限及异常停止，验证初猜依赖和收敛。

## 科学限制

当前没有spin-up收敛结果，没有独立观测检验。末段原生顶高545—677km对Swarm高度量级有利，但不是03-21—23全轨道有效率，ZG/WGS84关系仍未闭合。Cd/迎风面积/机动记录和其他未建模轨道力未完成。不能以跨日成功声称真实密度或轨道精度改善。当前模型启动额度已用完（一次），到此停止。
