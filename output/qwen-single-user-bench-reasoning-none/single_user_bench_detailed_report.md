# Qwen3.5-27B-UD-Q4_K_XL 单人压测详细报告（`reasoning-format none` 版本）

## 1. 报告结论

本轮调整后的结论已经很明确：

- 当前线上配置改为 `thinking=true + --reasoning-format none` 之后，之前单人压测里失败的 12 个 case 全部转为 `200`。
- 第二轮单人压测总计 `18/18` 成功，成功率从第一轮的 `33.3%` 提升到 `100.0%`。
- 这基本确认，之前的 `500 Failed to parse input at pos ...` 主因不在模型推理，也不在显存，而在 `llama-server` 对 reasoning/thinking 输出的后处理解析。
- 这套 workaround 适合当前的单人 `Precise coding tasks` 场景。
- 代价也很明确：服务不再把思考内容拆到 `message.reasoning_content`，而是直接保留在 `message.content` 里。

一句话概括：

> 现在这套服务已经从“thinking 能跑，但真实 coding 容易 500”变成了“thinking 仍然存在，但要接受 reasoning 与 answer 合并在 content 中”的稳定版本。

---

## 2. 当前线上配置

### 2.1 模型与服务

- 目标机器：`100.107.189.100`
- 模型：`/data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf`
- 模型别名：`unsloth/Qwen3.5-27B-UD-Q4_K_XL`
- 监听地址：`0.0.0.0:18343`
- OpenAI 兼容入口：`http://100.107.189.100:18343/v1`
- 运行方式：`systemd`
- 服务名：`llama-qwen`

### 2.2 当前启动脚本

文件路径：`/opt/llama.cpp/run-qwen.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}
exec /opt/llama.cpp/build/bin/llama-server \
  -m /data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf \
  --alias unsloth/Qwen3.5-27B-UD-Q4_K_XL \
  -ngl 99 \
  -c 262144 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  --temp 0.6 \
  --top-p 0.95 \
  --top-k 20 \
  --min-p 0.0 \
  --chat-template-kwargs '{"enable_thinking": true}' \
  --reasoning-format none \
  --host 0.0.0.0 \
  --port 18343
```

### 2.3 当前 service 文件

文件路径：`/etc/systemd/system/llama-qwen.service`

```ini
[Unit]
Description=llama.cpp Qwen3.5 27B server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=hhtele
WorkingDirectory=/opt/llama.cpp
ExecStart=/opt/llama.cpp/run-qwen.sh
Restart=always
RestartSec=5
StandardOutput=append:/var/log/llama/qwen-server.log
StandardError=append:/var/log/llama/qwen-server.err.log
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

### 2.4 这次修正的关键差异

和上一轮相比，唯一关键变更是新增：

```bash
--reasoning-format none
```

它的实际作用不是“关闭 thinking”，而是：

- 保留模型的思考过程输出；
- 但不再让 `llama-server` 去尝试把 thinking 文本拆成独立的 `reasoning_content` 字段；
- 从而绕过当前 Qwen3.5 + `llama-server` 在 reasoning 结构提取阶段的 parser/后处理问题。

---

## 3. 预热与执行方式

### 3.1 预热

服务调整并重启后，先做了预热请求，确认：

- `llama-qwen` 正常启动；
- 模型已成功加载；
- thinking 仍然存在；
- `/v1/chat/completions` 可以正常返回。

预热后的行为符合预期：

- `message.reasoning_content` 不再单独返回；
- 思考过程直接保留在 `message.content` 中。

### 3.2 压测方式

压测仍然只针对单人顺序使用场景，不测并发。

- 压测发起端：GCP 跳板机
- 目标地址：`http://100.107.189.100:18343/v1`
- 模型名：`unsloth/Qwen3.5-27B-UD-Q4_K_XL`
- 测试集：与第一轮保持一致，共 `18` 个 case

覆盖了 5 类场景：

- `smoke`：基础可用性
- `boundary`：`max_tokens` 边界
- `context`：长上下文阶梯
- `cache`：prompt cache 命中与复用
- `soak`：连续单人使用

---

## 4. 总体结果

### 4.1 成功率对比

| 轮次 | 总用例 | 成功 | 失败 | 成功率 |
| --- | ---: | ---: | ---: | ---: |
| 第一轮（默认 reasoning 提取） | 18 | 6 | 12 | 33.3% |
| 第二轮（`--reasoning-format none`） | 18 | 18 | 0 | 100.0% |

### 4.2 被修复的失败 case

第一轮失败、第二轮成功的 case 一共 12 个：

