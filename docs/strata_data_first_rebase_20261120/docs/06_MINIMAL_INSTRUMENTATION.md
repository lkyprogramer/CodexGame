# 最小观测改造：沿 Lab P01B 接新版 Strata，不改推理策略

本文件是 **P2 的设计与验收**，不是已实现功能，也不是启动服务器或运行 GPU 的授权。P0 固定身份，P1 先适配现有数据，**P2.0先复用或有限采集L0，只有决策必要字段缺失才逐项实例化P2 hooks**，P3校准所选探针并汇总基线，P4 单因素反事实，P5 至多一个候选正式评估。04 是 source audit，05 是数据契约，08 是 observer，19 是总实施顺序；时间/关联字段为 **PROPOSED 的可选证据附件**，不替换终端或原 Lab schema。字段名若有差异，以 05 的命名为准，不另设第二份事件格式。

**优先实现一个问题：父对话 → 子任务 → 父对话的慢是否由等待、真实前缀搬运／重读或执行路径变化造成？** P01B 已采的窄 host gap 不是新采集目标。没有真实输入、部署指纹、对应 raw、时间/路径边及 observer-off 对照的条件，标 `blocked/unknown`。新文件源锚定 [Strata 64524fb9…][strata]，历史组件锚定 [Lab c5f05b46…][lab]；不是最新安装包与两处 source 完全等价的声明。

## 先定路线，逐段停止

| 采集级别 | 做什么 | 不做什么 | 完成即止的条件 |
|---|---|---|---|
| L0（P1适配，P2.0资格） | `lab.runner`/已有 HTTP 路径读取健康、版本、`/v1/telemetry`、`/metrics`，本地 capture 元信息、计数和 SSE 语义边界，解析原生 stdout/stderr/快照；标可用值及源 | 不动 engine，不开 API request body monitor，不启网络 exporter，不接 live Herdr/prod | 身份已锁、队列和 cache 问题若用确定数据已定位，就不增 hook |
| L1（P2） | 沿 `P01B Adapter`/bounded native trace 同一 bundle，增加 request/leg/round correlation 和少量低成本采样，拆 waiting/prefill/cache/spec/CPU-DMA | 不改 `DraftPolicy`、cache eviction、`PSTAT` schema，不引入自动调参、第二 scheduler/controller | 采集开关通过离线负例；现有时间/数量的缺口得到补齐或明确 unknown |
| L2（P3–P4 条件） | 少量 windows 挂现有 profiler/软件 activity，补 dependency、stream graph 和实际 bytes；已找到了决定更改的一个瓶颈才采 | 不常驻 CUPTI、不开 Ada 上没有的 HES/PDL，不在生产 telemetry 定时扫 GPU trace，不把 profile 数当 benchmark 数 | 无法建立因果依赖、route 被 profiler 改变且无法校准，停止；不进入 P5 |

### L0：合同强制先于采集

