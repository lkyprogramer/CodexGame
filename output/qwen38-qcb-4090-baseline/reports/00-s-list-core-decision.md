# QCB-4090 S 名单 core 结论

日期：2026-08-23  
数据：跳板机 `reports.zip`（仅正式报告+审计，**无 JSONL**，不能做 McNemar / 配对 95% CI）  
赛道：Optimized · suite core · 32×3=96 · seeds 11/29/47  
审计：六个 Config 均 `passed=true`、96 对齐全、哈希 match。Fable 有 1 条 `endpoint_error`（RE005），审计仍过。

WORK 是冻结对照：Hard **45/96 = 46.9%**，CBI **46.7%**，exhausted **16/96**，CR Hard **0/12**。

---

## 1. 结论（先看这个）

没有出现碾压 WORK 的 coding agent。Hard 上 **Sharp / Salience 与 WORK 打平（45/96），Cold Fusion 多 1 题（46/96）**。

按方案预声明门槛（Hard 非劣、CBI +2pp、agent/repo 不崩、空转下降或 AT 补丁变好）：

| 候选 | 换现网？ | 原因 |
|---|---|---|
| **Sharp 模板** | 可以讨论，零换权重 | Hard 打平，CBI 49.8%（+3.1pp），exhausted 11，**agent_tool 58%→92%**。代价：repo 42%→29%，RE007 从 3/3 掉到 0/3 |
| **Salience-R5** | 可以讨论 | Hard 打平，CBI 49.1%（+2.4pp），**exhausted 最少 10**，agent 83%。bug_fix 变弱 |
| **Cold Fusion V1.1** | 可以讨论 | **Hard 46/96、CBI 最高 51.0%（+4.3pp）**，CR 第一次不是地板（2/12）。exhausted 17，略多于 WORK |
| Fable | 否 | Hard 40/96（−5.2pp，破 −3pp 地板），CBI 未达 +2pp |
| Grug | 否 | Hard 15.6%，invalid 25%，exhausted 37，agent 8.3%。**不是 coding agent** |

现网默认建议：**先不要换权重。** 若只想改善「停手 / 打补丁」，**Sharp `--chat-template-file` 成本最低**。若接受换 GGUF，质量略高选 Cold Fusion，空转最少选 Salience。三者都不是质变。

---

## 2. 主表

| | WORK | Sharp | Salience | Cold Fusion | Fable | Grug |
|---|---:|---:|---:|---:|---:|---:|
| Hard | **46.9%** | 46.9% | 46.9% | **47.9%** | 41.7% | 15.6% |
| 过题 | 45 | 45 | 45 | **46** | 40 | 15 |
| CBI | 46.7% | 49.8% | 49.1% | **51.0%** | 45.8% | 17.6% |
| Worst（类） | CR 6.0% | CR 7.3% | CR 15.7% | **CR 23.7%** | CR 16.7% | LC 1.2% |
| exhausted | 16 | **11** | **10** | 17 | 15 | 37 |
| invalid | 0 | 0 | 0 | 0 | 0 | **25%** |
| 工具合法率 | 95.6% | 95.6% | 95.4% | 95.3% | 96.2% | 97.7% |
| 不稳题 | 53.1% | 50.0% | 59.4% | 53.1% | 46.9% | 28.1% |
| 成功/小时 | 10.08 | 8.87 | 10.13 | **10.75** | 9.92 | 3.40 |
| completion P50 | 9559 | 9522 | 8139 | 7249 | 6929 | 5515 |
| thinking chars P50 | N/A（旧 runner） | 23415 | 18277 | 16866 | 12131 | **2885** |
| 成功墙钟 P50 | 119 s | 130 s | 104 s | 113 s | 71 s | 60 s |

thinking chars **不是** API reasoning token。Grug 思考正文确实短（约 Sharp 的 1/8），但靠空转把 completion 和 Hard 打穿。

---

## 3. 六类 Hard

| 类 | WORK | Sharp | Salience | CF | Fable | Grug |
|---|---:|---:|---:|---:|---:|---:|
| agent_tool | 58.3% | **91.7%** | 83.3% | 75.0% | 66.7% | 8.3% |
| single_file | 61.1% | 66.7% | **77.8%** | 72.2% | 33.3% | 11.1% |
| bug_fix | **66.7%** | 50.0% | 44.4% | 50.0% | 44.4% | 11.1% |
| long_context | 41.7% | 50.0% | 33.3% | 50.0% | **75.0%** | 0% |
| repo | **41.7%** | 29.2% | 33.3% | 29.2% | 33.3% | 20.8% |
| code_review | 0% | 0% | 8.3% | **16.7%** | 8.3% | **41.7%** |

共同结构：谁当 coding agent，agent_tool 都上去了；**仓库题和 bug_fix 是 WORK 更稳**。审查只有 Grug 明显会交卷，但它几乎不会写代码。

---

## 4. 对 WORK 的题级进出（3 seed 过题数，不是配对检验）

**Sharp** 更好 8 / 更差 6：AT003 1→3、AT005 0→2；RE007 3→0、BF001 2→0、SF012 3→1。  
**Salience** 更好 7 / 更差 9：同样救了 AT003/AT005、SF001 1→3；RE007 3→0。  
**Cold Fusion** 更好 10 / 更差 8：AT003 1→3，CR003/CR004 各 0→1，SF001 1→3；BF004 3→1、RE007 3→1。  
**Fable** 更好 8 / 更差 10：长上下文很强（LC001/LC002 到 3/3），单文件和 RE007 崩。  
**Grug** 更好 4 / 更差 22：多出来的 4 全是审查。

---

## 5. 方案门槛对照

预声明：Hard CI 下界 ≥ −3pp；CBI +2pp；agent 不得 <30%、repo 不得 <20%；exhausted <16 或 AT/RE 补丁变好。

无 JSONL，Hard 用点估计代替 CI：

- Sharp / Salience：Hard 0pp，CBI 过线，exhausted 下降，agent/repo 过线。
- Cold Fusion：Hard +1pp，CBI 过线，repo 29% 过线，exhausted 17 未降，但 AT003 1/3→3/3 满足「或」支。
- Fable：Hard −5.2pp，未过。
- Grug：全面未过。

**没有一个模型在 bug_fix+repo 上同时优于 WORK。** 换现网等于用 agent 环换修 bug/仓库稳定性。

---

## 6. 分类（方案第 11 节）

| 角色 | 选择 |
|---|---|
| 最高质量（CBI/Hard） | Cold Fusion |
| **最佳 Coding Agent** | **Salience**（空转最少 + AT/SF 强）或 **Sharp**（同权重、AT 最强） |
| 最佳成功任务/小时 | Cold Fusion 10.75（与 WORK 10.08 接近，不是假快） |
| 模板-only 提升 | Sharp：会停手、会打 AT 补丁；**没有减少思考量**（chars 仍很高） |
| 思考最短 | Grug，但任务失败 |
| 不推荐 | Grug 当 coding agent；Fable 换现网 |

---

## 7. 限制

- zip 只有 `*-core.md/json` 和 audit，没有 JSONL / artifact，不能做配对检验，也不能复盘 Java EOF 原文。
- WORK core 仍无 thinking chars（旧 runner）；思考量只能在五个新候选之间比。
- Fable 1 次 endpoint_error 未重跑。
- 全部 Optimized；不能外推 Normalized。

若要做正式 McNemar，需要 4090 上的 `*-optimized-core.jsonl`。
