# 2021年双初场同历元比较结果

本报告不衡量观测或轨道精度。B−A由完整初场切换产生，其他namelist参数逐字相同。

## 3月23日训练候选起点

|区域|原生ZG450km密度P95 %|最大相对差 %|绝对RMSE kg/m³|覆盖率 %|
|---|---:|---:|---:|---:|
|global|6.69483|7.4234|1.74718e-14|100|
|south_polar|6.05429|6.89694|1.48154e-14|100|
|south_mid|6.97952|7.4234|1.81304e-14|100|
|tropics|6.29462|6.67227|1.71826e-14|100|
|north_mid|6.67507|6.9543|1.77634e-14|100|
|north_polar|7.14073|7.24218|1.93311e-14|100|

## 全候选窗、最后24小时、终点的全局多变量差异

|变量|时窗|绝对RMSE(SI)|绝对P95(SI)|相对P95 %|最大绝对差(SI)|
|---|---|---:|---:|---:|---:|
|DEN|candidate|9.79937e-10|2.72055e-09|1.48877|7.57827e-09|
|DEN|last24h|8.9301e-10|2.49115e-09|1.29556|6.39891e-09|
|DEN|endpoint|8.48345e-10|2.38167e-09|1.22622|5.38697e-09|
|TN|candidate|3.84646|6.08011|1.56985|12.7191|
|TN|last24h|3.64888|5.67961|1.44117|11.9124|
|TN|endpoint|3.66748|5.89146|1.38344|10.6174|
|WIND_VECTOR|candidate|3.30487|6.82146|N/A|33.6651|
|WIND_VECTOR|last24h|3.13081|6.50505|N/A|29.5961|
|WIND_VECTOR|endpoint|2.86572|6.00639|N/A|16.4904|
|O1|candidate|0.0183133|0.034869|11.7012|0.0613227|
|O1|last24h|0.0161672|0.0302805|9.92972|0.0529828|
|O1|endpoint|0.015292|0.0286403|9.46154|0.0447475|
|O2|candidate|0.00215772|0.00389035|21.4586|0.00757496|
|O2|last24h|0.00181627|0.00315046|18.5608|0.00684374|
|O2|endpoint|0.00168678|0.0029633|17.5558|0.005392|
|N2|candidate|0.016463|0.0319446|19.0858|0.056393|
|N2|last24h|0.0145783|0.0278565|16.728|0.0485444|
|N2|endpoint|0.0138023|0.0263203|16.0948|0.0412595|
|HE|candidate|0.00164451|0.00301009|7.45636|0.0377773|
|HE|last24h|0.00155935|0.00291567|6.77344|0.0271483|
|HE|endpoint|0.00156304|0.00282196|6.29552|0.0254632|
|Z|candidate|1057.67|2231.2|0.557366|4692.88|
|Z|last24h|874.942|1800.64|0.441063|4373.08|
|Z|endpoint|783.893|1661.79|0.399966|2924.84|
|ZG|candidate|1063.2|2254.6|0.577027|4887.24|
|ZG|last24h|879.652|1824.36|0.456984|4507|
|ZG|endpoint|787.068|1683.74|0.414279|3102.88|

DEN单位kg/m³，TN为K，WIND_VECTOR为m/s；O1/O2/N2/HE为无量纲mmr；Z/ZG为m。风矢量与零比较，其相对P95为N/A；TN及高度的相对值仅描述，不是验收阈值。所有指标使用各变量共同有效掩码，TN原生顶层不计作有效样本。

## 图表及逐层/区域索引

- [composition_evolution](../results/tiegcm_2021_spinup_initial_condition_v1/comparison/figures/composition_evolution.png)
- [density_pressure_profiles](../results/tiegcm_2021_spinup_initial_condition_v1/comparison/figures/density_pressure_profiles.png)
- [native_ZG_450km_maps](../results/tiegcm_2021_spinup_initial_condition_v1/comparison/figures/native_ZG_450km_maps.png)
- [native_ZG_density_evolution](../results/tiegcm_2021_spinup_initial_condition_v1/comparison/figures/native_ZG_density_evolution.png)
- [native_evolution](../results/tiegcm_2021_spinup_initial_condition_v1/comparison/figures/native_evolution.png)

- native_summary.csv：3时窗×6区域×11变量。
- native_profiles.csv：逐原生层、同区域/时窗，含DEN/TN/风矢量/主要组分。
- native_hourly.csv：240小时全部预热和候选过程。
- native_density_groups.csv / native_density_group_hourly.csv：upper20—28及A中位ZG400—500km组选层索引和实际中位高度。
- native_ZG_density.csv / native_ZG_density_hourly.csv：共同原生几何高度覆盖率、P95、最大值、logRMSE。
- last24h_trends.csv：冻结无增长检验；不把时序点当独立样本作显著性。
- native_ZG_450km_maps.csv：候选起点和终点原始地图。

## 解释边界

预热期间差异可能总体减小而局部/组分仍超限，不能用一条全球平均曲线判断充分。候选层组随A参考ZG逐时变化，分层表与固定高度结果必须并列读取。自然昼夜/地磁变化不是本次A/B初态差的替代量。

初始化残余影响、模型物理误差、参考高度不确定性及AI拟合误差是不同问题；本次没有模型训练，没有重新提取或覆盖已有122帧，没有调整官方模型/训练统计。
