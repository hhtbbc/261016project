# TIE-GCM 2.0 Linux环境与实际运行检查

## 状态区分

- 原始2.0源码完整性：355个普通文件逐一与原始官方标签压缩包比较，全部相同。
- 依赖：项目内独立前缀已安装并实际使用Fortran/MPI/NetCDF/ESMF。
- 编译与链接：成功，但包含明确记录的GNU12兼容补丁，不能称为未经修改的原始2.0二进制。
- 初始化与默认算例：4个MPI进程的10分钟冒烟与官方默认2002年单日均正常退出，NetCDF密度/高度读取与单位核验通过。
- 科学状态：未完成公开benchmark逐场数值回归、现代编译栈全物理验证；未运行2023场，未完成spin-up或Swarm密度接口。不能把“能运行”升级为“已得到可信2023大气”。

## 初始服务器与隔离前缀

logs/drag_tiegcm_preflight.json记录：Linux/Ubuntu既有环境，gcc/g++/make/cmake可用，PATH无gfortran、MPI、nc-config、nf-config、ESMF工具或csh/tcsh；项目磁盘初始空闲约719 GB，内存信息已保存。未修改系统或其他环境，未用sudo/apt；A100不参与此CPU模型运行。

编译前缀/workspace/data/20261016/.envs/tiegcm。micromamba2.9.0来自conda-forge官方包元数据，下载6988090字节且SHA256匹配后仅安全提取bin/micromamba到项目.local/bin；没有运行网络安装脚本或shell init。包缓存.cache/conda/pkgs、根前缀.local/mamba、临时/日志全部显式指定工作区路径。74包总下载252214893字节，最大单包60389645字节，解压预算4 GB；未下载超过5 GB的单资源。

版本如下，精确build和SHA见logs/tiegcm2_stack_manifest.json，全部包URL/MD5锁见configs/tiegcm-stack-explicit.txt：

|组件|版本|用途|
|---|---|---|
|Fortran|12.4.0|gfortran_impl_linux-64|
|MPI|5.0.8|openmpi|
|NetCDF-C|4.9.2|libnetcdf|
|NetCDF-Fortran|4.6.1|netcdf-fortran|
|ESMF|8.6.1|esmf|

OpenMPI/NetCDF/ESMF均选同一MPI家族；GNU12前端与包中Fortran运行库/模块的兼容由实际编译、链接、MPI运行和NetCDF写读作工程检验，不仅凭包名推断。ESMF构建元数据中有GNU13路径，不代表已经验证所有跨版本行为；这是后续benchmark回归的理由。没有csh也可用受审查的bash/Python构建包装替代旧作业脚本，不运行原脚本中的其他机器路径或提交/邮件动作。

## 安装路径异常：已记录，外部清理等待明确授权

初次micromamba create即使指定项目环境/缓存，仍向/root/.conda/environments.txt新增登记行/workspace/data/20261016/.envs/tiegcm。这是本次隔离检查遗漏造成的实际越界副作用，不能宣称所有写入从未越界。发现后暂停并终止该安装进程，未安装包到全局；没有擅自清理外部文件，已请求用户仅删除该行的明确授权。

随后查看mamba2.9.0官方install.cpp：create_target_directory会register_env，而对已有项目前缀执行install（create_env=false）不会走该分支。因此在工作区手动保留conda-meta/history，采用锁文件download-only→审计post-link脚本→offline install。审计发现的3类post-link仅向PREFIX/.messages.txt写说明；未执行其提示中的CUDA/NCCL安装。第二路径前后外部登记文件SHA256和mtime完全一致，证据logs/tiegcm_safe_install_registry_check.json。脚本均已改用install而非create，未修改HOME/CODEX_HOME。异常详情logs/tiegcm_registry_incident.json。

## 原版源码、构建兼容修改

固定官方tiegcm2.0标签commit da712811d925376ff8ef40ff64bda7cc070ca661；原包SHA与来源见logs/tiegcm_source_acquisition.json。当前完整性复查logs/tiegcm2_source_integrity_current.json证明third_party/TIEGCM2.0未变。补丁只写入experiments/tiegcm2_build_v1的覆盖文件：

