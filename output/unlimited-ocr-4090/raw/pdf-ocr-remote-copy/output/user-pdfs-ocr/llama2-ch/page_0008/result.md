<table><tr><td></td><td>Time (GPU hours)</td><td>Power Consumption (W)</td><td>Carbon Emitted (tCO2eq)</td></tr><tr><td rowspan="4">LLAMA 2</td><td>7B</td><td>184320</td><td>400</td></tr><tr><td>13B</td><td>368640</td><td>400</td></tr><tr><td>34B</td><td>1038336</td><td>350</td></tr><tr><td>70B</td><td>1720320</td><td>400</td></tr><tr><td colspan="2">Total</td><td>3311616</td><td></td></tr></table>
表 2: 预训练期间的二氧化碳排放。时间：训练每个模型所需的总 GPU 时间。功耗：调整了用于 GPU 设备的峰值功率容量，考虑了功耗效率。100% 的排放量通过 Meta 的可持续性计划直接抵消，而且由于我们公开发布这些模型，预训练成本不需要由其他人支付。
乎相当的扩展性，最多可支持2000个GPU，这使得预训练的普及化程度更高。在RoCE和GPU功耗限制在350W的A100上，我们优化的代码库达到了相当于使用IB互连和400W GPU功耗的RSC性能的90%。
预训练的碳足迹。根据之前的研究（Bender等，2021；Patterson，2021；Wu，2022；Dodge，2022），并利用GPU设备的功耗估计和碳效率，我们旨在计算制备LLAMA2模型的碳排放量。GPU的实际功耗取决于其利用率，很可能与我们用作GPU功耗估计的热设计功耗（TDP）有所不同。需要注意的是，我们的计算未考虑其他功耗需求，例如互连或非GPU服务器功耗，以及数据中心冷却系统的功耗。此外，与人工智能硬件（如GPU）的生产相关的碳排放可能会增加总碳足迹，正如Gupta等（2022）所建议的那样。
表 ?? 总结了制备 LLAMA 2 模型时的碳排放。我们在 A100-80GB（TDP 为 400W 或 350W）类型的硬件上进行了累计 3.3M GPU 小时的计算。我们估计训练的总排放量为 539 吨 CO \( _{2} \) eq，其中 100% 被 Meta 公司的可持续性计划直接抵消。** 我们的开放发布策略还意味着其他公司不需要承担这些预训练成本，从而节省了更多全球资源。
2.3 LLAMA 2 Pretrained Model Evaluation
在本节中，我们报告了\anise和\cinnamon基本模型的结果，MosaicML预训练Transformer (MPT)模型 \( ^{†} \) ，以及Falcon (Almazrouei et al., 2023)模型在标准学术基准上的结果。对于所有的评估，我们使用我们的内部评估库。我们在内部重新复现了MPT和Falcon模型的结果。对于这些模型，我们总是选择我们的评估框架和任何公开报告的结果之间的最佳得分。
在表格3中，我们总结了一套流行基准测试的整体性能。注意，安全性基准测试在第4.1节中共享。这些基准测试被分为以下类别。所有单独基准测试的结果可在附录A.2.2中查看。
- 代码。我们在HumanEval (Chen et al., 2021)和MBPP (Austin et al., 2021)上报告了我们模型的平均pass@1得分。
- 常识推理。我们报告了PIQA (Bisk et al., 2020), SIQA (Sap et al., 2019), HellaSwag (Zellers et al., 2019a), WinoGrande (Sakaguchi et al., 2021), ARC easy 和 challenge (Clark et al., 2018), OpenBookQA (Mihaylov et al., 2018), 以及 CommonsenseQA的平均结果 (Talmor et al., 2018)。我们报告了CommonSenseQA的7-shot结果，以及其他所有基准测试的0-shot结果。
- 全球知识。我们在NaturalQuestions (Kwiatkowski et al., 2019)和TriviaQA (Joshi et al., 2017)上评估了5次迭代的表现，并报告了平均结果。
"https://sustainability.fb.com/2021-sustainability-report/"
\( ^{11} \) https://www.mosaicml.com/blog/mpt-7b
8