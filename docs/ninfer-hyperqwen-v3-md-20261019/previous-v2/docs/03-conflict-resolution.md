> V3 继承资料：P0—P6 的任务目标和上游合入顺序继续有效。命令依赖须先按根目录 `support/REHYDRATE.md` 恢复。

# 03｜逐文件冲突处理与隐藏依赖

## 1. 证据口径

下表覆盖 16 个双方都修改过的路径。这是 merge-base 两侧路径集合的交集，不是已实测的整仓冲突文件列表。对 `tokenizer.h`，已恢复 B/O/U 三个完整文件并验证 Git blob SHA，运行 `git merge-file --diff3 -p`，返回 2，得到 2 个冲突区块，原始输出在 `evidence/header-merge/`。其他路径为源码/补丁语义分析；P0 会补齐精确的整仓 index stages。

**只删除冲突标记不是完成条件。** 每一项必须同时满足接口完整、定制保留、上游新语义和独立测试四个条件。

## 2. 16 个文件的处理决定

### C01｜`include/ninfer/types.h`

你的改动是 `FrontendPrepareTiming` 和 `PromptSummary.frontend`；上游同时扩展 PromptProgress、生成停止/错误契约、缓存边界和决策类型。

采用上游完整公共类型定义，增量恢复 timing struct 和 summary 字段。该数据只用于观测，不得参与 identity/hash，不得把其布局当作持久化 ABI。决策 summary 与 Chat prompt summary 分开，不强行向决策填充虚假的 render/tokenize 时间。检查 aggregate initializer、enum switch 的穷尽性以及错误类型的映射。[S09]

验收：同一请求计时开启/关闭的 token、边界、identity 全部相同；所有生成 finish reason 正确映射；构建所有启用 package。

### C02｜`src/targets/qwen3_8/impl/frontend/tokenizer.h`【已实测文本冲突】

保留你的 `TokenizerWork`、`EncodingRestart`、`TracedEncoding`、首字节索引；保留上游 `SegmentedEncoding`、`PrefixRelation`、`encode_segmented` 及最终新增的 `token_id`。实测两个冲突分别集中在公共 encode 接口和私有扫描入口附近。

不要留下 `encode_impl` 与 `encode_added_token_segments` 两套独立生产实现。用一个私有扫描器，可选输出 trace 和 segment 元数据。`Tokenizer::token_id` 是 decision template 的依赖，即便 Chat 测试通过也不能删掉。

借用生命周期必须明确：SegmentedEncoding 借用 tokenizer 和 rendered text，仅在一次 prepare 内使用；`release_ids()` 之后不再调用 prefix。[S03、S04、S06]

### C03｜`src/targets/qwen3_8/impl/frontend/tokenizer.cpp`

实现 B0 的单调扫描，同时在 ordinary/added-token 发出位置记录段区间。added-token 同位置匹配仍按既有 `added_tokens_` 顺序决定；不要改成最长串优先，也不要顺手实现此前未实现的 strip/normalize flag 语义。

trace 只记初始 `(0,0)` 和真正选中 added token 的结束；ordinary EOF 只属于 segment 覆盖范围，不是 restart。无 added-token 解析模式继续走原 BPE；`TokenizerWork* == nullptr` 不引入全局原子统计。保留上游新增 token_id 查询与后续输出相关功能。

PrefixRelation 用同一 tokenizer 对切点所在局部片段重编码，以 token LCP 判断 common_tokens；`exact` 不能简单等于“切点位于 segment 末端之外”。UTF-8 中间切点、added token 中间切点、NFC 组合字符都必须过独立完整前缀 oracle。[S04—S06]

### C04｜`src/targets/qwen3_8/impl/frontend/processor.h`

以新 `ProcessedInput` / `EncodedChat` 为主，保留 `turn_rewrite_boundary`、`user_turn_boundary` 和 `std::vector<PromptBoundary> boundaries`；增量加入 `BoundaryEncodingWork`。保留最终 `VisionItem.preprocessing_digest`、`ProcessedDecisionState` 和 `process_decision_state`。

生产 DTO 不继续暴露旧 stable_prefix/checkpoint_hints 作为第二份权威数据。否则不同调用方会选择不同边界，缓存无法定义单一真相。旧字段只存在于 test-only Legacy DTO。[S07]

### C05｜`src/targets/qwen3_8/impl/frontend/processor.cpp`

替换点为 `encode_rendered_chat` 的主流程和 `Processor::process` 的结果搬移。采用新边界循环；同一次完整编码服务所有查询。按 byte_offset 进行请求本地 memo，但 memo 要区分“不可编码”“exact=false”“exact=true”结果，而不是把异常等同于普通 miss。

