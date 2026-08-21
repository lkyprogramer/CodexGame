# 00 · 总体设计

## 目标

QCB-4090 回答三个不同问题：

1. 某个 Qwen3.8-27B finetune 是否在同条件下提高 Coding 质量？
2. 某个 template/reasoning 策略是否提高完整 Agent 任务的成功/时间效率？
3. 某个量化、MTP 或上下文配置是否更适合 24GB 4090？

这三个问题对应不同实验，不能用一张混合榜单回答。

## 架构

```text
Task prompt + isolated workspace
              │
              ▼
OpenAI-compatible local endpoint
              │
     ┌────────┴──────────────┐
     │ Patch/Agent full tools │ Review read-only tools
     └────────┬──────────────┘
              ▼
workspace diff / review JSON
              │
              ▼
hidden verifier ── GPU/usage/tool trace
              │
              ▼
JSONL records → model report → paired comparison → leaderboard
```

## 非目标

- 不建立跨硬件的绝对 tok/s 排行；
- 不用 48 题宣称覆盖全部软件工程；
- 不自动运行任意 shell 命令；
- 不使用另一个 LLM 作为唯一裁判；
- 不把公开题库当作长期不可污染的秘密集。

## 可扩展点

题目目录有稳定 contract：`task.json`、`prompt.md`、`workspace/`、`hidden_tests/verify.py`、`reference/`。新增任务必须通过 authoring guide 中的基线失败、参考通过和泄漏检查。
