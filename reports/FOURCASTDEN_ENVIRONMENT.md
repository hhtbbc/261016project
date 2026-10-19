# FourCastDEN Linux运行环境（2026-10-19）

## 检查与选择
已读取既有环境报告 reports/ENVIRONMENT_2026-10-19.md；用户给出的ENVIRONMENT-2026-10-19.md为文件名分隔符差异，实际旧文件存在，未重建或覆盖。操作前磁盘/内存/GPU证据 logs/day1_resource_preflight.json。
PATH和/usr/bin未发现Python3.10，仅3.12；系统已有uv 0.9.26可只读调用，未发现conda/micromamba/gfortran。采用uv管理的独立CPython3.10.19，安装目录 .local/python，下载约28.5MiB；原作者3.10.14与本机3.10.19为补丁版本差异，不能宣称位级一致。
保留原.venv（3.12无pip），新建.venv310；不重建/删除旧环境，不修改系统或其他项目。解释器下载日志 logs/python310_install.log，虚拟环境 logs/venv310_create.log。

## 使用方式
```bash
cd /workspace/data/20261016
source scripts/activate310.sh
python --version
uv pip check --python "$PWD/.venv310/bin/python"
python scripts/validate_fourcastden.py
```
最后一条仅在权重下载校验完成后运行。项目环境无需全局pip；使用uv pip --python显式目标。缓存/临时文件均由activate.sh和activate310.sh约束到项目内，并设置CUDA_CACHE_PATH、UV_CACHE_DIR、UV_PYTHON_INSTALL_DIR、UV_PYTHON_BIN_DIR，线程上限4，避免占满共享CPU。

## 依赖范围
声明清单 configs/requirements-inference-linux.txt，已解析完整版本 configs/requirements-inference-linux.lock.txt，安装日志 logs/inference_dependencies_install.log。共63个已解析包，一致性检查通过（logs/dependency_consistency.log）。

|类别|包/版本|用途|
|---|---|---|
|核心|torch 2.4.1+cu121、numpy1.25.0|网络/FFT与数组|
|网络|timm1.0.13、einops0.8.0、torchvision0.19.1+cu121|初始化/DropPath、重排、timm导入依赖|
|配置|ruamel.yaml0.18.6|作者YParams读取YAML|
|数据/辅助|netCDF4 1.7.1.post2、ppigrf2.0.0|作者模块导入、IGRF系数与太阳辅助模块|
|间接依赖|sympy、pandas等|torch及ppigrf依赖，完整版本见lock|
|原导入链绘图|matplotlib3.10.0、cartopy0.24.1|已安装；应用可选导入补丁后单步数值推理不依赖绘图执行|

不安装Windows运行库/编译工具、ai-models/GraphCast/MindSpore、Lightning/torch-optimizer等非活动推理链路依赖。apexpy有Fortran构建需求，本机无gfortran；当前不现场计算磁坐标，改为延迟可选导入，仍实际读取作者mag.npz。

## CUDA验证
logs/cuda_import_smoke.json及.log：Python3.10.19、torch2.4.1+cu121，CUDA可用，设备NVIDIA A100-SXM4-80GB；已知数值4×4 GPU FFT往返最大误差0。models.afnonet及inference.inference均可导入。
注意四个版本不能混淆：驱动575.57.08、驱动支持CUDA上限12.9、系统Toolkit12.8、PyTorch wheel自带runtime12.1。作者Windows环境为runtime12.4；本次未使用系统nvcc编译扩展。版本不同不自动意味着数值一致，当前只验证可运行，尚未跨作者环境比较输出。验证脚本使用FP32并关闭TF32，不擅自启用半精度。

## 兼容修改
第三方原目录字节未变，见logs/upstream_integrity.json。工作副本与补丁见patches/README.md。自有配置覆盖Windows绝对路径、Direct/Flow选项、静态文件和权重路径；显式设置从真实样本核实的img_shape_x=36、img_shape_y=72，修复作者配置尺寸默认0的问题。
作者eval的日期索引与默认循环假设全年数据；单步验证直接使用作者TGCMForecast.inference(0)，所有网络和预处理计算不替换。完整模型/权重/单步结果见logs/minimal_validation.json，若不存在或状态failed，不应宣称该阶段成功。

## 最终运行结果
四个checkpoint ZIP包2,901,442,296字节已完整下载并匹配MD5=78aa5107bf60927e6898cb19449520b7；ZIP成员读取/CRC校验通过。Direct_ckpt.tar为776,485,772字节的PyTorch ZIP序列化文件，含epoch、model_state（150项）、optimizer_state_dict，扩展名tar不代表普通tar格式。各权重SHA256见logs/checkpoint_sha256.json，完整目录见logs/artifact_downloads.json。
最初weights_only=True读取遇到ruamel ScalarFloat不在默认允许列表，错误见logs/checkpoint_inspection.log；尝试safe_globals上下文时发现torch2.4.1没有该API，保留logs/checkpoint_inspection_allowlist.log；核查pickle GLOBAL后使用add_safe_globals([ScalarFloat])，weights_only=True成功，证据logs/checkpoint_inspection.json及_allowlist_v2.log。作者原TGCMForecast仍沿用其weights_only=False加载路径，权重来自已校验官方归档，原加载逻辑未被改写。
原AFNONet精确配置CUDA构建通过：64,695,744参数；Direct的model_state严格匹配，无missing/unexpected keys，没有strict=False。
单步真实推理：2023-01-04 00:00→01:00 UTC，通过作者TGCMForecast.inference(0)。预测shape=(1,2,171,36,72)，第0帧是初始状态，第1帧是预测。参考含177通道。模型加载约1.17秒，加载后本次推理及评价约0.96秒，峰值torch分配显存1,035,196,928字节；这些是本窗口测量，不是正式吞吐基准。
结果experiments/20261019_minimal_direct/result.npz；逐层指标results/metrics/20261019_direct_one_hour.csv；日志logs/minimal_validation.log/.json。
数值验证：NumPy独立重算171个通道加权指标，与作者实现RMSE最大相对差1.882e-7、ACC最大绝对差1.456e-7；反归一化往返最大误差4.596e-14；预测有限且密度100%正。细节logs/independent_result_checks.json。
只通过基础运行与数值一致性检查；尚无多步、全年/磁暴、跨原Windows环境或观测/轨道物理验证。原始NPZ不含单位元数据，需要后续与NetCDF/文档进一步核对。
