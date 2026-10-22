"""Evidence-based reports; reads saved results only, no inference or networking."""
import json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/fourcastden_twelve_hour_mar24_v1';MODELS=('Direct','Flow','LogDEN','History')
def main():
 a=json.loads((F/'analysis.json').read_text());c=json.loads((F/'two_window_comparison.json').read_text());rt=json.loads((F/'runtime.json').read_text());sup=json.loads((F/'supervision.json').read_text());audit=json.loads((F/'delivery_audit.json').read_text());assert audit['status']==c['status']=='PASS'
 def write(p,s):
  with (ROOT/p).open('x') as f:f.write(s)
 def win(d,m,h):return next(x for x in c['windows'] if x['date']==d and x['model']==m and x['hour']==h)
 def var(d,m,h,n):return next(x for x in c['summary'] if x['date']==d and x['model']==m and x['hour']==h and x['variable']==n)
 def table(key,factor=1):
  out='|日期|模型|+1h|+2h|+3h|+6h|+9h|+12h|\n|---|---|---:|---:|---:|---:|---:|---:|\n'
  for d in ['2023-01-04','2023-03-24']:
   for m in MODELS:out+=f'|{d}|{m}|'+ '|'.join(f'{win(d,m,h)[key]*factor:.7g}' for h in [1,2,3,6,9,12])+'|\n'
  return out
 perf='|日期/模型|加载s|读取解码s|标准化s|其余预处理s|首forward ms|其余均值ms|12forward合计ms|loop s|保存s|物理解码hook s|CUDA峰MiB|\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|\n'
 for r in c['performance']:perf+=f"|{r['date']} {r['model']}|{r['model_load_s']:.4f}|{r['read_decode_s']:.4f}|{r['normalization_s']:.4f}|{r['other_preprocess_s']:.4f}|{r['first_formal_forward_ms']:.3f}|{r['later_forward_mean_ms']:.3f}|{r['network_total_GPU_ms']:.3f}|{r['author_loop_metrics_hooks_s']:.4f}|{r['save_s']:.4f}|{r['physical_decode_hook_s']}|{r['peak_allocated_bytes']/2**20:.3f}|\n"
 phys=[p for r in rt['records'] for p in r['step_physics']]
 validation=f'''# FourCastDEN Mar24连续12小时执行验证（2026-10-22）

HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 实际执行与来源

固定Mar24 01→13，4官方模型各12步，48正式forward，无额外GPU预检，无失败模型/自动重试。Direct/Flow/log真实01，History真实00/01；后续全部来自预测。没有重新运行Jan4、六小时、TIE、RK45、24h或训练/微调。开始确认本地及远端main为b081de700089634221381d9ee4aad2eb6e2355b9。

先冻结MAR24_TWELVE_HOUR_PREREGISTRATION.md，239测试27.884秒通过（复用四模式12步CPU作者循环毒化、History最后双预测和前缀检查，加2日期隔离/门禁测试）。旧ERFA合成dubious-year警告保持，不修改依赖。AFNONet严格加载，Direct/Flow/log64,695,744参数，History66,870,720；177/354输入、171输出、FP32、TF32关闭。四权重/对应普通static/static_log/隔离log兼容层SHA及原作者树与旧实验保护{audit['protected_files_unchanged']}项不变。

官方目录先确认08—13六成员，压缩合计12,469,476字节，远端目录CRC/尺寸/offset复核；网络实际{audit['network_body_bytes']}字节={audit['network_body_bytes']/2**20:.4f}MiB<25MiB。全Range206/Content-Range/长度、ZIP和zlib CRC/SHA、14键/shape/dtype/有限哨兵/正DEN/TN/ZG递增通过，raw0444，00—07只读复用。文件时间来自官方名称、网格/单位来自源码和static契约，不冒称NPZ有完整独立坐标元数据。

## 前六小时与反馈门禁

逐step hook精确比较旧Mar24六小时input/scalar/raw network/state，means/std精确；全部最大差0。执行后pred初始化+前6帧逐元素一致，24模型时效六变量summary与旧DEN指标全部相同，见prefix_metrics_gate.json。原六小时文件不改，门禁失败会保存失败前缀并停止，不放宽阈值。

12步完整作者inference而非两个6h拼接；History [real00,real01]→[real01,pred02]→[pred02,pred03]→…；Flow normalized delta加当前state；log使用匹配log10(g/cm3)统计与pow10反变换，DEN乘1000为kg/m3，风/Z乘.01为SI。每步未来aux/scalar与目标对齐，真实171物理场只评价。已知未来外部条件仍HINDCAST，非实时自主预测。

## 独立评价与数值状态

公共raw目标02—13、普通physical climatology、真实01持续性一致；cos纬度加权RMSE/有效ACC、偏差/极值、逐层/极区/顶部/固定upper/near组均保存。独立NumPy加权求和复核{audit['common_physical_channel_checks']}物理通道时效rtol1e-12，作者native normalizedRMSE最大相对差{audit['author_normalized_RMSE_max_relative']:.4g}、ACC最大绝对差{audit['author_ACC_max_absolute']:.4g}，沿用rtol2e-5/RMSEatol1e-25/ACCatol2e-6。log native ACC/dex与公共物理指标分表，未更改容差。

48输出finite、DEN100%正，TN范围{min(x['TN_min_K'] for x in phys):.3f}—{max(x['TN_max_K'] for x in phys):.3f}K，最大绝对风分量{max(x['max_abs_wind_m_s'] for x in phys):.3f}m/s，Z位势高度{min(x['Z_min_m'] for x in phys)/1000:.3f}—{max(x['Z_max_m'] for x in phys)/1000:.3f}km。无指数溢出/非正密度/明显数值发散，不等于真实物理准确。所有模型每lead171通道RMSE均优于真实01持续性；仍只是对TIE参考。

## 计算成本

{perf}

本次监督{sup['wall_s']:.6f}s、worker内部{rt['GPU_phase_wall_s']:.6f}s含加载/CPU I/O/指标/保存，峰RSS{sup['peak_RSS_bytes']/2**30:.4f}GiB；独立CPU分析{a['CPU_analysis_s']:.4f}s、峰{a['analysis_peak_RSS_KiB']/1024:.3f}MiB。初审新增{audit['new_files_bytes']/2**20:.3f}MiB（最终以final_delivery_audit.json为准）<800MiB；GPU600s、RAM4GiB内。

物理解码hook单独计时是独立float64物理检查成本，属于作者loop的一部分；作者native log反变换还包含于native指标调用区间，不能把二者相加当纯解码。Jan4没有同项独立计时记N/A不是0。首次Direct冷CUDA，后续模型已warm；网络事件/native指标事件/loop/读写分别记录，不能按本次冷启动排序速度或与TIE完整仿真声称端到端加速。

## 复现与交付

source scripts/activate310.sh；unittest discover；run_fourcastden_twelve_hour_mar24.py --fetch；无参preflight；supervise_fourcastden_twelve_hour_mar24.py；analyze_fourcastden_twelve_hour_mar24.py；compare_fourcastden_twelve_hour_mar24.py；audit；write_reports；audit --final。所有run/下载/launch输出exclusive，原数据不覆盖。预测大NPZ只本地；CSV/图/配置/审计/日志公开轻量部分。Jan4只读SHA验证，无重新推理。当前仅完成工程/条件参考场实验，未完成训练复现、独立真实大气或正式轨道精度验证。
'''
 write('reports/FOURCASTDEN_TWELVE_HOUR_MAR24_VALIDATION.md',validation)
 text='''# FourCastDEN两窗口四模型12小时比较（2026-10-22）

HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 主要发现与范围

Jan4历史只读，Mar24新4×12，共同01起点/02—13目标、各官方权重与匹配统计。History额外00真实状态，不是单因素训练消融。两窗口不是全年统计，不用网格数夸大独立样本数。原作者未来驱动和下边界给定，尚非实时自主预测。

Mar24高层相关组Flow仅+1最低，History+2—4最低，log+5—12最低；Direct没有延续Jan4中后期的该指标优势。固定upper20—28在+12却是Direct最低，History的顶部/极区局部指标也有条件优势，不选单层组宣布总体架构优劣。History全层绝对DEN所有时效仍最高。

## 高层组相对RMS（%）

'''+table('near400_500_mean_relative_RMS',100)+'''
## 全层DEN逐层绝对RMSE平均（kg/m3）

'''+table('mean_DEN_layer_RMSE_kg_m3')+'''
## 同组高层绝对RMSE（kg/m3）

'''+table('near400_500_mean_absolute_RMSE_kg_m3')
 text+='''
Mar24 near组+1/+2为20/21/22，+3—11为20/21，+12又为20/21/22（中位ZG421.145/455.861/492.273km）。Jan4始终21/22/23。因此+12变化和跨日期差还含压力组组成不同，不能称固定450km或Swarm沿轨误差；固定upper20—28和全部逐层结果是必要补充。每个时效同日期四模型使用完全同组/目标/掩码。

## 第12小时局地风险与系统偏差

|日期|模型|固定upper相对RMS %|顶层相对RMS %|顶层P95 %|极区全部层最大相对差 %|near均值相对偏差 %|
|---|---|---:|---:|---:|---:|---:|
'''
 for d in ['2023-01-04','2023-03-24']:
  for m in MODELS:
   r=win(d,m,12);text+=f"|{d}|{m}|"+'|'.join(f'{r[k]*100:.6f}' for k in ['upper20_28_mean_relative_RMS','top_relative_RMS','top_relative_P95','polar_relative_max','near400_500_relative_bias'])+'|\n'
 text+='''
四模型Mar24 near均为正密度偏差约3%；History局地极区最大差较小，但log局地极差较大，不能仅凭平均误差选模型。相对残差大并非数值发散，所有密度有限正值。极区固定upper逐层平均相对RMS曲线另图，避免只用单个极值判断稳定性。

## 误差增长：同时看倍率和绝对增量

|日期|模型|near 12/1|near 12/6|near 12−6百分点|near峰值时效|全层绝对DEN 12/1|
|---|---|---:|---:|---:|---:|---:|
'''
 for d in ['2023-01-04','2023-03-24']:
  for m in MODELS:
   r=next(x for x in c['growth'] if x['date']==d and x['model']==m and x['metric']=='near400_500_mean_relative_RMS');q=next(x for x in c['growth'] if x['date']==d and x['model']==m and x['metric']=='mean_DEN_layer_RMSE_kg_m3');text+=f"|{d}|{m}|{r['ratio_12_to_1']:.4f}|{r['ratio_12_to_6']:.4f}|{r['absolute_increment_12_minus_6']*100:.6f}|{r['peak_lead_hour']}|{q['ratio_12_to_1']:.4f}|\n"
 text+='''
Jan4 near Direct/Flow/log+9峰、History+11峰；Mar24 Direct/Flow/log+6峰后回落，History+12略高于+6，后半段均有起伏。Flow从首小时较低误差出发，12/1倍率较大，但不能单凭倍率称更不稳定；Mar24更大的初始误差也使增长倍率小于Jan4。History并未持续缓解中后期误差，仍存在+2—4的条件高层优势，不应删除其结果。log无指数发散，不证明对数表示总能改善相对误差。

## 六变量第12小时误差（各自单位，不相加）

|日期|模型|TN K|UN m/s|VN m/s|WN m/s|Z m|DEN kg/m3|
|---|---|---:|---:|---:|---:|---:|---:|
'''
 for d in ['2023-01-04','2023-03-24']:
  for m in MODELS:text+=f'|{d}|{m}|'+ '|'.join(f"{var(d,m,12,n)['mean_layer_RMSE_SI']:.7g}" for n in ['TN','UN','VN','WN','Z','DEN'])+'|\n'
 text+='''
Mar24第12小时六变量平均层RMSE均由log较低，Jan4均为Direct较低；这不是总体排名。Mar24 TN与Z的首末误差倍率较大，Flow Z约14.24倍、TN约11.63倍；History TN约11.78倍。风场存在多次下降，不预设单调或用不同单位误差相加判断最敏感变量。完整RMSE/ACC/偏差/极值/增长与持续性逐时逐层CSV保留。

## 实际驱动与日期条件

作者Mar24 00—13 Kp7.15上升至04时7.8833后下降到13时2.5833，F107152.644→156.791，F107A157.894→157.579；Jan4 Kp3.30—4.633并非安静。原逐时NPZ驱动不变，未用GFZ替换。两窗口同UT但季节/初态/前期演化/太阳与地磁条件不同；Mar24末时效near误差约Jan4的2.15—2.82倍是条件比较，不能称磁暴造成若干倍误差，不能由峰值时刻估计因果时延。

## 成本与产物索引

'''+perf+'''
新Mar24监督约39.97秒/峰RSS1.39GiB，Jan4历史39.44秒/1.39GiB，均含启动与I/O/审计；网络forward合计和loop不能相互代替。纯网络事件每组约0.21—0.35秒，冷首forward不能用作吞吐排名。离线场生成、在线查询、AI推理、轨道集成成本分别评价，未与TIE全仿真做直接加速倍数推断。

results/metrics/fourcastden_twelve_hour_mar24_v1_保留本次8类原生/公共CSV；two_window_前缀保留两窗windows/summary/growth/polar/performance/drivers。results/figures同前缀：两窗high_DEN、absolute_DEN、fixed_upper、6_vs_12、growth_absolute_and_ratio、polar、variables、performance；另有Mar24单窗8图。全部真实结果，Jan4不重跑，大预测数组本地。

## 研究决策

支持继续研究多步训练、分层/相对密度损失及History训练协议核查，尚未证明改进有效或确定最佳层权重。2023不参与调参，后续训练使用2000—2021和2022独立验证；需作者完整入口/配置/样本清单/统计与采样/学习曲线证据。训练实施优先级见FOURCASTDEN_TRAINING_IMPLEMENTATION_PLAN.md。

24h具有检验漂移/正性/更长误差积累的价值，但这两窗12h不保证24h稳定；建议先取得合法训练/验证小样本和原协议，同时将同两窗四模型24h作为另授权研究。不能挑当前优胜模型或日期，也不能自动执行。需补14—次日01每窗12帧、核网络/存储/显存预算、完整24步毒化和前12h一致性门禁、无中途真值重置。

本次证明的是代码与数值流程、对TIE-GCM参考场的条件预测；独立真实大气密度和最终轨道精度仍未验证。AI输出Z非ZG、外部高度/时间插值/未来条件现实可得性、Swarm真实Cd/面积/姿态/推力和共同力模型/独立观测等仍阻碍第三阶段正式验证。完成后停止，不自动24h、训练或轨道。
'''
 write('reports/FOURCASTDEN_TWELVE_HOUR_TWO_WINDOW_COMPARISON.md',text)
 print('Actual-evidence Mar24 validation and two-window reports written')
if __name__=='__main__':main()