隐式边界要求 exact 且满足空/全量边界规则；显式边界使用 common_tokens，随后按上游规则去零、去重、过滤，保证严格递增和不越过 rewrite frontier。模板边界的 exact 检查先于 uint32 溢出检查；内部逻辑错误不应被宽泛 catch 掩盖成无效客户端切点。

图像占位符展开会移动 byte boundaries，必须保留 `adjust_rendered_boundaries_for_replacement` 与 profile/budget 新路径。计数里的旧字段 `checkpoint_hints` 可以保留为历史名称，但其新含义必须文档化为本次候选边界数，扩展版本须区分旧统计。[S05—S08]

### C06｜`src/targets/qwen3_8/export/ninfer/targets/qwen3_8/prepared_prompt.h`

在上游新的 prompt identity/boundary 结构上保留 PrepareStats 的 convert/render/tokenize/positions 和 rendered size。不能把被上游删除的 StablePrefix 单字段重新放回 identity，替代新 boundaries。

prepared prompt 的 observer 计数是请求本地 transient 数据；快照/continuation 的格式不因计时字段不同而发生缓存 miss。MRoPE / preprocessing identity 属于语义身份，必须保留，不与 timing 混淆。

### C07｜`src/targets/qwen3_8/impl/frontend/frontend.cpp`

保留上游从 EncodedChat.boundaries 到 PreparedPrompt 的完整映射、决策准备、媒体状态和 UTF-8 输出修复；在实际新的函数边界内恢复自定义计时。不要按旧行号机械套补丁。

Text 的转换/渲染/tokenize/position 计时应嵌套于一次 prepare；Vision 原实现把 processor 合并计入 render，并以 tokenize=-1 标记不可拆分，不得改成 0 冒充零成本。决策准备单独命名，缺失的 Chat 指标不得复制成“已测值”。生成输出允许 U+FFFD 修复不意味着输入 tokenizer 可以宽松接受非法 UTF-8。[S09、U27]

### C08｜`src/serve/generation_service.h`

把你的 PrepareRequest / GenerationMetrics 计时字段增量加入上游新头文件；保留新增 `ToolParameterKinds`、tool begin/arguments/end、prompt progress callbacks、决策接口与一次性消费的 handle/lifetime。

不能用旧头文件覆盖，因为代码可能还编译到局部目标，但新的流式 endpoint 和决策服务会缺回调、丢参数或破坏 shared ingress。所有回调必须在既有 consumer 生命周期内执行，不能为计时额外持有裸 request 指针。[S10]

### C09｜`src/serve/generation_service.cpp`

保留新 `prepare/run/prepare_decision/decide` 流程，只移植计时取样点和数据搬移。prepare 的结束点包含同步 submit；异步 GPU 工作可能与 host 返回重叠，必须用实际时间起点解释指标，不盲目把各字段相加当作互斥耗时。

不恢复已经删除的旧终态 parser，也不以旧 streamed_content_bytes 逻辑覆盖新的 discarded-bytes / incomplete-call 契约。请求取消与媒体 lease、generation handle 的 release 顺序保持上游。

### C10｜`src/serve/request.h`

保留新请求类型、缓存选项与工具结构，仅恢复 `body_bytes`。它来自 HTTP raw body 的字节数；没有 HTTP 输入的测试和 count helpers 保持 0。不得把客户端 JSON 自带的 body_bytes 字段当成权威输入，也不得将其写入 prompt identity。

### C11｜`src/serve/http_server.cpp`

在新的 Chat Completions 和 Anthropic handlers 中，解析成功后、prepare 之前设置 `request.body_bytes = req.body.size()`。沿用上游 model/adapter 分类：决策 adapter 不能通过 Anthropic 任意 model fallback 混进生成路径。

保留流式工具回调、错误事件、连接取消、路由新增和容量控制。不要用整段旧 handler 换回 `body_bytes` 那一行。

### C12｜`src/serve/responses_http.cpp`

设置 `request.generation.body_bytes`，计量的是本次原始 HTTP 请求，不能因为 previous_response_id 展开后更长而声称 HTTP body 也变长。前缀内容大小与最终 rendered size 单独记录。

保留 prompt progress SSE、增量 tool arguments 和仅保存完整工具对象的历史规则。断流/length 截断不应把半个 JSON 参数保存成可再次执行的工具历史。

### C13｜`src/serve/request_log.h`

