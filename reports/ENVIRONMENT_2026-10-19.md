# 服务器环境检查报告
检查日期：2026-10-19 UTC；初始目录为空，根目录realpath与指定路径一致。

| 项目 | 实测 |
|---|---|
|系统|Ubuntu 24.04.1 LTS，x86_64，Linux 5.4.0-218-generic|
|CPU|Intel Xeon Platinum 8336C，系统可见112逻辑CPU|
|内存|系统可见1.9 TiB，总可用约1.8 TiB，swap为0|
|磁盘|共享NFS挂载3.5T，剩余约681G（动态值，不是独占配额）|
|GPU|NVIDIA A100-SXM4-80GB，81920 MiB，检查时0 MiB占用|
|驱动|575.57.08；nvidia-smi显示驱动支持CUDA 12.9|
|Toolkit|nvcc 12.8.93；与驱动显示的CUDA上限不是同一概念|
|Python|系统3.12.3；项目.venv为3.12.3，user site禁用|

完整命令、stdout、stderr见 logs/environment_checks.json。以上CPU/内存为系统可见值；容器限制需结合日志中的cgroup读数，不能视为可独占资源。

标准 python3 -m venv 失败：ensurepip不可用。随后使用 python3 -m venv --without-pip 成功；sys.prefix 为项目 .venv，sys.base_prefix 为 /usr，两者不同。基础隔离验证通过；pip、PyTorch与科学计算包均未安装，GPU计算未测试。
未使用sudo/apt或全局pip。作者Python3.10.14的Windows环境与本机不同，停止依赖安装，后续需制定Linux最小推理环境方案。
缓存设置入口 scripts/activate.sh；所有项目输出均在指定工作区。虚拟环境引用系统解释器/标准库属只读使用，不向系统路径安装。
