"""Synthetic fixtures shared by the CLI and local workbench; no network access."""

from pathlib import Path
import tempfile

from PIL import Image, ImageDraw

from .annotations import add_annotation
from .core import add_evidence, candidate, crop, init_case, load, save
from .report import render_html


def create_demo(case):
    case = Path(case)
    with tempfile.TemporaryDirectory() as folder:
        photo = Path(folder) / 'synthetic.png'
        im = Image.new('RGB', (1000, 650), '#dce6d6')
        draw = ImageDraw.Draw(im)
        draw.rectangle((0, 510, 1000, 650), fill='#6b7272')
        draw.polygon([(120, 240), (350, 100), (580, 240)], fill='#243a35')
        draw.rectangle((145, 240, 555, 510), fill='#243a35')
        for x in (220, 320, 420):
            draw.rectangle((x, 270, x + 85, 320), fill='#b1c7c4', outline='#111111', width=4)
        for x in (450, 480):
            draw.ellipse((x, 235, x + 10, 245), fill='#f5e5bb')
        draw.rectangle((260, 380, 440, 510), fill='#c2a27a')
        draw.text((24, 20), 'SYNTHETIC DEMO / NOT A REAL LOCATION', fill='#162b23')
        im.save(photo)
        reference = Path(folder) / 'reference.png'
        im.crop((100, 80, 650, 550)).resize((880, 752), Image.Resampling.NEAREST).save(reference)
        init_case(photo, case)
        crop(case, (120, 100, 460, 420), 'facade', 2)
        candidate(case, 'Synthetic building / 虚构建筑', 'No real address / 无真实地址', 'https://example.org/')
        add_evidence(case, 'c1', 'reference', 'https://example.org/', 'match',
                     'Synthetic illustration only. No official address or Street View verification has occurred.', reference,
                     provider='Generated offline / 离线绘制')
        add_annotation(case, 'e1', 'Three windows / 三扇窗', [214, 264, 297, 63], [182, 294, 476, 101])
        add_annotation(case, 'e1', 'Two roof lights / 两盏屋顶灯', [444, 230, 52, 20], [550, 240, 84, 32])
        data = load(case)
        data['title'] = 'Offline demo / 离线演示'
        save(case, data)
        render_html(case)
    return case
