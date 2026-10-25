# 2021年14天预热扩展驱动验证

实际代码由模型03-09至03-26及两日插值边界计算：GPI原始03-07至03-28，中心81日观测支持01-26至05-07。共102个有效Fobs日、22×8=176个definitive Kp桶，无缺测、重复或非有限值。无Fadj、插值/估算Fobs替换，也没有使用05-09缺测值。

复用已取得的GFZ官方年度原始档案`data/raw/f107_2021_recovery_v1/gfz_year.txt`，SHA256 `f969f23b0b0d4aba80dca6f35d3e95c2d35a7e482457bc1812e5c0827090caae`，原来源`ftp://ftp.gfz-potsdam.de/pub/home/obs/Kp_ap_Ap_SN_F107/Kp_ap_Ap_SN_F107_2021.txt`，Fobs/Kp按GFZ CC BY 4.0引用。无需新增下载，原始档案保持不变；SN未提取使用。Fobs未暴露逐日质量标志，验证的是已发布有效正观测、连续性及字段选择；Kp质量列=2为definitive。

扩展GPI `data/processed/tiegcm_2021_spinup_14day_v1/gpi_2021_14day.nc`，SHA256 `6dad9d0ff290e841c32fb736b8f097365d7c4eebe2e12a0cef5c301b0eae8847`。NETCDF3_CLASSIC，year_day int32、f107d/f107a/kp float64，ndays22/nkp8，UTC与实际年份2021。原2021/2022 GPI不修改。

独立math.fsum/81相对NumPy均值最大差1.42109e-14 sfu；通量四点午时锚点多项式与GpiDriver、Kp中心锚点线性插值、POWER/CTPOTEN独立复核最大差7.10543e-14。GFZ桶起点不误认作模型插值中心。新旧GPI在03-16至26共同14401个分钟节点最大差0。

这只是驱动与实现一致性，不是大气模拟物理精度证明。全部驱动为HINDCAST，原Apr05_v1与05-09 DATA_GAP_UNRESOLVED不变。详细数组及来源见`experiments/tiegcm_2021_spinup_14day_v1/driver_audit.json`；构建入口`prepare_tiegcm_2021_14day_drivers.py`，未启动网络训练或归一化统计拟合。
