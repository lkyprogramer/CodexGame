# Inkling 4090：KV 量化、新权重支持与长上下文实施方案

**日期：2026-11-28（北京时间）**  
**状态：设计与待执行计划。本文没有实施代码、启动 GPU 实验或修改现有任务状态。**  
**配套评估：** `Inkling_4090_Quantization_Context_Assessment_20261128.md`

> 后续执行者：按本文任务依赖推进；可用独立执行者实现互不共享修改范围的子任务，并逐项审阅。代码实现需使用 subagent-driven-development 或 executing-plans 工作流。本文中的新文件、接口、环境变量与脚本均为拟议项，不能当作当前仓库已支持的功能。

## 0. 目标、范围与不可破坏的约束

**Goal：** 在单 RTX 4090 上，先降低八个全局 target KV 的容量斜率，争取128Ki长上下文提速与192–256Ki容量；随后仅为通过外部质量筛选的一款低位权重实现原生支持；512Ki–1Mi列为带条件的后续阶段。

**Architecture：** 保留三遍、48个visit、每个visit独立状态。第一阶段只给8个全局visit增加FP8/INT8存储，40个局部visit维持现有FP16 ring；在CUDA tile内反量化，沿用attention语义。目标KV与draft KV分开配置。权重接入按一个真实文件的完整格式闭包实施，不先建通用量化框架。

**Tech Stack：** 现有Rust workspace、CUDA C++、SM89、Python实验/判定脚本；参考后端仍保留既有llama.cpp b12751。新候选若需要新后端，另建辅助对照，不改写G2。

**Spec：** 配套评估报告第3–10节、附录A/B；源码与实验室固定版本见下表。

| 对象 | 固定快照 |
|---|---|
| Engine | `d586fec31afd08526d0500ba815a33be18199c65` |
| CodexGame / 4090-report | `495f110dfe4a1bb5e5ae743c9378ab9a9937e103`，lab v3.0.26 |
| A1 SHA256 | `e64276656f072e9b2197a61723667cbdb71da66a716ffd966e572c21088f3cd3` |
| 固定正式模型 | 24物理层；core 3遍；48visit；global 8 / local 40 |

### 0.1 与现有计划的关系

- 现有主线继续保持 **K12 + T45 → T44 → K15 → K13 → K14 → T47**。
- 本文的“任务0–11”仅是文档内编号，不占用新的T/K编号；T46已经是现有评估闭环，不能复用其编号。
- CPU inventory、数据冻结、内存计算、判定器回归可并行准备；单张4090的基准与正式实验串行运行。
- 本文不替换A1，不变更当前默认dtype，不改变正式三遍，不自动升级参考runtime。
- 不把动态循环、专家裁剪、跨pass KV共享、树推测、prefix cache或多卡训练引入首轮依赖。
- 当前API按请求reset。没有现成的prefix持久化功能需要本轮兼容；不能借KV改造扩建一个新缓存平台。

### 0.2 审阅重点

1. 量化写入必须发生在短卷积、K clipping、V normalization之后；Q/R长度缩放、RPE与sink语义不变。
2. decode、2–8行verify、分块prefill和草稿派生head都覆盖；不存在“只测单token”的支持闭包。
3. rejected token不会改变已提交位置的scale或编码；逻辑位置与ring地址不可混用。
4. 显存报告包含权重/scale、target与draft KV、scratch、graphs和加载/预填充峰值。
5. 容量成功、数值可接受、真实终答成功与端到端提速分别判定；证据缺失直接INVALID或INCONCLUSIVE。

## 1. 依赖与交付物

| 文档内任务 | 挂靠方向 | 前置条件 | 必须交付的结果 |
|---|---|---|---|
| 0. 冻结与证据门 | T41追加 / T46 | 无GPU依赖 | 源码/资产清单、数据完整性负控、显存账 |
| 1. KV codec参考 | T44 | 0 | FP8-head与INT8-g64的CPU规范、样本与对拍 |
| 2. 缓存布局与配置 | T44 | 1；K12/T45接口冻结 | per-visit typed storage、准确allocation报告 |
| 3. 写入/提交路径 | T44 | 2 | step/prefill/verify一致的编码与回滚 |
| 4. attention readers | T44；协调K15 | 3 | decode、verify、prefill的量化reader |
| 5. 状态与数值门 | T25/T45追加 | 4 | 边界、拒绝、重置、graph切换报告 |
| 6. 受控扩大容量 | T44容量扩展 | 5 | 192/224/240/256Ki真实请求报告 |
| 7. 质量与性能决策 | T46 | 5；容量分支用6 | PASS_SPEED/PASS_CAPACITY等明确结论 |
| 8. 新权重外部筛选 | T31 | 0；独立GPU时隙 | 0或1款进入native实现 |
| 9. 单资产原生闭包 | T31后续 | 8通过；基线已冻结 | 完整格式支持与四模式回归 |
| 10. 远历史KV4 | T44后续研究 | 7通过 | 确定性远近视图、512Ki验证 |
| 11. 组合与1Mi研究 | 联合阶段 | 9/10通过 | 四臂质量、真实prefill与终答证据 |

任务8可以先做CPU inventory，但不能与主线抢占同一GPU做对照。任务9、10可以在接口冻结后由不同执行者实现；其GPU验证和最终组合仍串行。

## 2. 任务0：冻结输入，修补证据完整性，重建显存账

**现有修改位置（后续执行时）：** lab的 `tools/t25/t25_judge.py`、`tests/test_t25_judge.py`，以及既有T46判定入口。  
**拟新增：** `tools/t44/run_manifest.schema.json`、`tools/t44/memory_report.py`、`tools/t31/asset_manifest.py`。保持脚本单一职责，不建立独立调度平台。

- [ ] 保存engine commit、dirty diff哈希、二进制SHA256、编译flags、CUDA/driver、PTX/cubin哈希、GPU型号/总显存/功率与时钟策略。
- [ ] 保存A1、draft与每个候选的完整本地SHA256；远端LFS metadata只用来核对，不能替代本地文件校验。
- [ ] manifest列出tokenizer/chat template、prompt原始文本哈希、输入token ID哈希、长度、固定输出预算、采样参数、seed、校准/开发/留出集分区。
- [ ] 每个case显式登记应输出的position集合、vocab宽度、dtype、张量形状；判定器读实际NPZ逐项核对，而不是只信任JSON摘要计数。
- [ ] 加两条已知会暴露缺口的负控：所有position偏移100000；NPZ截成1行但JSON行数不改。两者必须非零退出，不能落入PASS。
- [ ] 加一条身份负控：互换两个case的结果，或替换输入hash；必须识别。避免用扩大的数值容差掩盖错位数据。
- [ ] 冻结参考输出与判定规则后再跑候选；不能根据候选结果临时新增“这个负控不必触发”的例外。
- [ ] 对大logits允许分块归约或压缩保存，但保留可重放输入、实际行索引、摘要、分块hash、命令与二进制。不能仅保留一个无法重跑的PASS字样。

