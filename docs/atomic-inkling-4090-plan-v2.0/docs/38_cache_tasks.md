# 缓存与统一预算实施计划（L00–L07）

> **For agentic workers:** 按[AGENTS](../AGENTS.md)逐任务实施、验证、审查；提供superpowers时可用subagent-driven-development/executing-plans，没有插件也执行本包合同。本文是待实施计划，当前所有L能力NOT_RUN。

**Goal:** 在Atomic中建立可逐bit恢复的完整状态缓存，并在有证据时扩展SM89压缩Pool及资源协同。
**Architecture:** 状态/拥有权/预算先闭合，raw Tier→compressed Tier→局部Pool→完整profile→独立确认。原CUDA生命周期和G0–G7不变。
**Tech Stack:** C++/ggml/CUDA与Python实验工具；可选Rust/Tile走原K任务，未选择时不阻断。
**Spec:** [总体计划](00_integrated_master_plan.md)、[状态合同](34_cache_state_contracts.md)、[Tier](35_tier_cache_design.md)、[Pool](36_compressed_pool_sm89.md)、[资源协同](37_unified_resource_policy.md)。

## 全局约束与审查重点

- 源、资产、target、source representation、Codec/codebook、layout、state inventory、graph和预算分别锁定。
- 只读/写初始化有效范围；任意raw bits精确还原，模型非有限值另拒绝。
- 完整checkpoint与单KV record分开；同会话续接与跨请求prefix共享分开。
- token提交不等于压缩发布；已emit前缀不撤销；raw sealed、raw open、encoded新页并存峰值必须有界。
- metadata内容也有reader→update→replay事件边；不能只保护地址。
- 现有Q8_0与论文BF16不混比；新codec不得默认更换模型精度。
- 同一GPU一次一个性能实验；仅选中功能有资格依赖；原验收阈值不下调。

## 文件、接口和验证步骤

以下NEW/MODIFY路径均指将来的Atomic隔离checkout，不是在本Markdown包内已有实现。`lab.py cache-run`由L00增加的计划接口；当前不得执行它宣称成功。

### L00 · 来源、支持矩阵与实验输入冻结

**依赖：** T01；所选功能另按机器DAG条件依赖。

**Files：**

- `NEW tools/inkling-lab/cache_profiles.py`
- `NEW profiles/cache-capabilities.json`
- `NEW tests/test-cache-contracts.py`

**Interfaces：** 读取固定源、实际Tensor格式清单；输出CodecProfile与逐shape/dtype/mask/spec支持矩阵，不把论文字段直接当真实值。

**测试与断言：** LX01, LX02。未知dtype/布局、错误codebook或不存在的source pin必须拒绝；每个可选功能写显式状态。

- [ ] 建立上述反例/正常fixture，运行并确认待实现能力失败，不能因skip/空集获得绿色。
- [ ] 在T01 runner增加cache-run phase分派、参数解析及明确未实现退出码；先实现validate/inspect，不伪造后续phase。
- [ ] 运行适用CPU/GPU/state测试；保存实际命令、非空case数、失败计数及原始输出。无硬件则BLOCKED，保持已有工作产物。
- [ ] 按下列计划接口生成phase证据；该phase完成不等于G2–G6全部PASS。
- [ ] 完成同行审查与单任务commit；补齐DECISION和EXPERIMENT，继续已授权且依赖完成的任务。

```text
PLANNED_AFTER_L00_AND_IMPLEMENTATION
python tools/inkling-lab/lab.py cache-run --phase l00 --manifest runs/L00.json --cache-profile profiles/cache.json --out evidence/L00
```

**DoD/停止：** Reviewed deliverable completion is separate from capability gates; selected cache features need explicit profile-scoped evidence. Unselected cache tasks do not block T12. 不能实现或没有收益时保存可复现原因；原始数据不可由摘要替代。

### L01 · 完整StateInventory与快照事务

**依赖：** L00, T05；所选功能另按机器DAG条件依赖。

**Files：**

