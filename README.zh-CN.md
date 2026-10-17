<p align="center"><img src="docs/assets/banner.svg" alt="Photo Location Workflow · 看图找地点，保留证据" width="100%"></p>
<p align="center">
<a href="https://github.com/xudaniel/photo-location-workflow/actions/workflows/tests.yml"><img src="https://github.com/xudaniel/photo-location-workflow/actions/workflows/tests.yml/badge.svg" alt="自动测试"></a>
<a href="https://github.com/xudaniel/photo-location-workflow/releases"><img src="https://img.shields.io/github/v/release/xudaniel/photo-location-workflow?color=24795c" alt="最新版本"></a>
<img src="https://img.shields.io/badge/Python-3.10%2B-386b58" alt="Python 3.10+">
<a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-d9bd70" alt="MIT 许可"></a>
</p>
<p align="center"><a href="README.md">English</a> · <strong>简体中文</strong><br>
<a href="#快速开始">快速开始</a> · <a href="docs/commands.md">命令手册</a> · <a href="docs/case-studies.md">真实案例</a> · <a href="CHANGELOG.md">更新记录</a></p>

# 找到地点，也留下依据。

**Photo Location Workflow** 把照片定位研究整理成一条可复核的流程：整图反向搜索、独特局部裁切、官网地址核对、街景对照，以及证据报告。

本地中英文网页工作台和命令行共用图片准备、记录、文件完整性检查与报告。**最终判断由审阅者完成**。可选研究助手通过 OpenAI 分析图片、生成搜索词并联网整理假设；手动调查和离线演示无需模型密钥。

```mermaid
flowchart LR
    A[原照片] --> B[整图反向搜索]
    B --> C[辨识度高的局部]
    C --> D[官网名称与地址]
    D --> E[街景或游客360全景]
    E --> F[人工核对与证据记录]
    F --> G[离线HTML或PDF报告]
```

## 功能一览

