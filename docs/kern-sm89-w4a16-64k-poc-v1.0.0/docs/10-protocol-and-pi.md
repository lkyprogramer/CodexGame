# HTTP / Pi合同

当前上游kern-serve的非greedy参数会warning后仍greedy。这不满足可审计A/B。P0先修成：支持temperature0；不支持的非默认采样字段返回明确4xx，绝不静默忽略。[S07]

## 测试API

生产18343及鉴权不改。candidate18041、oracle18042只在loopback提供：`/v1/models`、`/v1/completions`、`/v1/chat/completions`、SSE。raw completions需要支持token-id数组，用于精确64K测试；若frontend不支持，由T15补齐，不偷偷decode→encode改变长度。

开发专用trace endpoint由T14新增：`/poc/v1/traces/<request_id>`，只监听本地、默认生产禁用。服务必须接收并返回X-Request-ID，trace绑定该请求，不能取上一条metrics冒充本条。

### trace最小schema

```json
{"request_id":"uuid","prompt_tokens":65536,"generated_token_ids":[123],
 "accepted_target_tokens":2048,"engine_decode_wall_ms":60000,
 "prefill_ms":30000,"reused_tokens":0,"computed_prefill_tokens":65536,
 "truncated":false,"speculation":"none","state_frontier":67583,
 "kv_dtype":"bf16","gdn_dtype":"fp32","profile_sha256":"64hex"}
```

这里数值是schema示例，不是真实成绩。`engine_decode_wall_ms`包含生成阶段必要的host控制、图提交、同步与commit，不仅是某一个kernel event；计数为真正提交的target tokens。CPU采样若有，不得排除在该时间之外。

## Pi测试模式

P0：双方greedy、thinking off、同模板。包内`poc_tools.java_runner`在临时PI_CODING_AGENT_DIR下写models.json，并实际运行Pi工具循环；现有 ~/.pi 不改。启动前保存 `pi --version`/`pi --help`，若当前版本flag不同，修测试适配并记录差异，不能把CLI错误算模型失败。

P1再实现温度/top_p/top_k和medium thinking，才有资格与现网medium生产体验比较。不能把P0 off的耗时直接压过NInfer medium宣称同等质量。

## stream要求

解析reasoning/content/tool-call arguments，忽略只有role/usage的帧。SSE一个事件可能含多个token；特别是投机输出，不得把帧数当token数。缺usage就记null；缺[DONE]/协议中断记INCOMPLETE。客户端window-tps仅探索值，最终速度gate必须有engine trace。
