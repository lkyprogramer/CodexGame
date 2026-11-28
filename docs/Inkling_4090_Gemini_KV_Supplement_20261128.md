# Inkling 4090：Gemini 量化方案核实与增量补充

**日期：2026-11-28（北京时间）**  
**性质：对外部方案的技术审阅及可执行补充设计；不替换前序评估和实施方案。**  
**审阅对象：** 用户附件 `gemini-kv.md`，45,611 bytes，SHA256 `b6c4d58de24f0cedaba50d22040fa6cd02a39ee7fbb8b220c92b1dfa0fa0a6be`。

**沿用文档：** `Inkling_4090_Quantization_Context_Assessment_20261128.md`、`Inkling_4090_Quantization_Context_Implementation_Plan_20261128.md`。本次没有修改这两份文档、引擎仓库或现有任务状态。

## 1. 结论

Gemini 方案中有值得吸收的实现思路，尤其是 **GQA × verify 多 query 共同读取 KV**。但它的当前状态、容量预算与若干数值论证存在实质错误，不能按整份 RFC 或其8周里程碑直接执行。

建议分成三类处理：

1. **优先补充：** 将多query KV复用做成T44/K15内部的独立对照实验；保留当前FP16/FP8两条路径，以证明收益来自读取复用还是存储压缩。
2. **有条件补充：** 前缀FP16保护、V-only旋转的K8V4、精确FP4码字到FP8的微内核、直接MXFP8执行的小范围对照，以及小热点区域的L2保留实验。
3. **不采纳为承诺：** 整个循环核心常驻L2、原生格式再省2.6GB、DSpark按固定显存处理、256K→420K→768K容量表、1.6–2.1倍prefill、未经修正的TQ4无偏性，以及把所给CUDA片段视为可直接接入的完整实现。

保持既有顺序 **K12 + T45 → T44 → K15 → K13 → K14 → T47**。下文的“补充A–F”只是本文内编号，不创建新的T/K任务，不自动重开已经暂缓的K17。[S01][S02]

## 2. 核查范围与证据等级

本次重新查询GitHub，确认引擎HEAD仍为 `d586fec31afd08526d0500ba815a33be18199c65`，`4090-report`仍为 `495f110dfe4a1bb5e5ae743c9378ab9a9937e103`，与前序文档一致。[S01][S02]

实际完成的工作：

- 阅读附件全文，对照现有Rust/CUDA、checkpoint loader、draft和诊断接口。
- 查询NVIDIA Ada白皮书、CUDA 12.8/PTX 8.7、L2官方文档及TurboQuant原文。
- 用真实模型shape重新计算L2下界、MXFP8字节差与容量情景。
- CPU穷举全部65,536个FP4 packed输入；检查128维FWHT基底；复现scale、局部累加溢出、QJL和softmax反例。
- 独立审阅硬件、数学/代码、模型/计划三个部分，并对关键CPU结果复跑。

**未做：** CUDA编译、SASS验证、RTX4090实测、新模型整文件下载或引擎改造。下文的CPU数学结果不能写成GPU性能或GPU浮点精度实测。

## 3. 逐项审阅总表

| 附件主张 / 核查事项 | 核实判断 | 处理 |
|---|---|---|
| 4090 FP8→FP16约660、FP8→FP32约330 TFLOPS | 官方稠密理论峰值支持 | 保留，但不直接外推端到端速度 |
| 当前KV为BF16 | 当前target与默认DSpark为FP16 | 更正dtype与所有接口 |
| 40个local visit只占160MiB | 默认3072行ring实际480MiB | 更正预算，不能缩到1024行 |
| 新增原生NVFP4/MXFP8加载即可省2.6GB | NVFP4与checkpoint导入已存在；直接MXFP8仅有小量字节差 | 拆成现有能力和窄格式实验 |
| 关闭vision立即再省0.64GB | 当前文本路径没有这笔GPU驻留 | 不计该收益 |
| embedding offload统一省0.85GB | 取决于资产；A1约0.458GiB，BF16约0.863GiB | 沿用K16，按资产记账 |
| DSpark属于固定O(1)状态 | 另有4096C bytes全局KV | 加入容量斜率 |
| 全循环核心38–44MB，可锁在72MB L2 | 仅Q/K/V/O理想4bit已108MiB | 否定整个核心常驻；缩成小窗口实验 |
| GQA×verify query共用KV page | 有实际研究价值 | 本文最高优先级增量 |
| 每个page只反量化一次 | 示例实际上每warp重复解码 | 以实测指令/流量验证，不承诺理想倍数 |
| 所给reader可直接接现有merge | sink、RPE、partial布局与split计数均需修改 | 保留思路，重写明确接口契约 |
| E2M1原始码字可精确展开为E4M3 | 正确；CPU全部packed输入通过 | 保留微基准，不宣称带scale仍无损 |
| group16合并group32仍无损 | 一般不成立，存在3.125%反例 | 视为新量化或保留独立group |
| K32后晋升FP32保证不溢出 | 局部sum本身即可超过65504 | 加数值范围证明或使用F32累加 |
| RMS后严格服从N(0,1) | 错误；仅约束均方值 | 实测分布，码本作为候选 |
| 所给Hadamard-QJL严格无偏 | 选择的投影不满足继承定理的条件；CPU反例成立 | 不进入首轮GPU实现 |
| 点积无偏可消除softmax偏移 | 非线性下不成立 | 仍需attention/任务质量门 |
| Qwen支线、cmp-prefill和新selftest参数 | 前两者已存在；指定量化测试flag尚无实现语义 | 纠正资产/容量依据，补真实测试选择器 |
| 128/256K时DSpark必须严格快于plain | 不是KV正确性的必要条件 | 按profile判断速度型/容量型价值 |
| 8周达成容量与速度表 | 缺同资产、同协议、内存及质量证据 | 改为分阶段继续/停止条件 |

