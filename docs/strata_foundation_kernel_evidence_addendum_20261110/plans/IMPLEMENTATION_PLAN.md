# 4090 Kernel Evidence Addendum Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development（支持子代理时）或 superpowers:executing-plans（无子代理时）。先遵守本包AGENTS、用户授权和原冻结合同；不得把文档任务视为GPU运行许可。

**Goal：** 把samir-vllm的简洁正确性/内存边界、Nabo的生成代码与计数器诊断方法，接入既有完成路径和SpecPilot式证据治理。

**Architecture：** 原O0–O6、四类实验记录和唯一controller不变；只增加版本化证据附件与薄适配。默认engine starts=0、GPU budget=0。

**Tech Stack：** 既有lab Python标准库/测试框架、Strata C++/CUDA的已有manifest/dispatch/checker入口。初版不新增服务、数据库、GPU collector或自动搜索器。

**Spec：** [证据合同](../docs/04_EVIDENCE_CONTRACT.md)、[计数器](../docs/05_CODEGEN_AND_COUNTERS.md)、[数值守卫](../docs/06_NUMERICAL_GUARD.md)、[内存合同](../docs/07_MEMORY_AND_ORACLE.md)。

**Global Constraints：** 不重开旧closure；不改变baseline、抽样、quality、oracle、预算；不自动升级Strata；source/build/deployed分离；未知阻断晋升但允许保存诊断；既有文件如已实现则只审差量。

**Review Focus：** 因果与时间域、实际运行路径身份、覆盖完整性、别名生命周期、统计合同继承、非法自动执行、范围膨胀与可维护性。

## 0. 两个根与一个交付边界

- `<LAB_ROOT>`：CodexGame 的 `docs/strata_4090_128k_lab`。
- `<STRATA_ROOT>`：独立、只读优先的Strata工作树；SHA先记录，不假定就是生产版本。
- 下文代码路径都是**建议/PLANNED**。E0先寻找实际模块；有实现则复用，改路径表后独立review。禁止建另一套相同功能目录。
- 本ZIP交付的是计划、合成合同与离线自检。以下产品代码、GPU资格、优化部署均未在本轮实施。

E0→E1→E2→E3→E4严格串行。每阶段的Implementation Task最小测试通过后，派独立reviewer与独立tester；二者都通过才能进入下一阶段。独立子代理不是OS权限隔离，仍须限制读写与执行权限。

## E0 · 对齐原包、现场实现和关闭账本

### E0.1 来源与部署身份盘点

- 输入：本包sources锁、原包hash、真实仓库HEAD/dirty状态、已有组件manifest；只读。
- 输出：`<LAB_ROOT>/reports/kernel-evidence/source-and-deployment-map.md`，逐项SOURCE_INSPECTED/BUILD_INSPECTED/DEPLOYED_UNKNOWN，不混为一层。
- 不做：fetch/升级/编译/启动引擎；缺现场信息写UNKNOWN。
- 最小测试：更换source SHA但保留旧binary hash的夹具不能得到loaded绑定；parent ZIP hash漂移明确报错。
- 完成：每项来源、状态、有效范围可追溯；无需“补齐GPU信息”才能完成文档盘点。

### E0.2 原模块与历史去重

- 输入：原27任务实现状态、唯一controller/RunEvidence、F01/F02/F03等关闭与P05阻断。
- 输出：`reports/kernel-evidence/reuse-map.md`，每一拟建模块标REUSE/EXTEND/NOT_IMPLEMENTED。
- 最小测试：给“新增donor但机制相同”的候选，保持closure；DFlash2后续USER_REPORTED与raw证据分列。
- 完成：旧F02等不在新计划执行队列；没有二套runner/scorer。

### E0.3 合同预注册

- 输入：04–08章与E0.1/0.2；可与E0.1的只读盘点并行草拟，最终需合并其输出。
- 输出：`reports/kernel-evidence/contract-v1.md`：schema、字段有效域、未来计数器授权边界、fixed-text MVP、read/write白名单。
- 最小测试：任何shell命令、自动启动或模型路径出现在可执行配置中均拒绝；GPU预算为0。
- 阶段门：独立review确认没有伪装成基础设施的旧kernel探索；独立tester复核parent hash与所有状态标签。

