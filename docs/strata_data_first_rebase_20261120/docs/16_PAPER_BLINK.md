# 16｜Blink：分开控制面与专家计算，不移植整套 CPU-free serving

## 1. 论文身份与代码可得性

arXiv [2604.07609v1](https://arxiv.org/abs/2604.07609) 为 **Blink: CPU-Free LLM Inference by Delegating the Serving Stack to GPU and SmartNIC**，Mohammad Siavashi等，提交2026-04-08 UTC。本轮读取[全文](https://arxiv.org/html/2604.07609v1)的设计、实验与限制章节，并做两轮公开实现定向检索（每轮5个候选，有重复）。

**未核实到可固定commit的作者公开实现。** 论文表述为计划发表时开源；本包只把已读设计当论文证据，不编造源码路径或启动命令。HTML里的旧ACM模板年份不是论文日期。

## 2. 底层分工

~~~mermaid
flowchart TD
    A["Client HTTP"] --> B["SmartNIC DPU"]
    B --> C["Tokenize / request queue"]
    C --> D["RDMA GPU ring"]
    D --> E["GPU 常驻控制CTA"]
    E --> F["Graph batching / KV / decode"]
    F --> E
    E --> G["Completion ring"]
    G --> B
    B --> H["SSE response"]
    I["CPU 初始化"] -.-> E
~~~

DPU负责API/输入输出，GPU256-thread常驻控制CTA做admission、batch、KV管理及device-side CUDA graph调度。fire-and-forget配合tail-launch更新父窗口，处理outstanding launch限制；共享ring依赖owner/state transition。CPU不在其steady-state控制路径。

与Strata的关键差别：你当前模型的CPU不仅负责“发kernel”，还可能承担必要的量化专家计算、权重/状态I/O与数据准备。移掉CPU控制不可能自动移掉这些数学和存储工作。

## 3. 实验条件不对应4090工作站

| 论文条件 | 本项目区别 |
|---|---|
| H100 96GB、256GB RAM、BlueField-3、200Gbps RDMA | 单4090 24GB/64GB；没有同等DPU与显存余量 |
| FP16模型全驻GPU | 目标为量化MoE/CPU offload等混合路径 |
| 1–32req/s offered load，每点60s | 主要长上下文agent会话/少量子任务，不是同分布 |
| TRT-LLM1.1.0、vLLM0.13、SGLang0.5.8 | 不是当前Strata相同资产对照 |
| chunked prefill、prefix caching、CPU offloading关闭 | 用户反复依赖的核心能力恰在这里 |
| graph cache约650–1000项/2–4GB | 对24GB预算是显著成本，不可忽略 |

以上边界来自全文§4/§6/§7。speculation、prefix、offload、multi-GPU在扩展讨论中出现，不等于已实现与验证。论文的高百分位改善不能直接换算为你的tok/s。

### 3.1 正结果和接近无收益的结果都要看

论文四个模型为Llama-3 8B、Phi-4 15B（14.7B）、Qwen-3 32B、Qwen-3 30B-A3B。下表只摘[§6.2 / Table 6](https://arxiv.org/html/2604.07609v1#S6.SS2)的两个对照，单位均ms；每格为“P99 TTFT / P99 TPOT”的**跨负载几何均值**，不是某次单请求吐字速度。

| 模型与作者划定负载区间 | Blink | 同compiled engine的TRT-LLM | SGLang |
|---|---:|---:|---:|
| Qwen-3 30B-A3B，λ≤4 req/s | 1397.5 / 35.5 | 4814.7 / 65.8 | 11839.8 / 120.8 |
| Qwen-3 32B，λ≤2 req/s | 9481.3 / 113.4 | 9621.4 / 115.2 | 11413.0 / 123.3 |

区间按**Blink自身吞吐饱和点**划定，其他基线可能已在其中排队；因此大倍数同时包含可承载负载的差异。GPU-bound的32B与TRT几乎持平，说明控制面优化有明确边界。§4.2 Fig.3另一组同engine/H100/batch16消融中，CPU逐步往返路径makespan为GPU调度的1.16–1.70倍；这是特定调度消融，不能套到Strata现有graph/offload路径。

§3的CAT隔离反例同样值得保留：LLC miss从57.6%降到6.8%，P99 ITL却仅55.6→54.0ms。这支持本包的判断方法——低层counter改善必须闭合到任务终点，不能把漂亮counter当优化成功。

## 4. 真正值得补进基础能力的三件事

### 4.1 CPU成本按职责拆分

至少区分harness等待、HTTP/API、server queue、native scheduling、CPU expert compute、DRAM争用、文件/页缓存、发布。CPU利用率高不等于host控制是瓶颈；旧0.12–0.13% host gap也不表示新版本全部CPU路径都只有这么多。

要证“host干扰使GPU闲”：同一请求依赖、CPU runnable/排队与GPU ready-but-idle的时间对应，不能凭两张平均利用率曲线。先read-only观测，只有真的出现才考虑授权的隔离对照；不默认运行压力负载或改绑核。

### 4.2 Ownership 与完成发布

request/slot/epoch复用、cancel/timeout、publication以及下次续聊必须可追踪。恢复到某个cache generation后，什么时候状态ready、什么时候可以对client宣告完成，需要明确终点。

这与先前Hyperkernel服务增补的ownership/progress思路重合：若已实现就映射新路径；未实现则作为P2小挂点，不再写一个GPU常驻调度器。

### 4.3 服务端与用户端不同终点

device已commit、服务已解析、SSE已write、client已收完整工具参数，是不同事件。任务收益必须落到用户真正等待的终点；减少CPU发射不等于省去了应用工具I/O或子代理排队。

## 5. 不进入本轮的路线

- SmartNIC/RDMA与全CPU-free改造：硬件、量化/驻留/服务语义不匹配，成本过大。
- 持久megakernel或整套device-side调度：无本机新关键路径证据，旧host-gap路线不能靠论文标题重开。
- 把device-side graph等同PDL，再宣称sm89全部不能做或全部可以做：两者不同，能力按API独立查。
- 为支持Blink先关闭prefix/offload/chunked预填充：这改变目标负载和功能，不能算Strata优化。

## 6. 后续可证伪问题

只在P3观察到实际控制等待时提出：同一计算/缓存/请求下，是否存在可减少的CPU orchestration关键段？该段是否大于max(4%,2×AA)门对应时间？新复杂度与显存开销会不会抵消？

若答案仍是旧窄gap且没有新机制，归档NO_HEADROOM。若等待属于CPU专家或DRAM，转成相应事实报告，不能将“CPU-free”当修复方向。论文贡献纳入基础能力即可，不强凑性能候选。

