# Vienna Basin Warm Burst

An animated map of the evening of 17 November 2026, when a warm west wind broke through the cold air in the Vienna Basin. Gumpoldskirchen gained 8.4 °C in 20 minutes.

The site is three static files:

- `index.html` holds the page, its styles and its code.
- `assets.js` holds the data for the evening: station readings, terrain shading, borders, rivers and lakes.
- `history.js` holds 30 years of similar jumps at Gumpoldskirchen.

No build step is needed. Open `index.html` through any web server.

## Regenerating the data

`assets.js` is the only copy of the station readings in this repository. GeoSphere keeps the 10-minute TAWES dataset for a limited time, so keep the file unless you have fetched the readings again.

Run these from the `tools` folder. They need Python 3 with `numpy` and `Pillow`.

```sh
mkdir -p data geo tiles
curl -o data/meta.json "https://dataset.api.hub.geosphere.at/v1/station/historical/tawes-v1-10min/metadata"
python fetch.py
python gettiles.py
B=https://raw.githubusercontent.com
curl -o geo/laender.json "$B/ginseng666/GeoJSON-TopoJSON-Austria/master/2021/simplified-99.5/laender_995_geo.json"
curl -o geo/rivers.json "$B/nvkelso/natural-earth-vector/master/geojson/ne_10m_rivers_lake_centerlines.geojson"
curl -o geo/rivers_eu.json "$B/nvkelso/natural-earth-vector/master/geojson/ne_10m_rivers_europe.geojson"
curl -o geo/lakes_eu.json "$B/nvkelso/natural-earth-vector/master/geojson/ne_10m_lakes_europe.geojson"
curl -o geo/countries.json "$B/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_boundary_lines_land.geojson"
python build_assets.py
```

`build_assets.py` writes `assets.js` to the repository root.

## Regenerating the history

`history.js` lists every day since 1994 on which Gumpoldskirchen warmed by 6 °C or more within 20 minutes. It comes from the GeoSphere climate station archive (`klima-v2-10min`), which keeps the full record.

```sh
python fetch_history.py
python build_history.py
```

`build_history.py` writes `history.js` to the repository root.

## Sources

- Station readings: [GeoSphere Austria Data Hub](https://data.hub.geosphere.at/), TAWES and climate station 10-minute observations, CC BY 4.0.
- Terrain: Mapzen terrain tiles on AWS.
- Borders, rivers and lakes: Natural Earth and Statistik Austria.

The colored surface between stations is an estimate. Only the station dots and numbers are measurements.
