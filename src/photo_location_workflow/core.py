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
    if (p.scheme not in ("http", "https") or not p.hostname or p.username or p.password
            or any(ord(ch) < 32 for ch in value)):
        raise ValueError("Use an http(s) URL without embedded credentials.")
    return value


def hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


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


def prepare_phone_format(source):
    """Register optional HEIF support for an iPhone original, including extensionless uploads."""
    with Path(source).open('rb') as stream:
        header = stream.read(64)
    if header[4:8] == b'ftyp' and any(brand in header for brand in (b'heic', b'heix', b'hevc', b'hevx', b'mif1', b'msf1')):
        try:
            from pillow_heif import register_heif_opener
        except ImportError as exc:
            raise ValueError('HEIC/HEIF needs the mobile extra: pip install "photo-location-workflow[mobile]"; or export JPEG. / 请安装 mobile 扩展或先导出 JPEG。') from exc
        register_heif_opener(thumbnails=False)


def copy_image(source, target):
    """Normalize orientation and remove EXIF/GPS by copying decoded pixels."""
    prepare_phone_format(source)
    with Image.open(source) as original:
        oriented = ImageOps.exif_transpose(original).convert("RGB")
        clean = Image.new("RGB", oriented.size)
        clean.paste(oriented)
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            clean.save(stream, format="PNG")
        return list(clean.size)


