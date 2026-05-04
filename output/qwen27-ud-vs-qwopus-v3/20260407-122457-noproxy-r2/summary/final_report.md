# Qwopus3.5-27B-v3-Q4_K_M vs Qwen3.5-27B-UD-Q4_K_XL

## 直接结论

本轮**没有产出可接受的完整对比结论**。

原因不是下载失败，也不是 runner 故障，而是你指定的评测 profile：

- `-c 65536`
- `--temp 0.6`
- `--top-p 0.95`
- `--top-k 20`
- `--chat-template-kwargs '{"enable_thinking": true}'`
- 不带 `--reasoning-format none`

在当前 4090 上的 `llama.cpp` 服务链路里，`Qwen3.5-27B-UD-Q4_K_XL` 作为 baseline **本身不兼容**：

- 最小 `READY` 请求返回 `HTTP 502`
- 64K coding 基线 22 题全部是 transport failure
- 错误形态是：`Remote end closed connection without response`

同一 profile 下，`Qwopus3.5-27B-v3-Q4_K_M` 的最小 `READY` 请求是 `HTTP 200`，说明候选模型至少能在该 profile 下正常返回。

因此，本轮能下的唯一严格结论是：

- **不能在你指定的 profile 下，对这两个模型做公平的 executor 对比**

## 已完成事项

### 模型下载

- 文件：
  `/data/models/qwen/Qwopus3.5-27B-v3-Q4_K_M.gguf`
- 大小：
  `16547395456`
- sha256：
  `2409fb2acfde19960c10ac05e9cad34d1e56421c256a0cc5b69eb54f0c97e5c0`

参考：
- [download_meta.json](/Users/luo/Documents/github/CodexGame/output/qwen27-ud-vs-qwopus-v3/20260407-122457-noproxy-r2/summary/download_meta.json)
- [remote_download_meta.json](/Users/luo/Documents/github/CodexGame/output/qwen27-ud-vs-qwopus-v3/20260407-122457-noproxy-r2/transfer/remote_download_meta.json)

### 基线失效证据

- `Qwen3.5-27B-UD-Q4_K_XL` 在请求 profile 下，最小 `READY` 请求返回：
  - `HTTP 502`
  - 或 `RemoteDisconnected`
- 64K coding 基线结果：
  - `22 / 22` 均非成功响应

参考：
- [results.csv](/Users/luo/Documents/github/CodexGame/output/qwen27-ud-vs-qwopus-v3/20260407-122457-noproxy-r2/64k/27b_ud_q4_xl/results.csv)
- [bench.log](/Users/luo/Documents/github/CodexGame/output/qwen27-ud-vs-qwopus-v3/20260407-122457-noproxy-r2/64k/27b_ud_q4_xl/bench.log)

### 候选最小健康检查

- `Qwopus3.5-27B-v3-Q4_K_M` 在同一 profile 下：
  - 最小 `READY` 请求返回 `HTTP 200`

这说明问题不是“整条服务链坏了”，而是 baseline 与该 profile 的兼容性问题。

## 为什么这轮不能继续拿结果硬比

按原判定规则，优先级是：

1. agentic 稳定性
2. 64K coding 质量
3. 262K extreme
4. 速度

但现在 baseline 在第一轮 64K coding 就已经**没有可用响应**，所以：

- 没法比较质量
- 没法比较速度
- 也没有继续跑 262K / agentic 的意义

继续往下跑，只会得到一份“baseline 全挂、candidate 部分可用”的伪结论，这不是可接受的模型对比报告。

## 最合理的下一步

如果你还要继续做这组模型对比，建议只选下面两个修正方向之一：

1. 保持其它参数不变，只给两边都补上 `--reasoning-format none`
   - 这是最小修正
   - 目标是先让 `Qwen3.5-27B-UD-Q4_K_XL` 恢复稳定可答

2. 直接切回旧的稳定 executor 口径
   - `thinking=false`
   - `--reasoning-format none`
   - 然后重跑 64K / 262K / agentic

如果目标是“公平比较模型能力”，我更推荐第 2 条。  
如果目标是“验证 Qwopus 在 thinking=true profile 下值不值得用”，我更推荐第 1 条。
