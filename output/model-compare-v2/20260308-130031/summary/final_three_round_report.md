# 三轮 Qwen Coding 对比综合报告

## 1. 最终结论

直接结论：经过这 **三轮评测** 之后，我现在的综合偏向已经比较明确，**更偏向 `Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled Q4_K_M` 作为 4090 上的默认 coding 模型**。

这个偏向不是因为它在每一题都更聪明，而是因为它在三轮里反复体现出三个更稳定的特征：

- 更常把答案落到可见正文里，而不是把主要内容困在 `reasoning_content`
- 对真实业务 bug、最小修复和脚本落地的回答更像可直接执行的工程产物
- 在长上下文下更稳，失败形态也更“干净”

如果只保留一句话判断：

**现在我更倾向把蒸馏模型当作 64K coding 默认模型；到了 262K 极限档，我也更信它。**

## 2. 三轮分别看到了什么

### 第一轮：64K，10 个真实 coding 任务

这是最早的一轮基准线，对比的是：

- 现网 `UD-Q4_K_XL`
- 蒸馏 `Claude-4.6-Opus-Reasoning-Distilled Q4_K_M`

当时的核心结论是：

- 蒸馏模型整体略好，但优势还是“小幅领先”
- 它在分页边界、协议暴露这类题上更容易直接给到正确落点
- 基线在个别偏架构 restore 题上不差，但经常更像在“想”，不一定更像在“交付”

参考报告：

- `output/model-compare/20260308-120818/summary/model_compare_detailed_report.md`

### 第二轮：64K 扩展轮，22 个更贴近日常业务的任务

这一轮比第一轮更有代表性，因为题型扩大到了：

- `14` 个 Java / Spring 多文件业务题
- `4` 个 TypeScript / CodexGame 真实仓库题
- `4` 个日常脚本 / agentic coding 题

这一轮的量化结果：

- 基线：`22 / 22` 成功
- 蒸馏：`22 / 22` 成功
- 平均耗时：基线 `29.79s`，蒸馏 `27.11s`
- 平均生成速度：基线 `42.33 tok/s`，蒸馏 `44.29 tok/s`
- 平均显存占用：基线 `18689.66 MiB`，蒸馏 `17647.54 MiB`

更重要的是质量侧结论：

- 蒸馏模型明显更好：`11` 题
- 基线明显更好：`2` 题
- 基本同级：`9` 题

这一轮最重要的发现不是“蒸馏赢了 11 题”，而是：

- 基线有 `7` 题 `content = ""`
- 也就是主要答案掉进了 `reasoning_content`
- 这对真实使用是硬伤，因为用户看到的 final answer 可能是空的或近乎空的

而蒸馏模型在这轮里：

- `content = ""` 的题是 `0`
- 也更少出现明显截断和半截答案

也就是说，这一轮真正拉开差距的不是抽象“智力”，而是**回答成品率**。

这一轮我会把蒸馏模型的优势总结成三类：

1. **最小修复更稳**
   - `java_idempotency_payment_callback`
   - `java_outbox_publish_before_commit`
   - `java_cache_stale_after_write`
   - `java_retry_duplicate_side_effect`
   - `java_permission_scope_trust_bug`

2. **协议 / runtime state 边界更清晰**
   - `ts_runtime_metrics_protocol`

3. **脚本题更像真实可执行产物**
   - `script_bash_log_triage`
   - `script_python_jsonl_replay_analyzer`
   - `script_bash_atomic_deploy`

基线仍然有价值的地方：

- `java_pagination_boundary`
  - 这题蒸馏反而被接口命名带偏，往 `endInclusive + 1` 这种错误方向走
- `script_python_csv_reconcile`
  - 两边都不够完美，但基线更贴近“差异 CSV + 人类摘要”这个原始要求

参考报告：

- `output/model-compare-v2/20260308-130031/64k/summary/compare_report.md`

## 3. 第三轮：262K extreme 长上下文

这一轮不再考“常规 64K coding”，而是考：

- 长日志
- 大量重复噪声中的 root cause 提取
- 极限上下文下的最小修复/最小脚本能力

实际打进模型的 prompt token：

- `194k ~ 199.5k` token 的任务，两边都能真实跑起来
- 这说明 262K 在这台 4090 上不是纸面参数，至少在 `~200k prompt tokens` 量级上是真能工作的

这一轮的主跑结果：

