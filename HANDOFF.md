# HANDOFF

## 当前任务

生产机 `192.168.10.29` 上，2026-09-30 02:31:53 -04:00 切到新 NInfer 镜像之后，Pi 连续使用时出现过 **`Response was truncated before completion.`**。用户确认旧镜像长期使用没有这句报错。这句报错已经对上两次真实请求：服务端把思考通道写满客户端的 `max_tokens=32768`，以 `finish_reason=length` 正常结束，没有工具调用。

用户已经明确拒绝上一轮提出的修复：思考单独封顶（4096 或 8192），预算用尽时强制提交 `</think>` 再继续采样。不要实现这个方案，不要把它写成已接受的结论，也不要为了它打新镜像或重启 `18343`。

下一会话要重新查原因，并给出用户能接受的修法。当前没有被证据钉死的机制是：为什么同一套权重、同一套采样、同一个 32768 预算，旧前端 1902 次可比请求都会自己停住，新前端在 2026-09-30 下午这个新会话里有两轮不停。

本文件写于调查结束时。主机状态以文中的观测时刻为准，接手后先按「给下一会话的第一步」复核，不要假设进程号和日志末尾没变。

## 已完成

只做了只读调查。没有改生产脚本，没有重启，没有回滚，没有打新镜像，没有改 Pi 配置，没有改 ninfer 源码。

### 用户看到的报错到底是什么

已观察：Pi 界面这句英文只在 `message.stopReason === "length"` 时绘制。

- 文件：`/Users/luo/.nvm/versions/node/v22.19.0/lib/node_modules/@earendil-works/pi-coding-agent/dist/modes/interactive/components/assistant-message.js` 约 132–141 行。注释写明 length stop 可以发生在工具调用完成之前。同一字符串也在 bundle chunk 里。
- Pi 的 OpenAI 流客户端 `dist/bundle/chunks/openai-completions-XW2Q5HVC.js` 里 `mapStopReason`：`finish_reason === "length"` 映射成 `stopReason: "length"`。`stop` / `end` 映射成 `stop`。`function_call` / `tool_calls` 映射成 `toolUse`。流在没有 `finish_reason` 时结束，走的是另一条错误（`Stream ended without finish_reason`，`stopReason` 为 `error`），不是这句文案。代理把连接关掉时，文案是连接类错误，也不是这句。
- 服务端 `src/serve/translate.cpp` 的 `finish_reason_wire`：`OutputLimit` 和 `ContextCapacity` 都变成线上的 `"length"`；`StopToken` / `StopString` / `None` / `Cancelled` 变成 `"stop"`。JSONL 里用内部名 `output_limit`、`context_capacity`，不会出现单词 `length`。
- `http_server.cpp` 约 1168、1242 行把这个 wire 值写进 chat completions。Pi 走的是 OpenAI chat 兼容层，不是 Anthropic messages。

因此这两次失败是服务端完整结束了 HTTP 响应，不是 SSE 中途被掐断。

### 两次失败的服务端记录

主机日志分析于主机本地时间 2026-09-30 22:32 左右跑完。切分点用的是切换时刻 `2026-09-30 02:31:53 -04:00`。下面两行是新镜像上、`requested_output_tokens >= 256` 且打满预算的全部真实请求。数字来自那次 JSONL 汇总，不是估算。

| 字段 | 2026-09-30 12:02:21 -04:00 | 2026-09-30 12:10:09 -04:00 |
|---|---|---|
| finish | `output_limit` | `output_limit` |
| prompt_tokens | 20597 | 22345 |
| completion_tokens | 32768 | 32768 |
| requested_output_tokens | 32768，来源 `client` | 32768，来源 `client` |
| prefix_cache_hit_tokens | 19606 | 20513 |
| prefix_reuse_path | `append_frontier` | `append_frontier` |
| message_count | 19 | 26 |
| tool_count（请求里） | 10 | 10 |
| tool_call_count（解析结果） | 0 | 0 |
| enable_thinking / preserve_thinking | true / true | true / true |
| tool_choice / temperature | auto / 1.0 | auto / 1.0 |
| decode / total / ttft / prefill 秒 | 330.034 / 330.797 / 0.446 / 0.346 | 308.933 / 309.970 / 0.748 / 0.640 |
| MTP accepted/drafted | 0.495，rounds 13188，fallback 1 | 0.555，rounds 12296，fallback 1 |
| continuation | source `l1`，restored 等于 hit，agree 为空，miss `none`，restore_fail `none`，rollback false | 同左，restored 20513 |

`agree` 为空的含义在 `request_log.cpp` 的 `continuation_json`：没有做更深候选的 preflight 时写 null，不是「在 token 0 处分歧」。上下文大约 2.1 万 / 262144，不是 `context_capacity`。MTP 用的是 `--lm-head-draft`，接受率大约 0.5 只能说明草稿头和主头还大致同向，不能证明 KV 正确。

