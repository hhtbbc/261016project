# 独立大气阻力模块与合成验证

## 实现范围

新增src/orbit/drag.py和src/atmosphere/density_interface.py，未改变原中心引力、J2、积分器或评价模块。接口已运行并通过独立物理测试；没有Swarm-A阻力精度结果，也没有经验模型或TIE-GCM密度接入轨道的实验。

阻力a=−0.5*rho*Cd*A/m*|v_rel|*v_rel，单位统一：rho kg/m³、Cd无量纲、A m²、m kg、速度m/s、加速度m/s²。维度为(kg/m³)(m²/kg)(m²/s²)=m/s²。非法密度/参数/非有限输入报错，不能悄悄截成0。

## 相对速度及参考框架

输入积分状态为GCRS。EarthFixedFrame复用冻结EOP、Astropy完整状态变换，将位置和速度转至ITRS。v_ITRS已包含坐标系随时间变化的贡献，不能再额外减一次omega×r。共转大气在ITRS速度为0，因此v_rel_ITRS=v_ITRS；有风时v_rel_ITRS=v_ITRS−wind_ITRS。得到的物理阻力加速度用ERFA同一旋转矩阵Q的转置转回GCRS，只旋转力矢量，不加科氏/离心项。

等价的简化固定角速度公式是v_rel_inertial=v_inertial−omega×r−wind_inertial；它仅用于明确标注的合成框架，真实EarthFixedFrame不把GCRS Z固定当自转轴。

共转假设忽略热层中性风，尤其可能遗漏高纬/扰动期风效应。WindProvider要求相对地面的中性风，Cartesian ITRS m/s；局地东/北/上需另做正确旋转，不能用离子漂移冒充中性风。

DensityQuery包含标量UTC、ITRS位置m、WGS84经纬度和椭球高m。DensityProvider.density_kg_m3可替换真实密度来源；ConstantDensityDemo明确只供合成测试。TIE-GCM原生高度/纬度约定可能不同，须由其适配器完成映射，不能直接把椭球高当压力层或ZG。

DragProperties要求参数来源说明；支持properties_provider(query,v_rel)回调，预留姿态面积和Cd计算。没有内置“Swarm默认质量/Cd”。DragForce.evaluate返回密度、相对速度、加速度、参数和查询信息，供后续记录；__call__适配既有make_state_derivative，积分器无需修改。

## 验证与合成实验

最终全套28项测试通过，包括新增6项阻力测试：零密度、零相对速度、反向耗散、rho/A/m线性比例、SI量级、非法参数、完整坐标系共转/风速/面积回调、查询接口以及轨道能量-功一致性。测试中的地固静止点GCRS速度>400 m/s，但完整变换后相对共转大气速度接近0；避免了直接把惯性速度当相对速度的错误。

合成演示值（均不是Swarm-A）：400 km理想圆轨道，m=100 kg、A=1 m²、Cd=2.2、固定rho=1e-12 kg/m³，恒定角速度7.292115e-5 rad/s、零地固风。只含中心引力+阻力，传播3圈，用中心引力能量变化检查阻力做功。独立解析量级检查中v_rel=7500 m/s时加速度为6.1875e-7 m/s²。

完整合成轨道：初始相对速度7174.288630510 m/s，初始阻力模5.66174591e-07 m/s²；传播16660.872813757 s。比机械能变化-72.335582368 J/kg，积分v·a_drag所得比功-72.337376235 J/kg，相对差2.4798615e-05；无阻力对照能量变化0.001793601 J/kg。基准/更严设置最大位置差0.005236230 m。

本合成顺行轨道比共转大气更快，所有采样v·a_drag<0，机械能下降。一般存在风或超同步能量交换时，惯性能量不一定单调下降；普适的是a_drag·v_rel≤0，不能强制任意轨道惯性能量单调。力学测试仅验证实现/数值，不验证真实密度或Swarm参数。

## 复现与输出

```bash
cd /workspace/data/20261016
source scripts/activate_orbit.sh
python -m unittest discover -s tests -v
python scripts/run_drag_synthetic.py --run-tag drag_synthetic_repeat1
```

脚本使用独立的UniformRotationDemo，明确不是实际EOP框架；真实框架另有坐标/共转测试。新run-tag保留已有实验。

- tests/test_drag.py；logs/drag_tests_v2.log：28项通过，v1的27项日志保留。
- experiments/drag_synthetic_v1/summary.json、states.npz；logs/drag_synthetic_v1.log。
- results/metrics/drag_synthetic_v1_energy.csv；results/figures/drag_synthetic_v1_energy.png。
- 参数核查docs/SWARM_DRAG_PARAMETERS.md；后续对比协议docs/DENSITY_COMPARISON_DESIGN.md。

现有限制是模型接入效率尚未针对长时RK45优化；EarthFixedFrame每次使用完整Astropy转换，优先正确性。未来若缓存矩阵/导数，应新增相同状态/速度误差检验后再做性能对照。本次到接口与合成验证停止，没有真实卫星阻力定量结论。