- `NEW common/atomic-cache-record.h`
- `NEW common/atomic-cache-state.h`
- `NEW common/atomic-cache-state.cpp`
- `NEW tests/test-atomic-cache-state.cpp`

**Interfaces：** Context/Cursor是Atomic真实上下文的只读适配视图；capture_state_inventory(Context&, Cursor)生成成员表；prepare_checkpoint返回带lease的SnapshotTicket；publish/restore只有在全部校验和event完成后生效。持久格式按34，不序列化裸CUDA句柄。

**测试与断言：** LX07, LX08, LX09, LX10, LX13, LX14, LX15, LX19, LX21, LX22。故意漏conv、错末token边界、跨请求复制RNG/工具状态、图表早覆写均应失败；合法同session续接与独立重算比较。

- [ ] 建立上述反例/正常fixture，运行并确认待实现能力失败，不能因skip/空集获得绿色。
- [ ] 实现typed subrecords目录、原子发布、state/member-source绑定、resource admission、事件寿命和CS01–CS25语义验证；manifest可以先验证结构，不能代替语义程序。
- [ ] 运行适用CPU/GPU/state测试；保存实际命令、非空case数、失败计数及原始输出。无硬件则BLOCKED，保持已有工作产物。
- [ ] 按下列计划接口生成phase证据；该phase完成不等于G2–G6全部PASS。
- [ ] 完成同行审查与单任务commit；补齐DECISION和EXPERIMENT，继续已授权且依赖完成的任务。

```text
PLANNED_AFTER_L00_AND_IMPLEMENTATION
python tools/inkling-lab/lab.py cache-run --phase l01 --manifest runs/L01.json --cache-profile profiles/cache.json --out evidence/L01
```

**DoD/停止：** Reviewed deliverable completion is separate from capability gates; selected cache features need explicit profile-scoped evidence. Unselected cache tasks do not block T12. 不能实现或没有收益时保存可复现原因；原始数据不可由摘要替代。

### L02 · 真实KV采样、Codec参考与成本表

**依赖：** L00, T03, T04；所选功能另按机器DAG条件依赖。

**Files：**

- `NEW tools/inkling-lab/cache_corpus.py`
- `NEW tools/inkling-lab/cache_codecs.py`
- `NEW common/atomic-cache-codec.h`
- `NEW tests/test-cache-codecs.py`

**Interfaces：** 用已资格模型导出初始化有效字节与LayoutDescriptor；encode_raw/ decode_exact以bytes+不可变CodecProfile为输入输出；先CPU位型oracle，后目标GPU编解码。不得将Q8_0伪装BF16。

**测试与断言：** LX02, LX03, LX04, LX05, LX06, LX16, LX17, LX18。原始位型全覆盖/随机与真实样本往返；8191/8192/8193、页/块边界、2GiB/4GiB偏移、不可压数据、码本替换和截断文件均有负例。

- [ ] 建立上述反例/正常fixture，运行并确认待实现能力失败，不能因skip/空集获得绿色。
- [ ] 只移植许可明确且格式匹配的参考；补raw fallback、长度上界与真正wire-format；按层/loop/head/位置记录payload、allocated、完整状态ratio以及同步/成本，不以单个平均数决策。
- [ ] 运行适用CPU/GPU/state测试；保存实际命令、非空case数、失败计数及原始输出。无硬件则BLOCKED，保持已有工作产物。
- [ ] 按下列计划接口生成phase证据；该phase完成不等于G2–G6全部PASS。
- [ ] 完成同行审查与单任务commit；补齐DECISION和EXPERIMENT，继续已授权且依赖完成的任务。

```text
PLANNED_AFTER_L00_AND_IMPLEMENTATION
python tools/inkling-lab/lab.py cache-run --phase l02 --manifest runs/L02.json --cache-profile profiles/cache.json --out evidence/L02
```

**DoD/停止：** Reviewed deliverable completion is separate from capability gates; selected cache features need explicit profile-scoped evidence. Unselected cache tasks do not block T12. 不能实现或没有收益时保存可复现原因；原始数据不可由摘要替代。

