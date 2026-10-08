# NInfer-4090 CED / Late-State Prefill：AI 开发与阶段验收包

版本：1.0.0 · 日期：2026-09-11 · 语言：中文说明、英文代码与字段。

**交付性质：完整实施计划，不是已实现的推理引擎、训练好的 Predictor，也不是性能验证报告。** 本包只附带计划导航、资源估算与文档校验工具；它们不会连接服务器、停止现网或训练模型。

## 目标与主路线

在用户现有 `tensorninja/ninfer-4090@44a2c6c` 上增加一个**默认关闭、文本单并发、限定场景启用**的近似长输入预填充路径。固定 Qwen3.8-27B 原权重，不更换模型、不重建推理引擎、不新增常驻大模型。

主路线：**基线与隔离 → 真实状态注入 → StateOnly GDN → 离线 Teacher 数据和小型 Predictor → CED-16 → MTP/缓存语义 → Java/Pi 真实验证 → 有条件拓展 → 交付。**

本包沿用“CED-16/24/32”作为实验名，准确含义是 *Late-State Prefill (LSP)*，不是把原模型无损转换成原生 Causal Encoder-Decoder。预测器是否足够准确、是否真能省时，是必须被实验回答的问题，不是本计划的既定事实。

## 最先交给 AI 的文件

直接复制 [AI 总执行提示词](prompts/START.md)，并让执行 AI 能读取整个解压目录。它首先阅读本页、[约束](AGENTS.md)、[现网基线](docs/01-baseline-and-corrections.md)、[状态契约](docs/03-contracts.md)、[Phase 0](phases/P0.md)，然后按依赖执行。

```bash
python3 tools/validate_package.py
python3 tools/planctl.py list
python3 tools/planctl.py show P0
python3 tools/budget.py --split 48 --rank 256 --tokens 100000
python3 -m unittest discover -s tests -v
```

以上命令**现在即可运行**，仅验证文档包。执行进度写入LAB_ROOT下的独立state/报告，不修改本包初始NOT_RUN manifest；planctl导航不是GPU证据。本包后文出现的 `tools/ced_lab/`、`ced-research/`、`--late-state-*`、新增 CTest 名称，均是任务将要创建的交付契约；不是当前上游已有命令，未完成对应任务前不可执行。

## 阶段组织

| Phase | 交付中心 | 统一验收重点 |
|---|---|---|
| P0 | 冻结基线、保护现网、建立测试入口 | 当前 native 行为与真实资源可复现 |
| P1 | 分层执行与 Teacher 状态注入 | 正确注入全部必要状态；off 路径不变 |
| P2 | StateOnly GDN 与缓存写入原语 | 独立数值 oracle、卷积历史、长 T 与性能预算 |
| P3 | 有界 Teacher 数据、离线 Predictor 训练 | 无数据泄漏、可学习性、内存和数据上限 |
| P4 | CED-16 + 精确尾部执行；先关闭 MTP | 从原始请求到可用输出的近似路径闭环 |
| P5 | MTP 状态、缓存来源隔离、取消/恢复 | 不把近似状态标成原生；MTP 不缺状态 |
| P6 | Java/Pi、长上下文与配对 A/B | 真实任务质量与端到端收益 |
| P7 | CED-24 / CED-32 条件拓展 | 每个 split 单独阶段式验收，不强行推进 |
| P8 | 发布候选、回退与最终验收报告 | 默认关闭、最佳已通过档位、现网未被暗改 |

**每个 Phase 所有开发 Task 合并后，才在同一集成提交上统一运行该 Phase 的完整验收。** Task 内允许编译、契约测试和短单测；不要求每完成一个 Task 就重复长上下文、训练或全量 Agent 测试。只有统一 Gate 为 PASS 才能解锁下一必需阶段。

P7 是可选分支；P8 可以从 P6 的合格 CED-16 直接交付。P7A（40/24）通过后才允许 P7B（32/32）；更激进档失败不能使已通过的较小档失效。

## 文件导航

- [架构](docs/02-architecture.md) / [接口与状态契约](docs/03-contracts.md) / [数据和训练](docs/04-data-training.md)。
- [统一验证](docs/05-verification.md) / [用例和统计](docs/06-benchmarks.md) / [资源及运维](docs/07-operations.md)。
- [源码映射](docs/08-source-map.md) / [风险和决策](docs/09-decisions.md) / [AI 执行手册](docs/10-execution.md) / [命令契约](docs/11-command-contracts.md)。
- `phases/`：逐 Phase、逐 Task 的实施、依赖、修改文件、测试与停止条件。
- `manifests/plan.json`：与阶段文档同源生成的任务图；`manifests/gates.json`：统一 Gate 条件。
- `configs/`：固定基线、实验默认值与预算。`templates/`：任务、运行、阶段报告模板。

## 什么才算完成

“完成计划包”不等于“完成 CED”。引擎实施的合格结果可以是：

1. CED-16 实证有效，以默认关闭方式交付；较大 split 不继续。
2. CED-24 或 CED-32 也独立通过，交付实际最优档位。
3. 预测误差或收益不满足 Gate，明确 NO-GO，保留原生现网，并给出可复现证据。

禁止为了给出一个“成功”结论而降低质量门槛、隐藏重算/回退成本、把 SKIP 当 PASS，或把 Teacher 注入结果当作 Predictor 的准确率。
