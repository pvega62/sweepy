                                  ████  █   █  ████  ████  ████  █   █
                                  █     █   █  █     █     █  █  █   █
                                  ████  █ █ █  ███   ███   ████   █ █ 
                                    █  ██ ██  █     █     █       █  
                                  ████  █   █  ████  ████  █       █  
<h1 align="center">Sweepy：多引擎求职搜索与评分</h1>

<p align="center">
  <strong>更聪明、更精准、更快速、更强大地搜索。</strong><br>
  并行抓取主流平台的职位，自动为简历评分，并生成排序报告。
</p>

<p align="center">
  <a href="https://github.com/pvega62/sweepy/actions"><img src="https://github.com/pvega62/sweepy/actions/workflows/ci.yml/badge.svg" alt="持续集成"></a>
  <a href="#quick-start"><img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10 或更新版本"></a>
  <a href="../LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT 许可证"></a>
  <a href="https://m8ven.ai/mcp/pvega62-sweepy-07ewva?s=readme"><img src="https://m8ven.ai/badge/mcp/pvega62-sweepy-07ewva?v=a2ea0bac35a4ed6e7512771f55ab2271" alt="M8ven 评分"></a>
</p>

<p align="center">
  <a href="#quick-start"><strong>快速开始</strong></a> ·
  <a href="#features">功能</a> ·
  <a href="#job-engines">职位引擎</a> ·
  <a href="#portfolio-support">作品集支持</a> ·
  <a href="#documentation">文档</a> ·
  <a href="https://github.com/pvega62/sweepy/issues/new">报告问题</a>
</p>

<p align="center">
  <a href="../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.ja.md">日本語</a> · <a href="README.ar.md">العربية</a> · <strong>简体中文</strong>
</p>

---

Sweepy 是一款免费工具，它搜索职位板，并按你的简历为每条职位评分。它读取公司招聘网站和职位板，丢弃重复与失效的职位，然后写出排序报告。你可以只对一次搜索关闭重复检查，而不改动配置。设置向导会打开一个启动台，用于搜索、创建配置、调优搜索，以及执行 Sweepy's Toolbox 中的引擎与聚合器管理等任务。

> 当前版本与发布历史见 **[CHANGELOG.md](../CHANGELOG.md)**。

## <a name="features"></a>功能

- **一次搜索多处来源。** 从 Greenhouse、Ashby、Lever、Workable、Built In NYC、LinkedIn、Indeed、Glassdoor 和 ZipRecruiter 收集职位。这些来源都无需 API key。
- **所有引擎并行运行。** 已启用的引擎同时启动。因此一次搜索的耗时接近最慢的那个引擎，而不是它们之和。
- **某个职位板失败时继续运行。** 每个引擎都有超时和熔断器。一个端点失败不会拖住整轮运行，也不会把同一个请求重复五次。
- **按需增加引擎。** 在向导中安装 HireHunt、openroles、jobdrop 或 Apify，无需离开终端。
- **按你的简历为每条职位评分。** 读取 PDF 或 Word 简历的文本，衡量其中有多少内容与职位匹配。
- **过滤失效链接。** 检查每个 URL，删除已不存在的职位。
- **跨职位板检查重复职位。** 匹配规范化后的职位名称、公司和地点，即使各职位板使用不同 URL 也能识别。传入 `--no-dedupe` 可在一次运行中保留每个职位板的列表。
- **跳过你已看过的职位。** 每日搜索报告新职位，而不是昨天的列表。Sweepy 在四天窗口内抑制已报告的职位。传入 `--include-seen` 可在一次运行中重新纳入它们。
- **把你导向正确的简历。** 把每个职位发给你为该角色写的那条简历 track，然后用颜色徽标标注卡片。
- **让作品集参与每个判断。** 把 Sweepy 指向在线作品集，或本地 PDF、Word、Markdown、文本或 HTML 文件。每张卡片都会列出该作品集里的作品。当你申请不止一类角色时，为每条简历 track 保留一个作品集。
- **生成你能用的报告。** 产出每页一张卡片、链接可点击的 PDF，另外还有供你自己跟踪的 CSV 和 JSON 文件。
- **把 CSV 变成申请跟踪表。** CSV 以 `date_applied`、`status`、`interview_stage`、`offer_amount`、`offer_date`、`follow_up_date`、`contact` 和 `notes` 结尾。你可以通过 Excel、Google Sheets 或 Notion 填写这些列。Sweepy 会把你的记录复制到同一配置的后续搜索中。PDF 给你一份排序后的阅读清单，每张卡片上都有申请链接。电子表格能保留超出 PDF 卡片上限的职位，并记录你对每个职位做了什么。用 `export.tracking: false` 关闭这些列。

