# QCB-4090 WORK core 完整基线报告

> 基准：QCB-4090 v1.0.0 · 赛道 **Optimized**（现网 OpenClaw WORK）· Suite **core** 32×3 = 96  
> 日期：2026-08-21  
> 机器：`192.168.10.29` RTX 4090 24GB  
> 配置：`work-udq4xl-optimized-112k-mtp2`  
> 机器报告：[`work-core.md`](work-core.md) · JSON：[`work-core.json`](work-core.json) · 审计：[`work-core-audit.json`](work-core-audit.json)

本报告冻结 **现网 WORK** 作为后续 S 名单（Sharp / grug / Fable / Salience / Cold Fusion）的唯一对照。不是 Normalized 榜，也不是多模型横评。

---

## 1. 一句话结论

现网 Qwen3.8-27B UD-Q4_K_XL（112K / MTP n=2 / medium）在 QCB core 上 **Hard 46.9%（45/96），CBI 46.7%，最差类 code_review 6.0%**。基础设施干净（invalid 0、endpoint error 0、审计通过）。真正的缺口是：**空转打满 40 次工具（16/96）、Java 补丁截断、审查题 0/12 Hard**。短闭环单文件/修 bug 能做；当 coding agent 收工仍不稳定。

Smoke 25%（3/12, n=1）被高方差压低了。core 才是基线。不要用 HumanEval 解释这个数字。

| 推荐 | 内容 |
|---|---|
| 现网默认 | 维持 WORK。core 证明能干活，但不是合格的自主 coding agent。 |
| S 名单第一刀 | Sharp 模板。权重不变，只看空转、截断补丁、CR JSON 有没有好。 |
| 换权重门槛 | 配对 Hard CI 下界 ≥ −3pp，CBI +2pp，CR 不得继续全 0 还自称赢，空转题数要下降。 |
| 本报告不能推出 | 「3.8 比 3.6 强/弱」、Normalized 智力、任何 finetune 已经更好。 |

---

## 2. 运行是否完成

| 项 | 值 |
|---|---|
| nohup 进程 | **已退出**（检查时无 `qcb`/`run_suite` 进程） |
| JSONL | 96 行，无缺无重 |
| 时间窗 | 2026-08-20 09:15:35Z → 13:46:43Z（约 4.5 h 墙钟） |
| 样本墙钟合计 | 4.47 h |
| 日志 | `/home/hhtele/qcb-4090-baseline/logs-core.out` 最后一行 `CR004 seed=47` |
| 审计 | `passed=true`，`--check-artifacts`，108 份 artifact 齐全 |
| 模型哈希 | 96/96 `match`，SHA256 `bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372` |

远程真源：

```text
/home/hhtele/qcb-4090-baseline/results/work/work-udq4xl-optimized-112k-mtp2-optimized-core.jsonl
```

本地副本：`output/qwen38-qcb-4090-baseline/results/work/`。

---

## 3. 冻结实验身份

| 项目 | 值 |
|---|---|
| Lane | optimized（现网 WORK，不是 Normalized） |
| 别名 | `openclaw/Qwen3.8-27B-WORK` |
| GGUF | `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf` |
| Template | `official-jinja-medium`（嵌入官方 jinja） |
| Context | 112000，KV q8_0 |
| MTP | n=2 |
| Reasoning | medium，经 `chat_template_kwargs` |
| 采样 | temp 1.0 / top_p 0.95 / top_k 20 |
| `max_tokens` | 8192 |
| `max_tool_calls` | 40 |
| Seeds | 11, 29, 47 |
| llama-server | `/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server`（空正文补丁） |

启动参数以 `OPENCLAW_QWEN38_4090_RUNBOOK.md` 第三节为准。本轮未改 18343。

---

## 4. 质量主表

| 指标 | core 96 | smoke 12（seed 42） | 说明 |
|---|---:|---:|---|
| Hard Success | **46.9%（45/96）** | 25.0%（3/12） | smoke n=1 偏低，不当智力分 |
| Partial | 55.4% | 28.3% | |
| CBI | **46.7%** | 25.7% | 六类等权 |
| Worst Category | **6.0%（code_review）** | 0%（n=1 无意义） | 审查 0/12 Hard |
| Invalid output | 0% | 0% | 无「交不出 diff/JSON」 |
| Infrastructure | 0% | 0% | 服务未崩 |
| 不稳定题 | **53.1%（17/32）** | 0%（单 seed） | 同题跨 seed 有过有挂 |
| `completed` | 80 | 9 | |
| `tool_budget_exhausted` | **16** | 3 | 打满 40 次；其中 1 次仍 Hard PASS（AT003/29） |

按 seed：11 → **17/32**；29 → 14/32；47 → 14/32。没有单 seed 崩盘。

---

## 5. 六类矩阵

