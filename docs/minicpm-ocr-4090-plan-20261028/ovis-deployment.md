# OvisOCR3 在 29 的部署与专项测试方案

设计日期2026-10-28；2026-10-29已在29下载、部署并执行模型推理，实际结果见[执行记录](execution-report.md)。本文件保留设计基准；共同变量、用例与胜负判定以[统一对比合同](comparison-plan.md)为准。

## 1. 权威源和锁定信息

官方模型仓库HF revision：`4833d5d2afa6e769ee933f024504d67ace80a24c`。[模型卡固定版本](https://huggingface.co/ATH-MaaS/OvisOCR3/blob/4833d5d2afa6e769ee933f024504d67ace80a24c/README.md)即本轮任务用法与prompt真源；本模型卡未指向另一个专用部署GitHub源码仓库，不凭同名项目猜测权威实现。

模型基于Qwen3.5-0.8B，HF safetensors元数据共852,985,920个BF16参数；model.safetensors为1,706,030,528字节（约1.59GiB）。权重SHA256 `aa2311c6b22b07cf3afe9aac6e8bcb02a2b19dd8671b2a91d0b144071577e600`。[HF元数据](https://huggingface.co/api/models/ATH-MaaS/OvisOCR3?blobs=true)

架构`Qwen3_5ForConditionalGeneration` / `qwen3_5`，文本24层混合linear/full attention、head_dim256、2个KV heads、hidden1024；视觉patch16、spatial_merge_size2；配置max_position_embeddings262144。config的transformers_version=4.57.0.dev0是序列化元数据，不是已证实能装4.57并运行此模型的依赖锁。[config](https://huggingface.co/ATH-MaaS/OvisOCR3/blob/4833d5d2afa6e769ee933f024504d67ace80a24c/config.json)

完整小文件和hash已汇总至 [ovis-source-lock.json](ovis-source-lock.json)。该文件状态明确为候选、未部署验证；含HF revision、每文件HF blob/可得SHA256、ModelScope文件revision/SHA、vLLM版本和wheel hash。30个文件HF SHA与ModelScope SHA一致，包含权重、tokenizer.json、全部prompts、配置、chat template和crosspage脚本；`.gitattributes`和LICENSE不一致，merges/vocab等非LFS大文件未下载逐字对比，不能声称整个仓库完全一致。

[ModelScope官方metadata](https://modelscope.cn/api/v1/models/ATH-MaaS/OvisOCR3/repo/files?Revision=master&Recursive=true)含每文件SHA；主权重hash与HF一致。本地HEAD `https://modelscope.cn/models/ATH-MaaS/OvisOCR3/resolve/master/model.safetensors`返回200，0.293s；只证明该请求可达，不代表29下载速率或全链下载成功。部署使用snapshot_download完整目录（含prompts/），下载后与候选hash锁核对；master是可变分支，不独立作为不可变锁。HF与ModelScope两者非同一Git commit namespace，不互填revision。

## 2. 官方推理依赖与4090条件

官方安装命令只有：

```bash
pip install "vllm==0.22.1" pillow
```

vLLM v0.22.1 tag对应commit `0decac0d96c42b49572498019f0a0e3600f50398`。[官方tag API](https://api.github.com/repos/vllm-project/vllm/git/ref/tags/v0.22.1)

PyPI该版支持Python>=3.10,<3.15，x86_64 wheel SHA256 `cc50536c93827a577b2bc45f038b8b866c31ed220631008521a337c9b2558f4d`，wheel约261MB。依赖torch2.11.0、torchvision0.26.0、torchaudio2.11.0，默认CUDA13.0；Transformers范围>=4.56并排除若干5.0至5.5版本，没有精确版本锁。[PyPI metadata](https://pypi.org/pypi/vllm/0.22.1/json)、[CUDA依赖](https://github.com/vllm-project/vllm/blob/v0.22.1/requirements/cuda.txt)、[Transformers依赖](https://github.com/vllm-project/vllm/blob/v0.22.1/requirements/common.txt)、[默认CUDA](https://github.com/vllm-project/vllm/blob/v0.22.1/vllm/envs.py)

29驱动610.57.04满足CUDA13的>=580要求，sm89在v0.22.1 CMake CUDA13支持列表中。由此可判断硬件具备基础条件；没有Ovis官方4090显存峰值或吞吐数据，本轮不能伪造。[sm89源码](https://github.com/vllm-project/vllm/blob/v0.22.1/CMakeLists.txt#L104)、[NVIDIA兼容](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)

建议原生栈单独容器/venv，Python3.12，torch按vLLM0.22.1锁，不与MiniCPM的torch2.14.0源码环境合装。安装前dry-run、选定确实识别qwen3_5和processor的Transformers版本，生成完整freeze/wheel manifest；官方未给精确TF版本，不编造一套“官方锁”。使用隔离CUDA13依赖，宿主CUDA12.3不是必须升级项。

原生vLLM的registry确有Qwen3_5ForConditionalGeneration。[v0.22.1 registry](https://github.com/vllm-project/vllm/blob/v0.22.1/vllm/model_executor/models/registry.py#L561)

MiniCPM已锁的较新vLLM commit `18343393b4da41a7e8027efbc4c7e77c28301bf0`也登记同架构；该环境的Transformers源码有qwen3_5适配。因此存在“同runtime公平轨”候选，但仍需实际加载Ovis tokenizer/processor/weights及sm89 kernels图像推理后才可宣布兼容。新runtime结果不得冒充官方0.22.1复现结果。[共享候选registry](https://github.com/vllm-project/vllm/blob/18343393b4da41a7e8027efbc4c7e77c28301bf0/vllm/model_executor/models/registry.py#L614)

## 3. 官方输入/解码真源与16K预算

模型卡LLM初始参数：tensor_parallel_size1、gpu_memory_utilization0.8、gdn_prefill_backend="triton"、limit_mm_per_prompt image2。SamplingParams(max_tokens=16384,temperature=0.0)。tokenizer.apply_chat_template(enable_thinking=False)，图像convertRGB，mm_processor_kwargs为：

```json
{"images_kwargs":{"min_pixels":200704,"max_pixels":8294400}}
```

以上分别为448²和2880²。模型自己的preprocessor_config默认size shortest_edge65536、longest_edge16777216，processor_class Qwen3VLProcessor、image_processor_type Qwen2VLImageProcessorFast；不能忽略官方显式resize并误称使用等同预处理。[processor配置](https://huggingface.co/ATH-MaaS/OvisOCR3/blob/4833d5d2afa6e769ee933f024504d67ace80a24c/preprocessor_config.json)

generation_config明确do_sample=false、temperature0，EOS为[248044,248046]。chat_template在未启用thinking时生成空think区以关闭思考；仍按官方显式enable_thinking=False。[generation_config](https://huggingface.co/ATH-MaaS/OvisOCR3/blob/4833d5d2afa6e769ee933f024504d67ace80a24c/generation_config.json)、[chat template](https://huggingface.co/ATH-MaaS/OvisOCR3/blob/4833d5d2afa6e769ee933f024504d67ace80a24c/chat_template.jinja)

**官方max_tokens16384是输出上限，不是模型总上下文16K。** 用户希望固定16K时必须动态裁定输入+输出，不能照抄“输出16384”后与图像一起发送。patch16×merge2形成32×32像素/视觉token量级；源码计算grid_t×grid_h×grid_w/(merge²)。在最大面积2880²时约8100视觉token；2图约16200，加prompt和前序Markdown后可能直接超过16K；即使单页输出8192再加文本prompt也可能超额。[视觉token源码](https://github.com/vllm-project/vllm/blob/v0.22.1/vllm/model_executor/models/qwen3_vl.py#L888)

推荐预算门槛：先用实际processor展开图像与prompt、统计input_ids/网格、分配max_new_tokens≤16384−实际prompt_tokens−安全余量；记录resized宽高/grid和实际prompt tokens。不得仅以原始像素估计后声称足够。对跨页轨用更低max_pixels（例如1536²或2048²，仅作为待验证候选），但必须注明偏离官方预处理，实际前序Markdown也计入预算；若仍超限，记录该固定16K条件失败，不静默截断Markdown或任意增大上下文。另设受控长上下文轨时两模型共同列明资源和预算。

2026-10-29实施更正：锁定vLLM0.22.1/Transformers4.57.6下，嵌套images_kwargs没有覆盖processor大小；将8294400改4147200时，两图实际/tokenize仍完全相同（18605/18894）。该原生示例复现保留为诊断，不充当有效像素预算基线。部署适配改为单独的顶层min_pixels/max_pixels；同时使用实际processor网格和服务/tokenize/usage复核，记录相对官方示例的差异，不混传两种写法。此前420输入与LOWPIX-r1均保留，标准Ovis需在参数生效后重跑。

## 4. 部署候选命令与真实差异

以下是29待验证服务计划，非官方已测命令。原生栈专用容器，GPU只启动一个服务，BF16/16384/.65/maxseq4/batch8192；Ovis并发4是4页/4请求，MiniCPM区域并发4是4个裁剪请求，不能当相同文档并发。统一外层页队列才可比较吞吐。

```bash
vllm serve /models/OvisOCR3 \
  --served-model-name ovisocr3 \
  --host 0.0.0.0 --port 18500 \
  --dtype bfloat16 \
  --max-model-len 16384 \
  --max-num-seqs 4 \
  --no-enable-prefix-caching \
  --mm-processor-cache-gb 0 \
  --max-num-batched-tokens 8192 \
  --gpu-memory-utilization 0.65 \
  --gdn-prefill-backend triton \
  --limit-mm-per-prompt '{"image":1,"video":0}' \
  --mm-processor-kwargs '{"min_pixels":200704,"max_pixels":8294400}' \
  --default-chat-template-kwargs '{"enable_thinking":false}'
```

容器内0.0.0.0配宿主127.0.0.1端口映射；不开放公网。跨页模式单独切换image2，串行调度同GPU，不同时另启第二模型服务。所有flags在installed --help预检后锁定；特别不要将Mini较新版新增的`--trust-request-mm-kwargs`直接套到0.22.1（本轮未在该tag找到对应字段，列旗标兼容gate）。服务端默认chat kwargs在该tag真实字段/自动CLI注册存在；gdn flag明确列在EngineArgs。[gdn flag](https://github.com/vllm-project/vllm/blob/v0.22.1/vllm/engine/arg_utils.py#L1528)、[默认chat kwargs](https://github.com/vllm-project/vllm/blob/v0.22.1/vllm/entrypoints/openai/cli_args.py#L96)

不强行复制Mini的downsample_mode4x/max_slice_nums9，它们不是Ovis的处理合同；不强行添加DSpark，Ovis模型卡没有此能力。官方原生greedy temp0，非Mini默认0.01/top_p0.001/top_k1。公平轨可同时设greedy0但单列为共同解码轨，不据此更改原生推荐轨。无需将config中的262144当作本轮目标上下文。

## 5. 任务prompt及输出合同

全部prompt固定为模型仓库prompts/*.txt原始字节，在source-lock里都有SHA；不能用Model Hub auto-generated usage片段替代作者说明。独立图片/页每次infer([page],prompt)；infer([page1,page2],...)意味着单请求两图，不是独立batch。

| 任务 | 真实prompt文件 | 输入与输出 |
|---|---|---|
| 全页纯文本 | plain_ocr.txt | 一图；纯文字，明确禁止Markdown/JSON/解释/补全 |
| 全页Markdown | document_markdown.txt | 一图；自然阅读顺序，LaTeX、HTML table、视觉bbox图片引用 |
| 全页结构 | document_structured.txt | 一图；JSON array，bbox/category/content；24个明确类别 |
| 布局 | document_layout.txt | 一图；JSON array，bbox/category，无转录 |
| 公式 | formula_recognition.txt | 一图；LaTeX；独立表达式$$...$$ |
| 图表数据 | chart_parsing.txt | 一图；title/source/x_title/y_title/values JSON；数字值为string，缺元信息用字符串None |
| 区域转录 | region_ocr.txt | 一图+替换{target_region}；坐标输入归一化，不输出坐标 |
| 字级定位 | word_spotting.txt | 一图；bbox/text JSON |
| 字段/模板抽取 | kie_fields.txt / kie_schema.txt | 替换{keys_json}/{schema_json}；schema是输出示例模板，不是正式JSON Schema约束 |
| 图像描述/流程图 | figure_captioning.txt | 必须full-page image；JSON array，视觉块含caption与可选Mermaid |
| 跨页表格 | crosspage_table.txt | 两相邻图+对应当前Markdown；source_pages/html JSON |

[全部作者prompts](https://huggingface.co/ATH-MaaS/OvisOCR3/tree/4833d5d2afa6e769ee933f024504d67ace80a24c/prompts)

文档类别：abstract、algorithm、aside_text、chart、content、display_formula、doc_title、figure_title、footer、footer_image、footnote、formula_number、header、header_image、image、inline_formula、number、paragraph_title、reference_content、seal、table、text、vertical_text、vision_footnote。

bbox顺序[left,top,right,bottom]，整数[0,1000)，非像素；原点左上，换算x*width/1000和y*height/1000，参考实际送入模型且方向一致的图。crop输入坐标相对crop而非原页；无rotation字段或自动deskew承诺。结构化JSON只是prompt请求，未启用约束解码；必须用schema验证数组、键、坐标范围与顺序、类别、content类型，不把json.loads成功当完整语义通过。

Markdown/structured的image/chart内容为`<img src="images/bbox_left_top_right_bottom.jpg" />`。模型不创建这些文件，包装层必须从对应原图按归一化坐标裁剪写入；多页用独立page目录，保留源页与旋转/缩放映射。官方Markdown例`filter_imgtags=True`会删除视觉引用；完整文本/图片导出必须False，保留raw_markdown。尾部重复清理会改写内容，raw与processed双轨评分，不能只测清理后结果。

figure_captioning的视觉类内容规定英文caption≤100词，标签可保留原语言；flowchart的Mermaid是可选项（prompt原文may follow），不是所有图或几何/地图必出Mermaid的保证。普通structured任务只给图片引用，不会自动变成caption。图形描述质量与OCR字符准确率分开；描述可能含无依据细节，不能混入纯文本OCR正确率。

## 6. 跨页真实依赖与输出

Stage1先分别用document_markdown或structured解析全部页，保留每页raw/finish_reason；structured先按阅读顺序拼content成Markdown。Stage2输入2相邻图和它们的当前Markdown（INPUT_PAGE index=1/2），用crosspage_table任务判断延续/重构；绝非对两图直接统一OCR即可完成。

输出数组每对象exact fields source_pages/html，source_pages为当前输入局部1-based页号，html完整table；无延续指定`[{"source_pages":[],"html":"No cross-page table exists between these pages."}]`。表内图引用含page_N/images/...，包装层须追溯原页，不以轮次局部页号覆盖文档真实页号。

**采用脚本的支持范围**：官方document pipeline每个相邻页对只接受一次合并，默认绑定“前页最后一表、后页第一表”。它不是任意表片段匹配器；同页多表、非边界续表、每页对两条独立续表都不能据模型返回了正确HTML就声明完整支持。helper `apply_pair(..., bindings=...)`虽允许显式片段绑定，但主pipeline的预测/写回/来源登记仍使用单次边界策略，不能只改helper调用就声称全链多合并已完成。[脚本支持声明](https://huggingface.co/ATH-MaaS/OvisOCR3/blob/4833d5d2afa6e769ee933f024504d67ace80a24c/document_crosspage.py#L12)、[默认绑定](https://huggingface.co/ATH-MaaS/OvisOCR3/blob/4833d5d2afa6e769ee933f024504d67ace80a24c/document_crosspage.py#L649)。

每张原表保存片段ID=`(原始page_id, 0-based table_index)`、原始HTML/文字hash、所占区间；每次合并保存实际操作数片段ID集合。无歧义的单表页可使用默认边界绑定。**初始适配器对任一操作页含多表的自动写回关闭**；仅记录默认last/first不能算可靠绑定。多表必须先有单独版本化的系统片段选择/绑定适配及通过证据，将模型合并内容与所选片段对应，才可另开profile；本轮不实现该匹配器。当前无该能力时标`UNSUPPORTED/FAIL`并保留原页，可单列原始HTML诊断，不宣称文档重建成功。PRED不得使用人工GT绑定；ORACLE指定片段仍只属于诊断。

写回验收同时检查：目标片段替换/删除准确、来源祖先集合正确、所有未参与表格的HTML/文字hash及位置关系保持、非表正文保留、资源可解析。原脚本已有非表正文不变检查，但它不能证明未参与的其他表格没被覆盖；不能只看重建TEDS、页号或该非表检查。

3+页从最后相邻对向前递归；merge结果写入较早页，再将更新Markdown重渲染为图片才用于下一步，保持图文一致。原始页图+已修改Markdown不一致会破坏输入合同。[作者完整脚本](https://huggingface.co/ATH-MaaS/OvisOCR3/blob/4833d5d2afa6e769ee933f024504d67ace80a24c/document_crosspage.py)

作者脚本额外依赖beautifulsoup4、markdown-it-py、playwright和Chromium；mathjax.js作为本地asset。它内置LLM同官方0.22.1/0.8显存/max_tokens16384/2880²，当前CLI只有model/output/stage1-prompt等，不应编造--max-model-len或--max-pixels旗标。16K/.65部署要适配其后端/渲染输入或另用共用API包装调用，明确记录不是脚本原样执行。浏览器渲染时延、CPU/RAM、图生成和原图crop成本全部计入端到端，不能只比较Stage2模型decode时延。

README示例Stage1接受finish_reason length后继续拼表，但用户质量验收应将length视为不完整，并禁止不完整前序页进入跨页成功结果。这是验收策略收紧，需留失败证据，不用清理算法冒充恢复遗漏内容。

## 7. 公平比较的必要边界

1. 同数据、同300DPI外部栅格化页、同旋转策略/页顺序、同GT、同硬件与独占GPU时段。Mini默认PDF内置144DPI会造成混杂，统一外部预渲染或给Mini明确适配，不让Ovis300DPI对Mini144DPI。
2. 原生完整系统轨：Mini=layout CPU+裁剪+region OCR+组装；Ovis=整页原生。允许各自推荐内部预处理/prompt/采样，以相同输出目标与资源上限评估；记录像素、视觉token、切块数和每页请求数。两者并发4语义不同，外层页并发统一，服务内部maxseq4分别记录。
3. 共享条件轨：同真实题块/区域、同raw文本/公式/表格任务、同greedy和总上下文/输出预算，可用共同runtime候选，但必须通过两模型加载/处理/输出smoke。原生与共享轨分表，不能混为单一排行榜。
4. 原始输出质量和产品后处理质量同时记录。Mini repair/dedupe与Ovis重复尾清理、image-tag过滤都可能改内容，不能一边只测clean文本另一边测raw；同官方图片被转为占位/描述时按视觉区域覆盖另测，不能从普通OCR分母里无声移除困难图片标签。
5. 端到端wallclock包括栅格化/布局/裁剪/排队/模型/后处理/JSON验证/图片导出/跨页浏览器重渲染；GPU推理时间和token/s另表。每页输入token不同，token/s不能独立代表页处理效率；报告pages/s与p50/p95/max、峰值显存/CPU/RAM、成功/超时/截断/非法JSON率。
6. 两模型官网榜单来自不同系统与评测设置，不据官方分数相差0.05判胜。Ovis README明确usage不是benchmark reproduction设置，作者并未给4090吞吐；不能将Mini5090的1.217页/s与Ovis模型参数量推断速度拼成结论。Ovis标题0.8B和Mini1.3B也不代表线性速度比例。
7. 幻觉、漏字、重复、图形标签、公式/表格结构、跨页误合并与不合并分别统计；图形caption/Mermaid是额外能力轨，若Mini无对应任务只记能力差异，不混入共通OCR总分。业务验收阈值要共同固定，未达到不得用“模型部署成功”代替“业务可用”。

## 8. 实施准入gate

完整ModelScope下载与manifest；独立vLLM0.22.1解析依赖和TF版本冻结；CUDA13/driver/sm89实测；gdn triton kernel与MM resize/grid验证；16K真实图文预算控制；单页image1和跨页image2模式切换；固定prompt字节；finish_reason/原始响应/各阶段耗时保存；完整图片与bbox导出；跨页原始页号映射和浏览器依赖；共享runtime候选兼容smoke。上述未跑前只称方案已准备，不写“已部署/已通过/比Mini更快更准”。

## 9. 独立环境、下载与启动步骤

与Mini使用不同release和venv，宿主根目录建议`/data/ocr/ovisocr3`。语料、GT、栅格化结果复用共同只读资产，不各自重做一套不同输入。原件和GT不能出现在模型prompt或模型可自动读取的输入目录中，输出按candidate/profile/run分目录。

| 宿主路径 | 容器路径 | 用途 |
|---|---|---|
| `/data/ocr/ovisocr3/models/main` | `/models/OvisOCR3` | 模型、完整prompts和脚本，只读 |
| `/data/ocr/ovisocr3/configs` | `/config` | 实际配置、启动脚本和任务prompt映射，只读 |
| 共同冻结的OCR输入目录 | `/inputs` | PDF/页图/诊断crop，只读；不含GT |
| `/data/ocr/ovisocr3/runs` | `/runs` | 产物、请求原始响应、计时与失败记录 |
| `/data/ocr/ovisocr3/cache` | `/cache` | 独立模型/JIT缓存，冷热策略一致 |

1. `jssh 29`检查GPU/显存、`free -h`、`df -h /data`、`ss -ltn`和现有容器；确认拟用18500端口无冲突。保留当前硬件/软件快照，不停其他业务。
2. 候选基础环境可用已有`nvidia/cuda:13.0.1-base-ubuntu24.04`，执行前检查image ID/digest和GPU透传。它与vLLM CUDA13 wheel路线一致，但JIT/系统库完整性仍需实际验证；缺依赖只修本容器，不改宿主CUDA12.3。构建时准备Python3.12及独立uv工具环境，uv版本与Mini一致。
3. 在镜像固定路径安装下列环境，先dry-run并保存解析结果，再装入专用venv。`transformers`等传递依赖必须在首次成功前冻结确切版本和wheel hash；仅一个vLLM版本号不能作为完整依赖锁。

```bash
uv venv /opt/ovisocr3/.venv --python 3.12 --seed
uv pip install --python /opt/ovisocr3/.venv/bin/python --dry-run \
  'vllm==0.22.1' pillow openai
uv pip install --python /opt/ovisocr3/.venv/bin/python \
  'vllm==0.22.1' pillow openai
uv pip check --python /opt/ovisocr3/.venv/bin/python
/opt/ovisocr3/.venv/bin/python -c \
  'import torch,transformers,vllm; print(torch.__version__,torch.version.cuda,transformers.__version__,vllm.__version__)'
```

`openai`是本地兼容API客户端依赖，pillow/openai/Transformers最终版本均写完整lock；不调用OpenAI云端或付费API。安装器如何取得Python/GCC/uv复用Mini方案的隔离原则，不能把两个候选的torch环境合并。

4. 独立下载工具环境安装并冻结`modelscope`。按用户指定[魔搭仓库](https://modelscope.ai/models/ATH-MaaS/OvisOCR3)取得完整snapshot，包含所有prompts、processor、tokenizer、模板与脚本；保存此次API文件revision/哈希响应。

```python
from modelscope import snapshot_download
snapshot_download(
    'ATH-MaaS/OvisOCR3', revision='master',
    local_dir='/models/OvisOCR3',
)
```

`master`只用于取件，实际准入按[ovis-source-lock.json](ovis-source-lock.json)内每文件SHA，权重必须匹配`aa2311c6b22b07cf3afe9aac6e8bcb02a2b19dd8671b2a91d0b144071577e600`。HF与魔搭LICENSE等非运行文件存在差异，按各自来源分别记录，不要求把一个仓库Git revision填到另一个仓库。

5. 固化环境、下载结果、服务端`--help`和有效配置；运行第4节服务命令。GPU容器仅映射`127.0.0.1:18500:18500`，本机API base为`http://127.0.0.1:18500/v1`。同一Docker网络中的适配器使用实际容器DNS名，不混用宿主127.0.0.1。
6. 保存真实图像processor grid/token数、neutral sampling、模型/EOS与thinking配置。检查`GET /health`/`GET /v1/models`后，用真实小页跑纯文本、结构化、公式和表格，再完成一份完整PDF；检查不是只有HTTP200或空JSON。
7. 首次warmup/JIT成功后做禁止联网的冷进程启动和完整页回归，找出惰性下载。最终镜像digest、系统/传递依赖、模型文件和适配器diff一起封装为不可变release。两候选原生环境均完成后再做同runtime C1兼容实验。

## 10. API适配与完整产物要求

vLLM接口接收图像消息，不直接接收PDF、Word或自动执行跨页重建。计划中的Ovis文档适配器负责共同300DPI栅格化、逐页调度、正确prompt、预算、JSON验证、bbox裁图、全文导出和文档对账；当前没有这套适配器实现。HTTP任务包装层沿用主方案的可选交付边界，不能杜撰模型自带`/v1/documents`。

一个基础结构化请求的候选客户端如下，**预算门未完成前只作小页冒烟，不能直接作为完整质量runner**：

```python
import base64
from pathlib import Path
from openai import OpenAI

client = OpenAI(
    base_url='http://127.0.0.1:18500/v1',
    api_key='local-only', max_retries=0, timeout=120,
)
prompt = Path('/models/OvisOCR3/prompts/document_structured.txt').read_text()
image_bytes = Path('/inputs/smoke-small-page.png').read_bytes()
encoded = base64.b64encode(image_bytes).decode('ascii')
response = client.chat.completions.create(
    model='ovisocr3',
    messages=[{'role': 'user', 'content': [
        {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + encoded}},
        {'type': 'text', 'text': prompt},
    ]}],
    temperature=0.0, top_p=1.0, max_tokens=2048,
    extra_body={
        'top_k': -1, 'repetition_penalty': 1.0,
        'chat_template_kwargs': {'enable_thinking': False},
    },
)
print(response.choices[0].finish_reason)
print(response.choices[0].message.content)
```

2048只是小页冒烟预算；正式runner按共同合同的实际图文tokens与任务上限分配，保存请求、原始响应、usage、finish_reason和所有attempt。`max_retries=0`用于防止客户端默认重试叠加，执行器最多1次可恢复重试且仍受原deadline。`length`不能记完整成功。

服务端固定MM参数，客户端不混传root与nested重复resize参数。若实际版本的processor合并行为与模型卡不同，先验证栅格大小/视觉token一致性并记录适配，不以未生效的kwargs自称已控制输入。

部署前最小适配清单：

| 编号 | 工作 | 定向验证 |
|---|---|---|
| O-A1 | 同一已栅格化输入/页号/方向送入API；真实16K预算与strict deadline | 大页、长竖作文、两图加长Markdown；超预算明确失败，无静默截尾 |
| O-A2 | 保留raw JSON/Markdown，验证结构与坐标；确定性转公共IR | 非法JSON、未知类别、无效bbox/重复块；不靠抽出普通文字掩盖结构失败 |
| O-A3 | `filter_imgtags=False`，按页和归一化坐标落真实图片；图内字追加识别计成本 | 图片引用全部可解析；page/crop坐标可回映射；图中文字不漏、不重复 |
| O-A4 | 原始/清理后内容、usage/finish_reason/尝试/阶段耗时落盘 | 人为小预算length和空白页；尾清理改写可见且不丢原文 |
| O-A5 | 文档/页/块终态及完整产物原子对账 | 中间页/导图/组装失败不能产生完整成功；断连和重启可定位旧run |
| O-A6 | 跨页后端改为同一16K/.65预算；声明单次边界绑定范围并登记表片段ID，不把helper显式绑定当已实现的多合并pipeline | 两图/PRED/原页与片段祖先/递归重渲染对账；无可靠系统绑定不写回；未参与表格和正文全部保留 |

不得给Ovis端到端补识别喂人工GT框。框只能来自其自身结构化输出；GT裁剪是独立R0诊断，执行目录和profile隔离。

## 11. Ovis专项测试与采用边界

除共同Q01–Q22/F01–F12外，必须执行：

1. 原生plain、Markdown、structured三模式各跑开发页对照，正式C0以structured为主；每个模式的全部调用与产物独立，不能拼接不同模式的最佳质量和最短耗时。
2. 全部4份长竖作文：完整原图、正确crop诊断、格线/空白区、漏行与重描/涂改；若有分块，测边界重叠去重和顺序。姓名crop、整页作文、英文GNHK分别报告。
3. 固定24类别中页眉页脚/脚注/页码/图注/vertical_text等逐类覆盖，尤其图像/chart返回引用后的图内文字。模型JSON类别存在不代表该类文字已完整转录。
4. 表格HTML、公式LaTeX、字段/代码精确性、结构化JSON和像素bbox映射；不把JSON可解析或公式可渲染当内容正确。
5. X01相邻续表、X02三页以上链、X03非续表/相似表头负例；加“每页多表但仅一条边界续表”“非边界续表”“两条独立续表”“旁侧未参与表格”fixture。先完整Stage1，后Stage2；目标重建正确与其他片段保留必须同时通过。原脚本不支持的绑定/多合并明确记缺口，不默认写回或用GT替PRED。直接和递归版本分表，错误合并、漏合并、重复行、片段/页号/资源错配均列出。
6. X04 full-page figure captioning与可选Mermaid，明确同一图的OCR字、caption事实和图结构分别评分。Mermaid缺失不影响普通OCR分数，但业务若要求流程图可执行格式则单列缺口。
7. 单页image1与跨页image2的真实预算和内存，在0.65/16K下无法完成的case保持失败；改变max_pixels或32K探索另建profile，不覆盖原case。
8. 每模型相同全页/区域/负载/冷暖/60min稳定性及回滚。Ovis快于Mini或更准的结论只能来自共同合同的实测，不由模型大小/官方榜单推断。

跨页预处理额外依赖`beautifulsoup4`、`markdown-it-py`、Playwright/Chromium和本地MathJax文件，准备后冻结版本及asset SHA。作者脚本没有本方案的预算CLI开关，不编造旗标；后端改造与渲染/CPU/存储成本都记录在O-A6和全局报告里。
