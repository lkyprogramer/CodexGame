# 文档包校验记录

发布日期：2026-09-11。

- 结构检查：PASS；9个Phase，53个Task（44个开发/专项Task + 9个阶段统一Gate）。
- 任务DAG：无重复ID、无缺失依赖、无环；P7A→P7B显式子Gate。
- JSON解析、阶段文档Task覆盖、本地Markdown链接、代码围栏、安全默认值：PASS。
- Python辅助工具：24项unittest全部通过；原始记录见`verification/tool-tests.txt`。
- 估算器：CED16/rank256为36,613,504个参数，BF16参数约69.835MiB；100000标签token约26.751GiB。只为预算估算，不是GPU峰值实测。
- 初始状态：全部引擎实施Task为NOT_RUN；生产暂停、生产启用、功率修改均默认未授权。

本次没有连接用户4090、编译NInfer、运行CUDA、生成训练数据、训练Predictor或测量Agent质量/速度。不能用本记录代替任一P0—P8的真实Gate。

SHA256SUMS覆盖包内所有交付文件（不包含自身）。解压后可运行`python3 tools/validate_package.py`检查内容校验和；ZIP创建后另进行了CRC及解压字节完整性检查。