本次报告已用原判定器CPU复现上述两条数组缺口；这不等于历史数据错误。修补只针对完整性检查，不重写T25/T46全部逻辑。[P05]

### 2.1 显存分类必须覆盖实际常驻状态

| 分类 | 需记录内容 |
|---|---|
| 权重 | packed payload、aux、外部mat_scale、embedding、为BF16旁路生成的Q8副本 |
| target KV | 逐visit的K/V bytes、scale bytes、行数、padding、格式 |
| target固定状态 | conv、prefill/verify scratch、attention workspace、router/experts缓冲 |
| draft | DSpark与DFlash2分别列权重、KV、features、selector、folded head、rollback |
| 运行时 | CUDA context/modules、graphs、分配器保留、临时pack、加载峰值与稳态峰值 |

当前 `GemvMatrix::bytes()` 没有完整覆盖外部mat_scale，因此不要把现有一条权重日志当作完整内存账。新telemetry应按底层allocation统计，避免把同一共享buffer重复计入。[P01][P02]

对plain、单DSpark、单DFlash2、双草稿四种模式，至少采集：加载后、session后、graph warmup后、真实prefill峰值、decode峰值、reset后。报告`cudaMemGetInfo`观测与已知allocation之差，不强行把差值归到KV。

## 3. 任务1：冻结两款KV8 codec的精确定义

**拟新增：** engine `crates/quant/src/kv.rs`；在 `crates/quant/src/lib.rs` 导出必要纯CPU参考。测试只覆盖会影响数值/状态的边界，不做实现镜像式测试。

首轮只比较现有T44的两种选择，不悄悄把“INT8每64通道”替换成其他group size。

| 字段 | `fp8_e4m3_h128` | `int8_g64` |
|---|---|---|
| data | 每元素1 byte | 每元素1 byte、有符号 |
| scale | K/V分别每token、每KV head一个FP16 | K/V分别每token、每64通道一个FP16 |
| head dim | 128 | 128，即每head两个group |
| payload/全局token | 16,384 bytes | 16,384 bytes |
| scale/全局token | 256 bytes | 512 bytes |
| 合计/全局token | 16,640 bytes | 16,896 bytes |
| 首轮全局历史精度 | 全部KV8 | 全部KV8 |
| local层 | FP16 ring | FP16 ring |

### 3.1 编码规则

1. 从当前FP16 cache定义的值开始：先得到与现有路径相同的post-conv/post-norm值并按原cache语义舍入FP16，再编码。若后续研究直接从F32编码，视为单独候选，不能偷偷改变参考。
2. `amax=max(abs(x))`；全零group使用scale=1、code=0。非有限输入在debug/验证路径显式失败并记录visit/position，不能静默清零。
3. FP8使用NVIDIA E4M3的finite-saturating、round-to-nearest-even语义，最大有限值448；明确排除E4M3FNUZ。基础scale为`amax/448`。
4. INT8取对称整数范围[-127,127]，基础scale为`amax/127`；使用一致的nearest-even和饱和规则。
5. 基础scale写为FP16后，编码也使用**实际存下来的scale**，不能用未舍入F32 scale编码、再用FP16 scale解码。非零scale下界至少为可表示的最小正FP16值；验证CUDA路径对subnormal的处理与CPU一致。极端范围按固定规则报错或使用预先定义的保护精度，不隐藏fallback。
6. 解码为`float(code)*float(scale)`；FP8先按同一E4M3规则解码。每个token/group的scale独立，写新token不会改变任何旧token的scale。
7. 首轮不做跨token在线重估scale、异步历史重压缩、zero point或随机舍入，减少推测回滚状态。

**验收：** CPU/GPU的code bytes、scale bits一致；同一encoded row解码值一致。覆盖零值、正负边界、tie、极小值、离群值、scale舍入、分组分界，并用真实48visit探针的post-prep K/V样本补充。量化误差统计必须区分K/V、global物理层与pass。

**继续条件：** 输出可重复、8bit误差在短留出集无明显异常；否则先查实现和scale定义，不启动长GPU扫描。

## 4. 任务2：在真实Session内增加typed KV storage

**拟新增：** `crates/model/src/inkling/kv.rs`。  
**修改：** `crates/model/src/inkling.rs`、`crates/kernels/src/inkling.rs`。首轮不把 `crates/kvcache` 骨架重构成通用cache服务。[P01]

建议最小接口如下，名字为提案，语义为契约：

```rust
enum KvCodec { F16, Fp8E4M3H128, I8G64 }

struct KvLayout {
    version: u32,
    codec: KvCodec,
    rows: usize,
    kv_heads: usize,
    head_dim: usize,
    data_row_stride: usize,
    scale_row_stride: usize,
}

enum KvStorage {
    F16 { /* K/V DeviceBuffer<u16> + layout */ },
    Q8  { /* K/V DeviceBuffer<u8>, scales DeviceBuffer<u16> + layout */ },
}

struct VisitKv {
    physical_layer: usize,
    pass_index: Option<usize>,
    slot: usize,
    storage: KvStorage,
}
```

`pass_index`对prelude/coda可为空；它不是要求先完成整个T23重构。沿用当前正确slot展开，在测试中显式核对48visit映射即可。

- [ ] 8个global分配Q8数据与独立K/V scales，40个local继续当前FP16 ring。
- [ ] 保留F16默认与完整原分支；新配置固定在session创建时，拒绝mid-request改变codec。
- [ ] 所有长度/stride/bytes计算用checked usize/u64运算；明确kernel参数的32位范围，不把bytes乘法截成u32。
- [ ] session保存logical valid end、capacity；ring modulo只用于storage address，因果mask/RPE/长度tau使用绝对逻辑position。
- [ ] 保存分配地址稳定性，graph捕获后不移动buffer；graph key包含codec、布局版本、verify rows及所有改变kernel路径的配置。
- [ ] `reset`恢复position与conv/draft状态；可保留物理buffer内容，但reader不得读取valid end之外的数据。debug poison用于揭露误读。

**拟议实验开关：** `ASTRAL_TARGET_KV=f16|fp8_e4m3_h128|int8_g64`。未设置时F16；未知值直接错误。它不控制DSpark/DFlash2 KV，日志也分别显示target与draft精度。首轮不新增十几个独立开关。

**验收：** 同C下实际global KV payload分别等于16640C/16896C（额外对齐单列），local仍为最多480MiB；F16关闭开关后回到既有分配与数值路径。不存在隐藏的全C FP16 shadow。

## 5. 任务3：实现统一写入和可回滚状态

**修改：** `crates/kernels-src/cu/inkling.cu` 的attention prep/write路径及Rust wrapper；`crates/model/src/inkling.rs` 的step、prefill、spec verify调用。[P01][P02]

### 5.1 写入链路

顺序固定为：短卷积输出 → K L2 clipping / V RMS normalization → 原FP16 cache值的舍入 → 按token/head/group编码 → 写K/V codes和scales → attention读取同一位置。

实现可融合进已有kernel。先保证语义一致，再在profile证明有用时融合，不能为了一个额外launch省事而保留整个上下文的F16副本。

