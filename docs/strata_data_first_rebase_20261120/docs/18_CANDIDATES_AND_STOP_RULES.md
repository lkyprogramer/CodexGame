# 18｜候选、证据资格与停止规则

## 1. 结论与排序

当前**零项已获得GPU算法实验资格**。C01/C02只是数据到位后可回答的两个新问题；两项可以做离线分析，不同时开启在线改造。P0–P3的采集交付独立有价值，即使最后所有候选均NO_GAIN。

本章max(4%,2×AA)指完整门。若缺同一新版R身份的独立正式AA，不设AA=0：乐观上界<4%可直接淘汰；≥4%且其余必要证据齐备也只能CONDITIONAL_AWAITING_AA。最多一个单项可申请P5.0独立测噪，重算完整门后才讨论原型/AB，详见19。

| ID | 当前状态 | 新差量 | 首个允许动作 |
|---|---|---|---|
| C01 | CONDITIONAL_OFFLINE_ONLY | Speedy新增8-gram索引恢复被trigram 4-way覆盖的旧长匹配 | 受限同会话token trace离线回放 |
| C02 | OBSERVATION_ONLY | Poly提出的真实行分布/physical padding审计，针对新版actual route | 按实际launch做census，不重分组 |
| O01 | DATA_REQUIREMENT | harness/HTTP/native queue与父前缀物理恢复 | P1/P2事件关联，不预设cache算法改造 |
| O02 | DATA_REQUIREMENT | ready-hit与pending-copy、CPU/DMA共享瓶颈、RAM/SSD真假I/O | 分母与依赖采集；不重跑旧lending/PCIe |
| FQSA | COMPATIBILITY_ONLY | FlashInfer main API与当前KV/布局是否有交集 | 文件/shape兼容卡；不下载/切格式 |
| BLINK | OUT_OF_SCOPE_IMPLEMENTATION | 控制面隔离思想 | 只吸收事件/ownership，不DPU/GPU-free移植 |
| D1/H2/K-PAIR/M0 | RETAIN_PRIOR_STATUS | 11/15原source-delta卡 | 不改旧结论，不冒充已执行；见02 |

## 2. C01｜suffix 二级索引的离线反事实

### 机制与旧路线区别

旧H1/NInfer ngram、Strata lookup-chain2和窗宽扫参已经有负证据。这里不是“再加lookup”，而是在**最新Strata已有lookup**中查明三元组四路桶是否丢掉实际有价值的更旧来源；Speedy多一张8-gram索引能否找回。

