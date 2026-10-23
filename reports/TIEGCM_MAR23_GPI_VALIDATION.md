# Mar23 v2 GPI验证

2026-10-23；两年源数据门禁全部通过后生成两份独立新文件，不改旧GPI。

|年份|ndays×nkp|新GPI SHA256|
|---|---|---|
|2021|15×8|d9fdad36af5672ae8a34c977d67247437ba20084406d04b417905739b10c783b|
|2022|14×8|9bf83f53133a9290002d72300705681fc9da9ee89b2d2ed712271cdc799ec6f7|

路径`data/processed/training_window_mar23_v2/gpi_YEAR_mar23_v2.nc`，NETCDF3_CLASSIC。year_day为实际YYYYDDD/int32；f107d/f107a/kp float64；GPI合法域与前后两日padding分开。所有日数据有限，无空值。

复用原`prepare_tiegcm_training_drivers.py`的arrays/write_gpi与原GpiDriver，旧脚本未改。F107A=本日及前后40日Fobs等权平均；独立math.fsum/81与NumPy最大差分别1.4211e−14、2.8422e−14 sfu。所有输入均原GFZ有效记录。

独立多项式系数拟合复核每日太阳noon四点插值；独立分段权重复核Kp桶中心线性插值。检查整个合法域每一天在0、60、300、600、5399、5400、10800、43199、43200、86399秒，包括午夜、桶中心及太阳noon切换。与GpiDriver最大标量差2021为7.1054e−14，2022为1.1369e−13，均小于预定1e−10阈值。

GFZ Kp时间是00/03等桶起点，模型锚点是01:30/04:30等桶中心；不把Kp直接当午夜阶跃。POWER保持现有gpi.F两分支，CTPOTEN=15+15Kp+0.8Kp² kV，未设固定输入覆盖。

模型00:10实际值（与预期一致）：

|年份|F107 sfu|F107A sfu|Kp|POWER GW|CTPOTEN kV|
|---|---:|---:|---:|---:|---:|
|2021|76.9083899813|74.6865752200|2.2591111111|29.7964622892|52.9695330765|
|2022|105.8811085614|119.3359136823|2.148|28.5858814872|50.9111232|

每分钟模型日志与独立计算按打印精度0.000501核验，暖态NetCDF驱动差小于1e−10。完整源数组、11节点预期驱动、SHA与独立误差见`experiments/training_window_mar23_v2/gpi_YEAR_audit.json`。
