"""Offline demo with generated illustrations, not user photographs."""

from pathlib import Path
import tempfile

from PIL import Image, ImageDraw

from photo_location_workflow.core import add_evidence, candidate, crop, init_case
from photo_location_workflow.report import render_html


def main():
    case = Path("cases/demo")
    with tempfile.TemporaryDirectory() as folder:
        photo = Path(folder) / "synthetic.png"
        im = Image.new("RGB", (1000, 650), "#dce6d6")
        d = ImageDraw.Draw(im)
        d.rectangle((0, 510, 1000, 650), fill="#6b7272")
        d.polygon([(120, 240), (350, 100), (580, 240)], fill="#243a35")
        d.rectangle((145, 240, 555, 510), fill="#243a35")
        for x in (220, 320, 420):
            d.rectangle((x, 270, x + 85, 320), fill="#b1c7c4", outline="#111111", width=4)
        for x in (450, 480):
            d.ellipse((x, 235, x + 10, 245), fill="#f5e5bb")
        d.rectangle((260, 380, 440, 510), fill="#c2a27a")
        d.text((24, 20), "SYNTHETIC DEMO / NOT A REAL LOCATION", fill="#162b23")
        im.save(photo)
        init_case(photo, case)
        crop(case, (120, 100, 460, 420), "facade", 2)
        candidate(case, "Synthetic building / 虚构建筑", "No real address / 无真实地址", "https://example.org/")
        add_evidence(case, "c1", "reference", "https://example.org/", "match", "Synthetic illustration of the comparison workflow. No official address or Street View verification has occurred.", photo)
        report = render_html(case)
        print(f"Offline demo ready: {report.resolve()}")


if __name__ == "__main__":
    main()