## E1 · 只读证据附件与路径绑定

### E1.1 Artifact身份解析（可与E1.2并行）

- 建议文件：`lab/observability/artifact_bindings.py`、`tests/observability/test_artifact_bindings.py`。
- 输入：已存在组件manifest、已授权二进制文件hash、编译记录、已存在loaded-module记录。
- 输出：04章分层绑定结果及reason codes；复用现有hash/安全路径工具。
- 最小测试：同名不同文件、dirty源码、缺loaded映射、JIT来源未知、SM86/SASS冒充SM89路径；拒绝路径逃逸及manifest命令执行。
- 边界：不反向通过import/执行二进制补身份，不为缺产物重新编译。

### E1.2 Tensor与work scope附件

- 建议文件：`lab/observability/kernel_evidence.py`、对应test。
- 输入：已有event index、dispatch/manifest快照、真实或合成shape描述；data_origin必填。
- 输出：kernel-evidence/v1验证器；共享batch单份引用、图generation与replay映射。
- 最小测试：混合量化元数据丢失、跨request乱配、捕获次数乘错图、共享耗时重复、无精度domain、64位ID浮点化。
- 边界：不改原completion-path/v1身份生成器，不从kernel排列猜归属。

### E1.3 附件接入（依赖E1.1/1.2）

- 修改：现有RunEvidence序列化/解析处；真实路径由E0确定，不再写一个serializer。
- 输出：版本化attachment refs、hash、limitations；旧无附件记录仍可读取但不能假设具备新证据。
- 最小测试：旧schema兼容、未知附件保留、不可信附件不改变Decision、raw引用不可覆盖。
- 阶段门：reviewer审源→运行链的每一个跳跃；tester运行上述负例与旧归因回归，所有已有决定不变。

## E2 · Codegen与counter的离线适配

### E2.1 静态资源报告导入

- 建议文件：`lab/observability/codegen_evidence.py`、对应test。
- 输入：既有check_cuda_spills输出/组件manifest/反汇编文件；不执行编译。
- 输出：SM、symbol、REG/STACK/LOCAL/SHARED、工具版本与产物hash绑定；保存原exit code。
- 最小测试：77不能算PASS；--list不能算审查通过；未扫描vendored范围明示；SM86 allowance不能套SM89；静态LOCAL不生成动态流量字段。
- 边界：不复制上游spillchecker，不跑P11/F02编译或tile搜索。

### E2.2 Counter附件导入（与E2.1可并行）

- 建议文件：`lab/observability/counter_evidence.py`、对应test。
- 输入：已存在导出文件或合成夹具；实际capture只留未来授权接口。
- 输出：metric是否supported、单位、scope、采集版本、replay/cache/clock、丢失计数、观察器角色。
- 最小测试：metric unsupported/null不填0、不同launch bytes/duration禁止精确比值、权限失败blocked、计数器采集不能成为observer-off结果。
- 边界：不启动NCU、不自动sudo、不查询驱动计数器、不新增常开看板。

### E2.3 观察器图差异绑定

- 修改：既有observer qualification模块与数据导入薄适配，不新增另一套overhead裁判。
- 输入：已有执行开关与dispatch/graph证据；STRATA_VERIFY_PROFILE实际存在语义。
- 输出：graph CHANGED的正常路径observer资格为REJECTED，UNKNOWN为证据不足/未评估；附件角色可保留DIAGNOSTIC_ONLY但不得覆盖资格。图等价且完整后才套原1%/3%区间规则。
- 最小测试：env未设与env="0"不可当等价；禁用fork/fusion即使U=0.99仍拒绝；graph未知即使U=1.00仍不能QUALIFIED；相同kernel数不能证明相同依赖。
- 阶段门：reviewer审数学与scope；tester验证仅离线导入也能完整表达BLOCKED/UNKNOWN，不因缺GPU阻止文档/解析器验收。

## E3 · 数值完整性与内存小oracle

### E3.1 元数据/位置完整性（与E3.3可并行）