- [ ] Q/R的learned scale、clipping与全局tau位置保持不变；不得给K/V施加Q的长度缩放。
- [ ] 同一prep函数族覆盖step=1、verify=1..8、prefill=1..2048。
- [ ] K/V对应的scale写入完成后同stream reader才可见；graph replay不读取前一请求的scale。
- [ ] 推测round写入的candidate行只在相应逻辑position可见；拒绝后按现有流程重置valid end和conv历史，下一次覆盖未接受行。
- [ ] 禁止编码一个token时修改同page旧token的scale。这使首轮回滚不需要恢复历史量化元数据。
- [ ] 保持当前短卷积rollback的原精度与顺序；KV压缩不顺带压缩conv、features、draft checkpoint。

### 5.2 必须写明的提交语义

对已提交范围`[0, committed_end)`，量化bytes与scales不因拒绝分支改变。候选范围`[committed_end, tentative_end)`可以被覆写；未接受token不可留在后续attention可见集合里。所有产生输出的reader以自己的query position与valid bounds构造因果范围，不能用“当前物理buffer已写到哪里”替代。

首轮每行独立scale天然适合此约束；KIVI式跨token共享scale与ResidualQuant式后到anchor不属于这个实现。[P07][P09]

## 6. 任务4：完整覆盖attention reader

**修改：** `crates/kernels-src/cu/inkling.cu` 的split/merge/prefill attention、`crates/kernels/src/inkling.rs` 的dispatch/workspace，以及 `crates/model/src/inkling.rs::Session::probe_report`、`crates/model/src/inkling/probe.rs` 的诊断读取。协调K15，避免两个分支各自重写一套split策略。

| 路径 | 必须覆盖 | 基准方式 |
|---|---|---|
| decode | 1行query，所有已提交历史 | 同encoded KV的高精度attention oracle；再对比原F16质量 |
| verify | 1..8行，含不整齐尾部 | 固定输入与KV状态，逐行decode对比；接入T45契约 |
| prefill | 1..2048行，多chunk | 真实因果mask、ring wrap、跨chunk边界 |
| split/merge | 不同split数与长C | 归约完整性、sink只计一次、workspace上界 |

### 6.1 第一版选择

在寄存器/shared memory tile内把Q8解码到现有算术所需类型，保持当前QK、PV与归约逻辑。一次加载K/V尽量供同KV head的3个query heads复用。不得把整个C反量化成另一个全量FP16 cache；临时tile必须在memory report中有上界。

需冻结一个容易遗漏的舍入契约：现有prefill使用F16输入、F32累加的MMA，`float(code)*float(scale)`未必可精确表示为F16。首版固定 `reader_math=dequant_f16_rn_v1`，不再新增用户开关：`raw_decode=F32(code)*F32(stored_scale)`，`effective_KV=F32(RN_F16(raw_decode))`。这里的`F32(code)`表示按有符号INT8或E4M3规则解码后的数值，不是把FP8字节直接转整数。decode/verify/prefill读取相同的KV有效值；CPU同时提供raw与effective两层参考，分别报告codec误差和额外F16舍入误差。该契约不意味着完整attention逐位一致，现有prefill仍有Q、概率与归约顺序的差异。未来如将scale移到QK/PV中而跳过RN-F16，作为独立reader模式重跑T45与质量门。

FP8在第一版表示**存储精度**；不同时改成FP8 QK/PV Tensor Core算法。后者只有在独立数值与端到端收益成立后再立项。[P10]

### 6.2 attention语义契约

- scale应用到正确K/V group；RPE用绝对distance，距离≥1024的bias为零。
- query-dependent sink遵循现有公式：真实key分数减sink，另有一次零logit、零value项；它不能在每个split重复添加。
- gate sigmoid仍在attention输出之后；output projection与最终vocab softcap保持原顺序。
- split归约对同一组encoded K/V按已有数值门验收；如果改归约顺序，显式报告改变，不能归咎为“量化天然误差”。
- 关闭量化时dispatch回原F16路径。调试用MAX_CTX=8192的简化kernel不得在大C配置中误启用。

### 6.3 两种误差必须分离

**实现误差：** 用同一encoded KV，先核对raw codec解码，再由CPU或离线F64 oracle在规定的effective KV上重建attention；GPU结果应通过浮点归约容差。错误scale、position、sink属于实现bug。raw到effective的舍入增量独立统计，不用旧FP16回调把它隐藏。

**近似误差：** 用同一原始FP16 KV，比较量化与未量化模型输出、logits、任务质量；这属于codec选择。不能用放宽实现容差代替质量评估。

### 6.4 probe必须理解codec与query视图

当前 `ReportIn::kv` 回调返回 `Vec<u16>`，`probe_report` 按FP16读取缓存。新实现必须让回调显式返回codec-aware的F32解码值或带格式的snapshot，并保留原codes/scales供精确核对；禁止把Q8 bytes当half，也不能只为沿用旧接口而把raw解码值额外舍入后冒充codec oracle。

诊断输出同时记录codec、reader算术模式、slot、绝对query position、key position范围。到Q4-far阶段，oracle按每个query的p/j选择FP16 near或Q4 far，再按已登记算术模式重建attention；不能一律读取Q4解码值。单次probe对大C可分块读取/归约以限制host峰值，不把诊断全量snapshot常驻在GPU上。[P01][P02]

微基准记录read bytes、scale/decode成本、registers、occupancy、global load、kernel time。最后只以完整请求收益决定是否默认采用，不能从cache bytes减半直接写“速度翻倍”。

## 7. 任务5：状态、边界与batch行为验收

**修改/新增测试：** 各crate中与KV读写/dispatch相邻的定向测试；lab新增 `tools/t44/kv_state_cases.json` 与 `tools/t44/kv_judge.py`。这些是计划路径，当前不存在不代表已完成。

### 7.1 最小覆盖矩阵

| 维度 | 取值/构造 |
|---|---|
| group/tile边界 | 63/64/65；127/128/129 |
| 局部窗口 | 1023/1024/1025 |
| 默认ring边界 | 3071/3072/3073，以及两次以上wrap |
| prefill chunk | 1、7、8、63、64、127、128、1024、2048；同输入不同分块 |
| verify | 1..8行；draft k=1..7；全接受、零接受、每个中间接受长度 |
| 模式 | plain、DSpark、DFlash2、请求级双草稿选择 |
| 重用 | A→reset→B→reset→A；B使用完全不同token分布 |
| 容量边缘 | 最后一行、最后8行、应拒绝的超界请求 |
| 布局 | F16、FP8-head、INT8-g64；8个global逐个验证 |

- [ ] 用可控draft强制每个接受/拒绝长度，核对已提交KV hash、conv状态与后续logits。
- [ ] 同一固定QKV输入的编码不依赖batch shape；端到端decode/verify沿用K12/T45已确定的契约，新增误差不能被宽松门隐藏。
- [ ] prefill与decode不强行声称天然逐位一致；使用既有经过负控校准的数值门，并单列新KV造成的增量。
- [ ] CUDA graph捕获/切换在正确codec和buffer地址上重放；检查双草稿request边界交换后的reset。
- [ ] 不添加请求中途切换draft或codec。当前设计不具备无代价迁移全部草稿因果历史的机制。
- [ ] 检查负控：错scale、交换global slot、错误valid end、重复sink、漏掉一个量化group，都应至少被一个精确测试或质量门识别。

