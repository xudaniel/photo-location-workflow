import { MobileConnection } from "/mobile.js";
import { GeoWorkbench } from "/geosleuth.js";
import { MapsWorkbench } from "/maps.js";
import { ResearchWorkbench } from "/research.js";
import { ComparisonWorkbench } from "/comparison.js";
("use strict");
const translations = {
  en: {
    chooseCase: "Investigations",
    cameraPhoto: "Take photo",
    localInvestigation: "Investigate",
    cropEnable: "Enable touch selection",
    cropDone: "Finish selection · scroll",
    investigations: "YOUR INVESTIGATIONS",
    newPhoto: "+ New photo",
    localOnly: "On your computer",
    eyebrow: "OBSERVE · COMPARE · VERIFY",
    title: "Every place has a story.",
    subtitle: "Turn a photograph into a trail of evidence.",
    tryDemo: "Try offline demo",
    noKey: "NO API KEY NEEDED",
    landingTitle: "Start with a scene.\nFind its story.",
    landingText:
      "Prepare an image, isolate a distinctive detail, and keep the sources behind your answer.",
    dropTitle: "Drop a photo here",
    dropHint: "or click to choose · JPG, PNG, WebP",
    uploadPrivacy:
      "Manual tools stay local. Optional AI sends only the inputs you select.",
    stepPhoto: "Photo",
    stepDetail: "Distinctive detail",
    stepEvidence: "Evidence",
    stepReport: "Report",
    scene: "SCENE WORKSPACE",
    selectHint:
      "Drag a rectangle around a distinctive detail. You can also enter pixel coordinates below.",
    detailName: "Detail name",
    scale: "Zoom",
    saveCrop: "Save detail",
    selection: "SELECTION",
    search: "SEARCH THE SCENE",
    searchTitle: "Follow the strongest clue.",
    searchHint:
      "Save the prepared image, open Google, then upload it with “Search by image”. Nothing is sent to Google automatically.",
    downloadImage: "Save search image",
    openLens: "Open Google Lens ↗",
    candidates: "Candidate places",
    addCandidate: "+ Add a candidate",
    placeName: "Place name",
    address: "Full address",
    sourceUrl: "Source URL",
    saveCandidate: "Save candidate",
    evidence: "Evidence log",
    addEvidence: "+ Add evidence",
    candidate: "Candidate",
    evidenceKind: "Source type",
    official: "Official address",
    reference: "Reference photo",
    streetview: "Street View / 360°",
    text: "Text / sign",
    verdict: "Observation",
    match: "Match",
    unclear: "Unclear",
    contradiction: "Contradiction",
    captured: "Image capture year / month",
    provider: "Provider / contributor",
    observation: "What matches or differs?",
    referenceImage: "Reference image (optional)",
    saveEvidence: "Save evidence",
    conclusion: "Your conclusion",
    confidence: "Confidence",
    high: "High confidence",
    confirmed: "Confirmed",
    unknown: "Not identified",
    reason: "Reason and remaining uncertainty",
    saveConclusion: "Save conclusion",
    exportHtml: "Download HTML",
    exportPdf: "Download PDF",
    reviewReminder:
      "Confidence is a human judgment. PDF export needs PDF support and a suitable font.",
    footer: "Local workspace · Optional AI starts only when requested",
    original: "Whole photo",
    noCandidates: "Add a candidate after checking a source.",
    noEvidence: "Keep matches, uncertainty, and conflicting details here.",
    map: "Map ↗",
    source: "Source ↗",
    cropSaved: "Detail saved.",
    saved: "Saved.",
    loading: "Working…",
    failed: "Could not complete this step: ",
    selectFirst: "Draw a rectangle or enter the crop coordinates first.",
    addFirst: "Add a candidate before recording evidence.",
    integrityOk: "✓ Local files checked",
    integrityFailed: "Some local files need attention.",
    review: "Review this observation",
    saveReview: "Save review",
    previousReviews: "Previous reviews",
    sourceImage: "Your photo",
    referencePhoto: "Reference",
    fileTooLarge: "Choose an image smaller than 32 MB.",
    exported: "Report sent to your browser. Check its download or share menu.",
    viewReport: "View report",
    newCase: "Photo prepared. Select a distinctive detail to continue.",
    demoReady:
      "Offline demo ready. This is a fictional building, not a verified location.",
  },
  zh: {
    chooseCase: "选择调查",
    cameraPhoto: "拍照",
    localInvestigation: "线索调查",
    cropEnable: "开启触摸框选",
    cropDone: "完成框选，继续滚动",
    investigations: "我的地点调查",
    newPhoto: "+ 新建照片调查",
    localOnly: "在你的电脑上运行",
    eyebrow: "观察 · 对照 · 核实",
    title: "每个地方，都有线索。",
    subtitle: "从一张照片出发，留下有据可查的答案。",
    tryDemo: "体验离线演示",
    noKey: "无需 API 密钥",
    landingTitle: "从眼前的风景，\n找到背后的地点。",
    landingText: "准备照片、框选最有辨识度的细节，再把判断与来源保存在一起。",
    dropTitle: "将照片拖到这里",
    dropHint: "或点击选择 · JPG、PNG、WebP",
    uploadPrivacy: "手动工具在本机运行；可选 AI 只发送你选定的内容。",
    stepPhoto: "准备照片",
    stepDetail: "框选细节",
    stepEvidence: "核对证据",
    stepReport: "导出报告",
    scene: "照片工作区",
    selectHint: "拖动框选独特建筑、招牌或岩块；也可以在下方输入像素坐标。",
    detailName: "细节名称",
    scale: "放大倍率",
    saveCrop: "保存局部",
    selection: "框选坐标",
    search: "沿着线索找下去",
    searchTitle: "让独特细节带路。",
    searchHint:
      "先保存准备好的图片，再打开 Google，通过“以图搜图”上传。此界面不会自动向 Google 发送照片。",
    downloadImage: "保存搜图图片",
    openLens: "打开 Google 搜图 ↗",
    candidates: "候选地点",
    addCandidate: "+ 添加候选地点",
    placeName: "地点名称",
    address: "完整地址",
    sourceUrl: "来源链接",
    saveCandidate: "保存候选",
    evidence: "证据记录",
    addEvidence: "+ 添加核对证据",
    candidate: "候选地点",
    evidenceKind: "来源类型",
    official: "官网地址",
    reference: "参考照片",
    streetview: "街景 / 360°全景",
    text: "文字 / 路牌",
    verdict: "核对结果",
    match: "吻合",
    unclear: "暂不确定",
    contradiction: "存在矛盾",
    captured: "影像拍摄年 / 月",
    provider: "影像提供者 / 贡献者",
    observation: "哪些细节吻合或不符？",
    referenceImage: "参考图片（可选）",
    saveEvidence: "保存证据",
    conclusion: "形成结论",
    confidence: "把握程度",
    high: "高把握",
    confirmed: "已核对确认",
    unknown: "尚未识别",
    reason: "判断依据与尚未确认之处",
    saveConclusion: "保存结论",
    exportHtml: "下载 HTML 报告",
    exportPdf: "下载 PDF 报告",
    reviewReminder:
      "把握等级由人工审阅决定。PDF 导出需要安装 PDF 扩展及合适字体。",
    footer: "本地工作区 · 可选 AI 由你主动启动",
    original: "整张照片",
    noCandidates: "查看来源后，在这里记录候选地点。",
    noEvidence: "把吻合点、不确定之处和反例一起留下。",
    map: "查看地图 ↗",
    source: "查看来源 ↗",
    cropSaved: "局部已保存。",
    saved: "已保存。",
    loading: "正在处理…",
    failed: "这一步未能完成：",
    selectFirst: "请先在照片上框选区域，或填写裁切坐标。",
    addFirst: "请先添加候选地点，再记录核对证据。",
    integrityOk: "✓ 本地文件检查正常",
    integrityFailed: "部分本地文件需要检查。",
    review: "复审这条观察",
    saveReview: "保存复审",
    previousReviews: "之前的复审",
    sourceImage: "原照片",
    referencePhoto: "参考影像",
    fileTooLarge: "请选择小于 32 MB 的图片。",
    exported: "已向浏览器发送报告，请查看下载或分享菜单。",
    viewReport: "打开报告",
    newCase: "照片已准备好。框选最有辨识度的细节继续。",
    demoReady: "离线演示已就绪。这是虚构建筑，不是已确认地点。",
  },
};
let cropTouchEnabled = false;
let language = localStorage.getItem("photo-location-language");
if (!["en", "zh"].includes(language))
  language = navigator.language.startsWith("zh") ? "zh" : "en";
