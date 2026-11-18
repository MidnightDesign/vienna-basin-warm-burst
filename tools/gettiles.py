import math, urllib.request, os, sys, concurrent.futures as cf
def tx(lon,z): return (lon+180)/360*2**z
def ty(lat,z):
    r=math.radians(lat); return (1-math.log(math.tan(r)+1/math.cos(r))/math.pi)/2*2**z
views={'wide':(9,13.9,17.25,47.35,48.95),'close':(10,15.4,17.2,47.5,48.55)}
jobs=[]
for name,(z,l0,l1,b0,b1) in views.items():
    for x in range(int(tx(l0,z)),int(tx(l1,z))+1):
        for y in range(int(ty(b1,z)),int(ty(b0,z))+1):
            jobs.append((z,x,y))
def get(j):
    z,x,y=j; p=f'tiles/{z}_{x}_{y}.png'
    if os.path.exists(p) and os.path.getsize(p)>0: return
    url=f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'
    for a in range(3):
        try:
            d=urllib.request.urlopen(url,timeout=60).read(); open(p,'wb').write(d); return
        except Exception as e: err=e
    print('fail',j,err)
with cf.ThreadPoolExecutor(6) as ex: list(ex.map(get,jobs))
print(len(jobs),'tiles')
