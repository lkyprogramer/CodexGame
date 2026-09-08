# 现网 NInfer 相对 WORK / vLLM：用实测讲清楚

口径：同一套 HTTP 阶梯 + 同一套 Pi Java 三题 + 同一张 4090。  
三路对齐测的是 **NInfer 221k**（切流前）。现网已是 **262k**，decode/Java 与 221k 同级（见 fusion A2）。  
WORK 的 systemd 本来就是 medium，所以它的 off 表和 medium 表非常接近。

原始表：`results/COMPARE.md`（off）、`results/medium/REPORT.md`、`reports/09-fusion-final.md`、`reports/10-pi-prefix-prod.md`。

---

## 一句话

- **长生成 / 长上下文 decode：NInfer 断层第一**（184k 约 87–98 t/s，WORK ~38，vLLM ~47–53）。
- **超长 prompt 的首字：vLLM 第一**（184k TTFT 66s，NInfer 94s，WORK 134s）。
- **真正干活的 Agent（thinking=medium，现网默认）：NInfer ≥ WORK ≫ vLLM。**
- 质量门（184k 针、Java 3/3）三套都过；NInfer 还把窗口从 200k 拉到 **262k**。

所以切默认是用「decode 和 Agent 墙钟」换掉 WORK，不是用 NInfer 去赢 vLLM 的冷 prefill。

---

## 三套栈分别是什么

| | WORK（旧默认） | **NInfer（现默认）** | vLLM huge-mtp |
|---|---|---|---|
| 引擎 | llama.cpp `llama-server` | tensorninja@44a2c6c | patched vLLM |
| 权重 | UD-Q4_K_XL-dv3 GGUF 16.3G | `.ninfer` groupwise 16.96G | W4A16 AutoRound |
| 窗口 | 200192，KV q4 | **262144**，KV `rk4v4-e8` | 200k 档，KVarN |
| 投机 | MTP n=2 | MTP n=3 + lm-head-draft | MTP n=3 |
| 思考 | medium | medium（兼容层注入） | 测过 medium |
| 调用名 / 口 | `openclaw/Qwen3.8-27B-WORK` :18343 | **同名同口** | `qwen3.8-27b` :18020 |

---

## 1. 长 decode：NInfer 的主优势

thinking=medium（和现网一致）：

| 深度 | WORK | **NInfer 221k** | vLLM | NInfer / WORK | NInfer / vLLM |
|---|---:|---:|---:|---:|---:|
| ~4k | 77.6 | **127.1** | 57.8 | 1.64× | 2.20× |
| ~64k | 60.2 | **110.6** | 63.7 | 1.84× | 1.74× |
| ~120k | 46.5 | **115.4** | 63.4 | 2.48× | 1.82× |
| **184k** | **38.4** | **98.5** | 53.1 | **2.57×** | **1.86×** |

thinking=off 阶梯同一形态：WORK 184k **36.7**，NInfer **87.2**，vLLM **47.4**。  
262k 现网档 off：184k **87.2**，和 221k 持平。

WORK 随深度掉得很快（4k 78 → 184k 38）。NInfer 掉得慢（127 → 98）。这是切默认最硬的一条：Agent 一旦历史变长，NInfer 还在 ~100 t/s，WORK 已经 40 以下。

原因（源码/架构，不是口号）：Ada 重调的 INT8 attention + MTP n=3 接受率在代码/工具轨迹上够用；E8 4-bit KV 让 262k 仍全驻 GPU，没有系统内存 spilling。vLLM 的 MTP 在 Ada 上 decode 没有这条专用路径快。

---

## 2. 首字 / prefill：vLLM 仍最好，NInfer 好于 WORK

medium，184k 档：

| | WORK | NInfer | **vLLM** |
|---|---:|---:|---:|
| TTFT | 133.8 s | 94.1 s | **65.8 s** |
| prefill t/s | 1383 | 1974 | **2802** |

off 深档同样：WORK 133.6s / NInfer 94.6s / vLLM **65.8s**。

读法：

- 扔一个 180k 冷仓库 dump、只要几十字回复：vLLM 先出字。
- 同一 dump 要写长补丁：NInfer 从第 1 个 token 之后把时间抢回来（decode 快 1.9×）。
- WORK 冷 TTFT 和 decode 都最慢。

NInfer 相对 WORK 的 prefill 也有提升（INT8 prefill 路线，作者测过 115k **2409 t/s**；我们 HTTP 184k 仍是 ~1974）。赢不过 vLLM 的 CUDA/Triton 大块 prefill。

---

