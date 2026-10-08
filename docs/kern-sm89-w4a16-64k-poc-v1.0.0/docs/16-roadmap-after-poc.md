# P0之后：不是这次验收的隐含承诺

## P1a：真实采样与medium thinking

新增device sampler/RNG计数器，top-k/top-p/temperature/seed的明确合同。先无spec验证分布，再做Pi medium和现网对齐。不能把greedy接受逻辑直接套到随机采样的spec路径。

## P1b：DFlash2或MTP

优先从完整plain provider出发。DFlash2新增draft权重、tap/local context、draft/verify/accept/advance的事务，最后token/EOS/取消下只能commit实际接受的prefix。概率采样必须使用正确accept/reject规则；greedy正确不能证明随机采样无损。

## P1c：内存精度变体

FP16 GDN、INT8 embed/head、INT8/FP8 KV分别做profile与oracle。先测质量和长会话，再测速度。低bit并不自动更快；量化/反量化或状态replay可能增加计算。

## P2：120K→200K

当且仅当64K可用与数值合同稳固，再引入完整低比特KV codec+scale+attention消费路径。不是把manifest dtype写成u8就算压缩完成。需要200K实际输入、输出余量、checkpoint预算、long-needle/Java代码精确检索、多轮append与soak。

NInfer E8与KVarN只能作为独立参考，不混成一个未验证的codec。未来完成200K也要单独发布证据，不能沿用本包的POC_GO。

## 另一种价值路径

如果Kern最终未胜过NInfer serving，但得到验证过的SM89 kernel/数值测试器，可在许可允许和接口匹配下将局部成果移回NInfer。实验平台价值与生产替代价值分开判断。
