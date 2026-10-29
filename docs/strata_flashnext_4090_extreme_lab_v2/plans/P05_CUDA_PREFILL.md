# P05：RTX 4090 的 CUDA / prefill 主线实施与验收计划

执行基线最终刷新为`4b9e05a2a806a3fe24f7b2560d98626c37dade35`（v0.2.6）；本文41cf固定实现锚在相关文件中未变，见[最新差异](../sources/FRESHNESS_DELTA.md)。
本计划是可交给 AI 实施者的设计和测试合同，不表示已经修改、编译或运行引擎。主线源码固定为 `41cf05a06a25dd29103b7b27a2279a3f60c21876`；生产对照保留 v0.2.3 `5c8dd322528cc84f68f461ad54a506b9da8fa8d4` + EXACT6。实际模型为 **GSQ-RCO IQ3_XXS**，不是 IQ3_S，也不是 NVFP4。硬件是 RTX 4090 24 GB、Xeon Silver 4216、64 GB / 约 36 GB/s DDR4；模型逐层类型和实际矩阵必须实机导出后再定 kernel 组合。

主目标有三类，分别计收益：减少 scratch 使更大的 prefill chunk 或更多 resident experts 可用；缩短现有 CUDA GDN recurrence；按实际 IQ 矩阵与路由分布改善 MMQ / fused kernel。它们不一定提高稳态 decode，必须分别报告 TTFT、完整请求时间和后续 decode。

## 1. 三条路径的状态与平台资格

| 路线 | 当前状态 | 4090 的关键判断 |
|---|---|---|
| PR #4039 group scratch / HC region | **open、未合并**；head `c4dd0af3cb78cf8bc4c33df5ed279de5578168d6` | 先适配最新代码及实际 mixed-format；作者8GB卡收益不外推 |
| `STRATA_GDN_CHUNKED=1` | **主线已有** CUDA FP32 32-token chunk | sm80+、默认至少128SM、约93.7KB shared/block、T≥128、scratch约25.6MB；必须确认实际分支与资源检查 |
| `STRATA_PF_FUSED=1` / native fused IQ | **主线已有 opt-in** | Ada可试，主线默认启用资格主要针对特定sm120/GFX；实际GU/down类型与Hadamard决定覆盖 |

`STRATA_GDN_CHUNK` 是另一个独立 Volta 实验实现；AMD 的 WMMA chunk 又是另一实现。不要混淆开关、精度、资源门槛或测试。

4090 的 sm89 路线不包含 Hopper thread-block cluster、sm90 PDL、TMA/WGMMA 或 Blackwell 原生 FP4 MMA。Ada 可使用当前源码适用的普通 CUDA、cp.async、FP16/BF16/int8 矩阵路径；具体版本/编译支持以实际 toolkit、CMake 与deviceattrs为准。用户已试过的Ada默认表、IL0/IL89无收益不作为新任务重复扫描。

