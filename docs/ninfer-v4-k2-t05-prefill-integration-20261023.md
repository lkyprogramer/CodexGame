# K2-T05：T1024真实Prefill接入，CPU交付完成

**仅T1024已接入隔离候选的真实27B Prefill。BO构建、新增16项CPU合同与集成评审完成，0 GPU/模型/HTTP请求。完整Prefill及Chat收益尚未验证。** T512不补测；其他shape和Verify/Decision/分段路径保留raw。原GPU服务保持停止。

## 实际代码与身份

远端通过`jssh 29`操作，独立目录`/home/hhtele/ninfer-v4-k2-t05-prefill-integration-20261023`，分支`codex/k2-t05-prefill-integration-20261023`。基点`3ea537c00c759ef2a4577b525ae691f694ae102e`，候选树`9818eafa5d2660c2ea9682cc7653e6603f21ebb5`；未创建commit、push或部署。

- family的`TextContext::gdn_mix`经`gdn_convolve_qkv`调用公开Ops边界。只有`Phase::Prefill`、无segments、T=1024、C10240/Q2048/K2048/V6144才进入直接输出路径。
- 新的`causal_conv1d_silu_split_qkv_1024`验证固定shape、BF16、连续布局、4字节对齐与别名合同。state输入输出可精确同址；其余存储必须分离。数据不合格在launch前拒绝。
- 复用上轮已测的split kernel、原FP32表达式/BF16舍入和独立state kernel，仅将bench私有launcher改为共有launcher名称。完整kernel文件与原FP64参考/准则逐字节未变；原raw Op与Verify snapshot代码不变。
- Q/K/V直接写现有连续workspace根。投影、GDN递推、归一化、后投影、stream顺序、state slot和缓存格式不改。原`qkv_c`仍按旧recipe分配，不能声称节省allocator或峰值显存。
- product内部调用只接入T1024；旧bench的其他shape实现保留作历史复现资料，未执行。35B不同几何继续raw，本轮未构建35B包。

源码：[family路由](../output/ninfer-v4-k2-t05-prefill-integration-20261023/source/src/targets/qwen3_8/impl/runtime/gdn_convolution.h)、[真实调用点](../output/ninfer-v4-k2-t05-prefill-integration-20261023/source/src/targets/qwen3_8/impl/runtime/text_context_impl.h:999)、[Ops合同与验证](../output/ninfer-v4-k2-t05-prefill-integration-20261023/source/src/ops/wrapper/causal_conv1d_silu.cpp:199)、[可应用补丁](../output/ninfer-v4-k2-t05-prefill-integration-20261023/remote/evidence/K2-T05-T1024-prefill.patch)。

## 构建、CPU验证与评审

复用原BO镜像`sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`、独立复制的构建缓存与依赖；保持CUDA13.2/SM89/Release/27B-only/最多4 worker。`runc`、无网络、无GPU设备，显式断言`/dev/nvidia0`及`/dev/nvidiactl`不存在。未下载依赖。原1263文件复制后逐字节校验，旧目录和冻结GPU bundle均未变。

实际构建命令：

```sh
cmake --build /build -j 4 --target ninfer_k2_prefill_integration_cpu_test ninfer_k2_prefill_split_probe ninfer-serve
/build/tests/ninfer_k2_prefill_integration_cpu_test
```

BO产品server和probe构建PASS；旧probe仅编译未运行。新增CPU目标直接编译实际family helper、公开wrapper及Tensor/dtype实现，以记录型launcher和extract边界验证host控制流。它没有模拟GPU计算，不证明新二进制的设备数值或Graph正确性。

16项包括：T1024实际split选择、T1023/T1025/T1/Decision/Verify/segmented/另一注册几何的原路由；完整Q/K/V地址和stream传递；精确/分离state；非法shape/dtype/stride/null/alignment以及QKV/部分state重叠在launch前拒绝。没有执行T512测试。

首轮`build-r1`缺family export include目录、第二轮`build-r2`缺`dtype_size`实现链接，均完整保留；补齐新增CPU目标的准确依赖后`build-r3`PASS。初次16项CPU PASS后，评审补上同宽Q/K地址顺序和V地址的精确断言；仅变更的CPU目标`build-r4`重建，`cpu-r2`16/16 PASS。共16个唯一新场景、两次执行；未重跑旧Baseline、旧16项合同或已通过GPU任务。

本轮由主代理做集成评审，未声称独立评审。已核对public Ops边界、shape/phase/segment限制、workspace不重叠、state事务、stream与下游消费；依赖闭合和地址断言问题已修复，未发现剩余阻断。已有continuation文件`snprintf`编译warning保留，不在本补丁内扩张修复。

证据：[最终CPU原始输出](../output/ninfer-v4-k2-t05-prefill-integration-20261023/remote/evidence/cpu-r2.stdout)、[构建回执](../output/ninfer-v4-k2-t05-prefill-integration-20261023/remote/evidence/build-r3.json)、[评审记录](../output/ninfer-v4-k2-t05-prefill-integration-20261023/remote/evidence/integration-review.json)、[源码身份](../output/ninfer-v4-k2-t05-prefill-integration-20261023/remote/evidence/source-identity.json)。

