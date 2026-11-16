"""Create the local dashboard data from audited CSVs and official address points."""
import collections
import csv
import importlib.util
import json
import math
import re
import statistics
import sys
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]
ROOT=PROJECT.parent
sys.path.insert(0,str(ROOT))
from summarize_stations import station, LISTED
spec=importlib.util.spec_from_file_location('report_source',ROOT/'outputs/station_report/support/prepare_report.py')
report=importlib.util.module_from_spec(spec);spec.loader.exec_module(report)
STATIONS=[
 (1,'835 Clark Avenue West',43.802943,-79.449259),
 (2,'9290 Keele Street',43.837397,-79.508926),
 (3,'7690 Martin Grove Road',43.774153,-79.609428),
 (4,'835 Nashville Road',43.841960,-79.658463),
 (5,'2 Fieldstone Drive',43.793341,-79.549076),
 (6,'120 McCleary Court',43.798281,-79.513838),
 (7,'40 Eagleview Heights',43.845393,-79.552214),
 (8,'111 Racco Parkway',43.815420,-79.473617),
 (9,'9601 Islington Avenue',43.824225,-79.607636),
 (10,'10800 Dufferin Street',43.880327,-79.492444),
]
SUFFIX={'AV':'AVE','AVENUE':'AVE','BV':'BLVD','BOULEVARD':'BLVD','CR':'CRES','CRESCENT':'CRES','CT':'CRT','COURT':'CRT','DRIVE':'DR','GT':'GATE','LANE':'LANE','LN':'LANE','PK':'PKWY','PY':'PKWY','PARKWAY':'PKWY','PLACE':'PL','ROAD':'RD','STREET':'ST','TR':'TRL','TRAIL':'TRL','WY':'WAY','CL':'CIR','CIRCLE':'CIR','CLOSE':'CLOSE','SQ':'SQ','SQUARE':'SQ','PT':'PT'}
def norm(value):return re.sub(r'[^A-Z0-9 ]','',re.sub(r'\s+',' ',str(value or '').upper())).strip()
def suffix(value):return SUFFIX.get(norm(value),norm(value))
def number(value):
 value=str(value or '').strip()
 try:return str(int(float(value)))
 except ValueError:return norm(value)
def key(n,street,st):return (number(n),norm(street),suffix(st))

index=collections.defaultdict(set)
direction_index=collections.defaultdict(lambda:collections.defaultdict(set))
reference=PROJECT/'scripts/cache/york-vaughan-address-points.json'
points=json.loads(reference.read_text())
for feature in points['features']:
 a=feature['attributes'];g=feature.get('geometry')
 if not g or a.get('ADD_NUM_SUFFIX'):continue
 n=a.get('ADDRESS_NUMBER');name=a.get('STREET_NAME');st=a.get('STREET_TYPE')
 if not n or not name:continue
 # Direction fields are retained as part of the address, never discarded.
 full=' '.join(str(v) for v in (a.get('PREFIX_DIRECTION'),name,a.get('SUFFIX_DIRECTION')) if v)
 point=(round(g['y'],6),round(g['x'],6));fullkey=key(n,full,st)
 index[fullkey].add(point)
 direction_index[key(n,name,st)][fullkey].add(point)
 # Prefix types such as "Highway" are included in the official full name.
 if a.get('FULL_STREET_NAME') and not st:
  index[key(n,a['FULL_STREET_NAME'],'')].add(point)
addresses=[];addressLookup={};reasons=collections.Counter()
def locate(raw):
 k=key(*raw)
 if k in addressLookup:return addressLookup[k]
 match=index.get(k,set());method='unmatched';lat=lon=None
 if not k[0] or not k[1]:method='incomplete_address'
 else:
  if not k[2]:
   candidates=[v for kk,v in index.items() if kk[:2]==k[:2]]
   if len(candidates)==1:match=candidates[0]
  direction_completed=False
  if not match:
   variants=direction_index.get(k,{})
   if len(variants)==1:
    match=next(iter(variants.values()));direction_completed=True
  if match:
   pts=list(match)
   # Multiple reference points at one civic address are accepted only when
   # clustered within 50 metres; larger ambiguous sites remain unlocated.
   ys=[p[0] for p in pts];xs=[p[1] for p in pts]
   spread=math.hypot((max(ys)-min(ys))*111320,(max(xs)-min(xs))*111320*.72)
   if spread<=50:
    lat=round(statistics.median(ys),6);lon=round(statistics.median(xs),6)
    method='official_address_point' if len(pts)==1 else 'official_address_cluster'
    if direction_completed:method+='__unique_direction_completion'
   else:method='ambiguous_address_points'
 addressLookup[k]=len(addresses)
 addresses.append({'address':' '.join(str(v).strip() for v in raw if str(v).strip()),'lat':lat,'lng':lon,'match':method})
 reasons[method]+=1
 return addressLookup[k]

