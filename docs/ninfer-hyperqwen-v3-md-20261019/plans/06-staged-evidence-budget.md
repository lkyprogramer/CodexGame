# 分层测量范围与预算（2026-10-21，已获授权）

## 当前目标

用户已授权采用 [Baseline成本复审](../../ninfer-baseline-scope-review-20261021.md) 的精简安排，并补齐未来“greedy草稿、Target sampling输出”的合同。该报告的REVIEW/PROPOSAL记录编写当时状态；本页是采用后的现行安排。当前仍只改文档/采集工具并运行已有B29，不实施引擎优化、不改变生产采样/模型/codec。

**完成后的状态补充（2026-10-21）：** 278项已记账、8+2已评分；实际250条新采集/28复用，原gap/拒绝/附件缺失见[最终报告](../../../output/ninfer-baseline-29-20261020/FINAL-REPORT.md)。当前用户仅授权据此评估并更新方案，不授权重新启动Baseline、重跑完成任务或实施优化。后续试点、耗时及RE003质量归因修订以[plans/07](07-baseline-informed-validation.md)与[完成后分析](../research/04-completed-baseline-assessment.md)为准；本页原执行顺序属于保留的测量合同。

本页替代此前将672声明单元一次展开为14,420个core请求、Pi44×5和20工程×3的首次执行安排；旧manifest、状态、raw、损坏记录全部保留，不原地覆盖。完整672目录继续存在，未测项保持未资格，不把预算精简改成PASS。本页定义measurement scope，不新增或绕过full/e1_w6/e1_w8的feature release DAG。

## 1. 初始B29参考：174 core +104专项

| 组 | 精确选择 | 请求数 |
|---|---|---:|
| 全长度薄覆盖 | 14个P；O512；4 workload；cold/warm；Target生产sampling；各1次；P256/tool两格不可表示单列 | 110 |
| Target-greedy诊断 | P1024/32768/131072/253952；copy/free_java；cold/warm；O512；各1次 | 16 |
| 输出预算边界 | P1024/131072/253952；O128/2048；4 workload；cold/warm；Target生产sampling；各1次 | 48 |
| 长decode | P32768/131072/253952；copy/free_java；cold/warm；O8192；Target生产sampling；各1次 | 12 |
| Pi固定回放 | 冻结44个派生wire各1次；O32768；两条异常、分支、脱敏身份保留 | 44 |
| 状态/协议/容量 | 16容量边界+17协议/队列/断开+P32768/196608各5次append/branch/system+P196608的5次L2观察 | 48 |
| 合计 | core=110+16+48=174；专项=12+44+48=104 | **278** |

14个P为256/1024/4096/8192/16384/32768/65536/98304/131072/163840/196608/229376/245760/253952。O是预算而非必须生成量；length/耗尽不算任务完成。实际P、O_eff、cache条件、fingerprint、raw/指标与现行plans/05一致；正式core保持原argv，不启no-prefix-reuse。cold实际hit留gap，不为凑齐110而改参数或掩盖attempt。

已有service-cold、A/A、监控开销先按raw/hash/身份核对复用，不整套重跑。顺序冻结为两条Pi异常(O32768)→8工程各一次(seed1701)→2个外部repo若READY则执行；否则继续余下278并自动等待/执行external。外部未完成不得声称完整任务完成。旧记录按证据资格复用。44Pi不排在大合成矩阵全部完成之后。

有效旧记录只按预登记cell、wire、hash、采样、cache与环境条件匹配；固定取最早有效记录，不按速度/答案挑选。保留run/block、runner版本、重启与污染信息；损坏raw不可恢复者标INVALID_EVIDENCE，不计有效样本，不删除原件。若需要校准、暖状态准备或受控重试，全部另记实际请求，不隐入278结果数；预算变化须在发请求前写清。

278是首次工程参考覆盖，不是正式性能/尾延迟资格。缺项/gap列未完成；没有新候选时不宣称优化改善。B29没有round wall/真实ITL/可靠reasoning分项等字段时保留null+原因，不能通过增加旧版本请求补出不存在的计量。

