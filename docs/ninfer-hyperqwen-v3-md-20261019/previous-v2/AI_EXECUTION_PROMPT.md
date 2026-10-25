> V2 参考快照：P7—P12 不再是执行权威；按根目录 `plans/00-master-plan.md` 和 `plans/01-v2-migration-map.md` 执行。本文保留历史设计与来源，不表示实现完成。

# 可交给后续开发 Agent 的启动指令

你负责在用户已有的 `lkyprogramer/ninfer-4090:b0-scanner` 定制基础上合入固定上游。交付物是可验证的完整源码、测试证据与受控部署资格，不是只修改文档。

先读取本包 README、docs/00—08、plans/00-master-plan.md、plans/tasks.json，以及目标仓库适用AGENTS。按data/source-lock.json的固定SHA执行：共同祖先44a2c6c，用户O=e0b05f7，上游U=5b99996。检查完整SHA，不追随浮动HEAD。

## 执行边界

当前这份包没有替你克隆、合并、编译、测试NInfer或部署。证据只证明单tokenizer.h的2处冲突与辅助工具自测。你必须从P0补齐整仓source audit、当前PROD、模型资源和真实基线；不要从包内模板推断任何phase已完成。

在独立开发目录建立集成worktree。保护原分支及当前生产overlay；禁止reset/clean生产目录、全仓ours/theirs、伪merge、改golden迎合实现。禁止在一张24GB卡同时加载两份27B做蓝绿。测试服务器操作限已明确授权的主机/容器，生产切换另需明确目标和窗口。

## 开发方式

运行本包Python自测和DAG验证。按P0→P6，每phase先串行import/freeze接口，再依赖调度task；支持subagent则依文件责任并行，不支持则拓扑串行。每task读取自己的plans/tasks/Px-Tyy.md，先测试断言，再实现，再review；保留raw RED/GREEN和实际commit。不要把预期环境错误当作功能RED。

核心融合策略：上游PromptBoundary/SegmentedEncoding权威 + 单B0扫描器；B1 memo/work/selected-token restarts适配进同一路径。legacy DTO只在测试层，冻结算法不变。保留prepare_detail与UTF8字节size，上游corelog最终24、fork命名扩展v1。导出生命周期与cache identity不能为了小diff退回旧结构。

P4采用新midrise rk4v4必须通过长context/Java质量和容量门槛；旧E8仅通过旧image+argv+cache回退，不静默alias。P5完整引入最终API/图像源码。decisionadapter未提供时，purecontract/op仍测试，真实decision资格明确UNQUALIFIED且生产不启用；不能虚构业务精度。

## 阶段 gate

所有task合入同一提交后，独立reviewer审查完整phase diff，重新构建和测试。必须覆盖旧自定义测试、G1 standalone逐case对齐、上游新回归、真实4090/27B、本阶段长上下文/工具/缓存场景。不得以ctest exit0忽视0test/skip77，或把4096context的prefix_real当262K验证。

把reviewed_commit、每check的source_commit、task commit、raw文件及SHA256写入phase-result。required_checks由plans/tasks.json拥有，不能在结果文件删项或降成manual。运行phase_gate.py进行一致性检查；脚本不是代码/硬件真实性证明，人工/Agent review必须同时看真实日志。

上一gate没通过，不进入下一phase；允许在已阻断阶段内继续独立可完成工作并报告状态。phase review改了源码就重跑受影响测试，最后证据必须对应最终commit。对风险发现作最小必要修复，不扩展CI治理、新模型支持或训练项目。

## 性能与发布

冻结P0 profile：实际reasoning/medium代理契约、MTP3等以现场为准，不能关闭thinking或把128K以上输入缩短以“优化”。区分PROD/O/C，单卡串行A/B/A，监测频率/温度/功耗，报告cold/hot/client TTFT与token速率，质量按冻结Java编译/测试判定器。

缺原G1、权重、GPU或授权时如实BLOCKED/PENDING，不能删除测试或降低阈值。最终分别报告源码完整、Chat资格、可选decision/vision/browser资格、实际发布状态。执行生产试运行和回滚必须有批准，旧三件套保留。实际恢复旧实例并跑正常请求才能写回滚通过。

## 完成输出

给出最终commit/镜像digest/profile与cache路径、34上游和43定制项保留账本、7phase gate、CPU/CUDA/真实模型/长Agent质量、性能配对、当前驻留版本、实际回滚记录和所有未资格能力。没有执行的内容不得写“通过”。


## P6之后

本包v2增加tqLLM性能融合。真实P6-GATE通过之后读取[TQLLM_EXECUTION_PROMPT.md](TQLLM_EXECUTION_PROMPT.md)，按P7—P12接续。不要从旧E8基线或上游U裸版本直接跳到DFlash2实现。
