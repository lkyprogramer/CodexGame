# 为什么 Lucebox 长上下文慢，以及还能怎么优化

对象：4090 上 Lucebox（IQ4_XS + DFlash2，采样验收，200K q4）vs 现网 WORK（V3 + llama.cpp MTP n=2，200K q4）。  
源码：`/home/hhtele/lucebox-qwen38-4090` HEAD `298031a`（`Luce-Org/lucebox`）。  
本机证据：`03-ctx200k-sampled.md`、`C200Q4.stderr.log`。社区：官方 README / PR #625 / PFlash·KVFlash 文档，以及 X、Reddit。

---

## 先分清两种「慢」

普通人把「长上下文慢」说成一件事，机器里其实是两段：

| 阶段 | 在干什么 | 你的体感 | 本次 180k 针 |
|---|---|---|---|
| **Prefill（读入）** | 把整段历史 squint 一遍，写成 KV | 发出去之后一直转圈，第一个字很晚才来 | **约 163s / 179542 tok ≈ 1100 t/s** |
| **Decode（生成）** | 已经读完，开始往外蹦字 | 开始出字之后的速度 | **0.54s / 28 tok = 51.5 t/s** |

164 秒几乎全是读入。生成只有半秒。  
所以「长上下文劣势」要拆成：**读得比 WORK 慢**，以及 **读完之后写字掉到和 WORK 同一档**。

---

## 1. 大家都会慢：越长越要扫越大的草稿纸

每生成一个新 token，注意力都要看已经写下的全部 KV。上下文从 30 涨到 180000，草稿纸大约大 **6000 倍**。4090 的瓶颈从「算得动」变成「显存带宽扫得动」。

这不是 Lucebox 独有：

- 本机 WORK 近邻（YMQ C0，同卡 llama.cpp、200K、MTP n=2）：**160k decode 48.7 t/s**
- 本机 Lucebox：**180k decode 51.5 t/s**
- 早期 Qwen3.8 MTP：**125k ≈ 54 t/s**
- X 上 4090 + EXL3 + DFlash2（不是 Lucebox）：5K→140，18K→85，73K→28，**146K→16 t/s**（@Oluwaphilemon1，2026-09-03）

**已观察：** 长窗口 decode，Lucebox 并不比 WORK 差，都掉到 ~50。  
**推断：** 再抠 kernel 也抹不平「KV 随长度线性变贵」这条物理曲线，只能减小每次要扫的 KV（窗口、分页、压缩），或少做几次正主前向（规格解码）。

---

## 2. Lucebox 自己多出来的慢：读入，以及验收故意变窄

### 2.1 官方就承认：DFlash2 的 prefill 不如 llama.cpp

