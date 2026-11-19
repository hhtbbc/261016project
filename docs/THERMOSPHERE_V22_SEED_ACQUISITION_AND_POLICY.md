# V22：秋分初态人工获取与政策审定

两年份GPI已独立验收，不能自动转为模型RUN_READY。当前缺少官方秋分原件及用户初态政策。

1. 人工打开[HAO官方下载入口](https://www.hao.ucar.edu/modeling/tgcm/download.php)。[TIE-GCM2.0指南](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/quickstart.html)说明需提供邮箱、不需登录密码，5°启动数据包为`tiegcm_res5.0_data.tar`，文档体积约1.5GB。当前页面的交付可用性、条款及实际大小仍须人工确认；本轮没有提交表单。
2. 如已合法持有该官方包，请提供位于项目内的文件及来源记录。否则，先人工完成官方流程，并另行授权包的受限获取。不要重试或绕过V21的403，不使用未核实镜像。
3. 应取得的精确成员是`tiegcm_res5.0_sepeqx_smax_prim.nc`。仅检查包成员清单和安全提取该文件，不解压整包，不覆盖旧mareqx。后续导入建议目录为项目相对路径`data/raw/tiegcm_autumn_initial_source_v1/`；当前未创建或自动导入。
4. 保留官方来源URL、获取日期、包/文件字节数、SHA256和适用条款。原件禁止改时间戳或补变量。下一任务再运行既有`observations.autumn_validation.inspect_initial`，核对真实year/day/mtime、SOURCE_START、34状态、网格、维度/单位、掩码及数值。
5. 在实物审查之后，用户明确审定A（旧mareqx同源）或B（官方sepeqx同季）。若选B，2021/2022固定同一原件SHA；与March背景身份不同必须披露。若选A，必须明确接受季节适应性未验证的风险，不能把403解释为A自动获批。
6. 政策及初态身份闭合后，下一轮才准备并冻结两份独立16天配置，逐次申请正式积分；本轮没有生成积分input.inp或执行模型。

官方[目录说明](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/dirstruct.html)列出精确初态名，但列表不是当前交付成功的证据。官方Globus说明针对benchmark历史场，尚未证实能取得完全相同的单记录启动文件，不作为替代路线。