JSONL 的 `request` 对象没有 prompt 正文，也没有 completion 正文。不要从日志里期望读出用户内容。

### 同一次 Pi 会话里，客户端实际收到了什么

失败会话文件（笔记本，UTC 时间戳）：

`/Users/luo/.pi/agent/sessions/--Users-luo-Documents-javatest-qwen3.8-27b-candidate-kit-v1.0.0--/2026-09-30T15-55-17-847Z_01a0f307-01d6-768d-92ec-f8512b8c047e.jsonl`

会话 id `01a0f307-01d6-768d-92ec-f8512b8c047e`。目录名对应工作区 `~/Documents/javatest/qwen3.8-27b-candidate-kit-v1.0.0`。31 行。模型 `openclaw/openclaw/Qwen3.8-27B-WORK`。`thinkingLevel` 是 `medium`。

时区：Pi 时间戳是 UTC。主机日志是 -04:00。`16:02:21Z` = `12:02:21-04:00`，`16:10:09Z` = `12:10:09-04:00`。调查时笔记本文件 mtime 显示成 2026-10-01 00:10，与主机 12:10 -04:00 对得上（笔记本当时按东八区显示）。

只统计了结构，没有把正文写进对话或本文件。两个 `stop=length` 的助手消息都只有一个 `thinking` block，没有 `text`，没有 `toolCall`，`errorMessage` 为空：

- 16:02:21Z：`usage.output=32768`，`cacheRead=19606`，`input=991`，thinking 115689 字符、15259 词。80 字符滑窗 1446 块全部唯一。几乎全是 ASCII。反引号代码块 115 处，花括号成对出现。结尾是字母数字，不是 `</think>`。块内 `<think>`、`</think>`、`<|`、`tool_call` 计数都是 0。
- 16:10:09Z：`usage.output=32768`，`cacheRead=20513`，`input=1832`，thinking 114560 字符、15419 词、2344 行。80 字符滑窗 1431 块全部唯一。代码块 181 处。同样没有闭合标记。

`usage.reasoning` 两次都是 0。这是代理在引擎没填 `completion_tokens_details.reasoning_tokens` 时用 `setdefault(..., 0)` 补出来的，不能当成「没有思考 token」。思考正文在 Pi 的 content block 里。

同一会话里其余助手回合都是 `stop=toolUse`，思考只有几十到几百字符，然后带工具调用。工具结果里没有 `<|im_start|>`、`<|im_end|>`、`<think>`、`</think>`、`<tool_call>` 这些字面控制标记。所以不是工具输出里夹了聊天特殊串、把模板切碎这么简单。

服务端同一时段的真实回合（`tool_count>=1` 且 `requested>=256`）紧挨着这两次：

- 11:56:35 `full_reset` prompt 8934，completion 181，工具调用 2。前一条真实请求在这之前约 461 分钟，是早上那轮的结尾。
- 11:56:39 `append_frontier` hit 9114，prompt 14965，completion 254，工具调用 3。
- 11:56:42 `append_frontier` hit 15218，prompt 16362，completion 308，工具调用 5。
- 11:56:48 `full_reset` prompt 14964，completion 99，工具调用 1。prompt 比上一轮小，消息数跳到 15。
- 11:56:50 `append_frontier` hit 15062，prompt 19533，completion 74，工具调用 1。下一轮 hit 19606，等于 19533+74-1，符合「生成的停止符不进下一次前缀」这种几何，不是凭空命中。
- 12:02:21 第一次 `output_limit`。这一轮从 11:56:50 之后开始，解码 330 秒。
- 12:04:55 `full_reset` prompt 16505，completion 295，工具调用 1。prompt 比失败轮小，消息数 20。Pi 在 16:04:47Z 插入了一条 2 字符的用户消息，然后模型又开始调用工具。失败轮的 3 万 token 思考没有原样留在下一轮的前缀里。
- 12:04:57 `append_frontier` hit 16799，prompt 18921，completion 94。
- 12:04:59 `append_frontier` hit 19014，prompt 20414，completion 100。
- 12:10:09 第二次 `output_limit`。解码 309 秒。

两次失败的前一轮都是短工具调用，而且用了同一条 L1 `append_frontier`。不能把原因写成「前缀缓存整段坏了，所以新镜像每一次续写都错」。

### 新镜像早上那轮并没有这个报错

同一分析里，新镜像 03:49:25 到 04:15:00 -04:00 的真实回合全部是 `stop_token`。开头 `full_reset`，prompt 208540、消息数 606、completion 235。随后大多 `append_frontier`，少数 `restore_turn_checkpoint`。prompt 最高到 245357（03:55:23，completion 107，当时 requested 已降到 12566）。03:58:31 又一次 `full_reset`，prompt 掉到 45953、消息数 82，之后长到 04:15:00 的 prompt 82890、completion 704。

