# 机器合同说明

- `source-lock.json`：项目/论文/模型revision的审计pin，不是已下载权重清单。
- `source-audit.json`：49项Atomic/squid源码的commit、路径、Git blob SHA与URL；静态核查，不是硬件测试。
- `task-graph.json`：44任务的依赖与初始状态。R03公开runner缺口已撤销，当前NOT_RUN；实际能力另行资格。
- `run-contract.json`：JSON Schema 2020-12，定义未来lab的原始运行记录结构。
- `run-example.json`：有意保持NOT_RUN/null的示例，不能直接启动模型或作为PASS证据。
- `gate-contract.json` / `gate-example.json`：与run事实分离的资格决策，顶层能力key绑定被资格化的candidate；输入按candidate/baseline/reference角色分别绑定各自key和文件hash。G3另需冻结comparison contract，G7还要求当时执行会话的授权记录。填写JSON本身不创造权限。
- `pair-plan-example.json`：未填充的成对运行计划，T01的run消费它，在一次调度中交错A/B并产生baseline/candidate证据子目录。
- `validation-policy.json`：本方案预先提出的策略阈值；更改必须在看数据前记录DECISION。
- `test-catalog.json`：148测试ID与原文验收含义，覆盖原TC/GX/AX及新增LX/UX/MGX。全部计划测试NOT_RUN。

Schema只检查结构和有限的条件约束。T01还必须实现语义检查：能力与锁文件匹配、P+N+实现reserve≤capacity、实际输入达到计划、files/hash真实存在、target_4090与正确硬件对应、selected feature已资格、真实raw而非合成数据、非空测试集合、正确CI与独立样本、exact target的oracle、所有实际argv可追溯。

一个人手写合法JSON并不能构成测试通过。run的PASS最多说明该次采集及声明的oracle检查通过，不能推出统计收益或发布资格；原始run禁止嵌入gate_decisions。独立gate.json必须读取并验证所有input run的实际状态、角色对应的锁定能力key、required tests与raw artifacts/hash，再由审查形成结论。candidate输入必须匹配gate顶层key；baseline/reference保留各自key，不能要求AR与DSpark的完整key相同。G3按comparison_contract检查预登记固定因素、允许差异和共同成对schedule；改变目标的业务比较单列，不冒充同目标算法加速。NOT_RUN/BLOCKED输入不授予对应能力PASS。G7授权必须能追到真实执行会话，不能把文件内自述当授权。

主线formal_mini只允许R3。研究last-loop/guidance产生新target_fingerprint；2DSD必须使用匹配的研究资产与实际proposal。候选k、块大小b、verify宽度B分别记录。未实现能力返回BLOCKED，不静默退化成另一个算法却保留原标签。

G0可用inventory角色引用硬件inventory与资产锁等类型化事实，该输入的运行能力key可为null；G1–G6的推理能力必须引用实际run记录。status=PASS仍不能跳过内容验证。配置中的扁平模式字段与cache_contract/guidance_contract必须相符；所有runtime会影响目标的字段须进入03的规范化指纹。

## v1.1补充

`source-lock.json`新增S18–S21，核心来源pin为16项；02文档来源登记共21项。`ghost-source-audit.json`提供Ghost最新公开分支、tag/PR lineage、树差异及实际读取源码的Git blob/SHA256核对；`ghost-transfer-matrix.json`将机制映射到六个可选G任务和GX测试。`validation/ghost-ci-observed.json`在包根的validation目录，记录观察到的外部CPU CI，不是本地模型执行记录。

v1.1时文档版本为1.1；JSON实例`schema_version`仍为1.0。本次run schema只扩充合法task_id，原示例继续有效。新增配置维度见05与25，由T01实现后的语义验证器绑定实际dispatch/指纹；未选机制不要求伪造字段或PASS。G04初始DEFERRED，其余新增任务NOT_RUN。v1.1的68项计划测试当时均NOT_RUN。


## v1.2补充

