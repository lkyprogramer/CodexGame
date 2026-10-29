# 验证工具增量升级说明

本目录是在原附件验证框架的独立副本中修复测量、评分和证据完整性问题。**未修改 Strata 引擎；未运行目标 GPU；未连接或部署 29 号机。** 本文说明真正可执行的接口、改变的判定行为与尚未实现的边界。

## 1. 命令接口

在包根目录运行，Python 3.10+（本轮本地运行环境为3.12；目标机原报告为3.11.2）：

```bash
PYTHONDONTWRITEBYTECODE=1 python -B -m lab.cli selftest
PYTHONDONTWRITEBYTECODE=1 python -B -m lab.cli --help

# 只有结构检查：无需local.json，无GPU、无HTTP请求。
PYTHONDONTWRITEBYTECODE=1 python -B -m lab.cli validate-plan \
  --plan plans/park_restore.example.json

# 自动使用campaign.json登记的arms、comparisons、primary_metric。
PYTHONDONTWRITEBYTECODE=1 python -B -m lab.cli stats --results /ABS/PATH/results

# 显式选择配对与时间指标；多组可重复传 --pair。
PYTHONDONTWRITEBYTECODE=1 python -B -m lab.cli stats \
  --results /ABS/PATH/results --pair p:base --metric decode_ms
```

`run.sh`/`run.ps1` 继续转发同样的 CLI。原 `init/doctor/assets/bootstrap/prepare/build/run/noise/mig/cfg/scenario` 名称不变。GPU相关命令仍需要原维护窗口、安全门、完整模型/资产和实际构建；本轮没有执行这些命令。

`stats` 在写出 `summary.json`、`requests.csv`、`REPORT.md` 后，如果有缺项、重复、失败或未评分则退出码为 **2**；合法描述性/筛选报告为0。0不是采用或部署许可。未知实验臂、非法metric、坏JSON等参数错误同样退出2。

支持的时间metric：`wall_s`、`ttft_s`、`visible_ttft_s`、`reasoning_ttft_s`、`tool_ttft_s`、`prompt_ms`、`decode_ms`。均按“时间越低越好”计算；不把tok/s当作时间输入。`ttft_s`保留旧含义，详见第3节。

## 2. 严格 JSON 评分

`lab.scoring.score(case,response)` API不变。新增 `strict_json(text)` 与 `typed_equal(actual,expected)`：

- 递归区分JSON表示类型：`false`≠`0`、`true`≠`1`、`1`≠`1.0`；list/dict嵌套同样适用。
- 拒绝重复object key以及NaN/Infinity扩展；非有限float不可能通过exact比较。
- 工具名必须来自声明白名单；工具参数必须与可信fixture的预期键、值和类型一致。
- 本功能不是通用JSON Schema实现。当前固定oracle使用exact expected值，因此精确比较比仅检查schema更严格；开放式schema、`oneOf`等仍需专门validator。

旧报告的89/90不能自动用新规则重算，因为附件没有原始response数据。新版本评分结果需标记harness版本；不得把修复前后的通过率直接混池。

## 3. 流式计时与超时

`http.chat(base,body,key='',timeout=1800,on_first=None,idle_timeout_s=None)` 保留所有旧位置参数，新增最后一个可选参数。

- `timeout`：整个请求的绝对截止，包含连接、HTTP头、prefill和stream。
- `idle_timeout_s`：socket无数据期限。None时取timeout；不再暗中截为60秒。
- 独立watchdog只中断本函数创建的socket。持续heartbeat或持续发送半条SSE行不能延长绝对截止。
- CLI运行时从local配置读取 `request_timeout_s` 和新增 `request_idle_timeout_s`。示例保持1800秒绝对期限、idle=null；真实长prefill所需值应预先冻结。

新response字段：