1. 沿用 `lab.runner.OwnedServer`/`managed_server`/`evidence_lifecycle` 的启动所有权、resource 与 cleanup gate；沿已存在的 HTTP client/请求审计路径与 `p01b_run.Adapter` 对接。本轮未部署 O0–O6/E0–E4；不存在可直接运行的 `tools/frontier/exploration_control.py`，不能提供它的 CLI。当 tool fixture 不需启动时，用离线 parser/schema/test，不额外建 orchestration 层。
2. 运行身份：实验 run/pair/arm（含是否启 diag）、engine binary SHA-256、archive/manifest build_id（可空但有原因）、实测 source SHA、配置与有效 args/env digest、模型/量化/PLE/draft/profile hashes、OS、driver、CUDA runtime、GPU UUID/SM、PCIe link、CPU/NUMA、host/cgroup/free budget。`INFO` 和端点只证明实际生效字段的一部分；未知不能猜。`v0.2.16` tag 与 `0.1.62` Linux/Windows build 不可互填。
3. 复用已有 SSE 捕获面，显式观测 request start/headers、first positive evidence（忽略 keepalive/comment、role-only frame 和空 `content`）、first reasoning、first visible、first valid tool object、finish/usage 与错误/断链。tool-only 完成不是首可见文本缺失导致失败；但「返回了停词或不合法 tool args」也是与纯 200/结束状态不同的 outcome，使用原质量门。
4. 每个请求同时记录逻辑 `prompt_total`,`prompt_read`,`reused`,`output`、旧 DONE/B(DONE) 实际解析出的 fields、至少一份状态快照接收时间及 `/metrics` scrape。保持部分完成/取消、`NOT_RUN`、缺失值，禁止把未执行预判为零。公开 metrics只读；不为「看一次状态」触发 `/v1/vram`、`/slots/...restore` 或安装/更新。
5. 现有 text logs 不稳定：适配器只解析固定 build 的 known format，用最小正则/strict typed conversions，带 `source`、`scope`、`reason_if_missing`、`observed_at`。断线、不完整行、身份改变、同时间无 ID 的 stdout/err，不做时间邻近模糊 JOIN。保留时序摘要及源 locator/hash；拒绝把 `STRATA_SPEC_TRACE` 原 token Id/prob、`STRATA_PARK_TRACE` 内存地址、原 prompt/secret 日志写到交付的脱敏证据。

## L1.1：一个可跨层但不过度承诺的 lineage

在 **一条已有的 run bundle** 内，采样上游向下游传以下层级；point event 用 monotonic tick + producer 身份，以上游或下游自己的 clock 计算段内 delta。

| 关联层 | 稳定键和范围 | 最小记录 | 失败、并发和时钟处理 |
|---|---|---|---|
| Lab case/agent turn | `run_id/case_id/turn_id`, 同 run 随机的 `session_id`,`parent_turn_id`；不同 run 不追踪真实用户 | caller enqueue/dispatched、语义类别、context bucket、want_tool、private manifest ref；不同子会话各用 opaque ID | 真实外部 harness 不合作就没有其 queue，标 unavailable；已有历史投影不是实际 HTTP ingress。 |
| HTTP request | `server_instance_id/http_request_id`, parent opaque `turn_id` 仅受控 lab request | ingress authenticated parsed/lease/admission、prepare/tokenize/tool bridge、generation entry、生效配置、安全输出的首帧/收尾 | 入口拒绝/超时/无 engine 仍有 request outcome；不要要求它假造 native leg。普通请求不接受/反射任意长 user tag。 |
| Native leg | `engine_process_epoch/worker_id/native_ordinal`, link `http_request_id`; `slot/group` 与 phase 可空并区分 slot-local 和 global | control send/CCD drain、native accept/prepare、first token/finish、`DONE/BDONE`，绝不能用 slot number 单独关联 | SOLO→BGEN→SOLO、MCP/structured retry 分段；`PSTAT` host span/window 不能映射到未标记的 request。Engine-only restart 新 epoch；Python `/v1/telemetry` instance 不变。 |
| Round/work span | `native_leg_key/round_ordinal`；同一批窗另有 `worker_window_id` 与 participating leg keys | actual plan、scope、verify shape、contributor legs/slots、CPU batch id/timestamps、kernel family及 transfer spans；GPU edge 限 L2 | 同一次 batch work 保持 shared scope，不把全量 CPU/I/O bytes 重复归给每个请求；invalid/unknown 与真实 0 分开。 |

**首选迁移方式：** 首先使 P01B 现有 `dep/trace` 管道用新路径，从 `StrataEngine` stdio 会话把明确的 native leg open/close 接进单份 ring；若无无歧义 native ordinal 关联，才做一个 versioned opt-in correlation key。选定一个，不平铺多实现。若新私有 key，服务侧用 local validated 64/128-bit decimal/hex only，engine 只在已协商 capability 的实验构建把该 opaque 值加入 `GEN/GENI/BGEN/BGENI` control frame，解析后从 prompt tokens 剥离；无能力/默认 disabled 一字节不变。借现有 CONTROL queue/`_send_for` 发，不另开 HTTP endpoint。决定在 impl 时先用 stub 做协议 round-trip，不能任由后台 parser 将未识别的行变成 T/ERR，或串进下一请求。

