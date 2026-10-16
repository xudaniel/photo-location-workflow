"""Keyless map links and auditable, manually inspected viewpoints; no network calls."""
import math
import re
from urllib.parse import parse_qs, urlencode, urlsplit
from xml.etree import ElementTree as ET

from .core import find_candidate, load, now, save, web_url

TOOLS = ('google_streetview', 'google_satellite', 'google_terrain', 'google_earth', 'mapillary', 'openstreetmap', 'other')
VIEW_NOTICE = ('Saved parameters reopen a view; they do not verify a match. Panorama IDs can expire; '
               'coordinate fallback may show different imagery. / 保存视角不等于已核实；全景 ID 可能失效，坐标回退可能显示不同影像。')


def text(value, name, limit=2000):
    if value is None:
        return ''
    if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 for c in value):
        raise ValueError(f'{name} must be text up to {limit} characters without control characters.')
    return value.strip()


def number(value, name, low, high):
    if value is None or value == '':
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(f'{name} must be between {low} and {high}.')
    try:
        result = float(value)
    except (ValueError, OverflowError):
        raise ValueError(f'{name} must be between {low} and {high}.') from None
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError(f'{name} must be between {low} and {high}.')
    return result


def coordinates(value):
    lat = number(value.get('latitude'), 'Latitude', -90, 90)
    lon = number(value.get('longitude'), 'Longitude', -180, 180)
    if (lat is None) != (lon is None):
        raise ValueError('Supply both latitude and longitude, or leave both blank.')
    return {'latitude': lat, 'longitude': lon}


def coord_string(value):
    return f'{value["latitude"]:.15g},{value["longitude"]:.15g}'


def capture_date(value, required=False):
    value = text(value, 'Capture date', 10)
    if not value:
        if required:
            raise ValueError('Record the displayed capture year / month, or explicitly use unknown.')
        return None
    if value == 'unknown':
        return value
    if not re.fullmatch(r'[0-9]{4}(?:-(?:0[1-9]|1[0-2]))?', value) or int(value[:4]) < 1:
        raise ValueError('Use a capture year YYYY, month YYYY-MM, or unknown; never invent a missing month.')
    return value


def clean_location(value):
    if not isinstance(value, dict):
        raise ValueError('Map location must be an object.')
    result = coordinates(value)
    result.update(place_id=text(value.get('place_id'), 'Place ID', 300),
                  shared_url=text(value.get('shared_url'), 'Map URL'),
                  notes=text(value.get('notes'), 'Location provenance'))
    if result['shared_url']:
        web_url(result['shared_url'])
    if not (result['latitude'] is not None or result['place_id'] or result['shared_url']):
        raise ValueError('Supply coordinates, a Place ID, or an inspected map URL.')
    return result


def search_url(candidate):
    context = candidate.get('map_location', {})
    query = coord_string(context) if context.get('latitude') is not None else f'{candidate["name"]} {candidate["address"]}'
    params = {'api': 1, 'query': query}
    if context.get('place_id'):
        params['query_place_id'] = context['place_id']
    return 'https://www.google.com/maps/search/?' + urlencode(params)


def map_url(value, basemap='roadmap'):
    if value.get('latitude') is None:
        return None
    return 'https://www.google.com/maps/@?' + urlencode({'api': 1, 'map_action': 'map', 'center': coord_string(value), 'zoom': 17, 'basemap': basemap})


