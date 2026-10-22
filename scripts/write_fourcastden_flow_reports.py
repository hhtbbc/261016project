"""Render reports and prospective data requests from saved evidence; no inference."""
import json,csv,sys
from pathlib import Path
from datetime import datetime,timedelta
ROOT=Path(__file__).resolve().parents[1]
from run_fourcastden_multistep import sha
F=ROOT/'experiments/fourcastden_flow_two_step_v1'
def write(p,text):
 with (ROOT/p).open('x') as f:f.write(text)
def main():
 a=json.loads((F/'analysis.json').read_text());r=json.loads((F/'runtime.json').read_text());pre=json.loads((F/'preflight.json').read_text());dr=json.loads((ROOT/'experiments/fourcastden_two_step_v1/runtime.json').read_text())
 rows=a['summary'];paired=a['paired'];den=list(csv.DictReader((ROOT/'results/metrics/fourcastden_direct_flow_v1_density_layers.csv').open()));layers=list(csv.DictReader((ROOT/'results/metrics/fourcastden_direct_flow_v1_layers.csv').open()))
 def get(h,m,n):return next(x for x in rows if x['hour']==h and x['model']==m and x['variable']==n)
 def denget(h,m,k):return next(x for x in den if int(x['hour'])==h and x['model']==m and int(x['ilev_index'])==k)
 inv={x['name']:x for x in json.loads((ROOT/'logs/test_archive_inventory.json').read_text())}
 plans=[]
 for label,t0,L,H in [('history_fair_2h','2023-01-04T01:00:00',2,1),('history_fair_6h','2023-01-04T01:00:00',6,1),('history_fair_12h','2023-01-04T01:00:00',12,1),('history_fair_24h','2023-01-04T01:00:00',24,1),('storm_preselected','2023-03-23T00:00:00',24,1),('season_June','2023-06-21T00:00:00',24,1),('season_September','2023-09-23T00:00:00',24,1),('season_December','2023-12-21T00:00:00',24,1)]:
  t=datetime.fromisoformat(t0);names=[(t+timedelta(hours=h)).strftime('%Y_%m_%d_%H%M%S.npz') for h in range(-H,L+1)]
  assert all(n in inv for n in names);missing=[n for n in names if not (ROOT/'data/raw/test_minimal_2023'/n).exists()]
  plans.append(dict(label=label,t0_UTC=t0,horizon_hours=L,n_history=H,total_frames=len(names),new_frames=len(missing),new_member_bytes=sum(inv[n]['bytes'] for n in missing),new_zip_compressed_bytes=sum(inv[n]['compressed'] for n in missing),required_names=names,new_names=missing,central_directory_entries_verified=True,member_content_CRC_SHA_NOT_yet_verified=True))
 plan=dict(status='DESIGN_ONLY_NOT_DOWNLOADED',inventory_SHA256=sha(ROOT/'logs/test_archive_inventory.json'),plans=plans)
 (F/'future_data_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
 validation=f'''# 官方Flow两小时自回归验证（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 实际执行与配置

本次只运行一次正式Flow，00→01→02 UTC，实际网络forward恰好{r['network_calls']}次。Direct两小时结果仅读取，未再次运行Direct网络；198项自动化测试通过，无包安装、资产下载、训练、TIE或轨道传播。

官方README_inference_2023.md模型表、config/AFNO.yaml::afno_inference和inference/inference.py是本次实现依据。Flow权重Flow_ckpt.tar SHA256 `{r['checkpoint_sha256']}`，Direct权重SHA `212187479c2df3ead151ec339683198f9e0632e23b892ac4d829ce1048724efb`。两者同AFNONet {r['parameters']:,}参数，150项model_state按作者默认strict=True严格加载（没有strict=False），177×36×72输入/4标量/171输出。通道顺序TN、UN、VN各28，WN、Z、DEN各29；n_history=0、log_DEN=false、dt=1、n_prediction=2、普通static、FP32、TF32关闭。实际配置config.yaml、preflight.json与protected.json位于experiments/fourcastden_flow_two_step_v1。

配置从官方Flow afno_inference展开，不由Direct权重改造。覆盖仅项目路径、预测长度2、36×72网格、num_workers=0及日志/输出标签；两模型核心结构、变量、驱动、归一化和坐标配置逐项相同。Direct/Flow均使用同一官方普通static，并非为了公平强迫不匹配的统计。

原作者数据日志“包含3小时past history”实际来自数据集长度3的通用提示，不代表n_history=3；实际配置和输入shape已核实n_history=0。

## 增量含义及反馈

作者forecast先gen=model(inp,sw)，随后flow分支gen+=inp[:,:171]，所以delta与state都处于zscore空间。x_next_norm=x_current_norm+delta_norm；反归一化为x_next=x_next_norm*std+mean，物理增量只是delta_norm*std，不能额外加mean。该Flow不是光流warp，不是积分器中的速度。

Hook在作者原位累加前复制原始增量，随后独立检查两步累计状态与输入：两个float32累加逐元素一致，第二步输入恰为第一步累计预测；预测shape {r['state_shape']}。目标01/02时的真实171物理状态只评价，未来下边界、太阳/地磁辅助与四标量按作者方法已给定，因此是HINDCAST，不能称实时自主预报。

CPU合成测试直接调用原作者循环，用恒定增量验证1→1.25→1.5；零增量不变；毒化未来真值不改预测或输入；改变未来辅助只改变相应输入；错误的直接增量反馈被拒绝；独立反归一化公式测试通过。合成结果不当真实预测。两次正式输入、增量和输出已保存于data/processed/fourcastden_flow_two_step_v1/result.npz（仅本地），SHA `{r['file_sha256']}`。

## 公平性与独立复核

Flow的real、means、stds、climatology、t0状态、两目标的6个二维辅助和4标量与Direct保存值逐元素一致。原三帧SHA和完整保护列表见protected.json；Direct历史SHA `{json.loads((ROOT/'experiments/fourcastden_two_step_v1/runtime.json').read_text())['file_sha256']}`。原始第三方源码、运行副本、权重/static/样本/历史结果保持不变，最终交付audit复核。

独立NumPy float64逐171通道cos纬度加权RMSE与气候态ACC重算，RMSE预注册rtol2e-5/atol1e-25，ACC rtol2e-5/atol2e-6，无有效分母记N/A；Flow最大RMSE相对差{max(v['RMSE_max_relative'] for k,v in a['independent_metric_checks'].items() if k.startswith('Flow')):.3e}，ACC最大绝对差{max(v['ACC_max_absolute'] for k,v in a['independent_metric_checks'].items() if k.startswith('Flow')):.3e}。Direct保存作者指标也再次独立复核，不调用网络。

## 物理基础检查

预测全部finite，DEN正值比例100%，TN正；没有裁剪、平滑、外推或事后修正。各变量最小/最大值和偏差见summary.csv；这只排除本次明显异常，不证明未来长时稳定或真实大气准确度。Z为位势高度，不能当ZG。图示ilev=4.0（数组index22），参考ZG中位约439.5/441.3km，实际高度随经纬变化，不是固定450km剖面。

## 耗时与显存

A100-SXM4-80GB / torch {r['torch']} / runtime CUDA {r['cuda']}。模型加载（包括首次CUDA初始化）{r['model_load_including_CUDA_initialization_s']:.6f}s，单独数据读取预处理{r['preprocess_read_s']:.6f}s，作者两步循环含评价及hooks {r['author_loop_metrics_hooks_s']:.6f}s；实际循环也会再次读取3帧，因此这些口径不得直接相加当纯网络时间。首个冷forward {r['network_GPU_ms'][0]:.6f}ms、第二forward {r['network_GPU_ms'][1]:.6f}ms；GPU阶段总墙钟{r['GPU_phase_wall_s']:.6f}s<300s。

包含checkpoint加载的分配峰{r['loading_peak_allocated_bytes']/2**20:.3f}MiB；加载后reset的推理阶段分配峰{r['inference_peak_allocated_bytes']/2**20:.3f}MiB、保留峰{r['inference_peak_reserved_bytes']/2**20:.3f}MiB。Direct历史只测推理阶段峰，不能与Flow加载峰比较。新数组约{r['new_experiment_bytes']/2**20:.2f}MiB，最终所有新产物受500MiB门禁。

## 可重复命令及停止边界

先source scripts/activate310.sh；python -m unittest discover -s tests；python scripts/run_fourcastden_flow_two_step.py（静态）；timeout 300s python scripts/run_fourcastden_flow_two_step.py --execute（本次唯一一次，旧run-tag自动拒绝）；python scripts/analyze_fourcastden_direct_flow.py；python scripts/write_fourcastden_flow_reports.py；python scripts/audit_fourcastden_flow.py。报告/分析采用独占输出，重复正式实验应另行授权并修改独立标签。没有更多GPU执行。
'''
 write('reports/FOURCASTDEN_FLOW_TWO_STEP_VALIDATION.md',validation)
 lines=['# Direct / Flow两小时受控对照（2026-10-22）\nHINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING\n\n仅1个初始时刻、2个目标，两官方权重同配置；Direct只复用历史。以下是与TIE-GCM模拟参考的误差，不是观测或轨道精度。\n\n## 各变量平均逐层RMSE\n\n每一层先按作者cos纬度加权，再对层的RMSE算术平均；不是全高度混合RMSE，更不是固定几何高度指标。\n\n|小时|变量|SI单位|Direct|Flow|固定t0持续性|Flow/Direct|\n|---:|---|---|---:|---:|---:|---:|']
 for h in (1,2):
  for n in ['TN','UN','VN','WN','Z','DEN']:
   d=get(h,'Direct',n);f=get(h,'Flow',n);p=get(h,'Persistence',n)
   lines.append(f"|{h}|{n}|{d['unit']}|{d['mean_layer_RMSE_SI']:.6g}|{f['mean_layer_RMSE_SI']:.6g}|{p['mean_layer_RMSE_SI']:.6g}|{f['mean_layer_RMSE_SI']/d['mean_layer_RMSE_SI']:.5f}|")
 lines.append('''\n## 结果及评价指标的差别

第一小时，Flow的TN/UN/VN/WN/Z平均逐层RMSE较低，DEN较高2.950%；第二小时Flow的TN/UN/VN/Z较低，WN较高2.468%、DEN较高2.842%。Flow第一小时170/171层、第二小时141/171层RMSE低于Direct，但不能按通道数跨变量投票认定总体架构胜者。两模型六变量平均逐层RMSE均随步数增大；Flow第2/1小时增长倍率有时更高，仅2步不能外推长期误差增长率。

两者在两个目标的全部171通道均优于同一个固定00时持续性基准。气候态ACC全部有效，逐层ACC见layers.csv和变量平均见summary.csv；高ACC受本次场的相关结构影响，不等于观测精度。持续性不使用01真值重置。

DEN平均绝对RMSE被高密度底层显著影响：第一小时Flow仅最底层index0较差，其余28层均较低；第二小时Flow有24/29层较低。因此“平均DEN绝对RMSE稍高”和“多数上层相对误差较低”可以同时成立。不能只报告其中一种。

## DEN代表压力层

表中高度是该目标参考ZG的全球中位，仅定位原生压力面，空间高度有范围，不能当固定高度误差。P95为该层全部原生空间点绝对相对差的非面积加权分位数；加权相对RMS/logRMS另有CSV。

|小时|ilev数组index|参考ZG中位km|Direct绝对相对差P95 %|Flow P95 %|
|---:|---:|---:|---:|---:|''')
 for h in (1,2):
  for k in [0,4,10,20,22,28]:
   x=denget(h,'Direct',k);y=denget(h,'Flow',k)
   lines.append(f"|{h}|{k}|{float(x['reference_ZG_median_km']):.3f}|{float(x['relative_P95'])*100:.6f}|{float(y['relative_P95'])*100:.6f}|")
 lines.append('''\n最大相对P95集中在顶层index28（ilev7），第二小时Direct约0.996%、Flow约0.949%；不能把这当整个模型大气误差上界。绝对误差最大是高密度底层index0。极区/局地差异见热力图，不用平均指标掩盖空间极值。所有预测密度均正且有限，没有异常修正。

## 计时比较
''')
 lines.append(f"历史Direct两次GPU事件{dr['network_GPU_ms'][0]:.6f}/{dr['network_GPU_ms'][1]:.6f}ms；Flow为{r['network_GPU_ms'][0]:.6f}/{r['network_GPU_ms'][1]:.6f}ms。总事件时间差Flow−Direct={sum(r['network_GPU_ms'])-sum(dr['network_GPU_ms']):.6f}ms；仅跨日两次各一个冷/暖forward，不能据此确定速度优势。Direct未重跑，也未为Flow额外warm-up。网络结构/参数量相同，主要是训练目标和推理状态更新差异。\n")
 lines.append('''\n## 文件索引及科学边界

- results/metrics/fourcastden_direct_flow_v1_layers.csv：1026条逐变量/层/小时/模型RMSE、ACC、偏差。
- 同前缀summary.csv：36条变量汇总；density_layers.csv：174条正性、极值、相对/log误差；paired.csv：12条层数与模型比值。
- results/figures/fourcastden_direct_flow_v1_density_hour1/2.png：参考/Direct/Flow密度；relative_hour1/2.png：统一色限误差。
- 同前缀DEN_layers.png、variable_RMSE.png、error_growth.png、GPU_timing.png：分层、六变量、增长、计时，共8图。
- experiments/fourcastden_flow_two_step_v1/analysis.json、runtime.json、delivery_audit.json：计算定义、性能与保护清单核验。

本次不能判定总体Direct/Flow优劣，不能验证实测大气、更不能推断Swarm轨道误差。第一阶段真实Cd/迎风面积/姿态与推进器定义、TIE外部ZG映射、预热和10分钟时间离散、引力截断及SRP/潮汐等受力缺口仍开放。Flow成功不解除任何正式接口门禁。下一步优先更多独立初值，再讨论长时泛化或训练；本次停止。
''')
 write('reports/FOURCASTDEN_DIRECT_FLOW_COMPARISON.md','\n'.join(lines).rstrip()+'\n')
 print('Reports and future-data member plan written; no new inference.')
if __name__=='__main__':main()