来源分别见现有引擎[S03]–[S09]、NVIDIA[S10]–[S12]与论文[S13]。附件未提供可复核的GPU原始结果，因此其性能表都应按假设处理。

## 4. 必须先修正的项目事实与资源预算

### 4.1 FP16、ring和原生加载

现有target cache由 `DeviceBuffer<u16>`分配、CUDA按 `__half`读取，是FP16；不能仅凭u16位宽推断dtype，也不能把它改为BF16后声称默认路径未变。当前global Q/R则是prep后的F32，附件reader把Q输入改为BF16又引入了独立的精度变化。[S03][S04]

默认local ring行为是 `roundUp64(1024+max(tmax,8))`，tmax=2048时为3072行，40个visit合计480MiB。附件160MiB只对应1024行的理想窗口，无法覆盖整个prefill chunk中较早query仍需读取的历史。

当前 `inkling_checkpoint.rs` 已实现：BF16 dense/embedding转Q8_0、NVFP4按原值重排、MXFP8解码后转Q8_0、controller等转相应F32布局。原生文本 `plan()` 只建立 `model.llm.*` 张量，索引完整safetensors不等于把vision上传GPU。因而“新增原生加载”和“关闭vision”不能再作为A1上的两笔新节省。[S05]

实际资产命名也应按loader核对：源专家使用 `w13_weight`、`w2_weight`、对应 `_scale`、`_amax`、`_outer_scale_denominator` 等；附件通用的 `weight_packed/weight_scale_2` 不是已验证的本项目schema。

### 4.2 直接MXFP8仍有价值，但省量约0.119GiB

需要区分“能读取原生checkpoint”和“MXFP8原样驻留、直接执行”。后者确实还可研究。

最后4层相关专家的参数量为：

\[
P=4\times128\times(2304^2+2304\times1152)=4,076,863,488.
\]

Q8_0每32值占34B，原生MXFP8每32值为32B码字加1B E8M0 scale，即33B。因此该部分的布局差：

\[
\Delta M=P(34-33)/32=127,401,984B=0.118652GiB.
\]

新aux、pack和workspace还需另外计入。如果同时把dense/embedding恢复到原生BF16，驻留反而可能增大。直接MXFP8的主要问题是“能否减少一次重新量化带来的数值损伤，以及其执行成本是否划算”，不能用它承诺再省2.6GB。[S05][S08]

### 4.3 附件容量里程碑无法由自身预算推出

沿用前序报告的历史情景基项 `B=18.710571289 GiB`。它来自旧T17 plain的128Ki峰值，已扣除全局KV与随C增长的attention workspace；不是新版本实测值。

附件给出的布局本身可推出以下全局KV斜率：

| 布局 | 八个global visit总bytes/token | 含metadata的说明 |
|---|---:|---|
| FP8-head | 16640 | K/V各一个每token/head的FP16 scale |
| K8V4 | 12544 | 平均6.125bit/KV元素，实际压缩约2.612倍 |
| 附件TQ4带padding | 8704 | 平均4.25bit/KV元素，与普通INT4-g64同档 |

还需加attention workspace约195C bytes；DSpark另有4096C bytes全局KV，并非固定项。

| 情景 | plain估算 | 再加DSpark全局KV的估算下界 |
|---|---:|---:|
| A1 + FP8，256Ki | 22.821GiB | 23.821GiB |
| A1 + FP8，420,000 token | 25.296GiB | 26.898GiB |
| A1 + K8V4，512Ki | 24.931GiB | 26.931GiB |
| A1 + 附件TQ4，768,000 token | 25.076GiB | 28.005GiB |

**右列未加入DSpark权重、固定Spec缓冲、新codec临时区和安全余量。** 附件还要求预留1.2GiB，故其A1+DSpark+FP8的240–256K承诺不成立。即使先无条件给予其声称的2.6GB权重节省（约2.421GiB），420,000 FP8+DSpark与768,000 TQ4+DSpark仍约24.477/25.584GiB，未加草稿固定项就超过24GiB。

这否定的是附件所列步骤与预算的自洽性，不是证明任何重构都达不到这些长度。更长容量仍可通过真正低位权重、不同draft profile和KV4探索，但应按前序方案逐级实测。

### 4.4 Qwen和命令：不能因其他错误而一概否定

当前仓库确有 `qwen35.rs`，对应Qwen3.8-27B；64层、16全局/48DeltaNet、4KV heads×256的结构基本有源码依据。但真实资产是MXFP4 checkpoint转换路径，并非附件假设的UD-Q4_K_XL基线；`qwen-generate`当前创建的capacity还被 `.min(8192)`限制。其80K/512K及48→60–68tok/s需要独立资产、服务接口和实验，不并入本次Inkling验收。[S09]

