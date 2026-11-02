# DF01 / D0B · CPU准备缺口补齐

日期：2026-11-02。范围：用户授权补齐D0的CPU准备缺口，并参考两个指定仓库构造代码样本。连接方式为`ssh 29`。

**已完成：CPU输入、参考夹具、原生验证程序和预登记准备。** 当前`CPU_preparation_ready=true`。D1的GPU正确性仍未验证，`D1_GPU_qualified=false`。本次没有GPU实验、目标引擎启动或生产启停。

原[D0回执](DF01-D0-PREPARATION-20261102.md)保留`BLOCKED_PREPARATION`。本次使用独立目录补齐缺口，没有改写原失败与缺失记录。原六FAIL、P05和已关闭探索结论不变。

## 1. 输入

两个参考仓库保持只读。取样只包含指定的Git已跟踪源码、测试与构建文件。不读取环境文件、生产导出或运行凭据。

| 仓库 | 固定HEAD | 用途 |
|---|---|---|
| hhtele-superuser | f40f8a454c85062a614b2cfc9e6ca8b85797d4e5 | 角色/权限修改场景；独立认证清理场景 |
| lishuedu-data-sync | 172ddaa60facfdb922ad7a2c29d95f115a4e7919 | 命令幂等、取消、租约与状态回调的长代码留出 |

新样本的来源标签为`repository_constructed_not_pi_session`。这些样本是基于真实源码构造的修改请求，不是Pi请求回放，也不构成两个仓库的业务验收。

取样规则：按预定顺序累加完整文件。达到目标、越过范围或用完清单时停止。仅在实际计数的有效前缀中选择最接近目标者。记录全部计数尝试，不重复文件、不截断源码、不加填充。选择过程没有观察DFlash2输出。

| 单元 | 来源 | A0/PT0实际token数 | 结果 |
|---|---|---:|---|
| S-C | superuser角色/权限，10个完整文件 | 7,907 | 符合6,144–10,240 |
| S-R | 原Pi发布审计说明 | 7,051 | 符合6,144–10,240 |
| L-C | 原Pi Java LSP R04代码修改历史 | 104,207 | 符合98,304–122,880 |
| L-R | 原Pi上游评估历史 | 103,183 | 符合98,304–122,880 |
| D3-S-C | superuser认证清理，13个完整文件 | 6,717 | 符合6,144–10,240 |
| D3-L-C | data-sync命令取消，13个完整文件 | 105,962 | 符合98,304–122,880 |
| D3-L-R | 原Pi移植架构说明 | 104,749 | 符合98,304–122,880 |

七项均用原A0 tokenizer/frontend和PT0渲染。CPU计数与tokens-file逐ID往返一致。输入＋2048输出预算＋4096预留均不超过131072。provenance记录原文件SHA256、脱敏次数、固定HEAD和文件清单。

D3主留出与D2主选择样本来自不同仓库和不同任务。S-C与D3-S-C使用不同文件集合。旧5947-token和81-token样本仍在原D0原件中，没有重标为通过。

## 2. Q8参考夹具

固定Q8 pack没有更换：SHA256为c7d83c0cdfeadc7c692a1587795adb0181cfd94dacd96ac1a91f71ea7ecc62ed。原checkpoint/config/pack均重新校验，与D0一致。

参考计算使用独立目录中的`torch==2.5.1+cpu`。`torch.version.cuda is None`检查通过。十个轮子共185367064bytes，来源为官方CPU索引，逐文件SHA256冻结。安装使用`--no-index --no-deps --target`，未向生产venv安装依赖。

第一次下载因跨平台轮子匹配和索引连接失败而结束。第二次明确Linux平台与官方CPU索引后取得依赖。没有修改系统代理或安装CUDA依赖。

参考代码复用固定DFlash2 Torch前向。新增DF2P读取器直接反量化实际Q8权重，恢复原norm、conv和BF16 codebook形状。参考计算还覆盖实际激活格式：

- 原生draft GEMM输入：32元素一组，FP32 scale，最近偶数舍入。
- draft head输入：Q8_1，FP16 scale，远离零舍入，保留有限值夹限。
- CPU控制检查覆盖两种格式的12个舍入值。

权重矩阵的GEMM输入才应用量化，attention矩阵乘和selector codebook点积不误套量化。CPU归约、RoPE和GPU实现不宣称逐bit相同。GPU数值、token和概率仍按冻结门判断，不在D0放行。

| 夹具 | context rows | seed | 覆盖 |
|---|---:|---:|---|
| drafter-n32 | 32 | 1 | 短context |
| drafter-n2048 | 2048 | 2 | 滑窗边界 |
| drafter-n2064 | 2064 | 3 | 环容量边界 |
| drafter-n2300 | 2300 | 4 | 环绕与滑窗掩码 |

最终四组参考用时40.555s。每组保存随机tap、embedding、原生Q8 head、词表映射、最终行和selector结果。CPU共执行8次reference forward：最初FP32激活版本4次，最终Q8激活版本4次。前一版本原件保留，不作为最终GPU比较参考。

## 3. 两项原生验证程序

程序只编译、链接，没有执行GPU路径。使用原A0 CUDA12.3/sm89/Release工具链和只读静态库。生产binary没有替换。

| 程序 | 夹具数 | 内容 | 最终binary SHA256 |
|---|---:|---|---|
| drafter_qualification | 7 | 四组Q8前向/环边界；三组独立selector | dd81db40825ea253339df28e1b9eb5d7c2927d4148b698efca1638582d815200 |
| target_state_qualification | 9 | snapshot往返；greedy/sample首拒、中拒、全拒、全接受；目标EOS | 53c2ab79c8dc1a0778e0c280135fe3f4a072aa9d5ea5c6b28ca9d83eec8129ab |