| 功能 | 作用 |
| --- | --- |
| 本地网页工作台 | 拖放照片、鼠标框选、中英文切换、候选地点、双图证据对照与一键导出。 |
| 图片准备 | 校正 EXIF 方向、移除元数据、保留输入文件、记录校验和。 |
| 独特局部裁切 | 保存原始分辨率裁切及最近邻放大图，使用独立目录防止覆盖原图。 |
| Google Lens 辅助 | 默认只显示手动操作说明；显式加 `--upload` 后使用可见、临时 Chromium 会话。 |
| 结构化证据 | 记录候选、地址、来源、拍摄年／月、提供者、匹配、不确定与反例。 |
| 保留复审历史 | 修订判断时必须说明理由，旧判断仍保留。 |
| 完整性检查 | 发现文件缺失、内容变化、越界路径和无效候选引用。 |
| 结论等级约束 | 记录官网地址和视觉证据后，才允许采用较高把握等级。 |
| 双图细节对照 | 同步缩放、按相对比例拖动，两侧分别框选对应区域，保存编号并点击定位。 |
| 双图对比报告 | 导出可离线查看的 HTML 和支持中文的 PDF，附来源、并排图片及复审记录。 |
| 可选 geo-sleuth 工作台 | 网页后台预处理、可选 OCR、实时日志、取消与恢复、辅助图预览、候选反证与逐条审阅；保留原有证据核对流程。[安装与限制](docs/geo-sleuth.md#简体中文)。 |

## 手机也能用

手机与电脑连接同一可信 Wi-Fi，安装 `mobile` 扩展后运行 `photo-locate ui --lan`，扫描电脑工作台二维码或输入连接码。支持手机上传照片／HEIC、裁切、后台调查与报告查看。电脑需保持运行，文件保存在电脑。[完整连接说明](docs/mobile.md#简体中文)。

## 地图核对（main / 下个版本）

保存实际查看的街景参数与拍摄日期，固定候选坐标和 Place ID，结合卫星、地形及其他地图核对；导出 Earth 可用的候选 KML，重开已存视角，并将修订历史写入 HTML／PDF。**地图链接无需 Google 密钥，来源内容仍需实际人工查看。**

完整操作、重开模式和覆盖限制见[中英文地图核对指南](docs/maps.md)。新增功能已在 `main`，最新发行标签仍是 v1.3.0；已有源码目录可这样试用：

```bash
git switch main
git pull --ff-only
python -m pip install -e '.[pdf]'
photo-locate ui
```

## 本地工作台

![本地网页工作台，使用虚构建筑演示](docs/assets/workbench-preview.jpg)

安装后运行 `photo-locate ui`，浏览器会打开本机工作台。点击“体验离线演示”即可试用，无需上传照片或申请密钥。

## 对应细节，逐处核对

![双图细节对照与编号标注，采用离线虚构案例](docs/assets/comparison-preview.jpg)

为证据附上参考图片后，点击“对照细节”即可打开双图工作区：

- 使用缩放按钮、滑条或 Ctrl/⌘ + 滚轮同步缩放；开启“同步拖动”后，两侧按各自图片的相对比例移动。普通滚轮用于滚动页面。
- 切到“框选细节”，在原图和参考图分别框选同一处特征，填写说明并保存。也可直接输入两侧 `X、Y、W、H` 像素坐标。
- 点击编号会同时定位并放大两侧对应区域。切换候选或证据，可以分别检查不同参考影像。
- HTML／PDF 同时输出编号总览、每组局部对照及原始坐标；HTML 编号链接可跳转到对应细节。
- 移除误标会保留原坐标和操作历史，之后不会复用该编号。新增或移除标注后，结论恢复为候选，需重新审阅。

框选由审阅者建立对应关系，程序不自动判断两处特征是否相同。标注保存在 `case.json`，原图和参考图文件保持不变。每条附图证据最多支持 100 组标注；旧记录无需迁移。

## 报告预览

下图来自离线虚构建筑演示，仅展示双图版式，不代表真实地点识别。

![合成案例的双图报告预览](docs/assets/report-preview.jpg)

## 快速开始

### 安装 v1.3.0

需要 **Python 3.10+**。CI 覆盖 Ubuntu 的 Python 3.10、3.12、3.13，以及 macOS 15、Windows 2025 的 Python 3.12。

```bash
git clone --branch v1.3.0 https://github.com/xudaniel/photo-location-workflow.git
cd photo-location-workflow
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[pdf]'
```

Windows PowerShell 使用 `python -m venv .venv` 和 `.venv\Scripts\Activate.ps1`。只需要 HTML 时，执行 `python -m pip install -e .` 即可。

也可以从 [Releases](https://github.com/xudaniel/photo-location-workflow/releases/latest) 下载 wheel，执行 `python -m pip install /path/to/photo_location_workflow-1.3.0-py3-none-any.whl`。上述方式直接从 GitHub 安装，不依赖 PyPI 发布。

### 打开本地界面

```bash
photo-locate ui
```

1. 拖放或选择照片，在照片上框选独特细节，再保存局部。
2. 保存搜图图片，另行打开 Google Lens 手动上传，记录候选地点与官网地址。
3. 添加来源、拍摄年／月、提供者和参考图片，逐条记录匹配或反例；界面会并排显示原图和参考影像。
4. 保留复审理由，保存结论，下载 HTML 或 PDF 报告。

工作台仅监听 `127.0.0.1`，共用 CLI 的校验规则与 `case.json`；无需 Node、前端构建或模型密钥。`--cases` 可指定调查目录，`--port` 更换端口，`--no-open` 关闭自动打开浏览器。运行期间不要从其他进程修改同一调查。关闭终端或按 Ctrl-C 停止服务，之后可重新打开继续。

### 不上传照片，先跑一个离线演示

在工作台点击“体验离线演示”，或执行：

```bash
photo-locate demo --case cases/demo-v1
photo-locate check cases/demo-v1
photo-locate report cases/demo-v1
```

用浏览器打开 `cases/demo-v1/report.html`。演示采用程序绘制的**虚构建筑**，全程离线，结论保留为候选。再次运行时选择新的空目录。wheel 安装也包含演示和完整网页。仓库不附私人原照片或第三方地图影像。

## 可选半自动研究助手

```bash
photo-locate ui --env-file /path/to/your/ignored.env.local
```

也可在启动服务器的环境中配置 `OPENAI_API_KEY`。可选 `OPENAI_MODEL` 更换模型，默认 `gpt-5.6-terra`。模型需支持图片输入、Structured Outputs 和 Responses API 的 `web_search`。密钥只在本地服务端读取，不写入浏览器、调查记录或报告。

1. 写下已核对的线索，选择原图和原始裁切（最多四张）。笔记停笔后自动保存，也可点击“保存进度”。
2. 确认发送范围后点击“分析照片并检索”。选定图片先缩至最长边 1600 像素，重新编码为 JPEG，再与该次笔记发送给 OpenAI；第二步将分析结果用于文字联网检索。
3. 查看观察、搜索词、待核对问题、带来源的地点假设。只有出现在实际搜索返回来源中的链接可附到建议候选；来源本身仍须人工核对。
4. 点击“加入候选记录”后才生成普通候选。助手不会自动新增“官网吻合”或街景证据，也不会提高结论等级。
5. 勾选已处理问题，补充笔记。分析完成后即保存检查点，检索失败可继续而不重做分析；服务器关闭后，未完成任务会标记为中断，可手动继续。

新一轮研究分两步，各调用一次模型；一次联网请求最多允许两次搜索工具调用。手动继续可能为未完成步骤再产生一次请求。继续操作只补做未保存的步骤，使用该轮原有图片和笔记；补充新线索后可新建一轮。图片变化会阻止旧轮继续。请求超时不代表远端没有计费；程序不会自动重试。API 额度不足、速率限制、鉴权错误会明确显示，并保留已保存结果。

`case.json` 的可选 `research` 字段保存笔记、问题完成状态、历史轮次、输入图片校验和、模型和用量。研究建议留在工作台与本地记录中；正式证据报告仅纳入已建立的候选与人工审阅记录。联网搜索是文字检索，Google Lens 反向搜图与街景仍需另行实际操作。启用助手会产生 OpenAI API 费用；余额不足时，手动调查功能仍可使用。

## 一次完整调查

### 1 · 准备图片并搜索整张场景

```bash
photo-locate init /path/to/photo.jpg --case cases/trip
photo-locate lens cases/trip
```

`init` 保存方向已校正、移除元数据的无损 PNG 副本，并记录原文件的 SHA-256。调查记录不保存原图的绝对路径。`lens` 显示准备好的文件路径和 Google 地址，默认**不上传**。

如需可选的浏览器辅助上传：

```bash
python -m pip install -e '.[browser]'
playwright install chromium
photo-locate lens cases/trip --upload
```

`--upload` 会把选定的副本发送给 Google。请在可见浏览器中检查结果，再回交互终端按 Enter，程序保存本地截图及可见链接。遇到登录、同意弹窗、验证码或界面变化，由你手动处理或停止；程序不绕过验证码，也不调用未经公开的 Lens 接口。手动上传始终是备用方式。

### 2 · 搜索辨识度最高的局部

窗组、招牌、入口、特殊岩块和瀑顶通常比普通森林更有价值。以下坐标仅作语法示例，请按自己的图片调整：

```bash
photo-locate crop cases/trip --box 0,100,200,300 --label facade --scale 4
photo-locate lens cases/trip --asset assets/crops/facade/native.png --upload
```

坐标是**校正方向后副本**中的 `x,y,width,height`。命令返回原始裁切和放大图路径。放大只展示已有像素，不能恢复模糊路牌和车牌；车辆登记地也不能证明拍摄地。

### 3 · 记录候选并核对官网地址

下面用公开景点演示。只有实际查看了对应页面、确认信息后，才应为自己的调查记录 `official` 匹配。

```bash
photo-locate candidate cases/trip \
  --name '銚子大滝 / Chōshi Ōtaki' \
  --address '青森県十和田市大字奥瀬字奥入瀬' \
  --url 'https://www.tohokukanko.jp/attractions/detail_1573.html'

photo-locate evidence cases/trip --candidate c1 --kind official \
  --url 'https://www.tohokukanko.jp/attractions/detail_1573.html' \
  --verdict match --notes '已在官方旅游页面核对景点名称及所在地。'
```

候选记录包含已编码的 Google 地图链接。来源分类、页面内容与匹配判断均由审阅者提供；工具不能自动证明网站上的说法真实。

### 4 · 核对街景或游客全景

在 Google 地图选择 **Street View & 360°**。优先比较稳定特征：窗组、灯、门框、道路走向、挡墙、路牌、山形、岩壁层理。区分 Google 官方道路街景与游客上传的全景，也要记录影像月份。

将下例的链接、月份、截图和备注替换为你实际查看的材料：

```bash
photo-locate evidence cases/trip --candidate c1 --kind streetview \
  --url 'https://www.google.com/maps/YOUR_OBSERVED_VIEW' \
  --captured 2018-10 --provider '游客360全景；贡献者姓名' \
  --image /path/to/observed-view.png --verdict match \
  --notes '瀑顶中央岩块、右侧层状岩壁和左岸树木位置对应。'
```

只显示年份时用如 `--captured 2025`，无日期时用 `--captured unknown`。看不清用 `unclear`，发现不符用 `contradiction`。工具导入截图的去元数据副本，并记录校验和。

### 5 · 复审、检查、形成结论

新材料改变判断时，修订记录而不抹去旧意见：

```bash
photo-locate review cases/trip --evidence e2 --verdict unclear \
  --reason '观察点太远，暂时不能核对这块岩石。'
photo-locate check cases/trip
```

实际补齐所需证据后：

```bash
photo-locate conclude cases/trip --candidate c1 --level confirmed \
  --note '官网地址及已核对全景一致；精确相机站位尚未测量。'
photo-locate report cases/trip
photo-locate report cases/trip --format pdf
```

新增或复审证据后，旧结论会退回 `candidate`，需要重新判断。上面的 `unclear` 示例必须经进一步有依据的复审，或补充另一份匹配全景，才能用于支持 `confirmed`。

## 把握等级代表审阅决定

| 等级 | 程序检查的要求 |
| --- | --- |
| `unknown` | 尚未确定地点。 |
| `candidate` | 工作候选，证据仍不足。 |
| `high` | 官网地址匹配记录 + 附图的视觉匹配 + 本地文件完整 + 无未解决反例。 |
| `confirmed` | 在 `high` 基础上，另有附图且匹配的街景／360°记录。 |

程序检查的是**证据记录的结构与完整性**，不会替代事实判断。SHA-256 能发现文件变化，不能证明照片真实或地点正确。没有全景覆盖时，保留 `high` 或更低等级并说明限制。

## 报告与中文字体

- **HTML：**图片内嵌、响应式排版、离线查看、支持打印；包含双图对照、证据标签、提供者、日期及复审历史。
- **PDF：**双图、可点击来源、中日文文字、裁切附页及嵌入字体；需要 `pdf` 扩展。
- **字体：**检测 macOS Arial Unicode、Linux 文泉驿及 Windows 微软雅黑常见路径；需要时使用 `--font-path /path/to/font.ttf` 或 `.ttc`。Ubuntu/Debian 可安装 `fonts-wqy-microhei`。请确保选定字体覆盖报告所用字符。
- **输出：**默认放在调查目录的 `report.html`／`report.pdf`；`--output` 自动创建父目录，禁止输出到调查图片目录或错误扩展名。

分享前请打开 PDF 检查文字、图片与分页。报告包含你附加的图片、备注和链接。

## 本地数据与隐私

```text
cases/trip/
├── case.json                    # 候选、证据、判断、校验和
├── assets/
│   ├── source.png               # 去元数据并校正方向的副本
│   ├── crops/facade/            # native.png + pixels.png
│   └── evidence/e1.png          # 附加参考图（如有）
├── report.html
└── report.pdf
```

手动工具无需付费模型密钥；仅在明确传入 `--env-file` 时读取文件中的 `OPENAI_API_KEY` 和 `OPENAI_MODEL`，也可从进程环境读取。程序不使用日常浏览器登录配置。调查和截图留在本地；主动启动研究助手时，选定图片、该轮笔记与分析结果会发送给 OpenAI，生成的搜索词用于联网检索。移除元数据**不会**遮挡画面中的人脸、车牌和文字。`.gitignore` 排除常见调查／输出目录及栅格图／PDF；自定义路径仍应在提交前自行检查。

本项目面向公开景点与场景对照，不做人物身份识别、模糊文字恢复或私人实时行踪推断。

## 兼容性与限制

- **0.1.0 的 schema-v1 调查仍可读取。** 旧文件没有校验和时提示警告，不补称过去已通过校验；新裁切和证据使用独立目录。
- 同一调查请**一次只由一个进程修改**；JSON 存储不是并发数据库。
- Google 界面可能变化，搜索会话链接可能过期。浏览器助手需要显示环境和交互终端；CI 不访问真实 Google 服务。
- 街景覆盖因地点而异。日期由审阅者录入；Google AI 摘要和结果排名只能作为线索。

## 开发与测试

```bash
uv sync --locked --extra dev --extra pdf --extra release
uv run --locked --extra dev --extra pdf pytest -q
uv run --locked --extra release python -m build
uv run --locked --extra release python -m twine check dist/*.whl dist/*.tar.gz
```

CI 执行多版本测试、构建 wheel／源码包、检查包元数据，并验证已安装 wheel 的命令。测试使用合成图片，不访问 Google。参见 [贡献指南](CONTRIBUTING.md)、[完整命令手册](docs/commands.md)、[AI 助手执行规则](docs/agent-workflow.md)和[公开案例](docs/case-studies.md)。

## 可复现开发与发行

`uv.lock` 锁定依赖，`--locked` 会拒绝过期锁文件。CI 在三个系统上运行合成数据测试，并独立安装 wheel 检查演示和网页资源。Linux CI 强制验证中文 PDF；其他系统缺少字体时会明确跳过该项。

推送与包版本一致的 `vX.Y.Z` 标签后，自动发行工作流先运行完整 CI，再构建 wheel、源码包和 SHA-256 清单并发布 GitHub Release。参见 [贡献指南](CONTRIBUTING.md)；仓库附中英文问题表单与 PR 模板。

## 许可与致谢

代码及原创说明采用 **[MIT License](LICENSE)**，© 2026 Daniel Xu。第三方照片、字体、地图影像和商标归各自权利人；本项目并非 Google 官方产品。浏览器辅助采用公开的 [Playwright 文件上传 API](https://playwright.dev/python/docs/input#upload-files)。
