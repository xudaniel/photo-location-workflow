"""Loopback-only workbench, using the same case store and validation as the CLI."""

import base64
import binascii
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
from pathlib import Path
import re
import secrets
import tempfile
import threading
from urllib.parse import parse_qs, unquote, urlsplit
import uuid
import webbrowser

from . import __version__
from .annotations import add_annotation, remove_annotation
from .core import add_evidence, asset_path, candidate, check_case, conclude, crop, init_case, load, review_evidence, save
from .demo import create_demo
from .maps import candidate_links, export_kml, parse_google_url, save_location, save_view, shortlist_url
from .report import render_html, render_pdf
from .research import OpenAIResearch, ResearchManager, settings

MAX_BODY = 48 * 1024 * 1024


def create_server(cases_root, port=0, research_client=None):
    root = Path(cases_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    lock = threading.RLock()
    research = ResearchManager(research_client, lock)
    static = files('photo_location_workflow').joinpath('static')

    class Handler(BaseHTTPRequestHandler):
        server_version = 'PhotoLocationLocal'

        def log_message(self, *args):
            pass  # Avoid storing request content or private image names in access logs.

        def _send(self, value, mime='application/json', status=200, filename=None):
            if mime == 'application/json':
                value = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime + ('; charset=utf-8' if mime.startswith('text/') else ''))
            self.send_header('Content-Length', str(len(value)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            if filename:
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(value)

        def _host_ok(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def _authorized(self):
            expected_origin = f'http://127.0.0.1:{self.server.server_port}'
            origin = self.headers.get('Origin')
            return self._host_ok() and (origin is None or origin == expected_origin) and hmac.compare_digest(
                self.headers.get('X-Local-Token', ''), token)

        def _case(self, name):
            if not re.fullmatch(r'[\w-]{1,80}', name):
                raise ValueError('Invalid case name.')
            path = (root / name).resolve()
            if path.parent != root or not (path / 'case.json').is_file():
                raise ValueError('Case not found.')
            return path

        def _state(self, path):
            data = load(path)
            try:
                shortlist = shortlist_url(data)
            except ValueError:
                shortlist = None
            return {'id': path.name, 'data': data, 'integrity': check_case(path),
                    'maps': {'candidates': {c['id']: candidate_links(c) for c in data['candidates']}, 'shortlist_url': shortlist}}

        def do_GET(self):
            if not self._host_ok():
                return self._send({'error': 'Unexpected host.'}, status=403)
            parsed = urlsplit(self.path)
            if parsed.path in ('/', '/app.js', '/comparison.js', '/research.js', '/maps.js', '/style.css'):
                name = {'/': 'index.html', '/app.js': 'app.js', '/comparison.js': 'comparison.js', '/research.js': 'research.js', '/maps.js': 'maps.js', '/style.css': 'style.css'}[parsed.path]
                value = static.joinpath(name).read_bytes()
                if name == 'index.html':
                    value = value.replace(b'__LOCAL_TOKEN__', token.encode())
                return self._send(value, {'index.html': 'text/html', 'app.js': 'text/javascript', 'comparison.js': 'text/javascript', 'research.js': 'text/javascript', 'maps.js': 'text/javascript', 'style.css': 'text/css'}[name])
            if not self._authorized():
                return self._send({'error': 'Local session authorization required.'}, status=403)
            try:
                with lock:
                    if parsed.path == '/api/cases':
                        items = []
                        for folder in root.iterdir():
                            if folder.is_dir() and (folder / 'case.json').is_file() and folder.resolve().parent == root:
                                try:
                                    data = load(folder)
                                    items.append({'id': folder.name, 'title': data.get('title', folder.name), 'updated_at': data['updated_at'], 'level': data['conclusion']['level']})
                                except (ValueError, OSError, KeyError):
                                    continue
                        return self._send({'cases': sorted(items, key=lambda c: c['updated_at'], reverse=True), 'version': __version__})
                    if parsed.path == '/api/research':
                        return self._send({'configured': research.client.configured, 'model': research.client.model})
                    match = re.fullmatch(r'/api/cases/([^/]+)(?:/(asset|report|research|kml))?', parsed.path)
                    if not match:
                        return self._send({'error': 'Not found.'}, status=404)
                    path = self._case(unquote(match[1]))
                    if match[2] == 'kml':
                        return self._send(export_kml(load(path)), 'application/vnd.google-earth.kml+xml', filename='candidate-places.kml')
                    if match[2] == 'research':
                        return self._send(research.snapshot(path))
                    if match[2] == 'asset':
                        relative = parse_qs(parsed.query).get('path', [''])[0]
                        data = load(path)
                        allowed = {data['source']['asset']}
                        allowed.update(c[k] for c in data['crops'] for k in ('native', 'zoom'))
                        allowed.update(e['asset'] for e in data['evidence'] if e.get('asset'))
                        allowed.update(s['screenshot'] for s in data['searches'] if s.get('screenshot'))
                        if relative not in allowed:
                            raise ValueError('Image is not part of this investigation.')
                        return self._send(asset_path(path, relative).read_bytes(), 'image/png')
                    if match[2] == 'report':
                        format_ = parse_qs(parsed.query).get('format', ['html'])[0]
                        if format_ not in ('html', 'pdf'):
                            raise ValueError('Choose HTML or PDF.')
                        result = render_pdf(path) if format_ == 'pdf' else render_html(path)
                        return self._send(result.read_bytes(), 'application/pdf' if format_ == 'pdf' else 'text/html', filename=f'photo-location-report.{format_}')
                    return self._send(self._state(path))
            except (ValueError, OSError, KeyError, TypeError) as exc:
                return self._send({'error': str(exc)}, status=400)

        def _upload(self, value, directory):
            if not isinstance(value, str):
                raise ValueError('Choose a local image first.')
            try:
                raw = base64.b64decode(value, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise ValueError('The image upload could not be read.') from exc
            if not raw or len(raw) > 32 * 1024 * 1024:
                raise ValueError('Choose an image smaller than 32 MB.')
            path = Path(directory) / 'image'
            path.write_bytes(raw)
            return path

        def do_POST(self):
            if not self._authorized():
                return self._send({'error': 'Local session authorization required.'}, status=403)
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length <= 0 or length > MAX_BODY:
                    return self._send({'error': 'Request is empty or too large.'}, status=413)
                if self.headers.get_content_type() != 'application/json':
                    return self._send({'error': 'JSON request required.'}, status=415)
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError('Expected an object.')
                route = urlsplit(self.path).path
                with lock, tempfile.TemporaryDirectory() as temporary:
                    if route in ('/api/cases', '/api/demo'):
                        path = root / ('demo-' if route.endswith('demo') else 'photo-')
                        path = root / (path.name + uuid.uuid4().hex[:12])
                        if route.endswith('demo'):
                            create_demo(path)
                        else:
                            init_case(self._upload(body.get('image'), temporary), path)
                            data = load(path)
                            data['title'] = str(body.get('title', 'Untitled photo'))[:100]
                            save(path, data)
                        return self._send(self._state(path), status=201)
                    if route == '/api/maps/parse':
                        return self._send(parse_google_url(body['url']))
                    match = re.fullmatch(r'/api/cases/([^/]+)/(crop|candidate|evidence|review|conclude|annotate|unannotate|research|progress|adopt|map-location|map-view)', route)
                    if not match:
                        return self._send({'error': 'Not found.'}, status=404)
                    path = self._case(unquote(match[1]))
                    if match[2] == 'research':
                        return self._send(research.start(path, body.get('assets'), body.get('language', 'en'), body.get('consent'), body.get('resume')), status=202)
                    elif match[2] == 'progress':
                        return self._send(research.progress(path, body.get('notes'), body.get('resolved')))
                    elif match[2] == 'adopt':
                        research.adopt(path, body.get('run'), body.get('index'))
                    elif match[2] == 'crop':
                        box = body['box']
                        if not isinstance(box, list) or len(box) != 4 or any(type(v) is not int for v in box):
                            raise ValueError('Select a rectangular detail in the photo.')
                        crop(path, box, body['label'], int(body.get('scale', 4)))
                    elif match[2] == 'map-location':
                        save_location(path, body['candidate'], body['location'])
                    elif match[2] == 'map-view':
                        save_view(path, body['evidence'], body['view'], body.get('captured'), body.get('provider'))
                    elif match[2] == 'candidate':
                        candidate(path, body['name'], body['address'], body['url'])
                    elif match[2] == 'evidence':
                        photo = self._upload(body['image'], temporary) if body.get('image') else None
                        add_evidence(path, body['candidate'], body['kind'], body['url'], body['verdict'], body['notes'], photo, body.get('captured') or None, body.get('provider'), body.get('map_view'))
                    elif match[2] == 'review':
                        review_evidence(path, body['evidence'], body['verdict'], body['reason'])
                    elif match[2] == 'annotate':
                        add_annotation(path, body['evidence'], body['label'], body['source_box'], body['reference_box'])
                    elif match[2] == 'unannotate':
                        remove_annotation(path, body['evidence'], body['annotation'], body['reason'])
                    else:
                        conclude(path, body['candidate'], body['level'], body['note'])
                    return self._send(self._state(path))
            except (ValueError, OSError, KeyError, TypeError) as exc:
                return self._send({'error': str(exc)}, status=400)

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    original_close = server.server_close
    def close():
        research.close()
        original_close()
    server.server_close = close
    return server, token


def serve(cases_root, port=8765, open_browser=True, env_file=None):
    server, _ = create_server(cases_root, port, OpenAIResearch(*settings(env_file)))
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'Photo Location Workbench {__version__}: {url}\nLocal files: {Path(cases_root).resolve()}\nPress Ctrl-C to stop.')
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
