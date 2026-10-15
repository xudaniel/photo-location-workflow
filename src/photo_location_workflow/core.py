"""Local image preparation and explicit, human-reviewed evidence records."""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from PIL import Image, ImageOps

KINDS = ("official", "streetview", "reference", "text")
VERDICTS = ("match", "unclear", "contradiction")
LEVELS = ("unknown", "candidate", "high", "confirmed")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def web_url(value):
    p = urlsplit(value)
    if p.scheme not in ("http", "https") or not p.netloc or p.username or p.password:
        raise ValueError("Use an http(s) URL without embedded credentials.")
    return value


def load(case):
    data = json.loads((Path(case) / "case.json").read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported case schema.")
    return data


def save(case, data):
    data["updated_at"] = now()
    path = Path(case) / "case.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def asset_path(case, relative):
    root = Path(case).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Asset path must stay within the case directory.")
    return path


def copy_image(source, target):
    """Normalize orientation and remove EXIF/GPS by copying decoded pixels."""
    with Image.open(source) as original:
        oriented = ImageOps.exif_transpose(original).convert("RGB")
        clean = Image.new("RGB", oriented.size)
        clean.paste(oriented)
        clean.save(target, format="PNG")
        return list(clean.size)


def init_case(photo, case):
    root = Path(case)
    if root.exists() and any(root.iterdir()):
        raise ValueError("Choose an empty case directory; existing files are never overwritten.")
    photo = Path(photo).resolve()
    with Image.open(photo) as im:
        im.verify()
    root.mkdir(parents=True, exist_ok=True)
    (root / "assets").mkdir()
    size = copy_image(photo, root / "assets/source.png")
    data = {
        "schema_version": 1, "created_at": now(),
        "source": {"asset": "assets/source.png", "size": size,
                   "original_sha256": hashlib.sha256(photo.read_bytes()).hexdigest(),
                   "metadata_removed": True},
        "crops": [], "searches": [], "candidates": [], "evidence": [],
        "conclusion": {"level": "unknown", "candidate_id": None, "note": ""},
    }
    save(root, data)
    return data


def crop(case, box, label, scale=4):
    data = load(case)
    if not 1 <= scale <= 16:
        raise ValueError("Scale must be between 1 and 16.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", label):
        raise ValueError("Label must use 1-48 letters, numbers, underscores or hyphens.")
    if any(c["label"] == label for c in data["crops"]):
        raise ValueError("Crop label already exists.")
    x, y, w, h = box
    with Image.open(asset_path(case, data["source"]["asset"])) as im:
        if min(x, y) < 0 or min(w, h) <= 0 or x + w > im.width or y + h > im.height:
            raise ValueError("Crop must fit inside the source image: x,y,width,height.")
        cut = im.crop((x, y, x + w, y + h))
        paths = {"native": f"assets/{label}.png", "zoom": f"assets/{label}-pixels.png"}
        cut.save(asset_path(case, paths["native"]))
        cut.resize((w * scale, h * scale), Image.Resampling.NEAREST).save(asset_path(case, paths["zoom"]))
    item = {"label": label, "box": list(box), "scale": scale, **paths}
    data["crops"].append(item)
    save(case, data)
    return item


def candidate(case, name, address, url):
    web_url(url)
    if not name.strip() or not address.strip():
        raise ValueError("Candidate name and address cannot be blank.")
    data = load(case)
    item = {"id": f"c{len(data['candidates']) + 1}", "name": name, "address": address,
            "source_url": url, "maps_url": "https://www.google.com/maps/search/?" + urlencode({"api": 1, "query": f"{name} {address}"})}
    data["candidates"].append(item)
    data["conclusion"] = {"level": "candidate", "candidate_id": item["id"], "note": "Awaiting evidence review."}
    save(case, data)
    return item


def find_candidate(data, candidate_id):
    for item in data["candidates"]:
        if item["id"] == candidate_id:
            return item
    raise ValueError(f"Unknown candidate: {candidate_id}")


def add_evidence(case, candidate_id, kind, url, verdict, notes, image=None, captured=None):
    data = load(case)
    find_candidate(data, candidate_id)
    if kind not in KINDS or verdict not in VERDICTS:
        raise ValueError("Invalid evidence kind or verdict.")
    web_url(url)
    if not notes.strip():
        raise ValueError("Describe the observed details or uncertainty.")
    if kind == "streetview" and (not captured or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])|unknown", captured)):
        raise ValueError("Street View needs --captured YYYY-MM, or unknown when no date is displayed.")
    item = {"id": f"e{len(data['evidence']) + 1}", "candidate_id": candidate_id,
            "kind": kind, "url": url, "verdict": verdict, "notes": notes,
            "captured": captured, "reviewed_at": now(), "asset": None}
    if image:
        item["asset"] = f"assets/{item['id']}.png"
        copy_image(image, asset_path(case, item["asset"]))
    data["evidence"].append(item)
    # A new observation invalidates the old conclusion until reviewed again.
    data["conclusion"] = {"level": "candidate", "candidate_id": candidate_id, "note": "New evidence added; review conclusion again."}
    save(case, data)
    return item


def conclude(case, candidate_id, level, note):
    data = load(case)
    find_candidate(data, candidate_id)
    if level not in LEVELS or not note.strip():
        raise ValueError("Choose a valid confidence and supply a reason.")
    items = [e for e in data["evidence"] if e["candidate_id"] == candidate_id]
    if level in ("high", "confirmed"):
        if any(e["verdict"] == "contradiction" for e in items):
            raise ValueError("Unresolved contradictions prevent high/confirmed confidence.")
        official = any(e["kind"] == "official" and e["verdict"] == "match" for e in items)
        visual = any(e["kind"] in ("streetview", "reference") and e["verdict"] == "match" and e["asset"] for e in items)
        if not (official and visual):
            raise ValueError("High/confirmed needs an official address match and an attached visual comparison.")
        if level == "confirmed" and not any(e["kind"] == "streetview" and e["verdict"] == "match" and e["asset"] for e in items):
            raise ValueError("Confirmed additionally needs a reviewed Street View/360 image.")
    data["conclusion"] = {"level": level, "candidate_id": candidate_id, "note": note, "reviewed_at": now()}
    save(case, data)
    return data["conclusion"]
