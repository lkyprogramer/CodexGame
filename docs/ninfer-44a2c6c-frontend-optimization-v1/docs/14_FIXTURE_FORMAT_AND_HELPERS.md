# 14｜交付测试输入、辅助工具与使用方式

## 14.1 数据不是性能结果

本包交付86个小型对抗输入、8种长会话生成配方及可重复生成器。它们是**可让测试程序读取的输入合同**，不是已经跑完的Qwen/NInfer测试。真正的token IDs和PreparedPrompt golden必须由固定基线及原制品的六份frontend资源生成。

`data/test-matrix.json`把每个case映射到负责实现的任务及拟新增test target。某case不适用于真实资源，例如synthetic-added-priority，必须用synthetic fixture测试；不得为了运行它改生产tokenizer。

## 14.2 adversarial_cases.jsonl的kind

| kind | 读取方式与测试操作 | oracle/验收 |
|---|---|---|
| `raw-boundaries` | 按text原始UTF-8 bytes枚举byte_cuts；按parse_added_tokens设置调用encode与局部resolver | baseline完整E(text)、每个独立E(prefix)及error；cut可能在码点内部，不能预过滤非法cut |
| `append-pair` | 先编码before建立snapshot，再编码after；after未必是append，测试fallback | after的候选完整结果必须等于baseline；无安全cut可正确miss |
| `synthetic-added-priority` | 创建完整byte-vocab的专用Tokenizer；added_tokens中ID≥300只属于合成资源 | 同位置按小ID，不得按最长匹配；选中ID和后续tokens与baseline一致 |
| `synthetic-merge` | 专用byte-vocab+给出的merge规则；枚举cut | `a+b->ab`让`E(a)`不是`E(ab)`的token前缀，必须维持nonexact错误 |
| `invalid-utf8` | 严格base64解码raw_base64，直接传std::string/string_view；不要提前Unicode解码修复 | 和baseline相同失败阶段/异常包装，不能替换成U+FFFD让它通过 |
| `rendered-contract` | 构造RenderedChat，将rendered字段映射至三个optional与ordered checkpoint_hints | stable/full、turn/not-full、user=0、重复hint、输出顺序与首个错误 |
| `chat-transform` | 按messages和options构造PromptInput，然后应用transform形成第二请求 | render、token_ids、全部metadata、可观察错误合同 |
| `lifecycle` | 不当作普通字符串测试；驱动有界cache的所有权/预算/乱序发布场景 | 相同prompt结果，无悬空引用、无错误串用、预算触发时正常fallback |

`real-or-synthetic-byte-vocab`表示至少在完整synthetic资源上运行，真实资源可再运行；不是随机选其一来跳过真实资源gate。两个模板组合都要测：`thinking_toggle_compatible_options`使用thinking-toggle模板时**移除reasoning_effort**，因为该模板在基线明确不支持该字段；另加不移除字段时原错误仍发生的负例。

`checks`是要求，不是结果。`oracle`标识固定基线，不含实际golden。JSON中没有业务token ID的猜测值。

## 14.3 chat-transform操作定义

`append_messages`：按顺序追加，不重排历史。`after_options`：覆盖明确列出的字段，其余沿用。`after_tools`：替换整个tools清单，并维持接收到的对象成员顺序。`replace_message`：只替换给出的index。`keep_first_messages`：截短到该条数。未出现的操作不执行。

每个chat-transform至少分别检查baseline第一请求和第二请求，candidate第一请求/第二请求以及第二请求独立fresh-cache路径。测试是否hit与输出是否正确是两条断言，不能让“所有请求都fallback”伪装成增量功能通过。

## 14.4 生成长会话

```bash
python3 tools/generate_sessions.py --out-dir /tmp/ninfer-ftc-fixtures
# 单独生成最接近最慢请求形态的一组
python3 tools/generate_sessions.py --out-dir /tmp/ninfer-ftc-max --only max-shape
```

生成器只使用Python标准库，固定seed；不连外网、不发HTTP、不写原仓。输出每个配方一个JSONL和manifest。每条记录包含完整request和canonical input SHA。不存在model字段，回放器统一注入本机固定model ID后，再计算**实际送入对照实验**的payload hash。

