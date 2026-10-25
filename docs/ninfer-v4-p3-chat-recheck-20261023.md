# P3 Chat Completions 最小实机验收

2026-10-23。结论：**P3_MINIMUM_CHAT_ONLY_PASS_WITH_DISCLOSED_LIMITATIONS**。

本轮两个未关闭项均通过。复用原136个small-T数值场景、139次Op、130次Graph capture/260次replay和4个已通过的Chat合同，当前Chat-only最小功能范围完成。原FAIL/INCONCLUSIVE原件及成绩不改写；完整P3、性能资格和生产发布仍未取得。

原GPU服务现已保持停止，候选已清理，GPU计算进程为空。没有自动恢复原服务，没有部署修补代理到原服务。后续保持停止，直到用户要求恢复。

## 实际结果

| 新attempt | 结果 | 实机证据 |
|---|---|---|
| native Chat nonstream | PASS | 1个完整工具调用，逻辑text严格38 UTF-8字节，精确内容/hash正确，无多余反斜杠 |
| isolated proxy Chat stream | PASS | 9个非空参数delta，单response ID，`tool_calls`终态和一个`[DONE]`，最终逻辑text同为38字节 |

代理首参数到达客户端比**同一个server、对应请求的durable done早229.134765625毫秒**。同一主机时间戳和实际传输观测证明本次提前交付；不是逐token ITL，也不是吞吐或端到端收益估计。

转义一项只澄清了诊断提示中的一次JSON字面量解码，严格38字节预期和工具执行断言不变。产品parser没有添加通用unescape。本次单样本通过不能证明模型以后不会再误解提示。原44字节/6个多余反斜杠的失败仍保存，原始token IDs与解析前markup缺口也未消失。原因与离线修补见[修补报告](ninfer-v4-p3-chat-repair-20261022.md)。

## 实际预算与时间

| 计账项目 | 实际 | 上限 |
|---|---:|---:|
| 模型生成HTTP | 2 | 2 |
| 候选wire | 5：2客户端＋1代理上游＋2直接telemetry | 5 |
| 含内建warmup的模型提交 | 3 | 3 |
| 恢复wire | 0 | 0 |
| 新Op/Graph/native场景/Pi/旧Baseline/grader | 0 | 0 |

实机窗口上海时间 **00:34:28→00:36:24**，共 **116.431秒（1分56秒）**。720秒清理点、900秒硬截止保持，实际完成后提前清理；没有延长窗口、追加请求或失败重发。

telemetry的admitted_requests为1→3，含一次内建启动warmup；前后同server_instance_id，running/waiting/prefilling/decode_ready均为0。durable日志恰有两个request_start和两个request_done，Engine ID为2、3，canonical ID和代理nonce/body SHA严格关联，未结束请求0。

| 请求 | P | O | cache | 实际computed prefill |
|---|---:|---:|---:|---:|
| native nonstream | 411 | 245 | 0 | 411 |
| proxy stream | 411 | 224 | 409 | 2 |
| 合计 | 822 | 469 | 409 | 413 |

以上是按服务器请求求和的实际token计数，不是唯一上下文或计费token。warmup仅有提交计数，未暴露独立HTTP结果token，保留null。代理请求复用了相同提示前缀，不能把这组耗时当作冷请求对照实验。

## 冻结、执行与保留的失败

通过`ssh -J jump 29`（当前`jssh 29`等价路线）操作隔离目录：

- 候选源码：`/home/hhtele/ninfer-v4-p3-chat-repair-20261022/source`，树`fe1ad3328d2caad003dc51f8c0ab288e1e26df6a`，分支`codex/p3-chat-repair-20261022`。
- 实际窗口：`/home/hhtele/ninfer-v4-p3-chat-recheck-20261023-r2`。
- 窗口ID：`p3-chat-recheck-r2-20261023-163348`。
- 冻结回执SHA：`c1b91b386c0e46ab5d7d09becd78b45e98f307d083c504d65942b478cb4bdb19`。
- 候选serve SHA：`21e25ced57512cab1e8278544018e5e189e7f0865e881c2c919169905d6c331e`。复用已有二进制，没有重建或重跑已通过GPU任务。

