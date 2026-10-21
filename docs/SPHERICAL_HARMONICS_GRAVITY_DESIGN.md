# 完整低阶球谐引力设计

## 冻结模型与范围

采用已有GFZ ICGEM EGM2008文件前缀，不重新下载大型模型。原字节SHA256为ce9334659955fe001e31b63f77838cd883436ee91830940a8e0836e4bdf55d1e，16384字节，完整包含n=0及2—8的所有m=0..n；n=1按地心原点约定为零。源文件及前次下载清单在data/raw/gravity_sources。新模型自身GM=398600441500000m³/s²、R=6378136.3m，tide_free、fully_normalized、静态8×8。C22=2.43938357328313e−6，S22=−1.40027370385934e−6。不是仅m=0，不是全2190阶模型。

来源：[GFZ原系数文件](https://icgem.gfz-potsdam.de/getmodel/gfc/c50128797a9cb62e936337c890e4425f03f0461d7329b09a8cc8561504465340/EGM2008.gfc)、[ICGEM](https://icgem.gfz.de/)、[NGA官方入口](https://earth-info.nga.mil/)。NGA完整压缩包标104MB，本任务直接复用已有低阶前缀。IERS潮汐系统、低阶世变/潮汐、完整相对论时标缩放未实现；系数不是2023实测更新。

H0保持旧GM=398600441800000、R=6378136.6、J2=1.0826359e−3。H1统一EGM2008的J2=−sqrt(5)C20约1.08262617e−3。GM差−300000m³/s²、R差−0.3m及J2更换均明确存在。H1−H0包括这些参数差，不能全部归因于增加阶数。只在同一位置分别计算参数差加速度作量级诊断，不额外传播或拟合。

## 势与稳定计算

机械势U=−GM/r Σ_n(R/r)^n Σ_m Pbar_nm(z/r)[C_nm cos(mλ)+S_nm sin(mλ)]，a=−grad U。归一化N_nm=sqrt[(2−δ_m0)(2n+1)(n−m)!/(n+m)!]，不带Condon–Shortley相位。C00=1包含中心项，因此不得再叠加central_gravity或旧J2。

生产实现用无量纲笛卡尔q=r/R和正则实心球谐H_nm=q^n P_nm(qz/|q|)exp(imλ)。H_mm=(2m−1)(qx+i qy)H_(m−1,m−1)，H_(m+1,m)=(2m+1)qz H_mm，其余按Legendre三项递推。势项为GM/R乘N_nm(C ReH+S ImH)/|q|^(2n+1)。同时递推Cartesian梯度；不除cos纬度、水平半径或sin余纬，精确两极无奇异。float64/complex128内部多项式，公开仅支持已验证0≤order≤degree≤8，不将未验证高阶递推直接推广。

## 地固与惯性

复用EarthFixedFrame和冻结Astropy EOP/闰秒。每次RHS由当前GCRS完整状态转换ITRS，以现有ERFA c2t06a旋转矩阵Q计算地固物理加速度，再用Q.T旋回GCRS；不加入科氏/离心力，也不将地固轨迹二阶导数当引力。包含非轴对称项，必须使用完整绕地球轴的经度相位，不能只用地固Z方向。沿用IAU2006/2000A、TT/UT1/xp/yp，不含观测dX/dY，与旧框架一致。

## 独立验证与预注册门槛

外部参考选用SHTOOLS/Fortran MakeGravGridPoint，omega显式为0，4π归一化无CS相位，返回r/theta/phi向量独立旋回Cartesian。参考不调用生产递推。文档：[API](https://shtools.github.io/SHTOOLS/pymakegravgridpoint.html)、[归一化](https://shtools.github.io/SHTOOLS/real-spherical-harmonics.html)。Orekit网页本次实际返回访问拒绝，不宣称已执行Orekit。

100随机点加赤道/±89.9°近极（外部Fortran不支持精确极点，生产实现另测精确两极连续性），逐分量rtol2e−12/atol2e−12m/s²；势负梯度中心差分h=10km/1km/100m显示二阶收敛、细步相对差<2e−8；中心、同参数J2/J3/J4解析结果一致；C22/S22经度依赖与极限连续；完整力旋转与既有框架一致。通过前不运行真实传播。旧J3/J4独立球坐标/复步长属于不同数学路径，非外部软件检验；旧J4 RMSE增加不等于公式错误，部分力项抵消及缺失项仅为假设。

## 运行授权与门禁

一次短时预检后，只允许H1六小时base/tight各一次。单历元SP3初态、UTC起止2023-03-21 00:00:02—06:00:02、60秒输出、原容差/步长和冻结时间数据；H0/G1/G2只读。base/tight最大位置差<0.5m；短例不得有NaN/Inf或初始化漂移；不按SP3好坏选择参数。独立一次性文件防重复，失败不自动重试。配置及源/旧数据SHA在独立experiments/spherical_harmonics_v1。所有结果PROVISIONAL / HINDCAST / NO_DRAG，不是正式精度排名。
