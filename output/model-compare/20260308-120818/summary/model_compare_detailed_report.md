# 4090 单卡 Coding 模型对比报告

## 1. 结论

直接结论：在这轮 **64K / 单槽 / thinking=true / 同一 llama.cpp 二进制** 的真实 coding 对比里，`Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled Q4_K_M` 整体上 **比现网 `unsloth/Qwen3.5-27B-UD-Q4_K_XL` 更好，但优势是小幅领先，不是代际差距**。

这次更关键的结论不是“它更快一点”，而是：

- 质量侧：蒸馏模型人工总分 `131 / 150`，基线是 `121 / 150`。
- 稳定性：主跑蒸馏模型 `10/10` 成功，基线 `9/10`；基线失败题在复跑时恢复为 `200`，所以这更像一次链路抖动，而不是模型必现缺陷。
- 性能与资源：蒸馏模型平均生成速度更高，显存占用更低，大约少 `1.0 GiB`。
- 任务风格：蒸馏模型在“直接给出最小修复方案”的题型上更稳、更像可执行 code review；基线在个别偏架构、偏恢复流程的题上更像“慢思考”，但不总能落成更好的 final answer。

如果你现在只选一个作为 **4090 上 64K 单人 coding 默认模型**，这轮结果我建议选蒸馏模型。

## 2. 本轮对比范围

固定约束：

- 同一台 4090，同一份 `llama.cpp` 二进制
- 顺序切换，不做并发共存
- 固定 benchmark 端口：`28343`
- 固定上下文：`64K`
- 固定参数：

```bash
-ngl 99
-c 65536
-np 1
-fa on
-ctk q4_0
-ctv q4_0
--temp 0.6
--top-p 0.95
--top-k 20
--min-p 0.0
--chat-template-kwargs '{"enable_thinking": true}'
--port 28343
```

对比模型：

- 基线：`/data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf`
- 候选：`/data/models/qwen/Qwen3.5-27B.Q4_K_M.gguf`

任务集：

- `8` 个 Java/Spring 多文件题
- `2` 个 CodexGame 仓库内真实 TypeScript 多文件题

## 3. 兼容性说明

计划里原本要求统一使用 `developer + user` 两段消息，但实际 benchmark 时发现这两类 Qwen 模板在 `llama-server` 下不接受 `developer` role，会直接报：

```text
Unable to generate parser for this template ... Unexpected message role.
```

所以正式跑数时做了一个 **兼容性降级**：

- 任务文本不变
- 只把首条高优先级消息从 `developer` 改成了 `system`
- 两边模型完全一致处理

保留下来的失败样本目录：

- `ud_q4_xl_developer_role_400/`

这个调整不改变两边相对公平性，但需要在报告里明确说明。

## 4. 主跑结果

### 4.1 硬指标

| 指标 | 基线 UD-Q4_XL | 蒸馏 Q4_K_M |
| --- | ---: | ---: |
| 主跑成功数 | 9 / 10 | 10 / 10 |
| 主跑成功率 | 90.0% | 100.0% |
| 平均总耗时 ms | 25601.08 | 26341.27 |
| 平均 prompt_ms | 2341.88 | 2157.32 |
| 平均生成 tok/s | 42.15 | 44.17 |
| 平均 reasoning 长度 | 1841.80 | 1341.60 |
| 平均 content 长度 | 1872.00 | 2643.60 |

### 4.2 资源侧

| 指标 | 基线 UD-Q4_XL | 蒸馏 Q4_K_M |
| --- | ---: | ---: |
| GPU 采样点数 | 389 | 325 |
| 平均 GPU 利用率 | 54.85% | 68.48% |
| 峰值 GPU 利用率 | 100% | 99% |
| 平均显存占用 | 18620.79 MiB | 17572.08 MiB |
| 峰值显存占用 | 18804 MiB | 17762 MiB |
| 平均功耗 | 219.35 W | 276.75 W |
| 峰值功耗 | 437.3 W | 435.7 W |

解释：

- 蒸馏模型的平均显存占用更低，约少 `1048.71 MiB`。
- 蒸馏模型 GPU 利用率更高，说明在同样参数下跑得更“满”。
- 蒸馏模型平均 tok/s 更高，属于真实可感知但不夸张的优势。

## 5. 人工评分结果

评分规则：

- 问题定位准确度：`0-4`
- 根因解释正确度：`0-4`
- 修复方案最小性：`0-4`
- 约束遵守度：`0-3`
- 幻觉 / 不安全建议罚分：`0 到 -3`

总分：

- 基线：`121 / 150`，平均 `12.1 / 15`
- 蒸馏：`131 / 150`，平均 `13.1 / 15`

逐题胜负：

