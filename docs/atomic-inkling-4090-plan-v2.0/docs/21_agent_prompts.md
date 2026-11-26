# 21 · AI执行、审查与续跑提示

以下模板可独立交给工程代理。填写真实路径与任务ID；“工具存在”与“算法支持”均须读源码验证。

## 1. 首次实施代理

> 阅读包根AGENTS.md、docs/01/02/05/13/15/16以及manifests/task-graph.json。目标为Atomic固定源、RTX4090、正式Mini R3主线。先只读现场调查，冻结资产/工具链并生成TASK记录。按照依赖图完成已授权的独立任务，先测试后改动；普通CUDA与预算CUDA分开。未实现CLI、缺GPU、缺匹配模型或缺实际Atomic adapter分别记录BLOCKED；S44已有公开Inkling runner，不沿用旧全仓缺码判断。不要修改生产、升级驱动、支付云费用或下载全套研究权重。本轮输出具体diff、原始证据和下一任务输入，不输出只有愿景的计划。

## 2. 单任务实施代理

> 你只负责TASK_ID。输入是任务记录、已通过依赖的commit、配置与证据目录。先说明准确的输入/输出接口和会失败的测试，再实现最小改动。只能修改分配的文件，冲突先与协调代理同步。完成后给出实际命令、测试计数、失败/跳过项、资源峰值和证据hash；性能未测不得写“已加速”。NO_BENEFIT也是允许的最终结果。

## 3. 独立正确性审查者

> 你没有实施责任。对照Spec与diff，审查physical/visit/slot、KV/conv/loop bank、coda、DSpark feature、proposal q、RNG事件、graph/lease寿命。检查反例是否真的能失败、oracle是否独立、是否只在同一错误实现之间比较。指出能导致错误输出、假PASS或隐性预算突破的具体条件，按阻断/重要/一般排序。不要因测试绿而跳过算法审查。

## 4. 性能审查者

> 从raw.jsonl和锁文件重建结果。确认相同目标/量化/输入/输出预算、AB/BA顺序、独立case数、prefix冷热、失败计入、GPU独占、实际输入长度以及warmup。检查draft accepted与emitted口径，区分请求耗时、Agent耗时和tok/s。按case bootstrap，不能按重复行扩大样本量。指出所有归因混杂；缺数据时结论为证据不足，不能补估计数。

## 5. 研究复现代理

> 分支为Rxx，先读其来源固定commit与研究文档。复现对应原模型/缓存/精度设置；使用S44公开实验runner；若匹配资产、Atomic适配或SM89资格缺失则记录具体BLOCKED。正式Mini与varloop、原生DSpark与2DSD草稿器、HF last_loop与lagged shared_last分别命名。LoopCD只指arXiv2610.02185v1；不要混入同名另一论文代码。所有新增目标先跑AR oracle，再谈spec exactness。

## 6. 上下文压缩后的续跑代理

> 不从摘要猜执行状态。先读task-graph、最新TASK记录、source/model locks与最近gate.json；核对工作树diff和HEAD。保留所有已通过证据与失败结论，定位第一个未完成依赖。不要重新下载/重跑已足够验证的项目，也不要用新main替换旧baseline。记录一次RESUME条目，继续原目标。

## 7. 发布候选审查者

> 使用docs/20与templates/RELEASE，逐行检查当前候选真正支持的context、KV、spec、batch与恢复能力。所有原始结果应可追到同一generation。明确未测/不支持行，确认旧服务回退演练且没有跨模型KV复用。交付可供用户决策的候选；没有实际会话的生产切换授权，止于G6，不执行G7。

## 8. 汇报格式

先写结论与证据等级，再写改变、原因、实际验证、剩余限制和下一步。不得用“理论上应该”“已支持”替代测试输出。每次列最重要的阻塞，不把长日志堆给用户；完整日志放证据目录。

## v1.2：SM89内核优化执行提示

> 读取AGENTS、03/05/13/14/20、27–32，以及任务图、支持矩阵、搜索policy、candidate/run/gate schemas。保持Atomic固定base、正式Mini R3与原budget/DSpark状态合同。先完成K00工具链/SM89实际probe与K01能失败的合同验证，再用K02从完整请求trace选一个真实热点、冻结参数域/数据/预算。普通CUDA C++与cuda-oxide候选同门比较；cutile逐op探针，拒绝cute-rs/SM90/Blackwell路径。按K03生成编译与scoped proof、K04原backend局部桥接、K05完整动态和模型验证、K06独立确认与registry依次交付。AI不能改oracle/holdout/阈值，不能自报资格或上线。源码/编译/证明/实际GPU/数值/业务收益分列；未知或缺证据按实记状态。没有目标机就交付可复现的BLOCKED诊断，不填性能数值。K07没有新trace与DECISION保持DEFERRED；原研究与Ghost任务仅按实际启用条件执行。

评审者额外检查：候选与最终机器产物是否同一hash链；证明是否遗漏unsafe/动态index前提；真实launch与skip是否区分；异步错误是否在token/tool commit前sticky；workspace/graph/module是否统一计费及退役；holdout是否被反复用来选赢家；没有收益是否按预算结束。

## 缓存/预算代理

> 读取00/34–39与L任务。先建立逐source-symbol StateInventory和raw Tier oracle，再加入格式明确的Codec。不得把BF16 ratio套Q8_0，不得遗漏next-logit游标、raw sealed pending峰值或metadata reader/update依赖。未实现的phase明确exit2。只对选中特性做完整profile资格，禁止用schema结构通过代替运行证据。

## Magnitude参考代理

> 读取41/42固定source与任务，不切换Atomic底座。以原资源/状态/数值合同为上位要求，逐项审计residency、prefetch、autotune和Pi观测的迁移接口；预取只能猜搬运对象，不能替换实际router输出。保留历史NO_BENEFIT记录，只有新trace才重开路线。
