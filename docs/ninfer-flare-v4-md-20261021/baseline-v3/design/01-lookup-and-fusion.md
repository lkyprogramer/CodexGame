# Lookup、融合与复杂度约束

## 正确的历史边界

Lookup 只消费本次请求已经 tokenized 的有效输入与已许可输出。当前请求重写、truncate/compact、reset、lane复用均递增history_epoch并按新token序列重建；不能拿prompt_cache_key相等代替token前缀相等。候选可以包含合法added-token ID，但 stop/EOS仍由Target的停止策略处理。history包含已经作为输出交付、尚作为本轮anchor处理的token；不能再把anchor重复append。首版media/adapter请求不进入新分支。

提供以下拟建接口，路径 `src/runtime/generation/prompt_lookup.h/.cpp`：

```cpp
struct LookupMatch {
    std::uint32_t source_end = 0, match_tokens = 0, valid_tokens = 0;
    std::array<ninfer::TokenId, 15> continuation{};
    bool candidate_budget_exhausted = false;
};
class PromptLookup {
public:
    PromptLookup(std::size_t maximum_tokens, std::size_t index_budget_bytes);
    void reset(std::span<const ninfer::TokenId>, std::uint64_t history_epoch);
    void append(std::span<const ninfer::TokenId> committed);
    LookupMatch propose(std::uint32_t maximum_drafts) const;
};
```

header 的 `<span>/<array>/<cstddef>/<cstdint>` 与 TokenId include 必须齐全。无匹配返回valid=0；hash碰撞只能增加候选验证成本，不能输出未经逐token核对的匹配。

## 首版算法选择

优先 CPU 有界索引：以4-token hash查候选end位置，再向前验证到最多12-token；候选列表以结束位置降序遍历，最多核验64个；在已核验集合中优先更长匹配，同长度取最近位置。每查询最多核验64个候选，最多15个后续token；索引候选来自整个本请求历史，不只最近65K。32MiB host/lane 为**起始预算上限**，token mirror另记；不够时关闭Lookup并记录reason，不缩减Target历史。

候选预算意味着不保证找到全历史的最长匹配：存在大量同hash/同4gram时，较早的长匹配可能未被访问。oracle必须区分“proposal有效”与“全局最优召回”，不能用不完整索引冒充全扫描等价。低熵重复、同前缀大量方法名、相邻重叠匹配都要测。GPU全扫描是H1的对照，不是默认更快；选择依据含初建/append/查找/Host↔GPU传输的净成本。

不引入每请求重新BPE、不在每生成token重扫整段历史、不把NInfer已有B0改回通用tokenizer。索引只在已提交append时增量维护。

## 融合规则 C14

输入 Neural 向量 N、Lookup向量 L及匹配长度 m。输出一个连续前缀候选，不是两棵树。H1阈值是实验初值：nmin=6、nstrong=8、agree_min=2、tail_min=4。最终由H5冻结；不把donor默认值视为最优。

令 `agree = min(两者首个不同位置, L.valid, N.length)`。

1. `take_head = m>=8 || (m>=6 && agree>=2)`。成立则可用Lookup替换头部。
2. 使用Lookup长尾必须满足 `m>=4 && (take_head || agree==N.length)`，并且Lookup真实覆盖头部到尾部。**头部替换只覆盖一小段时，不能接上一个依赖原神经前缀的孤立尾段。**
3. `take_head` 且 L.valid<N.length：首版保守地截到Lookup提供的连续长度；不接剩余神经尾部，除非已证明它依赖的所有前序token完全一致。损失的是提案效率，不是Target质量。
4. `take_head=false` 时保留神经候选；仅完整头部相同时接Lookup额外尾部。
5. lookup缺尾/源已耗尽/epoch不符，截断或使用已合格神经候选；任何padding不能成为“有效草稿”。

如果提出lookup-only，L从当前真实后缀出发，整个K均有明确来源。第一版不做任意“先MTP再对其尚未提交尾部查库”的串联扩展。后者需要更复杂条件历史，留作独立试验。

## 独立例子

N=[10,20,30]，L=[10,20,30,40,50]：头一致，允许尾部40/50。
N=[10,99,30]，L=[10,20,30,40,50]、m=4：不得混成[10,99,30,40,50]；神经前缀不同，丢Lookup尾。
N=[10,20,30]，L=[11]、m=8：可选lookup-only[11]，但不能自动接[20,30]。这时逻辑K1/V2，首版物理W4并mask其余2列；不是调用不存在的W2图。
候选来自历史不代表它正确；所有位置都经完整Target验证，无条件直接发布禁止。

## 确定链与Target sampling

上述C14是首版保守fusion策略，不是“异头保留旧神经tail必然采样有偏”的数学断言。任意确定性合法链都能按delta-q进入现有sampling接受器，前提是Target按最终mixed chain每个实际prefix计算p并使用正确processor/count overlay。不能把旧神经prefix的Target概率或softmax当新q。proposal不得窥视本轮accept/correction RNG。若放宽C14，要单独证明性能、MTP/aux对齐和policy合同；当前保守截断可继续保留。共同资格见 [design/11](11-sampling-acceptance-and-proposal.md)，未资格sampling回原路径，greedy只描述proposal。
