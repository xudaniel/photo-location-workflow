import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .annotations import add_annotation, remove_annotation
from .core import KINDS, LEVELS, VERDICTS, add_evidence, candidate, check_case, conclude, crop, init_case, load, review_evidence, selected_asset
from .maps import TOOLS, candidate_links, export_kml, parse_google_url, save_location, save_view, shortlist_url
from .lens import LENS_URL, run_lens
from .report import render_html, render_pdf


def box(value):
    try:
        values = tuple(int(v) for v in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use x,y,width,height integers.") from exc
    if len(values) != 4:
        raise argparse.ArgumentTypeError("Use exactly four integers: x,y,width,height.")
    return values


def parser():
    p = argparse.ArgumentParser(description="Photo location: image search → distinctive crop → authoritative address → Street View → evidence report")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create a local case and an EXIF/GPS-free image copy.")
    init.add_argument("photo", type=Path)
    init.add_argument("--case", required=True, type=Path)
    ui = sub.add_parser("ui", help="Open the local bilingual photo investigation workbench.")
    ui.add_argument("--cases", type=Path, default=Path("cases"))
    ui.add_argument("--port", type=int, default=8765)
    ui.add_argument("--no-open", action="store_true")
    ui.add_argument("--env-file", type=Path, help="Optional local OpenAI key/model file; never copied into a case.")
    demo = sub.add_parser("demo", help="Create an offline demonstration with a synthetic image.")
    demo.add_argument("--case", type=Path, default=Path("cases/demo"))
    cut = sub.add_parser("crop", help="Crop distinctive details without inventing pixels.")
    cut.add_argument("case", type=Path)
    cut.add_argument("--box", type=box, required=True)
    cut.add_argument("--label", required=True)
    cut.add_argument("--scale", type=int, default=4)
    search = sub.add_parser("lens", help="Show search instructions; upload only with explicit --upload.")
    search.add_argument("case", type=Path)
    search.add_argument("--asset", help="Native crop path from case.json, e.g. assets/crops/facade/native.png.")
    search.add_argument("--upload", action="store_true", help="Send the selected prepared image to Google via a visible browser.")
    cand = sub.add_parser("candidate", help="Record a candidate, address and source URL.")
    cand.add_argument("case", type=Path)
    cand.add_argument("--name", required=True)
    cand.add_argument("--address", required=True)
    cand.add_argument("--url", required=True)
    ev = sub.add_parser("evidence", help="Record a reviewed source or comparison, including uncertainty.")
    ev.add_argument("case", type=Path)
    ev.add_argument("--candidate", required=True)
    ev.add_argument("--kind", choices=KINDS, required=True)
    ev.add_argument("--url", required=True)
    ev.add_argument("--verdict", choices=VERDICTS, required=True)
    ev.add_argument("--notes", required=True)
    ev.add_argument("--image", type=Path)
    ev.add_argument("--captured", help="Street View/360 capture year YYYY, month YYYY-MM, or unknown.")
    ev.add_argument("--provider", help="E.g. Google Street View, or a named visitor's 360 panorama.")
    review = sub.add_parser('review', help='Revise a verdict without erasing its earlier judgment.')
    review.add_argument('case', type=Path)
    review.add_argument('--evidence', required=True)
    review.add_argument('--verdict', choices=VERDICTS, required=True)
    review.add_argument('--reason', required=True)
    mark = sub.add_parser('annotate', help='Number corresponding pixel regions in source and reference images.')
    mark.add_argument('case', type=Path)
    mark.add_argument('--evidence', required=True)
    mark.add_argument('--label', required=True)
    mark.add_argument('--source-box', type=box, required=True)
    mark.add_argument('--reference-box', type=box, required=True)
    unmark = sub.add_parser('unannotate', help='Remove a paired region while retaining its history.')
    unmark.add_argument('case', type=Path)
    unmark.add_argument('--evidence', required=True)
    unmark.add_argument('--annotation', required=True)
    unmark.add_argument('--reason', required=True)
    check = sub.add_parser('check', help='Check local asset paths, checksums and evidence references.')
    check.add_argument('case', type=Path)
    done = sub.add_parser("conclude", help="Assign a human-reviewed confidence; evidence requirements are enforced.")
    done.add_argument("case", type=Path)
    done.add_argument("--candidate", required=True)
    done.add_argument("--level", choices=LEVELS, required=True)
    done.add_argument("--note", required=True)
    show = sub.add_parser("status", help="Display the complete evidence record.")
    show.add_argument("case", type=Path)
    report = sub.add_parser("report", help="Generate a self-contained HTML or PDF comparison.")
    report.add_argument("case", type=Path)
    report.add_argument("--format", choices=("html", "pdf"), default="html")
    report.add_argument("--output", type=Path)
    report.add_argument("--font-path", type=Path, help="PDF: optional TrueType font containing the required CJK characters.")
    loc = sub.add_parser('map-location', help='Save manually checked candidate coordinates / Place ID / share URL.')
    loc.add_argument('case', type=Path)
    loc.add_argument('--candidate', required=True)
    for field in ('latitude', 'longitude', 'place-id', 'shared-url', 'notes'):
        loc.add_argument('--' + field)
    view = sub.add_parser('map-view', help='Attach a replayable inspected map view to existing evidence.')
    view.add_argument('case', type=Path)
    view.add_argument('--evidence', required=True)
    view.add_argument('--tool', choices=TOOLS, required=True)
    for field in ('original-url', 'latitude', 'longitude', 'pano', 'heading', 'pitch', 'fov', 'provider'):
        view.add_argument('--' + field)
    view.add_argument('--captured', default='unknown')
    view.add_argument('--availability', choices=('unreviewed', 'available', 'unavailable'), default='unreviewed')
    maps = sub.add_parser('map-links', help='Show candidate map links or export coordinate markers as KML for Earth.')
    maps.add_argument('case', type=Path)
    maps.add_argument('--kml', type=Path)
    parse = sub.add_parser('map-parse', help='Read explicit parameters from documented Google api=1 URLs; no network.')
    parse.add_argument('url')
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            result = init_case(args.photo, args.case)
        elif args.command == "ui":
            from .ui import serve
            serve(args.cases, args.port, not args.no_open, args.env_file)
            return 0
        elif args.command == "demo":
            from .demo import create_demo
            result = create_demo(args.case)
        elif args.command == "crop":
            result = crop(args.case, args.box, args.label, args.scale)
        elif args.command == "lens":
            if args.upload:
                result = run_lens(args.case, args.asset)
            else:
                _, path = selected_asset(args.case, args.asset)
                result = {"url": LENS_URL, "prepared_image": str(path),
                          "instruction": "Open Google, select Search by image and upload this copy. No upload performed. Use --upload for the optional visible-browser assistant."}
        elif args.command == 'map-location':
            result = save_location(args.case, args.candidate, {k: getattr(args, k) for k in ('latitude', 'longitude', 'place_id', 'shared_url', 'notes')})
        elif args.command == 'map-view':
            result = save_view(args.case, args.evidence, {k: getattr(args, k) for k in ('tool', 'availability', 'original_url', 'latitude', 'longitude', 'pano', 'heading', 'pitch', 'fov')}, args.captured, args.provider)
        elif args.command == 'map-parse':
            result = parse_google_url(args.url)
        elif args.command == 'map-links':
            data = load(args.case)
            if args.kml:
                from .report import prepare_output
                output = prepare_output(args.case, args.kml, 'kml')
                raw = export_kml(data)
                output.write_bytes(raw)
                result = {'kml': str(output)}
            else:
                result = {'candidates': {c['id']: candidate_links(c) for c in data['candidates']}, 'shortlist_url': shortlist_url(data)}
        elif args.command == "candidate":
            result = candidate(args.case, args.name, args.address, args.url)
        elif args.command == "evidence":
            result = add_evidence(args.case, args.candidate, args.kind, args.url, args.verdict, args.notes, args.image, args.captured, args.provider)
        elif args.command == 'review':
            result = review_evidence(args.case, args.evidence, args.verdict, args.reason)
        elif args.command == 'annotate':
            result = add_annotation(args.case, args.evidence, args.label, args.source_box, args.reference_box)
        elif args.command == 'unannotate':
            result = remove_annotation(args.case, args.evidence, args.annotation, args.reason)
        elif args.command == 'check':
            result = check_case(args.case)
        elif args.command == "conclude":
            result = conclude(args.case, args.candidate, args.level, args.note)
        elif args.command == "status":
            result = load(args.case)
        else:
            result = render_pdf(args.case, args.output, args.font_path) if args.format == "pdf" else render_html(args.case, args.output)
        print(json.dumps(result, ensure_ascii=not sys.stdout.isatty(), indent=2, default=str))
        return 1 if args.command == 'check' and not result['ok'] else 0
    except (ValueError, OSError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
