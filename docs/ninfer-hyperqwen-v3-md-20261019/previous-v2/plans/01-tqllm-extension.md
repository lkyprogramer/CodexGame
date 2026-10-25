> V2 参考快照：P7—P12 不再是执行权威；按根目录 `plans/00-master-plan.md` 和 `plans/01-v2-migration-map.md` 执行。本文保留历史设计与来源，不表示实现完成。

# tqLLM 后续融合实施总计划

> **For agentic workers:** 用superpowers:subagent-driven-development或superpowers:executing-plans按任务推进；先读本页与设计，不直接对旧生产二进制运行新flag。

**Goal:** 在已合格P6集成版本上，以同Target质量/上下文为约束，获得可验证的MTP/Lookup/完整验证、DFlash2和全局草稿检索收益。

**Architecture:** 保留NInfer单一执行/状态/缓存权威。tqLLM是只读算法/算子参考，不是merge parent；新增companion和archive均有边界与预算。

**Tech Stack:** C++20/CUDA sm89、现有CMake/CTest与Pythonreference，单RTX4090/64GBhost。

**Spec:** [研究结论](../docs/tqllm/00-executive-and-scope.md)、[C01—C05契约](../docs/tqllm/03-speculation-contracts.md)、[C06DFlash2](../docs/tqllm/04-dflash2-design.md)、[C07—C08Archive](../docs/tqllm/05-selective-draft-cache.md)。

## Global Constraints

固定Targetartifact、tokenizer/template、rk4v4及原context/pool与回退门槛；禁止静默Target换权/量化/截context；不取消B0、计时与原oracle。新feature默认off，DFlash2首版greedy/base/text/chainK<=5，完整Target验证；不合并无关Git历史。只使用已resident且已资格的后端，请求开始冻结计划。公开CLI/头文件/CMake/Program集成由Integrator唯一串行所有者处理。

## Review Focus

跨backend的ready状态与缺DraftArchive的Target热命中（P8-T01/P11-T05）；拒绝/bonus导致featurefrontier与tokenfrontier不同（P10-T04）；长上下文第0页检索不到（P11-T02）；CPU刷新晚于lane复用（P11-T04）；采样lattice分数被误当q及Target词表被裁剪（P10-T05/P10-T06）。每类都有对应负例，不以源文件存在表示验收完成。

## 阶段

| Phase | 目标 | 实施tasks | 统一gate |
|---|---|---|---|
| P7 | 冻结整合基线、资产、观测和资源预算 | 4 | P7-GATE |
| P8 | MTP宽度策略与Prompt Lookup共用精确验证 | 5 | P8-GATE |
| P9 | 已有完整KV验证的瓶颈优化 | 4 | P9-GATE |
| P10 | 原生27B DFlash2 companion与固定ring | 7 | P10-GATE |
| P11 | 全局草稿archive、选择、异步staging与图 | 7 | P11-GATE |
| P12 | 最终集成审查、A/B/A与受控发布回滚 | 5 | P12-GATE |


总DAG：`P6-GATE → P7 → P8 → P9 → P10 → P11 → P12`。机器权威是[完整tasks.json](tasks.json.md)，仅新增节点镜像在`../data/tqllm/extension-tasks.json`。原35task+7gate不改依赖，新32task+6gate接续；所有节点未执行。

## 并行批次与文件锁

P7-T01/T02可并行，T03等T01接口冻结。P8-T02/T03分别Runtime/Lookup并行，T04集成。P9按明确热点顺序串行。P10-T02/T03/T04在T01view冻结后并行，T05集成，T06单owner接续。P11-T01/T02并行，T03取两者接口后CUDA实现，T04/T05接续生命周期。P12-T02/T03在T01后并行，单卡GPU队列唯一，T04需真实部署授权。并行的是独立worktree里的不同文件，不是任意同文件同时修改。

每task输出代码/测试/测量或明确NO_CHANGE，commit级自审后统一集成。同phase最终由独立reviewer读完整组合diff；gate所有检查绑定同commit。没有subagent可用时按相同依赖顺序串行执行，不冒充独立审查。

## 变量及可运行命令

```bash
export PACK=/path/to/extracted/ninfer-upstream-merge-20261015
export REPO=/path/to/ninfer-integration-worktree
export BUILD=/path/to/ninfer-build-sm89
export OUT=/path/outside/repository/evidence-tqllm
export TASK_OUT="$OUT/P8/P8-T03"
export CORPUS=/path/to/frozen-workload-manifest.json
export PROFILE=/path/to/frozen-profile.json
export TQLLM_REF=/path/to/read-only-tqllm-checkout
# MERGED_BASE_SHA must be read from a genuinely passed P6-GATE, not set to U.
python3 "$PACK/scripts/phase_gate.py" --validate-plan
python3 -m unittest discover -s "$PACK/tests" -v
```

NInfer构建选项沿用原包[命令手册](../docs/08-command-runbook.md)，不假设当前容器有CUDA。新增testtarget的源文件和target名由task登记，必须先build再CTest；手工调用GPUtest退出77也应视为BLOCKED。task末运行命令均在`$REPO`内，工具包脚本用`$PACK`绝对路径，证据只写`$OUT`。

## 新基准driver的固定CLI契约（P7-T02实现）

`python3 tools/bench/run_speculation_matrix.py --manifest FILE --profile FILE --out DIR`。输入manifest包括`schema_version=1, corpus_hash, split, cases[]`，每case有`case_id, body_file, prompt_tokens, input_token_sha256, max_output_tokens, repetitions, quality_command_argv`。profile有`target_artifact_sha256, tokenizer_sha256, compiled_commit, server_command_argv, cache_directories, speculative_config, gpu_uuid, expected_context, expected_concurrency`。启动由本地显式命令完成，不内置远端host。输出每次请求`raw-events.jsonl, request-log.jsonl, timing.json, quality.json, environment.json`及带failure/skip的`summary.json`；未达到actualtokens/未返回错误记录必须失败。模型token计数从同Targettokenizer/API获取，不以字符数估算替代。

计算辅助工具已经随包提供（不是GPU实现）：

```bash
python3 "$PACK/scripts/tqllm_eval.py" budget "$PACK/profiles/tqllm-budget-example.json"
python3 "$PACK/scripts/tqllm_eval.py" coverage "$PACK/profiles/tqllm-coverage-example.json"
python3 "$PACK/scripts/tqllm_eval.py" rounds "$PACK/profiles/tqllm-rounds-example.json"
```

预算示例故意`inputs_measured=false`，输出ILLUSTRATIVE_ONLY。GPU/host显存预算通过不等于推理速度/准确性通过。首批新辅助测试覆盖bonus计数、全局候选范围、预算漏项/回收证据和NaN错误。

## 高阶NO_GO与部分成果

P7允许完整记录“drafter资产尚未就绪”，只冻结低风险源码/基线与缺项清单；不因此阻止P8/P9。但P10-T01必须补齐全部真实资产清单后才能开始执行。P10/P11预算或正确性不满足则gate阻断；仅性能未达采用线而实验完整时，记录promotion=DECLINED并保持off，可完成研究交付。不得把未执行task设optional或改前置gate。ring未获采用不阻止P11针对该瓶颈做研究。

单独发布E1/E2仍须按部署规范完成明确范围review、最终A/B/A、批准窗口、canary与回滚。`templates/tqllm-partial-release.json`是该单独记录的起点；它不是P12全扩展gate，需人工审查真实证据。用户本次仅请求文档，不在本环境执行远端生产操作。