### L03 · Tier闲置快照与直接分页恢复

**依赖：** L01, L02, T10；所选功能另按机器DAG条件依赖。

**Files：**

- `NEW common/atomic-cache-tier.h`
- `NEW common/atomic-cache-tier.cpp`
- `NEW ggml/src/ggml-cuda/atomic-cache-codec.cu`
- `NEW tests/test-atomic-cache-tier.cpp`

**Interfaces：** CacheManager.store/lookup/restore消费L01 checkpoint和L02 CodecProfile；decode_cache_record使用34/35的有界目的span和CacheOpTicket；raw Tier与compressed Tier共享相同淘汰策略。

**测试与断言：** LX08, LX11, LX12, LX15, LX16, LX17, LX19, LX21, LX22, LX23, LX30, LX32。先RAM再SSD；每个encode/copy/write/publish/load阶段插入取消/短读/满盘/错误；保证无半状态可见，restore能与独立prefill比较。

- [ ] 建立上述反例/正常fixture，运行并确认待实现能力失败，不能因skip/空集获得绿色。
- [ ] 按Tier-0/1/2顺序实现；32/64/128MiB只是合计device staging候选，按最大record与在途峰值准入；不实现活跃token跨层缺页。
- [ ] 运行适用CPU/GPU/state测试；保存实际命令、非空case数、失败计数及原始输出。无硬件则BLOCKED，保持已有工作产物。
- [ ] 按下列计划接口生成phase证据；该phase完成不等于G2–G6全部PASS。
- [ ] 完成同行审查与单任务commit；补齐DECISION和EXPERIMENT，继续已授权且依赖完成的任务。

```text
PLANNED_AFTER_L00_AND_IMPLEMENTATION
python tools/inkling-lab/lab.py cache-run --phase l03 --manifest runs/L03.json --cache-profile profiles/cache.json --out evidence/L03
```

**DoD/停止：** Reviewed deliverable completion is separate from capability gates; selected cache features need explicit profile-scoped evidence. Unselected cache tasks do not block T12. 不能实现或没有收益时保存可复现原因；原始数据不可由摘要替代。

### L04 · 局部SM89压缩Pool与B1 Attention

**依赖：** L01, L02, T04, T05；所选功能另按机器DAG条件依赖。

**Files：**

- `NEW ggml/src/ggml-cuda/atomic-kv-pool.cuh`
- `NEW ggml/src/ggml-cuda/atomic-kv-pool.cu`
- `NEW tests/test-atomic-kv-pool.cpp`

**Interfaces：** PoolArena.reserve/seal/publish/retire控制页与raw overflow；局部AttentionProvider读取sealed records、pending raw和open tail；仅一个实际合法dtype/geometry的B1 global路径。

**测试与断言：** LX03, LX04, LX05, LX18, LX19, LX20, LX21, LX22, LX25, LX26。不支持SM/dtype/head/GQA/scale/softcap/mask必须拒绝；overflow容量0、最后slot、满池时不得写slot0或坏map；反例需能检测。

- [ ] 建立上述反例/正常fixture，运行并确认待实现能力失败，不能因skip/空集获得绿色。
- [ ] CUDA C++参考起步，使用SM89合法load/MMA并记录资源；E Codec和N Attention分开；先测prefill workspace与真实净容量，失败则NO_BENEFIT或限缩能力，不扩张后端。
- [ ] 运行适用CPU/GPU/state测试；保存实际命令、非空case数、失败计数及原始输出。无硬件则BLOCKED，保持已有工作产物。
- [ ] 按下列计划接口生成phase证据；该phase完成不等于G2–G6全部PASS。
- [ ] 完成同行审查与单任务commit；补齐DECISION和EXPERIMENT，继续已授权且依赖完成的任务。

```text
PLANNED_AFTER_L00_AND_IMPLEMENTATION
python tools/inkling-lab/lab.py cache-run --phase l04 --manifest runs/L04.json --cache-profile profiles/cache.json --out evidence/L04
```

