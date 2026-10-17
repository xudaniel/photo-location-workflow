const words = {
  zh: {
    title: "手机连接",
    hint: "手机和电脑需在同一可信 Wi‑Fi，电脑保持运行。扫描二维码，或打开地址并输入连接码。",
    code: "连接码",
    url: "手机访问地址",
    link: "扫码连接链接",
    copy: "复制连接链接",
    selected: "链接已选中，请复制。",
    copied: "连接链接已复制。",
    devices: "已连接手机",
    revoke: "断开全部手机并更换连接码",
    disconnect: "断开本设备",
    connected: "已连接电脑工作台",
    plain: "通过局域网 HTTP 传输；请勿做公网端口转发。",
    noQR: "安装 mobile 扩展可显示二维码，连接码仍可使用。",
  },
  en: {
    title: "Connect a phone",
    hint: "Keep both devices on the same trusted Wi‑Fi and leave the computer running. Scan the QR code, or open the address and enter the code.",
    code: "Connection code",
    url: "Phone address",
    link: "Pairing link",
    copy: "Copy pairing link",
    selected: "Link selected. Copy it to continue.",
    copied: "Pairing link copied.",
    devices: "Connected phones",
    revoke: "Disconnect phones and rotate code",
    disconnect: "Disconnect this device",
    connected: "Connected to your computer",
    plain:
      "Uses HTTP over your LAN. Do not forward this port to the public internet.",
    noQR: "Install the mobile extra for QR codes; the code still works.",
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
export class MobileConnection {
  constructor({ container, request, notify }) {
    Object.assign(this, { container, request, notify });
  }
  async update(language) {
    this.language = language;
    const value = await this.request("/mobile");
    this.value = value;
    this.container.hidden = !value.enabled;
    if (!value.enabled) return;
    const t = words[language];
    this.container.innerHTML = `<details><summary>${value.admin ? t.title : t.connected}</summary>${value.admin ? `<p>${t.hint}</p><div class="phone-share"><div class="phone-qr"></div><div><label>${t.url}<input readonly name="phone-url" value="${esc(value.url)}"></label><p>${t.code}: <strong class="phone-code">${esc(value.code)}</strong></p><p>${t.devices}: ${value.devices}</p><label>${t.link}<input readonly name="phone-link" value="${esc(value.link)}"></label><button class="secondary" data-mobile="copy">${t.copy}</button></div></div><p class="hint">${t.plain}</p><button class="secondary" data-mobile="revoke">${t.revoke}</button>` : ""}<button class="quiet" data-mobile="disconnect">${t.disconnect}</button></details>`;
    if (value.admin && value.qr_available) {
      const blob = await this.request("/mobile/qr", undefined, true);
      if (this.qr) URL.revokeObjectURL(this.qr);
      this.qr = URL.createObjectURL(blob);
      const img = document.createElement("img");
      img.src = this.qr;
      img.alt = t.title;
      this.container.querySelector(".phone-qr").replaceChildren(img);
    } else if (value.admin)
      this.container.querySelector(".phone-qr").textContent = t.noQR;
    this.container.onclick = (event) => {
      const button = event.target.closest("[data-mobile]");
      if (button)
        this.action(button.dataset.mobile).catch((error) =>
          this.notify(error.message, true),
        );
    };
  }
  async action(action) {
    const t = words[this.language];
    if (action === "copy") {
      try {
        await navigator.clipboard.writeText(this.value.link);
        this.notify(t.copied);
      } catch {
        const input = this.container.querySelector("[name=phone-link]");
        input.focus();
        input.select();
        input.setSelectionRange(0, input.value.length);
        this.notify(t.selected);
      }
    } else if (action === "revoke") {
      await this.request("/mobile/revoke", {});
      await this.update(this.language);
      this.container.querySelector("details").open = true;
    } else {
      await this.request("/mobile/disconnect", {});
      location.replace("/");
    }
  }
}
