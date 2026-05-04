# Qwen3.5 thinking=true 下真实 coding prompt 容易 500 的专项排查

## 1. 问题定义

当前线上服务配置为：

```bash
/opt/llama.cpp/build/bin/llama-server \
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
  --host 0.0.0.0 \
  --port 18343
```

在该配置下：

- 简单请求常常成功
- 真实 coding / review / patch 类 prompt 经常返回：

```text
Failed to parse input at pos XXXX:
```

并映射成：

```json
{"error":{"code":500,"message":"Failed to parse input at pos ...","type":"server_error"}}
```

---

## 2. 已确认的事实

### 2.1 不是显存问题

GPU 侧压测显示：

- 显存长期稳定在约 `22.5GB`
- 没有出现 OOM 型崩溃
- 服务在思考模式下仍能持续生成

因此，这不是“thinking=true 导致显存不够”的问题。

### 2.2 不是模型根本不可用

`thinking=true` 下以下请求已成功返回：

- 简单数学问题
- 简短 Python coding
- 中等上下文的一部分请求

而且返回中包含：

- `message.content`
- `message.reasoning_content`

所以：

- thinking mode 本身可用
- 模型本身也能推理

### 2.3 失败发生在“生成之后”

服务日志已经证明，失败请求通常不是一开始就挂，而是：

1. prompt 已完成处理
2. 模型已经完成大量生成
3. 最后在结果整理阶段抛出 `Failed to parse input at pos ...`

典型日志片段：

```text
prompt eval time = 72.09 ms / 37 tokens
eval time = 23885.94 ms / 1024 tokens
total time = 23958.03 ms / 1061 tokens
slot release ...
srv operator(): got exception: {"error":{"code":500,"message":"Failed to parse input at pos 4209: ","type":"server_error"}}
```

结论：

- 不是模型没生成
- 而是 **server 对生成结果的解析失败**

---

## 3. 源码定位

在 `llama.cpp` 当前源码中，异常直接来自：

[`common/chat.cpp`](/tmp/llama-latest.UDaXqt/common/chat.cpp)

对应逻辑：

```cpp
if (result.fail()) {
    throw std::runtime_error(std::string("Failed to parse input at pos ")
        + std::to_string(result.end) + ": " + input.substr(result.end));
}
```

也就是说：

- `llama-server` 在把模型输出解析成 OpenAI chat 消息结构时
- PEG parser 失败
- 于是返回 `500`

---

## 4. 模板层面的关键线索

Qwen3 模板里不仅有 thinking，还内建了 tool call 结构。

模板片段来自：

[`models/templates/Qwen-Qwen3-0.6B.jinja`](/tmp/llama-latest.UDaXqt/models/templates/Qwen-Qwen3-0.6B.jinja)

可以看到它包含：

- `<think> ... </think>`
- `<tool_call> ... </tool_call>`

这说明 parser 处理的并不仅仅是“普通文本 + 思考内容”，还会尝试识别：

- reasoning
- content
- tool call 结构

一旦模型输出在这些结构之间“半符合、半不符合”，就容易进入 parser 失败路径。

---

## 5. 对照实验

为了把问题收敛到根因，我用同一条失败 prompt 做了三组对照：

Prompt：

```text
Given a Java service that sometimes throws NullPointerException after loading an optional nested config, explain the likely root cause and give the smallest safe fix.
```

测试环境：

- 模型：`Qwen3.5-27B-UD-Q4_K_XL.gguf`
- `thinking=true`
- `ctx-size=65536`
- `np=1`
- 相同采样参数

### 5.1 变体 A：默认行为（`--reasoning-format auto`）

结果：

- `HTTP 500`
- 错误：

```text
Failed to parse input at pos 4209:
```

说明：

- 默认自动 reasoning 提取路径会失败

### 5.2 变体 B：`--reasoning-format none`

结果：

- `HTTP 200`
- 同一条 prompt 成功返回
- thinking 内容被保留在 `message.content` 中
- 不再单独提取到 `message.reasoning_content`

这是一条非常关键的证据：

> **thinking 生成本身没有问题，问题出在 reasoning 的“提取/结构化解析”路径。**

### 5.3 变体 C：`--reasoning-format deepseek-legacy`

结果：

- `HTTP 500`
- 错误：

```text
Failed to parse input at pos 4081:
```

说明：

- 不是只有 `auto` 会失败
- 只要进入“把 thinking 单独提取出来”的这类路径，就容易失败

---

## 6. 更接近真实 coding 场景的验证

我又拿之前压测里失败的 `context_small` 长代码 prompt 做了验证：

- 原始配置：`thinking=true`，默认 reasoning 提取
  - 结果：`500`
- 改成：`thinking=true + --reasoning-format none`
  - 结果：`200`

这说明：

- `--reasoning-format none` 不是只对短 prompt 有效
- 对真实 coding 上下文也有效

---

## 7. 现在最合理的根因判断

基于源码、日志和对照实验，目前最合理的根因是：

### 根因判断

`llama-server` 在 `thinking=true` 下，会尝试把 Qwen3.5 的输出拆成：

- `reasoning_content`
- `content`
- 可能的 tool call 结构

但真实 coding prompt 更容易让模型输出：

- 更长的 thinking
- 更复杂的结构化文本
- 更像 JSON / XML / function call 的片段

这会让 PEG parser 在后处理阶段失败。

更精确地说：

> **问题主要在 “reasoning extraction / structured parsing” 路径，而不是在 thinking generation 路径。**

---

## 8. 与社区反馈是否一致

是，一致。

我查到的公开反馈方向包括：

- `llama.cpp` 曾有多条 Qwen3 / enable_thinking / jinja / tool calling 相关 bug
- 社区已有 `Qwen3.5-27B-GGUF` 在 coding 任务中出现 overthinking / prompt failure 的反馈
- `llama.cpp` 最近也有关于 thinking / tool call / faulty parsing 的 issue

也就是说：

- 你这里不是孤例
- 但我这次排查把它进一步缩小到了一个更具体的工作结论：

> **当前最可疑的不是模板启用 thinking 本身，而是 server 对 thinking 输出的结构化提取。**

---

## 9. 当前最稳的 workaround

如果目标是：

- 保留 thinking
- 同时尽量提升真实 coding prompt 的成功率

当前最稳的 workaround 是：

```bash
--chat-template-kwargs '{"enable_thinking": true}' \
--reasoning-format none
```

它的效果是：

- 仍然允许模型思考
- 但不再强行把思考拆成 `message.reasoning_content`
- 而是把整段输出保留在 `message.content`

代价是：

- 客户端不能再直接依赖 `reasoning_content`
- 需要自己从 `content` 里处理或展示 thought 文本

---

## 10. 结论

截至当前排查，可以给出一个高置信度判断：

1. `thinking=true` 本身不是罪魁祸首
2. `Qwen3.5-27B-UD-Q4_K_XL` 本身也不是不能做 coding
3. 当前高概率问题在于：
   - `llama-server`
   - `thinking` 输出
   - `reasoning/tool-call` 结构化解析
4. 已验证可行的绕法是：
   - 保留 `thinking=true`
   - 改用 `--reasoning-format none`

换句话说：

> **如果你的目标是“thinking 仍然开着，但真实 coding prompt 不再频繁 500”，目前最靠谱的方向不是关掉 thinking，而是停止让 server 去结构化提取 reasoning。**

