# 现网 18343：Pi 多轮 tools 的 prefix 命中

时间：2026-09-08 11:44–11:45。生产 NInfer，未停 unit。thinking=medium。

原始：`output/qwen38-4090-compare/results/prod-prefix/`

## 结论

Pi 的 Java 三题（24 次 HTTP，26/13/8 次 tool）足以证明现网 prefix 在 **Agent 追加历史** 下是有效的：

- `prefix_cache_hit_tokens` **+154961**
- 计算 prefill（`llamacpp:prompt_tokens_total`）**+26845**
- 命中率 **154961 / (154961+26845) ≈ 85%**
- `continuation_stable_prefix_restores` **+20**（24 个请求里，后续 turn 几乎都在恢复检查点）
- Java **3/3**，墙钟 25 / 13 / 19 s

`continuation_lookup_hits` 仍是 0：L1/L2 continuation **别名查找** 和 paged-KV prefix 复用不是同一条路。现网有效的是 **rolling-tool / stable prefix restore**，不是 L3 disk。

## HTTP 对照（短 prompt，故意改写）

| 模式 | prompt | cached | 含义 |
|---|---:|---:|---|
| A-append | 173 | **86** (50%) | 在末尾追加 assistant+user，前缀命中 |
| 改写**第一条** user（reminder 拼进根消息） | 190 | **无** | 根 user 一变，整段前缀作废 |
| 只改**最新** user | 182 | 无（本探针） | 短会话 + thinking 正文不稳定时，usage 也可能不报 cache |

OpenClaw 若每轮改写最早的 user/system，会落到第二行，Pi 默认不会这么干。Pi 默认是第三行之前的 **追加**，和 Java 三题一致。

## 还不能用 Pi 代替的

OpenClaw 把 **session memory / reminder 写进历史中间或根 user** 的那种改写。要证那个，需要一次真实 OpenClaw 会话或按它的消息形状重放；不是再跑一遍 Java 三题。
