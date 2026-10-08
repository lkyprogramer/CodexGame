# 09｜基准、逐请求回放与统计

## 9.1 四条控制线

A0：纯44a2c6c（只加测量，不改语义）。A20：现网prepare-detail overlay，必须先证明与A0前端输出等价。
B1：A20/已审计诊断基线上single-pass，跨请求cache关闭。
B2：同B1加incremental。

不把B2同时改BPE/扫描器/采样后的结果归因于cache。可选B3常数优化另开实验。

## 9.2 冻结矩阵

| 维度 | 取值 |
|---|---|
| prompt实际tokens | 4K、32K、64K、128K、192K、240K |
| message形态 | 大块user文档；32回合；约160/350/769条碎片tool-history |
| 更新 | exact同输入；assistant+tool追加；单字节历史改写；tool schema变化；最后generation opener变化 |
| CPU cache | cold/empty；warm；disabled；budget不足；entry淘汰 |
| GPU cache | cold/full_reset；warm append；checkpoint restore |
| output budget | 1用于前端/TTFT探针；512/1536用于代表生成；不可混同测速口径 |

tokens必须由冻结资源实测，不用chars/4。合成recipe目标深度容差±128token，最终报告实际值。原245194/769/810Kchar记录的正文未知，不能声称合成sample就是那一条。

## 9.3 工作放大回放

先固定R，分别仅改变hint集合：0、3、32、128、256个合法候选。该实验直接隔离“messages/bytes vs boundary数”。若用完整render，messages不同会同时影响内容，需另有人工RenderedChat component对照。

每次报告：`legacy_requested_encode_bytes/render_bytes`、`ordinary_bpe_input_bytes`、各阶段CPU wall、用户CPU time、主encode数。预期B1的主BPE一次，局部边界BPE只编码短片段。若“cache hit很高但BPEbytes仍几十倍R”，说明优化漏了边界路径。

## 9.4 CPU测试计时

先warm tokenizer资源/常驻分配，再计时；不要让资源文件读取和首次load进入tokenize。完整prepare和纯tokenize分别报告，不混为一个数。A/B交错顺序或分session配对，固定CPU governor/线程、负载和构建优化级别。记录CPU型号/核数/频率、RSS、可用内存；不要只记录4090型号。

长请求样本量小于20时p90/p95仅描述，不包装为稳定SLO。不同mode、不同sessions的分布不得直接相减当净收益。`tools/summarize_bench.py`以pair_id做配对，缺pair会失败，不悄悄丢掉。

## 9.5 GPU/HTTP测试

本机引擎直连用于隔离frontend；生产代理路径另测用于用户体感。两路都显式固定medium、temperature/top_p/top_k，防止绕过兼容层后默认xhigh。首次非空reasoning/content/tool-argument delta才算用户TTFT，role-only包、progress、heartbeat不算。

cold要使用新隔离服务/已知清空状态；warm每个模式先用同样历史seed请求prime，再回放相同tail序列。不要在同一CPU缓存/同一GPU状态先跑candidate再以污染状态测baseline。cache命中与computed_prefill必须逐行核对。

不能以`max_tokens=1`探针的耗时从另一次长请求中相减估计decode，那会受warmup、JIT和cache污染。优先引擎阶段timing加客户端逐事件计时。首token已在TTFT内，decode intervals通常按max(completion_tokens−1,0)计算；源计时定义先验证。

## 9.6 日志规整

本包 `schemas/benchmark-row.schema.json` 是规范化结果，不声称原schema20有同名字段。执行者写一个明确mapping adapter，并用真实三条日志测试：cold、warm、missing-field。缺失字段保留null；不猜单位；milliseconds转seconds只能一次。

工具调用成功、taskverify、stop_token各自独立统计。所有超时/取消/request_error需要纳入分母。`request_done`样本无错误，不等于系统没有错误。

## 9.7 性能结论模板

报告分别回答：

1. B1将主历史BPE重复次数和耗时降低多少？它是否已经足够解决体感问题？
2. B2相对B1，在相同warm前缀与delta上还省多少？哪些输入因证书失效回退？
3. 用户可见TTFT、p90和整体任务墙钟是否同步改善？
4. 同一GPU状态路径是否不变？有没有为CPU优化牺牲模型语义/缓存正确性？
5. 哪些Gate还没有执行？

不要再以“prefill只有0.3秒，tokenizer完成后TTFT必定0.3秒”作结论。逐行测量剩余时间，发现新瓶颈再单独立项。