**验收出口：** 实现错误为FAIL_IMPLEMENTATION；漏数据为INVALID。只有两者清零，才允许把后续logits差异解释为有损量化质量变化。

## 8. 任务6：受控放开132096上限

**修改：** `crates/model/src/inkling.rs::MAX_CONTEXT/Session::new`、`crates/cli/src/main.rs` 的配置校验，以及API请求长度检查。当前真实上限是132096；不是简化调试attention的8192。[P01][P02]

### 8.1 分离默认值、受支持上限与实验上限

- [ ] 保持现有默认context；仍使用现有CLI参数 `--ctx`，不发明已经存在的 `--ctx-size`。
- [ ] 拟新增 `ASTRAL_ALLOW_EXPERIMENTAL_CONTEXT=1` 作为超过当前验证上限的明确实验开关；没有它仍拒绝未验证的大C。
- [ ] 实验硬上限先设1,048,576，而不是取消所有范围检查。每个passed profile记录自己验证到的最大C，不能一处PASS让所有codec/draft自动获得同上限。
- [ ] 检查target、draft的`capacity+16`、workspace、graph shape、position转换和kernel循环；内部bytes运算用checked usize/u64。
- [ ] API在launch之前检查`prompt+已有上下文+max_new_tokens+推测安全余量≤C`；不足时给出清晰错误，不能silent clamp、截断prompt或把超界读当成正常EOS。
- [ ] 大C路径禁用仅支持8192的诊断kernel；诊断需要时明确报“不支持该长度”，不能换一个错误实现继续跑。

### 8.2 上探顺序与真实输入

| 模式 | 首轮容量点 | 后续点 | 条件 |
|---|---|---|---|
| plain + KV8 | 128Ki →192Ki | 224/240/256Ki | 质量/峰值/真实prefill均通过 |
| 单DFlash2 + KV8 | 128Ki →192Ki | 224/240/256Ki | 独立测固定草稿开销，不能套用plain预算 |
| 单DSpark/双草稿 | 128Ki | 按实测预算逐级 | 额外4096C斜率仍存在 |
| KV4后续 | 256Ki | 384/512Ki | 任务10完成 |
| 新权重+KV4 | 512Ki | 768Ki/1Mi | 任务9、10完成，任务11单独验收 |

容量C与prompt长度P分开记录。容量smoke可以用64-token prompt，但不能产生“长输入已支持”结论。真实测试P建议为`C−4096−guard`，保留至少4096 token终答预算；guard按实际verify最大步长固定，不能让最长prompt占满全部可输出空间。

同时保留32K/64K/128K共同输入点，用来比较原路径和新路径。每个新C至少有真实自然文本、中文/中英混合、代码或多文档任务，不能只重复一个词来填满cache。

### 8.3 prefill和延迟的独立门

global attention在真实输入长度N上仍有二次项。用32/64/96/128Ki及已通过的新长度拟合`T_prefill(N)=aN+bN²+c`，报告拟合残差与测量范围；禁止跨很远长度只给单点承诺。首轮记录每chunk耗时，定位global attention、controller、expert GEMM与pack成本。

为避免无限消耗GPU，试验前固定单请求预算。可采用以下**离线长文研究档的初始预算建议**：256Ki prefill≤180秒、512Ki≤600秒、1Mi≤1800秒。这些是人为的试验继续条件，不是模型能力或交互产品SLO；实际需要可在实验前调整，并记录理由。达到预算上限中止为BUDGET_EXHAUSTED，不能以截短输入后PASS替代。

交互档必须单独满足其TTFT目标；容量档达到1Mi但首字很慢，只能标记离线容量用途。仍保留K13的原优先级与后续prefill优化，不把它塞进KV8首版一起重写。

## 9. 任务7：质量、吞吐与价值判定

**拟新增：** `tools/t44/kv_eval.py`、`kv_profile.py`、`rules_kv8.json`、`cases/`。  
**复用：** T25数值门、T45 batch行为、T46 top-2048+tail筛选与现有G2/T21协议；它们各自的原始范围与限制保持可见。[P05][P06]

### 9.1 两级样本，不把小样本写成非劣证明

**开发筛选集：** 每域32–64个短任务，32/64/128Ki各若干长任务，短语料PPL与固定位置full-vocab logits。只用于淘汰明显差的codec，不产生正式“质量无损”结论。

**冻结留出集：** 覆盖中文说明/信息提取、英文与混合文本、代码理解/修改、数学推理、多文档多跳、变量或状态追踪。优先选有程序化或盲评规则的任务；最终评分只看最终answer字段是否完成要求，reasoning中出现关键字不算成功。

每个需要非劣结论的域在试验前选择固定N（例如256、512或1024），依据pilot的配对差异方差与目标margin估算功效。不得反复查看普通95%区间并在第一次通过时提前宣布成功。若要顺序检验，必须预先登记alpha spending或confidence sequence；否则中途只因明显伤害/无效停止，正式结论在预定N产生。

大长度任务成本更高。256/512Ki/1Mi先用8–32个多样化case验证可执行性与显著失败；若预算不足以达到正式质量置信度，状态就是QUALITY_PILOT或INCONCLUSIVE，而不是“完整长上下文支持”。校准集、调codec开发集与留出集必须不同。

### 9.2 比较基线与长长度参考缺口

首轮共同长度≤128Ki，以同一A1、F16 target KV、同一prompt/seed/输出预算为质量基线。量化后的plain与量化后的spec在同一target下比较推测正确性；不能要求它们逐token等于原F16目标。

超过当前F16 GPU容量，必须明确参考从哪里来：

1. 可用同A1的辅助后端CPU/offload运行同长度F16参考，记录其数值差异，并先在共同长度建立跨后端对照。
2. 64GB RAM不能无条件承诺1Mi F16参考可跑：target全局KV已约32GiB，再加权重、local KV、工作区、运行时和OS可能逼近或超过可用内存。先测RSS与峰值，不以swap失控的结果做速度比较。
3. 如另有足够内存/显存资源，可使用；本计划不假定用户已有更大GPU，也不把租用资源设为默认前置条件。
4. 选定position的离线attention oracle能证明reader正确，短长度F16对齐能证明共同范围质量；二者都不能单独证明1Mi完整模型与F16非劣。
5. 缺少可运行的同长度参考时，记录gold-task绝对成绩、终答与重跑一致性，并把“相对F16质量”标记INCONCLUSIVE。不得用另一个量化模型当作等价无损参考。

### 9.3 数值与任务门

