"""Record actual completed v2 evidence; no model execution."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_tiegcm_2022_b14_v2 import F,O,B,A
if __name__=='__main__':
 s=json.loads((B/'status.json').read_text());assert s['qualification']=='PASS'
 state=dict(A14_DATA_INTEGRITY='PASS',A14_ENGINEERING='PARTIAL',A14_LAUNCHER_EXIT='UNKNOWN',B14_ENGINEERING='PASS',B14_ACTUAL_RETURN_CODE=0,DUAL14_SENSITIVITY='AVAILABLE_EXPLORATORY_V2',HISTORICAL_V1_PAIR_ENGINEERING='NOT_PASS',FULL_STATE_SCIENTIFIC_SPINUP='FAIL',SCIENCE_TRAINING_READY=False,EXTERNAL_DATUM='EXTERNAL_DATUM_UNVERIFIED',SCIENTIFIC_REAL_ORBIT_VALIDATION_READY='BLOCKED')
 (F/'final_states.json').open('x').write(json.dumps(state,indent=2))
 entry=f"""

## 2026-11-13接续：探索性v2补齐2022 B14及两年联合分析

- 本轮用户明确选择协议B；新tag tiegcm_2022_b14_exploratory_pair_v2启动前冻结协议/SHA。2022 A14数据PASS、工程PARTIAL/退出UNKNOWN原样保留；新B14工程独立PASS，不追认原v1双轨完整工程PASS。旧B14入口未调用，A14未重跑。
- 4-rank非物理MPI测试0.622844秒，真实父wait rc0、四rank同专属session、清理通过。新监督器源码SHA与上一轮23项测试冻结版本一致，本轮没有虚报重跑23项单元测试。
- B14仅一次2022-03-09至25连续23040步（60秒/4MPI/OMP1），17主/384小时次、33卷3371589248字节；2026-11-12运行端日志09:21:42—10:02:11 UTC，11-13继续仅收尾分析。真实父Popen.wait rc0，监督{s['elapsed_s']:.6f}秒，1206采样/0缺口，峰值采样会话RSS{s['peak_sampled_tree_rss_bytes']/2**20:.3f}MiB，CPU user/system{s['children_cpu_user_s']:.3f}/{s['children_cpu_system_s']:.3f}秒，清理通过。文件mtime与运行端钟偏差保留，不以mtime代替monotonic预算。
- 配置除SOURCE/独立身份外物理相同；smax34状态、SOURCE_START、GPI/可执行/apex及旧资产SHA核验；2304个实际10分钟驱动日志节点、384暖态记录、完整日历/单位/网格/字段审计通过，驱动最大差2.84e-14。5GiB/16GiB/4800秒/256MiB卷/余盘20GiB及含旧A14的12GiB总预算未扩大，无重试/Restart。
- 2022候选49帧450km双初态P95由8.931086%降至3.298004%（降低63.07275%），最后24h3.061277%、终点2.852207%，覆盖100%。200—500km全有效域冻结门槛无失败格；原生层DEN/TN/风通过，但O1/O2/N2/HE全窗失败2965/4290/3688/35格，末24h1373/2122/1815/15格。完整状态科学质量仍FAIL。
- 四方案×四映射共同2880/2880 Swarm观测点；已有A7/B7/A14只读复用，仅新增B14 11520查询、全部有效，观测下载0。Map-A A7/A14 RMSE2.915160/2.739357e-13kg/m³（降低6.03066%），B7/B14 2.327279/2.512460e-13（反增7.95697%）；相对RMS A20.549745→19.892541%、B18.533847→19.113987%。Map-B/E下A相对RMS反增约0.624/0.628%，B相对RMS反降约0.877/0.875%，绝对RMSE方向却相反，不择优映射。
- 统一各年03-23至25的49帧：2021 450km P95 6.059497→2.123731%（降低64.95203%），2022 8.931086→3.298004%。两年Map-A均A源观测RMSE略降、B源反增，内部趋同不保证外部观测改善。2021原73帧5.869/2.081%报告保持不变；500km各域及八轨共同空间/时槽另报，不作年份单因素因果。
- 独立复算：473历史资产SHA不变、33新卷一致、16组观测指标、450km逐列独立插值/P95和全部门槛矩阵计数通过；9张真实图可读。独立验证14.462秒/RSS178.664MiB，旧A14与新实验/结果约6.34GiB<12GiB。源码/输入/输出SHA、资源及警告日志保留。
- 下一步建议另行冻结DEN专项工程候选v3，优先审查同smax且工程完整的2021 B14/2022 B14v2，理由是来源/工程资格一致而非观测误差排名；CPU新版本提取须另授权，随后才小规模单步Direct工程训练。完整171仍需标签稳定性、WN/Z等质量、统计/优化器协议和季节活动覆盖；组分不是171直接目标，但其物理影响不忽略。
- 原122帧、训练统计、权重及全部旧轨迹不改；无GPU/AI训练或新卫星传播。SCIENCE_TRAINING_READY=False、EXTERNAL_DATUM_UNVERIFIED与真实轨道BLOCKED保持。主报告TIEGCM_2022_B14_EXPLORATORY_V2、TIEGCM_2022_7VS14_COMPARISON_V2、SWARM_TIEGCM_2022_FOUR_SCHEME_V2、TIEGCM_2021_2022_SPINUP_SYNTHESIS_V2；方案docs/FOURCASTDEN_AFTER_B14_V2_TRAINING_PLAN.md。
"""
 for name in ['STATUS.md','WORKLOG.md']:
  with (ROOT/name).open('a') as out:out.write(entry)
 with (ROOT/'WORKLOG.md').open('a') as out:
  out.write("""
- 实际命令与单次启动警告见本tag commands.json：activate_tiegcm.sh后run_tiegcm_2022_b14_v2.py prepare / mpi-test / execute；finish_tiegcm_2022_b14_v2.py只等待新gate后执行独立工程审计、delta14/B14_B7/joint及观测；activate_orbit.sh后finalize及verify。区域摘要算法存scripts/summarize_tiegcm_b14_regions_v2.py并与实际CSV逐值核对。
- 模型/监督执行无错误；离线NetCDF missing_value dtype警告保留，有效值/填充检查通过。一次报告源编辑定位断言和一次收尾编排语法错误均未启动任何模型或改动科学结果，修正后语法检查通过；无模型重试/阈值变化。数值指标函数复用不改，只有新路径/身份/输出适配。
- 仅安全提交本任务公开代码、冻结配置、报告、轻量CSV/PNG与审计清单。新/旧NetCDF、逐点观测、权重与凭据不上传；无关未跟踪同步日志保留。远端同步见最终本地核验记录。结束停止，不自动生成候选、训练或追加模拟。
""")
 print('Final states / STATUS / WORKLOG updated')
