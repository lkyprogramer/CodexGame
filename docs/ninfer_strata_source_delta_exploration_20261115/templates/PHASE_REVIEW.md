# 独立 Phase 审阅 / 验证记录模板

状态：TEMPLATE_NOT_RUN。

- phase / experiment_id：null
- reviewer / verifier（须独立于对应实现）：null
- 输入manifest与spec hash：null
- 工作树/二进制/模型身份：null
- 权限与预算范围：null

## Reviewer

- [ ] 机制差量不重复旧关闭；H2/K-PAIR/M0标签正确。
- [ ] 没有用公开HEAD代生产；未绑定值不伪装0。
- [ ] D1同来源同W消融、实际skip与catch-up；H2词表/数值/sidecar账。
- [ ] Target / q / RNG / mixed-state / terminal语义正确。
- [ ] 只改批准范围，default-off，原scorer/holdout未变。
- [ ] Source claims、作者bench与本机结果分离。

Critical / Important / Minor发现、固定文件定位、处理意见：

`未填写，不能视作无发现。`

## Verifier

- [ ] 从原件独立运行本Phase获准的最小测试或重算，记录完整argv/exit/stdout/hash。
- [ ] 没有权限时不启动GPU，不把CPU PASS扩成模型资格。
- [ ] missing/drop/stale/失败/预算计数正确。
- [ ] 正式统计无伪重复、成功交集/补样本/挑最好格。

命令与观察结果：`NOT_RUN`。

## 门决策

`PASS / REJECT / BLOCKED / INCONCLUSIVE`：null；原因与证据：null。

未关闭Critical不得进入下一Phase；独立审阅本身不提供下一Phase权限。
