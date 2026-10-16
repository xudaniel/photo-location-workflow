"""Persistent local investigation jobs; external hypotheses never mutate cases."""

from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import threading
from uuid import uuid4

from . import geosleuth as bridge
from .core import hash_file, now, selected_asset
from .tasks import TaskStopped, atomic_json, workspace_lock

ACTIVE = {'queued', 'preparing', 'processing', 'reviewing', 'cancelling'}
RETRYABLE = {'failed', 'interrupted', 'cancelled', 'partial'}


class GeoJobs:
    def __init__(self, root, lock=None, executor=None, config=None):
        self.root = Path(root).resolve() / '.geo-sleuth'
        self.lock = lock or threading.RLock()
        self.executor = executor or ThreadPoolExecutor(max_workers=2, thread_name_prefix='photo-local')
        self.owns_executor = executor is None
        self.config = config or {}
        self.jobs = {}
        self.closed = False

    def configuration(self):
        skill = Path(self.config.get('skill_dir') or os.environ.get('GEO_SLEUTH_DIR') or
                     Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'skills/geo-sleuth').resolve()
        uv = self.config.get('uv') or os.environ.get('GEO_SLEUTH_UV') or shutil.which('uv')
        if not uv:
            sibling = Path(sys.executable).with_name('uv.exe' if os.name == 'nt' else 'uv')
            uv = str(sibling) if sibling.is_file() else None
        if not uv:
            return {'configured': False, 'error': 'Install uv or configure GEO_SLEUTH_UV on the server.'}
        try:
            bridge._scripts(skill)
        except (ValueError, OSError):
            return {'configured': False, 'error': 'Install the complete geo-sleuth skill or configure GEO_SLEUTH_DIR.'}
        return {'configured': True, 'skill_dir': str(skill), 'uv': str(uv)}

    def _folder(self, case, run_id):
        if not re.fullmatch(r'g[0-9a-f]{12}', str(run_id)):
            raise ValueError('Invalid local investigation run.')
        root = self.root / Path(case).name
        path = bridge._inside(root, run_id)
        return path

    def _job(self, case, run_id):
        folder = self._folder(case, run_id)
        return folder, bridge._read(bridge._inside(folder, 'job.json'))

    def _save(self, folder, job, **changes):
        job.update(changes, updated_at=now())
        atomic_json(folder / 'job.json', job)

    def _public(self, folder, job):
        value = dict(job)
        value['log'] = ''
        value['can_cancel'] = any(key[1] == job['id'] for key in self.jobs)
        manifest_path = folder / 'work/bridge.json'
        if manifest_path.is_file():
            manifest = bridge._read(bridge._inside(folder, 'work/bridge.json'))
            entries = manifest.get('commands', [])
            value['commands'] = [{k: e.get(k) for k in ('script', 'status', 'started_at', 'finished_at')}
                                 for e in entries[-20:]]
            if entries and entries[-1].get('log'):
                log_path = bridge._inside(folder / 'work', entries[-1]['log'])
                if log_path.is_file():
                    with log_path.open('rb') as stream:
                        stream.seek(max(0, log_path.stat().st_size - 12_000))
                        value['log'] = stream.read(12_000).decode('utf-8', errors='replace')
        value['previews'] = self._previews(folder)
        return value

    def snapshot(self, case):
        with self.lock:
            runs = []
            parent = self.root / Path(case).name
            for path in sorted(parent.glob('g*/job.json')) if parent.exists() else []:
                if path.resolve().parent.parent != parent.resolve():
                    continue
                job = bridge._read(path)
                key = (str(Path(case).resolve()), job['id'])
                if job['status'] in ACTIVE and key not in self.jobs:
                    try:
                        with workspace_lock(path.parent):
                            self._save(path.parent, job, status='interrupted', error='Server stopped. Resume saved steps.')
                    except ValueError:
                        pass  # Another server still owns this run.
                runs.append(self._public(path.parent, job))
            config = self.configuration()
            return {'configured': config['configured'], 'error': config.get('error'),
                    'runs': sorted(runs, key=lambda r: r['created_at'])}

    def start(self, case, body):
        with self.lock:
            if self.closed:
                raise ValueError('Server is shutting down.')
            case = Path(case).resolve()
            self.snapshot(case)
            if any(k[0] == str(case) for k in self.jobs):
                raise ValueError('A local investigation is already running for this case.')
            if len(self.jobs) >= 2:
                raise ValueError('Two local investigations are running; wait for one to finish.')
            config = self.configuration()
            if not config['configured']:
                raise ValueError(config['error'])
            if body.get('resume'):
                folder, job = self._job(case, body['resume'])
                if job['status'] not in RETRYABLE:
                    raise ValueError('Only a stopped or partial run can resume.')
                if job['asset_sha256'] != hash_file(selected_asset(case, job['asset'])[1]):
                    raise ValueError('Input image changed; start a new investigation.')
            elif body.get('operation'):
                folder, job = self._job(case, body.get('run'))
                if job['status'] not in {'completed', 'partial'}:
                    raise ValueError('Wait for results before editing the candidate board.')
                operation = body['operation']
                if not isinstance(operation, dict) or operation.get('kind') not in {'clue', 'falsify'}:
                    raise ValueError('Choose an observation or a falsification test.')
                text = operation.get('text')
                if not isinstance(text, str) or not text.strip() or len(text) > 2000:
                    raise ValueError('Write 1–2000 characters.')
                job['operation'] = {**operation, 'id': uuid4().hex}
            else:
                if type(body.get('ocr', False)) is not bool:
                    raise ValueError('OCR must be enabled explicitly.')
                asset, image = selected_asset(case, body.get('asset'))
                run_id = 'g' + uuid4().hex[:12]
                folder = self._folder(case, run_id)
                folder.mkdir(parents=True, exist_ok=False)
                job = {'schema_version': 1, 'id': run_id, 'created_at': datetime.now(timezone.utc).isoformat(),
                       'asset': asset, 'asset_sha256': hash_file(image), 'ocr': body.get('ocr', False),
                       'result': None, 'reviews': {}, 'operation': None, 'checkpoints': {}}
            self._save(folder, job, status='queued', error=None)
            cancel = threading.Event()
            key = (str(case), job['id'])
            self.jobs[key] = {'cancel': cancel, 'future': None}
            self.jobs[key]['future'] = self.executor.submit(self._work, case, job['id'], config, cancel)
            return self.snapshot(case)

    def _work(self, case, run_id, config, cancel):
        key = (str(case), run_id)
        folder, job = self._job(case, run_id)
        workspace = folder / 'work'
        try:
            with workspace_lock(folder):
                def stage(name):
                    if cancel.is_set():
                        raise TaskStopped('cancelled')
                    with self.lock:
                        self._save(folder, job, status=name)
                stage('preparing')
                bridge.prepare(case, workspace, config['skill_dir'], config['uv'], job['asset'], resume=True, cancel=cancel)
                job['checkpoints']['prepare'] = True
                if not job.get('operation'):
                    stage('processing')
                    result = bridge.intake(case, workspace, job['ocr'], reuse=True, cancel=cancel)
                    job['checkpoints']['intake'] = result['result']
                else:
                    stage('reviewing')
                    bridge.update_board(case, workspace, job['operation'], cancel=cancel)
                stage('reviewing')
                result = bridge.review(case, workspace, cancel=cancel)
                with self.lock:
                    # Preserve marks saved while this worker was running.
                    job['reviews'] = self._job(case, run_id)[1].get('reviews', {})
                    self._save(folder, job, result=result, operation=None,
                               result_token=hashlib.sha256(json.dumps({k:v for k,v in result.items() if k != "created_at"}, sort_keys=True).encode()).hexdigest(),
                               status='partial' if job['checkpoints'].get('intake') == 'partial' else 'completed')
        except Exception as exc:
            with self.lock:
                status = 'cancelled' if isinstance(exc, TaskStopped) and exc.reason == 'cancelled' else 'failed'
                message = str(exc) if isinstance(exc, ValueError) else 'Local tool failed; inspect the saved log and resume.'
                self._save(folder, job, status=status, error=message)
        finally:
            with self.lock:
                self.jobs.pop(key, None)

    def cancel(self, case, run_id):
        with self.lock:
            folder, job = self._job(case, run_id)
            active = self.jobs.get((str(Path(case).resolve()), run_id))
            if not active:
                raise ValueError('This run is not active in this server.')
            active['cancel'].set()
            if active['future'] and active['future'].cancel():
                self.jobs.pop((str(Path(case).resolve()), run_id), None)
                self._save(folder, job, status='cancelled')
            else:
                self._save(folder, job, status='cancelling')
            return self.snapshot(case)

    def mark(self, case, run_id, key, verdict, note):
        with self.lock:
            folder, job = self._job(case, run_id)
            if job['status'] in ACTIVE:
                raise ValueError('Wait for the run to finish before reviewing clues.')
            if verdict not in {'reviewed', 'unclear', 'rejected'} or not isinstance(note, str) or not note.strip() or len(note) > 2000:
                raise ValueError('Choose a review status and write a note (1–2000 characters).')
            result = job.get('result') or {}
            allowed = {'ocr:' + str(i) for i, _ in enumerate(result.get('ocr_hypotheses', []))}
            allowed.update('candidate:' + c['name'] for rows in result.get('board', {}).get('candidate_levels', {}).values() for c in rows)
            if key not in allowed:
                raise ValueError('Review item does not belong to this run.')
            history = job.setdefault('reviews', {}).setdefault(key, [])
            history.append({'verdict': verdict, 'note': note, 'at': now(), 'context': job.get('result_token')})
            self._save(folder, job)
            return self.snapshot(case)

    def _previews(self, folder):
        root = bridge._inside(folder, 'work')
        paths = []
        if not root.exists():
            return paths
        manifest_path = bridge._inside(root, 'bridge.json')
        if not manifest_path.is_file():
            return paths
        manifest = bridge._read(manifest_path)
        attempt = manifest.get('intake')
        for entry in reversed(manifest.get('commands', [])):
            args = entry.get('arguments', [])
            if entry.get('script') == 'intake.py' and '--out-dir' in args:
                attempt = args[args.index('--out-dir') + 1]
                break
        if not attempt:
            return paths
        output = bridge._inside(root, attempt)
        for path in sorted(output.glob('*/*')):
            if path.suffix.lower() in {'.jpg', '.jpeg', '.png'} and path.parent.name in {'edges', 'variants'}:
                if path.resolve().is_relative_to(root) and path.stat().st_size <= 8_000_000:
                    paths.append(path.relative_to(root).as_posix())
        return paths[-48:]

    def image(self, case, run_id, relative):
        folder, _ = self._job(case, run_id)
        if relative not in self._previews(folder):
            raise ValueError('Image is not a generated preview in this run.')
        path = bridge._inside(folder / 'work', relative)
        return path.read_bytes(), 'image/png' if path.suffix.lower() == '.png' else 'image/jpeg'

    def close(self):
        with self.lock:
            self.closed = True
            futures = []
            for (case, run_id), value in list(self.jobs.items()):
                value['cancel'].set()
                future = value['future']
                if future and future.cancel():
                    folder, job = self._job(case, run_id)
                    self._save(folder, job, status='cancelled', error='Server stopped before this task started.')
                    self.jobs.pop((case, run_id), None)
                elif future:
                    futures.append(future)
        wait(futures, timeout=5)
        if self.owns_executor:
            self.executor.shutdown(wait=False, cancel_futures=True)