def init_case(photo, case):
    root = Path(case)
    if root.exists() and any(root.iterdir()):
        raise ValueError("Choose an empty case directory; existing files are never overwritten.")
    photo = Path(photo).resolve()
    prepare_phone_format(photo)
    with Image.open(photo) as im:
        im.verify()
    root.mkdir(parents=True, exist_ok=True)
    (root / "assets").mkdir()
    size = copy_image(photo, root / "assets/source.png")
    data = {
        "schema_version": 1, "created_at": now(),
        "source": {"asset": "assets/source.png", "size": size,
                   "original_sha256": hash_file(photo),
                   "sha256": hash_file(root / "assets/source.png"),
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
    if not re.fullmatch(r"[\w-]{1,48}", label):
        raise ValueError("Label must use 1-48 letters, numbers, underscores or hyphens.")
    if any(c["label"] == label for c in data["crops"]):
        raise ValueError("Crop label already exists.")
    x, y, w, h = box
    if w * h * scale * scale > 40_000_000:
        raise ValueError("Zoom would exceed 40 million pixels; use a smaller crop or scale.")
    with Image.open(asset_path(case, data["source"]["asset"])) as im:
        if min(x, y) < 0 or min(w, h) <= 0 or x + w > im.width or y + h > im.height:
            raise ValueError("Crop must fit inside the source image: x,y,width,height.")
        cut = im.crop((x, y, x + w, y + h))
        paths = {"native": f"assets/crops/{label}/native.png", "zoom": f"assets/crops/{label}/pixels.png"}
        folder = asset_path(case, paths['native']).parent
        folder.mkdir(parents=True, exist_ok=False)
        cut.save(folder / 'native.png')
        cut.resize((w * scale, h * scale), Image.Resampling.NEAREST).save(folder / 'pixels.png')
    item = {"label": label, "box": list(box), "scale": scale, **paths,
            "native_sha256": hash_file(asset_path(case, paths['native'])),
            "zoom_sha256": hash_file(asset_path(case, paths['zoom']))}
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


def selected_asset(case, relative=None):
    data = load(case)
    relative = relative or data['source']['asset']
    allowed = [data['source']['asset']] + [c['native'] for c in data['crops']]
    if relative not in allowed:
        raise ValueError("Select the prepared source or a native crop listed in case.json.")
    path = asset_path(case, relative)
    if not path.is_file():
        raise ValueError(f"Prepared image is missing: {relative}")
    expected = data['source'].get('sha256') if relative == data['source']['asset'] else next(
        c.get('native_sha256') for c in data['crops'] if c['native'] == relative)
    if expected and hash_file(path) != expected:
        raise ValueError(f'Prepared image changed: {relative}; review it before uploading.')
    return relative, path


def add_evidence(case, candidate_id, kind, url, verdict, notes, image=None, captured=None, provider=None, map_view=None):
    data = load(case)
    find_candidate(data, candidate_id)
    if kind not in KINDS or verdict not in VERDICTS:
        raise ValueError("Invalid evidence kind or verdict.")
    web_url(url)
    if not notes.strip():
        raise ValueError("Describe the observed details or uncertainty.")
    from .maps import capture_date, clean_view
    captured = capture_date(captured, kind == 'streetview')
    view = clean_view(map_view) if map_view is not None else None
    if view and view['tool'] == 'google_streetview' and kind != 'streetview':
        raise ValueError('Google Street View requires Street View evidence.')
    item = {"id": f"e{len(data['evidence']) + 1}", "candidate_id": candidate_id,
            "kind": kind, "url": url, "verdict": verdict, "notes": notes,
            "captured": captured, "provider": provider, "reviewed_at": now(), "asset": None,
            "original_verdict": verdict, "reviews": []}
    if view:
        item['map_view'] = {**view, 'saved_at': now()}
    if image:
        item["asset"] = f"assets/evidence/{item['id']}.png"
        copy_image(image, asset_path(case, item["asset"]))
        item['sha256'] = hash_file(asset_path(case, item['asset']))
    data["evidence"].append(item)
    # A new observation invalidates the old conclusion until reviewed again.
    data["conclusion"] = {"level": "candidate", "candidate_id": candidate_id, "note": "New evidence added; review conclusion again."}
    save(case, data)
    return item


def review_evidence(case, evidence_id, verdict, reason):
    """Revise a judgment while keeping the observation and review history."""
    data = load(case)
    if verdict not in VERDICTS or not reason.strip():
        raise ValueError('A valid verdict and an explanation are required.')
    item = next((e for e in data['evidence'] if e['id'] == evidence_id), None)
    if item is None:
        raise ValueError(f'Unknown evidence: {evidence_id}')
    item.setdefault('original_verdict', item['verdict'])
    item.setdefault('reviews', []).append({'from': item['verdict'], 'to': verdict,
                                          'reason': reason, 'at': now()})
    item['verdict'] = verdict
    data['conclusion'] = {'level': 'candidate', 'candidate_id': item['candidate_id'],
                          'note': 'Evidence reviewed; assess the conclusion again.'}
    save(case, data)
    return item


def check_case(case):
    """Offline integrity check. It does not verify facts or source authenticity."""
    data = load(case)
    errors, warnings = [], []
    refs = [(data['source']['asset'], data['source'].get('sha256'))]
    for c in data['crops']:
        refs += [(c['native'], c.get('native_sha256')), (c['zoom'], c.get('zoom_sha256'))]
    refs += [(e['asset'], e.get('sha256')) for e in data['evidence'] if e.get('asset')]
    refs += [(s['screenshot'], s.get('sha256')) for s in data['searches'] if s.get('screenshot')]
    for relative, expected in refs:
        try:
            path = asset_path(case, relative)
            if not path.is_file():
                errors.append(f'Missing asset: {relative}')
            elif expected and hash_file(path) != expected:
                errors.append(f'Asset changed: {relative}')
            elif not expected:
                warnings.append(f'No stored checksum (legacy or incomplete record): {relative}')
        except ValueError as exc:
            errors.append(str(exc))
    ids = {c['id'] for c in data['candidates']}
    if len(ids) != len(data['candidates']):
        errors.append('Duplicate candidate IDs.')
    if len({e['id'] for e in data['evidence']}) != len(data['evidence']):
        errors.append('Duplicate evidence IDs.')
    from .maps import clean_location, clean_view, capture_date
    for c in data['candidates']:
        if c.get('map_location') is not None:
            try:
                clean_location(c['map_location'])
            except (ValueError, TypeError, AttributeError) as exc:
                errors.append(f"Invalid map location in {c['id']}: {exc}")
    for e in data['evidence']:
        if e.get('map_view') is not None:
            try:
                normalized = clean_view(e['map_view'])
                if normalized['replay_url'] != e['map_view'].get('replay_url') or normalized['replay_mode'] != e['map_view'].get('replay_mode'):
                    raise ValueError('Saved replay URL / mode does not match its parameters.')
                if normalized['tool'] == 'google_streetview' and e['kind'] != 'streetview':
                    raise ValueError('Google Street View requires Street View evidence.')
                capture_date(e.get('captured'), True)
            except (ValueError, TypeError, AttributeError) as exc:
                errors.append(f"Invalid map view in {e['id']}: {exc}")
        if e['candidate_id'] not in ids:
            errors.append(f"Unknown candidate in {e['id']}.")
        try:
            from .annotations import validate_annotations
            validate_annotations(case, data, e)
        except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
            errors.append(f"Invalid annotations in {e['id']}: {exc}")
    con = data['conclusion']
    if con.get('candidate_id') is not None and con['candidate_id'] not in ids:
        errors.append('Unknown conclusion candidate.')
    return {'ok': not errors, 'errors': errors, 'warnings': warnings,
            'assets_checked': len(refs), 'checked_at': now()}


def conclude(case, candidate_id, level, note):
    data = load(case)
    find_candidate(data, candidate_id)
    if level not in LEVELS or not note.strip():
        raise ValueError("Choose a valid confidence and supply a reason.")
    items = [e for e in data["evidence"] if e["candidate_id"] == candidate_id]
    if level in ("high", "confirmed"):
        integrity = check_case(case)
        if not integrity['ok']:
            raise ValueError('Fix case integrity errors before upgrading: ' + '; '.join(integrity['errors']))
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
