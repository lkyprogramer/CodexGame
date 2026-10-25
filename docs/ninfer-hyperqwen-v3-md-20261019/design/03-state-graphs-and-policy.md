# 状态对齐、CUDA Graph 与复制控制器

## C15：不要混用frontier

至少分别记录：Target已处理输入frontier、已许可输出长度、MTP已对齐frontier、Draft feature已提交frontier、Lookup history长度。全接受后的bonus token已输出不代表其Target hidden已经计算；它常作为下一轮anchor。因此不同frontier的关系必须由现有row/round契约推导，不是简单强制数值相等。[NI03/NI04]

NI04显示MTP路径在verify之后调用 `mtp_prepare_next_round`、`mtp_forward_decode_batch` 做alignment，再生成下一轮proposal。Lookup接收了比MTP更长的尾部时，alignment必须覆盖对应已计算Target hidden，而不是只对齐末尾一个token。若alignment kernel未覆盖W8/W16，先实现精确分块/新shape，并用独立串行teacher-forced oracle比较。

**COPY模式省略的是神经proposal生成，不是所有MTP forward。** 每轮保留必要alignment；若尝试延迟对齐，则显式进入NEEDS_SYNC、保存有界pending已提交hidden，重入时先catch-up，并把cost计入。第一版默认eager alignment，避免复杂延迟状态和隐藏长prefill。

## C16：每lane控制状态

拟建 `src/runtime/generation/hybrid_policy.h/.cpp`：

```cpp
enum class CopyState : std::uint8_t { Short, Probe, Copy, Cooldown };
struct HybridFeedback {
    std::uint64_t lane_epoch, request_epoch, round_id, resource_generation;
    std::uint32_t committed_tokens, accepted_drafts, proposed_tokens;
    std::uint32_t lookup_valid, match_tokens;
    bool terminal, rejected, transfer_complete;
    double round_wall_ms, alignment_ms;
};
struct HybridDecision {
    std::uint32_t physical_verify_width; // qualified physical W; logical V is separate
    bool run_neural_proposal;
    bool requires_resync;
};
HybridDecision advance_hybrid_policy(HybridPolicyState&, const HybridFeedback&,
                                    const QualifiedCostTable&);
```

`HybridPolicyState`与`QualifiedCostTable`在H4-T04同一头文件完整定义，禁止邻近worker另造同名schema。cost表按context桶、active lanes、cache路径、W、proposal profile分桶，使用校准集，不在固定评测集上调整。

初始策略：连续2个新鲜、合格、候选足够且前轮输出饱和的反馈才从Probe进入Copy；仅在估计每committed-token成本至少低5%时切宽。Copy允许最多2个短暂证据丢失的宽验证（实验初值）；**真实拒绝立即退出drafter-free模式**，不能被Sticky覆盖。Cooldown至少完成1个正常proposal+verify步后才准再次进入。stop、cancel、epoch变更、资源失效立即清空状态。

缺失数据不填0成本。反馈event未完成时继续保守短路径；允许使用已完成旧反馈作为性能提示，但必须同request/lane epoch、round_id单调且只消费一次。绝不读DMA还在写的pinned buffer。

## C17：graph生命周期

graph内只做设备数据流；host策略在每轮图外执行。采用双buffer反馈，各有CUDA event；以非阻塞event query判断可读性，不能每步cudaDeviceSynchronize。资源预分配，capture期间无新分配/host未来状态分支。

Graph key 至少包含backend形态、物理W、物理B、context envelope/拓扑、KV codec、proposal profile、resource_generation；逻辑V/valid-mask为设备输入。verify/align/propose分图时图体类型也须区分，不能将skip路径和完整proposal图错用。lane token offset/valid值写设备输入buffer，不将变化位置误当固定捕获值。若图绑定真实lane指针，key还必须区分lane binding，或改为稳定间接表并证明一致。

首版H4 Copy/W16仅C1资格；C2/C4保持固定宽度已合格route。扩展多lane时按同构width/backend分组，轮转不饥饿，不借其他请求的命中信号给本请求启用长块。H8未验证该组合则不发布该组合。

## C18：错误及恢复

提案失败：本轮不产生未授权输出，使用原已ready的短MTP或ordinary；设备context故障仍走原致命路径，不统统伪装成可恢复proposal错误。RoundFault按原轮级作用域放弃pending状态。late DMA、cancel期间index更新、slot erase/save/restore都以epoch隔离。缓存目录与发布镜像三件套分离，详细部署见 [运行手册](08-deployment.md)。

## Proposal head更换与状态最小失效

proposal head改变只影响提案token选择，不自动改变同一已提交历史上的Target状态。可以沿用的MTP已对齐KV/hidden必须先用完整identity/frontier证明一致；尚未验证的旧proposal、候选token缓冲及绑定旧head地址的Graph一律失效。首版采用保守的aux重建策略可以，但应单列恢复成本，不让Target缓存无故失效。

头部完整精度只读权重与映射在启动冻结。回滚的旧head默认保留在旧artifact/镜像中，不要求两个head都常驻GPU；配置确需同时驻留时必须按实际双份内存记账。

## sampling与COPY状态

COPY可跳过deterministic proposal，但最终Target仍按原sampling/processor/RNG接受、residual或bonus；真实拒绝后恢复proposal/mandatory alignment的状态机保留。每列count overlay使用最终mixed prefix，不让被拒尾或stop后token修改全局count。不得用本轮accept/correction/bonus随机数决定Lookup/宽度候选；只能用已完成历史反馈。Graph/eager、lateDMA、restore与width切换按design/11补sampling合同，未资格组合不开放。
