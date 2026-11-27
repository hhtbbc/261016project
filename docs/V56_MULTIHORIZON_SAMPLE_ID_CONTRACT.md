# V56 样本 ID 合同

合成端点 ID 是 UTF-8 紧凑 JSON 数组经 SHA256 所得。

```text
["V56_SYNTHETIC_ENDPOINT", source_SHA, source_identity, split_identity,
 cutoff_UTC, horizon_hours, target_UTC]
```

UTC 采用秒精度 ISO-8601 Z，horizon 是整数。合成背景 SHA 与历史快照 SHA 独立冻结。毒化合成标签不改变两者。各行记录角色、访问约定、排他性历史结束及最后允许小时点。不同合成 split 的完整 UTC 支持区间不得重叠或共端点。该隔离规则仅适用于合成开发，V37 划分保持。

真实观测元数据点 ID 使用产品 SHA 与绝对 UTC，不含窗长。累计窗口 [t,t+h) 在三个时效分别有 120、360、720 个 30 秒节点。窗口成员用 cutoff+horizon+sample_id 标识，条目重复是嵌套窗口关系。小时括区和时间权重按 UTC 计算。时间身份核验不授予外部高度和未来标签准入。
