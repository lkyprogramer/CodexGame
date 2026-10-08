# 17 · 独立项目：长会话 full_reset 的定位与改造准入

**状态：只读调查/实验设计，不随B0+B1自动改配置。**

## 17.1 为什么值得单列

review报告长>=32K的272请求中，200append只1.1minprefill，64full_reset却57.8minprefill。其分组认为46次与2工具小客户端交错、15次idle>600、2次restart、1次compaction有关。附带日志缺失且分类基于元数据，应写“待验证假设”，不是已证明的每条因果。

原v1根据append hit中位数排除cache容量优化的判断过宽。tokenizer修复不会解决client交错/idle淘汰后的冷prefill；但一起改会失去归因并增加回滚风险。

## 17.2 FR-00：只读证据

记录source/镜像/参数/fullimageID；读取L1 entries、retain/evict、L2 publication success/failure与具体reason；记录冷reset前后request时间、匿名client身份（若来源已支持）、tool_count、prompt_cache/session routing hints、token深度。不得记录secret正文。

确认高频2工具请求实际由哪个进程/代理产生，不凭tool_count猜标题生成。确认L1 TTL的实际resolved值，而不只读源default。确认L2拒绝到底是RejectedTooLarge、其它capacity或结构错误；记录完整error/counter变动。

## 17.3 FR-01：串行与交错实验

维护授权且输入/资源固定：A主会话连续append；B小会话插入后再续A；C不同alias重复A；D空闲小于/大于600后续A。各条件至少3次，控制同一image/无tokenizer变化、同样memorybudget、同prompt与outputreserve。

记录每次cache path、reused/computed、TTFT、L1/L2变化，不以一次命中归纳普遍规律。若B导致A失去residentstate而alias不能恢复，再调查layercapacity和publication；若只有idle失败，先检查TTL及L2payload。

## 17.4 FR-02：实际镜像大小测量

读取已有安全export/diagnostic入口或在隔离构建加只读serialized-size统计，测160K/210K/245K状态的实际字节、压缩前后、包含哪些target/GDN/MTP/checkpoint部分。不能用KV理论大小代替serializedimage，也不能仅凭RejectedTooLarge把一个确定GiB数写进文档。

若确认单image>8GiB，评估L2容一条/两条的预算、host RSS与其它OCR容器峰值；RAM“可用45GB”是某时点观察，不等于可永久分配45GB。配置改变必须独立授权、重启与回滚，不能直接开16GiB/L3。

## 17.5 可选改造及权衡

| 方案 | 需要的证据 | 风险 |
|---|---|---|
|小客户端路由到已有其它服务|实际来源和可用服务已确认|新模型质量/额度/endpoint授权；不假设单4090能同时装第二大引擎|
|L1同时容纳两路|实际retainedstate + active峰值可容|VRAM压力、更多graph/workspace、反而spill|
|增大L2/启用L3|实际payload与host/disk预算|restore延迟、RSS/OOM、I/O，不能保证热TTFT等价L1|
|调idleTTL|idleevict可重复且有空闲容量|长期占显存与多会话公平性|
|稳定session alias|真实路由key缺失/变化造成可证明问题|alias不能凭空扩大容量或代替状态identity|

## 17.6 交付与准入

FR报告独立给出hypothesis→test→observation→alternative explanations→decision。先完成只读识别与byte测量，再选一个最小变更，不一次同时改路由、L2和TTL。验证各路隔离、无silentstate错用、reset/prefill总和变化和rollback。把full_reset收益与B0+B1的tokenize收益分列，不直接把54min上限当真实省时。
