# 轨道与配套数据来源核验（2026-10-19）

## 推荐目标与时间
选择Swarm-A：既有官方精密轨道产品，也实际取得同星历史TLE；适合先做单星、低轨阻力敏感性验证。Swarm-C可后续复查，B作为不同高度的扩展；今天未对B/C下载或排名。不能用GNSS高轨SP3替代。
建议48小时窗口UTC2023-03-21 00:00:02至03-23 00:00:02（GPS标签03-21 00:00:20至03-23 00:00:20）。选2秒偏移使t0对应实际10秒GPS网格采样，避免用未来参考位置差分估计初速。正式日期转换仍待Astropy/闰秒核验；本次reader完全保留GPS标签，没有隐式转UTC。
GFZ已取得该区间Kp，03-21至22日主要采样最大3.667，不将其未经其他检查直接定为“完全无扰动/无机动”。24—72小时长度是评价窗口，不代表TIE-GCM可以省略之前的spin-up。

## ESA SP3：实测匿名可下载
[目录说明](https://swarm-disc.github.io/product-catalogue-tools/SW_SP3xCOM_2_.html)和[下载入口](https://swarm-diss.eo.esa.int/#swarm/Level2daily/Latest_baselines/POD/RD)。本机无需登录/令牌，目录和3个文件均HTTP200；这只证明本次公开路径，不泛化到所有ESA服务（VirES等另有规则）。原始访问日志logs/meeting_sources_http*.json。
可用查询：GET https://swarm-diss.eo.esa.int/?do=list&maxfiles=10000&pos=0&file=swarm%2FLevel2daily%2FLatest_baselines%2FPOD%2FRD%2FSat_A 。5778个目录条目，首文件覆盖2013-12-31/2014-01-01，末文件覆盖2026-09-22/23；包含不同版本重复，不能由首末推断每天都完整。
下载参数：`?do=download&file=`加URL编码后的完整path。目录Latest_baselines仍含0201和0203，不能随意混合，今日统一0203并记录SHA256。

|ZIP文件名的时间部分（均前缀SW_OPER_SP3ACOM_2__、后缀_0203.ZIP）|字节|内部GPS日期|
|---|---:|---|
|20230320T235942_20230321T235942|440078|2023-03-21|
|20230321T235942_20230322T235942|439918|2023-03-22|
|20230322T235942_20230323T235942|439999|2023-03-23|

共1,319,995字节压缩数据，保存data/raw/orbits/swarm_a/；安全解压至其extracted子目录，每ZIP含.HDR及.sp3，CRC检验通过、SHA256见logs/swarm_candidate_download.json。取第三日是为了覆盖UTC末端及数据边界，不等于计划运行72小时轨道。

## 实际格式优先于产品目录概述
目录概述为SP3c、ITRF、GPS、10秒，实际0203样本为`#dV`，即SP3-d且有速度；头部参考框架IGS20、`%c`时间GPS、每文件8640历元，P/V各8640条、单星ID L47，三日共25920点。IGS20为与ITRF2020对齐的IGS参考框架实现，见[IGS参考框架说明](https://igs.org/wg/reference-frame/)。不能把IGS20直接命名成TEME或WGS84，也不能声称普通ITRS变换已校正全部框架实现差异。
实际P位置单位km，V速度dm/s；reader分别乘1000和0.1输出SI。缺失clock为999999.999999，不当成位置；正式时钟/不确定度解析尚未实现。
文件名/HDR有效期标UTC，如首文件从03-20 23:59:42开始；SP3内部首时刻为03-21 00:00:00 GPS，二者对照差18秒。HDR产品创建日期为2026，样本观测日期为2023；按后处理参考使用。
[SP3-d格式规范](https://files.igs.org/pub/data/format/sp3d.pdf)已保存data/raw/meeting_sources/sp3d_spec.pdf。
SP3是reduced-dynamic精密定轨参考，包含受力/观测处理假设；不是绝对真值。官方目录的厘米级描述不能替代本日期质量报告；SP3xVAL与机动/姿态标记尚未获取。当前短记录未给出机动旗标，不能据此判断无机动。

## 历史TLE：已取得，但标明归档链路
NORAD39452/COSPAR2013-067B，TLE标题SWARM A；SP3文件A/任务头对应同星，L47是SP3标识，不是NORAD。
Space-Track gp_history同日查询无凭证返回401，未登录成功，也未注册或使用任何用户凭证。若后续需官方逐条来源/发布时间，应由用户已授权账号或其导出记录补充。
[ETH Satellite Database](https://satdb.ethz.ch/)说明其从CelesTrak抓取归档；[查询API文档](https://satdb.ethz.ch/api-documentation/)公开GET，不需认证。本次实际取得8条，分页next=null，69字符行、两行NORAD一致及两行mod10校验全部通过。原查询见logs/meeting_sources_http_round3.json；原响应和TLE保存data/raw/orbits/tle/。
查询范围03-20到03-23，加before=2、after=0；返回记录包括03-18的前置数据。不把当前最新TLE当作2023历史TLE。
拟定t0前最新历元为2023-03-20 20:30:00.330336 UTC，龄期3.5004638小时；已冻结swarm_a_selected_before_t0.tle，不按后续SP3误差再选最佳一条。详见logs/swarm_tle_audit.json。归档未给出抓取/发布时间，因此“历元早于t0”不证明该TLE当时已经公开；当前可做历史历元对照，严格运营预测需补可用性证据。
没有用TLE的B*反推固定CdA/m；B*不能直接当几何面积或已知阻力系数。

## 卫星属性与其他资源
[ESA任务参数](https://www.esa.int/Applications/Observing_the_Earth/FutureEO/Swarm/Facts_and_figures)给发射质量473kg（含推进剂），不是2023实时质量。不能用卫星外接矩形尺寸直接代替迎风面积。
[TU Delft几何/气动资料入口](https://thermosphere.tudelft.nl/)可用于后续查宏模型和姿态相关面积；本机HTTPS握手超时，尚未取到具体Swarm模型。Cd、2023质量、迎风面积/姿态和机动时间仍未核实，未编造数值。若临时用常数Cd做原型，必须作为假设敏感性实验，不能宣称高精度结果。
未来另需IERS地球定向参数UT1-UTC/极移和冻结闰秒表。Astropy内建ITRS/GCRS/TEME辅助实现，不能忽略速度变换、地球自转或框架实现差异。

## 已做的最小实验
src/evaluation/sp3_reader.py保留原时间尺度，只读单星c/d的P/V；固定字段转换，拒绝缺P/V、重复/不规则历元、未知时间基准与缺位置。scripts/inspect_swarm_sp3.py读取3日，检查连续性/量级、P的中心差分与V一致性，输出results/figures/20261019_swarm_a_sp3_overview.png。
reader5项单元测试通过：真实头与单位、未知时间尺度、缺位置、缺速度、重复历元；logs/sp3_reader_tests.log。检查报告logs/swarm_sp3_inspection.json。中心差分速度残差含10秒截断误差，不能当SP3速度精度估计；图的地心半径不是椭球高度。本次无坐标变换或轨道预测。
