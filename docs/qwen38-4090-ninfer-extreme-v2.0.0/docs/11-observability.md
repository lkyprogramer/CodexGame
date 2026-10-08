# 观测、统计与真实性

## 1. 三种账本不可混用

- HTTP：TTFT、总wall、usage target/completion、reasoning/visible结构、finish。包含网络和burst影响。
- Engine request：prompt_total、exact_lcp、reused、computed_prefill、restore、prefill、decode、queue、已提交输出、cache路径。
- Engine round：proposed K、physical W、live Q、accepted、licensed、committed、完整round_ms、proposal来源、catchup成本。

SSE一帧可能包含多个token，不能按帧计速；completion_tokens是否包含thinking按接口实测，不猜。`client_decode_estimate_tps`只是诊断，GPU/engine gate不得读这个字段。

**现状（44a，`22 §2.2`）**：HTTP与Engine request两层已基本可用——`/metrics`有`ninfer:draft_accepted_tokens_total`、`llamacpp:prompt_tokens_total`、`prompt_seconds_total`、`prefill_energy_joules_total`；请求结果有`speculative_accepted_tokens`、`reused_prompt_tokens`、`cached_tokens`；compat proxy注入`usage.prompt_tokens_details.cached_tokens`。**缺的是Engine round层**（每轮`round_ms/physical W/live Q/licensed/committed/origin/catchup_ms`），这是T02的范围；T02不重建前两层。

## 2. round schema

详见`contracts/round.schema.json`。`round_ms`从准备proposal前到此次commit完成，包含CPU lookup、同步和必要catch-up。细分CUDA事件可能重叠，不能简单累加；与wall交叉检查。counter在既有host授权边界汇总，避免每层/每token强同步。性能测量时关闭详细tensor dump和ncu；记录instrumentation开关。

定义：

```text
AL_licensed = Σlicensed / rounds
AL_committed = Σcommitted / rounds
acceptance = Σaccepted_drafts / Σproposed_drafts
throughput = Σcommitted / Σround_seconds
prefix_token_reuse = Σreused / Σprompt_total
reprocess_fraction = Σcomputed_prefill / Σprompt_total
```

licensed含correction/bonus；committed经stop/cancel后可能更少。来源中AL定义不同，导入时必须注明，不能直接把“accepted drafts=3”当“4tokens/round”。只统计完成输出会产生幸存偏差；错误/timeout/cancel分别列出。

## 3. 配对设计

固定20个请求/轨迹prefix：4桶（Java新代码、tool JSON、rewrite/copy、reasoning/QA）各5；12用于调参、8锁住heldout，按session分组分割而非同一会话相邻prefix分到两边。新增数据清理后target tokens应重新校准，对照读同一份清理后payload。

以相同case、采样profile、context、power配置、热缓存条件配对。运行顺序ABBA减漂移，主桶每个case/profile**至少8个配对点**（`tools.metrics.MIN_GATE_PAIRS`；跨两次进程启动），并先跑一轮baseline-vs-baseline（A/A）得到噪声底`aa_noise_abs = max|ratio−1|`。报告各桶、全局按实际traffic权重的总量，以及95%配对区间——取percentile bootstrap与log-ratio Student-t区间中**更保守**者（n=5时percentile bootstrap只有3125种重采样，区间明显偏窄，不能作为门的依据）。不要只报告最快seed；未达到输出长度的请求不当2048-token持续速度样本。

## 4. 主要字段

`run_id, case_id, session_id, branch_id, backend_commit, image_id, target_sha, companion_sha, kv_profile, state_schema, sampler, seed, reasoning_effort, prompt_actual, max_output, output_actual, prefix_path, reused, computed, cold/warm, queue_ms, restore_ms, prefill_ms, round_ms, task_wall_ms, GPUclock/power/temp, error, profiled`。

目标字段缺失即“缺证据”。允许保留原HTTPusage，但**不得猜成engine字段**。相同sourceSHA不够：bin、artifact、flags和cache状态也要有identity。

## 5. 采集负担与私密信息

counter汇总/异步ring输出优先，抽样1/16的详细round用于分解；总request计数完整。添加观测前后A/A测额外开销，>1%则减采样并标记不能直接用当前计时。日志不写Authorization、sudo交互、真实用户文件正文；完整请求采集为单独私有目录，0600和授权开关。提交分析包时只保留清理后的摘要和sha，不上传原思考内容。

## 6. adapter中的额外守恒检查

请求首次prefill授权的token、Frontend强制control token及spec round token可能由不同事件发布。T02必须对照真实事件序列建立守恒式，单独记录prefill/control emitted数，不能盲目把HTTP completion总数等同Σround committed。verify前取消的round没有licensed=accepted+1事件，使用abort记录而不是塞进completed-round schema。

`paired_gain_lcb`指**预先指定主指标、方向归一化后**的收益下界：吞吐用candidate/base，TTFT用base/candidate。不得跑完以后才从多个指标中挑最好一个。helper的bootstrap只适用于提供的配对样本；同一session中的相关请求须按session块重采样，不能把3000次bootstrap误当3000个独立观测。

**单位固定**：`paired_summary`返回的是ratio及ratio区间（`ci95_low`已是bootstrap与t区间中更保守者）。写入资格事实时必须 `paired_gain_lcb = ci95_low - 1`；例如吞吐ratio下界1.04写入0.04，不能写1.04。同时写入`paired_n`（主桶配对数，<8→BLOCKED）与`aa_noise_abs`（A/A噪声底，>0.03→BLOCKED）。`task_wall_ratio = candidate_wall / baseline_wall`，越小越好。ttft方向反转在输入配对时完成，不混入同一分组。
