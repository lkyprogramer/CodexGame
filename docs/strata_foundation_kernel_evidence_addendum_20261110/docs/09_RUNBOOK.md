# 09 · 执行手册与停止条件

状态：**PLANNED / NOT implemented**。当前仅允许离线交付与 CPU 检查；engine starts、generation requests、GPU budget 均为 **0**。本手册补充原 `docs/15_RUNBOOK.md`，不授予 GPU、真实服务、模型下载或远端写入权限。

## 1. 开始前先辨认已有能力

依次读本包 README、AGENTS、START_HERE_AI、[03](03_BASE_INTEGRATION.md)、增量计划，以及原底座 O0–O6 合同。确认原包 hash、固定源码 SHA、现场部署身份分别记录；“审计最新源码”不是“已部署”。保留原 ZIP/MANIFEST，不原地重写。

后续获准在 Lab 实现时，先检查 dirty worktree、已有 controller、monitor、completion schema、force checker、manifest、spill 与 microbench；只增适配器/附件，不复制 pipeline。Lab 为唯一执行根，原生 Strata 修改使用独立 worktree。E0 先产出来源锁、复用矩阵、零预算 scope；其余按 E0–E4 与原 27 任务的依赖推进，每阶段独立 review/test。

## 2. 本包当前允许的 CPU 操作

工作目录为本包根目录。先确认脚本、tests 与固定输入确实存在；缺失记 `NOT_IMPLEMENTED/BLOCKED`，不要猜造 CLI。逐项运行、分别保留输出与退出码：

```bash
python3 -B -m unittest discover -s tests -v
python3 -B tools/validate_addendum.py
```

已有经核查的上游源码文件时，才可执行下项；路径是待替换占位符，不会自动下载：

```bash
python3 -B tools/probe_upstream_force_check.py --source /absolute/path/to/audited/force_check.py
```

Probe 仅接受其 SHA256 白名单中的固定源码，使用合成输入检查已定位行为；不得删白名单以迁就文件，不 import 任意用户模块，不调用 `gen/score`、引擎或 GPU。源缺失/hash 不符即停止该项。该结果证明特定工具行为，不证明模型正确性；实际检查范围和未执行项逐项写入 `VALIDATION.md`。

若 probe 复现“上游接受不完整输入”，应同时记录“该行为复现成功”和“该输入不具备实验资格”，不能把前者写成数值正确性通过。零测试、跳过、预期拒绝与真正执行通过分别计数；测试发现命令成功也不代表验收矩阵全部已实现。失败时保留原件与首个失败原因，先处理本项离线合同，不转而启动真实 scorer 获取替代证据。

## 3. 证据关联次序

先源码与配置，再候选编译产物，再已有加载/JIT 记录，最后关联实际 dispatch/graph replay/完成点。每层都用内容 hash 和原 scope 引用：编译成功不等于加载，加载不等于路径命中，命中不等于完成或收益。当前不得为补链而编译、跑 microbench 或生成 live 记录；缺层就停在其证据等级。

按 [08](08_TEST_AND_ACCEPTANCE.md) 逐项完成正反例及验收清单。强制区分诊断与 observer-off 数据；profile 改变 graph 时不能用其测量证明正常路径等价。保存 UNKNOWN、失败与未匹配项，禁止为得到结论裁剪输入集合或重写失败记录。

未来若用户另行授权设备实验，必须先在原 ExperimentSpec/BudgetLedger 冻结阶段、输入、身份、引擎/请求数、capture/replay/pass、重试、时长、报告体积和清理边界；复用既有 OwnedServer/owner lock。再依原小 CUDA→短模型→长跑资格顺序执行，不能跳级。这里不提供可直接启动产品/采集器的替代命令，也不把未来合同当当前权限。

## 4. STOP / NO-REOPEN

| 条件 | 必须动作 |
|---|---|
| 未授权、预算为零、工具/权限/架构不满足 | STOP/BLOCKED；不 sudo/setcap、改驱动、换机器或自动续采 |
| 身份冲突、forcing 集合/覆盖失败、observer 改路径、质量失败 | 保留证据并阻断相应资格；不靠补跑、放宽容差或删除样本修复结论 |
| 依赖/加载/状态证据不足 | UNKNOWN/INSUFFICIENT_ATTRIBUTION；列明缺口，下一 GPU 任务为 null |
| 无新增机制，或触及历史关闭边界 | NO-REOPEN；新 SHA、tile、名字或微基准局部变快都不是重开理由 |

F01/F02/F03、GU-SwiGLU/TG21、P01/P01B、P24HC、NP3、SPEC/SPECCOST 等既有关闭结论保持；继承用户报告的 DFlash2 后续复验收益不足结论（本轮未核原始 trace），继续保留 MTP=4，不重复对比。旧 GU/TG21 占比是历史条件 profile，不能充当当前 warm completion 曝光。原 4%+AA、六对 exact bootstrap、retrieval FAIL 与 P05 阻断无例外。

结束时提交任务 ID、改动文件、对应 K 用例、证据索引、五轴判定、剩余未知和唯一下一步；当前 `next_gpu_task=null`。离线可做事项耗尽即结束，不用无限采集替代决策。
