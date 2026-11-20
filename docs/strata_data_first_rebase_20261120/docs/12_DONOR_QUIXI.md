# QuixiInfer：借因果归因和实验记账，不移植三层专家引擎

对象：[QuixiAI/QuixiInfer master `ce25391`](https://github.com/QuixiAI/QuixiInfer/tree/ce25391bff43ac9bb101e8d1f62e3705f8972494)，无 GitHub release/tag。该快照 README 和生产 handoff 均以 DeepSeek-V4.1-Flash 为当前主路径，历史 Qwen 代码不代表 4090 生产支持。
本机新基线未绑定；历史是 Qwen3.8-Flash-Next GSQ-RCO IQ3_XXS 两分片、Xeon Silver 4216、PCIe Gen3 ×16。其他模型、量化、PCIe 或内存不能换进同一个 A/B。

## 代码里的真实架构与开关边界

| 机制 | 代码证据 | 应避免的误读 |
|---|---|---|
| 三层专家、GPU 请求 mailbox | [engine](https://github.com/QuixiAI/QuixiInfer/blob/ce25391bff43ac9bb101e8d1f62e3705f8972494/crates/qx-engine/src/dsv41/mod.rs) 与 [driver](https://github.com/QuixiAI/QuixiInfer/blob/ce25391bff43ac9bb101e8d1f62e3705f8972494/crates/qx-engine/src/dsv41/driver.rs)：VRAM、锁页 RAM、NVMe；AVX-512 VNNI 与 staged DMA 分担 miss；NVMe 用 direct I/O 与 io_uring | 不假设当前 Strata 的 CPU/主存等待同样是瓶颈，不照搬 5090 迁移比例 |
| Prompt chunk | layer-major、大块只搬每层需要的专家；短块精确组 kernel、长块生产 F16，且可省不接入尾部状态的部分上层 | 部分 prefill 路径数值不等价；输出并不当然随 cache 命中与相同种子锁死 |
| 存储弹性 | 大 context 未用 KV store tail 可给专家；独立 RAM-yield 用专用 arena 退回主存 | yield 是减 OOM/共享机器容量，实测有 pause，不是 decode 提升 |
| 推测和准入 | [worker](https://github.com/QuixiAI/QuixiInfer/blob/ce25391bff43ac9bb101e8d1f62e3705f8972494/crates/qx-serve/src/worker_ds.rs#L448-L487)：单解码器为首选，按匹配长短与来源记收益；失败 rollback/refeed；字面草稿由 target 确认；最长 prefix 影响等待请求准入 | 前缀复用不是同会话 token index；默认跨请求文本 corpus 存在时序侧信道，禁止移到多人服务 |

worker 按 own/corpus × 命中长度构建四个桶，独立决定 `k` 与 backoff（负收益就暂停）；宽度不在已 seal 的 graph 集合还会折回。“只有 proposal”不代表测量中真的走到该 verify window。[提案与宽度处理](https://github.com/QuixiAI/QuixiInfer/blob/ce25391bff43ac9bb101e8d1f62e3705f8972494/crates/qx-serve/src/worker_ds.rs#L777-L827)、[反悔和结算](https://github.com/QuixiAI/QuixiInfer/blob/ce25391bff43ac9bb101e8d1f62e3705f8972494/crates/qx-serve/src/worker_ds.rs#L995-L1050)。
`QX_DS_SPEC_MULTI=0` 默认不在别的 decoder 旁开启：试验中 file edit 30.9→25.4s，但旁路 essay 23.2→29.4s。单流复写测得 27.3→17.0s，不能外推到一般 coding；其他请求回复恰同题时的高收益不能拿来设置生产共享索引。

## 原数字可重复到什么程度

来源：[README 条件/指标](https://github.com/QuixiAI/QuixiInfer/blob/ce25391bff43ac9bb101e8d1f62e3705f8972494/README.md#L42-L92)、[summary](https://github.com/QuixiAI/QuixiInfer/blob/ce25391bff43ac9bb101e8d1f62e3705f8972494/perf/baselines/rtx-5090_ryzen-9-9950x_121g/summary.md)、[run.json](https://github.com/QuixiAI/QuixiInfer/blob/ce25391bff43ac9bb101e8d1f62e3705f8972494/perf/baselines/rtx-5090_ryzen-9-9950x_121g/run.json)、[raw JSONL](https://github.com/QuixiAI/QuixiInfer/blob/ce25391bff43ac9bb101e8d1f62e3705f8972494/perf/baselines/rtx-5090_ryzen-9-9950x_121g/results.jsonl)。

- RTX 5090 32GiB、Ryzen 9 9950X、128GB DDR5 双条、NVMe；DS-V4.1-Flash-1017 UD-IQ2_XXS 的 `.qxp`，非本机合同。`setd-promo39` 的工作树哈希与当前 HEAD 区分，原 summary 有 `correctness skipped`，几个 case 样本仅 1/1。
- 单流 1k：31ms/token；恢复到 256k 后强制 decode 39ms/token；3×262k 并发约 81ms/token/请求，三路各 12.4 tok/s、合计约 37，不是单路 37。
- 500 tok/s 是 256k prompt **最后 8k**，不是从 0 到 256k。16k 从空跑，已编译以后的 1392 tok/s 和新进程 1132–1158 不是同一种状态。
- 对照 Strata 的 cold 启动、最后 64 tokens 计法与并发能力不同，主要对照一次，不适合作为性能排序。18.475 是多个 case 的几何平均 ms/t，保留它的分项，不把分数当新指标。
- 生产 F16 prompt chunk 为误差限而非位同：报告 KL≤0.03/top1≥95% gate；fresh 与复用 prefix 的 greedy 可能不同。小窗/多序列/恢复等另有 [ds-checks](https://github.com/QuixiAI/QuixiInfer/blob/ce25391bff43ac9bb101e8d1f62e3705f8972494/tools/ds-checks.sh)，不能从该 run 的速度摘要推断所有 parity 都证明了。

## 对自己的反例尤其有用

见 [findings](https://github.com/QuixiAI/QuixiInfer/blob/ce25391bff43ac9bb101e8d1f62e3705f8972494/perf/findings.md#L16-L61) 与 [历史 Qwen/Strata RCA](https://github.com/QuixiAI/QuixiInfer/blob/ce25391bff43ac9bb101e8d1f62e3705f8972494/docs/strata-rca.md#L1-L75)。

1. 前缀从一种主题切换，VRAM 占比曾从约 56% 掉到 17%、很久才回升；真实因子是 cache 衰减按 window 而非 token，不能仅用“位置长了”归因。
2. 按上一个 token 预取，在 256k 仅覆盖约 23% host-served picks；大提速不能由“预取得很忙”推导。64–255 token 的 chunk 可减短 prompt TTFT，但并发 decoder 9.31→8.43 tok/s；更短的某类请求反而慢。
3. 短 prompt 曾把 io_uring submit/read 等待错算 PCIe；独立驱动时间和 Nsight copy timeline 把两者区分。另一次把 NVRTC 反复 CUDA OOM 错认为 glibc arena，见 [memory 工单笔记](https://github.com/QuixiAI/QuixiInfer/blob/ce25391bff43ac9bb101e8d1f62e3705f8972494/perf/findings.md#L168-L185)。
4. 历史 Flash-Next NVFP4/5090：400-token 64k 从 81–82→95 tok/s 是一揽子改动；113 tok/s 是 2000-token warm 尾段，不能用来对标 Strata 的 400-token 114–116。对照 Strata pack 原作者还无法本机运行。
5. 同一历史试验放宽 early admission 后，mixed-load hit ~70%→13–20%、合计约 33 tok/s，降级为 opt-in；显式专家 group 在 CPU-bound 的 16 sequences 只 +1%。CPU pool 单跑 54 GB/s，加 DMA 后 CPU 29 + DMA 28 ≈ 57 GB/s，说明共享 DRAM，不能相加各自不争用的峰值。
6. RAM-yield 模拟 VM 退回 12GiB，256k decode 39.0→42.2ms/token，切换 pause 0.5–1.7s。真实 VM 当时尚未测，容量 UX 可以独立讨论，不能放入优先加速路径。

### 三种合约不能揉在一起

| 比较 | 合法基准 | 主要混淆项 |
|---|---|---|
| forced 位置尾段 | 同一 token position、同一 capture warming 和 cache 方式、固定短输出 | 第一次 CUDA graph capture 除以几十个 tokens，会显著污染均值 |
| 冷/热单流端到端 | 固定 prompt bytes/token IDs，从 client request 开始，分别看 TTFT、结束 wall | 进程编译缓存、HTTP、首 token 与 decode 稳态不能叠成单个 tok/s |
| 并发 server | 固定各客户端时序与 prompt 组成，既报 aggregate 又报 per-stream ITL | 优先大 prefill/提升整机 t/s 可能让旁路单用户 p95 变差 |

[scoreboard](https://github.com/QuixiAI/QuixiInfer/blob/ce25391bff43ac9bb101e8d1f62e3705f8972494/perf/scoreboard.md) 有 case median、平台和过程注记。重用的是这种 provenance，不是作者的几何均价。

## 在当前 Strata 里如何用这些证据

上游 [prefill](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/src/prefill/prefill.cpp#L4530-L4556) 已有 routable issuer 控制，[专家路径](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/src/core/expert_source.cpp) 已有多种 cache/staged/CPU 机制；[DraftPolicy](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/src/spec/draft_policy.cpp#L577-L630) 已有窗口成本逻辑。旧 workspace/expert lending、去重、调度/CPU gap 结论不因这家有相似实现而失效。

| 归因问题 | 最小事件与口径 |
|---|---|
| 为什么此位置更慢？ | 固定生成长度的 pos bucket、相同 prompt/主题；记录 warm/cold、cache reuse、capture/unfitted/late 热状态分层 |
| 是因为 host 驱动还是 DMA 吗？ | CPU pool 启停/runnable/flag ready、copy enqueue/event ready、GPU wait 起止与原因；合成互斥时间，并单记 overlap |
| 是数量多还是每条慢？ | 每层 unique route、residency-before-demand、host/stage/NVMe page fault、transfer bytes；首/尾时间和实测 concurrency |
| 推测有没有把工作推给别的步骤？ | source/bucket、proposed/accepted/committed、实际 width、rewind/refeed、CUPTI/TTFT/ITL 分别看 |

### 判定顺序

1. 先看位置和请求组成固定以后是否仍有 excess wall。如果只在冷启动见到，记录为冷路径，不贴到所有长 decode。
2. 然后确认 excess wall 与具体事件重叠。例如有 H2D bytes 只说明通路工作，不说明依赖它的 GPU kernel 在等。
3. 只有冷/热与相同位置证据同时支持时，才算改变了某条已关闭路线的前提；没有结构性变化，不扫比例。
4. 跟踪跨请求 timing 能泄露信息的实验路径，不能把同会话查询隔离当成可选优化。核心采集尽量不存可逆文本或跨会话 token。

输出摘要建议分成「原因已证实」「可排除」「缺字段，暂不能判断」。同一请求里 trace delta 与 path availability 一起报告，不能拿 donor 的 `likely` 对填数据。

这不是新候选实现。除非当前基线在真实工作负载且固定位置对照中说明瓶颈换了，并且端到端机会达到 **至少 4% 且超过 2× A/A 噪声**，否则不开一轮新的 CPU/DMA、工作区、专家分层或 HC 参数测试。测出的是均值以外的 capture/队列尾时，只在相应冷态报告，不夸大稳态收益。
正式采样和停止规程见 [05_DATA_MODEL_AND_MEASUREMENT.md](05_DATA_MODEL_AND_MEASUREMENT.md) 与 [18_CANDIDATES_AND_STOP_RULES.md](18_CANDIDATES_AND_STOP_RULES.md)。
