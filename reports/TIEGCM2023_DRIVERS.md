# 2023太阳与地磁驱动文件及质量

文件：data/processed/tiegcm2023/gpi_20230312_20230325.nc；SHA256 `60fa18244fcdbd8b1bb5300bda86cde68abcca9a9152539bcdc5fc30377aa9f6`。脚本scripts/prepare_tiegcm2023_drivers.py拒绝覆盖现有输出目录。数据来源[GFZ API说明](https://kp.gfz.de/en/data)、[字段与物理约定](https://kp.gfz.de/app/format/Kp_ap_Ap_SN_F107_format.txt)，原始JSON及SHA见logs/tiegcm2023_driver_audit.json和data/raw/tiegcm2023_sources/manifest.json。已有原始数据未改。

14个UTC日2023-03-12—25，112条Kp；model有效日期03-14—23（含03-23 00:00:02），支持03-14七天或03-18三天spin-up。前后各两天留给实际源码插值。year_day=int32 YYYYDDD；f107d/f107a=float64(ndays)，kp=float64(ndays,nkp=8)，NETCDF3_CLASSIC；全局yearday_beg=2023073、end=2023082，是去掉两侧padding后的日期。NetCDF读回/类型/维序检查通过。源Fortran存储kp(8,ndays)，与Python文件维序反向，不能写成kp(nkp,ndays)。

f107d使用**观测Fobs**，非调整到1AU的Fadj；GFZ推荐Fobs用于地球大气/电离层，单位sfu=1e-22 W m^-2 Hz^-1。Fobs是每日观测，日标签不是精确观测UTC瞬间；TIE-GCM源码将日值锚定12:00UT。f107a按源码mkncgpi为当天前40+当天+后40个日值算术平均，不是过去81天平均。原始Fobs覆盖01-31—05-05，全部81项完整。日通量范围[134.2, 160.3]，平均通量范围[158.21111111111108, 161.90740740740742]。原始明显高值保留，不平滑；API没有逐条太阳质量标志，不能声称独立认证所有观测。GFZ年文件URL404已记录；不伪造完整D标志。

Kp输入范围0—8，全部API status=def；原105条加03-25剩余7条，重复冲突检查通过。API时间是三小时间隔**起点**；模型赋到01:30、04:30…22:30UT中心，线性插值，跨日取前后日。ap和Ap另已获取作旁证，其单位为等效活动指标，Ap是八个ap日均取整；本模型GPI实际不读取Ap，不能以Ap代替Kp。

实际util.F采用POWER=16.82 exp(0.32Kp)-4.86 GW（Kp<=7），大于7采用153.13与300GW间线性公式；CTPOTEN=15+15Kp+0.8Kp² kV。gpi.F开头注释中的老公式不等于执行代码。配置须启用HEELIS/GPI_NCFILE，并省略固定F107/F107A/POWER/CTPOTEN/**KP**及相应时间序列覆盖。GPI只负责这条驱动路径；不能直接声称它包含所有高纬IMF物理。

**真实消费者验证**：链接当前2.0全部对象（排除tgcm主程序），只调用rdgpi/getgpi，未进行时间积分。16个03-21时刻，八个Kp中心计算POWER/CTPOTEN与独立公式相符，正午F107=151.6、F107A=160.79135802469133，检查通过。logs/tiegcm2023_gpi_consumer_corrected.log。首次测试忘设rd_kp=spval并传入86400秒，日志保留；修正为同日0—81000秒和显式禁用常数覆盖。跨日必须改变日期，不能传86400；正式运行前仍需检查真实namelist和边界实际配置。

太阳81日平均、事后def Kp、2025重处理姿态及SP3均含事后资料，全部实验标为**hindcast**，不是实时预报。当前驱动完整，但太阳源质量标志不足已披露。未启动2023仿真。

补充Ap质量：112个ap、14个Ap均def；八个ap日均四舍五入与Ap全部一致，Ap范围2—73；logs/tiegcm2023_ap_quality.json。未把Ap写入模型不读取的GPI字段。