`astral cmp-prefill`实际存在；`selftest --sm89-quant`目前没有该筛选语义，CLI进入的是普通selftest。未来新增flag必须实现并输出实际运行的测试集合，不能把普通selftest成功误当成新量化测试成功。[S07]

## 5. 硬件部分：保留真实机会，撤回没有依据的保证

### 5.1 峰值数字基本正确

NVIDIA Ada白皮书v2.02给RTX4090的稠密理论峰值：FP8→FP16累加660.6 TFLOPS，FP8→FP32累加330.3，FP16/BF16→FP32累加165.2；稀疏有效值另为两倍。CUDA12.8/PTX8.7也列出了SM89可用的稠密FP8 MMA指令族，包括附件采用的FP16累加形式。[S10][S11]

所以FP8 MMA值得研究。问题在于“必须采用FP16内层累加”“可跑满660”“完整prefill提升1.6–2.1倍”的推导。实际成本还包括解码、scale、FP32晋升、寄存器、tile形状、专家不均衡和非GEMM工作。

现有 `mma3` 是FP16输入、FP32累加，附件称其BF16不准确。`F80`是共享kernel family，不表示4090没有FP8能力。现有代码已经有 `nvfp4_frag_layout`、fragment上传和mma5；load-time repack不是从零开始的新能力。[S06]

以T42的2K prefill为例，NVFP4 mma3约占45.5%。若只把这一部分理想化为快4倍，其他不变，Amdahl计算约为1.52倍；要得到更高完整收益需要额外变化及实测，不能只用660/165推导。[S02]

### 5.2 整个循环核心放入L2的前提错误

只计算core12层的Q/K/V/O，真实shape给出：

\[
12\times2304\times(3072+1024+1024+3072)=226,492,416\text{参数}.
\]

即使全部按理想4bit、完全不计scale/padding，也需要 **108MiB**，已经超过4090的72MiB L2。gate、relative projection、router、controller尚未计入。按Q8_0表示，这四类投影就约229.5MiB。因此“全部core为38–44MB、免费3倍”的前提不成立。[S03][S08][S10]

L2 persistence也只是提高保留优先级，不是锁页；`hitRatio=1`不保证100%命中。固定48MiB额度必须改为查询真实device limits、检查API返回，并验证graph执行路径与策略复位。可以留下小热点窗口实验，不能默认开启整个core锁定。[S12]

### 5.3 小M、分页对齐、persistent grid都是待测选择

M≤8时，权重读取的理想算术强度通常较低，值得优先分析带宽。但这不证明解包指令一定完全隐藏；小矩阵、依赖链、spill、occupancy、cache命中和调度都可能成为限制。

32×128B=4096B的page算术正确，但它只是一种布局候选。每线程16B load次数不等于DRAM事务数；一个global page包含全部8个KV heads和K/V，实际数据为64KiB、scale另1KiB。不能由“4KiB正好对齐”推出page32一定最优。[S14]

固定128个persistent blocks也不等于每个专家只从DRAM读取一次。现有引擎已有grouped work items，不能与虚构的“每token每专家单独launch”比较。K17已有相关暂缓路线，本补充不因附件重复提及就重新启动它。[S02][S06][S15]

## 6. CUDA与量化数学：哪些正确，哪些必须改

### 6.1 FP8 writer是骨架，尚未满足当前契约

附件§3.2使用BF16输入，并称在QKV/RoPE后写入；当前Inkling target没有RoPE，cache值应来自短卷积、K clipping、V RMS normalization之后的FP16语义。

其编码使用F32 scale，存储时再舍入FP16，读取端则使用存下来的scale。这不等同于前序方案“按实际stored scale编码”的定义。CPU按F32除法、倒数与乘法模拟的例子：amax=0.5、x=7.62939453125e−6时，使用F32 scale与stored FP16 scale会分别产生E4M3 code3、code4。它未必单独导致质量失败，但必须固定为一种明确codec，不能默默混用。

还需补host侧capacity/page-table/非负position检查，保留合法valid end和推测回滚语义。仅有per-token metadata，不能证明所有状态都只需要一次 `seq_len -= r`。[S03][S04]

### 6.2 多query读取的想法有价值，接口必须重新接齐

附件§3.3有五个会影响结果的缺口：

1. **sink是query-dependent。** 当前值来自每token的投影，布局为`[query, head]`；示例只按head索引。相同key/value、sink分别为0和ln3时，两个query应分别输出0.5和0.25，不能用同一个head常量。
2. **RPE缺少参数。** 当前项为`R_p·B_(p−j)`，有限extent1024；示例只有一句“ALiBi/RelBias”注释，没有R、bias和extent输入，prefix循环也缺这项。
3. **sink约定与现有merge不兼容。** 将“真实logit减sink+额外零logit”改写成“真实logit不减+虚拟logit=sink”在数学上可以成立；但必须按query处理且只计一次。示例split0已经加入虚拟sink，现有merge又会加一次，不能直接复用。
4. **partial布局和active split规则不同。** 示例用三个独立`[split,query,head]`数组，现有merge读交错`[query,head,split,HD+2]`；示例按32行page连续切分，当前merge按64行chunk推导活跃split。
5. **额外数值与性能变化未隔离。** Q被改为BF16；示例每warp重复解码，且虽写“双缓冲”，实际只有一份K/V page buffer，没有已实现的重叠流水。

最小正确例子是单key、value=1、真实logit=0、sink=0：一份sink输出1/2；重复计sink会输出1/3。这是接口错配，不应被当成低位量化允许的误差。[S03][S04]

