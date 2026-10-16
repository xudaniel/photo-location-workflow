# Command reference / 命令手册

All commands support `--help`. Most successful commands print JSON to stdout; `ui` prints a local URL and serves until stopped; failures print an error to stderr. The interactive Lens assistant also displays progress and prompts. Paths can contain spaces when quoted. / 所有命令支持 `--help`；成功输出 JSON，失败向 stderr 输出错误。交互式 Lens 另有提示。含空格的路径请加引号。

| Exit code / 退出码 | Meaning / 含义 |
| --- | --- |
| `0` | Completed successfully / 成功。 |
| `1` | `check` found integrity errors / `check` 发现文件完整性错误。 |
| `2` | Invalid arguments or a handled operation error / 参数或操作错误。 |

When stdout is redirected, JSON uses standard Unicode escapes so legacy Windows pipe encodings can read it; decoded values are unchanged. Interactive terminals retain readable Unicode. / 重定向输出采用标准 Unicode 转义，兼容 Windows 旧编码管道，JSON 解码后的内容保持不变；交互终端保留可读中文。

## `ui` / 本地网页工作台

```bash
photo-locate ui --cases cases --port 8765
photo-locate ui --cases cases --port 8765 --no-open
photo-locate ui --env-file /path/to/ignored.env.local
```

Starts the English/Chinese workbench on `127.0.0.1` only. Imports local photos, supports pointer or coordinate cropping, candidates, evidence comparison, reviews and report downloads. `--no-open` prevents automatic browser launch. Ctrl-C stops the server. / 启动本机中英文工作台，可导入、框选、记录候选与证据、复审并导出；Ctrl-C 停止。

Images stay local until you explicitly upload them or start optional OpenAI research. `--env-file` reads only OPENAI_API_KEY and OPENAI_MODEL on the server. PDF needs the `pdf` extra and an embeddable CJK font. / 图片保持本地，搜图另行手动上传。PDF 需要扩展及字体。

## `demo` / 离线演示

```bash
photo-locate demo --case cases/demo
```

Creates a synthetic building, one crop, a candidate and an unverified reference comparison in an empty directory. No network required; conclusion stays `candidate`. Also available as **Try offline demo** in the UI. / 在空目录绘制虚构建筑、裁切并生成演示记录；全程离线，保留候选等级。界面内也可一键创建。

## `init`

```bash
photo-locate init photo.jpg --case cases/trip
```

Creates a new investigation in an empty directory. Copies decoded pixels to a PNG, normalizes EXIF orientation, strips metadata, and records original/normalized SHA-256 values. The original file remains unchanged. / 在空目录创建调查，校正方向、移除副本元数据并保存 SHA-256；原文件不变。

## `crop`

```bash
photo-locate crop cases/trip --box 10,20,200,120 --label sign --scale 4
```

`--box` is `x,y,width,height` in normalized image pixels. `--scale` defaults to 4 and accepts 1–16, subject to a 40-million-pixel enlarged-image limit. Labels accept 1–48 Unicode word characters or hyphens; paths and duplicate labels are rejected. Outputs native PNG and nearest-neighbor PNG under `assets/crops/LABEL/`. / 坐标基于校正方向后的副本；放大倍率 1–16，放大后不超过四千万像素。标签支持中文；禁止越界、路径和重名。

## `lens`

```bash
photo-locate lens cases/trip
photo-locate lens cases/trip --asset assets/crops/sign/native.png
photo-locate lens cases/trip --asset assets/crops/sign/native.png --upload
```

Without `--upload`, prints instructions and sends nothing. With it, requires the `browser` extra, installed Chromium, a display, and an interactive terminal. Only a listed prepared source/native crop can be selected; changed prepared assets are rejected. / 默认只输出说明；`--upload` 需要浏览器扩展、Chromium、显示环境和交互终端。仅允许准备好的原图副本或原始裁切。

Captures are unverified research materials. Status values include `captured_unverified`, `not_results`, `interrupted`, and `capture_failed`. / 搜索截图不是已确认的定位证据；状态区分搜索结果、非结果页、中断和截图失败。

## `candidate`

```bash
photo-locate candidate cases/trip --name 'Landmark' --address 'Public address' \
  --url 'https://example.org/official-page'
```

Creates `c1`, `c2`, etc., with a Google Maps search URL. Requires a nonempty name/address and an HTTP(S) source without embedded credentials. It does not fetch or authenticate the page. / 建立候选及地图链接；不自动读取或认证来源页面。

## `evidence`

```bash
photo-locate evidence cases/trip --candidate c1 --kind reference \
  --url 'https://example.org/reference' --verdict unclear \
  --notes 'Window alignment is uncertain.' --image reference.jpg

photo-locate evidence cases/trip --candidate c1 --kind streetview \
  --url 'https://www.google.com/maps/YOUR_VIEW' --verdict match \
  --captured 2026-06 --provider 'Google Street View' \
  --notes 'Windows, lights, and road geometry align.' --image panorama.png
```

| Option / 参数 | Accepted values / 取值 |
| --- | --- |
| `--kind` | `official`, `streetview`, `reference`, `text` |
| `--verdict` | `match`, `unclear`, `contradiction` |
| `--captured` | Required for `streetview`: `YYYY`, `YYYY-MM` or `unknown` / 街景必填。 |
| `--provider` | Optional provider/contributor description / 可选提供者说明。 |
| `--image` | Optional local screenshot/reference; copied without metadata / 可选附图，导入时移除元数据。 |