1. sphpac.F：lfim/lfin包装缺失theta数组声明，与被调用theta(*)不一致；补dimension theta(*)，符合其文档定义。
2. util.F：将BOZ直接初始化REAL的非标准DATA写法改为整数位型经TRANSFER到binary64；保留原IEEE位图，未静默开启invalid-boz。
3. mud.F：iprm(16)调用需要17元素的mud2cr；其等价COMMON本就有17项且第17项写迭代次数，声明扩为17，与相邻mudmod/muh2cr一致。不是压制越界诊断。
4. 仅nchist.o启用-fallow-argument-mismatch：实际诊断为旧NetCDF F77隐式接口不同调用间scalar/array秩差。审查属性长度1、ndims=0时忽略dimids、REAL*8对应nf_*_double后才作局部兼容；不全局屏蔽类型错误。说明logs/tiegcm_netcdf_rank_review.txt。
5. 本地Make.workspace显式链接-lnetcdff、-lnetcdf和ESMF路径；保持原-fdefault-real-8/-fno-range-check，O2，MPI模式、5°网格。原源码/Makefile不动。

三份统一补丁位于configs/patches/tiegcm2_gfortran12_*.patch。准备新构建目录会自动生成覆盖文件并校验与补丁一致，复现覆盖文件与已运行构建逐字节相同，见logs/tiegcm_build_overlay_repro.json。五次编译尝试完整日志logs/tiegcm2_build_attempt1—5.log保留；最后成功链接。保留的旧库数组边界警告及短暂clock-skew警告不等于已完成科学验证，本次正常执行及输出检验提供实际工程证据。

## 启动文件与实际运行

从官方公开支持目录取得3个已核验小文件，不下载整套1.5 GB包：

- tiegcm_res5.0_mareqx_smin_prim.nc：16993144字节，2002春分低太阳启动完整场。
- gswm_diurn_5.0d_99km.nc：23889780字节。
- gswm_semi_5.0d_99km.nc：23889784字节。

合计64772708字节，下载/NetCDF结构/SHA分别见data/raw/tiegcm2_support/manifest.json和logs/tiegcm_support_netcdf_audit.json。网格72经度×36纬度，lev/ilev各29；默认2002 day80，60 s步长，Heelis高纬固定POWER18/CTPOTEN30、F107/F107A70，GSWM日/半日潮汐，不需要旧GPI驱动文件。它不是2023驱动配置。

单rank第一次因要求不存在的OpenMPI5 osc=pt2pt而失败；检查组件后改为rdma。第二次单rank在第1步60秒墙钟上限终止，根因尚未定位，不宣称单rank可运行。按官方桌面建议改4rank后10步正常完成约2.27秒，因此采用4rank做默认单日。使用TCP/self BTL、ob1、PMIx hash，MPI/PMIx临时路径都设在项目.tmp/mpi；未使用GPU。容器现有root身份仅通过OpenMPI自身确认变量启动，不使用sudo或新增权限。

官方默认单日（2002-03-21 00:00→03-22 00:00）1440步、4rank、60秒步长，returncode=0，墙钟152.248519秒，限额300秒；正常退出。max_launcher_rss_kb=259860仅为子进程统计值，不能冒充4个MPI进程峰值内存总和。模型输出2个NetCDF合计226636752字节。

主历史初始/终点共2时刻，次历史小时采样24时刻；原默认HIST=1 0 0含义是一日，不是一小时。成功日志logs/tiegcm2_default_1day_v1.log，资源logs/tiegcm2_default_1day_v1_resources.json，输出experiments/tiegcm2_default_1day_v1/。所有失败/限时目录也保留。

## 输出单位、缺失值和覆盖范围

实际次历史DEN(time,ilev,lat,lon)单位g/cm³，转kg/m³乘1000；ZG同一网格单位cm，转m乘0.01。默认单日DEN全部有限/正、无掩码，约1.257e-13—1.199e-6 kg/m³（包含约96 km到模型顶的完整垂直域，不能将全域最大值当卫星高度密度）。ZG每列严格递增，顶层全球/全时范围约448.964—513.086 km。