scopes={}
dimensions={'Annual':['All'],'Day_night':['Day','Night'],'Weekday':report.WEEKDAYS,'Month':[f'{m:02d}' for m in range(1,13)],'Season':['Winter','Spring','Summer','Autumn']}
for ss in ['All stations']+list(range(1,11)):
 sid='all' if ss=='All stations' else str(ss)
 for yy in ['All years',2023,2024,2025]:
  yid='all' if yy=='All years' else str(yy)
  groups={}
  for dim,labels in dimensions.items():groups[dim]=[{'label':label,**report.stats(yy,ss,dim,label)} for label in labels]
  scopes[sid+'|'+yid]=groups
 print('Prepared statistics:',sid,flush=True)

incidents={};rawTotals={};recordsTotal=0
for year in (2023,2024,2025):
 with (ROOT/f'VFRS_{year}.csv').open(encoding='utf-8-sig',newline='') as f:
  rows=[{k.strip():v.strip() for k,v in r.items()} for r in csv.DictReader(f)]
 rawTotals[str(year)]=len({r['Inci_no_b'] for r in rows});recordsTotal+=len(rows)
 for r in rows:
  incident=incidents.setdefault(r['Inci_no_b'],{'id':r['Inci_no_b'],'year':year,'date':r['Alm_date_b'],'time':r['Alm_time'],'type':r['Descript'],'district':r['District'],'addresses':[],'responses':[]})
  aid=locate((r['Number'],r['Street'],r['St_type']))
  incident['addresses'].append(aid)
  cancelled=r['Cancelled']=='T'
  incident['responses'].append([r['Unit'],station(r['Unit']),int(cancelled),None if cancelled else int(r['Response_time_seconds']),int(r['Occupied_time_cancelled_seconds'] if cancelled else r['Occupied_time_seconds'])])
for inc in incidents.values():
 addressIDs=collections.Counter(inc.pop('addresses'));inc['address']=addressIDs.most_common(1)[0][0]
 inc['addressConflict']=len(addressIDs)>1
 if inc['addressConflict']:
  # If source records disagree, do not silently choose one location.
  inc['unlocatedReason']='conflicting_recorded_addresses'
 inc['stations']=sorted({r[1] for r in inc['responses'] if r[1] is not None})
coverage={}
for yy in ('all','2023','2024','2025'):
 subset=[i for i in incidents.values() if yy=='all' or str(i['year'])==yy]
 located=[i for i in subset if addresses[i['address']]['lat'] is not None and not i['addressConflict']]
 locatedIDs={i['id'] for i in located}
 coverage[yy]={'total':len(subset),'located':len(located),'unlocated':len(subset)-len(located),'rate':len(located)/len(subset),'reasons':dict(collections.Counter(i.get('unlocatedReason',addresses[i['address']]['match']) for i in subset if i['id'] not in locatedIDs))}
stations=[]
for s,address,lat,lng in STATIONS:
 stations.append({'id':s,'label':f'7-{s}','address':address,'lat':lat,'lng':lng,'units':report.CAPACITY[s],'listedUnits':LISTED[s]})
payload={'updated':'2026-10-15','stations':stations,'scopes':scopes,'rawIncidentTotals':rawTotals,'addresses':addresses,'incidents':list(incidents.values()),'coverage':coverage,
 'sources':{'addresses':points['source'],'stationCoordinates':'Provided by user','analysis':'Audited 2023–2025 incident CSVs','addressReferenceDate':points['downloaded']}}
from privacy import sanitize
payload=sanitize(payload)
target=PROJECT/'dist/data.js';target.write_text('window.VFRS_DATA='+json.dumps(payload,separators=(',',':'),allow_nan=False)+';',encoding='utf-8')
(PROJECT/'scripts/cache/geocoding-summary.json').write_text(json.dumps({'coverage':coverage,'addressCounts':dict(reasons)},indent=2))
assert len(incidents)==41627 and recordsTotal==66080
assert all(-80<a['lng']<-79 and 43<a['lat']<45 for a in addresses if a['lat'] is not None)
assert sum(v for v in rawTotals.values())==41627
assert len(scopes)==44
print('Geocoding coverage:',json.dumps(coverage),flush=True)
print('Dashboard bundle:',round(target.stat().st_size/1024/1024,2),'MB',flush=True)
