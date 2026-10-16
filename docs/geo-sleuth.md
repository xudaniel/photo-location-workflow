# geo-sleuth bridge / 本地调查工具桥接

[English](#english) · [简体中文](#简体中文)

## English

[Oldcircle/geo-sleuth](https://github.com/Oldcircle/geo-sleuth) is an independent MIT-licensed geolocation skill with image preparation, OCR and a candidate/falsification board. This optional **web and CLI bridge** adds those tools to Photo Location Workflow without adding a model dependency to the base installation. Open a case in the web workbench to use **Local clue investigation**.

```mermaid
flowchart LR
    A[Prepared source or native crop] --> B[Separate geo-sleuth workspace]
    B --> C[Local preparation and optional OCR]
    B --> D[Candidate board and falsification]
    C --> E[Unreviewed review.json]
    D --> E
    E --> F[Human review: Lens, official address, Street View]
    F --> G[Existing evidence record and comparison report]
```

### Install and prepare

Install this project normally, then install [uv](https://docs.astral.sh/uv/getting-started/installation/) and the complete external skill. Codex users can install `skills/geo-sleuth` through skill-installer; the default discovery path is `$CODEX_HOME/skills/geo-sleuth`, or `~/.codex/skills/geo-sleuth` when `CODEX_HOME` is unset. For other environments:

```bash
git clone https://github.com/Oldcircle/geo-sleuth.git tools/geo-sleuth
git -C tools/geo-sleuth checkout 836d70eea196b194391017e6e018e04ccc85aaa4
photo-locate demo --case cases/demo
photo-locate geo-sleuth prepare cases/demo --workspace private/geo-demo --skill-dir tools/geo-sleuth/skills/geo-sleuth
photo-locate geo-sleuth intake cases/demo --workspace private/geo-demo
photo-locate geo-sleuth review cases/demo --workspace private/geo-demo
```

The pinned revision is the integration review baseline, not a claim that arbitrary installed versions have been tested. `--skill-dir` locates a complete skill, not just its scripts. `--uv /absolute/path/to/uv` supports installations outside `PATH`. Preparation invokes local third-party Python code; use a reviewed installation. uv can download Python dependencies on first use. These commands need no OpenAI key or paid model request.

Choose a **new empty workspace outside the case directory**. `prepare` copies only the checksum-verified, metadata-free source. `--asset assets/crops/sign/native.png` selects a native crop; enlarged images are rejected. It initializes `board.json`, exports candidates with uniform priors and records hashes of the input and installed Python scripts in `bridge.json`. Same-name candidates remain distinct through their case IDs. Existing candidates use the placeholder board level `area`; review their geographic level before interpreting the board's coverage or exclusions. New candidates added later require a fresh export or a manual board update.

### Web workbench and resumable jobs

Run `photo-locate ui`, open a case and use **Local clue investigation**. Choose the prepared whole image or a native crop; OCR remains unchecked until you enable it. Click **Start local investigation**. Jobs run in the background on the same two-worker executor as optional OpenAI research. The page shows actual preparation / preprocessing / review stages, recent live output, generated helper images and previous runs. Progress is stage-based; there is no invented completion percentage.

**Cancel task** stops the current subprocess tree; queued work is cancelled without starting. **Resume saved progress** checks input and script hashes, reuses completed preparation and fully successful preprocessing, and retries only incomplete/partial work. A server restart marks abandoned runs interrupted so they can resume. No model requests are made by these local jobs. Pipeline checkpoints and clue review history live under `<cases>/.geo-sleuth/<case>/<run>/`, outside `case.json`. This directory contains private investigation material and is covered by the default `cases/` ignore rule; exclude it yourself when choosing a different root.

Once results are ready, add a directly observed clue, append a candidate falsification test, or review a candidate/OCR item with a mandatory note. These edits update the external board or local review history, not case evidence. A changed result makes previous review marks historical instead of applying them to new output. The UI shows previews from the latest preprocessing attempt; failed attempt directories remain on disk for diagnosis. OCR can download model weights; enhanced images and text remain hypotheses.

The server discovers the installed skill and uv automatically. Override with server environment variables `GEO_SLEUTH_DIR=/path/to/skills/geo-sleuth` and `GEO_SLEUTH_UV=/path/to/uv`. Browser requests cannot choose arbitrary executables or script paths. A uv executable beside the server's Python is also detected. Missing setup leaves manual investigation and saved results available.

### Use the board to test alternatives

Inside the exported workspace, use the upstream board commands. This example records an observation, then a test that could disprove a candidate. Substitute an actual exported candidate name for `Candidate A`:

```bash
cd private/geo-demo
uv run ../../tools/geo-sleuth/skills/geo-sleuth/scripts/board.py clue "Three window bays visible" --kind infra --status observed --file input.png
uv run ../../tools/geo-sleuth/skills/geo-sleuth/scripts/board.py falsify "Candidate A" --text "Reject if the facade has only two bays in a comparable view."
uv run ../../tools/geo-sleuth/skills/geo-sleuth/scripts/board.py rank
uv run ../../tools/geo-sleuth/skills/geo-sleuth/scripts/board.py next
```

Return to the project root and run `geo-sleuth review` again to refresh the snapshot. The original `board.json` remains editable. Follow upstream documentation for likelihood ratios, hierarchical candidates, computed exclusions and coverage checks. **A ranking share of 1.0 is not 100% location confidence.** It can simply mean only one candidate was entered.

### Outputs and limits

| File | Purpose |
| --- | --- |
| `input.png` | Exact prepared image copy, with its checksum. |
| `bridge.json` | Provenance, candidate-ID mapping, command arguments, bounded logs and exit status. Contains local tool paths; review before sharing. |
| `board.json` | External hypotheses, observations, exclusions and proposed tests. |
| `intake-*/` | Separate preprocessing runs, edge crops, variants and `intake.md` / `intake.json`. Failed/partial steps remain visible. |
| `review.json` | Unreviewed board report, OCR hypotheses, step status and verification checklist. Refreshed on each review. |

`intake` always passes **`--no-rev`** and defaults to **`--no-ocr`**. No bridge command uploads the image to a reverse-image engine or opens a browser. Optional `intake --ocr` may download model weights and run additional OCR passes; text from upscaled/tiled images remains a hypothesis, especially on plates and signs. Preprocessing variants may alter appearance: they are search aids, not evidence of details in the original pixels. Model/dependency downloads require network access; this is not an offline sandbox for arbitrary upstream code.

The bridge does **not** run upstream reverse-image browser automation, `doctor.py` browser probes, or undocumented Street View endpoints. Google Lens and actual Maps/Street View review remain explicit investigator steps. It does not claim a search, address check or Street View comparison occurred.

`review` checks the case/image association and installed script hashes, uses a fresh upstream report file, and saves suggestions outside the case. **No command in this bridge changes `case.json`, creates reviewed evidence, excludes a case candidate, or raises confidence.** Adopt verified findings through the existing workbench or `candidate` / `evidence` commands, then export the normal HTML/PDF report. `review.json` is a research handoff, not that comparison report.

On a nonzero exit or timeout, inspect `bridge.json` and the run directory. A partial intake is reported as partial even when its process exits successfully. Changed scripts/images require a new workspace. Interrupted CLI preparation can continue with `prepare ... --resume`; subsequent `intake` runs create a new attempt directory. Web resume automatically reuses fully successful preprocessing after verifying the JSON and generated image checksums. A workspace has a nonblocking OS lock shared by web and CLI commands; a POSIX tool retains the lock if its server crashes, preventing a resumed job from overwriting an orphan writer. After the tool exits, refresh to resume. On Windows a kill-on-close Job Object also stops tools when the server exits. Logs stream to `logs/*.log`, capped at 100,000 bytes per command, with only the latest command's text duplicated in the manifest. Cancellation and timeout stop the POSIX process group or terminate the Windows Job Object; detached processes that deliberately escape their process tree are outside this runner's containment. Dependencies already downloaded remain in uv's cache. This is process management, not an operating-system sandbox. Keep research workspaces private and outside version control.

### Attribution

Upstream: [Oldcircle/geo-sleuth](https://github.com/Oldcircle/geo-sleuth), MIT, copyright 2026 Oldcircle. Reviewed revision: [`836d70e`](https://github.com/Oldcircle/geo-sleuth/tree/836d70eea196b194391017e6e018e04ccc85aaa4). The bridge is original adapter code; upstream code is installed separately and is not vendored in this package. Its own dependency licenses and service terms remain applicable.

## 简体中文

[geo-sleuth](https://github.com/Oldcircle/geo-sleuth) 是 MIT 许可的独立照片定位技能，提供本地预处理、OCR、候选板和反证计划。本项目通过可选**网页和命令行桥接**使用这些工具，基础安装不新增模型依赖。打开案卷即可使用“本地线索调查”。

### 安装与使用

先正常安装本项目和 [uv](https://docs.astral.sh/uv/getting-started/installation/)。Codex 用户可通过 skill-installer 安装完整的 `skills/geo-sleuth`；默认查找 `$CODEX_HOME/skills/geo-sleuth`，未设置环境变量时查找 `~/.codex/skills/geo-sleuth`。其他环境可运行上方安装示例，固定到已检查的 `836d70e` 版本，并传入 `--skill-dir`。版本号表示本次检查基线，不表示任意新版本都已验证。uv 不在 PATH 时传 `--uv /绝对路径/uv`。工具会执行本地第三方 Python 脚本，首次运行可能下载依赖；不需要 OpenAI 密钥或付费模型调用。

三个步骤：

1. `prepare`：将校验通过、已去除 EXIF 的图片和候选导出到案卷目录之外的**全新空工作区**。`--asset` 可选原始分辨率裁切，拒绝放大图。保留同名候选的不同案卷 ID。候选暂以 `area` 层级导入，行政层级与地址仍需核实；后加的候选需要重新导出或手动更新候选板。
2. `intake`：生成边缘裁切和搜索辅助变体。始终禁止反向搜图上传，默认不运行 OCR。显式加 `--ocr` 才启用文字识别，可能下载模型；放大或分块识别出的字仍是待核对假设，模糊车牌不能补字。变体可能改变外观，不能当作原图细节证据。
3. `review`：汇总候选板和 OCR 到独立 `review.json`，标记为 `unreviewed`。执行前检查案卷图片关联、工作副本图片和已安装脚本的哈希。上游排名占比不等于定位正确概率，只有一个候选时也可能显示 1.0。

可在工作区用上方 `board.py clue / falsify / rank / next` 示例记录观察、设计排除测试，再回项目根目录刷新 `review`。示例中的候选名需要替换成真实导出的名字。候选板支持的排除、行政层级和覆盖范围规则，以其上游文档为准。

### 网页任务与恢复

运行 `photo-locate ui` 后，在案卷的“本地线索调查”中选择准备图或原生裁切，按需启用 OCR，再启动任务。页面显示真实阶段、最近日志、最新一次预处理的辅助图片及历史调查。使用与 OpenAI 研究助手共用的两个后台工作线程；不虚构进度百分比。

“取消任务”会停止当前子进程树；尚未开始的排队任务直接取消。“从保存进度继续”会校验图片和脚本，跳过成功完成的准备及预处理，重试失败或部分成功的阶段。服务重启后，遗留任务标记为中断，可继续处理。本地任务不调用付费模型。

结果完成后，可以记录直接观察、追加候选反证计划，或逐条审阅候选/OCR 并写明依据。结果发生变化时，旧审阅保留为历史，不套用到新结果。任务及审阅存于 `<cases>/.geo-sleuth/<case>/<run>/`，不进入 `case.json`。默认 `cases/` 已排除版本控制；使用其他案卷目录时请自行排除。

服务器自动寻找完整技能与 uv，也支持 `GEO_SLEUTH_DIR`、`GEO_SLEUTH_UV` 环境变量；还会查找 Python 可执行文件旁的 uv。网页不能指定任意执行程序或脚本路径。缺少配置时仍可使用手动功能与已有结果。

### 如何接回我们的流程

工具负责整理观察与候选，审阅者继续完成 **Google Lens → 官网名称及完整地址 → 实际街景细节与拍摄月份 → 证据报告**。三个桥接命令均不修改 `case.json`，不自动新增已核对证据、不排除案卷中的候选，也不提高结论等级。确认后通过现有网页或 `candidate / evidence` 命令记录，再导出原有 HTML/PDF；`review.json` 只是研究交接材料。

本桥接没有执行反向搜图、`doctor.py` 浏览器探测或未公开的街景接口，也不会把“未执行”写成“搜过但没有结果”。依赖和模型下载需要网络，它不是隔离任意第三方代码的离线沙箱。

输出含图片、候选板、`intake-*` 运行目录、审阅快照及 `bridge.json`。后者记录参数、退出状态、有限长度日志和本地工具路径，分享前请检查。部分步骤失败会显示 `partial`；整体失败或超时则检查日志。日志持续写入 `logs/*.log`，每条命令最多保留 100,000 字节；清单只重复保存最新命令的文本。取消与超时会清理 POSIX 进程组，Windows 终止 Job Object；主动脱离进程树的程序不在此机制的控制范围内。这是进程管理，不是操作系统沙箱。OS 工作区锁可阻止网页与 CLI 同时写入同一个工作区；POSIX 工具在服务崩溃后仍持锁，直到工具退出，刷新后才可恢复。Windows Job Object 会在服务退出时一并停止工具。脚本或图片变化需新建工作区；CLI 准备中断可用 `prepare ... --resume` 继续，网页会自动复用校验通过的完整成功步骤。已下载依赖继续留在 uv 缓存中。工作区应留在本地并排除版本控制。

上游版权归 2026 Oldcircle，采用 MIT License。本项目仅包含自行编写的适配器，未打包其源代码；上游依赖许可和外部服务条款仍适用。

Windows process containment follows the [Microsoft Job Object API](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information). / Windows 进程管理依据微软 Job Object 接口。
