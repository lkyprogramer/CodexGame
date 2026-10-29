# 性能实验协议

## 1. 四类工作负载分开

| Profile | 输入 | 输出 | 场景 | 主指标 |
|---|---|---|---|---|
| decode-fixed | 约1K/8K/32K/64K/122K，使用精确tokenizer | 固定512或余量允许值 | 同状态、关闭外来负载 | engine decode_ms、window_ms、接受token/窗 |
| cold-prefill | 8/32/64K与接近上限 | 短固定输出 | 没有可复用KV；SSD冷热单独标 | read_tokens / prompt_ms、TTFT |
| agent-append/edit | 固定真实或可重建多轮转录 | 原始任务需求 | 追加、前缀编辑、工具结果 | restricted time-to-success与完成率、reused/read tokens |
| multi-session | A/B/C切换，4slot边界、取消 | 固定或任务输出 | park/restore与资源压力 | 恢复TTFT、重复prefill、cache失败率 |

普通长测试不是“131072输入再生成512”。历史最大约122.8K输入仅证明那个请求，不代表完整128K长期循环。

## 2. 冷暖标签

分别记录process、expert-cache、KV-prefix、RAM-page-cache、SSD五个冷热维度。新进程不等于SSD冷；token计数探针也可能暖化prefix。禁止执行全局drop_caches作为默认流程；真的测冷盘须在专门维护实验中说明方法与影响。

## 3. 配对与顺序

已实现runner的统计单位是`round`：CFG/MIG每轮两臂各启动一个独立进程，顺序AB/BA交替；PR实验是base/off/on与on/off/base交替。每进程使用冻结case顺序，前置tokenizer校验会影响冷暖，必须标记。这不是四进程ABBA宏块，也没有实现统一warmup/profile-reset适配器。

- A/A与screening至少5个paired round；这个数量只供筛查，不能自动当正式统计充分。
- 每round内部多题/多window相关，bootstrap重采样round，不把它们当独立样本。当前统计在每个场景层与round内，先分别把各arm对应case的时间求和，再对两个arm的整轮时间比取log并bootstrap；各场景层分开。这不是各case ratio的几何平均。
- 正式实验在解盲前冻结独立paired block数、case顺序、warmup/reset、seed和停止规则。不能边看显著性边加样本到首次PASS。
- 若采用更强的ABBA/BAAB宏块，P00必须先实现`paired_block_id / process_instance_id / order_position / replicate_id`和聚合：同block先合并A的两个重复及B的两个重复，再对block bootstrap；当前runner不支持该模式。
- spec/lookup输入相似度、cache命中、CPU miss、accepted tokens、输出长度都记录；同样输入不保证同样计算量。

## 4. 时间字段

`wall_s`端到端；`ttft_s`保留legacy首任意输出；`first_reasoning_s`、`first_visible_s`、`first_tool_s`和首参数时间分别记录。SSE chunk可能含多个token，event gap不能命名ITL。逐token p95/p99需要引擎时间戳；没有就报告NOT_MEASURED。完整tool-ready需最后一段参数到齐并通过schema。

引擎日志的decode tokens/s、CUDA event时间、nsys kernel累计时间与HTTP wall不是同一分母。profiling和正式性能测量用不同运行，测出profile开销，不把ncu replay后的时间当在线服务时间。

## 5. 执行环境

除实验卡预先声明的处理变量外，所有arm保持相同EXACT6、CPU governor/C-state、sampling、template、MTP和context。处理变量进入config diff及E/N/Q/X分类；spec、draft或host实验不能暗中改变其它条件。禁止其他模型服务/编译/内存压力与性能run并发。协议要求持续观察外来GPU PID、温度、RAM、swap及资源释放。当前monitor覆盖GPU身份/温度与MemAvailable；owned进程退出后wait_released核对释放。swap与完整CPUfreq/带宽/功率时间序列由P00补齐，未采样字段写NOT_MEASURED。只停止自己拥有的进程，不能杀外来进程。

最新source的auto策略必须输出effective状态。若在线自适应影响arm内部形状，记录为策略本身的处理效果；不能再宣称只有某一个kernel变了。

## 6. 观测最小集合

每请求保存request_id、case_id、dataset_sha、arm、round、context_bucket、cache_state、scenario、engine/source/config/assets/host指纹、输入输出token、采样参数、成功/失败及原因、raw SSE或可恢复日志、时间字段。每窗口额外保存T、draft来源、接受数、CPU miss数、resident数、拷贝字节、graph key、phase timings。

window instrumentation字段是拟新增/需移植的接口，先执行P00，不假装当前lab已解析所有GPU窗口字段。

## 7. 成本控制

单kernel筛查→短模型数值→小场景A/B→长上下文→留出任务。明确无收益的候选停止，不为凑“优化数量”继续跑。候选必须保留全部失败。模型oracle失败和task_budget_exhausted进入质量四格，失败任务时间计预定B；基础设施失效令比较BLOCKED/INSUFFICIENT，OOM/crash触发硬拒绝。不能只统计成功run。
