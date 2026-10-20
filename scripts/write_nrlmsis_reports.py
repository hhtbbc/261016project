"""Render research reports from the completed offline audit; no simulations."""
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
a=json.loads((R/'experiments/nrlmsis2023_v2/audit.json').read_text());d=json.loads((R/'logs/nrlmsis_drivers_audit.json').read_text());ref=json.loads((R/'logs/nrlmsis_reference_audit.json').read_text())
root='experiments/nrlmsis2023_v2/audit.json'
def write(name,text):
 p=R/name
 if p.exists():raise ValueError('Refuse report overwrite: '+name)
 p.write_text(text)
write('reports/NRLMSIS_2023_DRIVERS.md',f'''# NRLMSIS 2023年驱动核验（HINDCAST）

采用NRLMSIS 2.1 / pymsis 0.13.0。依据[官方calculate API](https://swxtrec.github.io/pymsis/reference/generated/pymsis.msis.calculate.html)及实际安装的msis.py，显式传入全部太阳与地磁参数；geomagnetic_activity=-1启用历史Ap模式。模型不接收Kp代替Ap。

## 冻结输入与时间约定

原GFZ数据不重新下载；太阳Fobs支持2023-01-31—05-05，ap/Ap支持03-12—25。原始文件SHA与已有TIE驱动审计/来源清单逐项相符。冻结文件configs/nrlmsis2023_gfz_frozen.json，SHA256 `{d['driver_sha256']}`。原始来源、SHA和32条三小时边界测试见logs/nrlmsis_drivers_audit.json。GFZ来源及许可：[数据说明](https://kp.gfz.de/en/data)、[格式说明](https://kp.gfz.de/app/format/Kp_ap_Ap_SN_F107_format.txt)，CC BY 4.0；原API响应保存在data/raw/，不替换原文件。

- F10.7取目标UTC日的前一日Fobs，保留实际日地距离下观测值，不用1AU调整Fadj。
- F10.7A取目标UTC日D−40至D+40的81个Fobs算术平均，不对异常高值擅自裁剪。居中平均及事后def产品包含未来信息，因此是hindcast。
- 三小时ap为[00,03)、[03,06)等UTC半开区间，整点转入新桶；不做TIE使用的中心时刻线性Kp插值。
- 七项输入依次为：当日Ap、当前三小时ap、3/6/9小时前ap、12—33小时前8桶均值、36—57小时前8桶均值。最长历史57小时；目标03-20—23均完整，日界和03:00边界独立索引测试通过。
- ap及Ap每值均def；每日Ap与八个ap平均之差不超过官方整数舍入的0.5。太阳API无逐值质量标记，仅确认完整、有限、非缺失；不能宣称已独立验证观测质量。

2023-03-21的前日F107=156.1 sfu，F107A=160.79135802469133 sfu。当日Ap=6。00:00:02的历史数组为[6,9,9,5,27,10.125,6.875]；03:00:02为[6,4,9,9,5,12.375,7.375]；06:00:02为[6,6,4,9,9,10.75,8.5]。这与TIE同日自身插值的F107不必相等，不能把差异全归于大气模型结构。

所有调用显式提供F107/F107A/Ap，实验中将pymsis.msis.get_f107_ap替换为立即抛错，证明确实没有使用默认补数路径。缺测、错误数组长度或非有限参数均拒绝；不联网回填、不返回零密度。
''')
s=a['sampling']['60'];b=a['scalar_latency_ms']
write('reports/NRLMSIS_DENSITY_VALIDATION.md',f'''# NRLMSIS密度接口及环境验证

## 已实现与环境

src/atmosphere/msis_density_provider.py实现显式NRLMSIS 2.1接口，包装库固定pymsis 0.13.0（实际PyPI最新核验版本，网页文档页显示0.12.0，关键语义另与已安装源码核对）。已有Python {a['python']}、numpy {a['versions']['numpy']}，复用.venv310；没有修改TIE-GCM环境。linux cp310 manylinux wheel约1.31MB，SHA与PyPI相符，详情logs/nrlmsis_install_manifest.json。底层为wheel自带msis21f Fortran扩展及msis21.parm，二进制/系数/参考表SHA见logs/nrlmsis_backend.json。小型wheel无需新增编译器，依赖仅numpy>=1.23；uv检查70个已装包兼容，无升级旧包。

现有venv没有pip模块，首次python -m pip命令未执行安装；改用项目既有uv pip --python .venv310/bin/python --no-deps安装已校验wheel。安装/依赖检查见logs/nrlmsis_install.log，锁定环境见configs/requirements-nrlmsis-20261020.lock.txt。全部缓存与临时文件沿用activate_orbit.sh的项目内路径。

## 契约与正确性

输入UTC、WGS84大地经纬度与椭球高m；内部高度除1000送入pymsis，输出总质量密度kg/m³。ITRS入口复用DensityQuery.from_itrs/Astropy EarthLocation，不重复实现地理转换。保守接口域为高度0—1000km、纬度±90°；经度周期规范化。向量必须同长度，避免意外进入网格广播模式；非法时间/非有限/缺驱动/无效密度立即报错。输出含版本、具体驱动、provenance及HINDCAST标签。原TIE外部坐标门禁保持EXTERNAL_DATUM_UNVERIFIED。

新增12项自动化测试，覆盖标量/向量、单位与独立CGS参考、太阳/Ap响应、重复查询、随高度下降、极区/接缝、日期与57小时历史、81日与前日约定、缺失历史、非法版本/长度/数据、契约和原正式门禁。完整测试日志logs/nrlmsis_all_tests.log，126项通过（既有114+新增12）。

上游预存NRLMSIS2.1双精度Fortran回归表200行的总密度全部通过；参考rho由g/cm³乘1000换SI。最大相对差{ref['maximum_density_relative_difference']:.8%}，低于上游预置0.2%舍入容差，没有事后调阈值。该表独立于本次运行生成，但仍来自相同模型体系，不是独立观测，也不是独立物理精度验证。模型响应的合成测试不冒充真实Swarm密度。

## 实际沿SP3离线诊断

2023-03-21 00:00:02—06:00:02 UTC，首先300秒73点通过，再60秒361点。SP3 GPS→UTC使用已有冻结闰秒/EOP入口，原始HDR独立日期锚点、原生10秒网格精确选点；没有轨道积分、拟合或密度反演。与既有TIE条件查询的UTC、ITRS和WGS84值逐点核验一致。

- 全361点有效；密度最小{s['rho_kg_m3']['min']:.12e}、最大{s['rho_kg_m3']['max']:.12e}、中位{s['rho_kg_m3']['median']:.12e} kg/m³。
- WGS84高度{s['height_m']['min']/1000:.6f}—{s['height_m']['max']/1000:.6f} km，纬度{s['latitude_deg']['min']:.6f}—{s['latitude_deg']['max']:.6f}°。
- 361点批量调用含驱动构造{s['batch_wall_s']:.6f}s，约{s['batch_wall_s']/361*1000:.3f}ms/点；单点契约361次均值{b['mean']:.3f}ms，P95 {b['p95']:.3f}ms。
- 整个只读审计、离线计算和绘图{a['total_analysis_wall_s']:.3f}s，进程累计峰RSS {a['peak_process_RSS_MiB']:.3f}MiB；含库/图形内存，不是模型独占增量。
- 原46个S3/S7 NetCDF和2个沿轨CSV读取前后48项SHA相符；原始SP3哈希见审计orbit_metadata，并与冻结源清单复核。

初次离线脚本在解析旧审计的相对文件路径时于计算前失败，没有模型积分或结果；保留失败日志nrlmsis_comparison.log和空v1目录，修正后独立v2完成。没有覆盖任何旧实验。

复现：source scripts/activate_orbit.sh；python scripts/prepare_nrlmsis_drivers.py（只接受同内容）；PYTHONPATH=src python -m unittest discover -s tests -v。离线运行python scripts/run_nrlmsis_comparison.py --run-tag nrlmsis2023_v2（已存在则拒绝；公共输出也禁止覆盖）。在副本中复现或显式改新产物命名，不能覆盖本次证据。

数据：results/metrics/nrlmsis2023_300s.csv、nrlmsis2023_60s.csv；完整审计{root}。本次新TIE积分0、新RK45积分0。
''')
rows=[x for x in a['comparison'] if x['region']=='global']
table='\n'.join(f"|{x['mapping_source']}|{x['relative_median_percent']:.3f}%|{x['absolute_relative_p95_percent']:.3f}%|{x['density_difference_RMSE_kg_m3']:.6e}|{x['log_RMSE']:.6f}|" for x in rows)
peak='\n'.join(f"- {k}：{v['utc']} UTC，纬度{v['wgs84_lat_deg']:.3f}°、经度{v['wgs84_lon_deg']:.3f}°，椭球高{v['height_wgs84_m']/1000:.3f}km，密度{v[k+'_kg_m3']:.6e}kg/m³。" for k,v in a['peaks'].items())
write('reports/NRLMSIS_TIEGCM_COMPARISON.md',f'''# NRLMSIS与TIE-GCM沿SP3密度比较

HINDCAST；全部TIE比较为PROVISIONAL。NRLMSIS不是观测真值，S7没有被证明更准确。以下是相同参考轨迹上的模型条件差异，不是轨道预测误差。

## 共同数据与假设

361个60秒SP3点、窗口2023-03-21 00:00:02—06:00:02 UTC。NRLMSIS明确使用WGS84。TIE复用data/processed/swarm_provisional_v1/PROVISIONAL_full_S3/S7.csv，源SHA、时间、ITRS位置和WGS84转换全部匹配；没有使用上一任务各自传播轨迹的密度冒充同轨迹对照。A为WGS84纬度/椭球高近似原生ZG，B为地心纬度和r−6371000m近似ZG。两者均不是已验证的参考面转换；正式TIE外部接口仍拒绝。

## 结果

相对差定义(TIE/NRLMSIS−1)，P95为其绝对值的95分位；log为自然对数ln(TIE/NRLMSIS)，密度差RMSE单位kg/m³。

|条件|相对差中位|绝对相对差P95|密度差RMSE|log比值RMSE|
|---|---:|---:|---:|---:|
{table}

四组在整个样本集均低于NRLMSIS。B相较A的中位负差较小，但P95更大，不能据此称B更准确。S7相较S3较接近本次NRLMSIS，也不构成S7真实性证据。具体纬带统计在results/metrics/nrlmsis2023_comparison.csv（南北极区±60°、中纬30—60°、低纬±30°）；各纬带仅代表本轨迹采样，不能推及全球空间平均。

A的log比与绝对纬度相关接近0；B的相关约0.81，与高度约0.55，提示映射B的纬度相关径向高度变化会改变比较结构。轨道高度、纬度、地方时和相位共变，不能从该相关性作因果分解或把重复轨道样本当独立统计样本。

峰值（60秒离散样本，不是连续极值）：

{peak}

## 原因区分与性能

- S3/S7只改变预热历史；A/B改变外部坐标假设；NRLMSIS/TIE还包含模型结构、驱动定义/时间插值和物理强迫差异。
- NRLMSIS是前日Fobs、当日中心81日均值和分段三小时Ap历史；TIE是自身太阳时间插值及Kp→POWER/CTPOTEN路径。相同原GFZ来源不代表进入模型的驱动数值/物理作用相同。
- NRLMSIS的批量计算与现有TIE条件CSV扫描/重用是不同操作。成本图分别标注，不将CSV读取时间冒充TIE模型仿真或原生插值成本。S3/S7历史仿真成本见各自运行报告，本次没有重运行。
- 低阶引力、Cd/面积/姿态/推力未闭合，本次未用任何气动参数，未计算新的轨道、未校准未来SP3、未作正式精度排名。

## 图表与下一步

results/figures/nrlmsis2023_density.png、ratios.png、latitude.png、drivers.png、cost.png（后四个同nrlmsis2023_前缀），分别给出密度、比值/log、纬带、驱动和计算开销。逐时刻原表/审计/峰值均可独立重算。

软件上已具备显式经验密度DensityProvider契约，可在另获授权后以同一演示参数开展受控RK45探索；正式Swarm精度评估仍被高度、气动、推进器和完整受力问题阻碍。本次到离线密度分析为止。
''')
print('Three reports written')
