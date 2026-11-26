# Atomic Engine × Inkling × RTX 4090 完整工程执行包

**版本：2.1 · 2026-11-26（Asia/Shanghai）**  
**44篇专题、44个任务、148项计划验证；另含机器合同、来源锁、辅助工具和交付检查。**  
**交付：完整设计与AI实施输入。目标推理引擎尚未在本轮实现或测量。**

## 这次重新组织后的主线

以Atomic为底座，正式Inkling-2-Mini固定R3为主力候选，在单RTX4090 24GB、64GB RAM上优先建立正确、可恢复、可计费的CUDA服务，再沿真实瓶颈优化。历史Xeon Silver4216、PCIe Gen3和SSD约600GB由T00重新确认；不能据历史配置决定实际带宽或容量。

这份完整包吸收Atomic、Ghost、squid5090、原生DSpark、2DSD、PR51161、LoopCD/ARLoop、CUDA Rust及安全证明文章、LoomKV、GAAC/SplitZip/ZipFusion/ZipServ，并加入Magnitude。项目以机制进入同一个状态/资源/资格架构，默认不启用全部特性。

**建议从[00 总体计划](docs/00_integrated_master_plan.md)开始。** 执行核心顺序是：

1. 机器/资产/正式R3普通CUDA与质量基线。
2. 完整状态事务、统一物理账本与reserve-before-advance。
3. 原生DSpark固定宽度、profiler驱动的SM89局部kernel。
4. 完整会话raw Tier对照，再做RAM/SSD无损编码。
5. 若真实瓶颈成立，选择专家驻留/预取或GPU压缩Pool。
6. 组合实验、Java8/Pi完整任务、长时间服务和可审查发布候选。

## 本版关键判断

- **LoomKV Tier和Pool分开。** Tier保持GPU原表示，优化RAM/SSD与恢复；Pool改变GPU页和Attention。前者不释放活动GPU KV，后者不能靠codec逐bit恢复就宣称最终输出逐bit一致。
- **实际表示优先。** Q8_0、F16、BF16、FP8、affine/rotated KV是不同合同。不能把BF16的0.71比例套给现有Q8，更不能先增大为BF16再称节省显存。
- **缓存必须完整。** KV、SWA、逐loop conv、必要控制/draft状态、cursor和next logits一起决定续接资格。对象编码、完整checkpoint、活跃GPU lease分别建模。
- **Magnitude是推理引擎。** 重点借鉴一个物理store一份账本、DMA/最后读者退休、有界预取、因果路由回放、CostEpoch和被动观测。当前没有Inkling family适配；其专家SSD路径不证明完整会话SSD恢复。
- **纠正2DSD旧判断。** `feat/inkling-dspark@962874f…`已有公开实验runner；旧版漏查，R03由BLOCKED改为NOT_RUN。正式Mini匹配drafter、Atomic适配和SM89仍需资格。
- **v2.1：mainline llama.cpp已能运行正式Mini。** b12751作为T02跨引擎oracle和回移植来源；Atomic `fb69fff`已确认缺#32799分词等4项上游修复。128K在4090上的首要约束是attention相对位置bias（稠密回退vs #33063），不是权重；IQ4级+Q8 KV预计可全驻留。DFlash2作为T06扩展。4090只读现场与停服窗口见[43](docs/43_upstream_llamacpp_4090_site.md)。
- **CUDA Rust更新单独保留来源链。** 当前S45为`f35d6ccc…`；原141文件详细审计仍绑定历史S22，不能把旧proof/CI迁移成新版本证据。4090不使用TMA/PDL/TMEM/tcgen05等更高架构路径。

具体事实和固定链接见[02](docs/02_evidence_register.md)、[22](docs/22_integration_matrix.md)、[33](docs/33_lossless_source_audit.md)、[40](docs/40_upstream_refresh.md)、[41](docs/41_magnitude_source_audit.md)。所有作者数字和外部CI均与目标机测试隔离。

## AI执行入口

先读[AGENTS](AGENTS.md)、[00](docs/00_integrated_master_plan.md)、[01目标合同](docs/01_product_contract.md)、[05架构](docs/05_architecture.md)，再按[机器DAG](manifests/task-graph.json)选择任务。T/R/G/K原ID保留；L00–L07负责缓存，M00–M03补充Magnitude机制。共用ledger、状态和证据接口只实现一次；可选任务不全部变成T12前置。

可交给工程代理的起始指令：

