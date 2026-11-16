"""Minimize incident data before it enters the distributable atlas."""
import math
from collections import Counter

CATEGORIES = ('EMS', 'Fire', 'Vehicle collision', 'Rescue', 'Alarm', 'Public hazard', 'Public assistance', 'Other')

def category(description):
    if description in CATEGORIES:
        return description
    s = description.lower()
    if any(x in s for x in ('medical', 'resuscitator', 'chest pains', 'asphyxia', 'respiratory', 'accident or illness', 'vital signs', 'seizure', 'alcohol or drug', 'oxygen', 'cpr', 'traumatic shock', 'burns', 'defibrillator', 'electric shock', 'home/residential accident', 'commercial/industrial accident')):
        return 'EMS'
    if 'vehicle collision' in s:
        return 'Vehicle collision'
    if any(x in s for x in ('rescue', 'extrication', 'trapped')):
        return 'Rescue'
    if any(x in s for x in ('alarm', 'false fire', 'human -')):
        return 'Alarm'
    if s == 'fire' or any(x in s for x in ('outdoor fire', 'burning', 'combustion explosion')):
        return 'Fire'
    if any(x in s for x in ('assistance', 'assisting', 'public service')):
        return 'Public assistance'
    if any(x in s for x in ('hazard', 'gas leak', 'co incident', 'spill', 'power lines', 'ruptured', 'overheat', 'no fire', 'pre fire', 'suspicious substance', 'building collapse', 'bomb')):
        return 'Public hazard'
    return 'Other'

def sanitize(payload):
    if payload.get('privacy', {}).get('version') == 1:
        return payload
    thresholds = {}
    for station in ['all'] + [str(s['id']) for s in payload['stations']]:
        for year in ['all', '2023', '2024', '2025']:
            values = [r[3] for i in payload['incidents'] if year == 'all' or str(i['year']) == year
                      for r in i['responses'] if r[1] is not None and r[2] == 0 and r[3] is not None and r[3] >= 0
                      and (station == 'all' or str(r[1]) == station)]
            total, four, six = len(values), sum(v <= 240 for v in values), sum(v <= 360 for v in values)
            thresholds[f'{station}|{year}'] = dict(total=total, within4=four, within6=six, between4and6=six-four,
                above6=total-six, rate4=four/total if total else None, rate6=six/total if total else None)
    areas, lookup, incidents = [], {}, []
    for i in payload['incidents']:
        a = payload['addresses'][i['address']]
        located = not i['addressConflict'] and a['lat'] is not None
        # Fixed cells about 556 m north/south and 500 m east/west at Vaughan.
        cell = (math.floor(a['lat']/.005), math.floor(a['lng']/.00625)) if located else None
        if cell not in lookup:
            lookup[cell] = len(areas)
            areas.append({'lat': round((cell[0]+.5)*.005, 6) if cell else None,
                          'lng': round((cell[1]+.5)*.00625, 6) if cell else None})
        incidents.append({'year': i['year'], 'category': category(i['type']), 'address': lookup[cell],
                          'responses': [[None, r[1], r[2]] for r in i['responses']]})
    payload.update(addresses=areas, incidents=incidents, thresholds=thresholds,
        privacy={'version': 1, 'location': 'Approximate 500-metre grid areas', 'detail': 'Broad category and reporting year only'})
    return payload

if __name__ == '__main__':
    import json
    from pathlib import Path
    target = Path(__file__).resolve().parents[1] / 'dist/data.js'
    payload = sanitize(json.loads(target.read_text(encoding='utf-8')[17:-1]))
    target.write_text('window.VFRS_DATA='+json.dumps(payload, separators=(',', ':'), allow_nan=False)+';', encoding='utf-8')
    print('Sanitized', len(payload['incidents']), 'incidents into', len(payload['addresses'])-1, 'approximate areas.')
    print(dict(Counter(i['category'] for i in payload['incidents'])))
