"""Read existing evidence only; no orbit or atmosphere execution."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def write(name,text):
 with (ROOT/name).open('x') as f:f.write(text.rstrip()+'\n')
def main():
 F=ROOT/'experiments/common_density_h6_v1';a=json.loads((F/'analysis.json').read_text());s=json.loads((F/'run_summary.json').read_text());assert s['passed'];lines=['# 第一阶段阶段性技术报告（2026-10-21）','\n## 验收结论\n','三条路线的工程原型已建立；统一H6背景下的受控敏感性实验与数值门槛通过。正式卫星轨道预测精度尚未验证。本报告复用既有真实实验，无新轨道、大气仿真或参数拟合。\n','|层次|已有证据|验收判断|','|---|---|---|','|工程实现|SP3/TLE、时间坐标、SGP4、RK45、球谐/日月/阻力、NRLMSIS/TIE接口、S3/S7与审计|实现范围内通过|','|受控敏感性|冻结H6/单历元初态/合成气动下C0—C3与base/tight配对门槛|给定条件下通过|','|正式科学精度|真实气动/姿态推力、严格高度、充分预热与缺失受力尚未闭合|尚未验收，不能排名真实密度模型准确性|',
 '\n## 1. 领导研究目标与三条路线\n','按10月19日早会要求，第一阶段比较历史TLE+SGP4、NRLMSIS经验大气+RK45、TIE-GCM物理大气+RK45，研究密度对低轨传播结果及完整成本的影响。第二阶段复现/改进FourCastDEN，第三阶段才评价AI替代大气仿真后的轨道与端到端收益。RK45是数值积分方法，密度和引力是物理模型，不能预设其比SGP4准确。\n',
 '## 2. 数据、时间和参考框架\n','Swarm-A（NORAD39452），ESA SP3 reduced-dynamic后处理产品，原GPS日历/IGS20框架，10秒P/V采样，冻结GPS↔UTC、IERS-B与闰秒。SP3为精密参考而非绝对真值。历史SGP4用单条历史TLE（历元2023-03-20 20:30:00.330336 UTC，实际发布时间未完全核实），TEME正确转地固评估；48小时窗口2023-03-21 00:00:02—03-23 00:00:02 UTC，平均625.566m、三维RMSE763.846m、起点518.729m、终点1724.640m。\n',
 'C0—C3只比较共同六小时2023-03-21 00:00:02—06:00:02 UTC，361个60秒输出点；共用同一SP3单t0完整位置/速度转GCRS后自由传播，不利用后续SP3修正。SGP4初始化及窗口不同，不与此表直接排名。\n',
 '## 3. 两类大气模型\n','NRLMSIS2.1/pymsis0.13.0根据UTC、WGS84位置、前日F10.7、中心81日F10.7A与7项Ap历史直接计算经验密度。TIE-GCM2.0通过物理方程、边界和太阳/地磁驱动生成全球场，5°水平网格、60秒模型步长，S3/S7分别连续5天10分/9天10分，共同窗口每10分钟输出。两组均未证明充分初态无关；S7不是观测真值。\n',
 '所有驱动为事后冻结HINDCAST；NRL使用Ap，TIE使用自身Kp电动力约定，不混用。TIE原生ZG与外部高度登记未严格闭合，映射A/B均为PROVISIONAL。沿相同SP3参考位置的旧离线比较中S7/A、S7/B相对NRL绝对相对差P95约41.971%/45.360%（定义|TIE/NRL−1|）；不能把模型差当真实密度误差。\n',
 '## 4. 统一H6动力学\n','H6=完整EGM2008 40×40（含中心项与所有m项）+太阳/月球地心差分引力；ITRS计算地球物理加速度后转GCRS，不额外叠加中心/J2或虚拟力。GM=3.986004415e14m³/s²，R=6378136.3m，fully_normalized/tide_free。日月ERFA内置星历保留PROVISIONAL_EPHEMERIS与Newtonian坐标/GM时标限制。40阶未证明截断收敛。共同配置configs/provisional_common_force_model.json，初态SHA194f248cfaa2ea727cf70f834e47034968355249a52c177bb9d4fd3dc49eaee4。\n',
 'RK45 base/tight rtol1e−10/1e−12，位置atol1e−3/1e−5m、速度atol1e−6/1e−8m/s，最大步长30/15s。m400kg、Cd2.2、A1m²仅演示；共转大气、ITRS零中性风。每次RHS以自身预测状态查询密度并计算阻力，不使用沿SP3密度表。\n',
 '## 5. 六小时受控结果\n','C0复用无阻力H6，C1=NRLMSIS，C2=S7/A，C3=S7/B。全部PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST / FORCE_MODEL_INCOMPLETE。\n','|组|相对C0终点位移m|SP3终点残差m|SP3全窗三维RMSE m|','|---|---:|---:|---:|']
 for n in ['C0','C1','C2','C3']:
  r=a['residuals'][n];d=0. if n=='C0' else a['pairs'][n+'_C0']['terminal_m'];lines.append(f"|{n}|{d:.6f}|{r['terminal_m']:.6f}|{r['rmse_3d_m']:.6f}|")
 lines+=['\n|密度/映射对照|1h位移m|3h位移m|6h位移m|全窗位移RMS m|','|---|---:|---:|---:|---:|']
 for n in ['C1_C2','C1_C3','C2_C3']:
  d=a['pairs'][n];lines.append('|'+n+'|'+'|'.join(f'{x:.6f}' for x in d['hours_1_3_6_m'])+f"|{d['rmse_3d_m']:.6f}|")
 lines+=['\nC1终点残差较小只是当前假设下的结果，不能证明NRLMSIS真实精度优于TIE。模型间位移、SP3参考残差、base/tight数值差及大气模型真实性是不同问题。\n',
 '## 6. RAC主要发现\n','模型间RAC使用共同C0惯性状态，R向外、C沿r×v、A=C×R。C1−C0终点R/A/C约−9.834/+174.454/−0.066m；C1−C2约−3.004/+58.274/−0.022m，主要为沿轨变化。密度改变能量与周期，可导致同历元相位领先；不能用“阻力减速”直接推断同历元位置必然落后。SP3残差RAC另用同历元参考P/V。\n',
 '## 7. 数值和数据门槛\n','H6六小时base/tight最大差0.058398m；C1/C2/C3最大位置差0.062554/0.058233/0.058278m，均小于预注册0.5m；全部模型配对最大变化最差0.004324m，小于0.1m。一小时预检均通过。第一阶段矩阵完成时187项自动化测试通过，独立流式审计48,204条查询记录，核实公式/方向/驱动/8列和初态/源文件SHA。数值门槛通过不代表物理误差有相同上界，也不约束10分钟场欠采样。\n',
 '## 8. 成本分层\n','|模型|密度查询均值/P95 ms|RK45积分s|含输出在线s|一次场生成+在线参考s|','|---|---|---:|---:|---:|']
 for n in ['C1','C2','C3']:
  r=a['resources'][n];lines.append(f"|{n}|{r['query_mean_ms']:.3f}/{r['query_p95_ms']:.3f}|{r['integration_s']:.3f}|{r['online_total_s']:.3f}|{r['from_zero_field_plus_online_reference_s']:.3f}|")
 lines += [f"\n矩阵预检与tight等全部12次传播共{s['propagation_wall_s']:.3f}s，峰RSS{s['peak_RSS_MiB']:.3f}MiB。各base组4346次RHS、4707次查询，查询费用已包含在积分及在线总耗时，不重复相加。S7历史场生成1382.676s、4MPI；本轮复用，新增场生成0，A/B共享同一场，不能把生成费用重复算两次。NRL在项目内无需先生成全球多日场，其原始模型开发成本未计入。不同工作量不能直接换算全球物理仿真对单点经验模型的加速比。\n",
 '## 9. 已完成工程成果\n','数据/时间/坐标标准化，SGP4历史基准，可组合RK45引力/日月/阻力，统一球谐外部数值校验，NRLMSIS显式驱动，TIE2.0 Linux部署/apex更新/GPI/S3/S7，原生密度插值、独立候选坐标桥、两轮条件阻力矩阵、逐查询审计、CSV/图表、长期文档与GitHub版本管理均可追溯。原生Restart严格连续/分段一致性仍未通过，连续仿真路线避开了该故障，不能声称Restart已修复。\n',
 '## 10. 未完成的正式科学验证\n','真实Cd及参考面积/几何与姿态四元数0601定义、质量标志和不确定度、dt_thr/f_thr实际净推力；TIE外部高度/纬度登记；预热初态无关性与高频场；引力截断充分性、潮汐/SRP/相对论等。DNSAPOD与POD共享信息，不是绝对独立真值。详见FORMAL_PARAMETER_EVIDENCE_REQUESTS.md。不能利用验证窗口SP3拟合参数再宣称独立预测。\n',
 '## 11. 为什么现在启动FourCastDEN\n','第一阶段已提供统一数据契约、对照/数值门槛和成本口径，足以开始原生TIE参考场上的独立AI推理复现。第二阶段启动不代表第一阶段正式精度验收完成；高度、气动和受力问题继续追踪，不因AI拟合TIE良好而解除。先恢复官方权重/资产和多步逻辑，获得可复现的原生场指标，再谈训练和轨道应用；当前不训练。\n',
 '## 12. 证据入口与汇报图表\n','主证据：experiments/common_density_h6_v1/{configuration,run_summary,analysis,independent_audit,publication_review}.json；H6两报告、COMMON_FORCE_DENSITY_ORBIT_COMPARISON.md、NRLMSIS_TIEGCM_COMPARISON.md及相应results/metrics。所有表由既有JSON读取，未启动任何新模型。精选5图见PHASE1_FIGURE_INDEX_20261021.md，原图不复制或覆盖。\n']
 write('reports/PHASE1_STAGE_REVIEW_20261021.md','\n'.join(lines))
 choices=[('position_differences','模型间位移','同背景下密度来源/映射改变六小时传播，不能叫真实预测误差'),('SP3_residuals','SP3探索残差','合成参数与未闭合参考面，不按残差排名真实准确度'),('RAC_differences','RAC方向','同历元C0惯性基底，差异以沿轨为主'),('density_drag','密度与阻力','各自预测轨迹上的实时查询，区别于同位置诊断'),('costs','在线成本','查询是积分子集，不能相加；S7历史离线1382.676s另计且A/B共享')]
 text=['# 第一阶段组会图表索引（2026-10-21）','全部复用真实既有图，不重画、不复制。统一PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST / FORCE_MODEL_INCOMPLETE，星历PROVISIONAL_EPHEMERIS。\n']
 for i,(suffix,title,caption) in enumerate(choices,1):
  p=ROOT/f'results/figures/common_density_h6_v1_{suffix}.png';h=hashlib.sha256(p.read_bytes()).hexdigest();text += [f'## 图{i}：{title}',f'![{title}](../results/figures/{p.name})',caption,f'\n源图：results/figures/{p.name}；SHA256 `{h}`。对应CSV：results/metrics/common_density_h6_v1_*。\n']
 write('reports/PHASE1_FIGURE_INDEX_20261021.md','\n'.join(text))
if __name__=='__main__':main()
