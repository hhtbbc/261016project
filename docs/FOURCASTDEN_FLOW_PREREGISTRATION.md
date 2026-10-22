# Flow两步受控对照预注册（2026-10-22，GPU前）

仅执行一次官方Flow 2023-01-04 00→01→02 UTC。Direct读取历史，不运行网络。使用官方AFNO.yaml的afno_inference，覆盖本机路径、36×72、n_prediction=2、num_workers=0及日志选项；保持flow=true、n_history=0、log_DEN=false、dt=1、普通static。Strict加载，无网络数学修改。

源码事实：inference/inference.py::forecast先调用AFNONet输出delta，再以float32原位gen+=inp[:,:171]。状态和增量均在同一zscore空间，物理状态=(normalized state)*std+mean；物理增量=delta*std，不重复加mean。第二步输入第一步累计状态。目标时刻六个辅助二维通道和四标量保留作者方法，HINDCAST；未来真实171状态只评价。

门禁：CPU实际作者循环合成增量/零增量/毒化未来状态/辅助条件/错误反馈/反归一化测试通过；全量既有测试通过。旧保护清单和Direct result SHA必须一致。原源码/运行副本/static/权重/样本不变。逐元素精确核对两次状态更新及反馈；严格要求2个真实forward。预测全部finite、TN正、DEN100%正；失败不裁剪，不重试，不扩窗。

公平性：初始状态/目标/均值标准差/气候态/辅助及标量逐元素核对Direct，压力层/单位/mask相同。固定t0持续性，不利用01时真值更新。独立NumPy float64 RMSE与作者比rtol=2e-5/atol=1e-25，ACC rtol=2e-5/atol=2e-6；无有效分母记N/A。先按各层统计，再报告变量平均逐层RMSE，不能当固定几何高度误差。

资源：GPU阶段最多300秒，新增500MiB，无训练/新数据下载/轨道或TIE积分。分别记录加载（含CUDA首次初始化）、首个冷forward、第二forward、预处理、作者循环含metrics/hooks、推理阶段显存及包含加载的峰值。Direct仅使用旧计时，跨日单次测量不代表稳健速度排名。

图以参考ZG中位高度最接近450km的原生ilev展示并列出实际高度；Z是位势高度。此次结果只针对1个初值2个目标的TIE-GCM参考，不作总体架构排名、独立观测或轨道精度结论。
