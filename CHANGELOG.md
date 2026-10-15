# Changelog / 更新记录

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
