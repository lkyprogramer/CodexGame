# 18 · 风险、实验停止条件与投入控制

## 1. 最容易造成错误结论的风险

| 风险 | 检测证据 | 对策/停止条件 |
|---|---|---|
| Mac profile被当作CUDA支持 | CLI/loader/context能力表 | T02普通CUDA与T09预算分开；未资格仍拒绝 |
| 正式模型与varloop混用 | config、权重、template、draft hash | 新target身份，研究分支，不污染主线 |
| loop KV/conv误共享 | per-pass状态比较、SWA覆盖负例 | 停止性能优化，修复状态，重跑依赖测试 |
| DSpark feature或head错配 | 资产契约与per-visit记录 | 加载时拒绝，不能靠低接受率掩盖 |
| draft/tree挤出驻留权重 | NVML、ledger、H2D bytes变化 | 限宽/关闭spec或换合格profile，报告净影响 |
| 只测重复prompt造成100%接受率 | 原始prompt/accept分布 | 加入独立Java/工具/长ctx语料，holdout隔离 |
| q4容量收益伴随质量下降 | QC/long-context任务/工具门 | 单列target变更，不自动启用 |
| graph指向已回收buffer | generation key、event/lease测试 | 禁用相关图，修生命周期后重资格 |
| hidden/coda映射不清 | adapter状态定义与omega0测试 | LoopCD-Hidden保持BLOCKED |
| 2DSD实验runner与目标能力错配 | S44 registry/runner、资产与Atomic/SM89审计 | 公开runner已存在，实际适配/匹配drafter/资格缺项分别记录 |
| PCIe/SSD成本超过收益 | bytes/实效带宽下界、profiler | 优先驻留与减小工作集，不无限prefetch |
| 权限/数据/工具依赖缺失 | 显式错误与缺失清单 | 只阻塞受影响任务，其他已授权工作继续 |

## 2. 实验前先写可证伪假设

例：H-CORE：在受限显存profile中，静态core优先比同容量LRU降低device miss bytes并降低请求耗时；如果只是命中率变化但wall time没有改善，假设未通过。

H-GRAPH：目前关键路径至少有可观CPU launch空隙，复用固定图可减小该空隙并降低完整请求时延；如果kernel已饱和而gap很小，就不开发大规模persistent kernel。

H-SPEC：单位已commit token的完整spec周期成本低于AR；接受率本身不是判据。

H-KV：节约KV让选定长context/profile满足显存或减少搬运，且质量非劣；短ctx没变快不能否定容量价值，但不能称加速。

每个假设写入EXPERIMENT模板：目标、变量、对照、数据、资源上限、停止规则、预期机制与反例。

## 3. 停止规则

- 首个正确性失败就暂停性能计分，保存最小失败输入与state dump。
- 两轮有明确profiler因果证据的修正后，确认实验仍无净收益，标NO_BENEFIT；再次尝试需要新证据和新experiment_id。
- 公开实现/资产缺失标BLOCKED；可以完成不依赖该缺口的工作，但不能用不同模型替代后沿用Inkling结果标签。
- 内存最坏峰值超预算且没有已验证的回退路径，拒绝能力行；不能靠OOM重试选幸存样本。
- 未注册的量化/loop/KV/sampler组合保持UNQUALIFIED；严禁运行时猜测布局。
- 看过holdout才改阈值或筛样本，该轮作废并保留审计记录；重建独立holdout后才重新确认。

## 4. 前序已停止路线如何处理

此前Strata DFlash2正确但未比MTP spec4形成足够端到端收益；CPU pool/launch overlap等旧探索也存在no-benefit结论。这些不证明Inkling DSpark必然无益，也不授权照旧重新跑一遍。必须给出不同模型/不同瓶颈/不同实现的新证据，才重开相应类别。

不要把旧模型75tok/s或NInfer约149tok/s当作Inkling的同条件目标。不同tokenizer、质量、上下文、工具链与任务长度使这些数字不能直接比较。当前生产对照在T00/T03重新冻结。

## 5. 范围与投入

第一轮只完成正式模型主线的基线、容量、完整状态和原生投机。新量化训练、2DSD适配蒸馏、大型多卡训练、全后端重写不在MVP关键路径。若需要付费云卡或重新训练草稿器，先交付具体数据/资源计划与已证实阻塞，再由实际会话授权；本包不预授权费用。

持续维护成本也进入决策：每项优化记录新增代码/依赖、需要维护的shape/type组合、fallback覆盖与测试时长。为1%孤立微基准收益引入大量不可测试分支，应拒绝。

## 6. 不确定性分类

- **源代码事实**：固定commit可核对，未来变化不自动更新结论。
- **作者实验**：保留原硬件/精度/工作负载/过滤条件，只作候选依据。
- **工程推断**：如PCIe Gen3应优先全驻留，必须用本机profile验证。
- **策略阈值**：5%/10%性能和非劣门等是本包选择，可在看数据前修订并留记录。
- **未执行项**：永远NOT_RUN/BLOCKED；没有数字就是没有数字。

## v1.2：自动搜索与新后端停止条件

新增风险：preview前端错误、证明范围误读、ABI/host前提遗漏、graph持有已卸载module、异步lease过早释放、动态MoE索引未经真实producer保证、arch skip冒充实跑、搜索赢家偏差和旧hash资格复用。针对性负例见AX；不能用scoped proof替代原状态/质量/资源测试。

编译/证明受外层时间与内存额度约束；UNKNOWN/超时不当PASS。目标机不支持某编译组合只阻塞该路线，原CUDA C++继续可用。最多两轮有trace依据的修正、累计候选预算用尽即按实际原因结案，不以换语言/工具重新计数。

K07独立backend需要真实相邻op/布局/分派关键路径、现有ggml接口的具体限制和完整维护预算；按28的P0–P3推进。单kernel微基准或B200算力不足以开启重写，K07不因K06无收益自动开启。历史无收益路线仍须新的Inkling证据与DECISION。

## v2主要新增风险

1. 平均压缩率被误用作最坏容量；raw overflow、尾块、metadata和prefill临时副本抹去收益。
2. KV恢复正确但conv/control/next-logit或RNG/工具状态不完整。
3. graph地址稳定但record map在reader完成前被覆盖。
4. GAAC等窄后端错误接受Inkling真实scale/mask/softcap/spec。
5. 分层prefetch和Codec后台工作争抢专家搬运，微基准快但Agent更慢。
6. R03旧阻塞虽撤销，但研究asset、诊断脚本和Humming资格被错误继承。
7. Magnitude的量化codec/自动调优或并发目标被直接套为Atomic/Q8/单active路径。

每项有L/M任务与LX/UX/MX用例；失败按原两轮有trace的修正上限结案，不以重写backend规避NO_BENEFIT。
