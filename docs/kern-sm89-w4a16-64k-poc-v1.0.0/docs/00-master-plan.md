# 总方案：用可审计的 64K PoC 建立 4090 性能实验底座

## 目标与非目标

用户希望把 Qwen3.8-27B 在 4090 上的质量、速度、长 Agent 工作体验推向更好的组合。当前要交付的工程里程碑是 **Kern-SM89-W4A16、真实64K输入**，不是证明已达到理论最优，也不是一次实现完整200K生产替代。

原方案中“只换 sm_89”“greedy 必须全程同文本”“默认 FP16 GDN”需要精确化：Kern 的当前发布包是 GB300 kernel + BF16权重；需要新的量化 provider、ABI 和布局合同。不同合理浮点路径可能在近似平局处产生不同 token，必须定位数值差异而不是用文本差异一票判断。P0 保留源配置 FP32 state，减少同时变化的变量。[S01][S02][S05]

## 推荐路线

`固定 W4A16 checkpoint → 在4090运行同权重 reference → 导出经过验证的 packed buffers/ABI → 新 Kern provider → SM89 kernels → plain eager → plain graph → 64K + append cache + Pi Java`。

使用现有 kernel-sanders vLLM 环境作为**可选依赖/算子来源**，但不照搬它的默认 DFlash2、INT8 embedding、FP16 state、KVarN、八槽配置。每项都必须显式关闭或还原到 P0 合同；做不到时该环境不是合格 oracle。[S04]

另一条路线是重写完整 NInfer codec/Program 到 Kern；它会增加转换与状态边界工作，当前不推荐。直接 offload BF16 27B 到 CPU 只适合辅助调试，不作为“4090高性能”交付。

## 固定 P0 合同

| 项目 | 值 |
|---|---|
| 模型 | Qwen3.8-27B 完整语言 decoder，64层，不删层/头 |
| 权重 | dbirks W4A16 AutoRound（本机实际 revision/hash 冻结） |
| activation / GDN | BF16 / FP32 |
| Attention KV | BF16，16层、4 KV头、head_dim256 |
| 输入 / 输出 | 65,536 / 至少2,048 target token |
| 最大窗口/池计划 | 73,728 tokens；以页对齐后的真实容量验收 |
| 并发 / 草稿 | 1 / none |
| 采样 | temperature=0 的 greedy；其他非默认采样请求明确拒绝 |
| 首选prefill chunk | 512；256/1024 为独立受控候选 |
| 生产 | NInfer 保持默认，PoC 不自动切流 |

首阶段文本模式不装载 vision/MTP 未使用权重，**不是改变语言模型权重**。原始文件保持只读。embedding/lm_head 保持源精度；需要再量化时升级为单独 profile，oracle 必须同步。

## 两个不同的成功判定

**工程可用 POC_GO：** 同权重数值门、实际64K、最低速度、缓存、Java、生命周期和资源安全都通过。

**值得替代 NInfer：** 在同机产品任务、相同 thinking/采样、相同工作量下有稳定改进，且没有质量或恢复退化。两边权重/KV精度不同，不能把这种产品比较称为严格引擎A/B。3个Java题只是一组 smoke gate，不是统计上的通用能力等价证明。

本包提供工程可用 gate；替代结论必须保守。继续优化的实际价值可能在冷 prefill、少量新增 token 的 extend、缓存恢复和 host 开销，而非单一峰值 tok/s。
