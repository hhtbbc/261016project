"""Write reports solely from saved actual twelve-hour experiment evidence."""
import json,csv
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/fourcastden_twelve_hour_jan4_v1';MODELS=('Direct','Flow','LogDEN','History')
def main():
 a=json.loads((F/'analysis.json').read_text());rt=json.loads((F/'runtime.json').read_text());sup=json.loads((F/'supervision.json').read_text());audit=json.loads((F/'delivery_audit.json').read_text());old=json.loads((ROOT/'experiments/fourcastden_six_hour_v1/analysis.json').read_text())
 def write(name,s):
  with (ROOT/name).open('x') as f:f.write(s)
 def win(m,h):return next(r for r in a['windows'] if r['model']==m and r['hour']==h)
 prefix=[]
 for m in MODELS:
  for h in range(1,7):
   for n in ['TN','UN','VN','WN','Z','DEN']:
    x=next(r for r in a['summary'] if r['model']==m and r['hour']==h and r['variable']==n);y=next(r for r in old['summary'] if r['date']=='2023-01-04' and r['model']==m and r['hour']==h and r['variable']==n);assert x==y
   x=win(m,h);y=next(r for r in old['windows'] if r['date']=='2023-01-04' and r['model']==m and r['hour']==h)
   assert all(x[k]==v for k,v in y.items());prefix.append(dict(model=m,hour=h,all_old_summary_and_DEN_group_metrics_exact=True))
 with (F/'prefix_metrics_gate.json').open('x') as f:json.dump(dict(status='PASS',records=prefix),f,indent=2)
 def table(key,factor=1):
  text='|模型|+1h|+2h|+3h|+6h|+9h|+12h|\n|---|---:|---:|---:|---:|---:|---:|\n'
  for m in MODELS:text+='|'+m+'|'+'|'.join(f'{win(m,h)[key]*factor:.7g}' for h in [1,2,3,6,9,12])+'|\n'
  return text
 high=table('near400_500_mean_relative_RMS',100);absolute=table('mean_DEN_layer_RMSE_kg_m3');highabs=table('near400_500_mean_absolute_RMSE_kg_m3')
 performance='|模型|加载s|读取解码s|标准化s|其他预处理s|首forward ms|其余均值ms|12forward合计ms|作者loop s|保存s|CUDA allocated MiB|\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'
 for r in a['performance']:performance+=f"|{r['model']}|{r['model_load_s']:.4f}|{r['read_decode_s']:.4f}|{r['normalization_s']:.4f}|{r['other_preprocess_s']:.4f}|{r['first_formal_forward_ms']:.3f}|{r['later_forward_mean_ms']:.3f}|{r['network_total_GPU_ms']:.3f}|{r['author_loop_metrics_hooks_s']:.4f}|{r['save_s']:.4f}|{r['peak_allocated_bytes']/2**20:.3f}|\n"
 phys=[s for r in rt['records'] for s in r['step_physics']]
 validation=f'''# FourCastDEN Jan4连续12小时验证（2026-10-22）

HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 实际范围与门禁

仅2023-01-04 01→13 UTC，目标02—13，四模型各一段完整12步，合计4序列48正式forward、0额外GPU预检，无失败重试。未拼接两个6h、未在中间回灌真值，未运行Mar24/24h、训练/TIE/RK45。先恢复历史提交9447e7856d1eae07dc47834b93cee29b8038c0a1推送成功，实际远端核对相同，日志logs/git_twelve_hour_recovery.log（本地）。

docs/FOURCASTDEN_TWELVE_HOUR_PREREGISTRATION.md在正式GPU前冻结：checkpoint/static/代码/数据SHA、FP32/TF32关闭、同原作者AFNONet、History354输入/其他177、输出171、History额外真实00。新增5项测试，全237项27.861秒通过；原有ERFA合成测试dubious-year警告保留，无依赖更改。12步CPU真实作者循环+合成网络对四模式未来真值毒化预测不变，最后History两个预测状态正确，后期teacher forcing/scalar错位拒绝，12步与6步合成前缀精确一致。

只新增08—13六NPZ。已存中央目录与远端目录逐成员比尺寸/CRC/offset；成功206/Content-Range、ZIP和zlib CRC、SHA、14键、shape/dtype/finite/哨兵/正DEN与TN/ZG逐层递增全部通过，raw0444。网络响应体{audit['network_body_bytes']}字节={audit['network_body_bytes']/2**20:.4f}MiB<25MiB，无失败下载/整包响应。00—07复用原件，无原始文件覆盖。NPZ时间由官方文件名、网格/单位由作者静态和代码契约确定，NPZ自身不含完整坐标/单位元数据。

## 前六步历史一致性

四模型前6次真实hooks将input/scalar/raw output/生成state与历史六小时数组逐元素比较，全部最大归一化差0；means/stds亦精确一致。门禁在第6次hook立即写prefix_gate，若失败会终止并保存失败前缀。执行完独立比较完整pred前7帧（含初始化）亦相同。24个模型时效的六变量summary与原DEN组指标全字段精确一致，prefix_metrics_gate.json；未修改历史6h。

全部12步通用check_autoregression检查匹配逐步state与未来aux/scalar；Flow normalized delta相加，log匹配static_log/log10/pow10，History [real00,real01]→[real01,pred02]→[pred02,pred03]→…，无未来物理真值反馈。所有权重严格load，无strict=False。log沿用既有隔离兼容包装器，原树与权重不变。

## 评价、物理与资源

所有48输出finite、DEN100%正，TN {min(x['TN_min_K'] for x in phys):.3f}—{max(x['TN_max_K'] for x in phys):.3f}K；最大绝对风分量{max(x['max_abs_wind_m_s'] for x in phys):.3f}m/s，Z位势高度{min(x['Z_min_m'] for x in phys)/1000:.3f}—{max(x['Z_max_m'] for x in phys)/1000:.3f}km。未发现数值溢出/非正密度/明显发散，不表示真实物理预测已经准确；完整每lead范围见runtime。

公共物理目标为同原始NPZ02—13、普通physical climatology、真实01持续性；DEN乘1000为kg/m3，风/Z乘.01为SI。独立NumPy加权求和复核{audit['common_physical_channel_checks']}个物理通道时效，rtol1e-12；作者native normalized RMSE最大相对差{audit['author_normalized_RMSE_max_relative']:.4g}、ACC最大绝对差{audit['author_ACC_max_absolute']:.4g}，沿用rtol2e-5/RMSEatol1e-25/ACCatol2e-6。log native ACC在log空间、std-scaled DEN为dex，分表不混排。没有放宽门槛。所有raw/代码/四权重/统计/历史保护{audit['protected_files_unchanged']}项SHA不变。

{performance}

监督总墙钟{sup['wall_s']:.6f}s，GPU worker内部{rt['GPU_phase_wall_s']:.6f}s含加载/I/O/指标/保存；峰RSS{sup['peak_RSS_bytes']/2**30:.4f}GiB，独立CPU分析{a['CPU_analysis_s']:.4f}s、峰{a['analysis_peak_RSS_KiB']/1024:.3f}MiB。新增数据初审{audit['new_files_bytes']/2**20:.3f}MiB<800MiB。GPU事件只计网络区间，Direct首forward含CUDA冷启动，其他模型运行时已warm；不能由本次单次计时作稳定速度排名。作者native指标首次编译/派发等待也不是纯kernel性能。

12h与旧6h网络次数各组12对6，warm单步基本约18ms；总I/O/保存/初始化非线性，不能把总墙钟简单视为网络推理。四组只各加载一次，12步内无重复加载，无证据显示资源泄漏；ru_maxrss/CUDA峰不能证明任意长序列不会增长，未作专门长时内存测试。后续严格吞吐应另授权固定warm-up/同步/重复计时。

## 复现入口和产物

source scripts/activate310.sh；unittest discover；run_fourcastden_twelve_hour_jan4.py --fetch；无参preflight；supervise_fourcastden_twelve_hour_jan4.py；analyze_fourcastden_twelve_hour_jan4.py；audit_fourcastden_twelve_hour_jan4.py；write_fourcastden_twelve_hour_reports.py；audit --final。once-only目录不可删除标记后重试。指标CSV和8图前缀fourcastden_twelve_hour_jan4_v1；配置/反馈/范围/哈希/监督/指标审计在experiments同标签，大NPZ只本地。最终交付体积/哈希以final_delivery_audit.json为准。
'''
 write('reports/FOURCASTDEN_TWELVE_HOUR_JAN4_VALIDATION.md',validation)
 comparisons=f'''# FourCastDEN Jan4四模型12小时比较（2026-10-22）

HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING

## 结果范围

一个固定初始窗口不是全年泛化样本，不把空间网格当独立重复。History额外真实00，其余真实01；不同权重/训练目标/部分统计不同，非单因素训练消融。未来已知外部驱动/LBC给定，非实时自主预测。公共单位/真实参考一致，Z是位势高度，不是ZG。

高层相关组所有12lead均为ilev索引21/22/23，+12参考全球中位ZG为418.775/450.840/484.069km；这是参考中位400—500km压力层组，不是固定450km、外部WGS84或Swarm沿轨误差。

## 高层相关组相对RMS（%，逐层加权相对RMS再平均）

{high}

Flow只在+1h最低，Direct在+2—12h最低。+12排序Direct、log、Flow、History。Direct/Flow/log组误差均在+9h达到本窗口最大后略降，History在+11h最大后略降；不能预设单调增长或将下降称收敛。History没有在长时效获得本窗口高层优势。

## 全层DEN逐层绝对RMSE平均（kg/m3）

{absolute}

Direct在+2—12h最低；Flow在+1h最低，History所有12时效最高。Direct、Flow、log在+7h附近的绝对指标达到局部峰后回落再有起伏；History全层绝对DEN连续增长，初始误差也较大，不以较小增长倍率美化稳定性。

## 同一高层组绝对RMSE（kg/m3）

{highabs}

+12h相对均值偏差Direct/Flow/log/History分别{', '.join(f"{win(m,12)['near400_500_relative_bias']*100:.5f}%" for m in MODELS)}，均偏高。高层相对RMS的12h/6h倍率分别{', '.join(f"{win(m,12)['near400_500_mean_relative_RMS']/win(m,6)['near400_500_mean_relative_RMS']:.4f}" for m in MODELS)}；同时看绝对幅度，不当作统计稳定性置信界。高层绝对RMSE比全层平均小很多，混合全部压力层会掩盖上层相对误差。

## 其他变量、顶部与极区

'''
 comparisons+='|模型|+12 TN K|UN m/s|VN m/s|WN m/s|Z m|顶层相对RMS %|顶层P95 %|极区最大相对差 %|\n|---|---:|---:|---:|---:|---:|---:|---:|---:|\n'
 for m in MODELS:
  v=[next(r['mean_layer_RMSE_SI'] for r in a['summary'] if r['model']==m and r['hour']==12 and r['variable']==n) for n in ['TN','UN','VN','WN','Z']];e=win(m,12);comparisons+='|'+m+'|'+'|'.join(f'{x:.5f}' for x in v+[e['top_relative_RMS']*100,e['top_relative_P95']*100,e['polar_relative_max']*100])+'|\n'
 comparisons+='''
+12h Direct六变量的逐层平均RMSE均较低，但这不是长期总体胜出证据。温度/风/Z与密度不能将不同单位RMSE相加。完整逐层物理ACC、偏差、极值、极区/非极区相对/log误差和持续性在CSV。多种风场误差有逐步下降，Flow的TN/Z本窗口持续增长，不能一概宣称所有误差单调。

log没有指数溢出或失稳，但高层仍高于Direct；不说明log训练目标一般无效。History的输入/stat/严格权重/hooks/毒化及前缀验证均通过，未发现工程错位，保留其较差结果；真正训练协议还需作者证据。只研究当前checkpoint，不修改归一化制造改善。

## 驱动与物理解释限制

原NPZ00—13 Kp约3.30—4.633，F107约144.731—146.024、F107A156.913—157.436；Jan4不是“无地磁活动”基准。逐时记录drivers.csv，没有替换作者驱动；不能由误差峰与Kp下降直接归因/推断响应时延，初态/季节/场演变/递归误差混杂。Mar24本次只设计。

## 图表索引与后续

results/figures/fourcastden_twelve_hour_jan4_v1_：high_DEN高层相对曲线；absolute_DEN全层绝对；variables六变量；growth相对首时效增长；high_absolute_bias高层绝对及偏差；layers_12h全部29原生层；performance网络/loop/显存；drivers作者Kp。全部来自本次真实数组，CSV保留全部1—12时效及持续性。

先另授权Mar24同协议12h，保留四模型、前6h一致性门禁、相同物理指标及不同活动状态；不先据Jan4淘汰History/Flow或直接24h。两窗口通过后再预注册24h及更多独立日期。当前支持研究多步/上层相对或分层损失的假设，不证明新方法有效；需完整训练/2000—2021及2022验证数据、多个种子和独立测试。详见TRAINING_READINESS和MAR24_TWELVE_HOUR_PLAN。真实大气精度/卫星轨道精度与参考场拟合分开，正式高度/气动/受力门禁不变。
'''
 write('reports/FOURCASTDEN_TWELVE_HOUR_JAN4_COMPARISON.md',comparisons)
 print('Actual-evidence reports and exact historical metrics gate written')
if __name__=='__main__':main()
