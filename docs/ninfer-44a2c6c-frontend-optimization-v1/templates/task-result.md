# Task result

填写task_id、base_commit、candidate_commit、diagnostic_overlay_hash及执行者。

| 项 | 记录 |
|---|---|
| 输入/资源身份 | 填真实hash与来源；缺失明确UNKNOWN |
| 修改文件 | 实际diff清单 |
| 红测 | 命令、退出码、预期失败与实际失败 |
| 绿测 | 命令、退出码、通过/失败/跳过数 |
| 等价证据 | token+全部metadata对照与错误case |
| 性能证据 | 逐请求数据文件、统计scope、环境 |
| 残留/回滚 | 状态、镜像、服务与清理 |
| 当前限制 | 未执行检查及原因 |

## 下一任务可依赖的接口

只列已经实现并验证的接口，不复制规划接口伪装为已完成。