## 预期收益的边界

复用[上次段级结果](ninfer-v4-k2-t05-hardware-20261023.md)：T1024 raw/split中位event耗时64.084/40.704μs、同批改善中位数36.4834%。两类中位数算法不同，不能混作同一个改善估计。

仅按两列event中位差折算，`(64.084−40.704) × 48 / 1000 ≈ 1.12ms/完整1024 chunk`；8个完整chunk约8.98ms。这是静态外推，不是整模型实测。真实收益还取决于投影/attention/GDN占比、cache、host检查、功耗/频率及完整调度；可能低于噪声。没有可信的完整Prefill/TTFT收益百分比承诺。尾块和Decode不使用新路径，不能据此承诺decode tokens/s提升。

## 下一步最小实机范围：仅提案，尚未冻结驱动

| 范围 | 最小预算 | 要证明什么 |
|---|---:|---|
| 原基点→新候选的完整Prefill | 1个固定8193 token场景；各1 warmup＋5 measured，共12次native prefill | 8个T1024块及T1尾块；实际route-hit；完整状态/logits一致；整段prefill计时 |
| Chat Completions | 各2个长前缀新请求，共4个 | 普通文本stream与具名tool_choice增量JSON；SSE终态、解析和TTFT |
| HTTP warmup与readiness | 各variant 1次warmup＋1次readiness | 2次额外模型提交、2次无模型wire |
| 合计 | **18个模型工作单位：12 native＋4 Chat＋2 warmup；8个wire** | 不追加旧Op/T512场景，不运行Pi或grader |

native首个measured迭代在计时区间外导出所有GDN FP32 state、BF16 conv、逻辑attention KV和logits进行比较；不对含request ID/时间戳的容器外壳做伪逐bit断言。非分段native固定token输入不额外插BOS，预期每迭代候选split命中`8×48=384`次、raw为0；实际值必须由驱动记录后核对，不能以源码predicate替代。

完整Prefill采样前停止，无需另设greedy替代生产sampling。Chat保留生产sampling/medium；新测试体与输出预算须在未来驱动冻结时明确，不修改Pi原32768预算。隔离验证使用原model/codec、context262144、chunk1024，continuation cache off、prefix reuse禁用，cache目录与现网隔离。容量不够即停并记缺口，不降context。

最低信号提案：完整状态及数值合同全通过，五个同序号测量对的prefill中位改善≥1%、至少4/5更快、单对无>3%回退；原基点→候选是顺序两组，**不是AB/BA交错**，须同时保留clock/power、host/event、加载与温度记录，结果仍受顺序偏差限制。4个Chat测量只做功能及观测smoke，不足以给p95、总体TTFT或分布资格；没有信号就保留raw发布默认，不能自动追加补测。

当前还需补齐真实驱动、route witness、全状态比较、controller和空账本，预计**3–5工程小时**。实际model Graph capture/replay、算法kernel及辅助传输次数/字节尚未枚举，明确为null＋原因；必须先冻结，不能凭18个工作单位隐含无限GPU迭代。详见[预算提案JSON](../output/ninfer-v4-k2-t05-prefill-integration-20261023/future-validation-proposal.json)。

驱动准备后，实机预计**8–15分钟**，建议硬限20分钟、第17分钟只清理候选；分析约0.5–1小时。估算含原context容量检查、加载、warmup、证据导出和清理，不是服务切换授权。原GPU服务全程保持停止，不自动恢复。候选资格与生产发布仍分别验收；不以本轮CPU交付授予K4或生产资格。

## 冻结与保留

源码冻结回执SHA：`99b44b0a2d3bc0eec40c342a29827bdaba16f0c1373b69523fcb707a51ff2f61`；归档SHA：`aa93ab02f9b3134bc903ad26d313c0d40cac681bc198705eee57823d468692ad`。[冻结回执](../output/ninfer-v4-k2-t05-prefill-integration-20261023/remote/evidence/freeze-receipt.json)、[归档回执](../output/ninfer-v4-k2-t05-prefill-integration-20261023/archive-receipt.json)、[完整交付摘要](../output/ninfer-v4-k2-t05-prefill-integration-20261023/integration-core.json)。server/probe/CPU binary的SHA均绑定源码身份，二进制保留远端build目录。归档包含源码、补丁、原始构建/CPU日志及回执；本地持久源码逐字节比对归档通过。

前后核验原容器、镜像、argv和缓存身份仍符合冻结snapshot，原服务exited/PID0、GPU idle；不恢复原服务。18处G1差异、C1附件缺口、全部历史失败及本次两次构建失败均保留；C0/K2-T01/K1-T01追加预算0。`p95=null`，`optimization_qualification=false`。
