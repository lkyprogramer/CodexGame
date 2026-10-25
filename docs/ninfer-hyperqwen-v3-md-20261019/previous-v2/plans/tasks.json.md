# V2 支撑材料：`plans/tasks.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: plans/tasks.json -->
<!-- payload-sha256: 2e46a2abad73f66e60cbfcdaaf895dc9b613e061a9b2a33f6a60149f8e5a0caa -->
<!-- payload-bytes: 179198 -->

<!-- payload-begin -->
````json
{
  "schema_version": 1,
  "as_of": "2026-10-15",
  "source_lock": "../data/source-lock.json",
  "delivery_kind": "implementation_plan_not_executed",
  "phases": [
    {
      "id": "P0",
      "title": "基线冻结与完整冲突实测",
      "upstream_sha": null,
      "gpu_required": true,
      "parallel_policy": "4项任务，源码/环境并行，资源与基线按依赖推进",
      "exit_criteria": "识别PROD/O差异；找齐G1素材；冻结门槛与回滚。",
      "gate": "P0-GATE",
      "required_checks": [
        {
          "id": "SOURCE_AUDIT",
          "kind": "manual"
        },
        {
          "id": "PROD_PROFILE",
          "kind": "manual"
        },
        {
          "id": "BUILD",
          "kind": "manual"
        },
        {
          "id": "FRONTEND",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_qwen3_8_frontend_test$",
            "^ninfer_qwen3_8_tokenizer_work_test$",
            "^ninfer_qwen3_8_tokenization_equivalence_test$",
            "^ninfer_qwen3_8_encoding_restart_test$",
            "^ninfer_qwen3_8_boundary_encoding_test$",
            "^ninfer_qwen3_8_legacy_oracle_test$"
          ]
        },
        {
          "id": "ORACLE_G1",
          "kind": "manual"
        },
        {
          "id": "BASELINE",
          "kind": "manual"
        },
        {
          "id": "GPU_RAW",
          "kind": "manual"
        },
        {
          "id": "REVIEW",
          "kind": "manual"
        }
      ]
    },
    {
      "id": "P1",
      "title": "前端、边界与观测融合",
      "upstream_sha": "94cdb5a975e514935ed4be214ee7f776a8683635",
      "gpu_required": true,
      "parallel_policy": "串行import后5个工作面并行；测试与实现在联合集成中校验",
      "exit_criteria": "所有前端/oracle/新边界、cache/guard和prepare_detail通过。",
      "gate": "P1-GATE",
      "required_checks": [
        {
          "id": "BUILD",
          "kind": "manual"
        },
        {
          "id": "FRONTEND",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_qwen3_8_frontend_test$",
            "^ninfer_qwen3_8_tokenizer_work_test$",
            "^ninfer_qwen3_8_tokenization_equivalence_test$",
            "^ninfer_qwen3_8_encoding_restart_test$",
            "^ninfer_qwen3_8_boundary_encoding_test$",
            "^ninfer_qwen3_8_legacy_oracle_test$"
          ]
        },
        {
          "id": "ORACLE_G1",
          "kind": "manual"
        },
        {
          "id": "CACHE_GUARD",
          "kind": "manual"
        },
        {
          "id": "TIMING_PROTOCOL",
          "kind": "manual"
        },
        {
          "id": "GPU_RAW",
          "kind": "manual"
        },
        {
          "id": "PERFORMANCE",
          "kind": "manual"
        },
        {
          "id": "REVIEW",
          "kind": "manual"
        }
      ]
    },
    {
      "id": "P2",
      "title": "异步 export 与调度",
      "upstream_sha": "4d3366e5b9a959627a6db1f0eb36932be0482def",
      "gpu_required": true,
      "parallel_policy": "import后lifecycle/metrics并行，GPU压测等待二者集成",
      "exit_criteria": "fence/alias/lane安全且长热会话不回退。",
      "gate": "P2-GATE",
      "required_checks": [
        {
          "id": "BUILD",
          "kind": "manual"
        },
        {
          "id": "FRONTEND",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_qwen3_8_frontend_test$",
            "^ninfer_qwen3_8_tokenizer_work_test$",
            "^ninfer_qwen3_8_tokenization_equivalence_test$",
            "^ninfer_qwen3_8_encoding_restart_test$",
            "^ninfer_qwen3_8_boundary_encoding_test$",
            "^ninfer_qwen3_8_legacy_oracle_test$"
          ]
        },
        {
          "id": "ASYNC_LIFECYCLE",
          "kind": "manual"
        },
        {
          "id": "GPU_RAW",
          "kind": "manual"
        },
        {
          "id": "PERFORMANCE",
          "kind": "manual"
        },
        {
          "id": "REVIEW",
          "kind": "manual"
        }
      ]
    },
    {
      "id": "P3",
      "title": "small-T 与流式工具",
      "upstream_sha": "f4089901fa17b83ecbb21bd2bde17bf614c3bf03",
      "gpu_required": true,
      "parallel_policy": "import后CUDA/serving/buildQA并行；GPU验收在合并后",
      "exit_criteria": "算子正确、工具流完整、长Agent吞吐与质量合格。",
      "gate": "P3-GATE",
      "required_checks": [
        {
          "id": "BUILD",
          "kind": "manual"
        },
        {
          "id": "FRONTEND",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_qwen3_8_frontend_test$",
            "^ninfer_qwen3_8_tokenizer_work_test$",
            "^ninfer_qwen3_8_tokenization_equivalence_test$",
            "^ninfer_qwen3_8_encoding_restart_test$",
            "^ninfer_qwen3_8_boundary_encoding_test$",
            "^ninfer_qwen3_8_legacy_oracle_test$"
          ]
        },
        {
          "id": "OPS_GPU",
          "kind": "manual"
        },
        {
          "id": "TOOLS_PROTOCOL",
          "kind": "manual"
        },
        {
          "id": "GPU_RAW",
          "kind": "manual"
        },
        {
          "id": "PERFORMANCE",
          "kind": "manual"
        },
        {
          "id": "REVIEW",
          "kind": "manual"
        }
      ]
    },
    {
      "id": "P4",
      "title": "midrise KV 与决策基础",
      "upstream_sha": "29d13e3d99491ed82e7be4edc801d92a59643cea",
      "gpu_required": true,
      "parallel_policy": "import后codec/decision/telemetry/output四面并行；实机qualification收敛",
      "exit_criteria": "新KV长上下文合格；可选决策资格单列。",
      "gate": "P4-GATE",
      "required_checks": [
        {
          "id": "BUILD_MATRIX",
          "kind": "manual"
        },
        {
          "id": "FRONTEND",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_qwen3_8_frontend_test$",
            "^ninfer_qwen3_8_tokenizer_work_test$",
            "^ninfer_qwen3_8_tokenization_equivalence_test$",
            "^ninfer_qwen3_8_encoding_restart_test$",
            "^ninfer_qwen3_8_boundary_encoding_test$",
            "^ninfer_qwen3_8_legacy_oracle_test$"
          ]
        },
        {
          "id": "CODEC_GPU",
          "kind": "manual"
        },
        {
          "id": "CACHE_VERSIONS",
          "kind": "manual"
        },
        {
          "id": "DECISION_CONTRACT",
          "kind": "manual"
        },
        {
          "id": "LONG_QUALITY",
          "kind": "manual"
        },
        {
          "id": "GPU_RAW",
          "kind": "manual"
        },
        {
          "id": "PERFORMANCE",
          "kind": "manual"
        },
        {
          "id": "QUALIFICATION_SCOPE",
          "kind": "manual"
        },
        {
          "id": "REVIEW",
          "kind": "manual"
        }
      ]
    },
    {
      "id": "P5",
      "title": "最终上游 API、视觉与 Web",
      "upstream_sha": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
      "gpu_required": true,
      "parallel_policy": "import后protocol/vision/web并行；最后统一API/GPU验收",
      "exit_criteria": "全部U源码进入；Chat与已启用能力验证，未启用能力不伪PASS。",
      "gate": "P5-GATE",
      "required_checks": [
        {
          "id": "BUILD_MATRIX",
          "kind": "manual"
        },
        {
          "id": "FRONTEND",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_qwen3_8_frontend_test$",
            "^ninfer_qwen3_8_tokenizer_work_test$",
            "^ninfer_qwen3_8_tokenization_equivalence_test$",
            "^ninfer_qwen3_8_encoding_restart_test$",
            "^ninfer_qwen3_8_boundary_encoding_test$",
            "^ninfer_qwen3_8_legacy_oracle_test$"
          ]
        },
        {
          "id": "PROTOCOL",
          "kind": "manual"
        },
        {
          "id": "VISION_STATE",
          "kind": "manual"
        },
        {
          "id": "WEB_BUILD_TEST",
          "kind": "manual"
        },
        {
          "id": "GPU_RAW",
          "kind": "manual"
        },
        {
          "id": "PERFORMANCE",
          "kind": "manual"
        },
        {
          "id": "QUALIFICATION_SCOPE",
          "kind": "manual"
        },
        {
          "id": "REVIEW",
          "kind": "manual"
        }
      ]
    },
    {
      "id": "P6",
      "title": "全量验收、试运行与回滚",
      "upstream_sha": null,
      "gpu_required": true,
      "parallel_policy": "最终review后quality与部署准备并行，再串行canary/rollback",
      "exit_criteria": "生产切换需批准；实际rollback与最终scope清楚。",
      "gate": "P6-GATE",
      "required_checks": [
        {
          "id": "SOURCE_RETENTION",
          "kind": "manual"
        },
        {
          "id": "BUILD_MATRIX",
          "kind": "manual"
        },
        {
          "id": "FRONTEND",
          "kind": "junit",
          "required_patterns": [
            "^ninfer_qwen3_8_frontend_test$",
            "^ninfer_qwen3_8_tokenizer_work_test$",
            "^ninfer_qwen3_8_tokenization_equivalence_test$",
            "^ninfer_qwen3_8_encoding_restart_test$",
            "^ninfer_qwen3_8_boundary_encoding_test$",
            "^ninfer_qwen3_8_legacy_oracle_test$"
          ]
        },
        {
          "id": "FINAL_QUALITY",
          "kind": "manual"
        },
        {
          "id": "GPU_RAW",
          "kind": "manual"
        },
        {
          "id": "PERFORMANCE",
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
        }
      ]
    },
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
        "ChatQuality：20Java任务×3重复的编译测试/工具正确率不下降；差异不以“浮点”直接豁免。",
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
        "QualityAndCapacity：20×3Java判定/长5needle、共享KV拒绝策略满足冻结条件；样本不足不能说统计非劣。"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
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
      "status": "PENDING"
    },
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
  ],
  "strict_evidence": true,
  "extension": {
    "id": "tqllm-v2",
    "source_lock": "../data/tqllm/source-lock.json",
    "requires": "P6-GATE",
    "status": "PENDING"
  }
}
````
<!-- payload-end -->
