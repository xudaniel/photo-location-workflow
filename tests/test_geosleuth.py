import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from photo_location_workflow import geosleuth
from photo_location_workflow.cli import main
from photo_location_workflow.tasks import TaskStopped
from photo_location_workflow.core import candidate, crop, init_case


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    source = tmp_path / "private.jpg"
    exif = Image.Exif()
    exif[270] = "private original metadata"
    Image.new("RGB", (40, 30), "green").save(source, exif=exif)
    case = tmp_path / "case"
    init_case(source, case)
    candidate(case, "-Possible place", "Address to verify", "https://example.org/")
    skill = tmp_path / "skill"
    (skill / "scripts").mkdir(parents=True)
    for name in ("board.py", "intake.py", "_net.py", "regions.py"):
        (skill / "scripts" / name).write_text("# External tool fixture\n", encoding="utf-8")
    monkeypatch.setattr(geosleuth.shutil, "which", lambda _: sys.executable)
    calls = []

    def external(command, **kwargs):
        calls.append(command)
        root = Path(kwargs["cwd"])
        script, args = Path(command[2]).name, command[3:]
        if script == "board.py" and args[0] == "init":
            (root / "board.json").write_text('{"candidates": {}, "photo": "input.png"}', encoding="utf-8")
        elif script == "board.py" and args[0] == "report":
            result = {"board": {"main": {"name": "External guess", "share": 1.0}, "alternatives": []}}
            (root / args[-1]).write_text(json.dumps(result), encoding="utf-8")
        elif script == "intake.py":
            out = root / args[args.index("--out-dir") + 1]
            out.mkdir()
            (out / "intake.json").write_text(json.dumps({"result": "partial", "status": {
                "edges": "ok", "variants": "failed"}, "ocr": [{"text": "uncertain plate", "pass": "up"}]}), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="external output", stderr="")

    monkeypatch.setattr(geosleuth, "run_process", external)
    return case, tmp_path / "workspace", skill, calls


def test_bridge_keeps_external_claims_out_of_case(bridge):
    case, workspace, skill, calls = bridge
    before = (case / "case.json").read_bytes()
    result = geosleuth.prepare(case, workspace, skill)
    assert result["candidates_exported"] == 1
    assert calls[1][-2:] == ["--", "-Possible place"]
    with Image.open(workspace / "input.png") as im:
        assert not im.getexif()
    intake = geosleuth.intake(case, workspace)
    assert intake["result"] == "partial"  # A zero exit alone is not full success.
    assert {"--no-rev", "--no-ocr"}.issubset(calls[-1])
    snapshot = geosleuth.review(case, workspace)
    assert snapshot["review_status"] == "unreviewed"
    assert snapshot["board"]["main"]["share"] == 1.0
    assert snapshot["ranking_is_probability"] is False
    assert snapshot["ocr_hypotheses"][0]["pass"] == "up"
    assert snapshot["image_search"] == "not performed by bridge"
    assert (case / "case.json").read_bytes() == before
    assert not list(workspace.glob("result-*.json"))


def test_native_crop_only_and_no_overwrite(bridge):
    case, workspace, skill, _ = bridge
    item = crop(case, (1, 2, 10, 12), "sign")
    with pytest.raises(ValueError, match="native crop"):
        geosleuth.prepare(case, workspace, skill, asset=item["zoom"])
    geosleuth.prepare(case, workspace, skill, asset=item["native"])
    with Image.open(workspace / "input.png") as im:
        assert im.size == (10, 12)
    with pytest.raises(ValueError, match="empty"):
        geosleuth.prepare(case, workspace, skill)
    with pytest.raises(ValueError, match="outside"):
        geosleuth.prepare(case, case / "external", skill)