### 挂点：从 Python 进入 C++，仅复用已经存在的边界

| 层 | 必须保留的真实边界 | tag 源锚点与实现限制 |
|---|---|---|
| HTTP ingress、输出与客户端 | 入站认证/已验请求/请求 lease、开始准备、写 frame/flush/断链，客户端自己收 headers/frame 到语义字段 | [server.py `_post` L6966–6990][http]、[OpenAI prepare/openai_chunks/SSE L7436–7489][sse]，Anthropic / Responses 依各自规范找对应 writer；只在实验开时建立 `http_request_id` 并连接到 `cancel` 上既有 request context。tokenize/工具桥/阻塞写不是 GPU 时间。原始 HTTP 字节留私有 evidence 哈希，不作为默认扩展字段。 |
| Service generation | 现有 terminal ID、queue/deadline/FIFO、busy/first/finish 与 outcome | [`Service._run` L5232–5244、L5323–5417][queue]，[first L5461–5470][first]，[history/finalize L5729–5782][finish]。单槽 admitted=fifo 获得（可能尚未 load）；多槽 admitted=waiting registry；而 Python `queue_started` 回调点不等价于 GPU 首次排程。只补数据，不重命名旧事件或 altering sorting。 |
| `StrataEngine` & native | stdout pump、`_send_for`、solo/batch frame、slot claims、replay parser；接 timeout/abort status | [`server.py` L994–1037/L1343–1352/L1870–1946/L2068–2091/L2189–2222/L2405–2434][batchserver]；[`generate.cpp` BGEN rewrite L17383–17404, GEN parsing L17696–17790][genparser]。epoch + ordinal/slot 用原控制线串行边界；stale `BT/BDONE` 按既有筛选，不被 trace 用作生产反向控制。`_parse_done` L1155–1175 和 `_apply_bdone` L1519–1532 仅附加证据，不能改上游输出字段来适配旧 parser。 |
| Host 的 cache/prefill 接续 | 匹配候选、期望 vs 成功 restore、首次 dirty/rewind、native 实际 read start/end、loan/refill | [`generate.cpp` request `r0` L18017–18034、候选 L18399–18560、park/restore L18665–18846、`RESUME` L19011–19023][resume]；[prepare_loan L19375–19526、refill L19275–19358、`prompt_ms` L20423–20442][loan]；[`Prefill::run` layer-major accept/reject/fallback L9018–9055][path]。记录实际选中路径与理由，不以版本号、env、INFO cap 或首次 startup banner 猜。 |
| 独立复制/验证 | `conversation_snapshot_restore[_prefix]` 上游已经作合法性与传输状态判断，context 有各 component；抓 scope/bytes/status，保留首 use | [`conversation_state.cpp` `conversation_checkpoint_restore` L417–461、snapshot save L563–640、restore L770–855][restore] 及 [`conversation_snapshot.cpp` `conversation_kv_restore`/`_prefix` L513–565][restorekv]。已知 copy size 时在真实 CUDA memcpy lane 或 file IO 那一侧计数，不另扫描 device 或 CPU buffer；若只知道 plan/grant bytes，字段命名 `planned_*`，与 actual 分开。 |
| Native verify/commit/draft | 窗口选择→校验 graph/start/end→实际 commit→输出→准备**下一**轮草稿，跨 stage 故障另记 | [`generate.cpp` decision L21455–21591、`ver.run` L21781、裁剪/commit L21822–21896、next draft L21925–21940][round]；[`verify.cpp` profile/commit L2765–2788/L3950–4065][verify]。用实际 selected graph kind、T、context bucket、padding/work rows、actual offered/verified/accepted/committed/emitted。设定 `a` 含义后仅做合同特定公式；不把含 first-fed/bonus 的 commit rows 当模型 output tokens。 |
| Expert/CPU/DMA | `expert_pool_dispatch_multi` plan、source use、pool kickoff→join、doorbell wait、DMA actual submit/completion；最低只记每窗口摘要 | [`expert_source.cpp` L4946–5268 中的 dispatcher、`expert_hit_run` L5473–5490][expert]；[`verify.cpp` L3540–3668/L4900–4953 host wait][verifywait]；[`pool.cpp` worker drain L1166–1190、队列发布/归并 L1250–1384][pool]；[`ple_reader.cpp` L448–589/L608–622][ple]。分开 distinct jobs/route entries，出 critical wait 或 unavailable，不把 CPU thread times 叠加作 wall。PLE table bytes/page-cache 与 expert data、H2D versus GPU across PCIe read 各自口径。 |

