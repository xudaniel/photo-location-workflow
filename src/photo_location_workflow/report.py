"""Self-contained HTML and optional PDF; source claims remain reviewer-supplied."""

import base64
import html
from pathlib import Path

from .core import asset_path, load, web_url

DISCLAIMER = "Confidence is a human review decision, not a calibrated probability. Enlarging pixels does not recover unreadable text. Vehicle registration is not proof of shooting location."


def render_html(case, output=None):
    data = load(case)
    output = Path(output or Path(case) / "report.html")
    esc = lambda s: html.escape(str(s or ""), quote=True)

    def link(url, label):
        return f'<a href="{esc(web_url(url))}" rel="noreferrer">{esc(label)}</a>'

    def image(relative):
        raw = asset_path(case, relative).read_bytes()
        return f'<img src="data:image/png;base64,{base64.b64encode(raw).decode()}" alt="Comparison evidence">'

    def card(title, content):
        return f'<section><h2>{esc(title)}</h2>{content}</section>'

    con = data["conclusion"]
    parts = [card("Conclusion / 结论", f'<strong>{esc(con["level"])}</strong><p>{esc(con["note"])}</p>'),
             card("Original / 原图（已移除元数据）", image(data["source"]["asset"]))]
    for crop in data["crops"]:
        parts.append(card(f'Crop / 局部: {crop["label"]}', f'<p>Original pixels: {esc(crop["box"])}; nearest-neighbor scale: {crop["scale"]}x.</p>' + image(crop["zoom"])))
    for c in data["candidates"]:
        parts.append(card(f'Candidate / 候选 {c["id"]}: {c["name"]}', f'<p>{esc(c["address"])}</p>' + link(c["source_url"], "Address source / 地址来源") + " · " + link(c["maps_url"], "Google Maps")))
        for e in data["evidence"]:
            if e["candidate_id"] == c["id"]:
                body = f'<p>{esc(e["kind"])} · {esc(e["verdict"])} · Captured: {esc(e["captured"] or "not recorded")}</p><p>{esc(e["notes"])}</p>'
                if e["asset"]:
                    body += '<div class="compare">' + image(data["source"]["asset"]) + image(e["asset"]) + '</div>'
                parts.append(card(f'Evidence / 证据 {e["id"]}', body + link(e["url"], "Source / 来源")))
    for search in data["searches"]:
        parts.append(card("Search log / 搜索记录", f'<p>{esc(search["status"])} · {esc(search["reviewed_at"])}</p>' + link(search["url"], "Lens session (may expire)")))
    doc = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Photo location evidence</title><style>
body{font:16px/1.6 system-ui,sans-serif;max-width:1120px;margin:40px auto;padding:0 24px;background:#f4f5f0;color:#18372e}section{background:white;padding:24px;margin:20px 0;border-radius:12px}h1{font-size:30px}h2{font-size:20px}p{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#27684e}img{display:block;max-width:100%;max-height:620px;object-fit:contain;margin:12px auto}.compare{display:grid;grid-template-columns:1fr 1fr;gap:16px}.compare img{width:100%;height:400px}.note{color:#576b61} @media(max-width:700px){.compare{grid-template-columns:1fr}}@media print{body{background:white;margin:0}section{break-inside:avoid;border:1px solid #ddd}.compare img{height:270px}a{overflow-wrap:anywhere}}
</style><h1>Photo location / 照片地点证据</h1>'''
    output.write_text(doc + f'<p class="note">{esc(DISCLAIMER)}</p>' + ''.join(parts) + '</html>', encoding="utf-8")
    return output


def render_pdf(case, output=None, font_path=None):
    try:
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table
    except ImportError as exc:
        raise ValueError('Install PDF support: pip install -e ".[pdf]"') from exc

    data = load(case)
    output = Path(output or Path(case) / "report.pdf")
    if not font_path:
        font_path = next((p for p in (
            Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf'),
            Path('/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'),
            Path('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'),
            Path('C:/Windows/Fonts/msyh.ttc'),
        ) if p.is_file()), None)
    if not font_path:
        raise ValueError('PDF needs an embeddable CJK TrueType font: use --font-path /path/to/font.ttf (or .ttc). HTML export needs no font installation.')
    font = "EvidenceFont"
    pdfmetrics.registerFont(TTFont(font, str(font_path)))
    style = ParagraphStyle("body", fontName=font, fontSize=10, leading=16, wordWrap="CJK", spaceAfter=12)
    title = ParagraphStyle("heading", parent=style, fontSize=20, leading=26, spaceAfter=16)
    p = lambda s, heading=False: Paragraph(html.escape(str(s)), title if heading else style)

    def image(relative, width=245, height=310):
        path = asset_path(case, relative)
        w, h = ImageReader(str(path)).getSize()
        scale = min(width / w, height / h)
        return Image(str(path), width=w * scale, height=h * scale)

    con = data["conclusion"]
    story = [p("Photo location / 照片地点核对", True), p(f'{con["level"]}: {con["note"]}'), p(DISCLAIMER), image(data["source"]["asset"], 510, 470)]
    for c in data["candidates"]:
        story += [PageBreak(), p(f'{c["id"]}: {c["name"]}', True), p(c["address"]), p(c["source_url"]), p(c["maps_url"])]
        for e in (e for e in data["evidence"] if e["candidate_id"] == c["id"]):
            story += [p(f'{e["id"]}: {e["kind"]} / {e["verdict"]} / {e["captured"] or "date not recorded"}'), p(e["notes"]), p(e["url"])]
            if e["asset"]:
                story += [Table([[image(data["source"]["asset"]), image(e["asset"])]], colWidths=[255, 255]), Spacer(1, 14)]
    for c in data["crops"]:
        story += [PageBreak(), p(f'Crop / 局部: {c["label"]}', True), p(f'Pixel box: {c["box"]}; nearest-neighbor enlargement {c["scale"]}x. No generated details.'), image(c["zoom"], 510, 570)]

    def footer(canvas, doc):
        canvas.setFont(font, 8)
        canvas.drawString(36, 22, f'Photo location evidence | {doc.page}')

    SimpleDocTemplate(str(output), leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36, title="Photo location evidence").build(story, onFirstPage=footer, onLaterPages=footer)
    return output