## 2. 工程质量：初始8题×1+2repo×1，发布26/variant

先复用已有题面/工作区/隐藏judge，不再要求为凑20题而新造并逐阶段跑满。选定集：

| 来源 | 题目/ID | 初始用途 |
|---|---|---|
| 既有Pi三题 | idempotency、retry-contract、reconnect-loop | 历史锚点、工具/多轮/重试状态 |
| [QCB题库](../../qwen38-coding-benchmark-4090-v1.0.0/docs/03-task-catalog.md) | BF009、RE003、RE007、AT005、LC003 | 缓存失败污染、事务/outbox合同、稳定游标、SQL分句、较长仓库税额舍入 |
| 真实Java仓库holdout | 固定google__gson-2158与javaparser__javaparser-4561（SWE-bench Multilingual），commit/image与empty/gold gate预登记 | 跨文件、真实构建、干净环境补丁评分 |

初始8工程各1次，固定seed1701；2repo各1次；repo环境未就绪不阻塞先交付全P/已有题参考，记录REPO_NOT_RUN。最初trusted grader外层300秒的安排在已授权环境修复中改为外层450秒/容器420秒，完成Baseline实际按该值冻结；每repo编程1800秒(30分钟)、parent2400秒(40分钟)不变，提前完成立即评分。这是记录实际运行合同，不是本次评估修改现网参数，也不是官方50分钟标准。Pi逐请求O32768、24turn/60tool原限制不变；固定回放44条仍各40分钟deadline，构建/评分环境时间另记。正式发布8题×3固定seed+2repo各1次=**26任务运行/variant**，这不是26个HTTP请求；模型/工具轮次与全部实际成本另计。初始工程可使用首个固定seed，发布task/seed逐项配对，不以pass@3掩盖失败。RE003-v1的题意/隐藏trim不一致需版本化治理，不能把原FAIL改PASS或将修正oracle与v1直接配对。

撤回“20Java×3是通用工程下限”的要求。保留17合成业务合同与算术smoke作为可选诊断，不默认加入每阶段或发布集；内存MyBatis-like/outbox模拟不是Spring/MyBatis/JDBC/数据库集成资格。8题/3seed也不自动证明总体能力无退化或3个百分点非劣，报告逐题质量、失败、耗尽和CI限制。

QCB原runner不是Pi；复用资产须接入同一个冻结Pi scaffold、固定tool/system/reasoning/sampling/JDK/构建工具及scaffold版本/hash，不混合不同agent分数。真实repo选题先证明空patch失败、gold patch通过，冻结依赖与资源；不能按模型成绩挑题。agent只提交允许路径patch，重新应用到干净同版本repo并注入未修改测试评分；原工作区测试全绿仅供调试。该自定义2题只报内部结果，不报官方SWE-bench分数。

历史Pi A层固定请求不执行工具、不等于上述工程闭环。B层按各variant真实工具结果续接；保留O32768/medium，不通过强关reasoning/降预算使任务看似更快。长期能力按跨文件、工具反馈、持续上下文检验，不强制让模型空转到deadline。

## 3. 每阶段：相关合同+最多240个A/B相关请求

筛选候选集合至多P1024/32768/98304/131072/196608/253952中的6档、2类与改动相关负载、cold/warm、一个Target sampling profile、每版本5次配对观察：最大 `6×2×2×5×2=240` 请求，至少3个交错时间block。它是T1筛选，不是T2正式资格。若状态准备、warmup、重试或2个哨兵的模型调用需要额外请求，应预先从该阶段额度留出，减少有效格或记录明确的新预算；不能把hidden prep排除后仍宣称阶段≤240。数值/CPU合同和环境准备的工作量单列。

每阶段只测实际变更边界：