这轮里打印出来的最大 completion 是 03:52:55 的 3031，finish 仍是 `stop_token`，工具调用 1。04:15:00 那条是 `stop_token`、completion 704、`tool_call_count=0`，时间线上被标了 `*`，但不是 `output_limit`，Pi 不会因此显示这句截断。值得下一会话单独看这条 Pi 消息，不要把它和两次 length 混成同一机制。

requested 随 prompt 变大而下降，观察值大致是 `prompt_tokens + requested_output_tokens ≈ 257921`（例如 225688+32233、245357+12566）。Pi 模型配置里的 `contextWindow` 是 262000，`maxTokens` 是 32768。下降从「再给 32768 就会顶破某个更小的上下文预算」开始。这是客户端行为。两次失败时 prompt 只有约 2 万，requested 仍是 32768，所以不是这条预算把它们截断的。

04:15 之后到 11:56 没有真实工具请求。当前 `ninfer-request.jsonl` 的 mtime 在调查时是 2026-09-30 12:20:11，最后一条 `request_done` 也在这个时刻。不要把「日志停了」写成「进程死了」。调查当时 GPU 上仍有 `ninfer-serve`，约 22588 MiB。进程号会变，接手时重查。

### 旧镜像为什么没有这句报错

已观察，不是推断。旧镜像定义为日志时间戳早于 2026-09-30 02:31:53 -04:00。统计口径：`request_done`，`tool_count>=1`，`requested_output_tokens>=256`。

- 这样的旧请求共 7578 条，`requested_output_tokens_source` 全部是 `client`。
- `requested` 的众数：2048 有 3660 条，32768 有 1902 条，8192 有 1814 条，4096 有 95 条。`enable_thinking` true 3918 条，false 3660 条。false 的 3660 与 requested 2048 对齐，是另一种客户端，不是这次 Pi。
- `requested>=32768` 的 1902 条：最大 completion 5721，打满预算 0 条，finish 为 `stop_token` 1901 条、`cancelled` 1 条。
- 全部 7578 条里 completion ≥ 8000 的是 0，≥ 4000 的是 8。p50 98，p90 473，p99 1802，最大 5721。
- 历史里 `requested>=256` 的真实 length/capacity 只有 6 条。其中 2 条就是上面的新镜像 32768。旧镜像 1 条是 2026-09-12 03:58:25 -04:00：prompt 18648，completion 1276，requested 1276，`output_limit`，thinking true，0 个工具调用，path `restore_turn_checkpoint`。另外 3 条是 2026-09-21 08:47–08:48，prompt 1473，completion 2047，requested 2048，`context_capacity`，thinking false。这 4 条都不是「Pi 在 26 万上下文上把 32768 写满」。

Pi 长会话（含 9 月 30 日早上在新镜像上的续写）：

`/Users/luo/.pi/agent/sessions/--Users-luo-Documents-github-codex-java-lsp-mcp--/2026-09-19T10-00-03-829Z_01a0b91b-d3f5-7399-b9ee-75ca51f2b4f2.jsonl`

2016 个助手消息。`stopReason`：`toolUse` 1932，`error` 57，`stop` 27，`length` 0。output token 最大 5721，p50 247，p90 1005，p99 2700。最长 thinking block 11005 字符，而且那一轮仍然是 `toolUse`。57 个 error 的文案是：`Connection error.` 35，`This operation was aborted` 7，`terminated` 7，`Request timed out.` 5，`502 Bad Gateway` 3。没有这句截断。

切换前两天（9 月 29 日 00:00 -04:00 到切换点）的真实回合只有 26 条，全部 `requested` 落在 16384 与 32768 之间，completion 最大 1569，finish 25 条 `stop_token`、1 条 `cancelled`。这 26 条里的 `output_limit` 计数是 0。同一窗口里 `requested<=64` 的 157 条几乎全是 `output_limit`，那是测试阶梯和冒烟（`max_tokens` 8/16/32 这一档），不要当成 Pi 故障。新镜像切换后的 5 条 `output_limit` 里，3 条是上线后的短冒烟，2 条才是这次 Pi。

结论只到这里：旧前端上，Pi 这种 32768 的工具回合都会在预算前发出停止符并完成工具调用，所以 Pi 收不到 `length`。新前端没有改这个预算，也没有改「思考不闭合就一直占 completion」的规则。第一次走出旧分布的是 9 月 30 日下午这个新会话的两轮。早上同一新镜像、同一条旧长会话的续写仍在旧分布里。

### 代码上已经对过、并且没有被证伪的部分

运行镜像相对旧 pin `44a2c6c` 的产品差异，在笔记本树 `1dacb0f` 上用 `git diff --stat 44a2c6c 1dacb0f -- src apps` 看过，只有 4 个文件：

