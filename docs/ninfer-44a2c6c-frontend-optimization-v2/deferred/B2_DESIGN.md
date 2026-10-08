# B2 跨请求 token-prefix cache · 明确延期

**DEFERRED：不属于v2首期实现或完成率分母。** 本文保存后续可用的设计推理，不授权创建缓存、CLI或生产shadow。

## 开启前提

必须先满足[12 §12.2](../docs/12_ROADMAP_AND_DECISION_RULES.md)的发布后触发条件。先证明B0+B1残余普通编码成本值得共享状态复杂度，再写新的实现计划和review。附件的B2原型计时没有包括LCP/guard与实际生命周期，不可当最终性能承诺。

## 可保留的安全切点证明

旧R0、新R1的原字节LCP=L；r是旧主扫描实际选中的addedtoken结束点，最长addedtoken字节M。若`r<=L`且checked条件`M-1<=L-r`成立，则所有起点q<r的完整匹配都结束于L以内，在两输入同时存在/不存在，r前的scanner选择相同。于是新编码可复用旧T[:t_r]，重编码R1[r:]。

普通段EOF或“当前prefix exact”不是未来稳定切点。旧render结尾的assistant opener可能被下一轮历史重写，所以需要LCP与资源identity，不可只按sessionID/轮数缓存。

## 若未来实施，必须具备

只读snapshot与完整资源identity；Tokenizer/模板/renderoptions/media控制隔离；有界hostbytes/LRU与pin；同session并发隔离；memo与GPUlane不同生命周期；fallback保留完整新编码；无法验证identity时miss；不直接复制模型生成token成前端golden；不会将CPU命中当GPU也命中。

保存rawtext、tokenIDs、真实restart、资源fingerprint，metadata重建而不假定上一轮GPUfrontier等于CPUfrontier。检查hash必须防碰撞误用或追加exact字节确认。旧v1的26个跨请求对抗case原样保存为[延期数据](b2_adversarial_cases.jsonl)。

## 验证与ROI

相同资源/请求上完整oldencode与增量结果逐项相等；统计包含LCP/hash/锁/查找/编码/publication/eviction的整请求成本。仍优先离线差分，不自动恢复生产80秒legacy shadow。最终若只省几百毫秒且维护复杂度大，应继续延期。
