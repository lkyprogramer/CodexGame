# 开发 AI：从这里开始

你负责在用户的 4090 机器上实现并验证 **Kern-SM89-W4A16 64K PoC**，不是写一份“建议以后实现”的报告。当前 ZIP 已提供需求、接口合同、测试工具和题目；SM89 模型 provider 与 GPU 测试适配器仍需你实现。

## 不可变事实

- 用户最新 Driver/KMD = **610.57.04**，CUDA UMD = **13.3**。不沿用旧 545/12.3 作为驱动限制；也不假定 nvcc=13.3。
- RTX 4090 24GB、64GB RAM、600GB SSD，单 GPU 同时只允许运行一个 27B 引擎。
- 当前生产：`openclaw-qwen38-ninfer.service`；模型调用名 `openclaw/Qwen3.8-27B-WORK`；兼容端点 `127.0.0.1:18343/v1`；引擎 `18030`；NGINX `28343`。
- 禁止改现网 unit、NGINX、模型文件、NInfer repo、镜像 tag 和 production launch 脚本。允许的暂停是显式维护窗口，不是切流。
- 测试 candidate 用 `18041`，oracle 用 `18042`，**串行占 GPU**。既有 NInfer 是产品比较基线；同 W4A16 oracle 才是数值基线。

## 第一轮必须执行

```bash
# 已有numpy时可直接自检；缺依赖则先按docs/17建立隔离工具环境。
bash scripts/self_check.sh
bash scripts/preflight.sh
python3 scripts/next_task.py
```

阅读：`docs/00-master-plan.md`、`docs/01-machine-and-operations.md`、`docs/02-source-and-environment-lock.md`、`docs/03-architecture.md`、`docs/04-memory-budget.md`。复制 `configs/local.example.json` 为 `configs/local.json`，只用本机检查结果填写模型、tokenizer 和源代码路径；不要猜目录。

然后逐个执行 `configs/tasks.json` 中依赖满足的任务。一个任务一个小提交；先失败测试，再最小实现，再验证。每个任务的原始命令、退出码、git diff、硬件状态、证据路径写入 `work/records/<task-id>/`。用任务文件里的测试命令验收，而不是根据模型输出“看起来正常”标记完成。

## 开发闭环

1. T00–T03：冻结生产与工程环境、选同一量化源、读 safetensors header 算内存、生成 reference oracle。
2. T04–T10：SM89 制品合同、Marlin packing/ABI、控制投影、GDN、Attention、完整 provider。
3. T11–T14：4K/64K 数值闭环、图执行、内存与可靠 telemetry。
4. T15–T21：协议拒绝语义、Pi、append cache、生命周期和性能/质量验证。
5. T22–T23：生成本机一小时资格计划与最终裁决，进行有边界的优化。
6. P1 任务只在 P0 通过后考虑；不得为完成 64K PoC 偷换成压缩上下文、FP16 state 或更小模型。

## 动手前的三个硬检查

**控制平面独立。** 开发 AI 不得通过被测 NInfer 提供自己的推理。否则暂停 NInfer 后会失去恢复能力。用外部 Codex/其他受控模型或异机执行器。

**网络可达。** 已有报告说明该机默认不能直连 GitHub。优先在联网机器制作固定 git bundle、wheelhouse、Cargo vendor 和镜像 tar；在目标机按哈希验收。不能把网络失败当成 CUDA 不支持。

**资源排他。** CPU 文档/代码/测试可并行，GPU 编译运行/基准采集串行。没有明确授权的维护窗口，不运行 `guard_gpu.py --allow-production-pause`，也不自行 `systemctl stop` 或 `docker kill`。

## 证据输出

完成任务后更新 `work/task-status.json`（任务 id → PASS/FAIL/BLOCKED + evidence），但不要修改签发时的 `configs/tasks.json` 初始状态。最后生成 `results/<run>/evidence.json`：引用同一 run 下的真实文件及 SHA；运行 `python3 -m poc_tools.cli report ...`。

`configs/evidence.template.json` 的 null 和 NOT_RUN 是诚实的初态，不能以任意数值补齐。开发时新增的命令、二进制、tensor layout 和库版本都要固化到 run 的 profile/lock。

## 最终回报用户

报告已实现的 commit、模型/packed 权重 digest、准确输入长度、no-spec 吞吐、cold/append TTFT、Java 3题、恢复/取消测试和生产恢复状态。失败时给出第一个失败合同、复现命令和最小日志，不得声称“已经达到极致”。
