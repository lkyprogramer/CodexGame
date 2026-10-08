# 01 · 固定源码审计与语义入口

## 1.1 真实调用链

`GenerationService::prepare()` 把请求转换为 PromptInput，再调用 Engine frontend prepare，生成 PreparedPrompt 后 submit。旧版本 JSONL 的 prepare 截止点在 submit 前；本地 schema20 overlay 据评审移动到 submit 后并增加明细。因此比较19/20时必须统一计时定义，不能直接作阶段相减。

前端关键链路：

```text
Frontend::prepare
    ├─ text: render → encode_rendered_chat → positions/identity
    └─ media: render/expand → encode_rendered_chat → positions/identity
Frontend::count_tokens → render → Tokenizer::encode
Frontend::prepare_tokens → 输入 token IDs，不经过文本编码
```

`append_frontier` 由后续 Engine 对完整 PreparedPrompt 与已有状态比较产生。B0/B1 不依赖该字段，输入冷/热均执行同一个纯函数优化。

## 1.2 源码对象与路径

| 对象 | 固定路径/入口 | 修改意图 |
|---|---|---|
| S01 | `src/targets/qwen3_8/impl/frontend/processor.cpp::encode_rendered_chat` |B1替代重复前缀编码，旧错误合同不动 |
| S02/S05 | `.../frontend/tokenizer.h/.cpp::Tokenizer::encode` |B0搜索、共享encode_impl与可选trace |
| S06 | `.../frontend/chat_template.cpp::last_real_user_query/render` |只读；测量真实H，不改模板 |
| S07 | `.../frontend/frontend.cpp` |连通text/count/prepare_tokens，透传计数 |
| S08/S09 | `src/targets/qwen3_8/export/ninfer/targets/qwen3_8/{prepared_prompt,frontend}.h` |现有类型，观测字段按真实overlay最小扩展 |
| S10/S11 | `tests/CMakeLists.txt`、`tests/targets/qwen3_8/test_frontend.cpp` |复用原测试结构，增加独立oracle/精确差分 |
| S12/S13 | 根及target CMake |遵守现有C++20/CUDA构建，不引入新前端框架 |
| S14/S15 | `AGENTS.md`、`.../frontend/resources.cpp` |治理与六资源绑定，不重写制品 |

完整 blob 身份由 [source-lock.json](../source-lock.json) 给出。v1 的7处可疑行范围已经移除；未独立逐行确认的条目用symbol与完整blob定位。执行者运行 `tools/check_source_pin.py` 对本地历史对象核验，不能仅验证当前工作树文件名。

## 1.3 B0 当前语义

旧扫描器逐 token 遍历已按ID排序的 `added_tokens_`，为每个 token找最早起点；只在`found < match_pos`时替换。并列起点保留较早ID。普通分段调用原`append_bpe_ids`，推入added ID后游标跳到匹配末端。

配置拒绝空content与`single_word/lstrip/rstrip/normalized=true`。**special可为true**，其编码识别和decode跳过语义不能丢失。`parse_added_tokens=false`直接把全文作为普通文本送入原BPE，不扫描任何added token。

## 1.4 B1 当前错误合同

主编码先执行，失败就直接抛出。之后依次处理stable、turn、正值user offset，再处理hints；无排序修复或去重输出。

| 条件 | 原异常 | 原消息 |
|---|---|---|
| b大于渲染长度 |logic_error|`{name} byte offset exceeds rendered chat`|
|独立prefix编码抛std::exception|logic_error|`{name} cannot be tokenized independently`|
|prefix为空/禁止full却全长/长于T/不等于T前缀|logic_error|`{name} is not an exact token prefix`|
|通过上述检查后token数超uint32|overflow_error|`{name} token boundary exceeds uint32`|
|hint token frontier小于前一个|logic_error|`semantic checkpoint boundaries are not ordered`|

name分别`stable prefix`、`turn rewrite prefix`、`user turn prefix`、`semantic checkpoint prefix`。user offset=0不验证；stable/turn的0仍按旧逻辑验证并报错。allow_full对stable/hints为true，turn/user为false。

## 1.5 Hint 的条件性

`last_real_user_query` 从尾找role=user，跳过trim后整体被`<tool_response>`与`</tool_response>`包住的user文本。没有真实user则抛原错误。每条assistant是否追加StableTurn/Rolling取决于其索引是否在该user之后、是否已有completed tool history、是否已有stable turn。system可生成StablePrefix，generation opener可生成最后hint。

因此统计应采真实H、Q和每个b，而不从`message_count`反推出强规则。短期保持chat_template.cpp原样，避免把语义变更混入性能修复。
