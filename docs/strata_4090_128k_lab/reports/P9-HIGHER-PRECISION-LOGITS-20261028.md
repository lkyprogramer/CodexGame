# 同发布 revision 的较高精度权重 logits 对照（2026-10-28）

**29上已有同一发布revision的IQ3_S，两项完整长输入复测已完成，但原错误轨迹没有改变。** 保持P8同token、同参考客户端/库/图及相同NGL18/F16 KV配置，IQ3_S与IQ3_XXS的16/16个长输入argmax一致，仍为 `1751936`＋EOS、`6395887`＋EOS。概率与分差改变，未将正确首位或连字符提升至第一名。

本轮不支持把切换IQ3_S作为这两项失败的修复；仍不能分离基础模型与两量化共用的误差。原六项FAIL、原评分和P6正确性门保持；生产未改、未部署，没有下载模型权重。

## 权重盘点与身份

只读扫描29上可读的 `/data/strata-data/models`、`/data/models`、Hugging Face/ModelScope cache，以及home下qwen/model相关目录。共见90个GGUF/safetensors文件；按Flash-Next/GSQ-RCO/qwen4exp谱系筛出4个分片，即已有IQ3_XXS与IQ3_S两套。没有扫描root私有目录或无关业务数据目录；这是可读模型位置的核查，不声称全盘不存在其他文件。详见 [inventory.json](../workspace/combination/higher-precision-20261028/inventory.json)。

本地 `.hfd/repo_metadata.json` 记录了同一个不可变发布快照：

- repository：`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF`
- revision：`ed59f92082b1e93c0e96d60a8b11aab089b52f09`
- lastModified：`2026-09-29T10:28:23Z`

该快照同时列出两套权重的4个LFS SHA256。本轮重新完整读取4个分片，内容hash与该快照全部匹配，size/mtime在读取前后不变；并非仅按文件名或历史说明认定同源。

| 量化/分片 | 字节数 | 本轮完整SHA256 |
|---|---:|---|
| IQ3_XXS / 1 | 47039860096 | `219ea929900dfa9ef091f3aa473fdba6874b65fcb36526d7d851ac9e95856d15` |
| IQ3_XXS / 2 | 28800138432 | `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113` |
| IQ3_S / 1 | 54817524224 | `4c1eb2ceb4915e1192f4f386021897bde56a97f40a0bb78bb86465e0f7d2aca3` |
| IQ3_S / 2 | 28800138432 | `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113` |

来源快照、精选LFS回执及本轮全内容hash见 [source-repo-metadata.json](../workspace/combination/higher-precision-20261028/source-repo-metadata.json)、[revision-receipt.json](../workspace/combination/higher-precision-20261028/revision-receipt.json)、[full-weight-hashes.json](../workspace/combination/higher-precision-20261028/full-weight-hashes.json)。四文件共159457661184字节＝148.507GiB，本轮全部重新计算SHA256。

两套GGUF的1224张量名称与形状、全部tokenizer元数据、qwen4exp架构/超参数、imatrix元数据相同。已读取的general/qwen4exp/tokenizer/quantize字段仅3处不同：`general.file_type`、`general.repo_url`、`general.tags`。完整header快照与 [IDENTITY_AND_CAPACITY.json](../workspace/combination/higher-precision-20261028/IDENTITY_AND_CAPACITY.json) 可复核。

这里确认的是**同一个公开量化仓库的不可变发布revision与GSQ-RCO谱系**。作者未在这些文件中提供可独立核验的基础训练checkpoint commit；不能把发布revision或另一个MTP revision冒充基础checkpoint SHA。

## “较高精度”的实际范围

IQ3_S总文件大小比IQ3_XXS增加7777664128字节，属于平均精度更高的RCO混合量化。276个张量的量化格式变化，230个载荷增加、46个减少；不是所有张量都提高位宽。包括输出头Q5_K→Q6_K，以及专家、attention、SSM等不同张量的分配变化，详见 [tensor-quantization-changes.json](../workspace/combination/higher-precision-20261028/tensor-quantization-changes.json)。

两套完全相同的shard2仍是IQ4_NL PLE embedding：51,200,245,760元素、28,800,138,240字节张量载荷。因此本轮不能当作BF16基础模型或“已排除全部量化影响”的对照，也不能将变化定位到某个单一格式/算子。

## 保持项与资源资格

复用P8实际参考客户端、库hash及其 `qwen4exp` 模型图。仍为已有 `87b37ea-dirty` 构建，不是本轮干净重建；唯一tracked脏文件是server-schema，身份边界见P8。NGL18（blk.31～47及输出层）、F16 K/V、batch/ubatch512、16线程、131072上下文、lazy PLE、无MTP/MoE cache均保持不变。只将参考加载的GGUF从IQ3_XXS切到IQ3_S，不修改Strata原生实现或配置。

本轮是条件logits诊断，未建立配对性能实验，不根据两次参考读入耗时报告推理速度改善。

