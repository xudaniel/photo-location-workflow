import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from photo_location_workflow.core import add_evidence, candidate, conclude, crop, init_case, load
from photo_location_workflow.report import render_html


@pytest.fixture
def investigation(tmp_path):
    source = tmp_path / "input.jpg"
    im = Image.new("RGB", (100, 80), "green")
    exif = Image.Exif()
    exif[270] = "private metadata"
    im.save(source, exif=exif)
    root = tmp_path / "case"
    init_case(source, root)
    return root


def test_source_has_no_private_metadata(investigation):
    with Image.open(investigation / "assets/source.png") as im:
        assert not im.getexif()
        assert im.size == (100, 80)
    assert "input.jpg" not in (investigation / "case.json").read_text()
    with pytest.raises(ValueError):
        init_case(investigation / "assets/source.png", investigation)


def test_crop_retains_pixels_and_rejects_out_of_bounds(investigation):
    item = crop(investigation, (10, 5, 20, 15), "facade", 3)
    with Image.open(investigation / item["native"]) as im:
        assert im.size == (20, 15)
    with Image.open(investigation / item["zoom"]) as im:
        assert im.size == (60, 45)
    for bad in [(-1, 0, 10, 10), (95, 0, 10, 10), (0, 0, 0, 1)]:
        with pytest.raises(ValueError):
            crop(investigation, bad, "bad")
    with pytest.raises(ValueError):
        crop(investigation, (0, 0, 1, 1), "../escape")


def test_confidence_requires_observed_evidence_and_resets_on_new_evidence(investigation):
    candidate(investigation, "Test landmark", "Public address", "https://example.org/")
    with pytest.raises(ValueError):
        conclude(investigation, "c1", "confirmed", "Guess")
    add_evidence(investigation, "c1", "official", "https://example.org/", "match", "Address checked")
    with pytest.raises(ValueError):
        conclude(investigation, "c1", "high", "Address alone")
    add_evidence(investigation, "c1", "streetview", "https://maps.google.com/", "match", "Three windows and road align", investigation / "assets/source.png", "2026-06")
    assert conclude(investigation, "c1", "confirmed", "Address and visual features agree")["level"] == "confirmed"
    add_evidence(investigation, "c1", "text", "https://example.org/", "unclear", "Plate unreadable")
    assert load(investigation)["conclusion"]["level"] == "candidate"
    add_evidence(investigation, "c1", "reference", "https://example.org/", "contradiction", "Road runs in a different direction")
    with pytest.raises(ValueError):
        conclude(investigation, "c1", "high", "Ignore mismatch")


def test_report_escapes_external_text_and_rejects_unsafe_links(investigation):
    candidate(investigation, '<script>alert("x")</script>', "Address", "https://example.org/")
    report = render_html(investigation)
    text = report.read_text()
    assert "<script>" not in text
    assert "&lt;script&gt;" in text
    assert "data:image/png;base64," in text
    with pytest.raises(ValueError):
        candidate(investigation, "x", "y", "javascript:alert(1)")
    with pytest.raises(ValueError):
        add_evidence(investigation, "c1", "streetview", "https://maps.google.com/", "match", "Observed", captured="2026-99")


def test_cli_default_search_does_not_upload(investigation):
    result = subprocess.run([sys.executable, "-m", "photo_location_workflow", "lens", str(investigation)], capture_output=True, text=True)
    assert result.returncode == 0
    assert "No upload performed" in result.stdout
    assert load(investigation)["searches"] == []


def test_report_rejects_escaping_asset_paths(investigation):
    import json
    path = investigation / "case.json"
    data = load(investigation)
    data["source"]["asset"] = "../input.jpg"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        render_html(investigation)


def test_pdf_with_cjk_and_comparison_images(investigation):
    pytest.importorskip("reportlab")
    from photo_location_workflow.report import render_pdf
    candidate(investigation, "示例建筑", "虚构地址", "https://example.org/")
    add_evidence(investigation, "c1", "reference", "https://example.org/", "match", "中文备注与原图并排。", investigation / "assets/source.png")
    crop(investigation, (0, 0, 30, 30), "detail", 2)
    output = render_pdf(investigation)
    raw = output.read_bytes()
    assert raw.startswith(b"%PDF-")
    assert b"/FontFile2" in raw  # The actual font program travels with the report.
