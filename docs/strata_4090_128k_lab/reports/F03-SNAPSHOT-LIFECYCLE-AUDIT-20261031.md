# F03 · 会话快照复制与生命周期审计

结论：**NO_QUALIFIED_CANDIDATE，本轮关闭。** 审计和必要CPU验证在一个工作日上限内完成；未发现可证明的泄漏或可安全删除的已结束快照。唯一新差量“同步KV capture避免被随后覆盖的零填”通过host后端正确性检查，但三个固定CPU配对均更慢，不保留为下一步候选。

GPU引擎启动0、推理请求0，没有重建engine；生产保持停机。缓存预算6144MiB/4 slots、PT0、模型/原始提示和既有六FAIL均保持。P05继续BLOCKED_EVIDENCE。本轮目标是暖态请求wall/TTFT与内存资格审计，不替换原decode性能指标。

## 原件与内存账本

复用P01B三请求及六份进程内存快照；账本位于`workspace/frontier/f03-20261031/MEMORY_LEDGER.json`。只有既有原件的离线分析，没有追加服务请求。

| 阶段 | native RSS MiB | native匿名 MiB | native VmSwap MiB |
|---|---:|---:|---:|
| prime前 | 44143.77 | 43090.51 | 348.83 |
| prime后 | 44974.74 | 43918.74 | 328.25 |
| append_1后 | 48356.07 | 46224.78 | 328.14 |
| append_2后 | 50485.64 | 48323.95 | 327.10 |

整个RSS增长6341.87MiB，其中第二append增长2129.57MiB。最大匿名VMA的RSS40927.22MiB全程稳定；smaps没有分配栈，不能把每个匿名VMA唯一对应到C++对象。

P01B日志明确两份parked image的逻辑容量：2417773568和2198511800bytes，合计4616285368bytes（4.2993GiB），没有eviction，均无retained KV复用。第二次park耗时1198.2ms，位于请求开始后、rewind/新prompt计算前，约占该请求8473.70ms wall的14.14%。这是本次观察的串行成本，不是可删量。

逻辑capacity账与RSS/PSS、共享映射不是同一口径，不相加或相减推导“泄漏”。fault/swap数据也不证明可省等待；其中哪些物理页与某个snapshot相同，没有runtime地址归属证据。合法旧分支占用空间不等于生命周期错误。

## 生命周期与已有覆盖

18个实际审计源码逐SHA匹配P6原tag；主要链如下，行号相对P6树。

| 对象/路径 | 所有权与最后使用约束 | 审计结果 |
|---|---|---|
| generate.cpp:14237→10645→10449 | checkpoint rewind、incoming restore或slot替换前，先park旧分支 | PT0追问不匹配完整live尾部，因此回退checkpoint并park有合理依据 |
| conversation_state.cpp:533–618 | 局部captured持有running state、checkpoints、KV；全部成功后才发布 | 失败不发布partial image；不应提前释放仍可回访的旧分支 |
| conversation_cache.hpp:336–358 | 完整恢复take转移所有权，内部前缀borrow保留donor | 旧分支与活跃链不是无条件可合并的同一对象 |
| generate.cpp:14415–14420；cache.hpp:278–296 | 只有incoming恢复后retain KV；后续dirty边界和会话身份限制复用 | P01B没有restore/borrow，故reused_kv_bytes=0符合此链，不是复用故障证明 |
| cache.hpp:383–467 | budget、LRU、guard、drop_superseded已存在 | 删除旧分支须保留其最深checkpoint；不能凭同一用户或相同token数删除 |
| generate.cpp:14209–14213、10598–10610 | 现有PARK_ASYNC路径可move马上丢弃的checkpoint；后台reader由join/token维持 | 不把已有move/async重接当新机制，不重开旧开关 |
| conversation_buffer.hpp | snapshot-owned分段buffer，保留恢复后的单一owner；增长不搬动旧payload | 跨两个仍合法分支强行共享需新的所有权/计账设计，本轮不扩为COW框架 |

原件未保存完整checkpoint身份，所以不能断言究竟哪一个最深checkpoint导致未supersede。直接关闭缓存、降低预算、删除分支、改PT0、malloc_trim或重新MMAP都不属于本轮候选。

