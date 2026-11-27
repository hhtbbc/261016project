# V55 用户最小人工交接

1. **先发 GFZ 草稿。** 从 GFZ Kp 官方 Contact 的已公布渠道询问 2021-05-09、2021-06-16。最小有效答复包含原始 observed F10.7、单位 sfu、观测时刻、质量和日值归档/修订标识。两天未恢复同定义时保持 GFZ_2021_GAP_UNRESOLVED。保存答复出处、文档版本和可核验原件，先勿修改原驱动。 [GFZ 草稿](V55_GFZ_INQUIRY_EN.md)
2. **并行提交 ESA 归档请求。** 在账户持有人自行接受适用条款后，询问两个完整 0504 文件以及对应 0301 Level 2 规范和交付链。记录目录、发布标识和官方校验和（若可用）。若收到封装 ZIP，保留封装原字节和交付关联，按官方流程从中提取精确 SP3 字节。原有 0301 无需再上传；如通过授权会话重取同版验证，保留可信交付证据及字节身份。 [ESA 草稿和产品名](V55_ESA_INQUIRY_EN.md)
3. **请 NCAR 回答 ZG 外部定义。** 需要物理零面、测量方向、纬度登记、底边界及 GSWM 参考，以及可由独立来源复核的控制点。只有模型内部锚点的答复不足以建立外部映射。 [NCAR 草稿](V55_NCAR_INQUIRY_EN.md)
4. **交接路径** `/workspace/data/20261016/data/raw/thermosphere_external_handoff_v55/staging/`。三类声明文件名应精确为 `GFZ_2021_evidence.json`、`ESA_0301_delivery.json`、`NCAR_ZG_evidence.json`。附件声明使用同目录普通文件 basename 和独立 SHA256。SP3 使用两个精确 basename，并附 `<完整文件名>.source.json`。无需递交账号、个人邮箱、Cookie、令牌、带签名链接或私密邮件完整正文。公开出处和必要的回复摘要可提交，受限资料留在受控区。 [结构与示例](../experiments/thermosphere_external_evidence_handoff_v55/handoff_contract.json)

## 交接后执行

```bash
cd /workspace/data/20261016
source scripts/activate_tiegcm.sh
export PYTHONPATH="$PWD/src:$PWD/scripts:$PYTHONPATH" CUDA_VISIBLE_DEVICES=''
python -B scripts/check_external_evidence_v55.py
python -B scripts/check_external_evidence_v55.py --accept-sp3
```

无参数运行只做受控扫描和结构预检。显式参数仅把合格 SP3 字节和收据发布到只读 accepted。GFZ、ESA、NCAR 文件始终进入待人工权威审查，文件出现不会更新科学门禁。第二次传入不同 SHA 的同名 accepted 文件会报告冲突。没有自动评分、模型积分、邮件或联网路径。

只有在审议工件确认 SP3 与 CDF 同框架及历元、同卫星参考点及 GRS80 解释后，才在 staging 放入对应 `<SP3>.geometry_review.json`，并显式执行 `python -B scripts/admit_swarm_sp3_v55.py <SP3 basename> --compare-accepted`。该入口只比对冻结的 CDF 几何清单，使用精确 UTC 交集，不隐含轨道位置插值。输出为来源端几何对照，不能解封密度或证明模型高度。
