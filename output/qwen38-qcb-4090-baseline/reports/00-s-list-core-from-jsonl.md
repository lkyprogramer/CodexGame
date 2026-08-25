# QCB-4090 S 名单 core：JSONL 详细结论

日期：2026-08-23  
数据：`results.zip`（跳板机），六个 Config 各 96 行 core JSONL，`(task, seed)` 与 WORK **完全配对**。  
对照：WORK Optimized UD-Q4_K_XL 112K MTP n=2 medium。  
限制：McNemar 已算；无人工全量补丁审阅。thinking chars 不是 API reasoning token。

---

## 1. 一句话

**Hard 上没有人显著打败 WORK。** Sharp / Salience 与 WORK 打成 45–45（各 +14/−14），Cold Fusion 46 vs 45（+19/−18，p≈1）。Fable 略差不显著。**Grug 显著更差**（15 vs 45，p≈0）。

有工程意义的分化在 **Agent 环 vs 仓库/修 bug**：

- Sharp / Salience / Cold Fusion：**更会停手、更会打 AT 补丁**（AT003 1/3→3/3）。
- 同一批模型：**RE007（WORK 3/3）几乎全灭**，主因 Java 补丁截断 `reached end of file while parsing`。
- Grug：思考正文最短（chars ≈ Sharp 的 1/8），但是靠空转（37/96）和 invalid（18/96）换来的，**不能当 coding agent**。

现网：**先不换权重。** 只想改善空转/工具，上 Sharp 模板。换 GGUF 没有统计上的 Hard 收益。

---

## 2. 配对 Hard（McNemar，相对 WORK）

| 候选 | Hard | +独赢 | −独输 | 双过 | 双挂 | p（双侧精确） | Holm 后 |
|---|---:|---:|---:|---:|---:|---:|---|
| Sharp | 45/96 | 14 | 14 | 31 | 37 | 1.00 | 不显著 |
| Salience | 45/96 | 19 | 19 | 26 | 32 | 1.00 | 不显著 |
| Cold Fusion | 46/96 | 19 | 18 | 27 | 32 | 1.00 | 不显著 |
| Fable | 40/96 | 13 | 18 | 27 | 38 | 0.47 | 不显著 |
| Grug | 15/96 | 9 | 39 | 6 | 42 | ≈0 | **显著更差** |

Holm 五次比较后，只有 Grug 能下「与 WORK 不同」的结论。Cold Fusion 多 1 题是噪声。

CBI 仍按方案点估计：Cold Fusion 51.0%、Sharp 49.8%、Salience 49.1%、WORK 46.7%、Fable 45.8%、Grug 17.6%。CBI +2pp 过线的是前三个，**但 Hard 配对不支持「更会过隐藏测试」。**

---

## 3. 六类过题数（/n）

| 类 | n | WORK | Sharp | Salience | CF | Fable | Grug |
|---|---:|---:|---:|---:|---:|---:|---:|
| agent_tool | 12 | 7 | **11** | 10 | 9 | 8 | 1 |
| single_file | 18 | 11 | 12 | **14** | 13 | 6 | 2 |
| bug_fix | 18 | **12** | 9 | 8 | 9 | 8 | 2 |
| repo | 24 | **10** | 7 | 8 | 7 | 8 | 5 |
| long_context | 12 | 5 | 6 | 4 | 6 | **9** | 0 |
| code_review | 12 | 0 | 0 | 1 | 2 | 1 | **5** |

模式稳定：finetune/模板吃 Agent 和部分单文件，吐出 bug_fix 和仓库。审查只有 Grug 明显会交卷。

---

## 4. Agent 行为（这才是名单要测的）

| | exhausted | 非 CR 的 `patch_bytes=0` | 编译截断/EOF | AT003 | AT005 | BF005 | RE007 |
|---|---:|---:|---:|---|---|---|---|
| WORK | 16 | 6 | 14 | 1/3 | 0/3 | 0/3 | **3/3** |
| Sharp | **11** | 5 | 11 | **3/3** | **2/3** | 0/3 | 0/3 |
| Salience | **10** | **2** | 14 | **3/3** | **2/3** | 0/3 | 0/3 |
| Cold Fusion | 17 | 6 | 14 | **3/3** | 1/3 | 0/3 | 1/3 |
| Fable | 15 | 3 | 18 | 2/3 | 0/3 | 0/3 | 0/3 |
| Grug | **37** | **43** | 15 | 0/3 | 0/3 | 0/3 | 0/3 |

