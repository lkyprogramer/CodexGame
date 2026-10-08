# GDN、Attention与prefill路径

P0把源模型的FP32 recurrent state保持到底。FP16 state只能作为独立P1优化；不是代码移植的默认前提。[S05]

## 持久状态

GDN含causal conv历史与SSM state。conv kernel_dim4表示3个历史位置；每个layer/sequence/slot都有明确stride。padding行写null/dedicated pad slot，不得写真实session。prefill与decode都从同一已提交frontier续算。

Attention的page-size、K/V interleave、head顺序与scale是provider合同。旧Kern捕获曾固化784-token页，后来TRTLLM路线改用64。**不能只把JSON中的784改64，却继续用旧cubin。** 新provider可选64-token页，但必须重新编译/捕获配套read/write/attention核。[S01][S02]

## Prefill末token

源Kern的Qwen bring-up指出：GDN chunk prefill与recurrent decode的结合/舍入路径不同。应让完整prompt（包含末token）走prefill，由最后一行norm/head产出首个生成token，不能机械复用纯Transformer“最后prompt token走decode”的旧约定。[S02]

## 正确的输入增量

下一轮复用的是**已被模型消费并形成状态**的token，不是“已经发给客户端的所有token”。最后一个sampled token可能尚未输入下一步。输出、KV/GDN frontier、checkpoint.len必须记清，不能缓存未执行的token，亦不能重复执行最后一位。

## 不采用的捷径

不截短attention window、不做PFlash、不语义压缩用户输入、不只保留GDN而丢KV、不使用旧session的state冒充前缀新状态、不改变rope scaling以便假装64K支持。所有这类改变都属于新模型数值配置，需要独立评估。

## 验证形状

chunk=256/512/1024，输入长度1/63/64/65/511/512/513、跨页、跨chunk；prefill后1步/16步/256步decode。先用相同chunk比较eager与graph，再做不同chunk漂移诊断；不要把不同chunk的文本完全相同当作所有实现的必然条件。
