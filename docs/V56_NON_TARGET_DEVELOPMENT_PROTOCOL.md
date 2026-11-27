# V56 非目标开发协议

V37 历史窗为 [t−3h,t)，累计未来窗为 [t,t+h)，t 为 06Z/18Z，h 为 1、3、6 小时。V56 的 t+h 是工程端点和合成基线时刻，正式半开窗口、分窗和门槛保持。

V37 的 DEVELOPMENT_SOURCE 为 2021/2022 各自的 03-23、03-24、03-25、09-23，允许历史限定密度和已评分未来汇总，未来密度保持封存。V56 的开发和基线只使用合成密度。真实输入仅有两份 V53 授权元数据 CSV。

b_H 为截止前合规配对 log 差的中位数。原 Raw λ=0、Global λ=1、ShrinkageHalf λ=0.5，各时效共享同一截点冻结系数。Persistence 和 TwoFrameLinear 为合成诊断基线，本轮无新校正系数。

```bash
cd /workspace/data/20261016
source scripts/activate_tiegcm.sh
export PYTHONPATH="$PWD/src:$PWD/scripts:$PYTHONPATH" CUDA_VISIBLE_DEVICES=''
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python -B scripts/test_multihorizon_time_alignment_v56.py
python -B scripts/test_future_access_isolation_v56.py
python -B scripts/verify_non_target_prediction_protocol_v56.py
```

脚本独占创建输出，重放需独立准备干净的实验工作区。三个 49 帧原生合成场共用 36×72 和 4 个 ilev。独立解析多项式用于验证原生八列查询。预测 worker 只接受历史快照路径、SHA、cutoff、split，统计从三条允许记录派生。评估器拥有独立同路径毒化文件。重新启动预测进程验证输出一致并触发拒绝。这是受信任代码的接口隔离，运行任意外部代码前需文件系统权限约束与独立审计。误差指标仅覆盖合成诊断。
