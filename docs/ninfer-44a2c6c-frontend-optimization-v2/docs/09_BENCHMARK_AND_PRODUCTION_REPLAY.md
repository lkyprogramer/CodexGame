# 09 · 基准设计、输入校准与生产对照

## 9.1 保留证据与新实验分开

评审提供28条session CPU行与4条raw语料行。20条session有direct legacy参照，其余以已比过legacy的B1作间接参照；不能视为28条全部直接旧版验证。新测试必须链接候选产品代码，用完整独立legacy做G1。

`data/generated_sessions`是v2新合成数据，不是评审原输入。原`gen_prodshape.py`依赖raw语料而附件未包含这些文件，本包保留它供审计，不声称能完全复现101.56s。新增自写固定corpora与generator让后续实验具备可重复输入。

## 9.2 变量设计

主矩阵固定B≈450KB/900KB，分别控制recent assistant rounds≈3/18，使标准工具模板H接近5/20；**真实H仍以renderer测量**。固定总messages后，在历史段插入真实user，避免所有工具轮都堆在第一条user之后。增加一个new-user-after-long-tail场景，验证B基本不变而H下降。

独立扫：B、selected added count A、H、普通文本语言/代码比例、tool payload结构。不要只按token深度分档或把message_count当H。一个H≈384的stress保留用于正确性/复杂度，不参与生产效果预测。

## 9.3 四个离线 build lane

| lane | scanner | boundary | 用途 |
|---|---|---|---|
|legacy|旧find|原完整prefix编码|reference与性能baseline|
|b0|新单遍|原processor原样|单独归因B0|
|b1|旧find|新局部验证|证明单做B1还有代价，仅测试构建|
|b0-b1|新单遍|新局部验证|首期产品candidate|

配对汇总只纳入相同pair_id/repetition的完整两侧；若legacy只跑3次、candidate跑7次，前3对进入paired文件，额外4次放单臂分布文件，不能伪造legacy行，也不能把unpaired数据塞给严格配对工具。G4candidate p90取全部真实7次，配对收益取真实3对，并报告两者样本量。

不同lane使用相同request/resource hash，环境、编译优化、CPU pin尽量一致。不可使用review简化B0支路替代真实b0 lane。

## 9.4 CPU 执行协议

记录CPU型号、affinity、GCC/glibc、编译flags、镜像digest、governor、并行负载、input/resource二进制hash。先warmup两次candidate，计时期间不写大量stdout、不tokenizer下载、不生成fixture。慢legacy交错3次，candidate至少7次，避免连续先跑冷legacy后warmcandidate造成偏差。

只跑一个CPU基准，优先非生产同配置隔离机。若确需在29并行运行，用户授权后固定一个空闲逻辑核、nice19，记录业务TTFT/CPU压力并设置中止阈值；这不等于对生产零干扰。不变更governor/CPU quota抢资源。

## 9.5 输入校准必须离线完成

生成时`token_count_status=UNMEASURED`、`http_eligible=false`。执行者用真实resource对应frontend只编码/计数，输出case_id、input_sha256、resources_sha256、prompt_tokens、render_bytes、H、Q，再使用：

```bash
python tools/calibrate_fixtures.py data/generated_sessions/prod_h20.jsonl \
  "$MEASUREMENTS" --output-reserve 2048 --output "$CALIBRATED"
```

参数变量代表执行者实际生成文件，不是内置现成结果。helper不调用tokenizer，只校验已提供测量与input身份。HTTP选择还要核对`declared_use`、真实渲染hash、严格`P+reserved_output<=262144`；无法满足则缩小tool_bytes重新生成/编码/hash，不得截掉真实旧输入后仍沿用旧caseID比较。

约900KB合成形态即使273K tokens仍是合法CPUstress；HTTP采用校准至≤260096的独立fixtures。README中的“900KB≤1s”是CPU函数门，不要求它也必能走HTTP。

## 9.6 原始输出与聚合

基准每一行至少固定schema2的pair_id/session_id/mode/cohort/cache_kind、prompt/input/resource身份和prepare/tokenize等指标；pair_id必须编码case与repetition。run_id/编译器/sampling另存run manifest，不能向严格row schema塞未知字段。`oracle_match=true`只有本次完整reference对比通过才可填；未做为null，不列入paired performance结论。

本包`summarize_bench.py`按pair_id、session_id、input/resource hash、prompt_tokens、cohort和cache_kind配对；model/sampling/编译环境另由run manifest核对，结果不自动变成G4PASS。特别记录CPU-only的seconds、主/局部bytes、Q/A，不仅最终tok/s。times非负有限，缺失不是0。

## 9.7 生产收益的正确说法

评审1690条元数据的84.2分钟tokenize和57.8分钟full_reset prefill属于报告口径；缺logs不能独立复算。估算节约不得直接加到任务wall下降百分比，因请求可能重叠、工具/用户时间不同。发布后应逐条sum实际tokenize，同时输出same client/prompt/H分层和时间区间union。

工程结果报告先写：在匹配输入与CPU上B0+B1耗时x、原版y，G1合同全相等。再写授权HTTP中TTFT实际变化，最后给生产窗口只读统计。不能先把80.6s减0.443s就宣布现网已做到1s。

## 9.8 full_reset 控制变量

CPU测试完全不依赖GPUcache。HTTP性能对照须隔离高频小客户端，先建立单会话连续append基线，再进行另案的客户端交错实验。tokenizer修复不应通过提高L2预算获得附带收益后归功给B0+B1。
