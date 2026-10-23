"""Official metadata audit and actual synthetic smoke report; never train here."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/fourcastden_training_smoke_v1';G=ROOT/'experiments/fourcastden_training_smoke_cublas_v2'
def put(name,s):
 with (ROOT/name).open('x') as f:f.write(s)
def main():
 software=json.loads((F/'22250237.json').read_text());data=json.loads((F/'21859635.json').read_text());r=json.loads((G/'gpu_result.json').read_text());sup=json.loads((G/'supervision.json').read_text());failed=json.loads((F/'supervision.json').read_text());assert r['status']==sup['status']=='PASS'
 table='|记录|文件|字节|官方checksum|\n|---|---|---:|---|\n'
 for label,z in [('软件22250238',software),('数据21859635',data)]:
  for x in z['files']:table+=f"|{label}|{x['key']}|{x['size']}|{x['checksum']}|\n"
 put('reports/FOURCASTDEN_OFFICIAL_TRAINING_RESOURCE_AUDIT.md',f'''# FourCastDEN官方训练资源核查（2026-10-23）

## 实际访问与身份

本次直接HTTP API读取[软件概念记录22250237](https://zenodo.org/api/records/22250237)最终跳转[版本22250238](https://zenodo.org/records/22250238)，HTTP200；[数据21859635](https://zenodo.org/records/21859635)HTTP200。resource_http.json保存实际URL/HTTP/字节与SHA，原JSON随审计保留。软件概念DOI不等于版本号；两记录metadata.version都未提供字符串，不杜撰v1，version关系index0/is_last=true是此次API返回快照。

软件标题AFNO Software for TIE-GCM-Based Multivariable Thermospheric State Forecasting，作者Zhou, shuyang与He, Changyong，发布日期2026-09-02；数据标题2023 TIE-GCM Simulation Dataset for AFNO Inference Evaluation，作者He, Changyong与Shuyang, Zhou，2026-08-09。软件说明明确用途为模型实现、推理、评价和配套权重/统计，配合2023测试数据；数据说明明确是模拟参考，不是独立观测验证。两个API未列论文DOI的related_identifiers，不能声称元数据双向绑定已完整证明。

论文DOI[10.3390/rs18183134](https://doi.org/10.3390/rs18183134)直接MDPI页面及XML实际HTTP403，网页工具另遇429，均不伪称全文已读；Crossref官方登记API HTTP200，标题与用户所指一致，作者Shuyang Zhou/Changyong He/Dunyong Zheng/Dongfang Lin，与Zenodo前两作者对应，abstract说明2000—2023模拟/四变体/2023给定驱动测试，支持资源与研究主题一致。Crossref主资源和PDF链接仅指MDPI，未提供另一训练仓库。全文其他资源声明因访问限制未重新核实，不能断言不存在任何其他官方训练地址。

## 当前公开文件完整清单

{table}

本次只获取小元数据/文本，没有下载上述大型档案或任何训练数据。软件Apache-2.0、数据CC BY4.0、access_right=open来自当日API。source zip本地原件MD5与当前官方清单完全一致（official_source_inventory.json），实际检查归档全部成员和已解压源码，无train_tiegcm.py/完整训练入口/四变体活动训练YAML/学习曲线。普通static/static_log及四checkpoint是既有官方资源，继续只读；checkpoint_files.zip本次不重取，不能用仅检查内部checkpoint SHA等同重新验整个2.9GB归档MD5。

原包README_inference_2023明确不提供训练/验证数据及重训说明。models/model_module.py保留training_step/optimizer片段，但forward要求(value, flow)+warp，与已验证AFNONet(x,4scalar)直接171输出不兼容；config/AFNO.yaml有注释训练配置和活动推理项，不能当作四checkpoint的完整实际训练协议；dataset注释指向缺失train_tiegcm.py/SAMPLER_PERCENT。NVlabs AFNO仅为架构来源，不冒充TIE专用训练入口。

## 分级结论

A：没有取得并验证完整官方训练主程序；B：论文/登记摘要支持多年数据训练与2023独立测试描述，但2000—2021及2022数据、完整协议不在当前文件清单，不能声称可下载；C：已读推理包中的残留训练片段；D：本次自有src/training为独立重建工程，合成测试成功，不称完整论文训练复现。

当前记录没有公开非2023小时文件/训练数据清单或专门申请入口；需要向作者取得许可、精确版本及小样本位置，本次没有发送联系消息。记录公开并不等于训练集可取得或可拿2023替代。缺四变体实际损失/纬度或通道权重、优化器/调度、采样/seed、统计年份与掩码、AMP/裁剪/恢复、原学习曲线和数据SHA。其他未知项保持未知。

## 许可与代码复用

官方软件记录声明Apache2.0，数据CC BY4.0；原源码包根目录未找到LICENSE，afnonet.py引用NVlabs/AFNO-transformer，后续再分发完整第三方代码需确认原始文件及notice链。本次不复制或修改作者代码，只导入已有只读Linux副本。独立工程使用现有torch2.4.1(BSD-3)、numpy1.25.0(BSD-3-Clause)、timm1.0.13(Apache-2.0)、einops0.8.0(MIT)，许可证字段来自已安装包metadata；未新增依赖。数据许可不自动扩展到尚未提供的训练资料，未来先确认。
''')
 rows='|step|合成MSE|裁剪前梯度L2|train_step墙钟秒|\n|---|---:|---:|---:|\n'
 for x in r['records']:rows+=f"|{x['step']}|{x['loss']:.9f}|{x['gradient_l2_before_clip']:.9f}|{x['wall_s']:.6f}|\n"
 put('reports/FOURCASTDEN_TRAINING_SMOKE_TEST.md',f'''# FourCastDEN独立训练工程合成预检（2026-10-23）

INDEPENDENT_IMPLEMENTATION / SYNTHETIC_ENGINEERING_ONLY / NO_REAL_DATA_TRAINING

## 已完成与未完成

本次建立src/training/pipeline.py、独立配置与执行/监督脚本；不是官方完整训练复现。原AFNONet全64,695,744参数/36×72/177二维+4标量→171输出，未缩小架构，随机初始化，未读官方checkpoint或真实NPZ。原第三方树/四权重/static/既有实验SHA保护见delivery_audit。未12/24h预测、TIE、RK45、真实训练/微调。

247项全套CPU测试27.191秒通过，其中8项新增训练测试覆盖shape/loss/backward/梯度/参数更新、validation无更新、非2023年份与连续窗口/跨年/时区拒绝、split分离、未来目标毒化不改变输入、仿射归一化往返、同seed重复，以及含SGD动量/调度/RNG/模型/step的精确checkpoint恢复与下一步等价。旧ERFA合成dubious-year警告保留，不改变环境。

## GPU实际两次启动，累计只完成3个训练step

v1首次在第一forward的CuBLAS运算被确定性检查拒绝，缺CUBLAS_WORKSPACE_CONFIG，0完成step、0optimizer更新，无checkpoint；监督{failed['wall_s']:.6f}秒，日志/代码SHA/失败标记完整保留。未关闭确定性检查或改网络，将环境:4096:8在torch导入前设置，用独立cublas_v2标签纠正预检；不是隐藏失败或覆盖重跑同标签。

成功预检执行step1/2，保存唯一checkpoint，释放模型，随机重建同结构后严格恢复到step2，再执行step3；总共3训练更新，另一次独立合成validation无更新，没有真实数据。两进程监督合计{failed['wall_s']+sup['wall_s']:.6f}秒<300，成功进程{r['wall_s']:.6f}秒内部墙钟，监督{sup['wall_s']:.6f}秒。CUDA确定性/FP32/TF32关闭保留。

{rows}

loss只是任意标准化合成映射的MSE，降低只证明链路更新，不代表真实温度/密度精度改善。随机未训练输出不按物理DEN正值评价，张量不是物理大气。验证合成loss={r['validation_loss']:.9f}亦无科学解释。

## checkpoint与资源

GPU step2模型SHA恢复精确一致；优化器param_groups/state和scheduler完全一致、step=2，之后成功step3。GPU配置SGD momentum0，optimizer状态无动量张量，CPU测试另外使用momentum0.9证明非空optimizer状态恢复与连续训练数值等价。RNG包括Python/NumPy/CPU/CUDA、training/eval状态、config/label/代码来源。加载只允许可信本地产生.pt，拒绝官方权重目录，不声称可安全加载未知pickle。

唯一synthetic_step2.pt为{r['checkpoint_restore']['checkpoint_bytes']}字节={r['checkpoint_restore']['checkpoint_bytes']/2**20:.3f}MiB，留本地不上传。新增500MiB预算不足以保存完整Adam类参数+两动量状态（约0.75GiB），因此工程配置显式SGD0动量/lr1e-4/固定调度/clip1，是资源可控的独立假设，不冒充作者优化器，不改变架构追求loss。未来正式优化器/存储需另核协议与预算。

成功进程CUDA allocated峰{r['peak_allocated_bytes']/2**20:.3f}MiB、reserved峰{r['peak_reserved_bytes']/2**20:.3f}MiB，nvidia-smi进程峰{sup['peak_GPU_process_bytes']/2**30:.3f}GiB<20GiB；CPU ru_maxrss峰{r['peak_RSS_KiB']/1024:.3f}MiB。仅batch1/单步/SGD/FP32实测，不能外推完整Adam、多步展开/大batch时长与显存。模型原声明但未调用norm.weight/norm.bias无梯度，与既有推理源码一致，未修补该数学行为；其余有效梯度统计逐step保存。

## 运行入口与下一门禁

source scripts/activate310.sh；unittest discover；run_fourcastden_training_smoke.py由监督v1启动（失败已保留）；run_fourcastden_training_smoke_cublas.py由独立监督启动（3step通过）。once-only目录，不自动追加step/真实训练。future真实数据需合法2000—2021/2022样本、官方预处理/统计与许可、预注册日期及split、接口单步与多步指标、资源门禁；现有OfficialFrameSource/EpochPairs真实路径仅实现，尚未真实样本运行，不称已验证真实训练。

模型与训练损失、checkpoint兼容经过工程验证，与TIE参考拟合、真实观测密度、最终轨道精度和效率分别论证。第三阶段高度/Z/ZG/WGS84、小时场插值、驱动可得性、真实Swarm气动/姿态/推力及共同受力门禁继续。下一优先取得作者材料和非2023小样本，而非立即大训练。
''')
 print('Official resource and actual smoke reports written')
if __name__=='__main__':main()