| 指标 | 首轮KV8建议门 | 说明 |
|---|---|---|
| 数据完整性 | 预期case/position/hash全部匹配 | 缺失即INVALID |
| 同codec实现正确性 | CPU/GPU byte与scale一致；reader通过浮点归约门 | 不和原F16近似误差混合 |
| PPL | 相对增量≤0.5%，每域单列 | 初始工程门，非通用行业标准 |
| KL | top-2048+tail用于筛选；晋级者抽样全词表复核 | 不把旧分布0.43%差异移植为新分布误差界 |
| 任务成功率 | 配对95%单侧置信下界≥基线−2pp | 逐域报告；多域判定控制多重比较 |
| 截断/重复失败 | 增量的95%单侧上界≤1pp | 样本不足不作无退化承诺 |
| 最终答案 | 确实进入answer、格式正确、满足任务 | reasoning命中与空answer单列 |
| 推测性能 | 接受token/round、draft时间、verify时间、拒绝率 | 目标变了，不能假设旧接受率不变 |

二分类配对结果保存四格计数；用预先选定的配对比例差区间，不能把两组独立二项区间硬相减。连续指标可按case配对bootstrap，固定seed与重采样数。小样本零失败也需上置信界；例如几十个全过case不能证明失败率变化小于1pp。

代码任务尽量运行冻结测试用例；事实/检索用精确或容错解析器；开放回答采用盲评与固定rubric，保留分歧。不得用同一个被测模型给自己的量化输出打分作为唯一证据。

### 9.4 性能矩阵与计时协议

共同容量/输入点：8K、32K、64K、96K、128Ki；模式为plain、单DSpark、单DFlash2、双草稿，均在各自能容纳的点运行，不强行让一个OOM配置参与平均。

先对plain和实际常用草稿模式做pilot，晋级者再完成四模式回归。固定GPU功率/时钟策略、温度区间、后台占用；随机AB/BA顺序。常规点2次warmup+5次独立repeat；高成本真实长输入在预算内至少3次，达不到就报告样本不足及原始波动。

必须同时输出：

- 现有T21兼容的“每prompt中位数再求均值”，便于与222.5/251.4/257.6同口径对照。
- 总生成token/总wall time、TTFT、prefill tok/s、decode tok/s、完整请求时间及p50/p95。
- 每次请求的input/output长度、正确终答与停止原因；`ignore_eos`固定长度只用于速度，不计作任务完成。
- 目标attention split/merge/pack、expert、draft、verify的时间分项，以及草稿接受效率。
- 峰值显存与剩余显存；分别覆盖加载、graph、prefill、decode，不能只测空session。

默认mixed workload的权重在run前冻结；32短+8长的T21是80%短prompt，不代表用户所有未来任务。新长上下文profile独立列出，不混进旧平均数让结果看起来更快。

### 9.5 正式决策

| 状态 | 必须满足 |
|---|---|
| PASS_SPEED | 质量/状态通过；64–128Ki完整decode≥10%收益且配对区间支持收益；短桶回退≤3%；完整请求时间无未披露恶化 |
| PASS_CAPACITY | 真实新长度prefill+生成+质量通过；共同长度完整请求回退≤5%；显存余量≥0.75GiB；标明交互/离线用途 |
| NO_BENEFIT | 实现正确，但收益没有达到预注册用途门；保留研究结果，默认不切换 |
| QUALITY_FAIL | 实现已验证，近似损伤仍超门；保护敏感visit或退回高精度 |
| FAIL_IMPLEMENTATION | 状态、codec、batch或越界错误 |
| INVALID | 数据/身份/输入/position不完整或错位 |
| INCONCLUSIVE | 参考、样本或统计功效不足 |
| BUDGET_EXHAUSTED | 超过预先登记计算/时间预算 |

容量型收益不要求一定速度提升，但必须明确其代价。一次PASS只适用于所记录资产、codec、draft、C、实现版本和任务范围。

## 10. 任务8：T31先做外部权重筛选

### 10.1 第一批只评两款

| 候选 | 固定revision | 首轮用途 |
|---|---|---|
| GSQ-RCO IQ3_S | `f0da1097633dd7c2f5733e4077cff861be122245` | 质量/容量主候选；约10.641GiB文件 |
| AP Q3_K_XL | `94a178b6dad70c9ecee7784cd4a9b9ebfa383f6c` | native成本对照；约12.696GiB文件，保留32个NVFP4张量 |

若两者均不能满足容量目标，再以GSQ Q2_K_XL、AP IQ2_XXS作为第二批。kaiPTQ和EXLR8有独立编码runtime，保留为研究比较，不与普通GGUF port混成第一项任务。[P11][P12][P13]

### 10.2 先冻结格式清单

拟议asset manifest至少包含：tensor name、shape、dtype ID、block size、block bytes、payload bytes、外部scale、作用模块、embedding/head标记、是否共享、所需执行行数、当前runtime是否支持。

统计按**参数/字节/实际调用成本**汇总，不能仅按tensor数量估工作量。GSQ IQ3_S需要12个当前loader未支持的格式；四款GSQ/AP合并需14个，但不要求一次全做。GSQ Q2_K_XL实际没有Q2_K；AP外部 `.scale` 已有发现/上传机制，应复用验证。[P01][P11][P12]

### 10.3 外部runtime也要先验格式

现有T31的b12751不能被假定支持所有新格式，尤其id42的Q2_0。先用完整metadata和一组tensor oracle核对辅助runtime的真实支持，再固定其commit与binary hash。若必须用新llama.cpp或fork：

- 保留b12751作为G2参考身份。
- 在新辅助runtime上重跑同一A1，再与新候选配对；不能把“新runtime+新权重”对旧A1runtime的差异全部归给量化。
- kaiPTQ只能用其对应kaiLLM兼容路径；`.gguf`扩展名不证明普通llama.cpp可读。

### 10.4 进入native port的条件

- [ ] 短留出集和32–128Ki任务没有超出预先登记质量预算；极低位候选可以提不同预算，但不得事后改门解释失败。
- [ ] 完整闭包的驻留估算预计至少节省2GiB；保护张量、embedding、pack复制都已计入。
- [ ] 全格式CPU decode与权重语义可获得可核查参考，许可证/来源信息可随资产记录保留。
- [ ] 与不换权重的KV8路线相比，有明确额外容量或端到端价值。
- [ ] 选择一款；若均不通过，结论为T31当前NO_GO，继续A1+KV路线，不因已调研而强行接入。

GSQ/AP上游成绩只用于候选排序，不能直接当本项目验收。GGUF解码到BF16外部评测能检验保存的量化权重质量；它不验证本项目packed kernel的性能或误差。[P11]

## 11. 任务9：只实现选中资产的完整native闭包

### 11.1 修改位置与职责

