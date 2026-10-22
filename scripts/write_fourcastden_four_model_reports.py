"""Narrative, future data inventory and six-hour design; no extra inference."""
import sys,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_fourcastden_multistep import sha,dump
from run_fourcastden_four_model_multidate import F,MODELS
from fourcastden.four_model_windows import ALL_DATES

def main():
 a=json.loads((F/'analysis.json').read_text());rt=json.loads((F/'runtime.json').read_text());sup=json.loads((F/'supervision.json').read_text());audit=json.loads((F/'delivery_audit.json').read_text());diag=json.loads((F/'History_interface_diagnostics.json').read_text());dl=json.loads((F/'download.json').read_text());pre=json.loads((F/'preflight.json').read_text())
 def write(path,s):
  with (ROOT/path).open('x') as f:f.write(s)
 def win(d,m,h):return next(r for r in a['windows'] if r['date']==d and r['model']==m and r['hour']==h)
 def var(d,m,h,n):return next(r['mean_layer_RMSE_SI'] for r in a['summary'] if r['date']==d and r['model']==m and r['hour']==h and r['variable']==n)
 def count(h,n,m='History',against='Direct'):return sum(var(d,m,h,n)<var(d,against,h,n) for d in ALL_DATES)
 stats='|模型|时效h|全层DEN绝对RMSE均值 kg/m3|同指标中位数|近400—500组相对RMS均值 %|同指标中位数 %|\n|---|---:|---:|---:|---:|---:|\n'
 for h in (1,2):
  for m in ['Direct','Flow','LogDEN','History']:
   x=next(r for r in a['density_aggregate'] if r['model']==m and r['hour']==h and r['metric']=='mean_DEN_layer_RMSE_kg_m3');y=next(r for r in a['density_aggregate'] if r['model']==m and r['hour']==h and r['metric']=='near400_500_mean_relative_RMS');stats+=f"|{m}|{h}|{x['mean']:.8g}|{x['median']:.8g}|{y['mean']*100:.6f}|{y['median']*100:.6f}|\n"
 high='|日期|Direct %|Flow %|log-DEN %|History %|最低|\n|---|---:|---:|---:|---:|---|\n';absolute='|日期|Direct kg/m3|Flow kg/m3|log-DEN kg/m3|History kg/m3|最低|\n|---|---:|---:|---:|---:|---|\n'
 for d in ALL_DATES:
  high+=f'|{d}|'+ '|'.join(f"{win(d,m,2)['near400_500_mean_relative_RMS']*100:.6f}" for m in ['Direct','Flow','LogDEN','History'])+'|'+min(MODELS,key=lambda m:win(d,m,2)['near400_500_mean_relative_RMS'])+'|\n'
  absolute+=f'|{d}|'+ '|'.join(f"{win(d,m,2)['mean_DEN_layer_RMSE_kg_m3']:.8g}" for m in ['Direct','Flow','LogDEN','History'])+'|'+min(MODELS,key=lambda m:win(d,m,2)['mean_DEN_layer_RMSE_kg_m3'])+'|\n'
 counts='|变量|History优于Direct窗口数 +1h|+2h|\n|---|---:|---:|\n'+''.join(f'|{n}|{count(1,n)}/5|{count(2,n)}/5|\n' for n in ['TN','UN','VN','WN','Z','DEN'])
 perf='|新序列|独立读取ms|loop含指标/hooks s|forward 1/2 ms|保存s|推理allocated峰MiB|\n|---|---:|---:|---|---:|---:|\n'
 for r in rt['records']:perf+=f"|{r['date']} {r['model']}|{r['read_preprocess_s']*1000:.3f}|{r['author_loop_metrics_hooks_s']:.4f}|{r['GPU_forward_ms'][0]:.3f}/{r['GPU_forward_ms'][1]:.3f}|{r['save_s']:.4f}|{r['peak_allocated_bytes']/2**20:.3f}|\n"
 inputshas='\n'.join(f"- {r['name']}: SHA256 `{r['sha256']}`，CRC32 `{r['CRC32']}`。" for r in dl['records'])
 validation=f'''# 五日期四模型共同起点：执行验证（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 授权与资产

五日期固定Jan4/Mar23/Jun21/Sep23/Dec21，统一01起点、02/03目标。Jan4四模型仅从既有npz读取并核对SHA及原指标，不执行网络；新增4日期×4模型=16序列、32forward，0额外真实预检forward。History额外00/01初态、其他仅01，不能称训练单因素消融。无训练/微调/6h/新TIE/轨道。启动前本地main和远端均58c35d9dee2bf15145d2cd85a47235eaa723f7ac，工作区干净。

422个历史保护文件（原始树/Linux副本/4权重/static/static_log/旧结果/日志）SHA不变。四套官方checkpoint分别见preflight.json，与历史官方校验表一致，严格load_state_dict，不使用strict=False。History354输入/171输出、66,870,720参数；其他177/171、64,695,744。log复用已验证隔离覆盖层，原统计/权重不改。

## 最小数据

先从官方2023.zip中央目录核对四成员均存在，随后仅Range提取四个03。HTTP响应全部206，Content-Range与长度精确相符，ZIP校验CRC32及独立zlib复核。总响应体{audit['network_body_bytes']}字节={audit['network_body_bytes']/2**20:.3f}MiB，低于20MiB；未重取其他数据或整包。新文件验证后只读0444。

{inputshas}

14键、变量shape、float32、finite/有限哨兵、正DEN/TN、ZG垂直顺序及训练网格契约检查通过；各字段min/max/unit完整保留*_download.json和preflight。NPZ无独立时间/经纬度/单位属性，日期来自成员名，单位/网格来自作者源码与不变static，不能冒称WGS84/ZG登记已验证。原样本物理范围及预报极值均可复核，不因模型误差大删除日期。

## 时序、反馈与匹配统计

window_indices拒绝Jan4/未注册日期、缺帧/重复/错序/非法history，保证4小时是同日连续00/01/02/03，不能跨季节连接。作者dataset日志“16 hours of past history”是总文件数描述，不是实际n_history；配置History=1，其余0。

复用作者inference：History第一次[real00+aux01,real01+aux02]→pred02，第二次[real01+aux02,pred02+aux03]→pred03，目标标量02/03；其他单状态；Flow normalized delta加当前state，log在原g/cm3做log10、对应static_log标准化，输出10**(norm*std+mean)×1000转kg/m3。真实hooks核对完整输入和反馈、每序列恰好2forward；实际174物理/LBC通道独立从raw重建归一化逐元素一致。未来真实171状态仅评价，给定未来驱动保留HINDCAST。

CPU原有毒化测试继续通过，新5项批量窗口测试加入后共226项（24.779s）。新推理全finite、DEN100%正/TN正，无补0/裁剪/重试。正式后另查History：与Direct普通mean/std逐元素相同，当前01初始171通道和返回real完全一致；未在检查路径发现归一化、checkpoint维度、时间或反馈错误，不能因此排除未公开训练协议或认定唯一误差根因。

## 独立指标

raw物理02/03共同目标、普通physical climatology、固定real01持续性；全部float64反变换、DEN kg/m3、风m/s、Z位势高度m。原压力层、lev/ilev、相对RMS/P95/自然ln指标不当固定450km或Swarm沿轨误差。log作者原生ACC和dex另表，不与共同physical ACC/RMSE混排。

独立NumPy加权求和实现复核{audit['common_physical_channel_checks']}个模型通道时效，rtol1e-12；native normalized RMSE最大相对差{audit['author_normalized_RMSE_max_relative']:.3g}，ACC最大绝对差{audit['author_ACC_max_absolute']:.3g}，沿用rtol2e-5、atol1e-25/ACC2e-6；未放宽。Jan4共同物理DEN40项复算与既有数值一致。所有5日期等权均值/中位/min/max、6模型配对组合、增长与排序保留CSV，不把格点数当独立实验数。

## 实际资源

GPU监督墙钟{sup['wall_s']:.6f}s，进程峰RSS{sup['peak_RSS_bytes']/2**30:.3f}GiB；内部GPU阶段{rt['GPU_phase_wall_s']:.6f}s含CPU读取/指标/hooks/SHA/保存，不是纯forward。第一次冷History157.167ms，其他forward约17.92—20ms；各模型各加载一次后复用四日期，加载时间分别约1.386/1.126/1.131/1.135s（History/Direct/Flow/log）。Jan4旧计时来自另一独立进程且有冷预检，性能表明确区分来源，不能作严格吞吐排名。

{perf}

CPU分析{a['CPU_analysis_s']:.3f}s，分析进程峰RSS{a['analysis_process_peak_RSS_KiB']/1024:.3f}MiB；每次显存allocated/reserved与CPU累计ru_maxrss分别记录。初审新增文件{audit['new_files_bytes']/2**20:.3f}MiB<650MiB，大型NPZ只本地。新显存History约295MiB、普通约282MiB，历史输入翻倍并不意味着总网络成本翻倍。没有把首个cold event与随后warm事件作模型加速比。

## 文件与命令

入口source scripts/activate310.sh；unittest discover；run_fourcastden_four_model_multidate.py --fetch；同脚本静态；supervise_fourcastden_four_model.py；analyze_fourcastden_four_model_multidate.py；audit_fourcastden_four_model_multidate.py；write_fourcastden_four_model_reports.py；最终audit --final。once-only标签不能删除launch后重试，未来需新授权/标签。配置/请求/CRC/SHA/监督/实际反馈审计在experiments/fourcastden_four_model_multidate_v1，压缩大数组data/processed同标签，日志logs/fourcastden_four_model*。本报告是工程验证，不是完整论文训练复现、独立真实大气或轨道准确度证明。
'''
 write('reports/FOURCASTDEN_FOUR_MODEL_MULTIDATE_VALIDATION.md',validation)
 comparison=f'''# 五日期四模型统一01起点比较（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 共同目标与统计单位

每日期01→02→03，Jan4历史只读，另4日期新运行；模型/归一化不同、History额外真实00信息，非严格训练消融。五日期为等权窗口，n=5小规模诊断，无全年/显著性结论。所有模型反变换到同raw TIE-GCM物理参考、同普通physical climatology及相同01持续性；各自native指标另保留。平均层RMSE指先逐层cos纬度加权RMSE后层间等权平均，不混不同变量单位。

## 主要回答

History全层DEN绝对RMSE、高层（参考中位ZG400—500km组与固定upper20—28）相对RMS在两个时效5/5窗均未优于Direct，也未优于Flow。第一小时Flow两项主要DEN指标均5/5最低；第二小时近400—500组Flow3窗最低（Jun/Sep/Dec）、Direct2窗最低（Jan/Mar）。第二小时绝对DEN：log3窗最低（Mar/Jun/Sep）、Direct Jan最低、Flow Dec最低。不能按一项指标选最终模型。

{stats}

均值/中位数可能排序不同；第二小时高层相对RMS等窗均值Direct0.135726%、Flow0.136720%很接近，受Jan4影响，不能仅用“Flow赢3窗”或仅用全窗均值宣布架构优越。每项min/max见density_aggregate.csv；其他变量同样有aggregate.csv逐变量分单位均值/中位/min/max。

## 第二小时逐窗：高层相对与全层绝对

以下近400—500按参考ZG全球中位选择原生ilev层组，每个目标实际索引/中位高度在windows.csv；不是固定几何450km，不是实际卫星沿轨误差。

{high}

{absolute}

全部第一小时和第二小时、固定上层、P95/log差、顶部和极区误差完整CSV，不挑有利日期/层。History绝对密度误差较大在五日期重现；最低5原生层贡献其各层RMSE之和的约97.5%—99.2%，这是RMSE加和的构成比例，不是总MSE贡献/统计方差。低层密度量级大，不能用绝对指标替代上层相对指标；History上层指标同样未改善。

## History额外信息是否有价值

{counts}

第一小时仅Dec WN优于Direct；第二小时仅Dec UN/VN/WN优于Direct。不能说History完全没有任何局部或变量优势，但未显示TN/Z/DEN跨窗优势。所有日期/层的ACC、偏差、极值保留，不将不同单位变量投票合成“总精度”。

已专门检查History与Direct训练mean/std相同、当前初态相同、real目标与aux相同、354输入顺序与预测反馈正确，checkpoint SHA/150项维度严格加载且ordinary static匹配；没有在这些已核查路径找到真实代码错误。较差结果是现有官方模型在该条件协议下的实际残差，保留不修补；尚无原始训练数据/完整训练配置，不能保证排除所有上游模型问题，更不能从一次或五次运行宣布唯一根因。

## 增长和日期依赖

每模型5窗×6变量共30项平均层RMSE均从1h增加到2h，120/120。History DEN绝对RMSE倍率约1.456—1.505；Direct1.373—3.188，Flow1.686—3.622，log1.419—3.167。History在Jan/Dec等窗倍率较小，但其起始绝对误差高约一个数量级，不能说已缓解漂移；在Mar/Jun/Sep，History DEN倍率反而略高于Direct。高层相对增长History约2.56—3.42倍，通常比Mar/Jun/Sep其他模型更高；倍率与绝对误差必须一起看。只有两个目标不支持长期稳定性结论。

## 00/01起点条件敏感性

旧三模型00起点目标01/02，新01起点目标02/03；相同lead不是相同目标，不能称完全同任务。另提供共同目标02的旧+2h/新+1h配对，但其初始信息/lead不同，不能排名纯架构或归因特定驱动。History无合法00起点对照，不作此比较。

新+2h近400—500组相对RMS对旧+2h的倍率：Jan4 Direct/Flow/log约3.186/4.246/2.558，Dec21约2.591/2.275/2.297；Mar23约1.046/1.148/1.089，Jun21约0.964/0.957/0.954，Sep23约1.013/1.032/1.041。因此不是所有01时都更难，不同日期依赖明显。旧Flow两时效5/5高层较低，在新第二小时Jan/Mar被Direct超越；log旧第二小时5/5绝对最低在新窗口变成3/5。

逐日期原始F107/F107A/Kp四帧见drivers.csv，原参考相邻小时物理变化见reference_changes.csv。未凭误差变化宣称地磁因果，未更换原NPZ驱动或平滑输入。Mar23早期不是强磁暴样本；不同UT/目标时效、状态/驱动和参考演变相互混杂。无NaN/Inf/负DEN/异常修补或额外重跑，不能因大残差推定数据损坏。

## 成本与成果索引

新32forward监督42.575s/峰RSS1.222GiB，四模型各加载一次；History参数66.87M，比64.70M多3.36%，输入354vs177。推理allocated约295vs282MiB；单次warm事件不能给严格速度排名。详细读取/加载/首次/后续forward/loop含评价hooks/保存/RSS/CUDA表见performance.csv，Jan4来源单列。CPU分析10.557s、峰约364MiB。不能把GPU phase墙钟当网络forward耗时，不能把本次计时等同端到端AI替代TIE仿真效率。

- layers.csv8550行、summary.csv300行、density_layers.csv4350行、windows.csv50行（含Persistence）；author_native.csv6840行，log dex/ACC空间明确。
- aggregate.csv48行、density_aggregate.csv40行，5窗均值/中位/min/max；pairs.csv360行、density_pairs.csv300行；rankings.csv50行；growth.csv120行。
- initialization.csv360行，明确同lead异目标/同目标异lead；performance.csv20行；drivers.csv20行；reference_changes.csv90行。
- 统一前缀results/metrics/fourcastden_four_model_multidate_v1_；7图在results/figures同前缀high_DEN、absolute_DEN、variables、growth、history_pairs、initialization、performance。
- experiments/fourcastden_four_model_multidate_v1/analysis.json、History_interface_diagnostics.json、delivery_audit.json/最终审计，所有原始大数组仅本地。

226测试、6840共同物理通道独立复核、422历史保护SHA通过；以日期为样本，不能把格点增加当显著性证据。当前不足以选择最终模型或确定训练超参数；值得提出相对/分层损失、多步训练及History训练协议核查假设，但必须用独立训练/验证数据而非2023调参。下一步仅设计Jan4和基于外部GFZ预选Mar24的6h连续实验，不执行；真实大气/轨道精度门禁不变。
'''
 write('reports/FOURCASTDEN_FOUR_MODEL_MULTIDATE_COMPARISON.md',comparison)
 # Fixed external-driver choice, independent of model errors; no new download.
 gfz=ROOT/'data/raw/meeting_sources/gfz_Kp_extended_support.txt';g=json.loads(gfz.read_text());external=[dict(time=t,Kp=k,status=s) for t,k,s in zip(g['datetime'],g['Kp'],g['status']) if t.startswith('2023-03-24') and int(t[11:13])<=6];assert len(external)==3 and all(r['Kp']>=5 and r['status']=='def' for r in external)
 inventory=json.loads((ROOT/'logs/test_archive_inventory.json').read_text());byname={r['name']:r for r in inventory};future=[]
 for day in ['2023-01-04','2023-03-24']:
  members=[]
  for h in range(8):
   name=day.replace('-','_')+f'_{h:02d}0000.npz';assert name in byname;existing=day=='2023-01-04' and h<=3
   members.append(dict(name=name,already_available=existing,needed_download=not existing,**{k:byname[name][k] for k in ['bytes','compressed','crc']}))
  future.append(dict(date=day,t0_hour=1,target_hours=list(range(2,8)),members=members))
 dump(F/'six_hour_future_inventory.json',dict(status='DESIGN_ONLY_NO_DOWNLOAD_NO_INFERENCE',dates=future,GFZ_source=str(gfz.relative_to(ROOT)),GFZ_SHA256=sha(gfz),GFZ_selection=external,selection_rule='Additional independent untested day Mar24: all three GFZ UTC00/03/06 Kp bins >=5, def; chosen by external drivers, not model error',new_members=12,new_member_compressed_bytes=sum(m['compressed'] for d in future for m in d['members'] if m['needed_download'])))
 plan=f'''# 下一阶段四模型6小时连续预测方案（设计，未执行）

## 任务与预注册窗口

先本次五日期四模型短时工程门禁和独立评价验收，再另行授权6h。固定工程基准Jan4 2023 t0=01至07；第二窗口固定Mar24 2023 t0=01至07，尚无该窗模型误差。本地GFZ公开驱动def状态UTC00/03/06分别Kp7.333/8/6.333，按全部>=5的外部增强活动规则选择，不根据模型表现筛日期。GFZ文件SHA `{sha(gfz)}`。这不是实时预报，作者NPZ的小时插值/通量约定还须下载后逐项核验，不能直接替换成GFZ值。

官方既有2023.zip目录核对两日期00—07全部存在；只确认中央目录，不是尚未下载成员的CRC或物理有效性。详细文件名、CRC、压缩/解压字节、已具备状态在six_hour_future_inventory.json。本次未下载或执行这些未来帧。

## 最少输入

每窗8帧00/01/02/03/04/05/06/07。History真实00+01，其他真实01；目标02—07共6步。Jan4已00—03，缺04—07四帧；Mar24尚无输入，需00—07八帧；总新增12帧，只Range提取，不能下载整包。预算请求建议网络40MiB（以清单实际压缩字节加目录开销复核）、新增800MiB、GPU600s、RAM4GiB；这些为未来建议，不沿用本次授权，超预估先停止。可先仅授权Jan4四模型，再独立执行增强活动窗，不能因首窗结果差而更换第二窗。

## 连续反馈必须升级验证

作者原n_prediction=6，而非将3个2h实验拼接或在02/03重新喂真状态。普通模型每步使用前一步预测，Flow按normalized增量更新；log始终在其匹配log标准化表示滚动；History窗口：[real00,real01]→[real01,pred02]→[pred02,pred03]→…→[pred05,pred06]预测07。03开始两个历史物理状态都必须是预测值。aux和目标标量严格按作者原循环对应，记录给定未来条件HINDCAST。

现有two-step feedback_check只支持两次，不能未经修改直接用于6h；新建独立任意长度检查器/合成毒化测试，毒化02以后所有真实171状态后整个6步预测不变。hook记录六次输入与输出，检查无变量/历史/辅助错位。严加载官方4权重/匹配static，原源码不改，log复用隔离等价层。不可由更换归一化、指数裁剪或真实状态重置掩盖失败。

## 评价与停止

1—6h逐步逐变量/原生层cos RMSE、physical climatology ACC，DEN相对RMS/自然ln/P95/偏差/正性；相同real01持续性。400—500参考中位ZG层组和固定upper20—28分开；目标ZG只作参考分组，不把它当AI预测几何高度或轨道输入。既往2h结果只能作一致性核验，不替代6h真实连续反馈。

逐步记录温度/风/Z/DEN物理极值、NaN/Inf、非正密度、指数溢出、增长及空间偏差。不预设6h一定稳定；出现数值/单位/反馈/数据门禁失败停止并保留各时效，不能补0/裁剪/自动重试；只因残差较大不删除样本。独立NumPy复核沿用现阈值，工程通过不以模型必须优于其他为条件。

只两窗仍是诊断，不能用空间格点数量作独立样本；无法证明全年优势、真实大气或轨道准确度。判断误差是否随lead持续增长及是否支持随后12/24h，不能用2点或单窗线性外推。

## 资源与可发表研究前提

本次32forward含I/O监督42.6s/峰RSS1.22GiB，未来8个6h序列共48forward但单结果更大、活动驱动可能改变数值/输出压缩。按本次存储外推约0.5—0.7GiB并留裕量，建议上述800MiB/600s；是估计，不是实测或运行许可。模型各加载一次复用两窗，单序列独立初始化；加载/读取/forward/指标/保存分别计，CPU RSS与显存各监控；严格吞吐需要另预注册warm-up/重复方案，不能额外默认执行。

在模型改进前还需作者完整训练入口、2000—2021训练/2022验证/2023锁定测试的可追溯数据和配置、损失/优化器/采样/随机种子、计算预算；四预训练变体不是训练因果消融。改进应预注册主要高层密度指标、独立验证集选参、多种子/对照与长期稳定性，不在这5个2023窗上拟合层权重。真实大气精度需独立观测，卫星轨道应用还需DEN/Z/ZG/外部高度/时间接口、Swarm气动姿态推力和共同受力误差控制。本次只交付设计，停止，不自动训练、6/12/24h或轨道。
'''
 write('docs/FOURCASTDEN_SIX_HOUR_EXPERIMENT_PLAN.md',plan)
 print('Wrote validation/comparison reports and 6h design; no future download or forward')
if __name__=='__main__':main()
