# P2 最小实机验收：native 通过，HTTP 关联驱动停测，现网已恢复

**本轮 P2 最小实机验收未通过。** 4 个新增 native 场景全部 PASS，实际提交7次；C1 在第3个 HTTP 请求后因客户端 ID 关联错误安全停止，剩余 C1 及 C3 未执行。原服务已恢复并验活，独占窗口实际 **695.45秒（11分35秒）**，未超过40分钟。本次没有模型质量失败结论。

全程通过 `jssh 29`（`ssh -J jump 29`）。2026-10-22 19:16:07 至 19:27:43（Asia/Shanghai）运行，原生产镜像、参数和缓存目录恢复；没有重跑旧 Baseline、BO、G1、P1、编程题、grader 或本轮已通过 native。采样和 Pi medium/32768 不变，Pi 请求数为0。

[最终账本](../output/ninfer-v4-p2-hardware-20261022/final-summary.json) · [原控制器结果](../output/ninfer-v4-p2-hardware-20261022/evidence/controller-finished.json) · [恢复验活](../output/ninfer-v4-p2-hardware-20261022/evidence/restoration.json) · [最终只读核查](../output/ninfer-v4-p2-hardware-20261022/final-live-validation.json)

## 身份、预算与实际结果

实机对象是隔离分支 `codex/p2-async-export-20261022` 的源码树 `4c58698eda334ad3fc2c27c4fc22fc8c08dabbcc`，CLI/server/native 二进制与[原 r5 回执](../output/ninfer-v4-p2-observation-driver-20261022/observation-driver-r5/status.json)的 SHA 一致。候选只使用私有目录 `/home/hhtele/ninfer-v4-p2-20261022/hardware/window-20261022`、私有端口和 cache namespace，未挂载原生产 cache。

| 范围 | 本轮实际 | 上限 | 结论 |
|---|---:|---:|---|
| 新 native 场景 | 4 | 4 | 全部 PASS，各执行一次 |
| native 模型提交 | 1+2+3+1=7 | 7 | 无重发、无追加 |
| 候选 HTTP | 3 | 20 | health、telemetry、cold A；此后停止 |
| 恢复 wire 计账单位 | 4 | 4 | health 1 + 代理推理2（含上游）+ metrics 1 |
| 窗口 | 11分35秒 | 40分钟 | 未超时，36分钟恢复预留未触发 |

C1 原计划剩余9请求、C3原计划8请求均未运行。**C3 容量未测试，不是容量不足结论**，没有降 context。恢复额度已用满，本轮没有追加第二次停机窗口或探测。候选启动的内部 warmup export 也在原始日志中保留，不与 HTTP 请求重复计数。

native 原始结果分别见 [case1](../output/ninfer-v4-p2-hardware-20261022/evidence/native-case-1/result.json)、[case2](../output/ninfer-v4-p2-hardware-20261022/evidence/native-case-2/result.json)、[case3](../output/ninfer-v4-p2-hardware-20261022/evidence/native-case-3/result.json)、[case4](../output/ninfer-v4-p2-hardware-20261022/evidence/native-case-4/result.json)：

- case1：真实 CUDA fence 在后台复制前仍 pending，erase 在源 reader 持有时阻塞，释放后恢复。
- case2：同步/后台 image 逐字节一致，slot 保存/恢复通过；重启 Engine 后从 L3 恢复完整263-token frontier，实际复用263。
- case3：实际 D2H 后、alias 前受控故障可见，没有发布半成品 L2 alias；随后主动取消及新请求恢复通过。该 failed job 是预期注入证据，不是 CUDA 传输故障或模型失败。
- case4：Engine 析构等待真实 export 排空，终态记录源 reader 已释放。

## 停测原因与原请求核对

这是我方实机客户端的关联缺陷。旧客户端假定服务会回显发送的 `X-Request-ID`，而现有服务生成自己的规范 ID，并把它放在响应头和 request log 中。源合同位于 `src/serve/http_server.cpp` 的 `ensure_request_id()` 与 `make_request_log_context(...res.get_header_value("x-request-id")...)`，本轮未修改服务行为。

冷 A 发送 ID 为 `p2-1792668317608654979`；响应规范 ID 为 `req_843269dbc8eec8bc5ba46bbee08ff15e_3`。旧客户端用前者查日志，等待30秒后报 unknown，停止后续请求并触发原服务恢复。先前主机测试与评审未覆盖这个真实 HTTP 合同；本轮补上回归。

[真实 raw 离线核对](../output/ninfer-v4-p2-hardware-20261022/client-canonical-id-repair-v1/raw-reconciliation.json)已重算 request/raw/log SHA，确认：

