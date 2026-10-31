"""Report rendered from immutable observation comparison tables."""
from pathlib import Path
import csv,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import prepare_fourcastden_swarm_observation_v1 as task
from analyze_fourcastden_swarm_observation_v1 import table
F,O,D=task.F,task.O,task.D


def read(name):return list(csv.DictReader((O/name).open()))
def write(p,s):
    with task.inside(p).open('x') as f:f.write(s)


def main():
    pairs=[r for r in read('paired_update_changes.csv') if r['domain']=='common_AB_all_models' and r['region']=='global' and r['mapping'] in ('A','B')]
    metrics=read('metrics.csv');downloads=json.loads((F/'download_manifest.json').read_text());points=json.loads((F/'HAPI_CDF_point_registration.json').read_text())
    download=json.loads((F/'download_completed.json').read_text());analysis=json.loads((F/'analysis_completed.json').read_text());ind=json.loads((F/'independent_validation.json').read_text())
    obsbytes=download['raw_observation_bytes']+sum(x['request']['bytes'] for x in points)
    task.dump(F/'transfer_totals.json',dict(raw_ZIP_bytes=download['raw_observation_bytes'],HAPI_observation_point_bytes=sum(x['request']['bytes'] for x in points),
        total_new_observation_bytes=obsbytes,metadata_bytes=download['metadata_bytes'],total_network_payload_bytes=obsbytes+download['metadata_bytes'],limit_observation_bytes=10*2**20))
    main=['|日期|假设|模型|共同N|Open相对RMS %|更新后 %|相对RMS降低 %|RMSE降低 %|','|---|---|---|---:|---:|---:|---:|---:|']
    absolute=['|日期|假设|模型|Open RMSE|更新后RMSE|更新后MAE|更新后偏差|更新后相对P95 %|','|---|---|---|---:|---:|---:|---:|---:|']
    for r in pairs:
        main.append(f"|{r['date']}|{r['mapping']}|{r['model']}|{r['n']}|{100*float(r['open_relative_RMS']):.4f}|{100*float(r['updated_relative_RMS']):.4f}|{float(r['relative_RMS_reduction_pct']):.2f}|{float(r['RMSE_reduction_pct']):.2f}|")
        row=next(x for x in metrics if x['date']==r['date'] and x['mapping']==r['mapping'] and x['model']==r['model'] and x['scheme']=='Updated' and x['period']=='post' and x['region']=='global' and x['domain']=='common_AB_all_models')
        absolute.append(f"|{r['date']}|{r['mapping']}|{r['model']}|{float(r['open_RMSE'])*1e13:.4f}|{float(r['updated_RMSE'])*1e13:.4f}|{float(row['MAE'])*1e13:.4f}|{float(row['bias'])*1e13:.4f}|{float(row['relative_P95'])*100:.3f}|")
    main_text='\n'.join(main);abs_text='\n'.join(absolute)
    refs=['|日期|假设|参考场RMSE kg/m³|参考场相对RMS %|偏差 kg/m³|','|---|---|---:|---:|---:|']
    for day in ('2023-01-04','2023-03-24'):
        for mp in ('A','B'):
            r=next(x for x in metrics if x['date']==day and x['mapping']==mp and x['model']=='Direct' and x['scheme']=='Reference' and x['period']=='post' and x['region']=='global' and x['domain']=='common_AB_all_models')
            refs.append(f"|{day}|{mp}|{float(r['RMSE']):.6e}|{float(r['relative_RMS'])*100:.4f}|{float(r['bias']):.6e}|")
    ref_text='\n'.join(refs)
    raw_text='\n'.join(f"- `{Path(x['path']).name}`，{x['bytes']}字节，SHA256 `{x['SHA256']}`。" for x in downloads)
    report=f'''# FourCastDEN与同期Swarm-A沿轨密度的有条件观测对照

日期：2026-10-31；标签：`fourcastden_swarm_observation_v1`。

**PROVISIONAL_OBSERVATION_COMPARISON / HINDCAST / DNSAPOD_0301 / NO_TRAINING。**正式外部坐标门禁仍为`EXTERNAL_DATUM_UNVERIFIED`；没有新网络forward、TIE-GCM或轨道积分。本次是真实同期密度产品的条件比较，不是绝对大气真值、观测同化或真实轨道精度验证。

## 1. 本轮主要发现

1. 实际取得2023-01-04和03-24两份Swarm-A DNSAPOD 0301日文件；各2880条UTC30秒记录，目标01—13时各1441条。两份官方ZIP共279730字节；另取每日期1个HAPI记录核对字段，所有观测负载共{obsbytes}字节，小于10MiB。
2. A假设下08—13时四模型整体相对RMS均改善：Jan4下降1.76%—9.30%；Mar24下降27.64%—39.80%。这些改善远不能当成全部大气误差消除。
3. **B假设改变结论**：Jan4 History相对RMS增加3.79%；Mar24四模型相对RMS分别增加15.94%、20.20%、22.03%、9.93%。不能从A/B中选更接近观测的方案后宣称独立验证。
4. 全球改善不代表各区域改善：A假设Mar24北高纬四模型相对RMS均恶化。07时重置还可能立即远离Swarm产品值。
5. Mar24 Updated Flow在08—13时18个沿轨时刻拒绝高度查询，保留原因；主表所有模型和两坐标假设共同只用相同583点，Jan4为601点。原始请求和每个模型自身覆盖另行保存，没有静默删点。

## 2. 数据取得、质量和来源

### 2.1 文件存在性与下载

先从[ESA公开分发服务](https://swarm-diss.eo.esa.int/)读取实际Sat_A目录清单，确认每个目标日期**具体文件**唯一0301候选及大小，再冻结清单/下载预算、流式下载。不是用HAPI年度首末范围代替目标存在性。

{raw_text}

官方清单不提供发布方SHA；这里SHA是本地溯源校验，不冒称与官方checksum匹配。下载长度与清单严格一致；ZIP两成员CRC、解压前后逐字节/成员SHA独立复核通过。未覆盖原03-21至23文件。

原件：`data/raw/fourcastden_swarm_observation_v1/`，含ZIP、CDF、HDR、目录JSON、HAPI元信息及点核查CSV。原始观测与逐点衍生表默认仅本地保留，不自动上传公开仓库。下载URL/大小/CRC/SHA完整保存在`experiments/.../download_manifest.json`，全CDF字段及属性在`CDF_contracts.json`。

### 2.2 质量及坐标实物核查

- 产品：`SW_OPER_DNSAPOD_2_`，版本0301，POD/GPS气动加速度反演的中性质量密度，不是加速度计直接测量密度。
- CDF明确TIME SYSTEM=UTC、CDF_EPOCH，两个日文件均严格30秒连续；不使用GPS偏移。SP3旧文件不参与时间/位置替代。
- 使用`density`瞬时反演值，kg/m³；`density_orbitmean`独立保留、未用于主指标或填补。
- [VirES官方HAPI信息](https://vires.services/hapi/info?id=SW_OPER_DNSAPOD_2_)实际HTTP200，明确flag **0=nominal，1=anomalous**。本版本只接收0，1按定义拒绝，其他码单独标未知并隔离，不能泛化为所有非零码均坏。另要求密度有限、正且不是FILLVAL。
- 两天各2880条、目标各1441条flag全部0，密度均正有限；故本次质量过滤未删点，但nominal不等于无反演误差。完整质量分布见`quality_audit.csv`。
- 官方服务声明GRS80地理坐标；本轮各取01时同一实际记录，逐值核对CDF的latitude/longitude/altitude/density/flag与HAPI对应字段一致。HAPI Height_GD描述文字把height误写为latitude，单位m；不据此改变原字段。采用其GRS80地理位置解释，并保留证据/限制。
- 先由GRS80大地坐标建立同一地固位置，再转WGS84；没有把源纬度/高度直接重标为已证明的模型坐标。

[官方Swarm服务示例](https://notebooks.vires.services/notebooks/03l1_demo-dns)支持产品类型与字段来源；[ESA使用条款](https://vires.services/data_terms)沿用上轮实际取得的PDF/SHA，不把公开下载等同CC0。POD密度依赖处理、气动和轨道模型；与SP3共享信息，不能当成彼此绝对独立的真值。具体再处理创建时间见原HDR，不能声称2023当时已实时可用。

## 3. 原预测复用与查询协议

两日期原01→13的四模型NPZ，以及07重新初始化后08→13的四模型NPZ，全部只读。按各自means/stds反归一化，LogDEN按log10还原；DEN g/cm³×1000→kg/m³。参考用同UTC作者NPZ中的DEN和原生ZG；AI用已有TN/DEN/Z及给定TLBC工程反演ZG，不用未来真实ZG补AI高度。

四种坐标方案在同一地固位置下预先冻结：

- A：WGS84大地纬度、椭球高近似模型地理纬度、原生ZG。
- B：地心纬度、地心距离减明确6371000m球半径。
- D：只将A纬度改为B纬度，保持A高度；E：只改高度，保持A纬度。

A/B都不是已证明的正确登记；D/E仅分离因素，不作为另择优映射。模型半径或calczg有效半径不被解释成WGS84零面。

复用原生查询的八列规则：两时间×四水平列，即使权重0也全部检查；纵向log密度插值、横向密度双线性、时间密度线性。时间仅在已有相邻小时内、经度周期；纬度/高度越界、DEN异常或重建高度无效明确拒绝，不补0、不裁边、不外推。

`EventAwareDensity`保留07左右帧，t<07只选Open截断分支，t≥07选Updated；更新前720个时刻，Open/Updated的查询数组含拒绝位置均逐元素一致。07左右极限另存，不跨缝插值、不把重置瞬间当成新预测改善。08—13主要预测窗口为601个时刻；07—08过渡窗口119点另报。

## 4. 统计范围与共同有效域

主指标单位kg/m³；每个实际30秒沿轨点等权，不使用全球格点cos纬度权重。相对误差分母为同一时刻正的**瞬时观测密度**，没有另设密度分母下限。RMSE/MAE/有符号偏差（模型−观测）/最大绝对差/相对RMS/绝对相对误差P95/自然log差分别保存。

主评价掩码：质量通过∩参考场∩四模型Open和Updated∩A和B均有效。同一日期、窗口和区域，所有主比较用相同观测样本ID。另报各模型Open/Updated/参考的自身三方共同样本，作为覆盖敏感性，不替代主集合。

|窗口|Jan4质量通过/共同N|Mar24质量通过/共同N|
|---|---:|---:|
|01≤UTC<07|720/720|720/720|
|07<UTC<08|119/119|119/114|
|08≤UTC≤13|601/601|601/583|
|全窗排除07事件点|1440/1440|1440/1417|

Mar24后窗18个拒绝来自Updated Flow的无效高度列，A/B均为97.005%有效；其他模型/参考在该后窗自身查询100%有效，但为公平主比较也使用583点。过渡段另拒绝5点；总计23个非事件沿轨时刻不在全模型共同集。不能把这些点悄悄消失，也不能把97%说成可连续驱动轨道的100%有效。

有96个细分统计单元无样本（例如Jan4过渡1小时未经过南高纬），明确N=0、指标为空，不填0、不按此认为误差为0。沿轨序列高度相关；只有两个日期，不以2882点当2882个独立科学实验，不给显著性或全年泛化结论。

## 5. 08—13时真实观测符合程度

正“降低”表示改善，负表示恶化。全表为同一共同样本集合，**不是全层TIE参考误差，也不是13时单点误差**。

{main_text}

绝对指标表：RMSE、MAE、偏差统一以 **1e-13 kg/m³** 表示；相对P95为百分数。Open/Updated完整七指标及最大误差见`metrics.csv`、`post_global_all_metrics.csv`。

{abs_text}

同一主集合上的TIE-GCM参考本身对Swarm也有残差：

{ref_text}

因此，AI向TIE参考更靠近，并不必然向Swarm产品更靠近。A下改善是有真实同期反演数据支撑的条件结果；B下翻转同样是实际计算结果。不能据哪种结果更好来判定A/B正确，更不能将这些差异全归于网络能力。

绝对RMSE和相对RMS也可能给出不同判断：Mar24 B的Direct绝对RMSE略降1.44%，相对RMS却增加15.94%；Flow亦类似。两者分别强调较大绝对密度误差和相对观测值的误差，不能只选有利指标。

## 6. 区域、时效与07事件

区域按WGS84纬度固定：南≤−60°、北≥60°、中低纬abs<60°。Mar24主后窗南/北/中低纬N分别78/92/413，Jan4为120/93/388，不是全球均匀空间抽样。

A假设下Mar24北高纬相对RMS在Direct/Flow/LogDEN/History分别**增加83.85%/58.40%/21.18%/14.23%**；中低纬则分别下降47.00%/47.39%/45.67%/54.45%。Jan4 A的History南高纬也小幅恶化0.73%。区域反例全部保留。不能以全球沿轨改善取代极区风险。

07时每个模型/映射均保留左右实际查询，不计入主预测提升。例如A/Direct：

- Jan4观测7.159915e-13，左8.192745e-13、右8.828720e-13kg/m³；相对观测差由+14.43%变为+23.31%。
- Mar24观测2.081099e-12，左1.636866e-12、右8.363171e-13kg/m³；相对差由−21.35%变为−59.81%。

重置到TIE全状态不是重置到真实大气。这个单点恶化不能替代后六小时总体评价，也不能被后六小时平均改善掩盖。更新后的高度表示还包含AI诊断重建，而参考查询采用原始ZG，故差异并非纯DEN单变量贡献。

`hourly_metrics.csv`按UTC小时起点分箱，13时只含端点1样本，图中特别注明；曲线没有拟合平滑。不能把该端点值当一小时平均或原全场+12h指标。

## 7. 同期轨迹的几何与插值敏感性预算

两窗真实轨迹WGS84高度分别464.768—493.937km、460.206—489.770km。A/B高度差约−14.202至+7.137km、纬度差约±0.179°。这是两个坐标定义的可计算差，不是未知原生ZG登记误差的上界。

固定相同参考密度场与沿轨位置，四映射共同有效样本各1441：

|条件响应绝对P95|Jan4|Mar24|
|---|---:|---:|
|仅纬度D/A|0.2458%|0.2206%|
|仅高度E/A|26.7339%|21.9687%|
|混合B/A|26.7124%|21.9821%|
|交互项(B−D−E+A)/A|0.0453%|0.0331%|
|参考高度+1km|1.8386%|1.5169%|
|参考高度−1km|1.8752%|1.5424%|
|时间log与线性密度插值差|0.0554%|0.4090%|
|水平log与线性密度插值差|0.1609%|0.1509%|
|垂直线性与log密度插值差|3.5116%|3.5621%|
|稀疏一倍垂直网格敏感性|0.9751%|1.4907%|

这些是不同条件/算法的数值敏感性，不是误差置信区间，不求和成“总误差”。原生ZG未知零面、Swarm反演不确定度、AI重建高度准确度、TIE物理误差和5°网格未解析结构仍未被本轮独立量化。

尤其Mar24局地水平/时间插值最大差可能远高于P95，完整最小/最大值保留于`interpolation_sensitivity_summary.csv`。没有因此按观测选择另一种插值方案；主查询继续冻结规则。高度、纬度和时间沿轨相互关联，随高度变化的散点只是条件趋势，不是单独高度的因果效应。

## 8. 真实卫星轨道准备状态

|条件|实际状态|
|---|---|
|同期DNS密度/时间/位置|取得并质量审查通过，但仍为POD反演、非全球171通道|
|同期SP3|旧官方缓存目录明确列出Jan4/Mar24的0201/0203候选；本地尚未下载同日期原件/核对头及t0 P/V|
|质量/面积/Cd/姿态/推力|旧正式参数门禁继续；本轮未取得两目标日配套资料，演示常数不可替代|
|ITRS/WGS84到原生ZG|仍EXTERNAL_DATUM_UNVERIFIED；A/B不放行为真实转换|
|连续沿轨查询|Jan4当前取样通过；Mar24 Flow更新后不是100%，拒绝需中止轨道或另立模型方案|
|共同动力学/积分基础|H6及事件组合有工程基础；没有执行本轮真实轨道/全窗收敛验证|
|实际轨道精度验证|BLOCKED；密度残差、虚拟模型间位移和SP3位置误差不得混称|

最小后续工作：优先确认外部高度/地理坐标的独立登记依据，并在同时间观测算子上验证；若准备真实传播，限定一个日期取得匹配SP3及质量/姿态/推进器/气动定义，冻结t0前参数与共同受力。不能用这批验证密度或未来SP3反拟合高度偏移、Cd或密度系数再报告独立改进。

尚不能用稀疏沿轨密度直接更新全球171通道；需要背景、观测算子、协方差/集合和时效协议。没有新证据证明6小时是最佳周期，不自动扩24小时或训练。原122帧候选科学训练门禁保持False。

## 9. 验证、资源与文件

8项新CPU测试通过：版本质量规则、未知标志隔离、无分母下限、独立指标、共同掩码和07事件排除。旧已通过事件测试未重跑。实际查询103752次（两窗×1441×四映射×九场），另有参考±1km灵敏度和07左右诊断，均为CPU密度查询，不是网络forward。

主分析{analysis['wall_s']:.3f}秒、RSS峰值{analysis['peak_RSS_MiB']:.3f}MiB；独立复核{ind['independent_wall_s']:.3f}秒、{ind['peak_RSS_MiB']:.3f}MiB。3072个统计单元独立复算，其中有样本的20832个标量指标通过；86项本轮输入和2346项旧科学资产SHA均不变。原始下载约4.03秒，其余绘图/排版单独执行，不冒称纯分析或模型耗时。

数据目录`results/fourcastden_swarm_observation_v1/`：

- 公开轻量：metrics、paired_update_changes、post_global_all_metrics、query_validity、quality_audit、common_sample_coverage、hourly_metrics、敏感性汇总与独立核验CSV。
- 本地逐点：`queries_local.csv`、两日`*_observations_local.csv`、`*_aligned_local.npz`、geometry/interpolation/event/sensitivity的local表；保留全部拒绝和样本ID，不自动发布观测原件或逐点重打包副本。
- 9张真实数据图：Swarm_TIEGCM_reference_density、four_models_alongtrack_A、observation_error_hourly_A_B、post_update_gain_A_B、regional_observation_update_gain、coordinate_sensitivity_same_track、query_validity_by_model、observation_event_seam、calculable_sensitivity_budget。

图片全部标注DNSAPOD0301/PROVISIONAL/HINDCAST。前两版排版中间图保留在实验目录，不替换历史科研数据；最终图与源CSV索引另存。推荐组会展示：**post_update_gain_A_B、four_models_alongtrack_A、regional_observation_update_gain**，突出观测证据、坐标敏感性与局地反例。

## 10. 命令与结束边界

```bash
source scripts/activate_orbit.sh
python tests/test_swarm_density_comparison.py
python scripts/prepare_fourcastden_swarm_observation_v1.py
python scripts/analyze_fourcastden_swarm_observation_v1.py
python scripts/finalize_fourcastden_swarm_observation_v1.py
python scripts/plot_fourcastden_swarm_observation_v1.py
python scripts/write_fourcastden_swarm_observation_report.py
```

该标签已有产物，正式步骤拒绝覆盖；不要删除目录重放。只读查看上述CSV/报告不需要网络或GPU。初始官方清单请求URL/响应SHA在`listing_request.json`；两条小HAPI核对请求在`HAPI_CDF_point_registration.json`，后续复现须先重新核算版本与预算而非自动复用最新文件名。

本轮完成后停止，无训练、长时轨道积分、更多预测或自动数据下载。阶段进度同步到STATUS/WORKLOG，Git只提交轻量代码/派生统计/图，原观测本地保存，实际提交与远端核验以最终同步记录为准。
'''
    write(ROOT/'reports/FOURCASTDEN_SWARM_OBSERVATION_COMPARISON_V1.md',report)
    talk='''# 三分钟组会汇报：FourCastDEN与同期Swarm密度对照

李总，这一轮我们把评价从TIE-GCM参考场推进到了同期Swarm-A沿轨密度产品。我们实际取得了2023年1月4日和3月24日的官方0301版数据，30秒采样，每个十二小时窗口有1441个点，质量标志均为名义有效。下载原件不到三百千字节，没有新增网络推理或轨道积分。

结果最值得强调的是：理想更新对真实密度产品的符合程度，受到高度映射假设的明显影响。采用A假设，也就是把WGS84纬度和椭球高近似对应模型坐标，两个日期四模型整体相对RMS都改善。比如Mar24 Direct从17.45%降到12.63%，History从17.99%降到10.83%。但这与过去相对TIE-GCM的百分数不是同一指标，不能直接混比。

换成预先规定的B假设，也就是地心纬度和减固定球半径的径向高度，Mar24四模型相对RMS反而全部变差，大约增加一成到两成。我们不能看到A更好，就说A已经被证明正确。这恰好说明外部高度登记是重要科学问题，而不是可以省略的接口细节。

即使在A假设下，Mar24北高纬四模型也都恶化，全球改善主要来自其他纬度。更新瞬间还有一个直观例子：七点把模型状态重置到TIE-GCM后，Direct在该Swarm位置的相对偏差从约负21%变成负60%。这个点不计入预测提升，但说明物理模拟参考不等于真实大气。

我们完整保留了失败查询。Mar24更新后的601个观测时刻中，Flow有18个高度列查询失败，因此所有模型和A、B主比较统一使用同样的583点，没有让不同模型悄悄用不同样本。密度观测本身也是依赖POD和气动处理的反演产品，不是无误差真值；这些沿轨点又高度相关，不能冒充大量独立实验。

现在可以说，我们已经取得真实同期观测支撑的、有条件的密度符合程度结果；但还不能宣称真实轨道预测精度已经验证。下一步应先解决高度坐标登记和观测算子的资格，再补同日期SP3及真实气动、姿态和推进器资料。之后才能在统一动力学条件下研究密度改善是否真正改善轨道。本轮没有训练或扩展仿真，原科学训练门禁保持不变。
'''
    write(ROOT/'docs/FOURCASTDEN_SWARM_OBSERVATION_TALK.md',talk)
    print('Actual-data report and Chinese talk written')


if __name__=='__main__':main()
