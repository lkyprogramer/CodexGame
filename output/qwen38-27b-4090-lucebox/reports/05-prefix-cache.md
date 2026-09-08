# 工具前缀缓存 / agent-turn-cache 实测（4090 Lucebox 200K）

时间：2026-09-04 03:34–03:45 EDT  
`PREFIX_AB_OK`。WORK 已 restore：`openclaw/Qwen3.8-27B-WORK`，22958/1259 MiB。

配方：IQ4 + DFlash2 Q8，`--max-ctx 200000`，KV q4，`DFLASH_SAMPLED_VERIFY=1`。三档只改缓存开关。

| 档 | 开关 | 空载 |
|---|---|---|
| **P0** | `--prefix-cache-slots 0` | 19342 MiB |
| **P1** | `--prefix-cache-slots 32`（官方默认） | 同左 |
| **P2** | 32 + `--agent-turn-cache` | 同左 |

---

## 结论（先看这个）

1. **大工具表 + 短下一轮：前缀缓存是真的，而且很猛。**  
   官方 `benchmark_tool_prefix_cache.py`（24 个工具，首包约 **15k** token）：P1/P2 冷 prefill **9.2s → 热 0.15s，约 59×**。P0 几乎没加速（1.08×）。改一个工具描述会 miss，身份合同正确。
2. **OpenClaw 那种「每轮都带 tools、对话越来越长」：本轮没吃到加速。**  
   4 个小工具（tools 头约 **482** token）时，日志每次都 `snap_pos=482`，但 **`restore=false` `prefix_len=0`**。28k/92k 的下一短轮仍然全量 prefill（**16.5s / 63s**），和关缓存一样。
3. **`--agent-turn-cache` 没有额外赢面。**  
   官方短轮 P2≈P1（58.9× vs 59.5×）。真实 tool_call 后回灌：日志 `[agent-turn-cache] no compatible prefix checkpoint; skipped`，`agent_turn_cache_hit` 全 false。
4. **长上下文 128k 追加失败**（HTTP 400）：在已有 ~92k 历史上再 `pad(128000)` 超过 `max_ctx - 4096`。64k 档实际 prompt **约 92k**，不是满 128k。

所以：博客里的「热 prefill 48×」对应的是 **胖工具前缀 + 瘦新句子**，不是 **已经 28k/90k 的会话再问一句**。后者正是 OpenClaw 长会话。

---

## 1. 官方基准（胖工具、短轮、可复现）

24 tools × 8 params，首包 ~15050 token，`tool_choice=none`，只回 `OK`。

| 档 | 冷 prefill | 热中位 | 加速 | passed |
|---|---:|---:|---:|---|
| P0 无缓存 | 8872 ms | 8246 ms | **1.08×** | false |
| P1 32 slot | 9162 ms | **154 ms** | **59.5×** | **true** |
| P2 +agent | 9186 ms | **156 ms** | **58.9×** | **true** |

P1 日志（热轮）：`restore=true slot=0 prefix_len=14848`，effective≈15065，只补约 200 token。改工具后 `restore=false`、prefill 回到 8.6s。

P0 全程 `snap_slot=-1`，证明开关有效。

---

## 2. 模拟 OpenClaw（小工具 + 真 tool_call + 涨历史）

固定 system（CodexGame / tickMs=200）+ 4 个工具（read_file / run_python / glob / grep）。  
A1 让模型调工具；A2 回灌 `tickMs=200`；然后把 SESSION_LOG 垫到 28k、再垫到累计 ~92k，每档后面跟一条短 JSON 追问。

| 步 | P0 wall / prefill_ms | P1 | P2 | cache_hit |
|---|---|---|---|---|
| A0 pin ~500 tok | 0.33s / 272 | 0.35 / 295 | 0.33 / 280 | 全 false |
| A1 tool_call | 0.68s（2 calls） | 0.53（1 call） | 0.92（2 calls） | 全 false |
| A2 tool result | 0.41 / 342 | 0.44 / 331 | 0.47 / 357 | 全 false |
| A3 follow-up | 0.41 | 0.41 | 0.44 | 全 false |
| **G28 ~28.5k** | **16.3s / 16208** | **16.5 / 16392** | **16.6 / 16531** | 全 false |
| **W28 短追问** | **16.4s / 16271** | **16.6 / 16404** | **16.8 / 16624** | 全 false |
| **G64 ~92.4k** | **63.0s / 62889** | **63.7 / 63498** | **66.3 / 66171** | 全 false |
| **W64 短追问** | **63.8s / 63542** | **63.3 / 63021** | **66.5 / 66223** | 全 false |
| G128/W128 | HTTP 400 | 400 | 400 | — |

P1/P2 长轮日志：`snap_pos=482`（只钉工具头），`restore=false prefix_len=0`。  
W28 并没有 restore G28 的 28k。

---

## 3. 为什么官方 59×、真实长会话 1.0×

**已观察**

- 官方热轮 restore 的是 **~15k 工具头**，新 user 只有一两百 token。
- 带 `tools=` 的请求，快照停在工具头（482 或 15027），**不是** 当前 28k 对话末尾。
- 小工具头 482 < 默认 `--chunk 512`。文档写物理快照会落到 prefill chunk 边界；本机表现为 482 **只写不读**。
- `--agent-turn-cache` 要「先 restore 到兼容 checkpoint 再把 tool_call 续上」。prefix 都没 restore，它只能 skip。

**推断（与文档一致，未再改 chunk 复测）**

- OpenClaw 每轮都带 tools → 引擎优先钉工具头，**不会**把 28k 历史做成可 restore 的边界。下一句仍要 prefill「工具之后的全部历史」。
- 即便 482 能 restore，28k 追问也只能少 482 token，墙钟几乎不变。
- 59× 要同时满足：工具前缀 **远大于 chunk（512）**，且 **新后缀很短**。长日志/长会话不满足第二条。

---

## 4. 对现网的含义

| 场景 | 前缀缓存有没有用 |
|---|---|
| 每轮都塞很大的 tool schema，用户只说一句 | **有，本机 59×**（P1 已够，不必开 agent-turn-cache） |
| 工具很少（几百 token），会话涨到 28k/90k | **本轮测到没用** |
| tool_call 后回灌结果 | **本轮 agent-turn-cache 没接上** |
| 冷 180k 针 / 第一次读长日志 | 无关，本来就没有前缀 |

WORK 的 `--cache-prompt` 是另一套（llama.cpp slot prompt cache），**这次没有对 WORK 做同样 A/B**。

未改默认、未改 NGINX。未提交 git。

## 产物

远程：`/home/hhtele/lucebox-qwen38-4090/{logs/prefix-ab.out,logs/P{0,1,2}*.stderr.log,results/prefix-ab/}`  
本地：`output/qwen38-27b-4090-lucebox/reports/05-prefix-cache.md`

## 若还要挖

1. `--chunk 256` 或把 OpenClaw 工具表垫到 >512，看小工具能否 restore。  
2. 官方 24 工具 + 在后面挂 28k 历史，直接量「只钉工具头」时长会话还剩多少加速。  
3. 不带 `tools=` 的纯多轮，验证对话边界快照能否扛长历史（那已不是「工具前缀」）。
