# Changelog / 更新记录

## Unreleased / 待发行

- Resumable local investigation workbench: actual stage progress, cancel/resume, generated previews, candidate falsification and per-item review history in English/Chinese. / 新增中英文后台调查、真实阶段、取消恢复、预览、反证计划与逐条审阅历史。
- Streamed bounded subprocess logs, process-tree termination, cross-process workspace locks, preserved preparation/preprocessing checkpoints and a shared web executor. / 持续写入限长日志、清理子进程树、跨进程工作区锁、保存分步进度，并共用网页线程池。
- Local-job API authorization, restart recovery, input-bound review contexts and regression tests using actual child processes. / 新增本地任务权限、重启恢复、审阅结果绑定及真实子进程回归测试。

- Keyless map workbench: save inspected Street View pose, panorama ID, capture year/month, attribution and manually observed availability; preserve view correction history and reset conclusions for review. / 无密钥地图工作台，保存街景参数、日期、署名、人工覆盖状态与修订历史。
- Candidate coordinates, Place IDs, provenance and sharing links; coordinate-based satellite, terrain, nearby Street View and OpenStreetMap; Google candidate shortlist. / 固定候选位置、地点 ID 与来源，并提供多图层和候选清单。
- Google Earth / Mapillary entry points, coordinate-marker KML export, cross-map evidence and expanded HTML/PDF reports. / 增加 Earth、Mapillary 入口、KML 导出、跨地图证据及报告。
- Four map CLI commands, conservative standard-URL parsing, finite coordinate/camera validation and schema-v1 compatibility. No automatic map fetching, short-link expansion or geolocation claims. / 新增四个命令、保守解析与参数校验，兼容旧记录；不自动抓取地图或猜测链接含义。
- Optional CLI bridge to separately installed MIT-licensed geo-sleuth: prepared-image export, candidate board, local preprocessing, explicit OCR and unreviewed research snapshots. / 可选接入独立安装的 geo-sleuth，支持准备图导出、候选板、本地预处理、显式 OCR 和待审阅快照。
- Input/script provenance, failed/partial command logs and integrity checks; reverse-image uploads disabled, case evidence and confidence unchanged. / 保存输入与脚本校验信息、失败及部分成功日志；禁止桥接自动上传搜图，不修改案卷证据和结论。

## 1.3.0 — 2026-10-16

- Optional OpenAI research workbench: image observations, search queries, source-linked candidate hypotheses and verification questions. / 可选 OpenAI 研究助手，整理观察、搜索词、附来源假设与核对问题。
- Explicit input submission, bounded requests, server-only credentials, source URL filtering and manual candidate adoption. No automatic evidence or confidence upgrades. / 明确发送范围、限制调用次数、密钥留在服务端；候选须手动采纳，不自动形成核对证据。
- Persisted notes, resolved questions, run history and analysis/search checkpoints; resume failed or interrupted work without repeating saved analysis. / 保存笔记、问题状态、历史和分步检查点，支持中断后继续。
- Safe quota/authentication/transport errors and regression coverage for retry, integrity, duplicate jobs, source grounding and HTTP operations. / 区分额度、鉴权和连接错误，新增恢复、完整性、来源与 HTTP 测试。

Schema stays at 1; research fields are optional. Manual tools and the offline demo remain usable without a key. / 保持 schema-v1，手动工具和离线演示无需密钥。

## 1.2.0 — 2026-10-16

- Full-width paired image workspace: synchronized zoom, optional relative dragging, mouse or keyboard region selection, and numbered click-to-focus correspondences. / 双图工作区支持同步缩放、相对拖动、鼠标或键盘框选与编号定位。
- `annotate` and `unannotate` CLI/API operations, strict per-image pixel bounds, stable numbers, removal history and conclusion invalidation. / 新增标注命令与 API，校验像素边界、保留移除历史，并要求重新审阅结论。
- HTML/PDF include numbered overviews, paired detail crops, pixel coordinates and annotation removal history. / 报告附编号总览、局部对照、坐标和历史。
- Offline demo now uses differently framed images and two saved corresponding details. / 离线演示采用不同取景范围的图片和两组预置标注。
- Additional regression coverage for invalid regions, unchanged original assets, persistence, API/CLI operations and annotated reports. / 新增边界校验、原文件不变、保存恢复、API／CLI 和报告测试。

Schema remains at 1. Annotation fields are optional, so old records remain readable. No new model or browser dependency is required. / 保持 schema-v1，标注字段可选，兼容旧记录，无需新增模型或浏览器依赖。

## 1.1.0 — 2026-10-15

### Added / 新增

- `photo-locate ui`: local English/Chinese web workbench with drag/drop import, pointer or coordinate crops, candidate records, paired evidence images, verdict reviews and HTML/PDF downloads. / 新增本地中英文网页工作台，覆盖导入、框选、候选、证据对照、复审与导出。
- `photo-locate demo` and a one-click offline demo, included in installed wheels. / 安装包内附命令行及一键离线演示。
- Locked dependencies in `uv.lock`; CI on Linux, macOS and Windows, plus isolated wheel installation checks. / 锁定依赖、三系统 CI 与独立 wheel 安装验证。
- Tag-triggered GitHub releases gated by the full CI matrix, with wheel, source archive and SHA-256 manifest. / 完整 CI 通过后自动发行安装包与校验清单。
- Bilingual issue forms, PR template, updated READMEs and contributor/release guidance. / 中英文问题表单、PR 模板及完整说明。

### Compatibility / 兼容性

Schema stays at 1 and existing CLI commands remain available. The web workbench binds only to loopback, keeps files local, and opens Google separately for manual upload. It does not automatically identify locations or verify external sources. / 保持 schema-v1 和现有命令；本地界面不自动上传或识别地点。

## 1.0.0 — 2026-10-15

### Added / 新增

- Full English and Simplified Chinese READMEs, a visual project banner, bilingual command reference, and contributor guidance.
- `review`: revise an evidence verdict with mandatory reasoning while preserving original observations and judgment history.
- `check`: validate local asset existence, SHA-256 checksums, path boundaries, IDs, and candidate references.
- Per-asset SHA-256 for new normalized images, crops, references, and Lens captures.
- Optional image-provider attribution, clearer capture dates, and review history in comparison reports.
- Release wheel, source distribution, and SHA-256 manifest; package-build and wheel-install CI checks.

### Improved / 改进

- Redesigned responsive offline HTML reports; PDF reports now have clickable sources, comparison captions, and embedded CJK fonts.
- Native/enlarged crops and imported evidence now use separate directories, preventing labels from overwriting source or reference images.
- Prepared-image validation before browser upload; strict result-domain detection; explicit interrupted/failed capture states.
- Protected report output paths, automatic output-directory creation, stricter capture-month validation, and bounded crop enlargement.
- Updated GitHub Actions versions and pinned CI to Ubuntu 24.04.
- MIT SPDX metadata and packaged license file; version raised to 1.0.0.

### Compatibility / 兼容性

Schema version stays at 1. Existing 0.1.0 records and legacy asset paths remain readable. Legacy files without saved checksums produce warnings rather than retroactive claims of validation. New crops use `assets/crops/LABEL/native.png`; new attached evidence uses `assets/evidence/ID.png`.

置信等级仍是人工审阅标签；不会自动识别地点、认证来源陈述或计算地理位置概率。Google Lens 辅助依赖可变网页界面，CI 不访问真实 Google 服务。

## 0.1.0 — 2026-10-15

Initial evidence-first CLI: local image preparation, crops, optional Lens upload, candidate/evidence records, confidence requirements, synthetic demo, and HTML/PDF export.