**DoD/停止：** Reviewed deliverable completion is separate from capability gates; selected cache features need explicit profile-scoped evidence. Unselected cache tasks do not block T12. 不能实现或没有收益时保存可复现原因；原始数据不可由摘要替代。

### L05 · Pool完整R3、SWA、prefill与所选投机资格

**依赖：** L04, T10；所选功能另按机器DAG条件依赖。

**Files：**

- `MODIFY L04 local pool/provider files`
- `NEW tests/test-atomic-kv-pool-state.cpp`
- `NEW profiles/cache-model-capabilities.json`

**Interfaces：** 完整Profile声明每slot后端、spec/verify widths、graph generation和目标算术；dispatch只选择已资格子路径。未选研究机制不成为前置依赖。

**测试与断言：** LX11, LX12, LX20, LX21, LX22, LX25, LX26, LX27, LX28, LX29。SWA环绕、raw/压缩边界、各拒绝位置、EOS/cancel及恢复后AR64；仅对启用的2DSD/LoopCD增加相应测试，但不得由native DSpark资格推导。

- [ ] 建立上述反例/正常fixture，运行并确认待实现能力失败，不能因skip/空集获得绿色。
- [ ] 串行完整模型先通过，再接native spec；mixed raw-SWA合法时可保留；新数值路径按N和QC验证；所选2DSD需要R03先资格。
- [ ] 运行适用CPU/GPU/state测试；保存实际命令、非空case数、失败计数及原始输出。无硬件则BLOCKED，保持已有工作产物。
- [ ] 按下列计划接口生成phase证据；该phase完成不等于G2–G6全部PASS。
- [ ] 完成同行审查与单任务commit；补齐DECISION和EXPERIMENT，继续已授权且依赖完成的任务。

```text
PLANNED_AFTER_L00_AND_IMPLEMENTATION
python tools/inkling-lab/lab.py cache-run --phase l05 --manifest runs/L05.json --cache-profile profiles/cache.json --out evidence/L05
```

**DoD/停止：** Reviewed deliverable completion is separate from capability gates; selected cache features need explicit profile-scoped evidence. Unselected cache tasks do not block T12. 不能实现或没有收益时保存可复现原因；原始数据不可由摘要替代。

### L06 · 缓存、专家与投机的协同实验

**依赖：** L01；所选功能另按机器DAG条件依赖。

**Files：**

- `NEW tools/inkling-lab/cache_coupling.py`
- `NEW profiles/cache-factorial-plans.json`

**Interfaces：** 消费已资格L03和/或L05以及实际选中特性的G2/G4记录；输出冻结四格或其他预注册小矩阵的完整请求证据，不由JSON选择功能直接授权。

**测试与断言：** LX16, LX17, LX18, LX23, LX24, LX30, LX31。检测同一节省字节重复分配、缺特性资格、baseline已全驻留仍声称专家收益、漏失败样本或后台干扰；每项有可拒绝的合同。

- [ ] 建立上述反例/正常fixture，运行并确认待实现能力失败，不能因skip/空集获得绿色。
- [ ] 按37记录allocation峰值/PCIe/SM/CPU干扰；先等工作负载再等预算容量对照；冻结唯一赢家或NO_BENEFIT，不能连续复用holdout挑选。
- [ ] 运行适用CPU/GPU/state测试；保存实际命令、非空case数、失败计数及原始输出。无硬件则BLOCKED，保持已有工作产物。
- [ ] 按下列计划接口生成phase证据；该phase完成不等于G2–G6全部PASS。
- [ ] 完成同行审查与单任务commit；补齐DECISION和EXPERIMENT，继续已授权且依赖完成的任务。

```text
PLANNED_AFTER_L00_AND_IMPLEMENTATION
python tools/inkling-lab/lab.py cache-run --phase l06 --manifest runs/L06.json --cache-profile profiles/cache.json --out evidence/L06
```

**DoD/停止：** Reviewed deliverable completion is separate from capability gates; selected cache features need explicit profile-scoped evidence. Unselected cache tasks do not block T12. 不能实现或没有收益时保存可复现原因；原始数据不可由摘要替代。