- `src/targets/qwen3_8/impl/frontend/processor.cpp`
- `src/targets/qwen3_8/impl/frontend/processor.h`
- `src/targets/qwen3_8/impl/frontend/tokenizer.cpp`
- `src/targets/qwen3_8/impl/frontend/tokenizer.h`

停止符集合、思考通道解析、采样、`finish_reason_wire` 都不在这个 diff 里。权重是只读挂载，切换没换文件。

思考通道：

- `frontend.cpp` 约 937 行：`starts_in_reasoning = add_generation_prompt && enable_thinking`。
- 约 38 行：闭合标记是字面量 `"</think>"`。
- 约 523–552 行：`in_reasoning` 为真时，解码文本堆在 `think_marker_pending`，直到出现这个字面量才切回 content。
- 约 565–583 行：预算耗尽时 `terminalize`。若还在 reasoning，把剩余思考公布并关闭通道，finish 用的是调用方传入的 `OutputLimit`。
- 约 770–776 行：采样到停止符则 `FinishReason::StopToken`，即使当时还在 reasoning。这两次没有停止符，所以不是「闭合 token 被吞掉但 EOS 已经出现」。

`</think>` 在测试夹具里是单个 added token，id 248069；`<think>` 是 248068（`tests/targets/qwen3_8/test_frontend.cpp` 约 102 行）。线上词表是否仍是这个 id，没有在运行中的模型文件上再查过。不要在补丁里写死 248069。

`chat_template.cpp` 的 `resolve_reasoning_instructions`：未传 `reasoning_effort` 时默认 `XHigh`，会插入一段要求仔细思考的系统说明。`Medium` 返回空字符串，不插入说明。`Low` 才要求思考从简。代理把 Pi 没传的 effort 补成 `medium`，因此按笔记本上的代理源码，这两次不应该走到 xhigh 文案。主机上正在 exec 的代理是不是这份文件，还没核对。

当前扫描实现（`tokenizer.cpp` 约 643–717 行）和部署文档里的一句话不一致，下一会话要自己裁定，不要沿用文档一句就当代码：

- `load_added_tokens` 按 `tokenizer.json` 的 `added_tokens` 数组顺序 push，没有按 id 排序。
- `build_added_token_index` 只按首字节分桶，桶内仍是这个数组顺序。
- 扫描从左到右，在最早能匹配的字节上，取桶里第一个内容匹配的 token，然后停。同一起点的平局取决于数组顺序，不是代码里显式的「最小 id」。
- 部署文档 `docs/openclaw-qwen38-ninfer-b0-b1-20260930.md` 第 43 行写的是「最早起点，同一起点取最小 ID」。只有在数组本身已按 id 排好时，这两句才相同。
- 旧扫描是每个 added token 做 `find`，取最早出现位置；同一位置用严格小于保留向量里更早的那个。若平局双方首字节相同（同一位置匹配必然如此），新旧平局规则看起来等价。这是读 diff 后的判断，没有用这两次失败的渲染文本重放过。

B1 边界：对不上主 token 序列时走 `enforce_exact_token_prefix` 失败，请求应报错，而不是静默滑窗。这两次没有 `request_error`。这只能说明边界检查没失败，不能说明 GPU KV 与 token 账本一致。

Pi 请求形状（已读 `~/.pi/agent/models.json` 的字段，不要把 `apiKey` 抄进任何文件或日志）：

- provider `openclaw`，`baseUrl` `http://47.106.205.246:1082/v1`，`api` `openai-completions`。
- compat：`supportsDeveloperRole false`，`supportsReasoningEffort false`，`maxTokensField "max_tokens"`。没有设置 `thinkingFormat`。
- 模型 `openclaw/Qwen3.8-27B-WORK`，`reasoning true`，`contextWindow 262000`，`maxTokens 32768`。
- `detectCompat` 在这种 URL 上得到的 `thinkingFormat` 是 `"openai"`。`supportsReasoningEffort` 又被配置盖成 false，所以 Pi 不发送 `enable_thinking`，也不发送 `reasoning_effort`。
- 笔记本上的 `output/qwen38-27b-4090-ninfer/scripts/openai_compat_proxy.py`：从 `chat_template_kwargs` 抬升 `enable_thinking` / `reasoning_effort` / `preserve_thinking` 后删掉 kwargs。`enable_thinking === false` 时写成 `reasoning_effort=none`。否则 `setdefault("reasoning_effort", "medium")`，若 `enable_thinking` 缺省则写成 true。上游超时 1800 秒。330 秒的解码低于这个超时。代理不改写 `finish_reason`。
- 服务端 `--preserve-thinking` 开着。日志里的 `preserve_thinking: true` 可以来自这个服务端默认，不能单独证明 Pi 发了这个字段。Pi 的 `qwen-chat-template` 分支才会发 `preserve_thinking: true`，而这次 compat 不是那个分支。

