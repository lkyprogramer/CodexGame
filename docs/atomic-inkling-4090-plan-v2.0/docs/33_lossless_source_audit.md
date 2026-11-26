# 33 · LoomKV 与无损缓存项目：来源、差异和采用边界

**审计日期：2026-11-26（Asia/Shanghai）。论文结果、静态源码发现与本机结果严格分开；本机全部 NOT_RUN。**

## 1. LoomKV 的已确认事实

[LoomKV，arXiv:2611.32954v1](https://arxiv.org/abs/2611.32954v1) 于 2026-11-24 提交。本文核对原文 HTML/PDF；本次检索未确认作者可归因的官方代码、固定 commit 或软件许可证，因此不提供虚构安装命令。论文许可不替代软件许可。

| 项目 | 原文结论/范围 | 适用于本计划的判断 |
|---|---|---|
| 系统 | vLLM 0.30、LMCache 0.5.6，主要服务实验两张 H800 80GB，TP2 | Atomic/4090 必须重做接口和预算 |
| BF16 | 九模型约 0.71 stored/raw | 仅为采样先验，不作为 Inkling 的容量合同 |
| Tier | GPU raw，RAM/SSD 压缩；TileStream 直接恢复到分散页 | 先做完整状态的闲置缓存，保留原 Attention |
| Pool | GPU 压缩，FragPack 融合 decode；prefill 使用解压 workspace | 新 Attention、分配与状态资格 |
| 编码 | Tier BF16 3+3；Pool 3+4，配合 raw fallback | 两种 wire/layout 不可互称 |
| GPU容量 | 论文完整预算下可用 tokens 约 1.31–1.34 倍 | 不等于整卡容量增加，也不是最坏数据保证 |
| 外部缓存临界 | LRU 容量临界 goodput 2.7–3.6 倍；IDE 衍生 trace Pool 1.59 倍 | 来自特定复用/排队，不能写成单路 decode 倍率 |
| Tier开销 | 每卡额外约 2.5GB，约 2.1GB 为 buffers | 小缓冲重设计是4090前置任务 |
| Pool边界 | BF16/FP8、head_dim128、GQA≤8、block128 | F16、Q8_0、Q4、SWA/树形等逐项适配 |
| exactness | Tier原始bits保留；Pool与原Attention可能因累加顺序不同而有数值差异 | E Codec、N Attention、业务资格分开 |

依据：[论文 §III–IX](https://arxiv.org/html/2611.32954v1)。同一公式 `1 / ratio` 只是 payload 等价容量；真实 fixed pages、metadata、tail、overflow 和暂存必须扣除。

### 必须补上的工程细节

原文 Pool overflow 是有限资源；import 满时可以失败并重算。重算同一前缀不会保证数据更可压缩，所以本方案增加有界失败处理、raw-profile 重新准入或明确拒绝，防止无限重试。论文没有给出本机所需的完整取消、别名引用、跨图回收和 checkpoint 语义，相关设计见34–37。

论文 FP8 平均 record ratio 与实际统一页比例并不相同；不可把平均值直接用于 GPU allocation。压缩 KV 已经是 FP8 时，恢复的是原 FP8 bytes，不能称为恢复到最初 BF16 的无损精度。

## 2. 可用代码和固定版本

| 来源 | 固定版本 | 可借鉴内容 | 采用判断 |
|---|---|---|---|
| [GAAC](https://github.com/Intelligent-Microsystems-Lab/GAAC) | `a2cbcb5eb22b2bf08bb614a01189163b85c07cdd`，main | BF16 编码/参考解码、寄存器融合、分页/escape 设计 | 条件适配；不是直接替换后端 |
| [SplitZip](https://github.com/Intelligent-Microsystems-Lab/SplitZip) | `f6960f1487ab4a056f8565d749d355739dc8394a`，main | BF16 与新公开 E4M3/E5M2 codec | Tier 对照，补封装和异步路径 |
| [ZipFusion](https://arxiv.org/abs/2610.33719v1) | 论文 v1；官方源码未确认 | 无损块/融合 Attention、跨层回收 | 设计参考，不设代码依赖 |
| [ZipServ](https://github.com/HPMLL/ZipServ_ASPLOS26) | `15378387cb09634527ab0b20b7abfc9ffd5b62c5`，main | BF16 权重/位图、SM89解压与GEMM | Kernel/布局参考，非现成KV方案 |

GAAC 与 SplitZip 为 MIT；ZipServ 为 Apache-2.0，引用和移植保留原文件许可/NOTICE。模型、论文、内嵌依赖分别登记。

GAAC 最新提交修复 paged escape offset 在超过2GiB时的整数宽度问题。SplitZip 另有 `ai-visibility@d67139b…`，是较早 README 分支；main 已包含且 ahead3，不能把分支名字当作最新算法。ZipServ 当前 main 最近变更为 README，不等于内核最近变更。[GAAC修复](https://github.com/Intelligent-Microsystems-Lab/GAAC/commit/a2cbcb5eb22b2bf08bb614a01189163b85c07cdd) · [SplitZip比较](https://github.com/Intelligent-Microsystems-Lab/SplitZip/compare/d67139b807638a1fa8a62eefd13b03b27cc9162b...f6960f1487ab4a056f8565d749d355739dc8394a)

## 3. GAAC：算法值得借鉴，后端不能直接接管

[论文2610.38210v2](https://arxiv.org/html/2610.38210v2) 的 logical ratio 约71.1%，但附录的 resident tile 包含固定空间后约73.6%。这是两种计费对象，不是冲突。论文有个人设备实验，当前公开源码不能自动视为已发布全部 Metal/FP8 路径。

静态审查的关键边界如下，**均未在本机运行复现**：

- [vLLM backend](https://github.com/Intelligent-Microsystems-Lab/GAAC/blob/a2cbcb5eb22b2bf08bb614a01189163b85c07cdd/gaac/vllm/backend.py) 为 BF16，限制 head128/256，并拒绝 sliding-window、ALiBi、softcap、sinks 等；公开说明还限制 speculative/multi-token decode。不能据此宣称支持完整 Inkling。
- [paged128](https://github.com/Intelligent-Microsystems-Lab/GAAC/blob/a2cbcb5eb22b2bf08bb614a01189163b85c07cdd/gaac/vllm/paged_kernel.py) 实际 GQA dispatch 集合为1/2/4/6/8；scale硬编码为1/sqrt(D)，与接受自定义scale的256路径不同。运行前须拒绝非匹配参数，或独立修改并验证。
- `supports_compute_capability()` 的宽泛返回不是 SM89 资格。需要具体编译、实际 launch、输出与资源证据。
- [store.py](https://github.com/Intelligent-Microsystems-Lab/GAAC/blob/a2cbcb5eb22b2bf08bb614a01189163b85c07cdd/gaac/vllm/store.py) 中 raw side pool pop失败的路径具有回落slot0后仍写入/更新记录的静态风险；host错误检查又有延迟。移植前必须实现预留/写入/发布事务，耗尽时不覆盖任何活记录。这里是源码审查发现，不是已复现事故或已修复声明。
- 已有随机位型测试排除了NaN/Inf；本包增加任意原始bits、signed zero、subnormal、padding和异常payload往返。
- `Page.nbytes` 等便利属性不是完整 allocation 账本；base、padding、scratch、raw pool、尾块与图池全部独立核算。

## 4. SplitZip：适合建立传输对照

[v4论文](https://arxiv.org/html/2605.01708v4) 与 LoomKV 对照实验的 ratio 来自不同模型/条件，不应写成一个全局压缩常数。FP8 有可能膨胀，需原始记录 fallback。

固定源码 [codec_gpu.py](https://github.com/Intelligent-Microsystems-Lab/SplitZip/blob/f6960f1487ab4a056f8565d749d355739dc8394a/codec_gpu.py) 使用可变 codec 对象中的 LUT；返回 payload 不等于自描述持久格式。必须冻结码本并在记录中引用不可变 digest。其 `.item()` 长度回读是同步点，需移出关键路径；完整 record 的 metadata、shape、offset、padding 都要计费。

新 [codec_fp8_gpu.py](https://github.com/Intelligent-Microsystems-Lab/SplitZip/blob/f6960f1487ab4a056f8565d749d355739dc8394a/codec_fp8_gpu.py) 分 E4M3/E5M2 和不同 code bits，不能笼统称“支持所有8-bit KV”。实际 raw tail 以完整8-chunk组为界，小于8192 bytes；加入8191/8192/8193边界测试。原量化所需scale必须一起保存。

公开实现的编码对象、实际 GPU allocation 与 wire-format 并非同一事物；需要真正序列化再从新进程重建并decode的测试。纯同一对象 encode/decode 通过，会漏掉码本和隐藏 metadata 依赖。

## 5. ZipFusion 与 ZipServ 的使用范围

ZipFusion 参考价值在于压缩布局和 Attention 消费顺序共同设计、压缩/raw混合与跨层释放。没有确认官方代码时，任务输入是论文与可复现规范，不是虚构 Git dependency。其论文计时范围不能替代本包完整请求与TTFT验收。

ZipServ 的 [Makefile](https://github.com/HPMLL/ZipServ_ASPLOS26/blob/15378387cb09634527ab0b20b7abfc9ffd5b62c5/build/Makefile) 明确含SM89；发布入口是BF16矩阵pack/decompress/GEMM。它为4090提供可阅读的位图/MMA实现参考，却没有动态KV append、页表、SWA/causal mask、checkpoint或GGML Q8_0接口。CPU packer 与GPU指数还原的连续表约束必须保留，不随意替换为任意Top-K字典。

## 6. 本包最终选择

1. 保留真实 Q8/F16/BF16 raw baseline，不预先为了获得论文比例而换格式。
2. L02 用 GAAC/SplitZip 的合法输入格式建立参考，并加上自描述记录、无条件精确escape、有界输出和独立进程还原。
3. L03 吸收 LoomKV 的 Tier 数据路径；不要求复刻 LMCache 进程结构。
4. L04/L05 只在真实容量/带宽瓶颈下研究 SM89 Pool，可借鉴 GAAC/ZipFusion/FragPack 的布局。原生支持范围外先拒绝。
5. 相邻 loop 的 XOR/delta/shared codebook 仅为新的研究假设；随机读取依赖链、恢复成本、逃逸率和状态身份均需另立实验，不默认纳入首版。

详尽静态发现与source pins在 [lossless-source-audit.json](../manifests/lossless-source-audit.json)；机器事实记录不构成GPU资格。
