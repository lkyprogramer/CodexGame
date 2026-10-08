# v2 相对 v1 的调整

## 执行顺序

v1 的“B1 后立即做 B2”替换为 **B0 → B1 → 离线差分/CPU绝对门 → 受控HTTP → 发布**。B2 只保留延期设计。原 T06–T08 跨请求缓存任务不再执行；v2 使用相同 T00–T13 编号保存任务卡规模，但每张卡的职责重新分配，禁止混用旧卡。

## 实质修正

- 新增 P0 added-token 重复 find 根因，不再误列为普通 BPE 常数优化。
- B1 trace 记录新旧语义一致的实际扫描，不要求沿用低效搜索实现。
- 主性能语料按最后真实 user 距离控制 H≈5/20；极端 H≈384 留作压力，不作生产代表。
- 发布取消生产 shadow 与四模式开关，保留独立 offline oracle、完整错误合同、一次隔离 HTTP 和镜像回滚。
- text/vision 的 shared encoder 都受益；count_tokens 受 B0 益处，不引入 media legacy 分支。
- 核对 artifact 真实资源与诊断 overlay；SHA 前缀只作线索，完整 hash 仍需现场冻结。
- 纠正 source-lock 的越界行号；未知范围只引用 symbol 和 blob，不伪造行范围。
- 新增 full_reset 独立项目，明确高缓存命中中位数不能排除严重冷启动成本。

## 对评审也作限定

保留原始评审不改写，但 [16 二次审计](docs/16_ASSET_AUDIT_AND_LIMITS.md) 明确：真实 tts 示例不是字符串前缀冲突；原型 oracle 与 B0 支路不覆盖全部错误；12 条 session 基准超过 262K；原始日志/资源/raw 语料缺失；scan bytes 是逻辑搜索跨度；B2 时间不含完整缓存生命周期。采纳建议不等于把评审所有推断当成已证明事实。
