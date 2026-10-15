# Photo Location Workflow · 看图找地点

把“看起来像某地”变成一条可以复核的证据链。

**整图反向搜索 → 关键局部搜索 → 官网地址 → Google 地图街景/360° → 对比报告。**

这是本地运行的 Python 命令行工具。它负责图片准备、可选的 Google Lens 浏览器上传、候选与证据记录、结论约束，以及双图 HTML/PDF 报告。**视觉判断由使用者或连接此工具的 AI 助手完成**，程序不会把相似搜索结果自动判为拍摄地点，也不需要付费模型 API。

English: A local, evidence-first photo-location workflow. Prepare metadata-free images, crop distinctive details, optionally upload to Google Lens in a visible browser, review authoritative addresses and Street View, and export a comparison report. Human review is required; this is not an automatic geolocation model.

## 安装

需要 Python 3.10+。

```bash
git clone https://github.com/xudaniel/photo-location-workflow.git
cd photo-location-workflow
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[pdf]'
```

Windows 使用 `.venv\Scripts\activate`。仅生成 HTML 时，安装 `pip install -e .` 即可。

可选的可视浏览器助手：

```bash
python -m pip install -e '.[browser]'
playwright install chromium
```

## 一次完整调查

### 1. 整图搜索

```bash
photo-locate init /path/to/photo.jpg --case cases/trip
photo-locate lens cases/trip
```

第一条命令保存一份已校正方向、移除 EXIF/GPS 的无损 PNG 副本，原文件不变。第二条命令只显示 Google 地址和待上传副本路径，**不会发送图片**。到 Google 点击“Search by image”，上传副本。

如果希望程序打开独立 Chromium 并尝试上传，显式执行：

```bash
photo-locate lens cases/trip --upload
```

`--upload` 会将选定图片发送给 Google。浏览器保持可见，待你检查结果并按 Enter 后，保存本地搜索链接和截图；搜索结果仍标为未验证。遇到登录、同意弹窗、验证码或界面变化，由你在浏览器完成或停止。程序不绕过验证码，不调用未经公开的 Lens 接口。Google 界面随时可能变化，手动上传是备用路径。

### 2. 找最独特的局部

建筑立面、窗组、门框、招牌、瀑顶岩块通常比整片森林更有辨识度。下面坐标仅为语法示例，需按自己的图片修改：

```bash
photo-locate crop cases/trip --box 0,100,200,300 --label facade --scale 4
photo-locate lens cases/trip --asset assets/facade.png --upload
```

坐标为**校正方向后的图片**中的 `x,y,width,height`。工具同时保存原始像素裁切和最近邻放大图。放大不会创造文字细节；模糊车牌应记为“看不清”。车牌登记地也不等于拍摄地。

### 3. 核对官网与地址

找到强候选后打开其官网或可靠旅游机构页面，核对名称、完整地址，并记录**实际看到的内容**。下面用公开景点演示格式，不代表工具已替你的照片完成核对。

```bash
photo-locate candidate cases/trip \
  --name '銚子大滝' \
  --address '青森県十和田市大字奥瀬字奥入瀬' \
  --url 'https://www.tohokukanko.jp/attractions/detail_1573.html'

photo-locate evidence cases/trip --candidate c1 --kind official \
  --url 'https://www.tohokukanko.jp/attractions/detail_1573.html' \
  --verdict match --notes '在官方旅游页面核对了景点名称与所在地。'
```

`candidate` 输出的 `maps_url` 可直接打开 Google 地图。`official` 是你对来源的分类，工具不能替你判断页面真实性。

### 4. 街景 / 360° 交叉验证

在地图选择“Street View & 360°”。建筑场景核对窗户、圆灯、门框、道路走向、挡墙、树带、路牌、山形；自然景点核对岩壁、瀑顶分段等稳定地形。保存**自己实际查看过的**截图和该视角链接。

