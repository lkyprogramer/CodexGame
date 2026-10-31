# F03 · CPU验证回执

结果：审计/CPU验证完成，NO_QUALIFIED_CANDIDATE。没有GPU引擎启动或推理请求。详细报告在父目录`reports/F03-SNAPSHOT-LIFECYCLE-AUDIT-20261031.md`。

实际入口，CPU-only：

```bash
function jssh() { ssh -J jump "$@"; }
jssh -o BatchMode=yes -o ConnectTimeout=10 29 \
  'exec python3 -B /home/hhtele/strata-lab-4090/workspace/frontier/f03-20261031/CPU_VALIDATE.py'
```

每条g++/link/test命令、cwd、退出码、CUDA_VISIBLE_DEVICES和输出保存在同目录cpu/*.command.json及stdout/stderr。脚本本次执行一次，不自动复跑。

| 验证 | 结果与实际范围 |
|---|---|
| 原conversation_cache_test | 4834 CPU checks PASS，header-only |
| 基线扩展transfer test | 2068 host checks PASS，原GNU wrap，不初始化设备 |
| 单行原型扩展transfer test | 2068 host checks PASS，含完整/增量payload及每个copy点失败不发布 |
| buffer probe | 固定ABBAAB三对，payload一致；性能筛查不通过，三对均慢6.08%–7.74% |
| CPU-only依赖 | 裸probe ldd无CUDA；transfer链接旧库、CUDA_VISIBLE_DEVICES=-1 |
| 原件/源码 | root与独立Reviewer核42文件SHA/长度及18源码SHA一致 |
| 生产/配置保护 | 13保护hash、基线binary及配置不变；6144MiB/4slots/PT0不变 |

未运行GPU、模型请求、engine重建、GPU/DMA故障、native数值oracle、正式配对、质量验收或无关pnpm全仓测试。预先发现两个头文件路径猜测不正确，按真实include补齐18项源；Ninja无现成transfer目标，故只读取strata链接命令并手工链接旧库。它们是定位回退，不计为测试PASS。

剩余边界：CPU回归只能支持关闭本次筛查，不能证明真实GPU端到端退化、长期内存泄漏不存在或所有快照方向无空间。
