# 03 · 模型、草稿器与资产冻结

## 1. 资产家族必须分开

| 资产 | 角色 | 固定/循环特征 | 本包处理 |
|---|---|---|---|
| thinkingmachines/Inkling-2-Mini | 正式目标模型 | 24物理层，6层prelude + 12层core重复3次 + 6层coda；48次访问；is_varloop=false | 主线目标 |
| thinkingmachines/TML-d24-varloop-research | 深度研究目标 | 独立checkpoint；可变循环训练，默认3轮；不能当正式Mini开关 | R02/R03/R04研究资产 |
| AtomicChat/Inkling-2-Mini-GGUF | 社区转换/量化 | README所用revision包含IQ2_M与Q8_0 DSpark | 启动/容量锚点；高质量候选另锁定 |
| 原生Inkling DSpark | 正式模型投机草稿器 | visit/features和Markov head有版本约束 | T06起单独验证 |
| minseo25/2dsd-inkling-2-mini-varloop-dspark-drafter | 2DSD研究草稿器 | 5层、不同feature层与head，target为指定研究revision | 不与原生DSpark互换 |

官方模型资料见 [S02/S03](02_evidence_register.md)。官方声明的最高上下文只作为理论能力线索；本包仍按目标硬件实测。

## 2. 已锁定的来源

- 正式Mini当前核查revision：`c9d028302cd0f035fdf8e7e91f089a4ce94d2195`。
- varloop当前核查revision：`91a57fe2b779bbd12c0f74d1f518cbd5b84e8d0d`。
- Atomic README示例GGUF/原生Q8草稿器revision：`309509848b3151419aa26d069eb03db57fd29a00`。
- 2DSD草稿器revision：`fe3e545788b84e879f3eb8b8f426aaceb5fb44c5`。
- **2DSD草稿器config指定的训练target revision：`657b53ba5da7baefe9ff15dca5cd25f5bd3dbaa2`。复现该卡时用这个target，不擅自替换成varloop当前main。**

revision只锁仓库快照，不能代替每个本地文件的SHA256。下载完成后生成 `models.lock.json`，逐项保存文件长度与内容哈希。没有访问的资产填 `availability=BLOCKED`，不要填虚构hash。

## 3. 量化选择策略

以质量优先选择可在目标上下文稳定运行的最高可接受精度。至少形成一个启动锚点和一个质量候选：

1. **启动锚点**：已知存在的 `Inkling-2-Mini-AD-IQ2_M.gguf`，只验证加载、映射和容量，不预设满足主力质量。
2. **主线候选**：IQ3_S / Q4_K或其他可核实的更高质量GGUF。先枚举固定revision真实文件，再选；文件名和可用性不得靠猜。
3. **量化参考**：同源较高精度模型或离线高精度结果。如果高精度不能在4090驻留，允许小规模CPU/分层参考或离线外部参考，但要记录运行环境，不能据其速度比较。

GGUF名中的总体量化不代表每个tensor同一类型。记录embedding、output head、attention、expert gate/up/down和control各类tensor的实际type与bytes。混合量化是资产变更，不能与算子加速同时改。

## 4. 必填指纹

规范字段统一为 `target_fingerprint`。本包早期段落中的 `model_fingerprint` 是它的同义名称，**不得生成另一种hash**；实现与持久文件只写 `target_fingerprint`，读取旧别名时要求值完全相同。另设 `asset_fingerprint` 表示只读资产集合；`draft_fingerprint` 表示草稿器及其运行绑定。

T01以单一规范化工具生成指纹：UTF-8、对象key排序、无多余空白、拒绝NaN/Inf、所有可选字段显式null；需要精确跨语言一致的浮点参数先转换成规范十进制字符串。C++读取冻结字段与生成的hash，不各自用另一套浮点JSON格式重算。以下对象的规范JSON再计算SHA256：

- 源repo/revision、所有GGUF或safetensors分片的内容hash。
- tokenizer文件hash、special tokens与词表顺序。
- chat template全文hash、reasoning开关与tool序列化模式。
- 物理层数、loop_start/end/count、is_varloop、每次执行的visit映射。
- quantization manifest、KV类型、滑窗与位置编码参数。
- adapter/control-vector集合（初始为空）、输出head变换与LoRA兼容标记。
- 正交的 `cache_contract`：policy、`W_lag`（不用时null）、共享层scope、SWA参数、固定prefill分区/块内读取语义、decode/verify语义版本。SWA窗口另称 `W_swa`。
- 正交的 `guidance_contract`：论文ID（2610.02185v1）、none/hidden/logits、reference pass、fixed/adaptive、omega/omega_max、readout位置、norm/softcap/温度/processor顺序。KV与guidance可以组合，不能压成一个互斥模式名。
- `sampler_contract`：真实温度、top-p/top-k、penalties、grammar、tie-break和EOS/stop协议；`arithmetic_contract_id`指向本次reference的数值语义。

`target_fingerprint = SHA256(canonical(asset_fingerprint, loop_contract, cache_contract, guidance_contract, sampler_contract, arithmetic_contract_id))`。完整session key再加入draft指纹（若保存其状态）、state格式和执行epoch。k/B/b、2DSD r1/r2及tree调度参数属于运行manifest；只有它们改变目标的读取语义时才升级target身份，不能把通常只改变proposal的策略误当目标模型。

草稿器另有 `draft_fingerprint`：训练target revision、target feature visits、hidden/norm语义、head类型、词表和tokenizer hash、block_size、KV类型、量化、折叠output的目标head hash。

任何涉及这些字段的变化必须产生新model epoch，旧KV、conv、prefix与草稿状态不可继续使用。

## 5. 草稿器兼容性断言

原生Mini的特征和2DSD特征不同。已核查2DSD config使用 `target_layer_ids=[2,31,36,41,46]` 与 `feature_layers_per_loop=[2,7,12,17,22]`；其训练target、5层结构和head类型也与原生3层MTP配置不同。具体数组以固定配置为准，转换时保留原始语义，不允许只看hidden_size匹配就加载。[S08/S09]

加载时必须校验：词表及特殊token一致、feature层数/编号/visit语义一致、pre/post norm位置一致、hidden维度和head版本一致、目标量化/折叠投影匹配。失败时拒绝草稿器并保留串行目标能力，不静默使用错配草稿。

## 6. Folding只作为有条件优化

Atomic已有将旧式hidden_out低秩修正与target output组合的工具。它只折叠修正路径，不能声称消除整个大词表head；新式 `markov_w2` 资产可能走另一条路径。折叠必须绑定target head的确切hash，记录F16转换误差和额外bytes。LoRA或output scale发生变化时默认禁用，直到独立验证。[S01]

## 7. 资产锁文件示例

~~~json
{
  "schema_version": "1.0",
  "asset_id": "mini-fixed-r3-iq3-candidate",
  "family": "formal_mini",
  "source_revision": null,
  "files": [],
  "tokenizer_sha256": null,
  "chat_template_sha256": null,
  "loop_count": 3,
  "kv_mode": "per_loop",
  "draft_asset_id": null,
  "availability": "NOT_RUN",
  "qualification": "NOT_RUN"
}
~~~

这是待现场填充的结构，不是可直接启动的模型配置。非空文件hash和来源绑定由T00/T02验证后才进入后续任务。
