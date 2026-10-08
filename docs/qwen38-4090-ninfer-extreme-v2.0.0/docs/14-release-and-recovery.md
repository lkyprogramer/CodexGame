# 验收发布与回滚

## 1. 补丁分类

| 类别 | 允许改动 | 最小质量门 |
|---|---|---|
| A 控制/索引/缓存 |不改变target算术或存储|状态oracle+原3题+采样/会话负对照 |
| B 等价kernel |相同codec/计算合同|op比对+完整state/logits+真实任务 |
| C target近似 |新的QK/PV精度、codec、权重|更强holdout和既有质量集；不能仅3题放行 |
| D proposal近似 |只改draft量化/shortlist，target不变|q正确性+拒绝采样+性能+状态 |

## 2. 候选发布包必须包含

源commit、基础commit、完整diff、donor许可证/来源、编译器/nvcc/架构/镜像digest、target与companion每对象hash、运行flags、cache schema、原始计数/请求摘要、数值测试、原Java/holdout、容量实占证据、OOM/错误清单、恢复记录、未完成项。

源证据必须与测量对应的二进制/模型绑定。不能用上轮同镜像Java3/3替代本轮新KV/新draft配置，也不能用同recipe revision替代被原地改写shard的hash。

## 3. 推广顺序

1. CPU单测/静态/负对照；
2. 独占GPU op/数学/状态测试；
3. 一小时候选筛选；
4. 新会话独立复测+2小时以上定向soak；
5. 用户明确批准后才修改生产配置；保留完整旧镜像与artifact。

**本包不自动上线。** `CANDIDATE_PASS_NOT_RELEASED`并非GO；每个优化可独立合入，不强求打包全部“极致”选项。

## 4. 回滚

未上线实验：结束候选、恢复原unit、18343 models+smoke。已批准上线后：回原生产launch文件/镜像/旧artifact/旧cache目录。不同schema的cache独立目录，回滚不解析新cache。保留失败dump但先脱敏，不在recover中自动delete所有缓存。

## 5. 停止条件

性能显著改善但一个状态corruption即NO_GO；无损类数值差异未解释即暂停；损失类超出预登记quality budget即退回；200192不满足不能再降cap偷过（200192已是用户底线，docs/02 §1）；5轮小改都未超噪声就暂停该热点。不要为了展示进度升级为另一个大型引擎。