### 6.3 FP4码字展开函数正确，不等于完整W4A8无损

附件§4.2的LUT和符号位扩散，经CPU对所有65,536个16-bit packed输入穷举，**0处不匹配**，包括signed zero。这一函数可以保留。

但它只证明原始E2M1码字属于E4M3可精确表示的集合，不证明乘上任意scale后仍精确，也不证明“6条整数指令”“完全隐藏成本”或整个fragment映射正确。实际指令数需SM89编译和SASS核对；当前引擎已有PRMT/INT8/F16展开路径，必须与它们比较。[S06]

### 6.4 group16到group32不能无条件无损合并

取合法的raw weight=1、local scale=1、pair scale=1.5。合并后需表示2/3，而最近E4M3值为0.6875：

\[
1.5\times0.6875=1.03125\neq1.
\]

这是 **3.125%** 的单权重误差。若预存调整后的FP8 codes，数据已从4bit扩为8bit；若现场计算，则要计入转换和舍入成本。附件给出的内循环只解包原nibble、最终乘一个pair scale，尚未实现每个group的修正。

“把weight scale吸收入activation”也不普遍成立：scale依赖输出行/专家和K-group，而共享activation不能同时吸收不同输出行的不同scale。可行版本是保留group16的独立partial，或明确登记一次新的量化转换并重新验收。

### 6.5 每K32晋升FP32仍可能先溢出

合法E4M3 activation=448、E2M1 weight=6，32项同号相加为：

\[
32\times448\times6=86016>65504.
\]

局部FP16结果已溢出，事后提升到FP32不能恢复。CPU模拟得到inf；这不是说明真实模型必然经常发生，而是反证“无条件不会溢出”。需要证明每tile的输入范围、限制编码范围、缩短partial或使用F32累加。晋升也不能恢复tile内部已经丢掉的精度。[S11]

### 6.6 FWHT实现可保留，分布与旋转顺序论证需重做

附件FWHT128蝶形本身经CPU基底测试符合归一化Hadamard，F64模拟的最大正交误差约1.11e−16；这不是CUDA F32误差或吞吐证明。

附件用列向量写 `R=D·H`，相当于先Hadamard、后加随机符号。对全1向量，H将能量集中到一个坐标，之后的D只改符号，无法将其分散。通常应明确采用输入随机符号的 `H·D`，但即便如此，也不能声称每个输入都严格高斯。

RMS归一化只保证平均平方值，不能保证零均值或N(0,1)。有限维均匀球面旋转的坐标是Beta型边缘分布；高维高斯是近似，结构化Hadamard也不是Haar随机旋转。高斯Lloyd-Max常量只能作为一个待比较的码本。[S13]

正交内积恒等式与V聚合后只逆变换一次是成立的。实现中需确保未旋转prefix/near和旋转far处于一致坐标系；不能把两种基底的value和直接相加，再统一做一次逆变换。gate仍须在恢复原坐标之后。

### 6.7 附件QJL公式不具其声称的无偏性

原论文QJL证明使用iid Gaussian投影矩阵。附件替换为归一化 `R₂=H·D`，仍使用相应常数，不能直接继承定理。[S13]

取residual r=e₁、query q=e₁。对任意符号D，`sign(R₂r)·R₂q=√d`，所以附件估计恒为：

\[
\sqrt{\pi/(2d)}\cdot1\cdot\sqrt d=\sqrt{\pi/2}=1.253314\ldots
\]

真内积是1。CPU测试256组符号均得到同一结果。这是对所给残差估计器的反例，不是在声称真实模型所有residual都有25.3%误差。

即使修成正确的点积无偏估计，也不能推出softmax无偏：logits为[1,0]、第一项加入均值为0的±1噪声时，原概率0.731059，期望概率约0.690399。固定一次投影更不能保证每个样本精确。因此“彻底消除softmax偏移”“8bit Key零漂移”都应删除。

## 7. 可采纳增量与原方案的对应关系

| 增量 | 相比前序方案新增什么 | 挂靠位置 | 优先级 |
|---|---|---|---|
| A. GQA×verify-query读取复用 | 把此前的GQA复用扩成明确的多query分解对照、完整partial/merge契约 | T44稳定后，接K15 | 最高 |
| B. Prefix保护与V-only旋转 | 把已有近端/K8V4候选具体化；新增长距离prefix独立消融 | KV8通过后的KV4研究 | 中 |
| C. FP4→FP8及W4A8微内核 | 保留已核对的码字函数；用明确scale/溢出边界筛选FP8算术 | K13后续独立算术候选 | 中、研究性 |
| D. 直接MXFP8 | 精确区分原生导入与直接执行，量化再转换的质量/成本 | T31之外的窄格式对照 | 低至中 |
| E. 小热点L2保留 | 将不成立的全core常驻缩成可证伪小窗口 | 当前profile有证据才做 | 低 |
| F. Pack落盘缓存 | 只针对冷启动，补身份与失效契约 | 重排占冷启动显著份额时 | 条件性 |

global-only量化、local/conv维持原精度、per-token scale、graph地址稳定、近端FP16、长文质量与草稿收益等，前序方案已经覆盖，本补充不重复计为新发现。动态容量校验可扩充既有memory report，不要求先建通用分页平台。

