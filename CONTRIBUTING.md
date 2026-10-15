# Contributing / 贡献指南

Thanks for helping make photo-location research easier to verify. / 感谢你帮助改进可核验的照片定位流程。

## Local setup / 本地开发

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then use the committed lockfile. / 安装 uv 后使用仓库锁文件。

```bash
uv sync --locked --extra dev --extra pdf --extra release
uv run --locked --extra dev --extra pdf pytest -q
uv run --locked photo-locate ui --cases cases/development
```

PDF tests need an embeddable CJK font. Ubuntu/Debian: `sudo apt-get install fonts-wqy-microhei`. Linux CI requires PDF coverage; macOS/Windows skip only that test if the font is absent. / PDF 需要可嵌入中文字体；Linux CI 强制覆盖，其余系统缺字体时明确跳过。

CI runs Ubuntu Python 3.10/3.12/3.13 and macOS/Windows Python 3.12. HTTP tests cover local session authorization, imports, crops, candidates, evidence, review history and exports. / CI 覆盖三系统，本地 API 测试覆盖完整记录流程。

Optional research uses mocked API responses in CI, never real credentials. Test consent, exact selected inputs, source grounding, retained checkpoints and explicit adoption. Bounded live calls require a configured key and API credits; report their actual outcome separately. / 可选研究助手在 CI 使用模拟响应；真实调用需明确记录是否成功，不把模拟结果称为模型验收。

For UI changes, test the real browser flow: choose/drop synthetic image → draw/save crop → candidate → evidence with reference image → draw both regions → save/reopen/focus paired details → review → conclude → download HTML/PDF → reopen case. Check Chinese/English and a narrow viewport. HTTP tests cannot verify pointer coordinates or visual layout. / 界面改动需实际完成浏览器流程、切换语言并检查窄屏；HTTP 测试不能代替框选与视觉检查。

Update dependencies deliberately with `uv lock --upgrade`, inspect the diff, then rerun CI. Normal development uses `--locked`. / 更新依赖后检查锁文件变化并重跑 CI，日常使用锁定模式。

## Changes / 修改约定

- Keep core operations local and network-free; external image submission must remain explicit. / 核心操作保持离线，向外部提交图片须显式执行。
- Retain source attribution, uncertainty, contradictions, and review history. / 保留来源、不确定性、反例与复审记录。
- Use synthetic images in tests and documentation. Do not submit private photographs, credentials, browser profiles, or third-party map screenshots. / 测试采用合成图片，不提交私人资料或第三方地图截图。
- Add regression tests for behavior changes, keep schema-v1 compatibility when possible, and update both READMEs and the changelog. / 功能改动增加针对性测试，尽量兼容旧记录，更新双语说明。
- For PDF/report changes, generate the synthetic demo, render every PDF page, and inspect a browser preview. / 报告改动需逐页检查 PDF 并在浏览器查看 HTML。

## Pull requests / 提交 PR

Describe the concrete problem, the resulting behavior, and the checks performed. Keep each PR focused. Never include a user's actual investigation merely to reproduce a bug; create a small synthetic case instead. / 说明问题、改后行为与验证结果；使用合成案例复现问题。

## License / 许可

Contributions are accepted under the repository's MIT License. Third-party assets retain their original licenses and must include attribution and redistribution permission. / 贡献使用 MIT 许可；第三方素材需保留许可并具有再分发权限。

## Release / 发行

1. Update `pyproject.toml`, `__version__`, both READMEs and `CHANGELOG.md`. Refresh `uv.lock` with `uv lock`. / 同步包版本、双语说明、更新记录和锁文件。
2. Add bilingual `docs/release-vX.Y.Z.md`, validate tests, build with `uv run --locked --extra release python -m build`, and inspect the package contents. / 写双语发行说明并验证测试和打包内容。
3. Push main, then an annotated matching tag: `git tag -a vX.Y.Z -m 'vX.Y.Z'` and `git push origin vX.Y.Z`. / 推送主分支与对应带注释标签。
4. `release.yml` calls the full test matrix, verifies all version values, then creates wheel, source archive, SHA-256 manifest and GitHub Release. It publishes only after validation succeeds. / 自动发行先验证，成功后构建并发布。

GitHub Releases distribute this project; the workflow does not publish to PyPI. Existing release tags should not be moved. / 使用 GitHub Release 分发，不自动发布 PyPI；不要移动已发布标签。
