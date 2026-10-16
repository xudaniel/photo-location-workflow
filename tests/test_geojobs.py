import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from PIL import Image
import pytest

from photo_location_workflow import geosleuth
from photo_location_workflow.core import candidate, init_case
from photo_location_workflow.geojobs import GeoJobs
from photo_location_workflow.tasks import TaskStopped
from photo_location_workflow.ui import create_server


@pytest.fixture
def local_tools(tmp_path, monkeypatch):
    skill = tmp_path / 'skill'
    (skill / 'scripts').mkdir(parents=True)
    for name in ('board.py', 'intake.py', '_net.py', 'regions.py'):
        (skill / 'scripts' / name).write_text('# tool fixture', encoding='utf-8')
    state = {'calls': [], 'fail_report': False, 'block': False, 'intake': 'ok'}

    def execute(command, **options):
        script, args = Path(command[2]).name, command[3:]
        state['calls'].append((script, args))
        root = Path(options['cwd'])
        log = Path(options['log_path'])
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text('Live tool output', encoding='utf-8')
        path = root / 'board.json'
        if script == 'intake.py':
            if state['block']:
                options['cancel'].wait(8)
                if options['cancel'].is_set():
                    raise TaskStopped('cancelled')
            output = root / args[args.index('--out-dir')+1]
            (output / 'edges').mkdir(parents=True)
            Image.new('RGB', (12, 10), 'green').save(output / 'edges/top.jpg')
            (output / 'intake.json').write_text(json.dumps({'result': state['intake'], 'status': {'edges': 'ok'},
                 'ocr': [{'text': '<unreadable>', 'pass': 'up', 'box': [0, 0, 2, 2]}]}), encoding='utf-8')
        elif args[0] == 'init':
            path.write_text(json.dumps({'photo':'input.png','candidates':{},'clues':{},'falsify':{}}), encoding='utf-8')
        else:
            board = json.loads(path.read_text(encoding='utf-8'))
            if args[0] == 'add':
                for name in args[args.index('--')+1:]:
                    board['candidates'][name] = {'level':'area'}
            elif args[0] == 'clue':
                board['clues']['K'+str(len(board['clues'])+1)] = {'text':args[-1], 'source':args[args.index('--source')+1]}
            elif args[0] == 'falsify':
                board['falsify'].setdefault(args[-1], []).append(args[args.index('--text')+1])
            elif args[0] == 'report':
                if state['fail_report']:
                    return SimpleNamespace(returncode=3, stdout='report failed')
                report = {'candidate_levels':{'area':[{'name':name,'share':1.0} for name in board['candidates']]},
                          'falsify':board['falsify'], 'unused_clues':[c['text'] for c in board['clues'].values()]}
                (root / args[-1]).write_text(json.dumps({'board':report}), encoding='utf-8')
            path.write_text(json.dumps(board), encoding='utf-8')
        return SimpleNamespace(returncode=0, stdout='tool completed')

    monkeypatch.setattr(geosleuth, 'run_process', execute)
    config = {'skill_dir':skill,'uv':sys.executable}
    cases = tmp_path / 'cases'
    source = tmp_path / 'source.png'
    Image.new('RGB', (40, 30)).save(source)
    case = cases / 'demo'
    init_case(source, case)
    candidate(case, 'Candidate A', 'Unverified address', 'https://example.org/')
    return cases, case, config, state


def completed(manager, case, status='completed'):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        value = manager.snapshot(case)
        if value['runs'][-1]['status'] == status and not manager.jobs:
            return value['runs'][-1]
        time.sleep(.02)
    raise AssertionError(value)


def test_resume_reuses_successful_intake_and_marks_do_not_change_case(local_tools):
    cases, case, config, state = local_tools
    manager = GeoJobs(cases, config=config)
    before = (case / 'case.json').read_bytes()
    try:
        state['fail_report'] = True
        manager.start(case, {})
        failed = completed(manager, case, 'failed')
        assert failed['checkpoints']['intake'] == 'ok'
        state['fail_report'] = False
        manager.start(case, {'resume':failed['id']})
        run = completed(manager, case)
        assert len([s for s,a in state['calls'] if s == 'intake.py']) == 1
        manager.mark(case, run['id'], 'ocr:0', 'unclear', 'Native pixels do not support reading this plate.')
        saved = manager.snapshot(case)['runs'][-1]
        assert saved['reviews']['ocr:0'][0]['context'] == run['result_token']
        assert saved['log'] == 'Live tool output'
        assert saved['previews']
        assert (case / 'case.json').read_bytes() == before
    finally:
        manager.close()


def test_cancel_duplicate_start_restart_and_changed_inputs(local_tools):
    cases, case, config, state = local_tools
    manager = GeoJobs(cases, config=config)
    try:
        state['block'] = True
        run = manager.start(case, {})['runs'][-1]
        with pytest.raises(ValueError, match='already running'):
            manager.start(case, {})
        manager.cancel(case, run['id'])
        completed(manager, case, 'cancelled')
        state['block'] = False
        manager.start(case, {'resume':run['id']})
        done = completed(manager, case)
        folder, job = manager._job(case, done['id'])
        job['status'] = 'processing'
        manager._save(folder, job)
        assert manager.snapshot(case)['runs'][-1]['status'] == 'interrupted'
        (case / 'assets/source.png').write_bytes(b'changed')
        with pytest.raises(ValueError, match='changed'):
            manager.start(case, {'resume':run['id']})
    finally:
        manager.close()