源码：[Speedy suffix](https://github.com/DevDock-AI/Speedy/blob/7d500de0067f8fb31a9da1fbef16a303f790dacc/src/spec/suffix_drafter.cpp)，[Strata当前suffix](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/src/spec/suffix_drafter.cpp)，[Strata DraftPolicy](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/src/spec/draft_policy.cpp)。完整边界见 [14](14_DONOR_SPEEDY.md)。

### 必要输入

- 同一run/corpus的prompt+已提交历史token，合法使用与私密保存；当前时刻不能访问未来token。
- 实际trigram表容量/重置/淘汰、窗口政策、可选源与实际chosen；无这些不能说“本来会采用”。
- 验证成本按context/width/route与当前缓存状态，rollback/catch-up、CPU索引cost/RSS。
- copy/edit与non-copy任务预登记权重；不是只有人工碰撞夹具。

这些输入必须来自已有且获许可的W09原件，或在P3-CASE同一1引擎/6请求上限内**替换**成W09并另获内容采集许可。普通L1摘要没有完整token序列；缺原件就INSUFFICIENT，不默认开全量SPEC_TRACE、不额外启动模型。proposal构造只读当时可见前缀；事后比较已录未来答案仅用于oracle上界，不反馈给proposal、不算在线accepted。

### 输出

`eligible_steps, collisions, long_source_evicted, recovered_matches, match_len_hist, current_policy_would_choose, oracle_extra_commits, measured_accepted_if_available, added_lookup_cpu_ns, index_peak_bytes, verify_rows, offload_bytes_estimate, net_upper_bound`。

从未执行的target验证不能填measured_accepted。oracle只用作“即使全部理想也不值得”的淘汰上界，不能批准性能PASS。

### 前进条件

碰撞确实频繁、真实policy会选择、扣除新成本后的乐观空间仍超过 `max(4%,2×AA)`；同时有独立机制、same-session安全、greedy/采样状态/restore边界方案。若baseline禁lookup，停在离线研究，不为此打开线上开关。复制Speedy自有代码前核非商业许可；默认只独立实现思想，不视其全仓MIT。

### 停止条件

旧来源损失稀少；大部分proposal被现有policy拒绝；只有合成复写有效；新增CPU开销在non-copy吞掉收益；无法保持exact/采样合同；或上界不足。结论分别为NO_MECHANISM、NO_HEADROOM、NOT_APPLICABLE或STOP_CORRECTNESS。

## 3. C02｜实际 MoE padding census

### 机制与旧路线区别

不是再做F02 GU/TG21，也不是F05 scratch或P24 retained expert。先量化新版native prefill实际group内的行分布及padding；看看还有没有**当前已选tile/route没有吸收的浪费**。

源码与反例：[Poly #149](https://github.com/simplexai-labs/PolyStrata/pull/149)、[Poly NVIDIA数值边界](https://github.com/simplexai-labs/PolyStrata/blob/3e1642161198c50ff1abed4046f4e4f476099dbb/docs/DETAILS.md#L2515-L2555)、[当前Strata fused规则](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/include/strata/prefill/fused_tile_rule.hpp)。见 [17](17_DONOR_POLYSTRATA.md)。

### 必要输入

实际prefill route、quant/architecture、resident/staged分组、每expert真实rows、issued/padded rows、tile/grid、launch次数、kernel/time依赖、host分组/transfer等待。logical最大行数不能替代物理grid；没有准确grid分母就不报padding百分比。

### 可证伪计算

有效行比 `actual_work_rows / issued_work_rows` 只是工作量。去掉所有padding只是数学乐观极限；若内核DRAM/host/DMA受限，实际省时可接近0。必须联结其暴露完成路径，扣额外launch/group/table和失去overlap。

NVIDIA stream-k按tile数量决定切分，donor分组可能改变累加顺序；已有token分叉证据。**不直接把该实现纳入exact候选。** 只有设计出保持现行必要数值顺序/等价合同的方法，且source delta明确，才从“观测”升级“候选”。

### 停止条件

当前fused已解决同问题；真实路径不走对应MMQ/fused；padding不在关键路径；最高可能省时不足门槛；仅通过增大chunk/改量化获得变化；保持exact需要代价抵消收益。停止不启动tile网格搜索。

## 4. 条件性问题，不预排算法项目

- 真的出现idle parent被驱逐：先确认rendered prefix未变、owner与tier、池容量和scheduler；不能直接移植Poly PIN，因为它仅strata-poly且分段prefill本身可能改变输出。
- 短追加TTFT明显在SSE delivery：可研究flush/socket/缓冲与client边界，但不是GPU tok/s项目。Speedy TCP_NODELAY测试只证明设置存在。
- malloc RSS异常：先区分module/NVRTC重试、pinned pool与allocator；不照搬arena cap。
- CPU/DMA随负载漂移：先对齐估计/实际ready/wait与DRAM争用；Flywheel的“命中”不等于真正热命中。
- PLE/Engram：明确实际io mode/admission与物理读取；不靠名称或系统IOPS推根因。
- Kinetic树：default chain；未计量额外verify rows、共享前缀、rollback和状态资源前不立项。

## 5. 重开旧路线必须提交的证据

`old_id + old_verdict + donor_commit/symbol + target_route/signature + semantic_delta + why_old_evidence_does_not_apply + observed_sink_dependency + resource/correctness_bound + new_contract_id + finite_budget`。

缺任意关键项仍为DEFERRED。新版源码原生化可以支持重做**测量**，不能单独支持重做所有**优化**。已存在上游的项仅验证实际生效，不再实现一遍。

