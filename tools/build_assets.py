import json, math, io, base64
import numpy as np
from PIL import Image

ASPECT = 1.4


def mercy(lat):
    return math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def imercy(y):
    return math.degrees(2 * math.atan(math.exp(math.radians(y))) - math.pi / 2)


def bbox(l0, l1, latc):
    h = (l1 - l0) / ASPECT
    yc = mercy(latc)
    return (l0, l1, imercy(yc - h / 2), imercy(yc + h / 2))


VIEWS = {"wide": (9,) + bbox(13.9, 17.25, 48.13), "close": (10,) + bbox(15.45, 17.15, 48.03)}
print(VIEWS)


def tx(lon, z):
    return (lon + 180) / 360 * 2**z


def ty(lat, z):
    r = math.radians(lat)
    return (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * 2**z


OUT = {"views": {}}
IMG_W, IMG_H = 1260, 900
GW, GH = 420, 300
for name, (z, l0, l1, b0, b1) in VIEWS.items():
    x0, x1 = int(tx(l0, z)), int(tx(l1, z))
    y0, y1 = int(ty(b1, z)), int(ty(b0, z))
    mos = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256), dtype=np.float32)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            a = np.asarray(Image.open(f"tiles/{z}_{x}_{y}.png").convert("RGB")).astype(np.float32)
            mos[(y - y0) * 256:(y - y0 + 1) * 256, (x - x0) * 256:(x - x0 + 1) * 256] = (
                a[:, :, 0] * 256 + a[:, :, 1] + a[:, :, 2] / 256 - 32768
            )
    px0 = (tx(l0, z) - x0) * 256
    px1 = (tx(l1, z) - x0) * 256
    py0 = (ty(b1, z) - y0) * 256
    py1 = (ty(b0, z) - y0) * 256
    res = 156543.03 * math.cos(math.radians((b0 + b1) / 2)) / 2**z
    ex = 2.2 if name == "wide" else 2.6
    gy, gx = np.gradient(mos * ex, res)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    hs = np.zeros_like(mos)
    for az, w in ((315, 0.6), (270, 0.2), (360, 0.2)):
        azr = math.radians(360 - az + 90)
        alt = math.radians(45)
        hs += w * (math.sin(alt) * np.cos(slope) + math.cos(alt) * np.sin(slope) * np.cos(azr - aspect))
    flat = math.sin(math.radians(45))
    g = 128 + (hs - flat) * 175
    g = np.clip(g, 44, 222).astype(np.uint8)
    box = (round(px0), round(py0), round(px1), round(py1))
    im = Image.fromarray(g).crop(box).resize((IMG_W, IMG_H), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80, optimize=True)
    el = Image.fromarray(mos).crop(box).resize((GW, GH), Image.BOX)
    ela = np.clip(np.asarray(el), 0, 6000).astype("<u2")
    print(name, mos.shape, len(buf.getvalue()), ela.min(), ela.max())
    OUT["views"][name] = {
        "bbox": [l0, l1, b0, b1],
        "hill": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(),
        "elev": base64.b64encode(ela.tobytes()).decode(),
        "gw": GW,
        "gh": GH,
    }

W = VIEWS["wide"]
BB = (W[1] - 0.5, W[2] + 0.5, W[3] - 0.4, W[4] + 0.4)


def inb(c):
    return BB[0] <= c[0] <= BB[1] and BB[2] <= c[1] <= BB[3]


def rings(g):
    t = g["type"]
    c = g["coordinates"]
    if t == "LineString":
        return [c]
    if t in ("MultiLineString", "Polygon"):
        return c
    if t == "MultiPolygon":
        return [r for p in c for r in p]


def pack(r, nd=3):
    out = []
    last = None
    for c in r:
        p = (round(c[0], nd), round(c[1], nd))
        if p != last:
            out += [p[0], p[1]]
            last = p
    return out


def collect(path, flt=lambda p: True, nd=3):
    d = json.load(open(path, encoding="utf-8"))
    res = []
    for ft in d["features"]:
        if not ft["geometry"] or not flt(ft["properties"]):
            continue
        for r in rings(ft["geometry"]):
            if any(inb(c) for c in r):
                res.append(pack(r, nd))
    return res


OUT["states"] = collect("geo/laender.json")
OUT["borders"] = collect("geo/countries.json")
riv = collect("geo/rivers.json", lambda p: p.get("name") in ("Morava", "Mur"))
riv += collect("geo/rivers_eu.json", lambda p: p.get("name") in ("Enns", "Traun", "Dyje", "Raab"))
OUT["rivers"] = riv
OUT["danube"] = collect("geo/rivers.json", lambda p: p.get("name") in ("Donau", "Danube"))
OUT["lakes"] = collect("geo/lakes_eu.json", lambda p: p.get("name") in ("Neusiedlersee", "Attersee", "Traunsee"))
print({k: (len(OUT[k]), sum(len(r) for r in OUT[k])) for k in ("states", "borders", "rivers", "danube", "lakes")})

m = json.load(open("data/meta.json", encoding="utf-8"))
meta = {s["id"]: s for s in m["stations"]}
o = json.load(open("data/obs.json"))
ts = o["timestamps"]
S = o["stations"]
i0 = ts.index("2026-11-17T12:00+00:00")
i1 = ts.index("2026-11-17T23:40+00:00")
OUT["n"] = i1 - i0 + 1
SMALL = ("AM", "AN", "IM", "BEI", "DER")


def nice(n):
    n = n.replace("/", " / ")
    return " ".join(x.capitalize() if x not in SMALL else x.lower() for x in n.split())


