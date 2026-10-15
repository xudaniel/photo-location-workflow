"""Self-contained reports with explicit sources, decisions and review history."""

import base64
import html
from pathlib import Path

from .core import asset_path, check_case, load, web_url

DISCLAIMER = ('Confidence is a human review decision, not a calibrated probability. '
              'Enlarging pixels does not recover unreadable text. '
              'Vehicle registration is not proof of shooting location.')


def prepare_output(case, output, extension):
    root = Path(case).resolve()
    output = Path(output or root / f'report.{extension}').resolve()
    if output.suffix.lower() != f'.{extension}' or output.is_relative_to(root / 'assets'):
        raise ValueError(f'Report output must be a .{extension} file outside the assets directory.')
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def checked_data(case):
    integrity = check_case(case)
    if not integrity['ok']:
        raise ValueError('Case integrity failed: ' + '; '.join(integrity['errors']))
    return load(case), integrity


def render_html(case, output=None):
    data, integrity = checked_data(case)
    output = prepare_output(case, output, 'html')
    esc = lambda s: html.escape(str(s or ''), quote=True)

    def link(url, label):
        return f'<a href="{esc(web_url(url))}" rel="noreferrer">{esc(label)} ↗</a>'

    def image(relative, label):
        raw = asset_path(case, relative).read_bytes()
        return (f'<figure><img src="data:image/png;base64,{base64.b64encode(raw).decode()}" '
                f'alt="{esc(label)}"><figcaption>{esc(label)}</figcaption></figure>')

    def card(title, content, anchor=''):
        return f'<section id="{esc(anchor)}"><h2>{esc(title)}</h2>{content}</section>'

    def review_history(e):
        if not e.get('reviews'):
            return ''
        rows = ''.join(f'<li><strong>{esc(r["from"])} → {esc(r["to"])}</strong><p>{esc(r["reason"])}</p><small>{esc(r["at"])}</small></li>' for r in e['reviews'])
        return f'<details><summary>Review history / 复审历史 ({len(e["reviews"])})</summary><ol>{rows}</ol></details>'

    con = data['conclusion']
    chosen = next((c for c in data['candidates'] if c['id'] == con.get('candidate_id')), None)
    parts = [card('Conclusion / 结论', f'<span class="badge {esc(con["level"])}">{esc(con["level"])}</span>'
                  + (f'<h3>{esc(chosen["name"])}</h3><p>{esc(chosen["address"])}</p>' if chosen else '')
                  + f'<p>{esc(con["note"] or "No conclusion yet / 尚无结论")}</p>', 'conclusion'),
             card('Source image / 原图副本', image(data['source']['asset'], 'Orientation normalized · metadata removed / 已校正方向、移除元数据'), 'source')]
    for c in data['candidates']:
        parts.append(card(f'{c["id"]} · {c["name"]}', f'<p>{esc(c["address"])}</p><div class="links">'
                          + link(c['source_url'], 'Address source / 地址来源') + link(c['maps_url'], 'Google Maps') + '</div>', c['id']))
        for e in (e for e in data['evidence'] if e['candidate_id'] == c['id']):
            body = (f'<div class="meta"><span class="badge {esc(e["verdict"])}">{esc(e["verdict"])}</span>'
                    f'<span>{esc(e["kind"])}</span><span>Captured: {esc(e.get("captured") or "not recorded")}</span></div>'
                    f'<p class="provider">{esc(e.get("provider") or "Provider not recorded / 未记录提供者")}</p><p>{esc(e["notes"])}</p>')
            if e['asset']:
                body += '<div class="compare">' + image(data['source']['asset'], 'Source / 原图') + image(e['asset'], 'Reference / 对照影像') + '</div>'
            parts.append(card(f'Evidence / 证据 {e["id"]}', body + link(e['url'], 'Source / 来源') + review_history(e), e['id']))
    for crop in data['crops']:
        parts.append(card(f'Crop / 局部 · {crop["label"]}', f'<p>Pixel box: {esc(crop["box"])} · {crop["scale"]}× nearest-neighbor enlargement. No generated details.</p>'
                          + image(crop['zoom'], 'Original pixels enlarged / 原始像素放大'), f'crop-{crop["label"]}'))
    for i, search in enumerate(data['searches'], 1):
        body = f'<p>{esc(search["status"])} · {esc(search["reviewed_at"])}</p>'
        if search.get('screenshot'):
            body += image(search['screenshot'], 'Search capture / 搜索截图（并非已验证证据）')
        body += link(search['url'], 'Lens session (may expire) / 搜索链接（可能过期）')
        parts.append(card(f'Search / 搜索 {i}', body))
    warning = ''.join(f'<li>{esc(w)}</li>' for w in integrity['warnings'])
    parts.append(card('Integrity / 本地完整性', f'<p>{integrity["assets_checked"]} assets checked / 已检查文件。SHA-256 checks detect file changes; they do not prove location or image authenticity.</p><ul>{warning}</ul>'))
    doc = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>Photo Location · Evidence report</title><style>
