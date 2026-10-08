# AI_START_HERE · v2 执行入口

## 你要交付的结果

在固定提交和实际 `prepare-detail` 观测补丁之上，交付 **无跨请求可变缓存的 B0+B1 前端修复**。对完全相同资源与请求，保持原 `Tokenizer::encode`、`encode_rendered_chat`、PreparedPrompt 的输出和确定性错误合同；减少两层重复扫描；以独立 legacy oracle、有限差分、匹配 CPU 基准和一次维护窗口 HTTP 对照证明。

**本包不是产品实现完成的声明。你必须产生并核对自己的证据。**

## 先读与先做

1. 读取原仓库根 `AGENTS.md`、本目录 [AGENTS.md](AGENTS.md)、[范围](docs/00_SCOPE_BASELINE_EVIDENCE.md)、[评审处置](docs/15_REVIEW_DISPOSITION.md)。原仓治理与用户生产授权优先。
2. 用 [T00](tasks/T00.md) 锁定完整 commit、dirty diff、overlay、不可变镜像身份、实际 artifact 六份资源。只读核查不能演变成重启服务。
3. 运行本包自检，然后按 [任务 DAG](tasks/index.json) 和 [07 执行计划](docs/07_AI_EXECUTION_PLAN.md) 做 red → green → review。任务卡独立记录修改文件、命令、退出码、结果路径和 hash。
4. T03 B0 与 T05 B1 分别提交。产品最终只有一条优化编码路径，旧版本保留在独立测试 oracle 或已锁定旧镜像，不保留四个产品开关。
5. T11 HTTP 前必须取得维护窗口授权、停止测试与生产抢卡、识别并隔离高频 2 工具客户端。无法隔离则该对照 `BLOCKED`，不是性能 FAIL，也不是 PASS。
6. T13 独立审查通过后才执行 T12。禁止未经授权更改 Docker、systemd、GPU 参数、TTL、L2 预算、其他客户端路由。

## 已经确定、不再重复争论

- B0 改搜索算法，不改 added-token 选择规则；不得“最长匹配”。
- B1 复用的是同一次请求中已经证明正确的 prefix，不是跨请求缓存。
- `append_frontier` 在 tokenize 后产生，不能作为 tokenize 前判断条件。
- `exact_frontier`、`encode_with_boundaries` 不是本基线现有接口，不能从新 master 文档复制名称当成已有实现。
- `rendered_chars` 是 UTF-8 bytes；schema20 `prepare_detail.tokenize` 包住了主编码与所有边界验证。
- H 是实际 `checkpoint_hints.size()`；“最后真实 user 之后的 assistant 数 +2”只适用于特定标准工具会话，不是所有输入的通用公式。
- 6 份生产资源从 artifact 提取；不按旧转换器的 `official_resources.py` 清单拒绝现网资源。
- 评审给出的 273K 与 296K 输入不符合 262K HTTP 预算，必须另生成并校准。

## 不得扩展的内容

首期不做 B2、不改 BPE、不新增模型或推理引擎、不改 tokenizer 资源、不删 checkpoint、不禁用 thinking、不改变 JSON/工具序列化、不用答案相似代替 token 等价，不为优化标题工具而悄悄切换其服务。

## 交接与中断恢复

每次结束更新 `task-report.md`（模板见 [任务报告](templates/task-result.md)），标明最后绿色 commit、仍红的测试、下一张任务卡和禁止动作。不要凭历史聊天记忆恢复工作。测试资源不足时，只交付对应编译/离线证据并明确剩余门未跑。

最终至少交付：实现 diff、来源与资源 hash、独立 oracle 绑定说明、差分失败最小化机制、CPU 原始重复结果、HTTP 请求/响应元数据对照、镜像与回滚核验记录、G0–G7 报告。敏感正文仅在用户授权的本地受控目录，不进入仓库或常规日志。