| 分类 | 题/跑 | Hard | Partial | CI | 成功耗时中位 |
|---|---:|---:|---:|---:|---:|
| single_file | 6 / 18 | 61.1% | 64.3% | 61.7% | 119.9 s |
| bug_fix | 6 / 18 | **66.7%** | 66.7% | **66.7%** | 161.4 s |
| repo_engineering | 8 / 24 | 41.7% | 54.2% | 44.2% | 125.9 s |
| agent_tool | 4 / 12 | 58.3% | 58.3% | 58.3% | 55.5 s |
| long_context | 4 / 12 | 41.7% | 50.0% | 43.3% | 87.1 s |
| code_review | 4 / 12 | **0.0%** | 30.0% | **6.0%** | N/A |

能打补丁的短任务（SF/BF）是强项。仓库和长上下文大约四成。审查是结构性失败，不是「差一点」。

---

## 6. 逐题 × Seed（P=隐藏测试过）

| 题 | 类 | 11 | 29 | 47 | Hard | 备注 |
|---|---|:---:|:---:|:---:|---:|---|
| SF001 | SF | F | F | P | 1/3 | 失败侧编译截断 / 符号缺失 |
| SF002 | SF | P | F | F | 1/3 | smoke 也挂；47 打满预算 |
| SF003 | SF | F | P | F | 1/3 | |
| SF006 | SF | P | F | P | 2/3 | |
| SF008 | SF | P | P | P | **3/3** | |
| SF012 | SF | P | P | P | **3/3** | |
| BF001 | BF | P | P | F | 2/3 | |
| BF004 | BF | P | P | P | **3/3** | smoke 也过 |
| BF005 | BF | F | F | F | **0/3** | 三次都打满 40；几乎不收工 |
| BF006 | BF | P | F | P | 2/3 | |
| BF008 | BF | P | P | P | **3/3** | 成功但贵（中位 236 s / 20k tok） |
| BF009 | BF | F | P | P | 2/3 | |
| RE001 | RE | P | F | F | 1/3 | 29/47 空转 `patch_bytes=0` |
| RE002 | RE | P | P | F | 2/3 | |
| RE003 | RE | F | F | F | **0/3** | 断言 `trim` 或补丁截断 |
| RE004 | RE | P | F | F | 1/3 | 失败 seed 仍有 0.67 partial |
| RE005 | RE | F | F | F | **0/3** | 截断编译 / 导入断言 |
| RE006 | RE | P | F | F | 1/3 | |
| RE007 | RE | P | P | P | **3/3** | smoke 挂、core 稳过（n=1 陷阱） |
| RE009 | RE | P | F | P | 2/3 | |
| AT001 | AT | P | P | P | **3/3** | smoke seed42 空转 0 字节；core 全过 |
| AT002 | AT | P | P | P | **3/3** | |
| AT003 | AT | F | P | F | 1/3 | **三次都 outcome=exhausted**；29 仍过隐藏测试 |
| AT005 | AT | F | F | F | **0/3** | 11 空转 0 字节；后两次语义未打准 |
| LC001 | LC | F | F | P | 1/3 | |
| LC002 | LC | F | P | F | 1/3 | |
| LC003 | LC | P | P | F | 2/3 | 47 打满预算 |
| LC004 | LC | F | F | P | 1/3 | |
| CR001 | CR | F | F | F | **0/3** | 11/47 **非法 JSON**；29 缺 UNTRUSTED_KEY/FAKE_CRYPTO |
| CR002 | CR | F | F | F | **0/3** | 多次缺 CALLBACK_LOCK |
| CR003 | CR | F | F | F | **0/3** | 缺 SYMLINK/SIZE |
| CR004 | CR | F | F | F | **0/3** | 缺 TIMESTAMP/DEDUP_RACE |

**3/3 稳过（7 题）：** AT001, AT002, BF004, BF008, RE007, SF008, SF012。  
**0/3 稳挂（8 题）：** AT005, BF005, RE003, RE005, CR001–CR004。  
其余 17 题跨 seed 摇摆——这就是 `unstable_task_rate=53.1%`。

---

## 7. 失败根因（不要合成「模型不会写代码」）

样本分三类，可并存。

### 7.1 空转烧预算（16 次 `tool_budget_exhausted`）

打满 40 次。中位墙钟 **377 s**（成功任务中位 119 s）。其中 `patch_bytes=0` 的有：BF005/11、AT005/11、RE001/29、RE001/47、LC001/29。

BF005 **三 seed 全 exhausted**，是最干净的「不会停手」题。AT003 三次 exhausted 但 seed 29 补丁过了隐藏测试：Hard 按 verifier，不按 outcome 字段。

加 `max_tool_calls` 不会修这类题，只会更贵。S 名单要看：**exhausted 次数降、且 AT/RE 的 `apply_patch` 字节上升。**

### 7.2 补丁截断 / 语义未打准（completed 但隐藏测试失败）

反复出现 `reached end of file while parsing`（SF001/11、RE003/29、RE005/11+29、AT005/11）。这是思考+补丁把 `max_tokens` 或工具参数写爆，文件不闭合。另一部分是补丁能编译但断言失败（RE003 `trim`、AT005 SQL 切片、RE004 tags/bool）。

