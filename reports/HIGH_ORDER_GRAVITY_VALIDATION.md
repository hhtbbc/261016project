# J3/J4独立数值验证

## 模型定义与范围

采用configs/higher_order_gravity.json冻结的PROJECT_NOMINAL_J2_PLUS_EGM2008_ZONAL34。保留原μ/R/J2；GFZ文件C30/C40先非归一化再按μR^n重表达，不直接混用归一化系数。不是完整EGM2008或完整IERS2023模型，也没有校准SP3。来源、势函数与预注册门槛见docs/HIGH_ORDER_GRAVITY_DESIGN.md。

当前项目非归一化J3=-2.53241015932080123e-06，J4=-1.61989729392585738e-06。源Cbar30=9.57161207093472958e-07、Cbar40=5.39965866638991037e-07；原始部分文件SHA ce9334659955fe001e31b63f77838cd883436ee91830940a8e0836e4bdf55d1e，本次仅16384字节前缀，不声称完整EGM文件已下载。

## 测试与独立公式

新增9项测试，全套142项通过。包括极区/赤道/中纬、J3偶加速度与奇势/J4奇加速度与偶势、r^−5/r^−6衰减、旋转协变、关闭项恢复旧J2的逐元素状态、叠加、非法参数、固定轴能量/轴向角动量和数值收敛。

独立球坐标参考使用[GFZ STR09/02 §4.1](https://icgem.gfz-potsdam.de/docs/str-0902.pdf)正引力势及[ IERS式6.1—6.3](https://iers-conventions.obspm.fr/content/chapter6/icc6.pdf)归一化关系，用源μ/R/Cbar、scipy Legendre及径向/纬向导数转Cartesian；不调用生产加速度公式。生产模型用显式向量多项式。100个固定随机点逐项比较，另做复步长负梯度及中心差分，不以同一个函数自比冒充独立验证。这是独立数学路径，不是另一完整轨道软件或观测精度验证。

|项|球坐标参考最大相对差|复步长负梯度相对差|差分h=10000 / 1000 / 100m相对差|
|---|---:|---:|---|
|J3|3.1893e-15|1.1384e-15|9.5258e-06 / 9.5258e-08 / 9.5666e-10|
|J4|2.9503e-15|5.9210e-16|1.0518e-05 / 1.0518e-07 / 1.0513e-09|

固定门槛为独立/复步长相对2e−12、绝对1e−18m/s²；差分减步需显示二阶收敛，100m相对差<2e−7。全部通过，未放宽阈值。归档的poliastro v0.17 J3参考源也明确自称未完全验证，因此不作为唯一权威测试依据，没有安装/执行该下载源码。

## 固定轴保守合成验证

只用合成初态[6850000,0,0]m、[0,5400,5400]m/s，6000s；不是额外Swarm实验。能量包括中心、J2、J3、J4完整势，轴向角动量守恒，不要求角动量矢量不变。

base能量相对漂移1.981915e-11，轴向角动量9.884538e-12；tight分别6.281642e-13、3.139711e-13。两解最大位置差0.000528165m。严容差收敛；不能把固定轴守恒判据强加到真实时变轴模型。

## 六小时G2收敛与保护

G2 base/tight最大位置差0.058411155m，小于预注册0.5m；G2−G0配对变化0.000015805m，小于max(5mm,最大扰动1%)=19.268161790m。复用已保存G0 tight，未重跑G0。G1没有另加tight，不能声称逐组完整数值误差证明。配对误差中的抵消也不等于单轨绝对准确。

174项保护文件前后SHA不变，含D0—D5和原基础模型；初态小端float64 SHA `194f248cfaa2ea727cf70f834e47034968355249a52c177bb9d4fd3dc49eaee4`与既有D5相同。原RK45、J2、时间/坐标模块未改。原始SP3逐SHA与HDR锚点匹配，冻结EOP/闰秒沿用。没有NaN/Inf、拒绝或异常积分状态。

环境复用.venv310、numpy/scipy/Astropy。仅为读取公开ESA PDF新增项目内pypdf6.21.1和pycryptodome4.1.0，原numpy等数值包未升级；PDF原有AES格式最初缺后端，安装官方PyPI wheel后用普通空口令阅读路径解析，没有破解或尝试访问密码。下载SHA/依赖检查在logs/high_order_pdf_*，环境锁configs/requirements-gravity-20261020.lock.txt。原PDF/全文提取不入Git，第三方模型源码不改。

复现：source scripts/activate_orbit.sh；PYTHONPATH=src python -m unittest discover -s tests -v；python scripts/validate_high_order_gravity.py；python scripts/run_high_order_gravity_comparison.py --run-tag high_order_gravity_v1（静态）；同命令--execute。已有标签/验证输出拒绝覆盖；复现需显式使用独立产物位置，不重放本次授权。