FIX = {
    "GUMPOLDSKIRCHEN": "Gumpoldskirchen", "BAD VOESLAU": "Bad Vöslau", "WIEN/HOHE WARTE": "Wien Hohe Warte",
    "HOHE WAND/HOCHKOGELHAUS": "Hohe Wand", "WIEN/SCHWECHAT-FLUGHAFEN": "Wien-Schwechat Airport",
    "WIEN/UNTERLAA": "Wien Unterlaa", "KLAUSEN-LEOPOLDSDORF": "Klausen-Leopoldsdorf",
    "BRUNN AM GEBIRGE": "Brunn am Gebirge", "WIENER NEUSTADT": "Wiener Neustadt",
    "GROSSENZERSDORF": "Groß-Enzersdorf", "WIEN/MARIABRUNN": "Wien Mariabrunn",
    "WIEN JUBILAEUMSWARTE": "Wien Jubiläumswarte", "WIEN-INNERE STADT": "Wien Innere Stadt",
    "WIEN-DONAUFELD": "Wien Donaufeld", "WIEN STAMMERSDORF": "Wien Stammersdorf",
    "ST.POELTEN LANDHAUS": "St. Pölten", "TULLN/LANGENLEBARN": "Tulln-Langenlebarn",
    "RAX/SEILBAHN-BERGSTAT": "Rax Bergstation", "REICHENAU/RAX": "Reichenau an der Rax",
    "LINZ/HOERSCHING-FLUGHAFEN": "Linz-Hörsching Airport", "MOENICHKIRCHEN": "Mönichkirchen",
    "GAENSERNDORF": "Gänserndorf", "SCHOENGRABERN": "Schöngrabern",
    "BAD DEUTSCH-ALTENBURG": "Bad Deutsch-Altenburg", "NEUSIEDL AM SEE": "Neusiedl am See",
    "MUERZZUSCHLAG": "Mürzzuschlag", "SEMMERING/PASS": "Semmering", "GUTENSTEIN-MARIAHILFBERG": "Gutenstein",
    "LILIENFELD/TARSCHBERG": "Lilienfeld", "KERNHOF - ST. AEGYD A.N.": "St. Aegyd",
    "MARIAZELL/ST SEBASTIAN": "Mariazell", "OBERNDORF/MELK": "Oberndorf an der Melk",
    "RAABS/THAYA": "Raabs an der Thaya", "LAA/THAYA": "Laa an der Thaya", "BAERNKOPF": "Bärnkopf",
    "WAIDHOFEN/YBBS": "Waidhofen an der Ybbs", "BRUCK/MUR": "Bruck an der Mur", "WOERTERBERG": "Wörterberg",
    "ZWERNDORF-MARCHEGG": "Marchegg", "KREMSMUENSTER": "Kremsmünster", "WELS/SCHLEISSHEIM": "Wels",
    "VOECKLABRUCK": "Vöcklabruck", "ALTMUENSTER": "Altmünster", "PRAEBICHL": "Präbichl",
    "ROHRBACH AN DER LAFNITZ/EICH": "Rohrbach an der Lafnitz", "WEIZ - TESTSTATION": "Weiz",
    "KAPFENBERG-FLUGFELD": "Kapfenberg", "LIEBENAU-GUGU": "Liebenau", "HALL/ADMONT": "Admont",
    "IRDNING/GUMPENSTEIN": "Irdning", "REICHENAU/MUEHLKREIS": "Reichenau im Mühlkreis",
    "WACHTBERG BEI STEYR": "Steyr Wachtberg", "NEUDORF/LANDSEE": "Neudorf bei Landsee",
    "ZELTWEG - AUTOM. STAT.": "Zeltweg", "SCHAERDING": "Schärding", "GROEBMING": "Gröbming",
    "OBERWOELZ": "Oberwölz", "ST.RADEGUND": "St. Radegund", "LINZ-STADT": "Linz",
    "RIED IM INNKREIS": "Ried im Innkreis", "AIGEN IM ENNSTAL": "Aigen im Ennstal",
    "DACHSTEIN-SCHLADMINGER GLETSCHER": "Dachstein Gletscher", "STIFT ZWETTL": "Zwettl",
    "SCHWARZAU IM FREIWALD": "Schwarzau im Freiwald", "GARS AM KAMP": "Gars am Kamp",
}


def r1(v, k=10):
    return None if v is None else int(round(v * k))


st = []
for sid, s in S.items():
    me = meta[sid]
    if not (BB[0] + 0.2 <= me["lon"] <= BB[1] - 0.2 and BB[2] + 0.1 <= me["lat"] <= BB[3] - 0.1):
        continue
    T = s["TL"][i0:i1 + 1]
    if sum(v is not None for v in T) < len(T) * 0.8:
        continue
    st.append({
        "id": sid, "name": FIX.get(me["name"], nice(me["name"])),
        "lon": round(me["lon"], 4), "lat": round(me["lat"], 4), "alt": int(me["altitude"]),
        "T": [r1(v) for v in T], "rh": [r1(v, 1) for v in s["RF"][i0:i1 + 1]],
        "td": [r1(v) for v in s["TP"][i0:i1 + 1]], "dd": [r1(v, 1) for v in s["DD"][i0:i1 + 1]],
        "ff": [r1(v) for v in s["FF"][i0:i1 + 1]], "fx": [r1(v) for v in s["FFX"][i0:i1 + 1]],
    })
OUT["stations"] = st
print(len(st), "stations")
print(sorted(x["name"] for x in st))
js = "const ASSETS=" + json.dumps(OUT, separators=(",", ":"), ensure_ascii=False) + ";"
open("../assets.js", "w", encoding="utf-8").write(js)
print(len(js))
