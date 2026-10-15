import json
import re
import subprocess
import sys

from PIL import Image
import pytest

from photo_location_workflow.annotations import add_annotation, remove_annotation
from photo_location_workflow.core import add_evidence, candidate, check_case, conclude, hash_file, init_case, load, save
from photo_location_workflow.report import render_html, render_pdf


@pytest.fixture
def paired_case(tmp_path):
    source, reference = tmp_path / 'source.png', tmp_path / 'reference.png'
    Image.new('RGB', (100, 80), '#dce6d6').save(source)
    Image.new('RGB', (200, 100), '#243a35').save(reference)
    case = tmp_path / 'case'
    init_case(source, case)
    candidate(case, 'Synthetic', 'No address', 'https://example.org/')
    add_evidence(case, 'c1', 'reference', 'https://example.org/', 'match', 'Illustration only', reference)
    return case


def test_pixel_regions_survive_reload_and_do_not_change_assets(paired_case):
    data = load(paired_case)
    before = {path: hash_file(paired_case / path) for path in [data['source']['asset'], data['evidence'][0]['asset']]}
    item = add_annotation(paired_case, 'e1', 'Three windows / 三扇窗', [10, 20, 30, 15], [80, 10, 60, 25])
    assert item['number'] == 1
    assert load(paired_case)['evidence'][0]['annotations'][0]['reference_box'] == [80, 10, 60, 25]
    assert check_case(paired_case)['ok']
    render_html(paired_case)
    assert all(hash_file(paired_case / path) == digest for path, digest in before.items())


@pytest.mark.parametrize('bad', [[-1, 0, 20, 20], [0, 0, 0, 20], [90, 70, 20, 20], [1.2, 0, 1, 1], [True, 0, 1, 1], [0, 0, 1], '0,0,1,1'])
def test_invalid_regions_never_mutate_record(paired_case, bad):
    before = (paired_case / 'case.json').read_bytes()
    with pytest.raises(ValueError):
        add_annotation(paired_case, 'e1', 'Detail', bad, [0, 0, 20, 20])
    assert (paired_case / 'case.json').read_bytes() == before


def test_reference_bounds_and_missing_reference_are_rejected(paired_case):
    with pytest.raises(ValueError):
        add_annotation(paired_case, 'e1', 'Detail', [0, 0, 5, 5], [190, 90, 20, 20])
    add_evidence(paired_case, 'c1', 'official', 'https://example.org/', 'match', 'Address example')
    with pytest.raises(ValueError):
        add_annotation(paired_case, 'e2', 'No image', [0, 0, 5, 5], [0, 0, 5, 5])
    with pytest.raises(ValueError):
        add_annotation(paired_case, 'e1', '', [0, 0, 5, 5], [0, 0, 5, 5])


def test_removed_numbers_are_not_reused_and_history_is_exported(paired_case):
    add_annotation(paired_case, 'e1', 'Wrong rectangle', [0, 0, 5, 5], [0, 0, 5, 5])
    remove_annotation(paired_case, 'e1', 'a1', 'Marked the wrong window')
    item = add_annotation(paired_case, 'e1', 'Correct window', [10, 10, 5, 5], [20, 10, 5, 5])
    data = load(paired_case)
    assert item['id'] == 'a2'
    assert data['evidence'][0]['annotation_history'][0]['annotation']['source_box'] == [0, 0, 5, 5]
    assert 'Marked the wrong window' in render_html(paired_case).read_text(encoding='utf-8')


def test_annotation_change_requires_conclusion_review(paired_case):
    add_evidence(paired_case, 'c1', 'official', 'https://example.org/', 'match', 'Address example')
    conclude(paired_case, 'c1', 'high', 'Reviewed')
    add_annotation(paired_case, 'e1', 'Window', [0, 0, 10, 10], [0, 0, 20, 20])
    assert load(paired_case)['conclusion']['level'] == 'candidate'
    conclude(paired_case, 'c1', 'high', 'Reviewed again')
    remove_annotation(paired_case, 'e1', 'a1', 'Not the intended detail')
    assert load(paired_case)['conclusion']['level'] == 'candidate'


def test_corrupted_regions_block_report_and_confidence(paired_case):
    add_annotation(paired_case, 'e1', 'Window', [0, 0, 10, 10], [0, 0, 20, 20])
    data = load(paired_case)
    data['evidence'][0]['annotations'][0]['source_box'] = [0, 0, 99999, 2]
    save(paired_case, data)
    assert not check_case(paired_case)['ok']
    with pytest.raises(ValueError):
        render_html(paired_case)
    with pytest.raises(ValueError):
        conclude(paired_case, 'c1', 'high', 'Invalid region')


def test_html_contains_numbered_regions_detail_crops_and_escaped_label(paired_case):
    add_annotation(paired_case, 'e1', '<script>Windows / 窗户</script>', [10, 10, 20, 20], [30, 20, 40, 40])
    # A one-pixel region must remain a valid report input at any overview scale.
    add_annotation(paired_case, 'e1', 'One pixel', [99, 79, 1, 1], [199, 99, 1, 1])
    text = render_html(paired_case).read_text(encoding='utf-8')
    assert 'id="e1-a1"' in text and 'href="#e1-a2"' in text
    assert '&lt;script&gt;' in text and '<script>' not in text
    assert '[30, 20, 40, 40]' in text
    assert text.count('data:image/png;base64,') >= 7


def test_annotated_pdf_includes_dedicated_detail_pages(paired_case):
    pytest.importorskip('reportlab')
    add_annotation(paired_case, 'e1', 'Window / 窗户', [10, 10, 20, 20], [30, 20, 40, 40])
    try:
        output = render_pdf(paired_case)
    except ValueError as exc:
        import os
        if 'PDF needs an embeddable CJK' in str(exc) and os.environ.get('PDF_REQUIRE_FONT') != '1':
            pytest.skip('No CJK font installed')
        raise
    raw = output.read_bytes()
    assert raw.startswith(b'%PDF-') and b'/FontFile2' in raw
    assert len(re.findall(rb'/Type /Page\b', raw)) >= 3


def test_cli_can_record_regions(paired_case):
    result = subprocess.run([sys.executable, '-m', 'photo_location_workflow', 'annotate', str(paired_case), '--evidence', 'e1', '--label', 'Window', '--source-box', '10,10,20,20', '--reference-box', '30,20,40,40'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['source_box'] == [10, 10, 20, 20]


def test_overlapping_regions_keep_their_number_badges_separate():
    from photo_location_workflow.comparison import badge_position
    used = []
    for _ in range(4):
        badge_position((10, 10, 95, 60), (18, 20), (100, 80), used)
    assert len(used) == 4
    for i, rect in enumerate(used):
        assert 0 <= rect[0] < rect[2] <= 100 and 0 <= rect[1] < rect[3] <= 80
        for other in used[i+1:]:
            assert rect[2] <= other[0] or other[2] <= rect[0] or rect[3] <= other[1] or other[3] <= rect[1]