总数为16，不增加原D1程序预算。目标程序必须命中DFlash2并启用target taps；回退MTP时不能用它声称DFlash2通过。

drafter比较包含有限值、每行cosine≥0.98、norm比例0.95–1.05、七个token全部相同和概率绝对差≤0.05。独立selector覆盖unary选择、前驱依赖和tie，token必须相同，概率差≤1e-5。没有只打印相等数量而仍返回成功的路径。

目标程序使用真实target、verifier和专家池。它比较逐token与窗口执行的有效输出及KV/GDN/PLE/index状态，并单独推进、比较MTP fallback状态。普通目标logits必须有限，采样结果还必须符合独立host sampler参考。host参考按position索引Philox，保留top-k→top-p→min-p→temperature顺序。

snapshot和有效state按字节比较。若D1不能建立匹配路径或出现差异，停止为数值oracle阻断；不得自动加容差或追加样本。CPU准备不证明这些GPU检查将通过。

资格程序含诊断读回和同步。它们不用于性能计时。性能两臂仍使用D0的同一个最小host计量binary，SHA为dbda1eefd5d6ebf50d82af6f6eb22edb2daa7abb39447844ab8474268d38c68e，没有更改其CUDA调用或执行图。

## 4. CPU验证与失败保留

| 检查 | 已执行结果 |
|---|---|
| 数值/selector比较器 | 7项，错误token、错误概率、NaN和错误形状负对照均检出 |
| 状态比较器 | 10项，GDN、PLE、KV、MTP与索引元数据差异均检出 |
| host sampler | 201项，greedy tie、top-k和top-p控制检查通过 |
| CLI终止输出 | 3个合法场景通过，2个错误输出/非法提交负对照失败符合预期 |
| 原D0默认exact-match证明 | 复用原6561项CPU枚举证据，源码未变，没有重跑 |
| 原生验证程序构建 | 两项编译/链接exit0，GPU未执行 |

首次EOS测试错误地要求“内部提交行数必须等于可见输出token数”。源码抽取的host块在首EOS场景记录commit4、output1，测试返回`FAIL_PREFIX_CONSERVATION`。该失败及源码均保留。

这不是已确认的生产缺陷。当前CLI在终止时丢弃会话状态，没有API复用或状态导出。修改后的测试分别检查合法的已接受输入前缀和EOS截断输出；追加EOS后输出、提交超过窗口的负对照均失败。GPU夹具进一步比较实际提交前缀与逐tokenteacher forcing的状态。没有修改A0提交逻辑或缩减数值断言，也没有据此认可服务缓存生命周期。

构建日志保留-Wrestrict和测试源码的-Wmisleading-indentation告警。没有将告警写成检查失败，也没有扩大到无关重构。所有原生GPU结果仍为NOT_RUN。

## 5. 质量集与执行合同

18项质量输入均完成CPU渲染与token ID保存：

- 原六项长检索失败：请求文件SHA与P00冻结记录一致，gold和历史FAIL不变。
- 四项工具语义：tool-symbol、schema-boolean、tool-unicode、tool-long-id。
- 八项代码题：沿用原Java任务和Harness SHA；模型生成代码仅进既有受限Docker评分。

原六项保留各自历史采样与输出预算，不混入生产采样性能统计。工具JSON/schema和真实Pi工具链没有获得CLI验收结论。18项不是正式2pp质量非劣样本量，当前没有生成答案或重评分。

NATIVE_COMMANDS和PREREGISTRATION已冻结D1的6条生成命令、D2的22条生成命令。命令目录只是查找表，不作为执行循环；未选cap的D3命令不自动执行。D1包含greedy与生产采样对照。D2先执行三对A/A，再执行四单元、两cap配对。

MTP保留974MiB预留，DF保持D0预声明1900MiB，两臂各自expert-cache auto。未设置PROB/COUPLED/GATE_PICK，没有改PT0、模型、KV预算、温度、服务guard或其他优化。

首个GPU维护窗口仍限定两个验证程序、16组夹具、28次自由生成、4小时。D1子阶段仍限定60分钟和6次生成；通过D1不自动执行D2。所有GPU执行与停生产均未获本轮授权。

## 6. 原件与生产

远端目录：`/home/hhtele/strata-lab-4090/workspace/dflash2/df01-d0b-20261102`。

本地原件目录：`workspace/dflash2/df01-d0b-20261102/`。WHEELS、INPUTS、Q8_REFERENCES、QUALIFICATION_BUILD、QUALITY_INPUTS、NATIVE_COMMANDS和PREREGISTRATION给出来源、完整命令及SHA。权重、依赖、fixture二进制和验证程序留在29，不进入Git。

最终主机读回为2026-11-02 **10:47:39北京时间**：active/running，MainPID2443578，NRestarts0；health HTTP200、loaded=true、model=openclaw/Qwen3.8-next、max_context131072。13保护SHA全部一致。本轮没有目标模型HTTP/CLI生成请求，CPU参考前向另计8次。

原D0与D0B文件合计3854609061bytes，低于6GiB上限。两个取样仓库没有源码修改。无commit、push或部署。

最终原件与文档校验见workspace/dflash2/df01-d0b-20261102/PACKAGE_CHECKS.json。当前下一步是另行授权的D1 GPU资格验证，不是升级、服务接入或采用。