## 8. 补充A：GQA × verify 多query共用KV读取

### 8.1 要回答的问题

当同一个KV head服务3个query heads、verify又有1–8行时，能否在不改变每行算术与因果语义的前提下，将重复global加载减少到一个CTA内的tile读取，并得到端到端净收益？

**不预设：** KV字节减半就翻倍、融合24个slot就减少24倍DRAM流量、DSpark在每个长任务都必然超过plain。原先多次加载可能命中L2，融合也可能增加寄存器/shared memory和降低并行度。

### 8.2 最小实现范围

修改现有 `crates/kernels-src/cu/inkling.cu`、`crates/kernels/src/inkling.rs`，必要时调整 `inkling.rs` 的dispatch；沿用前序KV storage和codec-aware probe。不引入新的 `crates/astral-*` 目录树，不以分页作为前置条件。

1. 先在连续全局cache上做joint tiling；读取布局与分页、codec分开实验。
2. Q/R保留当前post-prep F32；输入sink明确为`[query, head]`；RPE的R、bias、extent必须显式传递。
3. 首版沿用当前“真实logits减sink，merge额外加零sink一次”的约定，减少代数变化；partial中不提前放sink。
4. 先保持现有partial内存布局。如果必须改布局，则reader、workspace sizing、active-split计数和merge成套变更，禁止接错。
5. 每query独立因果边界、max、exp sum和value sum；空split显式处理，不读未初始化partial。
6. 用实际query数量选择合法slot，但padding、split边界、归约顺序遵守T45契约；不能因为q_len变化而无意改变同一行算术。
7. 沿用 `reader_math=dequant_f16_rn_v1`。融合读取时不顺带改变反量化后的舍入，不加BF16 Q的新误差。

### 8.3 四臂与分解对照

| 试验臂 | target KV | query组织 | 用途 |
|---|---|---|---|
| A0 | FP16 | 当前每query路径 | 原实现基线 |
| A1 | KV8 | 当前每query路径 | 存储压缩收益 |
| A2 | FP16 | GQA×query融合 | 单独读取复用收益 |
| A3 | KV8 | GQA×query融合 | 最终组合与相互影响 |

性能点：32/64/128Ki，q_len=1/2/4/8；数值/状态覆盖完整1..8。query tile比较1/2/4/8，GQA比较1/3，再选少量组合。不要穷举所有grid、page和精度一起找最好数字。

微基准先固定同一Q/R/sink/KV状态，记录kernel时间、实际DRAM读取、L2命中、解码指令、register/spill、shared memory和occupancy。随后跑plain、DSpark、DFlash2真实请求，记录完整round时间、接受token/round、最终请求时间与质量。

### 8.4 交付与停止条件

拟在lab `tools/t44/` 增加 `mq_attention_cases.json`、`mq_attention_profile.py` 与相应case级报告；它们是待实现接口，不是当前可调用脚本。

- 实现门：RPE、不同query sink、边界、空split、不同q_len、拒绝/重置都通过；quantized reader与同codec oracle一致。
- pilot建议门：64/128Ki verify attention时间至少降低10%，且完整请求有超过测量噪声的收益；若增量完整请求改善不足约3%，先停止扩面。正式采用仍继承前序T44质量/性能门，不用这个pilot门替代。
- 初始pilot预算可限4 GPU小时；只在明确受益的shape和长度启用分派，不要求所有q_len都使用同一kernel。
- 若只减了逻辑load次数但DRAM流量/时间没有改善，或spill/occupancy抵消收益，记NO_BENEFIT。不得通过变更draft接受率的数值路径来伪装kernel加速。

## 9. 补充B：Prefix保护与V-only旋转的K8V4

### 9.1 Prefix保护是一项独立、低成本消融

前序方案已有按距离保留的near FP16。附件新增的可测问题是：远距离的最初几个token是否仍值得保留FP16。

拟比较 `prefix_protect_tokens=0/4/8/16`，以FP16保存，不使用BF16。8个token、8个global visit的K/V payload为256KiB；这是很小的固定成本，但仍不等于必有质量收益。

将它命名为“prefix保护”，与模型的query-dependent虚拟sink明确区分。reader对每个query p、key j按确定规则选精度：

- `j<prefix_protect_tokens`：读取prefix FP16；
- 否则 `0≤p−j<near_window`：读取near FP16；
- 其他合法历史：读取指定低位far。

prefix与near重叠时只计一个真实key。prefix是会话逻辑位置，不是物理ring下标；reset、长prompt、推测拒绝都要验证。实现可保留低位全C codes并另存prefix FP16，额外bytes按实际重复数据记账。

只在包含长距离系统指令、前缀事实、格式约束、后段干扰的冻结任务上检验它；评分最终answer，不能只看reasoning中命中关键字。若相对N=0没有可重复改善，默认仍为0，不增加常驻配置负担。

### 9.2 先仅旋转V，降低验证复杂度

比较三个候选，K保持同一已验证KV8：

1. 原始坐标的V INT4-g64；
2. V采用 `H·D` 后的INT4-g64；
3. V采用 `H·D`、按每向量RMS缩放、固定LM4码本。

这样先隔离旋转与码本是否改善V损伤，避免同时引入Q/K旋转、QJL和score变化。固定sign seed、矩阵顺序、归一化因子、码本版本及实际scale舍入；零向量、极小norm、离群值必须有明确定义。

