# TIE-GCM原生密度查询接口验证

## 实际完成范围

复用.venv310及activate_orbit.sh，新增原生ZG接口、外部坐标门禁、17项独立测试、只读审计/性能和绘图脚本。没有安装依赖、模型积分、下载场数据、修改第三方源树或真实卫星阻力传播。全套93项测试通过，原生查询17项单独通过。验证日志logs/tiegcm_density_{tests,all_tests,real_validation_v2}.log。

S3/S7的46个原NetCDF（21+25）读取前后逐文件SHA256均匹配原data_audit.json。没有覆盖历史文件。每组共同窗口290帧。最终可复现审计为experiments/tiegcm_density_interface_v2/audit.json，含提供器代码SHA和逐文件哈希。v1是增加溯源元数据前的离线性能记录，保留历史；v2为交付版本，没有新增模型积分。

## 算法及失败策略

按每卷实际year/mtime建立一次UTC索引，同时核对CF time，拒绝重复/缺帧及非600秒间隔；按时间定位文件/记录。实际DEN/ZG维度必须为(time,ilev,lat,lon)，单位必须匹配。只读取两帧四水平邻点的八个整垂直列，不加载全三维场。

每列显式屏蔽按源dtype表示的填充值、abs>1e30和非有限量，DEN转SI后要求正值，ZG要求严格递增。复用coverage.stencil_coverage对全部八列检查，即使某插值权重为0也必须有效；任一列越界或异常直接失败。经度360°周期；纬度仅在原生中心包围域内双线性插值，极冠显式POLAR_CAP_UNSUPPORTED，不构造极点或偷偷裁剪。原生时间端点使用范围内相邻两帧及0/1权重。

先每列按真实ZG对lnρ线性插值并指数还原，再水平双线性密度、最后UTC时间线性密度。结果记录时间权重、水平邻点/文件/记录、逐列垂直括层及权重、最小顶界裕量、来源/质量和原审计清单SHA。清单SHA是可追溯声明，不是每次查询重算2.5GB文件的验证；使用前由离线审计核验原文件。外部ITRS/WGS84适配明确返回EXTERNAL_DATUM_UNVERIFIED，标量阻力协议抛异常，不返回零密度。

17项合成测试覆盖可手算指数剖面/时间中点、网格点和单位、经度接缝、南北近极及极点、上下越界、时间前后越界、错误datum、NaN/填充/倒序邻列、线性及全log替代、源切换、重复/缓存关闭、CF时间错位、重复帧、零权重邻列损坏、文件描述符无泄漏。每个源另对首/中/末三个真实网格点和1000个原生450km测试点校验。网格点最大相对恢复误差小于2e-15。

## 实测性能

|源|查询数|平均ms|P95 ms|1000次累计秒|进程峰RSS MiB|
|---|---:|---:|---:|---:|---:|
|S3|1000|11.292|15.624|11.292|89.668|
|S7|1000|11.089|15.401|11.089|97.707|

延迟仅计主log插值查询，不包括前置哈希/索引、后续线性替代查询、SP3读取或绘图；文件系统已被哈希扫描预热，不是冷磁盘随机IO基准。峰RSS为同一顺序进程ru_maxrss的累计高水位，包含Python/库/结果列表等，不能视为提供器独占内存。LRU最多256列，实际数组缓存118784字节，无常驻NetCDF句柄；每次读取with关闭，文件描述符重复测试通过。当前每秒约90次原生查询的吞吐不是RK45总耗时预测，实际集成前可评估更高局部复用优化。

## 插值方法差异

固定相同1000个有效原生450km点，替换垂直算法（其余相同）计算相对差，以log垂直结果作分母；再比较将水平和时间也在log空间插值的替代方案。

|源|线性垂直差异绝对值P95|全log水平/时间差异绝对值P95|
|---|---:|---:|
|S3|3.4832%|0.0428%|
|S7|3.4933%|0.0415%|

这些是方案差异，不是相对真实大气的误差界。合成指数剖面中log垂直恢复解析值，真实剖面仍有离散误差。CSV保存2000条查询的原生坐标、UTC、密度、耗时和两种替代差；图不平滑，不冒充真实Swarm密度。

## 实际查询示例

原生坐标共同2023-03-21 00:05 UTC，模型纬度−85°，东经−180°，ZG450000m：
- S3: rho=1.556803286140e-12 kg/m³。
- S7: rho=1.639255309647e-12 kg/m³。

## 使用和复现

```python
from pathlib import Path
from atmosphere.tiegcm_density_provider import TiegcmDensityProvider, DATUM
with TiegcmDensityProvider(Path('experiments/tiegcm2023_s7_continuous_v1').glob('secondary_*.nc'), 'S7') as p:
    result = p.query_native('2023-03-21T00:05:00', -85, -180, 450000, datum=DATUM)
    assert result.valid, result.reason
```

CLI（从项目根，原标签已占用，重复审计换新标签；无模型积分）：

```bash
source scripts/activate_orbit.sh
python -m unittest discover -s tests
python scripts/validate_tiegcm_density_interface.py --run-tag tiegcm_density_interface_v3
python scripts/plot_tiegcm_density_validation.py --run-tag tiegcm_density_interface_v3
```

接口不保留打开句柄，close清缓存并禁止后续原生查询。非线程安全；并行调用须独立实例。时间字符串按UTC解释，带其他时间尺度的Astropy Time会先转换UTC。默认只索引共同10分钟窗口，不把预热日采样误当等间隔10分钟场。源标签是调用者的来源标识，文件来源及原清单可供审计；不根据“S7”标签假定更科学准确。

## 限制和后续

正式Swarm沿轨有效率/密度仍N/A，详见SWARM_TIEGCM_COVERAGE_AUDIT.md及坐标审查。当前不仅缺少有界的外部高度/纬度适配，还缺预热初态敏感性闭合、10分钟时序误差验证和真实气动参数/姿态/推进器处理，不能直接开始RK45精度结论。S3/S7同一接口可读不代表S7已充分收敛或是真值。
