# 原件与汇总数据合同

此文定义未来最小adapter的接口，不声称这些采集器已实现。字段不适用用null和reason；只有真实测得零才能写0。每个JSONL文件只追加当前campaign原件，新campaign另建目录，禁止覆盖旧实验。

## REQUESTS.jsonl

每个实际启动或未启动的计划请求保留一行：`campaign_id/engine_id/request_id/phase/prime_or_append/planned_order/execution_status/start_utc/start_monotonic_ns/end_monotonic_ns/clock_domain`。

身份字段：`request_body_sha256/rendered_token_ids_sha256/template_sha256/tokenizer_sha256/sampling_config_sha256/seed/prime_output_token_ids_sha256/rendered_history_sha256/stop_reason`。hash算法与序列化格式固定；token IDs用确定的字节编码。prime后才有的实际历史字段在执行前不得填造。

工作量字段：`prompt_tokens/read_tokens/reused_tokens/thinking_tokens/content_tokens/completion_tokens/sse_chunks/ttft_ms/decode_ms/wall_ms/valid/failure_kind`。SSE chunk与token分开，thinking与正文均计入。窗口计数不能替代完整请求计数。

性能固定探针还记录`fixed_output_contract_met/request_recipe_sha256/actual_history_comparable/trajectory_identity`。只有原件满足同输入和固定输出合同才转换为六对统计输入，不能在适配器里删掉差异。

## WINDOWS.jsonl与DEPENDENCIES.json

联合主键`engine_id/request_id/window_id`；记录完整起止、context、normal/continuation、draft数、accepted/committed token数、CPU/GPU expert IDs/格式/nt、分派、resident mask、kernel shape、stream/graph/事件身份。

区间含`start/end/unit/clock_domain/source_event_ids/coverage`。依赖边含`from/to/reason/evidence_ref/verified`；无法知道的边为UNKNOWN。同步wait与被等待工作不能相加。报告暴露区间并集、未知范围、删光上界、可信方案下的净模型；profiler改变了graph/融合时单独标明。

## MEMORY.jsonl

记录采样时间和所属native PID、RSS/PSS/VmSwap/VmLck/VmPin、minor/major fault累积值及差值、系统MemAvailable/swap/PSI、VRAM、expert slots、KV page/epoch、scratch/allocator高水位、alloc次数、温度、频率、功耗和GPU owner。

系统swap不是该PID的swap；已有VmSwap不是当前窗口发生换入的证明。actual map/consumer代际与KV resolve pin epoch用不同字段。精细硬件计数若无权限则UNKNOWN，不自动修改系统取数权限。

## RAW_MANIFEST.json

每个实际原件列`relative_path/bytes/sha256/kind/producer/version/created_at`；只列存在的文件，manifest不包含自身。包括失败日志、未完成请求状态与保护回执，不只打包成功输出。脱敏内容需明确是派生文件，保留与原始身份的映射但不发布密钥。

## 正式性能适配

`paired_stats.py`采用A/C标签：A绑定研究基线B，不能绑定生产A0；C是候选开启。A1关闭路径先与B验证。当前工具只支持恰好六对固定探针；两对支持层、诊断和真实任务质量数据使用各自报告，不补假样本凑六对。

主指标本轮冻结为decode_ms；A/A必须来自同指标。工具可支持别的主指标只是通用能力，不能允许当前campaign事后改目标。真实任务的受限时间和质量门均不由该计算器代替。