def test_board_updates_are_idempotent_and_invalidate_old_review_context(local_tools):
    cases, case, config, state = local_tools
    manager = GeoJobs(cases, config=config)
    try:
        run = manager.start(case, {})['runs'][-1]
        done = completed(manager, case)
        manager.mark(case, run['id'], 'candidate:Candidate A', 'reviewed', 'Reviewed as a hypothesis only.')
        operation = {'kind':'falsify','candidate':'Candidate A','text':'Reject if the facade differs.'}
        manager.start(case, {'run':run['id'], 'operation':operation})
        changed = completed(manager, case)
        assert changed['result']['board']['falsify']['Candidate A'] == [operation['text']]
        assert changed['result_token'] != done['result_token']
        assert changed['reviews']['candidate:Candidate A'][0]['context'] != changed['result_token']
        # A retry after an interrupted command must not append the same test twice.
        geosleuth.update_board(case, manager._folder(case, run['id'])/'work', {**operation,'id':'retry'})
        manager.start(case, {'run':run['id'], 'operation':{'kind':'clue','text':'Three visible window bays.'}})
        updated = completed(manager, case)
        assert updated['result']['board']['unused_clues'] == ['Three visible window bays.']
        board = json.loads((manager._folder(case,run['id'])/'work/board.json').read_text())
        assert board['falsify']['Candidate A'] == [operation['text']]
    finally:
        manager.close()


def test_http_jobs_previews_authorization_and_review_survive_restart(local_tools):
    cases, case, config, state = local_tools
    before = (case / 'case.json').read_bytes()
    server, token = create_server(cases, geo_config=config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(path, body=None, authorized=True):
        headers = {'X-Local-Token':token} if authorized else {}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        req = Request(f'http://127.0.0.1:{server.server_port}'+path,
                      data=json.dumps(body).encode() if body is not None else None, headers=headers)
        with urlopen(req, timeout=8) as response:
            return json.load(response) if response.headers.get_content_type() == 'application/json' else response.read()

    try:
        assert b'GeoWorkbench' in request('/geosleuth.js')
        with pytest.raises(HTTPError) as error:
            request('/api/cases/demo/geo', authorized=False)
        assert error.value.code == 403
        result = request('/api/cases/demo/geo', {'ocr':False})
        run_id = result['runs'][-1]['id']
        deadline = time.monotonic()+8
        while time.monotonic()<deadline:
            run = request('/api/cases/demo/geo')['runs'][-1]
            if run['status']=='completed': break
            time.sleep(.02)
        assert run['status']=='completed'
        raw = request('/api/cases/demo/geo-image?run='+run_id+'&path='+run['previews'][0])
        assert raw.startswith(b'\xff\xd8')
        with pytest.raises(HTTPError):
            request('/api/cases/demo/geo-image?run='+run_id+'&path=../../case.json')
        request('/api/cases/demo/geo', {'action':'mark','run':run_id,'key':'ocr:0','verdict':'unclear','note':'Cannot read the original.'})
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
    manager = GeoJobs(cases, config=config)
    try:
        assert manager.snapshot(case)['runs'][-1]['reviews']['ocr:0'][0]['verdict']=='unclear'
        assert (case/'case.json').read_bytes()==before
    finally:
        manager.close()


def test_missing_preview_rebuilds_intake_and_shows_only_current_attempt(local_tools):
    cases, case, config, state = local_tools
    manager = GeoJobs(cases, config=config)
    try:
        run_id = manager.start(case, {})['runs'][-1]['id']
        run = completed(manager, case)
        workspace = manager._folder(case, run_id)/'work'
        (workspace/run['previews'][0]).unlink()
        geosleuth.intake(case, workspace, reuse=True)
        current = manager.snapshot(case)['runs'][-1]
        assert len(current['previews']) == 1
        assert current['previews'] != run['previews']
        assert len([s for s,a in state['calls'] if s == 'intake.py']) == 2
    finally:
        manager.close()


def test_queued_cancellation_never_executes_a_tool(local_tools):
    from concurrent.futures import ThreadPoolExecutor
    cases, case, config, state = local_tools
    pool = ThreadPoolExecutor(max_workers=1)
    gate = threading.Event()
    occupying = pool.submit(gate.wait)
    manager = GeoJobs(cases, executor=pool, config=config)
    try:
        run_id = manager.start(case, {})['runs'][-1]['id']
        assert manager.cancel(case, run_id)['runs'][-1]['status'] == 'cancelled'
        assert not state['calls']
    finally:
        gate.set(); occupying.result(timeout=5)
        manager.close(); pool.shutdown(wait=True)