保留最终 `kRequestLogSchemaVersion = 24`，恢复 RequestLogContext 中的四个 size 字段。跨阶段按各阶段上游 schema 生成；最终不回退为 20。定义独立 extension version，不挤占未来上游全局 schema 号。

旧 schema20 判读需要 producer/字段存在性，不能只看数字。读取端允许没有 prepare_detail；媒体 tokenize=-1 表示未拆分，不得纳入速率分母。[S09、S14、S16]

### C14｜`src/serve/request_log.cpp`

在最新 request/start/done/server-start formatter 上保留 custom request size、prepare_detail 和 prepare_tokens_per_s。现有 `_chars` 实际来自 `std::string::size()`，是 UTF-8 字节；保留键名以便历史工具读取，明确单位，dashboard 标签不再写“字符数”。

保持新增 decision/adapter/energy/export/tool-discard 记录。计时扩展不调用 execution mutex 的同步设备快照，避免恢复上游已经修复的遥测饥饿。

### C15｜`tests/CMakeLists.txt`

合并两边测试目标集合，并修复每个目标的 source/include/link 定义。必须同时存在自定义 tokenizer_work/equivalence/restart/boundary/legacy 测试与上游 tokenizer_real、guard、row_commit、决策、图像相关测试。

`ninfer_qwen3_8_g1_diff` 和 `ninfer_qwen3_8_legacy_frontend_oracle` 是明确的 standalone executables，不能因 `ctest` 全绿就跳过。`bench_boundary_lanes.cpp` 的最终注册方式在 P0 全仓确认；不存在目标时在 P1 新建并注明，不假设它已经可执行。

单个 CMakeLists 由集成者串行修改；并行任务提交注册片段，不同时抢同一文件。NVFP4 在 sm89 的不可执行路径可按明确理由 skip；真实 27B / q4 / q5 / w8 验收不能 skip。[S11]

### C16｜`tests/test_request_log.cpp`

保留上游完整记录测试，并增加 custom extension、Text 分项、Vision sentinel、三个生成协议的 raw body size、缺字段旧日志等用例。至少有：base19、fork20、upstream20、21/22/23/24 的 fixture 或明确 normalization case。

不要把所有 expected schema 改成 24 就结束；那样无法防止旧 schema20 两种含义的歧义。计时测试不要求 wall-clock 精确数值，应检查非负/未知标记、单位、字段来源和时间包含关系。

## 3. 额外隐藏冲突：新增文件也可能坏

### Legacy oracle 的生产类型依赖

`reference/legacy_encode_rendered_chat.h` 直接 include 生产 processor.h，cpp 使用生产 `RenderedChat` / `EncodedChat` 和 `SemanticCheckpointByteHint`。上游删除这些旧字段后，虽然这些新增文件本身不会出现 Git 冲突，编译仍会坏。

处理顺序：P0 从 O 编译、保存独立 oracle 可执行物及 SHA；P1 引入 test-only `legacy_boundary_contract.h`，冻结旧 DTO。原 oracle 的完整前缀算法、异常优先级、tokenizer 算法不改；只允许 include/type alias/signature 的隔离改动，并做函数体/旧基线输出核对。新 Explicit contract 用“冻结 tokenizer + 完整前缀 encode + 独立 LCP”建立新 oracle，不调用生产 segmented prefix。

### G1 套件不等于所有素材已存在

驱动要求 cases JSONL、资源目录和 real-profile toggle template；旧驱动路由固定为 real53 / synthetic74。P0 必须实查素材。找不到时不得用空文件、降低计数或让 skip 冒充成功；可建立新版本套件，但须保留“原 G1 未复跑”的状态与缺失原因。

### Docker / AGENTS / state ABI

无权重 Dockerfile 与上游默认 Dockerfile 并存，不代表启动脚本会选对。上游 AGENTS 的架构原则应继承，但本次任务的生产保留约束必须显式加入。旧快照/continuation 的拒绝、命名空间隔离和回滚路径虽然不产生文字冲突，仍是阻断级验收项。

## 4. 禁止的解决手法

禁止 `git merge -s ours` 伪造包含性；禁止对整仓 `checkout --ours .` 或 `--theirs .`；禁止删除失败测试以通过构建；禁止改变 frozen oracle 的算法去匹配 candidate；禁止将旧 codec 名悄悄映射到新实现；禁止依赖 schema20 数字猜测生产者；禁止用无 GPU 的 skip77 宣称 GPU 验收；禁止通过缩短上下文或关闭 thinking 掩盖性能回退。
