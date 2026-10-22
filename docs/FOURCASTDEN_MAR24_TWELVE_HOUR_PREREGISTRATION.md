# Mar24四模型12小时执行预注册（2026-10-22）

本次新授权只执行2023-03-24 01→13，四官方模型各连续12步/共48forward。History真实00/01，其他真实01；逐步预测反馈，不重置/拼接，无未来物理真值泄漏。Flow normalized增量、log10/static_log/pow10原义不变，原源码/权重/统计不改。HINDCAST / TIEGCM_REFERENCE_ONLY。

补08—13六NPZ，25MiB网络硬限，先目录压缩大小+2MiB冗余检查，再206/Content-Range/CRC/SHA/14键/形状/finite/哨兵/正DEN和TN/ZG单调核验；00—07只读。已有Jan4实测39.44秒、约361MiB/峰1.39GiB，本次保守预计240秒、700MiB、峰2GiB。硬限GPU阶段600秒、RAM4GiB、新文件800MiB、剩余磁盘20GiB；超限停止不重试。

复用已验证12步四模式毒化/History双预测滑窗测试，新增日期隔离/精确门禁测试，全239测试先通过。正式GPU不增加额外真实预检。hooks前6步input/scalar/raw/state/means/std与Mar24旧6h逐元素一致，否则立即停并留失败前缀；后续正式评价还要核对旧六变量与DEN指标。原native rtol2e-5、RMSE atol1e-25、ACC atol2e-6；公共物理独立加权求和rtol1e-12，不事后放宽。

共同物理空间SI、raw目标/普通physical气候态/真实01持续性。DEN×1000 kg/m3，风/Z×.01 SI，Z非ZG；native logACC/dex另表。逐层/极区/顶部/固定upper20—28/参考ZG中位400—500km组与偏差/相对及绝对误差全报。组可随lead和日期不同，不称固定450km/Swarm沿轨误差；固定压力组补充比较。两个日期不作地磁因果或全年泛化。Jan4只读离线比较，不重推理。

计时分别记加载/读取/标准化/其他预处理/forward/native指标/独立物理解码/保存；Jan4未独立记录的解码计时记N/A而非0，不作冷启动速度排名或TIE整体加速比。只制定训练实施方案；不下载训练数据、不训练/调参/24h/TIE/RK45。2023不拟合任何统计/权重。任务结束安全同步Git并停止。
