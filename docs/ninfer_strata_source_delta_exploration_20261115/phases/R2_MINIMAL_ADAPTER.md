# R2 — 一个候选的最小默认关闭实现

依赖：R1选择一个候选、开发授权、隔离worktree。硬件/模型/HTTP仍0。不得修改生产树、旧golden、freeze或统计工具。

## R2-T1 先写最小失败测试

### 选择D1时

拟新增`src/targets/qwen3_8/impl/runtime/source_copy_plan.h`及项目现有test目录中的`source_copy_plan_test.cpp`。先检查现场已有H7/source planner，等价则不新增。

- [ ] 写能暴露错误source/编辑恢复/失效状态的测试，确认新assert失败而不是构建环境失败。
- [ ] 只用纯token输入，精确比较proposal/anchor/reason，不启动模型。
- [ ] 明确witness：哪些指令只是被弃草稿，哪些是MTP mandatory维护；若无法分离，禁止实现skip分支。

### 选择H2时

拟新增`src/targets/qwen3_8/impl/runtime/draft_head_shortlist.h`、资产manifest读取器与`draft_head_shortlist_test.cpp`；GPUselected-row文件只在绑定现有head launcher后确定，不能猜通用kernel名。

- [ ] 先测hash/shape/remap/tie/越界/缺失资产fallback。
- [ ] 资产schema与格式在code前冻结，禁止在运行时偷偷重新训练/转换模型。
- [ ] 为后续selected-row GPU oracle写测试定义，不在本Phase运行它。

## R2-T2 最小adapter

D1接入 `mtp_impl.h` / `text_context_impl.h` 的当前真实路由，Target verifier与Program权威commit不改数学；任何proposal skip须保留必要catch-up。H2仅包裹`proposal_argmax`与load bindings；原Target head和sampler不变。

- [ ] 用一个默认关闭开关；解析明确的off/on，未知值拒绝；unqualified sampled走baseline。
- [ ] 不在热路径新增IO、锁、动态分配、同步或独立线程池；scratch在原资源/Graph生命周期中预先绑定。
- [ ] 输入/资产不适配则fallback并给bounded reason；不能默默换codec、W或context。
- [ ] build仅使用项目现有受支持配置。若需要新依赖/权限，停止申请，不安装driver或“解锁”PDL。
- [ ] 最小验证：新增CPU合同测试＋直接受影响的现有回归；不每Task跑全仓/模型矩阵。

构建/test的**实际命令**由R0读取目标项目preset/CTest列表写入`binding.json.test_commands`，R2执行该精确argv。未绑定则BLOCKED，不能把本包虚构的target名当现成测试。测试产物存`runs/<id>/r2/`并封存stdout/stderr/exit code。

## R2-T3 证据与权限adapter

与T2可分文件并行：拟新增`tools/frontier/donor_delta_20261115/evidence_adapter.py`及`test_evidence_adapter.py`，只把事件映射到原四件套；不自行开引擎。

- [ ] 类型/ID/ns string/null reason检查；D1executed未知不得变false，H2head+AR不可变head-only。
- [ ] 落盘在控制器安全点，原始事件缓冲有cap，drop可见。
- [ ] 默认硬件批准0，template/缺授权/identity mismatch返回拒绝。
- [ ] 最小测试：合法样本、missing、错timebase、旧graph generation、dropped、预算耗尽、取消记录全部保留。

## Phase gate

独立Reviewer审代码+状态事务+历史差量；Verifier复现CPU/build最小集合，确认default-off无行为变化。文档/CPU绿仅给`CPU_PREPARED_NOT_GPU_QUALIFIED`。输出所有剩余硬件用例和R3申请，不自动启动模型。若实现超出R1机制、引入新dtype或graph重构，回到设计审查，不靠补测试放行。
