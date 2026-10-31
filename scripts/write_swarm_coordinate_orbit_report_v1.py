"""Generate an evidence-led report from actual files and cached residuals."""
from pathlib import Path
import csv,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from prepare_fourcastden_swarm_observation_v1 import dump,inside
from analyze_fourcastden_swarm_observation_v1 import table
F=ROOT/'experiments/swarm_coordinate_orbit_readiness_v1';O=ROOT/'results/swarm_coordinate_orbit_readiness_v1'


def main():
    budgets=list(csv.DictReader((O/'residual_budget.csv').open()));geom=list(csv.DictReader((O/'geometry_summary.csv').open()))
    products=json.loads((F/'SP3_product_contract.json').read_text());download=json.loads((F/'download_manifest.json').read_text());interp=json.loads((F/'interpolation_validation.json').read_text())
    summary=['|日期|三维差RMS m|三维差P95 m|三维差最大 m|高度差RMS m|高度差绝对P95 m|高度差最大 m|','|---|---:|---:|---:|---:|---:|---:|']
    for day in ('2023-01-04','2023-03-24'):
        a=next(r for r in geom if r['date']==day and r['metric']=='position_norm_m');h=next(r for r in geom if r['date']==day and r['metric']=='height_GRS80_m')
        summary.append(f"|{day}|{float(a['RMS']):.6f}|{float(a['abs_P95']):.6f}|{float(a['max_abs']):.6f}|{float(h['RMS']):.6f}|{float(h['abs_P95']):.6f}|{float(h['max_abs']):.6f}|")
    geomtext='\n'.join(summary)
    tab=['|日期/假设|Direct方案|N|AI−Swarm RMSE|AI−TIE RMSE|TIE−Swarm RMSE|AI−TIE相对RMS %（分母TIE）|','|---|---|---:|---:|---:|---:|---:|']
    for r in budgets:
        if r['model']!='Direct' or r['period']!='post' or r['region']!='global':continue
        tab.append(f"|{r['date']}/{r['mapping']}|{r['scheme']}|{r['n']}|{float(r['RMSE_AI_Swarm'])*1e13:.4f}|{float(r['RMSE_AI_TIE'])*1e13:.4f}|{float(r['RMSE_TIE_Swarm'])*1e13:.4f}|{float(r['relative_RMS_AI_TIE_with_reference_denominator'])*100:.4f}|")
    budgettext='\n'.join(tab)
    sources='\n'.join(f"- `{Path(r['path']).name}`，{r['bytes']}字节，SHA256 `{r['SHA256']}`。" for r in download)
    evidence=[
        dict(evidence='NCAR2.0 grid/Altitude Coordinates; existing official ZCoordinates PDF',version='TIE-GCM2.0',proves='use ZG for geometric-height registration; distinguish lev/ilev and Z',does_not_prove='precise WGS84/GRS80 zero surface or uncertainty',source='docs/TIEGCM_SWARM_COORDINATE_DATUM.md; cached official PDF SHA'),
        dict(evidence='getapex.F:125-145; actual updated apex.F90:358,1041-1075',version='2.0 plus official apex update',proves='apex input geodetic; own ellipsoid a6378.160km inverse_f298.25',does_not_prove='calczg ZG uses that same ellipsoid',source='experiments/tiegcm2_apex2023_v1/apex.F90'),
        dict(evidence='cons.F:315; lbc.F:105-150',version='2.0 retained physics',proves='default background lower Z plus GSWM perturbations',does_not_prove='modern external reference surface identity',source='third_party/TIEGCM2.0/src/cons.F;lbc.F'),
        dict(evidence='addiag.F:257-278',version='2.0 retained physics',proves='ZG bottom equals Z bottom, empirical gravity integral, top extrapolation',does_not_prove='effective r0 equals WGS84 radius',source='third_party/TIEGCM2.0/src/addiag.F'),
        dict(evidence='doc/description/mapping.tex:155-162',version='explicitly up to v1.8 in text',proves='97km neutral boundary vs90km field-line integration start are different concepts',does_not_prove='new2.0 external zero surface; do not reuse older-version statement as datum',source='third_party/TIEGCM2.0/doc/description/mapping.tex'),
        dict(evidence='new actual DNS0301/SP30203 with explicit time/ellipsoid conversion',version='0301/0203 postprocessed',proves='nominal Earth-fixed positions differ only metres, time matching/interpolation checked',does_not_prove='model ZG zero, true orbit error, or independent POD validation',source='results/swarm_coordinate_orbit_readiness_v1/geometry_summary.csv')]
    table(O/'height_definition_evidence.csv',evidence)
    report=f'''# 同期Swarm精密轨道、外部高度登记与真实轨道准入验证

2026-10-31；标签：`swarm_coordinate_orbit_readiness_v1`。

**本轮实际取得两份0203版同期SP3并完成DNS几何对齐；外部观测时间/椭球变换工程验证通过，产品位置存在数米残差，DNS的精确框架实现未独立闭合；TIE-GCM原生ZG登记仍BLOCKED，真实轨道预测准入仍BLOCKED。**没有网络forward、TIE积分、轨道传播或重复完整沿轨密度查询。

## 1. 输入、保护与实际工作

按要求读取十份项目状态/报告/协议，冻结源文件读入SHA。以服务器本地已有成果为准，保护未跟踪同步日志和本地private审计ref。原2021/2022候选、A7/B7/A14/B14、原SP3/DNS/模型预测及权重不修改。

本轮新数据为Jan4/Mar24官方SP3，缓存密度输入仍为上一轮真实DNS0301及原A/B/D/E查询值。上一轮实际是3072个统计单元、20832个有样本标量独立复核，以既有文件而非任务转述数字为准。

新增小型Hermite轨道插值模块与10项CPU测试，完成2882个同期DNS时刻的位置比较、P/V坐标变换、留出/独立插值核验及三方密度残差预算。新分析约15.74秒、峰值RSS236.14MiB，低于1800秒/4GiB门槛。102项本轮输入SHA保护；历史科学资产另按2346项清单复核。

## 2. 同期SP3实际取得

从[ESA Swarm公开分发服务](https://swarm-diss.eo.esa.int/)重新查询具体Sat_A目录，固定与旧实验一致的0203版本，不根据残差选择版本。原本地仅有03-21至23文件，没有重用或改名冒充目标日。

{sources}

新ZIP合计880272字节，含官方目录的全部本轮网络负载2687424字节，小于10MiB。先冻结大小和预算，下载长度匹配清单；CRC、解压成员SHA和逐字节回查通过。发布方未给出checksum，因此本地SHA不称为与官方SHA匹配。

实物两份均为：SP3-d、`#dV`有P及V，单星L47/Swarm-A，reduced-dynamic postprocessed product，0203，GPS日历，IGS20，10秒采样，每日8640个完整P/V。

P原km乘1000→m，V原dm/s乘0.1→m/s。实际HDR质量指标`000`、精度指数0原样保留，没有把它们转换为已验证的协方差或“零误差”。P记录未带可用机动/预测尾标；**缺少机动标记不证明没有推力**。

两SP3创建于2026-08-25，DNS0301创建于2024-09-17；二者都不是2023当时业务可得的证明，也不保证同一处理链/同一POD解。DNS原属性为GPS/POD气动反演及Basic Orbit地理位置；不能因共享GPS/POD信息就要求它与新0203逐点完全相同。

## 3. 时间、P/V与参考框架

### 3.1 GPS与UTC独立锚点

复用原`read_sp3`、`load_sp3_reference`和冻结IERS-B/闰秒入口，不改核心。GPS日历按统一时间标尺转UTC，不简单重标；2023样本差18秒。转换后首UTC与独立HDR Validity_Start差均0，EOP均在已冻结IERS-B域内，无自动更新/外推。

DNS为UTC30秒，SP3转换后的原生时刻在xx:xx:02/12/22/32/42/52秒。因此每个DNS时刻距最近SP3样本**2秒**，不是同网格，不能按记录行直接相减，也不能错误再加/减一次18秒。

### 3.2 插值验证与初始化因果性

新增`evaluation/orbit_interpolation.py:HermiteOrbit`：在原生P/V的TAI秒轴上做分段三次Hermite，解析求其导数作为插值速度；检查连续原网格、禁止越界/跨缺口。它是轨道状态插值，不是拟合Cd、轨道参数或动力学模型。

|交叉检查最大差|Jan4|Mar24|
|---|---:|---:|
|10秒Hermite与独立7节点六次位置多项式位置差 m|0.000130631|0.000128950|
|两方法速度差 m/s|0.000091818|0.000091810|
|原生隔点留出：20秒Hermite位置差 m|0.00463729|0.00464392|
|原生隔点留出速度差 m/s|0.000012014|0.000011799|

留出检验与方法差异只是内部数值资格，不是真实轨道误差上界。独立多项式导数也受原P量化/离散影响，不能据此给SP3速度建立物理置信区间。

01:00整点P/V的Hermite括点为00:59:52与01:00:02，使用了t0后2秒记录，必须标记**历史插值初始化**。另保存01:00:02原生P/V选项，无插值未来括点，但产品本身仍为事后POD，不能称严格实时初态。若用该原生点而仍结束于13时，时长为11h59m58s，不伪称精确12h。

统一原生状态及DNS时刻ITRS/GCRS P/V保存在`data/processed/swarm_coordinate_orbit_readiness_v1/`，只本地。位置和速度共同变换，未把地固速度当惯性速度。ITRS→GCRS→ITRS最大回差约4.68e-9m、9.06e-9m/s，只证明数值自洽，不能证明真实框架实现误差达到纳米。

### 3.3 框架实现的剩余限制

SP3明确IGS20，与ITRF2020对齐；继续沿用项目“IGS20作为ITRS对齐实现”的显式约定，未拟合Helmert变换。DNS明确GRS80大地坐标，但其CDF未独立给出精确ITRF实现。**椭球定义不等于参考框架实现。**以下为名义地固共同坐标中的实际产品差，不能声称严格毫米级框架登记已通过。

## 4. DNS与SP3几何一致性

DNS原GRS80经纬高转地固XYZ，SP3用同UTC插值位置；两者都转回同一GRS80/WGS84再比经纬高。经度差按周期处理，未估计时间偏移、平移、高度偏移或删除残差大点。

{geomtext}

高度差符号为SP3−DNS。Jan4平均−0.100143m，Mar24平均+0.159353m；经纬度差和全部逐时统计保留。极区经度角差受经线会聚影响，不能直接等价为横向距离。无新质量拒绝门槛，仅报告固定1小时统计及排名最大的5个差异时刻，不按排名删除观测。

数米位置残差明显大于约0.13毫米的插值方法差，不支持把它主要归因于当前插值误差。GPS/UTC和HDR锚点、P/V单位、相同参考椭球均已核对；剩余差可能包含不同处理版本、DNS位置来源和框架实现，但本轮不能独立分配这些原因。没有经验修正强行对齐。

利用已有参考剖面局部斜率，将实际DNS/SP3高度差换算成条件垂直密度响应，绝对P95约Jan4 **0.00434%**、Mar24 **0.00215%**。未新查询密度；该局部近似不是总位置误差的密度上界，也不约束未知ZG零面。

与之不同，旧A/B高度假设差约−14.2至+7.14km，条件密度响应P95为26.71%/21.98%。本轮米级外部产品高度差不能自动解决该模型高度定义问题。

## 5. ZG有界定向审查

复用已有NCAR2.0官方grid/Altitude Coordinates和ZCoordinates PDF，不再重复577点或103752次查询。定向查源码及版本适用性，证据表见`height_definition_evidence.csv`。

本轮新增明确细节：**实际使用的官方更新apex覆盖层**的SHA与S7冻结记录相同，其中req=6378.160km、逆扁率298.25，不是WGS84或GRS80常数。其convrt明确接受参考椭球以上高度；`getapex`实际传入的是电动力映射高度hs=130km。相同数值大地纬度/高度在该旧椭球与WGS84上的笛卡尔位置差约23m，仅为数学常数诊断，**不可直接作为ZG修正**。

这说明“apex写geodetic所以全模型就是WGS84”缺少依据；并不证明calczg使用apex椭球。calczg仍从Z下边界继承ZG底层，用自身经验g0/r0积分。`cons.F:315`的zbound和`lbc.F:105–150`默认背景加GSWM，不提供现代外部零面。`mapping.tex`提到97km下边界/90km场线积分，文本明确限至v1.8且两个概念不同，不能据旧说明覆盖2.0高度定义。

独立自生成TIE算例的ibgrddata=0/GSWM已核实；不能据此声称FourCastDEN作者所有原始数据有完全相同边界配置。

**本轮未取得可放行的ZG外部参考面依据。**已验证的是GRS80/WGS84与地固坐标的数学转换、UTC对齐和条件比较，不是ZG零面的科学确认。保留EXTERNAL_DATUM_UNVERIFIED，不新增一个貌似正式的适配器。

维护者英文咨询草稿：`docs/TIEGCM_ZG_EXTERNAL_REGISTRATION_QUESTIONS.md`，询问模型纬度、默认zbound零面、apex椭球与calczg的关系、Swarm推荐高度登记及精度限制。无臆造邮箱，未发送邮件。

## 6. 三方密度残差的独立分解

只读上轮逐点缓存及公共样本ID，保持A/B主后窗Jan4 N601、Mar24 N583，不重复密度查询。所有失败Flow时刻仍保留（A/B各18条，指相同18个UTC时刻）。

同单位、同一目标位置查询值满足：

`e=AI−Swarm=(AI−TIE)+(TIE−Swarm)=x+y`。

有符号残差逐点可加；均方满足`MSE(e)=MSE(x)+MSE(y)+2 mean(x y)`。若同时除以同一正Swarm密度，仍有对应相对均方交叉项恒等式。**RMSE、相对RMS、P95不可直接相加；分母改为TIE时也不能与Swarm分母各项混用。**

下表为Direct后窗示例，三个RMSE单位均为**1e-13kg/m³**，最后列按TIE密度作分母；所有模型/区域/时效结果完整存CSV。

{budgettext}

### 6.1 为什么A/B下改善结论会翻转

Mar24 Direct、共同Swarm分母的相对均方预算：

|假设/方案|AI−TIE均方项|TIE−Swarm均方项|有符号交叉项|合计AI−Swarm均方|
|---|---:|---:|---:|---:|
|A Open|0.0267231|0.0120252|−0.00829754|0.0304507|
|A Updated|0.00188537|0.0120252|+0.00203319|0.0159438|
|B Open|0.0301785|0.0354270|−0.0315300|0.0340755|
|B Updated|0.00222499|0.0354270|+0.00815588|0.0458079|

A/B改变TIE参考场对Swarm的条件残差，也改变AI与参考残差的空间取样关系。B Open中负交叉项产生较强抵消；更新虽然缩小AI−TIE项，却失去该抵消并转为正交叉项，所以相对RMS变差。**这是实际残差的代数说明，不是证明B是真实错误、A正确，或某种物理过程的因果贡献。**

B的绝对Direct RMSE仍可略降，而相对RMS升高，因为各密度水平权重不同。已按固定观测密度区间<1e-12、1e-12至2e-12、≥2e-12kg/m³保存描述统计，不用这些分组选择模型或调参。

### 6.2 能分开什么、不能分开什么

可分开：给定坐标假设下，三个已查询密度值的有符号差、均方、偏差、交叉项及按时间/区域分组的变化。

不可由本轮唯一分开：TIE真实物理偏差、Swarm反演误差、未知ZG零面、AI热力高度重建误差、5°/小时离散影响。AI使用重建ZG、参考使用原始ZG，因此AI−TIE是查询算子合成残差，不是纯网络DEN误差。

另从上轮保存的查询元数据单独提取AI/参考八邻列高度覆盖上下界差异，写入`cached_height_representation.csv`；它只记录几何表示范围差，不是卫星目标压力面的高度误差，不能将其换算成一个独立密度误差后再相加。无新高度拟合或模型修改。

## 7. 时间相关性、时空分布与稳健性

重用原公共样本保留更新前后、南北高纬及固定1小时块，07事件点不混入预测改善。前后时间块含不同沿轨区域，不能据某小时变化直接归因于单一地磁机制。

后窗30秒误差的lag-1描述相关系数范围**0.98267—0.99641**；首次降至1/e约**510—720秒（8.5—12分钟）**，并有更长周期变化。只对原索引连续的样本对计算，未把Flow失败点删除后压缩时间。

这些为有限、非平稳、沿轨周期序列的描述性尺度，**不等于有效独立时间尺度的正式估计**；不据此报有效N、置信区间或显著性。1441点不是1441次独立实验；两个日期也不足以全年泛化。UTC小时块、密度水平分组用于展示异质性，不用于事后选取更好的窗口。

## 8. 真实轨道准入判断

|条件|本轮状态|剩余必要证据|
|---|---|---|
|两目标日期SP3及原生P/V|工程PASS|0203/GPS/IGS20实物已取得；协方差和历史可用性非实时证明|
|DNS与SP3时间/参考椭球转换|工程PASS，精确框架实现PARTIAL|名义地固差数米；DNS的ITRF具体实现/处理链仍待说明|
|t0状态|历史回算可构造|01整点含未来2秒括点；原生01:00:02选项另有时间窗限制|
|TIE原生ZG外部登记|BLOCKED|维护者/独立资料明确零面及适用误差预算|
|四模型沿轨密度100%有效|未全通过|Mar24 Updated Flow后窗18点拒绝，不能补0/补真值|
|同期质量|缺正式完整采用依据|旧03-21至23记录不移用；目标日质量/质量标志及不确定度未取得|
|迎风面积/姿态|BLOCKED|目标日数据、0601旋转/面元/质量定义及投影模型|
|Cd及气体表面作用|BLOCKED|与实际参考面积一致的独立气动来源；不使用演示2.2/1m²|
|推进器/机动|BLOCKED|SP3无机动尾标不等于无推力；同期标志、支路/方向/定标未闭合|
|共同动力学与数值|已有H6/事件工程基础|未证明全部高精度受力充分，真实新窗口还须冻结并验证|
|真实轨道精度验证|**BLOCKED**|不得因轨道数据到位就开跑或用验证窗反拟合参数|

科学训练READY=False保持。可另行设计冻结合成气动参数的虚拟条件方案，但本轮不运行；它不是正式真实Swarm精度。也不把坐标阻碍扩大为其他已可完成工作的停止理由：本轮下载与DNS/SP3对齐已实际完成。

下一轮最小有价值动作：向维护者确认ZG定义，并限定一个日期开展同期气动/姿态/推力资料及版本字典的小规模准入审查；如先做条件传播，需另获授权、显式坐标假设、相同初态/受力、100%在线查询有效和事件base/tight验证。不能先拟合高度/Cd/密度比例再在同窗口称独立改进。

## 9. 交付、复核和停止

源代码：`src/evaluation/orbit_interpolation.py`，以及prepare/analyze/extend/plot/audit/write_swarm_coordinate_orbit_v1脚本；10项新测试。实际来源、CRC/SHA、HDR锚点、质量原值、初始化方案在`experiments/swarm_coordinate_orbit_readiness_v1/`。

结果`results/swarm_coordinate_orbit_readiness_v1/`：geometry_summary、geometry_hourly_summary、largest_geometry_differences、residual_budget、fixed_hour_blocks、descriptive_ACF、ACF_scale_description、Flow_failed_samples、height_definition_evidence、bounded_coordinate_diagnostics及高度表示CSV。原SP3、统一P/V和逐点位置表仅本地，不上传原观测。

推荐三图：`DNS_SP3_geometry_alignment.png`（时间/几何基础）、`signed_MSE_cross_term.png`（改善翻转的实际数学原因）、`time_blocks_and_autocorrelation.png`（相关性和时效异质性）。另有经纬度图和三方RMSE图。所有图来自真实本轮数据或原缓存，非合成结果。

```bash
source scripts/activate_orbit.sh
python tests/test_swarm_coordinate_orbit.py
python scripts/prepare_swarm_coordinate_orbit_v1.py
python scripts/analyze_swarm_coordinate_orbit_v1.py
python scripts/extend_swarm_coordinate_evidence_v1.py
python scripts/plot_swarm_coordinate_orbit_v1.py
python scripts/audit_swarm_coordinate_orbit_v1.py
python scripts/write_swarm_coordinate_orbit_report_v1.py
```

该标签已完成，脚本拒绝同名写入；不要删除历史目录重跑。只读CSV/报告不需网络或GPU。一次辅助表达式在输出前因list取abs报错，仅改为显式numpy数组并保存为可复现脚本，未重跑下载/主分析或修改科学阈值。

本轮安全同步只提交轻量源码、审计、统计和图。原始SP3、DNS、统一状态和逐点表均保留工作区，凭据不入库；不强推、不覆盖历史提交。实际SHA和远端状态以最终同步记录为准。完成后停止，不自动训练、积分或下载下一批资料。
'''
    p=inside(ROOT/'reports/SWARM_COORDINATE_ORBIT_READINESS_V1.md')
    with p.open('x') as f:f.write(report)
    talk='''# 三分钟组会汇报：同期轨道与密度观测的时间空间基准

李总，这一轮我们实际取得了1月4日和3月24日的Swarm-A精密轨道。两份文件共不到一兆字节，都是0203版、GPS时间、IGS20地固框架，有十秒采样的位置和速度。没有新增模型推理或轨道传播。

首先解决的是时间对齐。密度产品是UTC三十秒，轨道原生时刻与它通常差两秒，不能直接按行比较。我们显式转换GPS与UTC，再利用轨道原始位置和速度做Hermite插值。独立方法的位置差约零点一三毫米；把轨道隔点留出检验，最大差约四点六毫米，说明当前插值不是米级残差的主要来源。01时整点初态用了之后两秒的轨道记录，已明确标为历史插值初始化，不能包装成实时业务初态。

对齐后，两日期DNS与SP3的三维位置差RMS约四点三七米和三点五九米，高度差RMS约一点三四米和零点六三米。这是不同版本产品在名义共同地固坐标中的差异，不是实际轨道预测误差。密度和精密轨道共享部分POD处理信息，也不是两套绝对独立真值。

这些米级差异还不能解决TIE-GCM的高度零面。源码进一步确认，磁坐标辅助程序使用旧椭球常数，但calczg还有独立的经验重力和下边界登记；不能由此直接认定模型高度就是WGS84或旧椭球高。我们已准备好向维护者咨询的英文草稿，没有发送，也没有用观测拟合偏移。

密度方面，我们没有重复十万次查询，而是复用原逐点结果，把AI减Swarm拆成AI减TIE加TIE减Swarm。关键是均方误差还必须保留交叉项。B假设下原预测的一部分误差恰好抵消了TIE参考的观测残差；理想更新虽然让AI更接近TIE，却失去这种抵消，所以观测相对误差反而增加。这解释了实际指标反转，但不是证明某个坐标假设正确。

我们还发现三十秒相邻残差高度相关，因此不能把一千多个轨迹点当成一千次独立实验。所有失败Flow时刻仍然保留。

目前轨道数据基础已补齐，但正式真实轨道实验仍缺外部高度登记、同期气动面积和Cd、姿态及推力条件。下一步应针对这些具体门槛取证，而不是直接增加传播时长。本轮没有开展新的训练或长时间积分。
'''
    p=inside(ROOT/'docs/SWARM_COORDINATE_ORBIT_READINESS_TALK.md')
    with p.open('x') as f:f.write(talk)
    print('Evidence table, report and Chinese talk written')


if __name__=='__main__':main()