| 字段 | 含义 |
|---|---|
| `first_s` | 首个非空reasoning/visible/tool事件；兼容旧字段 |
| `first_reasoning_s` | 首段reasoning到达 |
| `first_visible_s` | 首段visible content到达 |
| `first_tool_s` | 首个tool_call片段到达，可能只有id/name |
| `first_tool_arguments_s` | 首段非空工具参数到达；不代表完整参数已可执行 |
| `output_event_times_s` | 有非空输出的SSE数据事件到达时间 |
| `output_event_gaps_s` | 相邻输出事件间隔；**不是token ITL** |

`measurements`相应增加 `reasoning_ttft_s/visible_ttft_s/tool_ttft_s/tool_arguments_ttft_s/output_events`。`ttft_s`仍映射first_s，避免破坏旧分析；新真实Pi工作流应明确选visible或tool首事件。`token_itl_ms`固定null；精确token ITL必须有引擎逐token时钟。缺usage时generated_tokens仍为null，绝不拿事件数填补。

限制：仍按Strata当前“每条data行是完整JSON”解析SSE；没有宣称支持任意多行data frame、多个并行choice的独立输出或重连续传。该工具只连接loopback HTTP，不实现TLS/远程认证会话。

## 4. 计划驱动的配对统计

新campaign自动输出schema_version=2的计划，核心形状如下。hash示例为说明性文本，真实runner会计算SHA256。

```json
{
  "schema_version": 2,
  "mode": "CONFIG",
  "arms": ["base", "cfg"],
  "comparisons": [["base", "cfg"]],
  "rounds": 5,
  "primary_metric": "wall_s",
  "case_ids": ["decode-short"],
  "cases": [{
    "id": "decode-short",
    "group": "decode",
    "cache_state": "sequence_controlled",
    "scenario": "http_replay",
    "context_bucket": "4096",
    "request_sha256": "actual-request-sha256",
    "fixed_output": 512
  }]
}
```

每条measured JSONL记录必须匹配预期 `round × arm × case_id`、顺序、request hash、分层标签与固定输出长度。缺失一整轮（即使所有arm同时缺失）、重复、额外case/arm、非有限/非正时间、失败、未评分都显示在 `invalid_pairs` 或对应失败字段中，并阻止候选结论。

schema2的每个case descriptor还必须包含合法的 `request_sha256`：恰好64个十六进制字符的字符串，大小写均可。缺失、空值、错误类型、长度不符或非hex字符都会使计划无效，即使所有arm的观测hash相同也不能补救。上面的`actual-request-sha256`是说明性占位，必须替换为冻结真实请求的摘要。原有plan/record摘要精确一致校验继续保留；旧无计划数据仍只可描述，不因这个修复自动获得资格。

新计划还要求收尾回执：

```json
{"state":"COMPLETE","final_audit":"PASS"}
```

只有生命周期正常收尾、配置与资产复核无异常，runner才写 `COMPLETION.json`。存在 `FAILURE.json` 时不能因原始请求已跑满就接受结果。

### 分层与抽样

固定分层键：`group/cache_state/scenario/context_bucket`。不同层永不合并成总体提速。`strata_comparisons`保留每层的全部显式pair；当且仅当只有一层，兼容字段 `comparisons`才提供该层结果，否则各pair为null。`runs.wall_s`是诊断总和，不用于跨层收益判定。

每层每轮先聚合该层预定case的时间，再对整轮做配对log-ratio bootstrap（5000 draws）；不重采样token、kernel或SSE chunk。结果中的 `sufficient` 至少需要5轮，仍只是筛选；正式质量非劣性、尾延迟和多候选选择偏差未由此解决。

`sequence_controlled`表示固定回放顺序，**不证明SSD冷读，也不证明零prefix reuse**。要比较明确冷/暖策略，必须在冻结corpus中预先赋 `cache_state`，并以read/reused tokens和机制回执检查其真实性；事后按命中效果重分组会改变估计对象。

### 决策状态