def clean_view(value):
    if not isinstance(value, dict) or value.get('tool') not in TOOLS:
        raise ValueError('Choose a supported map tool.')
    availability = value.get('availability', 'unreviewed')
    if availability not in ('unreviewed', 'available', 'unavailable'):
        raise ValueError('Choose unreviewed, available or unavailable imagery status.')
    result = {'tool': value['tool'], 'availability': availability, **coordinates(value),
              'original_url': text(value.get('original_url'), 'Original view URL'),
              'pano': text(value.get('pano'), 'Panorama ID', 500)}
    if result['original_url']:
        web_url(result['original_url'])
    for key, low, high in (('heading', -180, 360), ('pitch', -90, 90), ('fov', 10, 100)):
        result[key] = number(value.get(key), key, low, high)
    if result['tool'] != 'google_streetview' and (result['pano'] or any(result[k] is not None for k in ('heading', 'pitch', 'fov'))):
        raise ValueError('Panorama and camera parameters apply only to Google Street View.')
    if result['tool'] == 'google_streetview' and (result['pano'] or result['latitude'] is not None):
        params = {'api': 1, 'map_action': 'pano'}
        if result['pano']:
            params['pano'] = result['pano']
        if result['latitude'] is not None:
            params['viewpoint'] = coord_string(result)
        params.update({k: result[k] for k in ('heading', 'pitch', 'fov') if result[k] is not None})
        replay = 'https://www.google.com/maps/@?' + urlencode(params)
        result['replay_mode'] = 'panorama_id' if result['pano'] else 'nearest_panorama'
    elif result['tool'] in ('google_satellite', 'google_terrain') and result['latitude'] is not None:
        replay = map_url(result, result['tool'].removeprefix('google_'))
        result['replay_mode'] = 'map_center'
    elif result['original_url']:
        replay = result['original_url']
        result['replay_mode'] = 'saved_link'
    else:
        raise ValueError('Supply an inspected source URL, or Google view coordinates / panorama ID.')
    if len(replay) > 2048:
        raise ValueError('View URL exceeds 2048 characters; shorten the supplied fields.')
    result['replay_url'] = replay
    return result


def parse_google_url(url):
    """Only documented api=1 links; never infer place coordinates from a camera center."""
    web_url(url)
    parsed = urlsplit(url)
    if parsed.hostname not in ('www.google.com', 'google.com', 'maps.google.com') or not parsed.path.startswith('/maps'):
        return {'fields': {}, 'status': 'link_only'}
    query = parse_qs(parsed.query)
    if any(len(values) != 1 for values in query.values()) or query.get('api') != ['1']:
        return {'fields': {}, 'status': 'link_only'}
    q = {k: values[0] for k, values in query.items()}
    fields = {}
    location = q.get('viewpoint') if q.get('map_action') == 'pano' else (q.get('query') if parsed.path.startswith('/maps/search') else None)
    if location and re.fullmatch(r'\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*', location):
        lat, lon = location.split(',')
        fields.update(coordinates({'latitude': lat, 'longitude': lon}))
    if q.get('query_place_id'):
        fields['place_id'] = text(q['query_place_id'], 'Place ID', 300)
    if q.get('map_action') == 'pano':
        fields['tool'] = 'google_streetview'
        for key in ('pano', 'heading', 'pitch', 'fov'):
            if key in q:
                fields[key] = q[key]
        # Validate before returning any prefilled values.
        clean_view({**fields, 'original_url': url})
    return {'fields': fields, 'status': 'parsed' if fields else 'link_only'}


def save_location(case, candidate_id, value):
    context = clean_location(value)
    data = load(case)
    item = find_candidate(data, candidate_id)
    item.setdefault('map_history', []).append({'previous': item.get('map_location'), 'at': now()})
    item['map_location'] = {**context, 'saved_at': now()}
    item['maps_url'] = search_url(item)
    data['conclusion'] = {'level': 'candidate', 'candidate_id': candidate_id, 'note': 'Map location changed; review conclusion again.'}
    save(case, data)
    return item


def save_view(case, evidence_id, value, captured, provider):
    view = clean_view(value)
    date = capture_date(captured, True)
    provider = text(provider, 'Attribution', 1000)
    data = load(case)
    item = next((e for e in data['evidence'] if e['id'] == evidence_id), None)
    if item is None:
        raise ValueError('Evidence not found.')
    if view['tool'] == 'google_streetview' and item['kind'] != 'streetview':
        raise ValueError('Google Street View requires a Street View evidence record; use another tool for reference evidence.')
    item.setdefault('view_history', []).append({'previous': item.get('map_view'), 'captured': item.get('captured'), 'provider': item.get('provider'), 'at': now()})
    item.update(map_view={**view, 'saved_at': now()}, captured=date, provider=provider)
    data['conclusion'] = {'level': 'candidate', 'candidate_id': item['candidate_id'], 'note': 'Map viewpoint changed; review conclusion again.'}
    save(case, data)
    return item