## 唯一新差量及CPU验证

P6 `src/core/conversation_snapshot.cpp:361` 的非staged同步路径调用`resize(sizes[i])`，随后完整transfer覆盖`[keep,size)`。`keep<=old_size`已校验，因此新增字节全部处于覆盖范围。只在本轮CPU目录制作单行原型，改为已有`resize_for_overwrite`；原P6/P01B树、生产/回滚树和引擎二进制均未修改。slot fallback和全部异步路径保持。

正确性边界：transfer默认同步完成后返回；snapshot成功才move发布，其他直接调用者也只消费成功的局部对象。完整页/部分页/indexer spare row边界没有改。该源码意图不等于GPU数值验收。

实际在29执行：

- 原header-only `conversation_cache_test`：4834 checks PASS，覆盖superseded、旧分支保留、guard、dirty边界和分段容量。
- 扩展原`conversation_validation_test`的GNU wrap host transfer后端：基线和单行原型各2068 checks PASS。原断言全部保留，只新增每个真实copy位置逐点故障注入，覆盖checkpoint后/KV中途失败；要求返回false且不发布partial KV/running state。
- 测试设置`CUDA_VISIBLE_DEVICES=-1`，沿用原wrap；只编译host测试/原型对象并链接既有静态库。`ninja -t commands`仅读取原链接命令，没有构建或启动engine。裸buffer probe的ldd不含CUDA库。
- host wrap不能证明真实GPU/DMA、异步event或取消生命周期；这些NOT_RUN，不伪装为hardware PASS。

### 有限CPU成本筛查

使用实际`ConversationBuffer`，固定ABBAAB三对，不重试/替补。A为resize零填后copy，B为resize_for_overwrite后copy；全payload逐字节相等。使用整个2198511800byte snapshot作为偏乐观负载，真实候选只覆盖其中KV部分；没有drop_caches、trim、锁核、系统调参或配置扫描。

| 固定pair | A总耗时ms | B总耗时ms | B耗时变化 |
|---|---:|---:|---:|
| 1 | 626.107457 | 664.149373 | +6.0759% |
| 2 | 616.438846 | 664.130681 | +7.7367% |
| 3 | 616.332533 | 664.058422 | +7.7435% |

净省时为−38.04/−47.69/−47.73ms。不能只报告resize从约402ms降至0.34ms：B的copy阶段升到约664ms，完整成本没有减少。CPU分段值不能代替native CUDA/pageable-memory路径；结果不是GPU实测回归，也不是严格GPU收益上界。

本样本若要完整wall改善4%，需净省338.95ms，约为1198.2ms park的28.29%。当前CPU数据没有支持该空间；在三个预登记pair均无益后立即停止，没有继续改布局、缩负载或追加样本。本轮不输出候选，不进入native实施或GPU资格。

## 独立审阅与归档

独立Reviewer只读审查所有权链、单行原型和新增故障循环；确认无删断言、假空consumer或额外mock。Reviewer回读命令和原stdout，没有自行重跑CPU。随后独立核本地42项原件长度/SHA、18项源文件SHA及最终回执；支持NO_QUALIFIED_CANDIDATE关闭。见frontier/reports/F03_REVIEW.md和F03_TEST.md。

原始CPU导出42文件，压缩包SHA256：`6a387e43d8717595e1b599f1d732c18d4f007d5f2c66fe1e09448d0e2a3b0c23`。记录完整命令、输出、原型/test源码及库hash，不包含可执行文件、对象、库或权重。source目录另存18个审计源和tag身份；MEMORY_LEDGER、最终决策及文档检查作为本地补充，不倒写原42文件清单。

最终只读回执：2026-10-31 11:38:26北京时间，生产inactive/dead/enabled；GPU1MiB/42°C、无compute，18089可bind；13保护文件、原P6二进制和两份配置SHA未变。缓存6144MiB/4slots、PT0保持。无部署、推送或生产恢复。

## 结束点

F03本轮关闭。无泄漏或安全回收对象的充分证据，唯一新单行差量未过CPU成本筛查。保留所有正反原件，不扩大为快照共享/COW设计，不追加GPU；GPU内部空间仍未知，不能外推全局NO_GAIN。后续重开须有独立的新机制与当前暴露成本证据。
