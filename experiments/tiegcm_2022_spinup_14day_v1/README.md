# 本轮执行资格：PARTIAL

A14启动一次，模型日志/33卷数据完整，MPI退出码缺失；B14未启动。数据完整性不替代完整工程验收。execution_decision.json为最终状态。

实际执行：driver prepare、A14 launch、guardian同进程接管、partial数据审计、A14_A7、observation_partial、partial finalizer/independent audit。

未执行或未抵达：B14 guarded runner、delta14/B14_B7、完整joint/observation/finalizer。相应代码是准备状态，不代表可运行验证通过。不得重放任何已有launch_once run-tag。

commands.json和原supervisor/guardian/resume日志保存失败链路。A14/run_status.json中的launcher_exit_source仅预设采集路径；raw status为null，未取得实际退出码。B14放行所需工程PASS未满足。

原始NetCDF、输入namelist字节和逐点观测数组只保留本地。原122候选及历史科学门禁不变。
