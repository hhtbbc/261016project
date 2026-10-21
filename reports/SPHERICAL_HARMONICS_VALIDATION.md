# 完整8×8球谐引力验证

## 实现与来源

新增独立`spherical_harmonics_gravity.py`，使用已有GFZ EGM2008低阶前缀、完整n≤8/m≤n的C/S组合，自身GM=398600441500000m³/s²、R=6378136.3m，完全归一化/无CS相位/tide_free。机械势U为负，a=−grad U。笛卡尔实心球谐与梯度同步递推，不存在经度/极区除零；中心引力已包含，不再叠加旧模型。完整推导和参数差见[设计](../docs/SPHERICAL_HARMONICS_GRAVITY_DESIGN.md)。

## 外部软件与数学验证

使用SHTOOLS 4.14.1独立Fortran MakeGravGridPoint，显式omega=0，不含离心项；将其r/theta/phi向量独立变换Cartesian。100随机位置最大向量绝对差1.073419750e-14m/s²、相对差1.326113710e-15；固定门限rtol/atol=2e−12/2e−12m/s²。赤道和±89.9°近极也通过。SHTOOLS自身PlmBar_d1不支持精确极点（初次参考调用触发Fortran STOP，不能把进程退出0当测试成功）；生产精确两极另用有限性/邻近连续性及m=0解析式验证，没有扩大容差。

独立scipy lpmv计算势，解析中心/J2/J3/J4统一源参数比较；只开启J2及关闭各阶恢复、C22/S22经度变化、order截断、非法输入、全矩阵力旋转与有限性测试通过。9项新增、全151项测试通过，最终日志`logs/spherical_final_tests.log`。旧9项J3/J4测试仍保留，不等于执行了另一完整轨道软件。

中心差分势负梯度：

|h(m)|相对差|
|---:|---:|
|10000|1.240866289e-06|
|1000|1.240631609e-08|
|100|1.186034843e-10|

细步门限2e−8保持，三档二阶收敛。真实六小时base/tight最大位置差0.058408116m，低于预注册0.5m；没有用SP3残差设门限或拟合初态/系数。

## 时间、框架及保护

同旧初态SHA `194f248cfaa2ea727cf70f834e47034968355249a52c177bb9d4fd3dc49eaee4`，GCRS积分，经现有EarthFixedFrame/Astropy与ERFA c2t06a旋至ITRS计算，再Q.T仅旋物理力；TT/UT1/xp/yp冻结，与旧框架相同，不加入观测dX/dY、相对论缩放/潮汐等。含m≠0必须完整地球旋转，不能只用轴向。177项历史保护文件SHA前后不变，六份CDF另行校验。无旧D0—D5重跑、无TIE/新阻力/AI/48h传播。

## 环境与复现

复用.venv310 Python3.10.19。外部参考wheel13,898,723字节，PyPI SHA核验；初次仅安装pyshtools无依赖，完整包检查发现4项可视化/高层依赖缺失。为不升级项目，随后卸载此包、只将已验证wheel解包至`.local/reference/pyshtools_4_14_1`，加载自带Fortran扩展/动态库；不是全pyshtools Python API安装。原72包兼容，见`logs/spherical_environment_check.log`。原始wheel/元数据和二进制不入Git，轻量wheel/二进制SHA在`configs/spherical_reference.json`。初次degree0初始化误加degree1零项导致静态测试失败，修正后才通过门禁并运行轨道；保留失败日志，无失败传播重试。

复现依次：`source scripts/activate_orbit.sh`；`python scripts/prepare_spherical_reference.py`；`PYTHONPATH=src python -m unittest discover -s tests -v`；`python scripts/validate_spherical_harmonics.py`；`python scripts/run_spherical_harmonics_comparison.py`静态，再`--execute`。当前标签已使用，不得重放授权，脚本以x模式拒绝覆盖。异地需先按配置清单取得原GFZ前缀及冻结SP3/EOP资源；这不是脱离数据可单文件运行的软件。外部软件交叉验证是当前截断引力数值检查，不是Swarm轨道真实精度证明。
