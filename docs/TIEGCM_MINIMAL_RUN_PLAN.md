# TIE-GCM 2.0最小运行方案（尚未编译/仿真）
核验日期2026-10-19。目标是为Swarm-A的48小时历史实验准备可信密度，先完成可重复短例，绝不启动多年数据生成。

## 官方版本与源码证据
[官方仓库](https://github.com/NCAR/tiegcm)当前主线并非2.0；实际取得正式标签`tiegcm2.0`，固定commit `da712811d925376ff8ef40ff64bda7cc070ca661`，而不是beta标签或master。GitHub API的标签/树清单保存在data/raw/meeting_sources/。
原包data/raw/tiegcm2.0_da712811d925.tar.gz，11,770,244字节；SHA256=4c9c43cdb2c8ad20fef45a711eec5b8cc8c079511c18de8cde576cd7b31a352d。安全检查374成员（无路径穿越/链接/设备文件）后解压third_party/TIEGCM2.0，不修改原版。源码来源、摘要及未执行状态见logs/tiegcm_source_acquisition.json。
许可为仓库自带NCAR学术研究许可，保留原文件，不冒充Apache许可。旧下载页可能要求邮箱，官方GitHub标签API本次无需邮箱或登录；不为下载虚构邮箱。

## 当前服务器能否部署？
硬件资源充足不代表软件栈已就绪：logs/meeting_environment_audit.json显示make/cmake/gcc/g++可用，但PATH无gfortran/ifort/ifx、mpif90/mpifort/mpirun、nf-config/nc-config；ldconfig未找到系统级相关库，未发现可直接使用的编译栈。csh/tcsh也未找到。Python netCDF4已存在，但不提供完整、ABI兼容的Fortran/MPI/ESMF开发栈。
[官方编译说明](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/build.html)及本地scripts/Makefile、Make.gfort_hao64确认依赖：Fortran、MPI、NetCDF及ESMF。现代NetCDF通常需要独立netcdf-c/netcdf-fortran；不能只链接-lnetcdf假定已有Fortran接口。ESMF用于地理/地磁网格重映射，不能遗漏。
结论：当前不能直接编译运行；在工作区内配置一致的依赖栈有可行路径，但未实际验证，不能承诺Ubuntu24.04上无修改即可成功。A100不是此Fortran CPU模型的现成加速条件。

## 不修改系统的候选部署路径
后续先做包元数据/体积/ABI审计，优先项目内独立前缀`.local/tiegcm-stack`或`.envs/tiegcm`，缓存`.cache/conda`、临时`.tmp`。可评估受审查的micromamba/conda-forge包组合，或项目内源码构建；今天没有安装管理器、执行安装脚本或编译。
必须固定gfortran版本、同一MPI实现、NetCDF-C/Fortran、ESMF版本和编译器ABI，记录所有构建日志/锁定包。源码Make.gfort_hao64使用-fdefault-real-8及旧外部路径，现代GNU编译器可能暴露接口/实参问题；不得随意屏蔽报错或默认添加-fallow-argument-mismatch。先判断正确接口与精度，再以补丁记录最小兼容修改。
保留原Make/job，新增本地Make配置和受审计bash包装，或仅在项目前缀提供csh。模型2.0要求MPI，即使只有1个rank也不能擅自改为不支持的无MPI模式。ESMF必须与选定编译器/MPI匹配，不能复用未知ABI库。
所有modeldir/execdir/tgcmdata/output/OUTPUT/SECOUT都用工作区绝对路径；不要执行原job中/hao、/home、MSS或邮件提交动作。

## 2023运行必须先处理的地磁问题
[HAO官方通知](https://www.hao.ucar.edu/modeling/tgcm/index.php)指出原2.0发布版在2015年后IGRF不正确，要求更新src/apex.F90或使用3.0。本项目优先2.0，因此将来以“2.0+官方地磁更新”的单独工作副本构建，公开标注与纯2.0区别。
已只读保存更新apex.F90，来源固定commit `84185ee0b97307567c78e32ce85643b48a5cc1a9`：data/raw/meeting_sources/tiegcm_apex_update.txt。尚未替换/编译/验证接口或系数范围。不能把它的可下载当作兼容性测试已通过，也不能静默转3.0冒充2.0。早前FourCastDEN论文采用何种2.0修订仍待作者说明，本项目不假设完全相同。

## 初始场、边界与驱动
[官方QuickStart](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/quickstart.html)提供季节性启动场与默认例；对应本地scripts/tiegcm_res5.0_default.inp：2002年day80、5°、STEP=60s、SOURCE_START=80 0 0，Heelis固定低太阳活动条件及GSWM日/半日潮汐。
以下只HEAD检查，均HTTP200，未下载主体（logs/tiegcm_support_head.json）：

|资源|实测Content-Length|用途/限制|
|---|---:|---|
|tiegcm_res5.0_mareqx_smin_prim.nc|16,993,144|默认春分低太阳启动场，不是2023实际分析场|
|gswm_diurn_5.0d_99km.nc|23,889,780|日潮汐下边界|
|gswm_semi_5.0d_99km.nc|23,889,784|半日潮汐下边界|
|gpi_1960001-2017019.nc|1,751,352|旧驱动模板，覆盖不到2023，不能直接用于候选时段|

原始目录 https://download.hao.ucar.edu/pub/tgcm/data/tiegcm2.0/ 。三个默认必要场/边界合计64,772,708字节；这只是默认例最小资产候选，未验证NetCDF内容、所有分支是否另需文件。按需要下载单文件而非整份长期数据/全部2.5°包。
真实2023仿真需合适季节/太阳活动的初始完整场或可靠restart，并连续驱动预热至评价窗口；FourCastDEN预处理NPZ不含完整离子/组成重启状态，不能直接当SOURCE。

### F10.7与Kp获取和制作
[GFZ数据/API](https://kp.gfz.de/en/data)本次无认证返回200，已取：
- Fobs及Fadj：2023-01-31至05-05，各95日，含为居中81日均值准备的前后支持。
- Kp：2023-03-12至03-25，共105个3小时值（含右端点），用于预热与gpi插值边界。
原响应data/raw/meeting_sources/gfz_*spinup_support.txt和gfz_Kp_extended_support.txt，核验logs/meeting_driver_audit.json。03-20/21/22的Fobs为156.1/151.6/158.9 sfu；单位1sfu=1e-22W m^-2 Hz^-1。
必须区分观测Fobs与1AU校正Fadj、每日F107与F107A、Kp与Ap。不能把Kp直接作为经验MSIS的Ap。选择TIE-GCM/经验模型所需通量定义和均值/时间滞后后再制作驱动，记录出处与缺值规则；当前还未决定最终通量约定或生成生产驱动。
本地src/gpi.F读取year_day、f107d、f107a、kp(8,ndays)，且F107插值需要当前日前后2天；需保留边缘支持，遵循源码的插值时标。Heelis从Kp推高纬power/ctpoten，不得同时手工固定这些参数而掩盖动态Kp。
居中81日或事后真实太阳/地磁驱动用于离线hindcast可行，但它们含预测时刻之后的信息；须标记“给定真实未来驱动的历史比较”，不能宣称运营时完全自主预测。这与禁止借未来SP3拟合轨道初值分别管理。

## 两级最小运行与资源门槛（未来执行方案）
1. 编译/数值冒烟：先静态审计全部输出路径、构建一次，以5°/60s默认2002例、MPI 1 rank、10—60分钟模拟时长验证退出码、完整日志、restart可读、密度/高度有限及正确单位。增加时长前测墙钟、内存、输出体积，不照搬旧NCAR机器的速度估计。此级结果不能当2023可信大气。
2. 2023历史试验：验证更新地磁与2023驱动/初始场配置。评价前设置独立预热区间；暂以3天和7天为待评估方案，不把其当官方保证。由同一物理驱动推进，比较评价前段沿轨/全球log密度差与趋势；预先设定例如沿轨相对差1%及最大差阈值作为工程收敛目标，再做敏感性，不根据轨道验证误差择优。条件不收敛就延长/换初始场，不能只舍弃首小时或武断宣称“三天必够”。
3. 首个10—60分钟CPU测试亦须在后续当天指令和资源评估完成后才启动。多日spin-up不在今天授权执行范围；不进行20年模拟、训练或长期全局输出。
4. 两天评价窗口至少覆盖至末时刻并留时间插值余量；所有气象数据、restart、驱动、输出checksum和源码补丁要进入实验manifest。

## 输出与密度查询接口
保存primary供restart、secondary供应用。SECFLDS至少包括DEN、ZG，并建议TN/UN/VN/WN、ZGMID用于核对；Z/ZG虽常被强制输出也要实际检查文件。建议先10分钟secondary输出试运行，再检验1/5/10分钟输出对沿轨插值误差和体积的影响；不是直接沿用论文1小时输出就认为足够。STEP与输出间隔不是同一概念。
官方网格为log-pressure ln(p0/p)，不能把lev值当km。尤须以实际变量维度及源码为准：本地src/diags.F第72附近定义DEN单位g/cm3、levels=ilev；mkdiag_DEN说明rho在界面；ZG也是界面几何高度，ZGMID在lev。官方grid概述将一般中性量归到中点，不应据此误配此诊断DEN。
[网格/高度说明](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/grid.html)区分位势/几何高度。DEN查询优先配同位ZG（cm→m），DEN×1000→kg/m³；不要用Z代替ZG，也不要把TN的28有效层索引直接当DEN29层。
未来读取器必须按NetCDF变量名/维度/units重排，处理time.units、calendar、缺值和单调高度。查询位置的地理纬度定义/几何高度参考面需与TIE-GCM原坐标明确核对；MSIS所需椭球地理高度也必须明确，不能默认地心半径减常数完全等价。
空间方案：经度周期扩展、水平双线性权重；先在每个邻近柱按其自身ZG将log(rho)插到目标高度，再水平插值，最后按两个UTC时刻线性插值；文档规定顺序，不假设这些操作可交换。极区不擅自向缺网格区外推；单独定义并验证极帽策略，否则失败。超模型顶/底、缺值/非正密度、无时间包围或非单调高度必须报错/标记无效，不静默夹取或以MSIS填补C结果。
今天只有源码和接口方案，尚无本项目TIE-GCM生成密度，不能宣称C已完成。