- `smoke_java_bugfix`
- `boundary_max_tokens_8`
- `boundary_max_tokens_64`
- `context_small`
- `context_large`
- `cache_round_1`
- `cache_round_2`
- `cache_round_3`
- `soak_round_1`
- `soak_round_2`
- `soak_round_3`
- `soak_round_4`

这些 case 在第一轮的共同错误都是：

```text
Failed to parse input at pos XXXX:
```

第二轮统一变成 `HTTP 200`，这说明服务端失败点确实在 reasoning 输出的后处理，而不是推理主体。

---

## 5. 关键压测结果

## 5.1 基础 smoke

| 用例 | prompt_tokens | elapsed_ms | completion_tokens | 结果 |
| --- | ---: | ---: | ---: | --- |
| `smoke_math` | 17 | 3803.87 | 129 | 200 |
| `smoke_python_lru` | 27 | 18663.65 | 768 | 200 |
| `smoke_java_bugfix` | 37 | 25089.61 | 1024 | 200 |

结论：

- 之前短 prompt 的 Java bugfix 也会触发 `500`，现在已经稳定成功。
- 说明问题并不是“只有长上下文才会失败”，而是“更像真实 engineering/coding 的输出形态更容易触发解析失败”；workaround 正好避开了这个点。

## 5.2 `max_tokens` 边界

| 用例 | max_tokens | elapsed_ms | completion_tokens | content_length | 结果 |
| --- | ---: | ---: | ---: | ---: | --- |
| `boundary_max_tokens_8` | 8 | 908.04 | 8 | 25 | 200 |
| `boundary_max_tokens_64` | 64 | 2997.67 | 64 | 213 | 200 |
| `boundary_max_tokens_128` | 128 | 3704.58 | 128 | 397 | 200 |
| `boundary_max_tokens_256` | 256 | 3993.84 | 141 | 446 | 200 |

新的结论要和第一轮区分开来看：

- 从“接口稳定性”角度，`8` 和 `64` 现在也能成功返回，不再触发 `500`。
- 这证明之前低 `max_tokens` 的失败并不是 token 太小本身，而是 reasoning 解析路径导致的。
- 但从“coding 实用性”角度，`8` 和 `64` 仍然太小，不足以承载完整 reasoning + answer。

因此当前建议是：

- 如果只是连通性或健康检查，`max_tokens=8` 也能用。
- 如果是实际 `Precise coding tasks`，仍建议默认：
  - `512`
  - 或 `1024`

## 5.3 长上下文阶梯

| 用例 | prompt_tokens | elapsed_ms | prompt_ms | predicted_per_second | content_length | 结果 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `context_small` | 5230 | 21644.57 | 2106.48 | 42.11 | 3245 | 200 |
| `context_medium` | 19728 | 41156.64 | 8358.76 | 40.27 | 4508 | 200 |
| `context_large` | 64929 | 100341.62 | 32900.04 | 35.46 | 4977 | 200 |

结论：

- 这轮已经确认，`64.9K` token 级别的真实长上下文请求可以稳定返回。
- 首 token 相关的 prefill 成本会随 prompt 变长显著上升，这符合预期。
- 生成速度会随着上下文增大略有下降，但没有出现上一轮那种“跑完推理后在结果整理阶段报 500”的情况。

这比第一轮更重要的变化是：

> 之前大上下文失败，并不是 4090 顶不住，也不是 262K 起不来；而是服务后处理没有稳定接住生成结果。

## 5.4 prompt cache

| 用例 | prompt_tokens | elapsed_ms | prompt_ms | predicted_per_second | 结果 |
| --- | ---: | ---: | ---: | ---: | --- |
| `cache_round_1` | 19721 | 38207.62 | 8338.17 | 40.23 | 200 |
| `cache_round_2` | 19719 | 23665.99 | 304.36 | 40.22 | 200 |
| `cache_round_3` | 19720 | 27376.13 | 317.87 | 40.22 | 200 |

这组数据很关键：

- 第 1 轮到第 2 轮，`prompt_ms` 从 `8338 ms` 降到 `304 ms`
- 第 1 轮到第 3 轮，`prompt_ms` 仍保持在 `318 ms` 左右

这说明：

- prompt cache 已明确工作；
- 同前缀、多轮追问的单人 coding 使用模式，在当前配置上是有实打实收益的；
- 第二轮之后的主要耗时已不在 prompt 预处理，而在生成本身。

## 5.5 连续单人使用 soak

