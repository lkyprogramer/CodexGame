# Kern-SM89-W4A16 · Qwen3.8-27B · 64K PoC

**版本：1.0.0｜基线日期：2026-09-08｜交付类型：AI 开发执行文档 + 已实现的 CPU 辅助工具 + Java 测试夹具。**

这不是已经完成 SM89 移植的推理引擎安装包。包内不包含模型权重、CUDA cubin、可运行的 Kern 27B SM89 binary，也没有伪造 GPU 成绩。开发 AI 按 `AGENT_START.md` 执行任务，产出这些缺失的工程成果，再用这里的协议验证。

## 你的环境与目标

RTX 4090 24GB、64GB RAM、600GB SSD；最新用户提供 **Driver/KMD 610.57.04，CUDA UMD 13.3**。UMD 不是 Toolkit，实际 `nvcc`、cuBLAS、容器镜像由只读预检确认。现有 NInfer `44a2c6c`、`rk4v4-e8`、MTP3、262K 是受保护的生产基线。

首阶段只做：**Qwen3.8-27B，W4A16 权重，BF16 activations，FP32 GDN state，BF16 KV，单用户，no-spec，真实 65,536-token 输入 + 2,048-token 输出**。服务窗口/池的计划起点是 73,728 tokens，不把 `--capacity 65536` 当作“64K 输入还能继续生成”。

优先验证同权重正确性、64K 容量、长期 append cache 与 Java 工具循环；再优化速度。DFlash2/MTP、低比特 KV、200K 和随机采样属于后续独立阶段。

## 最快开始

```bash
unzip kern-sm89-w4a16-64k-poc-v1.0.0.zip
cd kern-sm89-w4a16-64k-poc-v1.0.0
# 已有numpy时可直接自检；缺依赖则先按docs/17建立隔离工具环境。
bash scripts/self_check.sh
bash scripts/preflight.sh
```

这两步不停止现网、不加载 27B、不安装驱动。把 `AGENT_START.md` 交给运行在外部模型或其他机器上的开发 AI，开始实施。**不要让执行器依赖即将被暂停的本机 NInfer。**

开发完成、T22 生成本机资格计划之后：

```bash
mkdir -p logs
ALLOW_PRODUCTION_PAUSE=1 nohup bash scripts/run_qualification.sh \
  configs/qualification.local.json > logs/qualification.log 2>&1 &
tail -f logs/qualification.log
```

只有你允许评测窗口时才设置该变量。程序默认拒绝暂停生产；正常退出/超时会尝试恢复原来处于 active 的 NInfer 服务。SIGKILL、断电和宿主故障仍需要人工恢复，详见运维文档。

## 目录

| 入口 | 内容 |
|---|---|
| `AGENT_START.md` / `AGENTS.md` | 开发 AI 的执行与禁止事项 |
| `docs/00-master-plan.md` | 总方案与决策 |
| `docs/01`–`docs/18` | 环境、模型、ABI、状态、缓存、数值、性能、Agent 与验收 |
| `tasks/` + `configs/tasks.json` | 有依赖关系、输入输出和验收命令的开发任务 |
| `poc_tools/` | 可运行的审计、SSE、数值、Java 和结果判定工具 |
| `fixtures/` | 三个独立 Java 8 修复项目；无需 Maven 网络 |
| `validation/` | 本次在生成环境实际运行的检查结果，与未执行的 GPU 项目 |
| `references/` | 固定源码位置和证据台账 |

**裁决：** `POC_GO` 只表示 64K、no-spec PoC；不表示胜过 NInfer，不表示 200K 已通过，更不自动切换生产。没有完整证据是 `BLOCKED`；预算耗尽是 `INCOMPLETE`；正确性失败是 `NO_GO`。
