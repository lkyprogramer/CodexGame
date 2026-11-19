# 证据接口：在原底座上补字段，不再建平台

状态：下面是未来 adapter 规格；本包没有实现 telemetry、collector 或 engine hooks。

## 1. 四件套

继续复用 ExperimentSpec / RunEvidence / Decision / BudgetLedger，见 [JSON模板](../templates/ExperimentSpec.json)。每个候选单独 `experiment_id`；旧 run ID 和额度不可复用。

JSON中的文件引用统一以`LAB_ROOT`为基准，ExperimentSpec声明`references_base`。本包固定安放路径为`addenda/ninfer_strata_source_delta_exploration_20261115/`，所以source_lock_ref包含该前缀。若现场不同，R0显式重新绑定实际路径并冻结hash，不能按spec文件当前目录猜路径；文档自身的Markdown链接仍相对所在MD解析。

`identity.source_lock_sha256`必须与实际锁文件字节相符；仅路径存在不合格，模板为null因此不可执行。后续source lock改变必须产生新spec hash，不能静默替换已冻结实验的输入。

| 记录 | 必须新增/绑定的内容 | 禁止 |
|---|---|---|
| ExperimentSpec | donor pins、旧路线差量、当前baseline身份、唯一处理变量、适用任务、冻结split/oracle/门槛 | 用“latest”替代commit，采后改指标 |
| RunEvidence | 实际执行身份、raw文件hash、失败/取消、observed path、资源峰值、采样/RNG合同 | 仅存成功均值或作者tok/s |
| Decision | 每个资格层独立状态、证据引用、已用预算、下一步authority | 一个PASS解锁所有阶段 |
| BudgetLedger | 授权ID、计费边界、引擎/请求/GPU wall/输出/存储限额及实际用量 | null预算当无限、失败不计数 |

所有64位ID/ns以十进制字符串保存；null必须有reason。未知值不得填0。示例里的0只用于确实未执行的计数/批准预算，不用于伪装耗时观测。

正式RunEvidence显式绑定`phase/pair_id/run_block_id/treatment/case_id/task_manifest_ref/run_order_index`，不能从文件名推断A/C或样本归属。资格阶段不适用的pair字段为null＋reason；正式配对缺字段必须拒绝统计。任务清单和权重与spec的hash一致。

## 2. 身份与因果

继承 completion-path/v1 的boot、PID/startticks、engine instance、request/attempt、slot generation、round以及CUDA context/stream/graph generation/replay node。candidate extension不能削弱这些键。

- correlation只能绑定同一身份链；时间邻接不能推出happens-before。
- CPU选择copy≠GPU神经草稿未执行；capture节点存在≠执行次数。
- kernel时长求和≠wall；重叠区间取并集仅证明busy footprint，不证明可省critical path。
- watchdog `cudaStreamQuery`只用于进展/故障分类，不能代替设备完成时间戳。
- cost identity至少含：engine/driver/device、model/head/sidecar、dtype/codec、W、sampler、context band、cache模式、graph与observer模式。失配拒用历史表。

## 3. D1 extension：`donor_delta.copy.v1`

| 字段 | 类型/单位 | 含义 |
|---|---|---|
| `planner_variant` | enum B0/B1/B2/B3 | 消融身份，不能混运行 |
| `source_kind` | prompt/output/none | 区别来源与可恢复语义 |
| `source_generation` / `source_token_begin` | decimal string或null | 请求内来源版本/位置，不保存明文源码 |
| `exact_match_tokens` / `proposed_tokens` | integer | hash命中不算exact |
| `anchor_state` / `planner_reason` | bounded enum | cold/anchored/edit_repair/backoff等 |
| `lookup_build_ns` / `lookup_query_ns` | decimal ns或null | 包括索引成本；诊断热路径记录应走预分配缓冲 |
| `neural_draft_executed` | true/false/null | false需要执行证据，不由选择标志推断 |
| `skipped_work_evidence` | ref或null | 原图/stream动作未执行的证据位置 |
| `catchup_rows` / `catchup_ns` | integer / ns或null | 草稿历史维护不能遗漏 |
| `accepted_proposal_tokens` | integer或null | verifier接受量 |
| `committed_input_rows` / `emitted_tokens` | integer或null | 终止裁剪后实提交与对外产出，不等同accepted |

## 4. H2 extension：`donor_delta.head.v1`

`existing_head_hash/token_remap_hash/sidecar_hash/rank/shortlist_limit/shortlist_actual/fallback_reason`；离线oracle另记`original_top1_in_shortlist/selected_rows_score_match`。成本分别为`projection_ns/score_ns/select_ns/rescore_ns/original_head_ns/ar_body_ns`，未知为null。

不得在正式服务热路径为了这些字段额外跑full head。资格双算只在明确标记的诊断窗口；正式C只执行其真实策略，正式A保原路。双算/trace结果不能当最终速度。

显存账独立记录 existing head、新增sidecar、短名单workspace、Graph arena、KV/state以及restore临时peak；禁止把总free差值直接当可回收head容量。

## 5. M0 extension：复用A2 cache-work语义

绑定`remaining_before/accepted_rows/bounded_rows/committed_input_rows/last_output_token_hash/next_unconsumed_position/merged_window/stop_reason/drafter_context_end`。下一请求记录exact-prefix、复用/重算token数、restore path、fallback reason及state身份；不能只记cache_hit布尔。

`last_output_token_hash`只在隐私许可内生成，token ID本身也可泄露内容；默认产物不公开原prompt/代码。不同来源时间戳不可直接相减，使用同一timebase或明示校准误差。

## 6. 文件与隐私

建议实验目录结构：`runs/<experiment_id>/{spec.json,budget.json,raw/,normalized/,decision.json,reviews/}`。这是旧控制器产物结构的映射，不强制搬迁现有数据。schema adapter记录源schema/version/hash和丢弃字段，拒绝静默补默认值。

raw不覆盖、输出按身份分目录、manifest封存；临时锁释放不删除失败原件。最大磁盘预算必须先冻结，超限停止采集并报告DROPPED，不截断到看起来成功。对外报告仅保散列、匿名case ID和必要计数；私有代码/hidden不上传GitHub或外部服务。

模板见 [RoundEvidence](../templates/RoundEvidence.json)、[RunEvidence](../templates/RunEvidence.json)。这些template不可作为真实run的输入原件。