## 3. Agent 墙钟：默认 medium 下 NInfer 不输 WORK，远好于 vLLM

同一套 Pi Java 三题（过 verify.sh 才算）：

**thinking=medium（现网口径）**

| | 题1 / 题2 / 题3 | p50 | tasks/h | tools/task |
|---|---|---:|---:|---:|
| WORK | 32 / 17 / 53 | 32 s | 35.3 | **9** |
| **NInfer 221k** | 32 / 23 / 31 | **31 s** | **41.9** | 12 |
| vLLM | 86 / 40 / 48 | 48 s | 20.7 | 13 |

**thinking=off（NInfer 当时还不是默认思考）**

| | 题1 / 题2 / 题3 | p50 |
|---|---|---:|
| **WORK** | 27 / 26 / 28 | **27 s** |
| NInfer 221k | 46 / 40 / 28 | 40 s |
| vLLM | 97 / … / …（首题含 JIT）p50 **44 s** | |

**切流后现网 262k medium（2026-09-08 11:44）**：25 / 13 / 19 s，仍 3/3。这不是三路同日重跑，只说明生产档 Agent 没有退化。

要点：medium 下 NInfer 每题 **多打 3 次 tool**，墙钟仍略短。decode 快把多出来的 tool 回合吃掉了。off 时 WORK 更省 tool、更短——那是「思考关着的短任务」，不是现网。

vLLM Agent 始终最慢：短 TTFT 差（4k 6.7s vs NInfer 1.2s）+ 首题 JIT + decode 只有 NInfer 的一半。

---

## 4. 缓存 / 多轮：三套都能命中，NInfer 更适合 tool 追加

100k 级 cache 阶梯（medium）：

| | WORK | NInfer | vLLM |
|---|---:|---:|---:|
| exact TTFT | **0.5 s** | 0.5–0.6 s | 1.6 s |
| append TTFT | 5.0 s | **3.5–3.6 s** | 5.0 s |
| cached tokens | 99695 | **99697** | 字段经常没有 |

现网 Pi 24 次请求（Java 三题，追加历史）：

- prefix 命中 token **154961** vs 实算 prefill **26845** → **约 85%**
- `stable_prefix_restores +20`

HTTP 探针：末尾追加 → 50% 命中；把 reminder 拼进**第一条** user → **0**。  
OpenClaw 若改根消息，会掉光；Pi/正常 tool 追加不会。

---

## 5. 窗口与显存

| | WORK | **NInfer 现网** | vLLM 我们这档 |
|---|---|---|---|
| 有效上下文 | 200192 | **262144** | 200k 级 |
| 184k 针 | 中 | 中 | 中 |
| 空载显存 | ~22958 MiB | **22594 MiB** | 同卡互斥，未当默认 |

E8 KV 的意义就是：24GB 里塞满模型 native 262k，还留 L1 6GiB 给 rolling-tool。WORK 200k q4 已经贴顶；再往上要更残 KV 或砍 MTP。

---

## 6. 质量

- 184k 针：三套全中（包括 NInfer 262k）。
- Java 3/3：三套全过（rk2 旁路 2/3，**没上现网**）。
- 没有做 SWE-bench / 人工代码评审。这里的「质量」= 检索针 + 这三道可验证 Java。不能外推成「比 WORK 更聪明」。

---

## 7. 对照着读：谁适合什么

| 工作负载 | 该用谁 | 依据 |
|---|---|---|
| OpenClaw / Pi，历史会涨到几十 k、要写代码 | **NInfer** | decode 2.5× WORK；medium Java ≥ WORK；262k |
| 每次扔 100k+ 冷仓库、回复很短 | vLLM | 184k TTFT 66s vs 94s |
| 极短、关思考、tool 很少 | WORK 仍能打 | off Java p50 27s vs NInfer 40s |
| 多用户排队 | 谁都不好 | 三套都是单卡单并发 |

---

## 8. 现网切流之后多了什么（相对旧 WORK 运维）

- 口和 model 名没变：`18343` / `28343` / `openclaw/Qwen3.8-27B-WORK`。
- 兼容层把 llama.cpp 的 `chat_template_kwargs` 转成 NInfer，并默认 medium。
- llama.cpp WORK unit **disabled**，随时可 `enable --now` 回滚。

未验证、不要夸大：

- 没有和 WORK 做同日 262k 对打（WORK 上不了 native 262k MTP）。
- 没有证明 OpenClaw 改根 user 时仍 85% 命中（探针是 0）。
- 社区 greedy 148 / 230 t/s 不是 Agent 采样数字。
