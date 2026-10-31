"""Render research reports directly from immutable result tables."""
from pathlib import Path
import csv,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
import run_fourcastden_ideal_update_6h as run
F,O,D=run.F,run.O,run.D


def read(name):
    with (O/name).open() as f:return list(csv.DictReader(f))
def write(path,text):
    path.resolve().relative_to(ROOT)
    with path.open('x') as f:f.write(text)


def main():
    end=read('DEN_12h_key_results.csv');pairs=read('paired_changes.csv');jumps=read('jump_at_update.csv');cost=read('standalone_reset_processing_cost.csv')
    rt=json.loads((F/'runtime.json').read_text());supervision=json.loads((F/'supervision.json').read_text());audit=json.loads((O/'delivery_audit.json').read_text());analysis=json.loads((O/'analysis.json').read_text());protocol=json.loads((F/'protocol.json').read_text())
    def row(day,model,group):return next(x for x in end if x['date']==day and x['model']==model and x['group']==group)
    high=['|日期|模型|Open +12h 相对RMS %|更新后 +6h 相对RMS %|相对下降 %|','|---|---|---:|---:|---:|']
    absolute=['|日期|模型|原全层平均RMSE kg/m³|更新后 kg/m³|相对下降 %|','|---|---|---:|---:|---:|']
    extreme=['|日期|模型|固定上层20—28：原→更新 %|顶部：原→更新 %|','|---|---|---:|---:|']
    compact=[]
    for day in run.DATES:
        for model in run.MODELS:
            x=row(day,model,'near400_500');a=row(day,model,'all');u=row(day,model,'upper20_28');t=row(day,model,'top')
            high.append(f"|{day}|{model}|{100*float(x['open_mean_layer_relative_RMS']):.6f}|{100*float(x['updated_mean_layer_relative_RMS']):.6f}|{float(x['improvement_pct_mean_layer_relative_RMS']):.2f}|")
            absolute.append(f"|{day}|{model}|{float(a['open_mean_layer_RMSE']):.8e}|{float(a['updated_mean_layer_RMSE']):.8e}|{float(a['improvement_pct_mean_layer_RMSE']):.2f}|")
            extreme.append(f"|{day}|{model}|{100*float(u['open_mean_layer_relative_RMS']):.3f}→{100*float(u['updated_mean_layer_relative_RMS']):.3f}|{100*float(t['open_mean_layer_relative_RMS']):.3f}→{100*float(t['updated_mean_layer_relative_RMS']):.3f}|")
            c=dict(date=day,model=model,UTC=day+'T13:00:00Z',all_pressure_points=True)
            for key in ('RMSE','mean_layer_RMSE','MAE','max_abs','relative_RMS','mean_layer_relative_RMS','relative_P95','log_RMS'):
                for prefix in ('open_','updated_','improvement_pct_'):c[prefix+key]=a[prefix+key]
            compact.append(c)
    run.csvout(O/'DEN_13UTC_all_metrics.csv',compact)
    jump_table=['|日期|模型|07时DEN相对跳变RMS %|TN跳变RMS K|水平风矢量跳变RMS m/s|Z跳变RMS m|','|---|---|---:|---:|---:|---:|']
    for day in run.DATES:
        for model in run.MODELS:
            z={x['variable']:x for x in jumps if x['date']==day and x['model']==model and x['region']=='global' and x['state_role']=='current07'}
            jump_table.append(f"|{day}|{model}|{100*float(z['DEN']['DEN_jump_relative_RMS_reference_denominator']):.3f}|{float(z['TN']['actual_update_RMSE']):.3f}|{np.hypot(float(z['UN']['actual_update_RMSE']),float(z['VN']['actual_update_RMSE'])):.3f}|{float(z['Z']['actual_update_RMSE']):.1f}|")
    load=sum(x['model_load_s'] for x in rt['records']);network=sum(x['network_GPU_total_ms'] for x in rt['records'])/1000
    prep=sum(x['read_preprocess_s'] for x in rt['records']);save=sum(x['save_s'] for x in rt['records']);allocated=max(x['peak_allocated_bytes'] for x in rt['records'])/2**30;reserved=max(x['peak_reserved_bytes'] for x in rt['records'])/2**30
    high_text='\n'.join(high)
    absolute_text='\n'.join(absolute)
    extreme_text='\n'.join(extreme)
    jump_table_text='\n'.join(jump_table)
    report=f'''# FourCastDEN第6小时理想全状态更新：两日期四模型实际对照

日期：2026-10-31。标签：`{run.TAG}`。

**OFFLINE_IDEAL_TIEGCM_FULL_STATE_UPDATE / HINDCAST / TIEGCM_REFERENCE_ONLY / NO_TRAINING。**本轮不是观测同化，不代表真实未来全球状态可获得，不进行轨道积分。

## 1. 结论

8个新序列、48次实际网络forward均完成；没有额外GPU预检、Open-loop重跑、训练、TIE-GCM或轨道积分。两个日期四模型的全球DEN误差均改善，但局地误差、更新跳变和热力诊断约束不一定改善。

- 13时参考400—500km相关原生层组：Jan4相对RMS下降54.37%—84.92%；Mar24下降65.38%—70.70%。
- 08—13时，六变量的全球全层平均RMSE在全部48个模型—目标时间配对中均降低；这不代表每个层或区域均改善。
- Mar24 13时Flow南高纬相关层组相对RMS增加4.96%，顶部相对RMS增加17.25%、P95增加55.33%；Direct北高纬UN平均层RMSE增加37.79%。不利结果全部保留。
- Mar24后六小时Flow无效原生高度重建列—时刻数反而从26增加到337，Direct 0→7、History 0→1、LogDEN 0→0。DEN误差更小不等于多场热力一致性更好。
- 07时硬更新有明确状态跳变；不能把更新状态本身的近零误差当作预测改善。不能据这两个窗口证明6小时是最佳业务更新周期。

## 2. 固定问题、数据与公平控制

Open：复用2023-01-04和2023-03-24原01→13连续12步预测，路径`data/processed/fourcastden_twelve_hour_{{jan4,mar24}}_v1/`。每个NPZ含13状态、模型对应means/stds、实际输入/标量和原网络输出。原作者参考小时NPZ来自两原实验的`data_view`，无新下载。

Updated：01—07的原预测历史保留，07时用对应真实TIE-GCM全状态初始化，实际新算08—13六步。History在07更新时额外获得06/07两个参考状态，其他模型只获07状态；History对06的纠正是模型历史记忆，不追溯修改06时已发布预测场。该信息量差异不是纯网络开关消融。

AFNONet、四套官方checkpoint、相应普通/static_log统计、网格与171通道顺序不变。checkpoint严格加载沿用作者默认strict=True，没有strict=False。普通模型177输入，History两个177块旧→新共354，输出均171、FP32，TF32关闭。所有构建/权重/统计/原数据SHA在`protected.json`与`code_frozen.json`记录。

未来08—13真实物理目标只评价；目标时刻LBC、太阳/磁坐标和4标量按作者原HINDCAST协议给定。实际网络hooks逐步核对输入物理状态来自07真实初态或前一步预测、History第三步起两状态均为预测、Flow累加归一化增量、LogDEN使用匹配log10统计。只读毒化未来物理目标后，实际输入的反馈核验仍通过，没有为此追加模型forward。

## 3. Baseline复核门禁

仅CPU读取原文件，独立einsum/cos纬度权重复算576条六变量RMSE和96条DEN窗口记录（每条含多个指标），与原CSV在冻结容差内一致。13个状态逐一对应01—13 UTC；174物理/LBC归一化通道与原full_data逐元素相同，旧12步反馈也重新核对。

容差：NumPy CSV相对2e-10，DEN绝对1e-25 SI、其他变量1e-8 SI；相对量绝对1e-15。基线耗时{protocol['baseline_wall_s']:.3f}秒，通过后才启动GPU。原baseline CSV、NPZ和模型未修改。

结果：`baseline_frozen_variables.csv`、`baseline_frozen_density.csv`。最终另独立解码、逐层点积计算{audit['independent_scalar_metrics']}个DEN标量指标，比对1536个方案/时刻/区域/层组记录；所有核验通过。

## 4. 指标定义和统计单位

TN K；UN/VN/WN从cm/s乘0.01到m/s；Z从cm乘0.01到m且仍为位势高度；DEN从g/cm³乘1000到kg/m³。LogDEN先标准化反变换，再10的幂还原，不使用exp替代。

加权整体RMSE为`sqrt(sum(w*error²)/sum(w))`，MAE同样cos纬度加权；同时保存“逐层加权RMSE的算术平均”，后者用于复现原报告，不能把两者混称。DEN相对RMS也同时保存整体RMS和原协议逐层RMS均值。P95为全选定点绝对相对误差的不加权95分位；最大绝对误差保留SI单位。参考DEN必须严格为正，使用原值作分母，无新分母floor。风场/高度不对近零值强行计算相对误差。

DEN组：全部0—28、按每个目标参考ZG全球中位高度400—500km选取的原生组、固定20—28、顶部28。原生层组不是固定450km高度。TN/UN/VN位于28个lev，WN/Z/DEN位于29个ilev；六变量另给全部有效层与逐层数据，不把lev索引强当ilev高度。

区域：全球、南高纬lat≤−60°、北高纬lat≥60°、中低纬|lat|<60°，严格沿用原±60°划分。格点/层/指标数量不是独立实验样本量；本次只有两个预选日期，不能宣称全年或显著性结论。

主评价保持全部有效压力域，不因原生高度重建失败删格点；另在Open/Updated共同高度有效列上做同mask配对，保留无效率及被排除数量。两种域必须分开阅读。

## 5. 13时DEN定量结果

### 参考400—500km相关原生层组

{high_text}

对比的是相同UTC13时：Open距01初态12小时，Updated距07理想状态6小时。这是有意引入额外真值信息的对照，不是信息量相同的架构比赛。

### 全层平均绝对RMSE（沿用旧报告的逐层均值）

{absolute_text}

完整整体RMSE、MAE、相对RMS、P95及最大绝对误差：`DEN_13UTC_all_metrics.csv`。各08、09、10、11、12、13时完整配对在`paired_changes.csv`，不只报告终点。

### 固定上层与顶部

{extreme_text}

Mar24顶部改善约31%—41%，明显小于相关400—500km层组约65%—71%；因此不能用一个整体百分比代表所有层。

## 6. 局地恶化与其他变量

全球六变量平均层RMSE在48个后更新模型—目标配对中均改善，但区域/层组并非全通过。聚合记录中，21条平均层绝对RMSE、6条平均层相对RMS、13条相对P95变差；这些指标可能对应同一事件，不能相加成独立样本。全部见`adverse_aggregate_cases.csv`，不是择优筛选。

Mar24 13时具体反例：

- Flow南高纬相关400—500km组：相对RMS 2.7000%→2.8338%，恶化4.96%；绝对平均层RMSE 7.06390e-14→7.81677e-14 kg/m³，恶化10.66%。
- Flow南高纬顶部：相对RMS 7.6086%→8.9208%，P95 14.7111%→22.8513%，后者恶化55.33%。
- Direct北高纬UN：平均层RMSE 42.0851→57.9878 m/s，恶化37.79%。

不同单位变量分别比较，没有把温度/风/高度RMSE相加。`metrics.csv`给全部变量/区域/时刻；`layer_metrics.csv`含125856条逐层记录。原CSV保留本地，公开压缩副本`layer_metrics.csv.xz`（{audit['published_xz_bytes']}字节）可无损恢复，SHA完全一致。

## 7. 07时状态跳变

{jump_table_text}

跳变是同一UTC07的“更新后状态减更新前预测”，不是一小时物理演化。DEN相对跳变用07参考DEN作分母；表中水平风是同单位UN/VN矢量RMS，Z仍是位势高度，不称几何高度跳变。History另记录06历史记忆的纠正，见`jump_at_update.csv`。

07真实归一化状态与模型初始化逐元素相同；恢复到物理单位时可能有float32归一化往返残差，不能把它当新增预测能力。07记录全部排除后更新预测成绩，只独立绘制跳变。

## 8. 热力一致性：误差下降不等于约束改善

复用原`fourcastden_density.py`，不改4—32质量范围或任何阈值。Jan4两方案四模型无无效重建列。Mar2408—13的列—时刻累计为：

|模型|Open|Updated|
|---|---:|---:|
|Direct|0|7|
|Flow|26|337|
|LogDEN|0|0|
|History|0|1|

Open Flow全12小时仍为原29个失败列—时刻，和上轮一致；后六小时占26。Updated Flow在13时有75列失败，反推质量最大37.788；Open同期5列失败、最大33.532。它们是诊断反演约束失败，不是负密度或网络NaN。本次所有输出TN正、DEN正且有限，Z及重建ZG垂直单调；不能因此宣称完整物理一致。

原因目前只能有界解释：逐变量误差变小不保证TN/DEN/Z的联合代数关系更接近约束，界面质量到中点质量递推可能放大不相容；不能直接把37.788解释成真实大气分子质量。具体机制待独立验证，没有裁剪、补真值或更改诊断公式。

数据：`physical_consistency.csv`、`paired_height_coverage.csv`，以及`metrics.csv`中`common_height_valid`域。主压力域仍完整保留，不通过删列美化结果。

## 9. 资源与额外成本

预检A100-SXM4-80GB、空闲约79GiB且无其他计算进程；磁盘约641GiB可用、CPU MemAvailable远大于4GiB。依据旧48forward约30秒及数据压缩成本，保守预计120秒，冻结GPU阶段600秒、RAM4GiB、allocated显存4GiB、新文件800MiB、余盘20GiB。

实际8×6=48次attempted/effective forward，额外预检0、重试0。模型只加载4次，第二日期复用。监督总墙钟{supervision['wall_s']:.3f}秒，worker内部{rt['GPU_phase_wall_s']:.3f}秒（前者另含校验/启动）；峰值进程树RSS{supervision['peak_tree_RSS_bytes']/2**30:.3f}GiB。推理CUDA allocated峰值{allocated:.3f}GiB、reserved峰值{reserved:.3f}GiB，均在限制内。

分项：权重加载合计{load:.3f}秒；全部48次GPU事件合计{network:.3f}秒；初次逐序列读取/预处理合计{prep:.3f}秒；输出压缩保存合计{save:.3f}秒。首次Direct forward含冷启动，不能按此给四模型稳健速度排名。GPU事件时间不等于完整推理墙钟。

单独CPU检查仅获取重置所需1帧或History2帧，缓存文件读取/预处理约{min(float(x['cached_local_read_preprocess_s']) for x in cost):.4f}—{max(float(x['cached_local_read_preprocess_s']) for x in cost):.4f}秒/次；状态复制另计。这是“未来参考状态已在本地”的开销。真实生成/获取未来全球全状态成本为NOT_MEASURED，不假设为0，不计算业务端到端加速比。

`performance.csv`中reset_state_extraction_s是整个初次get_data读取的上界/重叠计时，不能与read_preprocess重复加和；更窄的重置帧成本见`standalone_reset_processing_cost.csv`。循环时长还含未来条件读取、作者指标、同步与hooks，不与纯forward混淆。离线评价{analysis['evaluation_wall_s']:.3f}秒，另有绘图及独立审查。

## 10. 验收与完整性

|门禁|判定|证据|
|---|---|---|
|BASELINE_REPRODUCTION_READY|PASS|576变量/96密度窗口、真实UTC/归一化/旧反馈复核|
|IDEAL_UPDATE_INFERENCE_READY|PASS|8序列48forward、逐步hooks、History双真实历史及未来真值毒化|
|POST_UPDATE_EVALUATION_READY|PASS|9568聚合指标、125856逐层、2496配对；10752标量独立复核|
|PHYSICAL_CONSISTENCY_EVALUATED|PASS，表示检查已完成|明确保留失败列，不表示所有模型物理一致|
|STATE_UPDATE_CONCLUSION_READY|PASS，有界两窗口诊断|同时报告改善、局地恶化与跳变|
|SCIENTIFIC_TRAINING_READY|FAIL/False保持|原122帧候选科学质量门禁未解除，未做科学训练|

70项本任务数据/模型资产、2346项历史科学资产SHA保持一致；GPU关键源码在启动前冻结。旧权重、第三方源码、Open-loop数组、旧CSV/图和122候选均未覆盖。

独立审查末尾首次JSON输出因哈希变量名被覆盖而报错，原脚本/日志已保存。科学指标核验CSV和CPU重置成本当时已完成；仅修复审计记录输出并从已有检查表完成最终SHA/压缩复核，未重跑网络、未改变数据或容差。故障清单：`experiments/{run.TAG}/audit_serialization_incident.json`。

## 11. 局限与下一阶段

本轮只有两个日期、一种更新间隔和理想全状态。History多一帧参考信息；未来LBC/驱动已知；不能当成真实观测同化、全年统计、最终架构排名或最佳更新周期。2023仍用于预先指定诊断，不用其结果调损失/模型后再宣称独立测试。

优先补齐可实际取得的观测/更新状态、状态不确定性及物理约束验证；面向轨道应用，先完成外部高度/纬度登记和更新时间接缝处理，而非立即扩24小时。现有原生ZG重建仍是工程诊断，不代表独立真实几何高度准确度。

下一轮条件轨道设计：同一卫星初态、共同受力/气动，Open与Updated分别驱动12小时连续轨道。07时只更新大气，卫星位置速度不得用SP3重置。**必须保留07左极限和右极限两套大气状态，t<07查询Open、t≥07查询更新场**；不能把只有一个07新状态的小时数组在06—07插值，否则会把尚未发生的修正提前泄漏。积分器需在07事件处收步并携带同一卫星状态连续推进，再做事件前后数值收敛。外部坐标/参数门禁仍保留；本轮轨道积分0。

## 12. 三张最值得展示的图

1. `near_density_error_curves.png`：全部8模型—日期的完整误差曲线，展示累积与07更新后六小时效果，07重置成绩留空。
2. `regional_density_gain_13UTC.png`：全球改善与南高纬局地恶化同时可见，防止只看全局均值。
3. `thermodynamic_consistency.png`：Flow诊断失败列反而增加，说明精度与物理一致性必须分开验收。

补充：`model_effect_summary.png`、`six_variable_gain_13UTC.png`、`state_jump_07UTC.png`、`density_layer_profiles_13UTC.png`和8张13时三场全球图。16张PNG均可读；图表来源见`figure_sources.csv`。

## 13. 复现与停止边界

```bash
source scripts/activate_orbit.sh
python tests/test_fourcastden_ideal_update.py
python scripts/run_fourcastden_ideal_update_6h.py baseline
python scripts/run_fourcastden_ideal_update_6h.py supervise
python scripts/analyze_fourcastden_ideal_update_6h.py
python scripts/plot_fourcastden_ideal_update_6h.py
python scripts/audit_fourcastden_ideal_update_6h.py
python scripts/write_fourcastden_ideal_update_report.py
```

原标签已存在，正式基线/推理一旦启动即拒绝同标签重放；不要删除目录绕过。复现要在新独立标签中审查资源后执行。此次审计因已记录的序列化故障，仅以`audit_fourcastden_ideal_update_6h.py --finish`完成末尾记录，没有重跑48forward。只读查看关键表/报告不需任何GPU。

结果`results/{run.TAG}/`；原新预测`data/processed/{run.TAG}/`仅本地；协议、SHA和逐序列日志`experiments/{run.TAG}/`；控制台日志`logs/{run.TAG}_*.log`。组会稿：`docs/FOURCASTDEN_IDEAL_UPDATE_6H_TALK.md`。

完成后停止，不自动进行24小时预测、训练、TIE-GCM或轨道实验。
'''
    write(ROOT/'reports/FOURCASTDEN_IDEAL_UPDATE_6H_V1.md',report)
    speech='''# 三分钟中文组会汇报稿：六小时理想状态更新

李总，这一轮我们实际完成了一个问题的对照：AI连续预测十二小时，与第六小时获得一套完整参考大气状态、重新出发相比，误差能降低多少。

我们固定使用一月四日和三月二十四日，保留Direct、Flow、log-DEN、History四种官方模型。原十二小时结果完全复用，没有重跑。新增的部分只有早上七点初始化之后的六小时，共八个序列、四十八次网络计算。History额外用了六点和七点两帧参考，其他模型只用七点，这个信息量差异完整保留。

第一张图展示全部误差曲线。到十三点，参考高度中位数在四百到五百公里的原生压力层组，一月窗口四模型相对密度RMS下降约百分之五十四到八十五，三月窗口下降约百分之六十五到七十一。例如Direct在三月从百分之三点七六降到一点一零。七点直接输入真值后的成绩没有算作预测改善。

但是第二张区域图说明，全球改善不代表每个地方改善。三月Flow的南高纬顶部误差反而增大，P95从约百分之十四点七升到二十二点九；Direct北高纬的纬向风误差也变大。我们没有删除这些不利区域。

第三张图是这轮最需要注意的发现：Flow在更新后的六小时里，无效高度重建列时刻从二十六增加到三百三十七。温度和密度仍然有限且为正，但它们的联合热力关系不一定更一致。所以不能把误差下降直接等同于物理上更可靠。

更新还会制造跳变：三月全球密度相对跳变RMS约百分之四点六到五点零。这提示后续轨道实验必须在七点明确处理大气场切换，卫星本身的位置速度不能跟着真值重置，也不能把修正提前插值到六点到七点。

这次推理监督墙钟约四十八秒，但假设未来参考状态已经在本地。真实业务如何获得全球更新状态、需要多少时间，还没有解决。因此结论是：在这两个预选窗口，理想更新能明显抑制总体误差累积，但六小时还不能称最佳周期。这不是观测同化，也没有证明真实大气或卫星轨道精度。下一步应优先明确可获得的更新信息、物理一致性和坐标登记，而不是立即扩大到二十四小时。
'''
    write(ROOT/'docs/FOURCASTDEN_IDEAL_UPDATE_6H_TALK.md',speech)
    sources=[]
    for p in sorted(O.glob('*.png')):
        kind='raw-reference + saved old/new physical DEN, native index22' if p.name.endswith('_maps.png') else 'physical_consistency.csv' if p.stem=='thermodynamic_consistency' else 'jump_at_update.csv' if p.stem=='state_jump_07UTC' else 'layer_metrics.csv' if p.stem=='density_layer_profiles_13UTC' else 'metrics.csv + paired_changes.csv'
        sources.append(dict(figure=p.name,data_source=kind,source_code='scripts/plot_fourcastden_ideal_update_6h.py',source_code_SHA=run.sha(ROOT/'scripts/plot_fourcastden_ideal_update_6h.py'),dates='2023-01-04;2023-03-24' if not p.name.startswith('2023-') else p.name[:10],UTC='13' if '13UTC' in p.name or p.name.endswith('_maps.png') else '07 jump' if 'jump' in p.name else '02-13; reset07',reference='official author TIE-GCM NPZ; not observations',figure_SHA=run.sha(p)))
    run.csvout(O/'figure_sources.csv',sources)
    print('Report, 3-minute talk and figure source index written.')


if __name__=='__main__':main()
