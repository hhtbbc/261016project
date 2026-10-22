# log-DEN五日期预注册（正式GPU模型之前，2026-10-22）

固定Jan4、Mar23、Jun21、Sep23、Dec21各00→01→02 UTC，5个新log-DEN序列/10真实forward；Direct/Flow只读。官方Baseline_log_DEN_ckpt.tar、匹配static_log，flow=false/history0/log_DEN=true，普通AFNONet177输入/171输出/4条件、FP32/TF32false，strict加载。无训练/下载/扩窗/轨道。

已发现并在独立覆盖层处理：np.power(CUDA Tensor)不支持；DEN逐层std/mean向量需显式[:,None,None]广播；static_log time_means原始前导单例维需保值reshape。原作者树/Linux副本/权重/统计不改，完整diff及源/覆盖/补丁SHA保留；CPU逐值测试及小CUDA张量pow与独立NumPy比较rtol3e-7，保dtype/device，不裁剪。真实模型前全套CPU测试必须通过，错误日志保留。合成毒化使用可有限反变换的未来归一化状态9，超大999导致参考指数溢出的失败单独留存；溢出/下溢拒绝测试继续保留，不能靠裁剪使其通过。

物理公式：L=normalized*std_log+mean_log，rho_g_cm3=10**L，rho_kg_m3=rho_g_cm3*1000。其他变量不取log，但static_log非DEN统计与普通static也存在差别，各自必须匹配官方权重，不能认为只切换了一个严格消融开关。状态在各自匹配标准化空间反馈，未来真171状态只评价，未来辅助/驱动按作者提供，HINDCAST。

公平评价：三模型输出用float64按各自官方统计解码，统一与同一原始NPZ物理目标比较；DEN转换kg/m3。共同气候态固定普通static/time_means（从历史Direct保存值核验），不能将log气候态反指数当物理算术平均。旧Direct/Flow预测不重跑，但本轮统一原始物理参考，与此前float32归一化再还原参考的指标可有微小舍入差，旧指标不覆盖。

作者原指标另存：返回RMSE中DEN是物理g/cm3，其余是各自原单位；DEN ACC在log空间和log气候态上。捕获作者指标函数的原始归一化RMSE、FP32物理DEN运算输入，用独立float64重算核验；归一化RMSE/物理FP32操作数RMSE rtol2e-5/atol1e-25，ACC rtol2e-5/atol2e-6。FP64公平物理误差和FP32原生误差不强制相等，分别注明定义，不为结果放宽门槛。归一化log RMSE乘std得到dex，公平log误差另定义ln(rho_pred/rho_raw)，不混用底数。

每序列2次forward精确反馈、源文件/官方匹配归一化的初态校验；原始驱动相同，标准化辅助不强制跨统计逐位一致。所有预测finite、TN正、DEN100%正；失败立即停止，不重试或静默排除日期。所有五窗/层都报告；n=5按日期等权，不作全年/显著性/独立观测或轨道精度结论。

指标：逐变量原生压力层RMSE/共同物理ACC，DEN相对P95/RMS/自然logRMS/偏差、极区|纬|>=60°、最底与顶层、固定上层index20—28、参考ZG全球中位400—500km的原生层组（不是固定高度），持续性各窗固定00时。保留两小时增长和温度风场代价，不按较好日期或层筛选。

GPU总预算600秒包括小张量兼容探针和正式监督进程，RAM4GiB，新增250MiB。一次加载log模型处理5个独立序列，不加真实网络warm-up。分别记加载、冷/后续forward、读取、作者指标/hooks、输出反变换、保存及审计开销；Direct/Flow历史测量不能用于稳健吞吐排序。完整原始/预测数组不入Git，结束安全同步后停止。
