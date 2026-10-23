# 2021年第二完整初始场审查

本报告属于独立TIE-GCM数据质量研究。A为已有2021连续轨迹，B仅更换官方完整初始场；没有重新运行A，没有训练模型。

## 来源与身份

实际访问[NCAR官方TIE-GCM 2.0支持目录](https://download.hao.ucar.edu/pub/tgcm/data/tiegcm2.0/)，本地保存目录响应及请求元数据。目录提供5°和2.5°的mareqx/climatology、smin/smax文件。现有A使用5°mareqx_smin；本次只新增下载5°mareqx_smax一个文件，未下载气候态或2.5°资产。文件名只用于定位，兼容性由实际内容验证。

B原始文件16,993,144字节，SHA256 `a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7`；A源SHA256 `180475215a4922e9c55a77e80153cf641bc8fbb2b8d52633b4686ddee6942fff`。二者原始文件不修改，B下载后设只读。

B为NETCDF3_CLASSIC，history_type=primary，run_type=initial，实际记录2002年DOY80 00:00。内部model_version=tiegcm_trunk、svn1249、生成日期2016-02-01，上游source_file包含1.95资产路径。因此准确身份是“官方2.0支持目录提供的完整初始化资产”，不能把内部版本字段说成字面2.0或隐去上游历史。

模型许可见`third_party/TIEGCM2.0/src/tiegcmlicense.txt`：NCAR TIE-GCM Open Source Academic Research License，允许相应学术研究用途，有非商业/非运行产品限制。官方目录未发现单独数据许可证；不虚构CC许可，不向GitHub重新分发原始初场。

## 实际兼容性

- lat36/lon72/lev29/ilev29，与A和作者static坐标逐元素一致。
- 源码读取契约要求的34项当前状态、_NM历史状态及下边界均齐全，float64，维度/单位与A相同。
- SOURCE_START=[80,0,0]合法，实际模拟START_YEAR=2021、START=[75,0,0]。2002记录选择不等于2021真实大气初态，也不是Restart一致性验证。
- TN初始最大差696.299966K，证实不是复制相同状态。B源F107/F107A=200/200，A=70/70；这些仅是初场身份及冷echo继承值。两组从首个60秒步开始使用同一2021实际GPI，不以源标量固定后续强迫。
- 原始Kp=1e36为未计算填充值，只能标冷记录N/A，不能当有效地磁驱动。暖态驱动必须通过逐日志及NetCDF核查。

首次静态检查器错误地要求TI/TE顶层有效，检查因此停止，模型当时未启动。复核A/B均为相同原生顶层填充，`settei.F:638–659`明确将lev1的TI/TE输出设为spval；修正的是检查器的已知顶层掩码契约，未修改数据、源码、物理方程或预注册比较门槛。错误及依据保留在`initial_checker_incident.json`。

完整审计：`experiments/tiegcm_2021_spinup_initial_condition_v1/initial_state_audit.json`；下载身份：同目录`second_initial_download.json`。本次未执行额外10分钟模型预检，静态完整读取契约通过后只启动一次正式B积分。

## 同条件冻结

B namelist直接读取A冻结文本，仅替换SOURCE绝对路径；SOURCE_START无需改变，LABEL及其他参数也保持A原值。原label不代表初场相同，实验身份由独立目录、配置与SHA确定。可执行文件、apex、GPI、HEELIS/GSWM、60秒步长、4MPI/OMP1、输出间隔/SECFLDS完全一致。初场包含的组分、热状态和历史状态作为整体变化，不能将其称为只改变太阳通量的单因素物理实验。

预注册规则和SHA在启动前保存于`frozen_comparison_rules.json`，严格保留DEN5%、TN10K、水平风矢量20m/s、非痕量组分5%、至少95%有效样本的原门槛。实际比较结论见另外两份配对报告。