- 缺项/计划不全：`INCOMPLETE_OR_INVALID`；任何质量失败：`REJECT_OR_FIX`。
- MIG/CFG合法数据：`PAIRED_SCREEN_ONLY`；多层：`STRATIFIED_SCREEN_ONLY`。
- CLI临时改变登记pair或primary metric：`EXPLORATORY_ONLY`。
- 单臂：`RECORD_ONLY`；A/A：`NOISE_CONTROL_ONLY`。
- 只有预登记的单层PR三臂、关闭路径CI在±3%内、开启路径时间改善≥5%且CI下界>0，才可能 `CANDIDATE_FOR_HOLDOUT_NOT_PRODUCTION`。

旧无计划或没有schema2收尾协议的结果仍能生成描述性比值，但不会自动升级成候选。不要给历史目录补造完成回执使其“通过”。

## 5. 共享请求与生命周期审计

`audited_chat`用于campaign和三个既有scenario，发送前检查 `完整prompt + max_tokens + safety_tokens <= 131072`，响应后要求整型prompt/completion usage、检查输出上限与计数漂移。无法核查或漂移超过32token会记录错误并停止该场景继续发送；32token容差沿用旧协议，并非允许未知模板变化。

`managed_server`只管理当前OwnedServer，成功或失败均尝试 `wait_released`；释放失败写独立回执。`evidence_lifecycle`在所有出口复核配置与资产；次要审计错误不会覆盖原始请求错误，而是写入 `final_audit_errors`。MIG另保留部署目录清单差异。

资产收尾是**路径集合、size、mtime检查**，不是重新哈希78GB权重。首次assets快照仍有完整SHA256；不可把元数据快检描述为每次重新验证内容哈希。正式交付/发布应另行做完整hash或使用已验证的不可变资产策略。

GPU启动与运行中定期检查：唯一native engine必须具有预期可执行路径、当前进程组、pid/starttime以及131072上下文参数。发现外来进程会令本轮失败，只向本轮进程组发信号，不停止外来进程。`gpu_monitor_interval_s`可配置0.1～60秒，默认2秒；没有忽略外来计算进程的开关。profiler包装树继续支持原 `LAB_BUILD.json.gpu_exe`，但真实engine仍须属于本轮进程组。

禁止的 `STRATA_STAGE_PIN`、`STRATA_ROUTE_RESIDENT` 在最终运行配置统一拒绝，不再仅检查cfg入口。即使值为0也拒绝出现：应明确移除变量，不依赖各版本对字符串值的解释。

## 6. park/restore离线计划

新增 `lab.plans.validate_plan(plan)` 及 `validate-plan --plan FILE`。示例是格式示范，counted_prompt_tokens为合成值，不能拿去宣称真实token计数合格。

必须字段：

- `schema_version:1`、`kind:"park_restore"`、`engine_adapter:null`；validator明确拒绝自称已实现adapter。
- `max_context:131072`、`safety_tokens>=4096`、`min_available_mib>=4096`、`max_active_gpu_contexts:1`。
- 至少两个唯一session ID、至少三步；步骤必须形成离开某session后再恢复的序列。
- 每步含唯一id、声明session、冻结的request.messages/max_tokens、整型counted_prompt_tokens、expected_events。
- 事件限park/restore/evict/refuse/cancel/capture；至少显式park和restore。
- `required_receipts`必须覆盖示例的请求身份、usage、snapshot bytes、heap RSS、MemAvailable、swap、read/reused tokens、park/restore/trim时间及质量断言。

成功只返回 `OFFLINE_PLAN_VALID`，同时固定 `live_ready:false`、`tokenizer_verified:false`、`execution_result:"NOT_RUN"`、`engine_adapter:"NOT_IMPLEMENTED"`。这不是Strata会话ID适配、park/restore触发、内存有界、取消恢复或质量通过证明。

未来adapter必须先审实际新base的会话路由和日志事件：将固定逻辑session映射到服务端真实隔离键，保存token与KV/递推/MTP状态身份，并以引擎事件回执证明park/restore发生。当前没有 `scenario --name park-restore` 命令，不能在新文档中假装存在。

## 7. 兼容与集成约束

