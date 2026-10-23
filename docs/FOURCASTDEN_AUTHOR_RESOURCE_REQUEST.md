# FourCastDEN作者资料请求邮件草稿（2026-10-23）

状态：DRAFT ONLY / NOT SENT。收件人应为论文通讯作者；本次MDPI页面返回403，未核实通讯作者身份或公开邮箱，不根据姓名推测邮箱。发送前请由用户从官方论文通讯信息/作者机构页确认姓名和地址，并填写署名。Crossref列作者不等于通讯作者认定。已核查资源：软件DOI10.5281/zenodo.22250237（当前版本22250238），数据DOI10.5281/zenodo.21859635。

**To:** [Verified corresponding author name and email — to be confirmed]
**Subject:** Request for FourCastDEN training resources and a small reproducibility dataset

Dear Corresponding Author,

We are reproducing FourCastDEN and studying thermospheric density forecasting for subsequent satellite-orbit applications. Using your public software, static files, four pretrained checkpoints, and selected 2023 test samples, we have run Direct, Flow, log-DEN, and History forecasts, including continuous 12-hour evaluations against the TIE-GCM reference fields.

We would now like to reproduce training before investigating controlled improvements. We have not found a complete runnable training entry point or the 2000–2021 training and 2022 validation data in the published inference package. Could you please advise whether the following materials are available?

1. The complete training code and YAML configurations for the four checkpoints, including loss/latitude/channel weighting, optimizer, learning-rate schedule, sampling, random seeds, and checkpoint-resume settings.
2. Access instructions, licensing conditions, and file/checksum manifests for the training and validation datasets. If full access is impractical, could a small lawful sample of consecutive hours from a training year and from 2022 be shared first?
3. The exact preprocessing and normalization-statistics workflow, including source years, variable ordering, missing/top-padding handling, and historical auxiliary/forcing alignment.
4. If the datasets cannot be shared, the TIE-GCM version and run configurations needed to generate compatible independent data, including initialization/spin-up, lower boundaries, geomagnetic/solar forcing conventions, and output settings.

Our preregistered engineering sample candidates are 5–8 April 2021 and 5–7 April 2022, subject to availability and permission. We will keep 2023 separate from training and hyperparameter selection. We also recognize that agreement with TIE-GCM reference fields is not independent observational or satellite-orbit validation.

We would be grateful for any available materials or guidance and will follow the relevant licenses and citation requirements.

Best regards,
[Name]
[Institution / research group]
[Contact information]

## 发送前检查

确认通讯作者和公开邮箱来源；替换署名与机构；核对研究介绍，勿暗示已复现完整训练或取得未公开数据。只索取许可与资源说明，不自动发送或承诺数据使用权。可附已有官方权重推理/接口核验摘要，不发送权重或大型数据。