`patch_bytes=0` 共 18 次，全部在失败样本里（审查题本来就不打补丁，占 12 次；其余 6 次是真的没改仓库）。

### 7.3 审查格式与召回（CR 0/12 Hard）

- CR001：2/3 交不出合法 JSON（`Expecting value: line 1 column 1`）。
- CR002–CR004：JSON 能解析，但 required issue 永远缺一块（CALLBACK_LOCK、SYMLINK/SIZE、TIMESTAMP/DEDUP_RACE）。Partial 0.2–0.6，从未过阈值。

这是「读完不会按 rubric 交卷」，不是工具坏了。审查题工具只有读/搜，调用次数 2–6，没有空转。

---

## 8. Agent / 工具

| 指标 | 值 |
|---|---:|
| Tool calls | 1760 |
| Invalid tool calls | 78 |
| Valid tool-call rate | **95.6%** |
| Failed operations | 717 |
| Tool operation success | 57.4% |
| Public test runs | 28 |
| Recovery candidates | 8 |
| Recovery | **5/8 = 62.5%** |

工具 JSON 基本合法。失败在选错动作、补丁打不上、公开测试红了不收敛。公开测试一旦用起来，一半以上能救回来——问题是多数题根本很少跑 `run_tests`（smoke 几乎没跑）。

---

## 9. 效率与 4090（只描述，不拿来赢）

| 指标 | 值 |
|---|---:|
| 成功任务墙钟 P50 / P90 | 119.1 s / 239.6 s |
| 成功 completion token 中位 | 10790 |
| 成功任务 / 墙钟小时 | 10.08 |
| Prompt / decode tok/s 中位 | 714.1 / 76.7 |
| MTP acceptance | 62.6% |
| Peak VRAM | 22730 MiB |
| Peak power / temp | 446.1 W / 88 °C |
| Reasoning token | **N/A**（覆盖率 0；后端没回 `reasoning_tokens`，不能当 0） |
| 全场 completion token | 1,233,967 |

空转题又慢又贵。效率比较必须限制在 Hard 过门的任务上。BF008 3/3 过但中位 236 s / 20k tok，是「能过但不便宜」。

---

## 10. 和 smoke 的关系

重叠 12 题：

| 题 | smoke 42 | core 11/29/47 |
|---|:---:|---|
| SF001 | P | FFP |
| SF002 | F | PFF |
| BF001 | F | PPF |
| BF004 | P | PPP |
| RE001 | F | PFF |
| RE004 | F | PFF |
| RE007 | F | **PPP** |
| AT001 | F（40 次、0 字节） | **PPP** |
| AT002 | P | PPP |
| LC001 | F | FFP |
| CR001 | F | FFF |
| CR002 | F | FFF |

AT001 / RE007 从 smoke 挂变成 core 稳过，正好说明 n=1 不能给六类打分。CR 两边都是 0，这个信号稳定。

---

## 11. 对 S 名单的含义

WORK 已经证明：

1. **不是工具协议坏了**（合法率 95.6%，invalid output 0）。
2. **不是完全不会打补丁**（7 题 3/3，agent 题 AT001/AT002 全过）。
3. **缺的是停手、闭合补丁、按 JSON rubric 交审查。**

因此候选模型的第一观察点，按优先级：

1. `tool_budget_exhausted` 是否从 16/96 下降，尤其 BF005 / AT003 / RE001。
2. Java `reached end of file while parsing` 是否减少。
3. CR001 能否交出合法 JSON，CR002–004 的 required issue 能否凑齐。
4. Hard / CBI 相对本表的配对差。

Sharp 只改模板：若这三项不动，说明不是「官方模板太啰嗦」那么简单。grug 若 XML 工具收不成 OpenAI `tool_calls`，smoke 就会一票否决，不必等 core。

---

## 12. 产物清单

| 文件 | 用途 |
|---|---|
| `reports/work-core.md` | QCB 机器报告（身份/质量/六类/效率/逐题） |
| `reports/work-core.json` | 同上结构化 |
| `reports/work-core-audit.json` | 96 对齐全、artifact 齐全、`passed=true` |
| `reports/work-core-full.md` | 本文件（根因与基线冻结） |
| `reports/logs-core.out` | nohup 逐题 PASS/FAIL |
| `results/work/...-core.jsonl` | 96 条原始记录 |
| 远程 artifact | `/home/hhtele/qcb-4090-baseline/results/work/artifacts/`（18 MB / 108 份，未全量拉回） |

---

## 13. 限制

- 只覆盖 Optimized 现网配方。不能外推 Normalized、Q4_K_M、关 MTP、或 temp=0。
- llama.cpp 不回 reasoning token，思考成本只能从 completion + 墙钟间接看。
- 未做私有 Java 回放、未做人工补丁抽检全量（截断/空转已从 verifier stdout 抽样）。
- AT003/29 的 Hard PASS 伴随 exhausted outcome：报告 Hard 时以 `verification.passed` 为准，与 QCB 聚合器一致。