### Prefix 研究：四种不同的「复用」不能混算

1. `matched_prefix_tokens` 来自 token/picture 匹配候选；`retained/no-copy`、`rehydrated`、`reread` 分开。`RESUME` 的逻辑 token reuse 可以以 live/slot、D2D、RAM/H2D 或 SSD/validate 获得；来自 `/metrics` 的 reused 不能证明没有搬运。没有稳定 token 身份就保留原生 reused/read，另填 `restore_source/bytes=unknown`。
2. 分辨 cache destination、owned slot/匿名 conversation epoch，logical keep、download/restore waiting、physical H2D/D2H/D2D/stor read 字节。`GDN / QSA KV / sparse index / PLE / draft KV` 类目至少支持未知原因；若一个 snapshot 同时覆盖这些，不能把总字节重复记每个组件。先验收只做 `tier/source+restore_wall+actual read_count` 和已知 bytes，未证明物理 copy 的字段勿推导。
3. 将 park/save/evict/replace/rollback 作为 cache lineage 事件、而非强制操作。重启后 server lifetime totals 保留不代表 state 缓存保留；记录前一次 `engine.gen` 对新一条显式首次读取/恢复方式。节点上报 preemptions=0 不证明 parent 两次没被挤掉。
4. 真实 case 分别标 queue occupied、native cmd wait、resume validation/copy、prefill segment、expert-cache refill、first verify/draft、server first semantic 与客户端 first frame/toolfn。外部 s→客户端 s 与 engine ms 尺度口径独立；不计算「总等待 = client TTFT − 别的 clock 取出的 prompt time」。对于 cached tool-only，首可见 content 通常 `null`；只用首 valid tool 时间做该 SLA。

### ITL：三个可以准确命名的结果，不冒充逐 token

- **Wire/frame ITL**：客户端 `monotonic_ns` 相邻**有效**的同类 SSE frame；剔除 keepalive、role-only 和 usage-only。如果代理 flush/coalesce，不能插值得到内容 token 到达时间。记录 `coalesced` 与 `kind=reasoning|content|tool`。
- **Native token emit gap**：L1 若确实为每个提交 token 均已有独立 `T`/`BT` 行，可按 server 收行 monotonic 差分，仍含进程 pipe buffering 和同轮 burst；需要真实 engine emit 时刻才在已存在 emit loop 打点。绝不以 request decode_ms/len 合成逐 token 记录，也不为统计强制 flush 每 token。
- **Compute gap**：GPU commit window / stream prior dependency 与下一次 producer ready 的专业诊断，只在 L2 且时间/依赖可证时输出；当一个 window emit 多个 token，不给一个平摊的 GPU 单 token 间隔。三种 gap 用各自 P50/p95、coverage 和条件，不共用同名字段。

### Disable、上限与数据债

