# 球谐引力截断独立验证

## 源数据与实现

使用GFZ ICGEM同一EGM2008源，仅读65536字节，服务器完整Content-Length为252140870字节但没有读取完整文件。SHA256 `1ed7794419ff81568285fb4ebfbc1f82aedac938ac67bd5fbe7c68776b88fc00`，前16384字节逐位匹配旧前缀。所有n≤20/m≤n完整，n=1明确地心零项，20阶共231对C/S；8/12/20系数和GM398600441500000、R6378136.3、fully_normalized/no CS/tide_free完全相同。公开低阶副本configs/egm2008_20x20.json，来源URL/响应/SHA在configs/egm2008_degree20_source.json。

独立扩展模块gravity_truncation.py只扩展初始化，继承原Cartesian实心球谐/梯度，原8×8/框架/RK45源文件保持原样。阶乘/中间多项式在本次20阶和测试位置有限；不声称可以未经验证推广到任意高阶。完整地固Q旋转、包含中心项、不叠J2、无旋转系虚拟力。全部361个历史H1状态上，新8阶GCRS加速度与旧实现逐位相同，另直接势/力比较通过，未重新传播H1。

## SHTOOLS独立Fortran参考

继续使用已冻结pyshtools4.14.1 Fortran扩展和GM/R/C/S，omega=0；原binary SHA复核。100个随机点/级，覆盖约200km至5622km径向高度范围，另赤道/近极/经度接缝测试。纬度为地心球坐标，r为地心半径，不是WGS84高度或TIE ZG。极点无经度除零；SHTOOLS本身不支持精确极点导数，外部仅比较±89.9°，生产精确极点通过有限性/近邻连续性测试。

|阶/次|最大向量绝对差(m/s²)|最大相对差|100个构造点平均/P95纯场耗时(ms)|
|---|---:|---:|---|
|8×8|1.42177919e-14|1.85260102e-15|0.840 / 0.852|
|12×12|1.61360901e-14|2.10255640e-15|1.728 / 1.741|
|20×20|1.97057550e-14|2.80020526e-15|4.551 / 4.574|

预注册逐分量rtol/atol=2e−12/2e−12m/s²及向量相对门槛2e−12未放宽。中心差分势负梯度10km/1km/100m二阶收敛：

|阶|三档相对差|
|---|---|
|8|1.24086629e-06 / 1.24063161e-08 / 1.18603484e-10|
|12|1.24082946e-06 / 1.24046624e-08 / 1.33499816e-10|
|20|1.24092940e-06 / 1.24029718e-08 / 1.42546801e-10|

100m门槛2e−8保持。8项新增引力测试全部通过，传播前全159项通过；离线受力辅助再增4项，最终全163项通过（logs/gravity_truncation_final_tests.log）。没有改变原151测试门槛。外部数值验证是指定截断势的实现检查，不是轨道物理精度验证。

## 资源与积分门禁

唯一10分钟H3预检实测4.214s/146nfev；依据每次RHS耗时及历史nfev并乘1.5安全系数，预计剩余751.451s，小于1795.738s余量后才启动H2/H3/tight。无失败重试、无H1重复积分。新传播累计498.429s，峰RSS146.430MiB，小于1800s/2GiB，GPU未用。

H3 base/tight最大位置差0.058410966m，低于0.5m预注册门槛；共同初态/输出网格一致。H2本次没有tight，不声称H3−H2配对差值已经有两端独立tight证明；当前单轨数值误差约厘米，应与实际截断差一起判断。

201项历史保护哈希不变；原H1/G0—G2/D0—D5/基础源码不改。新原始NPZ/模型前缀和既有二进制留本地，公开配置、CSV、图、测试与JSON。命令：source scripts/activate_orbit.sh；python scripts/prepare_gravity_degree20.py；PYTHONPATH=src python -m unittest discover -s tests -v；python scripts/validate_gravity_truncation.py；python scripts/run_gravity_truncation.py（静态）及--execute（本次标签已封存，拒绝覆盖/重复）；python scripts/analyze_gravity_truncation.py；python scripts/estimate_missing_force_budget.py（仅离线，最终v2）；python scripts/write_missing_force_budget.py；python scripts/write_gravity_truncation_reports.py。已有输出x模式不可重放；复现需先设计独立run-tag/位置并获得对应传播授权。