注意三种布局的scale开销并不相同：LM4每head一个FP16 norm对应附件12544C；group64 INT4需要两个scale/head，不能一律沿用同一bytes/token。比较质量时同时报告实际总bytes，必要时构造相同预算对照。

V-only旋转时Q/K原有内积与RPE不变。far value累加在旋转坐标中，near/prefix在原坐标中：可以先对far的未归一化value和做逆变换，再按共同LSE统计合并；或者把各区域都转换到同一坐标。两种方式均须验证empty far、boundary和gate顺序。

### 9.3 进入更复杂旋转的门

只有上述简单候选在相同或相近总字节下有可复现的质量/速度优势，再研究Q/K一起旋转。收集真实post-prep KV，按global visit、pass、长位置统计norm、分位数、最大值、重构误差和attention输出误差；高斯码本与真实数据校准码本分开发现/留出验证。

附件TQ4暂不实现：其总成本已经与INT4-g64同为8704C档位，却增加第二投影、残差范数、位包和reader计算。未来若重做QJL，先给出符合所选投影的证明或严格数值误差证据，再与普通KV4按**总bytes**公平比较。

## 10. 补充C：保留FP4→FP8机会，先做有边界的算术实验

### 10.1 可复用的最小部分

把附件已通过CPU穷举的E2M1→E4M3函数纳入现有quant/kernel微基准，验证SM89编译、负零、全部码字、lane映射、tensor-tail、scale组和外部mat_scale。对照当前PRMT/INT8路径与mma3/fragment路径，不建立另一套“量化引擎”。

新预处理或pack若增加副本，应同时记录稳态与加载峰值。冷启动重排时间、decode、prefill分别报告；不能把重排提速当成token吞吐收益。

### 10.2 W4A8先解决两个约束，再测峰值

**scale约束：** 首个正确性原型保留每group16独立scale。可以用独立partial或masked-half K32来表达，但两次MMA及额外merge成本都要计算。若改成pair-scale FP8重数量化，则明确成为新有损候选，保存派生参数，重新跑T46；不得继续标注无损。

**range约束：** 先使用F32 accumulator作为正确性/成本对照。FP16局部累加只有在tile范围证明成立后才进入。若每tile有效项32、原码字绝对值≤6，一个粗充分界是activation绝对编码值≤65504/(32×6)≈341.17，并留舍入余量；可选择更保守的可表示范围，但要重新量化并测质量。K16、K64需要各自的界，不能复用一个数字。

外层FP32晋升只能减少跨tile的损失，不能恢复内层舍入。微基准必须包含同号极值、相消、真实activation与scale离散分布；不是只随机生成小幅正态输入。

### 10.3 范围与出口

先限A1已有NVFP4专家形状与真实prefill token/expert工作项，不扩大为Qwen EXL3支持。验证普通、稀疏专家分配、小尾部与不同row数，记录全部转换/量化/pack时间。

如果修正scale与range后，F16累加路径没有比F32版本或现有mma3/mma5更快，停止该分支。保留正确LUT和反例测试即可。它是K13后的独立研究，不是T44全局KV8的前置条件。

## 11. 补充D：直接MXFP8的小范围质量与成本对照

从**同一个固定原生checkpoint**派生两条路径：现有MXFP8→Q8_0转换，与保留原始MXFP8码字/scale的直接执行。不能从A1的Q8_0反推出丢失的原始值；若采用varloop A4，应作为不同模型身份单列，不能替正式A1做质量判定。

范围先限对应coda专家，保留其他权重、三遍、KV、draft与算术策略。所需改动集中在 `crates/quant`、checkpoint loader、`GemvType`上传/dispatch及专家kernel；覆盖decode、小批verify、prefill，不能只写一个格式enum。

先使用原始MXFP8的CPU decoder做oracle，验证scale边界、外部全局scale、shape与block布局；片上decode到现有算术，不整体展开成常驻BF16。

主要观察指标：相对原始保存值的误差、full-vocab logits/任务质量、coda kernel与完整请求成本、实际省下的bytes。若总节省接近理论0.119GiB但无质量或速度优势，不继续扩大。这是一个窄候选，不替代GSQ/AP的低位权重筛选主线。

## 12. 补充E/F：条件性实验

### 12.1 小热点L2保留

仅当新profile发现一个高复用、大小可容纳的明确区域时启动。先选已有连续allocation，避免为实验复制大块权重或临时重构全部arena。

- 查询实际L2容量、persisting上限和access-policy窗口上限，检查每个API返回；核对当前CUDA context与eager/graph执行路径。
- 对比off与少量4/8/16MiB级窗口，实际窗口不能超过所选allocation和device limits；hitRatio可试0.25/0.5/1，不默认48MiB。
- 同时测短、长上下文和真实draft模式。权重命中改善可能挤占KV/专家流量，需要看完整请求。
- 退出实验或切换profile时恢复策略；记录graph node属性，不能仅凭stream设置推定graph已生效。
- 建议先限1 GPU小时pilot；只有完整请求收益超过噪声、约2%以上且长桶无明显回退，才扩大验证。否则NO_BENEFIT，不默认启用。[S12]

### 12.2 Pack落盘缓存只解决冷启动

先拆分读取、解码、repack、上传、graph warmup的时间。若repack并非冷启动显著部分，或服务长期常驻，不优先做文件缓存。