- 响应完整、HTTP200；request_done 为 Engine request **2**，P **20057** / O **52**，`stop_token`。
- 对应完成 job **4**、lane **0**、digest `633361c7d74c00cc` 全部匹配；session 与 boundary alias 均成功。
- job2 属于另一 Engine request，未误关联。不存在需要重发的冷 A 请求。

原[失败 ledger](../output/ninfer-v4-p2-hardware-20261022/evidence/campaign/campaign.json)仍保留 `unresolved`、原超时和全部成本；不回写为成功。独立派生核对记录明确该请求已完成，语义未知结果为0，重发数为0。这次停测不能计作模型质量失败，也不能据单个成功请求把 C1/C3 验收标 PASS。

job4 的 host 时间记录为：排队至开始约2.187秒，copy span约0.232秒，源释放至发布结束约7.482秒，入队至发布结束约9.901秒。这是单次 host steady clock 观察，不是 GPU elapsed、L3 fsync、吞吐改善或完整任务 wall 的归因。

## 修复与必要验证

恢复现网后，仅修复隔离源码中的 `replay_agent.py` 与客户端测试：独立保存发送 ID 和 `server_request_id`，按响应规范 ID 关联；缺失、空或空白 ID 保留 raw 并停止，禁止回退、重发或隐式续跑。没有改 normalizer、引擎、codec、缓存策略、采样或 G1 golden。

修复后树为 `34d6fd408ab90214ba549401bb6a7c102b2b3a57`，与实机树只差上述两个 Python 文件。[修复补丁](../output/ninfer-v4-p2-hardware-20261022/canonical-id-fix.patch)、[源码快照](../output/ninfer-v4-p2-hardware-20261022/source-after-client-repair.tar.gz)、[远端源码回执](../output/ninfer-v4-p2-hardware-20261022/client-repair-source-receipt.json)均已保存。未创建 commit、push 或发布；新工具不能冒用旧 r5 的工具 SHA 或清空旧 campaign 后续跑。

通过29的固定 BO 镜像，在 runc/network=none、源码与证据只读、无 GPU 的容器中执行：

```bash
python3 -m unittest discover -s /src/tests/merge -p test_p2_replay_driver.py -v
python3 /out/reconcile_c1.py
```

结果为 **10/10 host 用例 PASS**，包括两项新增 ID 回归；已保存的真实 request/response/log 离线重放 PASS，没有新增 HTTP、模型或 GPU 请求。因变更仅两个 Python 文件，复用原未变二进制，没有重编或重跑已通过场景。精确 Docker 命令和原始输出见[验证回执](../output/ninfer-v4-p2-hardware-20261022/client-canonical-id-repair-v1/verification.json)。独立只读评审无剩余确定性 finding；评审者未执行实机请求。

## 原服务恢复与证据保全

恢复同一生产容器 `86cb6d9ae734...`、原镜像 `sha256:e753e228...`；新 PID **55505** 是正常重启结果。完整 args、两二进制 SHA、cache 挂载及原目录 inode/device 均与窗口前一致。原代理 MainPID1950、active/running，未停止或修改。健康、经原代理的实际推理和 processing/deferred=0 均在4个恢复单位内验证通过；最后只读核查没有追加请求。

原代理的直接 PID-FD 读取被宿主权限拒绝，权限预检失败均保留。本轮复用已验收原代理的 PID/start/argv/script 与监听 socket inode 连续性，再以真实代理推理验活；`direct_PID_FD_proof=false` 如实记录。候选的严格 PID-FD 归属校验未放宽。

原窗口冻结脚本、完整状态、request/raw/log、故障与恢复记录保留在远端持久目录。898项文件已登记 SHA/size；原 slot 文件单独在原路径保留，其他内容有约1.53GB远端归档。[完整远端回执](../output/ninfer-v4-p2-hardware-20261022/evidence-collection-receipt.json)列出路径与 SHA。82项元数据、全部请求/响应和日志另已下载并逐项校验，见[本机归档回执](../output/ninfer-v4-p2-hardware-20261022/metadata-collection-receipt.json)。未删除远端 cache、slot、失败或历史资料。

BO、Baseline、P1及真实 G1 的18处严格差分继续沿用原证据。V4 原388份文档另作改前快照，原断言和独立验收/发布门禁不删除。**本轮结论仍是：native 最小范围 PASS；HTTP 最小范围未完成；P2-GATE 未通过，生产发布未运行。** 修复后的客户端只取得主机与离线资格，后续须另行冻结 HTTP 验证清单，不能自动恢复旧 ledger、重跑 native 或把此次停测抹掉。
