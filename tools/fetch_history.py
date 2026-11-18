import json, sys, time, urllib.request
import numpy as np

BASE = "https://dataset.api.hub.geosphere.at/v1/station/historical/klima-v2-10min"
STATIONS = {
    "gump_old": ("5881", 1994, 2018),
    "gump_new": ("5882", 2018, 2026),
    "baden": ("5870", 1992, 2012),
}
for key, (sid, y0, y1) in STATIONS.items():
    ts_all, v_all = [], []
    for y in range(y0, y1 + 1, 2):
        end = min(y + 2, 2027)
        url = f"{BASE}?parameters=tl&start={y}-01-01T00:00&end={end}-01-01T00:00&station_ids={sid}&output_format=geojson"
        for attempt in range(5):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "weather-viz-script"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    d = json.load(r)
                break
            except Exception as e:
                print("retry", key, y, e, file=sys.stderr)
                time.sleep(8 * (attempt + 1))
        else:
            raise SystemExit("failed " + key)
        t = d["timestamps"]
        v = d["features"][0]["properties"]["parameters"]["tl"]["data"] if d["features"] else [None] * len(t)
        if ts_all and t and t[0] == ts_all[-1]:
            t, v = t[1:], v[1:]
        ts_all += t
        v_all += v
        print(key, y, len(t), flush=True)
        time.sleep(2)
    np.save(f"data/h_{key}_t.npy", np.array([x[:16] for x in ts_all], dtype="datetime64[m]"))
    np.save(f"data/h_{key}_v.npy", np.array([np.nan if x is None else x for x in v_all], dtype=np.float32))
