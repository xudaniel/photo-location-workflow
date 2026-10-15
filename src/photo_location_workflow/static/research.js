const labels = {
  en: {
    title: "Research assistant",
    subtitle:
      "Analyze selected images, prepare search queries and collect source-linked hypotheses.",
    notes: "Research notes and what you have already checked",
    save: "Save progress",
    assets: "Images to analyze (up to four)",
    consent:
      "Send selected images and saved research notes to OpenAI. Uses paid API calls; web search receives the generated queries.",
    start: "Analyze and research",
    resume: "Continue saved research",
    missing:
      "Assistant is optional. Start the server with OPENAI_API_KEY or --env-file to enable it.",
    ready: "Configured",
    empty:
      "No assistant research yet. Your manual investigation remains available.",
    planning: "Analyzing images",
    searching: "Searching the web",
    completed: "Research saved",
    failed: "Research stopped",
    interrupted: "Interrupted",
    queries: "Search queries",
    questions: "Questions to check",
    sources: "Search sources (unreviewed)",
    candidates: "Suggested candidates (unverified)",
    adopt: "Add as candidate",
    adopted: "Added as candidate",
    observations: "Image observations",
    limit:
      "Web search uses text queries; Google Lens and Street View still require your review.",
    consentNeeded: "Confirm sending the selected inputs to OpenAI first.",
    saved: "Research progress saved.",
    working:
      "Research continues in the background. You can reopen this case later.",
    history: "Earlier research runs",
    original: "Whole photo",
    snapshot: "Continuing uses the images and notes saved for that run.",
    noCandidates:
      "No source-supported candidate was suggested. Continue with the search queries and questions.",
    quota:
      "OpenAI API credits or billing limit exhausted. Saved progress is retained. Check API billing before continuing.",
    runError: "The action failed: ",
  },
  zh: {
    title: "研究助手",
    subtitle: "分析选定图片，生成搜索词，整理附来源的地点假设。",
    notes: "调查笔记与已经核对的线索",
    save: "保存进度",
    assets: "发送给助手的图片（最多四张）",
    consent:
      "将选定图片和已保存的调查笔记发送给 OpenAI。会产生 API 费用；联网搜索会接收生成的搜索词。",
    start: "分析照片并检索",
    resume: "从保存的进度继续",
    missing: "助手为可选功能。启动时配置 OPENAI_API_KEY 或 --env-file 后启用。",
    ready: "已配置",
    empty: "尚未运行研究助手。可以继续使用手动调查功能。",
    planning: "正在分析图片",
    searching: "正在联网检索",
    completed: "研究结果已保存",
    failed: "研究已停止",
    interrupted: "调查中断",
    queries: "建议搜索词",
    questions: "待核对问题",
    sources: "搜索来源（未经人工核对）",
    candidates: "建议候选（尚未确认）",
    adopt: "加入候选记录",
    adopted: "已加入候选",
    observations: "照片观察",
    limit: "联网检索使用文字搜索词；Google Lens 和街景仍需实际核对。",
    consentNeeded: "请先确认将所选内容发送给 OpenAI。",
    saved: "调查进度已保存。",
    working: "助手在后台处理，可以稍后重新打开这份调查。",
    history: "之前的研究记录",
    original: "整张照片",
    snapshot: "继续时使用该次研究已保存的图片和笔记。",
    noCandidates: "尚无附搜索来源的候选。可以沿搜索词和待核对问题继续调查。",
    quota:
      "OpenAI API 余额或计费额度已耗尽，进度已保留。请先检查 API 账单，再继续。",
    runError: "操作未完成：",
  },
};
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const link = (url) => {
  try {
    const u = new URL(url);
    return ["http:", "https:"].includes(u.protocol) ? esc(u.href) : "#";
  } catch {
    return "#";
  }
};
export class ResearchWorkbench {
  constructor({ container, request, notify, onUpdate, onAdopt }) {
    Object.assign(this, { container, request, notify, onUpdate, onAdopt });
    this.caseId = null;
    this.epoch = 0;
    this.timer = null;
    this.notesTimer = null;
    this.progressQueue = Promise.resolve();
  }
  async update(active, language) {
    const changed = this.caseId !== active.id;
    if (changed && this.value && this.container.querySelector("[name=notes]"))
      await this.saveProgress();
    this.language = language;
    this.active = active;
    this.caseId = active.id;
    if (changed) {
      this.epoch++;
      clearTimeout(this.timer);
      clearTimeout(this.notesTimer);
      this.value = null;
      this.container.replaceChildren();
    }
    const stamp = this.epoch,
      id = this.caseId;
    const config = await this.request("/research");
    const value = await this.request(`/cases/${id}/research`);
    if (stamp !== this.epoch || id !== this.caseId) return;
    this.config = config;
    this.value = value;
    this.onUpdate(value, id);
    this.render();
    this.poll();
  }
  t(key) {
    return labels[this.language][key] || key;
  }
  render() {
    const notes =
      this.container.querySelector("[name=notes]")?.value ?? this.value.notes;
    const consent =
      this.container.querySelector("[name=consent]")?.checked || false;
    const selected = [
      ...this.container.querySelectorAll("[name=asset]:checked"),
    ].map((i) => i.value);
    const runs = this.value.runs,
      latest = runs.at(-1),
      running = runs.some((r) => ["planning", "searching"].includes(r.status));
    const assets = [
      { path: this.active.data.source.asset, label: this.t("original") },
      ...this.active.data.crops.map((c) => ({
        path: c.native,
        label: c.label,
      })),
    ];
    this.container.innerHTML = `<div class="card-heading"><h2>${this.t("title")}</h2><span class="pill">${this.config.configured ? this.t("ready") + " · " + esc(this.config.model) : "Optional"}</span></div><p class="hint">${this.t("subtitle")}</p>${!this.config.configured ? `<p class="research-warning">${this.t("missing")}</p>` : ""}<label>${this.t("notes")}<textarea name="notes" maxlength="6000" rows="2">${esc(notes)}</textarea></label><button class="secondary" data-action="save">${this.t("save")}</button><details class="research-inputs"><summary>${this.t("assets")}</summary><div class="research-assets">${assets.map((a, i) => `<label><input type="checkbox" name="asset" value="${esc(a.path)}" ${(selected.length ? selected.includes(a.path) : i === 0) ? "checked" : ""}>${esc(a.label)}</label>`).join("")}</div></details><label class="research-consent"><input type="checkbox" name="consent" ${consent ? "checked" : ""}>${this.t("consent")}</label><button data-action="start" ${!this.config.configured || running ? "disabled" : ""}>${this.t("start")}</button><p class="hint">${this.t("limit")}</p><div class="research-results">${latest ? this.runView(latest) : `<p class="empty">${this.t("empty")}</p>`}${
      runs.length > 1
        ? `<details><summary>${this.t("history")} (${runs.length - 1})</summary>${runs
            .slice(0, -1)
            .reverse()
            .map((r) => this.runView(r))
            .join("")}</details>`
        : ""
    }</div>`;
    this.container.onclick = (e) => {
      const b = e.target.closest("[data-action]");
      if (b)
        this.action(b).catch((error) =>
          this.notify(this.t("runError") + error.message, true),
        );
    };
    this.container.oninput = (e) => {
      if (e.target.matches("[name=notes]")) {
        clearTimeout(this.notesTimer);
        this.notesTimer = setTimeout(
          () =>
            this.saveProgress().catch((error) =>
              this.notify(error.message, true),
            ),
          700,
        );
      }
    };
    this.container.onchange = (e) => {
      if (e.target.matches("[data-question]"))
        this.saveProgress().catch((error) => this.notify(error.message, true));
    };
  }
  renderResults() {
    const runs = this.value.runs,
      latest = runs.at(-1);
    this.container.querySelector(".research-results").innerHTML = latest
      ? this.runView(latest)
      : `<p class="empty">${this.t("empty")}</p>`;
    if (runs.length > 1)
      this.container.querySelector(".research-results").innerHTML +=
        `<details><summary>${this.t("history")} (${runs.length - 1})</summary>${runs
          .slice(0, -1)
          .reverse()
          .map((r) => this.runView(r))
          .join("")}</details>`;
    this.container.querySelector("[data-action=start]").disabled =
      !this.config.configured ||
      runs.some((r) => ["planning", "searching"].includes(r.status));
  }
  runView(run) {
    const p = run.result || run.plan;
    const questions = [
      ...new Set([
        ...(run.plan?.questions || []),
        ...(run.result?.questions || []),
      ]),
    ];
    return `<article class="research-run"><div class="research-meta"><span class="pill">${this.t(run.status)}</span><small>${esc(run.created_at)} · ${esc(run.model)}</small></div>${run.error ? `<p class="research-warning">${esc(run.error_code === "quota" ? this.t("quota") : run.error)}</p>` : ""}${p ? `<p>${esc(p.summary)}</p>${run.plan?.observations?.length ? `<details><summary>${this.t("observations")}</summary><ul>${run.plan.observations.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></details>` : ""}<h3>${this.t("queries")}</h3><div class="research-queries">${[...new Set([...(run.plan?.queries || []), ...(run.result?.queries || [])])].map((q) => `<a href="https://www.google.com/search?${new URLSearchParams({ q })}" target="_blank" rel="noreferrer">${esc(q)} ↗</a>`).join("")}</div><h3>${this.t("questions")}</h3>${questions.map((q, i) => `<label class="research-question"><input type="checkbox" data-question="${run.id}-q${i}" ${this.value.resolved.includes(run.id + "-q" + i) ? "checked" : ""}>${esc(q)}</label>`).join("")}` : ""}${run.result ? `<h3>${this.t("candidates")}</h3>${run.result.candidates.length ? run.result.candidates.map((c, i) => `<div class="candidate-card"><strong>${esc(c.name)}</strong><p>${esc(c.address)}</p><p>${esc(c.reason)}</p>${c.source_urls.map((url) => `<a href="${link(url)}" target="_blank" rel="noreferrer">${esc(url)}</a>`).join("<br>")}<div><button class="secondary" data-action="adopt" data-run="${run.id}" data-index="${i}" ${c.candidate_id ? "disabled" : ""}>${this.t(c.candidate_id ? "adopted" : "adopt")}</button></div></div>`).join("") : `<p>${this.t("noCandidates")}</p>`}<details><summary>${this.t("sources")} (${run.result.sources.length})</summary><ul>${run.result.sources.map((s) => `<li><a href="${link(s.url)}" target="_blank" rel="noreferrer">${esc(s.title)}</a></li>`).join("")}</ul></details>` : ""}${["failed", "interrupted"].includes(run.status) ? `<button data-action="resume" data-run="${run.id}" ${!this.config.configured ? "disabled" : ""}>${this.t("resume")}</button><p class="hint">${this.t("snapshot")}</p>` : ""}</article>`;
  }
  async saveProgress() {
    const id = this.caseId,
      epoch = this.epoch;
    const notes = this.container.querySelector("[name=notes]").value;
    const visible = [...this.container.querySelectorAll("[data-question]")];
    const ids = new Set(visible.map((e) => e.dataset.question));
    const resolved = [
      ...this.value.resolved.filter((q) => !ids.has(q)),
      ...visible.filter((e) => e.checked).map((e) => e.dataset.question),
    ];
    this.progressQueue = this.progressQueue
      .catch(() => {})
      .then(() => this.request(`/cases/${id}/progress`, { notes, resolved }));
    const value = await this.progressQueue;
    if (epoch === this.epoch && id === this.caseId) {
      this.value = value;
      this.onUpdate(value, id);
    }
  }
  async action(button) {
    const action = button.dataset.action,
      id = this.caseId,
      epoch = this.epoch;
    if (action === "save") {
      await this.saveProgress();
      this.notify(this.t("saved"));
      return;
    }
    if (action === "adopt") {
      await this.onAdopt(button.dataset.run, Number(button.dataset.index));
      return;
    }
    if (!this.container.querySelector("[name=consent]").checked)
      throw new Error(this.t("consentNeeded"));
    button.disabled = true;
    try {
      await this.saveProgress();
      const body = {
        consent: true,
        language: this.language,
        assets: [
          ...this.container.querySelectorAll("[name=asset]:checked"),
        ].map((i) => i.value),
      };
      if (action === "resume") body.resume = button.dataset.run;
      const value = await this.request(`/cases/${id}/research`, body);
      if (epoch !== this.epoch || id !== this.caseId) return;
      this.value = value;
      this.onUpdate(value, id);
      this.render();
      this.poll();
      this.notify(this.t("working"));
    } finally {
      if (button.isConnected) button.disabled = false;
    }
  }
  poll() {
    clearTimeout(this.timer);
    if (
      !this.value.runs.some((r) => ["planning", "searching"].includes(r.status))
    )
      return;
    const id = this.caseId,
      epoch = this.epoch;
    this.timer = setTimeout(async () => {
      try {
        await this.progressQueue.catch(() => {});
        const value = await this.request(`/cases/${id}/research`);
        if (epoch !== this.epoch || id !== this.caseId) return;
        this.value = value;
        this.onUpdate(value, id);
        this.renderResults();
        this.poll();
      } catch (error) {
        this.notify(error.message, true);
      }
    }, 2500);
  }
}
