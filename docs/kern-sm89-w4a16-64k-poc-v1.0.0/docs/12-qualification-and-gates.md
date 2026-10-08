# 一小时左右的资格测试与裁决

**前置条件：** 开发/编译/下载/模型重排/oracle捕获已完成，原始trace与模型锁已落盘。它们不计入一小时资格测试。第一次从零开发不可能由一个基准脚本凭空完成。

## 固定预算

| 阶段 | 预算上限 | 必需输出 |
|---|---:|---|
| 环境/制品复查、warm-up | 3min | device/config/artifact identity |
| 数值核心回归 | 10min | 同权重、teacher-forced、eager/graph |
| 4K/32K速度 | 5min | 3个seed×2048 target token |
| 真实64K | 10min | 3个seed速度 + 单独检索 |
| 10轮append与rewrite安全 | 8min | LCP/state/checkpoint trace |
| Pi Java三题 | 12min | 3/3、测试保护、真实工具记录 |
| 取消/切会话/restore | 7min | 有限状态、无污染、无OOM |
| 汇总/恢复 | 5min | decision与生产恢复状态 |

合计60min预算。某阶段超时则停止或标INCOMPLETE，不跳过必需门后给GO。生产恢复有独立安全尾部，不能为了卡住60min而省掉。

## 硬门

- 环境与制品：实际SM89；无Blackwell cubin；没有上下文截断/CPU权重offload；相同weight+profile身份。
- 数值：见08；所有pack/索引合同通过；没有非有限值或无法解释的state漂移。
- 容量：实际prompt id数=usage=65,536；连续完成至少2,048 target输出；真实峰值留≥512MiB。
- 性能：no-spec，短输入4K–8K至少3样本均≥50 tok/s；64K至少3样本均≥20 tok/s。50是阶段目标，不是承诺；若正确但未到50，记录性能未达标，可保留研究分支，不称GO。
- Agent：append能解释复用旧历史；近期rewrite不错误命中；Java3/3；取消后可继续；会话A/B/A不污染。

## 验收不同于系统比较

NInfer MTP3与Kern no-spec不能作同算法速度A/B。产品横比可看总任务完成时长，但必须列出各自精度/投机/thinking差异。正式引擎隔离比较使用同一W4A16 oracle、同KV、同state、同输入输出长度、同温度。

## 输出身份与证据

由T22把真实原始结果聚合为`evidence.json`，其路径相对本run目录，包含SHA。CPU工具`evaluate_evidence`拒绝缺文件、缺哈希、缺hardware/身份、不完整samples或“draft当output”。它是fail-closed的机械检查，不是防恶意伪造的远程证明；reviewer还要核对原始trace和运行来源。

```bash
python3 -m poc_tools.cli report results/RUN/evidence.json --out results/RUN/decision.json
```

`POC_GO`不自动升生产。失败或超时都保留已完成结果，不伪称全部成功。
