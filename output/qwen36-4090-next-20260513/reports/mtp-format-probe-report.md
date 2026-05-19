# MTP 格式修正探测报告

## 结论

本轮测试的三种非侵入式修正都不能真正解决 llama.cpp MTP chat endpoint 的空 `<think>` 包裹：

- baseline chat：仍输出 `<think></think>`。
- system prompt 禁止 thinking：仍输出 `<think></think>`。
- stop `</think>`：仍输出 `<think></think>`，没有阻断前缀。
- `/completion` endpoint：更差，输出真实 thinking 过程，不适合作为 JSON-only 修正路径。

因此当前可用修正只有客户端/网关后处理，或修改 server/chat template 源头。

## 测试配置

- 服务：MTP spec=4
- 端口：`18424`
- 模型：`/data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf`
- 测试目标：严格 JSON-only 输出。

## 结果

| Case | 成功 | 输出形态 | 评分 | 判断 |
| --- | --- | --- | ---: | --- |
| chat_json_baseline | 是 | 空 `<think>` + JSON | 2/5 | JSON 内容正确，但不是 JSON-only。 |
| chat_json_system_no_think | 是 | 空 `<think>` + JSON | 2/5 | system prompt 无法覆盖模板级输出。 |
| chat_json_stop_think_close | 是 | 空 `<think>` + JSON | 2/5 | stop sequence 不足以去掉已输出前缀。 |
| completion_json_raw_prompt | 是 | 真实 thinking 文本 | 1/5 | 比 chat 更差，不能用于严格格式。 |

综合评分：1.75/5。

## 关键证据

chat baseline 输出开头：

```text
<think>

</think>

{"answer":"exact-match 测试要求输出与预期结果完全一致...
```

completion endpoint 输出开头：

```text
<think>
Here's a thinking process:
...
```

## 记录位置

- Raw：`output/qwen36-4090-next-20260513/raw/mtp_spec4_format_probe.*`
- Log：`output/qwen36-4090-next-20260513/logs/mtp_spec4_format_probe.log`

## 最终判断

MTP lane 可以作为最高吞吐 lane，但不能直接用于 JSON-only / exact-match 质量评估。短期建议在测试网关做确定性清洗：仅移除开头空 `<think>\\n\\n</think>` 包裹；长期建议检查 llama.cpp Qwen chat template/reasoning format 源头。
