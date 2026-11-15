# Strata / RTX 4090 底层证据链增补包

版本：A1 · 2026-11-10（北京时间）  
适配：strata_observability_specpilot_foundation_20261106.zip（v1.0）  
性质：源码审计、增量设计、AI 可执行实施计划与离线合同示例；不是优化补丁，不是已部署底座。

## 先给结论

两个来源值得补充，但不能作为“4090 还有大幅提速空间”的证据。

- samir-vllm：借鉴清楚的分页/预算/临时内存生命周期与小型正确性对照；不复制其引擎、scheduler 或基础 CUDA kernels。
- Nabo kernel-primer：借鉴从真实耗时到编译产物、访存计数和机制证伪的工作方式；不外推 H200/JAX/RL 的收益。
- Strata 当前主线已有 token forcing、dispatch 统计、运行 manifest、spill 检查和多种微基准。本增补只补它们与原完成路径归因底座之间的身份、覆盖、误差和裁判连接。

最重要的新事实：**STRATA_VERIFY_PROFILE 会改变部分融合与并行路径；force_check.py 的 PASS 在输入集合不完整时也可能出现。** 前者必须先做观察器资格，后者必须先做完整性守卫。本次已以当前源码做三项纯离线反例复现，未启动引擎。

## 本包新增什么

| 增量 | 解决的问题 | 不重新建设 |
|---|---|---|
| 编译产物—运行路径身份桥 | 看到的 PTX/SASS 是否对应请求实际使用的代码 | 编译器、第二套 manifest |
| kernel 证据附件 | 关联 shape、layout、精度、图实例、计数器与完成 sink | 原 completion-path/v1、DAG 归因器 |
| 定向计数器协议 | 低带宽到底是流量多、访存推进慢，还是观测改变了调度 | 常开全量 NCU、第二套看板 |
| 数值输入完整性守卫 | 防请求交集、位置缺漏、单 stock arm、告警被当 PASS | 上游 Token Forcing 算法/新 scorer |
| 内存所有权与小 oracle 合同 | 防容量双计、scratch 过早复用、页表/有效域错误 | allocator、KV 压缩、adaptive tail |
| 增量实施与负例 | 可逐任务开发、每阶段独立审查、无候选正常停止 | LabFlow/controller/统计器 |

## 固定证据

| 对象 | 固定身份 | 范围 |
|---|---|---|
| 原始基础包 | SHA256 0a08667d8fc03d91e1b961a9e705f4649b357e65f25e285db847c390c2c99934 | 本轮已找到、读取并核 hash |
| samir-vllm main | 127c48089d5d872ca5c8b1f92fd624478975dde0 | 2026-11-03 提交；教学 Llama-3.2-1B/BF16/2048 |
| Strata main | 504b143342a9fe1aa8320a7b31e11f5c0ac265c3 | 2026-11-09 提交；源码参考，不是部署事实 |
| 用户实验档案 | fbc24c2603c2eca4bfbeca628c6c2476b7516bdc | 4090-report / docs/strata_4090_128k_lab |
| Nabo 原文 | 2026-10-15 发布/编辑；2026-11-10 获取 | 作者案例，不是本机复现 |

出处及限制见 [来源锁](sources/LOCK.json)、[来源目录](sources/SOURCES.md)。

## 阅读与执行顺序

1. [START_HERE_AI.md](START_HERE_AI.md)：给执行 Agent 的边界。
2. [接入原包与去重](docs/03_BASE_INTEGRATION.md)：原 O0–O6 的准确补充位置。
3. [samir-vllm 审计](docs/01_SAMIR_VLLM_REUSE.md)、[Nabo 方法落地](docs/02_NABO_TO_4090.md)。
4. [证据附件合同](docs/04_EVIDENCE_CONTRACT.md)、[编译产物与计数器](docs/05_CODEGEN_AND_COUNTERS.md)。
5. [数值守卫](docs/06_NUMERICAL_GUARD.md)、[内存与 oracle](docs/07_MEMORY_AND_ORACLE.md)。
6. [实施计划](plans/IMPLEMENTATION_PLAN.md)、[测试与验收](docs/08_TEST_AND_ACCEPTANCE.md)、[运行手册](docs/09_RUNBOOK.md)。
7. [实际验证结果](VALIDATION.md)、[独立审阅](REVIEW.md)。

解压后先运行包内离线检查：

~~~bash
python3 -B -m unittest discover -s tests -v
python3 -B tools/validate_addendum.py
~~~

这些命令不启动引擎、不接 GPU、不联网，也不证明产品已经实现。

## 不变的决定

保留 MTP spec4；DFlash2 已服务验收但未达到采用条件，不重新比较。F01/F02/F03、P01/P01B、P24 HC、NP3、SPEC/SPECCOST 的关闭/阻断不因新文档或新 donor 重置。旧六项长检索 FAIL、P05 证据阻断仍在。

默认 engine starts=0、generation requests=0、GPU budget=0；本轮没有修改生产、上游或用户仓库。未来开发、GPU 资格、优化实验、部署四种授权分开。**本包成功标准是更难被错误证据误导，不是承诺提速。**
