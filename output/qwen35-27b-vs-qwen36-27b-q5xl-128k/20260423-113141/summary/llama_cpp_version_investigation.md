# llama.cpp 版本影响排查

## 结论

版本会影响 Qwen3.6 的服务端输出解析和长上下文行为，但本次 128K 正式评测不能简单判定为“旧 llama.cpp 导致 Qwen3.6 变差”。当前证据更接近：

1. 正式评测用的 `/opt/llama.cpp/build/bin/llama-server` 是 2026-03-07 的 `c5a7788` 构建，并带有本地 chat/parser 相关改动。
2. Gemma4 评测脚本用的 `/home/hhtele/llama.cpp-gemma4-build/build/bin/llama-server` 是 2026-04-04 的 `9c69907` 构建。
3. 用 April 构建加载 Qwen3.6-27B Q5 128K 可以启动，但 no-thinking smoke 返回的 `content` 前缀含 `<think>

</think>

`，会污染现有 no-thinking benchmark 口径。
4. 正式 128K 评测里的 no-thinking smoke 对 Qwen3.6 是干净 `READY`，说明当前 `/opt` 构建至少在 no-thinking content 清理上更符合本轮口径。

因此不建议直接把 `/home/hhtele/llama.cpp-gemma4-build` 或未验证最新版替换进线上/评测脚本。建议另建独立 latest build 目录，先跑 parser/smoke/小样本 A/B，再决定是否进入完整评测。

## 4090 本机版本

| 路径 | 版本 | 提交时间 | 备注 |
|---|---|---|---|
| `/opt/llama.cpp/build/bin/llama-server` | `version: 1 (c5a7788)` | `2026-03-07T15:41:10+08:00` | 当前线上和本轮 Qwen3.6 评测使用；源码有 chat/parser 本地改动 |
| `/home/hhtele/llama.cpp-gemma4-build/build/bin/llama-server` | `version: 50 (9c69907)` | `2026-04-04T22:11:19+08:00` | Gemma4 评测脚本默认使用 |
| 官方 release | `b8893` | `2026-04-23T02:36:03Z` | 本排查时官方最新 release |

## April 构建 Qwen3.6 128K smoke

命令核心参数：

```bash
/home/hhtele/llama.cpp-gemma4-build/build/bin/llama-server   -m /data/models/qwen/Qwen3.6-27B-UD-Q5_K_XL.gguf   --alias bench/qwen36-newllama-smoke   -ngl 99 -c 131072 -np 1 -fa on -ctk q4_0 -ctv q4_0   --temp 0.2 --top-p 0.90 --top-k 20 --min-p 0.0   --reasoning-format none   --chat-template-kwargs '{"enable_thinking": false}'   --host 127.0.0.1 --port 18344
```

结果：

| 检查 | 结果 |
|---|---|
| `/v1/models` | 200，模型 ready |
| VRAM | 约 `21844 MiB / 24564 MiB` |
| `Reply READY only.` | `content = "<think>

</think>

READY"` |
| 小 coding smoke | 返回正确方向，但同样带 `<think>

</think>

` 前缀 |
| 恢复 | `qwen35-35b-a3b-uncensored` 已恢复 active，`/v1/models` 回到默认别名 |

## 影响判断

- 对本次人工评分中的“内容质量”而言，版本可能影响模型回答格式和 parser 结果，但 April 构建并没有证明 Qwen3.6 会更好；它首先暴露了 no-thinking 输出污染。
- 对长上下文/多轮 agent 而言，Qwen3.5/Qwen3.6 这类 hybrid/recurrent 架构在 llama.cpp 上仍有活跃问题：prompt cache、thinking、assistant prefill、grammar 约束都在近期 issue 中出现。
- 如果后续要公平判断 Qwen3.6，应该将“llama.cpp 版本”作为独立变量：同模型、同 prompt、同 quant，分别跑 `/opt`、April、latest 三套，不要把二进制升级和模型替换混在一轮结论里。

## 建议下一步

1. 在 4090 上新建 `/home/hhtele/llama.cpp-qwen36-latest-build`，从官方 `b8893` 或 master 编译 CUDA，不覆盖 `/opt/llama.cpp`。
2. 先跑 4 个 gate：
   - no-thinking smoke 不得有 `<think>` 注入到 `content`；
   - thinking smoke 的 `reasoning_content/content` 分离必须可解释；
   - 128K Qwen3.6 Q5 启动、短生成、显存记录；
   - 复跑 5 个此前 Qwen3.6 出错或落后的任务，人工对比是否实质改善。
3. 只有上述 gate 通过，再跑完整 128K coding+agentic benchmark。
4. 线上服务继续使用当前 `/opt` 构建，直到 latest build 通过 gate。
