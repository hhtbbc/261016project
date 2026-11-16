# 多卫星密度目录与实际样本质量审查 v1

2026-11-16。独立tag`thermosphere_observation_assimilation_feasibility_v1`。本轮只新增一个Swarm C日产品，A原件只读复用，B只元数据；没有密度校正、跨星拟合或轨道传播。

## 1. 官方产品目录

来源：[VirES官方DNS示例](https://notebooks.vires.services/notebooks/03l1_demo-dns)、[HAPI元数据服务](https://vires.services/hapi/)、各产品resourceURL指向的ESA handbook。TU Delft主站本轮服务器TLS握手超时，网页工具也未读到正文；以下已访问事实来自ESA/VirES，不能声称从TU门户实际下载了数据。

|产品ID|反演来源|当前服务目录覆盖/采样|目标日期证据与角色|
|---|---|---|---|
|SW_OPER_DNSAPOD_2_|GPS/POD非引力加速度反演|2014-01-01—2026-09-30，30s|2021/2022 Mar24原件0301存在；校正候选A|
|SW_OPER_DNSBPOD_2_|同类POD|同上，30s|两个目标日0301具体ZIP均列出；**未下载/未读数值，保留验证**|
|SW_OPER_DNSCPOD_2_|同类POD|同上，30s|2021目标文件已列出未下载；2022原件0301本轮取得；方法开发C|
|SW_OPER_DNSAACC_2_|POD+加速度计|2014-02-01—2025-11-30，10s|仅服务元数据，日文件/版本/有效记录未核实|
|SW_OPER_DNSBACC_2_|POD+加速度计|2015-03-01—2025-11-30，10s|仅元数据，B数值仍禁读|
|SW_OPER_DNSCACC_2_|POD+加速度计|2014-02-01—2026-05-31，10s|仅服务元数据，具体目标日未核实|
|GF_OPER_DNS1ACC_2_|GRACE-FO1加速度计|2018-05-29—2026-04-30，10s|跨高度后续候选；具体2021/2022日文件、版本/高度未取得|
|GR_OPER_DNS1ACC_2_|GRACE1加速度计|2002-04-04—2017-10-31，10s|历史案例，不覆盖2021/2022|
|CH_OPER_DNS_ACC_2_|CHAMP加速度计|2000-07-29—2010-09-04，10s|历史案例，不覆盖2021/2022|

目录年度范围**不证明具体一天有有效数据**。只有A本地原件、C本轮原件、B/C具体日文件清单得到相应证据；其余不标PASS。详见`product_catalog.csv`与`product_availability.json`。

密度字段单位kg/m³，Timestamp为UTC，Latitude_GD/Longitude_GD为GRS80大地坐标、Height_GD单位m。HAPI Height_GD的description误写“GRS80 latitude”，原文保留并标注；现有0301产品合同/项目先前GPS几何审查支持使用GRS80解释，但**本轮未取得C同期SP3作独立几何核验，2023 A/SP3经验不能代替2021/2022实测核验**。

POD区分`density`瞬时和`density_orbitmean`；本轮只读取前者。ACC集合有些仅暴露density、没有validity_flag，不能套用POD码表或将有限点全视为正式有效。GF/GR/CH还可能有orbitmean专用质量标志，要按实际版本另审。

POD与SP3共享GPS/POD及气动/辐射压处理信息；Swarm A/C近邻且方法同源，不能因网站/卫星名称不同就称独立绝对真值。ACC提供另一种测量途径，但仍依赖姿态、辐射压和气体表面模型，可能与其他产品共享处理输入。

## 2. 新C文件和下载预算

已具体列出并下载：
`SW_OPER_DNSCPOD_2__20220324T000000_20220324T235930_0301.ZIP`，**139647字节**。

ZIP SHA256：`4c62f9ecbccfdd4048dfa154b375aaea78d833ed40aaee026e2dec7db97387cd`。

解压CDF为191682字节，SHA256：`40b3ce3c0c8617c29de310effc44d5f16145f4f355c24a95b6a8938df0becf37`。官方清单长度匹配、ZIP CRC、成员路径/大小/SHA通过。发布方清单未提供SHA，故是本地完整性与后续追溯，不冒称与官方SHA比较通过。

两星B目标ZIP为20210324的140650字节、20220324的140015字节，仅查看名称/版本/大小/目录属性，未获取密度数据。

本地保存的全部新增官方目录/网页/代码元数据与C ZIP共3351175字节；另下载作者Code.rar237372字节，总**3588547字节（约3.42MiB）**。把参考资料也保守计入10MiB仍满足预算。没有重复下载A原CDF/ZIP，无论文大型mat或全年度档案。服务器PDF403/站点超时记录保留，未绕过认证。

## 3. 实际质量检查

|样本|原始/有效条数|UTC/间隔|实际高度km|瞬时密度kg/m³|大地纬度范围|
|---|---:|---|---|---|---|
|A 2021-03-24|2880/2880|00:00—23:59:30，30s|431.534—461.523|1.47036e-13—9.01432e-13|-87.3742—87.3731°|
|A 2022-03-24|2880/2880|同上|425.249—454.811|3.41775e-13—2.40374e-12|-87.3721—87.3709°|
|C 2022-03-24|2880/2880|同上|425.245—454.801|3.59446e-13—2.43108e-12|-87.3571—87.3559°|

三组原码均0（各2880条），无时间缺槽/重复/逆序，密度正且有限，经纬/高度范围检查通过；质量有效率100%。规则依据**实际0301 CDF和同产品HAPI**：0 nominal、1 anomalous、未知码隔离；不因名义质量正常宣称反演无误差。保留完整原标志及拒绝规则，不按与模型的一致性筛选。

C与A2022高度范围接近，不等于处于相同空间位置或处理误差独立。本轮没有把两星同UTC密度大小当精度排名，没有估计相对尺度或校正效果。

## 4. 可复用接口与实物证据

`src/observations/density_catalog.py:read_swarm_pod`复用既有2022读取器、UTC转换和0301质量逻辑，新增版本/SHA/身份/坐标范围检查与统一记录。提供mission/satellite/product/version/UTC/lat/lon/height/density/flag/source/SHA/coordinate/retrieval等字段；全部8640条留本地`unified_observations_local.csv`，公开`observation_file_index.csv`只含小型来源索引。未来ACC/GF读入器尚未实现，目录存在不代表可读取。

B值访问在打开文件前抛出ReservedObservationError。14项新CPU测试包括版本/损坏SHA拒绝、质量码、UTC历史窗口排除当前与未来、B保护、EOS单位与完整Restart结构拒绝。实际A/C文件读取和质量表是额外实物证据。

4张实际图位于结果目录：

- `01_observation_density_UTC.png`
- `02_actual_height_UTC.png`
- `03_latitude_density.png`
- `04_satellite_height_coverage.png`

图中注明UTC、GRS80、瞬时密度/单位与反演限制。原件只读，不公开重新分发；小图和汇总按项目规则同步。

GRACE-FO高度尚未实测，不虚填固定高度。本地既有500km共同域：2021同年四轨共同仅67.1462%，2022为100%，这不是GRACE-FO实际沿轨覆盖率；其位置/高度需独立取得后逐8邻列检查，不照搬论文把数据移到400km后称独立验证。
