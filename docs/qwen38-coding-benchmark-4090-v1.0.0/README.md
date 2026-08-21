# QCB-4090：Qwen3.8-27B Coding 横评基准

QCB-4090 是一套面向 **RTX 4090 24GB、本地 OpenAI-compatible 推理端点、Qwen3.8-27B 及其 GGUF 变种**的可复现 Coding 横评工程。它不把 HumanEval 一类单文件生成分数当成软件工程能力，而是同时测量：实现、修复、跨文件工程、工具调用、检索压力、代码审查、任务耗时、Token 成本和显存行为。

## 你会得到什么

- 48 道冻结题目，包含公开工作区、隔离隐藏验证和参考实现；
- 12/32/48/27 四套固定 Suite；
- Normalized 与 Optimized 两条严格分榜赛道；
- OpenAI-compatible 执行器、Patch/Agent 完整工具、Code Review 只读工具、统一 diff 应用和 GPU 采样；
- Java/Python 自动验证、代码审查 Rubric、原始响应和工具轨迹留档；
- 分类平衡评分、成功任务效率、配对 Bootstrap、McNemar 精确检验、Holm 修正和报告模板；
- 适用于 Original、Sharp Template、Grug、Fable、Salience、Cold Fusion 等候选的测试矩阵。

## 题库构成

| 类别 | 数量 | 重点 |
|---|---:|---|
| `single_file` | 12 | 算法、解析、并发、数值、边界、安全 API |
| `bug_fix` | 10 | 真实缺陷定位、回归修复、异常和时间语义 |
| `repo_engineering` | 12 | 幂等、事务、兼容、批量、分页、缓存一致性 |
| `agent_tool` | 6 | 搜索、读取、公开测试、补丁、失败恢复 |
| `long_context` | 4 | 大目录检索、上下文预算、无关文件抑制 |
| `code_review` | 4 | 安全、并发、文件上传、Webhook 审查 |

## 两条赛道

### Normalized

固定 system prompt、tool schema、reasoning effort、sampling、上下文、MTP 状态和题目顺序，用于比较 **权重/后训练本身**。

### Optimized

允许每个模型使用其最佳 template、reasoning effort、MTP、量化和服务器参数，用于比较 **4090 上最终可部署组合**。

两条赛道不得合并排名。Template-only 变体应同时报告“同权重行为优化”，不能冒充新权重模型。

## 快速开始

```bash
python3 scripts/verify_release.py
python3 -m qcb.cli --help
cp config/normalized.example.toml config/local-original.toml
# 修改 endpoint、模型路径与 sha256
python3 -m qcb.cli run --config config/local-original.toml --suite smoke --seeds 42
```

完整流程见 [`QUICKSTART.md`](QUICKSTART.md) 和 [`docs/04-runbook.md`](docs/04-runbook.md)。 全部设计与操作文档见 [`docs/README.md`](docs/README.md)。

## 核心原则

1. **质量和效率分开。** 更快但成功率明显下降，不判为更优模型。
2. **按任务配对。** 只比较相同题目、相同 Seed、相同赛道的数据。
3. **六类等权。** 防止数量较多的简单题主导总分。
4. **完整留痕。** 模型、GGUF、template、prompt、服务器、硬件和原始轨迹必须可追溯。
5. **隐藏测试隔离。** 待测模型只能看到 `workspace/` 与 `prompt.md`。
6. **不声称精确 token 档。** 长仓库的目录体量只是检索压力；实际进入上下文的 token 由读取轨迹和端点 usage 决定。

## 环境要求

- Python 3.11+
- JDK 17+（推荐 JDK 21）
- Git
- 可选：NVIDIA 驱动与 `nvidia-smi`
- 一个 OpenAI-compatible `/v1/chat/completions` 本地端点

执行器只依赖 Python 标准库。题目本身不需要 Maven、Gradle、pip 网络下载或第三方测试框架。标准 Suite 要求 `tool_mode=true`；代码审查任务只获得读取/搜索工具，不能修改仓库。

## 结果目录

每次运行会生成 JSONL 主记录和逐任务 artifact：最终回复、补丁、工具轨迹、原始 API 响应、隐藏验证结果及可用时的 GPU 采样。已有结果默认拒绝追加；使用 `--resume` 只补缺失 task/seed，`--overwrite` 必须显式指定。请把整个结果目录和最终报告一起归档。

## 重要限制

这套基准不能证明模型对所有真实项目都更好。它主要用于同一台 4090 上的相对横评。题目公开后可能被训练数据污染，因此长期使用应结合 `docs/12-private-replay-extension.md` 中的私有回放集。


## 结果审计

正式报告前执行：

```bash
python3 scripts/audit_results.py --results <result.jsonl> --check-artifacts --json <audit.json>
```

审计不通过的结果不得进入模型排名。
