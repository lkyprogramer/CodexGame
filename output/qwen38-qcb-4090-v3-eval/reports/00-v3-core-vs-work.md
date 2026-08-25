# 最终评估：V3 200K MTP n=2 core vs 冻结 WORK

日期：2026-08-24  
数据：跳板机 `reports-4090-v3.zip` + `results-4090-v3.zip`（core JSONL 96 行齐全，可做配对）。  
对照：冻结 WORK Optimized `bee238…` 112K q8 MTP n=2，Hard 45/96。  
候选：现网 WORK Dynamic V3 `3f227079…` 200K q4 MTP n=2。  
这是 **权重 + 窗口 + KV** 的组合对照，不能把分数差单独记在 V3 或 200K 头上。

## 结论

**Hard 打平，不是质量升级，也不该回滚。**  
96 对完全配对：两边都是 **45/96 = 46.9%**，McNemar 独赢各 16，p=1。QCB 预声明门槛 **不能声明 practical win**（Hard CI 下界 −10.4pp，CBI +1.6pp 不到 +2）。

真正变的是 **agent 环**：AT003 从 1/3 空转变成 3/3 打补丁，agent_tool Hard 58%→83%，exhausted 16→13。代价是 **bug_fix 12/18→9/18**。Code review 仍是 0/12。速度与现网同档（decode 77 vs 77 tok/s）。

**现网继续 V3 200K n=2。** 窗口和收工行为值这个组合；不要用 smoke 5/12 当「变聪明了」，也不要用 core 打平当「V3 没用」。

## 总表

| | 冻结 WORK 112K q8 | 现网 V3 200K q4 | Δ |
|---|---:|---:|---:|
| Hard | **46.9%** 45/96 | **46.9%** 45/96 | 0 |
| Partial | 55.4% | 56.2% | +0.8pp |
| CBI | 46.7% | 48.3% | +1.6pp |
| Worst（类） | CR 6.0% | CR 8.7% | +2.7pp |
| exhausted | **16** | **13** | −3 |
| invalid | 0 | 0 | 0 |
| 工具合法率 | 95.6% | 95.5% | 0 |
| 工具操作成功 | 57.4% | 56.4% | −1pp |
| 公测恢复 | 62.5% (5/8) | **100%** (9/9) | |
| decode tok/s | 76.7 | 77.4 | ≈0 |
| 成功墙钟中位 | 119 s | 103 s | −16 s |
| Peak VRAM | 22730 | 23030 | +300 |
| McNemar | — | 16 / 16，p=1 | |
| QCB practical win | — | **否** | |

配对 Hard 95% CI **[−10.4%, +12.7%]**，P(V3>WORK)=57.6%。

## 六类（Hard）

| 类 | WORK | V3 | 解读 |
|---|---:|---:|---|
| agent_tool | 7/12 **58%** | 10/12 **83%** | AT003 1→3，AT005 0→1。这是唯一质变方向 |
| bug_fix | 12/18 **67%** | 9/18 **50%** | BF006/008/009 各掉 1 |
| repo | 10/24 42% | 11/24 46% | RE006 1→3，RE002 2→0，RE007 3→1 |
| single_file | 11/18 61% | 10/18 56% | SF008/012 各掉 1，SF002 +1 |
| long_context | 5/12 42% | 5/12 42% | 200K 没有抬 LC Hard |
| code_review | 0/12 **0%** | 0/12 **0%** | 地板没动，partial 略好 |

独赢 ≥2 题：V3 拿 AT003、RE006；WORK 拿 RE002、RE007。其余都是 ±1 的种子噪声。

## Smoke 为什么骗人

V3 smoke 曾是 Hard 5/12 vs WORK 3/12。core 打平，说明 smoke n=12 只筛「会不会收工」，不够给六类打分。和 S-list 同一课：Sharp/Salience smoke 好看，core Hard 仍 45/96。

DFlash2 只有 smoke（6/12），**没有 core**，不能拿来和这条 96 样本比质量。

## 和 S-list core 放在一起

S-list 换模板/换 GGUF，Hard 最好也只到 Cold Fusion 46/96。V3 200K 同样停在 45。  
Coding agent 的墙还是：CR 全 0、BF005 全 0、空转题、Java 仓库截断（RE007 这次从 3/3 掉到 1/3）。**不是 MTP n，也不是再加 88K 窗口能拆掉的。**

## 现网建议

1. **保持** 已 enable 的 V3 200K q4 MTP n=2（别名仍 `openclaw/Qwen3.8-27B-WORK`）。
2. **不要**为 Hard 打平而切回旧 112K GGUF。窗口和 AT003 是实打实的运维收益。
3. **不要**把 DFlash2 设成 WORK。
4. 若还要抠质量：Sharp 模板（零换权重、S-list 里 agent 最好）或接受换 GGUF 的 Cold Fusion；都不是质变。下一刀不是再扫 MTP n。

原始报告与 JSONL：`output/qwen38-qcb-4090-v3-eval/from-jump/`。
