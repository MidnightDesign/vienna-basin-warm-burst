import json, urllib.request, time, sys
m=json.load(open('data/meta.json',encoding='utf-8'))
ids=[s['id'] for s in m['stations'] if s.get('is_active')]
base='https://dataset.api.hub.geosphere.at/v1/station/historical/tawes-v1-10min'
out={}
ts=None
B=40
for i in range(0,len(ids),B):
    chunk=ids[i:i+B]
    url=f"{base}?parameters=TL,RF,TP,DD,FF,FFX,PRED,RR&start=2026-11-17T06:00&end=2026-11-18T08:00&station_ids={','.join(chunk)}&output_format=geojson"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'weather-viz-script'}),timeout=90) as r:
                d=json.load(r)
            break
        except Exception as e:
            print('retry',i,e,file=sys.stderr); time.sleep(5)
    else:
        raise SystemExit('failed')
    ts=d['timestamps']
    for f in d['features']:
        sid=f['properties']['station']
        out[sid]={k:v['data'] for k,v in f['properties']['parameters'].items()}
    print(i,len(d['features']),len(ts)); time.sleep(1.5)
json.dump({'timestamps':ts,'stations':out},open('data/obs.json','w'))
print(ts[0],ts[-1],len(out))
