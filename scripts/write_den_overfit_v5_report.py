"""Build the final report from actual frozen arrays/records, no model execution."""
from pathlib import Path
import sys,json,csv,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from train_den_overfit_v5 import F,O
if __name__=='__main__':
 g=json.loads((F/'GPU_result.json').read_text());plan=json.loads((F/'plan.json').read_text());status=json.loads((F/'gpu_job/status.json').read_text());audit=json.loads((F/'final_audit.json').read_text());records=[json.loads(x) for x in (F/'updates.jsonl').read_text().splitlines()];comp=list(csv.DictReader((O/'fixed_AI_vs_Persistence.csv').open()));val=list(csv.DictReader((O/'validation_AI_vs_Persistence.csv').open()));base=list(csv.DictReader((O/'fixed_Persistence.csv').open()));groups=['all','upper20_28','top28']
 snapshot_table='|步数|normalized loss|全29层相对RMS|上层20—28|顶层28|非正数量|正值率|\n|---:|---:|---:|---:|---:|---:|---:|\n'
 for snap in g['fixed_snapshots']:
  rr={x['group']:x for x in snap['global_metrics']};snapshot_table+=f"|{snap['step']}|{snap['normalized_loss']:.9f}|{rr['all']['relative_RMS']*100:.6f}%|{rr['upper20_28']['relative_RMS']*100:.6f}%|{rr['top28']['relative_RMS']*100:.6f}%|{snap['nonpositive_count']}|{snap['positive_fraction']*100:.6f}%|\n"
 b={x['group']:x for x in base if x['region']=='global'};snapshot_table+=f"|Persistence|不适用|{float(b['all']['relative_RMS'])*100:.6f}%|{float(b['upper20_28']['relative_RMS'])*100:.6f}%|{float(b['top28']['relative_RMS'])*100:.6f}%|0|100%|\n"
 val_table='|分组|step100相对RMS|Persistence相对RMS|AI RMSE kg/m³|AI Bias kg/m³|AI正值率|\n|---|---:|---:|---:|---:|---:|\n'
 for name in groups:
  x=next(x for x in val if x['region']=='global' and x['group']==name);val_table+=f"|{name}|{float(x['AI_relative_RMS'])*100:.6f}%|{float(x['Persistence_relative_RMS'])*100:.6f}%|{float(x['AI_RMSE']):.9e}|{float(x['AI_bias']):.9e}|{float(x['AI_positive_fraction'])*100:.6f}%|\n"
 report=f'''# AFNONet真实DEN固定单样本100步过拟合v5

日期2026-11-13；tag`fourcastden_den_overfit_v5`；起始Git main本地/远端同`ca09097700874650af716ff3675bc7c46094e2c1`。

**唯一GPU任务成功完成100次更新。原AFNONet显著拟合同一真实样本，但未达到充分过拟合或超过Persistence的证据。最终2022验证仍明显较差，不是跨年泛化成功。** 原v3失败、v4训练记录与checkpoint、数据和统计均不改。全部科学门禁保持。

## 1. 冻结协议与可复用链路

固定2021 B14首对：2021-03-23 00→01 UTC，来自v3原NPZ。CPU读取一次、固定GPU拷贝一次，100次同一tuple；模型pre-hook100次输入对象一致，训练前后X/D/Y缓存SHA精确一致。没有随机样本、增强或其他训练对。CPU数据审计与5项新增策略/真实契约测试，及37项已有回归共42项CPU测试通过。449项原资产（含v4两份完整checkpoint）最终SHA通过；v3数据/2021统计不提取、不拟合、不重写。

X=[1,177,36,72]、D=[1,1,4]、Y=[1,171,36,72]、DEN=[1,29,36,72]。作者索引再次确认TN28/UN28/VN28/WN29/Z29/DEN29，DEN142:171、ilev，TN/UN/VN28有效lev。输入为当前171状态+目标时刻合法辅助、四标量条件，未来物理目标毒化未改变X/D。真实未来驱动故HINDCAST。DEN原g/cm³×1000成kg/m³；Z不是ZG，固定层不是固定几何高度。

2021训练统计SHA `{plan['statistics_SHA256']}`；固定样本DEN encode/decode最大相对差9.59751e-9。物理值均正、有限，参考ZG严格递增。主入口复用DenTrainer、作者原AFNONet、EpochPairs、AffineNormalizer、现有物理指标、runtime GPU策略/监督器与可信恢复，不新建训练框架。

原AFNONet64,695,744参数/177输入/4条件/171输出；seed20261113、FP32、AdamW1e-4、weight_decay0、常数LR（StepLR gamma1）、clip1、batch1、不加载作者或v4权重。新随机模型SHA `{g['initial_model_SHA256']}` 与v4同种子初始模型精确一致。

损失仍为DEN29的cos纬度加权normalized MSE，不改log/relative loss/残差/正值约束。其他142输出不监督，头梯度为0、头参数逐元素不变；共享网络变化不代表它们已训练，更不能将其用于多步。

## 2. 实际更新、梯度与资源

硬件：{g['hardware']['GPU']}，PyTorch{g['hardware']['torch']}，CUDA{g['hardware']['CUDA']}；继承设备可见性{g['hardware']['visibility']}。真实wait退出码0、工程监督PASS，监督{status['elapsed_s']:.6f}秒（上限300）、worker{g['wall_s']:.6f}秒。100次optimizer hook与100条实际更新记录，没有重试、额外更新或验证驱动的动态设置。实际forward153：训练100、固定检查点4、恢复探针1、最终验证48。全部额外forward启动前登记。

每步148个梯度张量均有限非零，clip前L2范围9.954618—294.416887，head有效参数每步变化。原作者未调用的末端`norm.weight`/`norm.bias`仍无梯度，保留报告，不改原网络。全部100步原clip1规则实际生效。梯度有限且有参数更新，不把大clip前数值直接叫梯度爆炸。

100次纯更新共{g['pure_update_wall_s']:.6f}秒，均值{g['pure_update_wall_s']/100:.6f}秒、中位{np.median([x['wall_s'] for x in records]):.6f}秒。固定样本读取/拷贝{g['cache_s']:.6f}秒，模型构造{g['construction_s']:.6f}秒；4次固定评价（含无更新状态核验）{g['fixed_evaluation_s']:.6f}秒，最终保存恢复{g['save_restore_s']:.6f}秒，48对验证{g['validation_s']:.6f}秒，指标/数组保存{g['save_metrics_s']:.6f}秒。计时区间有包含关系，不机械相加。

allocated峰值{g['peak_allocated_bytes']/2**30:.6f}GiB、reserved{g['peak_reserved_bytes']/2**30:.6f}GiB、进程GPU实际采样峰值{max(x.get('GPU_process_bytes',0) for x in status['samples'])/2**30:.6f}GiB；CPU树采样峰值{status['peak_sampled_tree_rss_bytes']/2**20:.3f}MiB，采样缺口0；满足20GiB GPU/8GiB CPU/余盘20GiB限制。GPU分配继承，CuBLAS在torch导入前设置`:4096:8`，不硬编码外部GPU编号、不关闭确定性。

本轮GPU阶段新增{g['output_bytes']}bytes（约{g['output_bytes']/2**30:.3f}GiB），小于2GiB。只保存一个最终完整checkpoint，不为0/10/50另存AdamW；固定预测摘要与全量验证数组留本地。CPU后处理{audit['wall_s']:.6f}秒、峰值{audit['CPU_peak_RSS_MiB']:.3f}MiB单独记录，不计为训练效率。

## 3. 固定真实样本的实际拟合

{snapshot_table}

normalized loss0→100下降99.876762%，全层物理相对RMS下降约96.51%。模型从随机斑块输出明显接近目标，固定样本非正3312→9→0→0。但step100全层/上层/顶层都仍比本样本Persistence差，只有原生level08的相对RMS小于Persistence（1.451635%对1.513853%），其余28层不能隐藏。

step100全层RMSE4.097644e-9、Bias−1.132034e-10kg/m³；Persistence对应3.486639e-9、−3.160833e-12。step50全层Bias−1.675841e-11，故Bias并非随RMSE同步改善。顶层step100相对RMS3.043031%，另有level05=2.631797%、level27=2.622522%、level04=2.602888%、level03=2.559413%；所有层明细保留。

更新日志loss是在对应step更新之前计算；0/10/50/100检查点是更新完成后的eval/no_grad评价，不能混淆step100日志0.212024与step100模型0.199936。所有检查点恢复原训练模式，模型与optimizer状态hash保持；不根据表现选最优checkpoint。

全程整体下降但不是严格单调：99次相邻变化中29次上升；最后20条更新前loss约0.2019—0.2695，均值0.231769，仍有小幅震荡。50→100物理误差继续改善，不能据此宣布不可降低的平台。线性总量图、log尺度图与全部层最终细节同时保留，不能仅展示平滑大趋势。

## 4. 数值、单位与损失排查

不是仅凭损失下降判断学习：固定源/条件缓存不变、未来真值不进输入、DEN-only梯度、随机初始SHA、训练专用统计和单位已核验；保存的物理数组独立复算所有检查点物理指标，normalized loss再由实际float32目标逐层独立重算并与GPU值一致（浮点复算rtol2e-6，不改变科学验收）。

`fixed_normalized_layer_audit.csv`记录逐层normalized MSE与std/目标密度比例。归一化误差和相对误差的关系为`(pred−truth)/truth = ((pred−truth)/std_SI)×std_SI/truth`；不同层/位置该比例不同，所以normalized loss与相对RMS或Bias不必同步。这里给出数值证据与代数关系，不据此单独判定某种新loss一定更好。没有发现需要修改数据、单位或通道的证据；残差不能简单都归咎于样本量。

线性反变换`DEN=mean+std*z`没有正值约束，z≤−mean/std就非正，这是已知数值风险。本轮固定样本后期已全部正，不代表所有输入均保证正；不能补0、取abs或截断获得好指标。

## 5. 最终一次2022验证

只在100更新和最终恢复后才创建并执行2022验证；48对全部一次no_grad前向，没有中途验证或参数调节。模型/AdamW hash与步数前后精确一致，梯度None。它仍是已反复使用的开发验证集，不是全新盲测。

{val_table}

验证3608064个DEN预测，非有限0、非正18（均在顶层），有限率100%、物理正值率99.999501%。所有负值保留在普通RMSE/Bias/relativeRMS中，分母为严格正真实标签，无floor。Persistence对相同48目标、同格点/层/区域与权重独立复算，与v3原CSV逐值一致；不删不利样本。

AI conditional logRMS全层/上层/顶层为0.1983331/0.2357611/0.2805337，正值域覆盖另报；为公平性还在**AI正值共同子域**比较双方log：Persistence0.0199837/0.0225314/0.0289956。log域限制不改变普通误差的全点统计。完整逐层、纬区、逐小时指标与共同正值域CSV保留。

历史v4十个不同样本10更新，全层31.8512%、上层38.2216%、顶层37.4637%；本轮最终20.7067/25.2058/27.5301%，观测到的结果较低、非正1316→18。但**样本组织与更新次数同时不同，不是纯训练长度消融**。本轮遵守最终一次验证，没有2022 step0/10/50结果，不能声称已经测得本轮2022误差随步数下降。全部29层最终仍劣于Persistence，单样本学习不能证明跨年泛化。

## 6. 最终checkpoint与完整性

本地`experiments/fourcastden_den_overfit_v5/step100.pt`保存完整model/optimizer/scheduler/RNG/step/config/输入和代码SHA；文件{(F/'step100.pt').stat().st_size}bytes，SHA `{g['checkpoint_SHA256']}`。从该可信本地文件恢复到新模型，step100、模型/AdamW/调度状态精确一致，GPU固定输入171输出逐元素精确一致，没有第101次更新。未读官方/v4权重作初始化，旧checkpoint不覆盖、不上传。

独立CPU审计确认449项旧资产不变、固定/验证物理指标重算一致、Persistence公平、最终checkpoint SHA一致。保护清单、输入/配置/代码SHA与资源在本tag JSON；具体门禁不因预测误差不理想而隐去。

## 7. 图表与交付

所有图位于`results/fourcastden_den_overfit_v5/`：

1. `01_fixed_100_update_loss.png`和`01b_loss_log_scale.png`：100次同样本实际loss，log图显露末段震荡。
2. `02_fixed_physical_error_checkpoints.png`：仅0/10/50/100实测物理误差与固定Persistence。
3. `03_fixed_by_layer.png`和`03b_final_layer_detail.png`：完整历史与50/100细节，保留全部29层。
4. `04_fixed_density_maps.png`和`04b_fixed_final_detail.png`：预先固定ilev24；原图四组共色标含随机step0，补充图明确仅最终细节色标，未换样本。
5. `05_nonpositive_checkpoints.png`：非正数量与正值率，只有四个实测点，不伪造中间步结果。
6. `06_2022_final_validation.png`：完整48对最终验证，注明非盲测。
7. `07_resources_and_timing.png`：实际100次更新与GPU采样，分开训练、评价、保存/恢复成本。

主CSV：training_updates、fixed_sample_metrics、fixed_AI_vs_Persistence、fixed_normalized_layer_audit、fixed_Persistence、validation_summary、validation_AI_vs_Persistence、matched_positive_log、independent_validation_metrics。没有从图片反推数字。

## 8. 结论、资格与下一阶段

- **问题A：** 原AFNONet已经明显学会拟合这个固定样本，达到约2%相对RMS、固定样本全正；但仍28/29层不及Persistence且末段震荡，不能称充分过拟合或可靠预测器。不设置事后<1%硬门槛。
- **问题B：** 最终2022相较历史v4数值较低，但仍显著差于Persistence；因无本轮中途验证且训练样本组织不同，不能证明纯100步带来跨年泛化改进。
- **问题C：** 优先做有界的固定样本剩余收敛对照（同配置延长至累计200），再做同起点/同预算的72对多样本对照；暂不同时换loss/网络。72对计划与资源申请见`docs/FOURCASTDEN_DEN_OVERFIT_V5_NEXT_DECISION.md`，本轮不执行。

工程数据/缓存、100步优化、检查点、最终验证与资源审计PASS；模型局部拟合证据成立但没有充分拟合的二元事后门槛；AI超越Persistence不成立、验证正值保证不成立。SCIENCE_TRAINING_READY=False、EXTERNAL_DATUM_UNVERIFIED、真实轨道BLOCKED、A14工程PARTIAL、旧v3FAIL均保留。没有训练完整171，没有自动多步或轨道。

## 9. 实际命令

```bash
cd /workspace/data/20261016
source scripts/activate_orbit.sh
CUDA_VISIBLE_DEVICES='' python -m unittest discover -s tests -p test_den_overfit_v5.py
# 同样CPU子进程方式执行环境11/DEN9/pipeline8/interface8/import1回归，共42项
python scripts/prepare_den_overfit_v5.py
python scripts/launch_den_overfit_v5.py  # 唯一已完成任务，不可重放已有tag
python scripts/finalize_den_overfit_v5.py
python scripts/detail_den_overfit_figures_v5.py
python scripts/write_den_overfit_v5_report.py
```

CPU测试的禁GPU仅针对测试子进程，不改变GPU任务继承环境。启动标记独占、原生supervisor直接Popen.wait，禁止删除标记重试。新文件/缓存均在项目内，.venv310 via activate_orbit。轻量源码/CSV/图/审计可安全同步GitHub，原始NetCDF/NPZ、完整预测数组/checkpoint/凭据不上传。最终Git同步状态独立记录。
'''
 with (ROOT/'reports/FOURCASTDEN_DEN_OVERFIT_V5.md').open('x') as f:f.write(report)
 print('Actual evidence report written')
