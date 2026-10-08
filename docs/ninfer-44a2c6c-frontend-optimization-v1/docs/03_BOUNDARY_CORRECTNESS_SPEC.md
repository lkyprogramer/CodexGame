# 03｜单请求编码与边界正确性规范

## 3.1 基线oracle的精确定义

记`E(s)`为本提交原始Tokenizer::encode，包含原始added-token识别、NFC、Qwen预切分与BPE。完整输入为原始UTF-8字节串R，旧处理器先求T=E(R)。对边界b，求P=E(R[0:b])；只有P非空、长度不超过T且P等于T的前缀，才是合法边界；allow_full=false时还要求|P|<|T|。

`stable_prefix_byte_offset`允许full；`turn_rewrite_byte_offset`不允许；`user_turn_byte_offset>0`才验证且不允许full；每个`checkpoint_hint`允许full，hint映射后的token边界必须非递减。原来的optional缺失、重复hint及kind不得改变。[S01/S08]

prefix编码失败由旧实现包装为对应name的logic_error；越界、空prefix、nonexact、uint32溢出保留原语义。候选路径不能把无效边界变成“无hint继续执行”。

## 3.2 新trace需要记录什么

每次原始编码扫描added tokens时，记录：

```cpp
// Proposed internal types, not present at the pinned commit.
enum class LexSpanKind : std::uint8_t { Ordinary, AddedToken };
struct LexSpan {
    std::size_t byte_begin;
    std::size_t byte_end;
    std::size_t token_begin;
    std::size_t token_end;
    LexSpanKind kind;
    int added_token_id; // -1 for Ordinary
};
struct RestartPoint {
    std::size_t byte_offset;
    std::size_t token_offset;
};
struct EncodeTrace {
    std::vector<int> token_ids;
    std::vector<LexSpan> spans;
    std::vector<RestartPoint> restarts;
};
```

offset始终是**原始bytes**，不是Unicode字符数，也不是NFC后的字节数。trace必须覆盖完整输入消费顺序，token区间连续且合法。重启点只记录0与**原扫描器实际消耗完added token后的cursor**；普通文本EOF不是通用重启点。

第一次实现不要重写BPE，不改变added-token选择。沿旧encode控制流记录trace即可。新增trace和work计数不进入输出模型token。

## 3.3 单个边界的局部精确验证

选择当前完整编码trace中，位于b之前/处且不会跨越b的最后一个已完成added-token重启点r。0是兜底。已知完整T中`[0:t_r]`对应已完成的词法前缀。

求局部`L=E(R[r:b])`，然后用以下规则得到原oracle同等结果：

```text
candidate_prefix_length = t_r + length(L)
check T[t_r : candidate_prefix_length] equals L
apply old nonempty/full/uint32 rules to candidate_prefix_length
```

因为r是当前输入中已完成added token后的scanner cursor，NFC和ordinary BPE不会跨过这个已存在的分隔；截短到b也不能创造更早、原来不存在的完整added-token匹配。因此`E(R[:b]) = T[:t_r] || E(R[r:b])`。这是本提交所支持的added-token flags全false条件下的局部分解，不是普通BPE可任意拼接的断言。

b位于一个added token内部时：r必须在该token开始以前，不能使用该token结束后的cursor；局部E会按旧规则把截断残片当普通文本或更短added token处理，再与完整T比较。b位于UTF-8码点内部时局部E应复现原prefix错误，包装规则不变。

b恰好在实际added-token开始/结束处，通常可以直接由trace得到token数；但必须保留old nonempty/full检查。最简单且正确的首版允许这些边界也走零/短局部E，之后再消除无必要调用。

## 3.4 为什么能改善碎片化会话

本提交Rolling hint经常位于`<|im_start|>assistant\n`之后。r可在`<|im_start|>`之后，因此局部验证常只编码`assistant\n`，不再编码前面的20万token。

新编码输入字节工作为`B + sum(b_i-r_i)`，重复b只计算一次。**不承诺任意输入的严格O(B+H)**：无added-token或一个巨大ordinary片段内有很多边界时，局部prefix仍可能较长。该情况保留正确性、记录slow fallback，作为后续专门优化，不删除边界或偷偷修改切点。

## 3.5 假设边界与跨请求边界不同

当前输入的合法prefix边界只回答“E(R[:b])是不是当前T前缀”。跨请求缓存还需要证明新输入R'不会改变b以前tokenization。03不能单独充当04的证明。

尤其不要仅凭token end、newline、UTF-8对齐、相同token数量或字符串hash相同就复用。NFC组合字符、Qwen正则类预切分、跨界added token都要覆盖。

## 3.6 同一offset去重，业务语义不去重

内部可将查询按byte_offset去重为map；其输出是独立prefix token长度或原编码错误。之后按原调用顺序应用不同name/allow_full规则，重建三个optional字段与所有hint。不得排序输出hint，不得消去同边界不同kind，不得先扫描所有非法offset而改变“第一个错误”位置。

缓存边界结果也必须绑定当前R和资源；不能只缓存`b -> token_count`跨输入使用。

## 3.7 独立oracle与最小反例

baseline独立进程/二进制从44a2c6c编译，使用相同六份frontend资源。candidate的legacy模式用于上线回退，但不单独承担独立证明，避免两个实现共享错误。

必须至少覆盖：

- NFC：`e`+U+0301、Hangul Jamo、组合符跨切点；全串有效但前缀UTF-8截断。
- BPE：构造`a,b -> ab`的合并，b落在a之后；当前prefix nonexact仍应拒绝。
- added：同位置`ab`/`abc`配置小ID优先，与最长匹配产生不同结果。
- partial added：旧串以`<|im_sta`结束，新串补齐；不得复用旧EOF。
- 重复hint：相同offset重复不同kind，输出保留全部。
- allow_full：同一b==R.size，stable合法/turn不合法分别处理。
- no media：两种受支持模板、preserve_thinking true/false、连续tool消息分组、最后assistant opener。
- media fallback：原processor行为及预算/错误不回归。

## 3.8 性能正确性联合门

不能以去掉边界验证获得性能通过。必须同时报告：主扫描输入bytes、局部prefix输入bytes、prefix query数/unique数、BPE片段输入bytes、旧方案理论请求bytes、实际encode调用次数与相同PreparedPrompt验证。

单请求成功应表现为：主历史BPE不再为每个hint重复；新增局部prefix工作随边界附近片段增长，而不是随每个hint之前完整历史增长。
