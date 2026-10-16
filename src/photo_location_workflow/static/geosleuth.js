const words = {
  zh: {
    title: "本地线索调查",
    subtitle: "用 geo-sleuth 整理细节、文字假设和候选反证。无需模型 API 密钥。",
    missing: "本地工具尚未配置。",
    setup: "查看安装说明",
    image: "调查图片",
    original: "整张照片",
    ocr: "启用 OCR（首次可能下载模型；识别文字仍需对照原图）",
    start: "开始本地调查",
    empty: "从一张准备好的照片或原生裁切开始。",
    queued: "等待处理",
    preparing: "准备图片与候选板",
    processing: "生成细节与文字线索",
    reviewing: "整理候选与反证计划",
    cancelling: "正在停止并保存",
    completed: "结果已保存",
    partial: "部分步骤成功",
    failed: "任务失败",
    interrupted: "任务中断",
    cancelled: "已取消",
    cancel: "取消任务",
    resume: "从保存进度继续",
    refresh: "刷新结果",
    history: "调查记录",
    log: "实时日志（最近部分）",
    retry: "重新连接进度",
    previews: "辅助裁切与变体",
    previewNote: "这些图片仅帮助观察和搜索；增强效果不能证明原图中的细节。",
    candidates: "候选与反证计划",
    rankNote:
      "排序占比不是定位正确概率。仍需 Google Lens、官网地址和实际街景核对。",
    noCandidates:
      "候选板尚无地点。可先在右侧候选记录中添加地点，再开始一轮调查。",
    test: "什么观察可以排除这个候选？",
    testSave: "保存反证计划",
    clue: "记录从原图直接观察到的线索",
    clueSave: "保存观察",
    ocrTitle: "OCR 假设（未经确认）",
    review: "逐条审阅",
    reviewed: "已核对线索",
    unclear: "仍不清楚",
    rejected: "不采用",
    note: "核对依据或剩余疑问",
    mark: "保存审阅",
    pending: "尚未审阅",
    noEvidence:
      "此处的观察、反证计划和审阅不会自动形成案卷证据或提高结论等级。",
    saved: "已保存。",
    steps: "已保存步骤",
    prepare: "准备",
    intake: "预处理",
    error: "操作未完成：",
    past: "此前审阅",
    observation: "观察内容",
    reused: "恢复会复用完整成功的步骤；失败或部分成功的步骤会重新运行。",
  },
  en: {
    title: "Local clue investigation",
    subtitle:
      "Use geo-sleuth for image details, text hypotheses and candidate falsification. No model API key needed.",
    missing: "Local tools are not configured.",
    setup: "Setup guide",
    image: "Investigation image",
    original: "Whole photo",
    ocr: "Enable OCR (may download models; check recognized text against native pixels)",
    start: "Start local investigation",
    empty: "Start with a prepared photo or native crop.",
    queued: "Queued",
    preparing: "Preparing image and board",
    processing: "Preparing visual and text clues",
    reviewing: "Compiling candidates and tests",
    cancelling: "Stopping and saving",
    completed: "Results saved",
    partial: "Partially completed",
    failed: "Task failed",
    interrupted: "Interrupted",
    cancelled: "Cancelled",
    cancel: "Cancel task",
    resume: "Resume saved progress",
    refresh: "Refresh results",
    history: "Investigation runs",
    log: "Live log (recent output)",
    retry: "Reconnect progress",
    previews: "Helper crops and variants",
    previewNote:
      "These are observation/search aids. Enhancement does not prove details in the original pixels.",
    candidates: "Candidates and falsification",
    rankNote:
      "Ranking shares are not location probabilities. Verify with Google Lens, an authoritative address and actual Street View.",
    noCandidates:
      "No places on this board. Add a candidate to the case, then start a new run.",
    test: "What observation could reject this candidate?",
    testSave: "Save falsification test",
    clue: "Record a clue directly observed in the original",
    clueSave: "Save observation",
    ocrTitle: "OCR hypotheses (unverified)",
    review: "Review each item",
    reviewed: "Clue reviewed",
    unclear: "Still unclear",
    rejected: "Do not use",
    note: "Review basis or remaining uncertainty",
    mark: "Save review",
    pending: "Not reviewed",
    noEvidence:
      "Observations, tests and reviews here do not create case evidence or raise confidence automatically.",
    saved: "Saved.",
    steps: "Saved steps",
    prepare: "Preparation",
    intake: "Preprocessing",
    error: "Could not complete: ",
    past: "Earlier reviews",
    observation: "Observation",
    reused:
      "Resuming reuses fully successful steps; failed or partial steps run again.",
  },
};
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const activeStates = new Set([
  "queued",
  "preparing",
  "processing",
  "reviewing",
  "cancelling",
]);
const retryStates = new Set(["partial", "failed", "interrupted", "cancelled"]);
export class GeoWorkbench {
  constructor({ container, request, notify }) {
    Object.assign(this, { container, request, notify });
    this.epoch = 0;
    this.urls = new Map();
    this.selected = null;
  }
  t(key) {
    return words[this.language]?.[key] || key;
  }
  async update(active, language) {
    const changed = this.caseId !== active.id;
    if (changed) {
      this.epoch++;
      this.selected = null;
      clearTimeout(this.timer);
      this.urls.forEach((url) => URL.revokeObjectURL(url));
      this.urls.clear();
      this.container.replaceChildren();
    }
    this.active = active;
    this.caseId = active.id;
    this.language = language;
    const stamp = this.epoch,
      id = this.caseId;
    try {
      const value = await this.request(`/cases/${id}/geo`);
      if (stamp !== this.epoch || id !== this.caseId) return;
      this.value = value;
      this.render();
      this.poll();
    } catch (error) {
      if (stamp === this.epoch) this.notify(error.message, true);
    }
  }
  render() {
    const oldAsset = this.container.querySelector("[name=geo-asset]")?.value;
    const ocr = this.container.querySelector("[name=geo-ocr]")?.checked;
    const busy = this.value.runs.some((r) => activeStates.has(r.status));
    const assets = [
      { path: this.active.data.source.asset, label: this.t("original") },
      ...this.active.data.crops.map((c) => ({
        path: c.native,
        label: c.label,
      })),
    ];
    this.container.innerHTML = `<div class="card-heading"><h2>${this.t("title")}</h2><span class="pill">geo-sleuth · Local</span></div><p class="hint">${this.t("subtitle")}</p>${!this.value.configured ? `<p class="research-warning">${this.t("missing")} <a href="https://github.com/xudaniel/photo-location-workflow/blob/main/docs/geo-sleuth.md" target="_blank" rel="noreferrer">${this.t("setup")} ↗</a></p>` : ""}<div class="geo-controls"><label>${this.t("image")}<select name="geo-asset">${assets.map((a) => `<option value="${esc(a.path)}" ${a.path === oldAsset ? "selected" : ""}>${esc(a.label)}</option>`).join("")}</select></label><label class="geo-checkbox"><input name="geo-ocr" type="checkbox" ${ocr ? "checked" : ""}>${this.t("ocr")}</label><button data-geo-action="start" ${busy || !this.value.configured ? "disabled" : ""}>${this.t("start")}</button></div><p class="hint">${this.t("noEvidence")}</p><label>${this.t("history")}<select name="geo-run">${this.value.runs.map((r) => `<option value="${r.id}">${esc(r.created_at)} · ${this.t(r.status)}</option>`).join("")}</select></label><div class="geo-run"></div>`;
    const select = this.container.querySelector("[name=geo-run]");
    if (!this.value.runs.some((r) => r.id === this.selected))
      this.selected = this.value.runs.at(-1)?.id;
    if (this.selected) select.value = this.selected;
    select.onchange = () => {
      this.selected = select.value;
      this.drawRun();
    };
    this.container.onclick = (event) => {
      const button = event.target.closest("[data-geo-action]");
      if (button)
        this.action(button.dataset.geoAction).catch((e) =>
          this.notify(this.t("error") + e.message, true),
        );
    };
    this.container.onsubmit = (event) => {
      const form = event.target.closest("form[data-geo-form]");
      if (!form) return;
      event.preventDefault();
      this.submit(form).catch((e) =>
        this.notify(this.t("error") + e.message, true),
      );
    };
    this.drawRun();
  }
  selectedRun() {
    return this.value.runs.find((r) => r.id === this.selected);
  }
  reviewForm(run, key) {
    const marks = run.reviews?.[key] || [],
      last = marks.at(-1);
    const current = last?.context === run.result_token ? last : null;
    return `<details><summary>${this.t("review")} · ${current ? this.t(current.verdict) : this.t("pending")}</summary><form data-geo-form="mark" data-key="${esc(key)}"><label>${this.t("review")}<select name="verdict">${["reviewed", "unclear", "rejected"].map((v) => `<option value="${v}" ${current?.verdict === v ? "selected" : ""}>${this.t(v)}</option>`).join("")}</select></label><label>${this.t("note")}<textarea name="note" maxlength="2000" required rows="2">${esc(current?.note || "")}</textarea></label><button class="secondary">${this.t("mark")}</button></form>${marks.length ? `<details><summary>${this.t("past")} (${marks.length})</summary><ul>${marks.map((m) => `<li>${esc(m.at)} · ${this.t(m.verdict)} · ${esc(m.note)}</li>`).join("")}</ul></details>` : ""}</details>`;
  }
  drawRun() {
    const run = this.selectedRun(),
      area = this.container.querySelector(".geo-run");
    if (!run) {
      area.innerHTML = `<p class="empty">${this.t("empty")}</p>`;
      return;
    }
    const busy = activeStates.has(run.status),
      result = run.result;
    const rows = Object.values(result?.board?.candidate_levels || {}).flat();
    this.renderKey = run.id + ":" + busy + ":" + (run.result_token || "");
    area.innerHTML = `<div class="geo-progress" role="status" aria-live="polite"></div><details><summary>${this.t("log")}</summary><pre class="geo-log" tabindex="0"></pre></details>${!busy && result ? `<h3>${this.t("candidates")}</h3><p class="hint">${this.t("rankNote")}</p>${rows.length ? rows.map((c) => `<article class="geo-candidate"><strong>${esc(c.name)}</strong><ul>${(result.board.falsify?.[c.name] || []).map((text) => `<li>${esc(text)}</li>`).join("")}</ul><form data-geo-form="falsify" data-candidate="${esc(c.name)}"><label>${this.t("test")}<textarea name="text" required maxlength="2000" rows="2"></textarea></label><button class="secondary">${this.t("testSave")}</button></form>${this.reviewForm(run, "candidate:" + c.name)}</article>`).join("") : `<p>${this.t("noCandidates")}</p>`}<details><summary>${this.t("clue")}</summary><form data-geo-form="clue"><label>${this.t("observation")}<textarea name="text" required maxlength="2000" rows="2"></textarea></label><button class="secondary">${this.t("clueSave")}</button></form></details>${result.board.unused_clues?.length ? `<ul>${result.board.unused_clues.map((c) => `<li>${esc(c)}</li>`).join("")}</ul>` : ""}${result.ocr_hypotheses?.length ? `<h3>${this.t("ocrTitle")}</h3>${result.ocr_hypotheses.map((c, i) => `<article class="geo-candidate"><p>${esc(c.text)}</p><small>${esc(c.pass)} · ${esc(JSON.stringify(c.box))}</small>${this.reviewForm(run, "ocr:" + i)}</article>`).join("")}` : ""}` : ""}${run.previews?.length ? `<h3>${this.t("previews")}</h3><p class="hint">${this.t("previewNote")}</p><div class="geo-previews">${run.previews.map((path, i) => `<figure><img data-preview="${i}" alt="${esc(path.split("/").at(-1))}" loading="lazy"><figcaption>${esc(path.split("/").at(-1))}</figcaption></figure>`).join("")}</div>` : ""}`;
    this.drawProgress();
    this.loadImages(run);
  }
  drawProgress() {
    const run = this.selectedRun();
    if (!run) return;
    const busy = activeStates.has(run.status);
    this.container.querySelector(".geo-progress").innerHTML =
      `<div class="research-meta"><span class="pill">${this.t(run.status)}</span><small>${esc(run.updated_at)}</small></div>${run.error ? `<p class="research-warning">${esc(run.error)}</p>` : ""}<p class="hint">${this.t("steps")}: ${
        Object.entries(run.checkpoints || {})
          .map(
            ([k, v]) =>
              `${this.t(k)} ✓${v === "partial" ? " (" + this.t("partial") + ")" : ""}`,
          )
          .join(" · ") || "—"
      }</p>${busy ? `<button class="secondary" data-geo-action="cancel" ${run.status === "cancelling" || !run.can_cancel ? "disabled" : ""}>${this.t("cancel")}</button>` : retryStates.has(run.status) ? `<button data-geo-action="resume" ${!this.value.configured ? "disabled" : ""}>${this.t("resume")}</button><p class="hint">${this.t("reused")}</p>` : ""}<button class="quiet" data-geo-action="refresh">${this.t("refresh")}</button>`;
    this.container.querySelector(".geo-log").textContent = run.log || "…";
  }
  async loadImages(run) {
    const stamp = this.epoch,
      id = this.caseId,
      selected = this.selected;
    for (const [i, path] of (run.previews || []).entries()) {
      const key = `${run.id}:${path}`;
      try {
        let url = this.urls.get(key);
        if (!url) {
          const blob = await this.request(
            `/cases/${id}/geo-image?${new URLSearchParams({ run: run.id, path })}`,
            undefined,
            true,
          );
          if (stamp !== this.epoch || id !== this.caseId) return;
          url = URL.createObjectURL(blob);
          this.urls.set(key, url);
        }
        if (selected !== this.selected) return;
        const img = this.container.querySelector(`[data-preview="${i}"]`);
        if (img) img.src = url;
      } catch (error) {
        if (stamp === this.epoch) this.notify(error.message, true);
      }
    }
  }
  async action(action) {
    const run = this.selectedRun();
    if (action === "refresh") {
      await this.reload();
      return;
    }
    let body;
    if (action === "start")
      body = {
        asset: this.container.querySelector("[name=geo-asset]").value,
        ocr: this.container.querySelector("[name=geo-ocr]").checked,
      };
    else if (action === "resume") body = { resume: run.id };
    else body = { action: "cancel", run: run.id };
    await this.send(body, action === "start");
  }
  async submit(form) {
    const data = new FormData(form),
      kind = form.dataset.geoForm,
      run = this.selectedRun();
    const body =
      kind === "mark"
        ? {
            action: "mark",
            run: run.id,
            key: form.dataset.key,
            verdict: data.get("verdict"),
            note: data.get("note"),
          }
        : {
            run: run.id,
            operation: {
              kind,
              text: data.get("text"),
              candidate: form.dataset.candidate,
            },
          };
    await this.send(body);
    this.notify(this.t("saved"));
  }
  async send(body, chooseLatest = false) {
    const id = this.caseId,
      stamp = this.epoch;
    const value = await this.request(`/cases/${id}/geo`, body);
    if (stamp !== this.epoch || id !== this.caseId) return;
    this.value = value;
    if (chooseLatest) this.selected = value.runs.at(-1)?.id;
    this.render();
    this.poll();
  }
  async reload() {
    const id = this.caseId,
      stamp = this.epoch;
    const value = await this.request(`/cases/${id}/geo`);
    if (stamp !== this.epoch || id !== this.caseId) return;
    this.value = value;
    const run = this.selectedRun();
    const key =
      run &&
      run.id +
        ":" +
        activeStates.has(run.status) +
        ":" +
        (run.result_token || "");
    if (key !== this.renderKey) this.render();
    else this.drawProgress();
    this.poll();
  }
  poll() {
    clearTimeout(this.timer);
    if (!this.value.runs.some((r) => activeStates.has(r.status))) return;
    this.timer = setTimeout(
      () =>
        this.reload().catch((e) => {
          this.notify(this.t("error") + e.message, true);
          // Retry transient failures; the explicit refresh control also remains available.
          this.poll();
        }),
      1200,
    );
  }
}
