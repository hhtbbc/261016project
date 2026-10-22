# Jan4四模型连续12小时预注册（2026-10-22）

固定2023-01-04 01→13 UTC，4官方模型各12真实forward，48总计；History额外真实00/01，其他真实01。未来物理状态只评价，逐步aux/scalar按作者方法给定，HINDCAST / TIEGCM_REFERENCE_ONLY。原权重/static及原源码/隔离log兼容层不改。非训练消融，不拟合2023统计，不运行Mar24/24h/TIE/RK45。

新增08—13六NPZ，官方ZIP目录/206/Content-Range/CRC/SHA/14字段/正DEN与TN/ZG递增检查；网络25MiB硬限。复用已有00—07，原件只读。沿用保守GPU600秒、RAM4GiB、新文件800MiB、空闲磁盘20GiB门禁；当前授权原文在Mar24设计节截断，未增加任何模型执行范围。依据历史48forward含I/O约40秒/392MiB，当前48forward预计240秒内、700MiB以内，是预算估计而非实测。

12步CPU实际作者循环合成四模式未来真值毒化通过后才正式GPU。不额外真实预检，不重跑旧6h。每个模型只启动一个完整12步连续序列，独立初始化。前6步hooks对历史6h的实际输入、scalar、raw网络输出、归一化预测state要求逐元素完全一致（比旧指标容差更严格）；means/stds亦精确匹配。若失败立即终止，留失败前缀、不正式评价、不重试。不是拼接两个6h任务，不在+6h输入真值。

每步finite、DEN正、TN正，异常停止不clip。全12步反馈/History滚动/Flow normalized增量/log10与pow10保持原义。原生指标沿用rtol2e-5、RMSE atol1e-25、ACC atol2e-6；公共物理独立NumPy加权求和rtol1e-12。DEN g/cm3→kg/m3×1000，风cm/s→m/s×.01，Z位势高度cm→m×.01。普通物理climatology与固定真实01持续性共同评价；log native ACC/dex分表。

报告所有lead1—12、六变量各自SI、DEN逐层/极区/顶部/固定upper20—28、参考ZG全球中位400—500km层组（不是固定几何450km），同时报告相对与绝对误差、偏差、1/2/3/6/9/12时效及6→12增长。不得以单窗口排名当泛化/独立观测大气或卫星轨道精度。Mar24只设计后续6帧及12h检验，不获取或执行；训练资源只读审查。所有历史SHA受保护，任务后安全Git同步，完成即停止。