| 阶段 | 必测风险/主指标 | 避免的重复 |
|---|---|---|
| P1/P2 | tokenizer/template/cache改写、export/restore；prepare、computed/reused、TTFT、生命周期 | 所有O/所有解码风格 |
| P3–P6 | kernel/shape/codec/状态/容量；独立oracle与质量/资源 | 用大自然语言样本替代数值证明 |
| H0 | 计数/单位/失败负例、ID/schema关联、监控开销 | 反复请求B29索取不存在的新metric |
| H1 | 同宽Lookup有/无命中；delta-q与Target sampling；round/E2E/CPU查找 | 全业务×全部P/O |
| H2 | 词表映射/覆盖/中文碎片、确定提案、Target支持与head成本 | 盲加重复次数当覆盖 |
| H3/H4 | W/B/V、采样accept/processor、Graph/state、复制转折与3关键长P | 未启用/不采用宽度的全尾延迟 |
| H6/H7 | companion/ring、全局页/epoch/lateDMA、分布/状态合同与完整成本 | 资产未齐就预跑该路线 |

只把相关性明确的2个Pi/工程任务作为哨兵；它们若有模型调用也纳入预登记预算。硬数值/状态/协议断言不因性能额度减少而免除。明显错误/无收益停止该候选；一次预登记追加仍CI跨阈值则INCONCLUSIVE/不采用，不无限采到显著。失败调试记录全部保留，发布使用未参与调参holdout。

## 4. H5/H8发布：按实际声明profile做资格

仅H5/H8对拟发布profile集中做正式关键case≥10有效配对、至少5独立run block、p95桶/variant≥100请求以及必要CI；此前T0/T1不承担全量发布重复。每个gate先冻结metric、bucket组成/权重、比较对象、样本/追加预算、缺值与判定规则。没有100样本或CI跨阈值仍INCONCLUSIVE，100只是最低可估条件，不是5%差异的充分证明。

可选预算示例：P32768/131072/196608/253952×3非copy负载×35 warm/variant=420 warm/variant；配各自cold准备，A+B共1680请求。预登记三种长P各105个普通负载混合样本、每类非copy跨四P各140个样本可以服务多个已命名gate，但不能称每个P×每类都满100，也不能用copy权重冲淡普通负载退化。同case/block相关性、多重gate及CI要处理。

此示例仅是O512请求级TTFT/E2E/相应decode回归；不替代完整生成任务wall。copy完整补丁至少10配对/5block，工程8×3+2、Pi相应holdout保持原预算和质量判定。Target生产sampling是收益目标；Target-greedy仅数值诊断，不能混入sampling分母。若声明要求更多profile/每格任务p95，单独明确增加预算或缩小发布声明，不能更名偷换。

原业务TTFT/prepare/decode、长context、质量、容量与回滚阈值不下降。即使阶段有限额度已经用完，缺正式证据不能推广；可以完成研究、标NO_ADOPTION/INCONCLUSIVE，不能把“按预算跑完”写为性能PASS。

## 5. 执行、状态与时间

ROOT唯一管理旧任务排空停发、保留旧证据、新manifest/runner/analyzer/orchestrator、单GPU锁和监控/唤醒；文档worker不触远端或服务参数。新scope必须版本化，恢复时同时校验plan/runner hash、case选择与旧记录复用键；unknown inflight、durability、损坏raw等原规则保留。

core2–4小时、阶段小时级、发布约1–2天仅为预算规划，不是ETA或性能资格。Pi44×32768可能长时间耗尽，保留原每请求40分钟deadline并由试点更新预估；任务/数值/构建未测不可承诺完成时刻。脚本确认推进/故障/恢复后让出回合，由定时唤醒读状态，不主动频繁poll。实际状态以run证据为准，不因本页采纳而声称切换/请求已完成。

根据已完成B29对应cell复算：plans/07的48主请求试点纯请求约16.49分钟，计Pi/准备后首轮64请求规划1–2 GPU小时，整个≤240阶段规划3–6 GPU小时；原1680正式示例纯请求约20.77小时，加工程/评分/审计规划24–36小时，异常可超48小时。这些都是未来隔离实验估计，不是执行许可；候选构建、BO/P6先决资格及第三比较轴另计。原精简Baseline约7小时14分包含修复与等待，不能直接当下一轮纯推理预算。
