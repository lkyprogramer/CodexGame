# 03 · B0/B1 精确语义与正确性论证

## 3.1 术语

R是原始渲染UTF-8字节串，E是固定资源与EncodeOptions下的旧编码函数，T=E(R)。b是当前请求的字节切点。r是本次主编码真实选中的一个added token的结束字节（或0），t_r是此时已输出的token数。r不是任意token边界、普通段EOF、字符串中未经选择的标记结尾。

所有比较在原字节/原token域；不把“Unicode字符数”“标准化后字节数”“模型生成token”混用。B1本期只处理同一个R的前缀，无需跨请求LCP或M−1guard。

## 3.2 B0 选择等价

在旧游标pos，定义候选集合：

`C = {(s,id) | s>=pos 且某added token的完整content从R[s]开始匹配}`。

旧算法对每个token找最小s，再选择最小s；同s只保留ID遍历中第一项，故取C的字典序最小元素。新算法从pos开始逐字节递增s，对该首字节桶内按ID升序检查完整content，首个匹配正是同一元素。随后普通段、输出ID和游标推进与旧算法一致。对迭代归纳，所有选中序列相同；普通片段送给同一NFC/BPE，故最终T相同。

证明前提：字典构造验证与ID排序不变，空content仍拒绝，所有比较均完整匹配而非prefix-of-input试探；`parse_added_tokens=false`保持旧直接普通编码；不新增word/strip/normalized flags语义。special标记不是禁止位，保留原行为。

**真实示例修正：** `<tts_text_bos>`不是`<tts_text_bos_single>`的字面前缀，前者的`>`与后者的`_`不同。两者用于真实token回归，但不能证明冲突优先级。使用真实冲突的合成字典如ID1=`ab`、ID2=`abc`，以及反转ID两组；从`abc`起点分别应先选择不同token。

## 3.3 B1 分解定理

取r<=b，且r是T扫描中已选added token结束点。R[:b]中所有完整匹配都存在于R；R扫描在到达r前选择的每个匹配，其结束<=r<=b，仍存在于R[:b]。候选变少而旧最小元素仍在，故到r为止的选择相同，普通片段也相同。added token分割后的普通片段各自做NFC/BPE，因此：

`E(R[:b]) = T[:t_r] || E(R[r:b])`。

将局部L=E(R[r:b])与`T[t_r:t_r+|L|]`比较，及p=t_r+|L|，即可重现旧prefix合法性判断。r=0始终成立，是没有安全点时的正确性回退。切点处于added token内部时必须回退到前一个已完成added结束点；不能复用跨过b的token。

## 3.4 校验顺序是合同的一部分

必须完整保留：主E(R)成功后才遍历边界；byte越界在局部编码之前报错；局部编码std::exception包装成当前name的logic_error；非空/full/长度/精确比较在uint32判断之前；hint顺序检查在该hint独立合法后执行。

两个边界含相同offset不表示相同校验，例如stable允许full，turn不允许。memo只复用原始事实，不复用最终判定。可将全长prefix编码减少为零局部字节，但不能跳过不允许full检查。

错误精确消息见[01 §1.4](01_PINNED_SOURCE_AUDIT.md)。对非法UTF-8/NFC边界，局部编码必须与独立旧prefix得到同一可观察错误；不得把异常统一改成`invalid boundary`。内存耗尽不纳入通常输入差分定理的成功分配假设，但仍必须传播失败，不返回部分PreparedPrompt。

## 3.5 输出比较合同

至少比较：主token_ids；stable/turn/user三个optional的“缺失/值”；checkpoint_hints的数量、每个kind、顺序、重复和boundary；PreparedPrompt token_types、3轴positions、rope_delta、identity、starts_in_reasoning；count_tokens结果；错误阶段、动态异常类型、完整what字符串。

仅比较主tokens不够。只看模型答案或tool_call解析成功也不够。编译/执行新产品函数的输出，必须和独立旧产品实现的输出比较，而不是只比较两份复刻原型。

## 3.6 复杂度界与不能承诺的内容

B0对每次调用扫描s单调向前；扫描位置不超过输入字节数，候选比较至多B×最大首字节桶大小，比较单token长度至多M。固定词表下相对于B为线性，但不能对任意巨大词表宣称与V/M无关。

B1成本为一次主E(R)，加唯一offset集合U上的`Σ E(R[r(b):b])`，以及查找trace与合同判定。典型工具opener附近局部只有十几bytes，这是实测形态不是普遍定理。无added分隔的大段普通文本可令r=0，多个boundary仍重编码很长部分；保持正确，不通过删boundary伪装“主编码1次”之外没有任何重复工作。

## 3.7 并发/生命周期证明义务

Tokenizer只读字典和索引桶；copy/move后索引仍指向当前对象自己的added_tokens_。trace/memo/stats单调用持有，不能写到共享Frontend::Impl。并发相同或不同输入必须输出独立一致；测试析构源Tokenizer后的copy对象，防止指针桶悬垂。

## 3.8 验证不是全输入穷尽

≤256bytes的选定有限样本全部cut +20,000随机变换，只证明这些输入经过差分；B0/B1通用性靠上述合同、源码审查与数学分解共同支持。不要把“全部byte cuts”扩写成“全部256字节字符串”。
