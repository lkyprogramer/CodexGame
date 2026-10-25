# V2 支撑材料：`data/tqllm/extension-tasks.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: data/tqllm/extension-tasks.json -->
<!-- payload-sha256: 57ac0873d3ec5e2d8536fdfee718425c03b7308cfea5e160dab678452bd7ee27 -->
<!-- payload-bytes: 88926 -->

<!-- payload-begin -->
````json
{
  "schema_version": 1,
  "delivery_kind": "PLAN_NOT_IMPLEMENTED",
  "phases": [
    {
      "id": "P7",
      "title": "冻结整合基线、资产、观测和资源预算",
      "description": "先证明优化对象和瓶颈，不把尚未合并的U当作合格P6。",
      "upstream_sha": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
      "gpu_required": true,
      "parallel_policy": "Freeze interfaces first; disjoint implementation files may run in parallel; CMake/public headers/Program integration are single-owner. One GPU serial queue.",
      "exit_criteria": "All required task outputs, integrated-commit review, non-skipped required tests and scoped GPU evidence; no default enablement without qualified profile.",
      "gate": "P7-GATE",
      "required_checks": [
        {
          "id": "SOURCE_ASSET_LOCK",
          "kind": "manual"
        },
        {
          "id": "BASELINE",
          "kind": "manual"
        },
        {
          "id": "SPEC_TELEMETRY",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_spec_perf_log_test$"
          ]
        },
        {
          "id": "GPU_PROFILE",
          "kind": "manual"
        },
        {
          "id": "BUDGET",
          "kind": "manual"
        },
        {
          "id": "REVIEW",
          "kind": "manual"
        },
        {
          "id": "ALL_PHASE_TARGETS",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_spec_perf_log_test$"
          ]
        }
      ]
    },
    {
      "id": "P8",
      "title": "MTP宽度策略与Prompt Lookup共用精确验证",
      "description": "先交付不需要新drafter权重的改进；不在此阶段谎报27B DFlash2对照。",
      "upstream_sha": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
      "gpu_required": true,
      "parallel_policy": "Freeze interfaces first; disjoint implementation files may run in parallel; CMake/public headers/Program integration are single-owner. One GPU serial queue.",
      "exit_criteria": "All required task outputs, integrated-commit review, non-skipped required tests and scoped GPU evidence; no default enablement without qualified profile.",
      "gate": "P8-GATE",
      "required_checks": [
        {
          "id": "BUILD",
          "kind": "manual"
        },
        {
          "id": "POLICY",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_speculation_policy_test$",
            "^ninfer_prompt_lookup_test$"
          ]
        },
        {
          "id": "VERIFY",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_external_draft_real_test$"
          ]
        },
        {
          "id": "LEGACY_REGRESSION",
          "kind": "manual"
        },
        {
          "id": "PERFORMANCE",
          "kind": "manual"
        },
        {
          "id": "REVIEW",
          "kind": "manual"
        },
        {
          "id": "ALL_PHASE_TARGETS",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_external_draft_real_test$",
            "^ninfer_mtp_width_real_test$",
            "^ninfer_prompt_lookup_test$",
            "^ninfer_speculation_policy_test$"
          ]
        }
      ]
    },
    {
      "id": "P9",
      "title": "已有完整KV验证的瓶颈优化",
      "description": "不裁剪Targetcontext，以有证据的热点选择最小算子/图优化。",
      "upstream_sha": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
      "gpu_required": true,
      "parallel_policy": "Freeze interfaces first; disjoint implementation files may run in parallel; CMake/public headers/Program integration are single-owner. One GPU serial queue.",
      "exit_criteria": "All required task outputs, integrated-commit review, non-skipped required tests and scoped GPU evidence; no default enablement without qualified profile.",
      "gate": "P9-GATE",
      "required_checks": [
        {
          "id": "BUILD",
          "kind": "manual"
        },
        {
          "id": "FULL_KV",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_gqa_attention_test$",
            "^ninfer_verify_envelope_test$",
            "^ninfer_mtp_width_real_test$"
          ]
        },
        {
          "id": "PROFILE_AND_NUMERICS",
          "kind": "manual"
        },
        {
          "id": "PERFORMANCE",
          "kind": "manual"
        },
        {
          "id": "REVIEW",
          "kind": "manual"
        },
        {
          "id": "ALL_PHASE_TARGETS",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_gqa_attention_test$",
            "^ninfer_mtp_width_real_test$",
            "^ninfer_verify_envelope_test$"
          ]
        }
      ]
    },
    {
      "id": "P10",
      "title": "原生27B DFlash2 companion与固定ring",
      "description": "先建立完整可验证的新drafter链，不同时引入全局检索和Token tree。",
      "upstream_sha": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
      "gpu_required": true,
      "parallel_policy": "Freeze interfaces first; disjoint implementation files may run in parallel; CMake/public headers/Program integration are single-owner. One GPU serial queue.",
      "exit_criteria": "All required task outputs, integrated-commit review, non-skipped required tests and scoped GPU evidence; no default enablement without qualified profile.",
      "gate": "P10-GATE",
      "required_checks": [
        {
          "id": "BUILD",
          "kind": "manual"
        },
        {
          "id": "ASSET_BINDING",
          "kind": "manual"
        },
        {
          "id": "DRAFT_OPS",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_dflash2_ops_test$",
            "^ninfer_dflash2_artifact_test$"
          ]
        },
        {
          "id": "DRAFT_REAL",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_dflash2_real_test$",
            "^ninfer_external_draft_real_test$"
          ]
        },
        {
          "id": "BUDGET_AND_PERFORMANCE",
          "kind": "manual"
        },
        {
          "id": "LEGACY_REGRESSION",
          "kind": "manual"
        },
        {
          "id": "REVIEW",
          "kind": "manual"
        },
        {
          "id": "INDEPENDENT_REFERENCE",
          "kind": "manual"
        },
        {
          "id": "ALL_PHASE_TARGETS",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_dflash2_artifact_test$",
            "^ninfer_dflash2_graph_test$",
            "^ninfer_dflash2_ops_test$",
            "^ninfer_dflash2_real_test$",
            "^ninfer_dflash2_state_test$",
            "^ninfer_external_draft_real_test$"
          ]
        }
      ]
    },
    {
      "id": "P11",
      "title": "全局草稿archive、选择、异步staging与图",
      "description": "在ringDFlash2的正确性、预算和基线测量已通过后，推进全局检索；ring尚无默认采用收益不阻断该实验。",
      "upstream_sha": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
      "gpu_required": true,
      "parallel_policy": "Freeze interfaces first; disjoint implementation files may run in parallel; CMake/public headers/Program integration are single-owner. One GPU serial queue.",
      "exit_criteria": "All required task outputs, integrated-commit review, non-skipped required tests and scoped GPU evidence; no default enablement without qualified profile.",
      "gate": "P11-GATE",
      "required_checks": [
        {
          "id": "BUILD",
          "kind": "manual"
        },
        {
          "id": "ARCHIVE_AND_INDEX",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_draft_archive_test$",
            "^ninfer_draft_page_index_test$"
          ]
        },
        {
          "id": "RETRIEVAL",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_draft_retrieval_test$",
            "^ninfer_draft_refresh_test$"
          ]
        },
        {
          "id": "LONG_REAL",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_dflash2_long_context_real_test$"
          ]
        },
        {
          "id": "CACHE_LIFECYCLE",
          "kind": "manual"
        },
        {
          "id": "BUDGET_AND_PERFORMANCE",
          "kind": "manual"
        },
        {
          "id": "REVIEW",
          "kind": "manual"
        },
        {
          "id": "ALL_PHASE_TARGETS",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_dflash2_long_context_real_test$",
            "^ninfer_draft_archive_test$",
            "^ninfer_draft_cache_lifecycle_real_test$",
            "^ninfer_draft_page_index_test$",
            "^ninfer_draft_refresh_test$",
            "^ninfer_draft_retrieval_test$",
            "^ninfer_selective_draft_policy_test$"
          ]
        }
      ]
    },
    {
      "id": "P12",
      "title": "最终集成审查、A/B/A与受控发布回滚",
      "description": "全套证据绑定最终commit与功能档位；本次交付的是这些步骤的计划，不自动执行生产变更。",
      "upstream_sha": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
      "gpu_required": true,
      "parallel_policy": "Freeze interfaces first; disjoint implementation files may run in parallel; CMake/public headers/Program integration are single-owner. One GPU serial queue.",
      "exit_criteria": "All required task outputs, integrated-commit review, non-skipped required tests and scoped GPU evidence; no default enablement without qualified profile.",
      "gate": "P12-GATE",
      "required_checks": [
        {
          "id": "SOURCE_AND_LICENSE_RETENTION",
          "kind": "manual"
        },
        {
          "id": "BUILD_MATRIX",
          "kind": "manual"
        },
        {
          "id": "FINAL_QUALITY",
          "kind": "manual"
        },
        {
          "id": "PERFORMANCE",
          "kind": "manual"
        },
        {
          "id": "GPU_RAW",
          "kind": "manual"
        },
        {
          "id": "CANARY",
          "kind": "manual"
        },
        {
          "id": "ROLLBACK",
          "kind": "manual"
        },
        {
          "id": "QUALIFICATION_SCOPE",
          "kind": "manual"
        },
        {
          "id": "REVIEW",
          "kind": "manual"
        },
        {
          "id": "FINAL_NATIVE_REGRESSION",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_dflash2_artifact_test$",
            "^ninfer_dflash2_graph_test$",
            "^ninfer_dflash2_long_context_real_test$",
            "^ninfer_dflash2_ops_test$",
            "^ninfer_dflash2_real_test$",
            "^ninfer_dflash2_state_test$",
            "^ninfer_draft_archive_test$",
            "^ninfer_draft_cache_lifecycle_real_test$",
            "^ninfer_draft_page_index_test$",
            "^ninfer_draft_refresh_test$",
            "^ninfer_draft_retrieval_test$",
            "^ninfer_external_draft_real_test$",
            "^ninfer_gqa_attention_test$",
            "^ninfer_mtp_width_real_test$",
            "^ninfer_prompt_lookup_test$",
            "^ninfer_qwen3_8_boundary_encoding_test$",
            "^ninfer_qwen3_8_encoding_restart_test$",
            "^ninfer_qwen3_8_frontend_test$",
            "^ninfer_qwen3_8_legacy_oracle_test$",
            "^ninfer_qwen3_8_tokenization_equivalence_test$",
            "^ninfer_qwen3_8_tokenizer_work_test$",
            "^ninfer_selective_draft_policy_test$",
            "^ninfer_spec_perf_log_test$",
            "^ninfer_speculation_policy_test$",
            "^ninfer_verify_envelope_test$"
          ]
        }
      ]
    }
  ],
  "tasks": [
    {
      "id": "P7-T01",
      "phase": "P7",
      "kind": "task",
      "title": "冻结P6基线、tqLLM来源与drafter资产契约",
      "owner": "Integrator + Artifact owner",
      "depends_on": [
        "P6-GATE"
      ],
      "modify": [
        "AGENTS.md"
      ],
      "create": [
        "docs/tqllm-adoption/source-lock.json",
        "docs/tqllm-adoption/source-license-ledger.json",
        "docs/tqllm-adoption/draft-asset-manifest.json"
      ],
      "interfaces": [
        "输入P6-GATE的真实source_commit；输出MERGED_BASE_SHA和固定T，所有新task从同一基线开工作树。",
        "C06先完整登记资产就绪状态/缺项：原revision、tensor shape/dtype/hash、特征时点、词表map、许可证；未知保持null且DFlash2不可用，P10-T01负责补齐后才准入。"
      ],
      "tests": [
        "SourcePin: P6-GATE.source_commit等于基线HEAD且包含O/U ancestry；变动HEAD拒绝。",
        "AssetInventory: 缺必需tensor/完整revision时记录asset_ready=false及缺项清单；重复id/错误Targetdomain拒绝资产；低风险P8/P9仍可进行。",
        "LicenseLedger: 所有拟复制文件对应T的path/blob/许可，第三方NOTICE和模型权重许可分开登记。"
      ],
      "implementation": [
        "读取实际P6集成树，重建符号清单；对T只做只读checkout，不merge无关历史。",
        "获取原始27B DFlash2 checkpoint完整revision和tensor inventory；本地asset盘只读，原文件hash入manifest。",
        "冻结C06 companion identity和资产状态清单；资产暂缺时明确高级路径BLOCKED，不猜参数；来源/基线与缺项完整登记可通过本inventory task，P10-T01不能据此越过资产门槛。"
      ],
      "verify": [
        "git merge-base --is-ancestor e0b05f7cb46adae2787be2ccbe605e1b0c9b3923 \"$MERGED_BASE_SHA\"",
        "git merge-base --is-ancestor 5b99996bc7c1fe6ff27f271a205eb605302ec8bb \"$MERGED_BASE_SHA\"",
        "git -C \"$TQLLM_REF\" rev-parse HEAD  # must equal 4d27324a124f92b7b7dcc554e6406ab6dc645b49"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "检查P6不是原方案模板PASS；不把源码1M常量当4090已验证能力；模型asset SHA不使用搜索结果短hash冒充。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P7-T02",
      "phase": "P7",
      "kind": "task",
      "title": "冻结实际长上下文与Java业务A/B语料",
      "owner": "Evaluation owner",
      "depends_on": [
        "P6-GATE"
      ],
      "modify": [
        "tools/bench/run_decode_scaling.py"
      ],
      "create": [
        "tools/bench/run_speculation_matrix.py",
        "tests/fixtures/speculation/cases.jsonl",
        "docs/tqllm-adoption/workload-manifest.json"
      ],
      "interfaces": [
        "消费P6 tokenizer/模板和实际部署profile；输出case_id→prompttokenhash/outputbudget/qualityoracle及A/B/A调度清单。",
        "C05轮日志和原HTTP/request日志均保留；新driver不得用tqLLM的不同Target数据做基线。"
      ],
      "tests": [
        "ActualTokens: 设置context262144但只有6000tokens的输入不得通过128K覆盖。",
        "OutputReserve: 253952prompt+2048output合法；超过实际max_context或共享KV entitlement拒绝，不能自动截prompt。",
        "FrozenQuality: Java expected来自冻结测试而非候选输出；同case改模板/权重hash拒绝配对。"
      ],
      "implementation": [
        "实现按真实token数构造混合代码/中文/工具文本case；各case关联位置不同的远端约束和编译/测试脚本。",
        "分别生成calibration和locked evaluation集合；后者至少30项Java任务，记录系统与工具命令、超时、判分。",
        "采集P6 None/MTP3/4/5适用配置的单卡串行A/B/A；未支持的组合不当作0性能，标UNSUPPORTED。"
      ],
      "verify": [
        "python3 tools/bench/run_speculation_matrix.py --help  # new driver",
        "python3 -m py_compile tools/bench/run_speculation_matrix.py"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "吞吐分母、prompt实际深度、冷/热cache与总Agentwalltime必须分开；不得重用已生成输出充当模型运行。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P7-T03",
      "phase": "P7",
      "kind": "task",
      "title": "增加采样式GPU阶段观测和稳定日志扩展",
      "owner": "Telemetry owner",
      "depends_on": [
        "P7-T01"
      ],
      "modify": [
        "include/ninfer/types.h",
        "src/serve/request_log.cpp",
        "src/serve/request_log.h",
        "src/targets/qwen3_8/impl/runtime/schedule.h"
      ],
      "create": [
        "src/runtime/generation/spec_perf.h",
        "tests/test_spec_perf_log.cpp"
      ],
      "interfaces": [
        "生产C05 extensions.spec_perf_v1；span包含关系和roundwall定义见设计03。",
        "Integrator独占公共字段与CMake落盘，worker仅修改新计时实现/测试。"
      ],
      "tests": [
        "CommittedCost: rounds(4tokens,20ms)+(1token,30ms)有效吞吐100tok/s，不得用3accepted得到60。",
        "Overlap: retrieval与verify重叠时roundwall只计关键路径；GPUevent未就绪不得序列化为0ms。",
        "LegacyLog: 原schema24/prepare_detail字段和值保留；未测量项为null/absent不伪造0，日志无原始prompt。",
        "OffPath: instrumentation关闭结果token完全相同；抽样开销有独立off/on实测。"
      ],
      "implementation": [
        "定义round计数/CPU时钟和CUDAevent池，默认不开逐层事件；每64轮抽样1轮为起始运维配置。",
        "插入draft/verify/GDN/commit/transfer和Graphhit观测；不在每层做device-wide sync。",
        "连接requestlog与本地性能sidecar，保留原log readers；用合成并发日志和真实GPUtrace交叉核对。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_spec_perf_log_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_spec_perf_log_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "区分空值与0；事件寿命必须晚于GPU完成；不得以计时开销抵消优化收益后改比较口径。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_spec_perf_log_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P7-T04",
      "phase": "P7",
      "kind": "task",
      "title": "建立实测资源账本和阶段采用门槛",
      "owner": "Performance + Runtime owner",
      "depends_on": [
        "P7-T01",
        "P7-T02",
        "P7-T03"
      ],
      "modify": [],
      "create": [
        "docs/tqllm-adoption/budget-measured.json",
        "docs/tqllm-adoption/profile-baseline.json",
        "docs/tqllm-adoption/adoption-criteria.json"
      ],
      "interfaces": [
        "消费C05原始trace与C06 geometry；输出各phase可用GPU/host预算，所有byte字段聚合口径固定。"
      ],
      "tests": [
        "BudgetNoGo: baselinepeak+新权重/ring/index/stage/graphs超过显存减512MiB预留时拒绝。",
        "ArchiveAccounting: 262144×5120×2=2.5GiB；原始5层12.5GiB不能当同大小；4lane不漏重复ring。",
        "NoSilentDowngrade: 不得改变Targetcodec/context或把TargetKV搬host使预算表通过。"
      ],
      "implementation": [
        "采集构造、warmup、最长prefill、4lane切换和cache恢复的分配峰值；draft未实现的份额先给上下界，不当实测。",
        "冻结P8/P9低风险5%walltime收益与P10/P11高风险128K≥15%采用线；继承原TTFT/decode回退规则。",
        "把瓶颈比例与C07archive可用host页数写入报告；P10设备预算在真正实现后重测，当前estimate不能预先授权启用。"
      ],
      "verify": [
        "python3 \"$PACK/scripts/tqllm_eval.py\" budget \"$TASK_OUT/budget-input.json\" --output \"$TASK_OUT/budget-output.json\""
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "reclaimed MTPslab必须有实际owner/bytes/释放证据；filebytes不能充当devicebytes。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P8-T01",
      "phase": "P8",
      "kind": "task",
      "title": "冻结策略、能力集合与新backend枚举",
      "owner": "Integrator",
      "depends_on": [
        "P7-GATE"
      ],
      "modify": [
        "include/ninfer/types.h",
        "src/serve/serve_options.cpp",
        "src/serve/serve_options.h",
        "src/targets/qwen3_8/impl/runtime/program.h"
      ],
      "create": [
        "src/runtime/generation/speculation_policy.h",
        "src/runtime/generation/speculation_policy.cpp",
        "tests/test_speculation_policy.cpp"
      ],
      "interfaces": [
        "实现C01 select_speculation原签名；新增--spec-policy FILE但默认不启用，启动前加载能力资源集合固定。",
        "输出C02 external frame准备契约；当前阶段DFlash2永远unqualified。"
      ],
      "tests": [
        "PolicyFilter: decision、non-greedy、adapter/media、unready/未加载backend只选合格fallback。",
        "CostChoice: output128时fixed20ms+0.01/token与fixed0+0.1/token选后者；output2048选前者。",
        "InvalidCalibration: NaN/负成本/缺项或Targethash不匹配拒绝auto，不能最小值选择0。"
      ],
      "implementation": [
        "按C01追加枚举并遍历所有switch/日志/选项，保留None/Mtp/DFlash数字与旧配置含义。",
        "新增profile解析及calibration key；选择只在lane/cache/bridge状态已知的请求开始进行。",
        "写资源能力及resolvedplan只读结构，冻结headers后交给P8并行worker，不提前填DFlashready。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_speculation_policy_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_speculation_policy_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "不能在请求热路径加载模型；固定--spec旧行为与错误码必须有回归。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_speculation_policy_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P8-T02",
      "phase": "P8",
      "kind": "task",
      "title": "MTP3/4/5完整shape与状态资格",
      "owner": "Runtime worker",
      "depends_on": [
        "P8-T01"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/layouts_impl.h",
        "src/targets/qwen3_8/impl/runtime/workspace_recipe.h",
        "src/targets/qwen3_8_27b/impl/variant.cpp"
      ],
      "create": [
        "tests/targets/qwen3_8_27b/test_mtp_width_real.cpp"
      ],
      "interfaces": [
        "消费C01 ResolvedSpeculationPlan；生产K对应verify4/5/6实际资源及graphprofile，不是假mask最大width。"
      ],
      "tests": [
        "WidthGeometry: K3/4/5的全部projection/attention/GDN/rowcommit形状合法；K6清晰拒绝。",
        "WidthExact: sameTarget普通与K3/4/5在greedy完整token序列一致，graph/eager均测。",
        "WidthBoundary: capacity尾部、0/部分/全接受、stop/取消时无越界和statefrontier错位。"
      ],
      "implementation": [
        "盘点原maxMTP5已有图/内存上限，尽量沿用已有profile；确实不支持的组合新增明确shape。",
        "核验跨请求K变化重新规划并使用对应图，活动请求不更换K；状态ready不足选择普通，不隐藏长prefill。",
        "记录实际launch/verifycols和显存，按131072/253952上下文用原Targetoracle验证。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_mtp_width_real_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_mtp_width_real_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "只看Attention宏1..6不够；frame/KV entitlement、MTPhead、GDN接受路径都检查。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_mtp_width_real_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P8-T03",
      "phase": "P8",
      "kind": "task",
      "title": "实现有界Prompt Lookup提案索引",
      "owner": "CPU worker",
      "depends_on": [
        "P8-T01"
      ],
      "modify": [],
      "create": [
        "src/runtime/generation/prompt_lookup.h",
        "src/runtime/generation/prompt_lookup.cpp",
        "tests/test_prompt_lookup.cpp"
      ],
      "interfaces": [
        "生产C02 PromptLookup reset/append/propose；只有tokenids，完全不拥有TargetKV或commit权力。"
      ],
      "tests": [
        "LookupMatch: ngram8→6→4优先，tie最新已提交历史；返回最多5tokens且后继范围合法。",
        "Collision: 哈希冲突、末尾匹配无后继、短文本、K0均不伪造提案。",
        "ScopeReset: 中途重写reset、会话/adapter切换不保留旧索引；取消草稿不append。"
      ],
      "implementation": [
        "实现每token增量索引，索引容量按冻结context上限固定；候选逐token确认。",
        "输出只读chain候选，不修改generationsampling或输出parser。",
        "添加预算耗尽关闭索引及统计reason，避免因重复日志导致O(N²)每轮全扫描。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_prompt_lookup_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_prompt_lookup_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "不能为了命中率检索其他会话；MTP/GDN状态不可由Lookupworker更新。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_prompt_lookup_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P8-T04",
      "phase": "P8",
      "kind": "task",
      "title": "外部提案共同验收与同构batch集成",
      "owner": "Integrator",
      "depends_on": [
        "P8-T02",
        "P8-T03"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/schedule.h",
        "src/targets/qwen3_8/impl/runtime/program_impl.h",
        "src/runtime/engine/concurrent_executor.h"
      ],
      "create": [
        "src/targets/qwen3_8/impl/runtime/external_draft_schedule.h",
        "src/targets/qwen3_8/impl/runtime/external_draft_schedule.cpp",
        "tests/targets/qwen3_8_27b/test_external_draft_real.cpp"
      ],
      "interfaces": [
        "实现C02 verify_external_chain，沿用existingTargetVerifyFrameView/target_verify_accept；唯一row许可与ReplaySSM提交。",
        "消费C01每请求plan并按backend/width组成同构subbatch，保留FIFO资格与公平轮转。"
      ],
      "tests": [
        "ExternalAccept: 错误Lookup首token立即修正；部分/全接受输出与ordinary一致，bonus最多一次。",
        "Transaction: 重复预测内容不绕过repetitionguard；取消/fault后lane和下一个请求可正常生成。",
        "MixedLanes: MTP与Lookup/None交错时token、usage、toolstream正确，不能串lane的GDN或adapter。"
      ],
      "implementation": [
        "将Lookupchain填入existingframe，不复制verifyaccept；缺命中ordinary轮应复用当前Targetstate。",
        "集成新plan入Program lifecycle，按已许可token更新Lookup与输出；测试注入所有接受长度。",
        "对mixedbackend/width子批次统计调度成本和queuep90，避免按一个路由无限drain队列。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_external_draft_real_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_external_draft_real_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "批次被拆分不意味着运行不变；完整检查unresolvedrow的RoundFault作用域。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_external_draft_real_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P8-T05",
      "phase": "P8",
      "kind": "task",
      "title": "低成本策略整体验证和E1候选",
      "owner": "Evaluation owner",
      "depends_on": [
        "P8-T04"
      ],
      "modify": [],
      "create": [
        "docs/tqllm-adoption/P8-qualification.json",
        "profiles/speculation-policy.json"
      ],
      "interfaces": [
        "输入P7冻结语料与P8 integratedcommit，产出候选profile；没有正收益保持featureoff。"
      ],
      "tests": [
        "SameTarget: baseline/candidate权重、codec、prompttokenhash一致；严禁引用外部TQ结果替代。",
        "EndToEnd: 对复制/长引用/低重复case报告walltime，Lookup失败开销不能从统计删除。",
        "DefaultSafety: policyoff时原P6行为不变；未资格的新路由不能进入生产manifest。"
      ],
      "implementation": [
        "在串行A/B/A运行None/MTP3/4/5/Lookup，不包含尚未开发的DFlash2。",
        "冻结选出的bucketcalibration并在独立lockedcorpus复验；保存全部请求失败与取消。",
        "满足原门槛且目标walltime≥5%改善才声明E1候选，否则featureoff并记录NO_GO，保留正确代码及报告。"
      ],
      "verify": [
        "python3 tools/bench/run_speculation_matrix.py --manifest \"$CORPUS\" --profile \"$PROFILE\" --out \"$TASK_OUT\"  # new driver after P7"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "source完成与E1性能采用分开；无收益不能通过修改case筛选伪造改善。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P9-T01",
      "phase": "P9",
      "kind": "task",
      "title": "固定完整验证数值oracle与优化点",
      "owner": "Numerics worker",
      "depends_on": [
        "P8-GATE"
      ],
      "modify": [
        "tests/ops/test_gqa_attention.cpp"
      ],
      "create": [
        "docs/tqllm-adoption/P9-hotspot-decision.json"
      ],
      "interfaces": [
        "消费C05 GPUtrace与N07 splitenvelope，输出唯一被优化的kernelroute或明确NO_CHANGE。"
      ],
      "tests": [
        "VerifyOracle: FA representedKV独立FP64参考覆盖rk4v4/INT8/BF16及width1/4/5/6，所有历史页必须可见。",
        "FirstDivergence: near-tiecase保存首次分歧前hidden/GDN/logits，不能仅比较最终自然语言。",
        "HotspotDecision: 没有可证主瓶颈不扩展kernel；NO_CHANGE需完整测量/理由不是skip。"
      ],
      "implementation": [
        "分析128K/248K下Targetattention、GDN、projection、drafter的关键路径份额。",
        "锁定split数量、KVtile复用、寄存器压力或launch开销中有证据的一项；定义before/after对照。",
        "扩展独立数值与历史针覆盖测试，冻结门槛后允许P9-T02优化。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_gqa_attention_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_gqa_attention_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "不得以Dustin稀疏近似替代本任务完整扫描；FP阈值先定后调优。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_gqa_attention_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P9-T02",
      "phase": "P9",
      "kind": "task",
      "title": "优化选定full-KV kernel或保持现状",
      "owner": "CUDA worker",
      "depends_on": [
        "P9-T01"
      ],
      "modify": [
        "src/ops/launcher/gqa_attention_decode.cu",
        "src/ops/kernel/gqa_attention_decode_i8.cuh"
      ],
      "create": [
        "docs/tqllm-adoption/P9-kernel-ablation.json"
      ],
      "interfaces": [
        "只消费existingKVlayout和执行envelope，不改变codec/Target语义；输出单一qualifiedroute或NO_CHANGE。"
      ],
      "tests": [
        "AllKeysVisible: 在最早/跨split/末页放针，任意key不能被稀疏裁掉。",
        "Determinism: 改tile/split时执行顺序与浮点变化按oracle检查，greedy差异不能默许。",
        "KernelBenefit: 报graph/eager以及SM时钟相同对照；不利profile不替换既有route。"
      ],
      "implementation": [
        "按热点决策实现一个有限变体；维持append/scale/逆旋转和掩码契约。",
        "若使用tqLLM思想或代码登记Tpath和NOTICE，不搬其GGUFKV格式。",
        "局部无收益时revert变体并交付NO_CHANGE测量报告，不为完成task强留代码。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_gqa_attention_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_gqa_attention_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "不能改变内存容量或减少可见页让算子看起来更快；所有数据拷贝记入总成本。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_gqa_attention_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P9-T03",
      "phase": "P9",
      "kind": "task",
      "title": "冻结verify图包络和资源生命周期",
      "owner": "Runtime worker",
      "depends_on": [
        "P9-T02"
      ],
      "modify": [
        "src/targets/qwen3_8_27b/impl/variant.cpp",
        "src/targets/qwen3_8/impl/runtime/layouts_impl.h"
      ],
      "create": [
        "tests/targets/qwen3_8/test_verify_envelope.cpp"
      ],
      "interfaces": [
        "生产C02共同验证所用graphenvelope；P10/P11继续复用，不自行改变Target算术。"
      ],
      "tests": [
        "EnvelopeEdges: 窗口128/160/512/4096/5000/8198/16390附近及128K/248K均满足launchcapacity。",
        "GraphFixed: resize/slotgeneration变更不能重放旧指针图，图上界内实际width符合task契约。",
        "NoFeatureTax: 新routeoff时原MTPworkspace/graph数量不增长；有分配必须计入资源账本。"
      ],
      "implementation": [
        "对变化route重新计算graph区间最大splitcapacity，输出可审查profile表。",
        "捕获eager/graph结果并跑state/prefix回归，保留旧正确fallback。",
        "总图缓存容量按P7预算，不使用request字符串产生无限键。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_verify_envelope_test ninfer_mtp_width_real_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_verify_envelope_test|ninfer_mtp_width_real_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "代码中的旧SM数量注释不是硬件测量；不可按注释固定4090最优参数。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_verify_envelope_test",
        "ninfer_mtp_width_real_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P9-T04",
      "phase": "P9",
      "kind": "task",
      "title": "完整验证优化的长上下文资格",
      "owner": "Evaluation owner",
      "depends_on": [
        "P9-T03"
      ],
      "modify": [],
      "create": [
        "docs/tqllm-adoption/P9-qualification.json"
      ],
      "interfaces": [
        "消费P7锁定corpus，输出E1升级资格或NO_CHANGE，随后才进入新drafter阶段。"
      ],
      "tests": [
        "LongActual: 131072/253952真实token输入及2048output可完成；大context短prompt不算覆盖。",
        "Quality: Java编译/测试/远端事实/工具调用与exact输出均不退化。",
        "NoGainNoDefault: walltime无5%收益的route不默认启用；若NO_CHANGE，证据仍完整。"
      ],
      "implementation": [
        "以同一合格P8作为增量基线并另报P6总收益，分离coldTTFT与warmdecode。",
        "检查sharedKV容量与并发尾延迟，重复A/B/A确认温度/时钟影响。",
        "冻结P9基线tag及允许feature清单，进入P10后不可悄悄换基线。"
      ],
      "verify": [
        "python3 tools/bench/run_speculation_matrix.py --manifest \"$CORPUS\" --profile \"$PROFILE\" --out \"$TASK_OUT\""
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "NO_CHANGE是审查结论，不是性能通过标签；最终默认profile必须引用实际候选。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P10-T01",
      "phase": "P10",
      "kind": "task",
      "title": "实现离线companion转换、typed绑定与只读模型view",
      "owner": "Artifact owner + Integrator",
      "depends_on": [
        "P9-GATE"
      ],
      "modify": [
        "src/targets/qwen3_8_27b/impl/package.cpp",
        "src/targets/qwen3_8_27b/impl/config.h",
        "src/serve/serve_options.cpp",
        "src/serve/serve_options.h"
      ],
      "create": [
        "tools/convert/qwen3_8_27b/convert_dflash2.py",
        "src/targets/qwen3_8_27b/impl/load/dflash2_bindings.h",
        "src/targets/qwen3_8_27b/impl/load/dflash2_bindings.cpp",
        "src/targets/qwen3_8/export/ninfer/targets/qwen3_8/dflash2_model_view.h",
        "tests/targets/qwen3_8_27b/test_dflash2_artifact.cpp"
      ],
      "interfaces": [
        "实现C06 companion model_id/weights_id、manifest校验与DFlash2ModelView；所有后续task消费这一个view。",
        "CLI新增--dflash2-artifact FILE并连接C01 capability集合；旧35B DFlash入口不变。"
      ],
      "tests": [
        "TypedInventory: wrongTargethidden/tokenizerhash/missingconv/selector/非法特征层和词表重复id均拒绝。",
        "NoRequantCascade: 默认从原始BF16单次量化，量化profile和tensorchecksum冻结；不默用TQ3再量化。",
        "NoFlagOnly: 无完整companion资产不能通过supported=true进入执行；Targetartifact字节不变。"
      ],
      "implementation": [
        "按P7原始manifest列出每矩阵布局/dtype，使用既有NInfer容器与量化布局离线转换。",
        "绑定显式DFlash2 view，完整核验feature时点/positions/convselector参数；unsupportedvariant返回明确错误。",
        "新资源仅在显式profilestartup加载，先仅CPU/metadata可用，GPU资格尚未通过前capability qualified=false。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_dflash2_artifact_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_dflash2_artifact_test)$'",
        "python3 -m py_compile tools/convert/qwen3_8_27b/convert_dflash2.py"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "模型名相同不代表tensor/feature协议相同；BF16reference不要求在24GB整套常驻，但生产量化后峰值必须测量。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_dflash2_artifact_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P10-T02",
      "phase": "P10",
      "kind": "task",
      "title": "建立独立DFlash2逐层reference和固定golden",
      "owner": "Numerical reference worker",
      "depends_on": [
        "P10-T01"
      ],
      "modify": [],
      "create": [
        "tools/reference/qwen3_8_27b/dflash2.py",
        "tests/targets/qwen3_8_27b/test_dflash2_reference.py",
        "tests/fixtures/dflash2/manifest.json"
      ],
      "interfaces": [
        "消费C06原始tensor与Target代表值/捕获协议，输出feature/G/KV/conv/lattice/chain逐层reference。",
        "reference只共享schema和输入数据，不import被测CUDAkernel或候选量化decode实现。"
      ],
      "tests": [
        "FeatureTap: pre/postlayer和norm前后错一个位置会命中失败golden。",
        "Lattice: 相同unary而不同前驱产生不同后继；tie按全域tokenid规则固定。",
        "ProjectedG: 同一G重建全部drafter层历史KV与直接注入reference一致，按dtype冻结数值准则。"
      ],
      "implementation": [
        "实现原始BF16/FP32数学reference，量化draft代表值通过独立反量化oracle进入第二组reference。",
        "构造块起始、短块边缘、多语言token、特殊token、0KV/长position的固定fixture。",
        "保存输入/资产/输出hash与误差规则，禁止从候选输出回填golden；CPU可分层低内存计算。"
      ],
      "verify": [
        "python3 -m unittest discover -s tests/targets/qwen3_8_27b -p test_dflash2_reference.py -v"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "tqLLM最终文字不是reference；本机不同Target权重产生的features不得直接求bitwise同值。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P10-T03",
      "phase": "P10",
      "kind": "task",
      "title": "实现DFlash2 dynamic-conv、selector和chain算子",
      "owner": "CUDA worker",
      "depends_on": [
        "P10-T01"
      ],
      "modify": [
        "src/CMakeLists.txt"
      ],
      "create": [
        "include/ninfer/ops/dflash2.h",
        "src/ops/dflash2/dynamic_conv.cu",
        "src/ops/dflash2/selector.cu",
        "src/ops/dflash2/chain.cu",
        "tests/ops/test_dflash2.cpp"
      ],
      "interfaces": [
        "消费DFlash2ModelView布局和C06语义；生产封闭Op：two-tapconv、top16、conditionedlattice、chain<=5。",
        "公共Op接受Tensor/WorkspaceArena/cudaStream_t，不读HTTP或缓存alias。"
      ],
      "tests": [
        "ConvTaps: 两侧dynamic+base、group映射与block边界符合独立CPU公式；不得带入Target4-tap GDNconv。",
        "SelectorTie: top16/lattice连续相等值选择确定，id映射不越过token域。",
        "OpIsolation: repeatbitidentity、eager/graph、无热路径allocation、输入未被意外覆写均检查。"
      ],
      "implementation": [
        "复用现有合格矩阵Op；只对缺的conv/selector/chain新增最窄实现，不大改所有weightformat。",
        "按T07数学语义编写CUDA，用明确attribution登记实际复制/改写函数；CMake由Integrator统一合入。",
        "与P10-T02独立reference对齐逐层误差；数值不满足先定位，不调松golden。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_dflash2_ops_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_dflash2_ops_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "lattice分数不得暴露为真实autoregressiveq；不存在的B/shape不能无条件泛化支持。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_dflash2_ops_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P10-T04",
      "phase": "P10",
      "kind": "task",
      "title": "feature捕获、ring、workspace与事务状态",
      "owner": "Runtime worker",
      "depends_on": [
        "P10-T01"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/text_context.h",
        "src/targets/qwen3_8/impl/runtime/text_context_impl.h",
        "src/targets/qwen3_8/impl/runtime/workspace_recipe.h",
        "src/targets/qwen3_8/impl/runtime/layouts_impl.h"
      ],
      "create": [
        "src/targets/qwen3_8/impl/runtime/dflash2_context.h",
        "src/targets/qwen3_8/impl/runtime/dflash2_context.cpp",
        "tests/targets/qwen3_8/test_dflash2_state.cpp"
      ],
      "interfaces": [
        "消费C06固定feature tap；生产C07所需projectedG及feature_frontier，但P10尚不提供hostarchive。",
        "ring、pendingfeatures、replay相关buffers由Program/arena拥有，generation/epoch独立。"
      ],
      "tests": [
        "CaptureCommit: 丢弃的verify候选G不进入可复用ring；bonus未forward时featurefrontier不虚增。",
        "RingWrap: 绕ring多次、短partialblock、边界rollback后visibleKV只对应合法原位置。",
        "BudgetLayout: rings按lane、scratch按同时存活、checkpoint/graphs逐项计费；超预算startup拒绝。"
      ],
      "implementation": [
        "在真实Targetprefill/verify已读取hidden时捕获指定特征，避免重复Target前向；feature时点匹配reference。",
        "G投影与alllayerK/V注入使用独立drafter权重，绝不读取TargetKV假装已准备。",
        "复用原pending/commit/fence寿命；旧Targetcachehit无drafterstate时返回unready，不自动全prompt重放。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_dflash2_state_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_dflash2_state_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "TargetFeaturelayer不是attentionlayerindex；tokenfrontier领先featurefrontier一行的情况必须有专门负例。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_dflash2_state_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P10-T05",
      "phase": "P10",
      "kind": "task",
      "title": "DFlash2单链进入共同验证、采样路由与故障边界",
      "owner": "Integrator",
      "depends_on": [
        "P10-T02",
        "P10-T03",
        "P10-T04"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/schedule.h",
        "src/targets/qwen3_8/impl/runtime/program_impl.h",
        "src/runtime/generation/speculation_policy.cpp"
      ],
      "create": [
        "src/targets/qwen3_8/impl/runtime/dflash2_schedule.h",
        "src/targets/qwen3_8/impl/runtime/dflash2_schedule.cpp",
        "tests/targets/qwen3_8_27b/test_dflash2_real.cpp"
      ],
      "interfaces": [
        "消费C06view、ring、Op和C02共同验收入口；生产DFlash2候选，不拥有第二套accept实现。",
        "C01第一版仅greedy/base/text ready请求开放，采样/adapter/media/decision按合格fallback表处理。"
      ],
      "tests": [
        "ChainExact: 强制0/1/K接受与bonus/stop边界，结果对相同Targetordinary逐token一致。",
        "UnsupportedFallback: 采样/LoRA/图像/无archive不得误入DFlash2，日志resolvedbackend与实际调用一致。",
        "FaultRecovery: Draft异常只放弃提案或请求，不污染下一轮Target/GDN；取消不发布未许可toolcall。"
      ],
      "implementation": [
        "保留trainedphysicalblock B，链取K3/4/5，再以width4/5/6调用共同verify。",
        "在Program事务成功后推进drafter已提交历史；保留未算bonusfeature的后续补齐逻辑。",
        "将第一次greedy差异的trace写入证据并阻断；不通过目标head只验top16来掩盖错误。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_dflash2_real_test ninfer_external_draft_real_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_dflash2_real_test|ninfer_external_draft_real_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "tqLLM声称exact不能作为本实现证明；CUDA差异需参考模型代表值而非自然语言容忍。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_dflash2_real_test",
        "ninfer_external_draft_real_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P10-T06",
      "phase": "P10",
      "kind": "task",
      "title": "固定ring图、草稿词表与head内存消融",
      "owner": "Performance worker",
      "depends_on": [
        "P10-T05"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/dflash2_schedule.cpp",
        "src/targets/qwen3_8_27b/impl/variant.cpp"
      ],
      "create": [
        "tests/targets/qwen3_8/test_dflash2_graph.cpp",
        "docs/tqllm-adoption/P10-head-graph-ablation.json"
      ],
      "interfaces": [
        "消费C01 resourcegeneration和C06tokenmap；生产finitephysicalshape图和head配置，不改Target完整词表。"
      ],
      "tests": [
        "GraphReplay: slotlayout/B/K/weightsgeneration改变后不复用错误图，graph/eager完全一致。",
        "PhysicalRows: 降K仅截候选时physicalB不变，报告不能虚称draftFLOPs按K减少。",
        "HeadAblation: 65536/131072/完整draft词表对比接受和成本，Target合法token不被draftmap裁掉。"
      ],
      "implementation": [
        "captureresource固定、warmupcoversshape，graph数量和额外head复本纳入预算。",
        "对词表map哈希/特殊token/尾部PAD规则写fixture，比较低precisiondraft与reference接受差距。",
        "并发首版只启用通过预算和混合lane资格的档位；未资格c4不能从c1外推。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_dflash2_graph_test ninfer_dflash2_real_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_dflash2_graph_test|ninfer_dflash2_real_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "批量性能不会自动优于拆分调用；不照抄tq256graph缓存上限。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_dflash2_graph_test",
        "ninfer_dflash2_real_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P10-T07",
      "phase": "P10",
      "kind": "task",
      "title": "固定ring DFlash2全量资格与24GB止损",
      "owner": "Evaluation + Runtime owner",
      "depends_on": [
        "P10-T06"
      ],
      "modify": [],
      "create": [
        "docs/tqllm-adoption/P10-qualification.json",
        "profiles/dflash2-ring-policy.json"
      ],
      "interfaces": [
        "输出E2采用决定及P11研究准入决定，两者分开；ringDFlash2与P9基线同Target/codec/实际tokens。"
      ],
      "tests": [
        "AssetMeasured: 发布资产revision、convertedhash、实际deviceweight/head/graph bytes完整可追溯。",
        "LongHotCold: 128K/248K cold、same-lanewarm、Target-onlyL2恢复的额外初始化成本均统计，不能删fallbackcase。",
        "AdoptionGate: 只有128K≥15%、248K原门槛、Agentwalltime及预算全部满足才能promotion=QUALIFIED；速度未达则DECLINED而不是伪造性能PASS。"
      ],
      "implementation": [
        "执行P7冻结矩阵与所有旧frontend/cache/toolstream回归，重点检查多轮状态留存。",
        "测startup/warmup/最长prefill/最大的并发峰值，禁止改Target权重或缩上下文解决OOM。",
        "预算/正确性未过则P10-GATE失败并保留E1；仅速度未达E2采用线但正确性/资源及基线测量完成时，记录promotion=DECLINED，允许P11研究，不默认启用ringDFlash2。"
      ],
      "verify": [
        "python3 tools/bench/run_speculation_matrix.py --manifest \"$CORPUS\" --profile \"$PROFILE\" --out \"$TASK_OUT\""
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "仅correctness通过不足以声称高性能可迁移；没有GPU时本task只能BLOCKED。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P11-T01",
      "phase": "P11",
      "kind": "task",
      "title": "独立ProjectedG host archive和版本化identity",
      "owner": "Archive worker",
      "depends_on": [
        "P10-GATE"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/dflash2_context.cpp"
      ],
      "create": [
        "src/targets/qwen3_8/impl/runtime/draft_archive.h",
        "src/targets/qwen3_8/impl/runtime/draft_archive.cpp",
        "tests/targets/qwen3_8/test_draft_archive.cpp"
      ],
      "interfaces": [
        "实现C07 DraftArchiveIdentity/Range及有界host页池；输出已提交G及featurefrontier，不复用Targetpayload。",
        "archiveappend(range,BF16bytes)的bytecount必须=token_count*draft_hidden*2；read返回lease，释放后才可逐页淘汰。"
      ],
      "tests": [
        "Reconstruct: 从G重建所有层draftKV等价于P10直接注入reference；任一层不满足阻断。",
        "Identity: draft/target/tokenizer/adapter/rope/profile/epoch任一不同不得复用；Targetcache仍可独立有效。",
        "BudgetLease: 总sessiontoken预算、未完成D2H、淘汰lease和迟到写入均不UAF，未许可G不发布。"
      ],
      "implementation": [
        "按C07保存projectedG而非原始5层features；同时保留metadata和featurefrontier。",
        "利用已有有界PinnedTransfer机制做分块D2H，hostarchive页可pageable，仅传输ringpinned。",
        "第一版仅进程内有效，不隐式向原Target L3序列化；冷启动archive缺失按fallback处理。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_draft_archive_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_draft_archive_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "bonustoken可能无feature；hostarchive有界不等于只用2.5GiB，多会话总量需测。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_draft_archive_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P11-T02",
      "phase": "P11",
      "kind": "task",
      "title": "全局页代表索引与两级CPU oracle",
      "owner": "Index worker",
      "depends_on": [
        "P10-GATE"
      ],
      "modify": [],
      "create": [
        "src/targets/qwen3_8/impl/runtime/draft_page_index.h",
        "src/targets/qwen3_8/impl/runtime/draft_page_index.cpp",
        "tests/targets/qwen3_8/test_draft_page_index.cpp"
      ],
      "interfaces": [
        "消费C07 identity和G重建K；输出所有合法logicalpage的代表/有效范围，coarse策略按设计05冻结。",
        "logicalpage256tokens与physicalKVpage分离；候选域不截last4096chunks。"
      ],
      "tests": [
        "OldestCoverage: 262144/1536产生16288合法16token远端chunks，index包含page0；强早期针必须可进入coarsetop8。",
        "PageOracle: 代表取最大L2的两条K，tie小position；不满页/空prefix/overwrite一致。",
        "Complexity: 输出记录page数量/bytes，随N增长O(N/256)；不得把整个索引宣称常数。"
      ],
      "implementation": [
        "固定reference的page代表与coarse聚合/归一化规则，先CPU独立实现并给随机case。",
        "页已填满时增量冻结代表，重写使边界页重建；索引覆盖所有archive有效页。",
        "在128K/248K加入第一、中央、最后页needle和同分确定性测试，不只复制tq6Kfixture。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_draft_page_index_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_draft_page_index_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "coarse代理可能降低接受率，正确排序不证明相关性；P11-T07真实任务必须验证。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_draft_page_index_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P11-T03",
      "phase": "P11",
      "kind": "task",
      "title": "GPU coarse/refine选择、按headstage与Draft位置映射",
      "owner": "CUDA worker",
      "depends_on": [
        "P11-T01",
        "P11-T02"
      ],
      "modify": [
        "include/ninfer/ops/dflash2.h"
      ],
      "create": [
        "src/ops/dflash2/retrieval.cu",
        "src/ops/dflash2/stage.cu",
        "tests/ops/test_draft_retrieval.cpp"
      ],
      "interfaces": [
        "消费C07pageindex和archiveG，生产固定head-specific最近/远端/anchorstage；TargetKV不变。",
        "C08virtualRoPE仅Draft；R32chunks、recent1536、anchor256为冻结首测profile而非不可调内核常数。"
      ],
      "tests": [
        "GlobalSelect: 最早页可选；coarse/refine按独立CPUoracle，ties、重复、partialchunk/padding屏蔽正确。",
        "Positions: 直接从G产生K并在virtualpos旋转，与reference对应；recent原位置不变，Targetpositionhash不变。",
        "Bounds: 每head<=32remotechunks，stagebuffer不越界；0remote/anchor重复/页淘汰均有定义。"
      ],
      "implementation": [
        "实现GPUcoarse页代表扫描和固定大小选择，回传最多top8页ids；禁止每轮传全attention矩阵。",
        "对worker回传G页重建各层K，在8页内按16tokenchunk refine，按head选择32chunk并排重。",
        "固定stage有效长度/mask，recent+anchor按同一policy构造；所有buffer在P11budget中计费。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_draft_retrieval_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_draft_retrieval_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "代理top8候选不能保留tq只看last4096的隐藏截断；RoPE不在已经旋转的低精度K上反复累积。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_draft_retrieval_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P11-T04",
      "phase": "P11",
      "kind": "task",
      "title": "图外异步刷新、双stage和迟到任务隔离",
      "owner": "Runtime worker",
      "depends_on": [
        "P11-T03"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/dflash2_schedule.cpp",
        "src/targets/qwen3_8/impl/runtime/workspace_recipe.h"
      ],
      "create": [
        "src/targets/qwen3_8/impl/runtime/draft_refresh.h",
        "src/targets/qwen3_8/impl/runtime/draft_refresh.cpp",
        "tests/targets/qwen3_8/test_draft_refresh.cpp"
      ],
      "interfaces": [
        "实现C08hostworker/ready-event/state-generation协议；固定stageA/B地址与两个有限graph入口。"
      ],
      "tests": [
        "LateResult: 刷新中取消、rewrite、adapter/lane变更后结果不得publish，lease全部释放。",
        "GraphBoundary: D2Hids/CPUarchive/H2D在图外，graph只捕获device计算；实现不得假装端到端CPUfree。",
        "RefreshFallback: deadline内未ready继续合法旧selection或recent-only，不同步阻塞Targetworker或读磁盘。"
      ],
      "implementation": [
        "实现每8round异步刷新起始策略，可通过冻结profile调整；只传pageids和G不传全文。",
        "记录generation/fence和占用的ringstage，完成event确认后切换active stage；预算不足不分配第三套缓冲。",
        "用延迟worker、强制淘汰和流完成重排做故障注入，再做graph/eager一致性。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_draft_refresh_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_draft_refresh_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "异步的确切不阻塞路径要看timeline；copy和compute重叠不能在成本里二次相加。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_draft_refresh_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P11-T05",
      "phase": "P11",
      "kind": "task",
      "title": "连接continuation、重写、slot与adapter生命周期",
      "owner": "Integrator",
      "depends_on": [
        "P11-T01",
        "P11-T04"
      ],
      "modify": [
        "src/targets/qwen3_8/impl/runtime/program_impl.h",
        "src/targets/qwen3_8/impl/runtime/prefix_identity.cpp",
        "src/targets/qwen3_8/impl/runtime/dflash2_context.cpp"
      ],
      "create": [
        "tests/targets/qwen3_8_27b/test_draft_cache_lifecycle_real.cpp"
      ],
      "interfaces": [
        "C07Targetidentity与Draftsidecar独立；L2/L3/slotrestore无Draft数据不改变Target复用资格。",
        "所有lane重写与P2异步export共用现有fence先后，archive异步任务不能在lane归还后读旧buffer。"
      ],
      "tests": [
        "TargetOnlyHit: 从原TargetL2恢复成功但Draftarchive缺失，选择MTP/None且无隐藏全prefill。",
        "RewriteScope: 改早期工具输出只能保留exactprefix页，边界页及后续Draft状态失效。",
        "LeaseIsolation: slot复用/adapter切换/restore/服务结束期间无跨identity读取或内存泄漏。"
      ],
      "implementation": [
        "在Program请求begin/retention/eviction/restore入口维护DraftIdentity和generation，复用已有缓存匹配语义。",
        "对缺archive/过期archive设置reason，不修改Targetaliaskind或旧payload版本。",
        "补全每条cancel/fault/shutdown的完成和lease回收，运行原prefix/cache/LoRA测试。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_draft_cache_lifecycle_real_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_draft_cache_lifecycle_real_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "一处invalidDraft不能强迫Target缓存coldreset；也不能以性能为由复用过期G。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_draft_cache_lifecycle_real_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P11-T06",
      "phase": "P11",
      "kind": "task",
      "title": "检索成本进入后端策略与观测",
      "owner": "Telemetry + Policy worker",
      "depends_on": [
        "P11-T05"
      ],
      "modify": [
        "src/runtime/generation/speculation_policy.cpp",
        "src/serve/request_log.cpp"
      ],
      "create": [
        "tests/test_selective_draft_policy.cpp",
        "profiles/dflash2-selective-policy.json"
      ],
      "interfaces": [
        "C01cost包含预计archive/refresh/init，C05记录原始关键路径和resolvedfallback；request开始选后端。"
      ],
      "tests": [
        "CostNotAcceptance: 接受率高但hostrefresh总时间更长时不选择selective，按committed/time而非acceptance决策。",
        "MissingHistory: 只有Targethit无Draftready时selective不被选为零成本路由。",
        "NoPolicyDrift: auto policy的校准/预算hash变更须新qualification，不在线偷偷换Target参数。"
      ],
      "implementation": [
        "给ringDFlash/selectiveDFlash分别登记costprofile，backendsame但retrievalpolicyid进入资源/日志identity。",
        "记录coverage、pagecount、refresh等待/丢弃、transferbytes、graphhit、archivemiss，原prepare_detail不删。",
        "对samecold/warm/rewrite输入做候选选择测试，避免按prompt长度硬选性能差路由。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_selective_draft_policy_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_selective_draft_policy_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "旧mtp-from只是静态阈值；新的成本策略是本次新增，不能声称源码已经实现自适应。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_selective_draft_policy_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P11-T07",
      "phase": "P11",
      "kind": "task",
      "title": "全局检索128K/248K远端依赖与端到端资格",
      "owner": "Evaluation owner",
      "depends_on": [
        "P11-T06"
      ],
      "modify": [],
      "create": [
        "tests/targets/qwen3_8_27b/test_dflash2_long_context_real.cpp",
        "docs/tqllm-adoption/P11-qualification.json"
      ],
      "interfaces": [
        "消费P7lockedcorpus，产出E3候选；包含P10ring-only和同TargetMTP/None各臂。"
      ],
      "tests": [
        "FarDependency: 第0页/中间/末尾不同Java签名及中文约束，selectedcoverage、greedy结果和编译测试同时证明。",
        "FullLifecycle: 全局检索在cold/L1/Target-onlyL2/rewrittenhistory/cancel/mixedload下都满足状态及无退化准则。",
        "RealGain: 128K≥15%增益、248K原门槛、真实Agentwalltime改善且24GB/64GB预算合格；无收益标NO_GO。"
      ],
      "implementation": [
        "执行recent-only、last65K原型覆盖对照、globalpage+archive、不同refresh间隔与预算的受控消融。",
        "对比固定8page/32chunk/1536recent起点，调参集选profile后锁定测试集只评最终配置。",
        "独立审阅所有bytes/事件/错误日志，明确索引近似只影响Draft提案，Target仍完整验证。"
      ],
      "verify": [
        "cmake --build \"$BUILD\" --target ninfer_dflash2_long_context_real_test",
        "ctest --test-dir \"$BUILD\" --show-only=json-v1 > \"$TASK_OUT/registered-tests.json\"",
        "ctest --test-dir \"$BUILD\" --output-on-failure --output-junit \"$TASK_OUT/results.xml\" -R '^(ninfer_dflash2_long_context_real_test)$'"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "不能把能找回needle当长时编码质量全部通过；编译/测试/工具协议和耗时必须并报。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [
        "ninfer_dflash2_long_context_real_test"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P12-T01",
      "phase": "P12",
      "kind": "task",
      "title": "最终来源、架构与原定制保留审查",
      "owner": "Independent reviewer + Integrator",
      "depends_on": [
        "P11-GATE"
      ],
      "modify": [
        "AGENTS.md"
      ],
      "create": [
        "docs/tqllm-adoption/final-retention.json",
        "docs/tqllm-adoption/final-license-ledger.json"
      ],
      "interfaces": [
        "消费原43项定制保留账本、原34上游commit与F01—F12借鉴账本，输出实际源码对应关系。"
      ],
      "tests": [
        "CustomPreserved: B0单一scanner/计数/计时/oracle/无权重镜像、原协议和cache行为无隐性替换。",
        "OneAuthority: Targetverify/rowcommit/ReplaySSM唯一，原35B DFlash语义未被27B路径覆盖。",
        "Provenance: 实际移植函数有immutableT出处/许可证/改写说明；模型asset单独许可核查。"
      ],
      "implementation": [
        "对最终分支完整diff做架构审查，不只看每个task的局部结论。",
        "检查未采用实验路径是否删掉或明确off并无默认内存税；同步真实AGENTS产品契约。",
        "review修改后由Integrator重新build相关矩阵；来源账本不能由“参考了tq”一句话代替。"
      ],
      "verify": [
        "git diff \"$MERGED_BASE_SHA\" HEAD --check",
        "git merge-base --is-ancestor 5b99996bc7c1fe6ff27f271a205eb605302ec8bb HEAD"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "保留的是用户行为与优化价值，不是重复旧实现；原E8不可以兼容别名回归。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P12-T02",
      "phase": "P12",
      "kind": "task",
      "title": "最终组合版本完整数值、业务与性能验收",
      "owner": "Evaluation owner",
      "depends_on": [
        "P12-T01"
      ],
      "modify": [],
      "create": [
        "docs/tqllm-adoption/final-quality.json",
        "docs/tqllm-adoption/final-performance.json"
      ],
      "interfaces": [
        "最终单一commit +profilehash +Target/draft资产hash与P7/P6baseline绑定；不可拼接不同commit通过记录。"
      ],
      "tests": [
        "FinalComposition: MTP/Lookup/DFlash2/global/graph组合在声明支持范围exact，non-greedy/adapter/media fallback原质量保留。",
        "ActualContextMatrix: 2K—248K实际tokens，单并发/部署并发，长输出、冷/热/重写/取消全部覆盖。",
        "AgentOutcome: 编译/测试/工具调用无新增失败，至少30冻结Java任务统计walltime和失败原因；达到采用线。"
      ],
      "implementation": [
        "在最终commit重跑所有必测，生成requiredCTest清单并校验无skip。",
        "按冻结矩阵A/B/A，原性能工具与新增roundcost并列；不通过最高tok/s选号。",
        "输出E1/E2/E3明确资格范围，未资格功能不能被finalreport默认包含。"
      ],
      "verify": [
        "python3 tools/bench/run_speculation_matrix.py --manifest \"$CORPUS\" --profile \"$PROFILE\" --out \"$TASK_OUT\""
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "pipeline overlap和resourcefootprint需实测；同source不同compiledflags也要绑定buildfingerprint。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P12-T03",
      "phase": "P12",
      "kind": "task",
      "title": "生成只读artifact与部署ready profile",
      "owner": "Deployment owner",
      "depends_on": [
        "P12-T01"
      ],
      "modify": [
        "Dockerfile.sm89-nobake"
      ],
      "create": [
        "deploy/tqllm-adoption/candidate-profile.json",
        "deploy/tqllm-adoption/rollback-profile.json",
        "deploy/tqllm-adoption/readiness.md"
      ],
      "interfaces": [
        "生产featureprofile必须只允许已通过资格的backend与请求组合；模型仍runtime只读挂载。"
      ],
      "tests": [
        "NoBake: 镜像不打包Target/draft权重，启动参数与assetfingerprint明确。",
        "NoSharedCache: 新旧实例不共享可写cache目录；Draftarchive进程内销毁不污染回滚。",
        "FailClosedStart: 错asset/license/profile/显存预算不足清楚拒绝，不能自动下载/缩context/改KV。"
      ],
      "implementation": [
        "在实验分支更新startup参数说明，保留原sm89/toolchain和新dependency锁。",
        "readycheck覆盖加载、warmup、真实短请求、graphshape和响应resolvedmodel，而不仅HTTP200。",
        "准备排空/停机/启动/恢复步骤；未获具体生产窗口授权不执行远端动作。"
      ],
      "verify": [
        "docker build -f Dockerfile.sm89-nobake -t \"$CANDIDATE_IMAGE\" .  # authorized local builder; no model copy"
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "两个27B实例单卡并跑不应成为默认bluegreen方案；所有步骤说明显存排空条件。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P12-T04",
      "phase": "P12",
      "kind": "task",
      "title": "获授权后的单卡试运行及实际回滚演练",
      "owner": "Deployment + Evaluation owner",
      "depends_on": [
        "P12-T02",
        "P12-T03"
      ],
      "modify": [],
      "create": [
        "docs/tqllm-adoption/canary-result.json",
        "docs/tqllm-adoption/rollback-result.json"
      ],
      "interfaces": [
        "输入具体部署授权、合格candidate/rollbackprofiles；输出真实试运行和回滚证据，不是脚本草案。"
      ],
      "tests": [
        "CanaryScope: 原服务排空后串行运行candidate，不越过授权主机/端口/时间窗口。",
        "RollbackWorking: 旧镜像+旧参数+旧cache恢复后真实生成/工具流/监控有效，不能只检查进程存在。",
        "Trigger: OOM/enginefailed/错误token/协议问题立即回滚；性能超原门槛按冻结观察窗口处理。"
      ],
      "implementation": [
        "核对主机/镜像/配置/模型指纹和当前负载；所有secret脱敏但不省略实际命令结果。",
        "完成同一轮候选smoke+受控流量，并按预设触发检查；不可无人看护地长期后台运行。",
        "实际切回旧合格档位并证明可用，再根据授权决定保留何档；无法部署时该taskBLOCKED。"
      ],
      "verify": [
        "# Deployment commands are resolved from the captured real environment; do not invent host/container names."
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "用户本次请求文档不等于授权当前机器生产切换；缺授权不得打勾。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P12-T05",
      "phase": "P12",
      "kind": "task",
      "title": "封版、机器门禁与开发/生产资格分离",
      "owner": "Integrator",
      "depends_on": [
        "P12-T04"
      ],
      "modify": [],
      "create": [
        "docs/tqllm-adoption/release-manifest.json",
        "docs/tqllm-adoption/release-notes.md"
      ],
      "interfaces": [
        "输出最终sourcecommit、compiledfingerprint、adoptiontier、全部gate和资产profile；status不混淆DOCS_READY与IMPLEMENTED/QUALIFIED。"
      ],
      "tests": [
        "EvidenceIdentity: reviewcommit/requiredchecks/运行结果与最终source一致；任一错hash/缺GPU/skip使gate失败。",
        "ExplicitScope: 未过的route/context/concurrency不出现在releaseenabled集合。",
        "Reproducibility: 包内链接/校验和/DAG完整；原计划历史证据不被改写成新GPU测试。"
      ],
      "implementation": [
        "补齐所有gate材料，在最终commit运行requiredtests并由独立reviewer确认。",
        "发布说明列出实际收益、适用profile、回退操作与未做项；不把研究15%门槛写成测量值。",
        "生成最终source/asset/config清单与可重跑命令，不自动push或改生产默认设置。"
      ],
      "verify": [
        "python3 \"$PACK/scripts/phase_gate.py\" --plan \"$PACK/plans/tasks.json\" --evidence \"$OUT/P12/phase-result.json\" --out \"$OUT/P12/gate.json\""
      ],
      "acceptance": [
        "Named assertions pass on the integrated commit; outputs and scope are reviewed; no missing input is counted as success."
      ],
      "review_focus": [
        "若P10/P11 NO_GO，单独发布E1/E2部分资格报告；不能把本P12全扩展gate改成可跳过前阶段。"
      ],
      "rollback": "保持上一合格release/profile；只在独立实验worktree修改，缺前置/预算或性能不满足时记录BLOCKED/NO_GO，不改旧golden。",
      "new_ctest_targets": [],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P7-GATE",
      "phase": "P7",
      "kind": "gate",
      "title": "统一代码review、完整集成测试与资源/性能门禁",
      "owner": "Independent reviewer + Integrator",
      "depends_on": [
        "P7-T01",
        "P7-T02",
        "P7-T03",
        "P7-T04"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P8-GATE",
      "phase": "P8",
      "kind": "gate",
      "title": "统一代码review、完整集成测试与资源/性能门禁",
      "owner": "Independent reviewer + Integrator",
      "depends_on": [
        "P8-T01",
        "P8-T02",
        "P8-T03",
        "P8-T04",
        "P8-T05"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P9-GATE",
      "phase": "P9",
      "kind": "gate",
      "title": "统一代码review、完整集成测试与资源/性能门禁",
      "owner": "Independent reviewer + Integrator",
      "depends_on": [
        "P9-T01",
        "P9-T02",
        "P9-T03",
        "P9-T04"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P10-GATE",
      "phase": "P10",
      "kind": "gate",
      "title": "统一代码review、完整集成测试与资源/性能门禁",
      "owner": "Independent reviewer + Integrator",
      "depends_on": [
        "P10-T01",
        "P10-T02",
        "P10-T03",
        "P10-T04",
        "P10-T05",
        "P10-T06",
        "P10-T07"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P11-GATE",
      "phase": "P11",
      "kind": "gate",
      "title": "统一代码review、完整集成测试与资源/性能门禁",
      "owner": "Independent reviewer + Integrator",
      "depends_on": [
        "P11-T01",
        "P11-T02",
        "P11-T03",
        "P11-T04",
        "P11-T05",
        "P11-T06",
        "P11-T07"
      ],
      "optional": false,
      "status": "PENDING"
    },
    {
      "id": "P12-GATE",
      "phase": "P12",
      "kind": "gate",
      "title": "统一代码review、完整集成测试与资源/性能门禁",
      "owner": "Independent reviewer + Integrator",
      "depends_on": [
        "P12-T01",
        "P12-T02",
        "P12-T03",
        "P12-T04",
        "P12-T05"
      ],
      "optional": false,
      "status": "PENDING"
    }
  ]
}
````
<!-- payload-end -->
