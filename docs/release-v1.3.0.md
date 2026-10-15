## Optional research assistant / 可选半自动研究助手

Run `photo-locate ui --env-file /path/to/ignored.env.local` to enable OpenAI research. The default model is `gpt-5.6-terra`; `OPENAI_MODEL` can override it. Manual investigations and the offline demo remain available without API credentials.

- Select prepared images/native crops, record clues and explicitly start research.
- Image analysis produces observations, search queries and verification questions. The next request collects web-backed, unverified candidate hypotheses.
- Candidate source URLs are filtered against actual tool-returned sources. Adopt a hypothesis manually; evidence and confidence requirements stay unchanged.
- Notes, completed questions, history and analysis/search checkpoints persist locally. Continue interrupted or failed work without repeating saved analysis.
- Credentials stay on the server. No new runtime dependency is required. OpenAI requests use `store:false`; selected inputs still go to OpenAI and API calls are billed.

新增图片分析、建议搜索词、附来源候选、待核对问题、笔记与历史保存。候选需手动加入记录，助手不会自动形成官网或街景吻合证据，也不会提高结论等级。分析完成即保存检查点，检索失败后可以继续。密钥留在本地服务端，手动工具仍无需密钥。

### Validation / 验证范围

Regression tests and browser workflows use synthetic images and explicitly simulated provider responses. A bounded live request was attempted, but the configured project's API returned `credit_balance_exhausted` / `insufficient_quota`. Real model output, search quality and end-to-end hosted-tool execution have **not** been validated with that credential. No automatic retries were performed.

合成数据的回归测试和浏览器流程已验证；真实调用因现有项目 API 余额耗尽受阻。模拟结果不代表真实模型或联网检索验收通过。程序明确显示额度错误并保留进度。

### Install / 安装

Download the wheel and run / 下载 wheel 后运行：

```bash
python -m pip install 'photo_location_workflow-1.3.0-py3-none-any.whl[pdf]'
photo-locate ui
```

Verify downloads against `SHA256SUMS.txt`. / 可使用 SHA-256 清单校验文件。

API contracts follow the official [web search](https://developers.openai.com/api/docs/guides/tools-web-search), [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) and [model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-terra).