源码：[prefill.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/prefill/prefill.cpp#L1573)、[CUDA GDN_CHUNKED](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/prefill/kernels.cu#L866)、[fused IQ支持](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/prefill/moe_fused_iq.cu#L1391)、[PR4039](https://github.com/Niko1221/Strata/pull/4039)。

## 2. PR4039 的实际改动与未解决风险

### 2.1 group scratch 的合同

PR新增的 `STRATA_PF_GROUP_SCRATCH=1` 把 `GU`、`H`、`Hq` 从整chunk的 `T*K` 行缩小到一个group可用cap；`Xq`、最终 `Dm` 等仍保留整chunk范围。默认 `MMQ_GROUP=16`、`K=10`、`n_expert=512`，cap由 `T + 3*(T*K*16/512)` 向64行对齐，约1.9375T；测试开关 `STRATA_PF_GROUP_CAP` 会钳制到至少T，因为一个合法expert每token最多路由一次，所以单expert最多T行。

超过cap的group按expert子范围执行GU→SwiGLU→H量化→down，输出落回原 `Dm` 行范围。空expert/空子范围必须跳过但不改变其他row映射。

实际资格比“支持MMQ”更严格：

- `mp.any` 且每层 `mp.layer` 为真；没有FP16fallback，也不能使用 `pf_wmma` 的FP16 buffers。
- 当前patch拒绝任意 `mp.direct`，因为 `STRATA_MMQ_DIRECT` guard tables按wholegroup组织。
- `run_impl` 若真实分支进入fused或非MMQ，必须拒绝或在执行前安全回退到原全尺寸布局；不能让缩小buffer继续写 `T*K` 行。
- `bytes_needed_impl`、`carve`、`moe_bufs`、host/devicebounds容量、relayout必须使用同一计划；原patch仅在两个文件中增加逻辑，测试覆盖需另补。

### 2.2 “相同kernel”不自动保证4090按位一致

`mmq::Context::run` 把 `Product.n`、`max_rows`、`total_rows` 传入底层MMQ调度。PR拆group会改变这些参数。主线 `mmq::whole_tiles` 已专门证明/排除stream-k是否会拆K；头文件明确指出108/128SM的部分少tile情况无法保证whole-tiles，GPU会用stream-k不同切分。

因此 **PR对“same bits”的描述须在4090强制触发subrange后重新验证**。出现差异时必须先排除索引错/越界，再判断是否仅为FP32规约顺序。处理选择：保持原wholegroup计算调度；限制为能证明whole-tile不变的形状；或明确升级为数值容差档并做质量评测。不得静默把bitexact测试放宽。

证据：[Product与whole_tiles合同](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/include/strata/prefill/moe_mmq.hpp#L75)、[Context::run](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/prefill/moe_mmq.cu#L417)、[whole_tiles实现](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/prefill/moe_mmq.cu#L526)。

### 2.3 pointer origin 必须显式审查

PR使用 `gu.dst = m.GU - ra * 1280` 把绝对row写入局部scratch。虽然GPU实际访问可能回到合法范围，host端构造allocation之前的C++指针存在对象边界语义问题，而且后续任何调度修改都容易让错误写域不被察觉。

建议拟新增显式 `dst_row_origin` 或局部row映射来表达 `dst[(absolute_row-origin)*ld]`，并在launch前检查最小/最大地址。这个field **不是主线现有Product成员**；实施者必须连同MMQ wrapper / mirrored实现一起审计，不能只在struct加字段却忘记底层kernel使用。若改动面过大，可用独立安全wrapper形成局部索引，但必须证明它不改变原求和调度。

### 2.4 HC region 复用

PR的 `STRATA_PF_HC_REGION=1` 在 `!gr_unfused()` 时，把 `xn16`、`lo`、`lo16`、`gated`、BF16x2的 `xn16_lo / lo16_lo` 并入 attention/MoE共享region。原主线已经让GDN、QSA、MoE scratch共享 `max(size)`，PR只是增添第四个互斥集合。

正确性依赖实际先后：HC read完成得到 `mixed` / `inj` 后，该半层attention或MoE才开始写region；attention/MoE最后读者完成后，`gr_write_norm_rs` 才能把下一半层 `xn16` 写回region。同一stream可建立顺序，但copy stream、CPUshare、peer/helper、PLE批处理、MTP draft_kv复用region、fused write条件都要明确生命周期，不能只靠注释假设。

## 3. 内存所有权与生命周期表

| 对象 | owner / 写者 | 最后读者与可复用时点 | 不能做的事 |
|---|---|---|---|
| `Prefill::Impl::region` | 当前Prefill实例；owned allocation或borrow loan | 当前half所有compute reader、异步子路径均完成后 | 活跃verify图仍用这些借出的expert slots时重carve |
| HC scratch集合 | `gr_norm_rs`、down/up/mix、fused write，主compute stream | `mixed`、`inj`产生且所有projection读取结束 | 保留旧 `xn16` 指针给异步reader后让QSA/MoE覆写 |
| GDN scratch | qkv/conv/gates/recurrence/outputprojection | GDNoutput projection与state更新结束 | 把长期GDNstate一起放入可覆写region |
| QSA scratch | Kc/Vc/Q/score/selection/attn | KVappend/copy依赖与attention/outputprojection结束 | 覆盖仍由kv_copy stream读取的K/V源 |
| MoE `GU/H/Hq` | 每group/subrange按同一compute stream更新 | down完成读取该Hq之后 | 下一group先写H而上一group down还未读完 |
| `Xq` | 整层activation quant/scatter | 所有expertgroup GU完成 | 按group缩小它却仍用全局bounds |
| `Dm` | GPU down及CPUshare回传 | 最终combine完成 | 缩小到一个group导致先前expert输出丢失 |
| `grp_gu/grp_d` | gather/copy stream与guard准备 | 对应group最后product读完、used event记录 | 未等待used event就让issuer覆盖slot |
| bounds / maps | CPU grouping→mapped/pinned upload→GPU | 当前group products/scatter完成 | host重写下一layer表时GPU仍消费 |
| KV、GDN、PLE会话状态 | `SessionState` | 按引擎commit、checkpoint、park/restore合同 | 将persistentstate计入“可节省scratch”或随relayout覆盖 |
| verify/MTP CUDA graphs | Verifier/MtpDrafter | graph持有的device地址在其生命周期内稳定 | prefillscratchrelayout后让图继续引用旧地址 |

`Prefill::relayout` 当前同步 `m.cs`、`m.copy`、`m.kv_copy` 并拒绝hybrid borrowed/owned spill。新增复用必须保持或加强此合同，若发现更多reader应补对应event/owner；不能直接删除这些同步来制造微基准改善。[主线carve/relayout](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/prefill/prefill.cpp#L1573)

## 4. P05 任务拆分

### P05-01：固定实际shape、资格与计量口径

**输入**：模型hash、native层manifest、生产CLI/env、main SHA、PR4039 head。**输出**：`prefill_manifest.json`、每层GU/down类型、shape、tail/Hadamard、MMQ/fused/fallback/direct选择与actualchunk、deviceattrs、scratch分配账。

已有形状默认GU `[1280,2560]`、down `[2560,640]`，但必须确认实际模型格式与布局；不要从IQ3_XXS包名推断所有层统一格式。记录 `mmq::fits` 与 `native_supported` 真正返回值。显式关闭profile重同步和自动策略，验证首次库初始化不进入steady统计。

**现有源**：`mmq_plan`、`fused_layout`、`moe_bufs`、`Prefill::bytes_needed_impl`、`native_supported`。**拟新增**：一次性debugmanifest导出，不是生产热路径log。**停止**：任何层身份/格式不明或silentfallback，先解决，不继续性能结论。

### P05-02：提取可验证的scratch计划

**现有源**：`Alloc`、`gdn_set_bytes / qsa_set_bytes / moe_set_bytes`、`Prefill::carve / bytes_needed_impl / relayout`。**输入**：T、formatplan、f16/bf16x2、src/borrow、maxcontext、sel/attnbatch。**输出**：各buffer offset/capacity/aliasgroup与峰值；所有加乘用检查过的size类型。

**拟新增结构**：`PrefillScratchPlan`、`BufferSlice`、`ScratchLiveRange`；可以先仅供测试，避免大范围重构。count-only与真正carve必须调用同一计划或逐项核验一致。

**拟新增 tests/targets**：`tests/prefill/scratch_plan_test.cpp` / `prefill_scratch_plan_test`。覆盖T0/1/31/32/33/63/64/127/128/129、实际chunk、非整除tail、64K/128Kcontext、overflow、allocationfailure与forcedcap边界。

**验收**：所有offset对齐、size边界、预估≥实际需要，允许有记录的allocatorgranule；alias只在不重叠live interval。**停止**：计划与carve无法一致，不应用PR节省内存。

### P05-03：单独适配 HC region，不合并group scratch

**现有源**：HCread L3194附近、`gr_write_norm_rs` L4868附近、PLE batch / `draft_kv` 使用region处。移植PR HC set部分，先保持原chunk、原expertgroup、原MMQ策略与原算术。

**拟新增测试**：`tests/cuda/prefill_hc_region_test.cu` / `prefill_hc_region_test`，在liveinterval之间poison已死亡region并检查后续输出；BF16x2lowhalf、paddedld、upmix/HCdown分支、controlvector、PLE前后边界、最后half不fusedwrite都覆盖。

**复用target**：`gr_parity`、`gr_multi_parity`、`gr_upmix_parity`、`gemm_bf16_parity`。这些只能验证算子，不替代region生命周期测试。

**验收**：同chunk/同调度的中间结果与最终logits、KV/GDN/PLEstate逐bit一致；compute-sanitizer相关内存检查无错误。**指标/停止**：实际peakVRAM降低才算内存结果；若region本来由更大的QSA set主导，节省量应按实际账计，不能照搬作者KB/token。无TTFT收益也可以保留为有明确场景价值的capacitypatch，但不能称prefill加速。

### P05-04：group scratch 的范围与bounds规划

**现有源**：`MmqPlan`、`MoeBufs`、run_impl中hostbounds生成、group `compute` lambda、`mmq::Product`。**PR源**：`SubRange`、`MoeRange`、`group_cap_rows`、`bounds_ints`。

先做纯host planner：从expert counts和order形成容量不超cap的子范围，逐条验证offset/length和每expert出现一次，绝不拆单expert超过T行这一合同。明确CPUshare移出的rows尾部、resident sorting、未激活expert、残缺lastgroup。

**拟新增 test/target**：`tests/prefill/mmq_group_range_test.cpp` / `prefill_mmq_group_range_test`；输出相同maps/bounds，不依赖GPU。**拟新增显式API**：`Product::dst_row_origin`或安全localmap wrapper，见第2.3节，非上游已有接口。

**验收**：所有range nrows≤cap；range并集等于应由GPU计算的rows且不重叠；原routeentry到Dm映射不变。**停止**：混合fallback/direct/fused资格未明确时应安全refuse或回退原layout，不能压buffer后再赌分支。

### P05-05：group scratch GPU正确性与stream-k审查

**现有源**：`mmq::Context::run / whole_tiles`、`quantize_scatter / swiglu / quantize`、groupgather/guard。**拟新增 test/target**：`tests/cuda/prefill_group_scratch_test.cu` / `prefill_group_scratch_test`。

逐层/逐subrange对照原wholegroup：GU、H、Hq字节、Dm、combinedoutput；不仅看最后文本。特别用forcedcap=T及倾斜分布强制subrange。记录原/新 `n, max_rows, total_rows`、tileconfig、stream-k是否改变。加redzone/poison检测缓冲区overread与最后group。

**复用target**：`prefill_mmq_scatter_test`、`prefill_mmq_tab_test`（仅对应已启用direct构建的对照，PRgroup模式本身当前拒绝direct）、`native_expert_parity`。

**验收**：A档必须逐bit；若仅stream-k变化导致舍入，提交可解释diff并先定B档质量门槛或保持原调度。**停止**：出现任意错误row/NaN/canary/隐式fallback/状态污染立即停，不以“量化本来有误差”忽略memorybug。

### P05-06：PR4039 与真实prefill状态/图回归

在HC-only、group-only分别通过后测试两者组合。固定chunk先验证精确性，再允许planner选择更大chunk；两种测试分开，否则无法区分内存复用和chunk重排误差。

**现有源**：`Prefill::run_impl / relayout / draft_kv`，`SessionState`，`Verifier` / `MtpDrafter` graph，conversation save/restore。**新增测试**：隔离请求fixture执行short→long→short、不同chunk、A→B→A、sharedprefixbranch、partialpage、specpartialreject、cancel/error后恢复；若需要testhook，标明补丁专有。

**复用target**：`gdn_parity`、`qsa_slots_parity`、`kv_stream_parity`、`conversation_snapshot_test`、`conversation_validation_test`、`conversation_split_failure_test`。

**验收**：无use-after-free的graph引用，借出的expert slots仅在安全期写，KV/GDN/PLE/尾部完整恢复；OOM/unsupported路径能回退或明确拒绝。**停止**：32K通过而128K失败或取消后下一请求不正确，不进入速度验收。

### P05-07：现有 `GDN_CHUNKED=1` 的受控资格验证

先不修改代码，记录 `gdn_rec_chunked` 是否真正执行；它有sm80/SM数/sharedmemory/scratch门槛，失败会回退原kernel。对4090确认资源属性，`=2`只绕过SM-count门槛，不能绕过sharedmemory或ISA，通常不应为本卡首选。

**现有源**：`src/prefill/kernels.cu` L866–1220与L2709分支；**现有target**：`gdn_rec_parity`。该测试把chunked实现复制在自己的CU里，因此它通过并不证明production dispatch/lifetime也正确。

原测试合同对chunked output/state用 `max(abs(diff))/max(abs(value)) < 1e-4`，这是已有synthetic数值界，不是128K模型质量保证。当前main目标默认覆盖若干不齐边界、8192、32768；需新增真实production调用和连续chunk state测试，包含127/128/129、2047/2048/2049、128K完整prompt及不同chunk分段。

**拟新增 test/target**：`tests/cuda/gdn_chunked_integration_test.cu` / `gdn_chunked_integration_test`，连接真实prefill函数，不再复制kernel。**验收**：FP32数值界、有限值、长state漂移与teacherforced质量，fallback明确。**停止**：只是recurrence快而整prefill无净增益，或质量越界，就关闭此opt-in。

### P05-08：真实IQ分布上的 grouped MMQ / fused对照

**现有源**：`moe_fused_iq.cu::native_supported / pick_ww`，`moe_mmq.cu::Context::run`，`prefill.cpp::mmq_plan`。分别测每个实际GU/down pair，实际T与expertrowhist，以及uniform/skewed/longtail。

已有 `STRATA_PF_FUSED=1` 不等于所有层fused：Hadamard层、某些格式、streamall条件和smallchunk可能回退。必须输出每层路径计数。现有tile开关 `STRATA_PF_FUSED_TILE=64|128` 可用于有限对照；不要复用已失败的decodeIL结果当prefillMMQ证据，也不要反过来把prefill收益算decode收益。

**现有targets**：`prefill_fused_iq_test`（支持 `--no-timing`、`--only=NAME`、`--chunks=A,B`）、`mmq_expert_bench`（位置参数为rowcounts）、`native_grouped_parity` / `iq_multi_parity` 是decode相关，用于相应核修改回归，非prefill全链证明。

**拟新增**：实际hist回放模式或 `prefill_iq_replay_bench` target；其manifest必须列realweight/seed、T、counts、maxrows、cold/hot。**验收**：按fused vs MMQ数值合同，truepack logitsKL与任务质量；**停止**：没有实际覆盖或microgain被layout/PCIe/CPUgrouping抵消时停止。scratch PR group模式与fused互斥，不能同时打开做首轮。

### P05-09：只为仍可见的瓶颈写新kernel / 调度

若P05-08证明真实MMQ/解码而非PCIe主导，可研究按hist选择tile、减少Xq重复读、gather/quant融合、guard准备批处理。若GDN仍主导，可调FP32chunk的superblock/columns/共享内存；任何新FP16/TensorCoreGDN方案属新数值路线，不伪装纯scratch优化。

**现有源**：MMQ/scatter/guards，`gdn_chunk_prep_kernel / gdn_chunk_scan_kernel`，nativefused kernels。**新增测试**：每种新layout/数学变换都扩对应productionintegrationtest，resourceattrs、registerspill、occupancy与launchfailurefallback必须记录。

**停止**：同一实际shape在有限候选中无稳定净收益就保留原kernel；不为“sm89专属”标签写一个更慢的复制版本。sm90+功能明确不在范围。

### P05-10：联合chunk与总VRAM预算

在固定chunk正确性通过后，才让scratch节省影响planner。比较：原chunk/原layout，新layout/同chunk，新layout/新chunk，三者必须单独报告。新增chunk候选只取少数有解释的点，保留KV maxcontext、MTPhead、expertcache、graphscratch和allocator余量预算。

**指标**：peakallocated/reservedVRAM、borrowedexpert槽数、prefillchunk数、每promptH2Dbytes、TTFT、后续decodecachewarmup、总requestwalltime。64GB/36GB/s限制下CPUshare/issuer/stager的竞争也记录。

**正确性**：chunk改变可能改变GDN/prefill数值，按B档；samechunk的HC复用仍按A档。**停止**：大chunk改善prefill却因cache eviction拖慢用户全请求，或128K接近上限出现OOM/显存峰值失控，不采用该组合。

### P05-11：质量、性能与发布证据

最终组合只包含前面各自通过的项目。用中文/英文/代码/JSON工具/长文检索与多轮branch，实际131072上下文内给输出预留空间。对近似项目记录teacherforcedlogitsKL、taskscore/错误类型；对scratch精确项目记录state/logithash，不混为一份“parity通过”。

性能关闭VERIFY_PROFILE、step-sync、ACT_DUMP、debugnan每层sync等诊断开销，用pairedA/B固定cacheinitialstate与adaptive，区别冷warmup/稳态、short/longprompt。明确所有实际dispatch命中和fallback，否则开关设置不证明被执行。

**建议决策门槛**：预先选性能主指标和统计规则；小改需可重复正收益，大型kernel/scheduler改动应有足以补偿复杂度的优势；p95/质量/内存安全为硬门槛。没有改善就保存阴性结果，不能用8GB作者或5090微基准的百分比替代4090实测。

## 5. 必须包含的偏斜与边界fixture

### 5.1 合法路由极端分布

“all-token-one-expert”指每个token的top10中都含同一个expert，使它有T行；其余9个ID仍须各不相同，不能把每token十个route都复制成同ID而违反router合同。需要两种不同压力：

1. 一个hotexpert有T行，其他9T条目在其余expert上分散；验证单expertcap下界。
2. 每个token都路由到同一组10个不同expert，并让它们排在同一个16-expertgroup；group共有10T行，强制产生多个subrange，最容易暴露cap、bounds和stream-k变化。

进一步覆盖：热点分布在group边界15/16、lastgroup不足16、uniform、Zipf-like longtail、仅1/2个活跃GPUexpert但其余CPUshare、所有expertresident、全部streamed、mixedresident、forcedcap=T、T+1、默认cap、超大cap、零rowexpert。无效重复ID另做输入拒绝测试，不能当合法性能case。

### 5.2 内存与数值边界

| 边界 | 断言 |
|---|---|
| T跨tile/chunk边界 | 31/32/33、63/64/65、127/128/129、2047/2048/2049；tail不读未写 |
| group range | 原absolutebounds与relativebounds一致，Dm全行恰写一次 |
| paddedld/quanttail | q8行padding、MMQweightoverreadguard、最后expert尾部有足够空间 |
| HC lowhalves | BF16x2高低半全部正确存活，gr_unfused时不错误alias |
| 数值 | 极小/极大有限activation、zero、量化scale边界；NaN输入按原合同处理 |
| mixedformat | 逐实际GU/down、Hadamard/tailmetadata；unsupported提前fail-safe |
| ownership | poisondeadregion、canary、compute-sanitizer、copyevent延迟注入 |
| state/graph | full/partialreject、parkrestore、prefixbranch、cancel、后续request复用 |

## 6. 精确性分级与实测报告格式

| 项目 | 默认验收档位 | 不能偷换的说法 |
|---|---|---|
| HC region同chunk同调度 | A：bitwise | 未检测异步reader就称“只是指针变更” |
| group scratch无dispatch变化 | A：bitwise | 只比最终argmax，不比中间数据 |
| group拆分触发stream-k变化 | 先查错，再决定B或改调度 | “相同kernel所以必定samebits” |
| GDN_CHUNKED | B：FP32规约变化 | 当作Volta FP16chunk，或声称完全bitexact |
| fused IQ vs MMQ | B：量化/规约数值合同 | 引用其他量化包的质量证明 |
| 新chunk方案 | B；若测得能精确证明可收紧 | 把samechunk内存节省与chunk改变混在一起 |

建议每项结果使用以下字段（**拟新增报告schema**）：

```json
{
  "candidate": "P05-05",
  "base_sha": "4b9e05a2a806a3fe24f7b2560d98626c37dade35",
  "patch_sha": "TO_BE_FILLED_AFTER_IMPLEMENTATION",
  "model_sha256": "TO_BE_FILLED",
  "gpu_cc": "8.9",
  "actual_paths": {},
  "chunk_tokens": 0,
  "context_tokens": 0,
  "group_splits": 0,
  "stream_k_changed": null,
  "correctness_contract": "A_or_B",
  "tests": [],
  "prefill_wall_ms": [],
  "ttft_ms": [],
  "request_wall_ms": [],
  "peak_vram_bytes": 0,
  "expert_h2d_bytes": 0,
  "decision": "not_run"
}
```

0/空值是模板占位，执行者必须填真实数值；不得把模板作为benchmark结果提交。

## 7. 已有 build targets 与新增target分离

已从固定SHA [CMake](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt#L1143) 和 [MMQ测试块](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt#L2005) 核对：

| 真实target | 实际用法/条件 |
|---|---|
| `gdn_rec_parity` | CUDA目标；默认正确性；`--bench`增加timing |
| `gdn_parity` | CTest调用 `--selftest` |
| `gemm_bf16_parity` | CUDA矩阵数值参考 |
| `gr_upmix_parity` | HC upmix相关 |
| `gr_parity` | CTest调用 `--selftest` |
| `gr_multi_parity` | 多row HC回归 |
| `prefill_fused_iq_test` | CUDA+MMQ+tests；低于支持架构可return77，skip不能写pass |
| `prefill_fused_moe_test` | canonical Q2等相关fused算子，不代替IQ真实包 |
| `prefill_mmq_scatter_test` | quant/scatter bytes对照 |
| `prefill_mmq_tab_test` | 仅 `_strata_mmq_tab_on` 构建有；PRgroup当前拒绝direct |
| `prefill_mmq_kquant_test` | 仅 `STRATA_MMQ_KQUANTS`；实际IQ包若无Kquant不是必测 |
| `mmq_expert_bench` | positional rowcounts；纯microbench不是端到端结论 |
| `native_expert_parity` | 实际shard路径或已有synthetic格式入口 |
| `native_grouped_parity`、`iq_multi_parity` | GPUdecode专家相关回归 |
| `qsa_slots_parity`、`kv_stream_parity` | KV/slot测试 |
| `conversation_snapshot_test`、`conversation_validation_test` | save/restore状态回归 |
| `prefill_plan_test` | 既有prompt规划policy测试，非新scratch所有权测试 |

使用已经配置好的隔离CUDA测试build。执行者先把 `STRATA_TEST_BUILD` 指向自身目录，先检查target存在；不要为这些命令覆盖生产编译配置：

```bash
cmake --build "$STRATA_TEST_BUILD" --target gdn_rec_parity gdn_parity gr_parity gr_multi_parity gr_upmix_parity gemm_bf16_parity prefill_fused_iq_test prefill_mmq_scatter_test
ctest --test-dir "$STRATA_TEST_BUILD" -N
ctest --test-dir "$STRATA_TEST_BUILD" --output-on-failure -R '^(gdn_rec_parity|gdn_parity|gr_parity|gr_multi_parity|gr_upmix_parity|gemm_bf16_parity|prefill_fused_iq_test|prefill_mmq_scatter_test)$'
"$STRATA_TEST_BUILD/gdn_rec_parity" --bench
"$STRATA_TEST_BUILD/prefill_fused_iq_test" --no-timing
```

多配置生成器的binary位置可能不同，应使用构建系统实际给出的路径。新 `prefill_scratch_plan_test`、`prefill_hc_region_test`、`prefill_mmq_group_range_test`、`prefill_group_scratch_test`、`gdn_chunked_integration_test`、`prefill_iq_replay_bench` 在实施并加入CMake之前都不存在。

## 8. 合法组合顺序与停止规则

先P05-01/02；再HC-only与group-only各自验证；然后组合scratch；独立验证已有GDN_CHUNKED与fused。group scratch与fused保持独立A/B分支。只有各单项通过，才把scratch + GDN_CHUNKED组合；如果最终选择fused，则group scratch不自动随同开启，HC region仍需单独确认生命周期。

每项限定有限形状候选和清晰假设。吞吐受PCIe/DDR而不是kernel限制时，不继续盲改CUDA；内存节省没有改变可用chunk或residentcache时，不保证速度提高；newchunk导致更多cacheeviction时按全请求结论；任何状态/内存错误先停止性能测试。所有未采用候选保留理由和原始数据，防止未来把本轮阴性结果重新包装为新路线。

完成交付应含patch、准确所有权表、实际dispatch/资源清单、A/B原始日志、质量报告、状态/图回归与可回退路径。当前文档没有任何目标机实测收益。
