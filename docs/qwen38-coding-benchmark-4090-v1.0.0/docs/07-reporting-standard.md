# 07 · 最终报告标准

最终报告必须能让另一名工程师仅凭归档产物重建实验条件、核对样本并理解结论边界。

## 必须包含的章节

1. 执行摘要和明确推荐；
2. 基准版本、MANIFEST、日期、Lane、Suite、Seeds；
3. 数据完整性、缺失/重复、重跑和排除；
4. 硬件、server commit、构建与完整启动参数；
5. 模型、GGUF SHA、Quant、Template SHA、请求参数；
6. Normalized 质量主榜；
7. 六类能力矩阵和 Worst Category；
8. Agent 工具、公开测试恢复和代表性轨迹；
9. 成功任务效率、Token、VRAM、功耗；
10. Pairwise Bootstrap、McNemar、Holm 与质量门槛；
11. Template/MTP/Quant/Context/Reasoning 消融；
12. Optimized 部署榜；
13. 失败根因与补丁人工审查；
14. 私有 Java 回放；
15. 最终部署参数、路由建议和限制。

完整骨架见 `templates/final-report.md`。

## 最低表格

- 模型配置总表；
- 数据完整性表；
- Normalized 质量主表；
- 六类矩阵；
- Agent 工具矩阵；
- 4090 成功任务效率矩阵；
- Pairwise 效应量/CI/p/Holm 表；
- 消融表；
- 失败根因表；
- 推荐场景与路由表；
- 逐题逐 Seed 附录。

## 数据引用规则

- 报告中的每个总数应能回溯到 JSONL；
- 每个案例应指向 artifact/run_id；
- reasoning、timings、MTP 或 GPU 未覆盖时显示 `N/A` 与覆盖率；
- Endpoint error 与模型失败分开；
- 合成示例数据必须显著标注，禁止作为实测；
- Normalized 与 Optimized 不合榜；
- Template-only 与 Quant-only 改造明确标识归因。

## “胜出”措辞

只有通过预声明质量门槛时，才可写：

> B 在本实验条件下相对 A 构成 practical win。

否则写：

> B 在某些维度有提升，但因 Hard/Worst/Invalid/配对完整性未通过门槛，不建议替代 A。

禁止没有限定条件的“全面碾压”“保留 99% 智力”“最强 Coding 模型”。
