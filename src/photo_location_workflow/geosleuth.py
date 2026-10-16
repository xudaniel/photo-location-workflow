"""Optional local bridge to an independently installed geo-sleuth skill.

External results stay in a separate workspace. They never change case evidence
or confidence, and ranking shares are never interpreted as probabilities.
"""

import json
import os
import shutil
from collections import Counter
from functools import wraps
from pathlib import Path
from uuid import uuid4

from .core import hash_file, load, now, selected_asset
from .tasks import TaskStopped, atomic_json, run_process, workspace_lock

UPSTREAM = "https://github.com/Oldcircle/geo-sleuth"
REVIEWED_REVISION = "836d70eea196b194391017e6e018e04ccc85aaa4"


def _write(path, value):
    atomic_json(path, value)


def exclusive(fn):
    @wraps(fn)
    def locked(case, workspace, *args, **kwargs):
        with workspace_lock(workspace):
            return fn(case, workspace, *args, **kwargs)
    return locked


def _read(path):
    if path.stat().st_size > 5_000_000:
        raise ValueError(f"External JSON exceeds 5 MB: {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path.name}")
    return value


def _inside(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("External workspace path must stay inside its directory.")
    return path


def _scripts(skill):
    paths = sorted((skill / "scripts").glob("*.py"))
    for name in ("board.py", "intake.py", "_net.py", "regions.py"):
        if not (skill / "scripts" / name).is_file():
            raise ValueError(f"Missing geo-sleuth script: {name}; install the complete skill.")
    return {p.name: hash_file(p) for p in paths}


def _execute(root, manifest, script, arguments, timeout=120, cancel=None):
    command = [manifest["uv"], "run", str(Path(manifest["skill_dir"]) / "scripts" / script), *arguments]
    env = dict(os.environ, UV=manifest["uv"], PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    entry = {"started_at": now(), "script": script, "arguments": arguments,
             "log": "logs/" + uuid4().hex + ".log", "status": "running"}
    for earlier in manifest["commands"]:
        earlier.pop("output", None)
    manifest["commands"].append(entry)
    _write(root / "bridge.json", manifest)
    try:
        result = run_process(command, cwd=root, env=env, log_path=_inside(root, entry["log"]),
                             timeout=timeout, cancel=cancel)
        entry.update(returncode=result.returncode, output=result.stdout[-100_000:],
                     status="completed" if result.returncode == 0 else "failed")
    except TaskStopped as exc:
        entry.update(status=exc.reason, error=str(exc))
        raise
    except (OSError, ValueError) as exc:
        entry.update(status="failed", error=f"{type(exc).__name__}: external tool did not finish")
        raise ValueError(entry["error"]) from exc
    finally:
        entry["finished_at"] = now()
        _write(root / "bridge.json", manifest)
    if result.returncode:
        raise ValueError(f"geo-sleuth {script} failed ({result.returncode}); see bridge.json command log.")
    return result


@exclusive

def prepare(case, workspace, skill_dir=None, uv=None, asset=None, *, resume=False, cancel=None):
    """Export a verified metadata-free image and initialize a candidate board."""
    case = Path(case).resolve()
    root = Path(workspace).resolve()
    if root == case or root.is_relative_to(case):
        raise ValueError("Use a separate workspace outside the case directory.")
    if resume and (root / "bridge.json").is_file():
        root, manifest = _validate(case, root, require_prepared=False)
        return _finish_prepare(case, root, manifest, cancel)
    if root.exists() and any(root.iterdir()):
        raise ValueError("Choose an empty geo-sleuth workspace; existing files are never overwritten.")
    skill = Path(skill_dir or Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills/geo-sleuth").resolve()
    scripts = _scripts(skill)
    uv_path = shutil.which(str(uv or "uv"))
    if not uv_path:
        raise ValueError("uv is required for geo-sleuth. Install uv or pass --uv /path/to/uv.")
    uv_path = str(Path(uv_path).resolve())
    relative, image = selected_asset(case, asset)
    data = load(case)
    root.mkdir(parents=True, exist_ok=True)
    # selected_asset only accepts prepared source/native crops and checks hashes.
    shutil.copyfile(image, root / "input.png")
    manifest = {"schema_version": 1, "created_at": now(), "prepared": False,
                "upstream": UPSTREAM, "integration_reviewed_revision": REVIEWED_REVISION,
                "skill_dir": str(skill), "script_sha256": scripts, "uv": uv_path,
                "case_source_sha256": data["source"]["sha256"], "asset": relative,
                "input_sha256": hash_file(root / "input.png"), "commands": [],
                "search_performed": False, "intake": None}
    _write(root / "bridge.json", manifest)
    return _finish_prepare(case, root, manifest, cancel)


def _finish_prepare(case, root, manifest, cancel):
    data = load(case)
    if manifest.get("prepared"):
        return {"workspace": str(root), "resumed": True}
    board_path = _inside(root, "board.json")
    if board_path.exists():
        board = _read(board_path)
        if board.get("photo") != "input.png" or not isinstance(board.get("candidates"), dict):
            raise ValueError("Invalid partially prepared board; use a fresh workspace.")
    else:
        _execute(root, manifest, "board.py", ["init", "--photo", "input.png", "--case", "Photo Location Workflow"], cancel=cancel)
    # Names are arguments, never shell text; -- protects names beginning with '-'.
    counts = Counter(c["name"] for c in data["candidates"])
    names = []
    for c in data["candidates"]:
        name = c["name"] if counts[c["name"]] == 1 else f"{c['name']} [{c['id']}]"
        while name in names:
            name += f" [{c['id']}]"
        names.append(name)
    manifest["candidate_mapping"] = dict(zip(names, (c["id"] for c in data["candidates"])))
    if names:
        _execute(root, manifest, "board.py", ["add", "--level", "area", "--note",
                 "Imported hypothesis; geographic level and address require review.", "--", *names], cancel=cancel)
    manifest["prepared"] = True
    _write(root / "bridge.json", manifest)
    return {"workspace": str(root), "candidates_exported": len(names), "image": "input.png",
            "image_upload_performed": False, "next": "geo-sleuth intake, then geo-sleuth review"}


def _validate(case, workspace, require_prepared=True):
    root = Path(workspace).resolve()
    m = _read(_inside(root, "bridge.json"))
    if m.get("schema_version") != 1 or (require_prepared and not m.get("prepared")):
        raise ValueError("Workspace is incomplete; prepare a fresh workspace.")
    if _scripts(Path(m["skill_dir"])) != m["script_sha256"]:
        raise ValueError("geo-sleuth scripts changed; review the update and prepare a fresh workspace.")
    data = load(case)
    _, image = selected_asset(case, m["asset"])
    if (data["source"]["sha256"] != m["case_source_sha256"] or
            hash_file(image) != m["input_sha256"] or
            hash_file(_inside(root, "input.png")) != m["input_sha256"]):
        raise ValueError("Workspace image does not match the selected case asset; prepare it again.")
    return root, m


@exclusive
def intake(case, workspace, ocr=False, *, reuse=False, cancel=None):
    """Run local preprocessing; reverse-image uploads are always disabled."""
    root, m = _validate(case, workspace)
    if reuse and m.get("intake") and m.get("ocr_enabled", False) == ocr:
        previous = _inside(root, m["intake"] + "/intake.json")
        try:
            intact = all(hash_file(_inside(root, path)) == digest
                         for path, digest in m.get('intake_artifacts', {}).items())
            if intact and m.get("intake_sha256") == hash_file(previous) and _read(previous).get("result") == "ok":
                return {"result": "ok", "reused": True}
        except OSError:
            pass  # Missing outputs can be regenerated in a new attempt.
    output = "intake-" + uuid4().hex[:12]
    args = ["input.png", "--out-dir", output, "--no-rev"]
    if not ocr:
        args.append("--no-ocr")
    _execute(root, m, "intake.py", args, timeout=600, cancel=cancel)
    result = _read(_inside(root, output + "/intake.json"))
    if result.get("result") not in ("ok", "partial"):
        raise ValueError("Intake did not produce usable visual steps; inspect its command log.")
    m.update(intake=output, ocr_enabled=ocr, intake_sha256=hash_file(_inside(root, output + "/intake.json")))
    m['intake_artifacts'] = {p.relative_to(root).as_posix(): hash_file(p)
                             for p in _inside(root, output).glob('*/*') if p.is_file()
                             and p.suffix.lower() in {'.jpg', '.jpeg', '.png'}}
    _write(root / "bridge.json", m)
    return {"workspace": str(root), "result": result["result"], "status": result.get("status", {}),
            "image_upload_performed": False, "ocr_is_unreviewed": True, "report": output + "/intake.md"}


@exclusive
def review(case, workspace, *, cancel=None):
    """Snapshot external suggestions for review without mutating the case."""
    root, m = _validate(case, workspace)
    board_path = _inside(root, "board.json")
    board = _read(board_path)
    if not isinstance(board.get("candidates"), dict) or board.get("photo") != "input.png":
        raise ValueError("Invalid external candidate board.")
    # Use a fresh result file: never merge an old result's conclusion/coordinates.
    target = "result-" + uuid4().hex + ".json"
    try:
        _execute(root, m, "board.py", ["report", "--merge", target], cancel=cancel)
        report = _read(_inside(root, target))["board"]
    finally:
        _inside(root, target).unlink(missing_ok=True)
    raw_intake = _read(_inside(root, m["intake"] + "/intake.json")) if m.get("intake") else {}
    snapshot = {"schema_version": 1, "created_at": now(), "review_status": "unreviewed",
                "upstream": UPSTREAM, "input_sha256": m["input_sha256"],
                "board_sha256": hash_file(board_path), "ranking_is_probability": False,
                "board": report, "ocr_hypotheses": raw_intake.get("ocr", []),
                "intake_status": raw_intake.get("status", {}),
                "image_search": "not performed by bridge", "street_view": "not performed by bridge",
                "next_steps": ["Review OCR against native pixels; do not complete unreadable plates.",
                               "Search with Google Lens and verify an authoritative address.",
                               "Compare actual Street View details and record the capture month.",
                               "Record reviewed evidence through photo-locate evidence or the web workbench."]}
    _write(root / "review.json", snapshot)
    return snapshot


@exclusive
def update_board(case, workspace, operation, *, cancel=None):
    """Apply a persisted, idempotent human observation or falsification test."""
    root, manifest = _validate(case, workspace)
    text = operation.get("text")
    if not isinstance(text, str) or not text.strip() or len(text) > 2000:
        raise ValueError("Write an observation or test using 1–2000 characters.")
    board = _read(_inside(root, "board.json"))
    if operation["kind"] == "clue":
        marker = "photo-location-workflow:" + operation["id"]
        if not any(c.get("source") == marker for c in board.get("clues", {}).values()):
            _execute(root, manifest, "board.py", ["clue", "--kind", "hint", "--status", "observed",
                     "--source", marker, "--file", "input.png", "--", text], cancel=cancel)
    elif operation["kind"] == "falsify":
        name = operation.get("candidate")
        if name not in board.get("candidates", {}):
            raise ValueError("Select a candidate on this run's board.")
        if text not in board.get("falsify", {}).get(name, []):
            _execute(root, manifest, "board.py", ["falsify", "--text", text, "--", name], cancel=cancel)
    else:
        raise ValueError("Unknown board operation.")