## <a name="quick-start"></a>快速开始

你需要 **Python 3.10 或更新版本**。在 Python 3.13 上，部分包需要从源码构建。你可能要先安装 Microsoft C++ Build Tools。参见 [安装 Sweepy](https://pvega62.github.io/software/docs/sweepy/installation)。

```bash
git clone https://github.com/pvega62/sweepy.git
cd sweepy
pip install -e .
sweepy
```

`pip install -e .` 会安装全部核心依赖，并把 `sweepy` 命令注册到你的 Python Scripts 文件夹。重新打开一次终端，让你的 shell 从 PATH 读取该文件夹。运行 `sweepy` 启动向导，或加上命令选项，例如 `sweepy --run`。你也可以直接用 `python swee.py` 运行脚本。

这一条命令就给你两个内置引擎。需要时，向导会提供四个可选引擎，你永远不需要手动安装另一个 requirements 文件。

如果想改为一次拉取所有兼容引擎，在同一条命令上加一个标志：

```bash
pip install -e ".[all-engines]"
```

这样会在一次依赖解析中加入 HireHunt、openroles 和 Apify。`jobdrop` 被排除，因为它的元数据无法与 JobSpy 一起解析。当你需要它的 33 个职位板时，用 `sweepy --install-engines jobdrop --allow-engine-conflicts` 安装它。[职位引擎](#job-engines)一节涵盖两条路径。

运行 `sweepy` 会打开向导的磁贴式启动台。用方向键在 **Start Sweep**、**Build Profile**、**Load Profile**、**Sweep Settings**、**Sweepy's Toolbox** 和 **Exit Sweepy** 之间移动，然后按 Enter。磁贴副标题用平实的词句说明操作，例如 **Run your job search now** 或 **Open a search you saved**。**Load Profile** 让你选择一个已保存的配置，用于下一次搜索。工具箱包含配置编辑、引擎管理、调试日志、帮助、最近日志、文档转换和更新。**Build Profile** 收集你的姓名、目标职位名称、地点和简历路径。完成后向导会保存配置。运行 `sweepy --setup --profile profiles/your_profile.yaml` 可以直接编辑配置。

子菜单以 **← Back** 打开，它返回打开该子菜单的上一级菜单。Esc 起同样作用。在提问处，Esc 重新打开上一个回答。在子菜单内，Esc 上升一级。在启动台，Esc 退出。Ctrl+C 可在任何位置退出。

当有版本发布时，拉取新代码，运行：

```bash
sweepy --update
```

Sweepy 检查你的 Git 远端，并对检出做快进。它会重新安装 `requirements.txt` 以及你已安装的可选引擎。对存在未提交改动的检出，它拒绝改动。若只想检查新版本而不做任何更改，请用 `sweepy --check-update`。

然后运行你的第一次搜索：

```bash
sweepy --run
```

`--run` 使用你最后保存的配置执行搜索。要指定其他配置，使用 `sweepy --profile profiles/your_profile.yaml`。

不修改配置设置，仅对一次运行关闭重复检查：

```bash
sweepy --run --no-dedupe
sweepy --profile profiles/your_profile.yaml --no-dedupe
```

默认情况下，当不同职位板列出相同的规范化职位名称、公司和地点时，Sweepy 只保留一条职位。Model Context Protocol（MCP）的 `run_sweep` 工具接受 `deduplicate=false`，实现同样的单次运行覆盖。

Sweepy 还会隐藏早前搜索中的职位。可以重新查看它们，或从头开始：

```bash
sweepy --run --include-seen      # report earlier postings too
sweepy --run --reset-history     # forget them, then sweep
sweepy --reset-history           # forget the last profile's history and exit
```

在脚本中调用 Sweepy 时，无提示地创建或更新配置：

```bash
sweepy --setup --non-interactive \
  --name "Alex Rivera" \
  --titles "Technical Writer,UX Writer" \
  --location "New York, NY" \
  --resume C:/resumes/alex.pdf \
  --sources jobspy,openroles \
  --openroles-companies figma,stripe,notion \
  --timeout 120 --no-cache
```

Sweepy 在写入文件之前校验已启用的引擎。缺少必填字段会立即失败并给出原因。在交互式向导中，把 OpenRoles 的公司 slug 留空即可跳过该引擎。OpenRoles 只搜索指定名称的公司职位板。启用 OpenRoles 的非交互式配置仍需要 `--openroles-companies`。非交互式标志包括 `--sources`、`--jobspy-sites`、`--hirehunt-sources`、`--jobdrop-sites`、`--openroles-companies`、`--apify-actor`、`--timeout`、`--cache-ttl`、`--no-cache`、`--history-days`、`--no-history` 以及 `--job-tracking` / `--no-job-tracking`。

如果你更愿意用编辑器而不是提示与工具调用，就填写配置文件：

```bash
cp profiles/template_custom.yaml profiles/my_search.yaml
# replace the four REQUIRED values, then run the copy
sweepy --profile profiles/my_search.yaml
```

模板记录了每项设置及其默认值。在发现职位开始之前，Sweepy 会打印你的姓名、职位名称和地点。拼写错误会在第一行输出中显现。

不打开向导，把简历或笔记文件转换为 PDF：

```bash
sweepy --convert path/to/resume.docx
```

`--convert` 接受 `.docx`、`.doc`、`.txt`、`.md` 和 `.pdf` 文件。它把 PDF 写在原文件旁边，并打印最终路径。

一次搜索耗时 30 到 90 秒。Sweepy 在工作时打印进度：

1. **加载你的配置。**
2. **发现职位空缺**，覆盖你启用的平台。
3. **校验链接**，丢弃失效的链接。
4. **为每个角色评分**，依据你的简历。
5. **写出你的报告。**

## <a name="what-you-get"></a>你会得到什么

每次运行都把带日期戳的文件写入 `results/` 文件夹。早前的报告保持原样。通过 MCP 运行的搜索会在文件名中加入 `mcp`，例如 `paralegal_nyc_mcp_2026-10-27-223115.pdf`。日期戳跟随你机器的时钟。设置 `export.timezone` 可按另一个时区命名文件。

- **一份 PDF 报告。** 每个角色一张卡片，按匹配分数排序，含薪酬、福利和申请链接。
- **一个 CSV 文件。** 包含每张卡片的字段、完整的职位正文，以及八列职位跟踪数据，Sweepy 会把这些数据复制到后续搜索中。可用 Excel、Google Sheets 或 Notion 打开它。若想要更小的文件，把 `export.description_chars` 设为正数。被截断的正文末尾会注明省略的字符数。
- **一个 JSON 文件。** 同样的数据，采用其他工具可读取的格式。

打开[示例 PDF](../docs/sample_report.pdf)，或查看[第 1 页的图片](../docs/sample_report.png)。

## <a name="job-engines"></a>职位引擎

Sweepy 内置两个引擎，还可再下载四个。`ats` 引擎直接读取申请人跟踪系统（ATS）。所有引擎都在同一个适配器背后运行。无论哪个引擎找到职位，配置写法都相同。

| 引擎 | 可用性 | 抓取内容 | 代理 | User-Agent | 描述 |
|---|---|---|---|---|---|
| `jobspy` | 内置 | LinkedIn、Indeed、Glassdoor、ZipRecruiter、Google Jobs、Bayt、Naukri、BDJobs | 支持 | 支持 | 可切换 |
| `ats` | 内置 | Greenhouse、Ashby、Lever、Workable、BuiltinNYC | 不支持 | 不支持 | 始终 |
| `hirehunt` | 可下载 | LinkedIn、Indeed、Naukri、Shine、Internshala、Unstop，以及六个公司职位板（Google Careers、Amazon、Meta、Apple、Netflix、Microsoft） | 不支持 | 不支持 | 始终 |
| `openroles` | 可下载 | 你指定的 Greenhouse、Lever、Ashby、Workday 职位板 | 不支持 | 不支持 | 始终 |
| `jobdrop` | 可下载 | 33 个职位板，包括 Google、Wellfound、Workday、iCIMS、Dice、USAJobs | 支持 | 支持 | 可切换 |
| `apify` | 可下载 | 托管 actor，默认 LinkedIn | 由 actor 处理 | 由 actor 处理 | 取决于 actor |

`jobdrop` 报告与 JobSpy 的元数据冲突：它锁定 `curl-cffi<0.8`，而 JobSpy 要求 `curl_cffi>=0.16.2`。这个锁定已过时。`jobdrop` 在更新的库上运行正常，该库仍包含它使用的所有浏览器身份伪装配置（`safari17_2_ios`、`chrome120`、`chrome124`）。

直接对两者执行 `pip install` 仍会失败。`--install-engines all` 会把 `jobdrop` 排除在外。加上 `--allow-engine-conflicts` 可用受支持的方式安装它。Sweepy 安装 `jobdrop` 时用 `--no-deps`，然后解析它的其他依赖，因此 `curl_cffi` 保持为 JobSpy 的版本，两个引擎都能运行。

```bash
sweepy --install-engines all
sweepy --install-engines openroles,apify
sweepy --install-engines jobdrop --allow-engine-conflicts
```

那次安装之后，`pip check` 仍会报告 `jobdrop` 过时的版本上限。这条警告描述的是元数据，而不是运行中的代码。

也可以打开向导，选择 **Sweepy's Toolbox**，再选择 **Download job engines**。该界面列出每个引擎的职位板和安装状态。运行 `pip` 之前它会征求确认。创建配置时选中一个未安装的引擎，向导会提供同样的下载。未经你确认，Sweepy 从不执行安装。

### <a name="disk-footprint"></a>磁盘占用

在 Windows 与 Python 3.13 上实测：

| 安装项 | 磁盘上的包 | 说明 |
|---|---|---|
| 核心（`requirements.txt`） | 283 MB | 53 个包，包括 pandas、pymupdf 和 MCP SDK |
| `hirehunt` | +13 MB | 增加 rich 和 markdown-it-py |
| `openroles` | +0.3 MB | 仅用 Python 标准库 |
| `apify-client` | +14 MB | 增加 impit 和 more-itertools |
| `jobdrop` | +406 MB | 主要是 scipy（134 MB）、playwright（113 MB）、tls-client（93 MB）和 selenium（34 MB） |

完整安装所有兼容引擎约占 **310 MB**。再加上 `jobdrop`，在它下载浏览器之前总量约为 **716 MB**。

浏览器二进制文件位于 Python 环境之外，首次使用时才下载：

- Playwright 的 Chromium 构建约 **710 MB**（Chromium 加上它的无头 shell）。
- 完整的 Playwright 套件（包含 Firefox 和 WebKit）约 **1.2 GB**。
- `jobdrop` 用于隐身路径的 Camoufox 会在首次启动时下载一个打过补丁的 Firefox。

Sweepy 运行每个内置引擎都不需要浏览器。核心安装完全不需要这些空间。

随时列出引擎及其安装状态：

```bash
sweepy --list-engines
```

`openroles` 读取你指定的职位板，且需要公司 slug。`apify` 读取 `APIFY_TOKEN` 环境变量，并向你的 Apify 账户计费。

安装引擎并不会启用它。用以下三种方式之一把它加入配置：

1. **向导。** 运行 `sweepy`，选择 **Sweepy's Toolbox**，再选择 **Manage job engines**，然后选择 **Choose engines and settings**。已安装的引擎带有 `[installed]` 标记。勾选一个，向导会提示输入它的设置。
2. **编辑配置。** 加载配置，然后在审核界面选择 **Manage job engines**。
3. **命令行。** 在 `--sources` 中指定引擎，并提供它的设置：

```bash
sweepy --setup --non-interactive --profile profiles/your_profile.yaml \
  --sources jobspy,ats,jobdrop --jobdrop-sites linkedin,indeed,wellfound
```

每条路径都会在写入文件之前校验引擎设置。缺少某个值（例如 `openroles` 的公司 slug）时会失败并给出原因，而不是保存一个损坏的配置。

### <a name="choosing-boards"></a>选择职位板

配置向导的平台步骤列出 Sweepy 能搜索的所有职位板，并按读取它的引擎分组。全部 63 个职位板出现在同一处，而不只是内置的 13 个职位板。

| 分组 | 职位板 | 标记 |
|---|---|---|
| `jobspy`（8） | LinkedIn、Indeed、Glassdoor、ZipRecruiter、Google Jobs、Bayt、Naukri、BDJobs | `built in` |
| `ats`（5） | Greenhouse、Ashby、Lever、Workable、BuiltinNYC | `built in` |
| `hirehunt`（12） | LinkedIn、Indeed、Naukri、Shine、Internshala、Unstop、Google Careers、Amazon、Meta、Apple、Netflix、Microsoft | 安装前为 `needs download` |
| `openroles`（4） | Greenhouse、Lever、Ashby、Workday | `needs download`，且需要公司 slug |
| `jobdrop`（33） | Google、Wellfound、Workday、iCIMS、Dice、USAJobs、Handshake 等 | `needs download`，且与 JobSpy 冲突 |
| `apify`（1） | 通过 Apify actor 访问 LinkedIn | `needs download`，且需要 `APIFY_TOKEN` |

每行显示它的引擎和安装状态，例如 `Indeed  [jobspy · built in]` 或 `Wellfound  [jobdrop · needs download]`。选定之前你就能看到标记。勾选一个来自尚未本地安装的引擎的职位板，向导会打印安装它的命令。已安装的引擎则显示 `installed`。重新打开已保存的配置时，其当前职位板已处于勾选状态。Sweepy 会保留配置中来自未安装引擎的职位板，在安装完成之前，搜索会跳过该引擎并发出警告。

### <a name="engine-settings"></a>引擎设置

```yaml
sources:
  enabled: [jobspy, ats, openroles]
  greenhouse:
    discovery: broad
    concurrency: 20
  openroles:
    ats: [greenhouse, lever, ashby, workday]
    companies: [figma, stripe, notion]
  jobdrop:
    sites: [linkedin, indeed, google, glassdoor]
    headless: true
    fetch_descriptions: true
    proxies: ["user:pass@host:port"]
cache:
  enabled: true
  ttl_seconds: 3600
history:
  enabled: true
  retention_days: 4
  match: url+role
  path: null
orchestrator:
  timeout_per_source_seconds: 180
  circuit_breaker:
    failure_threshold: 5
    cooldown_seconds: 30
```

较旧的配置仍然可用。`sources.jobspy` 下的职位板布尔值仍可分别开启和关闭各个 JobSpy 职位板。任何没有 `sources.enabled` 列表的配置都默认使用 JobSpy 加上内置 ATS 读取器。

- **描述默认开启。** 评分用职位文本与你的简历比对。只有在你接受匹配质量变差以换取更快搜索时，才把 `fetch_descriptions` 关掉。
- **Greenhouse 可按需读取更广的职位板列表。** `sources.greenhouse.boards` 指定你想要的职位板。设置 `sources.greenhouse.discovery: broad` 会同时扫描 `data/sources/greenhouse_slugs_broad.txt` 中随包附带的 619 个 slug 列表，Sweepy 还会追加配置中已指定的职位板。`sources.greenhouse.concurrency` 设置 Sweepy 一次读取多少个职位板：broad 模式为 20，其他情况为 1。广泛探测按设计会产生大量 HTTP 404 响应。Sweepy 用一条警告报告失败数量和前十个 slug，而不是每个职位板一行。
- **代理按引擎逐一启用。** 向导从文件读取代理，或接受一条内联代理；输入时隐藏密码，并且从不打印内容。`hirehunt` 不提供代理选项，因此当配置中设置了代理时，Sweepy 会记录一条警告。
- **缓存默认开启。** 使用相同引擎和设置的重复查询会在一小时内返回之前的结果。用 `cache.enabled: false` 清除，或缩短 `ttl_seconds`。
- **超时在边界处停止。** Python 无法终止已阻塞在库调用内部的线程。Sweepy 停止等待并继续执行，每个库在底层应用各自的 HTTP 超时。
- **熔断器跳过失败的引擎。** 连续五次失败后，Sweepy 在 30 秒内停止调用该引擎，并在 `skipped_sources` 中报告它。

### <a name="reported-postings"></a>已报告的职位

Sweepy 记录它报告的每条职位，并在下一次搜索中跳过同一条职位。记录存放在 `~/.sweepy/history.db`，按配置隔离。设置 `SWEEPY_HISTORY_PATH` 可存到别处。向导的 **Sweep Settings** 界面提供开关和保留窗口。

```yaml
history:
  enabled: true
  retention_days: 4   # 0 reports every posting on every run
  match: url+role     # url (strict) or url+role (default)
  path: null          # null uses ~/.sweepy/history.db
```

- **保留期是一种重新报告节奏。** Sweepy 抑制一条职位，直到 `retention_days` 过去，然后再次报告它。一条持续在线的职位最多每四天返回一次。
- **默认匹配较宽松。** Sweepy 先剥离跟踪参数和片段，再比较规范 URL。之后回退到规范化的职位名称、公司和地点，因此在其他职位板上的重新发布也算同一个角色。设置 `match: url` 可要求规范 URL 匹配。
- **只有在线职位计入。** 职位在其 URL 通过校验后才进入历史记录。失效链接永远不会变得不可见。
- **MCP 调用方得到同样的默认行为。** `run_sweep` 报告 `previously_seen_count` 和 `new_count`。传入 `include_seen=true` 可查看早前的职位，或调用 `clear_history` 忘掉它们。`create_profile` 接受 `history_config`。

### <a name="adding-another-engine"></a>新增另一个引擎

1. 创建 `engine/adapters/<name>_adapter.py` 并继承 `ScraperAdapter`。
2. 设置 `name`、三个 `supports_*` 标志、`default_concurrency` 和 `library`。
3. 编写 `preflight()` 校验配置，编写 `scrape()` 返回 DataFrame。
4. 在 `engine/adapters/__init__.py` 中注册它。
5. 在 `engine/engines.py` 中描述它，让向导能显示并安装它。
6. 在 `engine/sweep_config.py` 中加入配置块，并在 `_ENGINE_PROMPTS`（`engine/config.py`）中加入提示。
7. 把包加入 `requirements-engines.txt` 和 pyproject 的 extras。
8. 单独测试该适配器，然后在一次搜索中只启用它。

其余工作由编排器负责。它按名称分发，并强制执行超时。返回的任何数据帧都会被规范化。

## <a name="connect-to-antigravity"></a>连接 Antigravity

Sweepy 通过两部分在 Antigravity 桌面应用里运行。MCP 服务器提供搜索工具，`/sweepy` 技能添加聊天快捷方式。

**让 agent 来做。** 打开 Antigravity，开始一次聊天，然后发送这条消息：

> 帮我配置 Sweepy。注册用 `python <PATH_TO_SWEEPY>/server.py` 运行的本地 MCP 服务器，并从 `<PATH_TO_SWEEPY>/skills/sweepy` 安装技能。

Antigravity 会写入配置，并把技能文件添加到你的系统中。

**手动配置。** 按顺序完成以下步骤。

1. **添加 MCP 服务器。** 打开 **设置**（齿轮图标）> **MCP Servers**，添加名为 `sweepy` 的服务器。命令填 `python`，参数填 `["<PATH_TO_SWEEPY>/server.py"]`。
2. **安装技能。** 打开你的技能文件夹：Windows 上是 `%USERPROFILE%\.gemini\config\skills`，macOS 上是 `~/.gemini/config/skills`。把 `sweepy` 文件夹从 `skills/sweepy` 复制到该目录，然后重启 Antigravity。
3. **运行搜索。** 在聊天里输入 `/sweepy`。想用日常说法提出需求时，发送这条请求：*"用我 `C:/path/to/resume.pdf` 的简历创建一个搜索远程技术写作职位的配置，并运行第一次搜索。"*

Antigravity 调用与其他宿主相同的 MCP 工具。[MCP 集成](https://pvega62.github.io/software/docs/sweepy/reference/mcp-integration)页面介绍 Claude Desktop、VS Code 和完整的工具列表。

## <a name="agent-judgment"></a>Agent 判断

Sweepy 按共同词汇给职位评分，这种评分不调用模型，也不使用网络。相同的输入产生相同的分数，它衡量的是措辞，而不是契合度。MCP 服务器把 agent 评估视为预期路径。

`run_sweep` 不调用模型。它返回 `assessment_mode: "agent"`、`assessment_required: true` 和 `assessed_count: 0`。流程继续调用 `get_jobs`，对每个角色与简历做独立评估，然后 `submit_judgments`，最后 `render_report`。把每个判断放进一个 `judgments` 列表，可让 24 个角色的评估只需一次调用。已评估的卡片显示 `NN% MATCH`。未评估的卡片保留 `NN% KEYWORD OVERLAP`。

`get_jobs` 返回 `resume_documents`，包含每条简历 track 的解析文本。评判那段文本，而不是配置里的 `must_have_skills` 和 `synonyms`，它们只用于确定性的关键词匹配。像招聘人员那样读这份文档：可迁移的技能、每条要点背后的范围和资历、领域、工具，以及它证明的成果。然后按职位的申请人跟踪系统解析它的方式打分。解析器在标准 Experience 或 Skills 部分找到的词条算作证据。同样的词条如果位于表格、页眉、页脚、图片或双栏侧栏中，可能永远到不了人眼前，因此权重更低。当申请 URL 暴露 ATS 类别时，Sweepy 会指出它，判断结果也会记录解析器会丢掉什么。

`match_pct` 衡量任职资格，因此用工安排不计入其中。兼职工时、合同性质和地点属于 `concerns`。候选人能胜任的角色，只有在技能或经验与职位明示要求不符时才会失分。这样排序衡量的是契合度，而不是可到岗性。

两面都要评估。`alignment` 陈述亮点，即候选人契合的最强证据。`concerns` 陈述对候选人不利的因素。例如缺少某项资格、任职年限的空白、兼职工作时间、合同期限、需要搬迁的地点，或低于底线的薪酬。报告在要求那一行下方用一行打印这一对内容，CSV 会增加 `concerns` 列。仅关键词的运行会用简历缺少的职位关键词填充 `concerns`。

`submit_judgments` 还接受 `portfolio_highlight`。传入该职位对应的作品集作品，卡片会把它们作为 **Highlight** 打印。没有提交亮点的卡片会列出 Sweepy 找到的作品。

## <a name="portfolio-support"></a>作品集支持

Sweepy 每次搜索读取一次作品集，并在每张卡片上列出其中的作品。它在创建配置之前收集作品集。给它一个在线 URL，或本地 `.pdf`、`.docx`、`.md`、`.txt` 或 `.html` 文件。当你针对不止一类角色时，为每条简历 track 传入一个条目。

```yaml
portfolio:
  # One entry per resume track. An entry without `track` serves every track.
  sources:
    - track: "UX Writer Resume"
      url: "https://example.com/work"
    - track: "Technical Writer Resume"
      path: "C:/portfolios/technical-writing.pdf"
  pieces_per_card: 3
```

Sweepy 抓取在线作品集以读取其标题和链接。当页面阻止请求时，卡片保留链接并跳过作品列表。PDF 卡片显示作品集及其作品。CSV 和 JSON 导出会加入 `portfolio_url`、`portfolio_pieces` 和 `portfolio_highlight`。

要把作品集附加到已保存的配置，可从 MCP 调用 `set_portfolio`，或回答向导的作品集步骤。无交互设置接受 `--portfolio` 和 `--portfolio-track`。

`render_report` 接受 `playbook` 参数，用于结尾的策略框。用平实的文字书写。Sweepy 会转义 & 符号，并把换行转成折行。`**bold**` 渲染为粗体文本，尖括号变成纯文本。Sweepy 把 playbook 与该会话一起保存，后续渲染会复用它，而不是使用自动生成的内容。开始新的搜索会清除它。

在 `agent` 模式下，`render_report` 拒绝生成混合报告。它返回一个错误，列出未评估的职位 id。助手读取该列表，并为缺失的 id 提交判断。需要仅关键词报告的配置设置 `report.assessment: "keyword"`。命令行运行也会报告关键词重合度，因为没有 agent 提供判断。设置 `SWEEPY_REQUIRE_JUDGMENTS=1`，可让这道门同时约束每个配置和 `export_report`。

一次实时搜索会抓取职位板一分钟或更久。MCP 服务器在后台运行它。`run_sweep` 最多等待 45 秒，然后返回 `sweep_status: "running"` 和一个 `job_id`。轮询 `get_sweep_status`，直到它报告 `completed`。即使客户端断开，搜索也会继续运行。对于工具超时更紧的宿主，设置 `SWEEPY_MCP_WAIT_SECONDS` 可降低等待时间。

- MCP 创建的配置使用内置引擎，加上已安装且通过默认配置检查的可选引擎。
- 提供 `sources_config` 可明确选择引擎。
- OpenRoles 需要每家公司的 slug。
- Apify 需要明确启用，因为它可能产生费用。

助手可以用它的搜索工具核验结果并填补缺口。它应把跳过的来源和职位与雇主的招聘页面对照检查。它应补充经核验的遗漏项，并把无法访问的职位标为未核验。当无法确认覆盖完整时，它必须说明这一点。

设置步骤见 [MCP 集成](https://pvega62.github.io/software/docs/sweepy/reference/mcp-integration)。

每个 MCP 工具都发布只读、破坏性、幂等和开放世界提示。兼容的宿主在调用工具之前会读取这些提示。

## <a name="before-you-upload-your-resume"></a>上传简历之前

你的排版决定 Sweepy 能读到多少文本。双栏设计、表格或扫描页面会打乱引擎读到的文本，并降低你的分数。单栏清晰的真实文本提取最可靠，申请人跟踪系统也以同样的方式读取它。

第一次搜索之前，先读[简历格式建议](https://pvega62.github.io/software/docs/sweepy/guides/resume-tips)。

## <a name="documentation"></a>文档

### <a name="getting-started"></a>入门

- [简介](https://pvega62.github.io/software/docs/sweepy/intro)
- [安装](https://pvega62.github.io/software/docs/sweepy/installation)
- [配置](https://pvega62.github.io/software/docs/sweepy/setup)
- [运行第一次搜索](https://pvega62.github.io/software/docs/sweepy/first-sweep)
- [理解你的结果](https://pvega62.github.io/software/docs/sweepy/understanding-results)

### <a name="resumes-and-match-scores"></a>简历与匹配分数

- [简历格式建议](https://pvega62.github.io/software/docs/sweepy/guides/resume-tips)
- [评分与限制](https://pvega62.github.io/software/docs/sweepy/guides/scoring-and-limits)

### <a name="command-and-configuration-reference"></a>命令与配置参考

- [命令与标志](https://pvega62.github.io/software/docs/sweepy/reference/cli-reference)
- [配置参考](https://pvega62.github.io/software/docs/sweepy/reference/configuration-reference)
- [职位来源与平台](https://pvega62.github.io/software/docs/sweepy/reference/sources-and-platforms)
- [MCP 集成](https://pvega62.github.io/software/docs/sweepy/reference/mcp-integration)
- [MCP 工具参考](https://pvega62.github.io/software/docs/sweepy/reference/mcp-tool-reference)
- [开发者参考](https://pvega62.github.io/software/docs/sweepy/reference/developer-reference)

## <a name="legal-and-responsible-use"></a>法律与负责任使用

Sweepy 抓取公开职位板和职位板 API。抓取可能违反某些平台的服务条款。依赖该工具之前，请审阅那些条款。

- 把它用于**个人求职**。不要用于批量收集或再分发。
- 遵守速率限制。Sweepy 发送礼貌的 User-Agent，并在请求之间加入短暂延迟。用 `SWEEPY_SOURCE_DELAY` 环境变量提高延迟。
- Sweepy 不提供法律建议。

抓取通过 [`python-jobspy`](https://github.com/Bunsly/JobSpy) 运行；当你安装它们时，也通过 [`hirehunt`](https://pypi.org/project/hirehunt/)、[`openroles`](https://pypi.org/project/openroles/)、[`jobdrop`](https://pypi.org/project/jobdrop/) 和 [Apify](https://apify.com/) 运行。每个项目都发布自己的使用说明。Google Jobs、LinkedIn、Indeed 和 Glassdoor 的抓取可能违反那些平台的服务条款。Apify 把请求转移到托管服务。这不会改变法律风险。

## <a name="license"></a>许可证

Sweepy 以 [MIT 许可证](../LICENSE) 发布。
