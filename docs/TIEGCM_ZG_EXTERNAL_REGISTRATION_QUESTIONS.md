# TIE-GCM原生ZG外部登记：维护者咨询草稿

状态：仅草稿，未发送。收件人：NCAR/HAO TIE-GCM维护团队；本轮没有独立核实具体联系人邮箱，不猜测。

## 已核实、尚待确认

我们独立TIE-GCM 2.0算例使用`ibgrddata=0`、默认`zbound=136.291/sqrt(2)×1e5 cm`及GSWM日/半日潮；这不是已证明与FourCastDEN作者原运行配置完全相同的声明。

当前实际编译apex覆盖层与旧S7冻结SHA一致。它的`req=6378.160km`、逆扁率298.25属于磁坐标辅助例程；calczg另用纬度相关经验重力及有效半径。不能因为apex接受大地坐标就认定ZG是WGS84、GRS80或该旧椭球高。

## English email draft

**Subject: Clarification of geographic latitude and external height registration of TIE-GCM 2.0 ZG**

Dear TIE-GCM maintainers,

We are working on reproducible thermospheric density prediction and comparisons with Swarm-A POD-derived density. We use TIE-GCM 2.0 with the official post-2015 apex/IGRF update, retaining the original model physics. Our independent runs use the default lower-boundary background (`ibgrddata=0`) with migrating diurnal and semidiurnal GSWM tides. The background geopotential height is set by `zbound=136.291/sqrt(2)*1e5 cm`.

In our source, `addiag` initializes the bottom Z from the lower-boundary height. `calczg` sets the bottom ZG equal to Z and integrates upward using neutral temperature, molecular mass and empirical latitude/height-dependent gravity, with an extrapolated top interface. The apex helper uses an equatorial radius of 6378.160 km and inverse flattening 298.25, whereas `calczg` has a different effective-radius formulation.

We would like to register native DEN/ZG columns at Swarm geodetic locations, whose external coordinates are provided on GRS80 and can also be expressed on WGS84. Could you please clarify:

1. Is the model geographic latitude intended to be geodetic latitude, geocentric latitude, or a spherical-model convention, and is there a prescribed external ellipsoid?
2. What external reference surface defines the zero of the default lower-boundary height and geometric ZG? Is it an ellipsoid, mean sea level/geoid, a reference sphere, or an approximate conventional altitude?
3. Is ZG intended to share the apex helper's reference ellipsoid, or are the magnetic-coordinate and thermodynamic-height conventions independent?
4. What is the recommended, version-appropriate procedure for comparing DEN on native ZG with satellite densities at GRS80/WGS84 geodetic altitude? Are there example routines, validation cases or documented accuracy limitations?

We have not equated Z with ZG, applied fitted height offsets, or released our formal external density adapter. Our comparisons currently retain explicit provisional coordinate hypotheses. We would appreciate documentation or a recommended registration example before using the density fields in a physical orbit-validation experiment.

Thank you for your guidance.

Best regards,
[Name / affiliation]

## 回答后需要的验证

先保留原文与版本/配置适用范围；数学变换再以独立算例检查，经双方输入定义和误差预算验证后才审查放行。若回复只推荐近似几何高度，应按有界工程约定立项，不能自动称其为精确登记。不得用当前2023残差拟合一个偏移替代官方定义。