- 函数名和旧CLI保留；有意收紧的是评分类型、计划完整性和stats退出码。
- 旧 `test_clean_pairs_remain_screening_only` 原来只写requests.jsonl；现在补齐真实预登记计划和final receipt，继续检查候选仅为留出筛选。没有更改门槛去使旧缺项结果通过。
- `workspace.lock()`动态读取 `sources/LOCK.json`；没有在新代码中硬编码生产A0或newbase SHA。新包维护者应分别冻结production历史身份与最新基线，不能单凭版本文本相同替代hash。
- 既有路径约定仍是 `workspace/trees/base`、`workspace/trees/pr-N`、`build-lab/strata` 和 `LAB_BUILD.json`。当前 `prepare`还读取包根 `START_HERE_AI.md` 和 `prs/*PR<N>.md`；最终整包需提供与experiments对应的新任务文档。
- 题集和CLI候选列表来自 `config/experiments.json`、`fixtures/`；source lock与实验基线需由新包统一更新。原升级工作副本中的旧START/prs/sources（最终包已替换为最新研究版本）只是保持原测试依赖，不能覆盖主交付的新研究文档。
- `cfg --env`仍只接受STRATA_*。`MALLOC_MMAP_THRESHOLD_`/GLIBC_TUNABLES的受控allocator对照接口尚未实现；不要声称可直接用现cfg传此变量。

## 8. 验证记录与未覆盖

最终包只读复核另发现schema2缺计划请求hash的拒绝门遗漏，现已完成最小修复。先写失败回归：删除计划hash时原代码仍给候选且CLI退出0；随后强制64hex并将原合成夹具改为实际计算的SHA256。新回归覆盖缺失、错误类型、长度63/65、非hex、尾换行、大小写合法摘要及CLI退出2。受影响的22项统计/CLI/原统计集成测试全部通过；未重跑无关HTTP或目标机测试。红/绿命令和原始结果分别在 `evidence/statistics-request-hash-red.txt`、`evidence/statistics-request-hash-green.txt`。此处记录局部验证，最终整包完整运行由VALIDATION另记。

交付包以`evidence/final-package-tests.txt`为最终整合结果：**103项，102通过，1因无JDK跳过，0失败/错误**。此前99项阶段性日志在`final-tests-with-quality.txt`；最末统计请求hash门的red/green单独保留。早期未随本包携带的工作副本日志不作为最终证据。准确环境、命令和边界见根目录VALIDATION.md。

本轮可验证的是CPU逻辑、受控临时文件/Git、真实localhost HTTP/SSE及mock GPU身份分支。**仍未验证**：目标GPU/Strata端到端接入、CUDA编译、真实tokenizer128K边界、实际park/restore、真实Pi、生成Java的Docker集成以及目标机长期资源表现。本容器无JDK，可信Java参考程序检查按原条件skip，不声称通过。

本次没有新增网络依赖、自动安装、模型下载、systemd/驱动/host配置操作、引擎补丁或发布操作。

## 9. 独立质量门与registry资格增量

另有标准库CLI `python -B tools/quality_gate.py --input FILE [--output FILE]`，与 `lab.statistics` 的速度筛选分开。它读取预登记独立task pairs，输出完整四格和保守配对binary成功率非劣性界：`upperCP(b,n,.025)-lowerCP(c,n,.025)`。输入、失败分类、独立单位、数值方法、smoke界限及退出码见 `tools/QUALITY_GATE_README.md`。多seed必须事前聚合，基础设施失败不能用幸存样本挽救结论；预算耗尽是有效任务失败；OOM/crash硬拒绝。退出0只表示该相对质量门通过，不表示绝对质量、速度、安全或部署通过。

`lab.eligibility.qualify`新增读取registry的 `required_probes` 和 `execution_disabled`。后者为true时显式阻断历史/研究方向的自动资格；#4031/#4002纳入cache必须大于0的筛选，仍需加载后内存与机制探针。旧PCIe share说明改为0.007历史值、A0改为locked baseline；CFG-MMAP提示明确当前cfg未实现allocator env allowlist，不能据此直接运行。`tests/test_workspace.py`现在用#2253任务文档验证隔离prepare，便于主包移除无收益#3453旧入口。
