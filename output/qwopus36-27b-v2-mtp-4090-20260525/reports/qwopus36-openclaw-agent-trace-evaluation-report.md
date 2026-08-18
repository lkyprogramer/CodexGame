# Qwopus3.6-27B-v2-MTP OpenClaw Agent Trace Evaluation

生成时间：2026-05-25

## 结论

这轮真实 OpenClaw agent trace 测试后，结论比上一轮更明确：

- `Qwopus Q4_K_M n=2 p-min=0.75` 不适合作为当前生产基线的直接替换。它在真实 agent trace 中质量可用、cache 稳定、显存更低，但整体吞吐没有超过当前 `Qwen UD-Q4_K_XL n=4 p-min=0.75`，并且出现 1 个 patch unified diff 格式不严格样例。
- `Qwopus Q4_K_M n=4 p-min=0.0` 在模型卡声称适合的场景里确实有明显速度优势：多轮 JSON、patch review、DevOps runbook、重复相似 prompt 的 decode 都更快；但 acceptance 波动明显，最低到 `0.353`，更适合继续作为“极速实验 lane”，不建议直接进生产。
- prompt cache reuse 不是 Qwopus 的差异化优势。三条 lane 在 114k token 级长历史下都能稳定 warm 命中，`cache_n / prompt_tokens` 都约 `0.9955`，热 prefill 都在约 `0.71s`。

我的判断：Qwopus 在 Jackrong 模型页描述的 coding / DevOps / strict-format / agent 场景里，**只有放宽到 `p-min=0.0` 的极速策略时才体现显著性能优势**；稳定策略 `n=2 p-min=0.75` 没有形成对当前 Qwen 生产基线的综合优势。

## 测试依据

模型卡定位：

- Jackrong 模型页将 Qwopus3.6-27B-v2-MTP 描述为基于 Qwen3.6-27B 的 speed-oriented reasoning release，重点覆盖 reconstructed reasoning traces、coding discipline、DevOps procedures、math derivations，并通过 MTP 提升生成速度。
- 模型页推荐用途包括 agentic coding / code review、DevOps runbooks / configuration / incident diagnosis、structured reasoning、fast constrained output generation。
- 模型页 benchmark 声称 Qwopus 在 Logic、Coding、DevOps、Math、Edge-format 等 30 问本地基准里更快，并且 completion tokens 更少。

