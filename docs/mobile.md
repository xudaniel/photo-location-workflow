# Phone access / 手机使用

[English](#english) · [简体中文](#简体中文)

## English

The responsive workbench can be used from a phone browser while the computer runs the server. **The phone and computer must be on the same trusted Wi-Fi/LAN.** Investigations and original prepared files remain on that computer. This is LAN access, not a hosted service or an offline phone app.

### Start on the computer

These features are on `main`; the v1.3.0 tagged release predates phone access. From an updated source checkout:

```bash
uv sync --locked --extra mobile --extra pdf
uv run --locked --extra mobile --extra pdf photo-locate ui --lan
```

Or install from GitHub with pip:

```bash
python -m pip install "photo-location-workflow[mobile,pdf] @ git+https://github.com/xudaniel/photo-location-workflow.git"
photo-locate ui --lan
```

The `mobile` extra adds local QR generation and HEIC/HEIF decoding. Basic JPEG/PNG/WebP access and typed pairing codes work without it. PDF additionally needs the `pdf` extra and an embeddable font for the document's characters.

The server selects a private IPv4 interface and prints the phone address, an 8-digit connection code and a separate desktop sign-in link. The browser opens the desktop link automatically. For a machine with multiple interfaces, select one explicitly:

```bash
photo-locate ui --lan --lan-address 192.168.1.20 --port 8765 --cases cases
```

`--lan-address` requires `--lan` and must be a local RFC1918 IPv4 address. The server binds to that interface, not a public or wildcard address. A VPN can affect automatic selection; pass the actual Wi-Fi address if needed. Default `photo-locate ui` still listens only on `127.0.0.1`.

### Connect the phone

1. Keep the computer running and connect both devices to the same trusted network.
2. On the desktop workbench, expand **Connect a phone**. Scan its QR code, or open the printed phone address and enter the connection code. Each phone browser pairs separately.
3. Use **New photo** for the photo library/file picker, or **Take photo** for a camera capture request. The device/browser decides whether capture opens the camera directly or offers a menu.
4. On a touch screen, enable **Touch selection**, drag a detail, then save it. A completed touch drag returns the canvas to page scrolling. Pixel coordinate inputs also work. In paired comparison, choose **Scroll page**, **Move images** or **Draw regions** explicitly.
5. Use the sticky Photo / Investigate / Evidence / Report links to move around. Local background jobs keep running if you switch apps or temporarily lose the connection; reopen the case to see saved progress. Data is stored on the computer, not cached as an offline phone copy.

The phone can upload HEIC originals when the server has the mobile extra. Orientation follows the HEIF decoder and normal preparation; output is a metadata-free PNG. Auxiliary images and OCR remain hypotheses, and existing human evidence/confidence rules still apply. In LAN mode, **View report** opens the complete HTML report directly in the browser; use browser Back to return. HTML/PDF download buttons remain available, but saving and sharing presentation varies by browser.

### Pairing and access

LAN mode serves a pairing page until a device signs in. Pairing grants access to **all cases in that server's `--cases` directory**, including editing and optional configured research tools. Only the desktop sign-in role can reveal connection information or revoke all phones. The QR link carries a long random device secret in a URL fragment; the manual code has attempt limits. Pairing credentials are sent in a JSON body and removed from browser history before navigation.

Device sessions use HttpOnly, SameSite=Strict cookies with per-port names and a 12-hour lifetime; API calls also require the session header token and check request Host/Origin. Read-only report document navigation requires a paired cookie without putting secrets in the link. Sessions and connection codes are kept only in server memory and become invalid when the server restarts. **Disconnect this device** clears one session; the desktop's **Disconnect phones and rotate code** invalidates phone sessions and both phone pairing methods while retaining the desktop session. Existing investigations stay saved.

LAN transport uses **HTTP**, so use a trusted private network and keep pairing links/codes private. Do not publish the desktop sign-in link, forward the server port to the internet, or treat this server as a public cloud deployment. No firewall or router settings are changed automatically. External map/Lens links still open separately, and paid OpenAI research retains its explicit submission control.

If the phone cannot connect, check the address printed by the current server, that the computer is awake, and that Wi-Fi client isolation or the OS firewall is not blocking the chosen Python listener. A pairing error after a restart needs the new code; repeated failures temporarily limit attempts. Some secure-context browser conveniences (such as clipboard writes) are unavailable over LAN HTTP; the pairing-link field remains selectable for manual copying.

## 简体中文

现在可以在手机浏览器使用工作台，**电脑需运行服务，手机与电脑连接同一可信 Wi-Fi／局域网**。调查和图片保存在电脑中。这是局域网使用方式，不是云端服务，也不支持脱离电脑离线调查。

### 电脑启动

手机功能已进入 `main`，v1.3.0 发行包尚未包含。更新源码后运行上方 uv 命令，或从 GitHub 安装 `mobile,pdf` 扩展，再运行：

```bash
photo-locate ui --lan
```

`mobile` 扩展用于本地生成二维码与读取 HEIC／HEIF；不装也能用连接码及 JPEG／PNG／WebP。PDF 另需 PDF 扩展和支持相应字符的字体。

终端会显示手机访问地址、8 位连接码和独立的电脑登录链接，并自动打开电脑工作台。多网卡或 VPN 环境可用 `--lan-address 192.168.1.20` 指定本机 Wi-Fi IPv4 地址；也可用 `--port`、`--cases` 指定端口和调查目录。只允许 RFC1918 私有地址，不监听公网或通配地址。默认不加 `--lan` 时，仍只监听本机 `127.0.0.1`。

### 手机连接与操作

1. 保持电脑运行，手机连接同一可信 Wi-Fi。
2. 在电脑工作台展开“手机连接”，扫码进入；也可在手机打开终端显示的地址，再输入连接码。
3. “新建照片调查”可从相册或文件选择图片；“拍照”向系统请求相机采集，实际菜单由设备和浏览器决定。
4. 触屏上先点“开启触摸框选”再拖动，拖完后恢复页面滚动；也可输入像素坐标。双图对照可以切换滚动页面、移动图片和框选细节。
5. 顶部快捷导航跳转照片、线索调查、证据和报告。切换手机应用或临时断网不会取消电脑上的后台任务；重新打开案卷可查看保存的进度。页面不会保存可脱机使用的调查副本。

安装 mobile 扩展后可上传 HEIC 原图，按解码器与正常准备流程处理方向，并生成去除元数据的 PNG。辅助变体与 OCR 不自动成为核对证据。局域网模式下，“打开报告”可直接在浏览器查看完整 HTML 报告，用浏览器返回即可回到工作台。也保留 HTML／PDF 下载；保存或分享菜单因浏览器而异。

### 连接范围与管理

未配对的设备只能看到连接页。配对后可查看和修改该服务 `--cases` 目录中的**全部调查**，也可使用已配置的研究工具。只有电脑登录角色能查看分享信息和统一断开手机。二维码使用随机连接密钥，放在网址片段中；手动连接码限制尝试频率。连接后会移除地址中的密钥。

手机会话用 HttpOnly、SameSite=Strict Cookie 保存，并按端口区分，最长 12 小时；接口还校验会话头、Host 和 Origin。只读报告页面凭配对 Cookie 打开，链接不含会话密钥。重启服务会使会话、二维码与连接码失效，但调查文件继续保存。“断开本设备”只退出当前浏览器；电脑端“断开全部手机并更换连接码”会撤销手机会话并更换二维码和数字码，保留电脑会话。

局域网通过 **HTTP** 传输，请使用可信网络并保管连接码与链接，不要公开电脑登录链接或将端口转发到公网。本程序不自动修改防火墙或路由器。Google Lens／地图仍单独打开；付费 OpenAI 请求仍需明确操作。

无法连接时，核对本次启动显示的地址、电脑是否休眠，以及 Wi-Fi 设备隔离或防火墙是否阻止 Python 服务。服务重启后要使用新码。HTTP 下部分剪贴板功能不可用，可手动长按复制链接。
