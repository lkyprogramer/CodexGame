# QCB smoke：200K+V3 MTP / analogalok DFlash2 vs 冻结 WORK

日期：2026-08-24  
机器：`192.168.10.29`  
套件：QCB-4090 v1.0.0 **smoke 12×seed42**，与 WORK 基线完全配对。  
现网已恢复：`openclaw/Qwen3.8-27B-WORK`，`n_ctx=112128`，22664 / 1553 MiB。未 enable 新 unit。

这是组合配方对照，不是单因子：V3 权重 + q4 KV + 200K 窗口（DFlash2 另换 PR27342 binary）。不能把分数差单独归给「V3」或「200K」。

## 结论

1. **调用质量上，两套都强于冻结 WORK smoke。** Hard 3/12 → V3 MTP **5/12**、DFlash2 **6/12**。空转（`tool_budget_exhausted`）3 → **1**。工具协议没崩（invalid tool-call 仍 ~3–4%）。
2. **Agent 行为才是这次真正分开的地方。** WORK 空转的 SF002 / AT001，V3 MTP 都做成了 PASS；DFlash2 拿下 AT001 和 **LC001**（WORK、V3 MTP 都挂）。Repo 三题 **仍然全 0**。
3. **不要用这 12 题宣布生产切换已证明。** n=1/题，McNemar vs WORK：V3 p=0.63，DFlash2 p=0.25。QCB 自己的 smoke 门槛：V3 MTP **不能**声明 practical win（Hard CI 下界 −8.3pp）；DFlash2 **能**过门槛（CI [16.7%, 50%]，相对 WORK 零独输），但仍是 smoke 方差。S-list 里 Sharp smoke 也曾到 50%，core Hard 却和 WORK 打平。
4. **若只切一档现网：选 V3 + 200K + 原生 MTP n=2。** 现网同一份 binary，decode ~80 tok/s，tools ~88，空载余量 1259 MiB。DFlash2 这轮 Hard 更高，但工具路径 **40 tok/s**、要 PR27342、250K 生成后只剩 25 MiB，不当 WORK。

正式 `enable` 前至少再跑 **core 32×3**，或明确接受「只凭 smoke 换档」。

## 总表

| | WORK 基线 | V3 200K MTP | DFlash2 Q2 200K |
|---|---:|---:|---:|
| 权重 SHA | `bee238…` 旧 XL | `3f227079…` Dynamic V3 | 同 V3 + Q2 草稿 |
| binary | 20260817 | 同左 | **PR27342** |
| `n_ctx` | 112128 q8 | 200192 q4 | 200192 q4 |
| Hard | **25.0%** 3/12 | **41.7%** 5/12 | **50.0%** 6/12 |
| Partial | 28.3% | 45.0% | 65.3% |
| CBI | 25.7% | 42.3% | 61.2% |
| exhausted | **3** | **1** | **1** |
| invalid tool-call | 7 / 213 (3.3%) | 8 / 209 (3.8%) | 7 / 199 (3.5%) |
| 工具操作成功 | 50.5% | **62.2%** | 52.6% |
| decode tok/s 中位 | 78.3 | **80.0** | **40.3** |
| prompt tok/s 中位 | 625 | 863 | 243 |
| Peak VRAM | 22730 | 23030 | 22924 |
| 成功任务/Wall-hour | 5.21 | 12.00 | 7.47 |
| vs WORK McNemar | — | 独赢 3 / 独输 1，p=0.63 | 独赢 3 / 独输 **0**，p=0.25 |
| QCB practical win vs WORK | — | **否** | **是（仅 smoke）** |

DFlash2 smoke 用 **200K**（250K 已做过加载预检，生成后 25 MiB，不适合 12 题长跑）。

## 逐题（seed 42）

| 题 | 类 | WORK | V3 MTP | DFlash2 |
|---|---|---|---|---|
| SF001 | single_file | PASS 80.6s | PASS 34.8s | PASS 143s |
| SF002 | single_file | fail **空转** 850s | **PASS** 112s | fail 220s（跑完但测试挂） |
| BF001 | bug_fix | fail | **PASS** | **PASS** |
| BF004 | bug_fix | PASS | fail **空转** | **PASS** |
| RE001 | repo | fail 空转 | fail（跑完） | fail 空转 |
| RE004 | repo | fail | fail | fail |
| RE007 | repo | fail | fail | fail |
| AT001 | agent | fail **空转** | **PASS** | **PASS** |
| AT002 | agent | PASS | PASS | PASS |
| LC001 | long_ctx | fail | fail | **PASS** |
| CR001 | review | fail | fail | fail |
| CR002 | review | fail | fail | fail |

相对 WORK：

- V3 MTP 独赢 SF002 / BF001 / AT001，独输 BF004。
- DFlash2 独赢 BF001 / AT001 / LC001，**零独输**。
- V3 MTP vs DFlash2：MTP 独赢 SF002，DFlash2 独赢 BF004 + LC001（McNemar p=1）。

## 调用质量怎么读

- **协议**：三套都能稳定出 OpenAI `tool_calls`，invalid 率同量级。不是「V3/DFlash2 把工具打坏了」。
- **收工**：WORK smoke 三题空转到 40 次工具；V3/DFlash2 各只剩 1 题。这就是先前 core 里 AT003 那类 agent 差的同一方向。
- **Hard**：多过的是单文件 / bug / agent /（DFlash2）长上下文；**仓库题仍全灭**，和 S-list core 的 repo 墙一致。
- **速度**：MTP 保持现网 ~80 tok/s；DFlash2 工具路径再次掉到 ~40，和 8-19 矩阵（tools 32–43）一致。GPU 利用率 86% → 44%。

## 不做什么

- 不把 DFlash2 设成开机 WORK。
- 不覆盖旧 GGUF。
- 不拿 smoke 50% 去对标 S-list **core** 46.9%。题型不同，n 也不同。

原始 JSONL / 报告：`output/qwen38-qcb-4090-v3-eval/`。远端：`/home/hhtele/qcb-4090-v3-eval/`。