- 基线：`2 / 4` 成功
- 蒸馏：`3 / 4` 成功

但要更细地看：

- 其中 `extreme_reconcile_script_longctx` 两边都失败
- 失败原因不是模型，而是任务输入本身超了上下文上限：
  - `361,560 ~ 361,561 prompt tokens`
  - 服务端明确返回 `exceed_context_size_error`

所以把这个硬超界任务剔掉后，真正有意义的是另外 3 题：

- `extreme_restore_bootstrap_longctx`
- `extreme_runtime_metrics_longctx`
- `extreme_java_change_impact_longctx`

这三题上：

- 蒸馏主跑 `3 / 3` 都给出可用答案
- 基线主跑 `2 / 3`，其中一题需要 rerun 才恢复

更关键的是答案质量：

- `restore_bootstrap`
  - 蒸馏更接近真实 bug：抓到 `phase=running` 早于 thread bootstrap
  - 基线更像停在表层症状
- `runtime_metrics`
  - 蒸馏直接命中 protocol-first / runtime-state 边界
  - 基线首跑断开，重跑后又开始往 `world.snapshot` 方向漂
- `java_change_impact`
  - 蒸馏能把答案收敛到最小 idempotency guard
  - 基线出现 invented API / 截断风险

资源侧也支持这个判断：

- 基线 262K 平均显存占用：`22975.35 MiB`
- 蒸馏 262K 平均显存占用：`21987.11 MiB`

也就是说，在已经非常紧绷的 262K 档里，蒸馏模型大约还多出接近 `1 GiB` 的余量。

参考报告：

- `output/model-compare-v2/20260308-130031/262k/summary/compare_report.md`

## 4. 为什么现在我的偏向更明确了

如果只看第一轮，我会说：

- 蒸馏略好
- 但不值得过度解读

现在看完三轮，我的偏向明显加强了。原因是三轮里出现的是**同一类优势反复出现**，而不是偶然题型碰巧占优。

### 4.1 蒸馏模型更像“交付型回答”

这点在第二轮最明显。

基线的问题不是不知道，而是：

- 很多时候把关键内容留在 `reasoning_content`
- `content` 为空或过短
- 实际交付体验差

对真实 coding 使用，这比“某一题思考深一点”更重要。

### 4.2 蒸馏模型在最小修复上更稳定

三轮下来，蒸馏模型更常做到：

- 先抓真实业务 bug
- 再把修复收敛到最小变更面
- 最后补上合理的 regression checks

它不总是最有“哲学味”的，但更像能直接拿去改代码。

### 4.3 蒸馏模型在长上下文下更可信

262K 这一轮很关键，因为它回答的是一个和 64K 不同的问题：

- 不是“常规 coding 谁更顺”
- 而是“极限上下文谁更容易保持方向不漂”

在这方面，我现在更信蒸馏模型。

## 5. 那基线还值不值得留

值，但定位要更清楚。

我现在不会说 `UD-Q4_K_XL` 没价值。它仍然有两个可取点：

- 在个别题上会给出更长、更展开的思考
- 在少数偏架构、偏恢复流程的题里，它不一定更差

但它现在的问题也很明确：

- 成品率不够稳定
- 容易把 final answer 留空
- 在极限长上下文下更容易出现断连、漂移或 invented API

所以它更像：

- 一个仍然能用的深思考备选
- 而不是我现在最想留作默认入口的模型

## 6. 我的综合偏向

到这一步，我的综合偏向是：

### 默认 64K coding 模型

选：`Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled Q4_K_M`

原因：

- 成品率更高
- 业务 bug / 最小修复更稳
- 平均更快
- 平均更省显存

### 262K extreme 模型

如果你确实要在这台 4090 上跑长上下文极限任务，我也更偏向蒸馏模型。

原因：

- 主跑成功率更高
- 同样 `195k~199k` prompt token 下更稳
- 长上下文约束保持更好
- 失败更像清晰的输入边界，而不是莫名其妙的中途断开

## 7. 最终一句话

如果现在让我在这台 4090 上为你选一个更适合真实 coding 的默认模型，我会选：

**`Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled Q4_K_M`**

而且这次不是“略微偏向”，而是经过三轮之后，**偏向已经比较明确**。它不是每题都赢，但在“真实可用性、最小修复落地、正文成品率、长上下文稳定性”这四个更重要的维度上，已经连续赢了。 
