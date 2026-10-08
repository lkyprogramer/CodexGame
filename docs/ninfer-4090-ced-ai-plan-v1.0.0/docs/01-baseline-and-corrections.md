# 01 现网基线、证据等级与方案修订

## 1. 基线

本包以 2026-09-11 读取的默认分支 `tensorninja` 为源码基线：

```text
44a2c6c3392c9d51e76a895ed97bf1867530d252
commit timestamp: 2026-09-03T11:24:00Z
```

用户 2026-09-08 部署文档与这一提交一致。[S01][U01] 执行时仍须记录二进制实际 build id；不能只看工作树 HEAD。

| 项目 | 已有报告 / 计划处理 |
|---|---|
| GPU | RTX 4090，24564 MiB；单卡 |
| RAM / SSD | 约 62.5 GiB RAM / 600GB SSD 为已有环境线索；可用空间必须预检 |
| 制品 | `/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer` |
| 制品 SHA-256 | `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e` |
| 文件大小 | 18210531328 bytes；不是常驻显存精确大小 |
| 已报告来源 | `neroued/Qwen3.8-27B-NInfer`，rev `3526913004b1`；不能用变化后的 main 替换 |
| 生产 unit | `openclaw-qwen38-ninfer.service` |
| 镜像 / 容器 | `ninfer-4090:44a2c6c` / `ninfer-4090-prod` |
| 保护端口 | 18030（engine）、18343（兼容层）、28343（NGINX） |
| API model | `openclaw/Qwen3.8-27B-WORK` |
| Context / KV capacity | 262144 / 262144 |
| KV / speculation | `rk4v4-e8` / MTP3 + `--lm-head-draft` |
| Concurrency | 1 |
| 思考 | 兼容层默认 medium；原始 engine 缺省不能视为 medium |
| 空载显存 | 部署报告为 22594 / 24564 MiB，余量约 1970 MiB，不等于允许全部用光 |
| 工具链 | 使用已验证 CUDA 13.2 开发容器；宿主 nvcc 12.3 不用于本项目构建 |

这些是**历史部署记录**，不是本次对用户主机的新测量。P0 只读核对；发生不一致时记录实际值及原因，不自动升级。当前仓库要求 CMake≥3.28、CUDA compiler≥12.8、C++20、`sm_89`；`BUILD_TESTING` 默认关闭。[S02]

部署文档记录 4K/64K/120K/184K 的 MTP decode 约 112/111/110/87 tok/s，Java Pi 三题通过，但这不是大样本质量证明。已有 warm-prefix 命中线索意味着 CED 不能只靠冷输入 benchmark 宣称 Agent 提速。[U01]

## 2. 三种“正确”必须区分

- **Native-equivalent**：与同一 base artifact、codec、prefill compute profile、chunk、sampling 的原生 NInfer 路径对比。
- **Mathematical operator correctness**：新 StateOnly 算子对独立高精度 oracle 的数值误差。
- **Task-level quality**：近似状态之后真实任务是否仍正确。

当前 INT8 prefill 已有激活量化边界，native 也不是原始 BF16 模型的逐 bit 等价物。报告中用 `native`，避免笼统使用“无损 exact”。[S03]

## 3. 对上一轮方案的必要修订

| 原先容易误读之处 | 本计划采用的准确合同 |
|---|---|
| 有 continuation import/export 就能安全注入任何状态 | 它只提供搬运机制。层状态、conv、frontier、hidden、MTP 与来源标记必须一起正确 |
| 只预测 GDN 的 k/v/g/beta 就足够 | 必须额外构造 pre-convolution QKV 的最后三个历史值。本计划直接预测 pre-conv QKV，再复用真实卷积 |
| Decode 路径没改，质量风险只在 prefill | 解码算子不改，但它消费近似前缀，误差可影响整段输出、MTP 接受率和后续多轮 |
| ReplaySSM 可直接扩到 100K | 现有 replay-record 接口的域为 T=2..16；长输入用新的 StateOnly large-T 路径，不扩大短窗口循环硬顶 [S04] |
| 原来的 MTP 可以原封不动启用 | MTP prompt KV 依赖逐 token final hidden；需要新增对应 Predictor head 和状态准备合同 |
| 精确尾部执行会修复整个旧前缀 | 只保证尾部走原生算子，不保证消除早期近似误差 |
| Cache hit 等于零成本 | 省去复算，但仍有匹配、状态恢复、拷贝和排队成本 |
| 256K Context 可以因为 Predictor 而随意缩短 | 262144 是需保留的 native 能力；CED 初期仅资格化至 200000，超过时走正确的 native 路径 |
| CED-32 理论必然 2× | 只有忽略 Predictor、状态构造、KV 编码、尾部和共享成本的简化计算；不是真实上界证明 |

原生 DeepSeek CED 是模型结构和训练的一部分。本工程针对既有 Qwen checkpoint 进行 learned state approximation，不能引用 DeepSeek 成绩证明本工程有效。[S05]

## 4. 实验推进原则

优先确认“能正确接入”和“成本可能有利”，再训练；先 48/16，再 40/24，最后 32/32。不得把约 2496 tok/s 的仓库冷 prefill 记录当作用户真实 Agent 的当前吞吐，不能把 5090 的 benchmark 混入 4090 验收。[S03]

本包中的 1.10×、1.15×、误差阈值、数据量、预算和质量门槛均为**建议的研发决策线**，不是文献保证或已测结果。它们在 P0 冻结，不能看完测试结果后再调低。

来源索引：[源码与证据清单](08-source-map.md)。
