> V2 参考快照：P7—P12 不再是执行权威；按根目录 `plans/00-master-plan.md` 和 `plans/01-v2-migration-map.md` 执行。本文保留历史设计与来源，不表示实现完成。

# 归一数据格式（不是实测数据）

第一行是kind=run_metadata，至少填写run-manifest的当前真实身份。后续每行kind=sample，包含case_id、repeat、metrics。warmup不进入sample。`ttft_seconds`首内容口径在同一case中固定；decode_tok_s是已提交输出token的客户端定义速率，不包含prefill progress。

```json
{"kind":"sample","case_id":"long-hot-128k-tool-01","repeat":0,"metrics":{"ttft_seconds":1.0,"decode_tok_s":40.0,"prepare_seconds":0.1}}
```

以上数字只是字段示例，不用于任何报告。raw/client/server必须按request_id对齐。比较工具只校验明确的metadata键与配对样本，完整profile/clock/cache/resource一致性还需run-manifest和review核查。decision latency不用此Chat decode规则，必须独立判定。`--allow-change kv_dtype`只用于声明过的codec迁移；不得允许改dataset/GPU来让数值过线。32个CPU helper测试不包含任意真实网络或GPU调用。