G1 和 HTTP 阶梯只证明合成请求上新旧 token id 对齐、`token_mismatch` 为空。没有拿这个 Pi 会话的渲染结果重放。温度 1.0 的阶梯也不比较生成文本。所以「合成语料 token 对齐」不能外推成「这两轮 prompt 与旧前端逐 token 相同」。

### 被用户拒绝的方案，以及当时为什么提出

方案是：工具回合把 reasoning 封在 4096 或 8192，用尽时强制提交 `</think>` 这个 token（必须从线上词表查 id），再用剩余的客户端预算继续采样。动机是：Pi 把任何 `length` 都当成回合失败；这两次的 11 万字符思考已经被丢掉；旧分布里成功的思考大约不超过 3000 token，封顶不会切到那些已经自己闭合的回合。

用户对这个方案不满意。它还有这些未解决的问题，下一会话不要把它包装成根因修复：

- 它不解释新镜像为什么开始不停，只是把症状改成「提前离开思考」。
- 强制闭合后，模型仍可能在正文通道写满剩余预算且不调用工具，Pi 仍显示同一句。
- 若这两轮的 token 或 KV 已经偏了，强制闭合只会放出一个错误的工具调用。
- 它改变难任务上长思考的分布。用户要的是查清切换后才出现的原因。

## 当前状态 / 卡点

生产仍应是切换后的镜像。最后一次亲自核对是 2026-09-30 22:26–22:32 -04:00 这一窗口，不是写本文的时刻。

当时核对到的身份：

- unit `openclaw-qwen38-ninfer.service`，容器 `ninfer-4090-prod`。
- 镜像 `sha256:e753e2283db78bbe2fe1fc92b9d45300a27fd5765b367c434c9023cbf2cb1cb3`，标签 `ninfer-4090:frontend-b0-b1-1dacb0f`。
- 回滚标签 `ninfer-4090:prepare-detail` 必须仍是 `sha256:9c2dec8b9ff087d178f72b68251ff7ff18c77330833eaade5b40bf4c49eb312b`。不要 retag。
- 脚本备份 `/home/hhtele/ninfer-4090/launch/production-18343.sh.bak-20260930-cutover`。
- 主机脚本是权威。笔记本 `output/qwen38-27b-4090-ninfer/scripts/production-18343.sh` 是旧副本，不要 scp 上去覆盖。
- 端口：兼容层 `0.0.0.0:18343`，引擎 `127.0.0.1:18030`，NGINX `0.0.0.0:28343`。公网入口是跳板 `47.106.205.246:1082`，Pi 的 baseUrl 指向这里。28343 需要 Bearer。调查时 `/var/log/nginx/access.log` 只有 792 字节、mtime 2026-09-30 16:47，内容没读。真实 Pi 更可能直接进 18343 的 Python 代理，而不是 NGINX。
- 单卡 4090，约 22GB。不要同时再起一个模型进程。`ninfer-g1-devel` 调查结束时还在，没有 GPU，不要 `docker rm`，不要清 `/tmp/ninfer-g1/build`。
- `journalctl -u openclaw-qwen38-ninfer.service --since "2026-09-30 12:00:00"` 曾经打印 `-- No entries --`。当时 GPU 进程仍在。不要把空 journal 当成 unit 死亡或日志真空的证明。可能是权限或 journal 没接 docker 的 stdout。

卡点：机制停在「模型在这两轮没有采样出 `</think>` 或 EOS，于是 32768 全部算 completion，wire 变成 length」。没有证明分词差异，也没有证明 KV 错位。没有在旧前端重放这两次 prompt。NGINX access log、容器 stdout、主机代理脚本路径，都还没读。

CodexGame 工作区当时是脏的，与本故障无关：`docs/openclaw-qwen38-ninfer.md` 有修改，`docs/openclaw-qwen38-ninfer-b0-b1-20260930.md` 未跟踪。不要回滚这些文件，也不要在没被要求时提交。本 `HANDOFF.md` 是这次交接新增的。

## 下一步计划

目标是解释「为什么切换后才出现不闭合的思考」，而不是再交一个思考封顶。建议顺序如下。每一步都先复述它要区分的假设。未跑之前不要写成已证实。