def test_changed_input_or_upstream_requires_new_workspace(bridge):
    case, workspace, skill, _ = bridge
    geosleuth.prepare(case, workspace, skill)
    original = (workspace / "input.png").read_bytes()
    (workspace / "input.png").write_bytes(b"changed")
    with pytest.raises(ValueError, match="does not match"):
        geosleuth.review(case, workspace)
    (workspace / "input.png").write_bytes(original)
    (skill / "scripts/board.py").write_text("# changed code", encoding="utf-8")
    with pytest.raises(ValueError, match="scripts changed"):
        geosleuth.intake(case, workspace)


def test_same_name_candidates_keep_separate_case_identities(bridge):
    case, workspace, skill, calls = bridge
    candidate(case, "-Possible place", "Different address", "https://example.org/other")
    result = geosleuth.prepare(case, workspace, skill)
    assert result["candidates_exported"] == 2
    assert calls[-1][-2:] == ["-Possible place [c1]", "-Possible place [c2]"]
    m = json.loads((workspace / "bridge.json").read_text(encoding="utf-8"))
    assert set(m["candidate_mapping"].values()) == {"c1", "c2"}


def test_board_cannot_silently_refer_to_another_photo(bridge):
    case, workspace, skill, _ = bridge
    geosleuth.prepare(case, workspace, skill)
    (workspace / "board.json").write_text('{"photo": "another.png", "candidates": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="candidate board"):
        geosleuth.review(case, workspace)


def test_workspace_rejects_escape_and_oversized_external_json(bridge):
    case, workspace, skill, _ = bridge
    geosleuth.prepare(case, workspace, skill)
    path = workspace / "bridge.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["intake"] = "../private"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="stay inside"):
        geosleuth.review(case, workspace)
    (workspace / "board.json").write_bytes(b" " * 5_000_001)
    with pytest.raises(ValueError, match="exceeds"):
        geosleuth.review(case, workspace)


@pytest.mark.parametrize("timeout", [False, True])
def test_failed_process_is_logged_and_workspace_is_not_ready(bridge, monkeypatch, timeout):
    case, workspace, skill, _ = bridge

    def fail(command, **kwargs):
        if timeout:
            raise TaskStopped("timed_out")
        return SimpleNamespace(returncode=7, stdout="partial log", stderr="upstream failure")

    monkeypatch.setattr(geosleuth, "run_process", fail)
    with pytest.raises(ValueError):
        geosleuth.prepare(case, workspace, skill)
    log = json.loads((workspace / "bridge.json").read_text(encoding="utf-8"))
    assert not log["prepared"]
    assert log["commands"][0].get("error") if timeout else log["commands"][0]["returncode"] == 7
    with pytest.raises(ValueError, match="incomplete"):
        geosleuth.review(case, workspace)


def test_cli_ocr_is_explicit_and_requires_no_openai_key(bridge, monkeypatch, capsys):
    case, workspace, skill, calls = bridge
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert main(["geo-sleuth", "prepare", str(case), "--workspace", str(workspace), "--skill-dir", str(skill)]) == 0
    assert main(["geo-sleuth", "intake", str(case), "--workspace", str(workspace), "--ocr"]) == 0
    assert "--no-rev" in calls[-1] and "--no-ocr" not in calls[-1]
    assert main(["geo-sleuth", "review", str(case), "--workspace", str(workspace)]) == 0
    assert '"review_status": "unreviewed"' in capsys.readouterr().out


def test_resume_partial_preparation_does_not_initialize_board_twice(bridge, monkeypatch):
    case, workspace, skill, calls = bridge
    original = geosleuth.run_process
    fail = True

    def interrupted(command, **kwargs):
        if fail and command[3] == 'add':
            raise TaskStopped('cancelled')
        return original(command, **kwargs)

    monkeypatch.setattr(geosleuth, 'run_process', interrupted)
    with pytest.raises(TaskStopped):
        geosleuth.prepare(case, workspace, skill)
    fail = False
    geosleuth.prepare(case, workspace, skill, resume=True)
    assert len([call for call in calls if call[3] == 'init']) == 1
    assert json.loads((workspace/'bridge.json').read_text())['prepared'] is True
