# TIE-GCM 2023 地磁更新验证

本次是2.0主体 + 官方2025 apex更新 + 已记录GNU12兼容覆盖层，不是未修改的官方2.0，也不等于3.0。原始源码及历史结果保留。

## 官方来源及范围

[HAO官方通知](https://www.hao.ucar.edu/modeling/tgcm/index.php)指出旧2.0在2015年后地磁处理有问题。采用[固定提交源码](https://raw.githubusercontent.com/NCAR/tiegcm/84185ee0b97307567c78e32ce85643b48a5cc1a9/src/apex.F90)，commit `84185ee0b97307567c78e32ce85643b48a5cc1a9`。当前GitHub文件提交元数据与既有归档一致。源SHA256 `7dc94d3826d1b8d555fa6a6dea26e2a3788fbca2a86581aff3bcdefb52c5cdc3`；补丁SHA256 `336086a838722957e65390a46eae552e743f3d2707b839d95dc59a2e3448519e`。完整旧/新源哈希见experiments/tiegcm2_apex2023_v1/apex_provenance.json。

新cofrm包含2020、2025主场及2025—2030长期变化系数；2023在2020/2025之间线性插值。程序允许1900—2035，但2030后明确降低准确性警告，不能把代码接受日期当科学有效期。[NOAA IGRF-14](https://www.ncei.noaa.gov/products/international-geomagnetic-reference-field)2024发布，2025—2030为预测SV段。本次属于事后IGRF14时代系数hindcast。

**系数精度限制**：NCAR源码2020 g10=-29403.4 nT，而[NOAA表](https://www.ngdc.noaa.gov/IAGA/vmod/coeffs/igrf14coeffs.txt)DGRF2020为-29403.41 nT；官方NCAR保留较低小数精度。不得宣称全部195项逐项与NOAA精确一致。NOAA网页可读，容器urllib/curl下载均TLS失败；未伪造本地NOAA文件。保留官方更新，不自行替换系数。

## 编译与独立验证

构建目录experiments/tiegcm2_apex2023_v1，原2.0实际文件名本来就是apex.F90，并非通知中的apex.F。准备脚本首次断言旧名称失败（logs/apex2023_prepare.log），已修正，记录logs/apex2023_prepare_corrected.log。Make生成Srcfiles只有一个apex.F90，Depends指向本地覆盖层，链接只含一个apex.o；nm三个关键符号各一次，logs/apex2023_symbols.txt。

编译make -j2成功，日志logs/apex2023_build.log。仍有既有时钟偏差/老式Fortran警告，不代表全面科学移植认证。getapex使用的apex_mka/apex_mall/apex_q2g接口链接通过。

独立Python球谐势梯度与实际Fortran feldg在2023.2三处Cartesian点核对，最大差1.956e-5 nT，小于0.01 nT。它独立检查**算法实现**，共享NCAR系数，不能替代独立系数表认证；点包括数学延拓位置，不是三颗卫星观测。记录logs/apex2023_independent_field_check.json及field_values.txt；驱动源/可执行在experiments/tiegcm2023_field_check。

## 10分钟默认例

source scripts/activate_tiegcm.sh；python scripts/run_tiegcm2_smoke.py --build-tag tiegcm2_apex2023_v1 --run-tag 新标签 --ranks 4。

本次2002默认10分钟、4rank、60秒步长，returncode=0、NORMAL EXIT、墙钟2.269776秒，60秒超时限制。日志logs/tiegcm2_apex2023_smoke_v1.log及_resources.json，NetCDF检查同名前缀_netcdf_audit.json。没有运行2023模型。

相对旧2002短例，次历史DEN最大绝对变化6.939e-18 g/cm³，ZG 4 cm，TN 1.221e-4 K，UN 0.03125 cm/s、VN 0.01959 cm/s；主历史TN 9.160e-5 K。详见logs/apex2023_default_comparison.json。更新历史场系数可能造成小变化，因此未要求逐位相同。此短例只验证运行链路，不验证2023电离层/热层科学准确性。
