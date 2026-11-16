# TIE-GCM ZG咨询包V2.1：渠道说明与外部附件脱敏

2026-11-16 UTC；tag tiegcm_zg_external_registration_v2_1。

**附件脱敏通过；当前联系渠道独立核验受HTTP404阻碍。** 不标记完整EXTERNAL_SHARE_READY，不宣称已具备无条件人工投递资格。V2及更早原件保留，邮件未发送、未订阅、未提交表单或联系外部人员。

## 1. 仓库和范围

起始本地main与远端均915347f916e8080cebc5f707ac80622d12db918e，无并发提交。AGENTS/STATUS/WORKLOG、V2邮件/报告及目录均已读取。V2整个目录（含本地同步记录）及两份原文逐字SHA保护；较早相关文档和正式/临时接口另用V2旧SHA复核。无需重新运行高度/沿轨大审计。

## 2. 联系渠道：已核实与未核实必须分开

仅访问两个指定官方页面，没有查询其他支持渠道。

|项目|来源和结果|状态|
|---|---|---|
|列表名称/显示地址|官方2.0 Contact页显示tgcmgroup@ucar.edu，并建议订阅moderated list|旧版官方文字已核实|
|链接字面目标|该页原HTML锚点为http://mailman.ucar.edu/mailman/listinfo/tgcmgroup；未访问此额外HTTP地址|仅核实锚点，不等于订阅服务有效|
|用户指定HTTPS订阅页|https://mailman.ucar.edu/mailman/listinfo/tgcmgroup；浏览工具和独立有界HTTPS GET均404|当前正文不可获得|
|实际发帖地址候选|tgcmgroup@mailman.ucar.edu由本轮任务明确提供，V2.1 To按要求填写|USER_SUPPLIED_PENDING_OFFICIAL_REVALIDATION|
|管理员批准要求|任务提供为须管理员批准；本轮保留为发送前工作流条件|未独立取得当前官方政策原文|
|是否必须订阅才能发帖/是否封闭列表|现存Contact页的moderated措辞不能证明member-only或closed-list配置|UNVERIFIED，不凭经验推断|
|其他官方支持途径|旧Contact页列有科学技术联系人；未导出个人邮箱、未选收件人、未联系|仅旧页记载，不证明当前身份或可投递|

[官方Contact页](https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/contact.html)本轮直接GET200，5419字节，SHA7f914849cc980bcd3b03052e7d0bf6405a44437c420b1a24fe3ac441185e1c27。HTML仅本地保存。Mailman两种读取均404，不使用其他页面/域名/协议绕过，也不把用户提供的待核实信息写成已取得官方原文。

contact_route_evidence.json记录访问UTC、必要原文短摘录、实际锚点、HTTP失败和用户提供声明的来源。Mailman原文数组为空，绝无伪造订阅政策。没有测试邮件投递，因此即便未来可读，也不能直接确认当前维护者身份或送达。

## 3. V2.1邮件

新稿docs/TIEGCM_ZG_EXTERNAL_REGISTRATION_REQUEST_V2_1.md的技术正文（含主题和A/B/C/D）与V2逐字一致，SHA独立核验。保留真实2.0/apex版本、两B14配置、DEN/ZG ilev维度与单位、calczg/apex区别、Swarm产品、Map-A局限和科学问题。

只更改外围投递说明和附件清单。To为tgcmgroup@mailman.ucar.edu，发送前明确要求用户核实当前渠道、成功订阅并获管理员批准，再填[Name]/[Affiliation]/[Email]。这是一份条件性草稿；不是对当前网页政策已核验的声明。不会把tgcmgroup@ucar.edu显示文字直接当实际发帖地址。

## 4. 外部分享包

只导出白名单技术字段，未复制原始model_configuration_manifest：

- external_share/technical_summary_external.md：研究目的、版本、高度链、B14设置、未解决问题和求助内容。
- external_share/question_evidence_matrix_external.csv：七项问题的英文精简矩阵、官方公开URL、状态及待确认内容。
- external_share/configuration_summary_external.json：官方commit、必要SHA、两年运行数值、DEN/ZG单位与维度、Swarm版本与条件映射；没有原始文件属性或部署路径。
- external_share/SENDING_GUIDE.md：人工核实渠道/订阅确认/管理员批准/发帖步骤、建议附件和个人占位符；明确404及政策未核实。

四文件共13001字节。前三份可作为技术附件，指南可供人工操作或一并分享。它们不依赖内部文件链接即可理解，且可由公开URL/版本/必要SHA追溯技术来源。原始完整manifest、source_file/initial_file等NetCDF属性、完整执行记录、原始CDF/NetCDF及轨迹缓存不得直接作为邮件附件。

## 5. 独立脱敏及技术一致性验证

全文逐文件扫描；JSON递归键/值扫描；CSV所有表头和字段扫描；Markdown全文扫描；另外扫描新邮件草稿。拒绝内部绝对/项目路径、Windows/UNC路径、实际主机和账号值、非批准邮箱、敏感JSON键、凭据赋值及常见令牌格式、原始模型/观测文件名。只允许4个预定文件，拒绝额外日志或原始数据。

15项内存夹具测试全部通过，涵盖上述路径、嵌套敏感字段、JSON转义路径、凭据、邮箱白名单、实际主机值和文件白名单，测试不使用真实秘密。实际附件和新稿检出问题0，无未处理项。扫描是已定义规则的技术检查，不是对所有可能信息泄漏的无限保证；人工补充个人信息后应再次检查待发版本。

独立检查原V2邮件/报告/整个目录SHA未变，七问题和四组正文完整，出口配置数值、原始四源SHA、apex/patch SHA、日历和SI系数吻合V2。没有自动复制host/logname/source_file/initial_file或本地原始数据路径。原始技术结论、外部高度门禁不改变。

## 6. 资源、状态与停止点

受测准备/独立核验/技术复查CPU约0.01979秒，测试主体0.004秒，最大进程自报RSS794.992MiB；官方页面等待单列资源记录，浏览/Git/人工编辑不冒充连续采样。无新观测/模型/GPU/DART/轨道/训练；公开文件远低150MiB。

状态：TIEGCM_ZG_EXTERNAL_REGISTRATION_V2_1=ATTACHMENTS_SANITIZED_CONTACT_ROUTE_UNVERIFIED；external附件本身SANITIZED_ATTACHMENTS_READY，但manual_sending_ready=False。没有因附件安全而宣称渠道已核实。

EXTERNAL_DATUM_UNVERIFIED、SCIENCE_TRAINING_READY=False、DART_NOT_ADMITTED、REAL_ORBIT_BLOCKED、RestartFAIL及历史A14身份保持。

下一步只需用户人工补充可核实的Mailman页面/官方政策、确认地址和审批，填个人占位符后决定是否发送。若仍404则暂停发送，不自动选个人邮箱替代。收到实际回复再沿V2验收矩阵另任务检查；本轮停止，不进入历史代表性诊断/v14/DART。