| 位置 | 最小职责 |
|---|---|
| `crates/quant/src/lib.rs`及必要子模块 | dtype ID/layout、精确CPU decoder、codebook与block边界 |
| `crates/loader/src/lib.rs` | 完整GGUF tensor range/shape/block检查，未知类型错误提前 |
| `crates/model/src/inkling.rs::Loader::mat` | 资产支持清单、外部scale传递、明确fallback策略 |
| `crates/kernels/src/ops.rs` | packed matrix上传、dispatch、bytes与临时workspace计数 |
| `crates/kernels-src/cu/gemv.cu` | SM89 decode GEMV、小批矩阵、grouped expert路径 |
| `crates/kernels-src/cu/inkling.cu` | embedding读取等目标专用调用 |
| `crates/model/src/dspark.rs` | 新target head的Markov folding与派生状态重建 |
| `crates/model/src/dflash2.rs` | 新target embedding/head、mask row、top-16/selector回归 |
| `crates/model/src/inkling/probe.rs` | 新head的lens activation plane、codec-aware KV参考与诊断 |
| lab `tools/t31/` | format oracle、asset identity、四模式质量与性能 |

实际文件拆分依当前HEAD调整；不能因为本文列出新模块就机械扩建框架。保留已有NVFP4/Q8_0快路径。

### 11.2 先CPU解码，再GPU执行

- [ ] 从固定上游格式定义复制必要的常量/解码语义并记录来源与版本；不能按近似公式自行猜IQ codebook。
- [ ] 每种格式验证zero、block边界、负值、scale、codebook索引；实际tensor按固定seed抽block，并对数个完整小tensor与参考decoder逐值比较。
- [ ] Q2_0使用id42、64值/18byte布局，不按Q2_K的84byte/256值解释；expert-down K=1152要求正确分块，不能无声截尾。[P14]
- [ ] AP的NVFP4外部专家scale应用顺序沿用现有机制并与参考输出核对；测试非1 scale以免漏乘仍“看起来能跑”。
- [ ] 首个GPU版本优先保持原始量化值的等价pack；tile内decode到现有SM89可用算术。禁止调用仅SM120/Blackwell可用路径后宣称4090支持。
- [ ] 很少量冷门格式可以暂用明确记账的F32展开路径来闭合功能，但必须设置bytes预算并在结果写出；不能把大部分模型整体展开。它仍是待实现的执行fallback：现有 `launch_items` / `launch_mma` 并不因loader接受F32就自动支持F32矩阵，必须补dispatch、所需activation与数值对照，不能直接交给旧入口。
- [ ] 若展开为BF16/F16引入舍入，或重新量化为NVFP4/Q8_0，登记为新派生资产，重新做质量门。只有保持参考解码值的重排/表示转换才可称等价转换。

首版native要获得完整可运行资产，不必让每个少量tensor都达到最优kernel；但要保证原始低位模型的主要驻留节省真实存在，并按热点优先优化。

### 11.3 行数与调用形态的闭包

| 路径 | 需覆盖的形态 |
|---|---|
| 普通decode | 1行，dense/attention/head/专家 |
| verify | 2–8行，各专家token列表、重复/空专家、尾部 |
| prefill | 1..2048行，非整tile、K=1152/2304等真实shape |
| DSpark初始化 | `rank+1`行的target LM-head folding，通常65行 |
| DFlash2初始化 | target embedding的mask token、embed norm |
| DFlash2运行 | target head 1..7行、top-16、selector、vocab padding |
| 输出/调试 | full-vocab logits、普通/全层/verify probe一致 |

不要只为1、8、2048行写dispatch而遗漏65行启动路径。新权重改变target embedding/head后，重新构造所有目标相关派生表；未来若缓存这些表，cache key至少包含target完整hash、相关head/embedding hash、draft hash、算术/布局版本。当前若只在内存构造，则不需要凭空实现持久化缓存。[P03][P04]

还需审计activation plane：当前两套draft的一些head输入及probe的`lens_qa`使用 `QAct::new`，没有F16 plane。如果新格式依赖F16/BF16 MMA，就必须为这些调用补正确的F16输入与量化/更新路径，并计入显存；或者实现明确可验证的F32/量化activation reader。`QAct::with_f16`在某些target路径存在，不代表所有draft/probe路径都已经具备所需buffer。head、65行fold、1..7行draft输出和lens都要实际执行验证。

### 11.4 native验收与取舍

- [ ] 同一选中资产先对齐辅助runtime的质量与固定logits，再与A1比较，不把decoder bug误判成“低位损失”。
- [ ] 在F16 target KV下测新权重，隔离权重效应；然后才与KV8组合。
- [ ] 分别测plain、DSpark、DFlash2、双草稿的加载/内存/接受率/速度；某模式不支持时应明确拒绝配置，不默默关闭draft。
- [ ] 全部实际权重驻留至少比A1减少预注册目标（首轮建议≥2GiB）；只有文件变小不算通过。
- [ ] 共同长度性能可以形成速度型或容量型profile；复杂decode造成退化时，不用压缩率替代结论。
- [ ] 一款失败后先判断是质量、format成本还是kernel瓶颈；最多再评一个有不同工程理由的候选，避免无界扩展14格式。

如果最终转回NVFP4/Q8_0，只能把它交付为“新校准来源的派生权重”实验，不能宣称已经兑现原2–3bit权重的容量。

## 12. 任务10：远历史KV4及512Ki

**进入条件：** KV8的布局、状态、graph与评估已稳定；K15/K13后续变更已重新建立对应基线。首个KV4候选为对称INT4-g64，K/V独立FP16 scale；INT4-g32作为质量对照，不先做2bit。

### 12.1 两个显式候选

**Q4-all：** 所有global历史都用Q4，当前query可见的近端也读Q4。它是最简单的低位基线，用来隔离codec本身。

**Q4-far：** 全局每个位置保存Q4 codes/scales，同时保留固定长度FP16 hot ring。对每个query p，按逻辑距离选择：`0≤p−j<1024`读取FP16；更远历史读取Q4。局部40visit继续原FP16 ring。

这里**不能**用“某page恰好被后台压缩了吗”决定精度，否则同一token会随prefill分块/推测接受长度改变数值路径。为保证确定性，首版在写入每个token时同时生成其Q4表示与FP16热区值，reader按`p,j`选择；即使该行仍留在热区，远距离query也必须读它的Q4表示。

global hot ring采用与chunk兼容的保留量：`roundUp64(1024+max(tmax,8))`，默认3072行。8个global的额外FP16 K/V约96MiB；这不是全C shadow。Q4全容量仍按8704C bytes计，热区重复编码、scale、padding分别计入预算。

### 12.2 pack与提交

- [ ] INT4取值范围、nibble顺序、group64、FP16 scale舍入写成与任务1同级规范；不用不同kernel各自约定高/低4bit。
- [ ] 读写仅按合法row和group，不以对齐为由读取越过capacity的token；tail在kernel内mask。
- [ ] codes与hot ring的写入复用任务3提交语义。per-token scale不修改旧行；拒绝后无须回滚旧page的共享scale。
- [ ] 若后续为了pack效率改成page128/256，page只组织存储，不能改变每个query应读FP16还是Q4的逻辑规则。
- [ ] 任何异步压缩或只在eviction时编码的优化，都必须证明等价于确定性视图，并重跑不同chunk/接受长度测试；做不到就不合入。

### 12.3 远近attention合并

对far与near分别计算未归一化统计`(m,l,u)`：最大logit、减去该max后的exp总和、同权重的value和；两边都不重复加入额外sink。最终令：

