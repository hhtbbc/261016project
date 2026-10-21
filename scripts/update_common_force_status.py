"""Append verified H6 results; preserve earlier reports as dated snapshots."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/common_force_validation_v1'
def append(name,text):
 p=ROOT/name;p.write_text(p.read_text()+'\n\n'+text+'\n')
def main():
 s=json.loads((F/'run_summary.json').read_text());a=json.loads((F/'analysis.json').read_text());assert s['passed'];h=a['residuals']['H6'];d=a['pairs']['H6_H4'];g=s['gates']['H6']
 latest=f'''## 2026-10-21：H6组合与完整六小时数值门禁已完成

H4/H5 tight、H6 base/tight共四次六小时及H6两次600秒预检完成，无重试、无旧轨道重跑。H4/H5/H6单轨最大base/tight差均小于0.5m，各配对差稳定性小于0.1m，181项测试通过。H6单轨最大差{g['max_position_m']:.9f}m；40阶背景加入日月的终点位移{d['terminal_m']:.6f}m、全窗最大{d['max_norm_m']:.6f}m。H6 SP3终点残差{h['terminal_m']:.6f}m、三维RMSE{h['rmse_3d_m']:.6f}m。

本次传播墙钟{s['wall_s']:.3f}s、峰RSS{s['peak_RSS_MiB']:.3f}MiB，低于1800s/2GiB；历史SHA不变。实际配置effective_configuration.json区分继承来源的旧状态字段，旧记录保留。仅冻结configs/provisional_common_force_model.json供下一阶段条件研究，标记PROVISIONAL / HINDCAST / FORCE_MODEL_INCOMPLETE，星历保留PROVISIONAL_EPHEMERIS。

40阶未证明截断收敛，真实气动/姿态推力、TIE外部ZG登记、预热和高频场仍未闭合；缺失潮汐/SRP/相对论等。C0—C3仅设计未运行。下一入口reports/H6_FORCE_MODEL_VALIDATION.md、reports/H6_ORBIT_COMPARISON.md及docs/PROVISIONAL_DENSITY_COMPARISON_PLAN.md。完成后停止，任何新阻力矩阵/更高阶/TIE/AI/长窗传播均需另授权。'''
 append('STATUS.md',latest)
 p=ROOT/'STATUS.md';text=p.read_text();p.write_text(text.replace('# 当前状态\n','# 当前状态\n\n> 最新状态：H6六小时数值门禁完成，共同配置仅供PROVISIONAL条件实验；详见本文末节。以下早期摘要保留作历史记录。\n',1))
 append('WORKLOG.md',latest+'''

关键操作：source scripts/activate_orbit.sh；python -m unittest discover -s tests（新增测试首次src导入路径错误，修正测试引导后181项通过，未发生模型重试）；OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/run_common_force_validation.py（唯一）；python scripts/prepare_common_force_effective_config.py；python scripts/analyze_common_force.py；python scripts/write_common_force_reports.py；python scripts/update_common_force_status.py；python scripts/audit_common_force.py。运行日志logs/common_force_runs.log，测试logs/common_force_tests_pass.log；实际JSON/launch_once/门禁、NPZ、CSV与6图全部本地保存。无安装、下载、TIE/阻力/AI/24或48h运行，无参数拟合。沿用项目.venv310、冻结EOP/闰秒及GFZ系数/ERFA，系统环境未改。

新增组合模块及测试、受限运行/离线分析/独立审计脚本、两报告、预注册和C0—C3设计、条件配置；更新长期门禁/研究计划。旧实验、原始源码和正式TIE门禁不变。Git安全提交与实际远端SHA核对以最终同步日志和结束汇报为准。''')
 append('docs/COMMON_FORCE_MODEL_DECISION.md',latest+'\n\n以上旧节“尚缺六小时tight/H6”现已由本次证据解决，保留为历史快照；正式精密模型门禁仍未解除。选择H6依据物理组合和独立/数值门禁，不依据SP3残差最小。')
 append('AGENTS.md','''## H6完成后的最新门禁

common_force_validation_v1已按单独授权完成H4/H5六小时tight与H6六小时base/tight、两次600s预检；单轨0.5m和配对0.1m门禁通过，181测试通过。旧报告H6未运行/全窗PENDING属于历史状态，最新看H6两报告和本轮审计。仅冻结provisional_common_force_model.json作下一阶段条件背景，PROVISIONAL/HINDCAST/FORCE_MODEL_INCOMPLETE与PROVISIONAL_EPHEMERIS保留；40阶未证明截断收敛，真实气动/推力/高度/预热等门禁不变。C0—C3只有设计，尚未执行；新矩阵/长窗/更高阶/TIE/AI均需新授权，不能重复本次传播或混用旧J2密度组解释新力场。每次任务结束仍安全同步GitHub，不强推。''')
 append('docs/PROJECT_PLAN.md',latest)
 append('docs/FORMAL_ORBIT_VALIDATION_GAPS.md','''## H6数值与统一配置阶段更新

H4/H5/H6全六小时单轨和配对收敛门禁已完成，相关旧PENDING已解决。当前可在另获授权后，用冻结H6开展C0—C3条件研究；不等于正式精度验证就绪。40阶截断充分性/星历近似、潮汐SRP等受力、真实气动与推力、TIE高度与预热/时间分辨率门禁保留。详见H6_FORCE_MODEL_VALIDATION、H6_ORBIT_COMPARISON和PROVISIONAL_DENSITY_COMPARISON_PLAN。''')
if __name__=='__main__':main()
