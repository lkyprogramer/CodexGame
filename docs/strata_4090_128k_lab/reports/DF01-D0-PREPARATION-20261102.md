# DF01 / D0 · 资产、源码与CPU准备回执

日期：2026-11-02。合同：[DF01完整方案](../plans/DF01_DFLASH2_TEST_PLAN.md)。用户本次授权完成D0并直连`ssh 29`；未授权D1/GPU、停生产、服务移植或部署。

**本轮D0检查与准备已收口，资格为BLOCKED_PREPARATION，D1_READY=false。** 资产和计量版已准备，CPU抽象采样检查通过；输入与原生正确性夹具未满足原合同，不能进入D1。没有用合成填充、改短档范围或削弱断言制造通过。DFlash2本机收益仍UNKNOWN，不能将本次准备阻断说成NO_GAIN。

## 1. 已完成与未完成

| 项目 | 本次结果 | 证据/边界 |
|---|---|---|
| A0二进制能力 | 静态确认 | 实际SHA仍819ff262…fade3d；44条Dflash2Drafter符号，原构建含STRATA_HAVE_DFLASH2=1；未执行引擎 |
| 固定资产 | 下载、校验与CPU转换完成 | 固定revision，原始权重1,206,140,008bytes；Q8 DF2P v1为760,353,792bytes、81张量 |
| 目标/草稿兼容性 | CPU metadata符合必要条件 | target hidden2560/vocab248320、48层；draft五层/32Q/8KV/HD128、taps[5,15,25,35,45]；不代表数值验收 |
| 原生CLI命令 | 已生成、全部execute=false | 从实际生产native argv派生，明确移除serve及生产写入，保留MTP fallback；不绕过通用runner冻结门 |
| 连续decode计量 | 最小host改动编译、链接成功 | 两臂将用同一实验binary；0新增CUDA调用/同步；未GPU验证 |
| 默认采样合同 | 源码审计与CPU检查通过 | exact-match、目标逐位置采样、首拒后终止；PROB/COUPLED/GATE_PICK仍排除 |
| 实际输入 | 六项已渲染并保存原生输入IDs | 三项长输入和短解释符合长度；短代码/短代码支持不足，独立长代码留出缺失 |
| D1正确性程序 | 未准备完整 | Q8匹配reference、selector断言及真实target状态夹具仍缺；详见第5节 |
| D3/D4完整预登记 | NOT_READY | 独立主probe缺失，不能冻结完整A/A、正式留出及后续质量执行合同；旧六FAIL不变 |
| GPU/性能/质量/服务 | NOT_RUN | 0推理请求、0实验GPU启动、0服务启停 |

## 2. 资产与来源身份

29直连HF第一次获取config即返回`Network is unreachable`，0bytes，保留ASSETS_ATTEMPT1_REMOTE.json。按合同允许的一次不同方式恢复，本地HTTPS获取固定文件、校验后SCP至隔离目录；29再次重算权重与pack SHA。没有修改代理、生产配置或安装依赖。

- checkpoint：incoai/Qwen3.8-Flash-Next-DFlash2@a22a1744e85c17364dcc54a6a420af7135d4c7f6。
- config SHA256：2409575986f9ea24d455343eb469c0e6940def5edab1d1be503bb8eb4cc3b1b9。
- 原始权重SHA256：d6723f2a359eaf33ec0c95f22ae8edda896774020c552296a85e1913b4d3186f。
- Q8 pack SHA256：c7d83c0cdfeadc7c692a1587795adb0181cfd94dacd96ac1a91f71ea7ecc62ed。
- packer SHA256：27e7be9e95d5d94d6a28cb9084bbdfd651fb86e4bd84d79a8e71de94e8af9e58，与先前固定源码一致。
- 资产合计1,966,495,036bytes，未超过6GiB上限。资产留在29隔离目录的assets/，不进入Git或本地文档包。

target tokenizer metadata SHA为c7e57b1e2ab166d16b69b7cab6092ed5e17eb228f5ddc7523cc6d3b4759f0f97。head index为2560×248320；MTP draft_vocab全部唯一且在vocab范围内。目标整份47GB GGUF没有重新全量hash，本次仅核metadata与既有固定资产身份，不能宣称重新认证所有target权重。