:root{--ink:#183c32;--muted:#65736d;--accent:#24795c;--line:#dbe3dc}*{box-sizing:border-box}body{margin:0;background:#f3f5ef;color:var(--ink);font:16px/1.65 system-ui,-apple-system,sans-serif}header{padding:64px max(24px,calc((100vw - 1120px)/2));background:#153e32;color:#fff}header small{letter-spacing:.18em;color:#b8d7bc}h1{font-size:clamp(30px,5vw,48px);line-height:1.2;margin:14px 0}header p{color:#d3e3d3;max-width:750px}nav{display:flex;gap:24px;margin-top:24px}nav a{color:#fff}main{max-width:1168px;margin:28px auto;padding:0 24px}.stats{display:flex;gap:32px;padding:16px 4px;color:var(--muted)}.stats strong{display:block;font-size:26px;color:var(--ink)}section{background:#fff;padding:28px;margin:20px 0;border:1px solid var(--line);border-radius:16px;break-inside:avoid}h2{font-size:20px;margin:0 0 20px}h3{font-size:26px;margin:18px 0 4px}p{white-space:pre-wrap;overflow-wrap:anywhere}a{color:var(--accent);overflow-wrap:anywhere}.links,.meta{display:flex;gap:18px;align-items:center;flex-wrap:wrap}.badge{display:inline-block;padding:4px 13px;border-radius:99px;background:#eef1eb;color:#4c5d53;font-size:13px;font-weight:700}.confirmed,.high,.match{background:#def2e4;color:#17613f}.contradiction{background:#fce2dd;color:#9c3024}.candidate,.unclear{background:#fff0cb;color:#876217}figure{margin:18px 0 0;background:#f4f6f1;border:1px solid #e6ebe4;border-radius:10px;overflow:hidden}img{display:block;max-width:100%;max-height:620px;object-fit:contain;margin:auto}figcaption{padding:10px 14px;font-size:12px;color:var(--muted);background:#edf1e9}.compare{display:grid;grid-template-columns:1fr 1fr;gap:18px}.compare img{width:100%;height:360px}.provider,small{color:var(--muted)}details{margin-top:22px;border-top:1px solid var(--line);padding-top:18px}summary{cursor:pointer;font-weight:600}footer{padding:24px 0 50px;font-size:12px;color:var(--muted)}@media(max-width:700px){header{padding:36px 24px}.compare{grid-template-columns:1fr}.stats{gap:20px}section{padding:20px}.compare img{height:auto}}@media print{header{padding:18px;color:#183c32;background:white}header p,header small,nav a{color:#183c32}main{margin:0;padding:0}body{background:white}section{border-radius:0}.compare img{height:240px}nav{display:none}details{display:block}}
</style></head><body><header><small>PHOTO LOCATION WORKFLOW</small><h1>A place. A trail of evidence.<br>地点有据可查。</h1><p>Source images, address sources, visual comparisons and human-reviewed decisions in one offline report.</p><nav><a href="#conclusion">Conclusion / 结论</a><a href="#source">Source / 原图</a></nav></header><main>'''
    stats = '<div class="stats">' + ''.join(f'<div><strong>{n}</strong>{label}</div>' for n, label in [(len(data['candidates']), 'Candidates / 候选'), (len(data['evidence']), 'Evidence / 证据'), (len(data['crops']), 'Crops / 局部')]) + '</div>'
    output.write_text(doc + stats + ''.join(parts) + f'<footer>{esc(DISCLAIMER)}</footer></main></body></html>', encoding='utf-8')
    return output


def render_pdf(case, output=None, font_path=None):
    try:
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise ValueError('Install PDF support: pip install -e ".[pdf]"') from exc
    data, integrity = checked_data(case)
    output = prepare_output(case, output, 'pdf')
    if not font_path:
        font_path = next((p for p in (
            Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf'),
            Path('/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'),
            Path('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'),
            Path('C:/Windows/Fonts/msyh.ttc'),
        ) if p.is_file()), None)
    if not font_path:
        raise ValueError('PDF needs an embeddable CJK TrueType font: use --font-path /path/to/font.ttf (or .ttc). HTML needs no font installation.')
    font = 'EvidenceFont'
    pdfmetrics.registerFont(TTFont(font, str(font_path)))
    ink, muted = colors.HexColor('#183c32'), colors.HexColor('#65736d')
    style = ParagraphStyle('body', fontName=font, fontSize=10, leading=16, textColor=ink, wordWrap='CJK', spaceAfter=12)
    title = ParagraphStyle('heading', parent=style, fontSize=20, leading=26, spaceAfter=16)
    caption = ParagraphStyle('caption', parent=style, fontSize=8, leading=12, textColor=muted)
    p = lambda s, heading=False: Paragraph(html.escape(str(s)), title if heading else style)

    def link(url, label):
        return Paragraph(f'<link href="{html.escape(web_url(url), quote=True)}" color="#24795c">{html.escape(label)}</link>', style)

    def image(relative, width=245, height=310):
        path = asset_path(case, relative)
        w, h = ImageReader(str(path)).getSize()
        scale = min(width / w, height / h)
        return Image(str(path), width=w * scale, height=h * scale)

    con = data['conclusion']
    chosen = next((c for c in data['candidates'] if c['id'] == con.get('candidate_id')), None)
    story = [p('Photo location / 照片地点核对', True), p(f'{con["level"]}: {con["note"]}')]
    if chosen:
        story += [p(chosen['name']), p(chosen['address'])]
    story += [Paragraph(DISCLAIMER, caption), Spacer(1, 12), image(data['source']['asset'], 510, 420)]
    for c in data['candidates']:
        story += [PageBreak(), p(f'{c["id"]}: {c["name"]}', True), p(c['address']), link(c['source_url'], 'Address source / 地址来源'), link(c['maps_url'], 'Open Google Maps / 打开地图')]
        for e in (e for e in data['evidence'] if e['candidate_id'] == c['id']):
            story += [p(f'{e["id"]}: {e["kind"]} / {e["verdict"]} / {e.get("captured") or "date not recorded"}'), p(e.get('provider') or 'Provider not recorded / 未记录提供者'), p(e['notes']), link(e['url'], 'View evidence source / 查看证据来源')]
            if e['asset']:
                table = Table([[image(data['source']['asset']), image(e['asset'])], [Paragraph('Source / 原图', caption), Paragraph('Reference / 对照影像', caption)]], colWidths=[255, 255])
                table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f3f5ef')), ('BOTTOMPADDING', (0, 0), (-1, -1), 12)]))
                story += [table, Spacer(1, 14)]
            for r in e.get('reviews', []):
                story += [p(f'Review / 复审: {r["from"]} -> {r["to"]}'), p(r['reason']), Paragraph(html.escape(r['at']), caption)]
    for c in data['crops']:
        story += [PageBreak(), p(f'Crop / 局部: {c["label"]}', True), p(f'Pixel box: {c["box"]}; nearest-neighbor enlargement {c["scale"]}x. No generated details.'), image(c['zoom'], 510, 550)]
    story += [Spacer(1, 18), Paragraph(f'Local integrity: {integrity["assets_checked"]} assets checked. Checksums do not prove image authenticity.', caption)]
    for warning in integrity['warnings']:
        story.append(Paragraph(html.escape(warning), caption))

    def footer(canvas, doc):
        canvas.setStrokeColor(colors.HexColor('#dbe3dc'))
        canvas.line(36, 36, 559, 36)
        canvas.setFillColor(muted)
        canvas.setFont(font, 8)
        canvas.drawString(36, 22, f'Photo Location Workflow | {doc.page}')

    SimpleDocTemplate(str(output), leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=48, title='Photo location evidence').build(story, onFirstPage=footer, onLaterPages=footer)
    return output
