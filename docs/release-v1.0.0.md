# Photo Location Workflow 1.0.0

The first stable release of the local, evidence-first photo-location toolkit.

## English

**Research a scene, preserve the evidence, and publish a reviewable comparison.**

- Complete English and Chinese documentation, project artwork, command reference, and public case studies.
- Local image preparation, isolated crops, optional visible-browser Google Lens upload, candidate/address records, and Street View/360 comparisons.
- New `review` command preserves judgment history; new `check` command detects missing or changed case assets and broken references.
- Redesigned offline HTML reports and CJK PDF reports with paired images, provider/date notes, clickable sources, and review history.
- Fixes image-name collisions that could overwrite source assets; validates prepared images, output paths, capture months, and crop sizes.
- Schema-v1 compatibility with the initial 0.1.0 release. Legacy assets without checksums are reported honestly as unverified.
- MIT-licensed code. No private source photos, account information, or paid model keys included.

### Install

Download the wheel below and run:

```bash
python -m pip install ./photo_location_workflow-1.0.0-py3-none-any.whl
```

For optional features, use source installation with `.[pdf]` or `.[browser]`; browser assistance also requires `playwright install chromium`. PDF export needs a suitable CJK TrueType font. See the READMEs for the complete setup and workflow.

### Verification and limits

Local tests, the GitHub CI Python matrix, and package checks are run before publication. Browser automation uses Google's changing public UI and is not a live-Google CI test. Location decisions are human reviewed; confidence requirements and file hashes do not prove factual correctness or image authenticity.

## 简体中文

**首个正式版本：让照片地点有据可查。**

- 完整中英文 README、项目视觉、命令手册及公开案例。
- 本地图片准备、独立裁切、可选 Google Lens 可视上传、候选地址及街景／360°证据记录。
- 新增 `review`，修订判断同时保留历史；新增 `check`，检查文件缺失、内容变化及记录引用。
- 重新设计离线 HTML 和中文 PDF 报告，包含双图、提供者、日期、可点击来源与复审记录。
- 修复图片重名覆盖风险，补强上传图片、报告路径、拍摄月份及放大尺寸检查。
- 兼容 0.1.0 的 schema-v1 调查；旧文件缺少校验和时如实提示。
- 使用 MIT 许可，不附私人原图、账号信息或付费模型密钥。

下载 wheel 后可直接 `pip install`；PDF 和浏览器扩展安装方法参见 README。地点判断仍需人工核验；测试不等于已经替你核验照片，也不保证 Google 网页控件长期不变。

## Assets / 发布文件

- `photo_location_workflow-1.0.0-py3-none-any.whl` — installable Python wheel / 可安装包。
- `photo_location_workflow-1.0.0.tar.gz` — source distribution / 源码包。
- `SHA256SUMS.txt` — SHA-256 digests of the two packages / 两个包的文件校验和。

Repository / 仓库: https://github.com/xudaniel/photo-location-workflow
License / 许可: MIT
