"""Render numbered overlays and actual-pixel details without changing case assets."""

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from .core import asset_path


def badge_position(region, badge_size, image_size, used):
    """Prefer a corner of the region that does not hide an earlier number."""
    left, top, right, bottom = region
    bw, bh = badge_size
    candidates = [(left, top), (right - bw, top), (left, bottom - bh),
                  (right - bw, bottom - bh), (left, top - bh - 3), (left, bottom + 3)]
    # Stacking nearby also handles several identical or tiny regions.
    candidates += [(left, top + offset * (bh + 3)) for offset in range(1, 12)]
    for bx, by in candidates:
        bx, by = max(0, min(bx, image_size[0] - bw)), max(0, min(by, image_size[1] - bh))
        rect = (bx, by, bx + bw, by + bh)
        if not any(rect[0] < r[2] + 2 and rect[2] + 2 > r[0] and rect[1] < r[3] + 2 and rect[3] + 2 > r[1] for r in used):
            used.append(rect)
            return bx, by
    return max(0, left), max(0, top)


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
        badges = []
        for item in annotations:
            x, y, w, h = item[box_key]
            left, top, right, bottom = x * sx, y * sy, (x + w) * sx, (y + h) * sy
            draw.rectangle((left, top, right, bottom), outline='#173e32', width=stroke + 2)
            if right - left > 2 and bottom - top > 2:
                draw.rectangle((left + 1, top + 1, right - 1, bottom - 1), outline='#f7cc61', width=stroke)
            badges.append(((left, top, right, bottom), str(item['number'])))
        used = []
        for region, text in badges:
            bounds = draw.textbbox((0, 0), text, font=font)
            bw, bh = bounds[2] + 10, font_size + 8
            bx, by = badge_position(region, (bw, bh), image.size, used)
            draw.rectangle((bx, by, bx + bw, by + bh), fill='#173e32')
            draw.text((bx + 5, by + 2), text, fill='#ffe090', font=font)
    output = BytesIO()
    image.save(output, format='PNG')
    output.seek(0)
    return output