\[
m=\max(m_f,m_n,0),\qquad
l=e^{m_f-m}l_f+e^{m_n-m}l_n+e^{-m},
\]

\[
o=\big(e^{m_f-m}u_f+e^{m_n-m}u_n\big)/l.
\]

真实key的logit仍使用当前“减query sink”的定义，额外零logit/零value项只通过`e^{-m}`加入一次。空far/near使用显式空分支，避免`−∞−(−∞)`产生NaN。这个合并是数学恒等式，浮点顺序变化仍需数值验收。

若进一步借鉴SRFT/旋转V，far累计的value和必须先变回与near相同坐标系，再合并；或将两侧都保持同一变换域。最终gate/output projection前恢复原坐标，不能把不同基底的两个向量直接相加。[P08]

### 12.4 512Ki的继续条件

按旧基线情景，A1+Q4-g64在512Ki约23.056GiB，不含96MiB hot ring与新增开销；加热区后约23.15GiB。这个余量很薄，任何pack workspace/graph增加都可能影响0.75GiB保留门。INT4-g32更紧。先plain，带DFlash2需要重新测；不承诺A1+draft一定能容纳512Ki。

若质量失败，优先尝试：K8/V4、个别global visit保留Q8、group32或更大的near范围；每次只改一项。增加保护精度后的实际bytes/token重新计算，不继续沿用8704C预算。

若速度失败但容量有价值，按PASS_CAPACITY保留。若容量门也不过，进入已通过的低位权重组合，而不是直接降到2bit以追数字。

## 13. 任务11：组合、混合精度与1Mi研究

### 13.1 四臂组合，避免误差归因混乱

| 试验臂 | 权重 | target KV | 用途 |
|---|---|---|---|
| A | A1 | F16 | 原始基线，共同可运行长度 |
| B | 新权重 | F16 | 单独权重影响 |
| C | A1 | 新KV | 单独KV影响 |
| D | 新权重 | 新KV | 最终组合与相互作用 |

长长度无法运行A/B时按任务7记录参考缺口，不伪造四臂齐全。新权重会改变KV分布、Q长度敏感性、routing和草稿接受率，因此需重新校准scale与混合精度分配。

容量逐级512Ki→768Ki→1Mi。长profile优先单DFlash2：其KV为固定局部ring；不需要DSpark时不把整套DSpark常驻。双草稿在1Mi额外保留的一份DSpark global KV就约4GiB，不能忽略。[P03][P04]

如果新权重实际驻留≤11GiB，旧基项外推的新权重+Q4-g64+1Mi、无草稿情景约22.0GiB；加热区、DFlash2和新workspace后必须重新测。这说明存在合理空间，不是某个10.641GiB文件已经能跑1Mi的证明。

### 13.2 按visit混合精度

先测八个global visit的单点敏感性：每次只把一个visit的K或V从Q8改Q4，记录长位置score/logit/任务变化、bytes与实际reader成本。搜索空间先限`F16/Q8/Q4`，K/V可不同，按内存预算挑少量候选再联合重测。

不预设最后一遍必然最敏感，不假设单点误差可直接相加；Q的tau随位置增长，128K以下的排序也要在更长位置复核。LoopKV可借鉴的是这个成本/敏感性分配方法，不是其在其他模型上的共享策略。[P09]

### 13.3 SRFT与残差的研究门

SRFT的远近拆分、旋转与GQA复用值得借鉴，但其大长度计时由直接构造cache获得。移植SM89前，分别验证旋转开销、codebook读取、真实prefill、V norm偏离、gate顺序和每个global visit质量。[P08]

ResidualQuant式最后pass anchor只可能先研究core中的两个global物理层11/17的三次visit；prelude/coda不能按同一逻辑共享。需要先回答：

- 对当前query可读的历史token，其最后pass anchor是否已经完成并提交？
- 对一个大prefill chunk，早期pass读取同chunk较早token时，是否会依赖尚未产生的最后pass anchor？
- 使用近端FP16、缩小chunk或延迟编码能否维持相同因果与数值定义？由此增加的scratch和prefill成本是否吃掉收益？
- 推测拒绝后anchor、残差、conv历史能否一起回到相同committed state？

原公开runner对chunked prefill/prefix有限制，不能直接当drop-in。先做只读相关性/残差统计；没有明确存储收益与因果方案就停止，不启动复杂实现。2bit KV同理：把它作为KV4失败后的研究选择，而不是首轮1Mi捷径。

### 13.4 1Mi结论的用语边界

| 最强实际证据 | 可写结论 |
|---|---|
| 分配成功，短prompt运行 | 支持1Mi容量配置的smoke |
| 直接构造KV后decode | 1Mi attention reader性能实验 |
| 真正1Mi级输入prefill完成 | 真实长输入可执行，附TTFT/峰值 |
| 少量任务终答通过 | 1Mi任务pilot，限定样本/领域 |
| 冻结任务、参考与统计门通过 | 在列明资产/配置/任务域内通过1Mi验收 |

首字时间、有效终答率、每个正确答案耗时必须一并交付；不能只展示最好看的decode tok/s。

## 14. 可执行命令约定与证据包

以下为**后续实现完成后的执行模板**。实际路径/模型由run manifest提供；新脚本和开关均需先按前述任务实现。本文没有执行这些GPU命令。

### 14.1 现有命令可复用的部分

```bash
export ASTRAL_BIN=/absolute/path/to/astral
export A1_MODEL=/absolute/path/to/Inkling-2-Mini-UD-Q4_K_XL.gguf
export RUN_DIR=/absolute/path/to/run-directory

"$ASTRAL_BIN" version
"$ASTRAL_BIN" hw
"$ASTRAL_BIN" gguf-info "$A1_MODEL" --tensors
"$ASTRAL_BIN" selftest
"$ASTRAL_BIN" trace "$A1_MODEL" "$RUN_DIR/trace-manifest.json" "$RUN_DIR/trace"
"$ASTRAL_BIN" dump-final-logits "$A1_MODEL" "$RUN_DIR/logits-manifest.json" "$RUN_DIR/logits"
```

上面的`trace`/`dump-final-logits`使用各自已有manifest schema；新run manifest负责引用它们，不把两个格式擅自合并。现有CLI与含义见[P15]。

### 14.2 拟新增脚本的最小接口

```bash
# 在lab根目录；这些脚本须先实现
python3 tools/t31/asset_manifest.py \
  --model "$A1_MODEL" --out "$RUN_DIR/asset.json"

python3 tools/t44/memory_report.py \
  --manifest "$RUN_DIR/run.json" --out "$RUN_DIR/memory.json"

python3 tools/t44/kv_eval.py \
  --manifest "$RUN_DIR/run.json" --phase state --out "$RUN_DIR/state"

python3 tools/t44/kv_eval.py \
  --manifest "$RUN_DIR/run.json" --phase quality --out "$RUN_DIR/quality"

python3 tools/t44/kv_profile.py \
  --manifest "$RUN_DIR/run.json" --out "$RUN_DIR/performance"

python3 tools/t44/kv_judge.py \
  --manifest "$RUN_DIR/run.json" --rules tools/t44/rules_kv8.json \
  --results "$RUN_DIR" --out "$RUN_DIR/verdict.json"
```

