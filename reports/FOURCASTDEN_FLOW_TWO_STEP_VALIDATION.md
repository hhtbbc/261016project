# 官方Flow两小时自回归验证（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 实际执行与配置

本次只运行一次正式Flow，00→01→02 UTC，实际网络forward恰好2次。Direct两小时结果仅读取，未再次运行Direct网络；198项自动化测试通过，无包安装、资产下载、训练、TIE或轨道传播。

官方README_inference_2023.md模型表、config/AFNO.yaml::afno_inference和inference/inference.py是本次实现依据。Flow权重Flow_ckpt.tar SHA256 `cc88b4bbee4d70b7a49c94ae3a8127768c1529368abbd7d5f76018d0166a3021`，Direct权重SHA `212187479c2df3ead151ec339683198f9e0632e23b892ac4d829ce1048724efb`。两者同AFNONet 64,695,744参数，150项model_state按作者默认strict=True严格加载（没有strict=False），177×36×72输入/4标量/171输出。通道顺序TN、UN、VN各28，WN、Z、DEN各29；n_history=0、log_DEN=false、dt=1、n_prediction=2、普通static、FP32、TF32关闭。实际配置config.yaml、preflight.json与protected.json位于experiments/fourcastden_flow_two_step_v1。

配置从官方Flow afno_inference展开，不由Direct权重改造。覆盖仅项目路径、预测长度2、36×72网格、num_workers=0及日志/输出标签；两模型核心结构、变量、驱动、归一化和坐标配置逐项相同。Direct/Flow均使用同一官方普通static，并非为了公平强迫不匹配的统计。

原作者数据日志“包含3小时past history”实际来自数据集长度3的通用提示，不代表n_history=3；实际配置和输入shape已核实n_history=0。

## 增量含义及反馈

作者forecast先gen=model(inp,sw)，随后flow分支gen+=inp[:,:171]，所以delta与state都处于zscore空间。x_next_norm=x_current_norm+delta_norm；反归一化为x_next=x_next_norm*std+mean，物理增量只是delta_norm*std，不能额外加mean。该Flow不是光流warp，不是积分器中的速度。

Hook在作者原位累加前复制原始增量，随后独立检查两步累计状态与输入：两个float32累加逐元素一致，第二步输入恰为第一步累计预测；预测shape [1, 3, 171, 36, 72]。目标01/02时的真实171物理状态只评价，未来下边界、太阳/地磁辅助与四标量按作者方法已给定，因此是HINDCAST，不能称实时自主预报。

CPU合成测试直接调用原作者循环，用恒定增量验证1→1.25→1.5；零增量不变；毒化未来真值不改预测或输入；改变未来辅助只改变相应输入；错误的直接增量反馈被拒绝；独立反归一化公式测试通过。合成结果不当真实预测。两次正式输入、增量和输出已保存于data/processed/fourcastden_flow_two_step_v1/result.npz（仅本地），SHA `8646c3b8f66f504ae350a4d746da8a722f3fd0df03c89b482624c24bcca566c2`。

## 公平性与独立复核

Flow的real、means、stds、climatology、t0状态、两目标的6个二维辅助和4标量与Direct保存值逐元素一致。原三帧SHA和完整保护列表见protected.json；Direct历史SHA `4476774ab3861f59ebf7c390a18b2a2ea8e6eb2ded2c75875ac3dcd2f89cdaf1`。原始第三方源码、运行副本、权重/static/样本/历史结果保持不变，最终交付audit复核。

独立NumPy float64逐171通道cos纬度加权RMSE与气候态ACC重算，RMSE预注册rtol2e-5/atol1e-25，ACC rtol2e-5/atol2e-6，无有效分母记N/A；Flow最大RMSE相对差1.820e-07，ACC最大绝对差1.721e-07。Direct保存作者指标也再次独立复核，不调用网络。

## 物理基础检查

预测全部finite，DEN正值比例100%，TN正；没有裁剪、平滑、外推或事后修正。各变量最小/最大值和偏差见summary.csv；这只排除本次明显异常，不证明未来长时稳定或真实大气准确度。Z为位势高度，不能当ZG。图示ilev=4.0（数组index22），参考ZG中位约439.5/441.3km，实际高度随经纬变化，不是固定450km剖面。

## 耗时与显存

A100-SXM4-80GB / torch 2.4.1+cu121 / runtime CUDA 12.1。模型加载（包括首次CUDA初始化）1.274014s，单独数据读取预处理0.051112s，作者两步循环含评价及hooks 0.791990s；实际循环也会再次读取3帧，因此这些口径不得直接相加当纯网络时间。首个冷forward 152.144058ms、第二forward 18.434879ms；GPU阶段总墙钟3.400115s<300s。

包含checkpoint加载的分配峰987.240MiB；加载后reset的推理阶段分配峰281.251MiB、保留峰1106.000MiB。Direct历史只测推理阶段峰，不能与Flow加载峰比较。新数组约17.12MiB，最终所有新产物受500MiB门禁。

## 可重复命令及停止边界

先source scripts/activate310.sh；python -m unittest discover -s tests；python scripts/run_fourcastden_flow_two_step.py（静态）；timeout 300s python scripts/run_fourcastden_flow_two_step.py --execute（本次唯一一次，旧run-tag自动拒绝）；python scripts/analyze_fourcastden_direct_flow.py；python scripts/write_fourcastden_flow_reports.py；python scripts/audit_fourcastden_flow.py。报告/分析采用独占输出，重复正式实验应另行授权并修改独立标签。没有更多GPU执行。
