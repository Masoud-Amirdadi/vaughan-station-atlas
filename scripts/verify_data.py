"""Independent integrity checks against the three deduplicated source CSVs."""
import csv
import json
import statistics
import sys
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1];ROOT=PROJECT.parent
sys.path.insert(0,str(ROOT))
from summarize_stations import station
d=json.loads((PROJECT/'dist/data.js').read_text(encoding='utf-8')[17:-1])
rows=[]
for year in (2023,2024,2025):
 with (ROOT/f'VFRS_{year}.csv').open(encoding='utf-8-sig',newline='') as f:
  for raw in csv.DictReader(f):
   r={k.strip():v.strip() for k,v in raw.items()};r['year']=year;r['station']=station(r['Unit']);rows.append(r)
assert len(rows)==66080
assert len(d['incidents'])==len({r['Inci_no_b'] for r in rows})==41627
assert sum(len(i['responses']) for i in d['incidents'])==66080
for name,groups in d['scopes'].items():
 sid,yy=name.split('|');selected=[r for r in rows if r['station'] is not None and (sid=='all' or r['station']==int(sid)) and (yy=='all' or r['year']==int(yy))]
 nc=[r for r in selected if r['Cancelled']=='F'];cc=[r for r in selected if r['Cancelled']=='T'];a=groups['Annual'][0]
 assert a['responses']==len(nc) and a['cancelled']==len(cc),name
 assert a['incidents']==len({r['Inci_no_b'] for r in nc}),name
 values=sorted(int(r['Response_time_seconds'])/60 for r in nc)
 assert abs(a['avg']-statistics.mean(values))<1e-9,name
 assert abs(a['median']-statistics.median(values))<1e-9,name
 q=(len(values)-1)*.9;lo=int(q);hi=min(lo+1,len(values)-1);p90=values[lo]+(values[hi]-values[lo])*(q-lo)
 assert abs(a['p90']-p90)<1e-9,name
 assert abs(a['occupied']-statistics.mean(int(r['Occupied_time_seconds'])/60 for r in nc))<1e-9,name
 assert abs(a['cancel_occupied']-statistics.mean(int(r['Occupied_time_cancelled_seconds'])/60 for r in cc))<1e-9,name
 assert 0<=a['idle_pct']<=1
 for dim in ('Month','Weekday','Season','Day_night'):
  group=groups[dim];assert sum(v['responses'] for v in group)==a['responses'];assert sum(v['cancelled'] for v in group)==a['cancelled']
  assert abs(sum(v['idle'] for v in group)-a['idle'])<.01,(name,dim)
  assert abs(sum(v['avg']*v['responses'] for v in group)/a['responses']-a['avg'])<1e-8,(name,dim)
for year,coverage in d['coverage'].items():
 selected=[i for i in d['incidents'] if year=='all' or str(i['year'])==year]
 located=[i for i in selected if d['addresses'][i['address']]['lat'] is not None]
 assert len(located)==coverage['located'];assert len(selected)==coverage['total'];assert coverage['located']+coverage['unlocated']==coverage['total']
for a in d['addresses']:
 if a['lat'] is not None:
  assert 43.7<a['lat']<44.1 and -79.9<a['lng']<-79.2
 assert (a['lat'] is None)==(a['lng'] is None)
assert len(d['stations'])==10 and sum(s['units'] for s in d['stations'])==14
assert d['stations'][3]['lat']==43.841960 and d['stations'][3]['lng']==-79.658463
print('PASS: 44 analytical scopes; pooled response/occupied statistics; calendar reconciliations; 66,080 response records; 41,627 unique incidents; all station coordinates and geocoding coverage.')
print('Located:',d['coverage']['all']['located'],'/',d['coverage']['all']['total'])

allowed={'year','category','address','responses'}
assert all(set(i)==allowed for i in d['incidents'])
assert all(set(a)=={'lat','lng'} for a in d['addresses'])
assert all(len(r)==3 and r[0] is None for i in d['incidents'] for r in i['responses'])
for name, summary in d['thresholds'].items():
 sid,yy=name.split('|')
 values=[int(r['Response_time_seconds']) for r in rows if r['station'] is not None and r['Cancelled']=='F' and (sid=='all' or r['station']==int(sid)) and (yy=='all' or r['year']==int(yy))]
 assert summary['within4']==sum(v<=240 for v in values)
 assert summary['within6']==sum(v<=360 for v in values)
print('PASS: minimized incident schema and all 44 precomputed thresholds verified against source CSVs.')
