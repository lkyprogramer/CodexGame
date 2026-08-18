# 08-17 轮复盘

对象：`output/qwen38-27b-4090-20260817`  
那轮工程执行是认真的：18 个 lane、原始 request/response/GPU/日志齐全、生产服务有停/启/恢复。问题在 **配置假设** 和 **测试标准**，不是缺数据。

## 1. 配置问题

### 1.1 把 MTP n=4 写成灰度默认

最终结论推荐：

```text
spec-draft-n-max=4
spec-draft-p-min=0.75
ctx-size=65536
ctk/ctv=q8_0
enable_thinking=false
```

矩阵本身（32K、**KV q4**、temp=0）：

| lane | 2048 decode | acceptance |
|---|---:|---:|
| no-spec | 44.64 | n/a |
| n=1 p=.75 | 59.80 | 0.97 |
| n=2 p=.75 | 65.86 | 0.89 |
| n=3 p=.75 | 72.44 | 0.87 |
| n=4 p=.75 | 75.75 | 0.82 |
| n=2 p=0 | 85.40 | 0.65 |

选型逻辑是“n=4 比 n=2 p=.75 更快、比 n=2 p=0 更稳”。这是 Qwen3.6 生产配方的惯性（现网就是 MTP n=4 + p-min 0.75 + KV q4）。

和 3.8 架构冲突：单层 MTP head，社区记录 n=4 出 junk / crash。08-17 的质量表上 n=1…4 的 long/json/patch 分数几乎一样，**检测不到 junk**，所以错误地放行了 n=4。

### 1.2 矩阵用 q4 KV，推荐却写成 q8

`qwen38_mtp_n4_p075_ctx32/server.command.txt`：

```text
-ctk q4_0 -ctv q4_0
--spec-draft-type-k q4_0 --spec-draft-type-v q4_0
--spec-draft-n-max 4 --spec-draft-p-min 0.75
```

Agent / 长上下文 lane 才改成 q8。等于：速度表是 q4 测的，灰度推荐是 q8，两者没有同一套质量数字。

### 1.3 全局关掉 thinking

`03a` 复现：`--reasoning auto` + `max_tokens=16` + “Reply with OK only” → `content=''`，`reasoning_content` 被截断，`finish_reason=length`。

这是用例设计错误，不是“3.8 不能开思考”：

- 思考模型的短协议测试必须给够 `max_tokens`，或显式 `enable_thinking=false`。
- 正式结论却写成：OpenClaw **必须** 默认 `enable_thinking=false`。

等于为了让 16 token 的 OK 过关，砍掉这代模型的主能力。社区和官方都把 medium thinking 当工作默认。

同时启动参数自相矛盾：`--reasoning auto --reasoning-format deepseek` 又塞 `enable_thinking:false`。

### 1.4 采样是 greedy

`scripts/qwen38_eval.py` 每个请求：

```python
"temperature": 0,
"top_p": 1,
```

官方 thinking 档是 `1.0 / 0.95 / 20`。官方主榜也不是 greedy。08-17 的格式通过率、MTP acceptance、decode tok/s 都不能代表真实工作负载。

### 1.5 缺社区已钉死的 flag

相对 24GB 共识，08-17 缺：

- `--spec-default`
- 显式承认 n-max=2 为架构甜点（反而推 n=4）
- `--reasoning-budget` + 反重做 message
- 官方 thinking / instruct 两套采样
- `reasoning_effort` 必须走 `chat_template_kwargs` 的 sentinel

`-t 12` 也没设（影响通常不大）。

### 1.6 128K 当“能跑”而不是“能用”

`ctx131072_exact` 实际 prompt 124831，marker 召回通过，峰值 23552 MiB。结论还算克制（不建议默认 128K），但放行逻辑仍是 marker + 1024/2048 续写。没有长窗口交叉推理，也没有 q8 vs f16 对照。

## 2. 测试标准问题

### 2.1 用例测不到工作能力

| 套件 | 实际在测什么 | 缺什么 |
|---|---|---|
| smoke | OK、三字段 JSON | thinking 预算、schema、工具 |
| matrix long_* | 能否写出 1024/2048 字 runbook | 对错、可执行性 |
| patch_review | 提示词是否被围栏 | 有没有指出真实缺陷 |
| long_marker | 重复 ASCII 里找回针 | 约束推理 |
| agent trace | 3 轮合成 tool/json | 5+ 轮、可应用 patch、隐藏单测 |
| reasoning profile | 字段能不能拆开 | 任务是否解出来 |

`agent_safety` 的自动断言是 `contains: ["git status"]`。模型只要提到这三个词就算过，测不到拒绝策略。

### 2.2 质量分没有区分度

matrix 里 long 几乎全是 format 4 / quality 4，patch 全是 3/3 + `markdown_fence=True`，strict JSON 全是 5/5。n=1 和 n=4 无法区分。这种分数不能支持“n=4 更平衡”。

### 2.3 和 Qwen3.6 的对比不可比

3.6：旧 binary、生产 `temp=0`、reasoning off、MTP4、q4、128K、不同请求。  
3.8：新 binary、不同 ctx/KV、部分 thinking off。

`09` 自己也写了“不把不同 workload 的 tok/s 当严格 A/B”，但最终决策仍把两边的速度数字并列，削弱了“3.8 该不该换上”的判断。

### 2.4 有效吞吐没进决策

harness 其实算了 `effective_tokens_per_s`，决策只用 decode tok/s。thinking 模型必须拆思考 token 和正文 token。08-17 的 xhigh decode 67、low 84，但 xhigh completion 121 vs thinking-off 22——没有任务成功与否，无法判断 121 token 是在干活还是在空转。

### 2.5 `max_tokens=16` 污染了整轮叙事

这个用例失败被升格成部署硬门禁，并导出“默认关思考”。正确门禁是：

- 开思考时禁止用 16 作为短协议上限；
- 关思考作为 **请求级** 快路径；
- 另测 medium + budget，保证切断后仍有正文。

## 3. 仍应保留的资产

- 模型文件与 SHA256
- llama.cpp `4df29be` 构建（先检查是否已有 `--reasoning-budget`）
- 停/启生产的 wrapper 与恢复清单
- no-spec ≈ 44.6 tok/s
- 64/96/128K 的显存点
- prompt cache exact warm 约 20x 的方向
- “短 max_tokens + 开思考 ⇒ 空正文”的反例，应改写成回归用例，而不是产品默认

## 4. 本轮相对 08-17 的硬性变更

1. 默认 MTP `n=2`，n=4 只做负对照。
2. 工作档 KV / draft KV 一律 q8；q4 不再进速度矩阵。
3. 默认开 thinking，`medium` + `budget 16384` + 反重做。
4. 评测采样改官方 thinking 档；`temp=0` 降为附录。
5. 主指标改任务通过 / 可应用 patch / 无 junk，不再用 1–5 分和 decode tok/s 做灰度决策。
6. 长上下文改交叉事实题；128K marker 不再放行生产。
