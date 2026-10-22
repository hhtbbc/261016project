"""Create narrative and native metric CSV strictly from saved run artifacts."""
import sys,json,csv
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_fourcastden_multistep import dump
from run_fourcastden_history_comparison import F,D,MODELS
from fourcastden.validation import NAMES,LENGTHS,UNITS

def main():
 a=json.loads((F/'analysis.json').read_text());rt=json.loads((F/'runtime.json').read_text());sup=json.loads((F/'supervision.json').read_text());pre=json.loads((F/'preflight.json').read_text());dl=json.loads((F/'download.json').read_text());ranges=json.loads((F/'ranges.json').read_text());audit=json.loads((F/'delivery_audit.json').read_text())
 def win(m,h):return next(r for r in a['windows'] if r['model']==m and r['hour']==h)
 def var(m,h,n):return next(r for r in a['summary'] if r['model']==m and r['hour']==h and r['variable']==n)
 def write(path,s):
  with (ROOT/path).open('x') as f:f.write(s)
 rows=[]
 for m in MODELS:
  with np.load(D/f'{m}.npz') as q:
   for h in (1,2):
    offset=0
    for name,n,unit in zip(NAMES,LENGTHS,UNITS):
     for k,c in enumerate(range(offset,offset+n)):rows.append(dict(model=m,hour=h,variable=name,layer_index=k,author_returned_RMSE=float(q['author_rmse'][0,h-1,c]),author_RMSE_unit=unit,normalized_RMSE=float(q['author_normalized_rmse'][h-1,c]),std_scaled_native_RMSE=float(q['author_normalized_rmse'][h-1,c]*q['stds'][c,0,0]),std_scaled_unit='dex' if m=='LogDEN' and name=='DEN' else unit,author_ACC=float(q['author_acc'][0,h-1,c]),author_ACC_space='log10(g/cm3), own log climatology' if m=='LogDEN' and name=='DEN' else 'own physical climatology'))
     offset+=n
 with (ROOT/'results/metrics/fourcastden_history_v1_author_native.csv').open('x') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 table='|模型|参数量|checkpoint字节|加载s|独立读取/预处理ms|正式forward 1/2 ms|循环含指标/hooks s|保存s|推理CUDA allocated峰MiB|\n|---|---:|---:|---:|---:|---|---:|---:|---:|\n'
 for r in a['performance']:table+=f"|{r['model']}|{r['parameters']:,}|{r['checkpoint_bytes']}|{r['model_load_s']:.6f}|{r['read_preprocess_s']*1000:.3f}|{r['formal_first_forward_ms']:.3f}/{r['formal_second_forward_ms']:.3f}|{r['author_loop_metrics_hooks_s']:.6f}|{r['save_s']:.6f}|{r['peak_allocated_bytes']/2**20:.3f}|\n"
 shas='\n'.join(f"- {m}: `{pre['checkpoint_sha256'][m]}`" for m in MODELS)
 validation=f'''# 官方History首次两小时自回归验证（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 执行范围与数据

仅2023-01-04：History使用00/01真实状态，t0=01，目标02和03；其他三模型仅使用01真实物理初态。4个新独立序列/8正式forward，加唯一History真实forward预检1次。历史00→01→02数组不被当本次新起点结果，无训练/调参/额外日期/扩窗/TIE/RK45。221项全套自动测试通过（24.452s），新6项CPU测试调用实际作者循环及合成网络，不是额外真实模型预测。

唯一新原始成员`2023_01_04_030000.npz`，官方Zenodo2023.zip中央目录存在，偏移{dl['header_offset']}，成员CRC32={dl['CRC32']}。实际HTTP请求全部206并匹配Content-Range，传输{ranges['transfer_bytes']}字节（{ranges['transfer_bytes']/2**20:.3f}MiB）<10MiB。新文件SHA256 `{dl['SHA256']}`。00—02仅软链接原文件，不重下载。14字段、float32/shape/finite/哨兵/正密度/TN/ZG逐层单调检查通过；原始NPZ无独立单位或时间坐标属性，小时来自官方成员名、单位/网格来自作者UNIT_VARS和不可变static契约，不能声称外部观测坐标基准已被证明。详细stats/请求见download.json、ranges.json、preflight.json。

## 官方实现与通道顺序

直接依据`third_party/FourCastDEN/inference/inference.py` load_model、forecast、inference；README_inference_2023表格指定Baseline_1h_history_ckpt.tar、n_history1、flowfalse、log_DENfalse、普通static。AFNONet仍4×4 patch/768嵌入/12块，n_in_channels基础177×(history+1)=354，输出171、标量4；实际严格load_state_dict，无strict=False。History参数66,870,720，比64,695,744增加2,174,976（约3.36%），来自patch embedding多177输入。全部权重原样：

{shas}

每一177块是TN/UN/VN各28，WN/Z/DEN各29（171），随后TLBC/ULBC/VLBC、SEA、磁纬/磁经6个辅助通道。原inference按时间先旧后新reshape。第一输入：[real00物理+aux01]、[real01物理+aux02]，标量驱动02；第二输入：[real01物理+aux02]、[pred02物理+aux03]，标量03。History直接预测绝对归一化状态，不加增量。02/03真实物理通道只用于评价。

## 反馈与兼容性证据

CPU合成实际作者循环检查先后次序、354维、输出、aux/标量对齐；未来物理真值毒化后预测逐元素不变，逆序/teacher-forcing/辅助或标量错位均被拒绝。真实forward hooks逐元素检查两个完整177块与预测反馈，唯一预检输出与正式第一步逐元素一致。作者裁去最早历史后，pred为(1,3,171,36,72)，real为(1,3,177,36,72)，时间对应01/02/03；real额外保留6辅助通道。History无新增源码补丁；log模型复用上一任务经过SHA核对的隔离覆盖层，static_log单例、DEN广播和torch.pow等价修复不再改动。原源码、权重、static和既往结果356个保护文件SHA不变。

4模型实际原始174物理/LBC通道归一化独立重建完全一致于各自匹配统计；未来标量和磁通道匹配，普通三模型SEA一致，log SEA差最大7.153e-7，源自官方static坐标dtype，未强制替换。log静态统计其他变量亦不同；这是官方整套预训练配置对照，不是严格训练消融。

## 数值与物理检查

全部预测finite、DEN100%正、TN正，无裁剪、补0、重试。native标准化RMSE/自身气候态ACC与float64重算沿用rtol2e-5/atol1e-25、ACC绝对2e-6，未放宽；独立共同物理RMSE/ACC共{audit['independent_common_channel_checks']}个通道时效检验rtol1e-12通过。log作者DEN ACC仍log空间，返回DEN RMSE物理g/cm3，dex另存，不能与共同kg/m3或物理ACC混排。原生指标CSV有1368行，公共逐层CSV有1710行（含共同持续性）。

## 实际成本

{table}

History唯一冷预检forward={rt['records'][0]['history_precheck']['network_GPU_ms']:.3f}ms，之后正式两次已经warm；其他模型共享CUDA内核/文件缓存。首次正式forward不一定冷，不按上表的单次事件给吞吐排序。History额外输入增加参数约3.36%、推理allocated峰约{(a['performance'][0]['peak_allocated_bytes']/a['performance'][1]['peak_allocated_bytes']-1)*100:.2f}%，本例不是输入翻倍则成本翻倍。reserved显存含加载/缓存，不能当活跃tensor用量；load峰与每次推理峰分开记录。进程ru_maxrss为累积峰，独立监督聚合RSS峰{sup['peak_RSS_bytes']/2**30:.3f}GiB。

监督墙钟{sup['wall_s']:.6f}s，内部GPU阶段（含加载/CPU压缩/SHA等）{rt['GPU_phase_wall_s']:.6f}s，预算600s；纯网络事件另列。CPU离线分析{a['CPU_analysis_s']:.6f}s，独立预读取在作者loop内还会重复，不简单相加解释成纯推理时间。初审新增文件{audit['new_files_bytes']/2**20:.3f}MiB，另预留1MiB源码/报告，小于150MiB；无大型数组入Git。

## 重复执行与审计入口

`source scripts/activate310.sh`；`python -m unittest discover -s tests`；run_fourcastden_history_comparison.py --fetch；同脚本无参数静态；supervise_fourcastden_history.py；analyze_fourcastden_history.py；audit_fourcastden_history.py；write_fourcastden_history_reports.py；最终audit的--final。全部once-only，不要在同标签重复网络/推理；未来复现实验必须新授权/新run-tag，不能删除launch文件重试。

实际配置、数据/代码/权重SHA、hooks数组、runtime、supervision、reference_dynamics及audit均在experiments/fourcastden_history_comparison_v1；大型压缩结果在data/processed同标签，仅本地。日志logs/fourcastden_history*。这是工程和TIE模拟参考评价通过，独立真实大气/轨道科学准确度未验证。
'''
 write('reports/FOURCASTDEN_HISTORY_VALIDATION.md',validation)
 density='|模型|时效h|全层平均DEN RMSE kg/m3|400—500组相对RMS %|同组自然log RMS|顶层相对P95 %|\n|---|---:|---:|---:|---:|---:|\n'
 for h in (1,2):
  for m in ['Direct','Flow','LogDEN','History']:
   r=win(m,h);density+=f"|{m}|{h}|{r['mean_DEN_layer_RMSE_kg_m3']:.8g}|{r['near400_500_mean_relative_RMS']*100:.6f}|{r['near400_500_mean_log_RMS']:.8g}|{r['top_relative_P95']*100:.6f}|\n"
 vart='|变量（SI单位）|时效h|Direct|Flow|log-DEN|History|\n|---|---:|---:|---:|---:|---:|\n'
 for name,unit in zip(NAMES,['K','m/s','m/s','m/s','m','kg/m3']):
  for h in (1,2):vart+=f"|{name} ({unit})|{h}|"+'|'.join(f"{var(m,h,name)['mean_layer_RMSE_SI']:.8g}" for m in ['Direct','Flow','LogDEN','History'])+'|\n'
 growth='|模型|全层DEN绝对RMSE第2/1小时倍率|400—500组相对RMS第2/1倍率|\n|---|---:|---:|\n'
 for m in ['Direct','Flow','LogDEN','History']:growth+=f"|{m}|{win(m,2)['mean_DEN_layer_RMSE_kg_m3']/win(m,1)['mean_DEN_layer_RMSE_kg_m3']:.4f}|{win(m,2)['near400_500_mean_relative_RMS']/win(m,1)['near400_500_mean_relative_RMS']:.4f}|\n"
 comparison=f'''# FourCastDEN四模型共同起点对照（2026-10-22）
HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 任务和公平性

第二阶段复现，唯一窗口Jan4 2023，t0=01，预测02/03。四组都新执行，不拿旧00起点第2小时当本次第1小时；旧实验不覆盖。History额外获得00时真实状态，其余仅01，保留不同官方权重/匹配统计，不能称单一历史开关训练消融。

按共同raw NPZ物理目标与普通物理气候态，匹配反变换float64；DEN kg/m3、自然ln密度比，温度K、风m/s、Z位势高度m。全层平均先逐原生压力层算cos纬度RMSE再等权平均，不混不同单位。log本身log10(g/cm3)以10为底恢复，不能把标准化值/dex直接当密度。共同固定真实01物理场为持续性，不随模型改变；本窗口4模型两时效各171/171通道RMSE均低于该基准，但不等于真实大气观测精度。

## DEN：本次未支持History短时优势

{density}

History两时效全层平均绝对DEN RMSE约为Direct的{win('History',1)['mean_DEN_layer_RMSE_kg_m3']/win('Direct',1)['mean_DEN_layer_RMSE_kg_m3']:.2f}/{win('History',2)['mean_DEN_layer_RMSE_kg_m3']/win('Direct',2)['mean_DEN_layer_RMSE_kg_m3']:.2f}倍，不能隐藏底层不利结果。400—500组第一小时Flow最低，第二小时Direct最低，History均较高；固定upper20—28组排序也在CSV中，不能沿用旧00起点“Flow两小时均最低”的结论。log两小时均未取得四模型绝对DEN RMSE最小值：第一小时Flow、第二小时Direct最低；旧五窗00起点log第二小时5/5最低并没有在新01起点延续。这是初始相位/目标变化下的条件观察，不推翻或覆盖旧任务实际数据。

近400—500组按每个目标参考ZG全球中位定位原生ilev索引；第二小时同样包含21/22/23，中位高度随时间变化，完整值见windows.csv。不是固定450km几何剖面、不是WGS84高度，也不使用卫星坐标适配。每一层/全球/极区>=60度/非极区的相对RMS、P95、max、自然log RMS/偏差均保留density_layers.csv；不挑优势层。顶层P95并非同一个模型始终最好，表中完整呈现。

## 温度、风和Z

{vart}

History两个时效的六变量平均层RMSE均高于Direct，因而不能说额外历史在本窗口已经改善。第一小时除DEN由Flow最低外，其他五变量Direct最低；第二小时六变量均Direct最低。History第二小时个别变量较Flow略低，并不等于优于Direct/总体架构更优。每层ACC/分母有效性、偏差、极值另列CSV，RMSE和ACC不混为同一指标。

## 增长、稳定性和参考场核查

{growth}

四模型所有六变量平均RMSE都从1h增至2h。History全层DEN增长倍率更小，但起点绝对误差已高很多，不能据此认定更稳定或更准确；同组相对增长也未普遍小于log模型。两目标不足以估计长时漂移或证明历史输入失效。

观察到新窗口第2小时TN/风/Z及高层密度误差增长明显，于是只读核查原参考00→01、01→02、02→03相邻增量：TN平均层加权变化约17.156/17.361/17.528K，DEN约1.089/1.083/1.085e-12g/cm3，未见03时相邻增量的数量级跳变。原03通过CRC/SHA/shape/finite/正性，不因模型误差大而删窗、改目标或重跑；这也不是参考物理准确度证明，尚无独立真实大气观测。reference_dynamics.json保留各变量/下边界范围与实际驱动。

F10.7/f107a/Kp在四个小时依次为：

|UTC小时|F10.7 sfu|F10.7A sfu|Kp|
|---:|---:|---:|---:|
'''+''.join(f"|{r['hour_UTC']}|{r['f107d']:.6f}|{r['f107a']:.6f}|{r['Kp']:.6f}|\n" for r in a['drivers'])+f'''

未来驱动来自官方NPZ，模型没有自主预报它们；不能仅凭Kp增长把误差归因于磁暴，也不称强磁暴泛化检验。没有非有限值、非正DEN或指数溢出；History密度误差大于其他模型属于实际预测残差，未放宽工程门槛制造通过。

## 计算成本与独立复核

{table}

History已先做146.774ms冷预检，正式forward约18.4—18.6ms，其他模型共享进程预热。无大量重复warm-up，不给稳定吞吐排名。参数约多3.36%，输入两倍不代表总FLOP/耗时两倍。监督全部21.011s/峰RSS约1.225GiB，CPU分析{a['CPU_analysis_s']:.3f}s，读取、原循环含评价/hooks、保存、模型加载口径分开。GPU阶段包括CPU I/O，不能当纯forward总时间。

221测试、356保护文件SHA、原生与共同物理指标独立NumPy检查通过。共同物理通道核查1368次，native误差约1e-7量级，沿用门槛不变。原native DEN log ACC/dex另存author_native.csv，不同物理量指标不加总。无训练、调参、数据替换或失败重试。

## 结果索引与下一步

- results/metrics/fourcastden_history_v1_layers.csv：1710行公共逐层RMSE/ACC，含Persistence；summary.csv60行；density_layers.csv870行；windows.csv10行；growth.csv24行；performance.csv4行；drivers.csv4行；author_native.csv1368行。
- results/figures/fourcastden_history_v1_near400_500.png、DEN_layers.png、variables.png、growth_top.png、performance.png：真实结果5图。
- experiments/fourcastden_history_comparison_v1：配置/请求/CRC/SHA、预检、真实输入反馈、资源、分析与audit；data/processed同标签大型NPZ仅本地。

建议先做五日期同01起点的四模型短时对照（四个其他日期各需补03，另授权），再预注册6h，之后12/24h与实际强活动窗口。不用此单窗筛训练超参；History首次工程验证成功不等于泛化优势，log高层不利/Flow新时效改变排序都要求多初值而非挑选最佳窗口。真实大气、真实Swarm轨道验证仍须独立观测、气动/姿态/推力、TIE高度/预热/时间分辨率与共同受力误差控制，不能由AI对TIE拟合结果替代。
'''
 write('reports/FOURCASTDEN_FOUR_MODEL_COMPARISON.md',comparison)
 print('Wrote two reports and 1368-row separate native metrics CSV')
if __name__=='__main__':main()