按实际434个GPU张量计算，模型载荷从19029491712增至20653286912字节，增加1548.572MiB。用P8实测22030MiB峰值加该差额，预计23578.572MiB，小于实卡24564MiB；短资格先验证实际分配，未通过就不进入长输入。不降低NGL或改变分块，因此可直接复用P8相同布局的参考基线。

输入和条件前缀固定为P8：

| 原用例 | 完整输入token | int32序列SHA256 | 原gold | 每步强制追加的原七位前缀 |
|---|---:|---|---|---|
| 69632-prime | 69616 | `1ed7173ce27f28bdd2f1cc71e882ab6244008a687e1fda68c5c568d4709bab95` | `6763216-000738` | `1751936` |
| 102400-prime | 102392 | `5befd14dd87a5aa37371b9d61ced69e0a0aa3e1f0b745039a29363387b2f65a6` | `2390975-001086` | `6395887` |

每项仍采8行完整248320-way FP32 logits：原prompt的首个输出位置，以及依次强制追加原数字后的7个位置。若IQ3_S在首位或中间位置argmax改变，后续仍使用原前缀，必须按条件分布解释；不能把它串成IQ3_S自由生成的正确答案，更不能据此将原六项改成PASS。

## 实际排序

短复制资格已通过：63token输入，8个argmax均为预期 `6763216-`。数字后连字符高于EOS：IQ3_S为11.1835 logit，IQ3_XXS为9.9542；连字符均排名1。

68K已完成，IQ3_S八个argmax依次仍为 `1751936`、EOS248046，和IQ3_XXS八行相同。该条件轨迹的每个argmax都与强制前缀相符，因此其greedy失败路径自洽。首位与七位后的具体排序如下（概率来自全词表稳定softmax，不改变原评分）：

| 68K位置/量化 | 错误首位1排名/概率 | 正确首位6排名/概率 | 错误−正确logit | EOS排名/概率 | 连字符排名/概率 | EOS−连字符logit |
|---|---|---|---:|---|---|---:|
| 首位/IQ3_XXS | 1 / 22.3022% | 8 / 6.0661% | +1.3020 | — | — | — |
| 首位/IQ3_S | 1 / 43.4659% | 6 / 4.0715% | +2.3680 | — | — | — |
| 七位后/IQ3_XXS | — | — | — | 1 / 99.7590% | 2 / 0.2123% | +6.1524 |
| 七位后/IQ3_S | — | — | — | 1 / 94.8951% | 2 / 5.0723% | +2.9290 |

IQ3_S首位正确数字的名次虽然从8变6，概率却从6.07%降至4.07%，不能描述为整体更接近正确答案。EOS优势缩小，但最高分仍为EOS。

100K同样完成，IQ3_S八个argmax仍为 `6395887`、EOS，与IQ3_XXS相同。正确首数字2的概率提高，但最高分仍为错误的6：

| 100K位置/量化 | 错误首位6排名/概率 | 正确首位2排名/概率 | 错误−正确logit | EOS排名/概率 | 连字符排名/概率 | EOS−连字符logit |
|---|---|---|---:|---|---|---:|
| 首位/IQ3_XXS | 1 / 35.4439% | 6 / 4.9232% | +1.9740 | — | — | — |
| 首位/IQ3_S | 1 / 46.4751% | 2 / 22.5025% | +0.7253 | — | — | — |
| 七位后/IQ3_XXS | — | — | — | 1 / 97.3698% | 2 / 2.5988% | +3.6235 |
| 七位后/IQ3_S | — | — | — | 1 / 93.1150% | 2 / 6.8399% | +2.6111 |

另一EOS248044在七位后也未成为首选：68K的IQ3_XXS/IQ3_S排名47/18，100K为26/47。两项所有位置均未发生argmax分叉，故不涉及分叉后把强制前缀伪装成自由生成的情况；也没有将该逻辑轨迹当作六个原HTTP请求的新评分。

完整top20、十个数字及EOS/连字符的排名/概率、每步强制前缀与分叉标记见 [comparison.json](../workspace/combination/higher-precision-20261028/comparison.json)。两个量化的logits并不相同：68K八行去常量偏移RMSE为0.3692～0.7627，100K为0.3252～0.6995；KL(IQ3_XXS||IQ3_S)最大分别0.3186、0.4814。这里只描述分布差异，不以这些值设新通过门。

## 归因与未覆盖项

**已观察：** 同一参考图下，较高平均位宽的IQ3_S改变了概率分布，但两个prime的错误行及提前EOS完全保留。68K错误首位优势增大；100K正确首位概率上升，仍未超过错误首位；两项EOS优势都缩小但没有反转。

**可支持的推断：** “仅IQ3_XXS这套较低位宽分配造成，而换已有IQ3_S即可解决”的解释未获支持。结合P8独立图复现与P7格式/thinking控制，当前更支持该GSQ-RCO量化模型族在原none长表提示下的条件相关检索/格式失败；未出现必须修改Strata独有实现才能解释的差分证据。