若确有价值，缓存身份至少包含源模型完整hash、tensor schema、pack布局版本、目标SM、scale/算术语义版本。读取时校验长度、shape、校验和；失配回到源资产重新生成。采用临时文件加原子替换，不能把半写文件当有效cache。原始资产不可被覆盖。

缓存省的是重复启动成本，不承诺CPU重排固定小于1.5秒，也不计入decode tok/s。已有fragment pack路径应被复用。

## 13. 验收与调度：补充而不打断当前方案

### 13.1 沿用原有门，只补针对性负控

不直接采用附件统一的“FP8相对误差<1e−2”“mean KL<0.003”“98% NIAH”作为通用零退化证明。应明确相对误差分母/近零处理、输入与位置、参考后端、任务数量和置信区间。

`cmp-prefill`虽存在，但当前主要打印diff/KL并返回成功；需要判定器解析实际结果、应用冻结阈值，不能只看退出码。`selftest --sm89-quant`也需要真实实现，不能忽略未知flag后给出假通过。[S07]

在前序实施方案已有的状态、质量与性能门上追加以下定向用例：

| 用例 | 必须识别的问题 |
|---|---|
| 同QK、不同query sink | sink错误地只按head索引 |
| 单key+单虚拟sink | sink重复、遗漏或merge错配 |
| distance1023/1024/1025，prefix与near交叠 | RPE边界、重复真实key、混合精度视图 |
| q_len1..8、不同split、空split | batch数值、partial布局和active计数 |
| 拒绝每个候选长度、A/B/A reset | committed/prefix/near/draft状态一致 |
| raw E2M1全码字及scale ratio反例 | 把码字无损误当完整权重无损 |
| K32同号极值、不同partial长度 | FP16中间溢出与range假设 |
| all-ones、one-hot、真实KV | 旋转方向、分布假设和QJL偏差 |
| 相同总bytes的普通KV4与复杂codec | 只按nominal bits宣称优势 |

### 13.2 增量运行记录

在原run manifest增加必要字段即可，不建设新的实验平台：

```json
{
  "supplement_id": "gemini-kv-20261128",
  "reader_math": "dequant_f16_rn_v1",
  "attention_variant": "per_query_or_gqa_query_tiled",
  "query_tile": 1,
  "gqa_tile": 1,
  "partial_layout_version": 1,
  "sink_convention": "subtract_real_add_zero_once",
  "prefix_protect_tokens": 0,
  "rotation": {"scope": "none", "order": "none", "seed": 0, "codebook_hash": null},
  "weight_arithmetic_variant": "existing",
  "l2_policy": "off"
}
```

这是字段示意；正式记录应使用实际枚举、输入hash、完整原manifest和运行结果。不能把示意配置误报为已经实现的新flag。

### 13.3 推荐执行顺序

1. CPU准备可与主线并行：保存本文反例为定向测试，补格式/显存和CLI检查。
2. K12/T45按原计划完成，T44先建立可靠KV8 reader。
3. 在T44稳定后做补充A，接入K15；按四臂区分压缩与读取复用。
4. 前序KV4阶段启动时做补充B。先prefix和V-only，不直接上TQ4。
5. K13已有低成本prefill改造完成后，按热点再考虑补充C；补充D独立按价值取舍。
6. 补充E/F仅在profile或冷启动数据满足条件时做。Qwen EXL3与K17维持独立、暂缓状态。

单张4090的GPU实验串行，pilot预算不是正式质量证明的预算。每个候选输出PASS_SPEED、PASS_CAPACITY、NO_BENEFIT、QUALITY_FAIL、INVALID或INCONCLUSIVE等原有状态，并写明适用资产与配置。

## 14. 本次CPU验证摘要

| 检查 | 实际CPU结果 | 能证明什么 |
|---|---|---|
| FP4 packed16穷举 | 65,536输入，0 mismatch | 所给LUT/符号扩散正确 |
| FWHT128基底 | 最大正交误差约1.11e−16，F64模拟 | 蝶形索引正确；不是CUDA F32测量 |
| R=D·H，全1向量 | 仅1个非零坐标，绝对值√128 | 后置随机符号不能保证分散能量 |
| QJL one-hot反例 | 256组符号均为1.253314，真值1 | 所给结构化估计器不具有声称的无偏性 |
| FP16 K32极值 | 精确和86016，FP16转换inf | 外层晋升不能无条件防局部溢出 |
| group scale合并 | 1→1.03125 | 一般不是无损重排 |
| F32/stored-F16 scale | 找到code3与4分歧 | 编码精度契约必须冻结 |
| 重复sink | 正确0.5，错误1/3 | 示例与旧merge不能直接相接 |
| 均值为零logit噪声 | 0.731059→期望0.690399 | 点积无偏不能推出softmax无偏 |

### 最小复现代码

以下仅用Python标准库复现关键数学结果，可存为临时脚本执行；不需要模型或GPU。它不是引擎实现，也不替代后续CUDA测试。

