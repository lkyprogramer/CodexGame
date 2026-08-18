![](images/0.jpg)

图 4: LLAMA 2-CHAT 的训练：该过程始于使用公开可获得的在线资源对 LLAMA 2 进行预训练。在此之后，我们通过监督微调的方式创建模型的初始版本。随后，通过人类反馈的增强学习方法，具体来说是通过拒绝抽样和近端策略优化（PPO），对模型进行迭代性改进。在增强学习阶段，迭代奖励模型数据的积累以及模型改进是至关重要的，以确保奖励模型保持在分布范围内。
<table><tr><td></td><td>Training Data</td><td>Params</td><td>Context Length</td><td>GQA</td><td>Tokens</td><td>LR</td></tr><tr><td rowspan="4">LLAMA 1</td><td rowspan="4">See Touvron et al. (2023)</td><td>7B</td><td>2k</td><td>X</td><td>1.0T</td><td>\( 3.0 \times 10^{-4} \)</td></tr><tr><td>13B</td><td>2k</td><td>X</td><td>1.0T</td><td>\( 3.0 \times 10^{-4} \)</td></tr><tr><td>33B</td><td>2k</td><td>X</td><td>1.4T</td><td>\( 1.5 \times 10^{-4} \)</td></tr><tr><td>65B</td><td>2k</td><td>X</td><td>1.4T</td><td>\( 1.5 \times 10^{-4} \)</td></tr><tr><td rowspan="4">LLAMA 2</td><td rowspan="4">A new mix of publicly available online data</td><td>7B</td><td>4k</td><td>X</td><td>2.0T</td><td>\( 3.0 \times 10^{-4} \)</td></tr><tr><td>13B</td><td>4k</td><td>X</td><td>2.0T</td><td>\( 3.0 \times 10^{-4} \)</td></tr><tr><td>34B</td><td>4k</td><td>√</td><td>2.0T</td><td>\( 1.5 \times 10^{-4} \)</td></tr><tr><td>70B</td><td>4k</td><td>√</td><td>2.0T</td><td>\( 1.5 \times 10^{-4} \)</td></tr></table>
表 1: LLAMA 2 模型系列。计数仅指预训练数据。所有模型都使用全局批处理大小为4M个标记进行训练。较大的模型 — 34B和70B — 使用分组查询注意力（GQA）以提高推理的可扩展性。
数据混合方法，训练了比原来多 \(40\%\) 的总令牌数目，将上下文长度加倍，并使用了分组查询注意力（GQA）来提高更大规模模型的推理可扩展性。表1比较了新的LLAMA 2模型和LLAMA 1模型的特点。
2.1 Pretraining Data
我们的训练语料库包含了来自公开可获取的数据源的新的数据混合，其中不包括来自Meta的产品或服务的数据。我们尽力删除了已知包含大量私人信息的特定网站的数据。我们训练了2万亿个标记的数据，因为这提供了良好的性能和成本的权衡，在努力提高知识和减弱幻觉的过程中，对最可靠的来源进行了超采样。
我们进行了各种预训练数据调查，以便用户更好地了解我们模型的潜力和限制；结果可以在第4.1节中找到。
6