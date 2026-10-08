# 08｜测试集、独立oracle与验收门

## 8.1 三种不同的“通过”

**资料/辅助工具通过**：只说明本包JSON/链接/脚本工作，不说明NInfer修改完成。
**CPU前端通过**：独立legacy与candidate的token/边界/错误完全等价，且编码工作下降。
**4090/生产通过**：真实资源、实际HTTP、相同GPU缓存复用和Pi任务，性能与质量门都成立。

Gate报告使用PASS/FAIL/SKIP/NOT_RUN。CTest exit77、缺artifact、缺CUDA、无停机授权分别记录，不得合并为PASS。

## 8.2 数据包及oracle

`data/adversarial_cases.jsonl`提供可执行输入/边界/追加变换和验收policy；`data/session_recipes.json`定义生成长会话的种子、目标深度和消息形态。输入是本包原创合成文本，不代表1617条真实request正文。

token IDs goldens必须由**固定44a2c6c二进制+固定六资源**生成。没有真实tokenizer资源时，只能做synthetic fixture gate，不能编造真实Qwen token ID。记录输入hash、资源hash、oracle binary hash、原始输出/异常。

正式oracle对每个输入产生：token_ids、token_types、positions、rope_delta、stable_prefix_boundary、turn_rewrite_boundary、user_turn_boundary、ordered checkpoint_hints、identity.reusable、starts_in_reasoning。错误输出记录阶段、异常类别及旧处理器规定的可观察信息。耗时/缓存状态不进入等价golden。

## 8.3 测试层

| 层 | 输入与操作 | 必须检查 |
|---|---|---|
| L0 pinned identity | source-lock、git show、overlay | 完整SHA/文件blob，不误用HEAD |
| L1 tokenizer trace | 普通bytes、added、Unicode、parse_added=false | 主tokens完全不变，trace消费区间无洞无重叠 |
| L2 boundary | 所有byte cuts、重复/无序查询、full限制 | 局部解析和legacy prefix oracle完全一致 |
| L3 incremental | append、partial added、NFC、rewrites | tokens+metadata一致；证书无效必须fallback |
| L4 cache lifecycle | eviction、disabled、entry超预算、乱序并发 | 无悬空引用、无串用、上限可解释 |
| L5 frontend | 两种模板、tools、thinking、count_tokens、prepare_tokens | 原业务结果/错误不变 |
| L6 HTTP | streaming/nonstream、代理/引擎分层、错误码 | 工具/usage/timings保持合同 |
| L7 GPU | 相同warm序列、262K、MTP3/E8 | GPUcache与状态不被改写，无额外prefill |
| L8 live | session级真实分布 | 长热请求改善、无长尾/内存/正确性退化 |

## 8.4 最低样本要求

组件：运行本包全部adversarial cases；在synthetic byte-vocab+merge fixture中对≤256bytes样本枚举每个byte cut；固定seed至少20000次append/substring/Unicode/added-token变换。所有失败用例冻结回归，不抽样丢弃。

真实资源：至少1000个前端请求oracle对照，其中≥50个120K+、≥10个220K+；这些可以离线重放，不需要1000次GPU推理。数量是初始发布验证预算，不代表统计证明概率为零；必须包括明显反例而不仅随机样本。

GPU：选代表性长会话片段，至少32K、128K、192K、240K四档；每档基线/候选相同输入序列与采样。正常Agent preserve_thinking/tool-history必须覆盖；不是只做greedy无tool针测试。已有Pi Java三题作为现网兼容smoke，不外推为通用代码能力不变的统计证明。

## 8.5 G0–G7

- **G0可追溯**：base commit、overlay、artifact/资源/配置锁定，无未知语义补丁混入。
- **G1精确等价**：全部CPU oracle tokens与语义字段相等；任何mismatch即FAIL。非法输入保持旧错误合同。
- **G2结构性工作削减**：single-pass正常长tool-history只有一次主编码；不再出现每hint完整历史BPE。incremental命中时不做完整R主编码，边界处理也不重做整前缀。
- **G3资源**：64MiB cache预算实占可解释，超预算可正确fallback；无GPU新增常驻分配；并发及eviction无数据竞争/悬空引用。
- **G4性能**：同输入长碎片会话single-pass的tokenize中位数相对legacy下降目标≥80%；如果不足，定位剩余work后再判，不篡改门。incremental对“120K+、变化suffix≤8KiB”的请求目标tokenize p50≤1s、p90≤2s，且相对single-pass有净收益；绝对值是4090主机CPU目标，需要实测。
- **G5无回归**：<8K latency增量p50≤max(5ms,5%)；cold单次主编码性能不得显著回退；same-path GPU decode下降>3%需重复排除噪声，确认>5%即FAIL。
- **G6系统行为**：无新增request_error、工具解析错误、cache失配；相同序列GPUreused前缀/计算token数与基线一致或差异已归因至测量而非改动。
- **G7发布**：canary、镜像/参数回滚演练成功；shadow未执行时不能填写通过。无授权/硬件时保持NOT_RUN。

门不是“80%任意成本换来的成功”：若关闭hint、降低context、改权重/采样、换模板或忽略非法输入，G1/G0已失败，G4数字无效。

## 8.6 Shadow的oracle独立性

测试进程预生成legacy goldens，再单独运行candidate；不能只让新增trace与调用同一新增trace的“legacy”比较。生产shadow可以用保留的旧逻辑做在线防护，但它不是替代离线独立baseline的全部证据。

对同输入即使full tokens相等，hint判定变化仍可能影响GPUstate恢复。因此必须比较所有metadata，而非仅token数量/最终回答。
