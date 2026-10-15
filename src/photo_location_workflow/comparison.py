"""Render numbered overlays and actual-pixel details without changing case assets."""

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from .core import asset_path


def comparison_image(case, relative, annotations=(), box_key='source_box', detail=None):
    with Image.open(asset_path(case, relative)) as original:
        image = original.convert('RGB')
    if detail is not None:
        x, y, w, h = detail
        image = image.crop((x, y, x + w, y + h))
        # Nearest-neighbor enlargement displays the recorded pixels, never generated detail.
        if max(image.size) < 480:
            scale = max(1, min(4, 480 // max(image.size)))
            image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    else:
        original_width, original_height = image.size
        image.thumbnail((1800, 1400))
        sx, sy = image.width / original_width, image.height / original_height
        draw = ImageDraw.Draw(image)
        font_size = max(14, round(min(image.size) / 28))
        font = ImageFont.load_default(size=font_size)
        stroke = max(2, round(min(image.size) / 240))
        for item in annotations:
            x, y, w, h = item[box_key]
            left, top, right, bottom = x * sx, y * sy, (x + w) * sx, (y + h) * sy
            draw.rectangle((left, top, right, bottom), outline='#173e32', width=stroke + 2)
            if right - left > 2 and bottom - top > 2:
                draw.rectangle((left + 1, top + 1, right - 1, bottom - 1), outline='#f7cc61', width=stroke)
            text = str(item['number'])
            bounds = draw.textbbox((0, 0), text, font=font)
            bw, bh = bounds[2] + 10, font_size + 8
            bx, by = max(0, min(left, image.width - bw)), max(0, min(top, image.height - bh))
            draw.rectangle((bx, by, bx + bw, by + bh), fill='#173e32')
            draw.text((bx + 5, by + 2), text, fill='#ffe090', font=font)
    output = BytesIO()
    image.save(output, format='PNG')
    output.seek(0)
    return output
