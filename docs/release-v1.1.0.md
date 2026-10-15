## A local workbench for the complete investigation

Run `photo-locate ui` after installation to open the new English/Chinese workbench. Drop a photo, draw a crop, record candidates and evidence, compare reference images, preserve review history, and download HTML/PDF reports. The same local case files and evidence requirements power the CLI and the UI.

Try the one-click offline demo, or `photo-locate demo --case cases/demo`. The installed wheel includes the web assets and synthetic demo. No model API key, Node runtime or frontend build is required.

Open-source improvements include locked dependencies, Linux/macOS/Windows CI, isolated wheel checks, bilingual issue forms and a tag-triggered release workflow that publishes only after the full test matrix succeeds.

The interface runs on `127.0.0.1`. Google Lens opens separately for manual upload. PDF needs the `pdf` extra and a suitable CJK font. Schema-v1 cases and existing CLI commands remain compatible.

## 本地网页工作台，完成一整次地点调查

安装后运行 `photo-locate ui`，即可使用中英文工作台：拖入照片、鼠标框选、记录候选与来源、并排对照参考图、保留复审理由、下载 HTML/PDF。界面与命令行共用本地调查记录及证据约束。

点击“体验离线演示”，或运行 `photo-locate demo --case cases/demo`。安装包内附网页与虚构案例，无需模型密钥、Node 或前端构建。

开源工程新增依赖锁定、Linux/macOS/Windows CI、独立安装包验证、中英文问题表单，以及完整 CI 通过后自动构建发布的工作流。

界面仅在本机运行，Google 搜图另行手动上传。PDF 需要扩展及中文字体；兼容旧 schema-v1 记录和现有命令。

## Install / 安装

Download the wheel below, then / 下载下方 wheel 后运行：

```bash
python -m pip install 'photo_location_workflow-1.1.0-py3-none-any.whl[pdf]'
photo-locate ui
```

Verify downloads against `SHA256SUMS.txt`. / 可使用 SHA-256 清单核对下载文件。
