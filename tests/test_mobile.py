import base64
from http.cookiejar import CookieJar
import io
import json
import threading
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from PIL import Image
import pytest

from photo_location_workflow import ui
from photo_location_workflow.core import init_case, load
from photo_location_workflow.mobile import Pairing, PairingThrottled, lan_address, session_cookie


@pytest.mark.parametrize('address', ['127.0.0.1', '0.0.0.0', '8.8.8.8', '::1', 'example.org', '169.254.1.2'])
def test_lan_is_explicit_and_private(address):
    with pytest.raises(ValueError):
        lan_address(address)
    assert lan_address('192.168.3.20') == '192.168.3.20'
    assert lan_address('10.0.0.2') == '10.0.0.2'


def test_pairing_roles_expiry_revoke_and_rate_limit():
    clock = [0]
    pair = Pairing(clock=lambda: clock[0])
    admin = pair.exchange({'admin':pair.admin_secret}, 'desktop')
    phone = pair.exchange({'code':pair.code}, 'phone')
    assert pair.role(session_cookie(admin, 1), 1) == 'admin'
    assert pair.role(session_cookie(phone, 1), 1) == 'phone'
    assert pair.role(session_cookie(phone, 2), 1) is None
    old_code = pair.code
    pair.revoke_phones()
    assert pair.role(session_cookie(phone, 1), 1) is None
    assert pair.role(session_cookie(admin, 1), 1) == 'admin'
    with pytest.raises(ValueError):
        pair.exchange({'code':old_code}, 'phone')
    for _ in range(9):
        with pytest.raises(ValueError):
            pair.exchange({'code':'wrong'}, 'phone')
    with pytest.raises(PairingThrottled):
        pair.exchange({'code':pair.code}, 'phone')
    clock[0] = 301
    assert pair.exchange({'code':pair.code}, 'phone')
    clock[0] = 12 * 3600 + 1
    assert pair.role(session_cookie(admin, 1), 1) is None


@pytest.fixture
def paired_server(tmp_path, monkeypatch):
    # Exercise LAN authentication over a loopback socket without opening a CI interface.
    monkeypatch.setattr(ui, 'lan_address', lambda _: '127.0.0.1')
    server, token = ui.create_server(tmp_path/'cases', lan=True)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    origin = f'http://127.0.0.1:{server.server_port}'

    class Client:
        def __init__(self):
            self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

        def request(self, path, body=None, auth=True, request_origin=None):
            headers = {'X-Local-Token':token} if auth else {}
            if body is not None:
                headers['Content-Type'] = 'application/json'
            if request_origin:
                headers['Origin'] = request_origin
            req = Request(origin+path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
            with self.opener.open(req, timeout=10) as response:
                raw = response.read()
                return json.loads(raw) if response.headers.get_content_type() == 'application/json' else raw

    yield server, token, Client
    server.shutdown(); server.server_close(); worker.join(timeout=5)


def test_phone_pairing_upload_crop_report_and_revoke(paired_server):
    server, token, Client = paired_server
    desktop, phone, stranger = Client(), Client(), Client()
    landing = stranger.request('/')
    assert b'pair-form' in landing and token.encode() not in landing
    with pytest.raises(HTTPError) as error:
        stranger.request('/api/cases')  # Even knowing the CSRF token cannot bypass device pairing.
    assert error.value.code == 403
    with pytest.raises(HTTPError):
        stranger.request('/api/pair', {'code':server.mobile_pairing.code}, auth=False, request_origin='https://evil.example')
    phone.request('/api/pair', {'code':server.mobile_pairing.code}, auth=False)
    desktop.request('/api/pair', {'admin':server.mobile_pairing.admin_secret}, auth=False)
    page = phone.request('/')
    assert token.encode() in page and b'camera-input' in page
    assert phone.request('/api/mobile') == {'enabled':True,'admin':False}
    with pytest.raises(HTTPError) as error:
        phone.request('/api/mobile/revoke', {})
    assert error.value.code == 403
    out = io.BytesIO()
    Image.new('RGB',(100,80),'green').save(out,format='JPEG')
    state = phone.request('/api/cases', {'image':base64.b64encode(out.getvalue()).decode(), 'title':'Phone upload'})
    case = '/api/cases/'+state['id']
    view = '/view/'+state['id']
    assert phone.request(view, auth=False).startswith(b'<!doctype html>')
    with pytest.raises(HTTPError) as error:
        stranger.request(view)
    assert error.value.code == 403
    with pytest.raises(HTTPError):
        phone.request(view, auth=False, request_origin='https://evil.example')
    assert desktop.request(case)['data']['source']['size'] == [100,80]
    phone.request(case+'/crop', {'box':[1,2,20,30], 'label':'phone-detail','scale':2})
    assert phone.request(case+'/report?format=html').startswith(b'<!doctype html>')
    assert phone.request(case)['data']['crops'][0]['label'] == 'phone-detail'
    info = desktop.request('/api/mobile')
    assert info['devices'] == 1 and 'pair=' in info['link']
    desktop.request('/api/mobile/revoke', {})
    with pytest.raises(HTTPError):
        phone.request('/api/cases')
    with pytest.raises(HTTPError):
        phone.request(view, auth=False)
    assert desktop.request('/api/mobile')['devices'] == 0
    assert b'pair-form' in phone.request('/')


def test_pairing_throttle_and_disconnect(paired_server):
    server, _, Client = paired_server
    client = Client()
    for _ in range(10):
        with pytest.raises(HTTPError) as error:
            client.request('/api/pair', {'code':'invalid'}, auth=False)
        assert error.value.code == 400
    with pytest.raises(HTTPError) as error:
        client.request('/api/pair', {'code':server.mobile_pairing.code}, auth=False)
    assert error.value.code == 429


def test_session_cannot_replace_csrf_token(paired_server):
    server, _, Client = paired_server
    client = Client()
    client.request('/api/pair', {'pair':server.mobile_pairing.phone_secret}, auth=False)
    with pytest.raises(HTTPError):
        client.request('/api/demo', {}, auth=False)
    client.request('/api/mobile/disconnect', {})
    with pytest.raises(HTTPError):
        client.request('/api/cases')


def test_heic_is_normalized_without_metadata(tmp_path):
    heif = pytest.importorskip('pillow_heif')
    heif.register_heif_opener()
    photo = tmp_path/'iphone.heic'
    exif = Image.Exif()
    exif[270] = 'Private phone metadata'
    Image.new('RGB',(80,60),'green').save(photo,format='HEIF',exif=exif)
    case = tmp_path/'case'
    init_case(photo,case)
    with Image.open(case/'assets/source.png') as im:
        assert im.size == (80,60) and not im.getexif()
    assert load(case)['source']['metadata_removed']


def test_qr_is_local_png(paired_server):
    pytest.importorskip('qrcode')
    server, _, Client = paired_server
    client=Client()
    client.request('/api/pair', {'admin':server.mobile_pairing.admin_secret}, auth=False)
    raw=client.request('/api/mobile/qr')
    with Image.open(io.BytesIO(raw)) as im:
        assert im.format == 'PNG' and im.width >= 200
