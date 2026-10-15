import base64
import io
import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from PIL import Image
import pytest

from photo_location_workflow.ui import create_server


@pytest.fixture
def workbench(tmp_path):
    server, token = create_server(tmp_path / 'cases')
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'

    def request(path, body=None, authorized=True, request_origin=None):
        headers = {'X-Local-Token': token} if authorized else {}
        if request_origin:
            headers['Origin'] = request_origin
        if body is not None:
            headers['Content-Type'] = 'application/json'
        req = Request(origin + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        with urlopen(req, timeout=10) as response:
            value = response.read()
            return json.loads(value) if response.headers.get_content_type() == 'application/json' else value

    yield request, token
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


@pytest.fixture
def image_data():
    output = io.BytesIO()
    Image.new('RGB', (120, 90), 'green').save(output, format='PNG')
    return base64.b64encode(output.getvalue()).decode()


def test_local_session_and_static_assets(workbench):
    request, token = workbench
    page = request('/')
    assert token.encode() in page and b'__LOCAL_TOKEN__' not in page
    assert b'crop-canvas' in page
    assert b'pointerdown' in request('/app.js')
    assert b'@media' in request('/style.css')
    with pytest.raises(HTTPError) as error:
        request('/api/cases', authorized=False)
    assert error.value.code == 403
    with pytest.raises(HTTPError) as error:
        request('/api/demo', {}, request_origin='https://example.org')
    assert error.value.code == 403


def test_photo_to_comparison_export(workbench, image_data):
    request, _ = workbench
    state = request('/api/cases', {'title': '测试照片', 'image': image_data})
    case = '/api/cases/' + state['id']
    assert state['data']['source']['size'] == [120, 90]
    assert request('/api/cases')['cases'][0]['title'] == '测试照片'
    state = request(case + '/crop', {'box': [10, 10, 20, 20], 'label': 'window', 'scale': 2})
    assert request(case + '/asset?path=' + state['data']['crops'][0]['native']).startswith(b'\x89PNG')
    request(case + '/candidate', {'name': 'Example building', 'address': 'Example address', 'url': 'https://example.org/'})
    state = request(case + '/evidence', {'candidate': 'c1', 'kind': 'reference', 'url': 'https://example.org/', 'verdict': 'match', 'notes': 'Same window shape', 'image': image_data})
    assert state['integrity']['ok']
    state = request(case + '/review', {'evidence': 'e1', 'verdict': 'unclear', 'reason': 'Reconsidered shape'})
    assert len(state['data']['evidence'][0]['reviews']) == 1
    state = request(case + '/conclude', {'candidate': 'c1', 'level': 'candidate', 'note': 'Needs independent verification'})
    assert state['data']['conclusion']['level'] == 'candidate'
    report = request(case + '/report?format=html')
    assert b'Example building' in report and b'data:image/png;base64' in report


def test_demo_does_not_claim_verification(workbench):
    request, _ = workbench
    state = request('/api/demo', {})
    assert state['data']['conclusion']['level'] == 'candidate'
    assert state['integrity']['ok']
    assert state['data']['candidates'][0]['source_url'] == 'https://example.org/'


def test_invalid_inputs_and_asset_access(workbench, image_data):
    request, _ = workbench
    with pytest.raises(HTTPError):
        request('/api/cases', {'image': 'invalid base64!'})
    state = request('/api/cases', {'image': image_data})
    case = '/api/cases/' + state['id']
    for route, body in [
        ('/asset?path=case.json', None),
        ('/crop', {'box': [0, 0, 9999, 99], 'label': 'bad'}),
        ('/crop', {'box': ['0', 0, 5, 5], 'label': 'bad'}),
        ('/report?format=xml', None),
        ('/conclude', {'candidate': 'c1', 'level': 'confirmed', 'note': 'No evidence'}),
    ]:
        with pytest.raises(HTTPError):
            request(case + route, body)


def test_paired_regions_round_trip_through_http(workbench, image_data):
    request, _ = workbench
    state = request('/api/cases', {'image': image_data})
    case = '/api/cases/' + state['id']
    request(case + '/candidate', {'name': 'Synthetic', 'address': 'None', 'url': 'https://example.org/'})
    request(case + '/evidence', {'candidate': 'c1', 'kind': 'reference', 'url': 'https://example.org/', 'verdict': 'match', 'notes': 'Synthetic', 'image': image_data})
    assert b'ComparisonWorkbench' in request('/comparison.js')
    state = request(case + '/annotate', {'evidence': 'e1', 'label': 'Window', 'source_box': [10, 10, 20, 20], 'reference_box': [30, 20, 40, 40]})
    assert state['integrity']['ok']
    assert request(case)['data']['evidence'][0]['annotations'][0]['label'] == 'Window'
    assert b'id="e1-a1"' in request(case + '/report?format=html')
    with pytest.raises(HTTPError):
        request(case + '/annotate', {'evidence': 'e1', 'label': 'Invalid', 'source_box': [0, 0, 1000, 1000], 'reference_box': [0, 0, 1, 1]})
    state = request(case + '/unannotate', {'evidence': 'e1', 'annotation': 'a1', 'reason': 'Wrong detail'})
    assert not state['data']['evidence'][0]['annotations']
    assert state['data']['evidence'][0]['annotation_history'][0]['reason'] == 'Wrong detail'
