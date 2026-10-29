# 性能模型与收益上限

## 1. 用户目标函数

单轮任务时间拆成排队、模板/tokenize、恢复或prefill、decode、工具往返。正式主指标为预登记的 restricted time-to-success：每个任务给固定总预算B，正确完成记实际总wall，未正确完成记B；同时报告完成率及预算耗尽率。基础设施失效单列为无效比较，不能伪装模型失败。decode tokens/s是诊断指标，不能代替任务完成速度。

对一层CPU/GPU协作，使用实际依赖和资源竞争构成的DAG：

\[
T_l = \operatorname{critical\_path}(DAG_l)
\]

仅在分支相互独立的玩具模型中，可写成 `front + max(resident_GPU, CPU, H2D_then_GPU) + join`。其中第三项包含copy之后的完整GPU计算，不能只放copy时间；resident与cold expert竞争GPU资源时也不能当独立分支。跨stream重叠必须用事件边界验证，不能将各核累计时间直接相加。

CPU内存下界：读取实际专家字节数除以可持续内存带宽；GPU同理。PCIe下界用实际链路实测，不用4090产品页的接口上限。包括重读、scale、激活、中间结果和cache miss；模型文件大小不能直接当每token字节数。

## 2. Amdahl用于拒绝低价值改造

\[
S=\frac{1}{(1-f)+f/s}
\]

f是可优化部分在**同一口径关键路径**中的比例，s是局部加速。必须使用当前latest_base上的profile，历史值只用于筛选。

| 纯示例，非预测 | f | 局部加速s | 整体加速上限 |
|---|---:|---:|---:|
| 仅优化占5%的kernel | 0.05 | 2 | 1.026× |
| 优化占35%的CPU路径 | 0.35 | 1.5 | 1.132× |
| 占35%的路径理论消失 | 0.35 | 无穷 | 1.538× |

以历史18.5ms、约6.2ms CPU miss部分、折算20GB/s为**条件示例**，假定同一计时口径、同样提交token/窗、同样路由和驻留，且该6.2ms全部是未被其它工作覆盖的关键路径、全受带宽限制并能到36GB/s，则新窗口约18.5-6.2+6.2×20/36=15.74ms，约1.175×。实际6.2ms含调度、解码、同步，20GB/s只是平均blob折算，故这个计算不是可承诺的17.5%收益。

## 3. 专家放在哪里

为每个实际dtype/shape/nt测量：

\[
C_{cpu}(e,n),\quad C_{gpu}(e,n),\quad C_{copy}(bytes,pinned,contention)
\]

分配时比较新增CPU队列完工时间与新增GPU/拷贝完工时间，并考虑slot替换成本；不是简单比较单个expert的isolated时间。CPU miss的昂贵程度随nt、布局和当前队列变化。缓存目标应是“避免关键路径时间/所占字节”，不是只追求hit rate。

必须保留真实路由。预取猜错只能增加资源开销；不得偷偷跳过未命中的专家。

## 4. 推测窗口的目标

\[
\mathrm{effective\_tps}=\frac{\sum \mathrm{committed\_target\_tokens\_including\_bonus\_and\_correction}}{\sum \mathrm{round\_wall\_seconds}}
\]

`draft_accepted`、proposal数、target bonus/correction各自记录。只有phase timer经验证互斥且覆盖round边界时才允许求和；当前verify wall包含部分等待，不能再加一次stall。动态轮成本用总提交token/总wall，不平均每轮tokens/ms；spec0也有真实target输出。

接受率高并不保证更快：T增大会提高CPU每expert的nt、扩大graph和scratch、挤占expert cache；128K时KV访问也更贵。lookup与MTP可以有不同T集合，但必须控制额外graph显存及回退。

## 5. 会话缓存的收益口径

\[
\text{缓存净收益}=T_{避免重prefill}-T_{park}-T_{restore}-T_{内存回收}-T_{额外竞争}
\]

PR2253可能减少重复prefill导致的几十秒停顿，但不能据此宣称单轮decode tokens/s大幅提高。必须出现实际park/refuse/restore事件并记录reused/read token，不能仅把“相同文本的第二次请求”称为恢复测试。

## 6. 资源机会成本

- 多一个graph可能挤走若干专家，使CPU miss增加。
- 低比特KV可能释放显存，但旋转/解包成本、RAM流量与质量改变必须一起算。
- prefill大chunk减少专家重传，但更多scratch可能降低resident cache。
- 新CPU快路径可能增加临时预展开内存与LLC压力。
- 多worker、多stream、预取、profile在线学习都可能争夺同一DDR或PCIe。

组合收益不得直接相加；每次组合都重新测关键路径与资源分配。
