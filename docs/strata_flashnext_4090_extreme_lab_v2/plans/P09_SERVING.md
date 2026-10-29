# P09 — 服务层、真实Pi路径和host增量

**目标：**减少用户感知等待；对应O58–63。不能用并发吞吐换单请求延迟后宣称同一指标提速。

## P09-01 排队/模板/tokenizer/SSE归因

固定源码：[serve/server.py](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/serve/server.py)、[serve/frontend.py](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/serve/frontend.py)、[serve/runconfig.py](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/serve/runconfig.py)、[serve/telemetry.py](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/serve/telemetry.py)、[serve/replicas.py](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/serve/replicas.py)。先测queue、render、tokenize、prefix reconcile、engine wait、reasoning/visible/tool-ready。没有服务时间戳时不得用HTTP wall减kernel累计伪算排队。

候选：仅缓存完全相同模板/工具序列的编码、复用真实生成token IDs而非文本再编码、减少重复JSON解析与同步logging。保持请求内容/采样/工具定义一致；Pi剥离thinking导致prefix变化时先复现，不把BPE差异当唯一原因。新增cache key必须包含model/tokenizer/template/tool schema/config版本；不跨请求泄露状态。

**测试：**Unicode/特殊token、工具消息、reasoning保留/剥离、多tool并行结果顺序、截断、错误恢复、同text不同模板、SSE fragmentation、取消和慢客户端。`first_tool_arguments`不是完整tool-ready；tool-ready需要最终JSON有效且schema完整。

**收益门：**这段critical-path份额不足3%时不重写服务语言；优先结束此方向。异步发SSE不能提前触发未完整的工具。

## P09-02 并发与公平调度

单卡、单模型默认请求串行；4个conversation-cache slots不等于parallel=4。对真实长主任务+短helper流量，探索协作式yield或分片prefill；先测是否实际有队头阻塞。每个暂停请求保存KV/GDN/conv/MTP/sampler状态，RAM/VRAM能够容纳后才试。

比较单任务wall、helper p95、总体正确任务/小时、starvation、内存峰值；不把吞吐改善抵消主任务质量或延迟。时间片过短会反复park/copy，须纳入成本。多GPU PR4010不适用于本机。拟新增公平策略默认关闭，取消只取消所属request，不终止其他client。

## P09-03 上下文工程单独Q轨道

system/tools精简、去除重复文件、tool结果摘要/缓存、外部检索可减少输入成本，但改变模型看见的内容，归Q/O58。用户若选该轨道，必须保存原prompt和变更prompt的hash与可恢复映射，使用跨文件Java任务测试遗漏依赖、旧新版本冲突、异常栈和边界条件；不能与同输入kernel提速合并成一个百分比。

## P09-04 host与编译

performance governor和C6关闭已部署，不重做“发现”。实际测试线程亲和性归P01；NUMA/pinned first-touch/THP增量要先证据。历史THP已约85%，不能默认剩余全部可优化。`mlock`/巨量pin易侵蚀64GB余量，必须有上限和失败fallback，不全量锁43GB权重。不同进程allocator设置只在隔离配置比较，详P00。

PGO/LTO：固定代表性profile、离线构建variant、区分C++host与CUDA device link；记录exe/flags/GGML hash。先看host份额；CUDA热核不能因host LTO直接加速。不得自动用fast-math或删除同步。测试CLI、serve、error recovery、CPUISA dispatch及所有受影响格式，最后真实模型wall。

功率/温度：先长期记录nvidia-smi功率/温度/clock与CPUfreq、降频原因，再选用户已授权的可逆实验；GPU超频/电压/驱动解锁不作为本包自动动作。固定同一环境比较energy/correct task和稳定时间，防止短冷机boost假收益。

## P09-05 退出与交付

若服务/host等待份额低，停止。输出request timeline、源改动、配置diff、受影响schema、单元与集成测试、真实Pi回放和rollback。拟新增命令/开关必须先实现并有activation日志；直接改生产配置不属于本研究交付。
