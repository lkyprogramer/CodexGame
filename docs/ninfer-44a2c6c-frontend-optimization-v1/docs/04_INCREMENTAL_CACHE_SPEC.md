# 04｜跨请求 token 前缀复用

## 4.1 只缓存确定性前端结果

CPU cache保存旧输入的原始rendered bytes、token IDs、词法trace和资源/选项identity。第一期不缓存模型生成token，不读取GPU KV，不保存GDN状态，也不修改L1/L2。前一请求即使最终生成失败，其已经成功验证的输入编码仍是数学上有效的；首期采用更保守策略，只在prepare成功后发布snapshot，异常不发布。

### 缓存与GPU路径的关系

```text
new request -> full render -> CPU cache proof -> complete PreparedPrompt
                                                |
                                                v
                                  Engine chooses append/restore/reset
```

前端不能写`if (reusePath == AppendFrontier)`作为入口；这个值要在后续才知道。只把前端eligible与最终GPU路径做**事后交叉统计**。字节证明允许的保守前缀可在GPU full_reset时仍复用CPU编码；CPU miss也不应导致GPU miss。

## 4.2 资源身份

cache由Frontend实例持有；资源生命周期内tokenizer/模板固定。实例重建则清空cache。记录六资源的内容SHA256供审计；不能把模型显示名当资源身份。不同parse_added_tokens选项不能混用。

首期采取保守策略，将以下render语义纳入匹配key或在变更时禁用增量：template身份、enable_thinking、resolved reasoning_effort、preserve_thinking、add_generation_prompt、add_vision_id、prefix_checkpoint_policy、原顺序tool_jsons。实际rendered前缀仍要逐字节验证，key命中不能替代它。

adapter/model artifact变化时，GPU状态由原机制隔离；CPU层即使理论上只依赖tokenizer，首期也通过资源owner/模型generation隔离，避免复杂推理。不得将cache key注入模型文本。

## 4.3 安全重启点与有限lookahead证书

旧输入R0，新完整render R1，L为它们原始字节最长公共前缀长度。M为本实例所有受支持added token内容的最大**字节长度**。

从旧trace选择最大r，满足：

1. r为实际added token消费完成后的重启点，或0；
2. r>0时，`r + max(M-1,0) <= L`，用防溢出减法比较；
3. 资源/选项相容；前缀bytes直接相同；trace的token区间未被修改；
4. 本期只接受text-only；有媒体直接原路径。

为什么需要guard：R0=`ab`、R1=`abc`，配置added `ab`和更高优先级`abc`时，旧EOF切点可能被新token吞掉。有限最长token长度M使所有**起点<r且可能跨过r**的added-token匹配都落在已经验证相等的lookahead内；因此r以前匹配选择不变。r处于已消费added token之后，也阻止ordinary NFC/BPE跨越r。

该证书是本包设计，需要T05的穷举/对抗测试与review；不能只凭文中推导宣布已证明代码正确。任何无法满足证书的请求，回退到single-pass全主编码，不猜overlap长度。

可选的更保守首发实现：仅使用已证明前缀无歧义的固定delimiter集合；如果采取此实现，必须从加载token表验证无更长/更高优先级竞争匹配，不能只按token名称硬编码。默认推荐统一M字节guard，减少特例。

## 4.4 增量构造

```text
tokens = cached.tokens[0:t_r] || E(R1[r:])
trace  = cached.trace before r || translated suffix trace
```

suffix trace的byte_offset加r，token_offset加t_r。跨过r的旧span不能复用。下一步对**当前**RenderedChat全部边界运行03的resolver，不复用旧的hint业务列表。token_types、positions、rope_delta、PromptIdentity等继续按当前完整token结果重建。

**不能让边界验证把已跳过的历史再次全量encode。** 对b<=r，使用已经验证有效的当前组合trace；必要局部prefix仅在其重启点后计算。对于新suffix的边界，同样局部解析。否则CPU cache命中99.9%也可能仍然慢。

## 4.5 上次输入不等于GPU完整历史

旧snapshot只覆盖上次进入frontend的prompt。下一次仍需编码“上次assistant输出重新序列化部分 + 新tool结果 + generation opener + 安全回退尾巴”。所以CPU newly_encoded_tokens可以明显大于GPU computed_prefill_tokens；这是正常现象，禁止用两者强行相等作为Gate。

同理不要求CPU reused_tokens==GPU cached_tokens。唯一共同的正确性要求是完整PreparedPrompt等价，GPU复用机制不受破坏。

## 4.6 生命周期与内存

初始上限：8个snapshot、64MiB缓存**实占**预算。snapshot不可变，读者用shared_ptr pin。catalog锁内只做选项匹配、LRU和引用获取；字节比较、编码与验证在锁外。发布时再锁入，双检generation/资源identity；并行请求乱序结束不能以完成时间覆盖“唯一正确会话状态”，cache只是候选集合。

计费覆盖rendered string capacity、token vector capacity、span/restart vector capacity及retired-but-pinned条目。若被pin条目使预算不足，跳过新cache admission；当前请求仍走正确编码，不能HTTP OOM。可设置单entry最大16MiB；超过则不缓存，不能截断输入。budget=0等价不保留跨请求结果。

不做磁盘持久化，不新增L3。进程重启/模板资源更新清空即可。cache失效仅影响CPU性能，不得清除GPU原有状态。

## 4.7 Shadow与失配

线下same-input运行candidate和独立legacy；比较完整PreparedPrompt，不比较耗时字段。serve shadow只提交legacy结果，不额外GPU推理。candidate抛异常而legacy成功、candidate成功而legacy失败、任意token或hint不一致都算mismatch。

生产若采样shadow发现mismatch：本进程锁存禁用incremental、回退single-pass；若single-pass也与legacy失配，则回退legacy。只记录request ID、hash、首个不同索引、长度及错误类型，不记录正文。失败原始输入只在用户授权的本地隔离目录留存。

## 4.8 为什么暂时保留全量render

用户观测最长render只有13ms，远低于80.6s编码。保持fullrender使输入语义与旧实现一致，并为LCP验证提供权威bytes。优化后复杂度仍包括O(B)的render/byte比较/元数据重建；不能声称整请求严格O(delta)。省掉的是BPE与重复prefix扫描的大量成本。
