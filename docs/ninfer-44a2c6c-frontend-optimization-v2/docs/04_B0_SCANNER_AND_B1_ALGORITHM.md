# 04 · 扫描器、trace 与局部边界算法

## 4.1 B0 索引构建

在Tokenizer构造完成`load_added_tokens`与`merge_added_tokens_decoder`、最终ID顺序确定后，构造`std::array<std::vector<std::size_t>,256>`。每个元素保存added_tokens_的index，依原顺序插入。不得保存AddedToken*到自身vector，否则默认copy后指向旧对象。桶构造只做一次，不在每个encode内排序；每请求没有可变字典。

拟新增内部逻辑，代码仅作实现合同，执行者仍须先写测试：

```cpp
for (std::size_t j = 0; j < added_tokens_.size(); ++j) {
    const auto& token = added_tokens_[j];
    // Constructor validation already rejects empty content.
    added_token_indices_[static_cast<unsigned char>(token.content.front())].push_back(j);
}
```

## 4.2 共享单一编码实现

保留现有`encode`签名，将其和新`encode_traced`委托给同一`encode_impl`。只有trace-enabled调用分配restart向量；count_tokens不需要trace。`TokenizerWork*`可为空，统计不得全局累计。

```cpp
std::size_t match_pos = std::string_view::npos;
const AddedToken* match = nullptr;
for (std::size_t i = pos; i < text.size(); ++i) {
    if (work) ++work->scan_positions;
    for (std::size_t index : added_token_indices_[
             static_cast<unsigned char>(text[i])]) {
        const auto& token = added_tokens_[index];
        if (work) ++work->candidate_checks;
        if (token.content.size() <= text.size() - i &&
            text.compare(i, token.content.size(), token.content) == 0) {
            match_pos = i; match = &token; break;
        }
    }
    if (match) break;
}
```

找到match后，原样编码`[pos,match_pos)`普通段，push ID，pos跳末尾。没找到就原样编码`[pos,end)`并结束。trace在完成push后记录`{pos,ids.size()}`，不记录普通EOF。空输入的trace仍含初始`{0,0}`。

`scan_positions`是实际外层检查位置数量，不是DRAM字节；`candidate_checks`是完整候选比较尝试次数。旧find的`find_span_estimate`只在离线legacy基准作逻辑搜索跨度估计，不能与硬件访存读数混为一谈。

## 4.3 B1 数据流

1. `encode_traced(rendered.text)`生成T和单调restart表。
2. 按旧函数顺序访问三个optional与hints。
3. 先校验b<=B。
4. 以`upper_bound`找到最后`restart.byte_end<=b`；初始0永远可用。
5. 对唯一b，编码L=`encode(R.substr(r,b-r))`；不要拷贝T[:t_r]。
6. checked-add得到p；比较L与T中对应区间，缓存原始事实。
7. 为本次name/allow_full执行旧校验与错误包装，转换uint32。
8. 保持hint输出顺序、kind与重复，独立校验单调性。

局部encode调用也使用B0。benchmark中的B1-only应是测试/构建对照路径，不要求产品在运行时切换回旧scanner。

## 4.4 局部事实表示

```cpp
struct LocalPrefixFacts {
    bool independently_tokenizable = false;
    std::size_t token_count = 0;
    bool matches_main_prefix = false;
};
```

`std::unordered_map<size_t,LocalPrefixFacts>`仅当前encode_rendered_chat存活。局部编码异常在计算facts时记录不可独立编码；校验时按调用name抛旧logic_error，不能保存第一次name的异常对象。byte越界不进入memo。主E失败不创建可发布EncodedChat。

如果项目约束不允许吞catch后缓存失败，可以只缓存成功facts；失败每次立即抛并结束当前调用，仍然正确。关键是不能借memo改变先后错误。

## 4.5 Trace 的预算与防御

restart数≤主编码选中的added数量+1，约O(A)。不要每token记录完整UTF8字节，不要每边界复制主vector；对UTF8大文件仍用string_view切片。二分检索可应对boundary乱序；禁止为了线性扫描对hints排序，原有乱序必须照常报错。

size_t相加前检查溢出。uint32逻辑难以通过真实分配数十亿token测试，可把纯校验helper抽出，以可控逻辑长度测试检查顺序；仍对真实完整向量做其它差分。不得通过删除溢出检查让单元测试变简单。

## 4.6 统计与产品接口

生产新增统计只含计数与耗时，不含R/T/工具内容。新增prepare_detail子对象保持schema20旧字段定义；若现有消费者禁止新增字段，则显式升级schema并同步reader，不可静默改变版本语义。详细字段在[06](06_OBSERVABILITY_SCHEMA.md)。

## 4.7 不实现的捷径

不使用`longest match`、正则替代现有分段、手动拼接旧响应token、固定K overlap、字节/字符近似、从GPUappend状态提前判定、不分added优先级的通用trie、对各边界只算token长度不验证T前缀。评审B0原型中的长度简化不能进入产品。