TN为K，UN/VN为cm/s，后续转m/s乘0.01；它们在lev而不是DEN的ilev。次历史TN/风顶层是约9.999e35的缺失占位。由于float32变量搭配float64 missing_value，netCDF4会警告并拒绝自动掩码，不能把它当真实温度或风速。inspect_tiegcm_outputs.py按变量dtype转换缺失标记后显式掩码，默认单日TN掩码62208=24×36×72，正好一个顶层；有效TN约147.721—788.829 K。早期未正确掩码的初步审计日志保留，最终采用*_netcdf_audit.json。

源代码diags.F确认DEN在ilev，fields.F/addiag.F确认ZG在ilev并通过随高度重力计算；Z是定重力定义的位势高度，不能替代ZG。ZG仍是模型几何高度约定，和WGS84椭球高的严格映射须在密度接口阶段验证；不能因均写m就默认两者同义。

本窗口SP3转WGS84高度约460.312—489.989 km，而默认低太阳场部分格点顶低于460 km，故不能保证轨道全覆盖，也不得外推。这仅是2002默认场的覆盖检查，不等于已判断2023动态场的覆盖。

额外示例图results/figures/tiegcm2_default_2002_400km_demo.png在2002-03-22 00:00、原生ZG的400 km处逐列log-linear取密度，全部列都有垂直包围，无外推，密度约3.794e-13—9.357e-13 kg/m³；元数据logs/tiegcm2_default_demo_map.json。明确不是2023年Swarm大气，也不是观测精度验证。

## 复现与尚未完成事项

```bash
cd /workspace/data/20261016
source scripts/activate_tiegcm.sh
python scripts/build_tiegcm2_workspace.py --build-tag tiegcm2_build_new
make -j2 -C experiments/tiegcm2_build_new all
# 指定刚构建的新目录；默认指向已验证build_v1
python scripts/run_tiegcm2_smoke.py --build-tag tiegcm2_build_new --run-tag tiegcm2_smoke_new --ranks 4
python scripts/inspect_tiegcm_outputs.py tiegcm2_smoke_new
# 官方默认单日，300秒上限，仅使用新目录
python scripts/run_tiegcm2_smoke.py --run-tag tiegcm2_default_new --minutes 1440 --ranks 4
```

尚未进行2023仿真。必须先按[HAO正式通知](https://www.hao.ucar.edu/modeling/tgcm/index.php)为2.0更新2015后不正确的IGRF/apex，核验接口/版本，再制作2023驱动、合理初始场并验证spin-up。不直接用3.0替代2.0。官方旧下载表单要求邮箱；本次复用此前已从官方GitHub公开标签取得的源码，并使用无需认证的公开支持文件，没有填写虚假邮箱或绕过表单。若未来所需资源只经表单提供，应等待用户操作。

下一步骤见docs/TIEGCM2_EXECUTION_PLAN.md。本次不继续多日预热或2023仿真。

## 短例重复执行检查

新脚本的build-tag入口已用相同4rank/10分钟重跑验证。首次尝试逐位相同断言失败：主历史双精度TN最大差3.07e-12 K，UN/VN最大差1.29e-10/7.91e-11 cm/s；时间/mtime和次历史float32 DEN/ZG完全一致。差异与并行浮点舍入量级相符，未证明具体产生点；没有为此改模型。按温度1e-9 K、风1e-8 cm/s的后验诊断容差一致，不宣称二进制位级可重复或已完成官方benchmark。日志logs/tiegcm2_smoke_repro_check.json保留初始严格断言失败及所有差值。

400 km示例图的可复现入口：在轨道Python环境执行python scripts/plot_tiegcm_demo.py --output-prefix tiegcm2_default_demo_repeat（使用新前缀，拒绝覆盖已有产物）。该脚本由本次已执行的绘图过程整理，源码语法检查通过；不会启动模型。
