# 36 · Pool：面向 SM89 的压缩 GPU KV 与融合 Attention

**所属 L04/L05；条件路线，不能因 Tier 通过就启用。目标机实现与性能均 NOT_RUN。**

## 1. 何时开始

仅当 L02 的真实数据表明合适表示具有正的可分配容量收益，且 T04/profile 显示 GPU KV 容量或 KV 读带宽影响目标任务时开始。先修复重复 allocation、过大的 scratch/graph pool，再判断是否值得引入新 Attention。

LoomKV Pool 的已描述实现以 128-token、head_dim=128、GQA≤8、BF16/FP8 为边界；其 FragPack 与 Tier TileStream 不同。Prefill 仍会解码到临时 BF16 workspace，开放尾块保留 raw。它是融合 decode Attention 的参考，不是所有 Attention 路径零临时内存的方案。[论文 §VI、IX](https://arxiv.org/html/2611.32954v1)

## 2. 编码与 GPU 页必须分别评估

`encoded_payload_ratio`、`record_ratio_with_headers`、`allocated_pool_ratio`、`whole_engine_peak_ratio` 是四个不同量。可变记录被固定页分配后，最难压层、碎片、overflow、map、codebook、open tail 及临时 workspace 都可能消耗收益。

准入至少满足：

`pool_pages + raw_escape_pool + raw_open_tail + record_maps + codebooks + prefill_workspace_peak + in_flight_migration + graph_reservations <= assigned_cache_budget`。

只将相对于相同完整 profile 的 raw reference 真正减少的 device allocation 记为可重新分配字节。压缩后仍保留整份 raw KV 的实验只能证明 Codec，不可宣称容量释放。

所有分配使用预算预留与 generation。有限 overflow 满时必须在写入前 fail-closed：不写默认页、不覆盖 slot0、不发布坏 map，停止受影响的后续token推进；已经emit/commit的前缀不能撤销。保留已提交raw sealed block，连同新open tail计费，并按34规定的有界pending set施加背压。可以在干净边界选择已预留且已资格的raw profile重建；不能靠反复重算同一不可压前缀赌成功。发生部分破坏写入或异步错误，按 [34](34_cache_state_contracts.md) 的事务退役处理。

## 3. SM89 的实现选择

| H800/其他参考机制 | SM89 处理 | 验证指标 |
|---|---|---|
| TMA staging | 重新设计 vector load / 普通 cp.async 与双缓冲 | 实际 load overlap、对齐、shared bytes、尾块 |
| Fragment 顺序解码 | 按本机 mma.sync/ldmatrix 消费布局设计 | lane mapping、bank conflicts、数值路径 |
| 高吞吐查表 | PRMT/整数 bit 操作等可行候选 | 指令数、escape 分歧、register pressure |
| 大 shared pipeline | 减少 buffer/tile/阶段；实际编译资源约束 | spill、occupancy、寄存器/CTA、shared 总量 |
| 巨型固定 staging | 有界小 arena、跨模块预算复用 | 完整峰值而非平均值 |

RTX 4090 的 SM89 不具备 Hopper TMA。Ada 共享内存和寄存器限制见 [NVIDIA Ada 指南](https://docs.nvidia.com/cuda/ada-tuning-guide/index.html)；超 48 KiB 的每 block **总 shared** 需求按实际 static/dynamic 组合处理 opt-in。不能把一项 Hopper intrinsic 换名后宣称已完成移植。

Codec/attention 使用现有 ggml-cuda 局部 provider 为首选。CUDA C++ 先做可比较参考；cuda-oxide 的 SIMT 或适用 Tile 可以作为受限前端实验。是否编译成 SM89、实际执行哪个 kernel、是否 fallback，均写入 execution evidence。不要求 Rust 才能获得正确的系统设计。

## 4. 资格阶梯：从一个 shape 到完整模型

| 子阶段 | 支持范围 | 不能外推到 |
|---|---|---|
| P0 codec/布局 | 固定 dtype/shape 的 bitwise 解码 | Attention、模型、容量 |
| P1 micro Attention | B=1、一个合法 global head shape、sealed pages + raw tail | SWA、prefill、DSpark B>1、生产 |
| P2 serial model | 正式 R3、真实所有 global/SWA 与 conv、实际 scale/softcap/mask | 投机、多分支、完整服务恢复 |
| P3 full selected profile | 已选 DSpark/verify widths、graph、预算、cancel/rollback、prefill/cache resume | 不同量化/深度/codec/并发 |
| P4 service | 长上下文与真实多轮 Agent、资源峰值、soak、回退 | 未通过的容量行 |

如果只有 global KV 的 P2 子路径获益，可混合 raw SWA，不强制压缩全部访问。记录每个 logical slot 实际选择。对不支持的 scale、softcap、causal/window mask、head/GQA、page size、verify tree 均在准入拒绝；不能只满足 `head_dim=128` 就接入。

GAAC 的公开后端有自己的限制与静态代码风险；见 [33](33_lossless_source_audit.md)。参考它的 Codec 代码不自动继承其 vLLM ABI 或调度假设。

## 5. Prefill、短尾与投机

三类读取必须显式存在：完整压缩页、当前 raw 尾块、合法未提交候选的私有区域。seal/publish 只发生在对应 token 已提交且所有写完成后。拒绝候选不能污染已压缩历史，开放块写过 SWA 环时仍需可恢复副本。

Prefill 首先选择 raw buffer 或有界分块解压 + 原 Attention。若必须同时拥有长 prefix 的整份 raw workspace，GPU 净容量可能消失；L04 必须尽早实测并可以结案 NO_BENEFIT。分块 softmax 的归一化/累加顺序属于 N 类变化，不能因容量压力悄悄改算法。

DSpark multi-token verify 与 2DSD tree 的 mask/read set 不等于 B=1 causal decode。L05 之前压缩 Pool 的 spec 组合明确拒绝；既有 raw spec 路径继续保留。若后续只资格 native DSpark，不推出 2DSD 已支持。

## 6. 数值与正确性

Codec roundtrip 为 E；融合 Attention 因规约/softmax/精度路径变化通常进入 N。逐层、逐 pass、逐 head 对照 raw reference，使用 13 中已冻结的数值和质量合同。raw/压缩页混合时的输出应一致于候选声明的算术合同，不要求跨所有合法 kernel 位级相同。

先验证任意 raw bit pattern 的 Codec，再验证真实 KV 的数值。NaN/Inf 的 decoder roundtrip 与模型是否允许非有限值是两个问题：Codec 能保存 bits 不意味着非有限模型状态可被提交。

## 7. 搜索与停止

继续使用 K00–K06 的有界离线搜索。L04 初轮只选一个表示和一个热点 shape，block/tile 32/64/128 等是本地新格式的候选，不声称与论文格式二进制兼容。codebook、页大小、record map 一旦改变，必须升级 format/layout 指纹。

压缩比好但 spill/escape/功耗/分歧使 Attention 变慢；或 Prefill scratch 造成峰值更高；或需要牺牲 DSpark/权重驻留才能维持 Pool，均可能是 NO_BENEFIT。对请求关键路径使用 Amdahl 上界做立项筛选，最多两轮有 trace 支持的修正。容量目标与速度目标分别判定，不借容量收益隐去延迟退化。