实际248077的token字符串是`[PAD248077]`，不是假设的`[MASK]`。已改为核对官方config中的mask ID=248077及词表范围，并保留真实字符串；mask embedding与量化后的数值适用性仍待D1。target的24Q/2KV与draft的32Q/8KV属于不同网络，未将两者误要求相同。

## 3. 输入资格与真实计数

沿用现有Pi完整parent-chain投影器、脱敏规则和A0 tokenizer/frontend，明确继承reply/PT0；保存body、provenance、token ID序列及文件SHA，CPU count与写入tokens-file逐ID一致。没有发送生成请求，历史usage数不替代实际token数。

| 单元 | 来源/用途 | A0 PT0实际输入 | 原长度合同 | 结果 |
|---|---|---:|---|---|
| S-C | Pi Java LSP R04代码修改，entry03dd103d | 5,947 | 6,144–10,240 | 长度不足 |
| L-C | 同session后续完整工具上下文，entry3c715e7c | 104,207 | 98,304–122,880 | CPU长度通过 |
| S-R | Pi发布审计说明，entry5353c404 | 7,051 | 6,144–10,240 | CPU长度通过 |
| L-R | 旧P00上游代码评估，entry04af2621 | 103,183 | 98,304–122,880 | CPU长度通过；属于解释，不冒充代码修改 |
| D3-S-C | 独立Pi M0任务，entryf922c8ba | 81 | 6,144–10,240 | 长度不足，历史usage11785不能补足 |
| D3-L-R | 独立Pi移植架构解释，entry38f5e504 | 104,749 | 98,304–122,880 | CPU长度通过 |
| D3-L-C | 所查独立M0长上下文 | 未取得 | 98,304–122,880 | 全部候选需要现有投影器不支持的compaction恢复 |

本次只查已知Java LSP、codex-host、d2r-mobile相关session；不声称全部Pi历史都没有可用样本。保留原请求及完整turn边界，不将相同任务的另一个中间点静默换成独立主留出，不增加填充。所有已生成输入均满足输入＋2048＋4096≤131072，但长度通过不证明自然输出足够长、工具可执行或质量合格。

由于主A/A probe及部分选择/支持输入缺失，D2/D3完整矩阵不能预登记；后续D4也未被宣布为已完成冻结。CPU准备已在停生产前发现该阻断，没有消费GPU预算。

## 4. 计量适配与默认采样

隔离目录：`/home/hhtele/strata-lab-4090/workspace/dflash2/df01-d0-20261102`。仅复制generate.cpp，使用原A0 compile flags编译一个host translation unit，并链接既有只读A0静态库；CUDA12.3/sm89/Release及mandatory开关不变。原生产binary、base对象和库未重建。

实验binary为build/strata-df01，SHA256 **dbda1eefd5d6ebf50d82af6f6eb22edb2daa7abb39447844ab8474268d38c68e**。编译/链接exit0，用时74.088s；有generate.cpp中std::string相关-Wrestrict告警，未扩大到无关修复。METER.patch仅增加两次host时钟读取和最终汇总输出。

计时从batched prefill返回后、kvg_ensure及verifier/bind/prepare初始化之前开始，在最终ver.wait_commit成功且逐轮host adapt线程已join后停止。保留首个token和该边界内冷graph初始化；无新增CUDA事件、同步、kernel或执行图节点。模型加载/prefill、汇总打印、无需最终提交等待的专家refill及进程销毁不包含在该指标中，另报整个CLI进程wall。原native decode逐轮累计只作辅助。

默认路径：df2.draft根据已提交的target features确定性提案；verifier使用实际目标采样器，以Philox(seed,pos0+t)给每行取样；CLI只保留连续相等提案，首拒后提交目标token并结束窗口。没有启用MTP q列表；CLI未请求penalty/min_p/logit_bias。真实GPU采样、processor实现及KV/GDN/PLE恢复仍需D1验证，CPU证明不替代它们。

CPU编译检查复用生产penalty_rows、源码抽取的接受条件和Philox原语。另以独立有限Markov参考目标穷举27种proposal×243种随机序列，共**6,561项**，joint输出与逐token参考一致；错误“拒绝后仍保留后续行”的负例被检出。该枚举不是调用GPU采样器或真实target。另编译运行原draft_cap_test通过，确认Ada不自动改cap。

