
图5：LLAMA2模型的训练损失。我们比较了LLAMA2模型系列的训练损失。我们观察到，在进行了2T个标记的预训练之后，这些模型仍未显示出任何饱和迹象。
2.2 Training Details
我们采用了LLAMA1的大部分预训练设置和模型架构。我们使用了标准的Transformer架构(Vaswani et al., 2017)，使用了RMSNorm进行预归一化(Zhang and Sennrich, 2019)，使用了SwiGLU激活函数(Shazeer, 2020)和旋转位置嵌入（RoPE，Su et al. 2022）。与LLAMA1相比，主要的架构差异包括增加的上下文长度和分组查询注意力（GQA）。我们在附录第A.2.1节详细介绍了这些差异，并通过消融实验来证明它们的重要性。
超参数。我们使用AdamW优化器进行训练(Loshchilov and Hutter, 2017)，其中 \(\beta_{1} = 0.9, \beta_{2} = 0.95\)，\(\mathrm{eps} = 10^{-5}\)。我们使用余弦学习率调度，预热步数为2000步，并将最终学习率衰减到峰值学习率的 \(10\%\)。我们使用权重衰减0.1和梯度裁剪1.0。图5（a）显示了使用这些超参数训练LLAMA2的训练损失。
分词器。我们使用与LLAMA1相同的分词器；它采用了一种字节对编码（BPE）算法(Sennrich et al., 2016)，使用了来自SentencePiece (Kudo and Richardson, 2018)的实现。与LLAMA1一样，我们将所有数字分割成单独的数字，并使用字节来分解未知的UTF-8字符。总词汇量为32k个标记。
2.2.1 Training Hardware & Carbon Footprint
训练硬件。我们在Meta的研究超级集群（RSC）（Lee and Sengupta, 2022）和内部生产集群上预训练了我们的模型。这两个集群都使用NVIDIA A100。这两个集群之间有两个关键差异，首先是可用的互连类型：RSC使用NVIDIA Quantum InfiniBand，而我们的生产集群则配备了基于商品以太网交换机的RoCE（以太网收敛RDMA）解决方案。这两种解决方案均可实现200 Gbps互连。第二个差异是每个GPU的功耗上限——RSC使用400W，而我们的生产集群使用350W。凭借这两个集群的设置，我们能够比较这两种不同互连类型在大规模训练中的适用性。RoCE（一种更具费用效益的商业互连网络）可达到与昂贵的Infiniband几
7