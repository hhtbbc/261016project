"""Build joint quality report from recorded read-only audits, no model execution."""
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1];F=R/'experiments/tiegcm_training_mar23_v2_2022_longrun'
def main():
 a=json.loads((F/'joint_dataset_audit.json').read_text());assert a['total_frames']==122 and not a['scientific_training_READY']
 years=a['years'];keys=['DEN450_mean_kg_m3','TN_mean_K','horizontal_wind_RMS_m_s','f107d','f107a','Kp']
 table=[]
 for k in keys:
  vals=[]
  for y in ['2021','2022']:
   x=years[y]['diagnostics_only'][k];vals.append(f"{x['min']:.8g} / {x['median']:.8g} / {x['max']:.8g}")
  table.append('|'+k+'|'+'|'.join(vals)+'|')
 text='''# 2021/2022独立候选数据联合质量审查

INDEPENDENT_TIEGCM_DATA_GENERATION / HINDCAST / SPINUP_SUFFICIENCY_UNVERIFIED。

## 实际数据与隔离

|年份/角色|候选UTC窗口|帧数|小时配对|标签|
|---|---|---:|---:|---|
|2021训练候选|03-23 00至03-26 00|73|72|TRAINING_CANDIDATE_ONLY|
|2022独立验证候选|03-23 00至03-25 00|49|48|VALIDATION_CANDIDATE_ONLY|

共122帧/120个连续小时对，实际时域不重叠。两年各自从2002完整初猜独立连续积分，未用2021终点初始化2022，无Restart拼接；2021文件只读、未重跑。2023没有进入本次数据管线。

模型可执行、原初猜、apex来源SHA相同，原HEELIS/GSWM/SECFLDS/60秒/4MPI规则相同；各自真实GFZ Fobs/中心81日平均/def Kp及日历不同，IGRF按实际年份计算，GPI各自冻结。两年候选网格/变量/dtype/单位/顶部padding一致，与作者普通static四坐标逐元素一致。源卷和每帧NPZ实际SHA重新核验通过。

14键保留作者原生单位与float32，TN/UN/VN有效28层、其他压力界面29层，LBC与三标量结构一致；lat/lon/lev/ilev侧车单独保存。Z位势高度不能等同ZG或WGS84高度。全部候选DEN有限正、无有限哨兵值、ZG严格递增。初始primary冷echo不作为样本，167个预热小时/年未提取入候选。

只读作者接口分别通过177输入/171目标/4标量及未来真值毒化；没有神经网络forward、反向传播、参数更新、训练/验证loss调参或归一化统计拟合。原官方static只作兼容性检查，不宣称适用于独立从零训练。

## 候选窗口物理分布（最小 / 中位 / 最大）

下表为既有逐小时物理诊断的描述性汇总，**不是逐通道训练均值/方差或训练归一化文件**。DEN450单位kg/m³，TN为K，水平风RMS为m/s，F107/F107A为sfu，Kp无量纲。

|诊断|2021候选窗口|2022候选窗口|
|---|---|---|
'''+ '\n'.join(table)+'''

两年实际太阳/地磁驱动及大气初期演化不同，分布不同本身不等于数据错误；不按差异大小删除时段，不把年际差异当初始化敏感性，也不直接作单一太阳活动因素的因果解释。原生ZG450km仅模型参考域内逐列log密度插值，非固定WGS84/卫星沿轨误差。全层密度均值受低层主导，需与高层和逐层一起解释。

两个窗口长度不同，图中分别用各Mar23起点后的小时，不拼接为一个预测实验。只有两条短年度窗口，小时数据仍相关，不将空间格点或122小时当作122个独立泛化试验。不能声称全年/太阳活动阶段泛化，也不是独立真实大气观测或轨道精度。

## 门禁结论

ENGINEERING_CANDIDATE_DATASET_PASS；SCIENCE_TRAINING_READY=False。两年输入、连续运行、122帧、读接口与划分已具备，但7天预热仍无合法同驱动初场/更长预热对照。先开展预热敏感性设计与授权，再冻结物理质量接受范围、仅2021训练统计、独立2022验证、模型/损失/优化器/采样/资源等协议。没有本次真实训练授权。

共同质量CSV/图在results/fourcastden_2021_2022_dataset_v2；完整联合审计见2022长例目录joint_dataset_audit.json。两年各自日志/配置/输入输出SHA保留，大NetCDF/NPZ仅本地。训练前完整决策见docs/FOURCASTDEN_REAL_TRAINING_GATE_DECISION.md。
'''
 (R/'reports/FOURCASTDEN_2021_2022_DATASET_AUDIT.md').write_text(text)
 gate=R/'docs/FOURCASTDEN_REAL_TRAINING_GATE_DECISION.md'
 with gate.open('a') as f:f.write('\n## 本次实际工程结论\n\n两年连续运行及122帧/120小时对已通过共同只读质量门禁，时间隔离、单位/网格/模型一致；细节见联合数据集报告。独立验证候选已补齐，科学训练READY仍为False，主要先决缺口为预热充分性配对证据及独立训练协议/统计冻结。本次未训练或调参。\n')
 print('JOINT REPORT AND TRAINING GATE UPDATED')
if __name__=='__main__':main()
