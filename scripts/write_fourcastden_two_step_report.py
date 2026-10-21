"""Render measured two-step results and append current project status."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/fourcastden_two_step_v1'
def write(path,text):
 with (ROOT/path).open('x') as f:f.write(text.rstrip()+'\n')
def append(path,text):
 p=ROOT/path;p.write_text(p.read_text()+'\n\n'+text.rstrip()+'\n')
def main():
 r=json.loads((F/'runtime.json').read_text());a=json.loads((F/'analysis.json').read_text());pre=json.loads((F/'preflight.json').read_text());assert a['author_metric_matches_numpy'] and r['feedback']['passed']
 lines=['# FourCastDEN官方Direct两小时自回归验证','HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING','\n## 历史成果与本次范围\n',f"2026-10-19已完成Direct严格加载与Jan4 00→01单步、NumPy重算；原文件experiments/20261019_minimal_direct/result.npz的SHA256为 `{pre['history_legacy_one_hour_result_sha256']}`，本次只核验保留，不重复计作新成果。当前正式任务仅一次Jan4 00→01→02 Direct推理，真实网络forward恰好2次，无额外教师强制、6h/24h、训练或微调。新目录experiments/fourcastden_two_step_v1及data/processed/fourcastden_two_step_v1。\n",'## 数据、模型与防泄漏\n',
 '复用原始3个小时NPZ、官方Direct_ckpt.tar（SHA212187479c2df3ead151ec339683198f9e0632e23b892ac4d829ce1048724efb）、普通static和Linux仅可选导入补丁副本。原始源码逐字节对比原ZIP，四权重与static/static_log核验，所有资产原件不变。AFNONet 64,695,744参数，177二维输入、4标量、171输出，n_history=0、n_prediction=2、dt=1h、flow/log_DEN/perturb均false，FP32/TF32关闭，严格加载作者model_state。通过公开inference(0)调用，不改作者循环，避开全年CLI日期索引假设。\n',
 '实际forward hooks已保存两次输入/输出：第一次171状态等于00时初态；第二次171状态逐元素等于第一次预测，且不是回填01时真物理场；各步后6辅助通道和4标量来自对应01/02时。CPU合成毒化测试替换未来真物理场但预测和网络输入不变，改变未来辅助条件则输入确实改变；此测试不属于真实模型成果。\n',
 '未来F107/Kp及TLBC/ULBC/VLBC取作者已给定NPZ，SEA/sfeps由作者太阳几何函数计算，磁坐标用作者static。原始驱动值及每个样本来源见runtime.json。这些并非由网络自主预报的未来条件，不能称实时自主预测。NE/ZG虽在样本中，但不在171个预测通道中。Z是位势高度，ZG是几何高度。\n',
 '## 评价定义\n','使用作者cos(latitude)/mean(cos(latitude))加权逐通道RMSE，以及相对作者time_means气候态的ACC。独立NumPy float64重算；ACC仅在异常范数分母有限且>0时报告，否则N/A。参考采用作者float32归一化后的同一目标场，原始NPZ反归一化重建舍入差另记录于analysis.json。不用更新后的01时真状态当持续性：持续性在两个目标时刻都固定00时171通道，网格、权重、气候态及有效掩码与AI一致。\n',
 '下表为各变量逐压力层RMSE的算术平均，不是所有高度混成的RMSE，也不是固定几何高度450km误差。风cm/s→m/s和Z cm→m乘0.01，DEN g/cm³→kg/m³乘1000。样本本身无单位属性，依据作者UNIT_VARS和read_var未作SI转换的实际代码；不是依据docstring中的SI字样猜测。\n',
 '|变量|SI单位|1h AI RMSE|1h持续性RMSE|2h AI RMSE|2h持续性RMSE|1h/2h AI ACC平均|','|---|---|---:|---:|---:|---:|---|']
 for name in ['TN','UN','VN','WN','Z','DEN']:
  x,y=[v for v in a['variables'] if v['variable']==name];lines.append(f"|{name}|{x['SI_unit']}|{x['AI_mean_layer_RMSE_SI']:.8g}|{x['persistence_mean_layer_RMSE_SI']:.8g}|{y['AI_mean_layer_RMSE_SI']:.8g}|{y['persistence_mean_layer_RMSE_SI']:.8g}|{x['AI_mean_layer_ACC']:.8f}/{y['AI_mean_layer_ACC']:.8f}|")
 lines+=['\n六变量平均逐层RMSE均随第2步增大，但两步中每个171通道的AI RMSE都低于固定t0持续性。这里只是一个真实初态、两个目标时刻，不证明全年/磁暴/真实大气/轨道优越性。ACC很高也不等于独立观测验证。\n',
 '## 分层密度与图\n','342行逐层指标见results/metrics/fourcastden_two_step_v1_layers.csv，12行变量汇总见summary.csv；116行DEN层/基准相对差与自然log差见density_layers.csv。相对差定义ρ预测/ρ参考−1，没有人为密度floor；两步预测全部有限且DEN100%正。逐界面记录ilev与参考ZG全球中位/范围，避免把压力面当固定高度。地图选参考ZG全球中位最接近450km的原生界面，图注明实际ilev与中位高度，未做450km外推或外部WGS84映射。\n',
 'results/figures/fourcastden_two_step_v1_density_map_hour1/2.png包含真实参考、预测和相对差，配合density_vertical_errors、variables_vs_persistence、network_timing共5图。TN/UN/VN为28层lev，其余29层ilev，不能按同索引认定同高度。\n',
 '## 数值核查与资源\n',f"独立RMSE相对作者记录最大差{a['independent_RMSE_max_relative_difference']:.9g}，满足既有rtol2e−5；ACC满足atol2e−6。新首步与历史结果最大归一化差{r['first_step_vs_historical_max_normalized_difference']:.9g}，说明历史行为保持，不是新的单步复现声明。192项全套测试通过（187项原测试+5项新CPU验证）。\n",f"A10080GB/torch{r['torch']}/CUDA runtime{r['cuda']}，模型加载{r['model_load_s']:.6f}s，单独首次三帧读取及预处理{r['data_read_preprocess_s']:.6f}s；作者正式inference含再次读取、评价与审计hooks共{r['author_inference_plus_metrics_and_hooks_s']:.6f}s。两次CUDA event网络耗时{r['network_GPU_ms'][0]:.3f}/{r['network_GPU_ms'][1]:.3f}ms，包含首次调用冷启动差异，不当成稳定吞吐基准。GPU阶段总墙钟{r['GPU_phase_wall_s']:.6f}s，小于300s。\n",f"显存记录在模型加载后reset峰值计数：推理阶段peak allocated {r['peak_allocated_bytes']/2**20:.3f}MiB，peak reserved {r['peak_reserved_bytes']/2**20:.3f}MiB（含加载遗留缓存）。没有独立保存加载瞬态allocated峰，不能把此allocated数字当全流程峰，也不能直接与10月19日含checkpoint加载的峰相比较。初始GPU空闲显存由nvidia-smi确认。运行结果新增约{r['new_result_bytes']/2**20:.3f}MiB，完整交付新增量由最终审计核算，远低于500MiB；无下载、无其他项目写入。\n",'## S7兼容性发现与训练缺口\n',
 '静态探针确认S7目标记录14键齐全、lat/lon/lev/ilev与官方static一致；TN/UN/VN各顶层2592个有限padding，需显式掩码/移除。NetCDF自动missing_value无法安全cast曾发警告，probe保留手工哨兵统计，不能仅看finite。未将S7输入网络。仍需整点1h抽取、完整记录质量、原训练归一化分布与物理配置审查；AI的Z非ZG，正式高度接口不变。\n',
 '官方README只提供2023推理，训练主入口/2000—2021训练与2022验证数据、完整训练协议不齐；Lightning片段与AFNONet实际返回/条件接口有不一致。四权重已核验不等于四模型均可运行，更不等于完成论文训练复现。完整A—F路径、数据量/资源/防泄漏要求见FOURCASTDEN_PHASE2_RESEARCH_PLAN.md。建议下一次先做相同三帧的官方Flow两小时配对实验，需新授权；本次停止，不扩6/24h或训练。\n',
 '## 可重复命令与文件\n','source scripts/activate310.sh；python -m unittest discover -s tests；python scripts/run_fourcastden_multistep.py（静态）；timeout 300s python scripts/run_fourcastden_multistep.py --execute（唯一一次，当前标签拒绝重复启动）；python scripts/analyze_fourcastden_multistep.py；python scripts/write_phase1_stage_review.py；python scripts/write_fourcastden_two_step_report.py；python scripts/audit_fourcastden_delivery.py。新复现实验须更换独立输出标签并保留本次文件，不能重跑旧validate_fourcastden.py覆盖单步结果。\n']
 write('reports/FOURCASTDEN_TWO_STEP_VALIDATION.md','\n'.join(lines))
 text=f'''## 2026-10-21：第一阶段工程验收整理与FourCastDEN第二阶段A启动

新增PHASE1_STAGE_REVIEW_20261021及5张既有图索引，明确工程/条件敏感性通过、正式科学精度未验收；未重跑C0—C3/引力/TIE。恢复官方AI资产并SHA保护，历史单步不是新成果。一次Jan4 00→01→02官方Direct自回归成功，实际forward2次，第二步171状态逐元素反馈第一步预测；未来真实状态只评价，未来LBC/驱动显式HINDCAST。两步DEN有限正值，首步与历史逐元素一致；192测试通过。

第2小时六变量平均逐层RMSE均比第1小时增大，但两步全部171通道均优于固定00时持续性。GPU阶段{r['GPU_phase_wall_s']:.3f}s<300s，未训练/微调/扩6或24h；内存/事件计时口径和局限见FOURCASTDEN_TWO_STEP_VALIDATION.md。S7实际14键/网格匹配，但3种lev场顶padding、1h抽取、分布与Z/ZG问题仍需规范转换，本次没有输入S7。完整训练入口与2000—2022数据未齐，不称完整论文复现。

下一入口docs/FOURCASTDEN_PHASE2_RESEARCH_PLAN.md；建议另授权官方Flow同样两小时对照，之后再补统一变体窗口。正式轨道气动/推力/高度、预热和缺失受力门禁保持。完成停止，安全Git同步以最终远端核对为准。'''
 for p in ['STATUS.md','WORKLOG.md','docs/PROJECT_PLAN.md']:append(p,text)
 p=ROOT/'STATUS.md';p.write_text(p.read_text().replace('# 当前状态\n','# 当前状态\n\n> 最新：第一阶段工程/条件成果已整理，正式科学验收待完成；FourCastDEN Direct两小时自回归已完成，第二阶段A启动，未训练。详见末节。\n',1))
 append('AGENTS.md','''## 第二阶段启动后的最新规则

用户已授权并完成阶段一报告整理和一次官方Direct两小时自回归（fourcastden_two_step_v1，Jan4 00→01→02，192测试）。历史单步保留，不当作新成果。预测反馈与未来辅助/驱动区分，HINDCAST；未来真实物理状态不得反馈。四权重不等于完整训练复现，原训练入口与2000—2022数据仍缺。AI输出Z非ZG、1h非S7的10min；未经规范转换不得输入S7或取消正式高度门禁。阶段一工程和条件敏感性通过，正式气动/推力/高度/预热/受力门禁仍开放。此任务已结束，Flow/扩6或24h/训练/新轨道/TIE均需另授权，所有新成果继续安全同步GitHub。''')
 append('WORKLOG.md','执行命令：activate310；192项unittest；run_fourcastden_multistep.py静态和唯一--execute（timeout300）；analyze_fourcastden_multistep.py；write_phase1_stage_review.py；write_fourcastden_two_step_report.py；audit_fourcastden_delivery.py。模型/预处理/数据与指标均真实官方来源，CPU合成毒化测试不作为科研预测。源码/权重/static/样本和历史结果保护，原始源码不改，无包安装/新下载。S7_schema_probe只读目标记录并显式核验有限padding。正文首次MDPI请求429但官方搜索可读取训练划分摘要，未声称下载本地全文。实际完整交付SHA/容量/同步状态见审计JSON与最终汇报。')
if __name__=='__main__':main()