记录影像拍摄月份，区分官方道路街景与游客上传全景，区分夏季绿叶和秋季红叶。以下 URL、日期、截图路径需要替换为你实际核对的材料：

```bash
photo-locate evidence cases/trip --candidate c1 --kind streetview \
  --url 'https://www.google.com/maps/实际视角链接' \
  --captured 2018-10 --image /path/to/observed-panorama.png \
  --verdict match --notes '游客360全景：瀑顶中央岩块、右侧层状岩壁和左岸树木位置对应。'
```

无法读取拍摄月份时用 `--captured unknown`。不确定用 `--verdict unclear`；存在反例用 `contradiction`。所有记录均保存在本地 `case.json`。不要把暂时无法解释的反例删掉后宣布确认。

### 5. 结论与双图报告

```bash
photo-locate conclude cases/trip --candidate c1 --level confirmed \
  --note '官网地址及多个稳定地形特征对应；精确站位未测定。'
photo-locate report cases/trip
photo-locate report cases/trip --format pdf
photo-locate status cases/trip
```

默认输出 `cases/trip/report.html` 和 `report.pdf`。HTML 内嵌图片，双击即可离线查看。PDF 会检测并嵌入常见系统中文 TrueType 字体（macOS Arial Unicode、Linux 文泉驿、Windows 微软雅黑）；没有可用字体时需用 `--font-path /path/to/font.ttf` 或 `.ttc` 指定含所需中日文字形的字体。Ubuntu/Debian 可安装 `fonts-wqy-microhei`。工具不会输出依赖未嵌入中文字体的 PDF。分享 PDF 前打开检查页面与文字。

置信等级是**人工审阅标签**，不是模型概率：

| 等级 | 约束 |
| --- | --- |
| `unknown` | 尚未识别 |
| `candidate` | 有候选，但证据尚不足 |
| `high` | 官网地址匹配 + 附图的视觉匹配；无未解决反例 |
| `confirmed` | 在 `high` 基础上，另有已审阅且附图的街景/360°匹配 |

这些约束只检查记录是否齐全，不验证你填写的陈述是否真实。新增证据会将旧结论退回 `candidate`，需重新审阅。没有街景覆盖时可以保留 `high` 或更低等级，并说明限制。

## 无私人照片的离线演示

```bash
python examples/synthetic_demo.py
```

生成一组程序绘制的虚构建筑及 HTML 报告到 `cases/demo/`；不联网、不上传，结论保留为候选。公开仓库不附用户照片、地图截图或有版权的参考照片。[真实案例的方法说明](docs/case-studies.md)只引用公开地点与来源。

## 隐私与范围

- 所有调查、原图副本、裁切、报告与浏览器截图默认留在本地，并由 `.gitignore` 排除；发布前仍应检查 `git status`。
- 不读取 `.env`，不需要 OpenAI、Google Maps 或 SerpApi 密钥，也不使用正常浏览器的登录配置。
- 只有执行 `lens --upload` 才由浏览器助手发送图片；手动上传同样属于向 Google 分享图片。
- 报告包含你附加的图片与链接，分享前自行检查。EXIF 移除不等于遮挡图像中可见的人脸、车牌或个人信息。
- 不做人物身份识别、私人住址追踪、生成式补字或后台批量抓取；用途是公开景点与场景的可核验定位。

## 开发与验证

```bash
python -m pip install -e '.[dev,pdf]'
python -m pytest -q
```

测试涵盖元数据移除、裁切边界、结论升级条件、反例拦截、报告转义、路径限制和默认不上传。CI 在 Python 3.10/3.12/3.13 运行离线测试。浏览器助手不在 CI 访问 Google；它依赖可变的网页 UI，需要在自己的环境实际检查。

实现依据：[Playwright 上传文件](https://playwright.dev/python/docs/input#upload-files)。Google、Google Lens、Google Maps 等名称属于各自权利人；本项目非官方产品。代码采用 [MIT](LICENSE)，第三方照片与地图影像不受本项目许可覆盖。
