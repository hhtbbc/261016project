"""Reports and progress updates from completed C0-C3 evidence, not assumed results."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/common_density_h6_v1'
def write(p,text):
 with (ROOT/p).open('x') as f:f.write(text.rstrip()+'\n')
def append(p,text):
 x=ROOT/p;x.write_text(x.read_text()+'\n\n'+text.rstrip()+'\n')
def main():
 a=json.loads((F/'analysis.json').read_text());s=json.loads((F/'run_summary.json').read_text());c=json.loads((F/'configuration.json').read_text());assert s['passed'];tag='PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST / FORCE_MODEL_INCOMPLETE / PROVISIONAL_EPHEMERIS'
 lines=['# 统一H6背景下的NRLMSIS与TIE-GCM六小时条件对照',tag,'\n## 研究目标及范围\n','遵循10月19日早会第一阶段路线：SGP4、经验大气/RK45、TIE-GCM/RK45，研究密度与计算成本。当前完成统一非阻力动力学后的条件敏感性研究，正式物理精度验证仍未完成，第二阶段FourCastDEN未启动。旧D0—D5为J2背景，本轮不重跑、不混合排名；SGP4初始化不同，继续独立报告。\n',
 '## 冻结设置\n',f"C0读取已有H6 base/tight，无新增无阻力传播。C1=H6+NRLMSIS2.1/pymsis0.13.0；C2=H6+S7/A，C3=H6+S7/B。共同H6=完整EGM2008 40×40+ERFA日月地心差分力，已包含中心项，不额外叠J2/J3/J4。共同配置SHA `{c['common_freeze_sha256']}`，初态SHA `{c['initial_sha256']}`。\n",'窗口2023-03-21 00:00:02—06:00:02 UTC，单次SP3原生P/V初始化，GCRS积分、每60秒输出361点。全部同EOP/闰秒、GM/R/C/S、星历及RK45：base rtol1e−10/位置atol1e−3m/速度atol1e−6m/s/maxstep30s；tight1e−12/1e−5m/1e−8m/s/15s。实际配置及逐启动标记在experiments/common_density_h6_v1。\n',
 'm=400kg、Cd=2.2、A=1m²是显式演示，CdA/m=0.0055m²/kg，m/(CdA)=181.818kg/m²。共转大气/零ITRS中性风，使用完整ITRS速度，不重复减ω×r。C1使用模型明确支持的WGS84；C2映射A假设WGS84纬度/椭球高近似原生ZG；C3映射B用地心纬度与r−6371000m近似ZG。A/B均未经严格登记，不等于相同物理高度。正式外部接口继续EXTERNAL_DATUM_UNVERIFIED。\n',
 '## 软件链路与数据门禁\n','同一个CommonForceModel与原DragForce组合；每次RHS使用当前预测状态实时查询，不读沿SP3的密度表。MsisResearchDrag/ProvisionalDragForce和既有框架/插值均复用，仅新增仪表化包装，不改旧源码。自动天气下载入口被显式禁止，冻结GFZ通量/Ap历史；内部时刻保留精度，Ap按UTC三小时桶切换不平滑。S7索引一次，有界4096列LRU；每查询两帧×四邻点均须有效。失败/越界/非正或非有限密度立即中止，不补0或外推。187项测试通过，包含关闭阻力恢复H6、参数/标签/驱动边界与门禁；旧单位/缝合/极区测试仍通过。\n',
 '历史SGP4独立48小时基准：平均625.566m、三维RMSE763.846m、终点1724.640m；时间窗与初始化来源不同，不加入本轮六小时RK45受控排名。详见SGP4_SP3_BASELINE_2026-10-20.md。\n','## 模型间轨道差（不是相对SP3误差）\n','RAC基于共同C0同历元GCRS状态：R向外，C沿r×v，A=C×R；符号为前者减后者。\n','|差值|1h m|3h m|6h m|全窗RMS m|最大 m|终点R/A/C m|','|---|---:|---:|---:|---:|---:|---|']
 for n,x in a['pairs'].items():lines.append('|'+n+'|'+'|'.join(f'{v:.6f}' for v in x['hours_1_3_6_m'])+f"|{x['rmse_3d_m']:.6f}|{x['max_norm_m']:.6f}|"+'/'.join(f'{v:.4f}' for v in x['terminal_RAC_m'])+'|')
 lines+=['\n## SP3探索性诊断残差\n','SP3为精密参考产品，不是绝对无误差真值；仅t0用于初始化，后续不修正状态或拟合参数。RAC采用同历元SP3 GCRS P/V。\n','|模型|1h m|3h m|6h m|全窗三维RMSE m|终点R/A/C m|','|---|---:|---:|---:|---:|---|']
 for n,x in a['residuals'].items():lines.append('|'+n+'|'+'|'.join(f'{v:.6f}' for v in x['hours_1_3_6_m'])+f"|{x['rmse_3d_m']:.6f}|"+'/'.join(f'{v:.4f}' for v in x['terminal_RAC_m'])+'|')
 lines+=['\n## 数值收敛\n','运行前预注册一小时单轨<0.02m、阻力响应配对差<响应最大模1%；六小时单轨<0.5m，全部6组配对差<0.1m。完整配对差向量=(base组差)−(tight组差)，不比较两个标量模之差，不事后调宽。C0的tight也读取历史H6。这些是两组数值配置的差异，不是严格数学全局误差界，也不包含10分钟大气场的欠采样不确定性。\n','|单轨|最大位置差 m|位置RMS m|最大速度差 m/s|最大R/A/C差 m|','|---|---:|---:|---:|---|']
 for n,x in a['convergence'].items():lines.append(f"|{n}|{x['max_position_m']:.9f}|{x['rms_position_m']:.9f}|{x['max_velocity_m_s']:.9g}|"+'/'.join(f'{v:.7f}' for v in x['max_abs_RAC_m'])+'|')
 lines+=['\n|配对|最大变化 m|位置RMS m|最大速度变化 m/s|','|---|---:|---:|---:|']
 for n,x in a['paired_convergence'].items():lines.append(f"|{n}|{x['max_position_m']:.9f}|{x['rms_position_m']:.9f}|{x['max_velocity_m_s']:.9g}|")
 lines+=['\n## 密度→阻力→轨道\n','下表是各自实际传播轨迹、60秒输出点上的范围；逐RHS真实查询另存压缩审计记录，不能把输出样本范围称为全部内部时刻极值。\n','|模型|密度范围 kg/m³|阻力范围 m/s²|相对速率范围 m/s|','|---|---|---|---|']
 for n,x in a['density_on_own_trajectory'].items():lines.append('|'+n+'|'+'|'.join(f"{x[key]['min']:.8g}—{x[key]['max']:.8g}" for key in ['rho_kg_m3','drag_norm_m_s2','relative_speed_m_s'])+'|')
 lines+=['\n另用共同C0的361个固定状态/时刻离线查询三种密度，隔离路径变化；该表从不进入RHS。相同质量/Cd/面积和相对速度下，阻力模之比等于密度比。相对差按|ρ前者/ρ后者−1|定义，分母为后者，并非对称差；同时报告log密度比。各自在线路径上的密度变化还含轨道位置差，不能混为纯模型差异。约3小时附近NRLMSIS曲线的输入切换对应UTC 03:00的Ap桶边界，保留实际驱动，不人为平滑。密度改变能量与周期，累积为轨道相位位移，因此阻力方向为减速，并不意味着同历元位置必然沿轨落后。\n','|同C0位置密度比|比值中位数|绝对相对差P95|ln比值RMS|','|---|---:|---:|---:|']
 for n,x in a['same_position_density'].items():lines.append(f"|{n}|{x['ratio_median']:.6f}|{100*x['absolute_relative_p95']:.4f}%|{x['log_difference_rms']:.6f}|")
 lines+=['\n纬度带统计见latitude_density_comparison.csv，全部使用共同C0位置纬度。差异包括模型/驱动约定与A/B高度假设，S7未证明充分初态无关，不能据比值判断哪个接近真实大气。\n',
 '## 计算成本分层\n','|模型|历史场生成 s|密度查询均值/P95 ms|查询数|nfev|积分 s|含输出在线 s|列读取/缓存命中|','|---|---:|---|---:|---:|---:|---:|---|']
 for n,x in a['resources'].items():lines.append(f"|{n}|{x['offline_field_s']:.3f}|{x['query_mean_ms']:.3f}/{x['query_p95_ms']:.3f}|{x['density_queries']}|{x['nfev']}|{x['integration_s']:.3f}|{x['online_total_s']:.3f}|{x['column_reads']}/{x['cache_hits']}|")
 lines += [f"\n本轮6次一小时预检、6次六小时传播，总传播阶段墙钟{s['propagation_wall_s']:.3f}s，运行进程峰RSS{s['peak_RSS_MiB']:.3f}MiB。C0是历史成本，本次新增C0传播=0。在线成本含密度查询，不能把查询耗时再加进积分时间。S7历史生成1382.676s（9天10分钟、4MPI），原场本次复用，新增离线场生成=0；A/B共享同一S7场，不重复计算两次必需生成费用。单组从零参考成本=S7一次生成+本组在线；复用的边际成本只有在线。NRLMSIS在本项目无需生成全球多日场，模型开发/标定成本未纳入。\n",'S7列读取是每个缓存未命中的NetCDF列读取/开关句柄次数，每次读DEN/ZG；初始化另扫描14个卷的时间/网格元数据，未把这些元数据扫描伪装成零I/O。列LRU上限4096，实例结束关闭缓存，无长期开启句柄。MSIS无外部密度缓存，Fortran内部状态与冻结驱动复用。查询P95包含真实冷热缓存，内存按进程累计峰报告。离线仿真/查询/积分工作量不同，不以一次全球仿真与一次点查询直接给加速倍数。\n',
 '## 与旧J2背景的关系\n','旧D0终点SP3残差1066.087m，旧D5 903.190m，旧S7/A(D2)957.104m、S7/B(D4)951.417m；旧D5−D2/D4模型间终点差58.333/52.202m。本轮更新的是共同非阻力背景，旧数值只说明此前条件，不直接与新结果混成密度排名，也不能把残差的全部改变称为密度改进。新背景仍有截断/其他受力不确定性。\n',
 '## 正式验证条件与下一阶段\n','可靠结论：实现了在相同H6、初态、合成气动和数值条件下，仅改变密度来源/明确映射的可审计响应；本轮门槛内数值稳定。尚不能证明真实轨道预测优劣、S7充分预热或真实密度准确。仍需0601姿态/Flags/面积几何、Cd气体表面与参考面积、质量不确定度、dt_thr/f_thr实际推力解释、TIE ZG外部登记、预热初态敏感性及独立高频场验证；40阶截断未充分收敛、ERFA近似、SRP/潮汐/相对论等仍限制正式精度。不得用验证SP3拟合参数。下一步优先证据闭合及受控方案，不自动延长或开展AI。\n',
 '## 产物与复现\n','实际配置、门禁、独占启动标志和各次资源JSON在experiments/common_density_h6_v1；完整NPZ与逐RHS gzip JSONL在data/processed/common_density_h6_v1（不入库）；结果CSV/图以common_density_h6_v1_为前缀位于results/metrics、results/figures。日志logs/common_density_{tests,preflight,runs,analysis,audit}.log。\n','命令：source scripts/activate_orbit.sh；python -m unittest discover -s tests；python scripts/run_common_force_density_comparison.py（静态核验）；同命令--execute（本标签已执行，独占保护拒绝再运行）；python scripts/analyze_common_density.py；python scripts/write_common_density_reports.py；python scripts/audit_common_density.py。复现须另授权新标签并同步分析路径，禁止覆盖原结果。\n']
 write('reports/COMMON_FORCE_DENSITY_ORBIT_COMPARISON.md','\n'.join(lines))
 text=f'''## 2026-10-21：统一H6的C0—C3条件密度矩阵完成

C0复用H6，未重跑。新增C1/C2/C3各1h base/tight、6h base/tight，共12次，预注册单轨/配对门槛通过，187测试通过；无新TIE/更高阶/AI/长窗。C1−C2终点{a['pairs']['C1_C2']['terminal_m']:.6f}m，C1−C3 {a['pairs']['C1_C3']['terminal_m']:.6f}m，C2−C3 {a['pairs']['C2_C3']['terminal_m']:.6f}m。全部仍为{tag}。

共同H6/旧实验/驱动保护SHA不变，正式TIE入口仍拒绝。总传播{s['propagation_wall_s']:.3f}s、峰RSS{s['peak_RSS_MiB']:.3f}MiB。三种在线密度、同C0位置离线密度、力/轨道及SP3探索残差均有CSV/审计/图。主报告reports/COMMON_FORCE_DENSITY_ORBIT_COMPARISON.md。正式气动/推力/高度/预热/时间分辨率和缺失力门禁未解除；本轮完成后停止。下一步优先取得FORMAL_PARAMETER_EVIDENCE_REQUESTS列明的资料并设计物理验证，不自动扩窗或训练。'''
 for p in ['STATUS.md','WORKLOG.md','docs/PROJECT_PLAN.md','docs/COMMON_FORCE_MODEL_DECISION.md']:append(p,text)
 p=ROOT/'STATUS.md';p.write_text(p.read_text().replace('# 当前状态\n','# 当前状态\n\n> 最新：统一H6的C0—C3六小时条件密度对照完成，详见末节及COMMON_FORCE_DENSITY_ORBIT_COMPARISON。正式物理精度门禁仍保留。\n',1))
 append('AGENTS.md','''## H6密度矩阵完成后的门禁

common_density_h6_v1已单独授权完成C1/C2/C3各1h和6h base/tight共12次，C0读取既有H6，187测试及单轨/配对数值门槛通过。所有结果PROVISIONAL/SYNTHETIC_AERODYNAMIC_PARAMETERS/HINDCAST/FORCE_MODEL_INCOMPLETE，加PROVISIONAL_EPHEMERIS。旧J2 D0—D5仅历史条件；不得混旧新排名。共同配置SHA、旧源码/驱动/数据保持，正式TIE仍EXTERNAL_DATUM_UNVERIFIED。真实参数/推力/高度/预热/时间分辨率及截断/缺失力门禁继续。任务结束停止；任何新增传播/长窗/TIE/更高阶/AI须新授权。''')
 write('reports/PHASE1_H6_DENSITY_UPDATE.md',text+'\n\n以上旧D0—D5表保留为历史快照，最新H6矩阵采用完整40阶+日月共同背景。三路线工程原型与条件敏感性研究进一步完善，正式精度验收依然未完成；不按条件SP3残差给密度模型排名。')
 append('WORKLOG.md','关键命令及文件：source scripts/activate_orbit.sh；187项unittest；run_common_force_density_comparison.py静态及唯一--execute；analyze_common_density.py离线；write_common_density_reports.py；audit_common_density.py逐查询/历史SHA独立审计。复用.venv310，无安装/下载；缓存日志均项目内。新增common_density_research包装复用现有力/坐标/密度实现，冻结配置未修改。运行器按一小时实测×6×1.10预算门禁，失败不重试。Git安全提交与远端实际SHA核对见同步日志及最终汇报。')
if __name__=='__main__':main()
