# 执行入口与边界

本目录是数据优先的新研究计划，**不是执行授权**。先读 README、docs/00、docs/01–06、当前 Phase 和证据锁。

## 必须遵守

1. 以 CodexGame:4090-report 最新现场核对及其 AGENTS 为准；本包锁定的是 2026-11-20 研究快照，不自动追随 main 或更新运行环境。
2. 只复用一个 Lab 执行底座：`docs/strata_4090_128k_lab` 下 runner/http/frontier 等。规划的 `tools/frontier/exploration_control.py` 在已审计 tree 中尚不存在；若实施，补齐同一个既定入口，不另建 orchestration 服务。
3. Phase 串行，Phase 内互不冲突的 Task 可并行；同一 GPU 全局串行。每 Task 最小测试，每 Phase 独立 review 和统一回归。
4. 先写最小失败夹具，再实现最小适配/挂点，再回归。不得以宽泛异常、静默回退、缺值补零或修改 gold 让门变绿。
5. 旧 F02/F03/P24/NP3/VNNI/gather/DFlash2 等结论维持；新 tag 不自动重开。按 docs/02 和 docs/18 填真正机制差量。
6. 当前交付仅文档、契约与静态验证；新增 live/GPU 预算为零。进入实施阶段须按用户当轮授权记录允许的 Phase、机器、服务、端口、次数、时长和清理责任。
7. 旧规则的实验端口 18089 不等于当前空闲；生产/回滚树只读，不自动停止或恢复服务，不改 systemd/NGINX/驱动/CUDA 12.3/内核/GRUB/initramfs，不执行 updater。
8. 不开 `STRATA_STAGE_PIN`、`STRATA_ROUTE_RESIDENT`。总 GPU context ≤131072；渲染输入+输出预算+4096≤131072；沿用 85°C 停止、MemAvailable≥4096MiB 等已有硬边界。修改这些需要独立明确决定。
9. 不下载新大模型/切量化/切KV格式/改工具或思考模板来制造同合同“提速”；任何这种变化是独立质量与资源研究。
10. 凭证、真实源码、聊天明文、token 序列默认不进报告/公开归档。默认禁 `--api-monitor`；它会保存内容。本地受限证据需单独 opt-in、脱敏与留存范围。
11. 模型生成代码只在现有受限 Docker 评分流程执行。缺 Java 镜像记 NOT_RUN，不在宿主执行。
12. 源码存在、夹具通过、编译通过、实际 route 生效、GPU 正确、任务质量合格、性能收益、部署批准是八个不同状态。

## 启动当前实施任务时

- 读取 [19_PHASE_TASK_PLAN](docs/19_PHASE_TASK_PLAN.md) 当前 Task 的前置/所有文件/测试/产物/停止门。
- 维护旧四种控制记录 ExperimentSpec / RunEvidence / Decision / BudgetLedger；本包 JSON 为待绑定模板，不是运行回执。
- 新任务不得提前领取后续 Phase 的 GPU 次数；同一数据可复用时禁止为“更漂亮的图”再采。
- 限时内仍缺核心身份/原件/实际字段，明确 BLOCKED 或 INSUFFICIENT，并说明唯一缺口，不补造指标。
- 最终给出原始数据定位、派生表算法版本、各场景结论、失败/取消/未执行项和下一项允许动作。不可只贴平均 tok/s。

