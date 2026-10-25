> V2 参考快照：P7—P12 不再是执行权威；按根目录 `plans/00-master-plan.md` 和 `plans/01-v2-migration-map.md` 执行。本文保留历史设计与来源，不表示实现完成。

# 27B DFlash2 原生接入设计

## 架构取舍

选择“共享NInfer执行和状态设施，新增明确的DFlash2 companion绑定”，不把tqLLM的GGUF读取器、格式插件、server或memory-fit搬入产品。现有35B DFlash可复用buffer/生命周期设计，但它的层数、目标特征层和算子与27B DFlash2不可替换。[T02/T03/N01/N03/N04]

```text
same .ninfer Target artifact / same tokenizer / same full Target KV
              | selected-layer hidden (pending)
              v
  DFlash2 feature projection + normalization
              | commit-only publishing
              v
      bounded recent Draft KV --------- optional archive retrieval (P11)
              |
  anchor + mask block -> grouped conv / attention / MLP
              |
   draft head -> top16 -> conditional lattice -> chain <=5
              |
       existing TargetVerifyFrameView
              |
     target_verify_accept + ReplaySSM
              |
   licensed output + committed feature frontier
```

## C06：离线artifact与模型契约

新增`tools/convert/qwen3_8_27b/convert_dflash2.py`，输入**冻结revision的原始checkpoint**，输出`.ninfer` companion（拟定model_id=`qwen3.8-27b-dflash2`、weights_id=`groupwise-int-v1`）。这是明确增加的companion identity，不增加另一个Target或任意模型插件。loader仅通过`--dflash2-artifact FILE`绑定；普通`--spec dflash`仍按35B原契约。

P7登记资产状态；P10-T01必须取得完整权重清单、tensor shapes/dtypes/hash、config、license、target-layer ids、RoPE配置、conv_group_size、selector_rank、mask id、block size与词表映射后，才能冻结转换profile。此处不伪造下载过的Hugging Face完整revision；manifest为空时必须BLOCKED。

转换使用已注册NInfer groupwise-int存储与算子可以表达的布局。先用原始BF16资产建立CPU/PyTorch独立reference，再对**draft矩阵**单次量化并校验；norm、敏感selector表、embedding映射的dtype由转换profile明确列出。若已有Ops缺特定形状，P10-T03新增最窄的算子能力，不能静默套用Target常数。不得将tqLLM已量化TQ3文件再量化成Q4作为默认生产来源，以免累计误差且失去清晰reference。

`src/targets/qwen3_8_27b/impl/load/dflash2_bindings.h/.cpp`负责typed companion加载；新增`DFlash2ModelView`包括fc/enc_norm、每层qkv/o/gate-up/down、两侧动态conv/base、最终norm、selector-hidden/prev/next与draft词表映射。验证Targethidden/domain一致、layer ids合法且升序、所有张量inventory齐全、map不重复不越界、PAD/EOS/特殊token规则明确。不允许通过`config.supported=true`绕过完整绑定。

## 计算链与reference

feature抽取严格规定layer输出时点（层前/层后、norm前/后）与排列顺序，按原checkpoint训练契约而非同名猜测。reference从相同NInfer Target代表值计算相同隐藏特征；与tqLLM比较时不能默认两个量化Target会给同样特征。[T04]

历史注入是`G=enc_norm(fc(concat(target_features)))`，再映射到每层drafter K/V，K按各层norm和RoPE转换。[T04] 动态grouped conv为2-tap且使用base+dynamic项，attention/FFN前后各有位置；块开始的缺tap不能从上一块随意延续。[T07] selector的前驱/后继相互作用生成条件lattice；链选择复现tie、token map和position顺序。不是简单每一列独立argmax。

CPU reference路径`tools/reference/qwen3_8_27b/dflash2.py`与CUDA共享数据规范但不共享被测kernel/量化解码实现。输出逐层hidden、logits、top16、lattice和draftchain；每个误差阈值从算子代表值、累积精度和独立参考测试确定后冻结，禁止用tqLLM成品文本作唯一oracle。

## 固定ring和graph

新增`dflash2_context.h/.cpp`、`dflash2_schedule.h/.cpp`及layouts段；startup声明draft weights、ring、feature scratch、selector、head、graph allowance和checkpoint bytes。使用existing DeviceSpan/WorkspaceArena，不在decode热路径cudaMalloc。ring包含recent上下文和验证/草稿覆写保护；按manifest block与最大verify列算容量，不能硬编码2176为所有模型正确值。

必须区分`physical_draft_rows=B`与`accepted_candidate_limit=K`。tqLLM物理B来自drafter配置；K降低可以减少Target验证，但不必减少draft前向。首版保留原B，从链中取K<=5，记录其实际成本；只有独立证明shortened block仍按正确模型定义运行后才能增加可变物理B。[T05]

第一版base、text、greedy、chain。captured graph key至少包含backend、physical B、verify K+1、batch/slot布局、graph envelope、权重/资源generation；请求ID不应进入无限graph键。开启/关闭graph输出一致；warmup覆盖实际会用的shape，既有MTP/None不因不必要capture丢失显存。

## 草稿head与fallback

NInfer现有optimized proposal head131072行。[N02] 新draftvocab65536是消融项，不能自动搬同一整数列表：必须绑定Target token-domain/资源hash。比较65536/131072/完整drafthead的accepted与有效吞吐；Target验证head/采样域始终完整。CPUreference和rank/selector矩阵显存一起入账。

旧Target continuation命中但没有同identity drafter历史时，`dflash2_ready=false`，请求开始选择已就绪MTP或None；不得隐藏全prompt feature重算。P10的无archive固定ring允许新会话从完整prefill收集recent状态，P11再补持久草稿历史。中途失效时只在安全事务边界转ordinary，并记录fallback与成本，不能错误继续使用过期ring。
