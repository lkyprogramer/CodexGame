> V2 参考快照：P7—P12 不再是执行权威；按根目录 `plans/00-master-plan.md` 和 `plans/01-v2-migration-map.md` 执行。本文保留历史设计与来源，不表示实现完成。

# 全局 Selective Draft KV：可实现状态来源、检索与Graph

**目标：保留完整Target验证，只压缩Draft可见历史。** 全局覆盖不等于每轮读取完整历史；有界GPU工作集不等于无限免费历史。以下是本项目提出的新设计，不是tqLLM已有实现。[T04/T06/R01/R02]

## C07：Projected Feature Archive，不复用错误的payload

优先保存每个已提交位置的`G=enc_norm(fc(target_features))` BF16向量，维度`draft_hidden`。按tqLLM注入式结构，全部drafter层历史K/V可由G及冻结drafter权重重建。[T04] 这项等价性必须由P10reference/P11-T01逐层证明；模型变体若不满足，则禁用该archive方案，不能臆造重建。

拟定`src/targets/qwen3_8/impl/runtime/draft_archive.h/.cpp`：

```cpp
struct DraftArchiveIdentity {
    std::array<std::uint8_t,32> target_artifact;
    std::array<std::uint8_t,32> draft_artifact;
    std::array<std::uint8_t,32> frontend_resources;
    std::array<std::uint8_t,32> adapter_scope;
    std::array<std::uint8_t,32> prefix_identity;
    std::array<std::uint8_t,32> numerical_profile;
    std::uint64_t session_epoch;
    std::uint32_t layout_version; // 1 initially
};
struct DraftArchiveRange {
    std::uint64_t session_epoch;
    std::uint32_t first_token;
    std::uint32_t token_count;
};
```

numerical_profile涵盖Target量化/codec/执行路径、draft量化、位置变换、词表map；不能只用prompt文字做identity。archive只保存已提交前缀，pendingfeature在GPU事务scratch；accept后发布实际有Targetfeatures的行，bonus若尚未Target-forward，不得提前声称有对应G。`feature_frontier`与`token_frontier`分开，允许后者领先一个token并要求下轮补齐。

archive为进程级有界host分页池，多会话按identity/epoch共享明确引用；总预算不是每lane默认各2.5GiB。初版archive不跨进程持久化：Target L2/L3/slot restore仍可成功，但Draft缓存miss时退回合格后端。可在后续实现独立versioned sidecar，绝不把它塞进旧Target payload而继续沿用旧版本。复用PinnedTransfer设施和fence，不复用不匹配的Target KV字节。

## 全局两级候选

逻辑检索页固定256 token，独立于NInfer物理KV页尺寸；整个262144窗口共有1024逻辑页（最后不足页照实记录）。每页保留每个被索引draft层/kvhead的两条确定代表K和有效范围；1024页、5层、8KVhead、hd128、BF16时代表K约20MiB，仅为几何算例，不含meta/score和备份。

reference策略定义：每页按16-token chunk划分；在每页所有有效K中选择两条最大L2范数的代表，tie取较小token位置；实现不能用平均K却沿用该oracle。查询使用对应draft层anchor Q按GQA group均值，按L2归一化后的Q/代表K最大dot（cosine）得粗分，零范数代表分数为负无穷且mask；NaN视为输入错误。coarse选择8页（对所有draft层/head的粗分聚合取max，固定层/头顺序），tie小页号；精检索从这8页重建K，对每层/head沿用16-token chunk最大dot并取最多32chunks。这里的TopP8、R32是实验初值；被冻结的新配置必须把其内容加入policy identity。

Anchor另有256token预算，优先system/tools边界前256个token；预算不足时确定地截取，不引入未经评估的“理解Java语义”的分类器。Recent初值1536tokens，Retrieved最多512tokens；排重后按时间顺序排列，无效项mask为不可见。每个head可选择不同远端位置，但有效长度/padding和地址计算必须明确；第一版为简化graph可采用所有head的并集再截到总预算，reference与kernel必须选择同一策略。**本计划固定第一版采用逐head Top32，不做跨head并集**，stage按head保存position ids。

全局coarse扫描是O(N/256)，hostarchive是O(N)。只有Draft attention工作集与stage上限不随N增长；不得在复杂度汇报中写成“全系统O(1)”。需要超1M上下文时增加分层树是另一个项目，本轮不需要。[R01只提供研究方向，不为该具体索引背书]

## C08：位置策略、传输与图外刷新

初版复用tqLLM思想：远端K只在**drafter**内重定位到recent之前的virtual positions；在G→K投影完成、尚未RoPE时，按拟定virtual position施加一次RoPE，避免对已低精度旋转K重复旋转。V不旋转；recent保留对应位置。Target的原始KV位置、三轴MRoPE和attention完全不变。原始位置模式作为对照，不能混用identity。[T06]

流水线明确分开：

```text
committed feature/G --D2H async--> bounded HostDraftArchive
                        |
GPU coarse scores -> selected page ids --small D2H--> host worker
                                                        |
                     fixed staging <--H2D G / project K,V / RoPE
                          |
                 ready event + matching epoch
                          |
                  fixed-address Draft graph
```

CPU查archive和H2D不能被伪装成全GPU captured graph。P11的目标是恢复**Draft计算子图**的固定shape fast path，不宣称host检索端到端无CPU或无同步。每8个推测轮尝试刷新一次（初值），刷新成本、过期率和接受收益都要记；不用cudaDeviceSynchronize等待。显存支持A/B双stage且都计入预算，图绑定可预建两种固定地址，切换前等待完成event。新结果未就绪时复用仍合法的旧selection（其选中页必须在同一prefix内），否则recent-only；不能让Target执行线程同步读磁盘。

## 事务与生命周期

每个异步刷新绑定`session_epoch + lane_generation + prefix_identity + feature_frontier + policy_generation`。lane复用、adapter切换、工具修改历史、取消、slot restore或archive淘汰后，迟到结果必须被丢弃且归还lease。D2H导出与P2 continuation export一起经过lane重写fence，避免刚归还页被worker继续读取。

请求采用DFlash2前必须先达到最低recent所需feature覆盖；缺archive不能仅改变日志而继续使用随机/旧buffer。新cold请求可在真实prefill增量建archive；旧warm Target命中且archive不足则保持MTP/None，成本记作已选择的后端，不记DFlash2 cache hit。输入中途重写只保留hash一致的前缀页，边界页清除/重建，绝不能把新分支接到旧GDN状态。

## 不推进的情况

ProjectedG重建不等价、host预算不满足、全局代表检索无法命中早期针、刷新吞吐抵消接受收益、额外graph显存挤掉262K任一项成立，则P11 NO_GO。可继续使用P10 ring-only或P8/P9候选；不能用不匹配的Target L2弥补数据缺口。