1. 复核生产身份没变：镜像 digest、脚本第 6 行 `IMAGE=`、回滚标签 digest、18343/18030 是否仍是 `openclaw/Qwen3.8-27B-WORK`、JSONL 是否又有新的 `output_limit`。有已建立连接时不要重启。
2. 在主机脚本里找到真正 exec 的兼容层路径，和笔记本 `openai_compat_proxy.py` 对 diff。确认线上是否仍把缺省请求改成 `enable_thinking=true` 且 `reasoning_effort=medium`。若主机代理没注入 medium，模板会落到 xhigh 文案，这是一条还没排除的行为差异。
3. 用这两次 Pi 会话里失败回合的消息，在 CPU 上分别用旧 pin `44a2c6c` 和新前端渲染并编码。只比较 token id、边界和 `<think>` / `</think>` / `<|im_end|>` 的位置。不要把 prompt 或思考正文打进日志、提交或聊天。旧前端 oracle 的建法见 `docs/ninfer-44a2c6c-frontend-optimization-v2` 和已有 G1 驱动，不要在 4090 上再加载一份 22GB 权重来做这件事。
4. 若 token id 不一致，沿新增扫描的平局和工具结果里的重叠 added token 往下看。部署文档写的「最小 ID」和 `tokenizer.cpp` 的数组顺序要先对齐。
5. 若 token id 一致，再查 KV。失败轮的 hit 等于上一轮 prompt+completion-1，L1 restore 等于 hit，rollback 为 false。要找的是「账本匹配但 GPU 前缀不是这些 token」的路径，而不是再统计一次 finish。`--lm-head-draft` 的接受率不能当 KV 正确性的证据。
6. 读 NGINX `access.log` 时只留时间、状态码、字节数和方法，去掉 query 和 Authorization。确认 12:20 之后还有没有打到 29 的流量。容器 stdout 若有请求摘要，只抽 finish、token 计数和时间，不抽正文。
7. 单独看早上 04:15:00 那条 `stop_token` 且 `tool_call_count=0` 的 Pi 消息，确认它是正常的纯文本回答还是未解析的工具调用。这是另一条线索，不是这两次 length。
8. 只有在原因钉死后才提议修复。修复若要新镜像和重启，先写清它如何解释这两次样本，以及为什么不会把旧的 1902 次正常回合改掉，然后再向用户要重启授权。

## 绝对不要再踩的坑

- 不要实现或部署「思考封顶 + 强制 `</think>`」。用户已经拒绝。
- 不要把切换前 JSONL 里大量 `output_limit` 当成 Pi 故障。那些是 `requested<=64` 的阶梯和冒烟。上线后 3 条短 `output_limit` 同样是冒烟。思考打开时 `max_tokens` 16/32 会把预算耗在思考里，正文为空，那次冒烟用 128 才得到内容「二」。
- 不要说旧镜像也有同样的 Pi 截断。1902 次 `requested>=32768` 的旧工具回合没有一次打满。9 月 12 日那条 requested 只有 1276，9 月 21 日那 3 条是 thinking false 的小上下文 `context_capacity`。
- 不要说新镜像每一次续写都坏。9 月 30 日 03:49–04:15 的长会话在新镜像上仍是 `stop_token`。两次失败是下午新会话里的两轮。
- 不要把 `usage.reasoning=0` 当成没有思考。代理会补 0。看 Pi 的 thinking block 和完成 token 数。
- 不要把 journal 为空、或 JSONL 停在 12:20，写成服务已死。先看容器、GPU 显存和端口。
- 不要打印 NGINX Bearer、sudo 口令、`models.json` 的 `apiKey`、prompt、工具结果或思考正文。结构计数可以，原文不行。
- sudo 只用 `/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh`。不要在聊天里复述它读到的密钥。
- 29 现在从笔记本走公网跳板。用 `jssh 29`，不要假设内网 `ssh 29` 还能到。`jssh` / `jscp` / `jrsync` 是本机 zsh 函数：`ssh -J jump`、`scp -o ProxyJump=jump`、`rsync -e "ssh -J jump"`。Host `jump` 是 `frpc@47.106.205.246` 端口 6000，密钥 `~/.ssh/id_ed25519`。Host `29` 落地 `hhtele@192.168.10.29`。`jssh 31` 落地 `hhtele@192.168.10.31`，这次故障不在 31。
- 主机没有单独的 rsync，用 `jrsync`。不要把笔记本的 `production-18343.sh` 或代理脚本覆盖到主机。
- 不要往 `/home/hhtele/ninfer-4090` 写东西，除非用户再次授权，并且先备份要改的脚本。不要动 `/tmp/ninfer-g1/build`，不要删 `ninfer-g1-devel`。
- 不要同时跑两个约 22GB 的服务。不要把 `prepare-detail` retag 到新 digest。不要换权重，不要开 schema 21，不要做 B2。
- 不要为了重放这两次请求去打生产 18343。`max-concurrency` 是 1，一次 330 秒会堵住真实用户。CPU 对照可以离线做。
- JSONL 轮转文件的 mtime 是轮转时刻，不是里面记录的日期。`-2026-09-30` 在 2026-09-30 00:00 被转走，装的是 9 月 29 日。以每行 `timestamp_unix_ms` 为准。schema 19 和 20 都存在，缺字段用默认值，不要假设每行都有 `continuation_cache`。
- `prepare_detail.tokenize` 包住整段 `encode_rendered_chat`。`rendered_chars` 是 UTF-8 字节数。不要把 `tokenize_impl` 或 B1 计数写进 JSONL。
- 不要提交 CodexGame 里与本故障无关的脏文件。不要改 git 身份。不要 force-push。产品仓库在嵌套目录，见下一节。`lkyprogramer` 对 `tensorninja/ninfer-4090` 只有读权限，推送到 fork 曾经得到 HTTP 403 的是对上游的 push，不是对 fork。不要改 `origin` 指向。
- 笔记本 Pi 只用 `nvm use v22.19.0`。不要改 `~/.pi/agent/models.json`。4090 上没有 Pi。

