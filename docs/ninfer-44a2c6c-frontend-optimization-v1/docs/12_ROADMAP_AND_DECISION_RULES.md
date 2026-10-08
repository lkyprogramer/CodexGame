# 12｜后续路线与停止规则

## 12.1 新的优先级

第一项是去掉单请求hint引发的历史重复编码；第二项是跨请求token-prefix复用；第三项才是added-token scanner和BPE merge的常数/最坏复杂度优化。MTP、DFlash2、低bit模型、CUDA/attention本期不动。

此顺序与此前“只先加FrontendContinuation”的建议不同，原因是指定commit暴露了可独立修复的重复prefix调用。若B1已经把长会话tokenize压到可接受水平，它本身就是可以独立发布的成果。

## 12.2 B2上线的证据门

在B1成功后，重新测真实tokenize占比。若B2只省几毫秒却增加明显维护/失配风险，保留B2实验开关不作为默认；但不跳过已承诺的设计/测试说明。若B1仍然每turn需要几秒全量编码，B2有明确价值。

性能差的首因必须来自profile，不因“路线图里还有DFlash2”继续扩scope。没有净收益的变化应回退，不能用增加cache命中数字掩盖总wall没有下降。

## 12.3 可选P3

若fulltokenize本身仍慢：分别profile added_tokens逐候选find、NFC、qwen_split_words、BPE最小rank扫描与vector erase。候选包括ID-priority保持的多模式搜索器、减少临时string、逐词arena复用、保持leftmost tie的heap BPE。每项独立与固定legacy oracle对照，不顺便修正旧语义。

若新增hint落在巨大ordinary段，局部prefix工作仍膨胀：研究一次段内BPE产生多个前缀的精确边界结果，不能用不成立的“token结束就安全”捷径。

## 12.4 不应现在做

跨请求生成token直写cache、客户端delta新API、全增量Jinja、多模态增量、CPUcache持久化、多模型共享缓存、GPU多slot、换量化、runtime重写。只有新测量显示这些是主要瓶颈，才建立下一版需求。