生成器用字符数近似控制体积，`target_token_hint=245194`不是实际245194 token。所有输出显式`token_count_status=UNMEASURED`。正式benchmark先在离线校准阶段，使用固定tokenizer测量实际token数，通过增减最后一个工具结果的普通payload调整到目标范围；冻结校准后的request、真实token数和hash。不得在计时区调用token-count接口、动态调整文本或使用模型生成填充。

生成的长历史只有开头一个真实user query，后续是assistant/tool续写；奇数消息数以一个额外assistant说明对齐，不通过尾部新增user重置Rolling hints。否则会意外绕过本次要测试的检查点放大。

合成性能最重要的比较是：同总字节/近似token规模、不同checkpoint数量。默认8组配方用于初筛；最终T10要增加**相同冻结payload重分组**的100/200/400/800消息系列，以区分文本体积与hint数量。报告实际bytes/hints/tokens，不用名义档位替代测量。

## 14.5 原制品资源与独立oracle

六资源保持原始bytes；不要改行尾、JSON缩进、模板最后一个换行。测试里的模板fixture有读取时去除尾换行的既有逻辑，必须与固定源一致。

基线oracle导出程序须提供两种输入：raw tokenizer probe和完整PromptInput probe。raw probe输出tokens或error；完整probe输出全部PreparedPrompt语义字段。程序仅调用公有/测试允许的frontend入口，不运行GPUforward。基线oracle补丁只增加导出测试入口，不修改tokenizer、renderer和processor算法，记录其diff；candidate不得通过自己的新trace产生所谓baseline golden。

没有原资源时先运行synthetic测试，再将真实资源gate记NOT_RUN。禁止下载HF main补齐，更不能凭最终生成答案“看起来对”补写PASS。

## 14.6 检查代码版本

```bash
python3 tools/check_source_pin.py --repo /path/to/ninfer-4090 \
  --output /tmp/ninfer-base-check.json
```

脚本只运行本地只读git命令，核对指定commit、subject与source-lock的Git blob SHA。它不clone/fetch/checkout/reset。HEAD允许为基线后裔但会警告；dirty tree也会警告。**PASS仅表示固定提交对象/文件存在且匹配，不表示当前工作树、诊断镜像和运行进程等同此提交。**必须另行审阅诊断overlay并记录实际镜像ID、binary hash、启动参数。

## 14.7 对照结果汇总

先把本机schema19/20日志通过明确映射转换成`schemas/benchmark-row.schema.json`。本包不自动猜测原日志字段。`pair_id`必须包含case与repeat；两路的session/input/resources/prompt/cache_kind/cohort必须相同。

```bash
python3 tools/summarize_bench.py /tmp/normalized-results.jsonl \
  --baseline legacy --candidate single-pass --output /tmp/paired.json
```

工具拒绝重复pair、缺配对、身份不一致、负数/NaN/Infinity和缺失必填指标；可选TTFT未测时不当成0。失败/取消请求的tokenize_seconds允许显式null，成功请求则必须有真实非负测量；不为缺测填0。错误/取消/拒绝记录不消失，而是显示在status_counts并不计入性能样本。`oracle_match=false`显示失配；null是未验证，不自动当通过。

输出始终是`ANALYSIS_ONLY`。按原请求计算差值/比值后，再按session、depth、cold/warm分层；p50/p90使用type-7线性插值。每个数都附完整配对分母。没有自动G1/G4通过逻辑，也没有置信区间和能耗归因；这些仍按08/09人工及Review验收。

## 14.8 文档包自检

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 tools/validate_pack.py
```

第一条只测试本包helper；第二条检查文件、JSON/JSONL、任务依赖、链接和manifest。它们不是NInfer的CTest，也不能替代CUDA/4090/真实Agent测试。


## 14.9 已随包附带的长输入

`data/generated_sessions/`已包含按8个配方生成的32条请求输入与文件hash manifest，便于直接启动离线oracle工作；生成器仍提供以便复现。它们没有真实tokenizer校准，也没有GPU结果。不能把max-shape的名义245194当作测得深度，更不能将这些合成记录替代用户未提供的1617条生产原始日志。
