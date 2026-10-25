> V3 继承资料：P0—P6 的任务目标和上游合入顺序继续有效。命令依赖须先按根目录 `support/REHYDRATE.md` 恢复。

# 07｜决策记录、风险与失败处置

## ADR-01：采用增量 merge，不 rebase 已部署分支

选择：从 O 建集成分支，按 P1/P2/P3/P4/P5 上游 milestone merge，P6 验收。理由：保留双方 ancestry，阶段可定位、可回滚。一次性全量合并虽然操作少，但边界、工具流、异步导出、KV、决策和图像一起变化，不利于定位真实回归。逐条 cherry-pick 则容易遗漏依赖和未来重复冲突。

## ADR-02：上游边界权威 + B0 单扫描后端

选择：生产只维护新 PromptBoundary / SegmentedEncoding 契约；保留 B0、memo、计数和 trace。被替代的 B1 strict-only 控制流不作为第二条生产逻辑继续存在。测试层保留旧算法作为 oracle。

拒绝：只把头文件声明拼起来；分别调用 encode_traced 和 encode_segmented；借用上游优化实现来生成自己的 expected results。

## ADR-03：新 KV 主方案，旧 E8 通过旧发布物回滚

选择：P4 独立 qualification 后采用 midrise `rk4v4`；旧二进制/参数/缓存保留。理由：旧 E8 路径属于共享祖先的实现，上游删除它并同时修改所有读写端/flag/state ABI，恢复会形成长期双 codec 维护面。用户要保留的 262K 容量和长编码质量应由门槛保障，不等同于永远保留同一 kernel。

触发失败：248K 容量无法达到、关键检索/Java 任务退化、数值 oracle 不通过、吞吐回退无法解释。处置：P4 保持未放行，定位新 codec/merge/配置问题；P3 可单独作为已经资格化的 Chat 改善版本，但最终 U 的生产资格仍未完成。

备选只在有明确必要时启动：新运行时恢复 `rk4v4-e8-legacy` 为独立 codec revision，覆盖 enum/options、A1/A2/A3 编解码、A4 只读 prefix、rotation、物理布局、flags、snapshot/image identity、bench/log/文档，独立 cache namespace，完整 oracle。不能只恢复 enum 和参数别名。该备选是条件性扩展，不在当前默认计划中悄悄增加第二条生产路径。

## ADR-04：日志 schema 跟随上游，定制采用命名扩展

选择：最终主 schema24 + `lkyprogramer.prepare_detail` version1；保留六个分项与 size key，并定义字节单位/未知值。理由：避免两个 schema20 的含义冲突，也避免抢占未来上游的 25/26。对历史日志做兼容读取，不改写历史原件。

## ADR-05：代码合入与生产功能启用分开

选择：保留完整上游 source/history；现有生产默认不开新决策 adapter，不额外启用图像决策。资格范围分为 Chat-qualified、decision-text-qualified、decision-image-qualified。无模型素材的附加能力标记未资格化，不能把 skip 计为 pass。

理由：同一调度线程内决策可能占用 Chat 服务时间；短决策 per-round 快不代表用户编码流量吞吐不受影响。BF16 决策精度参考也不证明 262K 压缩 Chat/视觉决策质量。

## ADR-06：单卡串行实验和镜像级发布

选择：独立构建、串行 A/B/A、旧发布物保留。拒绝：在生产目录 git pull；一个 4090 同时启动两份 27B；全局 docker prune；在回滚时共用不同版本 cache。

## 风险登记

| ID | 风险 | 严重性 | 首次拦截 | 处理/证据 |
|---|---|---|---|---|
| R01 | 生产镜像与 O 不一致 | 阻断 | P0 | 单独 PROD/O 基线；不覆盖未知 overlay |
| R02 | refs 更新导致分析过时 | 阻断 | 每次 import | 按 SHA 锁定；变化重新审计而非追随分支名 |
| R03 | B0 与 segmented 重复编码 | 高 | P1 | main encode=1、四路基准、计数无语义影响 |
| R04 | Explicit 边界错误地严格拒绝 | 阻断 | P1 | 独立 full-prefix LCP oracle |
| R05 | legacy 类型依赖生产 DTO | 高 | P1 | 测试类型隔离与旧二进制 oracle |
| R06 | schema20 混淆与单位错误 | 高 | P1/P3/P5 | 历史日志 fixture、命名扩展、字节单位 |
| R07 | 导出期间 lane 被复用 | 阻断 | P2 | fence 状态机、故障注入、并发真实模型 |
| R08 | 小 T kernel 数值/图状态变化 | 阻断 | P3 | Op oracle + MTP/graph +业务质量 |
| R09 | 新 codec 读旧 state | 阻断 | P4/P5 | 格式拒绝、不同目录/namespace |
| R10 | 向热路径引入锁/遥测饥饿 | 高 | P4 | 长请求中并发监控与客户端速率 |
| R11 | KV capacity 被当作每 lane 配额 | 阻断 | P0/P4/P6 | 共享容量账本、负向准入测试 |
| R12 | 半个工具调用被执行/持久化 | 阻断 | P3/P5 | begin/delta/end、cancel/length、历史完整性 |
| R13 | 决策 adapter 走生成 fallback | 阻断 | P4/P5 | API model-kind 测试，尤其 Anthropic |
| R14 | 图像同 grid 不同 profile 假命中 | 阻断 | P5 | preprocessing digest + MRoPE identity 测试 |
| R15 | G1 资料缺失，假装已复跑 | 高 | P0/P1 | resources/cases/toggle manifest；缺失明确阻断 |
| R16 | GPU 测试 skip/零测试被认作通过 | 阻断 | 每个 gate | JUnit 必测名单，真实 GPU evidence |
| R17 | 短上下文/关闭 thinking 掩盖退化 | 阻断 | P0/P6 | 冻结 profile，128K/192K/248K 各自门槛 |
| R18 | 缺少回滚 cache 或旧 image | 阻断 | 部署前 | 三件套可恢复并实际演练 |

## 停止与继续规则

失败先归因到四类：环境/资料阻断、集成错误、上游已存在行为、数值/性能权衡。不得通过更改 oracle、减少样本、扩大容差、关闭功能悄悄绕过。环境阻断允许继续独立的文档/CPU 任务，但不跨越所属统一 gate；附加决策功能未资格化可按范围显式排除，不影响已经完整证明的 Chat 资格。

每次失败保留最小复现、同模型 O/U/C 三方结果、source/image/profile 身份、判定依据和下一次只改变一个因素的实验。不要把所有异常都归因于“量化本来不稳定”。
