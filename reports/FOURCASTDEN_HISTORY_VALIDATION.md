# 官方History首次两小时自回归验证（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 执行范围与数据

仅2023-01-04：History使用00/01真实状态，t0=01，目标02和03；其他三模型仅使用01真实物理初态。4个新独立序列/8正式forward，加唯一History真实forward预检1次。历史00→01→02数组不被当本次新起点结果，无训练/调参/额外日期/扩窗/TIE/RK45。221项全套自动测试通过（24.452s），新6项CPU测试调用实际作者循环及合成网络，不是额外真实模型预测。

唯一新原始成员`2023_01_04_030000.npz`，官方Zenodo2023.zip中央目录存在，偏移155345575，成员CRC32=4091454841。实际HTTP请求全部206并匹配Content-Range，传输3063982字节（2.922MiB）<10MiB。新文件SHA256 `b306e552d499a23333994f43af245c8a824e3a3d4fab149342cd399f05507968`。00—02仅软链接原文件，不重下载。14字段、float32/shape/finite/哨兵/正密度/TN/ZG逐层单调检查通过；原始NPZ无独立单位或时间坐标属性，小时来自官方成员名、单位/网格来自作者UNIT_VARS和不可变static契约，不能声称外部观测坐标基准已被证明。详细stats/请求见download.json、ranges.json、preflight.json。

## 官方实现与通道顺序

直接依据`third_party/FourCastDEN/inference/inference.py` load_model、forecast、inference；README_inference_2023表格指定Baseline_1h_history_ckpt.tar、n_history1、flowfalse、log_DENfalse、普通static。AFNONet仍4×4 patch/768嵌入/12块，n_in_channels基础177×(history+1)=354，输出171、标量4；实际严格load_state_dict，无strict=False。History参数66,870,720，比64,695,744增加2,174,976（约3.36%），来自patch embedding多177输入。全部权重原样：

- History: `cc4b44f6daea6188e4bfbde06796b950a50cfb215c0ad2295cff176a21a4ddc4`
- Direct: `212187479c2df3ead151ec339683198f9e0632e23b892ac4d829ce1048724efb`
- Flow: `cc88b4bbee4d70b7a49c94ae3a8127768c1529368abbd7d5f76018d0166a3021`
- LogDEN: `d314241ef9b91ba8e3405d77090b24ded03ceff361404f9ff5bd6212b828db18`

每一177块是TN/UN/VN各28，WN/Z/DEN各29（171），随后TLBC/ULBC/VLBC、SEA、磁纬/磁经6个辅助通道。原inference按时间先旧后新reshape。第一输入：[real00物理+aux01]、[real01物理+aux02]，标量驱动02；第二输入：[real01物理+aux02]、[pred02物理+aux03]，标量03。History直接预测绝对归一化状态，不加增量。02/03真实物理通道只用于评价。

## 反馈与兼容性证据

CPU合成实际作者循环检查先后次序、354维、输出、aux/标量对齐；未来物理真值毒化后预测逐元素不变，逆序/teacher-forcing/辅助或标量错位均被拒绝。真实forward hooks逐元素检查两个完整177块与预测反馈，唯一预检输出与正式第一步逐元素一致。作者裁去最早历史后，pred为(1,3,171,36,72)，real为(1,3,177,36,72)，时间对应01/02/03；real额外保留6辅助通道。History无新增源码补丁；log模型复用上一任务经过SHA核对的隔离覆盖层，static_log单例、DEN广播和torch.pow等价修复不再改动。原源码、权重、static和既往结果356个保护文件SHA不变。

4模型实际原始174物理/LBC通道归一化独立重建完全一致于各自匹配统计；未来标量和磁通道匹配，普通三模型SEA一致，log SEA差最大7.153e-7，源自官方static坐标dtype，未强制替换。log静态统计其他变量亦不同；这是官方整套预训练配置对照，不是严格训练消融。

## 数值与物理检查

全部预测finite、DEN100%正、TN正，无裁剪、补0、重试。native标准化RMSE/自身气候态ACC与float64重算沿用rtol2e-5/atol1e-25、ACC绝对2e-6，未放宽；独立共同物理RMSE/ACC共1368个通道时效检验rtol1e-12通过。log作者DEN ACC仍log空间，返回DEN RMSE物理g/cm3，dex另存，不能与共同kg/m3或物理ACC混排。原生指标CSV有1368行，公共逐层CSV有1710行（含共同持续性）。

## 实际成本

|模型|参数量|checkpoint字节|加载s|独立读取/预处理ms|正式forward 1/2 ms|循环含指标/hooks s|保存s|推理CUDA allocated峰MiB|
|---|---:|---:|---:|---:|---|---:|---:|---:|
|History|66,870,720|802585484|1.364010|64.948|18.619/18.375|0.665837|1.528907|294.806|
|Direct|64,695,744|776485772|1.124672|47.902|20.390/18.714|0.095592|1.289065|281.568|
|Flow|64,695,744|776485772|1.129902|47.879|19.357/18.356|0.089680|1.273128|281.568|
|LogDEN|64,695,744|776484108|1.137005|46.066|18.604/18.261|0.238495|1.366927|282.717|


History唯一冷预检forward=146.774ms，之后正式两次已经warm；其他模型共享CUDA内核/文件缓存。首次正式forward不一定冷，不按上表的单次事件给吞吐排序。History额外输入增加参数约3.36%、推理allocated峰约4.70%，本例不是输入翻倍则成本翻倍。reserved显存含加载/缓存，不能当活跃tensor用量；load峰与每次推理峰分开记录。进程ru_maxrss为累积峰，独立监督聚合RSS峰1.225GiB。

监督墙钟21.011274s，内部GPU阶段（含加载/CPU压缩/SHA等）12.858259s，预算600s；纯网络事件另列。CPU离线分析3.825084s，独立预读取在作者loop内还会重复，不简单相加解释成纯推理时间。初审新增文件108.318MiB，另预留1MiB源码/报告，小于150MiB；无大型数组入Git。

## 重复执行与审计入口

`source scripts/activate310.sh`；`python -m unittest discover -s tests`；run_fourcastden_history_comparison.py --fetch；同脚本无参数静态；supervise_fourcastden_history.py；analyze_fourcastden_history.py；audit_fourcastden_history.py；write_fourcastden_history_reports.py；最终audit的--final。全部once-only，不要在同标签重复网络/推理；未来复现实验必须新授权/新run-tag，不能删除launch文件重试。

实际配置、数据/代码/权重SHA、hooks数组、runtime、supervision、reference_dynamics及audit均在experiments/fourcastden_history_comparison_v1；大型压缩结果在data/processed同标签，仅本地。日志logs/fourcastden_history*。这是工程和TIE模拟参考评价通过，独立真实大气/轨道科学准确度未验证。
