/* Paired regions use original image pixels. Viewports use normalized centers. */
const words = {
  en: {
    zoomIn: "Zoom in",
    zoomOut: "Zoom out",
    title: "Compare the details.",
    kicker: "PAIRED IMAGE WORKSPACE",
    evidence: "Evidence image",
    pan: "Move images",
    scroll: "Scroll page",
    mark: "Draw regions",
    sync: "Sync dragging",
    fit: "Fit both",
    zoom: "Zoom",
    source: "Source photo",
    reference: "Reference image",
    hint: "Move: drag to inspect. Draw: select the same detail in each image, name it, then save. Click a saved number to focus both views. Zoom with the controls or Ctrl/⌘ + wheel.",
    label: "Detail description",
    save: "Save paired detail",
    clear: "Clear selection",
    empty: "No paired details yet.",
    remove: "Remove",
    removed: "Removed annotations are retained in the exported history.",
    missing: "Draw a region in both images and enter a description.",
    focused: "Focused detail",
    pixels: "Regions in original pixels: x, y, width, height.",
    sourceBox: "Source region",
    referenceBox: "Reference region",
    noImage: "Choose evidence with an attached image.",
    open: "Compare details",
    reason: "Removed from the comparison workbench.",
  },
  zh: {
    zoomIn: "放大",
    zoomOut: "缩小",
    title: "把对应细节放在一起。",
    kicker: "双图细节对照",
    evidence: "选择证据影像",
    pan: "移动图片",
    scroll: "滚动页面",
    mark: "框选细节",
    sync: "同步拖动",
    fit: "适应双图",
    zoom: "缩放",
    source: "原照片",
    reference: "参考影像",
    hint: "移动模式下拖动查看；框选模式下，在两图分别圈出同一细节，命名后保存。点击编号定位两侧区域；使用按钮或 Ctrl/⌘ + 滚轮缩放。",
    label: "细节说明",
    save: "保存对应标注",
    clear: "清空框选",
    empty: "尚无对应细节标注。",
    remove: "移除",
    removed: "移除的标注仍保留在导出报告的历史中。",
    missing: "请在两图分别框选区域，并填写细节说明。",
    focused: "当前定位细节",
    pixels: "坐标使用原图像素：X、Y、宽度、高度。",
    sourceBox: "原图区域",
    referenceBox: "参考图区域",
    noImage: "请选择附有图片的证据。",
    open: "对照细节",
    reason: "从双图对照工作台移除。",
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
const clamp = (value) => Math.min(1, Math.max(0, value));
export class ComparisonWorkbench {
  constructor({ container, imageUrl, onSave, onRemove, notify }) {
    Object.assign(this, { container, imageUrl, onSave, onRemove, notify });
    this.images = [];
    this.centers = [
      { x: 0.5, y: 0.5 },
      { x: 0.5, y: 0.5 },
    ];
    this.zoom = 1;
    this.drafts = [null, null];
    this.mode = matchMedia("(pointer: coarse)").matches ? "scroll" : "pan";
    this.serial = 0;
    container.innerHTML = `<div class="card-heading"><div><span class="eyebrow" data-ci18n="kicker"></span><h2 data-ci18n="title"></h2></div><label class="comparison-evidence-label"><span data-ci18n="evidence"></span><select class="comparison-evidence"></select></label></div>
    <p class="hint" data-ci18n="hint"></p><div class="comparison-toolbar"><div class="mode-buttons"><button type="button" class="secondary" data-mode="scroll" data-ci18n="scroll"></button><button type="button" data-mode="pan" data-ci18n="pan"></button><button type="button" class="secondary" data-mode="mark" data-ci18n="mark"></button></div><label class="sync-control"><input class="sync-views" type="checkbox" checked><span data-ci18n="sync"></span></label><div class="zoom-controls"><button type="button" class="secondary" data-zoom="-1" aria-label="Zoom out">−</button><label><span data-ci18n="zoom"></span><input class="comparison-zoom" type="range" min="1" max="12" step="0.25" value="1"></label><output class="zoom-value">1×</output><button type="button" class="secondary" data-zoom="1" aria-label="Zoom in">+</button></div><button type="button" class="secondary fit-views" data-ci18n="fit"></button></div>
    <div class="comparison-viewports">${[0, 1].map((side) => `<figure><figcaption data-ci18n="${side ? "reference" : "source"}"></figcaption><canvas class="comparison-canvas" data-side="${side}" aria-label="${side ? "Reference comparison canvas" : "Source comparison canvas"}" tabindex="0"></canvas></figure>`).join("")}</div>
    <form class="annotation-form"><div class="annotation-fields">${[0, 1].map((side) => `<fieldset data-side="${side}"><legend data-ci18n="${side ? "referenceBox" : "sourceBox"}"></legend>${["x", "y", "w", "h"].map((key, i) => `<label>${["X", "Y", "W", "H"][i]}<input name="${side}-${key}" type="number" min="${i < 2 ? 0 : 1}" required aria-label="${side ? "Reference" : "Source"} region ${key}"></label>`).join("")}</fieldset>`).join("")}</div><p class="hint" data-ci18n="pixels"></p><div class="annotation-save"><label><span data-ci18n="label"></span><input name="label" required maxlength="160"></label><button type="submit" data-ci18n="save"></button><button type="button" class="secondary clear-regions" data-ci18n="clear"></button></div></form><div class="annotation-list"></div><p class="hint annotation-history-note" data-ci18n="removed" hidden></p>`;
    this.canvases = [...container.querySelectorAll("canvas")];
    this.select = container.querySelector(".comparison-evidence");
    this.select.addEventListener("change", () =>
      this.loadEvidence(this.select.value).catch((e) =>
        this.notify(e.message, true),
      ),
    );
    container.querySelectorAll("[data-mode]").forEach((button) =>
      button.addEventListener("click", () => {
        this.mode = button.dataset.mode;
        this.setMode();
      }),
    );
    container
      .querySelector(".comparison-zoom")
      .addEventListener("input", (event) =>
        this.setZoom(Number(event.target.value)),
      );
    container
      .querySelectorAll("[data-zoom]")
      .forEach((button) =>
        button.addEventListener("click", () =>
          this.setZoom(this.zoom + Number(button.dataset.zoom) * 0.5),
        ),
      );
    container.querySelector(".fit-views").addEventListener("click", () => {
      this.centers = [
        { x: 0.5, y: 0.5 },
        { x: 0.5, y: 0.5 },
      ];
      this.focused = null;
      this.setZoom(1);
      this.renderList();
    });
    container.querySelector(".clear-regions").addEventListener("click", () => {
      this.drafts = [null, null];
      container.querySelector(".annotation-form").reset();
      this.draw();
    });
    container
      .querySelector(".annotation-form")
      .addEventListener("input", (event) => {
        if (event.target.name === "label") return;
        this.readFields();
        this.draw();
      });
    container
      .querySelector(".annotation-form")
      .addEventListener("submit", (event) => {
        event.preventDefault();
        this.readFields();
        const label = event.target.elements.label.value.trim();
        if (
          !label ||
          this.drafts.some((box) => !box || box[2] <= 0 || box[3] <= 0)
        )
          return this.notify(this.w("missing"), true);
        this.onSave(
          {
            evidence: this.evidence.id,
            label,
            source_box: this.drafts[0],
            reference_box: this.drafts[1],
          },
          () => this.clearDrafts(),
        );
      });
    container
      .querySelector(".annotation-list")
      .addEventListener("click", (event) => {
        const focus = event.target.closest("[data-focus-region]"),
          remove = event.target.closest("[data-remove-region]");
        if (focus) this.focus(focus.dataset.focusRegion);
        if (remove)
          this.onRemove({
            evidence: this.evidence.id,
            annotation: remove.dataset.removeRegion,
            reason: this.w("reason"),
          });
      });
    this.canvases.forEach((canvas, side) => {
      canvas.addEventListener("pointerdown", (event) => {
        if (
          this.images.length !== 2 ||
          this.mode === "scroll" ||
          !event.isPrimary ||
          event.button !== 0
        )
          return;
        canvas.setPointerCapture(event.pointerId);
        this.drag = {
          side,
          start: this.imagePoint(event, side),
          client: [event.clientX, event.clientY],
          centers: this.centers.map((c) => ({ ...c })),
        };
        if (this.mode === "mark") {
          this.drafts[side] = null;
          this.focused = null;
          this.draw();
        }
      });
      canvas.addEventListener("pointermove", (event) => {
        if (!this.drag || this.drag.side !== side) return;
        const drag = this.drag;
        if (this.mode === "pan") {
          const g = this.geometry(side),
            dx =
              (event.clientX - drag.client[0]) /
              (this.images[side].width * g.scale),
            dy =
              (event.clientY - drag.client[1]) /
              (this.images[side].height * g.scale);
          const targets = container.querySelector(".sync-views").checked
            ? [0, 1]
            : [side];
          targets.forEach(
            (i) =>
              (this.centers[i] = {
                x: clamp(drag.centers[i].x - dx),
                y: clamp(drag.centers[i].y - dy),
              }),
          );
        } else {
          const p = this.imagePoint(event, side);
          this.drafts[side] = [
            Math.min(p[0], drag.start[0]),
            Math.min(p[1], drag.start[1]),
            Math.abs(p[0] - drag.start[0]),
            Math.abs(p[1] - drag.start[1]),
          ];
          this.writeFields();
        }
        this.draw();
      });
      canvas.addEventListener("pointerup", () => {
        this.drag = null;
      });
      canvas.addEventListener("pointercancel", () => {
        this.drag = null;
      });
      canvas.addEventListener(
        "wheel",
        (event) => {
          if (!event.ctrlKey && !event.metaKey) return;
          event.preventDefault();
          this.setZoom(this.zoom + (event.deltaY < 0 ? 0.5 : -0.5));
        },
        { passive: false },
      );
      canvas.addEventListener("keydown", (event) => {
        if (event.key === "+" || event.key === "=") {
          event.preventDefault();
          this.setZoom(this.zoom + 0.5);
        } else if (event.key === "-") {
          event.preventDefault();
          this.setZoom(this.zoom - 0.5);
        }
      });
    });
    this.resizeObserver = new ResizeObserver(() => this.draw());
    this.canvases.forEach((c) => this.resizeObserver.observe(c));
    this.setMode();
  }
  w(key) {
    return (
      words[document.documentElement.lang.startsWith("zh") ? "zh" : "en"][
        key
      ] || key
    );
  }
  setMode() {
    this.container.querySelectorAll("[data-mode]").forEach((b) => {
      const selected = b.dataset.mode === this.mode;
      b.setAttribute("aria-pressed", String(selected));
      b.classList.toggle("secondary", !selected);
    });
    this.canvases.forEach((c) => {
      c.style.cursor =
        this.mode === "mark"
          ? "crosshair"
          : this.mode === "scroll"
            ? "auto"
            : "grab";
      c.style.touchAction = this.mode === "scroll" ? "pan-y" : "none";
    });
  }
  clearDrafts() {
    this.drafts = [null, null];
    this.container.querySelector(".annotation-form").reset();
    this.draw();
  }
  readFields() {
    this.drafts = [0, 1].map((side) => {
      const inputs = ["x", "y", "w", "h"].map((key) =>
        this.container.querySelector(`[name="${side}-${key}"]`),
      );
      return inputs.some((input) => input.value === "")
        ? null
        : inputs.map((input) => Number(input.value));
    });
  }
  writeFields() {
    for (let side = 0; side < 2; side++)
      ["x", "y", "w", "h"].forEach(
        (key, i) =>
          (this.container.querySelector(`[name="${side}-${key}"]`).value =
            this.drafts[side]?.[i] ?? ""),
      );
  }
  async update(state, candidate) {
    this.caseId = state.id;
    this.data = state.data;
    this.available = state.data.evidence.filter(
      (e) => e.candidate_id === candidate && e.asset,
    );
    this.container.hidden = !this.available.length;
    if (this.container.hidden) {
      this.evidence = null;
      this.key = null;
      this.serial++;
      return;
    }
    this.container
      .querySelectorAll("[data-ci18n]")
      .forEach((e) => (e.textContent = this.w(e.dataset.ci18n)));
    this.select.setAttribute("aria-label", this.w("evidence"));
    this.container
      .querySelector('[data-zoom="1"]')
      .setAttribute("aria-label", this.w("zoomIn"));
    this.container
      .querySelector('[data-zoom="-1"]')
      .setAttribute("aria-label", this.w("zoomOut"));
    this.canvases.forEach((canvas, side) =>
      canvas.setAttribute("aria-label", this.w(side ? "reference" : "source")),
    );
    [0, 1].forEach((side) =>
      ["x", "y", "w", "h"].forEach((key) =>
        this.container
          .querySelector(`[name="${side}-${key}"]`)
          .setAttribute(
            "aria-label",
            this.w(side ? "referenceBox" : "sourceBox") +
              " " +
              key.toUpperCase(),
          ),
      ),
    );

    const previous = this.evidence?.id;
    this.select.innerHTML = this.available
      .map(
        (e) =>
          `<option value="${esc(e.id)}">${esc(e.id)} · ${esc(e.notes.slice(0, 75))}</option>`,
      )
      .join("");
    const id = this.available.some((e) => e.id === previous)
      ? previous
      : this.available[0].id;
    this.select.value = id;
    await this.loadEvidence(id);
  }
  async loadEvidence(id) {
    const evidence = this.available.find((e) => e.id === id);
    if (!evidence) return;
    this.evidence = evidence;
    this.select.value = id;
    const key =
      this.caseId +
      ":" +
      id +
      ":" +
      (evidence.sha256 || "") +
      ":" +
      (this.data.source.sha256 || "");
    if (this.key !== key) {
      const serial = ++this.serial;
      this.key = key;
      this.images = [];
      this.centers = [
        { x: 0.5, y: 0.5 },
        { x: 0.5, y: 0.5 },
      ];
      this.zoom = 1;
      this.focused = null;
      this.clearDrafts();
      const images = await Promise.all(
        [this.data.source.asset, evidence.asset].map(async (relative) => {
          const url = await this.imageUrl(relative);
          const image = new Image();
          await new Promise((resolve, reject) => {
            image.onload = resolve;
            image.onerror = () => reject(new Error(this.w("noImage")));
            image.src = url;
          });
          return image;
        }),
      );
      if (serial !== this.serial) return;
      this.images = images;
    }
    if (!(evidence.annotations || []).some((a) => a.id === this.focused))
      this.focused = null;
    this.setZoom(this.zoom);
    this.renderList();
  }
  renderList() {
    const items = this.evidence?.annotations || [];
    this.container.querySelector(".annotation-list").innerHTML = items.length
      ? items
          .map(
            (a) =>
              `<div class="annotation-row"><button type="button" class="region-focus secondary" data-focus-region="${esc(a.id)}" aria-pressed="${a.id === this.focused}"><span class="region-number">${a.number}</span><span>${esc(a.label)}</span></button><button type="button" class="quiet region-remove" data-remove-region="${esc(a.id)}" aria-label="${esc(this.w("remove") + " " + a.number)}">${esc(this.w("remove"))}</button></div>`,
          )
          .join("")
      : `<p class="empty">${esc(this.w("empty"))}</p>`;
    this.container.querySelector(".annotation-history-note").hidden =
      !this.evidence?.annotation_history?.length;
  }
  open(id) {
    if (this.available?.some((e) => e.id === id)) {
      this.loadEvidence(id)
        .then(() =>
          this.container.scrollIntoView({ behavior: "smooth", block: "start" }),
        )
        .catch((e) => this.notify(e.message, true));
    }
  }
  geometry(side) {
    const canvas = this.canvases[side],
      rect = canvas.getBoundingClientRect(),
      image = this.images[side];
    const scale =
      Math.min(rect.width / image.width, rect.height / image.height) *
      this.zoom;
    return {
      width: rect.width,
      height: rect.height,
      scale,
      left: rect.width / 2 - this.centers[side].x * image.width * scale,
      top: rect.height / 2 - this.centers[side].y * image.height * scale,
    };
  }
  imagePoint(event, side) {
    const r = this.canvases[side].getBoundingClientRect(),
      g = this.geometry(side),
      image = this.images[side];
    return [
      Math.round(
        Math.max(
          0,
          Math.min(image.width, (event.clientX - r.left - g.left) / g.scale),
        ),
      ),
      Math.round(
        Math.max(
          0,
          Math.min(image.height, (event.clientY - r.top - g.top) / g.scale),
        ),
      ),
    ];
  }
  setZoom(zoom) {
    this.zoom = Math.max(1, Math.min(12, Math.round(zoom * 4) / 4));
    this.container.querySelector(".comparison-zoom").value = this.zoom;
    this.container.querySelector(".zoom-value").textContent = this.zoom + "×";
    this.draw();
  }
  focus(id) {
    const a = (this.evidence?.annotations || []).find((a) => a.id === id);
    if (!a || this.images.length !== 2) return;
    const boxes = [a.source_box, a.reference_box];
    this.centers = boxes.map((b, i) => ({
      x: (b[0] + b[2] / 2) / this.images[i].width,
      y: (b[1] + b[3] / 2) / this.images[i].height,
    }));
    this.zoom = 1;
    const zoom = Math.min(
      ...boxes.map((b, i) => {
        const g = this.geometry(i);
        return (
          0.72 *
          Math.min(g.width / (b[2] * g.scale), g.height / (b[3] * g.scale))
        );
      }),
    );
    this.focused = id;
    this.setZoom(zoom);
    this.renderList();
    this.container
      .querySelector(".comparison-viewports")
      .scrollIntoView({ behavior: "smooth", block: "center" });
    this.canvases[0].focus({ preventScroll: true });
  }
  draw() {
    if (this.images.length !== 2 || this.container.hidden) return;
    this.canvases.forEach((canvas, side) => {
      const g = this.geometry(side);
      if (!g.width || !g.height) return;
      const dpr = window.devicePixelRatio || 1;
      const width = Math.round(g.width * dpr),
        height = Math.round(g.height * dpr);
      if (canvas.width !== width) canvas.width = width;
      if (canvas.height !== height) canvas.height = height;
      const c = canvas.getContext("2d");
      c.setTransform(dpr, 0, 0, dpr, 0, 0);
      c.clearRect(0, 0, g.width, g.height);
      c.imageSmoothingEnabled = this.zoom <= 2;
      c.drawImage(
        this.images[side],
        g.left,
        g.top,
        this.images[side].width * g.scale,
        this.images[side].height * g.scale,
      );
      const badges = [];
      const box = (region, number, selected, draft = false) => {
        const [x, y, w, h] = region,
          px = g.left + x * g.scale,
          py = g.top + y * g.scale,
          pw = w * g.scale,
          ph = h * g.scale;
        c.lineWidth = selected ? 3 : 2;
        c.strokeStyle = draft ? "#fef8d8" : "#e8ba50";
        c.fillStyle = draft ? "rgba(255,239,166,.18)" : "rgba(232,186,80,.07)";
        c.setLineDash(draft ? [7, 4] : []);
        c.fillRect(px, py, pw, ph);
        c.strokeRect(px, py, pw, ph);
        c.setLineDash([]);
        if (
          number &&
          px + pw >= 0 &&
          py + ph >= 0 &&
          px < g.width &&
          py < g.height
        )
          badges.push({
            x: px,
            y: py,
            right: px + pw,
            bottom: py + ph,
            number,
          });
      };
      (this.evidence?.annotations || []).forEach((a) =>
        box(
          a[side ? "reference_box" : "source_box"],
          a.number,
          a.id === this.focused,
        ),
      );
      if (this.drafts[side]) box(this.drafts[side], null, false, true);
      const occupied = [];
      c.font = "bold 13px system-ui";
      for (const badge of badges) {
        const bw = c.measureText(String(badge.number)).width + 14,
          bh = 23;
        const positions = [
          [badge.x, badge.y],
          [badge.right - bw, badge.y],
          [badge.x, badge.bottom - bh],
          [badge.right - bw, badge.bottom - bh],
          [badge.x, badge.y - bh - 3],
          [badge.x, badge.bottom + 3],
          ...Array.from({ length: 11 }, (_, i) => [
            badge.x,
            badge.y + (i + 1) * (bh + 3),
          ]),
        ];
        let position = null;
        for (const [x, y] of positions) {
          const bx = Math.max(0, Math.min(x, g.width - bw)),
            by = Math.max(0, Math.min(y, g.height - bh)),
            r = [bx, by, bx + bw, by + bh];
          if (
            !occupied.some(
              (o) =>
                r[0] < o[2] + 2 &&
                r[2] + 2 > o[0] &&
                r[1] < o[3] + 2 &&
                r[3] + 2 > o[1],
            )
          ) {
            occupied.push(r);
            position = [bx, by];
            break;
          }
        }
        const [bx, by] = position || [badge.x, badge.y];
        c.fillStyle = "#173e32";
        c.fillRect(bx, by, bw, bh);
        c.fillStyle = "#ffe39d";
        c.fillText(String(badge.number), bx + 7, by + 16);
      }
    });
  }
}
