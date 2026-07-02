# Satellite data — `get_geo_data`

Satellite-derived indicators that exist in no statistical warehouse, fetched
live from the provider and aggregated over a region server-side. Use them for
signals official statistics can't see or publish too slowly: crop burning as
it happens, industrial activity from emissions, monsoon rainfall by state,
heatwaves, agricultural drought.

Read this before the first `get_geo_data` call in a session.

## The tool

```
get_geo_data(dataset, region, start_date, end_date, aggregation="monthly")
```

Returns `{columns, results, units, region, organization, attribution,
caveats, notes?}` — a small time series, at most 50 rows. Results are cached
server-side, so repeating a call is cheap; the first call to an external
provider can take 5–30 s (rainfall occasionally longer).

## Datasets

| dataset | measures | economic reading | history | lag |
|---|---|---|---|---|
| `fires_viirs` | Active-fire detections + fire radiative power (NASA FIRMS, VIIRS 375 m) | Crop-residue burning (Punjab/Haryana Oct–Nov, Indonesian burning season), deforestation fires, flaring | 2012→ | ~3 h |
| `no2_tropomi` | Tropospheric NO₂ column, quality-filtered area mean (Sentinel-5P) | Industrial + power + traffic activity; recessions and lockdowns show up in weeks, not quarters | 2018→ | ~3 days |
| `ndvi_s2` | Vegetation index NDVI, cloud-masked area mean (Sentinel-2) | Crop condition ahead of harvest statistics — compare the same season across years (sowing → peak canopy → harvest is a normal arc, not a trend) | 2017→ | ~2–5 days |
| `precip_chirps` | Rainfall, gauge-calibrated satellite (CHIRPS 0.05°) | Monsoon adequacy, drought/flood risk → food prices, rural demand, hydro | 1981→ | ~2 days prelim |
| `temperature_power` | 2 m air temperature mean/max/min (NASA POWER, MERRA-2 0.5°) | Heatwaves → electricity demand, labour productivity, crop stress | 1981→ | ~3 days |
| `soil_moisture_power` | Root-zone soil wetness 0–1 (NASA POWER, MERRA-2) | Sowing conditions and agricultural drought ahead of production data | 1981→ | ~3 days |

## Regions

- Any country: `"IND"`, `"China"`, `"Indonesia"` (ISO3 or plain name).
- States/provinces for: **IND, CHN, IDN, VNM, THA, MYS, PHL, PAK, BGD, LKA,
  MMR, KHM, NPL, KOR, JPN, TWN, USA** — `"India/Punjab"`, `"CHN/Guangdong"`,
  `"USA/Texas"`. Misspellings and common variants resolve (a `notes` entry
  says what matched); if a name can't resolve, the error lists valid names.
- Anywhere else: `"bbox:west,south,east,north"` in degrees.

The response's `region.resolved` echoes what was actually used — repeat it in
your narrative so the reader knows the exact geography.

## Windows and the 50-row budget

At most 50 intervals per call (~4 years monthly, ~7 weeks daily). Patterns:

- **Seasonal YoY** (the common ask — "Punjab stubble burning this year vs
  last 5"): one call per season, e.g. `2021-10-01→2021-11-30`,
  `2022-10-01→2022-11-30`, … in parallel. Don't fetch whole years to compare
  two months.
- **Long trends**: split at the 50-month boundary (e.g. 2018–2021, 2022–2025)
  and stitch.
- **`fires_viirs` is additionally capped at 3 years per call** (the provider
  serves 5-day chunks); seasonal calls sidestep this entirely.
- Daily grain is for event windows (a flood week, a heatwave fortnight), not
  long ranges.

## Reading the results honestly

- **`no2_tropomi` and `ndvi_s2`: check `valid_obs_share` on every row.** It is
  the share of pixels with a valid, cloud-free retrieval. Below ~0.2 the mean
  rests on a handful of clear-sky views — say so if you use it. Fully clouded
  months (South Asian monsoon: typically Jun–Sep) are **omitted from results**
  and named in `notes`; never interpolate through them silently.
- `ndvi_s2` is strongly seasonal: month-over-month moves mix crop cycle with
  weather. The honest comparison is same-month (or same-season) across years —
  e.g. Punjab wheat peaks Jan–Feb (~0.65–0.70 NDVI); a weak peak vs prior
  years is the signal, not the Nov→Feb climb.
- `fires_viirs` counts overpass detections, not fires put out — cloud cover
  suppresses counts; compare like-for-like seasons, and prefer `total_frp_mw`
  when arguing intensity rather than frequency.
- `precip_chirps` recent days are preliminary and revised in the final
  monthly product (~3rd week of the following month).
- POWER datasets are 0.5° reanalysis — honest at state/country scale, blind to
  city microclimates. Very small or very large regions sample the centroid
  cell (a `notes` entry appears for large ones).
- `notes` can also report partially failed fetches ("may undercount — retry").
  Retry once before using such a result.

## Attribution

Every response carries an `attribution` string — put it in the chart/report
`sources`, exactly as given. The Copernicus one ("Contains modified Copernicus
Sentinel-5P data…") is a licence requirement, not a courtesy.

## What this tool is not

- No nighttime lights yet (no provider offers hosted aggregation; a
  precomputed series is planned — check the catalog before assuming).
- Not a mapping tool: results are regional aggregates, not rasters or tiles.
- Shipping/trade activity is NOT here — the `portwatch` SQL schema carries
  IMF PortWatch's satellite-AIS daily series (chokepoint transits, port calls,
  import/export estimates); see `references/schemas.md`.
- For anything already in the warehouse (official rainfall indices, IMD data,
  electricity output), prefer the curated series — satellite data complements
  statistics, it doesn't replace them.

## Worked example — "Is Punjab's stubble burning worse this year?"

1. Current season: `get_geo_data("fires_viirs", "India/Punjab",
   "2025-10-01", "2025-11-30")`.
2. Prior seasons (parallel calls): same window for 2021–2024.
3. Compare `fire_detections` totals and `total_frp_mw`; note the season peaks
   in early November — a mid-October read is premature.
4. Chart monthly bars per year; cite "NASA FIRMS, VIIRS 375m active fire
   detections (S-NPP)".