### L07 · 独立确认、服务回放与可回退交付

**依赖：** L06, T10, T11；所选功能另按机器DAG条件依赖。

**Files：**

- `MODIFY tools/inkling-lab/qualification.py planned by T01`
- `NEW profiles/cache-release-candidate.json`
- `NEW tests/test-cache-service-replay.py`

**Interfaces：** 汇总完整profile与所有选中特性的原始证据；输出T12候选资料，不产生G7授权。实际工具副作用用隔离fixture，Pi测试保持active=1。

**测试与断言：** LX30, LX31, LX32。独立确认达原统计与质量门；至少100次save/restore/cancel交错；8h且200请求soak，涵盖已承诺长context和真实raw回退。

- [ ] 建立上述反例/正常fixture，运行并确认待实现能力失败，不能因skip/空集获得绿色。
- [ ] 执行原5%/10%、CI、p95、绝对SLO、150/300业务与状态恢复要求；容量晋级独立写代价；归档argv、日志、hash、失败与回退演练。
- [ ] 运行适用CPU/GPU/state测试；保存实际命令、非空case数、失败计数及原始输出。无硬件则BLOCKED，保持已有工作产物。
- [ ] 按下列计划接口生成phase证据；该phase完成不等于G2–G6全部PASS。
- [ ] 完成同行审查与单任务commit；补齐DECISION和EXPERIMENT，继续已授权且依赖完成的任务。

```text
PLANNED_AFTER_L00_AND_IMPLEMENTATION
python tools/inkling-lab/lab.py cache-run --phase l07 --manifest runs/L07.json --cache-profile profiles/cache.json --out evidence/L07
```

**DoD/停止：** Reviewed deliverable completion is separate from capability gates; selected cache features need explicit profile-scoped evidence. Unselected cache tasks do not block T12. 不能实现或没有收益时保存可复现原因；原始数据不可由摘要替代。

## 资格与退出码

0=该操作真实完成且自身检查通过；1=运行失败；2=实现/模型/硬件缺失；3=合同非法。所有phase必须显式报告operation、evidence_kind、实际launch与case数；exit0仅是runner结果，独立gate审查才授能力。

读取[cache-object-contract.json](../manifests/cache-object-contract.json)及[cache-semantic-rules.json](../manifests/cache-semantic-rules.json)。Schema只检查结构；L01必须实现跨文件、真实bytes、offset、身份、状态完整性、预算与事件语义验证。没有semantic validator时不能将PUBLISHED记录或合法JSON当成恢复资格。

活跃请求跨GPU/RAM/SSD的逐token缺页、跨loop delta codec和独立全后端仍为后置研究。L07完成产生可审阅候选，不等于部署授权。

## v2交叉审查后的唯一接口与适用范围

- L00冻结wire/header合同，L01实现`atomic-cache-record.h`；L02可按冻结协议并行写CPU codec参考，不另定义格式。
- run中唯一扩展为`config.cache_profile`，字段为mode、object_contract、codec_profile、state_inventory、resource_admission、transfer_policy。旧`*_ref`扁平别名禁止并存。成功的已选Tier/Pool记录必须给出五个非空artifact引用并验证真实文件/hash、执行capability；NOT_RUN/BLOCKED可以保留null但不授能力。
- L01补齐docs34§9的continuation_binding、物理key/view/arena映射、权威提交水位与CS26–CS29。JSON Schema检查不等于这些语义已实现。
- L05的通用测试不包括未选特性：native_dspark才要求LX27/T06，2dsd才要求LX28/R03，loopcd_hidden/logits才要求LX29/R04。机器DAG的conditional_required_tests和catalog applicability是规范；选中但缺证据必须BLOCKED，不能自行skip。
- L03的LX32仅消费至少100次功能性save/restore/cancel及无重复提交；8h且200请求的服务soak由L07/G6在T11后完成。阶段任务可交付组件证据，但不得提前宣称完整G6。