**尚未验证：** 两套都属于低比特RCO混合量化，共同PLE仍为IQ4_NL，其他相同张量/量化算法也可能有共同影响；没有独立基础checkpoint SHA、全16-bit模型或逐层数值parity，不能宣称基础模型固有缺陷，也不能排除所有量化/共用算法问题。276处量化分配同时变化，不把分差归因于某一张量或kernel。

本轮到此停止，不继续盲试量化档。若继续区分基础模型与共同量化影响，先补同GSQ处理的更高精度源权重及基础checkpoint revision证明，再用相同token/参考图验证；存储和布局缺口如下。原六项FAIL、原gold、原评分和P6正确性门FAIL保持；DEQUANT_SIDE仍未运行。不改提示默认值、生产权重、EOS处理或ISA门控，不建立性能/质量采用结论。

本轮没有找到同谱系完整BF16/F16权重，也没有自动下载。根据当前1224张量的真实形状，完整16-bit理想张量载荷为353887799040字节＝329.584GiB；保留当前低比特PLE、其余16-bit则约261.038GiB。它们不是已验证的下载文件大小或最低RAM要求。

盘点时可用磁盘约163.5GiB，仅存完整16-bit理想载荷就至少再缺约166.1GiB，尚不含元数据、转换临时空间或运行日志。原NGL18若全部16-bit，对应GPU张量约85272.5MiB，明确无法照搬到24GB卡；需要另定布局，并以同布局重新运行公共基线。本机约62.5GiB RAM不能容纳全部16-bit权重常驻，mmap/lazy能改变驻留需求，但其读盘成本与可运行布局未经验证。详见 [full16bit-resource-estimate.json](../workspace/combination/higher-precision-20261028/full16bit-resource-estimate.json)。

## 验证与复现证据

实验专用源码仅保存在本轮raw：[run_probe.py](../workspace/combination/higher-precision-20261028/run_probe.py)、[analyze_probe.py](../workspace/combination/higher-precision-20261028/analyze_probe.py)、[final_audit.py](../workspace/combination/higher-precision-20261028/final_audit.py)。复用P8输入/库校验、全logits读取、排名与资源Guard；未新增通用框架。驱动与预登记记录真实命令/源码hash，输出目录拒绝覆盖。

独立code-reviewer仅作本地静态只读核查，未发现影响当前探针结果的实质缺陷；没有运行SSH、模型或测试，不将其意见当运行验收。见 `STATIC_REVIEW.json`。

最初系统venv没有独立安装gguf包；随后仅将已有参考源码的`gguf-py`加入读取路径，成功读取header，没有安装依赖或下载。首次错误和修正保存在 `prepare-import-correction.json`。

复用的 `tests.test_reference_logits` 本机和29各5项通过，不声称新增P9专用单测。29初次stdout文件为空（unittest写stderr），随后仅补跑这5项并正确留存输出，最终日志为 `reused-helper-tests-29-final.log`，原回执保留。根仓库 `pnpm typecheck/lint/test/test:integration/build` 本轮均exit0，日志在 `local-verification/`；保留原Phaser chunk提示。未重跑P6服务402项、全量native parity/lab selftest。

实验包根复现时，每次使用新目录名，且前置完整hash/身份/容量资格必须已有并通过：

```bash
P9_PY=/home/hhtele/strata-0.1.43.1/.venv/bin/python
P9_TASK=workspace/combination/higher-precision-20261028
$P9_PY -B "$P9_TASK/run_probe.py" --precision IQ3_S --suite qualify --name higher-qualify-new
# long驱动核对本轮冻结的higher-qualify-v1资格；不能覆盖旧目录或跳过前置门。
$P9_PY -B "$P9_TASK/run_probe.py" --precision IQ3_S --suite long --name higher-long-new
```

资格和长输入阶段退出码均0，仅表示采集与门控完成。共1286个资源样本，无abort；峰值64°C/23588MiB，最低MemAvailable54147MiB。长输入阶段两个完整prompt均达到冻结计数，逐例打印消费FNV及8行完成标记。进程映射核对实际5个库hash及2个IQ3_S分片，见 `higher-long-v1/loaded-library-map.json`。

最终13个生产保护hash、原生二进制和六文件port、参考客户端/库均不变，4个权重的size/mtime仍与本轮完整hash时一致。两个拥有的C++ PID均退出，GPU1MiB/47°C、无计算进程，18089可绑定；生产仍inactive/dead/enabled。P6原182、P7原373、P8原140个raw文件及P3冻结输入逐一复核不变。见 [FINAL_PROTECTION.json](../workspace/combination/higher-precision-20261028/FINAL_PROTECTION.json)。未安装依赖、未下载权重、未改systemd、未启动生产，未提交/推送/部署。

raw：29 `/home/hhtele/strata-lab-4090/workspace/combination/higher-precision-20261028`；本地 [workspace/combination/higher-precision-20261028](../workspace/combination/higher-precision-20261028)。不复制大权重或已有库。双端逐文件SHA256回执为 `RAW_MANIFEST.json`、`REMOTE_RAW_INTEGRITY.json`；交付包MANIFEST共212文件。只新增本报告、更新入口/验证记录，实验专用源码与数据保存在raw，范围外既有修改保留。
