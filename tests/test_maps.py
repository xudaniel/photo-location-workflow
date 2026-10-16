import json
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit
from xml.etree import ElementTree as ET

from PIL import Image
import pytest

from photo_location_workflow.core import add_evidence, candidate, check_case, init_case, load, save
from photo_location_workflow.maps import (capture_date, clean_location, clean_view, export_kml,
    parse_google_url, save_location, save_view, search_url, shortlist_url)
from photo_location_workflow.report import render_html


@pytest.fixture
def case(tmp_path):
    photo = tmp_path / 'synthetic.png'
    Image.new('RGB', (100, 80), 'green').save(photo)
    path = tmp_path / 'case'
    init_case(photo, path)
    candidate(path, 'Synthetic <landmark>', 'Fictional & unverified', 'https://example.org/')
    add_evidence(path, 'c1', 'streetview', 'https://www.google.com/maps/', 'unclear', 'Synthetic test only', photo, 'unknown')
    return path


@pytest.mark.parametrize('value', [float('nan'), float('inf'), True, [], '91', 'junk'])
def test_coordinates_reject_invalid_latitudes(value):
    with pytest.raises(ValueError):
        clean_location({'latitude': value, 'longitude': 0})


def test_coordinates_require_pair_and_preserve_precision():
    with pytest.raises(ValueError):
        clean_location({'latitude': 0})
    loc = clean_location({'latitude': 40.6234567890123, 'longitude': 0})
    assert '40.6234567890123,0' == parse_qs(urlsplit(search_url({'name':'a','address':'b','map_location':loc})).query)['query'][0]


def test_parse_explicit_fields_without_inventing_locations():
    url = 'https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=40.123456789,0&pano=sample&heading=-45&pitch=12&fov=80'
    fields = parse_google_url(url)['fields']
    assert fields['latitude'] == 40.123456789
    assert fields['pano'] == 'sample'
    assert clean_view({**fields, 'original_url':url})['replay_mode'] == 'panorama_id'
    for url in ('https://maps.app.goo.gl/example', 'https://www.google.com/maps/@40,140,15z',
                'https://www.google.com/maps/@?api=1&map_action=map&center=40,140',
                'https://www.google.com.evil.org/maps/search/?api=1&query=40,140',
                'https://www.google.com/maps/search/?api=1&query=40,140&query=0,0'):
        assert parse_google_url(url) == {'fields': {}, 'status': 'link_only'}
    with pytest.raises(ValueError):
        parse_google_url('https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=99,140')
    fields = parse_google_url('https://www.google.com/maps/search/?api=1&query=0,0&query_place_id=example')['fields']
    assert fields == {'latitude':0.0,'longitude':0.0,'place_id':'example'}


@pytest.mark.parametrize('view', [
    {'tool':'google_streetview','latitude':0,'longitude':0,'heading':361},
    {'tool':'google_streetview','pano':'sample','pitch':-91},
    {'tool':'google_streetview','pano':'sample','fov':9},
    {'tool':'google_streetview'}, {'tool':'mapillary'}, {'tool':'google_streetview','pano':'sample','availability':'unknown_value'},
    {'tool':'mapillary','original_url':'javascript:alert(1)'},
    {'tool':'google_satellite','latitude':0,'longitude':0,'pano':'wrong'},
])
def test_invalid_views(view):
    with pytest.raises(ValueError):
        clean_view(view)


def test_view_modes_and_capture_precision():
    assert clean_view({'tool':'google_streetview','latitude':0,'longitude':0})['replay_mode'] == 'nearest_panorama'
    assert clean_view({'tool':'google_streetview','original_url':'https://maps.app.goo.gl/example'})['replay_mode'] == 'saved_link'
    assert clean_view({'tool':'google_terrain','latitude':0,'longitude':0})['replay_mode'] == 'map_center'
    for date in ('2024', '2024-01', 'unknown'):
        assert capture_date(date, True) == date
    for date in ('2024-00','2024-13','2024-1','0000','',None):
        with pytest.raises(ValueError): capture_date(date, True)


