# 2021/2022真实历史驱动审查

2026-10-23；INDEPENDENT_TIEGCM_DATA_GENERATION / HINDCAST。

## 实际结果

- 2021：**BLOCKED**。GFZ HTTP200返回2021-02-15至05-20观测通量，其中05-09为−1缺测，位于04-05中心81天平均所需的02-24至05-15内。没有填补、替换Fadj或复用2023数据；未生成GPI，未启动模型。首次失败后没有重试；Kp尚未获取，不声称2021驱动完整。
- 2022：PASS。Fobs为02-15至05-19每日94条；Kp为03-27至04-09共112个三小时桶，全部def。两次响应合计6727字节；Fobs API没有逐条质量标志，完整/正值检查不能代替原始观测质量认证。源许可CC BY4.0。
- GPI：NETCDF3_CLASSIC，ndays14/nkp8；year_day int32，f107d/f107a/kp float64。原始日03-27至04-09，合法查询03-29至04-07，额外两日用于模型插值。SHA256 `31ae38aa4908106c8cde4cb5cd9ea27dfc751bbf49eac7bafc894c6e92a33e6e`。

## 计算及独立复核

每日使用Fobs，中心81日含本日及前后各40日；独立math.fsum/81与NumPy结果最大差2.8422e−14 sfu。没有使用测试集重新拟合统计。GpiDriver与独立通用多项式权重在诊断0—600秒的11个节点一致，测试至小数10位；实际模型每分钟输出按日志打印精度0.000501核查，NetCDF暖态驱动差小于1e−10。

太阳通量采用模型noon锚点四点Lagrange，而非把每日值当作午夜阶跃。GFZ Kp时间戳为桶起点，模型锚点为01:30、04:30等桶中心；跨午夜使用前一日末桶和本日首桶线性插值。POWER(Kp≤7)=16.82 exp(0.32 Kp)−4.86 GW；高Kp按现有gpi.F分支，CTPOTEN=15+15Kp+0.8Kp² kV，绝非固定外部覆盖。

2022-04-05 00:10实际/预期：F107=124.73804458876316、F107A=123.32593272049596 sfu，Kp=0.8885555555555555，POWER=17.491790558449086 GW，CTPOTEN=28.959958113580246 kV。2021没有合法对应值，不能进行两年实际值比较。

## gcmprocpy独立参考

已读取[gpigen文档](https://tiegcmpy.readthedocs.io/en/stable/gcmprocpy/input_generation.html)及[2.0.0公开源码](https://tiegcmpy.readthedocs.io/en/stable/_modules/gcmprocpy/gpigen/core.html)：同样支持centered81和def，但默认start1960，中心平均的有效终点比请求end提前40天，并调用fill_fobs。故不直接替换当前失败即停的驱动流程，也不借其缺测填补绕过2021门禁。未安装或运行该工具。文件dtype/插值边界继续以本地TIE-GCM 2.0 gpi.F契约为准。

[GFZ官方说明](https://kp.gfz.de/en/data)确认桶起点、Fobs/Fadj区别及def适用指数。源URL、范围、许可、SHA、完整生成数组和11节点预期值见`experiments/tiegcm_training_years_v1/2022/driver_audit.json`；2021缺测证据见同目录`2021/missing_data_audit.json`。原始JSON和GPI保留本地data目录。