- L1 开关默认 **disabled**；关时无 lookup/clock/synchronization/allocation/IO 于热路径，不改 GPU graph/profile route，不改原 stdio/inference 对照结果。如 legacy build 有既有 clocks，不改变语义，也不加洗过的假零。可接受 gate 是一个预测稳定分支；trace mode off 不叠加既有 presence flags = 0，按 04 移除它们。
- 沿 P01B 预分配固定结构/ring，按 request/已标所有 leg 或预先确定的 1-in-N window 采，禁止每 expert IO/字符串格式化频繁输出。sample rate、seq、容量、high-water、drop count、clip/context scope 保留。慢盘 writer/关闭时最多只做可控 drain；不为 lossless 在推理线程阻塞或 `cudaDeviceSynchronize`。无 writer 记录不可见时 fail-soft 并报告不可验证，不继续把结果当完整 trace。
- 生命周期用 `run_id` + producer + epoch、strict sequence。重启时重新立文件／collector segment；断流 `gap/dropped=unknown` 若不知道丢多少。native request 已完成但 parent HTTP 取消时仍保留 partial + actual scope；`not_run`、cancel 与 stream 提前终止分别记。JSONL 只存数量/枚举/哈希或 opaque id，日志 schema 上限和 sanitizer 不经 model output 控制。
- Clock `steady_clock` / `perf_counter_ns` / `monotonic_ns` 并不保证跨域共享 epoch；同 host 也要量出 anchor/uncertainty 后才能做 merge。GPU event elapsed 不冒充绝对 wall。配对从 `run identity/arm + cohort` 建立，不从相邻 timestamp 盲合并。只有证实 A→B 是实际依赖时才将 A 放在 critical path，覆盖/不能对齐时写 unknown。

## L2：条件式 CUDA timeline，不调整推理路径

先 L1 给出一条可以否证的假设，例如「短 warm append 的 refill 在 first window 前串行，实际 PCIe waiting 消耗 TTFT」，再抓少量对应该 leg 的 `prefill_loan/refill` 或 verify window。优先现有 PfTimer/Verifier phase marks 和软件 graph-level activity；若不足以区分 launch grouping vs graph node，再在当前 driver/toolkit 验证 Nsight Systems/CUPTI software node trace。用 tag 的 `generate.cpp L19275–19358/L20569–20592`, `prefill.cpp L3773–3818`, `verify.cpp L3137–3202/L3999–4020` 的真实 boundaries 定位。不能按 graph capture node count 当实际执行、不能叠加 busy sum 计算 wall；记录 graph/imageID、stream/context/worker、CUDA API association、device timestamp domain、drop/error。CUDA profiler 之间冲突保持独立，辅助 profile-unaffected/off 配对仍走原 runner。

**4090 Ada 限制**：CUPTI Hardware Event System 只 Blackwell+，Strata 的 PDL gate 要 sm_90+；Ada 只做适用的 events、软件 CUPTI/Nsight Systems。绝不打开虚假的 arch emulation 当真实能力。需额外权限的 perf/profiling 单独授权；无权限就用 clock/duration/device event 局部 evidence，不绕过系统限制。

## Offline fixtures → P3 验收矩阵

| Fixture | 应通过 | 应拒绝/留 unknown |
|---|---|---|
| `telemetry_v1_single.json` / `legacy_404.json` / `status_only.json`（可直接用已有 tests fixtures） | `unknown`, `0`, health、正确显卡 ID 与单位、服务器/引擎版本独立；404 fallback | 401/parse 错误不能 fallback；无 epoch 时禁计算差分；invalid VRAM/counter 不被猜补。 |
| `activity_gaps.jsonl` / `engine_restart.jsonl` | 首次读建立(instance,last_seq)观测锚；启动前历史gap不误判当前掉点；锚后跳seq/重启显式记录 | 相同 epoch/seq 不复算；观测窗口内required gap拒资格；被重派slot旧帧不属于新request；序列不是整个请求DAG。 |
| `mock_sse_tool_reasoning_cancel` | keepalive+headers 非 first content；reasoning/visible/tool/finish 分开；tool-only `visible=null`; 输出失败保留 | 忽略 role-only、同 frame 无法拆 token、完整 JSON 不代表允许名称/参数；client disconnect 转 partial/non-success。 |
| `mock_native_legs` | 0/1 本地 solo、并行 BGEN 转 solo，BSTAT/pstats 拆 scope，optional DONE suffix 正确解析；批共享不重复记账 | 连续两请求 slot 0 或等长度 prompt 不可凭近邻 join；缺 pos/round list 的 logged spec 不作 per-leg attribution。 |
| `mock_cache_restore_ladders` | 同 `reused`，分别 live(D2D 可能 zero)、RAM(H2D)、SSD(more wait)、验证失败重读；实际 copy/size 可对账；state_epoch 不混 | `reused=P` 不能变成 zero H2D；refusal, unexpected rewrite 或 scope 不完整仍保留。 |
| `mock_spec_round_cut_and_async` | windowT、offered/verify/commit/emit 分开，next draft source、tail EOS/error 不污染后续 case；记录 served path 真实选值 | 窗口 shape 和 admission 没有同一个 denominator；no rollback case 的 unknown 不能冒充 0；profiler drop quality 不能 PASS 依赖 gate。 |
| `mock_arm_off_on` | 无 GPU 单测目标：两臂相同的 payload/type/ordering（可排除约定的随机 ID 差异）、新增字段仅 opt-in file，超上限有 `dropped` | 不用 mock 速度说开销过门；产出文件泄漏凭据/真实 prompt/数据路径、deadline 因推理线程写 trace 而变化均拦发布。 |

