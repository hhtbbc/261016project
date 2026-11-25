# V47 junsol 短路径恢复预检

**V47_B_RECOVERY_READY_FOR_AUTHORIZATION**。**SEED_SENSITIVITY_INCONCLUSIVE**。基线本地 HEAD / origin main 均为 `b2f3bf47fcf5c2d9feaba2e16d3ae11df765b00c`。V46 发布清单和比较合同逐项核验通过。A 组仍使用原 run_id `342ca7ee59a74a6aa600dd40f4459d91`；只读复核 33/33 卷 SHA，17 个主记录、384 个次历史小时和四个 rank 退出证据，原 GFZ GPI SHA 匹配。A 未重跑。原 B run_id `74e37781ad184841bb0b6114ff7cee4a`、失败记录及旧 claim 保留。

## 根因与真实读取

四个 V46 B rank 日志都显示 getfile 找到 147 字节完整路径，rdsource 以 120 字符 diskfile 接收后只能传入一个不存在的路径。nf_open 进入错误分支，nchist 的 120 字符内部格式化记录又触发 End of record。四个 rank 实际退出码均为 2，零步、零卷。独立 CPU Fortran 探针使用冻结 getfile、expand_path、nc_open 及 rdsource 取得并打开文件的调用块，链接原环境 NetCDF-Fortran。真实旧配置再次得到 147→120 和相同 End of record；恢复配置全链路通过。不同工作目录用同一配置实测拒绝。

恢复采用 `SOURCE = '../seed.nc'`，从未来 `run_B_junsol_recovery/` 或同级探针目录解析到 V47 父目录内的唯一普通文件。输入解析保留字面相对路径，PROJECTROOT 仅展开原有 GPI 等资产，SOURCE 长度在 getfile 与 rdsource 链上保持 10 字符。已查的 224/120 字符路径传递和 120 字符错误消息缓冲均未出现新溢出。没有运行完整模型初始化后的其他代码路径。

只读 `seed.nc` 计 16,993,144 字节，SHA256 `baed93b59dee7f8e6355c8d0224bd2335cf355bd0d632c9d2327aa7d0227475e`，与 V44 接受原件一致。真实 NetCDF-Fortran 读出 year=2002、day=172、mtime=[172,0,0]，全部 34 个原生字段读取通过。原件身份基于已验本地 SHA，NCAR 发布校验仍缺独立认证。探针编译的两次适配障碍涉及模块声明及隐式 Fortran 参数接口，修正仅限独立探针；最终探针无时间步。原 Fortran 源码、模型 ELF 和监督器均未修改。

## 配置、门禁及测试

旧 B 输入 SHA256 `851f33b2fb69389bc62b28f194e93691a5b8e49f3c1be1d5afcf7ca0e774eef9`。V47 输入 SHA256 `e75f70222d8266807adc3bc06242e470f668f54a523831f720ffe75930d558c1`。逐行唯一差异是 SOURCE。SOURCE_START=172 0 0；模型 2022-06-07 00Z 至 06-23 00Z、60 秒、23040 步、MPI4/OMP1/GPU0、HEELIS、氦、GSWM、输出合同及 GPI（SHA `d1e5cd2211a0ec6dd7e2c882341e3a2756626aa9ec4df74b8461ab4cc5d1a860`）全部保持。ELF SHA `f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776`。65 项冻结运行库合同通过，Open MPI 5.0.8，14 等效 CPU、约 272 GiB 有效内存及 1241 GiB 剩余磁盘，无活动模型。既有监督器支持新目录内单次启动与直接 wait；将于未来启动前复核资源及排他锁。

33 项 CPU 正反例通过。通过实际 CLI 拒绝无新授权的执行；独立运行目录尚未创建，未来启动前须为空。未产生 V47 预授权、claim 或 run_id；未来取得明确一次性授权后，另写绑定准备收据 SHA 的授权记录，复核 A、旧失败、种子、配置与资源，再生成新 run_id 和排他 claim。失败不自动重试。限额为墙钟 4800 秒（4770 秒触发，预留清理）、RSS 16 GiB、输出 5 GiB、启动/运行剩余盘 25/20 GiB。

V47 两个分析入口仅在 V46 A 和 V47 恢复 B 均工程通过后绑定两者，复用冻结 V46 主比较与独立数值计算。验证了源目录身份以及合成同 UTC 可读、错 UTC 拒绝。未执行真实 A/B 配对评价。阈值、时间、区域、高度、覆盖与趋势口径未改。V37 λ=0.5 和 2021 优先保持，2021 两日 Fobs 缺口及 ESA 原件缺口保留。未读未见 Swarm 密度，未评分，无 GPU/A100、MPI 任务、TIE-GCM 时间积分、AI、DART 或轨道传播。

下一轮可单独授权仅启动一次新的 V47 B 恢复积分，复用原 V46 A。若 B 通过真实工程验收才启动既定只读配对；原 V46 B 失败保持历史事实。
