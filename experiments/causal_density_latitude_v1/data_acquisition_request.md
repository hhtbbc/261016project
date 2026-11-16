# v13独立日期观测获取申请（未执行）

2026-11-16。两年目标CDF/ZIP/HDR均不在本地；已有官方目录缓存能确认其曾列示，未联网复查当前可用性。**本轮下载量0，拟合/评价0，按用户门禁停止。**

|日期|精确ZIP产品|缓存大小 bytes|
|---|---|---:|
|2021-03-23|SW_OPER_DNSAPOD_2__20210323T000000_20210323T235930_0301.ZIP|140271|
|2022-03-23|SW_OPER_DNSAPOD_2__20220323T000000_20220323T235930_0301.ZIP|139397|

两ZIP缓存合计 **279668字节（0.266712MiB）**。这是目录记录值，不是当前实测下载量或解压体积。

## 官方路径与本地缺口

- `swarm/Level2daily/Latest_baselines/DNS/POD/Sat_A/SW_OPER_DNSAPOD_2__20210323T000000_20210323T235930_0301.ZIP`
  预期本地原件：`data/raw/causal_density_latitude_v1/SW_OPER_DNSAPOD_2__20210323T000000_20210323T235930_0301.ZIP`，解压后同stem的`.cdf`和`.HDR`；三者均缺。
  未来授权后可用官方HTTPS入口：[产品下载](https://swarm-diss.eo.esa.int/?do=download&file=swarm%2FLevel2daily%2FLatest_baselines%2FDNS%2FPOD%2FSat_A%2FSW_OPER_DNSAPOD_2__20210323T000000_20210323T235930_0301.ZIP)。本轮未发起请求。
- `swarm/Level2daily/Latest_baselines/DNS/POD/Sat_A/SW_OPER_DNSAPOD_2__20220323T000000_20220323T235930_0301.ZIP`
  预期本地原件：`data/raw/causal_density_latitude_v1/SW_OPER_DNSAPOD_2__20220323T000000_20220323T235930_0301.ZIP`，解压后同stem的`.cdf`和`.HDR`；三者均缺。
  未来授权后可用官方HTTPS入口：[产品下载](https://swarm-diss.eo.esa.int/?do=download&file=swarm%2FLevel2daily%2FLatest_baselines%2FDNS%2FPOD%2FSat_A%2FSW_OPER_DNSAPOD_2__20220323T000000_20220323T235930_0301.ZIP)。本轮未发起请求。

## 建议下一轮最小授权

只申请以上两日Swarm A0301 ZIP及必要小元数据，新增原始下载上限建议1MiB（不重新拉取整份约1.45MB目录）；若官方大小/版本变化或文件超预算则停止。解压安全预算建议2MiB，不能写出项目。下载后记录HTTP来源、实际大小、ZIP CRC、所有成员SHA，CDF读取前核验SHA与产品身份。不得下载B/C或改变日期。

两CDF均须独立验证UTC00:00—23:59:30、2880记录/30秒、字段和原始单位、flag分布及有效性；上述只是目标条件，当前没有实测值。只有两日均合格，才能继续候选日期原NetCDF SHA/15—24Z/次日00边界/显式填值/八列覆盖预检，再冻结v13协议。

**3月23日的Stale06尚无冻结系数。** 不可使用3月24日v10/v11系数冒充；应在同日全天观测取得后，仅用3月23日[03,06)估计并在18Z评价前冻结。区域[15,18)N<30必须UNSUPPORTED，不能借其他区域或全局填补。

本申请不是下载授权，不启动下载、拟合、查询或评价。等待用户明确批准后继续同一数据门禁；不得把本轮BLOCKED记录改为已经完成。
