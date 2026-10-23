"""Publish reports from successful recorded audits only; never launches any model."""
import json,csv
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];F=R/'experiments/tiegcm_training_mar23_v2_2022_longrun';OUT=R/'results/tiegcm_training_mar23_v2_2022_longrun'
def main():
 run=json.loads((F/'run_status.json').read_text());a=json.loads((F/'data_audit.json').read_text());c=json.loads((F/'candidate_audit.json').read_text());pre=json.loads((F/'preflight.json').read_text());rows=list(csv.DictReader((OUT/'hourly_diagnostics.csv').open()));assert a['engineering_PASS'] and c['count']==49
 def range_of(key):
  x=[float(r[key]) for r in rows];return min(x),max(x)
 def exact(key):return f'{range_of(key)[0]:.8g}—{range_of(key)[1]:.8g}'
 density=[float(r['DEN450_mean_kg_m3']) for r in rows];ratios=np.array(density[1:])/density[:-1]-1;i=int(abs(ratios).argmax())
 fields='\n'.join(f"|{k}|{v['unit']}|{v['min']:.8g}|{v['max']:.8g}|{v['masked']}|" for k,v in a['fields'].items())
 text=f'''# 2022九天连续TIE-GCM工程验收

INDEPENDENT_TIEGCM_DATA_GENERATION / HINDCAST / SPINUP_SUFFICIENCY_UNVERIFIED / VALIDATION_CANDIDATE_ONLY。

一次mpirun从2022-03-16 00:00至03-25 00:00 UTC连续积分，4MPI/OMP1、60秒、12960步。没有Restart拼接、冷启动短例重跑或2021重跑。每日primary10记录/10文件、逐小时secondary216记录/9文件，全部时刻有序唯一、无跳帧；验证候选起点03-23 00含在49个整点记录内，预热167个小时记录未提取入候选目录。

## 资源与运行

|指标|实测|
|---|---:|
|监督端到端墙钟（含最终轻量卷检查）|{run['elapsed_s']:.6f} 秒|
|采样聚合树RSS峰值|{run['peak_sampled_tree_rss_bytes']/2**20:.3f} MiB|
|子进程user+system CPU|{run['children_user_cpu_s']+run['children_system_cpu_s']:.3f} 秒|
|NetCDF|{run['netcdf_bytes']} 字节|
|运行目录与stdout生成量（提取前）|{run['total_generated_bytes']} 字节|
|MPI退出/正常退出数|{run['returncode']} / {run['normal_exit_count']}|

3600秒/16GiB树RSS/5GiB新增/每卷256MiB/磁盘余量20GiB监督均未触发；单次launch_once且无重试。RSS0.1秒采样并重复计算共享页，可能漏瞬时峰值。运行时仅检查已关闭卷，最后逐卷复核；进度采样与在线已验卷数完整保留。

## 输入、日历及驱动

GPI `{pre['gpi_sha256']}`；可执行 `{pre['executable_sha256']}`；2002初场 `{pre['restart_sha256']}`；apex `{pre['apex_sha256']}`。完整namelist/输入/代码SHA见preflight及configuration.json。START_YEAR2022、START_DAY75、STOP85，SOURCE_START80仅选择2002初猜记录。HEELIS、GSWM、更新IGRF14/apex及原SECFLDS均未裁减。

实际每10分钟驱动日志{a['driver_verified_unique_minutes']}个唯一节点通过打印精度0.000501核验；所有暖态NetCDF驱动最大标量差{a['NetCDF_driver_max_abs_difference']:.3g}<1e-10。F107范围{exact('f107d')} sfu、F107A {exact('f107a')} sfu、Kp {exact('Kp')}。与既有GpiDriver/新GPI独立插值门禁一致。逐分钟合法域静态计算检查12961节点，不能冒称逐分钟内部观测trace。全部8次午夜及最终第9日端点连续推进，无驱动越界。

## 物理字段

|字段|原生单位|有效最小|有效最大|掩码数|
|---|---|---:|---:|---:|
{fields}

14键逐卷齐备、有限；DEN正、ZG逐列垂直严格递增；TN/UN/VN仅lev顶层全填充，保留28个有效层。WN/Z/DEN/ZG/NE等ilev29。TN100—5000K、水平风绝对值<2000m/s和组分0—1/质量分数和的既有宽工程范围通过，不能据此认定所有物理偏差已解决。

lat36/lon72/lev29/ilev29与作者普通static坐标逐元素一致。DEN原生g/cm³转SI乘1000，风cm/s乘0.01，Z/ZG cm乘0.01；Z是位势高度，ZG是几何高度。原生ZG450km诊断无外推，报告有效覆盖率{exact('DEN450_coverage')}；不等同WGS84 450km或Swarm沿轨密度。

global all-level密度均值受低层大密度主导，只作结构监控；另绘制原生450km全球/纬带及P95、TN、风、组分、ZG中位剖面及驱动。最大全球450km相邻小时变化{float(abs(ratios[i]))*100:.4f}%（{rows[i]['UTC']}→{rows[i+1]['UTC']}），这是自然时间变化的诊断，不是初始化误差、模型精度或因果判定。不能只凭均值平稳宣布收敛。

primary起点含继承初猜，未计算诊断N/A不补零，不参与验证候选。次历史虽为暖态诊断，预热充分性尚未证实。没有非有限/非正DEN或基本温度工程门禁失败。

## 图与审计

results/tiegcm_training_mar23_v2_2022_longrun：density.png、latitude_bands.png、temperature_wind.png、drivers.png、composition.png、ZG_structure.png；hourly_diagnostics.csv包含216小时及候选/预热分类。全部图来自本次实际输出。NetCDF每卷SHA/UTC/字段与每帧NPZ SHA分别在data_audit.json/candidate_audit.json，大数组只保留本地。
'''
 (R/'reports/TIEGCM_2022_LONGRUN_VALIDATION.md').write_text(text)
 windows='\n'.join(f"### {name}\n\n"+'\n'.join(f"- {key}：起{v['first']:.8g}、末{v['last']:.8g}、范围{v['min']:.8g}—{v['max']:.8g}。" for key,v in vals.items()) for name,vals in a['temporal_changes_not_spinup_convergence'].items())
 (R/'reports/TIEGCM_2022_SPINUP_ASSESSMENT.md').write_text(f'''# 2022候选7天预热诊断

结论：**SPINUP_SUFFICIENCY_UNVERIFIED**。工程连续运行通过，不等于物理初态影响已经消除。本次只有2002完整初猜出发的一条轨迹，无同驱动不同初场/更长预热配对，不能标正式收敛PASS。

以下单位为DEN450 kg/m³、TN K、水平风RMS m/s。前7天的首个DEN是03-16 01（初始00无有效诊断），末为03-23 00；最后48小时为03-23 00至03-25 00；验证边界诊断为03-22 12至03-23 12。所有变化发生在不同真实时刻，不是同历元初态敏感性。

{windows}

全窗口TN均值{exact('TN_mean_K')} K、水平风RMS{exact('horizontal_wind_RMS_m_s')} m/s、450km极区均值{exact('DEN450_polar_kg_m3')} kg/m³。图中昼夜/驱动/经纬度和高度结构变化保留；没有补零、平滑、删掉不利时刻。局地极端与纬带均值不能混同；原生450km未覆盖列明确计入覆盖率。仅全球均值曲线无法排除局地初态残留。

初始场2002与2022太阳活动/季节不完全匹配可能造成残余影响，现有序列不能量化它的独立贡献。2023 S3/S7已有预热敏感性，不能由本次九天没有崩溃推断7天充分。

下一阶段只设计：同历元同驱动、不同合法官方完整初场，或更长候选预热在共同目标窗口比较DEN、TN、风和组分，涵盖全球/低中高纬、原生层/450—500km有效域；沿用DENSITY_COMPARISON_DESIGN及窗口v2的预注册定义/多变量门槛，不根据本次变化事后调宽。更早预热还须扩展GPI合法域与81天支持，不能越界。无合法配对时继续该UNVERIFIED状态。

本次49帧只为VALIDATION_CANDIDATE_ONLY，不拟合归一化、不训练。工程质量、预热充分性、与作者分布一致性和真实大气精度是四个不同问题。
''')
 total=sum(f['bytes'] for f in c['frames'])
 (R/'reports/FOURCASTDEN_2022_VALIDATION_CANDIDATE_AUDIT.md').write_text(f'''# 2022独立验证候选数据只读验收

标签：INDEPENDENT_TIEGCM_DATA_GENERATION / HINDCAST / SPINUP_SUFFICIENCY_UNVERIFIED / VALIDATION_CANDIDATE_ONLY。

03-23 00至03-25 00共49帧，原地整点提取、无时间插值；预热167小时次历史未导出。目录data/processed/training_window_mar23_v2/candidates_2022，NPZ合计{total}字节。每帧十四个作者键，float32原生单位，TN/UN/VN28层、WN/Z/ZG/DEN/NE29层、LBC1层和三标量；原lev29/ilev29/lat/lon单独.npy侧车，避免破坏严格14键NPZ契约。

复用未修改作者read_var，保留原生g/cm³/cm/s/cm，不启用作者被注释的SI转换；与直接NetCDF记录去TN/UN/VN顶部后转float32逐元素相等。每帧validate_npz检查形状、有限哨兵、正DEN/温度及ZG递增。源卷SHA、记录号、NPZ SHA、时刻与全部标签完整保存；提取后只读。

作者读取器对某些missing_value属性有既有类型转换警告，未关闭数据检查；显式NetCDF掩码和独立逐元素对照验证填充值没有进入候选NPZ，警告不等同物理异常。

## 只读接口

复用OfficialFrameSource、inspect_pair及作者inference的输入拦截（在网络前中断），48个相邻小时对全部通过177二维输入/171目标/4条件，形状(1,177,36,72)/(1,171,36,72)/(1,1,4)。时间UTC连续、同2022，t状态与t+1辅助/驱动拼接；未来真实171状态仅作目标。48次未来物理真值毒化不改变输入。没有构建可训练Dataset、实例化AFNONet、网络forward、backward或optimizer.step。

兼容性检查读取既有作者普通static，并记录SHA；没有重算任何训练均值/方差。前三个外部标准化标量范围min={c['first_three_scalar_min']}、max={c['first_three_scalar_max']}。低太阳活动F107可低于作者SW_MIN80而得到<-1条件值，按原公式保留，不裁剪或当成读错。该分布差异需要在未来独立训练设计中审查，接口通过不能证明官方统计适合独立训练。

真正训练仍需预热/物理质量、仅2021训练数据的统计来源、损失/优化器/时间采样/资源/许可配置冻结；独立2022验证候选已补齐，但禁止参与训练统计；2023继续禁止训练/调参。本次不能开始科学训练，也不称作者原始训练集或论文完整训练复现。
''')
 (F/'report_numbers.json').write_text(json.dumps(dict(max_hourly_global450_change_percent=float(abs(ratios[i]))*100,candidate_npz_bytes=total),indent=2))
 print('REPORTS GENERATED FROM ACTUAL AUDITS')
if __name__=='__main__':main()