v1.2当时文档包1.2，原实例schema_version保持1.0；源锁30项、来源登记35项。原24任务/68测试保持，新增K00–K07/AX01–AX28，合计32任务/96测试。K07 DEFERRED，其余新增任务NOT_RUN，全部计划测试NOT_RUN；run schema仍仅扩展task_id，不改变原gate-policy/helper。

- `cuda-rust-source-audit.json`：固定main、已合入hardening、release/toolchain/driver/proof边界、141份去重源码hash及作者性能的适用范围。
- `sm89-backend-matrix.json`：硬件/前端/op分层能力；不含本机资格。cute-rs、Tile FP8/FP4等排除项明确。
- `kernel-search-policy.json`：执行前冻结的搜索额度提案、生成器权限和独立确认纪律；不构成费用或生产授权。
- `kernel-candidate-contract.json` / `kernel-candidate-example.json`：独立候选事实Schema和NOT_RUN/null示例；编译、proof、实际执行分开，qualification固定NOT_ASSESSED。
- `validation/cuda-rust-ci-observed.json`：外部CPU/proof compile、skipped Tile job与较早Blackwell GPU记录，均非本机4090run。

新Schema仅检查结构和有限条件。K01/T01仍须校验真实文件/hash、非空义务及计数求和、假设落实、真实设备/launch/输出、artifact与能力key同一性、完整测试范围和统计/授权。编译/证明可单独留事实，不自动获得gate；实际执行PASS只说明对应run/oracle，不代表性能或发布资格。

kernel候选引用放在原可扩展config/execution/oracle/measurements内，不向封闭engine/hardware/model任意塞字段。完整capability新维度见05/28；未知用null，不能补0或合成hash当真实文件。正式C++未请求proof与verified路线失败分别处理，不能把失败悄悄改成NOT_REQUESTED沿用身份。

## v2.0：完整缓存与Magnitude

当前包版本2.0，47来源ID、42源锁项、44任务、148计划测试。run/gate/kernel的既有schema_version保持1.0；新增cache合同为2.0，互不冒充。run合法task_id扩展L/M，config可引用cache profile；既有gate、validation-policy和两个helper与其9项测试保持。

| 文件 | 用途与边界 |
|---|---|
| [cache-object-contract.json](cache-object-contract.json) / [example](cache-object-example.json) | 完整checkpoint目录结构；planned/null示例不授能力；qualification固定NOT_ASSESSED |
| [cache-semantic-rules.json](cache-semantic-rules.json) | L01未来必须实现的CS语义检查；本文件不是验证器 |
| [cache-profile-example.json](cache-profile-example.json) | 尚未选定真实格式的Tier提案；staging上限是全部并发buffer+scratch总量 |
| [resource-policy.json](resource-policy.json) | 按阶段的峰值、reservation、retiring、transfer与cost epoch合同 |
| [lossless-source-audit.json](lossless-source-audit.json) | Loom论文与codec静态源码；作者测量不能作为本机数字 |
| [upstream-refresh-audit.json](upstream-refresh-audit.json) | 2DSD37新增文件blob核对、CUDA Rust14文件delta与CI摘要观察 |
| [magnitude-source-pins.json](magnitude-source-pins.json) | 49分支、8组比较、58源码pin、版本与许可元数据 |
| [magnitude-source-audit.json](magnitude-source-audit.json) | 20项分级发现与16项MGX计划；不分发第三方完整源码 |

M00和L01共用一个账本/状态实现，M01与G01/L03共用transfer lifetime，M02复用T/K证据，M03复用T11/L07协议与发布验证。仅被选中的功能增加对应依赖；不得为完整包所有任务伪造完成记录。Schema结构通过后，hash真实性、状态清单完备、数值区间关系、真实lease/event、容量和语义仍须实际验证。

[mechanism-profile-example.json](mechanism-profile-example.json)为M机制的关闭态提案，唯一run引用字段为`config.mechanism_profile_ref`。所选prefetch/spec_control/observability条件以该文件的enabled值求值；真实policy/receipt、capability与硬上限必须由语义验证器核对，不能把空值当作无限或已资格。
