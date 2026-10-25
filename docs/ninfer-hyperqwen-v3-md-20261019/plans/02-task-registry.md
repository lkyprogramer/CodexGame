# 唯一有效任务注册表

下面唯一JSON代码围栏可供Agent解析；2026-10-21已修订现行任务合同并增加baseline-only执行元数据，所有优化/集成任务状态仍PENDING，null的P6提交必须由实证填写。B29测量前置见plans/05–06；H1内新增T07共同sampling资格，未增加phase。B29前置，不是新增可绕过原依赖的phase gate。P0—P6继承；H0—H8取代旧P7—P12。依赖指向phase gate表示必须完成统一组合评审。

```json
{
  "schema": "ninfer.plan.md.v3",
  "as_of": "2026-10-21",
  "delivery": "MARKDOWN_ONLY_DESIGN_NOT_IMPLEMENTATION",
  "source": {
    "B": "44a2c6c3392c9d51e76a895ed97bf1867530d252",
    "O": "e0b05f7cb46adae2787be2ccbe605e1b0c9b3923",
    "U": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
    "H": "30dba4f11b577e1f7699ec0b2947d6fe9d5ea997",
    "qualified_p6_commit": null
  },
  "tasks": [
    {
      "id": "P0-T01",
      "phase": "P0",
      "kind": "task",
      "title": "冻结完整源码与实际合并冲突",
      "owner": "Integrator",
      "depends_on": [],
      "modify": [],
      "create": [
        "evidence/upstream-merge/P0/source-audit-summary.json",
        "docs/upstream-merge/retention-ledger.csv"
      ],
      "interfaces": [
        "输入 data/source-lock.json；输出完整 B→O、B→U、O→U patch / numstat、Git index stages 与定制保留账本。"
      ],
      "tests": [
        "PinMismatch：任一 SHA/共同祖先/11与34计数不符必须停止。",
        "SourceUnchanged：审计前后原工作区 HEAD、index 和未跟踪状态保持不变。"
      ],
      "implementation": [
        "按命令手册在非生产目录获取三个固定对象；额外脏改动独立归档，禁止 reset。",
        "运行 source_audit.py --merge-probe；核对 API 中的43个定制文件与本地完整结果。",
        "按实际 stages 更新 C01—C16；补充额外 rename/delete/add冲突，逐条指定保留、替代或历史证据。",
        "保存 git version 与策略；不得将单文件2冲突外推成整仓结论。"
      ],
      "verify": [
        "python3 \"$PACK/scripts/source_audit.py\" --repo \"$SRC\" --out \"$OUT/P0-source-audit\" --merge-probe"
      ],
      "acceptance": [
        "固定refs和分叉计数匹配；完整冲突清单已产生；43项保留账本无未分类。"
      ],
      "review_focus": [
        "确认没有在 /home/hhtele/ninfer-4090 生产目录执行源码操作；完整文件总量不能来自被截断API。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P0-T01.md"
    },
    {
      "id": "P0-T02",
      "phase": "P0",
      "kind": "task",
      "title": "核对生产三件套、代理配置与显存账本",
      "owner": "Deployment",
      "depends_on": [],
      "modify": [],
      "create": [
        "evidence/upstream-merge/P0/prod-profile.json",
        "evidence/upstream-merge/P0/capacity-ledger.json",
        "evidence/upstream-merge/P0/rollback-manifest.json"
      ],
      "interfaces": [
        "输入当前容器/启动脚本与代理实际配置；输出镜像digest、只读模型、启动argv、缓存目录及 GPU UUID。"
      ],
      "tests": [
        "NoCredentials：归档argv脱敏，不采集完整容器env或HTTP授权头。",
        "SharedCapacity：并发测试占用按共享KV池计算，不能按每lane262144计算。"
      ],
      "implementation": [
        "只读读取当前镜像、启动参数、GPU/驱动、模型SHA与兼容代理配置；把历史source-audit和当前值分列。",
        "保留镜像+参数+旧缓存目录；记录进程是否Git部署、当前是否包含B0/B1。",
        "核对 CUDA13.2构建/运行所需环境能实际加载，禁止复用旧记忆的驱动号作当前结论。",
        "依据 --help 与启动memory summary建立 weights/KV/workspace/graphs/MTP/LoRA/vision/slack账本，确定串行A/B窗口。"
      ],
      "verify": [
        "nvidia-smi --query-gpu=uuid,name,driver_version,memory.total,memory.used --format=csv",
        "docker image inspect \"$PROD_IMAGE\" --format \"{{.Id}}\"",
        "sha256sum \"$MODEL\""
      ],
      "acceptance": [
        "PROD和源码O身份关系明确；回滚三件套可定位；KV总预算与预留真实记录。"
      ],
      "review_focus": [
        "不要导出 docker inspect 的全部环境变量；快照模型文件不得改写。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P0-T02.md"
    },
    {
      "id": "P0-T03",
      "phase": "P0",
      "kind": "task",
      "title": "冻结真实资源、旧 oracle 和 G1 素材",
      "owner": "Frontend QA",
      "depends_on": [
        "P0-T01"
      ],
      "modify": [],
      "create": [
        "evidence/upstream-merge/P0/resources-manifest.json",
        "evidence/upstream-merge/P0/oracle-manifest.json",
        "evidence/upstream-merge/P0/cases-manifest.json"
      ],
      "interfaces": [
        "输入 O、同一.ninfer中的六份前端资源及原G1 cases/toggle；输出带SHA的原始oracle二进制和fixture manifest。"
      ],
      "tests": [
        "LegacyPinned：O构建后的原oracle输出不随candidate变化。",
        "G1Routing：real applied=53、synthetic applied=74；缺素材标BLOCKED，禁止降计数。",
        "TemplateBytes：fixture尾部newline处理与O read_pinned_template一致。"
      ],
      "implementation": [
        "在单独O worktree/build构建 legacy_frontend_oracle、g1_diff 与前端测试。",
        "从当前模型资源提取脚本的实际CLI导出六份资源，记录每份SHA；不得换用HF其他tokenizer。",
        "在用户项目和历史证据目录找回casefile/toggle；缺失时建立独立命名的补充套件但不冒称原G1完成。",
        "分别跑原G1 real/synthetic与20K固定种子变异，保存case_id、input/resource hash与输出；原算法只读。"
      ],
      "verify": [
        "cmake --build \"$BUILD_O\" --parallel 4 --target ninfer_qwen3_8_legacy_frontend_oracle ninfer_qwen3_8_g1_diff",
        "按 docs/08-command-runbook.md §6 对 BUILD_O 运行两种profile；不得只运行candidate。"
      ],
      "acceptance": [
        "原oracle可重放；资源一致；原G1真实执行或有明确阻断，不能在阻断状态通过P0。"
      ],
      "review_focus": [
        "原始业务数据只留用户主机；确认standalone程序不在CTest统计内。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P0-T03.md"
    },
    {
      "id": "P0-T04",
      "phase": "P0",
      "kind": "task",
      "title": "建立 PROD/O 配对基线与冻结质量门槛",
      "owner": "Performance QA",
      "depends_on": [
        "P0-T02",
        "P0-T03"
      ],
      "modify": [],
      "create": [
        "tools/bench/merge/replay_agent.py",
        "tools/bench/merge/normalize_metrics.py",
        "tests/merge/test_replay_and_metrics.py",
        "evidence/upstream-merge/P0/baseline-manifest.json"
      ],
      "interfaces": [
        "新增replay_agent.py：--base-url URL --cases JSONL --out JSONL --run-manifest JSON；按manifest协议回放，密钥仅从环境读取。",
        "新增normalize_metrics.py：--client JSONL --server JSONL --manifest JSON --out JSONL；以request_id关联，输出现有compare_metrics.py规范。"
      ],
      "tests": [
        "ReplayIsolation：拒绝未显式声明sandbox的执行型工具；历史HTTP写入不直放生产。",
        "ProgressIsNotToken：progress不计作首content；reasoning/content/tool分别标记。",
        "MatchedSamples：重复或缺失case_id/repeat、warmup混入、缺失GPU/model/dataset身份均失败。"
      ],
      "implementation": [
        "先用本地fixture/fake HTTP server写失败用例，再实现严格SSE事件采集及server-log normalization。",
        "准备至少20个隔离Java任务和长工具历史，固定编译测试判定器；同时保留128K/192K/248K长上下文用例。",
        "串行测PROD/O，3warmup、关键case至少10个配对样本；CPU四路lane的纯U可后补诊断，不拿它替换生产基线。",
        "在候选结果可见前冻结 docs/05-validation.md 的门槛和profile；记录PROD/O既存差异。"
      ],
      "verify": [
        "python3 -m unittest discover -s tests/merge -p test_replay_and_metrics.py -v",
        "python3 tools/bench/merge/replay_agent.py --base-url \"$TEST_BASE_URL\" --cases \"$REPLAY_CASES\" --out \"$OUT/P0/client.jsonl\" --run-manifest \"$RUN_MANIFEST\""
      ],
      "acceptance": [
        "没有空基线或skip；baseline raw与normalized可对应；门槛先冻结；能力/性能/样本不足分开。"
      ],
      "review_focus": [
        "真实工具循环成本需包含prefill/prepare/queue/restore和客户端总时延，不只记录GPU tok/s。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P0-T04.md"
    },
    {
      "id": "P1-T01",
      "phase": "P1",
      "kind": "task",
      "title": "串行合入上游里程碑（U01—U10）",
      "owner": "Integrator",
      "depends_on": [
        "P0-GATE"
      ],
      "modify": [
        "本阶段 data/upstream-commits.json 列出的所有变化路径",
        "tests/CMakeLists.txt（唯一串行所有者）"
      ],
      "create": [
        "docs/upstream-merge/P1-import-ledger.md"
      ],
      "interfaces": [
        "输入前一合格gate与上游固定提交 94cdb5a975e514935ed4be214ee7f776a8683635；输出带双亲的phase-base和文件责任锁表。"
      ],
      "tests": [
        "UpstreamAncestry：新phase-base同时包含前阶段与本里程碑祖先。",
        "Retention：43项定制账本有对应文件/替代测试，不能静默丢失。"
      ],
      "implementation": [
        "确认上一gate的提交与当前HEAD一致；执行 git merge --no-ff --no-commit 94cdb5a975e514935ed4be214ee7f776a8683635。",
        "按C01—C16以及P0新增冲突逐项解析；保存实际冲突/选择理由。",
        "以新版PromptBoundary/SegmentedEncoding头文件为接口基座，预留B0 work/restart接口；logger核心schema采用本里程碑值而非提前强设24。",
        "只对已review解析commit；允许暂存尚未资格化的phase-base，但不得部署。冻结头文件接口后再分派并行工作树。"
      ],
      "verify": [
        "git merge-base --is-ancestor 94cdb5a975e514935ed4be214ee7f776a8683635 HEAD",
        "git ls-files -u  # 必须为空",
        "git diff HEAD^ HEAD --check"
      ],
      "acceptance": [
        "真实merge ancestry成立；所有冲突已记录解析；定制保留项均有任务负责；phase-base标UNQUALIFIED。"
      ],
      "review_focus": [
        "严禁 -s ours、全仓ours/theirs、squash伪装全上游历史；不得用暂不能编译为理由删除tests。"
      ],
      "rollback": "尚无生产变更；丢弃独立实验分支或用可审计revert，继续从上一已资格化tag开发。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P1-T01.md"
    },
    {
      "id": "P1-T02",
      "phase": "P1",
      "kind": "task",
      "title": "统一 B0 扫描、分段前缀与 B1 memo",
      "owner": "Frontend implementation",
      "depends_on": [
        "P1-T01"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/frontend/tokenizer.cpp",
        "src/targets/qwen3_8/impl/frontend/tokenizer.h",
        "src/targets/qwen3_8/impl/frontend/processor.cpp",
        "src/targets/qwen3_8/impl/frontend/processor.h"
      ],
      "create": [
        "tests/targets/qwen3_8/test_segmented_prefix_merge.cpp"
      ],
      "interfaces": [
        "采用 docs/04-target-design.md 的 PrefixWork、encode_segmented(text, work=nullptr)、prefix(cut, work=nullptr)。",
        "BoundaryEncodingWork保留request-local记账；生产DTO仅boundaries一份权威。"
      ],
      "tests": [
        "EveryByteCut：≤256字节所有切点对照独立完整前缀LCP；覆盖NFC、NUL、invalidUTF8与added-token重叠。",
        "OneEncode：main_encode_calls==1；重复offset memo_hits增长而local_encode_calls不增长。",
        "TraceInvariant：起点(0,0)，只记录selected added token结束；ordinaryEOF不得冒充restart。",
        "LifetimeAndCopy：copy/move tokenizer与并发只读请求无悬空指针；release_ids后不再prefix。"
      ],
      "implementation": [
        "先加入上述会暴露重复编码/旧DTO/显式LCP不匹配的失败测试；借用P1-T03独立oracle接口，未合入时测试分支联合运行。",
        "让唯一B0扫描器同时可选输出ids/segments/restarts，保留added_tokens_顺序与parse_added=false。",
        "prefix仅重编码切点所在片段；processor memo缓存relation和预期invalid_argument，不吞内部logic错误。",
        "采用上游strict/explicit两路判断与有序boundary过滤；工作量字段不进入identity。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --parallel 4 --target ninfer_qwen3_8_segmented_prefix_merge_test  # 本任务新增",
        "ctest --test-dir \"$BUILD\" -R \"ninfer_qwen3_8_(segmented_prefix_merge|tokenizer_work|encoding_restart|boundary_encoding)_test\" --output-on-failure"
      ],
      "acceptance": [
        "所有切点raw IDs/LCP/exact/稳定异常顺序精确一致；无双重主编码；B0及trace观测保留。"
      ],
      "review_focus": [
        "对empty/full prefix、重叠token优先级、uint32检查先后和memo吞异常重点review。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P1-T02.md"
    },
    {
      "id": "P1-T03",
      "phase": "P1",
      "kind": "task",
      "title": "隔离 legacy DTO 并建立独立差分 oracle",
      "owner": "Frontend QA",
      "depends_on": [
        "P1-T01"
      ],
      "modify": [
        "tests/targets/qwen3_8/reference/legacy_encode_rendered_chat.h",
        "tests/targets/qwen3_8/reference/legacy_encode_rendered_chat.cpp",
        "tests/targets/qwen3_8/legacy_oracle_main.cpp",
        "tests/targets/qwen3_8/g1_diff_main.cpp",
        "tests/targets/qwen3_8/test_boundary_encoding.cpp",
        "tests/targets/qwen3_8/bench_boundary_lanes.cpp"
      ],
      "create": [
        "tests/targets/qwen3_8/reference/legacy_boundary_contract.h",
        "tests/targets/qwen3_8/reference/prefix_relation_oracle.h",
        "tests/targets/qwen3_8/test_legacy_contract_isolation.cpp",
        "tools/bench/merge/compare_frontend.py",
        "tests/merge/test_compare_frontend.py"
      ],
      "interfaces": [
        "Legacy DTO复制旧RenderedChat/EncodedChat相关字段到legacy_oracle命名空间；冻结算法函数体。",
        "test-only prefix_relation_oracle(legacyTokenizer,text,cut)通过两次完整encode与LCP返回common_tokens/exact，不调生产prefix。",
        "compare_frontend.py --baseline JSONL --candidate JSONL --out JSON：按case_id/input_sha256/resources_sha256匹配；限定排除impl与明确work字段。"
      ],
      "tests": [
        "NoProductDto：legacy_boundary_contract不include生产processor；旧算法与P0 oracle输出一致。",
        "ComparatorNegative：missing/duplicate case、resource不等、token/error差异必须失败。",
        "ContractSplit：旧implicit字段映射与新explicit边界分别断言，不能拿新规则改旧golden。"
      ],
      "implementation": [
        "先证明当前oracle受生产DTO变化破坏，加入独立DTO和结果对齐器失败用例。",
        "仅允许旧oracle include/type/signature隔离调整；保留tokenizer算法SHA，算法函数体单独审查。",
        "把旧G1输出适配到冻结DTO，新boundary suite独立命名；保留53/74路由。",
        "核实bench_boundary_lanes注册；需要时新增 ninfer_qwen3_8_boundary_lanes_bench，提供 --help和显式资源参数，再测四路编码。"
      ],
      "verify": [
        "python3 -m unittest discover -s tests/merge -p test_compare_frontend.py -v",
        "cmake --build \"$BUILD\" --parallel 4 --target ninfer_qwen3_8_g1_diff ninfer_qwen3_8_legacy_frontend_oracle ninfer_qwen3_8_legacy_contract_isolation_test",
        "按命令手册§6重跑G1；compare_frontend.py逐条对齐，并对照P0不可变二进制输出。"
      ],
      "acceptance": [
        "原G1与新契约差分全部通过；oracle独立；任何缺失或不同资源都失败；四路bench数据可重放。"
      ],
      "review_focus": [
        "不能通过改expected、降低case数、忽略未知字段来“修好”oracle。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P1-T03.md"
    },
    {
      "id": "P1-T04",
      "phase": "P1",
      "kind": "task",
      "title": "恢复 prepare_detail 与三协议请求体观测",
      "owner": "Serving observability",
      "depends_on": [
        "P1-T01"
      ],
      "modify": [
        "include/ninfer/types.h",
        "src/targets/qwen3_8/export/ninfer/targets/qwen3_8/prepared_prompt.h",
        "src/targets/qwen3_8/impl/frontend/frontend.cpp",
        "src/serve/generation_service.h",
        "src/serve/generation_service.cpp",
        "src/serve/request.h",
        "src/serve/http_server.cpp",
        "src/serve/responses_http.cpp",
        "src/serve/request_log.h",
        "src/serve/request_log.cpp",
        "tests/test_request_log.cpp"
      ],
      "create": [
        "tests/merge/fixtures/request-log/fork20.json",
        "tests/merge/fixtures/request-log/upstream20.json"
      ],
      "interfaces": [
        "保留FrontendPrepareTiming/PromptSummary.frontend与六个prepare_detail字段；扩展lkyprogramer.prepare_detail version=1。",
        "body_bytes来自req.body.size；legacy *_chars单位明确UTF8bytes。"
      ],
      "tests": [
        "TimerIdentity：带/不带work观察产生同样tokens、boundaries、identity。",
        "ThreeBodies：Chat/Messages/Responses rawbody准确，previous_response_id展开不增加body_bytes。",
        "MediaUnknown：未拆分tokenize=-1，不算为0或负速率；缺字段日志可读。"
      ],
      "implementation": [
        "添加失败的pure formatter/fixture用例；原logschema与扩展存在性分开。",
        "在新版prepare/run生命周期内移植计时，不覆盖新callbacks/handle/lease。",
        "记录Text各段与媒体unknown；保留旧键便于既有消费者，声明单位和producer扩展。",
        "加request progress观测但不把进度当首生成token；后续上游schema升级按核心版本迁移。"
      ],
      "verify": [
        "ctest --test-dir \"$BUILD\" -R \"ninfer_.*request_log.*test\" --output-on-failure",
        "使用P0 replay脚本对三个native端点和compat proxy校验request_id/size/timing。"
      ],
      "acceptance": [
        "定制11文件timing overlay的可观察能力完整保留；无prompt语义变化；schema碰撞有明确识别。"
      ],
      "review_focus": [
        "chrono范围不包含意外mutex/GPU同步；异步时间不盲目相加；日志不泄漏body和keys。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P1-T04.md"
    },
    {
      "id": "P1-T05",
      "phase": "P1",
      "kind": "task",
      "title": "验证 typed alias 与新缓存边界语义",
      "owner": "Cache implementation",
      "depends_on": [
        "P1-T01"
      ],
      "modify": [
        "src/runtime/cache/continuation_cache.cpp",
        "src/runtime/cache/continuation_cache.h",
        "src/targets/qwen3_8/impl/frontend/chat_template.cpp",
        "src/targets/qwen3_8/impl/frontend/chat_template.h",
        "tests/test_continuation_cache.cpp",
        "tests/targets/qwen3_8/test_frontend.cpp",
        "tests/targets/qwen3_8/test_runtime_mechanisms.cpp"
      ],
      "create": [
        "tests/merge/fixtures/cache-boundaries.json"
      ],
      "interfaces": [
        "只使用PromptBoundary(kind,depth,publish)和typed alias；模板层byte hints对接P1-T02输出。"
      ],
      "tests": [
        "AliasAtomic：payload准入失败不发布alias；同payload frontier/session不双份驻留。",
        "ExplicitBoundary：非对齐cut回退LCP；去0/重叠；不越rewrite frontier。",
        "RoutingIndependent：关闭implicit发布不等于关闭session routing；改system/tools/adapter不误命中。"
      ],
      "implementation": [
        "先补synthetic模板/alias失败用例，再核对上游对应状态转移。",
        "保留新显式断点计数限制与协议解析，按实际源码规范测试而非猜值。",
        "避免恢复旧stable_prefix单字段；模板语义旧兼容仅在test适配器处理。",
        "使用P0长工具历史验证端到端边界，不只比较渲染字符串长度。"
      ],
      "verify": [
        "ctest --test-dir \"$BUILD\" -R \"ninfer_(continuation_cache|qwen3_8_frontend|qwen3_8_runtime_mechanisms)_test\" --output-on-failure"
      ],
      "acceptance": [
        "alias/payload原子性和implicit/explicit/routing三维测试通过；新旧前端契约差异有对应测试。"
      ],
      "review_focus": [
        "新新增文件即使无文本冲突也需检查生产DTO依赖；本任务不改T04HTTPhandlers。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P1-T05.md"
    },
    {
      "id": "P1-T06",
      "phase": "P1",
      "kind": "task",
      "title": "验证 repetition guard、轮级故障与进度事件",
      "owner": "Runtime QA",
      "depends_on": [
        "P1-T01"
      ],
      "modify": [
        "src/runtime/generation/repetition_guard.h",
        "src/runtime/generation/row_commit.h",
        "src/runtime/engine/concurrent_executor.h",
        "tests/test_repetition_guard.cpp",
        "tests/test_row_commit.cpp",
        "tests/ai-sdk-openai/contract.test.mjs"
      ],
      "create": [
        "tests/merge/fixtures/round-fault.json"
      ],
      "interfaces": [
        "采用上游committed-token guard与round fault作用域；进度回调由T04保持接口。"
      ],
      "tests": [
        "DraftNotCommitted：拒绝draft不计入重复周期；guard触发finish reason可序列化。",
        "FaultScope：本轮受影响lane失败，排队请求可继续；非round异常不能被错误吞掉。",
        "ProgressOnly：长prefill期间有合法进度、不伪造content/tool token。"
      ],
      "implementation": [
        "在独立测试进程构造fault/周期fixture，不杀生产进程。",
        "补缺失状态组合断言并修复移植引入的问题；保持上游guard语义不改业务默认参数。",
        "对stable benchmark可显式禁用guard以隔离影响，但生产qualification还要测默认guard。"
      ],
      "verify": [
        "ctest --test-dir \"$BUILD\" -R \"ninfer_(repetition_guard|row_commit)_test\" --output-on-failure",
        "对Responses replay运行progress-only断言，并核对terminal event只出现一次。"
      ],
      "acceptance": [
        "局部失败可恢复，无永久容量丢失；循环检测不依赖未提交draft；progress不改变usage。"
      ],
      "review_focus": [
        "只单测guard不够，需combined phase从HTTP到runtime终态检验。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P1-T06.md"
    },
    {
      "id": "P2-T01",
      "phase": "P2",
      "kind": "task",
      "title": "串行合入上游里程碑（U11）",
      "owner": "Integrator",
      "depends_on": [
        "P1-GATE"
      ],
      "modify": [
        "本阶段 data/upstream-commits.json 列出的所有变化路径",
        "tests/CMakeLists.txt（唯一串行所有者）"
      ],
      "create": [
        "docs/upstream-merge/P2-import-ledger.md"
      ],
      "interfaces": [
        "输入前一合格gate与上游固定提交 4d3366e5b9a959627a6db1f0eb36932be0482def；输出带双亲的phase-base和文件责任锁表。"
      ],
      "tests": [
        "UpstreamAncestry：新phase-base同时包含前阶段与本里程碑祖先。",
        "Retention：43项定制账本有对应文件/替代测试，不能静默丢失。"
      ],
      "implementation": [
        "确认上一gate的提交与当前HEAD一致；执行 git merge --no-ff --no-commit 4d3366e5b9a959627a6db1f0eb36932be0482def。",
        "按C01—C16以及P0新增冲突逐项解析；保存实际冲突/选择理由。",
        "接受异步export的状态、stream和lane所有权变化，不用旧同步函数恢复定制timing。",
        "只对已review解析commit；允许暂存尚未资格化的phase-base，但不得部署。冻结头文件接口后再分派并行工作树。"
      ],
      "verify": [
        "git merge-base --is-ancestor 4d3366e5b9a959627a6db1f0eb36932be0482def HEAD",
        "git ls-files -u  # 必须为空",
        "git diff HEAD^ HEAD --check"
      ],
      "acceptance": [
        "真实merge ancestry成立；所有冲突已记录解析；定制保留项均有任务负责；phase-base标UNQUALIFIED。"
      ],
      "review_focus": [
        "严禁 -s ours、全仓ours/theirs、squash伪装全上游历史；不得用暂不能编译为理由删除tests。"
      ],
      "rollback": "尚无生产变更；丢弃独立实验分支或用可审计revert，继续从上一已资格化tag开发。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P2-T01.md"
    },
    {
      "id": "P2-T02",
      "phase": "P2",
      "kind": "task",
      "title": "补齐异步 export 的 fence 与生命周期回归",
      "owner": "Runtime implementation",
      "depends_on": [
        "P2-T01"
      ],
      "modify": [
        "src/runtime/engine/concurrent_executor.h",
        "src/targets/qwen3_8/impl/runtime/api_impl.h",
        "src/targets/qwen3_8/impl/runtime/program.h",
        "src/targets/qwen3_8/impl/runtime/program_impl.h",
        "src/targets/qwen3_8/impl/runtime/continuation_image.h",
        "tests/test_continuation_cache.cpp",
        "tests/targets/qwen3_8/test_runtime_mechanisms.cpp"
      ],
      "create": [
        "tests/merge/test_async_export_lifecycle.cpp"
      ],
      "interfaces": [
        "遵守上游export job/event/lane持有契约；不发明第二套cache线程或unbounded job queue。"
      ],
      "tests": [
        "InFlightMutation：export中reset/restore/evict/cancel不得提前改写buffer。",
        "PublicationAfterComplete：copy失败/取消后无半成品alias；job失败有可见状态。",
        "Drain：shutdown等待或明确取消所有job，未完成source ownership不丢。"
      ],
      "implementation": [
        "引入测试专用可控延迟/failure注入点，默认编译生产路径无额外同步。",
        "验证各mutation对fence的等待与lane选择；按上游settled-lane policy修复适配。",
        "将GPU事件与source生命周期检查合并到真实artifact回归，避免mock全通过却实际越界。"
      ],
      "verify": [
        "ctest --test-dir \"$BUILD\" -R \"ninfer_(continuation_cache|qwen3_8_runtime_mechanisms|async_export_lifecycle)_test\" --output-on-failure  # lifecycle为新增target"
      ],
      "acceptance": [
        "故障/取消/退出后缓存与容量一致；实际GPU事件完成前无source reuse；无悬空访问。"
      ],
      "review_focus": [
        "lane reset和CUDA Graph使用相同workspace时，导出fence是否仍覆盖所有读者？"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P2-T02.md"
    },
    {
      "id": "P2-T03",
      "phase": "P2",
      "kind": "task",
      "title": "对齐异步阶段耗时和导出指标",
      "owner": "Observability QA",
      "depends_on": [
        "P2-T01"
      ],
      "modify": [
        "src/serve/request_log.cpp",
        "src/serve/serve_metrics.cpp",
        "tests/test_request_log.cpp",
        "tools/bench/merge/normalize_metrics.py"
      ],
      "create": [
        "tests/merge/fixtures/async-export-log.json"
      ],
      "interfaces": [
        "prepare_detail含义不变；export总work、同步publish、queue/restore分别读取，不相互替代。"
      ],
      "tests": [
        "AsyncAccounting：publish下降时导出工作仍可追踪；两request重叠不按总时长平摊。",
        "MissingMetric：阶段缺字段返回unavailable，禁止0补值制造性能收益。"
      ],
      "implementation": [
        "加异步fixture负例并扩展normalizer schema适配。",
        "复查新增采样不在execution mutex内读取同步设备状态。",
        "记录请求、lane、digest与event进度，在性能报告中解释工作重叠。"
      ],
      "verify": [
        "python3 -m unittest discover -s tests/merge -p test_replay_and_metrics.py -v",
        "ctest --test-dir \"$BUILD\" -R \"ninfer_.*request_log.*test\" --output-on-failure"
      ],
      "acceptance": [
        "同一请求导出/恢复/prepare可追溯；无missing→0；归一前后的raw引用完整。"
      ],
      "review_focus": [
        "是否把host enqueue时间误标GPU completed时间？"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P2-T03.md"
    },
    {
      "id": "P2-T04",
      "phase": "P2",
      "kind": "task",
      "title": "实机混合热冷流量与导出压力验收",
      "owner": "GPU QA",
      "depends_on": [
        "P2-T02",
        "P2-T03"
      ],
      "modify": [
        "tools/bench/merge/replay_agent.py"
      ],
      "create": [
        "evidence/upstream-merge/P2/async-stress-manifest.json"
      ],
      "interfaces": [
        "输入P0 frozencases、P2候选、同codec/profile；输出A/B/A与cache lifecycle事件。"
      ],
      "tests": [
        "LongHotCold：热长会话加入冷请求后，合法复用不失效，队列能排空。",
        "ResourceRecovered：请求取消、cache驱逐后capacity回归稳定；没有持续正增长的不可归还字节。"
      ],
      "implementation": [
        "C=1与C=3在共享KV预算内实测，缓存目录独立。",
        "组合append/reminder rewrite/evict/cancel/restore与L2/L3发布。",
        "测prepare/TTFT p50/p90、client tok/s、export字节和总work，比较P1阶段。",
        "失败先按trace定位fence/identity/容量，禁止靠扩大上限掩盖。"
      ],
      "verify": [
        "python3 tools/bench/merge/replay_agent.py --base-url \"$TEST_BASE_URL\" --cases \"$ASYNC_CASES\" --out \"$OUT/P2/client.jsonl\" --run-manifest \"$RUN_MANIFEST\"",
        "python3 \"$PACK/scripts/compare_metrics.py\" --baseline \"$P1_NORMALIZED\" --candidate \"$P2_NORMALIZED\" --out \"$OUT/P2/performance.json\""
      ],
      "acceptance": [
        "长上下文正确性与性能门槛通过；fault/cancel无持续资源泄漏；raw GPU信息齐全。"
      ],
      "review_focus": [
        "本阶段不改KV codec，避免把codec差异归因于异步调度。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P2-T04.md"
    },
    {
      "id": "P3-T01",
      "phase": "P3",
      "kind": "task",
      "title": "串行合入上游里程碑（U12—U17）",
      "owner": "Integrator",
      "depends_on": [
        "P2-GATE"
      ],
      "modify": [
        "本阶段 data/upstream-commits.json 列出的所有变化路径",
        "tests/CMakeLists.txt（唯一串行所有者）"
      ],
      "create": [
        "docs/upstream-merge/P3-import-ledger.md"
      ],
      "interfaces": [
        "输入前一合格gate与上游固定提交 f4089901fa17b83ecbb21bd2bde17bf614c3bf03；输出带双亲的phase-base和文件责任锁表。"
      ],
      "tests": [
        "UpstreamAncestry：新phase-base同时包含前阶段与本里程碑祖先。",
        "Retention：43项定制账本有对应文件/替代测试，不能静默丢失。"
      ],
      "implementation": [
        "确认上一gate的提交与当前HEAD一致；执行 git merge --no-ff --no-commit f4089901fa17b83ecbb21bd2bde17bf614c3bf03。",
        "按C01—C16以及P0新增冲突逐项解析；保存实际冲突/选择理由。",
        "完整带入small-T kernel/plan/CMake删除项与增量工具协议；上游核心schema20不可覆盖定制prepare_detail。",
        "只对已review解析commit；允许暂存尚未资格化的phase-base，但不得部署。冻结头文件接口后再分派并行工作树。"
      ],
      "verify": [
        "git merge-base --is-ancestor f4089901fa17b83ecbb21bd2bde17bf614c3bf03 HEAD",
        "git ls-files -u  # 必须为空",
        "git diff HEAD^ HEAD --check"
      ],
      "acceptance": [
        "真实merge ancestry成立；所有冲突已记录解析；定制保留项均有任务负责；phase-base标UNQUALIFIED。"
      ],
      "review_focus": [
        "严禁 -s ours、全仓ours/theirs、squash伪装全上游历史；不得用暂不能编译为理由删除tests。"
      ],
      "rollback": "尚无生产变更；丢弃独立实验分支或用可审计revert，继续从上一已资格化tag开发。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P3-T01.md"
    },
    {
      "id": "P3-T02",
      "phase": "P3",
      "kind": "task",
      "title": "整体验证 small-T MMA 与算子路由",
      "owner": "CUDA implementation",
      "depends_on": [
        "P3-T01"
      ],
      "modify": [
        "src/ops/common/small_t_rowsplit_mma.cuh",
        "src/ops/common/small_t_rowsplit_mma.h",
        "src/ops/linear_add/q5/q5_linear_add_plan.cpp",
        "src/ops/linear_swiglu/q4/q4_linear_swiglu_plan.cpp",
        "src/ops/attn_input_proj/q4_q5/q4_q5_attn_input_plan.cpp",
        "src/ops/gdn_input_proj/q4_q5/q4_q5_gdn_input_plan.cpp",
        "tests/ops/test_attn_input_proj.cpp",
        "tests/ops/test_gdn_input_proj.cpp",
        "tests/ops/test_gdn_input_proj_conv_snapshot.cpp"
      ],
      "create": [
        "evidence/upstream-merge/P3/small-t-route-matrix.json"
      ],
      "interfaces": [
        "保持上游语义Op接口和sharedrowsplit; 准确列出各Q4/Q5的plan、kernel和workspace。"
      ],
      "tests": [
        "SmallTTails：T=1,2,3,4,8,12,16,24,32,33跨路由对独立数值oracle。",
        "GraphReplay：capture/replay不同活跃row数不越workspace；q4/q5/w8有效路由不可skip。",
        "DeletedRoute：旧small_t/SIMT/conv_snapshot源已删时CMake/plan无悬空引用。"
      ],
      "implementation": [
        "先加入路由边界/尾块回归，再核查upstream算子实现是否完整进入编译。",
        "把kernel、plan、public op、bench/测试成套处理；CMake变更交Integrator串行apply。",
        "记录独立oracle容差来源和maxerror；不以最终模型文本看似合理代替数值验证。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --parallel 4",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$OUT/P3/ctest-inventory.json\"",
        "按inventory运行linear_add/linear_swiglu/attn_input_proj/gdn_input_proj目标并导出JUnit；精确required名单由本任务freeze。"
      ],
      "acceptance": [
        "全部路由/尾块/graph数值通过；workspace符合预算；删除项和新源编译成套一致。"
      ],
      "review_focus": [
        "不要恢复被删除的独立GDN fused snapshot排程；算子快速路径不能改变请求语义。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P3-T02.md"
    },
    {
      "id": "P3-T03",
      "phase": "P3",
      "kind": "task",
      "title": "贯通三协议增量工具调用与历史存储",
      "owner": "Serving implementation",
      "depends_on": [
        "P3-T01"
      ],
      "modify": [
        "src/serve/tool_call_parser.cpp",
        "src/serve/tool_call_parser.h",
        "src/serve/generation_service.cpp",
        "src/serve/generation_service.h",
        "src/serve/http_server.cpp",
        "src/serve/anthropic_schema.cpp",
        "src/serve/openai_schema.cpp",
        "src/serve/responses_schema.cpp",
        "src/serve/responses_http.cpp",
        "tests/test_tool_call_parser.cpp",
        "tests/test_anthropic_schema.cpp",
        "tests/test_openai_schema.cpp",
        "tests/test_responses_schema.cpp",
        "tests/ai-sdk-openai/contract.test.mjs"
      ],
      "create": [
        "tests/merge/fixtures/tool-stream-cases.jsonl"
      ],
      "interfaces": [
        "StreamSink on_tool_call_begin/arguments/end与ToolParameterKinds；终态Complete/Incomplete和discarded_bytes遵上游。"
      ],
      "tests": [
        "DeltaJoin：多chunk参数连接等于nonstream完整JSON；字符串看似JSON仍保留string类型。",
        "IncompleteNotExecutable：截断/cancel/断连后无tool end，历史不保存成完整可执行调用。",
        "ThinkRecovery：未闭合think后的工具调用正确分类；混合普通文本与工具只发一次。",
        "ThreeProtocols：native与compatproxy两层均通过schema和tool replay。"
      ],
      "implementation": [
        "先把负例做成纯parser/schema fixture，再测真实SSE。",
        "移植新callbacks/生命周期但保留全部prepare timers/body_bytes。",
        "按新schema20的含义更新日志core；producer扩展仍保留，不回退旧parser的streamed_content_bytes。",
        "更新隔离Agent执行器，仅完整调用才允许落地测试工具。"
      ],
      "verify": [
        "ctest --test-dir \"$BUILD\" -R \"ninfer_(tool_call_parser|anthropic_schema|openai_schema|responses_schema)_test\" --output-on-failure",
        "使用P0 replay工具运行tool-stream-cases及历史回传，验证完整调用数量与编译测试结果。"
      ],
      "acceptance": [
        "3协议流式/非流式等价；所有不完整工具不可执行；timing定制保留；history不污染。"
      ],
      "review_focus": [
        "字符切片与JSON escaping跨chunk必须正确；别把progress/工具参数计为普通content。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P3-T03.md"
    },
    {
      "id": "P3-T04",
      "phase": "P3",
      "kind": "task",
      "title": "固定测试注册与 skip77 策略",
      "owner": "Build QA",
      "depends_on": [
        "P3-T01"
      ],
      "modify": [
        "tests/ops/linear_swiglu/test_nvfp4.cpp",
        "tests/ops/linear_swiglu/test_q4_a16.cpp",
        "tests/ops/linear_swiglu/test_q4_a8.cpp",
        "tests/ops/linear_swiglu/test_w8_a16.cpp",
        "tests/CMakeLists.txt（仅提交注册片段）",
        "tools/bench/run_admission_latency.py",
        "tools/bench/run_decode_scaling.py",
        "tools/bench/run_session_swarm.py"
      ],
      "create": [
        "evidence/upstream-merge/P3/required-tests.json"
      ],
      "interfaces": [
        "CTest inventory是目标存在性权威；必测q4/q5/w8/27B执行必须不skip；可选NVFP4明确未资格。"
      ],
      "tests": [
        "SkipIsNotPass：无设备返回77而非1，但4090资格中required77使gate失败。",
        "TargetUnion：fork standalone/G1与所有上游新tests都出现在构建图，不能只数ctest总数。"
      ],
      "implementation": [
        "P0确认三份linear_swiglu实际路径，若名字与文件账本不同按真实路径改计划而非创建错名文件。",
        "保留fork关于profile skip的修改，核对上游新tests返回码与CTest属性。",
        "生成required名单；记录新增benchdriver的实际 --help/参数，不猜运行签名。",
        "在缺GPU和真GPU两种环境分别验证返回码意义；35B暂不强加未合入上游修复前的运行资格。"
      ],
      "verify": [
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$OUT/P3/ctest-inventory.json\"",
        "python3 \"$PACK/scripts/check_junit.py\" \"$OUT/P3/ops.junit.xml\" --require \"ninfer_.*(linear|swiglu).*\""
      ],
      "acceptance": [
        "无设备skip行为正确；GPU必测非skip；required目标无missing；standalone程序单独列出。"
      ],
      "review_focus": [
        "regex不能误匹配导致漏掉重要路径；最终必须展开并freeze精确required名单。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P3-T04.md"
    },
    {
      "id": "P3-T05",
      "phase": "P3",
      "kind": "task",
      "title": "验证 small-T 与工具流的端到端收益",
      "owner": "Performance QA",
      "depends_on": [
        "P3-T02",
        "P3-T03",
        "P3-T04"
      ],
      "modify": [],
      "create": [
        "evidence/upstream-merge/P3/performance-manifest.json"
      ],
      "interfaces": [
        "输入P2同codec/profile基线；输出small-T微基准、MTP轮与客户端Java任务配对报告。"
      ],
      "tests": [
        "AcceptanceNotAssumed：固定draft=3，记录实际accepted/rounds，而非只看理论window。",
        "LongStillGood：128K/192K/248K热增量TTFT与decode满足冻结门槛。"
      ],
      "implementation": [
        "分开测single-request/MTP和C=3混合工具会话；不把batchaggregate tok/s说成单用户速率。",
        "在model/clock/cache配置一致时对P2/P3做A/B/A。",
        "若short-T提升而长期工具循环无改善，保留实测结论；不得把上游headline复制成本机收益。"
      ],
      "verify": [
        "python3 \"$PACK/scripts/compare_metrics.py\" --baseline \"$P2_NORMALIZED\" --candidate \"$P3_NORMALIZED\" --out \"$OUT/P3/performance.json\"",
        "运行冻结Java任务判定器，产出compile/test/tool正确率与每case原始轨迹。"
      ],
      "acceptance": [
        "算子与业务双层正确；长上下文不回退；small-T收益或无收益均有可信报告。"
      ],
      "review_focus": [
        "P3合格可作为后续KV迁移失败时的中间发布候选，但不是最终U全量上线。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P3-T05.md"
    },
    {
      "id": "P4-T01",
      "phase": "P4",
      "kind": "task",
      "title": "串行合入上游里程碑（U18—U27）",
      "owner": "Integrator",
      "depends_on": [
        "P3-GATE"
      ],
      "modify": [
        "本阶段 data/upstream-commits.json 列出的所有变化路径",
        "tests/CMakeLists.txt（唯一串行所有者）"
      ],
      "create": [
        "docs/upstream-merge/P4-import-ledger.md"
      ],
      "interfaces": [
        "输入前一合格gate与上游固定提交 29d13e3d99491ed82e7be4edc801d92a59643cea；输出带双亲的phase-base和文件责任锁表。"
      ],
      "tests": [
        "UpstreamAncestry：新phase-base同时包含前阶段与本里程碑祖先。",
        "Retention：43项定制账本有对应文件/替代测试，不能静默丢失。"
      ],
      "implementation": [
        "确认上一gate的提交与当前HEAD一致；执行 git merge --no-ff --no-commit 29d13e3d99491ed82e7be4edc801d92a59643cea。",
        "按C01—C16以及P0新增冲突逐项解析；保存实际冲突/选择理由。",
        "一次带入决策runtime+midrise codec+35B修复+telemetry/UTF8；源码依赖成套，不先单独cherry-pick某个kernel上线。",
        "只对已review解析commit；允许暂存尚未资格化的phase-base，但不得部署。冻结头文件接口后再分派并行工作树。"
      ],
      "verify": [
        "git merge-base --is-ancestor 29d13e3d99491ed82e7be4edc801d92a59643cea HEAD",
        "git ls-files -u  # 必须为空",
        "git diff HEAD^ HEAD --check"
      ],
      "acceptance": [
        "真实merge ancestry成立；所有冲突已记录解析；定制保留项均有任务负责；phase-base标UNQUALIFIED。"
      ],
      "review_focus": [
        "严禁 -s ours、全仓ours/theirs、squash伪装全上游历史；不得用暂不能编译为理由删除tests。"
      ],
      "rollback": "尚无生产变更；丢弃独立实验分支或用可审计revert，继续从上一已资格化tag开发。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P4-T01.md"
    },
    {
      "id": "P4-T02",
      "phase": "P4",
      "kind": "task",
      "title": "迁移 KV codec、序列化版本与缓存隔离",
      "owner": "CUDA / cache implementation",
      "depends_on": [
        "P4-T01"
      ],
      "modify": [
        "src/ops/kernel/gqa_attention_kv_encode.cuh",
        "src/ops/kernel/gqa_attention_kv_quant.cuh",
        "src/ops/kernel/gqa_attention_decode.cuh",
        "src/ops/kernel/gqa_attention_segmented.cuh",
        "src/ops/wrapper/gqa_attention.cpp",
        "src/core/paged_kv_cache.h",
        "src/targets/qwen3_8/impl/runtime/continuation_image.h",
        "src/targets/qwen3_8/impl/runtime/session_snapshot_impl.h",
        "tests/ops/test_gqa_attention.cpp"
      ],
      "create": [
        "tests/merge/fixtures/cache-format-versions.json",
        "evidence/upstream-merge/P4/codec-migration.json"
      ],
      "interfaces": [
        "新rk4v4统一midrise；rk4v4-e8退出支持不加静默alias；rk2v4-e8 root-key flag与4bitV同步。",
        "在该里程碑writer/reader核对snapshot5、targetimage4；更外层格式单独记录。"
      ],
      "tests": [
        "CodecBytes：A1/A2/A3 encoder字节按独立参考；全零h=0/饱和/FP16rounding有用例。",
        "OwnColumns：A4 readonly prefix、BF16 own K/V、page/split边界与causal mask正确。",
        "RejectOldPayload：旧版本/codec/flag不匹配拒绝或cache miss，不按新格式读旧字节。",
        "OldOptionRejected：rk4v4-e8明确不可用，错误不被自动转成rk4v4。"
      ],
      "implementation": [
        "先运行新增byte/version负例，再核对统一encoder各appendsite与inverseV路径全部一致。",
        "新cache路径/namespace在manifest固定，不迁移/覆盖旧payload。",
        "用已有numericoracle测everycodec的支持路径；不按旧E8greedy输出构造假bitwise门槛。",
        "把codec差异声明为唯一允许profile变化；更新startupoption/Docker例子与回滚参数账本。"
      ],
      "verify": [
        "ctest --test-dir \"$BUILD\" -R \"ninfer_(gqa_attention|kv_cache|qwen3_8_runtime_mechanisms)_test\" --output-on-failure",
        "在测试实例上验证旧--kv-dtype被拒绝，记录stderr及退出码。"
      ],
      "acceptance": [
        "codec/math/版本均通过；旧payload不误读；新目录可冷启动；旧镜像目录未变。"
      ],
      "review_focus": [
        "新旧rk4v4同名也可能格式不同；禁止只比较字符串名作为cache compatibility。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P4-T02.md"
    },
    {
      "id": "P4-T03",
      "phase": "P4",
      "kind": "task",
      "title": "整合决策 runtime、LoRA 和分支隔离",
      "owner": "Decision implementation",
      "depends_on": [
        "P4-T01"
      ],
      "modify": [
        "src/product/systemone/request.cpp",
        "src/product/systemone/render.cpp",
        "src/product/systemone/answers.cpp",
        "src/targets/qwen3_8/impl/frontend/decision_template.cpp",
        "src/targets/qwen3_8/impl/runtime/decision_impl.h",
        "src/targets/qwen3_8_27b/impl/load/lora_bindings.cpp",
        "src/targets/qwen3_8_27b/impl/variant.cpp",
        "tests/targets/qwen3_8_27b/test_engine_decision_real.cpp",
        "tests/ops/test_pointer_head.cpp"
      ],
      "create": [
        "evidence/upstream-merge/P4/decision-contract-matrix.json"
      ],
      "interfaces": [
        "决策为共享Engine中的prefill-only state+questions；pointerhead读出，不能走sampling/decode/MTP。",
        "Tokenizer::token_id保持added-token优先再basevocab，缺失token抛明确错误。"
      ],
      "tests": [
        "BranchIsolation：question只续接state、不读另一question结果；swap/permute顺序符合契约。",
        "AdapterKind：生成拒绝decisionadapter，base与不同adaptercache不混用。",
        "NoDraft：decision请求spec rounds/decode均不伪增；statepluslongestbranch满足容量。",
        "Reference：有真实adapter时对冻结reference测每题概率；无adapter标该资格BLOCKED，不捏造概率。"
      ],
      "implementation": [
        "先加结构/layout/adapter负例，并导出真实env/CLI要求。",
        "保持上游prefill phase A16、pointerhead、state snapshots/LoRA contract，不混入旧生成DTO。",
        "验证27B-only/35B-only/both配置构建，包含U21的完整修复。",
        "代码/合成和numericop资格必须完成；真实decision资格由P4-T06明确启用或留BLOCKED。"
      ],
      "verify": [
        "ctest --test-dir \"$BUILD\" -R \"ninfer_.*(pointer_head|decision|systemone).*test\" --output-on-failure",
        "分别用独立build目录构建27B-only、35B-only、both并保存CMakeCache与build日志。"
      ],
      "acceptance": [
        "代码和synthetic/layout/numericops必测通过；adapter缺失不阻塞chat资格但明确禁止宣称decision业务合格。"
      ],
      "review_focus": [
        "结构支持图片不等于adapter图像任务精度；接口不承诺外部模型相同输出。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P4-T03.md"
    },
    {
      "id": "P4-T04",
      "phase": "P4",
      "kind": "task",
      "title": "迁移 schema22、无饥饿遥测和双系统观测",
      "owner": "Telemetry implementation",
      "depends_on": [
        "P4-T01"
      ],
      "modify": [
        "src/serve/request_log.cpp",
        "src/serve/request_log.h",
        "src/serve/serve_metrics.cpp",
        "src/serve/serve_metrics.h",
        "apps/web/src/lib/records.ts",
        "apps/web/src/lib/derive.ts",
        "apps/web/src/lib/derive.test.ts",
        "apps/web/src/panels/SystemOnePanel.tsx",
        "tests/test_request_log.cpp"
      ],
      "create": [
        "tests/merge/fixtures/request-log/schema22.json"
      ],
      "interfaces": [
        "core schema22按U22；fork计时扩展仍v1；不可用指标null/unavailable而非0。"
      ],
      "tests": [
        "TelemetryAvailable：长prefill/decision期间health/telemetry不因execution mutex长期阻塞。",
        "AdapterSnapshot：pool/slabs驻留和actualmodel类型同server_start/telemetry。",
        "HistoricalLog：fork20/upstream20/22fixture都能显示正确单位/缺值。"
      ],
      "implementation": [
        "先加logfixture/derive单测，保留新的export/energy/decision字段。",
        "采用上游worker发布的快照，不从serve线程重新取执行锁进行同步设备采样。",
        "更新customtimer显示与normalizer；混跑只统计实际client速度和尾延迟。"
      ],
      "verify": [
        "ctest --test-dir \"$BUILD\" -R \"ninfer_.*request_log.*test\" --output-on-failure",
        "cd \"$INTEGRATE/apps/web\" && bun test && bun run typecheck"
      ],
      "acceptance": [
        "实时与历史日志一致；新增决策信息不破坏纯Chat；真实负载监控响应可追溯。"
      ],
      "review_focus": [
        "不同core schema不能用相同数字误认producer；计数snapshot不得残留已结束请求。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P4-T04.md"
    },
    {
      "id": "P4-T05",
      "phase": "P4",
      "kind": "task",
      "title": "隔离输出 UTF-8 修复与输入严格校验",
      "owner": "Frontend output QA",
      "depends_on": [
        "P4-T01"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/frontend/frontend.cpp",
        "tests/targets/qwen3_8/test_frontend.cpp",
        "tests/merge/fixtures/tool-stream-cases.jsonl"
      ],
      "create": [
        "tests/merge/fixtures/output-utf8-cases.json"
      ],
      "interfaces": [
        "只生成输出增量decoder允许replacement；input tokenizer验证策略保持O。"
      ],
      "tests": [
        "SplitCodePoint：合法中文/emoji跨token及SSEchunk最终完整。",
        "MalformedOutput：非法序列按上游规则替换U+FFFD，flush结束不遗留字节。",
        "InputStillStrict：同样非法UTF8作为输入仍维持既有异常，不因output修复放松。",
        "ToolUtf8：参数chunk修复不重复emit/破坏完整JSON。"
      ],
      "implementation": [
        "先建立输入/输出成对负例，保持旧tokenizeroracle不修改。",
        "移植U27输出路径并检查P1preparetimers继续存在。",
        "重跑rawtokenizer/G1与工具streamfixtures，区分生成替换和输入拒绝的报告。"
      ],
      "verify": [
        "ctest --test-dir \"$BUILD\" -R \"ninfer_qwen3_8_(frontend|tokenization_equivalence)_test\" --output-on-failure",
        "重跑输出utf8与tool-stream fixture，记录按字节的delta拼接。"
      ],
      "acceptance": [
        "合法输出无变化；非法输出可安全终态化；input/G1不回退。"
      ],
      "review_focus": [
        "不能用JSON序列化error_handler替代实际decoder正确性。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P4-T05.md"
    },
    {
      "id": "P4-T06",
      "phase": "P4",
      "kind": "task",
      "title": "4090 上验证新 KV 质量、容量与性能",
      "owner": "GPU qualification",
      "depends_on": [
        "P4-T02",
        "P4-T03",
        "P4-T04",
        "P4-T05"
      ],
      "modify": [],
      "create": [
        "evidence/upstream-merge/P4/qualification-scope.json",
        "evidence/upstream-merge/P4/codec-quality.json"
      ],
      "interfaces": [
        "输入P3旧codec与P4newrk4v4；profile除codec/version目录外保持冻结，decisions单独BF16profile。"
      ],
      "tests": [
        "FullContext：248K实际tokens+输出/系统余量不越262144；5needle和代码细节全部按判定器验证。",
        "ChatQuality：plans/06选定工程与repo集的编译测试/工具正确率不下降；差异不以“浮点”直接豁免。",
        "DecisionTolerance：启用真实decisionadapter时使用冻结per-questionreference容差；BF16资格与压缩codec偏差分开。"
      ],
      "implementation": [
        "串行P3/P4/P3，先smallrealprobe再128K/192K/248K、cold/hot和容量负例。",
        "记录reused tokens、memory summary、OOM/拒绝、MTP acceptance、各层时延。",
        "真实adapter缺失：结构tests仍必测，qualification-scope明确decision_text/image未资格，生产profile不配置该adapter。",
        "chat门槛失败保持P3生产候选；不得默默恢复E8旧encoder，按ADR另开显式重设计。"
      ],
      "verify": [
        "python3 \"$PACK/scripts/compare_metrics.py\" --baseline \"$P3_NORMALIZED\" --candidate \"$P4_NORMALIZED\" --allow-change kv_dtype --out \"$OUT/P4/performance.json\"",
        "运行long/Java任务判定器并附codec实际格式revision与所有missing资格。"
      ],
      "acceptance": [
        "chat质量/性能/容量必过；新缓存与旧隔离；可选decision资格真实标注。"
      ],
      "review_focus": [
        "上游+2.3%不是本机目标保证；不能拿BF16中短决策样本代表262K压缩Chat。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P4-T06.md"
    },
    {
      "id": "P5-T01",
      "phase": "P5",
      "kind": "task",
      "title": "串行合入上游里程碑（U28—U34）",
      "owner": "Integrator",
      "depends_on": [
        "P4-GATE"
      ],
      "modify": [
        "本阶段 data/upstream-commits.json 列出的所有变化路径",
        "tests/CMakeLists.txt（唯一串行所有者）"
      ],
      "create": [
        "docs/upstream-merge/P5-import-ledger.md"
      ],
      "interfaces": [
        "输入前一合格gate与上游固定提交 5b99996bc7c1fe6ff27f271a205eb605302ec8bb；输出带双亲的phase-base和文件责任锁表。"
      ],
      "tests": [
        "UpstreamAncestry：新phase-base同时包含前阶段与本里程碑祖先。",
        "Retention：43项定制账本有对应文件/替代测试，不能静默丢失。"
      ],
      "implementation": [
        "确认上一gate的提交与当前HEAD一致；执行 git merge --no-ff --no-commit 5b99996bc7c1fe6ff27f271a205eb605302ec8bb。",
        "按C01—C16以及P0新增冲突逐项解析；保存实际冲突/选择理由。",
        "带入/typesafe、OpenAI Decisions、image身份/版本与playground；最终core schema24、snapshot6/image5/decisionalias2需从源码复核。",
        "只对已review解析commit；允许暂存尚未资格化的phase-base，但不得部署。冻结头文件接口后再分派并行工作树。"
      ],
      "verify": [
        "git merge-base --is-ancestor 5b99996bc7c1fe6ff27f271a205eb605302ec8bb HEAD",
        "git ls-files -u  # 必须为空",
        "git diff HEAD^ HEAD --check"
      ],
      "acceptance": [
        "真实merge ancestry成立；所有冲突已记录解析；定制保留项均有任务负责；phase-base标UNQUALIFIED。"
      ],
      "review_focus": [
        "严禁 -s ours、全仓ours/theirs、squash伪装全上游历史；不得用暂不能编译为理由删除tests。"
      ],
      "rollback": "尚无生产变更；丢弃独立实验分支或用可审计revert，继续从上一已资格化tag开发。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P5-T01.md"
    },
    {
      "id": "P5-T02",
      "phase": "P5",
      "kind": "task",
      "title": "验证双决策协议、模型发现与错误契约",
      "owner": "Protocol implementation",
      "depends_on": [
        "P5-T01"
      ],
      "modify": [
        "src/product/openai_decisions/request.cpp",
        "src/product/openai_decisions/answers.cpp",
        "src/serve/openai_decisions_service.cpp",
        "src/serve/systemone_service.cpp",
        "src/serve/decision_models.cpp",
        "src/serve/http_server.cpp",
        "src/serve/openai_schema.cpp",
        "tests/test_openai_decisions_product.cpp",
        "tests/test_systemone_product.cpp"
      ],
      "create": [
        "tests/merge/fixtures/decision-wire-cases.jsonl"
      ],
      "interfaces": [
        "OpenAI与TypeSafe各自解析/答复，共享core decision input而非有损HTTP翻译；/typesafe实际路由为权威。"
      ],
      "tests": [
        "NativeWire：有序input/answers/confidence/usage按各协议自己的规则。",
        "NoFabrication：无adapter/未支持modality报真实错误；不添加未训练refusal或虚拟外部模型别名。",
        "Discovery：decisionadapter只广告decisioncapability，生成model解析拒绝误用。",
        "RemovedRoute：旧/systemone无未声明兼容alias；保留Chat三端点。"
      ],
      "implementation": [
        "先加纯product parser/answerformatter和路由负例，再修复merge中丢失的新接口。",
        "延续prepare_detail与bodyraw统计，不把decision preparation冒充Chat阶段。",
        "核实TypeSafe answer具体字段/rounding/truncation和OpenAI的拒绝截断规则，补协议differencefixture。"
      ],
      "verify": [
        "ctest --test-dir \"$BUILD\" -R \"ninfer_.*(openai_decisions_product|systemone_product|openai_schema|serve_options).*test\" --output-on-failure",
        "按decision-wire-cases回放两个native协议，检查HTTP状态、错误结构与usage。"
      ],
      "acceptance": [
        "两个协议的结构/错误均通过；生成路径继续可用；不通过别名伪装外部模型。"
      ],
      "review_focus": [
        "保持协议差异，避免把TypeSafe rounding或truncation套用OpenAI。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P5-T02.md"
    },
    {
      "id": "P5-T03",
      "phase": "P5",
      "kind": "task",
      "title": "合入图像预处理身份、MRoPE 与媒体容量",
      "owner": "Vision implementation",
      "depends_on": [
        "P5-T01"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/frontend/processor.cpp",
        "src/targets/qwen3_8/impl/frontend/processor.h",
        "src/targets/qwen3_8/impl/frontend/frontend.cpp",
        "src/targets/qwen3_8/export/ninfer/targets/qwen3_8/prepared_prompt.h",
        "src/targets/qwen3_8/impl/runtime/prefix_identity.cpp",
        "src/targets/qwen3_8/impl/runtime/continuation_image.h",
        "src/targets/qwen3_8/impl/runtime/session_snapshot_impl.h",
        "src/serve/generation_service.cpp",
        "src/serve/generation_service.h",
        "tests/targets/qwen3_8_27b/test_multimodal.py",
        "tests/targets/qwen3_8_27b/test_reference_frontend.py"
      ],
      "create": [
        "tests/merge/fixtures/image-state-cases.json"
      ],
      "interfaces": [
        "VisionItem.preprocessing_digest进入semanticidentity；image detail/resize/padding影响必须可区分。",
        "rawbytes/decodedpixels/patches/visiontokens/requestlease分别受预算约束。"
      ],
      "tests": [
        "SameBytesDifferentProfile：同图片不同detail/resize不得误命中；相同语义profile可合法复用。",
        "VisionOnce：cachedstate图像不按每question重复encodevision。",
        "MRoPE：positions/rope_delta与参考一致；snapshot restore不丢image identity。",
        "BudgetReject：超限拒绝不静默降画质；cancel后hostlease释放。"
      ],
      "implementation": [
        "先用小PPM和不同profile合成fixture测identity/position/budget。",
        "保留decisionstate与processor新字段，并确保B0主编码路径/计时不被新frontend.cpp覆盖。",
        "核对最终state6/5/2writer/reader，旧版本拒绝和namespace再次隔离。",
        "缺image-trainedadapter时仍完成图像处理/算子结构验证，业务图像决策精度另列未资格。"
      ],
      "verify": [
        "ctest --test-dir \"$BUILD\" -R \"ninfer_qwen3_8_(frontend|runtime_mechanisms)_test\" --output-on-failure",
        "设置真实27B权重后运行 ninfer_qwen3_8_27b_prefix_real_test 的vision子场景；该测试非长上下文资格。"
      ],
      "acceptance": [
        "图像profile身份、MRoPE、预算和取消必测通过；未伪造image-adapter准确率。"
      ],
      "review_focus": [
        "图像原始hash相同不够；preprocess policy/尺寸/padding都可能改变语义。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P5-T03.md"
    },
    {
      "id": "P5-T04",
      "phase": "P5",
      "kind": "task",
      "title": "验收 playground 与历史日志显示",
      "owner": "Web QA",
      "depends_on": [
        "P5-T01"
      ],
      "modify": [
        "apps/web/src/playground/request.ts",
        "apps/web/src/playground/answers.ts",
        "apps/web/src/playground/json.ts",
        "apps/web/src/playground/images.ts",
        "apps/web/src/playground/store.ts",
        "apps/web/src/lib/records.ts",
        "apps/web/src/lib/derive.test.ts"
      ],
      "create": [
        "tools/smoke/merge_playground_checklist.md",
        "evidence/upstream-merge/P5/browser-smoke.json"
      ],
      "interfaces": [
        "使用仓库bun锁文件；新增真实浏览器smoke检查单记录browser/version/build/sourcehash及实际结果。"
      ],
      "tests": [
        "OrderedInputs：primitive/answer顺序保持；大整数文本不因JS Number转换丢精度。",
        "ImageRoundTrip：detail/dataURL/分享与恢复正确，不泄漏localfilepath/secret。",
        "LogCompatibility：forkprepare_detail/schema24/未知扩展展示正确缺值与单位。",
        "NoPhantomFeature：未加载decisionadapter时UI提示实际不可用，不展示假结果。"
      ],
      "implementation": [
        "先补实际request/json/answer unitfixture，再按锁文件构建。",
        "在浏览器打开候选build与testserver，完成编辑/提交/响应/保存恢复/图片用例；截图只是辅助，断言字段需保存。",
        "没有浏览器执行通道时browser资格留BLOCKED；task源码/unit/build可PASS，browser_runtime仍UNQUALIFIED且不能宣称完整Web发布。",
        "web可作为独立已测试产物；不强迫Dockerfile.sm89-nobake包含dashboard。"
      ],
      "verify": [
        "cd \"$INTEGRATE/apps/web\" && bun install --frozen-lockfile && bun run typecheck && bun test && bun run build",
        "执行 tools/smoke/merge_playground_checklist.md；保存实际browser验证记录。"
      ],
      "acceptance": [
        "单测/类型/构建必过；browser执行资格单列；无权重服务镜像仍无需web。"
      ],
      "review_focus": [
        "不要引入未锁定依赖“修build”；新浏览器自动化框架须说明新增依赖，不能假定已安装。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P5-T04.md"
    },
    {
      "id": "P5-T05",
      "phase": "P5",
      "kind": "task",
      "title": "统一验收最终 API 与多模态状态",
      "owner": "Integration QA",
      "depends_on": [
        "P5-T02",
        "P5-T03",
        "P5-T04"
      ],
      "modify": [],
      "create": [
        "evidence/upstream-merge/P5/api-qualification.json"
      ],
      "interfaces": [
        "最终U核心schema24与customextension；代码资格、Chat、textdecision、imagedecision、browser分开列。"
      ],
      "tests": [
        "GeneratedEndpointRegression：三个生成端点/compatproxy仍正确；tools/history/progress/timers全链路有效。",
        "StateVersionNegative：在候选测试目录尝试旧版本payload，明确拒绝且不损坏新状态。",
        "MixedModeIsolation：有adapter时混合Chat/decision/image不跨lane/adapter复用；无adapter时错误资源释放可测。"
      ],
      "implementation": [
        "组合前四任务在同一集成commit，重跑CPU/CUDA/realprefix/HTTP回放。",
        "决策/图片真实adapter可用才跑业务精度；缺失资格在scope中列出并在生产profile禁用。",
        "在纯Chat主profile再跑长工具会话，确认新增服务功能没有隐性内存/导出/计时成本回退。"
      ],
      "verify": [
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$OUT/P5/all.junit.xml\"",
        "python3 \"$PACK/scripts/check_junit.py\" \"$OUT/P5/all.junit.xml\" --require \"^ninfer_qwen3_8_27b_prefix_real_test$\"",
        "使用P0 replay跑所有已启用协议/模态，产出scope和失败明细。"
      ],
      "acceptance": [
        "最终Chat主profile合格；所有无模型purecontract必测通过；可选业务资格如实记录；旧cache隔离。"
      ],
      "review_focus": [
        "通过P5不等于授权生产切换；P6仍须端到端质量和回滚门禁。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P5-T05.md"
    },
    {
      "id": "P6-T01",
      "phase": "P6",
      "kind": "task",
      "title": "完成全量 ancestry 与定制保留审查",
      "owner": "Integrator / independent reviewer",
      "depends_on": [
        "P5-GATE"
      ],
      "modify": [
        "docs/upstream-merge/retention-ledger.csv",
        "AGENTS.md",
        "docs/serving.md",
        "docs/continuation-cache.md",
        "docs/performance.md"
      ],
      "create": [
        "docs/upstream-merge/final-review.md",
        "evidence/upstream-merge/P6/qualification-scope.json"
      ],
      "interfaces": [
        "所有34上游提交与11定制提交均可追溯；每个定制项有代码/测试/替代/仅历史证据的明确结论。"
      ],
      "tests": [
        "AncestryBoth：O/U均为candidate祖先；无 -s ours伪合并，patch内容逐项对照。",
        "RetentionComplete：43项账本无未处理；B0/B1/计时/standalone/skip/Docker都映射到证据。"
      ],
      "implementation": [
        "重新生成最终gitdiff/retention与API消费清单；核对16共享路径外额外问题。",
        "把本次生产保留约束补充AGENTS，不盲从上游“无需兼容”的一般原则覆盖用户目标。",
        "独立reviewer在同一finalcommit审查架构/并发/数值/协议/测试；P0/P1阻断项不得拖成无声豁免。"
      ],
      "verify": [
        "git merge-base --is-ancestor e0b05f7cb46adae2787be2ccbe605e1b0c9b3923 HEAD",
        "git merge-base --is-ancestor 5b99996bc7c1fe6ff27f271a205eb605302ec8bb HEAD",
        "git diff --check"
      ],
      "acceptance": [
        "祖先成立且内容证据齐全；review无P0/P1阻断；scope所有未资格项明确。"
      ],
      "review_focus": [
        "“包含U祖先”不等于包含U实际行为；需防merge策略覆盖。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P6-T01.md"
    },
    {
      "id": "P6-T02",
      "phase": "P6",
      "kind": "task",
      "title": "最终 128K—248K Java Agent 配对验收",
      "owner": "Performance / quality QA",
      "depends_on": [
        "P6-T01"
      ],
      "modify": [],
      "create": [
        "evidence/upstream-merge/P6/final-quality.json",
        "evidence/upstream-merge/P6/final-performance.json"
      ],
      "interfaces": [
        "输入P0冻结PROD/O基线和最终候选；同时报告相对PROD、O和上一phase的差异。"
      ],
      "tests": [
        "FrozenSuite：模型/resource/dataset/seed/reasoning/tooljudger不变。",
        "NoRegression：建议TTFT p50≤+5%/p90≤+10%、decode p50≥-3%/p10≥-5%，prepare相同相对门槛，精确以P0冻结值为准。",
        "QualityAndCapacity：plans/06选定工程/repo判定/长5needle、共享KV拒绝策略满足冻结条件；样本不足不能说统计非劣。"
      ],
      "implementation": [
        "完整执行A/B/A或ABBA，控制频率/功耗/温度漂移；同一张卡不双加载模型。",
        "独立列出cold/hot/cache/工具/并发；对迁移后codec变化作显式比较声明。",
        "发现退化回溯phase与单项变量，修复后重跑受影响gate及最终质量，不通过降低门槛过线。"
      ],
      "verify": [
        "python3 \"$PACK/scripts/compare_metrics.py\" --baseline \"$PROD_NORMALIZED\" --candidate \"$FINAL_NORMALIZED\" --allow-change kv_dtype --out \"$OUT/P6/performance-vs-prod.json\"",
        "python3 \"$PACK/scripts/compare_metrics.py\" --baseline \"$O_NORMALIZED\" --candidate \"$FINAL_NORMALIZED\" --allow-change kv_dtype --out \"$OUT/P6/performance-vs-ours.json\""
      ],
      "acceptance": [
        "功能/数值/业务/容量/性能分别通过；原始样本与归一报告可一一复现。"
      ],
      "review_focus": [
        "能接受无显著加速但不回退；不能在没有样本时承诺整体提升。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P6-T02.md"
    },
    {
      "id": "P6-T03",
      "phase": "P6",
      "kind": "task",
      "title": "构建不可变镜像并演练启动与排空",
      "owner": "Deployment",
      "depends_on": [
        "P6-T01"
      ],
      "modify": [
        "Dockerfile.sm89-nobake"
      ],
      "create": [
        "deploy/merge-candidate-profile.json",
        "deploy/merge-rollback-profile.json",
        "deploy/merge-runbook.md"
      ],
      "interfaces": [
        "运行profile是tokenizedargv+只读model mount+独立cache+image digest；保持ENTRYPOINT ninfer-serve。"
      ],
      "tests": [
        "NoBakedModel：镜像层不包含模型；runtime可读.ninfer但不可写。",
        "NoSharedCache：candidate/prod目录不同；旧profile保留旧codec不被替换。",
        "DrainNoReplay：切换前拒绝新任务/等待活跃请求结束；进行中的tool calls不得自动重放。"
      ],
      "implementation": [
        "构建带revisionlabel的无权重镜像，保存digest及build依赖；先在test窗口单实例启动/health/realrequest。",
        "复用P0实际argv，仅改源码/codec/目录和明确批准项；不复制上游大并发默认值。",
        "用smoke验证warmup、gracefulshutdown、L3重启；部署工具默认dryrun，生产动作需要明确目标与批准。"
      ],
      "verify": [
        "docker build -f Dockerfile.sm89-nobake --label org.opencontainers.image.revision=\"$(git rev-parse HEAD)\" -t \"ninfer-4090:merge-$CANDIDATE_SHA\" .",
        "docker image inspect \"ninfer-4090:merge-$CANDIDATE_SHA\" --format \"{{.Id}}\""
      ],
      "acceptance": [
        "镜像/argv/模型/cache身份固定；test环境启动、排空、重启可用；生产还未擅自切换。"
      ],
      "review_focus": [
        "单卡不具备默认双活蓝绿容量；禁止docker system prune删除回滚镜像。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P6-T03.md"
    },
    {
      "id": "P6-T04",
      "phase": "P6",
      "kind": "task",
      "title": "在批准窗口执行生产试运行",
      "owner": "Deployment / user approval",
      "depends_on": [
        "P6-T02",
        "P6-T03"
      ],
      "modify": [],
      "create": [
        "evidence/upstream-merge/P6/canary-approval.json",
        "evidence/upstream-merge/P6/canary-report.json"
      ],
      "interfaces": [
        "批准包含host、容器、镜像digest、时间窗口、允许停机和回滚触发；不从“可直接部署测试”推断无限生产改动权限。"
      ],
      "tests": [
        "ApprovalRequired：未明确批准生产目标时仅test执行，final release状态PENDING而非伪PASS。",
        "CanaryHealth：从受控少量Java会话起步，监测error/toolcorrectness/TTFT/cache/memory，不仅health200。"
      ],
      "implementation": [
        "排空旧实例并确认旧镜像三件套保留；候选作为唯一驻留模型启动。",
        "先合成smoke再受控实际会话；因单GPU不可做双模型百分比分流，按时段和会话白名单逐步放量。",
        "采用P0预先冻结观察量：至少一个有代表性的业务窗口且≥100次已完成请求；不足时不完成最终生产资格。",
        "任何状态污染/OOM/工具错误或持续超过门槛立即停止放量并执行T05回滚路径。"
      ],
      "verify": [
        "按 deploy/merge-runbook.md 的已批准target执行；命令和退出码写入canary-report，不在本包预填成功。"
      ],
      "acceptance": [
        "实际试运行数据达到冻结观察量、业务正确和门槛合格；或明确PENDING不宣称完成发布。"
      ],
      "review_focus": [
        "警报触发条件不能在看到失败后改；不把会话不够当100个合成healthcheck替代。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P6-T04.md"
    },
    {
      "id": "P6-T05",
      "phase": "P6",
      "kind": "task",
      "title": "实际回滚演练与最终交付",
      "owner": "Deployment / final reviewer",
      "depends_on": [
        "P6-T04"
      ],
      "modify": [
        "deploy/merge-runbook.md",
        "docs/upstream-merge/final-review.md"
      ],
      "create": [
        "evidence/upstream-merge/P6/rollback-report.json",
        "evidence/upstream-merge/P6/release-manifest.json"
      ],
      "interfaces": [
        "回滚恢复旧镜像+旧argv+旧cache；再提升候选必须重新授权/确认状态，不自动双加载。"
      ],
      "tests": [
        "RollbackUsable：旧实例实际恢复health、一次正常生成和完整tool-call回路；旧cache可用或合法coldmiss。",
        "VersionIsolation：候选payload未写进旧namespace；旧启动参数不混入rk4v4新格式。",
        "ReleaseTruth：源码完成、chat生产资格、optional资格和实际发布状态分别列出。"
      ],
      "implementation": [
        "在批准测试/维护窗口执行候选→旧版本切换并跑真实smallprobe；不只检查命令存在。",
        "记录排空/停机/恢复时间和失败请求处理；进行中的写工具不得自动重试。",
        "保存finalsource/images/profiles/gates/quality/perf/caveats；按已批准release决定最终驻留旧版或新版。",
        "输出统一最终review与gate；保留旧镜像/cache至约定观察期结束，清理另行批准。"
      ],
      "verify": [
        "按 deploy/merge-runbook.md 回滚三件套并运行标准Chat+tool smoke；保存真实log与manifestSHA。"
      ],
      "acceptance": [
        "回滚实际可用；最终驻留版本明确；release manifest准确，没有把可选未测能力写成已通过。"
      ],
      "review_focus": [
        "不能用“已备份”代替实际回滚；不要在收尾删除唯一基线和历史oracle。"
      ],
      "rollback": "只撤回该任务提交；不重写已发布分支。",
      "optional": false,
      "status": "PENDING",
      "document": "previous-v2/plans/tasks/P6-T05.md"
    },
    {
      "id": "P0-GATE",
      "phase": "P0",
      "kind": "gate",
      "title": "统一代码 review 与集成测试门禁",
      "owner": "Independent reviewer + Integrator",
      "depends_on": [
        "P0-T01",
        "P0-T02",
        "P0-T03",
        "P0-T04"
      ],
      "status": "PENDING",
      "document": "previous-v2/plans/phases/P0.md"
    },
    {
      "id": "P1-GATE",
      "phase": "P1",
      "kind": "gate",
      "title": "统一代码 review 与集成测试门禁",
      "owner": "Independent reviewer + Integrator",
      "depends_on": [
        "P1-T01",
        "P1-T02",
        "P1-T03",
        "P1-T04",
        "P1-T05",
        "P1-T06"
      ],
      "status": "PENDING",
      "document": "previous-v2/plans/phases/P1.md"
    },
    {
      "id": "P2-GATE",
      "phase": "P2",
      "kind": "gate",
      "title": "统一代码 review 与集成测试门禁",
      "owner": "Independent reviewer + Integrator",
      "depends_on": [
        "P2-T01",
        "P2-T02",
        "P2-T03",
        "P2-T04"
      ],
      "status": "PENDING",
      "document": "previous-v2/plans/phases/P2.md"
    },
    {
      "id": "P3-GATE",
      "phase": "P3",
      "kind": "gate",
      "title": "统一代码 review 与集成测试门禁",
      "owner": "Independent reviewer + Integrator",
      "depends_on": [
        "P3-T01",
        "P3-T02",
        "P3-T03",
        "P3-T04",
        "P3-T05"
      ],
      "status": "PENDING",
      "document": "previous-v2/plans/phases/P3.md"
    },
    {
      "id": "P4-GATE",
      "phase": "P4",
      "kind": "gate",
      "title": "统一代码 review 与集成测试门禁",
      "owner": "Independent reviewer + Integrator",
      "depends_on": [
        "P4-T01",
        "P4-T02",
        "P4-T03",
        "P4-T04",
        "P4-T05",
        "P4-T06"
      ],
      "status": "PENDING",
      "document": "previous-v2/plans/phases/P4.md"
    },
    {
      "id": "P5-GATE",
      "phase": "P5",
      "kind": "gate",
      "title": "统一代码 review 与集成测试门禁",
      "owner": "Independent reviewer + Integrator",
      "depends_on": [
        "P5-T01",
        "P5-T02",
        "P5-T03",
        "P5-T04",
        "P5-T05"
      ],
      "status": "PENDING",
      "document": "previous-v2/plans/phases/P5.md"
    },
    {
      "id": "P6-GATE",
      "phase": "P6",
      "kind": "gate",
      "title": "统一代码 review 与集成测试门禁",
      "owner": "Independent reviewer + Integrator",
      "depends_on": [
        "P6-T01",
        "P6-T02",
        "P6-T03",
        "P6-T04",
        "P6-T05"
      ],
      "status": "PENDING",
      "document": "previous-v2/plans/phases/P6.md"
    },
    {
      "id": "H0-T01",
      "phase": "H0",
      "kind": "task",
      "title": "冻结实际P6基线、源码与shape目录",
      "owner": "Integrator",
      "depends_on": [
        "P6-GATE"
      ],
      "modify": [],
      "create": [
        "tools/bench/hybrid_source_audit.py",
        "tests/hybrid/test_source_audit.py"
      ],
      "interfaces": "audit(source_lock, actual_p6_gate, checkout, B29_manifest, BO_manifest) -> capability-manifest.json；分别绑定B29 image/binary/E8/schema20、BO重建与真实B6/rk4v4/schema24，P6缺证据阻断；不把本轮B29测量当H0完成。",
      "implementation": [
        "按plans/05先保全B29指纹/原样A/A；对照原P0的PROD/O/C设计，区分未知source provenance、远端目录与运行镜像。",
        "只有真实P6-GATE满足后审计B6的commit/build/image；保留dirty overlay，不用U/O/PINNED_COMMIT代替。沿instantiate.h定位全部shape消费者。",
        "输出B29/BO/B6、已有/拟新增/未核查与来源/资产表；schema20到24显式映射，缺字段null，codec独立数值/质量/速度门。"
      ],
      "tests": [
        "P6GateRequired：B29测量可独立执行；但缺真实P6记录/commit不一致不得宣称H0资格。",
        "NoSourceMutation：运行前后用户worktree/index/未跟踪状态不变；source未知不能填猜测SHA。",
        "ShapeInventory：每个限制及logicalV/physicalW包含layout/kernel/Graph/commit消费者；B29/E8与B6/rk4v4不得混同。"
      ],
      "test_target": "test_source_audit",
      "legacy_ids": [
        "P7-T01"
      ],
      "sources": "NI01–NI06/HQ02",
      "mode": "python",
      "status": "PENDING",
      "document": "plans/tasks/H0-T01.md"
    },
    {
      "id": "H0-T02",
      "phase": "H0",
      "kind": "task",
      "title": "冻结语料、请求矩阵与配对benchmark驱动",
      "owner": "Bench",
      "depends_on": [
        "H0-T01"
      ],
      "modify": [],
      "create": [
        "tools/bench/run_hybrid_matrix.py",
        "tests/hybrid/test_matrix_manifest.py"
      ],
      "interfaces": "run_hybrid_matrix.py --manifest FILE --profile FILE --out DIR；按plans/05–06与design/07保留14实际P/三O/4负载/cold-warm/两轨672声明目录；初始只执行174core+104专项=278请求，Pi44一次O32768，8工程一次+2repo一次；未来H0消费合格B6，本轮B29 runner独立。",
      "implementation": [
        "以会话/项目划分calibration/locked-test，覆盖14档实际P、中文/Java/tools/copy；冻结Pi树路径/compaction/context_edit与serializer，历史wire和session-derived分级。",
        "保存最终wire/count/hash并由生成prompt_tokens复核；P>C输入拒绝、O_eff=min(O,C-P+1)、末token不入KV；固定原argv，冷条件不达标留gap，client→response→serverID联结；Pi异常保留medium/32768。",
        "串行A/A或A/B/A、监控与checkpoint；按plans/06分初始薄层、阶段≤240相关A/B与H5/H8正式资格，预算不等于PASS；固定toolResult不执行不称闭环。"
      ],
      "tests": [
        "ActualDepth：配置262K但实际只4K不能满足长桶；计数与生成P不符、O_eff/页合同不符或cold实际hit需保留gap，不伪造通过。",
        "NoLeakage：相同项目/会话跨calibration/locked-test拒绝；Pi不同分支/压缩状态不能混成同wire。",
        "PairIntegrity：缺配对/重复ID/删慢样本/错采样cache/缺raw质量证据拒绝；固定轨迹不能标真实闭环。"
      ],
      "test_target": "test_matrix_manifest",
      "legacy_ids": [
        "P7-T02"
      ],
      "sources": "HQ01/HQ05",
      "mode": "python",
      "status": "PENDING",
      "document": "plans/tasks/H0-T02.md"
    },
    {
      "id": "H0-T03",
      "phase": "H0",
      "kind": "task",
      "title": "新增非侵入式round与路由观测",
      "owner": "Serving",
      "depends_on": [
        "H0-T01"
      ],
      "modify": [
        "src/serve/request_log.cpp",
        "src/serve/request_log.h",
        "include/ninfer/types.h"
      ],
      "create": [
        "tests/test_hybrid_request_log.cpp"
      ],
      "interfaces": "extensions.hybrid_spec_v1；分开logicalK/validV/physicalW/B/tokenrows、accepted/committed/bonus、roundwall/alignment；B29 schema20经显式adapter，不伪装schema24。",
      "implementation": [
        "只增加独立扩展，旧schema/prepare_detail字段和单位不改；B29缺字段null+reason，proxy补0 reasoning不当真实值。",
        "采样GPU events/route与client payload时钟，不逐层同步；保存重写requestID映射及schema adapter/hash。",
        "错误/取消/超时保留attempt与计数源；accepted不替completion，reused不计computed-prefill，SSE合并不造ITL。"
      ],
      "tests": [
        "CommitDenominator：accept=3/completion=2或bonus=1时按原许可/停止合同计交付，anchor不重复。",
        "SchemaPreserved：schema20/24与prepare_detail显式映射；缺metric或reasoning补0不能伪造真值。",
        "NoSyncHotPath：观测OFF/ON配对，超2%则降采样重测；缺ID映射不能关联错误请求。"
      ],
      "test_target": "ninfer_hybrid_request_log_test",
      "legacy_ids": [
        "P7-T03"
      ],
      "sources": "HQ05/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H0-T03.md"
    },
    {
      "id": "H0-T04",
      "phase": "H0",
      "kind": "task",
      "title": "实现显存、host与Graph资源账本",
      "owner": "Capacity",
      "depends_on": [
        "H0-T01"
      ],
      "modify": [],
      "create": [
        "tools/bench/hybrid_budget.py",
        "tests/hybrid/test_budget.py"
      ],
      "interfaces": "evaluate_budget(profile, planned_regions, observed_peak) -> budget-verdict.json；分物理列/多lane/共享workspace与持久记录。",
      "implementation": [
        "用design/06推导ReplaySSM及logits理论大小，做整数溢出及buffer别名校验。",
        "读取实测峰值及实际pipeline生命周期，不重复记共享workspace；未测字段保持UNKNOWN。",
        "生成W6/8/16、head profiles、draft ring的互斥/共驻配置账本。"
      ],
      "tests": [
        "TokenRowsNotSequences：B4/W16按64列而不是4列分配。",
        "NoDoubleSpend：旧head未释放、共享region重复计或负增量来源未知时拒绝free-memory结论。",
        "UnknownIsBlocked：缺graph/host/pinned/峰值证据不能标fits=true。"
      ],
      "test_target": "test_budget",
      "legacy_ids": [
        "P7-T04"
      ],
      "sources": "HQ05/NI01",
      "mode": "python",
      "status": "PENDING",
      "document": "plans/tasks/H0-T04.md"
    },
    {
      "id": "H0-T05",
      "phase": "H0",
      "kind": "task",
      "title": "建立逐层与整轮数值对照协议",
      "owner": "Numerics",
      "depends_on": [
        "H0-T01"
      ],
      "modify": [],
      "create": [
        "tests/targets/qwen3_8_27b/test_hybrid_baseline_real.cpp",
        "tools/bench/compare_hybrid_trace.py"
      ],
      "interfaces": "capture/compare同Target同prefill-state的token、Target hidden、GDN record/frontier、alignment输出；容差从原oracle继承，greedy token必须精确。",
      "implementation": [
        "固定ordinary/MTP3/4/5 baseline，记录已存在的浮点差异与适用范围，不偷偷换golden。",
        "为0/部分/全接受、budget与stop保存独立参考；用模型实际内部trace定位首次分叉。",
        "定义新route的L0/L1/L2/L3资格，尤其batch packing与Graph变化。"
      ],
      "tests": [
        "SameStartState：prefill拆分或KV不同的两条trace不能当verify单因素A/B。",
        "FirstDivergence：人为改变一列position或hidden时能定位第一处差异。",
        "BaselineNotFabricated：缺真实artifact/GPU时输出77/BLOCKED，不能生成candidate自指expected。"
      ],
      "test_target": "ninfer_hybrid_baseline_real_test",
      "legacy_ids": [
        "P9-T01"
      ],
      "sources": "HQ02/HQ05/NI03",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H0-T05.md"
    },
    {
      "id": "H0-T06",
      "phase": "H0",
      "kind": "task",
      "title": "实现fail-closed阶段证据检查",
      "owner": "QA",
      "depends_on": [
        "H0-T01",
        "H0-T02",
        "H0-T03",
        "H0-T04",
        "H0-T05"
      ],
      "modify": [],
      "create": [
        "tools/bench/check_hybrid_evidence.py",
        "tests/hybrid/test_evidence_gate.py"
      ],
      "interfaces": "check_hybrid_evidence.py --phase ID --record FILE --registry FILE；按design/07/09验证p95/CI/样本/规则与证据，未知规则/quantile、空metrics、重复/缺配对、skip、wronghash/commit/schema均fail-closed。",
      "implementation": [
        "记录代码/GPU/研究/production与baseline COLLECTED/QUALIFIED状态，完整DAG含生产gate，不从勾选或baseline采集推断通过。",
        "校验文件/hash/JUnit/actualroute、rule allowlist/单位/finite值及measurement_scope；H5/H8正式声明要求10配对/独立block与p95桶100，初始/筛选不冒充正式资格；缺值/不足BLOCKED或INCONCLUSIVE。",
        "实现p95与配对聚类CI并保留A1/B100+p95=.05必须FAIL负例；解析design/10原scope，NO_ADOPTION不覆盖缺资产/数值失败，promotion独立。"
      ],
      "tests": [
        "SkipCannotPass：0tests/GPU77/缺required/空metrics或未知quantile-rule拒绝；A1/B100仅p95规则必须FAIL。",
        "CommitBound：review/binary/profile/data/hash/schema不一致、配对重复/缺失、warmup混样或p95样本不足均不得通过。",
        "NoGoHonest：缺资产/数值失败/未测不能写NO_ADOPTION或QUALIFIED；派生scope不改排除任务真值，baseline不替phasegate。"
      ],
      "test_target": "test_evidence_gate",
      "legacy_ids": [],
      "sources": "HQ05",
      "mode": "python",
      "status": "PENDING",
      "document": "plans/tasks/H0-T06.md"
    },
    {
      "id": "H0-GATE",
      "phase": "H0",
      "kind": "gate",
      "title": "P6基线、语料、观测、资源与证据统一评审验收",
      "depends_on": [
        "H0-T01",
        "H0-T02",
        "H0-T03",
        "H0-T04",
        "H0-T05",
        "H0-T06"
      ],
      "status": "PENDING",
      "document": "plans/phases/H0.md"
    },
    {
      "id": "H1-T01",
      "phase": "H1",
      "kind": "task",
      "title": "落盘hybrid契约与显式能力准入",
      "owner": "Integrator",
      "depends_on": [
        "H0-GATE"
      ],
      "modify": [
        "include/ninfer/types.h",
        "src/serve/serve_options.h",
        "src/serve/serve_options.cpp"
      ],
      "create": [
        "src/runtime/generation/hybrid_contract.h",
        "tests/test_hybrid_contract.cpp"
      ],
      "interfaces": "落盘C10–C13/--hybrid-policy；ProposalSource非backend；logicalK/V与physicalW/B/tokenrows独立，K1/2映射W4、budget1映射K0/W1、budget2映射K<=1/W1或4；physical widths初始1/4/5/6。",
      "implementation": [
        "维持旧enum/CLI；policyoff旧graph与输出相同；当前baseline-only不实现本task。",
        "启动绑定target/tokenizer/kv/profile、deterministic-delta与Target processor/sampling资格；先base/text，生产sampling组合资格前OFF/回原合格sampling，Target-greedy只诊断。",
        "冻结logical/physical字段及整数乘积预算/映射；非法shape或无kernel资格拒绝；公共头/CMake由唯一Integrator串行合入。"
      ],
      "tests": [
        "LegacyOff：未传policy时原sampling/greedy CLI/graph/输出保持；不能以greedy资格冒充production sampling。",
        "CapabilityReject：未知fingerprint/字段/width、资源或sampling资格未ready时拒绝新配置；请求回原合格sampling，不能暗降ctx/codec/temperature。",
        "PhysicalShape：K1/V2和K2/V3都按W4、B*W预算；budget1/2不多发bonus，padding不计有效候选。"
      ],
      "test_target": "ninfer_hybrid_contract_test",
      "legacy_ids": [
        "P8-T01"
      ],
      "sources": "HQ02/NI03/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H1-T01.md"
    },
    {
      "id": "H1-T02",
      "phase": "H1",
      "kind": "task",
      "title": "实现request-local有界Lookup索引",
      "owner": "Lookup",
      "depends_on": [
        "H1-T01"
      ],
      "modify": [],
      "create": [
        "src/runtime/generation/prompt_lookup.h",
        "src/runtime/generation/prompt_lookup.cpp",
        "tests/test_prompt_lookup.cpp"
      ],
      "interfaces": "C14 PromptLookup接口；4gram索引、向前最多12token、每查询64候选、32MiB/lane cap；候选有效性与最优召回分开。",
      "implementation": [
        "只读当前tokenized history；reset绑定epoch、append只处理committed新token。",
        "以独立慢速全扫描oracle验证候选有效性；hash碰撞逐token确认，候选上限写telemetry。",
        "测全256K索引构建和查找净成本，对比GPU全扫描决定是否另开优化，不默认GPU更快。"
      ],
      "tests": [
        "CrossEpoch：同slot被新请求/改写复用时不能返回旧suffix候选。",
        "CollisionAndOverlap：碰撞、同4gram多实例及重叠match均不越界且逐token真实匹配。",
        "BudgetTruth：全局早期候选可达；超64候选截断标记与oracle最优差异不伪报exact-search。"
      ],
      "test_target": "ninfer_prompt_lookup_test",
      "legacy_ids": [
        "P8-T03"
      ],
      "sources": "HQ02/NI03/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H1-T02.md"
    },
    {
      "id": "H1-T03",
      "phase": "H1",
      "kind": "task",
      "title": "实现连续前缀的head/tail融合",
      "owner": "Proposal",
      "depends_on": [
        "H1-T01"
      ],
      "modify": [],
      "create": [
        "src/runtime/generation/hybrid_proposal.h",
        "src/runtime/generation/hybrid_proposal.cpp",
        "tests/test_hybrid_proposal.cpp"
      ],
      "interfaces": "fuse(neural, LookupMatch, limits, history_epoch) -> ChainProposal；执行C14阈值/一致性/partial-head截断，K<=5。",
      "implementation": [
        "head替换与tail扩展分别决策，每位置记录来源；无条件7+8拼接禁止。",
        "不足长度的lookup只产真实连续prefix，不能用padding或不一致神经尾补齐。",
        "冻结实际确定性delta候选，不取神经softmax/selector score冒充q或窥视accept RNG；Target sampling复用原接受器并经H1-T07资格，C14是保守fusion策略而非采样数学必要条件。"
      ],
      "tests": [
        "ConsistentTail：[10,20,30]与同头[10,20,30,40,50]可拼尾，异头不得拼。",
        "PartialHead：[11]强匹配替换后不得接依赖旧prefix的[20,30]。",
        "BoundsAndSources：K=0/1/5及invalidID/epoch错时明确拒绝或短回退，source mask与有效长度一致。"
      ],
      "test_target": "ninfer_hybrid_proposal_test",
      "legacy_ids": [],
      "sources": "HQ02/NI03/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H1-T03.md"
    },
    {
      "id": "H1-T04",
      "phase": "H1",
      "kind": "task",
      "title": "接入共同verify与完整MTP对齐",
      "owner": "Runtime Integrator",
      "depends_on": [
        "H1-T02",
        "H1-T03"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/mtp_impl.h",
        "src/targets/qwen3_8/impl/runtime/speculative_target_impl.h",
        "src/targets/qwen3_8/impl/runtime/instantiate.h"
      ],
      "create": [
        "src/targets/qwen3_8/impl/runtime/hybrid_impl.h",
        "tests/targets/qwen3_8_27b/test_hybrid_align_real.cpp"
      ],
      "interfaces": "verify_hybrid_chain复用target_verify_accept/speculative_accept_greedy_drafts与preview/resolve/commit，alignment使用实际许可hidden；H1不跳过神经proposal，sampling资格由H1-T07补齐。",
      "implementation": [
        "gate内新增hybrid入口；保留旧mtp_decode_batch_body，当policyoff走原路。",
        "准备最终mixed候选frame并逐实际prefix维护current_extents/valid_columns/Target p/count overlay/hidden；不另造acceptance或sampler。",
        "逐一验证接受尾部与bonus对应的MTP位置、hidden选择和next anchor。"
      ],
      "tests": [
        "AlignmentAllCommitted：lookup接受数超过神经有效数时，所有已计算且许可hidden均正确对齐。",
        "BonusFrontier：全接受bonus已输出但hidden未计算时不提前写aux archive。",
        "GreedySameTarget：W4/5/6对ordinary同起始状态完整token序列一致。"
      ],
      "test_target": "ninfer_hybrid_align_real_test",
      "legacy_ids": [
        "P8-T02",
        "P8-T04"
      ],
      "sources": "HQ02/NI03/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H1-T04.md"
    },
    {
      "id": "H1-T05",
      "phase": "H1",
      "kind": "task",
      "title": "补齐多lane、取消和continuation回归",
      "owner": "Runtime QA",
      "depends_on": [
        "H1-T04"
      ],
      "modify": [],
      "create": [
        "tests/targets/qwen3_8_27b/test_hybrid_lifecycle_real.cpp"
      ],
      "interfaces": "使用原Program pending/resolve与row_commit；Lookup和feedback仅辅助，不拥有Target/GDN发布权。",
      "implementation": [
        "固定C1/2/4短宽同构batch，构造0/部分/全接受、cancel和RoundFault。",
        "通过L1/L2/L3恢复/中途历史改写验证token suffix和epoch重建。",
        "保持三协议tool流与bodytiming，可在fake状态unit层最小测试，阶段gate再跑GPU。"
      ],
      "tests": [
        "NoRejectedPublication：未许可token/record不能进入cache或SSE。",
        "LaneIsolation：活动lane重排/零长度padding不改变其他请求输出。",
        "RewriteWarmReuse：Target热缓存有效时aux冷重建成本可见且不退回完整Targetprefill。"
      ],
      "test_target": "ninfer_hybrid_lifecycle_real_test",
      "legacy_ids": [
        "P8-T04"
      ],
      "sources": "HQ02/NI03/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H1-T05.md"
    },
    {
      "id": "H1-T06",
      "phase": "H1",
      "kind": "task",
      "title": "建立低宽度MTP/Lookup资格候选",
      "owner": "Bench",
      "depends_on": [
        "H1-T04",
        "H1-T05",
        "H1-T07"
      ],
      "modify": [],
      "create": [
        "tests/targets/qwen3_8_27b/test_hybrid_e1_real.cpp"
      ],
      "interfaces": "A0/A1/A2单因素对比；E1只表示候选，未完成H5前不生产启用。",
      "implementation": [
        "按plans/06预登记相关32K/128K/248K copy/noncopy小集，阶段≤240相关A/B请求；生产Target sampling同参数对比，Target-greedy单列诊断，正式p95/CI集中H5。",
        "比较MTP3/4/5与相同W的Lookup，不把宽度变化也算Lookup单因素。",
        "记录无收益情况和适用桶；不满足资源/正确性则禁用候选。"
      ],
      "tests": [
        "SameWidthAttribution：A1/A2的Target/KV/W/语料一致。",
        "TokenNotFrame：SSE合并不改变引擎已许可token ID计数与usage契约；不能重tokenize格式化输出代替计数。",
        "NoncopyGuard：无命中lookup不会强制长验证，额外CPU成本纳入结果。"
      ],
      "test_target": "ninfer_hybrid_e1_real_test",
      "legacy_ids": [
        "P8-T05"
      ],
      "sources": "HQ02/NI03/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H1-T06.md"
    },
    {
      "id": "H1-T07",
      "phase": "H1",
      "kind": "task",
      "title": "资格确定性草稿与Target sampling验收",
      "owner": "Sampling QA",
      "depends_on": [
        "H1-T04",
        "H1-T05"
      ],
      "modify": [],
      "create": [
        "tests/targets/qwen3_8_27b/test_hybrid_sampling_contract.cpp"
      ],
      "interfaces": "按design/11复用已有delta-draft accept/processor/RNG/preview/resolve/commit；不另造sampler。共同sampling硬合同为H1-T06前置，每个后续shape/profile仍需对应资格。",
      "implementation": [
        "先在P6真实树重定位并冻结已有接受器、processor/RNG及终止状态seam；补独立小词表精确参考，不把不全等价CPU reference当bitwise oracle。",
        "实现八组具名测试，覆盖实际mixed prefix、非top_k1 fractional接受/残差、处理器时序、support边界、bonus/stop/cancel与计数生命周期；仅复用现有runtime路径。",
        "分离同路径seed/state复现与普通/spec输出分布等价；冻结统计检验/功效，缺GPU/参考/组合证据保持OFF，合格前请求回原sampling，当前不实施引擎。"
      ],
      "tests": [
        "DeltaProposal：神经/Lookup/selector最终确定链逐位置q=delta，不用softmax/score或accept随机数挑候选。",
        "ConditionalMixedPrefix：替换头与保留/截断tail均按最终mixed prefix验证Target p，旧神经prefix的概率/hidden不可错用；C14保守策略独立。",
        "ProcessedTargetPrefix：复用实际温度/支持集/penalty顺序与归一化；count=已安装历史+本列前候选overlay，无未来列污染。",
        "FractionalAcceptResidual：精确枚举p=(.6,.3,.1)、d=第二项及首拒/中拒/全接受；GPU覆盖非top_k1分数概率，拒绝残差屏蔽d后正确归一化。",
        "ZeroOneSupport：p(d)=0/1、support外token、top-k/p/min_p边界与tie/CDF边界不越界、不除零、不裁剪Target全域。",
        "BonusCommitStopCancel：all-accept bonus、budget1/2、EOS/stop/取消复用preview/resolve/commit；区分license计数与最终发布前缀，终止/重装后合法请求无污染。",
        "SeedDistributionVsPath：同路径完整state/seed可重复，eager/graph/restore/lane分别验证；ordinary/spec分布检验不强求跨路径同seed token相同。",
        "LegacyFallback：未资格组合默认OFF并回原合格sampling，原请求T/p/k/reasoning不变；fallback、Target-greedy和旧top_k1不计新sampling资格。"
      ],
      "test_target": "ninfer_hybrid_sampling_contract_test",
      "legacy_ids": [],
      "sources": "design/11; O speculative_round/sampling_device; sampling-contract evidence",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H1-T07.md"
    },
    {
      "id": "H1-GATE",
      "phase": "H1",
      "kind": "gate",
      "title": "现有W≤6的MTP＋Lookup统一评审验收",
      "depends_on": [
        "H1-T01",
        "H1-T02",
        "H1-T03",
        "H1-T04",
        "H1-T05",
        "H1-T06",
        "H1-T07"
      ],
      "status": "PENDING",
      "document": "plans/phases/H1.md"
    },
    {
      "id": "H2-T01",
      "phase": "H2",
      "kind": "task",
      "title": "校准中文/Java/工具调用草稿ID候选",
      "owner": "Data",
      "depends_on": [
        "H1-GATE"
      ],
      "modify": [],
      "create": [
        "tools/convert/qwen3_8_27b/calibrate_draft_vocab.py",
        "tests/hybrid/test_vocab_calibration.py"
      ],
      "interfaces": "calibrate_draft_vocab.py --manifest FILE --rows 40960,65536,98304,131072 --out DIR；输出合法ID映射、分桶覆盖、连续覆盖和split hashes。",
      "implementation": [
        "只用校准集真实输出ID计频；引用源码自然文本作为补充需独立标签。",
        "保留观察到的byte-fragment token和必选controlIDs，不能套用whole-UTF8筛法。",
        "固定locked-test，按会话/项目隔离，数据缺中文或工具桶即不允许选择小表。"
      ],
      "tests": [
        "ByteFragmentKept：由多个ID拼成中文字符的片段按频次可入选。",
        "CoveragePerBucket：不能用英文总体97.5%覆盖中文失效。",
        "LockedTestExcluded：评测ID出现在计数输入时fail。"
      ],
      "test_target": "test_vocab_calibration",
      "legacy_ids": [],
      "sources": "HQ01/HQ06",
      "mode": "python",
      "status": "PENDING",
      "document": "plans/tasks/H2-T01.md"
    },
    {
      "id": "H2-T02",
      "phase": "H2",
      "kind": "task",
      "title": "离线生成只读proposal-head companion",
      "owner": "Artifact",
      "depends_on": [
        "H2-T01"
      ],
      "modify": [],
      "create": [
        "tools/convert/qwen3_8_27b/build_proposal_head.py",
        "tests/hybrid/test_proposal_artifact.py"
      ],
      "interfaces": "C20 converter：--target FILE --ids FILE --calibration FILE --out FILE；保持Target字节不变，输出typed .ninfer descriptor+row map。",
      "implementation": [
        "复用原低位proposal布局与离线packing，不量化Target主体、不加入GGUF运行时。",
        "manifest验证domain/rowcount/scales/checksum，tmp文件全部通过后最后发布索引。",
        "测试kill/重复执行恢复，旧proposal文件未完成前仍可用。"
      ],
      "tests": [
        "TargetUnchanged：转换前后Target SHA256完全一致。",
        "MapRejection：重复/负/超域/paddingID与缺scale均拒绝。",
        "AtomicPublish：中断在tensor写入后时不能留下可见半成品manifest。"
      ],
      "test_target": "test_proposal_artifact",
      "legacy_ids": [],
      "sources": "HQ06/V2 N02",
      "mode": "python",
      "status": "PENDING",
      "document": "plans/tasks/H2-T02.md"
    },
    {
      "id": "H2-T03",
      "phase": "H2",
      "kind": "task",
      "title": "绑定closed head profile与Graph身份",
      "owner": "Artifact Integrator",
      "depends_on": [
        "H2-T02"
      ],
      "modify": [
        "src/targets/qwen3_8_27b/impl/variant.h",
        "src/targets/qwen3_8_27b/impl/variant.cpp",
        "src/targets/qwen3_8/impl/runtime/graph_impl.h"
      ],
      "create": [
        "src/targets/qwen3_8_27b/impl/load/proposal_head_bindings.h",
        "src/targets/qwen3_8_27b/impl/load/proposal_head_bindings.cpp",
        "tests/targets/qwen3_8_27b/test_proposal_binding.cpp"
      ],
      "interfaces": "ProposalHeadProfile启动期选择四种closed rows；Tensor view/map与proposal fingerprint绑定，不改Target输出projection。",
      "implementation": [
        "解析--proposal-head，缺失则用原131072head；外来指纹明确拒绝。",
        "检查真实allocated/reserved是否释放旧head，graph不能绑旧地址。",
        "proposal变化使aux状态失效但不无故取消Target缓存身份；snapshot兼容按C13处理。"
      ],
      "tests": [
        "TargetVocabFull：Target logits仍完整token_domain，无draft shortlist裁剪。",
        "GraphIdentity：换head或resource_generation后不能命中旧图。",
        "MemoryActual：同驻旧head时报告额外成本，不能声称理论净节约。"
      ],
      "test_target": "ninfer_proposal_binding_test",
      "legacy_ids": [
        "P10-T06"
      ],
      "sources": "HQ06/NI02",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H2-T03.md"
    },
    {
      "id": "H2-T04",
      "phase": "H2",
      "kind": "task",
      "title": "验证proposal映射、完整输出与质量",
      "owner": "Numerics",
      "depends_on": [
        "H2-T03"
      ],
      "modify": [],
      "create": [
        "tests/targets/qwen3_8_27b/test_proposal_head_real.cpp"
      ],
      "interfaces": "针对4个rows profile逐ID映射；Target-greedy完整输出仅数值诊断，生产sampling各profile经delta-q/processor/state资格；miss只增加拒绝，不能裁剪Target输出域。",
      "implementation": [
        "用不同position的稀有token、中文碎片、Java泛型和JSON key生成参考。",
        "验证普通/optimized head在同Target下的完整输出，停止词正常传播。",
        "测试wrongdescriptor/资源ready丢失仅禁新profile，原MTP路径保留。"
      ],
      "tests": [
        "RareTargetToken：不在草稿词表的正确Target token仍能输出。",
        "MappingExact：row index不能直接当token ID。",
        "PerProfileExact：每个拟启用profile过Target-greedy完整输出诊断及生产sampling的H1-T07对应shape/processor/state资格，不要求ordinary与spec同seed逐token一致。"
      ],
      "test_target": "ninfer_proposal_head_real_test",
      "legacy_ids": [],
      "sources": "HQ02/NI03/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H2-T04.md"
    },
    {
      "id": "H2-T05",
      "phase": "H2",
      "kind": "task",
      "title": "用整轮成本选择词表而非coverage最大值",
      "owner": "Bench",
      "depends_on": [
        "H2-T04"
      ],
      "modify": [],
      "create": [
        "tests/hybrid/test_vocab_promotion.py"
      ],
      "interfaces": "select_vocab_profile(calibration, held_out, budget) -> explicit-profile.md；门槛见design/04，no adoption保留131072。",
      "implementation": [
        "比较head耗时、链首次miss、alignment及总roundwall；与H1同shape对照。",
        "固定各桶门槛，真实held-out仅运行最终候选，不遍历挑最好测试得分。",
        "冻结profile和采用理由，未来请求不自动按自然语言换词表。"
      ],
      "tests": [
        "CoverageNotTPS：高覆盖但head慢的profile不能仅因覆盖获选。",
        "BucketFloor：中文/Java/tools任一较原下降>0.5个百分点时拒绝通用默认。",
        "NoGainHonest：未达5%整轮改善时保持旧profile并记录NO_ADOPTION。"
      ],
      "test_target": "test_vocab_promotion",
      "legacy_ids": [],
      "sources": "HQ01/HQ06",
      "mode": "python",
      "status": "PENDING",
      "document": "plans/tasks/H2-T05.md"
    },
    {
      "id": "H2-GATE",
      "phase": "H2",
      "kind": "gate",
      "title": "中文/Java草稿词表与head companion统一评审验收",
      "depends_on": [
        "H2-T01",
        "H2-T02",
        "H2-T03",
        "H2-T04",
        "H2-T05"
      ],
      "status": "PENDING",
      "document": "plans/phases/H2.md"
    },
    {
      "id": "H3-T01",
      "phase": "H3",
      "kind": "task",
      "title": "冻结W8 frame及物理容量契约",
      "owner": "Runtime",
      "depends_on": [
        "H2-GATE"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/layouts.h",
        "src/targets/qwen3_8/impl/runtime/layouts_impl.h",
        "src/targets/qwen3_8/impl/runtime/workspace_recipe.h"
      ],
      "create": [
        "tests/test_chain_verify_layout.cpp"
      ],
      "interfaces": "ChainVerifyState逻辑K<=7/V<=8、物理W8，与MTP神经max5独立；物理B/W/B*W与valid列、record容量显式。",
      "implementation": [
        "列出所有Tensor/row/valid列，使用C10的K/V/physicalW/B/tokenrows完成shape closure与checked乘法。",
        "W1/4/5/6保留原合格profile，W8仅resources_ready和实际Target sampling/processor/state资格后准入；Target-greedy单列诊断，K1/2仍V2/3+W4。",
        "budget1用K0/W1、budget2最多K1/W4；实际O_eff/文本页与物理scratch分别预算，末token不再入KV；资源不足选合法短shape，不造固定正R或W2/3。"
      ],
      "tests": [
        "SeparateMaxima：MTP仍最多5神经草稿，外部K7/逻辑V8由物理W8验证。",
        "PhysicalRows：B4/W8按32物理token行，K1/2仍按物理W4而不是validV预算；B*W溢出拒绝。",
        "BoundaryBudget：剩余1/2/7/8token按O_eff/文本页和合法物理shape分别判断；padding无许可、bonus不多发，P超C拒绝与输出容量提前结束分开。"
      ],
      "test_target": "ninfer_chain_verify_layout_test",
      "legacy_ids": [
        "P9-T03"
      ],
      "sources": "NI01/NI04/HQ05",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H3-T01.md"
    },
    {
      "id": "H3-T02",
      "phase": "H3",
      "kind": "task",
      "title": "扩展W8完整KV Attention",
      "owner": "CUDA Attention",
      "depends_on": [
        "H3-T01"
      ],
      "modify": [
        "src/ops/launcher/gqa_attention_decode.cu",
        "src/ops/kernel/gqa_attention_decode_i8.cuh",
        "src/ops/kernel/gqa_attention_decode_bf16.cuh"
      ],
      "create": [
        "tests/ops/test_gqa_verify8.cpp"
      ],
      "interfaces": "existing GqaExecutionEnvelope/valid_columns；新增W8的BF16、INT8与合格rk4v4路由，不引入Triton。",
      "implementation": [
        "复用已有split-KV/rotated codec，调整8query tile与warp/register配置。",
        "遍历原context envelope边界，保证workspace取区间最大值。",
        "profile显示无收益时保留安全实现，不能用削减Target可见KV提速。"
      ],
      "tests": [
        "FullVisibleKV：第0/中/末端key均参与，tail mask因果正确。",
        "IndependentOracle：W8单/多lane与独立decode oracle容差一致。",
        "ScratchWritten：NaN填充scratch不被未初始化读取，padding行隔离。"
      ],
      "test_target": "ninfer_gqa_verify8_test",
      "legacy_ids": [
        "P9-T02"
      ],
      "sources": "HQ04/HQ05/NI01",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H3-T02.md"
    },
    {
      "id": "H3-T03",
      "phase": "H3",
      "kind": "task",
      "title": "扩展W8 GDN记录、许可与回放",
      "owner": "CUDA State",
      "depends_on": [
        "H3-T01"
      ],
      "modify": [
        "src/core/gdn_replay_records.h",
        "src/ops/linear_attention/gated_delta_net/recurrent.cu",
        "src/ops/linear_attention/gated_delta_net/recurrent.cuh"
      ],
      "create": [
        "tests/ops/test_gdn_verify8.cpp"
      ],
      "interfaces": "GdnReplayRecordSpec.width=8；接受数0..7，许可列来自原row commit，不包括拒绝尾状态。",
      "implementation": [
        "按真实operator实现定位记录/replay循环，保留FP32 persistent state。",
        "修补硬上界与vectorized访问，所有record容量按已冻结布局。",
        "对record row复用、跨layer offset和部分接受做串行oracle。"
      ],
      "tests": [
        "ReplayPrefixOnly：第j列拒绝后状态等于只提交前j个许可输入。",
        "LayerLaneIsolation：多层多lane的conv/key/value/gate地址不互相覆盖。",
        "FP32Retained：不得更改persistent GDN dtype以通过显存。"
      ],
      "test_target": "ninfer_gdn_verify8_test",
      "legacy_ids": [],
      "sources": "NI01/NI03",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H3-T03.md"
    },
    {
      "id": "H3-T04",
      "phase": "H3",
      "kind": "task",
      "title": "W8 MTP alignment与next-round闭环",
      "owner": "Runtime Integrator",
      "depends_on": [
        "H3-T02",
        "H3-T03"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/mtp_impl.h",
        "src/targets/qwen3_8/impl/runtime/hybrid_impl.h"
      ],
      "create": [
        "tests/targets/qwen3_8_27b/test_hybrid_verify8_real.cpp"
      ],
      "interfaces": "长lookup接受后的alignment范围从licensed列推导；与逐token teacher-forced MTP对照。",
      "implementation": [
        "对齐全部被许可且已计算Target hidden；必要时新增支持8列的alignment路径。",
        "处理bonus未计算hidden、output terminal与prepare next-round，避免一个token shift。",
        "原神经N保持3/4/5，外部K7不会增加神经AR循环到7。"
      ],
      "tests": [
        "Alignment8：全7候选接受后的next proposal状态与独立对齐一致。",
        "RejectEveryPosition：每个拒绝位置0..7后续多轮输出一致。",
        "NoARInflation：计数器证明没有无意生成7步神经草稿。"
      ],
      "test_target": "ninfer_hybrid_verify8_real_test",
      "legacy_ids": [],
      "sources": "NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H3-T04.md"
    },
    {
      "id": "H3-T05",
      "phase": "H3",
      "kind": "task",
      "title": "W8 Graph闭合与同构batch调度",
      "owner": "Graph",
      "depends_on": [
        "H3-T04"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/graph_impl.h",
        "src/targets/qwen3_8_27b/impl/variant.cpp",
        "src/runtime/engine/concurrent_executor.h"
      ],
      "create": [
        "tests/targets/qwen3_8_27b/test_hybrid_graph8_real.cpp"
      ],
      "interfaces": "C17 graph key及资源epoch；W8固定请求profile，不在本phase增加动态Sticky。",
      "implementation": [
        "startup预热W≤6与W8真实图，记录allocated/reserved和warm路径。",
        "同构group分别发射，小请求不默认padding到全W8；记录group调度公平性。",
        "宽度/context/资源key失配拒绝或已声明eager fallback，不无声走旧kernel。"
      ],
      "tests": [
        "GraphEagerExact：同shape eager/graph完整输出一致。",
        "RouteReached：W8测试必须命中W8kernel/图计数而非fallback。",
        "ShapeResourceKey：不同W/B/envelope/资源代次不得复用错误图。"
      ],
      "test_target": "ninfer_hybrid_graph8_real_test",
      "legacy_ids": [
        "P9-T03"
      ],
      "sources": "HQ02/HQ05",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H3-T05.md"
    },
    {
      "id": "H3-T06",
      "phase": "H3",
      "kind": "task",
      "title": "W8真实长上下文与业务资格",
      "owner": "Bench QA",
      "depends_on": [
        "H3-T05"
      ],
      "modify": [],
      "create": [
        "tests/targets/qwen3_8_27b/test_hybrid_w8_qualification.cpp"
      ],
      "interfaces": "W8资格包含数值、资源、C1/C2/C4适用范围；不合格时H4宽块分支不可开放。",
      "implementation": [
        "最小case验证128K copy/noncopy；阶段相关shape/state/processor硬合同及性能≤240相关A/B，H5集中拟发布profile正式资格。",
        "分别比较W6/W8同候选源与同W有无Lookup，避免归因混乱。",
        "状态正确而性能无益可标NO_ADOPTION；资源/数值失败保持BLOCKED/OFF。"
      ],
      "tests": [
        "LongActual：实际131072及253952输入覆盖，非仅max-context设置。",
        "BaselineQuality：Java编译/测试与tool schema不退化；W8生产sampling通过H1-T07对应组合，Target-greedy仅作诊断。",
        "NoDefaultWithoutGain：无净收益或不满足长上下文容量则不默认启用W8。"
      ],
      "test_target": "ninfer_hybrid_w8_qualification_test",
      "legacy_ids": [
        "P9-T04"
      ],
      "sources": "HQ02/NI03/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H3-T06.md"
    },
    {
      "id": "H3-GATE",
      "phase": "H3",
      "kind": "gate",
      "title": "W8完整链与Graph资格统一评审验收",
      "depends_on": [
        "H3-T01",
        "H3-T02",
        "H3-T03",
        "H3-T04",
        "H3-T05",
        "H3-T06"
      ],
      "status": "PENDING",
      "document": "plans/phases/H3.md"
    },
    {
      "id": "H4-T01",
      "phase": "H4",
      "kind": "task",
      "title": "冻结W16预算、frame与准入闭合",
      "owner": "Runtime",
      "depends_on": [
        "H3-GATE"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/layouts.h",
        "src/targets/qwen3_8/impl/runtime/layouts_impl.h",
        "src/targets/qwen3_8/impl/runtime/workspace_recipe.h"
      ],
      "create": [
        "tests/test_chain_verify16_layout.cpp"
      ],
      "interfaces": "K15/W16，只开放已通过W8前置的C1实验；仍保留N<=5。",
      "implementation": [
        "核验shape map的所有8→16消费者，特别logits/replay/entitlement/alignment。",
        "加入startup容量与Graph预算拒绝，不占用原P6保留headroom。",
        "记录W6/8/16实际物理开销，不按有效mask虚构省算。"
      ],
      "tests": [
        "WideNotMtp15：W16不能改变MTP神经上限。",
        "RowUnits16：token行容量与HQ05负例对应，不混seq单位。",
        "ExactCapacity：context及KVpool不能为通过W16启动被静默缩短。"
      ],
      "test_target": "ninfer_chain_verify16_layout_test",
      "legacy_ids": [],
      "sources": "HQ02/NI03/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H4-T01.md"
    },
    {
      "id": "H4-T02",
      "phase": "H4",
      "kind": "task",
      "title": "W16完整Attention与投影shape资格",
      "owner": "CUDA Attention",
      "depends_on": [
        "H4-T01"
      ],
      "modify": [
        "src/ops/launcher/gqa_attention_decode.cu",
        "src/ops/kernel/gqa_attention_decode_i8.cuh",
        "src/ops/kernel/gqa_attention_decode_bf16.cuh"
      ],
      "create": [
        "tests/ops/test_gqa_verify16.cpp"
      ],
      "interfaces": "W16 independent oracle，全KV，复用已覆盖smallT32的projection需证明真实route。",
      "implementation": [
        "测试8/16query tile并检查寄存器spill、occupancy及KV tile共享，不移植vLLM代码。",
        "若分两个W8导致Target算术变化，列为另一个实现候选独立验证，不偷换为W16同算法。",
        "保持其他dtype与W≤8路径无行为变化，profile小集只做task验证。"
      ],
      "tests": [
        "FullContext16：首/中/末页依赖与因果mask均正确。",
        "ProjectionRoute：所需projection/GQA均达到16列路径，无暗中fallback。",
        "NumericBound16：独立oracle+NaN scratch+边界shape通过原容差。"
      ],
      "test_target": "ninfer_gqa_verify16_test",
      "legacy_ids": [],
      "sources": "HQ02/NI03/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H4-T02.md"
    },
    {
      "id": "H4-T03",
      "phase": "H4",
      "kind": "task",
      "title": "W16 ReplaySSM和MTP alignment状态资格",
      "owner": "CUDA State",
      "depends_on": [
        "H4-T01"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/mtp_impl.h",
        "src/targets/qwen3_8/impl/runtime/hybrid_impl.h",
        "src/ops/linear_attention/gated_delta_net/recurrent.cu"
      ],
      "create": [
        "tests/targets/qwen3_8_27b/test_hybrid_state16_real.cpp"
      ],
      "interfaces": "许可前缀长度0..15、Target/aux frontier和bonus三者独立；不得只对齐尾token。",
      "implementation": [
        "先用逐token串行teacher-forced参考，再实施vectorized/分块alignment。",
        "覆盖每个拒绝位置及输出中途停止，archive/index仅append已提交值。",
        "在W6/W8/W16交替的固定测试schedule中验证多轮状态与输出。"
      ],
      "tests": [
        "AllRejectPoints16：0..15拒绝后KV/GDN/MTPfrontier符合原事务。",
        "BonusNotHidden：terminal bonus不能产生伪造projected feature。",
        "WidthSwitchExact：固定起始state下6→16→8与固定reference完整输出一致。"
      ],
      "test_target": "ninfer_hybrid_state16_real_test",
      "legacy_ids": [],
      "sources": "HQ02/NI03/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H4-T03.md"
    },
    {
      "id": "H4-T04",
      "phase": "H4",
      "kind": "task",
      "title": "实现每lane复制策略及安全反馈",
      "owner": "Policy",
      "depends_on": [
        "H4-T01"
      ],
      "modify": [],
      "create": [
        "src/runtime/generation/hybrid_policy.h",
        "src/runtime/generation/hybrid_policy.cpp",
        "tests/test_hybrid_policy.cpp"
      ],
      "interfaces": "C16状态机Short/Probe/Copy/Cooldown；2次新鲜成功进入、最多2步hold、真实拒绝立即退copy、1正常步刷新。",
      "implementation": [
        "QualifiedCostTable keyed by context/B/W/profile/cache path，只有估计cost至少改善5%才升级。",
        "反馈epoch/round/resource校验，event未完成不读取pinnedbuffer。",
        "首版复制模式仅C1；padding与其他请求flag不能改变本请求策略。"
      ],
      "tests": [
        "FreshEvidence：重复round_id、旧requestepoch或DMA未完成均不推进状态。",
        "RejectBeatsSticky：任何真实拒绝立即退出skip-proposal，不能hold宽模式掩盖。",
        "NoCrossLaneControl：A的复制状态不能让B改变宽度，C>1首版禁Copy。"
      ],
      "test_target": "ninfer_hybrid_policy_test",
      "legacy_ids": [],
      "sources": "HQ02/NI03/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H4-T04.md"
    },
    {
      "id": "H4-T05",
      "phase": "H4",
      "kind": "task",
      "title": "接入双宽度Graph及proposal-skip",
      "owner": "Graph Integrator",
      "depends_on": [
        "H4-T02",
        "H4-T03",
        "H4-T04"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/graph_impl.h",
        "src/targets/qwen3_8/impl/runtime/hybrid_impl.h",
        "src/runtime/engine/concurrent_executor.h"
      ],
      "create": [
        "tests/targets/qwen3_8_27b/test_hybrid_copy_graph_real.cpp"
      ],
      "interfaces": "host图外策略、双feedback/event、startup短/宽图；skip只跳神经proposal，保留mandatoryalignment。",
      "implementation": [
        "将旧耦合graph的hybrid分支分成可复用verify/align/propose图体，不重写原off路径。",
        "C1 copy run可省下一轮proposal，但拒绝后必须经历正常对齐/提案恢复。",
        "记录真实neural launches、alignment和Graphpool，不能只改控制flag而实际仍全算。"
      ],
      "tests": [
        "SkipIsReal：copy阶段proposal kernel计数减少，alignment计数按许可状态仍存在。",
        "GraphPolicyLive：host状态不会只在capture时运行一次。",
        "LateDMAReuse：cancel和lane回收后旧event完成不能污染新请求。"
      ],
      "test_target": "ninfer_hybrid_copy_graph_real_test",
      "legacy_ids": [],
      "sources": "HQ02/NI03/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H4-T05.md"
    },
    {
      "id": "H4-T06",
      "phase": "H4",
      "kind": "task",
      "title": "验证动态长块的实际适用边界",
      "owner": "Bench QA",
      "depends_on": [
        "H4-T05"
      ],
      "modify": [],
      "create": [
        "tests/targets/qwen3_8_27b/test_hybrid_copy_qualification.cpp"
      ],
      "interfaces": "显式copy profile候选，包含copy→解释→copy切换、long context、源耗尽及负例。",
      "implementation": [
        "用短/25K/128K/248K copy和noncopy对照，不将381作为验收目标。",
        "对固定W8、固定W16、dynamic、dynamic+skip做消融。",
        "把首次命中延迟、退出错步、alignment重同步与完整E2E纳入采用。"
      ],
      "tests": [
        "CopyEnds：复制结束/源耗尽后不持续浪费宽块，controller按新反馈退出。",
        "GreedyDynamicExact：所有动态schedule在冻结prefill下完整token相同。",
        "CostNotAcceptance：接受数更多但ms/committed更差时不promotion。"
      ],
      "test_target": "ninfer_hybrid_copy_qualification_test",
      "legacy_ids": [],
      "sources": "HQ02/NI03/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H4-T06.md"
    },
    {
      "id": "H4-GATE",
      "phase": "H4",
      "kind": "gate",
      "title": "W16、每lane策略与proposal-skip统一评审验收",
      "depends_on": [
        "H4-T01",
        "H4-T02",
        "H4-T03",
        "H4-T04",
        "H4-T05",
        "H4-T06"
      ],
      "status": "PENDING",
      "document": "plans/phases/H4.md"
    },
    {
      "id": "H5-T01",
      "phase": "H5",
      "kind": "task",
      "title": "低成本组合代码与数值最终审查",
      "owner": "Reviewer+Integrator",
      "depends_on": [
        "H4-GATE"
      ],
      "modify": [],
      "create": [
        "tests/targets/qwen3_8_27b/test_hybrid_combined_real.cpp"
      ],
      "interfaces": "组合H1–H4被资格的profiles，不把未资格W16纳入必然交付；继承B0/frontend/cache/tool保护账本。",
      "implementation": [
        "逐项检查原43定制文件/替代能力仍在，核对Target/模板/codec未漂移。",
        "在一个candidatecommit上重跑实际选择profile与offreference。",
        "公开API无新增默认负担；所有feature开关和资源解释一致。"
      ],
      "tests": [
        "RetentionAll：原定制保留账本没有未解释删除。",
        "CombinedCommit：数值、build与review绑定同一提交。",
        "UnsupportedOff：未合格width/vocab组合在资格表外明确不可启用。"
      ],
      "test_target": "ninfer_hybrid_combined_real_test",
      "legacy_ids": [
        "P12-T01"
      ],
      "sources": "HQ02/NI03/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H5-T01.md"
    },
    {
      "id": "H5-T02",
      "phase": "H5",
      "kind": "task",
      "title": "完整Java Agent和长上下文A/B/A",
      "owner": "Bench",
      "depends_on": [
        "H5-T01"
      ],
      "modify": [],
      "create": [
        "tests/hybrid/test_e1_release_matrix.py"
      ],
      "interfaces": "按design/07与plans/06对实际声明profile做正式任务wall、p95/CI；14档薄覆盖继承但不能替代拟发布长P/负载资格；工程8×3固定seed+2repo各1次=26任务/variant，C1/2/4按实际准入组合。",
      "implementation": [
        "对A0最终回归以及局部消融，冻结语料/编译/功耗/主机负载。",
        "锁定8题与2repo题目/工具/质量判定器、task/seed配对；统计token/轮、完成时间、耗尽及全部真实请求；repo未就绪保持NOT_RUN，不能宣布发布完整。",
        "低样本p95不作通过；失败/不确定如实计入，不给主观模型质量放水。"
      ],
      "tests": [
        "AgentOracle：编译、测试、工具schema从真实命令结果取得。",
        "ColdWarmSeparated：cold前缀0hit，warm不隐藏初始化成本。",
        "AdoptionThresholds：copy快但自由生成退化时只允许特定profile或全部拒绝。"
      ],
      "test_target": "test_e1_release_matrix",
      "legacy_ids": [
        "P12-T02"
      ],
      "sources": "HQ01/HQ05",
      "mode": "python",
      "status": "PENDING",
      "document": "plans/tasks/H5-T02.md"
    },
    {
      "id": "H5-T03",
      "phase": "H5",
      "kind": "task",
      "title": "发布不可变低成本profile并受控试运行",
      "owner": "Deployment",
      "depends_on": [
        "H5-T02"
      ],
      "modify": [],
      "create": [
        "docs/deployment/hybrid-e1-release.md"
      ],
      "interfaces": "镜像/参数/Target/proposal/policy/缓存namespace资格组成单一release；本次不执行。",
      "implementation": [
        "仅在已确定窗口排空旧服务；单卡依次启动候选，不共驻双27B。",
        "新缓存目录与原namespace分离，短smoke→long→limited真实流量。",
        "启动resolvedprofile/actualcontext与账本不一致即停止，不自动fit降级。"
      ],
      "tests": [
        "ReleaseIdentity：启动模型/镜像/policyhash与资格记录一致。",
        "NoSilentFit：不能通过改codec/context让profile运行。",
        "ControlledTraffic：流量切换前active=0且exportdrain完成。"
      ],
      "test_target": "deployment-e1",
      "legacy_ids": [
        "P12-T03",
        "P12-T04"
      ],
      "sources": "NI02",
      "mode": "manual",
      "status": "PENDING",
      "document": "plans/tasks/H5-T03.md"
    },
    {
      "id": "H5-T04",
      "phase": "H5",
      "kind": "task",
      "title": "实际回滚与低成本路线封版",
      "owner": "Deployment QA",
      "depends_on": [
        "H5-T03"
      ],
      "modify": [],
      "create": [
        "docs/deployment/hybrid-e1-rollback.md"
      ],
      "interfaces": "完成旧镜像+旧参数+旧缓存回切实证；H6资产阻断时仍有独立E1交付。",
      "implementation": [
        "执行一次排空/切回，不只验证脚本--help。",
        "用原Java/tool/热缓存smoke确认旧服务可继续，记录中断/恢复。",
        "明确E1适用profiles与未执行高级路线，关闭未采用开关。"
      ],
      "tests": [
        "RollbackTriplet：不是只关flag，旧三件套和schema真正恢复。",
        "ResumeWorks：回切后原真实请求/缓存恢复验证通过。",
        "ScopeTruth：未做DFlash2不能把E1命名为全融合完成。"
      ],
      "test_target": "rollback-e1",
      "legacy_ids": [
        "P12-T04",
        "P12-T05"
      ],
      "sources": "NI02",
      "mode": "manual",
      "status": "PENDING",
      "document": "plans/tasks/H5-T04.md"
    },
    {
      "id": "H5-GATE",
      "phase": "H5",
      "kind": "gate",
      "title": "低成本路线独立发布/回滚统一评审验收",
      "depends_on": [
        "H5-T01",
        "H5-T02",
        "H5-T03",
        "H5-T04"
      ],
      "status": "PENDING",
      "document": "plans/phases/H5.md"
    },
    {
      "id": "H6-T01",
      "phase": "H6",
      "kind": "task",
      "title": "冻结DFlash2资产并实现离线typed绑定",
      "owner": "Artifact",
      "depends_on": [
        "H5-GATE"
      ],
      "modify": [
        "src/targets/qwen3_8_27b/impl/config.h",
        "src/targets/qwen3_8_27b/impl/package.cpp"
      ],
      "create": [
        "tools/convert/qwen3_8_27b/convert_dflash2.py",
        "src/targets/qwen3_8_27b/impl/load/dflash2_bindings.h",
        "src/targets/qwen3_8_27b/impl/load/dflash2_bindings.cpp",
        "tests/hybrid/test_dflash2_artifact.py"
      ],
      "interfaces": "checkpoint immutable revision+tensor manifest+许可为前置；独立 .ninfer companion，typed DFlash2Config，不重用旧35B DFlash值。",
      "implementation": [
        "取得实际feature taps、layer/head/conv/selector/block参数与dtype，缺项停止。",
        "离线转换并验证Target/tokenizer/feature identity，descriptor与tensor exactshape一致。",
        "27B capability仅资产齐全及相应实现可用才启用；旧DFlash enum/路径不变。"
      ],
      "tests": [
        "AssetComplete：任何revision/license/tensor缺项都BLOCKED。",
        "GeometryBound：35B checkpoint或错误feature tap/hidden不允许作为27B。",
        "NoTargetMutation：转换不改变Target bytes、tokenizer或KVcodec。"
      ],
      "test_target": "test_dflash2_artifact",
      "legacy_ids": [
        "P10-T01"
      ],
      "sources": "V2 T03–T07/N01/N03",
      "mode": "python",
      "status": "PENDING",
      "document": "plans/tasks/H6-T01.md"
    },
    {
      "id": "H6-T02",
      "phase": "H6",
      "kind": "task",
      "title": "建立DFlash2逐层独立参考",
      "owner": "Numerics",
      "depends_on": [
        "H6-T01"
      ],
      "modify": [],
      "create": [
        "tools/reference/qwen3_8_27b/dflash2_reference.py",
        "tests/hybrid/test_dflash2_reference.py"
      ],
      "interfaces": "独立reference读取相同typed companion和represented输入，输出投影/conv/attention/selector与链token，禁止用candidate生成golden。",
      "implementation": [
        "按真实模型数学实现feature projection与dynamicconv、selector。",
        "分离低位权重表示误差与runtime误差；固定BF16/FP32累积参考。",
        "为block起点重置、batch边界、短有效K构造负例。"
      ],
      "tests": [
        "BlockReset：conv不跨两个请求的物理trained block。",
        "NeuralRowsTruth：消费K5不等于只算5物理mask，记录实际行数。",
        "IndependentExpected：修改candidate后reference不随之变化。"
      ],
      "test_target": "test_dflash2_reference",
      "legacy_ids": [
        "P10-T02"
      ],
      "sources": "HQ02/V2 T07",
      "mode": "python",
      "status": "PENDING",
      "document": "plans/tasks/H6-T02.md"
    },
    {
      "id": "H6-T03",
      "phase": "H6",
      "kind": "task",
      "title": "实现DFlash2动态卷积与selector算子",
      "owner": "CUDA Draft",
      "depends_on": [
        "H6-T01"
      ],
      "modify": [],
      "create": [
        "include/ninfer/ops/dflash2_conv.h",
        "include/ninfer/ops/dflash2_selector.h",
        "src/ops/dflash2/conv.cu",
        "src/ops/dflash2/selector.cu",
        "tests/ops/test_dflash2_ops.cpp"
      ],
      "interfaces": "Conv/selector从companion的真实结构推导；lattice输出是proposal score，非自动归一化的q。",
      "implementation": [
        "复用已合格linear/GQA算子，新增语义闭合的conv/selector，固定scratch。",
        "对多个物理block与valid列独立处理，不因verifyW16让草稿卷积越界。",
        "稳定tie规则、invalidtoken与selector topk边界测试，不引入tree。"
      ],
      "tests": [
        "ReferenceLayer：与独立reference逐层一致到冻结容差。",
        "NoCrossBlock：不同请求块的conv状态不互串。",
        "ScoresNotQ：确定性selector的实际q为delta，分数不冒充概率；Target sampling只在相应资格后开放，真正随机proposal无general-q合同仍OFF。"
      ],
      "test_target": "ninfer_dflash2_ops_test",
      "legacy_ids": [
        "P10-T03"
      ],
      "sources": "HQ02/V2 T07",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H6-T03.md"
    },
    {
      "id": "H6-T04",
      "phase": "H6",
      "kind": "task",
      "title": "实现feature捕获、ring和状态事务",
      "owner": "Runtime Draft",
      "depends_on": [
        "H6-T01"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/text_prefill_impl.h",
        "src/targets/qwen3_8/impl/runtime/speculative_target_impl.h"
      ],
      "create": [
        "src/targets/qwen3_8/impl/runtime/dflash2_state.h",
        "src/targets/qwen3_8/impl/runtime/dflash2_state_impl.h",
        "tests/targets/qwen3_8_27b/test_dflash2_state_real.cpp"
      ],
      "interfaces": "fixed ring与pending feature/frontier分离；只有已提交且已计算的Target feature注入。",
      "implementation": [
        "prefill/verify按真实tap捕获，不能把最后一层hidden假装为所有tap。",
        "为接受0/部分/全+bonus定义ring回滚、缺hidden与next anchor，和现有Target state生命周期连接。",
        "aux cache指纹/epoch与Targetcontinuation分离，缺aux可fallback而非长隐藏重算。"
      ],
      "tests": [
        "TapsExact：reference指定各层hidden与捕获列一致。",
        "CommitOnly：拒绝尾/未计算bonusfeature不进入ring。",
        "AuxMissVisible：Target热命中而draft冷时日志和fallback准确。"
      ],
      "test_target": "ninfer_dflash2_state_real_test",
      "legacy_ids": [
        "P10-T04"
      ],
      "sources": "NI03/V2 N04/T03",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H6-T04.md"
    },
    {
      "id": "H6-T05",
      "phase": "H6",
      "kind": "task",
      "title": "DFlash2进入统一fusion/verify/故障边界",
      "owner": "Runtime Integrator",
      "depends_on": [
        "H6-T02",
        "H6-T03",
        "H6-T04"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/hybrid_impl.h",
        "src/runtime/engine/concurrent_executor.h",
        "include/ninfer/types.h"
      ],
      "create": [
        "src/targets/qwen3_8/impl/runtime/dflash2_impl.h",
        "tests/targets/qwen3_8_27b/test_dflash2_hybrid_real.cpp"
      ],
      "interfaces": "request-level backend DFlash2 + C14逐位置fusion；使用已合格W集合，N来自trainedblock。",
      "implementation": [
        "将companion输出归一到ChainProposal，不复制Targetaccept算法。",
        "新backend先base/text、确定性delta提案+Target生产sampling；对应selector/width/processor/state资格前回原合格sampling，LoRA/media/decision保留原资格fallback。",
        "后端选择前检查ring ready与实际cache恢复cost，不在轮间下载/切权重。"
      ],
      "tests": [
        "SameTargetGreedy：DFlash2错误提案经Target后与reference完整输出一致。",
        "NNotW：W16时DFlash2仍按自己的trainedblock卷积/selector。",
        "FaultScope：proposal失败不污染Target；设备故障不伪装可恢复普通拒绝。"
      ],
      "test_target": "ninfer_dflash2_hybrid_real_test",
      "legacy_ids": [
        "P10-T05"
      ],
      "sources": "HQ02/NI03",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H6-T05.md"
    },
    {
      "id": "H6-T06",
      "phase": "H6",
      "kind": "task",
      "title": "草稿Graph、head与共驻资源消融",
      "owner": "Graph",
      "depends_on": [
        "H6-T05"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/graph_impl.h",
        "src/targets/qwen3_8/impl/runtime/workspace_recipe.h"
      ],
      "create": [
        "tests/targets/qwen3_8_27b/test_dflash2_graph_real.cpp"
      ],
      "interfaces": "所有ring/feature/selector/head/workspace图资源启动冻结；MTP和DFlash2是否共驻以budget验证，不作假设。",
      "implementation": [
        "比较实际低位companion与referencehead，proposal词表继续复用H2治理方法但参数独立。",
        "每graph key含draft fingerprint、physicaltrainedblock、W和资源代次。",
        "严格记录权重/额外dense fusedKV副本，不能只统计压缩文件。"
      ],
      "tests": [
        "GraphPointerStable：capture/replay不动态分配或换未绑定buffer。",
        "AllCopiesBudgeted：fusedKV/denseweights/head副本等实际驻留均计账。",
        "ProfileFallbackReady：MTP未ready时不能宣称无成本动态回退。"
      ],
      "test_target": "ninfer_dflash2_graph_real_test",
      "legacy_ids": [
        "P10-T06"
      ],
      "sources": "HQ02/V2 T03–T07",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H6-T06.md"
    },
    {
      "id": "H6-T07",
      "phase": "H6",
      "kind": "task",
      "title": "ring-only DFlash2资格与止损",
      "owner": "Bench QA",
      "depends_on": [
        "H6-T06"
      ],
      "modify": [],
      "create": [
        "tests/targets/qwen3_8_27b/test_dflash2_ring_qualification.cpp"
      ],
      "interfaces": "分别给正确性、GPU容量、性能、promotion结论；H7需要可工作的ring参考，不要求ring已成为默认。",
      "implementation": [
        "比较当前E1、DFlash2 ring及Lookup融合，按真实上下文和任务类别而非单峰值。",
        "24GB/262K资源不成立则主力profile不采用；可以保留明确标注的短ctx实验，不篡改目标。",
        "实验完整但性能不足可DECLINED继续H7；缺资产/数值失败则BLOCKED。"
      ],
      "tests": [
        "QualifiedScope：短ctx成功不能覆盖262K主力资格。",
        "PreparationCounted：冷/热draft准备和feature构建全部进入TTFT/E2E。",
        "ResearchVsPromotion：no gain与not run不同状态，不能混作PASS。"
      ],
      "test_target": "ninfer_dflash2_ring_qualification_test",
      "legacy_ids": [
        "P10-T07"
      ],
      "sources": "HQ04/V2 T08",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H6-T07.md"
    },
    {
      "id": "H6-GATE",
      "phase": "H6",
      "kind": "gate",
      "title": "原生27B DFlash2 bounded ring统一评审验收",
      "depends_on": [
        "H6-T01",
        "H6-T02",
        "H6-T03",
        "H6-T04",
        "H6-T05",
        "H6-T06",
        "H6-T07"
      ],
      "status": "PENDING",
      "document": "plans/phases/H6.md"
    },
    {
      "id": "H7-T01",
      "phase": "H7",
      "kind": "task",
      "title": "实现独立ProjectedG host archive",
      "owner": "Cache",
      "depends_on": [
        "H6-GATE"
      ],
      "modify": [],
      "create": [
        "src/runtime/cache/draft_feature_archive.h",
        "src/runtime/cache/draft_feature_archive.cpp",
        "tests/test_draft_feature_archive.cpp"
      ],
      "interfaces": "ProjectedGArchive按真实projection schema、Target/adapter/tokenizer/epoch/version命名；TargetKV不复用为DraftKV。",
      "implementation": [
        "只append许可且已计算的ProjectedG，固定host上限与回收策略。",
        "按页保存token范围与checksum，aux失效不破坏Targetcache。",
        "默认不把全部层DraftKV保存在GPU，全量host cost随context如实报告。"
      ],
      "tests": [
        "IndependentIdentity：不同feature/projection/adapter不互相恢复。",
        "CommittedArchive：拒绝尾与bonus缺hidden不写archive。",
        "HostCap：与L2/checkpoint/pinned预算共同超过64GBprofile时拒绝。"
      ],
      "test_target": "ninfer_draft_feature_archive_test",
      "legacy_ids": [
        "P11-T01"
      ],
      "sources": "V2 T03–T08/NI02",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H7-T01.md"
    },
    {
      "id": "H7-T02",
      "phase": "H7",
      "kind": "task",
      "title": "实现全局页摘要与两级检索oracle",
      "owner": "Retrieval",
      "depends_on": [
        "H6-GATE"
      ],
      "modify": [],
      "create": [
        "src/runtime/generation/draft_page_index.h",
        "src/runtime/generation/draft_page_index.cpp",
        "tests/test_draft_page_index.cpp"
      ],
      "interfaces": "global page256→top32page→refine chunk→retrieved≤512起始预算；oracle区分候选覆盖/检索质量/Target正确性。",
      "implementation": [
        "索引覆盖全部已归档页，不仅最近4096×16token；记录所有页的可候选性。",
        "用确定性低成本摘要建立CPU参考，预算控制选择数量而非默默截历史开头。",
        "平局顺序与页内位置固定，晚到新页更新epoch一致。"
      ],
      "tests": [
        "GlobalCoverage：0/25/50/75/尾页均可选，最近65K截断mutation必须失败。",
        "BudgetedSelection：返回数量不超过预算且不重复/越范围。",
        "NotConstantMemory：索引随页数增长的字节真实计账，不能标O1总内存。"
      ],
      "test_target": "ninfer_draft_page_index_test",
      "legacy_ids": [
        "P11-T02"
      ],
      "sources": "V2 T06/T10",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H7-T02.md"
    },
    {
      "id": "H7-T03",
      "phase": "H7",
      "kind": "task",
      "title": "GPU检索、DraftKV重建与位置映射",
      "owner": "CUDA Retrieval",
      "depends_on": [
        "H7-T01",
        "H7-T02"
      ],
      "modify": [],
      "create": [
        "src/ops/draft_retrieval/select.cu",
        "src/ops/draft_retrieval/reconstruct.cu",
        "src/ops/draft_retrieval/stage.cu",
        "tests/ops/test_draft_retrieval.cpp"
      ],
      "interfaces": "按companion投影从ProjectedG生成各层DraftK/V；复制/re-RoPE策略绑定identity；Target全KV不变。",
      "implementation": [
        "对已选全局token重建局部K/V，参考tqLLM方法但用NInfer typed views。",
        "检查old position→staging position的旋转及真实rope参数，不能直接把Targetpos解释成draftpos。",
        "固定recent+retrieved有效mask，所有GPUwrite/read容量进账。"
      ],
      "tests": [
        "ReconstructionReference：与独立逐层DraftKV计算比较。",
        "PositionIdentity：相同内容不同映射不能误命中旧stage。",
        "TargetUntouched：retrieval选择不改变Target可见KV或GDN状态。"
      ],
      "test_target": "ninfer_draft_retrieval_test",
      "legacy_ids": [
        "P11-T03"
      ],
      "sources": "V2 T06/T10",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H7-T03.md"
    },
    {
      "id": "H7-T04",
      "phase": "H7",
      "kind": "task",
      "title": "异步refresh、双staging与事件隔离",
      "owner": "Graph",
      "depends_on": [
        "H7-T03"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/dflash2_impl.h"
      ],
      "create": [
        "src/targets/qwen3_8/impl/runtime/draft_refresh.h",
        "src/targets/qwen3_8/impl/runtime/draft_refresh_impl.h",
        "tests/targets/qwen3_8_27b/test_draft_refresh_real.cpp"
      ],
      "interfaces": "refresh在graph外，双stage各自event；仅completed同epochstage可切换。",
      "implementation": [
        "预分配staging指针，copy/重建完成事件连接Draft图，不做每轮强同步。",
        "成本高或没刷新完成使用上一合格stage/只ring，不能读取半写buffer。",
        "请求cancel/slot复用递增epoch，迟到任务回收其lease，不污染新owner。"
      ],
      "tests": [
        "LateRefresh：旧request DMA完成不能推进新请求stage。",
        "GraphStillUsed：启用retrieval后Draft真实Graph计数仍可验证，不能只声称固定shape。",
        "StagingFallback：超预算/超时回ring并记录，不偷偷fullDraftKV。"
      ],
      "test_target": "ninfer_draft_refresh_real_test",
      "legacy_ids": [
        "P11-T04"
      ],
      "sources": "V2 T03/T06/HQ03",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H7-T04.md"
    },
    {
      "id": "H7-T05",
      "phase": "H7",
      "kind": "task",
      "title": "串接L1/L2/L3、重写及slot生命周期",
      "owner": "Cache Integrator",
      "depends_on": [
        "H7-T04"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/program_impl.h",
        "src/targets/qwen3_8/impl/runtime/session_snapshot_impl.h"
      ],
      "create": [
        "tests/targets/qwen3_8_27b/test_draft_cache_lifecycle_real.cpp"
      ],
      "interfaces": "aux archive/snapshot版本化；Target热+aux冷、history rewrite、adapter变化均显式状态，不以session hint代替token identity。",
      "implementation": [
        "restore前核对不同层级身份及已提交frontier，辅助状态缺失可安全退回。",
        "复用已有export fence与hostlease语义，禁止另一条无边界cache publisher。",
        "slot erase/save/restore、mid-historyrewrite、并发session分桶验证。"
      ],
      "tests": [
        "AuxColdTargetHot：不为了建立Draftarchive隐藏重做完整Targetprefill。",
        "RewriteInvalidation：被改写页与后继projection/索引失效，之前前缀可保留。",
        "VersionRejected：不兼容旧snapshot明确拒绝，不按相同文件名误读。"
      ],
      "test_target": "ninfer_draft_cache_lifecycle_real_test",
      "legacy_ids": [
        "P11-T05"
      ],
      "sources": "NI02/V2 N08",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H7-T05.md"
    },
    {
      "id": "H7-T06",
      "phase": "H7",
      "kind": "task",
      "title": "将检索与恢复成本纳入后端选择",
      "owner": "Policy",
      "depends_on": [
        "H7-T05"
      ],
      "modify": [
        "src/runtime/generation/hybrid_policy.cpp",
        "src/serve/request_log.cpp"
      ],
      "create": [
        "tests/test_selective_draft_policy.cpp"
      ],
      "interfaces": "成本表包含archivebuild/restore/refine/reconstruct/PCIe/alignment/graphmiss；请求级选MTP或DFlash2，轮内仅同backend来源/width变化。",
      "implementation": [
        "分context/cache/activeB统计，使选择依赖实际ready而非写死100K阈值。",
        "检索改善接受但criticalpath变慢时降低refresh/退ring，不修改Target。",
        "以受控采样更新观测，不在locked测试中调参数挑胜者。"
      ],
      "tests": [
        "CostComplete：忽略PCIe/rebuild的mutation会被判为不完整输入。",
        "ReadyRequired：无resident/auxready的后端不能用0成本参与选择。",
        "NoSamplingShortcut：selective每个backend/selector/width/processor组合需Target sampling资格；greedy诊断、fallback或score不替代delta-q/状态证明。"
      ],
      "test_target": "ninfer_selective_draft_policy_test",
      "legacy_ids": [
        "P11-T06"
      ],
      "sources": "HQ04/V2 T08",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H7-T06.md"
    },
    {
      "id": "H7-T07",
      "phase": "H7",
      "kind": "task",
      "title": "全局检索长上下文端到端资格",
      "owner": "Bench QA",
      "depends_on": [
        "H7-T06"
      ],
      "modify": [],
      "create": [
        "tests/targets/qwen3_8_27b/test_selective_draft_qualification.cpp"
      ],
      "interfaces": "128K/192K/248K远端依赖、copy/noncopy、cache/rewrite矩阵；对比ring和E1两种baseline。",
      "implementation": [
        "种入早期页依赖，对比最近65K受限参考与global，报告candidatecoverage和任务质量。",
        "将所有host/GPU成本和峰值加入A/B/A，不只报告draftattention。",
        "无收益则保留ring/E1；完整Target、原质量与context门槛不可降。"
      ],
      "tests": [
        "FirstPageReachable：actual248K第0页依赖确实进入候选与测试。",
        "WholeTaskGain：只有draft局部快而E2E慢不promotion。",
        "StateRestoreQuality：跨回合恢复/重写后Target-greedy诊断、生产sampling的delta-q/processor/state与Java任务质量分别不退化。"
      ],
      "test_target": "ninfer_selective_draft_qualification_test",
      "legacy_ids": [
        "P11-T07"
      ],
      "sources": "V2 T06/T10",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H7-T07.md"
    },
    {
      "id": "H7-GATE",
      "phase": "H7",
      "kind": "gate",
      "title": "独立archive与全局selective drafting统一评审验收",
      "depends_on": [
        "H7-T01",
        "H7-T02",
        "H7-T03",
        "H7-T04",
        "H7-T05",
        "H7-T06",
        "H7-T07"
      ],
      "status": "PENDING",
      "document": "plans/phases/H7.md"
    },
    {
      "id": "H8-T01",
      "phase": "H8",
      "kind": "task",
      "title": "全融合所有权、来源与定制保留审查",
      "owner": "Reviewer+Integrator",
      "depends_on": [
        "H7-GATE"
      ],
      "modify": [],
      "create": [
        "docs/deployment/hybrid-v3-retention-review.md"
      ],
      "interfaces": "全部采用项对应来源/许可、实现、assertion与qualification；未采用/阻断列不改成已交付。",
      "implementation": [
        "审查唯一Targetverify/GDN/Output/continuation所有权，无双实现漂移。",
        "逐项回看P0–P6/旧32任务映射，所有删除或替代有证据。",
        "检查随机采样声明、幅度范围、支持ctx与模型资产，不从donor测试继承资格。"
      ],
      "tests": [
        "SingleAuthority：无绕过原accept或直接发布Lookuptoken。",
        "AllMapped：旧P7–P12每任务都有新owner/处置。",
        "AttributionComplete：搬入代码保留文件许可与修改说明，模型许可独立。"
      ],
      "test_target": "review-v3",
      "legacy_ids": [
        "P12-T01"
      ],
      "sources": "HQ01–HQ06/NI01–NI06",
      "mode": "manual",
      "status": "PENDING",
      "document": "plans/tasks/H8-T01.md"
    },
    {
      "id": "H8-T02",
      "phase": "H8",
      "kind": "task",
      "title": "最终组合数值、协议和状态矩阵",
      "owner": "QA",
      "depends_on": [
        "H8-T01"
      ],
      "modify": [],
      "create": [
        "tests/targets/qwen3_8_27b/test_hybrid_v3_final_real.cpp"
      ],
      "interfaces": "只对本次声明的supported matrix放行，生产Target T1/.95/k20/presence0/preserve-thinking/medium不变；C1不扩C4，Target-greedy资格不开放sampling，新组合未资格回原合格路径。",
      "implementation": [
        "用单candidatecommit覆盖ordinary/MTP/Lookup/DFlash2/selected所有采用profile。",
        "执行budget/stop/取消/RoundFault/rewrites/auxmiss/graph复用负例。",
        "协议兼容包括三协议工具流、计时schema、rawbody、输入严格UTF8与输出replacement既有语义。"
      ],
      "tests": [
        "MatrixComplete：所有对外声明组合都有测试，未测不能靠fallback假通过。",
        "NumericsAndQuality：L0–L3诊断、delta-q/processor/RNG/commit的实际sampling组合与旧业务质量门槛分别通过。",
        "FailureIsolation：负例后服务仍可处理后续合法请求或按原致命契约退出。"
      ],
      "test_target": "ninfer_hybrid_v3_final_real_test",
      "legacy_ids": [
        "P12-T02"
      ],
      "sources": "HQ02/NI03/NI04",
      "mode": "ctest",
      "status": "PENDING",
      "document": "plans/tasks/H8-T02.md"
    },
    {
      "id": "H8-T03",
      "phase": "H8",
      "kind": "task",
      "title": "最终性能、容量与采用profile选择",
      "owner": "Bench",
      "depends_on": [
        "H8-T02"
      ],
      "modify": [],
      "create": [
        "tests/hybrid/test_v3_promotion.py"
      ],
      "interfaces": "design/06–07冻结门槛；相对P6和E1均给原始结果，报告未获益桶和资源成本。",
      "implementation": [
        "按plans/06对实际采用profile串行最终A/B/A；14档薄覆盖不逐阶段展开，发布工程8×3+2及拟声明长P/非copy p95桶/配对CI独立资格。",
        "测累积taskwall、coldwarmTTFT、committed吞吐和graphmemory；禁止不同checkpoint直接排名。",
        "产出approved profiles和OFF/DECLINED列表，保留原配置可回滚。"
      ],
      "tests": [
        "NoPeakRanking：381或273不可替代同Target业务A/B。",
        "MemoryAndContext：实际主力262Kcontext及KVpool不缩减。",
        "PromotionExplicit：研究完成不等于默认启用，未达门槛保持OFF。"
      ],
      "test_target": "test_v3_promotion",
      "legacy_ids": [
        "P12-T02",
        "P12-T03"
      ],
      "sources": "HQ01/HQ04/HQ05",
      "mode": "python",
      "status": "PENDING",
      "document": "plans/tasks/H8-T03.md"
    },
    {
      "id": "H8-T04",
      "phase": "H8",
      "kind": "task",
      "title": "完整候选受控试运行及实机回滚",
      "owner": "Deployment",
      "depends_on": [
        "H8-T03"
      ],
      "modify": [],
      "create": [
        "docs/deployment/hybrid-v3-release.md",
        "docs/deployment/hybrid-v3-rollback.md"
      ],
      "interfaces": "新snapshot/auxarchive/cache目录隔离，restore旧三件套实际验证；当前文档任务不执行生产。",
      "implementation": [
        "确认目标窗口和服务身份，严格排空后单模型切换。",
        "limited流量覆盖已资格profile，异常立即按design/08退回。",
        "执行一次完整实际回滚，记录原业务恢复而非仅容器健康。"
      ],
      "tests": [
        "SnapshotIsolation：旧实例不读新schema/aux数据目录。",
        "OperationalRollback：旧镜像+配置+缓存实测恢复。",
        "NoUndeclaredChange：无换driver/功耗/权重/联网下载等未批准操作。"
      ],
      "test_target": "deployment-v3",
      "legacy_ids": [
        "P12-T04"
      ],
      "sources": "NI02",
      "mode": "manual",
      "status": "PENDING",
      "document": "plans/tasks/H8-T04.md"
    },
    {
      "id": "H8-T05",
      "phase": "H8",
      "kind": "task",
      "title": "证据封版与完成/阻断清单交付",
      "owner": "Integrator",
      "depends_on": [
        "H8-T04"
      ],
      "modify": [],
      "create": [
        "docs/deployment/hybrid-v3-handoff.md"
      ],
      "interfaces": "finalmanifest列code/GPU/production状态、git ancestry、profilehash、evidencehash；未实施项目保持NOT_RUN/BLOCKED。",
      "implementation": [
        "在最终commit运行failclosed gate和全部声明范围对应的tests。",
        "给出维护手册：如何新增profile、何时invalidate graph/cache、如何重校准词表。",
        "封版MD知识入口和release清单；不附模型/密钥/私有流量。"
      ],
      "tests": [
        "EvidenceComplete：commit/config/datahash和所有mandatoryassertions互相吻合。",
        "HistoricalNotCurrent：旧63helpertests和donor性能不计本版GPU资格。",
        "TruthfulScope：高级路线阻断时仅交付已合格E1，不宣称完整H8完成。"
      ],
      "test_target": "handoff-v3",
      "legacy_ids": [
        "P12-T05"
      ],
      "sources": "HQ05",
      "mode": "manual",
      "status": "PENDING",
      "document": "plans/tasks/H8-T05.md"
    },
    {
      "id": "H8-GATE",
      "phase": "H8",
      "kind": "gate",
      "title": "最终组合资格和受控发布统一评审验收",
      "depends_on": [
        "H8-T01",
        "H8-T02",
        "H8-T03",
        "H8-T04",
        "H8-T05"
      ],
      "status": "PENDING",
      "document": "plans/phases/H8.md"
    }
  ],
  "release_scopes": {
    "full": {
      "phase_sequence": [
        "P0",
        "P1",
        "P2",
        "P3",
        "P4",
        "P5",
        "P6",
        "H0",
        "H1",
        "H2",
        "H3",
        "H4",
        "H5",
        "H6",
        "H7",
        "H8"
      ],
      "dependency_overrides": {},
      "completion_label": "FULL_SCOPE"
    },
    "e1_w6": {
      "phase_sequence": [
        "P0",
        "P1",
        "P2",
        "P3",
        "P4",
        "P5",
        "P6",
        "H0",
        "H1",
        "H2",
        "H5"
      ],
      "dependency_overrides": {
        "H5-T01": [
          "H2-GATE"
        ]
      },
      "completion_label": "E1_ONLY_W6",
      "requires_scope_record": true
    },
    "e1_w8": {
      "phase_sequence": [
        "P0",
        "P1",
        "P2",
        "P3",
        "P4",
        "P5",
        "P6",
        "H0",
        "H1",
        "H2",
        "H3",
        "H5"
      ],
      "dependency_overrides": {
        "H5-T01": [
          "H3-GATE"
        ]
      },
      "completion_label": "E1_ONLY_W8",
      "requires_scope_record": true
    }
  },
  "revision": "SLIM_BASELINE_AND_DETERMINISTIC_PROPOSAL_TARGET_SAMPLING",
  "execution_contract": {
    "mode": "BASELINE_ONLY",
    "document": "plans/05-baseline-29-execution.md",
    "optimization_implementation_authorized": false,
    "b29_binary_baseline_before_p6": true,
    "baseline_is_not_phase_gate": true,
    "inherited_payloads": "IMMUTABLE_HISTORICAL_BYTES",
    "current_statistics_authority": "design/07-metrics-and-acceptance.md",
    "phase_dependencies": "H1_T07_SAMPLING_PREREQUISITE_ADDED; P6_AND_H5_PRODUCTION_GATES_RETAINED",
    "qualified_b29_performance_run": null,
    "core_cache_control": "ORIGINAL_ARGV_ACTUAL_CACHE_CLASSIFICATION_GAPS_PRESERVED",
    "core_no_prefix_reuse_enabled": false,
    "runtime_capacity_contract": "P<=C; O_eff=min(O,C-P+1); text_ceiling=P+max(O_eff-1,0); no fixed positive R",
    "measurement_scope": {
      "document": "plans/06-staged-evidence-budget.md",
      "catalog_cells": 672,
      "initial_core_requests": 174,
      "initial_special_requests": 104,
      "initial_http_requests": 278,
      "pi_fixed_requests": 44,
      "pi_repeats": 1,
      "pi_max_tokens": 32768,
      "initial_engineering_runs": 8,
      "initial_engineering_seed": 1701,
      "external_repo_runs": 2,
      "external_instances": [
        "google__gson-2158",
        "javaparser__javaparser-4561"
      ],
      "stage_related_ab_requests_max": 240,
      "publication_task_runs_per_variant": 26,
      "budget_is_not_qualification": true
    },
    "future_sampling_contract": {
      "document": "design/11-sampling-acceptance-and-proposal.md",
      "proposal": "DETERMINISTIC_DELTA",
      "target": "PRODUCTION_SAMPLING_UNCHANGED",
      "new_combinations": "OFF_UNTIL_QUALIFIED",
      "fallback": "EXISTING_QUALIFIED_SAMPLING",
      "target_greedy": "SEPARATE_NUMERICAL_DIAGNOSTIC",
      "implementation_status": "NOT_IMPLEMENTED"
    }
  }
}
```