脚本应在缺输入/缺数组/identity不匹配时非零退出；quality与speed分开输出，不以脚本rc=0自动推断所有门通过。运行manifest schema至少固定以下字段：

```json
{
  "schema_version": 1,
  "engine": {"commit": "...", "binary_sha256": "...", "dirty_diff_sha256": "..."},
  "assets": {"target_sha256": "...", "draft_sha256": "...", "tokenizer_sha256": "..."},
  "config": {"passes": 3, "target_kv": "int8_g64", "reader_math": "dequant_f16_rn_v1", "capacity": 196608,
             "draft_mode": "dflash2", "prefill_tmax": 2048, "spec_k": 6},
  "data": {"manifest_sha256": "...", "split": "holdout", "expected_cases": 0},
  "protocol": {"seed": 1, "warmup": 2, "repeats": 5, "max_new_tokens": 4096},
  "rules": {"file_sha256": "...", "time_budget_seconds": 0}
}
```

这是schema形状示例；`...`与0占位不可直接用于正式跑数。输入校验必须拒绝这些占位值，并按case列出真实position集合。多draft配置用显式数组及各自hash，不将两个不同checkpoint折成同一字段。

### 14.3 每个候选的提交包

最少保存 `run.json`、`asset.json`、`memory.json`、`cases.jsonl`、`metrics.jsonl`、`verdict.json`、命令/环境记录、数值样本/摘要、代表性完整输出、失败样例与profile分项。

`verdict.json`必须列：门版本、数据完整性、实现正确性、质量、显存、速度、TTFT、适用profile、未完成项。摘要可很短，但原始case级证据必须能解释每一个最终状态。

## 15. 工作量、资源预算与停止点

以下是工程范围估计，不是已验证工时或交付承诺。假设执行者熟悉当前Rust/CUDA代码，能在独立分支开发并获得单卡串行验证时隙。

| 阶段 | 工程量级 | 初始GPU预算建议 | 停止点 |
|---|---|---|---|
| 任务0–1 | 小，CPU为主 | 仅少量真实KV样本抓取 | 数据/codec未冻结不继续 |
| KV8完整路径与状态门 | 数天至两周级，随K12/T45接口稳定性变化 | pilot≤4 GPU小时，晋级后单profile≤16小时 | 两轮明确修正后仍无质量/用途收益，保留结果并停止扩面 |
| T31两款外部筛选 | 小至中 | 初筛≤8 GPU小时；正式质量另登记 | 两款均无优势则不做native |
| 单资产native闭包 | 数周级；复杂IQ多类型不能按“一种格式”估算 | 每次只profile一个热点/候选 | 节省不足2GiB或质量失败则停 |
| KV4与512Ki | 中至大 | 按真实prefill计时先pilot，再定留出预算 | 热区/保护精度吃掉容量则转低位权重组合 |
| 1Mi、旋转/残差 | 研究项目 | 先少量真实case；正式统计预算独立登记 | 参考/终答/时间不够即INCONCLUSIVE，不持续堆实验 |

正式长任务统计可能远超pilot预算：若一个1Mi请求需要数十分钟，数百个case和多臂对照将需要大量GPU时间。必须先用TTFT与pilot估算总预算，不能在计划里把“几十分钟容量演示”当成“完整质量验证”。

每次扩大预算都以已完成的具体结果为依据；执行时不因本方案存在就自动进入所有后续研究阶段。当前用户要求的是评估和文档，代码与GPU执行属于未来工作。

## 16. 首个可交付里程碑

建议第一个可合入成果严格限定为：**A1不变、三遍不变、8个global visit可选FP8/INT8、40个local保持FP16；decode/verify/prefill和回滚全部覆盖；128Ki共同长度质量与性能报告；plain 192–256Ki及单DFlash2逐级容量报告。**

只有该里程碑通过，再为T31选中的一款权重补原生格式闭包；只有真实长期质量与内存证明需要，才进入KV4/混合精度。默认切换、支持长度上调与实验性profile应各自有明确证据和单独提交，便于回滚与归因。

## 来源与契约依据

本文的接口、阈值、任务划分和预算是设计建议；当前状态与数值语义来自以下固定源码。完整论文比较、模型格式清单、显存推导和证据限制见配套评估报告。

- [P01] [Engine Config/Loader/Session/Spec](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/model/src/inkling.rs)。
- [P02] [CUDA目标路径](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/kernels-src/cu/inkling.cu)；[Rust kernel接口](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/kernels/src/inkling.rs)；[matrix上传与dispatch](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/kernels/src/ops.rs)；[现有probe实现](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/model/src/inkling/probe.rs)。
- [P03] [DSpark与Markov folding](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/model/src/dspark.rs)。
- [P04] [DFlash2缓存、embedding/head与selector](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/model/src/dflash2.rs)。
- [P05] [T25 judge](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/tools/t25/t25_judge.py)；[测试fixture](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/tests/test_t25_judge.py)。
- [P06] [既有任务、T42顺序、T44/T45/T46](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/docs/07_tasks.md)。
- [P07] [KIVI](https://arxiv.org/abs/2402.02750)；[KVQuant](https://arxiv.org/abs/2401.18079)。
- [P08] [Inkling SRFT](https://arxiv.org/html/2611.29092v1)；[固定作者代码](https://github.com/aminems/inkling-1m-mlx/tree/51e1653dc55aa4153e809d43f76ace45ea7e7769)。
- [P09] [LoopKV](https://arxiv.org/abs/2611.04137)；[ResidualQuant](https://arxiv.org/abs/2610.10381)；[ResidualQuant实现限制](https://github.com/heejunkim00/ResidualQuant)。
- [P10] [NVIDIA Ada tuning](https://docs.nvidia.com/cuda/ada-tuning-guide/)；[格式支持矩阵](https://docs.nvidia.com/deeplearning/transformer-engine/support_matrix.html)。
- [P11] [GSQ-RCO固定资产目录](https://huggingface.co/ISTA-DASLab/Inkling-2-Mini-GSQ-RCO-GGUF/tree/f0da1097633dd7c2f5733e4077cff861be122245)；[评估代码](https://github.com/IST-DASLab/GSQ-RCO-eval)。
- [P12] [AP固定资产目录](https://huggingface.co/agentionai/Inkling-2-Mini-AP-GGUF/tree/94a178b6dad70c9ecee7784cd4a9b9ebfa383f6c)。
- [P13] [kaiPTQ模型卡](https://huggingface.co/kaitchup/Inkling-2-Mini-chimachima-kaiPTQ)；[EXLR8格式](https://github.com/kindlingai/exlr8/blob/main/FORMAT.md)。
- [P14] [格式结构](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-common.h)；[当前quant crate](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/quant/src/lib.rs)。
- [P15] [当前CLI语法](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/cli/src/main.rs)。