## 关键文件 / 命令 / 验证

### 访问和权威文档

```bash
jssh 29
jscp <local> 29:<remote>
jrsync -av <local>/ 29:<remote>/
```

部署身份以 `docs/openclaw-qwen38-ninfer-b0-b1-20260930.md` 为准。`docs/openclaw-qwen38-ninfer.md` 仍是架构和 llama.cpp 回滚说明，其中 2026-09-08 的镜像表已过期。构建门禁原文在 `docs/ninfer-44a2c6c-frontend-optimization-v2/`。

主机：

- 脚本：`/home/hhtele/ninfer-4090/launch/production-18343.sh`
- 备份：同目录 `production-18343.sh.bak-20260930-cutover`
- 日志目录：`/home/hhtele/ninfer-4090/logs/`，容器内 `/var/log/ninfer/`
- 当前日志：`ninfer-request.jsonl`。调查时 1790122 字节，mtime 2026-09-30 12:20:11
- 按天转走的文件也在这个目录，从 2026-09-09 到 `-2026-09-30`。分析旧镜像时要读这些文件，不能只读当前文件
- 缓存：`/home/hhtele/ninfer-4090/cache` → `/var/cache/ninfer`
- 权重：`/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer`，容器内只读 `/opt/ninfer/models/qwen3_8_27b.ninfer`，文件 SHA-256 `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`
- sudo 包装：`/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh`

启动参数切换前后比对过，除 `IMAGE=` 外相同：`--model-id openclaw/Qwen3.8-27B-WORK`，`--host 127.0.0.1 --port 18030`，`--max-context 262144 --kv-capacity 262144`，`--max-concurrency 1 --max-pending-requests 8 --pending-timeout-ms 600000`，`--prefill-chunk 1024 --kv-dtype rk4v4-e8`，`--spec mtp --draft-tokens 3 --lm-head-draft`，`--prefix-checkpoint-policy rolling-tool`，`--continuation-cache l1-l2`，L1 6144 MiB，L2 8192 MiB，`--request-log-jsonl /var/log/ninfer/ninfer-request.jsonl`，`--preserve-thinking`，`--default-max-tokens 32768`，`--temperature 1.0 --top-p 0.95 --top-k 20 --presence-penalty 0.0`。客户端 temperature 仍覆盖命令行，范围 `[0, 2]`。挂载三条：权重 ro、cache、logs。`--restart=no`，`--network host`，`--gpus all`。

回滚是把备份脚本拷回并重启 unit，确认第 6 行回到 `IMAGE=ninfer-4090:prepare-detail`，然后核对容器 digest 和两个 `/v1/models`。用户还没授权回滚。已有 18343 连接时不要停。

### 源码

笔记本产品树：`output/qwen38-27b-4090-ninfer/ninfer-4090`，分支 `b0-scanner`。调查时 tip 是 `e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`，跟踪 fork `https://github.com/lkyprogramer/ninfer-4090` 的 `b0-scanner`。运行镜像不是从这个 tip 重建的。

镜像里有、并且和线上行为有关的提交：`6b4286d` B0 单调扫描，`e924cc2` tokenizer work 计数（不进 JSONL），`1d05441` 重启轨迹，`a5128f0` B1 边界。schema-20 overlay 与后来的提交 `f3b231d` 一致，构建时那 11 个文件还没提交。overlay SHA-256 `579c0853f2ea690fd779861766f2530f213af2c990db023c3dfaeb2d01df01eb`。

不在运行镜像里：`1dacb0f` CPU harness，`46320bd` 只是 `Dockerfile.sm89-nobake`（其 SHA-256 `3f1fd17dbb4599a135958e166101cde3fdc03a369b0e7b25ab087d8a210e7cdc`），`7c9d959` swiglu skip，`e0b05f7` G1 驱动，`d5d2e17` 与 `c782577` oracle。`BUILD_TESTING=OFF`。

旧镜像从 `44a2c6c` 加当时未推送的本地补丁做成，已经写 schema 20。六个前端资源合计 SHA-256 `c8afe487da2dd305125cd7421a668bd55cadd632b13b0999956a7300d3917a51`。G0 不是 PASS，资源指纹当时自标 `LOCAL_BYTES_MEASURED_NOT_PRODUCTION_CERTIFIED`。