新账本只接受五个具名wire单位，发请求前持久化请求与额度；任何未知结果停止后续且不重发。guardian先于停服就绪，控制器只有一次候选启动许可；清理按label/容器ID及PID/start ticks/argv验证所有权，不包含启动原服务的路径。候选使用独立cache/slots/CUDA目录，不写原缓存。

本轮首次启动在停服前因Docker Mounts列表顺序变化误报身份不一致。原检查器要求列表顺序相同，但实际所有挂载字段完全一致。原堆栈、launch receipt、空账本和PID77758仍运行的快照保存于`prestop-r1`。该次没有state/controller-started、没有停服、模型/GPU/wire均0，不是模型失败，也不是已开始窗口的截止时间重置。

R2仅将Mounts按完整字段排序比较，仍严格绑定字段、数量和重复项；新增一项定向检查证明Source/Destination/RW变化仍被拒绝。原冻结工具未覆盖，新冻结回执经独立复核后才单次启动。

其它准备失败也保留：旧远端Python不支持`tarfile.extractall(filter=...)`，在提取和服务操作前失败，改为核对本任务归档路径/成员后使用受支持API；新控制器unittest命令误用选择器产生2个loader错误及7项不必要重复，均单列记录。预算5项、读取合同3项、最终清理定向3项及Mounts定向1项实际通过；原控制器7项和新增2项通过记录复用，没有重跑旧GPU/Baseline任务。前轮BO夹具及代理导入失败、P2两次失败、C1附件缺口和18处G1差异继续保留。

## 服务与证据收尾

原GPU容器`86cb6d9ae7348fb928570e60290d2dc8ac933170a3c7bca32016ff347e2e1ddd`现为stopped/PID0，镜像`sha256:e753e2283db78bbe2fe1fc92b9d45300a27fd5765b367c434c9023cbf2cb1cb3`、Args、Binds、RestartPolicy保持。原缓存device/inode仍为66306/24150039。原代理PID1950继续运行，原shim SHA`4b0cefa5c1c785c43303e1d261969e889cd5989a95c135bb14998c96f5f6ea11`未替换；本次验证的是隔离修补代理。候选容器`228ede3d5dfd23eec227bf9270031c5c0a6574c9a5941e76c6399a3c3ead479e`停止并保留，候选子进程清理，GPU进程空。

[最终汇总](../output/ninfer-v4-p3-chat-recheck-20261023-r2/final-summary.json)与[逐wire账本](../output/ninfer-v4-p3-chat-recheck-20261023-r2/remote-evidence/hardware-r2/wire-ledger.json)包含精确请求ID、SHA、token及阶段记录。[原件归档](../output/ninfer-v4-p3-chat-recheck-20261023-r2/evidence-delivery.tar.gz) SHA：

`99a104b5d5fc034f8329586d8b5812e825417dba34c7b0f0cc6197a4f1c11b76`

本机和独立审计均复算101份文件size/SHA匹配；运行脚本与冻结哈希一致。候选运行缓存/slots/CUDA缓存和生成字节码不作为wire原件交付，保留在远端，未删除原缓存。[独立收尾审计](../output/ninfer-v4-p3-chat-recheck-20261023-r2/independent-audit.json)只读取现有原件，没有运行SSH、HTTP、GPU或测试。

原实机4 PASS/1 FAIL/1 INCONCLUSIVE保持历史事实。本次两项新attempt与原4个未变合同分别提供当前最小覆盖，不把旧失败改为PASS。完整P3、ancestry/P6、性能及生产发布门禁继续独立；未提交/推送/发布。采样T1/top_p.95/top_k20/presence0/medium、Pi32768和诊断O4096均未改。p95=null，真实ITL=null，optimization_qualification=false。
