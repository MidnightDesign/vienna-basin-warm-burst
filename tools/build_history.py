import json
import sys
import numpy as np

STEP = np.timedelta64(10, "m")
LAG = 2
MIN_RISE = 6.0
BIG_RISE = 8.0
SUSTAIN = 3


def load(keys):
    t = np.concatenate([np.load(f"data/h_{k}_t.npy") for k in keys])
    v = np.concatenate([np.load(f"data/h_{k}_v.npy") for k in keys])
    t, idx = np.unique(t, return_index=True)
    v = v[idx]
    full = np.arange(t[0], t[-1] + STEP, STEP)
    out = np.full(len(full), np.nan, dtype=np.float32)
    out[((t - t[0]) / STEP).astype(int)] = v
    return full, out


def events(t, v, thr):
    d = v[LAG:] - v[:-LAG]
    best = {}
    for i in np.where(d >= thr)[0] + LAG:
        after = v[i:i + SUSTAIN + 1]
        # A real air-mass change stays warm; a sensor glitch drops straight back.
        if np.isnan(after).any() or after.min() < v[i - LAG] + thr * 0.6:
            continue
        day = str((t[i] - np.timedelta64(12, "h")).astype("datetime64[D]"))
        rise = float(v[i] - v[i - LAG])
        if day not in best or rise > best[day][0]:
            best[day] = (rise, i)
    rows = []
    for rise, i in best.values():
        cet = t[i] + np.timedelta64(1, "h")
        s = str(cet)
        hour = int(s[11:13]) + int(s[14:16]) / 60
        rows.append([s[:10], s[11:16], round(hour, 2), round(float(v[i - LAG]), 1), round(float(v[i]), 1), round(rise, 1)])
    return sorted(rows)


def valid_years(v):
    return round(float(np.isfinite(v).sum()) / 52560, 1)


t, v = load(["gump_old", "gump_new"])
ev = events(t, v, MIN_RISE)
tb, vb = load(["baden"])
evb = events(tb, vb, MIN_RISE)
out = {
    "station": "Gumpoldskirchen",
    "firstYear": int(str(t[0])[:4]),
    "validYears": valid_years(v),
    "events": ev,
    "baden": {
        "validYears": valid_years(vb),
        "n8": sum(1 for e in evb if e[5] >= BIG_RISE),
        "n6": len(evb),
    },
}
path = sys.argv[1] if len(sys.argv) > 1 else "../history.js"
open(path, "w", encoding="utf-8").write("const HISTORY=" + json.dumps(out, separators=(",", ":")) + ";\n")
big = [e for e in ev if e[5] >= BIG_RISE]
print(len(ev), "days with", MIN_RISE, "or more;", len(big), "with", BIG_RISE, "or more;", out["validYears"], "years")
print("evening 17-23:", [e[0] for e in big if 17 <= e[2] < 23])
print("23-07:", sum(1 for e in big if e[2] >= 23 or e[2] < 7), "Nov-Feb:", sum(1 for e in big if e[0][5:7] in ("11", "12", "01", "02")))
print("baden:", out["baden"])