| 任务 | 基线分 | 蒸馏分 | 更优 |
| --- | ---: | ---: | --- |
| `java_null_nested_config` | 13 | 15 | `distilled_q4_k_m` |
| `java_transaction_partial_commit` | 15 | 15 | `tie` |
| `java_path_body_id_mismatch` | 12 | 13 | `distilled_q4_k_m` |
| `java_audit_success_on_failure` | 14 | 14 | `tie` |
| `java_pagination_boundary` | 8 | 15 | `distilled_q4_k_m` |
| `java_optimistic_lock_missing` | 14 | 14 | `tie` |
| `java_enum_db_compat` | 11 | 11 | `tie` |
| `java_soft_delete_unique_email` | 14 | 13 | `ud_q4_xl` |
| `ts_boot_restore_consistency` | 8 | 7 | `ud_q4_xl` |
| `ts_runtime_metrics_protocol` | 12 | 14 | `distilled_q4_k_m` |

## 6. 逐题观察

### 蒸馏模型明显更好的题

- `java_pagination_boundary`
  这里是最典型差异。基线把大量注意力放在 `endInclusive` / `subList` 契约不一致上，偏题了；蒸馏模型直接命中“最后一页 clamp + offset 越界返回空页”，这更贴近真实 production bug。
- `java_null_nested_config`
  基线能发现问题，但主回答几乎都掉进了 `reasoning_content`；蒸馏模型给出的 final answer 更像可以直接交给工程师执行的修复说明。
- `ts_runtime_metrics_protocol`
  两边都知道要 protocol-first，但蒸馏模型更早锁定 `session.state` 扩展，不像基线那样先摇摆到“新增消息类型”。

### 基线略好的题

- `ts_boot_restore_consistency`
  这题两边都不算特别好，都没把 `stateStore` 的 atomic tmp+rename 以及 contract/test 补齐。基线的优点是更保守，主要指出“phase = running 过早 + threadIds 清空”的顺序问题；蒸馏模型更容易往“restore 阶段直接重建线程”走，修复更重。
- `java_soft_delete_unique_email`
  两边都命中 active-row filter，但基线额外提到了 partial unique index 作为长期硬化点，工程味更完整。

### 基本同级的题

- `java_transaction_partial_commit`
- `java_optimistic_lock_missing`
- `java_enum_db_compat`

这些题两边都能给出可用答案，差异不大。

## 7. 复跑结果

复跑任务：

- `java_audit_success_on_failure`
- `ts_boot_restore_consistency`
- `ts_runtime_metrics_protocol`

复跑结论：

- 蒸馏模型：`3/3` 全部稳定 `200`
- 基线模型：`3/3` 也全部稳定 `200`

这说明：

- 基线主跑里那次 `java_audit_success_on_failure` 的 `RemoteDisconnected` 更像一次链路/连接抖动，不像模型模板层必现问题。
- 即便如此，蒸馏模型在主跑阶段仍然比基线少一次波动，这一点可以记作小幅稳定性优势，但不能夸大成“基线不稳定”。

复跑里值得额外记录的两个点：

- 蒸馏模型复跑 TS 两题的耗时下降明显，尤其 `ts_runtime_metrics_protocol` 落到 `34614.63 ms`。
- 基线复跑 `ts_runtime_metrics_protocol` 反而上升到 `68145.79 ms`，说明它在这类大上下文协议题上的时延波动更大。

## 8. 是否建议替换现网

我的判断是：**可以考虑把蒸馏模型作为 64K coding 档默认模型，但不要立刻把基线价值归零。**

推荐决策：

- 如果目标是“单人实战 coding / code review / 最小修复建议”，优先蒸馏模型。
- 如果目标是“更长的慢思考 / 偏架构 restore 流程类推理”，基线依然有价值，至少不明显差。
- 如果只能保留一个 64K coding 默认模型，本轮建议切到蒸馏模型。

不建议过度解读的点：

- 这轮只有 10 个任务，虽然覆盖了 Java + TypeScript + 多文件，但样本还不算大。
- 这不是 262K 档测试，不能外推出超长上下文结论。
- 这也不是 tool-calling / agentic coding 对比，所以不代表带工具场景的最终结论。

## 9. 产物路径

主结果：

- `output/model-compare/20260308-120818/ud_q4_xl/`
- `output/model-compare/20260308-120818/distilled_q4_k_m/`
- `output/model-compare/20260308-120818/summary/compare_report.md`
- `output/model-compare/20260308-120818/summary/scores.json`

复跑结果：

- `output/model-compare/20260308-120818/ud_q4_xl_rerun/`
- `output/model-compare/20260308-120818/distilled_q4_k_m_rerun/`

兼容性失败样本：

- `output/model-compare/20260308-120818/ud_q4_xl_developer_role_400/`

## 10. 最终一句话判断

如果你的目标是 **4090 单卡上的真实 coding 质量**，这轮结果支持这样的结论：

**`Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled Q4_K_M` 比现网 `UD-Q4_K_XL` 更适合作为 64K coding 默认模型，但优势是“更稳、更像最终答案、更省一点显存”，不是“全面碾压”。**