P2.0的有限L0及P3所选trace off/on都须具备当轮硬件权限与预算；只有申请的受控病例，不默认另加 100K / 128K 多组冷读。L0已够则不建hooks、不重采；源码构建与未确认build的发布制品不可直接做observer配对。所有被测请求的实际输入 token + 输出预算 + 4096 ≤ 131072（exact tokenizer/templating 为准）；声称「128K」不能越窗。保留 P0 实际 resolved drafter/窗口/哈希同一身份。MTP/无 drafter/DFlash2 的旧结果不自动重开；若只是验证协议边界，先适用已有 CPU fixtures，不启 GPU 臂。

Observer 开销按 08：L0 ≤1%、L1 ≤2% 的服务时间 **95% CI 上界**目标，A/A 信号无法给足置信度写 `INSUFFICIENT`；L2 专用 profile 单列不混主 A/B。原 `headroom.py` 收有证据边的 intervals，`paired_stats.py` 和 `quality_gate.py` 只收符合合同的 paired case，模型/stop 等关键哈希一致，区分 cold/warm lifecycle。报告 profile-available 不等于 hardware-tested，observer 下质量或 route 与 off 不等价就调整或撤掉 hook。P4 单改变一个实际变量，带 opportunity upper bound 与受保护指标；对单次噪声、零物理路径关联、causal evidence `UNKNOWN` 的结果停。P5 只在真 gate 后拟做一个候选，不承诺交付时已运行任何 case。

最终 handoff 的 minimal outputs：一份基于已有 run layout 的身份/事件证据包，`join_coverage`/掉点原因，标准运行诊断（01–05 依既有目录），一句结论是否足以进入反事实。**没有实验 hook 也能开始读已存在的监控；没有足够归因与等口径数据就不改引擎。**

[strata]: https://github.com/Niko1221/Strata/tree/64524fb9fc82222ddce554c0643b64f056ec8366
[lab]: https://github.com/lkyprogramer/CodexGame/tree/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab
[http]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/terminal/serve/server.py#L6966-L6990
[sse]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/terminal/serve/server.py#L7436-L7489
[queue]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/terminal/serve/server.py#L5323-L5417
[first]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/terminal/serve/server.py#L5461-L5470
[finish]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/terminal/serve/server.py#L5729-L5782
[batchserver]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/terminal/serve/server.py#L1870-L1946
[genparser]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/program/generate.cpp#L17696-L17790
[resume]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/program/generate.cpp#L18399-L18560
[loan]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/program/generate.cpp#L19330-L19526
[path]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/prefill/prefill.cpp#L9018-L9055
[restore]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/core/conversation_state.cpp#L770-L855
[restorekv]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/core/conversation_snapshot.cpp#L513-L565
[round]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/program/generate.cpp#L21781-L21940
[verify]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/core/verify.cpp#L3950-L4065
[expert]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/core/expert_source.cpp#L4946-L5268
[verifywait]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/core/verify.cpp#L3540-L3668
[pool]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/kernels/cpu/pool.cpp#L1250-L1384
[ple]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/ngram/ple_reader.cpp#L448-L589
