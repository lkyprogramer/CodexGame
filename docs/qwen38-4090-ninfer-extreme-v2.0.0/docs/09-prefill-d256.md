# 冷 Prefill：d256 causal paged Attention 改造

## 1. 优化目标与来源

附件中NInfer184K cold94s，而vLLM对照66s，说明有实验价值，但不是Sage接口能原样替换。Sage官方已读API>128拒绝；Ada donor主要DiT。把它作为量化/warp/softmax思想和部分primitive来源，不把diffusion的rtol阈值当LLM容忍度。[S11–S14]

## 2. 从现有kernel做低风险基线

首先保留QK/PV数值路径，只调整prefetch、barrier时序、寄存器生命周期、tile调度和合法融合。确认profile热点仍是attention而不是head、host排队、重复cache reset。Qhead packing过去已被本机否决，不未经新证据重复同样设置。

## 3. 新A8/FP8-PV路径独立numeric profile

接口：`Q[chunk,24,256]`，历史K/V为已有分页packedcodec；causal合法条件为`key_abs <= prefix_abs + q_local`。对chunk间reuse，历史不能只取当前chunk K/V；也不能对所有旧keys作未来可见的中心化统计改变语义而不记录。前后key distribution不同（新BF16、旧量化）时，需明确到底使用落盘后decoded KV还是原始currentK；首版使用统一可重建的cache view，方便oracle。

QK的256维dot一次求完后再softmax。**两段128维各softmax后合并是错的。** FP8 P/V路线要有scale、超界、NaN、denormal和累加范围设计；默认FP32 running max/sum，FP16内部accumulation另列数值变更。

## 4. old-KV unpack策略

不能为了方便先把整个200K×全部层KV解压成FP16（显存超预算）。可选：每CTA tile内unpack；或者单层有限ring staging，生产结束及时复用。每个方案都把scratch峰值计入512MiB余量门。cache数学不变的tile布局优化先做，量化换路径后做。

## 5. 关键反例

- prefix=0、1、63、64、65、65535、183999、258000；chunk=1、127、128、1024；页面乱序与尾页半满。
- 24Q/4KV映射；mask导致整行空值；Q/K大异常值；softmax极端集中/平坦；64位stride超过2^31。
- prefill分成不同chunk与warm-resume；eager/graph；追加工具结果；中段rewind；logits接近平局。
- 用同一codec解码后的FP64/FP32 attention oracle区分“新kernel算错”和“原codec量化误差”。不要把所有差异都塞进放大的rtol。

## 6. Amdahl门

若attention占45%、kernel快2倍，端到端上限约`1/(.55+.45/2)=1.29`，不是2倍。采用真实阶段占比重算；dram/FP8算力天花板也要同频率、同dense/sparse口径。先争取真实TTFT收益95%下界≥5%；达不到就停止这条补丁，保留profile报告。45–55s只是研究目标，不是交付承诺。

改变target算术的上线质量要求高于suffix-only：原Java smoke、30语义holdout、深长文细节、既有Hard集和代表性真实repo回归；必要时更大公开benchmark。质量未建立即不能当默认，即使吞吐翻倍。
