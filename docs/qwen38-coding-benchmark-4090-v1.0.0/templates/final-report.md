# Qwen3.8-27B Coding 横评最终报告

> 基准版本：`QCB-4090 v__`  
> 报告日期：`YYYY-MM-DD`  
> Normalized 数据目录：`__`  
> Optimized 数据目录：`__`

## 1. 执行摘要

### 1.1 最终推荐

| 推荐类别 | 模型/组合 | 关键配置 | 证据 | 主要限制 |
|---|---|---|---|---|
| 最高质量 |  |  |  |  |
| 最佳 Coding Agent |  |  |  |  |
| 最佳成功任务/小时 |  |  |  |  |
| 最佳 64K+ 检索 |  |  |  |  |
| 最稳定 |  |  |  |  |
| 最佳 Template-only 改善 |  |  |  |  |

### 1.2 一句话决策

- 默认部署：
- 深度复杂任务备用：
- 长上下文备用：
- 不推荐组合及原因：
- 本报告不能推出：

## 2. 实验范围、冻结项与数据完整性

| 项目 | 值 |
|---|---|
| 基准版本 / MANIFEST SHA-256 |  |
| Suite / Seeds |  |
| 运行总数 / 缺失数 / 重复数 |  |
| 预声明质量门槛 | Hard -3pp；Worst -8pp；Invalid ≤8% 且相对 +3pp；CBI +2pp |
| 允许重跑规则 |  |
| 实际重跑与排除记录 |  |
| Reasoning usage 覆盖率 |  |
| GPU sampling 覆盖率 |  |
| Endpoint timings 覆盖率 |  |

## 3. 硬件、服务器与运行环境

| 项目 | 值 |
|---|---|
| GPU / VRAM / Power limit |  |
| Driver / CUDA runtime |  |
| CPU / RAM / OS |  |
| llama.cpp/server commit |  |
| 构建选项 |  |
| 完整启动命令 |  |
| Context / batch / ubatch |  |
| KV 类型 / Flash Attention |  |
| GPU offload |  |
| Warm-up 方法 |  |
| 运行顺序与 block |  |

## 4. 模型、GGUF、Template 与请求参数

| Config ID | 权重来源 | GGUF SHA-256 | Quant | Template+SHA | Reasoning | MTP | Context | Lane |
|---|---|---|---|---|---|:---:|---:|---|
|  |  |  |  |  |  |  |  |  |

任何只改变 Template 的配置必须明确标为 `template-only`；任何量化对照不得描述为新权重模型。

## 5. Normalized 主质量榜

| 排名 | 模型 | 合格 | Hard | Partial | CBI | Worst | Invalid | Infrastructure |
|---:|---|:---:|---:|---:|---:|---:|---:|---:|
|  |  |  |  |  |  |  |  |  |

## 6. 六类能力矩阵

| 模型 | Single | Bug Fix | Repo | Agent | Long Context | Review | Worst |
|---|---:|---:|---:|---:|---:|---:|---:|
|  |  |  |  |  |  |  |  |

说明每个显著提升和回退是否在多个 Seed、私有回放或补丁人工审查中复现。

## 7. Agent、工具与恢复行为

| 模型 | Tool calls | Valid calls | Operation success | Public-test recovery | Budget exhausted | Wrong/unsafe edits |
|---|---:|---:|---:|---:|---:|---:|
|  |  |  |  |  |  |  |

### 7.1 代表性成功轨迹

- Task：
- 搜索路径：
- 首次失败：
- 恢复动作：
- 最终补丁：
- 为什么该轨迹具有代表性：

### 7.2 代表性失败轨迹

同上，并区分：能力不足、上下文迷失、工具格式、测试误判、过度思考、欠思考、服务器故障。

## 8. RTX 4090 效率与显存

只比较通过质量门槛的模型。

| 模型 | 成功耗时 P50/P90 | 成功 Token P50 | Reasoning P50 | 成功任务/h | Peak VRAM | Prompt tok/s | Decode tok/s | MTP acceptance |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|  |  |  |  |  |  |  |  |  |

失败任务的短耗时不得计作效率优势。TTFT 若未使用 streaming 或服务遥测采集，填 `N/A`。

## 9. Pairwise 配对统计

| A | B | Hard B-A | 95% CI | Partial B-A | McNemar p | Holm p | Practical win |
|---|---|---:|---:|---:|---:|---:|:---:|
|  |  |  |  |  |  |  |  |

“Practical win”必须同时通过：Hard 非劣、Worst 保护、Invalid 门槛、CBI 实际意义阈值。

## 10. 消融实验

### 10.1 Original official vs Original Sharp

### 10.2 Finetune common template vs native template

### 10.3 Regular vs MTP

### 10.4 Q4 vs Q5 / coding-aware Imatrix

### 10.5 32K vs 64K+ 检索压力

### 10.6 medium vs xhigh

每个消融必须保持其他变量不变，并明确归因边界。

## 11. Optimized 部署榜

| 排名 | 可部署组合 | Hard | CBI | Worst | 成功任务/h | Peak VRAM | 最大稳定 Context | 备注 |
|---:|---|---:|---:|---:|---:|---:|---:|---|
|  |  |  |  |  |  |  |  |  |

不得把 Optimized 结果反推为“权重本体更强”。

## 12. 失败根因与补丁质量审查

| 根因 | 数量 | 涉及模型 | 代表任务 | 是否系统性 | 处置建议 |
|---|---:|---|---|:---:|---|
|  |  |  |  |  |  |

人工抽查至少覆盖：成功但补丁过大、部分通过、不同 Seed 分裂、安全题、长上下文题、Tool budget exhausted。

## 13. 私有 Java 项目回放

| 模型 | 任务数 | Hard | Build/Test | 错误编辑 | 成功耗时 | 与公开集方向一致 |
|---|---:|---:|---:|---:|---:|:---:|
|  |  |  |  |  |  |  |

说明私有任务的抽取方法、去泄漏方法、时间范围和保密边界。

## 14. 最终部署建议

```text
model:
quant:
template:
server commit:
startup flags:
context:
KV:
reasoning effort:
MTP:
request parameters:
fallback policy:
```

### 路由建议

| 任务类型 | 默认模型 | 升级条件 | 备用模型 |
|---|---|---|---|
| 普通补丁 |  |  |  |
| Repo 多文件 |  |  |  |
| 深度 Debug |  |  |  |
| 64K+ 检索 |  |  |  |
| 安全审查 |  |  |  |

## 15. 限制与后续验证

- 公开题库污染风险：
- 样本规模与小类别波动：
- Java/Spring 真实项目代表性：
- OpenAI-compatible usage 语义差异：
- Tool schema 与 Claude Code/Codex 差异：
- 需要补充的测试：

## 附录 A：逐题逐 Seed

必须附：Task、Seed、Hard、Partial、Outcome、Wall time、Token、Tool calls、Artifact 路径。

## 附录 B：完整配置、哈希和环境

附全部 TOML、环境 JSON、模型/Template SHA-256、server 日志和 Latin-square block。

## 附录 C：重跑与异常审计

逐条列出 infrastructure error、OOM、人工中止、允许重跑和数据排除。