代码锚点：

- `src/serve/translate.cpp` `finish_reason_wire`，约 251 行。
- `src/serve/request_log.cpp`：`finish_reason_name` 约 89 行，`request_json` 约 219 行，`continuation_json` 约 260 行，`request_done` 结果字段约 691 行。
- `src/targets/qwen3_8/impl/frontend/frontend.cpp`：思考闭合与 `starts_in_reasoning`，约 38、523、746、937 行。
- `src/targets/qwen3_8/impl/frontend/tokenizer.cpp`：分桶与扫描，约 643–717 行。
- `src/targets/qwen3_8/impl/frontend/chat_template.cpp`：effort 文案，约 218–242 行。medium 为空，缺省是 xhigh。
- `src/targets/qwen3_8/impl/frontend/processor.cpp`：B1 从重启点做精确前缀校验。
- 代理：`output/qwen38-27b-4090-ninfer/scripts/openai_compat_proxy.py` 约 129–144 行。以主机脚本 exec 的那份为准。

### 日志字段和已经跑过的统计

`request_done` 有用字段：`timestamp_unix_ms`，`schema_version`，`server_instance_id`，`request.requested_output_tokens` 与 `_source`，`message_count`，`tool_count`，`tool_choice`，`enable_thinking`，`preserve_thinking`，`sampling.temperature`，`result.finish_reason`，`prompt_tokens`，`completion_tokens`，`prefix_cache_hit_tokens`，`prefix_reuse_path`，`tool_call_count`，`timings_seconds` 的 decode/total/ttft/prefill，`speculative` 的 drafted/accepted/rounds/fallback，`continuation_cache` 的 source/restored_tokens/deepest_candidate_agreement/final_miss_reason/restore_failure/destructive_rollback。

调查时全库解析：`bad_json` 1，`request_done` 8098。schema 计数 19 有 17834 条事件、20 有 8163 条（这是所有事件，不是 done 条数）。错误汇总里，近两日窗口能归到旧镜像的 `request_error` 文案是 `client disconnected`，19 条。新镜像该窗口 `request_error` 为 0。

近两日窗口（2026-09-29 00:00 -04:00 起）`request_done` 332：旧 183，新 149。真实口径旧 26 / 新 142。新真实 finish：`stop_token` 140，`output_limit` 2。新真实 completion：139 条小于 2000，1 条至少 2000，2 条至少 32768。那 1 条 ≥2000 就是早上 3031 的 `stop_token`。

重跑统计时用只读 Python 读 JSONL，按 `timestamp_unix_ms` 切旧新，不要把 `requested<=64` 算进 Pi。分析脚本用完即删，不要留在仓库里。

### 还没跑的检查

- 主机正在 exec 的代理脚本与笔记本副本的 diff。
- NGINX `access.log` / `error.log` 的内容。只见过 `ls`：access.log 792 字节，mtime 2026-09-30 16:47。
- 这两次的容器 stdout。
- 用失败回合的渲染文本做旧/新 token id diff。
- 线上词表里 `</think>` 的真实 id。
- 04:15:00 那条 `tool_call_count=0` 的 `stop_token` 在 Pi 长会话里的 block 类型。
- 12:20 之后是否又有请求。写本文时没有再连 29。

## 给下一会话的第一步

先读本文件和 `docs/openclaw-qwen38-ninfer-b0-b1-20260930.md`。然后只读执行：

```bash
jssh 29 'python3 - << "PY"
import os, glob
from datetime import datetime
base="/home/hhtele/ninfer-4090/logs"
print("NOW", datetime.now().isoformat())
for p in sorted(glob.glob(base+"/ninfer-request.jsonl*")):
    st=os.stat(p)
    print(st.st_size, datetime.fromtimestamp(st.st_mtime).isoformat(), p)
PY
docker inspect -f "{{.Image}}" ninfer-4090-prod
sed -n "6p" /home/hhtele/ninfer-4090/launch/production-18343.sh'
```

确认镜像仍是 `sha256:e753e2283db78bbe2fe1fc92b9d45300a27fd5765b367c434c9023cbf2cb1cb3`，脚本第 6 行仍是 `IMAGE=ninfer-4090:frontend-b0-b1-1dacb0f`。若 JSONL 在 12:20:11 之后又有增长，先把新增的 `output_limit` / `context_capacity` 按同样口径抽出来，再决定旧结论还成不成立。

不要重启，不要回滚，不要改 Pi，不要实现思考封顶。身份核对之后的第一件分析是：在主机脚本里定位正在运行的兼容层，确认 `reasoning_effort=medium` 是否真的注入。这条若被否定，模板默认 xhigh 就是一条还没排除的切换差异。
