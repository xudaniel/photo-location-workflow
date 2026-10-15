# Contributing / 贡献指南

Thanks for helping make photo-location research easier to verify. / 感谢你帮助改进可核验的照片定位流程。

## Local setup / 本地开发

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,pdf,release]'
python -m pytest -q
```

PDF tests need an embeddable CJK font. Ubuntu/Debian: install `fonts-wqy-microhei`. / PDF 测试需要可嵌入中文字体。

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
