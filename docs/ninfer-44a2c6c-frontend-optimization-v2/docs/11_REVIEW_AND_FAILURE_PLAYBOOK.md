# 11 · 审查重点与失败排查

## 11.1 审查者应当拒绝的实现

| 迹象 | 为什么是阻断项 | 修复方向 |
|---|---|---|
|桶内按长度排序/最长匹配|破坏同位最小ID|保留ID顺序，真冲突词表差分|
|桶保存AddedToken*，未禁止copy|copy后指向源对象，可能悬垂|保存index，验证copy/move/destruction|
|每边界拼T[:t_r]新vector|保留O(B×Q)复制，只是换了热点|只比较局部片段、计算逻辑长度|
|边界只比较token长度|同长度不同ID也可能误接受|完整比较局部tokens与T对应段|
|memo缓存带name的最终error|同offset不同boundary语义错|缓存原始facts，逐调用判定|
|缺uint32或先做uint32检查|改变旧错误优先级|恢复原检查顺序并加逻辑长度test|
|为了性能排序hint、合并kind、删重复|改变checkpoint输出|memo与输出列表分离|
|把所有flags设false|special原值可能true|只拒绝原本不支持的4flag|
|把parsefalse也分割added|旧普通BPE语义改变|parsefalse原路径单独回归|
|从新master复制frontend接口|基线不一致，隐式引入行为变化|回44a2c6c真实类型|
|private测试调用新selector作reference|两边一起错|独立编译旧实现|
|拿review B0测量支路直接上线|该支路不保留全边界校验|B0只改scanner，processor原样|

## 11.2 观察到差分失败时

先冻结case、资源hash、seed、编译器和双方输出；停止后续性能试验。分清first failure出在raw encoding、boundary事实还是prepared metadata。用最小化删除内容但保留原始非法bytes与边界映射；不能通过“UTF8修复”使输入合法后称bug消失。

- raw token不一致：先检查字典加载顺序、真正冲突token、parse_added、普通段划分、cast unsigned char。
- 主token一致但boundary不一致：检查r是否来自实际完成added；局部slice是不是rawbytes；allow_full/name/0offset；NFC跨ordinary段；overflow顺序。
- boundary一致但hint错：检查输出是否被去重/排序、previous逻辑是否只在成功后更新。
- prepared不一致：检查diagnostics被误纳入identity或新field改变序列化；检查vision展开和offset映射。
- 并发偶发：查Tokenizer共享mutable状态、static scratch、复用trace容器、pointer bucket copy。

## 11.3 性能门不满足时

先验证candidate真实链接新代码、构建是Release且资源/fixture一致。查看main_encode_calls、scan_positions、localbytes。B0仍有重复find则先修结构；主scan线性但localbytes巨大可能是输入无安全分隔，确认是否被误标生产代表。主/局部都正常再profile普通BPE、分配/CPU干扰；不先加跨请求缓存掩盖。

B0+B1提高230倍的CPU原型数字不是产品验收目标本身。满足精确语义和匹配CPU绝对门比复制某个倍数重要。真实pureBPE吞吐按语料变化，要报告p90和负载。

## 11.4 HTTP慢但CPU快

逐请求对齐prepare_detail与clientTTFT；先排role-only流量/隐藏reasoning导致firstdelta差异。检查queue/restore/full_reset、进程冷启动、CPU数据转换、GPUfirsttoken。若cache失效看input/resource相等与其它客户端干扰；不能把allstop_token解释成任务成功。

## 11.5 审查报告必须回答

B0最左/ID语义依据是什么？B1分解在UTF8和partialaddedcut下为何成立？旧oracle是否真的独立且保留异常？真实artifact资源是否是生产版本？新增数据是否超原生窗口？短路径、count、vision、copy/move是否覆盖？生产是否只运行一种编码路径？full_reset与tokenizer收益是否分开？每个G状态是否有原始证据而非只贴汇总？

缺一项时，review结论可为`REQUEST_CHANGES`或`BLOCKED_EVIDENCE`，不要为了交付进度把缺证据写成低风险。
