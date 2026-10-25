> V2 参考快照：P7—P12 不再是执行权威；按根目录 `plans/00-master-plan.md` 和 `plans/01-v2-migration-map.md` 执行。本文保留历史设计与来源，不表示实现完成。

# 推测策略、共同验证与状态提交契约

这是新增接口设计，**不是当前NInfer已经提供的API**。Integrator在P8-T01冻结声明；其他task按本页消费者/生产者边界工作。源码基础：现有SpeculativeOptions为startup配置；TargetVerifyFrameView与target_verify_accept已存在。[N05/N06]

## C01：请求级选择，启动期资源集合

新增`src/runtime/generation/speculation_policy.h/.cpp`，命名空间`ninfer::runtime`。公共`SpeculativeBackend`保留None/Mtp/DFlash原值，在尾部追加`PromptLookup`和`DFlash2`；不得让旧DFlash含义变成DFlash2。

```cpp
struct SpeculationRequestFacts {
    std::uint32_t prompt_tokens;
    std::uint32_t output_budget;
    std::uint32_t expected_output_tokens; // frozen calibration; never an unmeasured zero
    std::uint32_t active_lanes;
    bool greedy;
    bool has_media;
    bool has_adapter;
    bool decision;
    bool mtp_ready;
    bool dflash2_ready;
    bool lookup_hit;
};
struct SpeculationCandidate {
    ninfer::SpeculativeBackend backend;
    std::uint32_t proposed_tokens;    // MTP/chain: 1..5; None:0
    double fixed_cost_ms;            // bridge/init/refresh charge, measured
    double ms_per_committed_token;   // not per accepted draft
    bool qualified;
};
struct ResolvedSpeculationPlan {
    ninfer::SpeculativeBackend backend;
    std::uint32_t proposed_tokens;
    std::uint32_t verify_columns;    // chain K+1; ordinary1
    std::uint64_t resource_generation;
    std::string fallback_reason;
};
ResolvedSpeculationPlan select_speculation(
    const SpeculationRequestFacts& facts,
    std::span<const SpeculationCandidate> candidates,
    std::uint64_t resource_generation);
```

C++20头文件明确include `<cstdint>/<span>/<string>`及`ninfer/types.h`。新增candidate enum并在所有switch、日志、CLI、reference路径补全。已加载且已资格的能力集合在Engine构造时冻结；新配置文件`profiles/speculation-policy.json`是本计划提出的运行契约，不当成现有CLI。P8-T01新增`--spec-policy FILE`解析，未传保持原`--spec`行为。模型或context/codec不匹配calibration fingerprint时禁用auto，回到固定合格配置；不自行联网下载资产。

首版只在请求开始、lane已选定、真实cache/bridge条件已知时解析一次。拟用成本=`fixed_cost_ms + min(facts.output_budget, facts.expected_output_tokens) * ms_per_committed_token`。缺校准不用0填充，直接不作为候选。相同成本优先None，再MTP，再Lookup，再DFlash2，防止无意义切换。校准按实际prompt深度、并发数、缓存路径分桶，不把128K的单请求曲线套在4路混合上。最终资格时校准配置也必须冻结。

Decision永远None；首版DFlash2只对greedy、纯文本、base权重开放。非greedy/图片/LoRA退到原已验证且状态已就绪的MTP，否则None，日志写原因。不能默认原MTP对所有组合都支持，资格表是准入依据。请求中途不加载新drafter、不切换backend；MTP宽度按请求固定。轮内宽度调整留到另一次数值/graph资格，不塞入本轮。

## C02：Lookup和DFlash2只提案

新增`src/runtime/generation/prompt_lookup.h/.cpp`：

```cpp
class PromptLookup {
public:
    explicit PromptLookup(std::size_t maximum_tokens);
    void reset(std::span<const ninfer::TokenId> committed_prefix);
    void append(std::span<const ninfer::TokenId> committed_tokens);
    std::vector<ninfer::TokenId> propose(std::uint32_t maximum_drafts) const;
};
```

