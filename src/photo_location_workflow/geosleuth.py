"""Optional local bridge to an independently installed geo-sleuth skill.

External results stay in a separate workspace. They never change case evidence
or confidence, and ranking shares are never interpreted as probabilities.
"""

import json
import os
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from uuid import uuid4

from .core import hash_file, load, now, selected_asset

UPSTREAM = "https://github.com/Oldcircle/geo-sleuth"
REVIEWED_REVISION = "836d70eea196b194391017e6e018e04ccc85aaa4"


def _write(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


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


def _execute(root, manifest, script, arguments, timeout=120):
    command = [manifest["uv"], "run", str(Path(manifest["skill_dir"]) / "scripts" / script), *arguments]
    env = dict(os.environ, UV=manifest["uv"], PYTHONIOENCODING="utf-8")
    entry = {"started_at": now(), "script": script, "arguments": arguments}
    manifest["commands"].append(entry)
    try:
        result = subprocess.run(command, cwd=root, env=env, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=timeout)
        entry.update(returncode=result.returncode, output=(result.stdout + result.stderr)[-100_000:])
    except (OSError, subprocess.TimeoutExpired) as exc:
        entry.update(error=f"{type(exc).__name__}: external tool did not finish")
        raise ValueError(entry["error"]) from exc
    finally:
        _write(root / "bridge.json", manifest)
    if result.returncode:
        raise ValueError(f"geo-sleuth {script} failed ({result.returncode}); see bridge.json command log.")
    return result


def prepare(case, workspace, skill_dir=None, uv=None, asset=None):
    """Export a verified metadata-free image and initialize a candidate board."""
    case = Path(case).resolve()
    root = Path(workspace).resolve()
    if root == case or root.is_relative_to(case):
        raise ValueError("Use a separate workspace outside the case directory.")
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
    _execute(root, manifest, "board.py", ["init", "--photo", "input.png", "--case", "Photo Location Workflow"])
    # Names are arguments, never shell text; -- protects names beginning with '-'.
    counts = Counter(c["name"] for c in data["candidates"])
    names = [c["name"] if counts[c["name"]] == 1 else f"{c['name']} [{c['id']}]"
             for c in data["candidates"]]
    manifest["candidate_mapping"] = dict(zip(names, (c["id"] for c in data["candidates"])))
    if names:
        _execute(root, manifest, "board.py", ["add", "--level", "area", "--note",
                 "Imported hypothesis; geographic level and address require review.", "--", *names])
    manifest["prepared"] = True
    _write(root / "bridge.json", manifest)
    return {"workspace": str(root), "candidates_exported": len(names), "image": "input.png",
            "image_upload_performed": False, "next": "geo-sleuth intake, then geo-sleuth review"}


def _validate(case, workspace):
    root = Path(workspace).resolve()
    m = _read(_inside(root, "bridge.json"))
    if m.get("schema_version") != 1 or not m.get("prepared"):
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


def intake(case, workspace, ocr=False):
    """Run local preprocessing; reverse-image uploads are always disabled."""
    root, m = _validate(case, workspace)
    output = "intake-" + uuid4().hex[:12]
    args = ["input.png", "--out-dir", output, "--no-rev"]
    if not ocr:
        args.append("--no-ocr")
    _execute(root, m, "intake.py", args, timeout=600)
    result = _read(_inside(root, output + "/intake.json"))
    if result.get("result") not in ("ok", "partial"):
        raise ValueError("Intake did not produce usable visual steps; inspect its command log.")
    m["intake"] = output
    _write(root / "bridge.json", m)
    return {"workspace": str(root), "result": result["result"], "status": result.get("status", {}),
            "image_upload_performed": False, "ocr_is_unreviewed": True, "report": output + "/intake.md"}


def review(case, workspace):
    """Snapshot external suggestions for review without mutating the case."""
    root, m = _validate(case, workspace)
    board_path = _inside(root, "board.json")
    board = _read(board_path)
    if not isinstance(board.get("candidates"), dict) or board.get("photo") != "input.png":
        raise ValueError("Invalid external candidate board.")
    # Use a fresh result file: never merge an old result's conclusion/coordinates.
    target = "result-" + uuid4().hex + ".json"
    try:
        _execute(root, m, "board.py", ["report", "--merge", target])
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
