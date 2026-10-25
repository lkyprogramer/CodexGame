# P1 追加补证与最终验收结论

**P1 本次授权的最小功能范围验收通过（P1_MINIMAL_FUNCTIONAL_PASS），原生产服务已恢复并验活。** 私有代理和完整长前缀 L2 两个缺口已关闭；复用上一轮 4 个 native PASS，不重跑。完整 P1-GATE、性能/生产发布资格仍独立记录，不以本次功能通过代替。

## 修复内容与实际结果

本轮只修实机驱动，NInfer 源码树仍为 `06dc421059087f9c614e0245702c05a8dead49e3`，既有 CLI/服务构建直接复用，无需重建或新增引擎改动。分支仍 `codex/p1-frontend-cache-20261022`，HEAD=O、MERGE_HEAD=U10，未提交、推送、打 tag 或部署候选。

| 缺口 | 修复与实机证明 |
|---|---|
| 代理端口误投 | 私有代理自己绑定 loopback 端口0并持有 socket，原子记录 PID/start_ticks/inode/window；请求前逐次核对监听归属，响应另带本次窗口标识。实际私有端口44407、上游47841，未使用已有 nginx 的28343 |
| 模型尚未加载就认定 ready | 后端以本次容器启动后的 model-loaded/listening 日志及精确 PID/socket 认定就绪；检查日志和进程不产生 HTTP 请求 |
| 代理语义 | 原生产 shim 原字节复制，SHA不变；测试包装仅记录转发字节并增加身份响应头，调用原 rewrite 函数。JSON与SSE均200，模型别名、medium、实际上游请求、usage与唯一SSE终态核查通过 |
| erase 破坏 L2 夹具 | 改为两个独立 system/session 的 A→B→A，B通过C1正常 admission 驱逐A；不调用 erase/slots，不缩上下文或缓存容量 |
| 等待重复 idle 日志 | 评审发现服务会抑制无变化日志，已在运行前修正。单个 idle/publication 样本只作旁证，缺样本不冒充 drain；最终实际 L2 恢复才是验收权威 |

[冻结脚本](../output/ninfer-v4-p1-followup-20261022/script-freeze.json) · [追加执行计划](../output/ninfer-v4-p1-followup-20261022/window-plan.json) · [请求与结果原件](../output/ninfer-v4-p1-followup-20261022/evidence/http/) · [机器汇总](../output/ninfer-v4-p1-followup-20261022/final-summary.json)。

## 完整长前缀 L2

| 请求 | Prompt | 命中 / 恢复 token | 实际路径 |
|---|---:|---:|---|
| 新 A | 6185 | 0 / 0 | lane0，full_reset，全量 prefill |
| 独立 B | 6184 | 0 / 0 | 同一 lane0，full_reset，正常替换 A |
| 原样返回 A | 6185 | **6183 / 6183** | **source=l2、routed_session、restore_turn_checkpoint** |

两次 A 的请求 body SHA 完全相同。返回 A 实际恢复 **422,844,790 bytes**，只计算2个 prefill token；restore_failure=none，destructive_rollback=false。满足运行前冻结的 P≥6000、命中与恢复≥P−4门槛，已排除上一轮只恢复11个公共前缀 token的假覆盖。[A原记录](../output/ninfer-v4-p1-followup-20261022/evidence/L2-A-cold-done.json) · [B替换记录](../output/ninfer-v4-p1-followup-20261022/evidence/L2-B-involuntary-eviction-done.json) · [A的L2恢复](../output/ninfer-v4-p1-followup-20261022/evidence/L2-A-restored-done.json)。

本轮是现有缓存路径的功能验证，没有实施新性能优化；这些单次观测不构成配对速度收益或正式p95。

## 预算、验证与原始失败

追加 **14/14计账单位＝11次客户端HTTP＋3次代理上游HTTP**：idle1、A/B/A3、两次代理含上游4、候选末态1、恢复5。5个候选模型请求均有唯一 start/done，无 request_error、无未结束请求；所有客户端请求HTTP200，没有重试。新增 native=0。

独占/恢复窗口为 **2026-10-22 14:14:07—14:17:57（Asia/Shanghai），3分50秒**，包含候选和原服务的模型加载。原32计账单位与4 native/12 submit/11 admission证据原样保留；两轮合计46计账单位，不把旧失败从分母扣除。[本轮账本](../output/ninfer-v4-p1-followup-20261022/evidence/state.json) · [上一轮失败与native结果](ninfer-v4-p1-hardware-20261022.md)。

Python语法检查通过，原服务监听归属的零HTTP预检通过，旧硬件交付258项SHA全部验证通过。实际HTTP、转发审计、请求原字节/SHA、sampler、长前缀L2、恢复状态等 **76项离线断言全部PASS**。没有重新运行旧CPU/G1/native、Baseline、Pi、编程题或grader。本轮5个新合成模型请求采用冻结夹具的16输出token；它们不是Pi运行，未回写生产default-max32768。

独立Standards评审未发现新恢复/预算/端口阻断；Spec评审指出日志静默夹具问题，修正后复核无finding，最终原件离线复核确认本轮结论。评审者未SSH或执行请求。[Standards](../output/ninfer-v4-p1-followup-20261022/review-standards.md) · [Spec修复复核](../output/ninfer-v4-p1-followup-20261022/review-spec.md) · [原件复核](../output/ninfer-v4-p1-followup-20261022/review-evidence.md)。

## 原生产恢复

验证结束即停止候选并启动原容器。容器 ID仍 `86cb6d9ae7348fb928570e60290d2dc8ac933170a3c7bca32016ff347e2e1ddd`，镜像仍 `sha256:e753e2283db78bbe2fe1fc92b9d45300a27fd5765b367c434c9023cbf2cb1cb3`。CLI/serve SHA、原参数与挂载、缓存目录 inode/device、启动及代理脚本 SHA 均一致。原 proxy/systemd MainPID1950保持，恢复后的GPU服务PID40985；候选已停止，controller/guardian已退出。

原 `/health`、原代理 `/v1/models`、新推理与最终 metrics 均200；processing/deferred=0、systemd active/running。原缓存目录未替换或清空；重启后的内存缓存重新预热。[恢复回执](../output/ninfer-v4-p1-followup-20261022/evidence/restoration.json) · [最终实时身份](../output/ninfer-v4-p1-followup-20261022/final-live-validation.json)。

## 验收边界

**此前声明的P1最小功能范围现已闭合，两个实机缺口不再阻挡该范围验收。** 本轮没有发现需要新增模型请求才能处理的范围内问题。

T=1、top_p=.95、top_k=20、presence=0及medium保持；生产默认输出32768和Pi预算不改。18处G1严格差分、97fc7be6自然循环、LoRA/vision与正式性能/发布要求继续保留原状态；不修改历史评分或声称质量改善。`full_P1_GATE=UNQUALIFIED`、`p95=null`、`optimization_qualification=false`。P1候选没有留在现网，也未自行进入下一阶段。

原Baseline/BO/G1、上一轮两次401、发连接前失败及构建错误均未覆盖。推进入口前，本轮另保存383份活动文档的原字节快照 v4-before-followup.tar.gz。