def test_location_history_shortlist_and_kml(case):
    save_location(case, 'c1', {'latitude':0,'longitude':140.123456789,'place_id':'sample','notes':'Manually checked test'})
    data = load(case)
    assert 'query_place_id=sample' in data['candidates'][0]['maps_url']
    assert 'place_ids=sample' in shortlist_url(data)
    assert 'Coordinates / 坐标: 0.0, 140.123456789' in render_html(case).read_text()
    xml = ET.fromstring(export_kml(data))
    assert xml.find('.//{*}coordinates').text == '140.123456789,0.0,0'
    assert xml.find('.//{*}name').text == 'c1 · Synthetic <landmark>'
    assert 'UNVERIFIED' in xml.find('.//{*}description').text
    save_location(case, 'c1', {'latitude':1,'longitude':2})
    data = load(case)
    assert data['candidates'][0]['map_history'][-1]['previous']['latitude'] == 0
    assert data['conclusion']['level'] == 'candidate'
    assert shortlist_url(data) is None
    with pytest.raises(ValueError): export_kml({'candidates':[]})
    with pytest.raises(ValueError): shortlist_url({'candidates':[{'map_location':{'place_id':str(i)}} for i in range(21)]})


def test_saved_view_report_history_integrity_and_assets(case):
    before = (case/'assets/source.png').read_bytes()
    view = {'tool':'google_streetview','latitude':0,'longitude':140,'pano':'example','availability':'unavailable','heading':12,'pitch':0,'fov':80,
            'original_url':'https://www.google.com/maps/'}
    save_view(case, 'e1', view, '2025', 'Synthetic attribution')
    save_view(case, 'e1', {**view,'heading':22}, 'unknown', 'Corrected attribution')
    data = load(case)
    e = data['evidence'][0]
    assert e['view_history'][-1]['previous']['heading'] == 12
    assert e['view_history'][-1]['captured'] == '2025'
    assert e['map_view']['availability'] == 'unavailable'
    assert e['captured'] == 'unknown' and 'saved_at' in e['map_view']
    assert check_case(case)['ok']
    report = render_html(case).read_text()
    assert 'Heading / 朝向: 22.0' in report and 'Heading / 朝向: 12.0' in report
    assert 'Synthetic attribution' in report and 'Panorama IDs can expire' in report
    assert 'Reopen saved view' in report
    assert before == (case/'assets/source.png').read_bytes()
    e['map_view']['replay_url'] = 'https://example.org/tampered'
    save(case,data)
    assert not check_case(case)['ok']


def test_new_map_evidence_validation_is_atomic(case):
    original = load(case)
    with pytest.raises(ValueError):
        add_evidence(case,'c1','reference','https://example.org/','unclear','Synthetic',
                     map_view={'tool':'google_streetview','pano':'sample'})
    assert load(case) == original
    entry = add_evidence(case,'c1','reference','https://example.org/','contradiction','Synthetic terrain mismatch',
                         captured='2024',map_view={'tool':'google_earth','original_url':'https://earth.google.com/web/'})
    assert entry['map_view']['replay_mode'] == 'saved_link'
    assert entry['captured'] == '2024'


def test_map_cli_round_trip(case,tmp_path):
    def call(*args):
        result = subprocess.run([sys.executable,'-m','photo_location_workflow',*map(str,args)],capture_output=True,text=True)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)
    call('map-location',case,'--candidate','c1','--latitude','0','--longitude','140')
    call('map-view',case,'--evidence','e1','--tool','google_streetview','--latitude','0','--longitude','140','--captured','2025')
    assert call('map-links',case)['candidates']['c1']
    path = tmp_path/'places.kml'
    call('map-links',case,'--kml',path)
    assert ET.parse(path).find('.//{*}coordinates').text == '140.0,0.0,0'
    assert call('map-parse','https://maps.app.goo.gl/test')['status'] == 'link_only'