索引只由本请求的token化prompt和已提交output构建。suffix n-gram长度依次8、6、4，优先更长匹配，再选最近的历史位置；哈希只是候选，逐token校验后取其后最多K个token，禁止读过已提交frontier。最大K=5；无匹配返回空并执行ordinary，不访问其他用户/adapter会话。每次append只更新新增加的索引项；重写/新请求reset，索引预算用实际最大context入账，预算耗尽时关闭Lookup而非丢弃Target历史。

新增`src/targets/qwen3_8/impl/runtime/external_draft_schedule.h/.cpp`，供Lookup和DFlash2调用共同chain入口：

```cpp
void verify_external_chain(
    schedule::ExecutionCore& execution, Tensor& continuation_hidden_store,
    TextContext& text, schedule::TargetVerifyFrameView frame,
    ops::GqaExecutionEnvelope envelope);
```

签名中的ExecutionCore、TextContext、Tensor等均用已有schedule定义。该函数检查`width=K+1`、有效列与lane映射，然后调用已有`target_verify_accept`；不得复制接受算法。P8-T04负责将外部提案填入frame，并由Program原pending/resolve路径提交。P10只增加新的提案生产者。

## C03：精确性定义与采样边界

首版保证目标是**相对于同一Target参数、量化、完整可见KV、采样/停止设置的greedy token序列一致**。DFLASH候选错了只多花时间，不能直接输出。四种情况必须覆盖：0个接受、部分接受、全部接受+bonus、输出预算/stop恰好截断。

tqLLM将plain/verify attention统一是值得借鉴的方法，但不自动证明NInfer所有宽度相同：GDN、projection、归约顺序、量化舍入也可能影响logits。发现差异记录首个不同token之前各层hidden/GDN/attention差值，先修复或改用精确路径；不得将“语义差不多”“近似tie”写成greedy exact通过。[T02/T09/N05]

随机采样不是greedy一致性。经典ratio接受需真实条件`q(token|history)`和拒绝后的归一化`max(p-q,0)`；DFlash2 top16/lattice能量并非天然满足该定义。[T07] 另一种target-sample-match可以在不使用q的前提下保持分布，但需要独立的目标抽样、counter-based RNG消耗和正确条件顺序，不能顺手声称当前实现已支持。首版新Lookup/DFlash2路径对非greedy禁用。未来采样工作必须另加小词表穷举分布、RNG重放、temperature/top-p/top-k联合测试；“同seed同文本”既不是分布正确性的充分条件，也不是所有正确算法的必要条件。

## C04：GDN、KV和输出只提交许可前缀

顺序固定：选择提案→完整Target verify→得出licensed前缀→原row commit contract→ReplaySSM恢复/推进→更新Draft/Lookup已提交frontier→发布输出。候选token对应的feature可暂存，但未许可部分不能写入可复用archive。取消、RoundFault、context容量失败都走原故障作用域；独立提案错误不得破坏已提交Target状态。

新backend并发首版仍使用原bounded FIFO，无优先级抢占。batch形成时按已解析backend/width分成同构子batch，轮转队列顺序，防止低命中Lookup或重检索请求独占执行线程。显式记录分组造成的有效batch下降及p90排队时间。异构填充最大宽度不是免费动态K；实际graph/kernel计数必须证明少算了列。

## C05：观测字段

追加`request_done.extensions.spec_perf_v1`，保留核心schema24及原prepare_detail。字段：`requested_backend`、`resolved_backend`、`proposed_tokens`、`physical_draft_rows`、`verify_columns`、`rounds`、`drafted_tokens`、`accepted_drafts`、`committed_tokens`、`round_wall_ns`、`graph_hit/miss`、`fallback_reason`、`archive_hit/miss`、`retrieval_refreshes`、`retrieval_candidate_pages`、`host_transfer_bytes`。详细GPUspan写受控性能sidecar，不把token内容/图像字节放入日志。

只在取样轮放CUDA events，生产默认低采样频率；不得每层cudaDeviceSynchronize。`draft/verify/commit/retrieval/transfer`有重叠时报告包含关系，成本比较用nonoverlapping关键路径round_wall。监控基线off/on对照，不把仪表自身开销算成新算法退化后掩盖。
