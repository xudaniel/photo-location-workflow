"""Paired pixel regions attached to a reviewed evidence image."""

from PIL import Image

from .core import asset_path, check_case, load, now, save


def validate_box(box, size):
    if not isinstance(box, (list, tuple)) or len(box) != 4 or any(type(v) is not int for v in box):
        raise ValueError('A region needs four integers: x,y,width,height.')
    x, y, w, h = box
    if min(x, y) < 0 or min(w, h) <= 0 or x + w > size[0] or y + h > size[1]:
        raise ValueError('The annotated region must fit inside its image.')
    return list(box)


def validate_annotations(case, data, evidence):
    """Validate optional schema-v1 regions, including manually edited records."""
    items = evidence.get('annotations', [])
    if not isinstance(items, list) or len(items) > 100:
        raise ValueError('An evidence record supports up to 100 paired annotations.')
    if not items:
        return
    if not evidence.get('asset'):
        raise ValueError('Paired annotations need an attached reference image.')
    with Image.open(asset_path(case, data['source']['asset'])) as source:
        source_size = source.size
    with Image.open(asset_path(case, evidence['asset'])) as reference:
        reference_size = reference.size
    numbers = set()
    for item in items:
        number = item.get('number')
        if type(number) is not int or number < 1 or number in numbers or item.get('id') != f'a{number}':
            raise ValueError('Annotation numbers and IDs must be unique positive integers.')
        numbers.add(number)
        label = item.get('label')
        if not isinstance(label, str) or not label.strip() or len(label) > 160:
            raise ValueError('Describe the detail in 1-160 characters.')
        validate_box(item.get('source_box'), source_size)
        validate_box(item.get('reference_box'), reference_size)


def _evidence(data, evidence_id):
    item = next((e for e in data['evidence'] if e['id'] == evidence_id), None)
    if item is None:
        raise ValueError(f'Unknown evidence: {evidence_id}')
    return item


def _reset_conclusion(data, evidence):
    data['conclusion'] = {'level': 'candidate', 'candidate_id': evidence['candidate_id'],
                          'note': 'Comparison annotations changed; review the conclusion again.'}


def add_annotation(case, evidence_id, label, source_box, reference_box):
    integrity = check_case(case)
    if not integrity['ok']:
        raise ValueError('Fix case integrity before annotating: ' + '; '.join(integrity['errors']))
    data = load(case)
    evidence = _evidence(data, evidence_id)
    items = evidence.setdefault('annotations', [])
    number = evidence.get('next_annotation_number', max((a['number'] for a in items), default=0) + 1)
    if type(number) is not int or number <= max((a['number'] for a in items), default=0):
        raise ValueError('Invalid next annotation number.')
    item = {'id': f'a{number}', 'number': number, 'label': label.strip() if isinstance(label, str) else label,
            'source_box': source_box, 'reference_box': reference_box, 'created_at': now()}
    items.append(item)
    validate_annotations(case, data, evidence)
    item['source_box'], item['reference_box'] = list(source_box), list(reference_box)
    evidence['next_annotation_number'] = number + 1
    _reset_conclusion(data, evidence)
    save(case, data)
    return item


def remove_annotation(case, evidence_id, annotation_id, reason):
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError('Explain why the annotation is being removed.')
    data = load(case)
    evidence = _evidence(data, evidence_id)
    item = next((a for a in evidence.get('annotations', []) if a['id'] == annotation_id), None)
    if item is None:
        raise ValueError(f'Unknown annotation: {annotation_id}')
    # Keep the former regions and reason, and never reuse a removed number.
    evidence['next_annotation_number'] = max(evidence.get('next_annotation_number', 1), item['number'] + 1)
    evidence.setdefault('annotation_history', []).append(
        {'action': 'removed', 'annotation': item, 'reason': reason.strip(), 'at': now()})
    evidence['annotations'].remove(item)
    _reset_conclusion(data, evidence)
    save(case, data)
    return item
