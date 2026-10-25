# SM89 kernel：一个实测热点、有限配置

NInfer已有gated RMSNorm+SiLU；可试的是D128 gated路径的CTA分组，不能重复宣称新增融合。GDN预载可比较无预载/滚动/完整窗口，保持Qwen GDN数学与state顺序；b12x KDA的head/gate/records不可照搬。

Q4/Q5 small-T已有P3实现与数值/Graph最小证据；只有真实路由占热点才调配置，不换权重格式/scale策略、不重复做上游已有kernel。若冷prefill才是主要瓶颈，应选择该实测prefill热点，不强制先做decode kernel。

每个热点最多三个静态配置；精确SM89/shape/codec/encoding/Graph key，保留原路由。独立数值参考、实际route-hit及完整Graph/round/service测量共用一次K4验收。无净收益保持原实现，不建在线通用autotuner，不直接搬Blackwell路径。Ada有FP8能力不等于可使用Blackwell blockscaled/NVFP4路径。

详见[K2-T01](../plans/tasks/K2-T01.md)和[预算](../plans/08-validation-budget-and-estimate.md)。