- 建议文件：`lab/observability/numerical_guard.py`、独立test文件。
- 输入：只读原set、TSV、meta、实际emitted-token receipt与运行身份；固定文本decode合同。原meta期望ids不足以自证actual输出；无收据则FORCED_OUTPUT_UNPROVEN，不自动补跑。
- 输出：INPUT_ADMISSIBLE或具体阻断；支持06章完整position mapping，不只统计行数。
- 最小测试：06章全部负例，特别是原工具三个反例、位置重排影响first departure、重复行抵消漏行、错误分区、NaN、有限却不合法的分数摘要、forced输出WARNING/收据缺失；合法tie与格式舍入通过。
- 边界：不改stats、不默默过滤数据、不降低golden，不调用gen/score。

### E3.2 上游check薄适配（依赖E3.1）

- 修改：已有数值检查入口；包内probe不是产品适配实现。
- 输入：guard通过的真实格式离线附件、锁定上游版本、显式check参数。
- 输出：原checker输出+版本hash+上层INPUT状态；不派生OPTIMIZATION_PASS。
- 最小测试：拒绝调用gen/score/任意module；保留REJECT/INCONCLUSIVE；原算法输出改变时报告差异而非调参数求PASS。
- 边界：升级上游SHA先重新审接口，不能沿用旧probe hash放行。

### E3.3 内存所有权与独立小oracle

- 建议文件：`lab/observability/memory_invariants.py`、`tests/observability/test_memory_invariants.py`。
- 输入：合成页/slot/scratch记录与小张量；复用已有snapshot/oracle有效域合同。
- 输出：按owner/generation/lifetime的检查；dequant/index/mask等CPU参考最小样例。
- 最小测试：跨generation复用、残留映射、重复计预算、释放早于最后消费、有效域外NaN不被错比、有效域内NaN必须失败。
- 边界：oracle需独立逻辑，不将candidate表达式逐字复制；不运行模型，不实现samir分页allocator，不开放F03/adaptive tail。

### E3.4 正确性门组合

- 修改：现有Decision输入校验，仅追加附件是否足够的前置条件。
- 输入：小oracle、fixed-text数值、原状态/golden/holdout报告。
- 最小测试：数值PASS+长检索FAIL仍拒绝；prompt数值PASS不能取得decode资格；不同文本只返回UNSUPPORTED_TEXT_CONTRACT，不误报所有算法错误。
- 阶段门：独立review算法独立性/有效域；独立tester直接构造恶意缺漏输入，不能只运行开发者happy path。

## E4 · 既有控制器接入、复核与交付

### E4.1 单一controller接入

- 目标：原计划`tools/frontier/exploration_control.py`或现场已确定唯一入口。
- 只改：读取已验证附件、显示reason/limitations、阻止不合格证据晋升、记录预算为0的离线完成。
- 最小测试：无候选正常STOP；诊断counter不能提高L等级；旧closure和6对统计结果逐字/结构回归；没有第二个scheduler或自动实验队列。

### E4.2 独立审核与独立全阶段测试

- reviewer只读review diff/合同/原始证据；tester独立执行CPU套件、离线负例、来源/链接/hash检查。
- 输出：`reports/kernel-evidence/review.md`、`tests-report.md`；列出未测/阻断项，而不是总括“全部完成”。
- 任一缺陷由implementation owner修复后，reviewer/tester只重验相应及受影响回归；不得删掉失败用例。

### E4.3 交付与后续授权边界

- 输出：模块和schema说明、旧功能回归表、未完成现场资格清单、版本化manifest。
- 通过标准：离线可审计、闭项不变、没有隐式执行、输入缺漏fail closed；不是tok/s提高。
- 后续若需GPU：单独批准原O2/O3/O4采集窗口、目标binary/模型/工作负载、观察器/权限、时间/磁盘上限。优化候选仍需新的premise_delta与原收益门；部署再单独授权。

## 工时和停止原则

不承诺固定天数。E0若发现原O0/O1或OwnedServer尚未实现，先回到原包依赖任务；不能用增补脚本填成另一套底座。任何身份、quality、权限阻断均保留，不用“先跑一次看看”绕过。

实施顺序固定为 **E0→E1→E2→E3→E4**。阅读和评审应优先关注E1身份桥、E2观察器资格、E3.1数值完整性；不能因优先关注就跳过阶段。counter适配只实现当前最小离线合同，未获准的现场采集保持未实现。先完成一个真实缺口的闭环，再扩大覆盖。
