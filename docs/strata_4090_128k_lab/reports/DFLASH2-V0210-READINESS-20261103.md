# Strata v0.2.10 DFlash2 发布版评估

**支持用 Qwen3.8-Flash-Next 在 29 隔离验证。** v0.2.10 的 App 和 Terminal 在支持的引擎上，对单并发 Qwen3.8 的 `auto` 优先选 DFlash2。RTX 4090 的 `sm_89` 在支持列表内。该版本已开放单卡 HTTP 服务路径。普通并发槽会回退 MTP。显式选择也必须核对实际加载结果。 [v0.2.10 发布说明](https://github.com/Niko1221/Strata/releases/tag/v0.2.10#what-is-new) · [控制层分派](https://github.com/Niko1221/Strata/blob/v0.2.10/strata_control/drafting.py#L409-L412)

## 29 的实际状态

- **已验证。** 用 29 上已有的 Control 0.1.56 执行 `strata launch --plan --family qwen --model iq3_xxs --context 128k --parallel 1 --gpu 0 --vision off --drafting dflash2 --tune skip --access local --port 18089 --data-dir /data/strata-data`。计划识别 RTX 4090、现有 76 GB IQ3_XXS 模型和 DFlash2。计划退出 0，未下载、未启动推理。
- **仍需准备。** 已验证的 DSv41 引擎仅服务 DeepSeek。Qwen 需要单独的 Linux x86_64 CUDA 13 引擎 0.1.56。29 的签名 feed 指向 `strata-engine-0.1.56-linux-x86_64-cuda-cuda13.tar.gz`，构建 `06698c674673+cuda13.0`，667,699,126 字节，SHA256 为 `df6a6dfd806289caa42becd2acc14081815bedac9ec8f5efa3821a7d10582ee5`。计划另报约 1.2 GB 草稿资产。现有 DF01 Q8 pack 保留为历史身份。发布版默认使用 Q4_0 草稿，可转换为 Q4_0 selector，须固定实际加载的 pack 和词表。 [发布包清单](https://github.com/Niko1221/Strata/releases/tag/v0.2.10#downloads) · [草稿资产常量](https://github.com/Niko1221/Strata/blob/v0.2.10/strata_control/drafting.py#L202-L214)
- **已验证。** 按模型名分派时，现有生产别名 `openclaw/Qwen3.8-next` 不匹配。标准名 `qwen3.8-flash-next` 匹配，Terminal 也可以用 `--family qwen` 识别。保留生产别名。隔离配置使用标准身份，避免复制旧别名后静默回退。 [模型匹配规则](https://github.com/Niko1221/Strata/blob/v0.2.10/strata_control/drafting.py#L247-L258)

## 旧 D1U 的证据边界

新版本的单卡服务资格改变了[旧源码核查](DFLASH2-SOURCE-REVIEW-20261031.md)中的 CLI 限制。D1U 的 n2300 仍是原 Q8 路径的失败记录。对比原冻结 CUDA 源、发布标签和官方 Qwen CUDA 13 构建源码，`rms_quant_kernel` 和 `df2_rms_quant` 两段函数文本的 SHA256 分别相同。新版本包含其他草稿和服务代码变更，现有证据未表明原 context Q/D 差异已修复。原 D1 FAIL、D2 未开始和历史质量失败保持。 [D1U 实测](DF01-D1U-N2300-CAUSAL-STOP-20261103.md) · [官方引擎构建源码](https://github.com/Niko1221/Strata/blob/06698c674673/src/kernels/cuda/dflash2.cu#L583)

## 如另行执行，先验证服务资格

1. 隔离安装 Qwen 0.1.56。核对签名 feed、组件 SHA256、CUDA `sm_89` 能力、target pack 和草稿词表。共用现有模型文件时按只读资产处理，写入隔离配置及日志。
2. 显式选 `dflash2`、单卡、单并发、128K。检查实际参数和日志，确认使用 DFlash2，未加载 MTP 层，并采集非零草稿轮数。对比同引擎关闭草稿的固定贪心输出及 EOS。验证短追加、会话恢复和取消。任一硬门失败即保留首个失败并停止。
3. 通过后才做同引擎 MTP spec4 对照。保持模型、KV、缓存预算、采样和请求一致。测真实冷读、短追加、生成速度、工具和任务通过率。沿用原 4% 采用门及正确性和资源门。若拟升级生产，另对当前 v0.2.3 实际基线验收，避免把引擎升级差量归给草稿。

本轮只执行源码核查和 `--plan`。Qwen 0.1.56、发布版草稿、GPU 生成及服务正确性在 29 上均未验证。生产保持停机。