来源：[Jackrong/Qwopus3.6-27B-v2-MTP-GGUF](https://huggingface.co/Jackrong/Qwopus3.6-27B-v2-MTP-GGUF)

## 测试配置

远端机器：RTX 4090，`192.168.10.29`

llama.cpp：

- binary：`/home/hhtele/llama.cpp-master-qwopus-20260525/build/bin/llama-server`
- commit：`549b9d84330c327e6791fa812a7d60c0cf63572e`
- version：`1 (549b9d8)`

统一服务参数：

```bash
-ngl 99
-c 131072
-np 1
-fa on
-ctk q4_0
-ctv q4_0
-rea off
--temp 0
--top-p 1
--cache-prompt
--cache-ram 2048
--cache-reuse 256
--slot-prompt-similarity 0.10
--host 127.0.0.1
--port 19343
--spec-type draft-mtp
```

对比 lane：

| Lane | 模型 | spec | p-min | 目的 |
|---|---|---:|---:|---|
| qwen_udq4xl_n4_p075 | Qwen3.6-27B-UD-Q4_K_XL | 4 | 0.75 | 当前生产基线同 binary 对照 |
| qwopus_q4km_n2_p075 | Qwopus3.6-27B-v2-MTP-Q4_K_M | 2 | 0.75 | 稳定候选 |
| qwopus_q4km_n4_p000 | Qwopus3.6-27B-v2-MTP-Q4_K_M | 4 | 0.0 | 极速实验候选 |

## 测试用例设计

这轮不再跑通用问答，而是围绕 OpenClaw agent 工作负载：

- `multi_turn_json_tools`：6 轮连续 JSON tool call，模拟 agent 多步工具选择。
- `patch_review`：review 一个有异步顺序问题和协议版本破坏的 diff，再输出修复 patch 和测试计划。
- `long_history_incremental_cache`：约 114k prompt tokens 的稳定长历史，连续 4 次只追加很小增量，测试长历史增量 cache reuse。
- `repeated_similar_cache`：约 114k prompt tokens 的重复相似 prompt，连续 5 次只改变小 delta，测试重复 prompt cache reuse 稳定性。
- `devops_runbook`：中文 DevOps incident runbook，覆盖 systemd、NGINX auth、llama-server 日志、prompt cache 和 rollback。

## 总览结果

| Lane | cases | strict pass | avg decode tok/s | avg response tok/s | avg accept | avg fmt | avg quality | warm cache ratio | peak VRAM MiB | max temp C |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen n4 p075 | 19/19 | 9/9 | 66.11 | 31.47 | 0.964 | 4.97 | 5.00 | 0.99549 | 22688 | 85 |
| Qwopus n2 p075 | 19/19 | 8/9 | 62.38 | 30.83 | 0.986 | 4.76 | 5.00 | 0.99549 | 21324 | 88 |
| Qwopus n4 p000 | 19/19 | 9/9 | 78.80 | 36.23 | 0.773 | 4.97 | 5.00 | 0.99549 | 21640 | 88 |

关键差异：

- Qwopus n2 p075 比 Qwen n4 p075 平均 decode 慢约 `5.6%`，response tok/s 慢约 `2.0%`。
- Qwopus n2 p075 峰值显存低约 `1364 MiB`，这是它最稳定的优势。
- Qwopus n4 p000 比 Qwen n4 p075 平均 decode 快约 `19.2%`，response tok/s 快约 `15.1%`，但 acceptance 明显更低。

## 分场景结果

| Suite | Lane | elapsed s | avg decode tok/s | avg accept | fmt | quality | warm cache hits |
|---|---|---:|---:|---:|---:|---:|---:|
| multi_turn_json_tools | Qwen n4 p075 | 3.657 | 85.44 | 0.959 | 5.00 | 5.00 | 0 |
| multi_turn_json_tools | Qwopus n2 p075 | 3.761 | 80.92 | 0.981 | 5.00 | 5.00 | 0 |
| multi_turn_json_tools | Qwopus n4 p000 | 3.366 | 99.43 | 0.810 | 5.00 | 5.00 | 0 |
| patch_review | Qwen n4 p075 | 6.435 | 65.33 | 0.944 | 5.00 | 5.00 | 0 |
| patch_review | Qwopus n2 p075 | 5.663 | 61.68 | 0.966 | 3.67 | 5.00 | 0 |
| patch_review | Qwopus n4 p000 | 5.271 | 82.65 | 0.571 | 5.00 | 5.00 | 0 |
| long_history_incremental_cache | Qwen n4 p075 | 77.438 | 55.40 | 0.965 | 5.00 | 5.00 | 3 |
| long_history_incremental_cache | Qwopus n2 p075 | 78.709 | 54.09 | 1.000 | 5.00 | 5.00 | 3 |
| long_history_incremental_cache | Qwopus n4 p000 | 79.620 | 59.73 | 0.782 | 5.00 | 5.00 | 3 |
| repeated_similar_cache | Qwen n4 p075 | 81.776 | 54.52 | 0.992 | 5.00 | 5.00 | 4 |
| repeated_similar_cache | Qwopus n2 p075 | 83.058 | 49.17 | 1.000 | 5.00 | 5.00 | 4 |
| repeated_similar_cache | Qwopus n4 p000 | 83.032 | 68.13 | 0.908 | 5.00 | 5.00 | 4 |
| devops_runbook | Qwen n4 p075 | 12.454 | 53.29 | 0.917 | 4.50 | 5.00 | 0 |
| devops_runbook | Qwopus n2 p075 | 13.958 | 52.47 | 0.947 | 4.50 | 5.00 | 0 |
| devops_runbook | Qwopus n4 p000 | 8.757 | 73.02 | 0.443 | 4.50 | 5.00 | 0 |

## 长历史与 Prompt Cache

长历史增量 cache：

| Lane | cold prompt tokens | cold prompt ms | warm cache_n | warm prompt ms 范围 | 结论 |
|---|---:|---:|---:|---:|---|
| Qwen n4 p075 | 114546 | 71734 | 114030 | 709-716 | 正常命中 |
| Qwopus n2 p075 | 114548 | 72672 | 114032 | 712-714 | 正常命中 |
| Qwopus n4 p000 | 114551 | 73567 | 114035 | 712-716 | 正常命中 |

重复相似 prompt cache：

| Lane | cold prompt tokens | cold prompt ms | warm cache_n | warm prompt ms 范围 | 结论 |
|---|---:|---:|---:|---:|---|
| Qwen n4 p075 | 114510 | 72223 | 113994 | 709-712 | 正常命中 |
| Qwopus n2 p075 | 114512 | 73252 | 113996 | 713-715 | 正常命中 |
| Qwopus n4 p000 | 114515 | 73645 | 113999 | 712-714 | 正常命中 |

结论：

- `--cache-prompt + --cache-reuse 256 + --slot-prompt-similarity 0.10` 对三条 lane 都稳定有效。
- Qwopus 没有在 prompt cache 上表现出明显额外优势；cache 命中主要来自 llama.cpp slot/prompt cache 行为，而不是模型本身。
- 114k prompt cold prefill 都在约 72-74s，warm prefill 都降到约 0.71s。

## 质量与失败样例

Qwopus n2 p075 唯一明显问题是 `patch_review_fix_diff`：

```diff
diff --git a/apps/game-runtime/src/runtime/GameRuntimeServer.ts b/apps/game-runtime/src/runtime/GameRuntimeServer.ts
@@
-      const output = JSON.parse(text);
-      setTimeout(() => this.applyAction(output.action), 0);
-      return true;
+      const output = JSON.parse(text);
+      await this.applyAction(output.action);
diff --git a/packages/protocol/src/messages.ts b/packages/protocol/src/messages.ts
@@
-export const runtimeProtocolVersion = 'v2';
+export const runtimeProtocolVersion = 'v1';
```

这个输出语义正确，但缺少标准 unified diff 的 `---` / `+++` file header，因此格式分为 `1.0`。对真实 coding agent 来说，这类问题会影响 patch apply 成功率。

对比：

- Qwen n4 p075：该 case 返回标准 unified diff，格式/质量均通过。
- Qwopus n4 p000：该 case 也通过，且 decode 更快，但 acceptance 低。

## 是否验证了模型卡声称的优势

| 模型卡场景 | Qwopus n2 p075 | Qwopus n4 p000 | 判断 |
|---|---|---|---|
| Agentic coding / JSON tool | 质量通过但不比 Qwen 快 | 明显更快且格式通过 | 极速策略有优势 |
| Code review / patch | review 质量通过，patch 格式失败 1 次 | 更快且通过 | 稳定策略不够稳，极速策略本轮通过 |
| DevOps runbook | 质量通过但比 Qwen 慢 | 明显更快且质量通过 | 极速策略有优势 |
| Fast constrained output | 多轮 JSON 通过但不快 | 多轮 JSON 更快 | 极速策略有优势 |
| Long history / cache reuse | cache 稳定但不优于 Qwen | cache 稳定且 decode 更快 | cache 本身无差异，decode 有差异 |

最终判断：

- 如果目标是“当前生产可靠替换”，Qwopus 还没有赢。
- 如果目标是“OpenClaw 的实验/灰度加速 lane”，`Qwopus n4 p-min=0.0` 值得继续扩大测试。
- 如果只允许稳定策略 `p-min=0.75`，Qwopus 的主要价值是省显存，不是提升真实 agent trace 吞吐。

## 生产恢复验证

测试 wrapper 退出后恢复了生产服务。wrapper 恢复日志刚启动时 `/v1/models` 仍在 loading，随后独立复核结果如下：

- `systemctl is-active openclaw-qwen36-mtp4-128k.service`：`active`
- `systemctl is-enabled openclaw-qwen36-mtp4-128k.service`：`enabled`
- `curl http://127.0.0.1:18343/v1/models`：返回当前生产模型
- `curl -H "Authorization: Bearer <token>" http://127.0.0.1:28343/v1/models`：HTTP `200`
- 无 token 访问 `28343`：HTTP `401`
- `llama-server.*19343` 残留进程：`0`

## 原始文件

本地目录：

```text
/Users/luo/Documents/github/CodexGame/output/qwopus36-27b-v2-mtp-4090-20260525
```

关键文件：

- trace 脚本：`remote/qwopus_openclaw_trace_eval.py`
- trace wrapper：`remote/run_qwopus_openclaw_trace_eval_wrapper.sh`
- trace 汇总：`raw/trace-remote-copy/trace-results/summary.json`
- trace 逐 case 输出：`raw/trace-remote-copy/trace-results/*.json`
- trace 日志：`raw/trace-remote-copy/trace-results/eval.log`
- 生产恢复日志：`raw/trace-remote-copy/trace-logs/restore-status.log`

## 下一步建议

1. 不替换生产 `Qwen n4 p-min=0.75`。
2. 新增灰度端口跑 `Qwopus n4 p-min=0.0`，只接低风险 agent trace：JSON tool、DevOps runbook、只读 review。
3. 对 `Qwopus n4 p-min=0.0` 再跑至少 100 条真实 OpenClaw patch apply 样例，重点统计 unified diff 可应用率、JSON parse 成功率、think leak、重复输出。
4. 如果 patch apply 成功率稳定，再考虑灰度到写文件类 agent 任务；否则 Qwopus 只作为只读/分析加速模型。