PR [#625](https://github.com/Luce-Org/lucebox/pull/625)（Qwen3.8 DFlash2 合入）在 R9700 上写过短 prefill：

| prompt | Lucebox | 上游 llama.cpp |
|---:|---:|---:|
| 512 | 1036 t/s | 1318 |
| 2048 | 1102 | 1277 |
| 6000 | 1038 | 1123 |

同卡本机 28k 冷启动墙钟：Lucebox **18.0s** vs WORK 近邻 **12.7–13.1s**（prefill **2400+ t/s**）。方向一致。

原因（源码 + 配置，已观察）：

- 本次 banner：`chunk = 512`，`pflash = off`，`prefill_cache = 0`，`agent_turn_cache = off`。整段 180k 是 **稠密、分块、无压缩** 的完整 prefill。
- 草稿 DFlash2 也要跟读这段 prompt（Reddit 5090 帖也有人指出：spec 会拖 prefill，因为草稿也要建 KV）。
- PR #625：UD-IQ4_XS 的 **普通前向比纯 IQ4 大约慢 14%**（子 4-bit kernel），换来的是更高接受率；这是质量/速度交换，不是 bug。
- llama.cpp WORK 开了 `-fa on`、`-b 1024 -ub 512`、`--cache-prompt`。Lucebox 冷针测每条 `prefix_len=0`、`pflash=false`，几乎没有前缀复用。

作者自己的定位（PFlash README / @pupposandro）：  
> Long context turns prefill into the silent killer.  
他们为 **Qwen3.6** 做了 PFlash（稀疏读入），**不是** 这次 Qwen3.8 推荐配方的默认。推荐配方是短窗 q8 + DFlash2 打 decode。

### 2.2 源码硬规则：上下文 ≥ 8192，验收宽度 16 → 8

`server/src/qwen35/qwen35_backend.cpp`（约 2736–2782 行）：

```text
kLongCtxNarrowTokens = 8192
kLongCtxMinVerify    = 8
committed >= 8192  →  verify_cap = min(block, max(8, block/2))
```

注释写得很直白：verify 走的是 **多 query 行的 tile kernel**，代价 ∝（验收行数 × KV 长度）。短 prompt 用 block 16 很赚；KV 一长，多出来的行会乘在已经变贵的注意力上，变成负债。

官方自己在 R9700 上的表（同一文件）：

| prompt | verify 16 | verify 8 |
|---:|---:|---:|
| 6,208 | 63.2 | **71.1** |
| 13,148 | 51.9 | 54.9 |
| 26,728 | 43.4 | 46.9 |
| 39,861 | 32.7 | **45.5** |

草稿仍提 16 个，只收窄 **验收批次**。  
**本机 200K 跑已经打出这条日志：**

```text
[qwen35-spec] context 27842 >= 8192: capping verify width 16 -> 8
(wide blocks lose to verify-attention cost at long context)
```

28k 起 avg_commit 从短码的 ~12 掉到 ~7，180k 仍约 5.6。所以长窗口即使还在 `[spec-decode]`，每步正主也只便宜半截，速度自然向 MTP n=2 / 普通 decode 靠拢。

这是 **有意的性能策略**，不是回归。

### 2.3 为了工具正确，他们关掉了最猛的长窗加速

`--fa-window`：源码和 `--help` 都警告，有限窗口会把系统提示 / 工具定义挤出注意力。PR #26 在 3090、60K 上：全窗 ~25 t/s，窗口 2048 → **~91 t/s（3.6×）**，但 **不适合 OpenClaw**。本次 `fa_window = 0`，正确。

`--paged-attention`：**启动即拒绝 `--draft`**，和 DFlash2 互斥。

PFlash / KVFlash 官方测的是 Qwen3.6 / Laguna，推荐 Qwen3.8 配方 **没有** 打开它们。本次 `pflash=off`。

---

## 3. 和 WORK 对照（只谈长上下文）

| | WORK（llama.cpp MTP n=2） | Lucebox DFlash2 采样验收 |
|---|---|---|
| 短 decode | ~75–91 t/s | **140–234 t/s（真优势）** |
| 28k decode | ~75–79 | **116**（仍快） |
| 160–180k decode | **~49**（YMQ C0） | **~52**（持平） |
| 28k 冷 prefill 墙钟 | **13s** | **18s** |
| 180k 冷墙钟 | 无 WORK 本体数；C0 128k 针 49s（可能有 cache） | **164s** |
| 前缀缓存 | `--cache-prompt` 生产开着 | 32 slot 有，针测未命中；`agent-turn-cache` 关 |
| ≥8k 的 spec | MTP 固定 n=2 | **强制 verify 16→8** |
| 官方长窗故事 | 200K 就是为 OpenClaw 会话 | 官方宣传 208 t/s 是 **短 HumanEval / R9700 greedy** |

**一句话：** Lucebox 没在长窗口「写字」上输给 WORK；它输在 **把长历史读进去**，以及 **过了 8k 就主动收窄规格解码**。这和作者产品重点一致：短代码 decode，不是 200K agent 会话。

---

## 4. 社区还说了什么

- Luce 作者 @davideciffa / @pupposandro：长上下文的杀手是 **prefill**；PFlash 声称 3090 上 128K TTFT 24.8s vs llama.cpp ~257s（**Qwen3.6**，keep_ratio 稀疏，不是无损满 KV）。
- KVFlash：decode 从 64K 到 256K 钉在 **38.6 t/s**，显存里只留 72MiB KV；针 14/16，**不保证和满缓存字节相同**。适合「塞进窗口」，不适合当 OpenClaw 无损 200K。
- 官方 Qwen3.8 推荐：IQ4 + DFlash2 block 16 + **q8 KV**，R9700 示例 `--max-ctx 131072`；**没有** 把 200K q4 + PFlash 写成 Qwen3.8 默认。
- r/LocalLLaMA：DFlash2 在代码上加速大、散文上接近白做（PR #625 也写 prose 经常跌破盈亏，会改走普通 decode）。
- 双 3090 vLLM+DFlash2（Reddit）：prefill **1.5–1.7 万 t/s** 量级，那是另一套运行时，不能拿来要求单卡 Lucebox。

---

## 5. 可能的继续优化（按「值不值得在 4090 OpenClaw 上做」排）

### 建议做（低风险，对准真痛点）

1. **Agent 前缀缓存**  
   `--agent-turn-cache` + 现有 `prefix_cache=32`。Luce 博客：工具定义反复发送时，热 prefill 可从 50s 降到 ~1s（48×）。OpenClaw 每轮都带 tools/system，这比把 200K 冷针再抠快更有用。  
   **未在本机跑过**，应先用真实 tool 多轮测命中，再谈上线。

2. **不要用 Lucebox 扛冷 200K**  
   长会话继续 WORK（`--cache-prompt` + MTP）。Lucebox 只接短轮 / 新会话。双后端比在 Lucebox 里硬堆 200K 更符合两边设计。

3. **保持 `fa_window=0`**  
   换 3× 长 decode，会丢 system/tools。OpenClaw 不能开。

### 可以 A/B，但不要当无损

4. **`--chunk 1024`**  
   官方并发笔记：相对 512 大约 **1–2%** TTFT，不是数量级。值得 28k/180k 各打一条，期望很小。

5. **PFlash（`--prefill-compression auto` + Qwen3-0.6B drafter）**  
   官方说是长 prefill 的正统解。代价：另下一份 0.6B、稀疏保留（默认 keep 5%）、NIAH 声称能中，**agent 工具/系统提示是否还在**没有 Qwen3.8 本机证据。有限窗口会被 PFlash 自动打到 `fa_window=0`（文档）。  
   若做：只测 OpenClaw 真实 system+tools+长日志，针和工具必须同时过。

6. **KVFlash**  
   长 decode 变平、显存恒定。针可能漏、输出非字节等同。OpenClaw 要精确文件路径/协议字段时风险高。最多当「检索型长文」旁路，不当 WORK 替代。

### 不建议当「继续优化 Lucebox 200K」

7. 打开 `--fa-window` 追 60K 90 t/s：工具会坏。  
8. `--paged-attention`：和 `--draft` 互斥，等于关掉 DFlash2。  
9. 200K 改回 q8 KV：已经 OOM。  
10. DDTree：短 greedy 本机没赢；长窗口 verify 更贵。  
11. 指望再向量化就把 180k 冷 prefill 打到 llama.cpp：PR #625 短 prefill 已经慢一截，这是引擎/量化路径差异。

---

## 6. 给普通人的结论

Lucebox 像请了个手飞快的实习生（DFlash2）帮正主猜下一句。上文很短时，一次猜十几字、正主一眼验收，所以能到 200+ t/s。

上文变成一部小说时：

1. 正主要先把整本书抄到桌上（prefill）——Lucebox 抄书比 llama.cpp 慢，180k 要两分多钟。  
2. 抄完之后每写一句都要翻整本书（注意力）——谁都快不了，WORK 也大约 50 t/s。  
3. 书超过约 8 千字，引擎 **故意** 让正主一次少验收几个字（16→8），免得翻书成本把加速吃光。日志已经证明本机触发了这条规则。

所以：短编码轮次 Lucebox 是真快；超长会话它既不是为这个场景调的，也没有打开作者后来为「长 prefill」做的 PFlash。继续优化若要做，优先 **工具前缀缓存** 和 **短/长分流**，而不是把 200K 冷读入硬拧到和 WORK 一样。

未验证：PFlash / agent-turn-cache / chunk=1024 在本机 4090 + Qwen3.8 + 工具 的实际数字。报告里的优化项除源码默认值和官方表格外，都还需要单独 A/B。