| 用例 | prompt_tokens | elapsed_ms | prompt_ms | predicted_per_second | 结果 |
| --- | ---: | ---: | ---: | ---: | --- |
| `soak_round_1` | 19715 | 27159.94 | 278.86 | 40.27 | 200 |
| `soak_round_2` | 19716 | 27746.21 | 320.69 | 40.25 | 200 |
| `soak_round_3` | 19716 | 25553.86 | 321.32 | 40.25 | 200 |
| `soak_round_4` | 19716 | 29093.90 | 317.34 | 40.27 | 200 |
| `soak_round_5` | 19716 | 51995.74 | 326.33 | 40.29 | 200 |

结论：

- 连续 5 轮单人使用全部成功；
- 没有出现上一轮那种中途 `500`；
- 第 5 轮总耗时明显更高，但仍然成功返回，说明它属于生成路径上的波动，而不是协议或 parser 层面的失败。

---

## 6. 资源使用情况

GPU 采样总数：`507`

### 6.1 显存

- 平均显存占用：`22680.03 MiB`
- 峰值显存占用：`22752 MiB`
- 最低显存占用：`22496 MiB`

这说明当前服务依然处于单卡 24GB 的高占用区间，但行为是稳定的。  
这也符合当前配置预期：

- `27B` 动态量化权重常驻 GPU
- `262K` 上下文
- `q4_0` KV cache
- 单 slot

### 6.2 GPU 利用率与功耗

- 平均 GPU 利用率：`59.89%`
- 峰值 GPU 利用率：`100%`
- 平均显存利用率：`52.91%`
- 峰值显存利用率：`97%`
- 平均功耗：`254.69 W`
- 峰值功耗：`436.62 W`

结论：

- 这依然是一套高负载配置；
- 但压测期间没有看到因为显存逼近上限而触发的请求级失败；
- 当前真实风险点已经从“显存容量边界”转移到了“客户端能否接受 merged reasoning output”。

---

## 7. 根因结论与 trade-off

## 7.1 现在基本可以确认的根因

结合上一轮失败现象和这一轮成功结果，可以把根因收敛到：

- `thinking=true` 本身不是问题；
- 模型 `Qwen3.5-27B-UD-Q4_K_XL.gguf` 本身也不是问题；
- 问题主要在 `llama-server` 对 Qwen3.5 thinking 输出的 reasoning 提取 / 结构化拆分路径。

也就是：

1. 模型已经完成推理；
2. 输出里包含 reasoning/thinking 文本；
3. server 试图把它拆成 `reasoning_content` 与最终答案；
4. 在真实 coding / review / 更复杂结构输出下，这一步容易 `Failed to parse input at pos ...`

而 `--reasoning-format none` 直接绕开了第 3 步，所以全套压测恢复稳定。

## 7.2 这套 workaround 的实际代价

收益：

- 接口稳定性大幅提升；
- 真实 coding prompt 不再频繁 `500`；
- 长上下文、cache、soak 都恢复可用。

代价：

- 客户端不能再依赖 `message.reasoning_content`；
- 需要从 `message.content` 中读取完整输出；
- 如果上层系统强依赖“思考内容和最终答案分字段返回”，这套配置就不是完美解。

因此当前更准确的表述应当是：

> 这是“单人 coding 稳定性优先”的配置，不是“结构化 reasoning 字段最完整”的配置。

---

## 8. 是否适合作为当前默认配置

对你现在的目标，即：

- 单人使用
- 主要做 `Precise coding tasks`
- 重视稳定性而不是多并发
- 能接受 reasoning 与 answer 合并在一起

我的结论是：

- 这套配置适合作为当前默认线上配置。

如果后面你明确需要：

- 独立的 `reasoning_content`
- 更干净的 OpenAI reasoning 字段兼容
- 更像 agent/tool structured output 的稳定支持

那就不该继续只停留在这个 workaround，而应该继续跟进 `llama.cpp` 上游修复，或者评估更适合 Qwen reasoning 的 serving 方案。

---

## 9. 工件位置

本轮工件目录：

- `/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench-reasoning-none`

关键文件：

- 原始 CSV：`/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench-reasoning-none/single_user_bench_results.csv`
- 原始 JSON：`/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench-reasoning-none/single_user_bench_results.json`
- 元数据：`/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench-reasoning-none/single_user_bench_meta.json`
- GPU 采样：`/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench-reasoning-none/gpu_samples.csv`
- VM 采样：`/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench-reasoning-none/vmstat.log`
- 本报告：`/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench-reasoning-none/single_user_bench_detailed_report.md`

第一轮失败版工件仍保留在：

- `/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench`

便于后续继续做前后对比。
