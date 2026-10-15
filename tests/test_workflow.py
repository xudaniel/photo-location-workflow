import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from photo_location_workflow.core import add_evidence, candidate, check_case, conclude, crop, hash_file, init_case, load, review_evidence, save, selected_asset
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
    assert "input.jpg" not in (investigation / "case.json").read_text(encoding='utf-8')
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
    text = report.read_text(encoding='utf-8')
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
    path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError):
        render_html(investigation)


def test_pdf_with_cjk_and_comparison_images(investigation):
    pytest.importorskip("reportlab")
    from photo_location_workflow.report import render_pdf
    candidate(investigation, "示例建筑", "虚构地址", "https://example.org/")
    add_evidence(investigation, "c1", "reference", "https://example.org/", "match", "中文备注与原图并排。", investigation / "assets/source.png")
    crop(investigation, (0, 0, 30, 30), "detail", 2)
    try:
        output = render_pdf(investigation)
    except ValueError as exc:
        if 'PDF needs an embeddable CJK' not in str(exc):
            raise
        import os
        if os.environ.get('PDF_REQUIRE_FONT') == '1':
            raise
        pytest.skip('No embeddable CJK font installed; Linux CI requires this test.')
    raw = output.read_bytes()
    assert raw.startswith(b"%PDF-")
    assert b"/FontFile2" in raw  # The actual font program travels with the report.


def test_crop_names_cannot_overwrite_source_or_evidence(investigation):
    original = hash_file(investigation / 'assets/source.png')
    for label in ['source', 'e1', 'source-pixels', '门框']:
        crop(investigation, (0, 0, 20, 20), label, 2)
    candidate(investigation, 'Building', 'Address', 'https://example.org/')
    add_evidence(investigation, 'c1', 'reference', 'https://example.org/', 'match', 'Observed', investigation / 'assets/source.png')
    assert hash_file(investigation / 'assets/source.png') == original
    assert check_case(investigation)['ok']


def test_missing_or_changed_asset_blocks_upgrade_and_report(investigation):
    candidate(investigation, 'Building', 'Address', 'https://example.org/')
    add_evidence(investigation, 'c1', 'official', 'https://example.org/', 'match', 'Checked')
    item = add_evidence(investigation, 'c1', 'streetview', 'https://maps.google.com/', 'match', 'Observed', investigation / 'assets/source.png', '2026-06')
    target = investigation / item['asset']
    target.write_bytes(b'changed')
    assert not check_case(investigation)['ok']
    with pytest.raises(ValueError):
        conclude(investigation, 'c1', 'confirmed', 'Should be rejected')
    with pytest.raises(ValueError):
        render_html(investigation)
    target.unlink()
    assert any('Missing asset' in s for s in check_case(investigation)['errors'])


def test_reviews_preserve_contradiction_history(investigation):
    candidate(investigation, 'Building', 'Address', 'https://example.org/')
    add_evidence(investigation, 'c1', 'official', 'https://example.org/', 'match', 'Address')
    add_evidence(investigation, 'c1', 'streetview', 'https://maps.google.com/', 'contradiction', 'Apparent wrong side of road', investigation / 'assets/source.png', 'unknown', 'Visitor panorama')
    with pytest.raises(ValueError):
        conclude(investigation, 'c1', 'confirmed', 'Not resolved')
    reviewed = review_evidence(investigation, 'e2', 'match', 'Camera was facing the opposite direction; road layout now verified.')
    assert reviewed['original_verdict'] == 'contradiction'
    assert reviewed['reviews'][0]['from'] == 'contradiction'
    assert reviewed['notes'] == 'Apparent wrong side of road'
    conclude(investigation, 'c1', 'confirmed', 'Rechecked geometry')
    assert 'Review history' in render_html(investigation).read_text(encoding='utf-8')
    review_evidence(investigation, 'e2', 'unclear', 'Insufficient detail')
    assert load(investigation)['conclusion']['level'] == 'candidate'
    assert len(load(investigation)['evidence'][1]['reviews']) == 2


def test_legacy_schema_one_cases_remain_readable(investigation):
    data = load(investigation)
    del data['source']['sha256']
    save(investigation, data)
    result = check_case(investigation)
    assert result['ok'] and result['warnings']
    assert render_html(investigation).is_file()


def test_report_output_protects_records_and_assets(investigation):
    for output in [investigation / 'case.json', investigation / 'assets/out.html']:
        with pytest.raises(ValueError):
            render_html(investigation, output)
    output = render_html(investigation, investigation / 'exports/deep/report.html')
    assert output.is_file()
    assert load(investigation)['schema_version'] == 1


def test_selected_asset_rejects_changed_source_or_unlisted_file(investigation):
    with pytest.raises(ValueError):
        selected_asset(investigation, '../input.jpg')
    (investigation / 'assets/source.png').write_bytes(b'changed')
    with pytest.raises(ValueError):
        selected_asset(investigation)


@pytest.mark.parametrize('captured', ['2026-00', '0000-01', '2026-1', None])
def test_panorama_month_validation(investigation, captured):
    candidate(investigation, 'Building', 'Address', 'https://example.org/')
    with pytest.raises(ValueError):
        add_evidence(investigation, 'c1', 'streetview', 'https://maps.google.com/', 'match', 'Observed', captured=captured)


def test_check_cli_has_nonzero_exit_for_broken_asset(investigation):
    (investigation / 'assets/source.png').unlink()
    result = subprocess.run([sys.executable, '-m', 'photo_location_workflow', 'check', str(investigation)], capture_output=True, text=True)
    assert result.returncode == 1
    assert 'Missing asset' in result.stdout


def test_lens_result_detection_does_not_accept_lookalike_domains():
    from photo_location_workflow.lens import is_results_page
    assert is_results_page('https://www.google.com/search?q=example')
    assert is_results_page('https://lens.google.com/search')
    assert not is_results_page('https://www.google.com.evil.test/search')
    assert not is_results_page('https://www.google.com/')
