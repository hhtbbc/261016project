# NRLMSIS密度接口及环境验证

## 已实现与环境

src/atmosphere/msis_density_provider.py实现显式NRLMSIS 2.1接口，包装库固定pymsis 0.13.0（实际PyPI最新核验版本，网页文档页显示0.12.0，关键语义另与已安装源码核对）。已有Python 3.10.19、numpy 1.25.0，复用.venv310；没有修改TIE-GCM环境。linux cp310 manylinux wheel约1.31MB，SHA与PyPI相符，详情logs/nrlmsis_install_manifest.json。底层为wheel自带msis21f Fortran扩展及msis21.parm，二进制/系数/参考表SHA见logs/nrlmsis_backend.json。小型wheel无需新增编译器，依赖仅numpy>=1.23；uv检查70个已装包兼容，无升级旧包。

现有venv没有pip模块，首次python -m pip命令未执行安装；改用项目既有uv pip --python .venv310/bin/python --no-deps安装已校验wheel。安装/依赖检查见logs/nrlmsis_install.log，锁定环境见configs/requirements-nrlmsis-20261020.lock.txt。全部缓存与临时文件沿用activate_orbit.sh的项目内路径。

## 契约与正确性

输入UTC、WGS84大地经纬度与椭球高m；内部高度除1000送入pymsis，输出总质量密度kg/m³。ITRS入口复用DensityQuery.from_itrs/Astropy EarthLocation，不重复实现地理转换。保守接口域为高度0—1000km、纬度±90°；经度周期规范化。向量必须同长度，避免意外进入网格广播模式；非法时间/非有限/缺驱动/无效密度立即报错。输出含版本、具体驱动、provenance及HINDCAST标签。原TIE外部坐标门禁保持EXTERNAL_DATUM_UNVERIFIED。

新增12项自动化测试，覆盖标量/向量、单位与独立CGS参考、太阳/Ap响应、重复查询、随高度下降、极区/接缝、日期与57小时历史、81日与前日约定、缺失历史、非法版本/长度/数据、契约和原正式门禁。完整测试日志logs/nrlmsis_all_tests.log，126项通过（既有114+新增12）。

上游预存NRLMSIS2.1双精度Fortran回归表200行的总密度全部通过；参考rho由g/cm³乘1000换SI。最大相对差0.04371377%，低于上游预置0.2%舍入容差，没有事后调阈值。该表独立于本次运行生成，但仍来自相同模型体系，不是独立观测，也不是独立物理精度验证。模型响应的合成测试不冒充真实Swarm密度。

## 实际沿SP3离线诊断

2023-03-21 00:00:02—06:00:02 UTC，首先300秒73点通过，再60秒361点。SP3 GPS→UTC使用已有冻结闰秒/EOP入口，原始HDR独立日期锚点、原生10秒网格精确选点；没有轨道积分、拟合或密度反演。与既有TIE条件查询的UTC、ITRS和WGS84值逐点核验一致。

- 全361点有效；密度最小1.129333063697e-12、最大1.805477317131e-12、中位1.580192140332e-12 kg/m³。
- WGS84高度460.427543—489.972356 km，纬度-87.365331—87.364168°。
- 361点批量调用含驱动构造0.340478s，约0.943ms/点；单点契约361次均值2.026ms，P95 2.314ms。
- 整个只读审计、离线计算和绘图17.394s，进程累计峰RSS 162.590MiB；含库/图形内存，不是模型独占增量。
- 原46个S3/S7 NetCDF和2个沿轨CSV读取前后48项SHA相符；原始SP3哈希见审计orbit_metadata，并与冻结源清单复核。

初次离线脚本在解析旧审计的相对文件路径时于计算前失败，没有模型积分或结果；保留失败日志nrlmsis_comparison.log和空v1目录，修正后独立v2完成。没有覆盖任何旧实验。

复现：source scripts/activate_orbit.sh；python scripts/prepare_nrlmsis_drivers.py（只接受同内容）；PYTHONPATH=src python -m unittest discover -s tests -v。离线运行python scripts/run_nrlmsis_comparison.py --run-tag nrlmsis2023_v2（已存在则拒绝；公共输出也禁止覆盖）。复现可使用新标签与新前缀，例如--run-tag nrlmsis2023_reproduce --output-prefix nrlmsis2023_reproduce，不能覆盖本次证据。

数据：results/metrics/nrlmsis2023_300s.csv、nrlmsis2023_60s.csv；完整审计experiments/nrlmsis2023_v2/audit.json。本次新TIE积分0、新RK45积分0。