第一次CPU枚举用均匀目标，负对照未被识别，作为FAIL_TEST_FIXTURE保留；原因是均匀目标抹掉了错误前缀的条件分布差异。改为非均匀、依赖历史的目标后原负断言通过，没有删除或放宽断言。两次脚本身份均保留。这不是DFlash2运行失败或GPU正确性结论。

NATIVE_COMMANDS.json仅准备未来命令，不执行：MTP保留974MiB预留，DF预声明1900MiB（依据源码bind/prepare建议、尚非实际峰值证明），各自expert-cache auto，专家槽损失计入候选成本；没有将MTP也改成1900或固定相同槽数。生产没有应用这些准备参数。

## 5. 阻断与下一步

当前只输出一个结论：**BLOCKED_PREPARATION，保持生产运行，不进入D1/D2。**

下一步仍是CPU准备缺口修复，而非GPU筛查：

1. 在有限、明确的历史范围内取得合格短代码与独立长代码主留出；若必须采用合成/compaction投影，先写明新输入合同，不能沿用“真实原请求”标签或悄悄放宽长度。
2. 准备与实际Q8 pack一致的reference、selector token/probability硬断言及两项有界原生GPU正确性程序。现有mk_parity_case依赖未安装的torch/safetensors/gguf；dflash2_parity只是打印tokens equal，exit状态只有cosine<0.98检查，不能作为完整selector验收。现有程序也未覆盖原合同的真实target拒绝/EOS/KV/GDN/PLE状态。
3. 补齐缺口后重新冻结D1/D2输入、程序、命令和资源合同。未补齐前，不开停机窗口；后续GPU仍需明确授权，首窗口上限仍为28次生成＋2个有界正确性程序、≤4小时。

本轮未安装Torch、移植服务或重构Pi compaction路径；没有以扩大CPU工程的方式绕过已发现的资格门。D3/D4未测，原六项长检索FAIL、P05及其他关闭结论原样保留。

## 6. 生产状态、原件与实际验证

最后读回2026-11-02 **09:46:40北京时间**：service active/running，MainPID2443578、NRestarts0；原native PID2443599未变。GET /health为HTTP200、loaded=true、status=ok、model=openclaw/Qwen3.8-next、max_context131072。13保护文件SHA全部一致。无GPU实验、无推理POST、无停启服务，无提交或push。

主要执行命令（均已实际运行）：

- `ssh 29 'python3 -B /tmp/df01-audit-d0-20261102.py'`：静态能力/生产保护回执，未启动引擎；首次符号名/主线程子进程枚举不完整，修正后回执保留V0与当前版。
- `nice -n 10 .../.venv/bin/python -B .../source/tools/dflash2_pack.py ...`：CPU Q8转换exit0；文件身份/81张量index核查通过。
- `nice -n 10 python3 -B .../build_meter.py`：单TU编译、链接exit0；新binary未运行。
- `nice -n 10 .../.venv/bin/python -B .../prepare_inputs.py`：六项CPU渲染和tokens-file roundtrip通过，长度门按上表判定。
- `nice -n 10 python3 -B .../cpu_sampling.py`：修正非均匀负例后CPU检查通过；原盲区失败保留。
- `nice -n 10 .../.venv/bin/python -B .../finish_d0.py`：draft_cap_test通过，D1_READY=false，生产保护通过。首次脚本假设mask字符串为[MASK]而失败，随后依据真实metadata核对官方ID，未改变模型/权重。

本地原件目录：`workspace/dflash2/df01-d0-20261102/`，含SOURCE_AUDIT、ASSETS、COMPATIBILITY、NATIVE_COMMANDS、INPUTS、METRICS、PREREGISTRATION、CPU_TESTS、METER_BUILD、HAND_BACK及FINAL_READBACK。原导出78个文本/源码/请求/token/回执文件，6,351,758bytes，逐文件SHA校验通过；weights/binary/object留在29，不随报告上传。

RAW_EXPORT.tar.gz为1,761,375bytes，SHA256 **4e54610dcf079ddd3e38f12b320be9ebeebef843512618d198d14f5dd67cef75**。最终health读回作为补充文件单列，不倒写原78文件清单。打包首次因归档在自身目录内触发directory changed提示，改为目录外按固定清单打包，exit0且逐文件验真。

文档/链接/清单最终检查见workspace/dflash2/df01-d0-20261102/PACKAGE_CHECKS.json；这类PASS不解除BLOCKED_PREPARATION。
