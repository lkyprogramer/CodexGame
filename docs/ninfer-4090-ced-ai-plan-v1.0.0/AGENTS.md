# 执行约束

本文件约束本计划包的执行，不自动覆盖目标仓库的 `AGENTS.md`。执行 AI 必须读取目标仓库当前规则；本任务明确增加了近似 prefill 产品能力，但没有授权无关重构、改权重、升级生产系统或隐瞒数值变化。

## 不可违背的约束

1. 只在独立实验副本/工作区及新构建目录开发。原生产源码、镜像 tag、模型文件、unit、NGINX 与兼容层保持不变。禁止 `git reset --hard` 清理用户目录，禁止浮动 `latest` 替换。
2. 一张 4090 同时最多运行一个 27B 引擎；Teacher 导出、Predictor 训练、oracle 与 candidate 串行独占 GPU。不得把“冻结权重”当成能同时加载两个模型的理由。
3. 本次用户授权的是**生成计划**。后续执行时，暂停生产需要显式维护授权 `allow_production_pause=true`；默认 false。无权限时停止在 `BLOCKED_RESOURCE`，不等待、不后台轮询、不擅自停现网。
4. 默认保留 `rk4v4-e8`、262144 容量与原 MTP3 配置作为原生基线；数值原语测试可单独用短上下文 BF16 KV。不得把换 KV/关 MTP/改思考强度的收益归给 CED。
5. `CED/LSP=off` 是交付默认值。真实推理不允许 Teacher 张量、未来 token、测试答案或另一请求的状态进入 candidate。
6. 首期只启用 Qwen3.8-27B groupwise-int、文本、C=1、无 LoRA；未验证的 Vision、其他模型/adapter、多并发请求在 admission 阶段拒绝近似路径或转到正确的原生路径，不能半途中悄悄切换状态语义。
7. 保留全部 64 层 base weights、全部层的 KV 和 GDN 状态；跳过计算不等于可以少分配这些状态。
8. MTP 的权重、KV、hidden、pending anchor、位置、draft 与 checkpoint 是额外合同；P4 只证明 no-spec，P5 才证明 MTP3。
9. 任何受到近似前缀影响的状态，后续执行完整层或 exact-tail 都不能洗成 native 状态。跨模式、跨 Predictor、跨 split、跨 adapter 的缓存禁止混用。
10. Task 允许小范围开发验证；Phase 末统一完整验证。GPU 测试独占串行，CPU 文档/训练工具开发可按 DAG 并行。执行者不得把同一文件交给多个 worker 同时修改。
11. Gate 只认明确证据：命令、退出码、非空用例计数、原始数据、集成提交、配置。CTest exit 77 / missing model / missing GPU / 超时不能算 PASS。
12. 训练、长测按预设 token/磁盘/试验上限执行。未通过时最多两轮**有因果依据**的修复重验；无改动重复跑到碰巧成功禁止。
13. 不上传用户源码、prompt、状态或日志到云端；导出的状态等同敏感会话数据，owner-only 权限，不纳入 git。
14. 当前自动化只输出实验结果/发布候选。生产启用和回退修改需要用户后续明确授权，不在本包自动执行范围。

## 最小工作记录

每 Task 记录修改文件、契约、局部验证与残留限制。每 Phase 用同一集成提交输出 `phase-report.md` 和 `gate.json`。无需再建多套规划树；不做与目标无关的审计或格式化。
