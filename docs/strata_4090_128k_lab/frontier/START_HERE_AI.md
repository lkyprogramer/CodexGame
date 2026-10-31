> 当前结束点：2026-10-31[Astra复核](reports/ASTRA_REASSESSMENT_20261031.md)完成，NO_QUALIFIED_CANDIDATE，本轮收口。F02保持DEFERRED_NEW_EVIDENCE，取消原拟四小时审计；不进入候选开发、不追加GPU。先读父目录行动计划和收口报告。P01/P01B/F03历史终态、六FAIL及P05 BLOCKED_EVIDENCE保留。生产随后按用户要求恢复运行，GPU已占用；回执在父目录`reports/PRODUCTION-RESTORE-20261031.md`，旧停机记录不代表当前资源状态。

# 给执行 AI：先证明有空间，再写内核

> 本文 P00–P07 均指 `frontier/P00`–`frontier/P07`，与历史 P0–P24 不同。当前阶段和授权范围由父目录 `plans/NEXT_ACTIONS.md` 确定。

## 任务和边界

目标是在这台 RTX 4090 / Xeon Silver 4216 / 64GB 级内存的机器上，提高**现用模型、单会话、128K 上限内的有效任务性能**。不要把缩短回答、减 thinking、删专家、换量化、改提示词或增加并发当成同一个优化。

原作者交付状态为 `PLAN_ONLY`；本轮P00准备已交付，阶段门见父目录workspace/frontier/p00-20261030/PHASE_GATE.json。原作者未连目标机；整合时完成只读身份核对，未编译 native 候选、未跑 GPU。所有 Phase 的硬件结果初始 `NOT_RUN`。先完成可离线完成的工作；后续会话明确授权执行时继续，不要求用户重复确认已经授权的常规步骤。

上述是导入时边界，P01/P01B和F03后续实际执行另有报告。当前没有待执行任务：以下读取与执行循环只在未来新合同成立时适用，不能据旧P01步骤重跑。重开须有独立新机制、当前真实暖态命中与依赖证据、可信净省时≥4%依据及用户明确的执行范围。

## 第一轮必读，按顺序

1. [快照](docs/00_SNAPSHOT.md)、[关闭台账](docs/01_EVIDENCE_AND_CLOSURES.md)。确认生产 A0、实验 P6、最新 main 三者不同。
2. [关键路径模型](docs/02_ARCHITECTURE_AND_LIMITS.md)、[限额诊断](docs/04_WARM_DECODE_DIAGNOSTIC.md)。不要从旧 profiler 的 kernel 总和立项。
3. [候选决策](docs/03_CANDIDATE_DECISION.md)、[引擎差量](docs/07_DONOR_DELTA.md)。识别已覆盖和硬件不适配。
4. [数值/质量](docs/05_NUMERICS_AND_QUALITY.md)、[统计](docs/06_BENCHMARK_PROTOCOL.md)。使用本包明确的新预登记政策，不混用 P3/P24/旧通用 stats 的门。
5. [阶段 DAG](plans/INDEX.md)、[接口与旧工具绑定](docs/10_HARNESS_BINDINGS.md)。只有当前 Phase 的依赖已通过才进入下一阶段。

## 直接执行的离线检查

```bash
python3 -B tools/validate.py --root .
python3 -B -m unittest discover -s tests -v
```

这两步验证交付与离线计算，不证明 CUDA、4216 或模型性能。禁止将合成 fixture 输出写成机器实测。

## 执行循环

1. 为本轮建立独立 run_id；登记授权范围、输入身份、源代码差量、上限、停止条件与不可改的评分合同。
2. P00 完成只读身份和旧证据映射。原报告链接中的 workspace 原件不一定在 GitHub；缺原件标 BLOCKED_EVIDENCE，不能据报告填造 hash。
3. P01 只采一次限额暖态长会话诊断：最多1引擎、3工作请求、3600秒墙钟总预算；100K prime 后两次真实Pi短追问append，按用户决定记录实际新读量，各目标/上限2048输出、每请求最多600秒。加载、冷却和收尾也占总预算，至少预留120秒清理。
4. P02 汇总证据。没有可验证依赖路径，或者可删成本不足，输出 NO_QUALIFIED_CANDIDATE/INSUFFICIENT；结束。不要继续到候选实现。
5. 只有一个候选拿到资格时，先汇报具体改动和验收边界，确定该阶段执行范围后按卡片选最小实现。源码差量没有实际命中、资源算不清、E1/Q 缺质量前提，均不进入正式性能。
6. P03–P04 做单候选最小实现、匹配分派数值、真实生命周期与必要 sanitizer。关闭路径必须先与原基线一致。
7. P05 先核已有稳定warm探针的完整原件，缺证据则不启动A/A或主批次；每个prime后再核实际append hash。资格成立后关闭 profiler、同步 dump、oracle、诊断调度和临时加载设置，按冻结整对运行统计。失败保留，不补跑替换，不边跑边看显著性。
8. P06 处理任务质量与必要热稳态。原六 FAIL 未解决时，不给总体 READY。性能或数值通过只能形成研究结论。
9. P07 导出报告、源码/构建/原件身份、负结果和保护回执。回收自己的进程与端口，生产保持原状态。

## 两类基线必须并存

- P：生产 A0 + 已部署项，只记录和保护，不自动升级。
- B：P6 原生 v0.2.7 + 已验证的六文件 reply/PT port，完整配置不变；用于本轮诊断与条件实验。

若仅原P6二进制不可得，但完整源码、port、构建/配置及资产原件齐全，可按原P6恢复流程在独立树重建并重新冻结身份；这是单独的基线恢复工作，不隐藏计入P01诊断。若port、配置或资产身份缺失，先BLOCKED_EVIDENCE，不猜测恢复。不能默默把main、Maya或HC二进制当B。新donor只作为来源，不触发整仓更新。

## 并行规则

同 Phase 的证据整理、源代码审阅、离线分析可分配不同代理。两个代理不得修改同一 native 文件；合并后再验证。GPU锁、引擎启动、采样、memcheck、最终配对都串行。每 Task 不派完整评测；阶段收口复用有效 review/test 证据；有新的实质变更时，安排独立审阅核范围/数值/归因与原件完整性，不为每个文档阶段固定增加两个代理。独立角色未实际跑硬件必须如实写明。

## 明确禁止的“捷径”

- 没有诊断先实现所有十二张卡；更换评测集证明原错误“已修复”；重复旧失败直到偶然好看。
- 用 tokens/window 增减替代 ms/有效 token；把 GPU wait 全部当 launch 开销；把 copy/kernel/CPU 时间相加成墙钟。
- 删除历史失败、将 OOM 视为无效样本后补齐六对、把 missing/NOT_RUN 当 PASS。
- 将模型的 target tail skip 再加深，或把 Edge0 zero-overflow 路由作为原模型无损方案。
- 自动部署、远程停别人进程、改系统权限以让工具工作、复制模型权重或安装不需要的依赖。

## 最终交接必须回答

做过什么、没做什么；从哪个源路径改了什么；实际命中多少；同路径数值是否一致；完整请求是否改善；原六 FAIL 和相对非劣是什么状态；是否有新资源/热风险；为什么结束；生产保护是否未变。没有资格时交付明确的负结果，不开下一轮自我循环。