```python
import math
import random
import struct

LUT = [0x00, 0x30, 0x38, 0x3c, 0x40, 0x44, 0x48, 0x4c]

def supplied_unpack(q):
    mag = sum(LUT[((q & 0x7777) >> (4*i)) & 7] << (8*i)
              for i in range(4))
    t = (q & 0x0088) | ((q & 0x8800) << 8)
    s = ((t & 0x00080008) << 4) | ((t & 0x00800080) << 8)
    return (mag | s) & 0xffffffff

def nibble_oracle(q):
    return sum((LUT[(q >> (4*i)) & 7]
                | (((q >> (4*i)) & 8) << 4)) << (8*i)
               for i in range(4))

bad = sum(supplied_unpack(q) != nibble_oracle(q) for q in range(65536))
assert bad == 0
print("fp4_unpack_mismatches", bad)

def h(v):
    y = list(v)
    stride = 1
    while stride < len(y):
        for base in range(0, len(y), 2*stride):
            for j in range(stride):
                a, b = y[base+j], y[base+j+stride]
                y[base+j], y[base+j+stride] = a+b, a-b
        stride *= 2
    return [x/math.sqrt(len(y)) for x in y]

d = 128
one_hot = [1.0] + [0.0]*(d-1)
rng = random.Random(24)
estimates = []
for _ in range(256):
    signs = [rng.choice([-1.0, 1.0]) for _ in range(d)]
    u = h([s*x for s, x in zip(signs, one_hot)])
    estimate = math.sqrt(math.pi/(2*d))*sum(abs(x) for x in u)
    estimates.append(estimate)
print("qjl_true", 1.0, "estimate_range", min(estimates), max(estimates))
assert all(abs(x-math.sqrt(math.pi/2)) < 1e-12 for x in estimates)
print("DH_ones_nonzero", sum(abs(x)>1e-12 for x in h([1.0]*d)))

tile_sum = 32*448*6
assert tile_sum > 65504
try:
    half_value = struct.unpack("e", struct.pack("e", float(tile_sum)))[0]
except OverflowError:
    half_value = "outside_finite_FP16_range"
print("tile_sum", tile_sum, "half", half_value)

assert 0.6875*1.5 == 1.03125
print("group_merge_relative_error", 0.6875*1.5-1)
sigmoid = lambda x: 1/(1+math.exp(-x))
print("softmax_original", sigmoid(1),
      "mean_with_zero_mean_noise", (sigmoid(0)+sigmoid(2))/2)
print("core_QKVO_ideal_4bit_MiB", 12*2304*(3072+1024+1024+3072)/2/2**20)
print("MXFP8_layout_saving_GiB", (4*128*(2304**2+2304*1152))/32/2**30)
```

## 15. 最终采纳意见

本补充接受的是**可验证的实现增量**：多query读取复用、低成本prefix消融、V-only旋转对照、精确码字展开与小范围FP8/MXFP8实验。它们都有清楚的最小范围和停止条件。

附件中的硬件峰值、正交恒等式和部分代码值得保留；容量表、全core L2、无损group合并、无条件防溢出及所给QJL无偏保证需要撤回。近期主线继续完成已有KV8，新的试验结果再决定是否扩大投入。

## 来源索引

附件按其章节号定位；源文件SHA256已在首页固定。下列源码以固定commit引用，公开文档访问日期为2026-11-28。

- [S01] [Engine固定提交](https://github.com/lkyprogramer/inkling-4090-engine/commit/d586fec31afd08526d0500ba815a33be18199c65)。
- [S02] [实验室07_tasks与T42/T43/T44/T45/T46](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/docs/07_tasks.md)；[K13/K15/K16/K17编排](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/docs/04_astral_fork.md)。
- [S03] [Inkling配置、加载、Session、Spec及query sink](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/model/src/inkling.rs)。
- [S04] [CUDA prep、attention、split/merge与RPE](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/kernels-src/cu/inkling.cu)；[Rust attention wrapper](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/kernels/src/inkling.rs)。
- [S05] [原生checkpoint loader](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/loader/src/inkling_checkpoint.rs)。
- [S06] [现有GEMV/GEMM、PRMT、mma3/mma5](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/kernels-src/cu/gemv.cu)；[quant及fragment layout](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/quant/src/lib.rs)；[matrix上传/dispatch](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/kernels/src/ops.rs)。
- [S07] [CLI、selftest、cmp-prefill、qwen-generate](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/cli/src/main.rs)。
- [S08] [实验室资产与A1组成](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/docs/01_model.md)；[固定AP资产/header对应文件](https://huggingface.co/agentionai/Inkling-2-Mini-AP-GGUF/tree/94a178b6dad70c9ecee7784cd4a9b9ebfa383f6c)；[DSpark](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/model/src/dspark.rs)；[DFlash2](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/model/src/dflash2.rs)。
- [S09] [Qwen3.8-27B实际模型路径](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/model/src/qwen35.rs)。
- [S10] [NVIDIA Ada GPU Architecture Whitepaper v2.02，Appendix A](https://images.nvidia.com/aem-dam/Solutions/geforce/ada/nvidia-ada-gpu-architecture.pdf)。
- [S11] [CUDA12.8 / PTX ISA8.7](https://docs.nvidia.com/cuda/archive/12.8.0/parallel-thread-execution/index.html)。
- [S12] [NVIDIA L2 Cache Control](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/l2-cache-control.html)。
- [S13] [TurboQuant原文，尤其§2.2 QJL与§3.1](https://arxiv.org/html/2504.19874v1)。
- [S14] [Nsight Compute Profiling Guide：request/sector/transaction](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html)。
- [S15] [CUTLASS Grouped Kernel Schedulers](https://docs.nvidia.com/cutlass/4.8.0/media/docs/cpp/grouped_scheduler.html)。
