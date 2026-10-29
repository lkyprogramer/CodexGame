# 最终交付验证回执

日期2026-10-25；对象为本ZIP内最终整合目录。“通过”只适用于验证工具与文件完整性，不代表4090推理性能或模型质量通过。

## 1. 已执行

| 检查 | 结果 | 证据 |
|---|---|---|
| 完整Python单元/集成测试 | **103项：102通过，1跳过，0失败/错误**，退出0 | [完整输出](evidence/final-package-tests.txt)、[结构化回执](evidence/final-package-validation.json) |
| 真localhost SSE/HTTP | 包含在完整测试；覆盖首输出分类、绝对deadline、idle、heartbeat、半帧阻塞 | 同一完整输出 |
| schema2计划hash回归 | 先复现错误候选/exit0，再修为拒绝/exit2；受影响22项通过 | [red](evidence/statistics-request-hash-red.txt)、[green](evidence/statistics-request-hash-green.txt) |
| paired NI数值交叉检查 | 64组n/k，与SciPy beta分位独立比较；最大绝对差约3.11e-14，小于1e-10门槛 | [数值结果](evidence/quality-numeric-crosscheck.json) |
| park/restore plan | 离线结构有效，execution_result=NOT_RUN；adapter未实现 | [CLI回执](evidence/offline-plan-validation.json) |
| 30任务合成NI例 | NONINFERIORITY_NOT_ESTABLISHED，退出1；不能认证2pp | [CLI回执](evidence/quality-demo-final.json) |
| 文档/配置静态检查 | 内部链接、JSON、围栏、64方向/13计划/12PR锁、固定源码路径及行号 | [静态回执](evidence/package-static-validation.json) |
| ZIP内容与SHA256清单 | zip CRC、解压后manifest和CLI verify核对 | MANIFEST.sha256在包内；打包回执在ZIP旁 |

完整测试命令：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m lab.cli selftest
```

当前容器无JDK，可信Java参考实现测试跳过；目标机正式Java能力门必须配好隔离JDK/容器后运行。不要把跳过当通过。测试创建临时目录、git fixture和localhost服务，需要允许loopback绑定；本轮经自动审核运行。未启动模型、GPU或用户生产服务。

## 2. 独立审阅与修正

[Round1](evidence/review_round1.md)、[最终研究审阅](evidence/review_final_research.md)、[最终工具审阅](evidence/review_final_harness.md)及[处理回执](evidence/REVIEW_DISPOSITION.md)随包。主要修正包括失败分类、预算化时间指标、spec分子/分母、paired NI零差异区间、统计单位、已有能力边界、版本身份与计划hash拒绝门。

## 3. 尚未执行或实现

- 未连接目标机，没有新的Flash-Next/Strata GPU benchmark、长上下文数值或真实Pi成绩。
- CPU pool、ISA、CUDA kernel、cache政策等是实施计划，不是随包成品补丁。
- 正式真实任务适配器、restricted time-to-success性能分析、ABBA宏块、window trace、park/restore live adapter和allocator env对照需P00实施。
- 现成corpus/MIG是greedy/thinking-off的strict smoke，不是sampled-thinking、完整生产配置或正式NI。
- quality_gate只判相对binary任务非劣，不能证明任务独立/事前登记、绝对质量、性能、稳定或部署资格。
- 没有逐行审计所有引擎；07为深入donor机制，11为额外官方文档对照，各自证据深度不同。

## 4. 复核入口

```bash
python3 -B -m lab.cli verify
python3 -B -m lab.cli validate-plan --plan plans/park_restore.example.json
python3 -B tools/quality_gate.py --input tools/examples/quality-smoke-30.json
```

最后一项预期退出1，是正确拒绝证据不足的演示，不是测试失败。修改后须保留diff与来源并生成新版本清单，不能跳过完整性门继续引用原包身份。
