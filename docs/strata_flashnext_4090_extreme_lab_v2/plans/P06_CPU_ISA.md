# P06：4216 的 CPU ISA、共享解包与预打包实施计划

本计划覆盖方向 O04、O05、O06，交给实现者后按任务顺序执行。它是设计与验收合同，**没有实现新 kernel，也没有在用户机器上运行性能测试**。CPU pool 的调度、量化阶段并行与 epoch 生命周期由 P01 承担；这里仅处理算术实现、ISA 分派及静态布局，二者先独立验证，再测组合。

固定研究源码为 Strata `41cf05a06a25dd29103b7b27a2279a3f60c21876`；生产 oracle 保留 v0.2.3 `5c8dd322528cc84f68f461ad54a506b9da8fa8d4` + 用户 EXACT6。目标为 Xeon Silver 4216、16C/32T、64 GB 双 DIMM DDR4，附件实测读带宽约 36 GB/s；GPU 为 RTX 4090。模型是 **GSQ-RCO IQ3_XXS**，具体 GU / down 格式须读取模型 manifest，不能从包名推断所有矩阵。

最终执行 base 更新为 `4b9e05a2a806a3fe24f7b2560d98626c37dade35`；CPU / CUDA / core / prefill tree 与本计划已审快照相同。PR3871经最后实时核查仍未合并，详见 [最终版本增量复核](../sources/FRESHNESS_DELTA.md)。保留下面的41cf固定源码引用。

## 1. 结论、顺序与已有失败记录

**优先证明实际 dispatch 与瓶颈，再决定是否写无 VBMI 的 VNNI 内核。**4216 的 AVX-512 VNNI 不等于当前 Strata 的宽 ISA 路径可用。现有宽路径还要求 VBMI，部分 IQ512 实现又要求 VPOPCNTDQ。直接放宽 `cpu_avx512_ok()` 会把此 CPU 送入含不支持指令的编译单元，不是有效优化。

执行顺序是：实际格式与 binary 身份 → 修复 benchmark 的真实路径 → dispatch 命中与频率证据 → 分离新 TU → 一种实际占比高的 dtype → 多 token → 可选预打包 → 全请求验收。O05 中“同 expert 多 token 只解包一次”已有实现，只补 trace 证明的空缺。既有 EXACT6、POOL8 / PROFILE、历史无收益记录继续保留；改 benchmark 或恢复已有功能不计为生产加速。

| 方向 | 本计划交付 | 必须满足的前提 | 可以立即停止的情况 |
|---|---|---|---|
| O04 无 VBMI VNNI | 独立 TU、独立运行时资格、实际类型的 dot/quant 实现 | 真实 CPU miss 关键路径有解包 / dot 余量 | 已到实际并发 DDR 上限，或降频抵消 |
| O05 多 token 复用 | 现有复用覆盖审计；缺失处增量实现 | 相同 expert 的合法 columns 在同一窗口重用权重 | nt 分布几乎为 1，或现有路径已经覆盖 |
| O06 预打包 | 可逆、按字节等价的布局以及 RAM / 启动成本账 | 未被 DDR / page-cache 压力吞掉收益 | 仅 LLC 热 micro 变快，冷读或总 wall 变慢 |

本机没有 VBMI 的前提来自用户附件，实施时仍须把 CPUID、XCR0、最终编译命令、实际 ggml ISA 打入实验 manifest。不能用型号名称替代可执行资格检查。

## 2. 固定源码事实与锚点

以下编号均指固定 main；链接不跟随最新分支。