Creates `e1`, `e2`, etc. Notes and source URLs are mandatory. Image records include SHA-256. A new observation resets the conclusion to `candidate`. / 备注及来源必填；新证据会使结论退回候选。

## `review`

```bash
photo-locate review cases/trip --evidence e2 --verdict match \
  --reason 'Rechecked the opposite-facing camera angle; geometry agrees.'
```

Changes the current verdict while preserving the original observation, original verdict, and every previous review. Requires a reason and resets the conclusion. Reports expose the review trail. / 修订当前判断，保留原始观察、最初判断和每次复审；理由必填，结论退回候选，报告显示历史。

## `annotate` / 对应细节标注

```bash
photo-locate annotate cases/trip --evidence e1 --label 'Three windows / 三扇窗' \
  --source-box 214,264,297,63 --reference-box 182,294,476,101
```

Both boxes are `x,y,width,height` in the respective metadata-free images' original pixels, with integer coordinates entirely inside each image. Evidence must have an attached reference image; up to 100 pairs are accepted per evidence. A number is assigned automatically and the conclusion resets to `candidate`. The UI also supports drawing both regions. / 两侧坐标分别基于各自图片；自动编号并将结论恢复为候选。证据须有附图，每条最多 100 组。

## `unannotate` / 移除标注

```bash
photo-locate unannotate cases/trip --evidence e1 --annotation a1 \
  --reason 'Selected the wrong window / 框错了窗户'
```

Retains the removed region, timestamp and reason in `annotation_history`. Removed numbers are not reused, and the conclusion must be reviewed again. / 保留旧坐标、时间和理由，不复用编号，需重新审阅结论。

## `check`

```bash
photo-locate check cases/trip
```

Offline checks of stored asset paths, file existence, available checksums, duplicate IDs, candidate references, and the selected conclusion reference. Missing legacy checksums are warnings. It does not verify page contents, GPS location, image authenticity, or factual judgments. / 离线检查文件及记录引用；旧文件缺少校验和仅警告，不验证事实。

## `conclude`

```bash
photo-locate conclude cases/trip --candidate c1 --level high \
  --note 'Official address and attached reference match; no panorama is available.'
```

Levels: `unknown`, `candidate`, `high`, `confirmed`. A reason is required. Stronger levels require a valid local case, an `official` match, an attached `reference`/`streetview` match, and no current contradiction for that candidate. `confirmed` additionally requires an attached matching `streetview` record. Human-entered statements are not independently verified. / 等级约束详见 README；它们不替代人工核验。

## `report`

```bash
photo-locate report cases/trip
photo-locate report cases/trip --format pdf
photo-locate report cases/trip --format pdf --font-path /path/to/cjk-font.ttf
photo-locate report cases/trip --output exports/trip.html
```

Default HTML embeds images and makes no automatic network requests. Clicking a source link opens the external site. PDF needs the `pdf` extra and a suitable CJK TrueType font. Parent output directories are created; the extension must match the format, and outputs cannot overwrite case assets. Integrity failures block export. / HTML 图片内嵌、无自动网络请求；点击来源才访问外部。PDF 需字体；完整性失败时拒绝导出。

## `geo-sleuth` / 可选本地调查桥接

The web workbench also provides local investigation jobs with live logs, cancel/resume, previews and clue reviews. / 网页也支持本地后台调查、实时日志、取消恢复、辅助图及逐条线索审阅。

```bash
photo-locate geo-sleuth prepare cases/trip --workspace private/trip-investigation --skill-dir tools/geo-sleuth/skills/geo-sleuth
photo-locate geo-sleuth intake cases/trip --workspace private/trip-investigation
photo-locate geo-sleuth review cases/trip --workspace private/trip-investigation
```

Use `prepare ... --resume` to continue interrupted CLI preparation. Requires a separately installed geo-sleuth skill and uv. Preparation exports the verified source, or `--asset` native crop, to a new external workspace. Intake disables image-search uploads and defaults to no OCR; `--ocr` explicitly enables optional model downloads. Review writes unreviewed hypotheses outside the case. No evidence or confidence is changed. See the [bilingual integration guide](geo-sleuth.md) for setup, board commands, provenance and limits. / 需独立安装 geo-sleuth 和 uv；导出准备图或原生裁切到新的独立工作区。默认不运行 OCR，始终不上传搜图；`--ocr` 可启用模型下载。审阅结果保持为案卷外的待核对假设，不改证据及结论。完整步骤见[中英文说明](geo-sleuth.md#简体中文)。

## `status` and version / 状态与版本

```bash
photo-locate status cases/trip
photo-locate --version
python -m photo_location_workflow --help
```

`status` prints the local record without modifying it. / `status` 只读显示调查记录。

## `map-location`, `map-view`, `map-parse`, `map-links` (main / next release)

See the [bilingual maps guide](maps.md) for candidate coordinates / Place IDs, saved camera parameters, manual coverage status, supported URL parsing and KML export. Map links require no API key. / 见[地图指南](maps.md)，涵盖位置、视角、人工覆盖状态、链接解析与 KML；地图链接无需密钥。