def candidate_links(candidate):
    context = candidate.get('map_location', {})
    links = [('Google Maps', search_url(candidate))]
    if context.get('shared_url'):
        links.append(('Saved map / 已保存地图', context['shared_url']))
    if context.get('latitude') is not None:
        links += [('Satellite / 卫星', map_url(context, 'satellite')), ('Terrain / 地形', map_url(context, 'terrain')),
                  ('Nearby Street View / 附近街景', clean_view({'tool': 'google_streetview', **coordinates(context)})['replay_url']),
                  ('OpenStreetMap', 'https://www.openstreetmap.org/?' + urlencode({'mlat': context['latitude'], 'mlon': context['longitude']}) + '#map=17/' + str(context['latitude']) + '/' + str(context['longitude']))]
    links += [('Google Earth', 'https://earth.google.com/web/'), ('Mapillary', 'https://www.mapillary.com/app/')]
    return links


def shortlist_url(data):
    ids = list(dict.fromkeys(c.get('map_location', {}).get('place_id') for c in data['candidates'] if c.get('map_location', {}).get('place_id')))
    if not ids:
        return None
    if len(ids) > 20:
        raise ValueError('Google shortlist supports at most 20 distinct Place IDs.')
    url = 'https://www.google.com/maps/@?' + urlencode({'api': 1, 'map_action': 'shortlist', 'place_ids': ','.join(ids)})
    if len(url) > 2048:
        raise ValueError('Shortlist URL exceeds 2048 characters.')
    return url


def export_kml(data):
    ns = 'http://www.opengis.net/kml/2.2'
    ET.register_namespace('', ns)
    root = ET.Element(f'{{{ns}}}kml')
    doc = ET.SubElement(root, 'Document')
    count = 0
    for item in data['candidates']:
        context = item.get('map_location')
        if not context or context.get('latitude') is None:
            continue
        context = clean_location(context)
        mark = ET.SubElement(doc, 'Placemark')
        ET.SubElement(mark, 'name').text = f'{item["id"]} · {item["name"]}'
        ET.SubElement(mark, 'description').text = f'UNVERIFIED CANDIDATE / 未核实候选\n{item["address"]}\n{item["source_url"]}'
        ET.SubElement(ET.SubElement(mark, 'Point'), 'coordinates').text = f'{context["longitude"]},{context["latitude"]},0'
        count += 1
    if not count:
        raise ValueError('Save candidate coordinates before exporting KML.')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def view_summary(view):
    labels = {'tool': 'Tool / 工具', 'availability': 'Availability / 查看状态',
              'latitude': 'Latitude / 纬度', 'longitude': 'Longitude / 经度',
              'pano': 'Panorama ID / 全景 ID', 'heading': 'Heading / 朝向',
              'pitch': 'Pitch / 俯仰', 'fov': 'Horizontal FOV / 水平视野',
              'replay_mode': 'Reopen mode / 重开方式', 'saved_at': 'Saved at / 保存时间'}
    values = {'unreviewed': 'Not checked / 未检查', 'available': 'Available / 可查看',
              'unavailable': 'Unavailable / 无影像或无法查看', 'panorama_id': 'Specified panorama / 指定全景',
              'nearest_panorama': 'Nearby panorama / 附近全景', 'map_center': 'Map center / 地图中心',
              'saved_link': 'Original link / 原始链接'}
    return ' · '.join(f'{label}: {values.get(str(view[key]), view[key])}' for key, label in labels.items()
                      if view.get(key) is not None and view.get(key) != '')