> 以本目录AGENTS.md、docs/00和目标合同为准。先做文档包自检，执行T00只读调查并锁定资产和版本；之后按task-graph逐任务实施，始终区分任务完成、能力资格和生产授权。对所选机制建立能失败的状态/数值/容量测试，保留原始数据，再进行单变量性能比较。L01/M00共用一个ResourceLedger；无实际瓶颈不做预取或Pool。每项交付代码、测试、原始证据与DECISION；对可逆且已授权的工作持续推进。真实访问、权限或产品范围阻塞时写明具体缺项，不伪造PASS、不放宽guard或阈值。

包内可直接运行`tools/preflight.py`、`tools/paired_stats.py`和`tests/test_tools.py`。文中`tools/inkling-lab/lab.py`、CacheManager、Pool/provider、M hooks均是对应任务未来要实现的路径，**不是此包现有推理能力**。本轮可复查结果与命令见[VALIDATION](VALIDATION.md)。

## 文档导航

| 阅读组 | 文档与用途 |
|---|---|
| 总体决策与证据 | [00总体计划](docs/00_integrated_master_plan.md) · [01目标](docs/01_product_contract.md) · [02证据](docs/02_evidence_register.md) · [03资产](docs/03_model_assets.md) · [22融合矩阵](docs/22_integration_matrix.md) · [40版本纠正](docs/40_upstream_refresh.md) |
| Atomic主线 | [04硬件](docs/04_hardware_memory.md) · [05架构](docs/05_architecture.md) · [06 CUDA移植](docs/06_atomic_cuda_port.md) · [07投机](docs/07_speculation.md) · [08 SM89](docs/08_sm89_kernels.md) · [09长上下文](docs/09_long_context.md) |
| 循环研究 | [10 last-loop](docs/10_last_loop_kv.md) · [11 2DSD](docs/11_2dsd.md) · [12 LoopCD/varloop](docs/12_loopcd_varloop.md) |
| 实施与验收 | [13正确性](docs/13_correctness_quality.md) · [14统计](docs/14_benchmarks.md) · [15原任务](docs/15_tasks.md) · [16手册](docs/16_runbooks.md) · [17服务](docs/17_rollout.md) · [18停止规则](docs/18_risks.md) · [19来源许可](docs/19_provenance.md) · [20验收](docs/20_acceptance.md) · [21提示词](docs/21_agent_prompts.md) |
| Ghost机制 | [23源码](docs/23_ghost_source_audit.md) · [24迁移](docs/24_ghost_transfer_design.md) · [25 G任务](docs/25_ghost_tasks.md) · [26 GX验证](docs/26_ghost_validation_runbook.md) |
| 自动底层优化 | [27 CUDA Rust/证明](docs/27_cuda_rust_source_audit.md) · [28后端](docs/28_custom_backend_architecture.md) · [29受限搜索](docs/29_automated_kernel_optimization.md) · [30算子](docs/30_sm89_kernel_program.md) · [31 K任务](docs/31_kernel_tasks.md) · [32 AX验证](docs/32_kernel_validation_runbook.md) |
| 完整缓存系统 | [33论文/codec审计](docs/33_lossless_source_audit.md) · [34状态/格式](docs/34_cache_state_contracts.md) · [35 Tier](docs/35_tier_cache_design.md) · [36 Pool](docs/36_compressed_pool_sm89.md) · [37资源协同](docs/37_unified_resource_policy.md) · [38 L任务](docs/38_cache_tasks.md) · [39 LX/UX验证](docs/39_cache_validation.md) |
| Magnitude融合 | [41源码/分支](docs/41_magnitude_source_audit.md) · [42 M任务/测试](docs/42_magnitude_integration.md) |
| v2.1上游与现场 | [43 mainline刷新/4090现场/窗口命令](docs/43_upstream_llamacpp_4090_site.md) |

机器材料见[manifests说明](manifests/README.md)，执行记录模板见`templates/`。Schema能拒绝部分无效结构，但不能验证GPU真执行、实际hash、事件寿命、抽样独立性和授权；这些需要后续语义验证器与真实证据。

## 冻结的验收原则

单项优化请求中位数减少≥5%，主力迁移真实任务中位数减少≥10%，配对95%CI支持正收益；关键分层p95退化≤5%并满足绝对SLO。质量以150个Java任务、300个工具案例的预注册非劣界限验收；soak至少8小时且200请求。精确门槛以[validation-policy](manifests/validation-policy.json)为准，本版没有降低。

初始单活跃GPU生成、VisionOff，性能实验全局串行。G04/K07仍DEFERRED；R03和新增L/M任务NOT_RUN；148项计划测试全部NOT_RUN。T12产出可审查服务候选，G7是否获授权由当时实际执行会话决定。包检查通过不能解释成4090性能、128K能力或生产就绪。
