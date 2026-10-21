"""Generate reports from actual completed H6 evidence only."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/common_force_validation_v1'
def write(path,text):
 with (ROOT/path).open('x') as f:f.write(text.rstrip()+"\n")
def main():
 a=json.loads((F/'analysis.json').read_text());s=json.loads((F/'run_summary.json').read_text());c=json.loads((F/'effective_configuration.json').read_text());assert s['passed'];lab='PROVISIONAL / HINDCAST / FORCE_MODEL_INCOMPLETE'
 lines=['# H6组合力模型与数值验证',f'\n状态：{lab}；日月另保留PROVISIONAL_EPHEMERIS。\n','## 方法与独立检查\n','CommonForceModel只组合一次完整EGM2008 40×40地球物理加速度及一次日月地心差分加速度；全部GCRS状态、SI，不额外叠中心项/J2，不含阻力、SRP、潮汐、相对论或假设推力。独立组合检查：关闭日月逐位恢复H4；退到20阶恢复H5；组件和、时间越界拒绝、连续性、单位/元数据检查。继承此前SHTOOLS和Horizons独立证据，不把SP3残差改善作为验证。\n',
 '181项全套测试通过（logs/common_force_tests_pass.log）。第一次测试发现新测试缺少src导入路径，修正测试引导后完整通过；没有模型传播重试。\n',
 '## 预注册门槛与实际结果\n','运行前docs/H6_VALIDATION_DESIGN.md固定单轨最大位置差<0.5m、配对差最大<0.1m、600秒预检<0.02m；速度和RAC报告不事后扩宽门槛。配对是(base模型差向量)−(tight模型差向量)，非两个标量位移之差。\n',
 '|检查|最大位置差 m|位置RMS m|最大速度差 m/s|门槛 m|结果|','|---|---:|---:|---:|---:|---|']
 for n,g in s['gates'].items():lines.append(f"|{n}|{g['max_position_m']:.9f}|{g['rms_position_m']:.9f}|{g['max_velocity_m_s']:.9g}|{g['threshold_m']}|PASS|")
 lines+=['\n完整逐时刻位置、速度和RAC见results/metrics/common_force_v1_convergence.csv及paired_convergence.csv。RAC数值比较使用共同历史H3惯性状态；SP3残差用同历元SP3的完整惯性状态。非严格数学全局误差界，也非星历/截断/真实气动不确定度界。\n',
 '## 冻结范围\n','所有门禁通过，仅冻结configs/provisional_common_force_model.json供下一阶段条件实验；包含系数/源码/初态/EOP与证据SHA、数值配置、星历与缺失受力。40阶未证明截断收敛，真实参数/高度/预热未闭合。没有C0—C3或其他新阻力/TIE/AI任务。\n']
 write('reports/H6_FORCE_MODEL_VALIDATION.md','\n'.join(lines)+'\n')
 lines=['# H3—H6六小时无阻力对比',f'\n{lab}；ERFA内置星历PROVISIONAL_EPHEMERIS。\n','## 实验条件\n',f"2023-03-21 00:00:02—06:00:02 UTC，GCRS积分、60秒输出361点，初态SHA `{c['initial_sha256']}`。H3/H4/H5 base及H3 tight只读历史，新增H4/H5 tight、H6 base/tight共4次六小时和H6两次600秒预检，无重试。\n",'EGM2008同源fully_normalized/tide_free，GM=3.986004415e14m³/s²，R=6378136.3m；40阶源SHA5ae41b8ae698a9c32448c8bfb27183297910e21c4edba6beb37c64ee355c6848。时间数据及完整base/tight参数见effective_configuration.json（configuration.json为继承来源快照，其旧degree/PENDING等字段不代表本轮有效配置）；rtol1e−10/1e−12，位置atol1e−3/1e−5m，速度atol1e−6/1e−8m/s，最大步长30/15s。\n',
 '## SP3诊断残差\n','SP3不是无误差真值；没有使用验证窗口拟合或修正状态。\n','|模型|1h m|3h m|6h m|全窗三维RMSE m|终点R/A/C m|','|---|---:|---:|---:|---:|---|']
 for n,x in a['residuals'].items():lines.append('|'+n+'|'+'|'.join(f'{v:.6f}' for v in x['hours_1_3_6_m'])+f"|{x['rmse_3d_m']:.6f}|"+'/'.join(f'{v:.3f}' for v in x['terminal_RAC_m'])+'|')
 lines+=['\n## 模型间位移（不是预测误差）\n','|差值|终点 m|全窗最大 m|全窗RMS m|终点R/A/C m|','|---|---:|---:|---:|---|']
 for n,x in a['pairs'].items():lines.append(f"|{n}|{x['terminal_m']:.6f}|{x['max_norm_m']:.6f}|{x['rmse_3d_m']:.6f}|"+'/'.join(f'{v:.3f}' for v in x['terminal_RAC_m'])+'|')
 lines+=['\nH6−H4只改变日月力；H6−H5只改变20→40阶；H6−H3同时改变两者，不能归因于单项。三个方向可有不同响应，不以终点残差最小删力或选系数。20→40既有最大33m/终点15m仍超过5m候选目标，H6数值收敛不证明40阶物理截断充分。\n','## 成本与资源\n','|本次传播|积分墙钟 s|nfev|接受步|','|---|---:|---:|---:|']
 for n,x in s['runs'].items():lines.append(f"|{n}|{x['elapsed_s']:.3f}|{x['nfev']}|{x['accepted_steps']}|")
 lines+=[f"\n本次受控运行总墙钟{s['wall_s']:.3f}s，进程峰值RSS {s['peak_RSS_MiB']:.3f}MiB，低于1800s/2GiB。无GPU。总墙钟包含门禁、输出和保护哈希检查，不含先行测试/离线制图；单轨耗时是当前机器实测非可移植速度标准。历史H3/H4/H5成本与当前H6见resources.csv，未将旧计算算成本次新传播。\n",'## 证据与局限\n','运行配置/launch_once/资源门禁/完整summary、analysis及SHA审计在experiments/common_force_validation_v1；轨道NPZ在data/processed/common_force_validation_v1（本地保留）。CSV和六张图以common_force_v1_为前缀位于results/metrics和results/figures。完整日志logs/common_force_runs.log。原实验及冻结源码SHA未变。\n','日月采用ERFA epv00/月moon98，与NASA Horizons几何参考有既有独立比较，但完整相对论空间/GM时标登记未闭合。仍缺SRP、潮汐/时变重力、相对论及实际推力。真实Cd/面积/姿态标志、TIE外部参考面、预热与高频场验证均未完成。下一阶段只建议另授权按PROVISIONAL_DENSITY_COMPARISON_PLAN开展条件研究，不宣称正式精度排名。\n']
 write('reports/H6_ORBIT_COMPARISON.md','\n'.join(lines)+'\n')
if __name__=='__main__':main()