AT003/AT005 是 WORK smoke/core 的空转代表题。Sharp/Salience/CF 都把它做成了会打补丁。  
BF005 六个模型 **全 0/3**：不是模板问题，是这题本身对 27B agent 太坑。  
RE007：WORK 三次补丁都过；其他模型反复 `Paginator.java: reached end of file while parsing`。这是 **max_tokens=8192 下的截断**，不是「不会分页」。

---

## 5. 思考量（reasoning_content 字符，禁止叫 Reasoning Token）

WORK core 是旧 runner，无 thinking chars。五个新候选全覆盖。

| | thinking chars P50 | 成功 / 失败 | LLM 轮次 P50 | completion P50 |
|---|---:|---:|---:|---:|
| Sharp | 23415 | 24997 / 20148 | 10.5 | 9522 |
| Salience | 18277 | 18319 / 18235 | 11 | 8139 |
| Cold Fusion | 16866 | 18806 / 12206 | 10.5 | 7249 |
| Fable | 12131 | 10791 / 16212 | 13 | 6929 |
| Grug | **2885** | **764 / 3100** | **22.5** | 5515 |

- Grug 少思考是真的，轮次翻倍，任务失败。
- Sharp **没有**减少思考，它赢在 AT 选择而不是更短的 think。
- Cold Fusion 思考量只略低于 Sharp，没有作者说的 1/5–1/2。
- 成功任务并不更短 think（Sharp/Salience/CF 成功侧 chars ≥ 失败侧）。

---

## 6. 失败形态（不要合成「不会写代码」）

1. **空转** `tool_budget_exhausted`：Grug 37，WORK 16，Salience 10 最好。Sharp 从 16 降到 11，且 AT003 不再打满。
2. **Java 补丁截断**：RE007 上 Sharp/Salience/Fable/CF 多次 EOF。WORK 反而过了。换模型没有修这个问题。
3. **审查**：WORK/Sharp 仍 0/12 Hard。Grug 5/12，这是它唯一的真赢面。
4. **Grug `invalid_output` 18 次**：不全是 JSON 坏了，有的是测试 FAIL 被记成这类；无论记账，Hard 已经崩。
5. **Fable 1 次 endpoint_error**（RE005），96 对仍齐。

---

## 7. 方案门槛（用 JSONL 复核）

| 门槛 | Sharp | Salience | CF | Fable | Grug |
|---|---|---|---|---|---|
| Hard 配对非劣（CI 下界 ≥ −3pp） | 点估计 0，对称 14/14，**不能声称更优** | 同左 | +1 题，不显著 | −5.2pp，McNemar 不显著但点估计破地板 | 显著更差 |
| CBI +2pp | +3.1 | +2.4 | +4.3 | 否 | 否 |
| agent ≥30% / repo ≥20% | 92% / 29% | 83% / 33% | 75% / 29% | 67% / 33% | **8%** / 21% |
| exhausted <16 或 AT 补丁变好 | 11，AT003 3/3 | 10，AT003 3/3 | 17，但 AT003 3/3 | 15，AT003 2/3 | 37 |

文字门槛 Sharp/Salience/CF 仍「可讨论换现网」。JSONL 后的统计结论是：**换了 Hard 不会更好，Agent 环会更好，仓库题会更差。**

---

## 8. 分类

| 角色 | 选择 | 依据 |
|---|---|---|
| 最高 Hard | 与 WORK 打平；CF 多 1 题无统计意义 | McNemar |
| **最佳 Coding Agent** | **Salience**（空转最少、AT 10/12、非 CR 零补丁最少）或 **Sharp**（同卡同权重，AT 11/12） | exhausted + AT |
| 模板-only | Sharp 改变的是工具行为，不是思考长度 | chars 仍最高 |
| 思考最短 | Grug | 不可用 |
| 审查最好 | Grug 5/12 | 以编码为代价 |
| 不推荐换现网 | Grug、Fable | Hard |
| 现网默认 | **维持 WORK**；若只修空转，加 Sharp 模板 | 零量化差 |

---

## 9. 本地路径

```
output/qwen38-qcb-4090-baseline/from-jump/results.zip
output/qwen38-qcb-4090-baseline/from-jump/results/<config>/*-core.jsonl
```

artifacts 仍在 zip 里未全量解开（五千文件）。需要复盘某题补丁时再按 run_id 抽。
