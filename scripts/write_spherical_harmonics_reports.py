"""Reports from saved validation/propagation audits only."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/spherical_harmonics_v1'
a=json.loads((F/'analysis.json').read_text());v=json.loads((F/'validation.json').read_text());run=a['run'];c=json.loads((F/'configuration.json').read_text())
validation=f'''# 完整8×8球谐引力验证

## 实现与来源

新增独立`spherical_harmonics_gravity.py`，使用已有GFZ EGM2008低阶前缀、完整n≤8/m≤n的C/S组合，自身GM={c['GM']:.0f}m³/s²、R={c['radius_m']}m，完全归一化/无CS相位/tide_free。机械势U为负，a=−grad U。笛卡尔实心球谐与梯度同步递推，不存在经度/极区除零；中心引力已包含，不再叠加旧模型。完整推导和参数差见[设计](../docs/SPHERICAL_HARMONICS_GRAVITY_DESIGN.md)。

## 外部软件与数学验证

使用SHTOOLS 4.14.1独立Fortran MakeGravGridPoint，显式omega=0，不含离心项；将其r/theta/phi向量独立变换Cartesian。100随机位置最大向量绝对差{v['max_absolute_difference_m_s2']:.9e}m/s²、相对差{v['max_relative_difference']:.9e}；固定门限rtol/atol=2e−12/2e−12m/s²。赤道和±89.9°近极也通过。SHTOOLS自身PlmBar_d1不支持精确极点（初次参考调用触发Fortran STOP，不能把进程退出0当测试成功）；生产精确两极另用有限性/邻近连续性及m=0解析式验证，没有扩大容差。

独立scipy lpmv计算势，解析中心/J2/J3/J4统一源参数比较；只开启J2及关闭各阶恢复、C22/S22经度变化、order截断、非法输入、全矩阵力旋转与有限性测试通过。9项新增、全151项测试通过，最终日志`logs/spherical_final_tests.log`。旧9项J3/J4测试仍保留，不等于执行了另一完整轨道软件。

中心差分势负梯度：

|h(m)|相对差|
|---:|---:|
'''
for x in v['finite_difference']:validation+=f"|{x['step_m']:.0f}|{x['relative_error']:.9e}|\n"
validation+=f'''
细步门限2e−8保持，三档二阶收敛。真实六小时base/tight最大位置差{run['convergence_max_m']:.9f}m，低于预注册0.5m；没有用SP3残差设门限或拟合初态/系数。

## 时间、框架及保护

同旧初态SHA `{c['initial_sha256']}`，GCRS积分，经现有EarthFixedFrame/Astropy与ERFA c2t06a旋至ITRS计算，再Q.T仅旋物理力；TT/UT1/xp/yp冻结，与旧框架相同，不加入观测dX/dY、相对论缩放/潮汐等。含m≠0必须完整地球旋转，不能只用轴向。177项历史保护文件SHA前后不变，六份CDF另行校验。无旧D0—D5重跑、无TIE/新阻力/AI/48h传播。

## 环境与复现

复用.venv310 Python3.10.19。外部参考wheel13,898,723字节，PyPI SHA核验；初次仅安装pyshtools无依赖，完整包检查发现4项可视化/高层依赖缺失。为不升级项目，随后卸载此包、只将已验证wheel解包至`.local/reference/pyshtools_4_14_1`，加载自带Fortran扩展/动态库；不是全pyshtools Python API安装。原72包兼容，见`logs/spherical_environment_check.log`。原始wheel/元数据和二进制不入Git，轻量wheel/二进制SHA在`configs/spherical_reference.json`。初次degree0初始化误加degree1零项导致静态测试失败，修正后才通过门禁并运行轨道；保留失败日志，无失败传播重试。

复现依次：`source scripts/activate_orbit.sh`；`python scripts/prepare_spherical_reference.py`；`PYTHONPATH=src python -m unittest discover -s tests -v`；`python scripts/validate_spherical_harmonics.py`；`python scripts/run_spherical_harmonics_comparison.py`静态，再`--execute`。当前标签已使用，不得重放授权，脚本以x模式拒绝覆盖。异地需先按配置清单取得原GFZ前缀及冻结SP3/EOP资源；这不是脱离数据可单文件运行的软件。外部软件交叉验证是当前截断引力数值检查，不是Swarm轨道真实精度证明。
'''
(ROOT/'reports/SPHERICAL_HARMONICS_VALIDATION.md').write_text(validation)
text='''# 完整8×8球谐无阻力轨道比较

PROVISIONAL / HINDCAST / NO_DRAG

## 共同条件与参数变化

Swarm-A，2023-03-21 00:00:02至06:00:02 UTC，361个60秒输出；相同单历元SP3原生P/V与GCRS完整状态转换，无未来SP3拟合/中途校正。旧G0/G1/G2只读。只运行一次H1十分钟短例和H1六小时base/tight各一次，没有扩大阶数、加入大气或运行TIE。

H1为统一静态EGM2008 8×8（含C22/S22及所有非轴对称项），不再采用原名义J2。相对G0，GM减少300000m³/s²、参考半径减少0.3m、C20及所有高阶参数体系一并变化，因此H1−G0不是仅“增加高阶项”的纯效应。加速度表单列源GM/C20变化的共同状态量级，未额外运行隔离轨道、不能分解其独立累计位移。

base rtol=1e−10、位置atol=1e−3m/速度1e−6m/s、maxstep30s；tight为1e−12、1e−5m/1e−8m/s、15s。冻结EOP/闰秒及坐标入口相同。SP3为有自身不确定性的后处理参考；R向外、C沿参考r×v、A=C×R，残差为模型减参考。

## SP3残差

|模型|1h(m)|3h(m)|6h终点(m)|全段3D RMSE(m)|R/A/C RMSE(m)|
|---|---:|---:|---:|---:|---|
'''
for n,s in a['residuals'].items():
 h=s['hour_1_3_6_m'];text+=f"|{n}|{h[0]:.6f}|{h[1]:.6f}|{s['terminal_m']:.6f}|{s['rmse_3d_m']:.6f}|"+' / '.join(f'{x:.6f}' for x in s['rac_rmse_m'])+'|\n'
h=a['residuals']['H1'];g=a['residuals']['G0']
text+=f'''
H1相对G0终点变化{h['terminal_m']-g['terminal_m']:+.3f}m，全段RMSE变化{h['rmse_3d_m']-g['rmse_3d_m']:+.3f}m。H1终点R/A/C分别为{h['terminal_RAC_m']}m。实际存在的方向残差按表报告，不预设8×8必然降低全部方向，也不以这组SP3结果挑选最终模型。

旧G1终点更小不能证明J4错误；旧G2全段RMSE更大只反映不完整受力下的残差变化。此前独立数学公式已通过，本次进一步用外部Fortran验证完整球谐实现。剩余残差可能涉及截断、GM/C20/潮汐/世变、未建模阻力/日月引力/SRP/推力、初态及参考等；本实验不能唯一分配来源。

## 模型间位移

|模型对|终点(m)|全段RMS(m)|
|---|---:|---:|
'''
for n,s in a['model_differences'].items():text+=f"|{n}|{s['terminal_m']:.6f}|{s['rmse_3d_m']:.6f}|\n"
text+='''
这些是模型间位移，不是预测误差。此前J2背景的合成阻力D5−D0终点174.662m、不同密度终点差52—65m仅为历史尺度参考；不能与新引力轨道混用作大气归因。

## 性能与收敛

|运行|墙钟(s)|nfev|接受步数|
|---|---:|---:|---:|
'''
for n,s in run['runs'].items():text+=f"|{n}|{s['elapsed_s']:.6f}|{s['nfev']}|{s['accepted_steps']}|\n"
text+=f'''
整个新传播流程{run['wall_s']:.3f}s，累计峰RSS {run['peak_RSS_MiB']:.3f}MiB，无GPU。base/tight最大位置差{run['convergence_max_m']:.9f}m；正常终止、状态有限、初态一致。H1每次RHS使用完整现有Astropy状态/地球旋转，计时包含框架转换，不能和旧缓存轴J2/G1/G2计时直接归因于球谐多项式计算。

共同H1状态加速度差范围：

'''
for n,limits in a['acceleration_ranges'].items():text+=f"- `{n}`：{limits[0]:.9e}—{limits[1]:.9e}m/s²。\n"
text+='''
## 成果与下一步门禁

真实图：`results/figures/spherical_harmonics_v1_*.png`（残差、RAC、模型差、收敛、加速度）；逐时刻CSV/性能表在`results/metrics/spherical_harmonics_v1_*`。配置/预注册验证/三次launch标记/审计在`experiments/spherical_harmonics_v1`，NPZ本地`data/processed/spherical_harmonics_v1`不上传。结果可重复审计但当前run-tag不允许重放。

下一步先研究20×20截断敏感性与日月引力、SRP/遮影/潮汐/低阶世变及真实推力，不自动执行。真实Swarm面积/Cd/姿态质量与推力仍缺当前产品版本证据；TIE高度/预热/时间插值门禁不变。未来NRLMSIS/TIE所有对照必须共同升级同一引力模型，冻结相同初态、气动、风、积分/EOP，再作另获授权的探索矩阵；正式精度结论还需完整物理与独立验证。不能以本次无阻力更小残差宣布某大气模型准确。
'''
(ROOT/'reports/SPHERICAL_HARMONICS_ORBIT_COMPARISON.md').write_text(text)
print('Reports written from actual audits')