| 源码 | 现状与改动边界 |
|---|---|
| [expert_layout.cpp L42](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/expert_layout.cpp#L42) `cpu_avx512_ok` | 检查 OSXSAVE / XCR0、F/BW/VL/VNNI/VBMI；必须保持旧 gate 的语义 |
| [expert_layout.cpp L77](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/expert_layout.cpp#L77) `cpu_avx512bw_ok` | 已有另一种较宽松资格；不能据此推断所有 IQ512 kernel 安全 |
| [expert_layout.cpp L261](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/expert_layout.cpp#L261) `cpu_avxvnni_ok` | 查 CPUID 7.1 的 VEX AVX-VNNI，和 4216 的 EVEX AVX-512 VNNI 不同 |
| [expert_layout.cpp L357](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/expert_layout.cpp#L357) `q2_rows_any`、L371 `act_quant_any` | Q2_0 pool 的真实入口；不应通过通用 ggml dot 替代它做生产估算 |
| [expert.cpp L153](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/expert.cpp#L153) `unpack64_q2_0` | 使用 `_mm512_multishift_epi64_epi8`，本身需要 VBMI；现有 zmm Q2 不能直接在 4216 启用 |
| [native_expert.cpp L251](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/native_expert.cpp#L251) `native_quant_act / native_quant_h` | 已有 Q8_K AVX2 quant；Hadamard 有自己的变换与临时向量生命周期 |
| [native_expert.cpp L277](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/native_expert.cpp#L277) `native_gu_mt_min / native_gu_rows` | nt=1 与 multi 求和顺序可能不同；EXACT1 还要求实际 ggml 编译为 AVX2 而非 AVX512 |
| [native_expert.cpp L336](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/native_expert.cpp#L336) 新 IQ512 单 token 路径 | 有 AVX512、gather、格式与首次 parity gate；不能把新 main 的此路径当作 4216 自动受益 |
| [iq_avx512.cpp L603](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/iq_avx512.cpp#L603) `iq512x_supported` | 另查 VPOPCNTDQ；旧 TU 的可用性不能由仅 VNNI 的 probe 代表 |
| [iq_avx2.cpp L457](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/iq_avx2.cpp#L457) `iq256_gu_rows_exact_one`、L500 `iq256_gu_rows_v` | 新实现对照的实用起点；应保留现有 EXACT6 的已验证语义 |
| [pool.cpp L1176](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/pool.cpp#L1176) `drain`、L1359 `run_split_multi_native` | GU / down 依据格式选不同入口；micro 必须对应实际 mode 5 / 6 |
| [CMakeLists.txt L1721](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt#L1721) | 现有 IQ512 TU 编译 flags 包含 VBMI、VPOPCNTDQ；不能直接复用它的全套 flags |
| [tools/check_isa_guard.py](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/tools/check_isa_guard.py)、[CMake L2305](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt#L2305) | 已有静态 ISA guard 与可选 SDE；新 TU 仍需专用 no-VBMI/no-VPOP 验证 |

## 3. 固定输入、输出及数值等级

### 3.1 输入

每个 fixture 记录模型 hash、layer/expert、`NativeFmt`、GU/down 类型、row stride、up/down/tail offset、Hadamard 属性、真实 blob 字节、activation / ActQ 字节、nt、row range、ggml 构建 ISA。缺少某种真实 dtype 时，该 dtype 的性能结论标为不适用；不能为了增加“覆盖率”用 synthetic 代替真实路径。

真实性分三层：单 row 函数；与 pool 相同的 GU→SwiGLU→quant→down；真实 verify 下 CPU / GPU overlap。它们输出各自的计时口径，不互相代替。特别是当前 `kq_cpu_bench` 的 gate/up 与 down timing 不等于完整 `ExpertPool` 调度时间，也不等于请求速度。

### 3.2 输出与正确性

第一版目标为 **E：与同 binary 的旧实际分派逐 bit 相同**。activation quant 输出按字节比较；GU、SwiGLU、down 分阶段 hash；同一 expert 的 nt 和 group 不能被重分组以绕过舍入差异。若新宽规约只能得到容差等价，应明确改列 **N：数值路径改变**，冻结阈值并追加长序列与质量评估，不能删掉失败的 exact 断言后称为“精确”。

VNNI 优化须逐式证明 signed / unsigned 操作数、zero-point correction、block scale、int32 累加不溢出；不得用饱和 dot 偷换非饱和语义。对 IQ3_XXS，表索引、符号位、scale 与 dot 的布局都需要分别验证，不能把 Q2 的 unpack 当作通用低比特实现。

### 3.3 性能输出

至少报告实际调用计数、每种 `(dtype, nt, path)` 的占比、权重字节 / s、GU / quant / down 时间、pool critical path、CPU 有效频率、并发 DDR 读写、p50 / p95 请求耗时和 accepted output tokens / wall time。附件约 36 GB/s 只是本机读带宽参考，GPU DMA、内存写回和 page fault 竞争下的可用带宽要重测。

## 4. 拟新增接口与开关

本节所有名字均为**拟新增，当前上游不存在**。第一轮仅给测试 harness 使用，默认关闭，不修改用户的生产 CLI。

```cpp
// Proposed internal API; not present in upstream.
struct ClxVnniCaps {
    bool os_state;
    bool avx512f, avx512bw, avx512dq, avx512vl, avx512vnni;
    bool fma, f16c;
};

enum class ClxRowsMode { Disabled, Evex256, Evex512 };

bool cpu_clx_vnni_ok() noexcept;  // Baseline TU only.
bool clx_rows_supported(const NativeFmt& fmt, int nt) noexcept;
void clx_native_gu_rows(const NativeFmt&, const uint8_t* blob,
                        const void* const* act, int nt,
                        float* const* ff, int r0, int r1);

struct CpuPackKey {
    uint64_t model_identity;
    uint32_t layout_version;
    uint32_t format_signature;
};
```

候选临时开关：**拟新增** `STRATA_CLX_VNNI=0|256|512`、`STRATA_CLX_TRACE=0|1`、`STRATA_CPU_PREPACK=0|selected`。仅在对应补丁落地后可运行；非法值拒绝、unsupported dtype 回到旧分派并统计 reason。trace 按 worker 局部计数，避免每个 row 争用全局 atomic。

新 kernel 源文件可为**拟新增** `src/kernels/cpu/iq_clx_vnni.cpp`、`q2_clx_vnni.cpp`，probe 留在现有 baseline TU。编译只允许实际需要且 CPU 支持的 F/BW/DQ/VL/VNNI、FMA/F16C 等；禁止继承 `-march=native`、VBMI/VBMI2、VPOPCNTDQ、VEX AVX-VNNI。具体 flags 由目标 compiler 的支持情况确定并写入 `compile_commands.json`。不能以关闭已有 ISA guard 换取构建成功。

## 5. 逐任务实施与验收

### P06-01：导出实际类型与调用分布

**输入**：真实 manifest、EXACT6 diff、生产配置和一组固定请求。**现有源**：`expert_layout_load`、`expert_pool_dispatch_multi`、`native_gu_rows`、`pool.cpp::drain`。**输出**：CPU format / nt / miss 分布与被调用符号清单，区分 IQ3_XXS GU、实际 down 与 Q2_0 特例。

**实施**：加低扰动、按 worker 累积的路径计数；同一 fixture 关闭计数重复运行以检查扰动。对使用 placeholder routing weights 的 dump 只读频率，不把它当真实误差和质量基准。

**验收 / 停止**：实际路径未知、计数总量不闭合或 silent fallback，先修观测。不对并未出现的 IQ3_S / TQ / NVFP4 优化占用本轮预算。复杂度低，主要风险是统计本身改变热路径。

### P06-02：修复基准，建立可信 oracle

**源**：[kq_cpu_bench.cpp L57 / L152](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/kq_cpu_bench.cpp#L57)。当前 `make_blob` 通过 CPU traits `from_float` 量化，有些 I-quant 没有此函数；Q2_0 又通过通用 `native_*` timing，和 pool 的专用 rows 不一致。

**参考补丁**：[PR #3871](https://github.com/Niko1221/Strata/pull/3871)，研究时 open / 未合并，head `b5dadce98478d2451f246afa240724b3011d54a2`，只改 benchmark。其做法是 `ggml_quantize_chunk` + 必要时 flat importance matrix，以及 Q2_0 的 `ActQ / act_quant_any / q2_rows_any` 真入口。人工核对 patch 与当前 pool 后单独移植，不能把它的异机 timing 校正当 4216 提速。

**输出**：有效 scales 的 synthetic blobs、真实 blobs replay、明确 header path、输入尺寸拒绝测试。实际 GU/down 类型分别报告。现有 target 为 `kq_cpu_bench`；为它新增测试 fixture 而不是假设已有 CTest 会覆盖 null quantizer 和 Q2 dispatch。

**验收 / 停止**：nt1…8、不支持类型与无效参数不会越界；Q2_0 的 byte quant 与 pool 一致；单 row 输出符合旧 oracle。若 benchmark 仍落错路径，停止所有速度比较。复杂度低；这一步是测量修复，不是引擎优化。

### P06-03：建立 ISA 隔离与反汇编门禁

**源**：`expert_layout.cpp`、`CMakeLists.txt`、`tools/check_isa_guard.py`。**拟新增**：上节独立 TU、baseline probe、`cpu_clx_isa_test` 与 `clx_isa_guard_check` 测试。不要把后者写成当前已有 build target。

**实施**：检测 OS 保存 zmm / opmask 的状态，以及每种 intrinsic 实际需要的 CPUID 位；不执行不受支持的试探指令。对新 TU、其 weak / COMDAT helper、静态初始化和链接后可达函数进行 CPU 反汇编检查，工具用 `objdump` / `llvm-objdump`，不是 GPU SASS。确认无 `vpmultishiftqb`、`vpermb` 等 VBMI 路径，无 `vpopcnt*` 的 VPOPCNTDQ 路径，无超出白名单的新指令；仅搜索几个助记符不等于完整 ISA 审计，应建立指令到扩展的明确规则。

**验收**：AVX2-only 与其他已有路径仍能启动、unsupported probe 不调用宽 TU；编译器内联 / LTO 不把宽指令泄漏进 baseline。现有 `isa_guard_check` 不替代新增的 no-VBMI 检查。SDE 的 hsw / adl 现有测试可作回归，但不能代替 4216 真机、实际频率与内存行为。

**停止 / 回滚**：任意非法指令或 baseline 泄漏，禁用整个新 dispatch；不要放宽旧 gate。复杂度中，正确性风险高于普通 kernel arithmetic。

### P06-04：单 dtype、nt=1 的无 VBMI 原型

**输入**：P06-01 中占 CPU critical path 最大的真实类型。优先实际 IQ3_XXS GU；若 Q2_0 down 占比更高且测量证据充分，可先做 Q2_0。**源**：`iq_avx2.cpp` / `iq_avx2_rows.inl`、`q2_avx2.cpp` 与宽路径的算法解释。

**拟新增实现**：先保持原 row、block 和 FP32 累加顺序，只换整数 unpack / dot；用 byte shuffle、shift/mask、已支持的 permute 或标量 lookup 替代 VBMI / VPOP。EVEX 256 和 512 分开实现并计量，不能把“更宽”预设为“更快”。对于 codebook gather，单独比较 gather 与 scalar-load，4216 上的延迟必须实测。

**正确性**：符号位全集、codebook 边界、合法极端 scales、零 activation、尾块、非整行 range、nt=1 实际 blob。quant、GU 和 down 分别定位首次差异；检查当前 EXACT6 所依赖的 ggml AVX2 编译合同。

**性能 / 停止**：独立 core 和生产并发线程数各测；记录有效频率，避免短 burst 避开宽指令频率效应。若解包更快但 DRAM 或频率使完整 expert 不变，不扩 dtype。复杂度高；初次 exact parity 失败不能直接更换 oracle。

### P06-05：nt2…8 共享解包，只补未覆盖处

**源**：`native_gu_rows`、`iq256_gu_rows_v`、`iq512x_rows`、`ExpertJobMulti`。当前 multi 已对一个 expert 的多个 columns 复用解包，先画出真实 dtype × nt 的覆盖表。

**拟新增**：同一解码 codebook block 驻留寄存器，累加多个 activation columns；容量过大时按小 token tile，但保持每 token 的 block 累加顺序。保持 job 的原 nt，不把稀疏 expert 合并成不属于同一权重的“batch”。ActQ 只在相同 layer、activation、format、Hadamard 与 scale 合同时复用，不能跨层或跨 token 误用。

**验收**：nt1…8 对应各自旧 oracle；同一输入在重复调用和不同 task 行块下结果一致；不越过 row range。根据真实 nt 直方图加权，不能只呈现 nt=8 峰值。附件平均 miss nt 约 1.31 的历史证据要求本轮重新确认，不能假设全是大 batch。

**停止 / 回滚**：已有代码已覆盖，或寄存器压力 / 指令数使真实分布更慢，则保留旧 multi。复杂度中高；与 P01 task 切分合测前先完成独立 correctness。

### P06-06：量化与 down 的真实链路整合

**源**：`native_quant_act / native_quant_h / native_down_rows`、`pool.cpp::drain`。GU 速度不是完整专家速度，必须加回 SwiGLU、完整中间量化与真实 down。

**实施**：先不改 quant 算术。若 profile 证明 quant 仍显著，再做单独的 CLX quant 或已有 AVX2 复用；Hadamard 与 scale reduction 每一步按实际格式保留。避免为新 GU 重复创建同一个 ActQ；避免每次 dispatch 重新分配 pack / lookup buffer。

**验收**：中间量化字节、完整 expert output、不同 nt、GU/down mixed types、r0/r1 分片。P01 的并行 quant 与本步骤不得同时作为首轮 patch，否则无法归因。

**停止**：剩余耗时来自 pool barrier 或 DDR，交给 P01 / 驻留计划处理；本步骤不借改 worker 数重跑已失败的 POOL8。复杂度中。

### P06-07：可逆预打包，先做最小布局

**源**：`NativeFmt`、`expert_layout_load`、`iq_avx2_rows.inl`，以及 CPU expert blob owner。**拟新增**：`CpuPackKey`、版本化 descriptor 和按需 pack owner。优先探索不扩大权重总量的 row/block 重排、code/scale 分区对齐，再考虑有限展开；不先把整个模型反量化成更宽格式。

**合同**：`unpack(pack(blob))` 恢复原有效字节；padding 有固定值；计算得到完全相同的量化权重。CPU pack 的所有权与 GPU 原格式分开；GPU fetch、cache resident 与磁盘 artifact 不得误读新的 CPU 格式。模型 / quant / layout 版本变化必须失效缓存，失败回到旧 blob。

**验收**：顺序与随机 experts、冷 DRAM / LLC 热、页边界、未对齐来源、GU/down 混合、尾块、64 GB 峰值占用、首次启动与重启。计算式需含原 blob、pack、构建临时区、pinned buffers、6 GiB conversation cache 与模型其余驻留；不能只报最终 pack 大小。

**停止 / 回滚**：pack 导致换页、减少可用 context / 会话容量、显著增加冷启动或只在 LLC 热 micro 赢，删除 pack cache 即回到原路径。复杂度中高。

### P06-08：端到端与 CPU / GPU 并发验收

**输入**：只改变一个 ISA 或 pack 因子的二进制；生产 EXACT6 oracle、固定 sampled / greedy workload、固定 spec4 / `--spec-min-p 0.5`（草稿阈值，非采样 `min_p`）。**输出**：A/A 噪声、ABBA paired 结果、留出集与错误日志。

至少覆盖 0 / 1 / 2 / 多 CPU experts、nt1…8、overlap on/off 的诊断、真实生产 overlap、spec accept0 / partial / full、cancel / resume、64K 与接近 128K 的合法请求。128K 是总 context 上限，prompt 必须留出 generation 空间。状态回滚由引擎已有合同执行，不因 CPU kernel 结果早到而提前释放 activation / jobs。

**验收**：E 档所有固定输入的输出、量化、state hash 符合 oracle；N 档按预冻结误差与质量门，不宣称 bitwise。性能以真实 accepted tokens / wall 和 p95 为准，CPU micro 的 GB/s 只作解释。

**停止门槛**：小改至少需重复正收益且配对置信区间不跨零；新增 ISA 或 pack 这种维护面较大的改动，可预先选择 3% 真实场景净收益作为工程门槛，并把允许的 p95 退化写进 manifest。这是建议决策阈值，不是预测收益。门槛只能测试前确定。失败则保留测量修复与证据，关闭新 dispatch。

### P06-09：组合、发布和永久回退

先与 P01 单独通过的 pool patch 做 2×2 对照，再与驻留 / PCIe 策略合测，因为 CPU 变快会改变 CPU-vs-GPU 成本选择。先后顺序不应让一次策略自适应掩盖另一个 kernel 的真实回归。

输出最小 patch 集、支持 dtype 白名单、构建身份、实际命中率、fallback reason、数值等级、性能与 RAM 账。旧 dispatch 始终可单独启用，回滚不需要模型重新转换。新开关保留为关闭默认，直到目标机器与必要兼容平台验收通过。

## 6. 构建目标与新增测试的严格区分

下表来自固定 main 的 CMake。命令应在用户准备好的隔离 build 目录执行；本计划不预设 build 路径和工具链。

| 当前已有 build target / CTest | 用途与限制 |
|---|---|
| `kq_cpu_bench` | micro；需先处理 P06-02；不是 CTest 或完整 pool |
| `iq_avx2_parity` | 现有 AVX2 rows；新 CLX 不会自动被覆盖 |
| `iq512_gather_parity` | existing target；`iq512_gather_parity_scalar/gather` 是 CTest 名；4216 跳过宽资格不算新实现通过 |
| `q8k_quant_parity` | Q8_K quant byte parity；须增加新分派覆盖 |
| `native_expert_parity` | synthetic / 真实 artifact 路径依测试参数；缺 fixture 不得当通过 |
| `pool_tasks_test`、`pool_stress` | 调度 / 生命周期回归；不能替代新 ISA arithmetic 测试 |
| `expert_multi_test` | 没有原宽 ISA 时可能 skip，须报告有效 case 数 |
| `q2_bitplane_parity` | 现有 AVX2 Q2 bitplane 分支，需相应构建条件 |
| `isa_guard_check` | **CTest 名，不是 build target**；静态宽 ISA 泄漏检查 |

来源：[CPU targets L1778–1819](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt#L1778)、[native parity L2152](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt#L2152)、[pool / ISA tests L2244–2335](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt#L2244)。

**拟新增 source / targets，均未实现**：`tests/cpu/clx_isa_test.cpp` / `cpu_clx_isa_test`；`tests/cpu/clx_rows_parity.cpp` / `cpu_clx_rows_parity`；`tests/cpu/native_pack_test.cpp` / `cpu_native_pack_test`；`tests/cpu/clx_trace_bench.cpp` / `cpu_clx_trace_bench`。测试 harness 要断言 `requested_path == executed_path` 和非零 invocation 数，unsupported 要明确 skip / fail，不输出零耗时“胜利”。

## 7. 冲突组合、停止与证据包

| 组合 | 冲突或归因风险 | 处理 |
|---|---|---|
| 新 VNNI + EXACT6 | 宽规约可破坏已有 exact 合同 | 以真实编译 oracle 分阶段比较；差异就拆为 N 档 |
| 新 VNNI + P01 pool | 调度和算术同时改变，难定位 race / rounding | 各自通过后 2×2 |
| 新 pack + GPU mapped fetch | GPU 可能按旧格式读取 CPU 新布局 | 保持独立 owner / 指针；禁止原地替换共享 blob |
| 全模型 pack + 6 GiB cache + 长 context | 额外内存挤占可用 RAM，引起 swap / admission 变化 | 全过程 peak RSS / pinned / available 账 |
| 新 multi + `STRATA_IQ_MT_MIN` | 路径或求和次序变化导致 spec 输出差异 | 初期冻结旧设置，不同时调整 |
| 新 CLX + compiler / ggml 更新 | oracle ISA、FMA contraction 或代码生成改变 | 固定工具链；一次只改一个因素 |
| CPU 更快 + adaptive routing | CPU / GPU 分流变化可扩大或掩盖收益 | 固定路由诊断 + 生产自适应两类都报 |

最终 evidence 至少含：manifest、实际格式与 path counts、全部 test/skip/fail 清单、反汇编与白名单报告、微测原始数据、paired 请求数据、CPU 频率 / DDR / RAM 峰值、质量等级、回滚命令和保留的旧 binary。未通过的路线记作无收益 / 不适用 / correctness failure，保留它们的停止原因，避免下一轮把同一失败当新方向重做。