let busy = false;
let active = null,
  chosen = null,
  selection = null,
  sceneImage = null,
  dragStart = null,
  generation = 0;
const urls = new Map();
const $ = (selector) => document.querySelector(selector);
const t = (key) => translations[language][key] || key;
const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const safeUrl = (value) => {
  try {
    const u = new URL(value);
    return ["http:", "https:"].includes(u.protocol) ? escapeHtml(u.href) : "#";
  } catch {
    return "#";
  }
};
const token = $('meta[name="local-token"]').content;

function translate() {
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  document
    .querySelectorAll("[data-i18n]")
    .forEach((e) => (e.textContent = t(e.dataset.i18n)));
  $("#language").textContent = language === "zh" ? "EN" : "中文";
  updateCropMode();
}
function notify(message, error = false) {
  const n = $("#notice");
  n.textContent = message;
  n.classList.toggle("error", error);
  n.hidden = false;
}
async function run(action) {
  if (busy) return;
  busy = true;
  document.body.classList.add("processing");
  document.body.setAttribute("aria-busy", "true");
  try {
    await action();
  } catch (error) {
    notify(t("failed") + error.message, true);
  } finally {
    busy = false;
    document.body.classList.remove("processing");
    document.body.setAttribute("aria-busy", "false");
  }
}
async function request(path, body, blob = false) {
  const options = { headers: { "X-Local-Token": token } };
  if (body !== undefined) {
    options.method = "POST";
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch("/api" + path, options);
  if (!response.ok) {
    let message = String(response.status);
    try {
      message = (await response.json()).error || message;
    } catch {}
    throw new Error(message);
  }
  return blob ? response.blob() : response.json();
}
async function imageUrl(relative) {
  const key = active.id + ":" + relative;
  if (!urls.has(key))
    urls.set(
      key,
      request(
        `/cases/${active.id}/asset?path=${encodeURIComponent(relative)}`,
        undefined,
        true,
      ).then((blob) => URL.createObjectURL(blob)),
    );
  return urls.get(key);
}
function clearUrls() {
  urls.forEach((p) =>
    p.then((url) => URL.revokeObjectURL(url)).catch(() => {}),
  );
  urls.clear();
}
async function listCases() {
  const result = await request("/cases");
  $("#version").textContent = "v" + result.version;
  $("#case-list").innerHTML = result.cases
    .map(
      (c) =>
        `<button class="case-button ${active?.id === c.id ? "active" : ""}" data-case="${escapeHtml(c.id)}"><strong>${escapeHtml(c.title)}</strong><small>${escapeHtml(t(c.level))}</small></button>`,
    )
    .join("");
  return result.cases;
}
async function openCase(id) {
  clearUrls();
  chosen = null;
  active = await request("/cases/" + encodeURIComponent(id));
  await render();
  await listCases();
}
async function mutate(action, body) {
  clearUrls();
  active = await request(`/cases/${active.id}/${action}`, body);
  await render();
  await listCases();
}
async function fileBase64(file) {
  if (file.size > 32 * 1024 * 1024) throw new Error(t("fileTooLarge"));
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Could not read image."));
    reader.onload = () => resolve(reader.result.split(",")[1]);
    reader.readAsDataURL(file);
  });
}
async function importPhoto(file) {
  if (!file) return;
  notify(t("loading"));
  clearUrls();
  chosen = null;
  active = await request("/cases", {
    image: await fileBase64(file),
    title: file.name.replace(/\.[^.]+$/, ""),
  });
  await render();
  await listCases();
  notify(t("newCase"));
}
function fieldOptions() {
  return active.data.candidates
    .map(
      (c) =>
        `<option value="${escapeHtml(c.id)}">${escapeHtml(c.name)}</option>`,
    )
    .join("");
}
async function render() {
  if (!active) return;
  const stamp = ++generation,
    data = active.data;
  $("#landing").hidden = true;
  $("#workspace").hidden = false;
  $("#view-report").hidden = !phone.value?.enabled;
  $("#view-report").href = `/view/${encodeURIComponent(active.id)}`;
  $("#case-title").textContent = data.title || active.id;
  $("#image-size").textContent = data.source.size.join(" × ") + " px";
  $("#confidence").textContent = t(data.conclusion.level);
  $("#confidence").className = "pill " + data.conclusion.level;
  if (!data.candidates.some((c) => c.id === chosen))
    chosen = data.conclusion.candidate_id || data.candidates[0]?.id || null;
  $("#candidate-list").innerHTML = data.candidates.length
    ? data.candidates
        .map(
          (c) =>
            `<div class="candidate-card ${chosen === c.id ? "selected" : ""}"><button class="candidate-select" data-candidate="${escapeHtml(c.id)}">${escapeHtml(c.name)}</button><p>${escapeHtml(c.address)}</p><a href="${safeUrl(c.maps_url)}" target="_blank" rel="noreferrer">${escapeHtml(t("map"))}</a><a href="${safeUrl(c.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(t("source"))}</a></div>`,
        )
        .join("")
    : `<p class="empty">${escapeHtml(t("noCandidates"))}</p>`;
  $("#candidate-details").open = !data.candidates.length;
  const evidence = data.evidence.filter((e) => e.candidate_id === chosen);
  $("#evidence-count").textContent = evidence.length;
  $("#evidence-list").innerHTML = evidence.length
    ? evidence
        .map(
          (e) =>
            `<article class="evidence-item"><div class="evidence-meta"><span class="pill ${escapeHtml(e.verdict)}">${escapeHtml(t(e.verdict))}</span><span>${escapeHtml(t(e.kind))}</span><span>${escapeHtml(e.captured || "")}</span></div><p>${escapeHtml(e.notes)}</p>${e.provider ? `<small class="muted">${escapeHtml(e.provider)}</small><br>` : ""}<a href="${safeUrl(e.url)}" target="_blank" rel="noreferrer">${escapeHtml(t("source"))}</a>${e.asset ? `<button type="button" class="secondary open-comparison" data-open-comparison="${escapeHtml(e.id)}">${language === "zh" ? "对照细节" : "Compare details"} · ${(e.annotations || []).length}</button><div class="evidence-compare"><figure><img data-asset="${escapeHtml(data.source.asset)}" alt="${escapeHtml(t("sourceImage"))}"><figcaption>${escapeHtml(t("sourceImage"))}</figcaption></figure><figure><img data-asset="${escapeHtml(e.asset)}" alt="${escapeHtml(t("referencePhoto"))}"><figcaption>${escapeHtml(t("referencePhoto"))}</figcaption></figure></div>` : ""}<details><summary>${escapeHtml(t("review"))}</summary><form class="review-form" data-evidence="${escapeHtml(e.id)}"><select name="verdict">${["match", "unclear", "contradiction"].map((v) => `<option value="${v}" ${v === e.verdict ? "selected" : ""}>${escapeHtml(t(v))}</option>`).join("")}</select><label>${escapeHtml(t("reason"))}<textarea name="reason" rows="2" required></textarea></label><button type="submit" class="secondary">${escapeHtml(t("saveReview"))}</button></form>${e.reviews?.length ? `<div class="review-history">${escapeHtml(t("previousReviews"))}:<br>${e.reviews.map((r) => `${escapeHtml(t(r.from))} → ${escapeHtml(t(r.to))}: ${escapeHtml(r.reason)}`).join("<br>")}</div>` : ""}</details></article>`,
        )
        .join("")
    : `<p class="empty">${escapeHtml(t("noEvidence"))}</p>`;
  for (const form of ["#evidence-form", "#conclusion-form"]) {
    $(form + " select[name=candidate]").innerHTML = fieldOptions();
    if (chosen) $(form + " select[name=candidate]").value = chosen;
  }
  $("#conclusion-form select[name=level]").value = [
    "high",
    "confirmed",
  ].includes(data.conclusion.level)
    ? data.conclusion.level
    : "candidate";
  const note = data.conclusion.note || "";
  $("#conclusion-form textarea").value =
    /^(Awaiting|New evidence|Evidence reviewed|Comparison annotations|Map location changed|Map viewpoint changed)/.test(
      note,
    )
      ? ""
      : note;
  $("#integrity").textContent = active.integrity.ok
    ? t("integrityOk")
    : t("integrityFailed");
  $("#integrity").classList.toggle("error", !active.integrity.ok);
  $("#crop-label").value = "detail-" + (data.crops.length + 1);
  $("#crop-list").innerHTML = data.crops
    .map(
      (c) =>
        `<button class="crop-thumb" data-crop="${escapeHtml(c.native)}"><img data-asset="${escapeHtml(c.native)}" alt="${escapeHtml(c.label)}">${escapeHtml(c.label)} · ${c.box[2]}×${c.box[3]}</button>`,
    )
    .join("");
  $("#search-asset").innerHTML =
    `<option value="${escapeHtml(data.source.asset)}">${escapeHtml(t("original"))}</option>` +
    data.crops
      .map(
        (c) =>
          `<option value="${escapeHtml(c.native)}">${escapeHtml(c.label)}</option>`,
      )
      .join("");
  document.querySelectorAll("img[data-asset]").forEach(async (img) => {
    try {
      const url = await imageUrl(img.dataset.asset);
      if (stamp === generation) img.src = url;
    } catch (error) {
      if (stamp === generation) notify(error.message, true);
    }
  });
  const url = await imageUrl(data.source.asset);
  const image = new Image();
  await new Promise((resolve, reject) => {
    image.onload = resolve;
    image.onerror = reject;
    image.src = url;
  });
  if (stamp !== generation) return;
  sceneImage = image;
  selection = null;
  ["x", "y", "w", "h"].forEach(
    (key) => ($("#crop-form [name=" + key + "]").value = ""),
  );
  const canvas = $("#crop-canvas");
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  draw();
  translate();
  await comparison.update(active, chosen);
  await research.update(active, language);
  await geo.update(active, language);
  maps.update(active, chosen, language);
}
function draw() {
  if (!sceneImage) return;
  const canvas = $("#crop-canvas"),
    context = canvas.getContext("2d");
  context.drawImage(sceneImage, 0, 0);
  if (selection) {
    const [x, y, w, h] = selection;
    context.strokeStyle = "#f7d174";
    context.fillStyle = "rgba(245,212,127,.15)";
    context.lineWidth = Math.max(2, canvas.width / 350);
    context.setLineDash([canvas.width / 100, canvas.width / 150]);
    context.fillRect(x, y, w, h);
    context.strokeRect(x, y, w, h);
    context.setLineDash([]);
  }
}
function point(event) {
  const c = $("#crop-canvas"),
    r = c.getBoundingClientRect();
  return [
    Math.max(
      0,
      Math.min(
        c.width,
        Math.round(((event.clientX - r.left) * c.width) / r.width),
      ),
    ),
    Math.max(
      0,
      Math.min(
        c.height,
        Math.round(((event.clientY - r.top) * c.height) / r.height),
      ),
    ),
  ];
}
function updateSelection() {
  if (!selection) return;
  ["x", "y", "w", "h"].forEach(
    (key, i) => ($("#crop-form [name=" + key + "]").value = selection[i]),
  );
  draw();
}
$("#crop-canvas").addEventListener("pointerdown", (event) => {
  if (
    !event.isPrimary ||
    event.button !== 0 ||
    (event.pointerType === "touch" && !cropTouchEnabled)
  )
    return;
  dragStart = point(event);
  event.currentTarget.setPointerCapture(event.pointerId);
});
$("#crop-canvas").addEventListener("pointermove", (event) => {
  if (!dragStart) return;
  const p = point(event);
  selection = [
    Math.min(p[0], dragStart[0]),
    Math.min(p[1], dragStart[1]),
    Math.abs(p[0] - dragStart[0]),
    Math.abs(p[1] - dragStart[1]),
  ];
  updateSelection();
});
$("#crop-canvas").addEventListener("pointerup", (event) => {
  dragStart = null;
  if (event.pointerType === "touch") {
    cropTouchEnabled = false;
    updateCropMode();
  }
});
$("#crop-canvas").addEventListener("pointercancel", () => {
  dragStart = null;
});
$("#crop-form").addEventListener("input", () => {
  const f = new FormData($("#crop-form"));
  selection = ["x", "y", "w", "h"].map((k) => Number(f.get(k)));
  draw();
});
$("#crop-form").addEventListener("submit", (event) => {
  event.preventDefault();
  run(async () => {
    const f = new FormData(event.target),
      box = ["x", "y", "w", "h"].map((k) => Number(f.get(k)));
    if (box[2] <= 0 || box[3] <= 0) throw new Error(t("selectFirst"));
    await mutate("crop", {
      box,
      label: f.get("label"),
      scale: Number(f.get("scale")),
    });
    notify(t("cropSaved"));
  });
});
$("#candidate-form").addEventListener("submit", (event) => {
  event.preventDefault();
  run(async () => {
    await mutate("candidate", Object.fromEntries(new FormData(event.target)));
    event.target.reset();
    notify(t("saved"));
  });
});
$("#evidence-form").addEventListener("submit", (event) => {
  event.preventDefault();
  run(async () => {
    if (!active.data.candidates.length) throw new Error(t("addFirst"));
    const body = Object.fromEntries(new FormData(event.target));
    body.image = body.image?.size ? await fileBase64(body.image) : null;
    await mutate("evidence", body);
    event.target.reset();
    event.target.elements.candidate.value = chosen;
    event.target.elements.captured.required = false;
    notify(t("saved"));
  });
});
$("#evidence-form select[name=kind]").addEventListener("change", (event) => {
  const f = $("#evidence-form [name=captured]");
  f.required = event.target.value === "streetview";
  if (f.required && !f.value) f.value = "unknown";
});
$("#conclusion-form").addEventListener("submit", (event) => {
  event.preventDefault();
  run(async () => {
    if (!active.data.candidates.length) throw new Error(t("addFirst"));
    await mutate("conclude", Object.fromEntries(new FormData(event.target)));
    notify(t("saved"));
  });
});
$("#evidence-list").addEventListener("submit", (event) => {
  if (!event.target.matches(".review-form")) return;
  event.preventDefault();
  run(async () => {
    await mutate("review", {
      ...Object.fromEntries(new FormData(event.target)),
      evidence: event.target.dataset.evidence,
    });
    notify(t("saved"));
  });
});
$("#case-list").addEventListener("click", (event) => {
  const button = event.target.closest("[data-case]");
  if (button) run(() => openCase(button.dataset.case));
});
$("#candidate-list").addEventListener("click", (event) => {
  const button = event.target.closest("[data-candidate]");
  if (button)
    run(async () => {
      chosen = button.dataset.candidate;
      await render();
    });
});
$("#crop-list").addEventListener("click", (event) => {
  const button = event.target.closest("[data-crop]");
  if (button) $("#search-asset").value = button.dataset.crop;
});
function download(blob, name) {
  const url = URL.createObjectURL(blob),
    a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
$("#download-image").addEventListener("click", () =>
  run(async () =>
    download(
      await request(
        `/cases/${active.id}/asset?path=${encodeURIComponent($("#search-asset").value)}`,
        undefined,
        true,
      ),
      "photo-location-search.png",
    ),
  ),
);
for (const format of ["html", "pdf"])
  $("#export-" + format).addEventListener("click", () =>
    run(async () => {
      download(
        await request(
          `/cases/${active.id}/report?format=${format}`,
          undefined,
          true,
        ),
        "photo-location-report." + format,
      );
      notify(t("exported"));
    }),
  );
$("#language").addEventListener("click", () =>
  run(async () => {
    language = language === "zh" ? "en" : "zh";
    localStorage.setItem("photo-location-language", language);
    await phone.update(language);
    $("#notice").hidden = true;
    translate();
    if (active) await render();
    await listCases();
  }),
);
function updateCropMode() {
  const button = $("#crop-mode"),
    canvas = $("#crop-canvas");
  button.textContent = t(cropTouchEnabled ? "cropDone" : "cropEnable");
  button.setAttribute("aria-pressed", String(cropTouchEnabled));
  canvas.dataset.selecting = String(cropTouchEnabled);
}
$("#crop-mode").addEventListener("click", () => {
  cropTouchEnabled = !cropTouchEnabled;
  updateCropMode();
});
$("#case-toggle").addEventListener("click", () => {
  const button = $("#case-toggle"),
    open = button.getAttribute("aria-expanded") !== "true";
  button.setAttribute("aria-expanded", String(open));
  $("#case-list").dataset.open = String(open);
});
$("#camera-photo").addEventListener("click", () => $("#camera-input").click());
$("#camera-input").addEventListener("change", (event) =>
  run(() => importPhoto(event.target.files[0])),
);
$("#new-photo").addEventListener("click", () => $("#photo-input").click());
$("#drop-zone").addEventListener("click", () => $("#photo-input").click());
$("#photo-input").addEventListener("change", (event) =>
  run(async () => {
    await importPhoto(event.target.files[0]);
    event.target.value = "";
  }),
);
$("#drop-zone").addEventListener("dragover", (event) => {
  event.preventDefault();
  event.currentTarget.classList.add("dragging");
});
$("#drop-zone").addEventListener("dragleave", (event) =>
  event.currentTarget.classList.remove("dragging"),
);
$("#drop-zone").addEventListener("drop", (event) => {
  event.preventDefault();
  event.currentTarget.classList.remove("dragging");
  run(() => importPhoto(event.dataTransfer.files[0]));
});
$("#demo").addEventListener("click", () =>
  run(async () => {
    clearUrls();
    chosen = null;
    active = await request("/demo", {});
    await render();
    await listCases();
    notify(t("demoReady"));
  }),
);
const phone = new MobileConnection({
  container: $("#phone-connection"),
  request,
  notify,
});
const geo = new GeoWorkbench({
  container: $("#geo-workspace"),
  request,
  notify,
});
const maps = new MapsWorkbench({
  container: $("#maps-workspace"),
  request,
  mutate,
  run,
  notify,
  fileBase64,
  download,
});
const research = new ResearchWorkbench({
  container: $("#research-workspace"),
  request,
  notify,
  onUpdate: (value, id) => {
    if (active?.id === id) active.data.research = value;
  },
  onAdopt: async (runId, index) => {
    await mutate("adopt", { run: runId, index });
  },
});
const comparison = new ComparisonWorkbench({
  container: $("#comparison-workspace"),
  imageUrl,
  notify,
  onSave: (body, done) =>
    run(async () => {
      await mutate("annotate", body);
      done();
      notify(t("saved"));
    }),
  onRemove: (body) =>
    run(async () => {
      await mutate("unannotate", body);
      notify(t("saved"));
    }),
});
$("#evidence-list").addEventListener("click", (event) => {
  const button = event.target.closest("[data-open-comparison]");
  if (button) comparison.open(button.dataset.openComparison);
});
translate();
run(async () => {
  await phone.update(language);
  const cases = await listCases();
  if (cases.length) await openCase(cases[0].id);
});
