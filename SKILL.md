---
name: area-elevation-capacity
description: Reservoir elevation-area-capacity (EAC) curves from a DEM (SRTM30 or any projected DEM), plus remote monitoring of reservoir storage and water level from satellite surface-water-area data (Global Water Watch). Use this whenever the user wants a reservoir's or tank's stage-area-storage / elevation-capacity table or curves, storage at FRL/MWL, a capacity table for routing or a dam-break study, to fill the "Reservoir Elevation-Area-Capacity Template", to run the QGIS "Reservoir Stage Calculator", or to estimate how much water a dam holds from its water-spread area over time, even if they only say "capacity curve", "area-capacity", "storage table" or "how full is the dam".
---

# Reservoir Elevation-Area-Capacity Curves

Two jobs, either or both:

1. **EAC curves**: for each water level, the flooded area and the stored volume, from a DEM of the
   reservoir basin clipped to its maximum flooded area.
2. **Monitoring**: turn a time series of satellite water-spread area (km²) into volume (MCM) and water
   level (m) by interpolating in the EAC table.

The method follows the manual in `01 Manual/` (QGIS for Hydrology – Reservoir Elevation-Area-Capacity
Curves & Reservoir Monitoring V1, A. de Jong, 2025); `references/method.md` condenses what you need from it.
Read that file before advising on DEM choice, polygon delineation, the Excel template or Global Water Watch.

## Files

| Path | Use |
|---|---|
| `scripts/delineate_reservoir.py` | Maximum flooded area polygon from DEM + seed point + dam/bund axis; `--spill` finds leaks |
| `scripts/eac_from_dem.py` | Headless EAC calculator (rasterio). Same numbers as the QGIS script |
| `scripts/monitor_volume.py` | Area time series → volume and level, same interpolation as the template's Calcs sheet |
| `02 Tools/Reservoir Stage Calculator V2.py` | The QGIS Python Console script, for users working in QGIS |
| `02 Tools/Reservoir Elevation-Area-Capacity Template V1.xlsx` | Excel template with curve, monitoring and annual charts |
| `03 Mirani Reservoir/` | Worked example: QGIS export (`01`) and completed template (`02`) |
| `04 Chembarambakkam Tank/` | Worked headless example: tank with a long bund, hidden bed, power-law fill (read its README) |
| `references/method.md` | DEM and datum caveats, polygon delineation in QGIS, template and GWW steps |

Setup: `pip install rasterio fiona shapely pyproj numpy scipy openpyxl matplotlib`.

## 1. Gather inputs

- **Reservoir**: name, dam location, and any known levels (sill, FRL, MWL, TBL) with their datum.
- **DEM**: a GeoTIFF from the user, or download one. Prefer **Copernicus GLO-30** (2011–15, better
  vertical accuracy) over SRTM (Feb 2000, integer metres, noisy in flat country); both are public on AWS
  (URLs in `references/method.md`). Mosaic enough tiles to cover every area that could flood plus the
  upstream valleys, and check that the result doesn't run into the DEM edge.
- **Maximum flooded area polygon** (gpkg/shp/geojson). This matters more than anything else: without
  it, every low cell in the DEM, including the valley downstream of the dam, counts as reservoir. Use the
  user's polygon if they have one; otherwise build it with `delineate_reservoir.py` (step 2a) or in QGIS
  (method.md §2). Never run on an unclipped DEM and report the result as the reservoir.
- **Levels**: minimum (default: DEM minimum), maximum (the contour used for the polygon, not the
  DEM's highest island), step (1 m is usual; 0.5 m for small tanks).
- For monitoring: the Global Water Watch CSV (`time`, `Surface Water Area (km2)`) or any date + km² table.

## 2a. Delineate the maximum flooded area (if no polygon)

```
python scripts/delineate_reservoir.py dem.tif --seed LON LAT --level TOP --barrier "lon,lat;lon,lat;..." --spill
python scripts/delineate_reservoir.py dem.tif --seed LON LAT --level TOP --barrier "..." --out area.geojson
```

- Seed: a point well inside the water. TOP: just above the crest or top of bund; the manual uses a
  contour 10–20 m above a dam crest, while for a tank the top of bund is enough.
- Barrier: the dam or bund axis. Trace it **on the DEM crest**: plot the DEM at native resolution with
  contours and follow the ridge. Lines drawn by eye from imagery sit beside the crest and leak around
  their ends. Burning it in matters wherever a 30 m DEM under-resolves the crest (Chembarambakkam's
  bund dips to 26.3 m in places).
- `--spill` reports the level at which the fill first escapes and where. If the spill point is at the
  end of the barrier, extend the barrier along the crest and rerun. If it is a natural saddle away from
  the dam, stop the curve just below it and report the saddle (it may be real, a cross bund, or a
  surface-model artefact). Plot the polygon over the DEM and look at it before using it.

## 2b. Compute the EAC table

```
python scripts/eac_from_dem.py reservoir_dem.tif --mask reservoir_area.gpkg \
    --min 47 --max 95 --step 1 --name "Mirani Reservoir" --out mirani_eac.xlsx --plot mirani_eac.png
```

- Area at level L = cells with z < L × cell area; capacity = Σ (L − z) × cell area over those cells.
  Columns: `BaseLevel_m, Pixels, Area_m2, Capacity_m3, Area_ha, Area_km2, Capacity_MCM, Area_acre,
  Capacity_acre_ft`, identical to the QGIS script's export so either can feed the template.
- A geographic DEM (lat/lon) is reprojected to its UTM zone at `--res` m (default 30). Areas measured
  in degrees are meaningless, which is why the QGIS script refuses such DEMs.
- Nodata left unset (99999, 0 outside the mask) corrupts the curve; the script drops implausible
  values and says so. Check its `note:` lines.

**DEM water surfaces.** Copernicus and SRTM flatten water bodies to a single level (find it as the
most common elevation inside the polygon), and nothing below it is measured. A reservoir that held
water when the DEM was flown therefore has a hidden bed: the curve shows zero storage up to that
level, then a jump in area. When a published capacity at FRL exists, fill the hidden part with a power
law from the bed or gauge zero, S(h) = S_w · ((h − GZ)/(h_w − GZ))^b, with S_w = S_pub(FRL) − S_DEM(FRL)
and b = A_w (h_w − GZ) / S_w, so the area is continuous at the water surface. Say clearly that this
part is forced to the published (often design, pre-sedimentation) capacity. `04 Chembarambakkam
Tank/build_chembarambakkam.py` is a worked example; adapt it rather than starting over.

**Sanity checks before reporting**: area and capacity rise monotonically; capacity ≈ Σ area × step;
the curve is smooth for large reservoirs (bumpy is normal when the reservoir is only a few hundred
cells); the area at the top level ≈ polygon area; a DEM bund/dam crest close to the known TBL
(a datum check); and where two DEMs disagree, say which you adopted and why. If a published capacity at FRL exists, compare and
state the difference; SRTM-based curves are planning-level.

## 3. Monitoring (optional)

```
python scripts/monitor_volume.py mirani_eac.xlsx "Surface Water Area (#88182).csv" \
    --start 2007-01-01 --name "Mirani Reservoir" --out mirani_monitoring.xlsx --plot mirani_monitoring.png
```

- The EAC input can be the step-2 output, the QGIS export, or a filled template workbook (reads `Data`).
- Areas outside the EAC range come back as "Area below/above Calibration range", as in the template.
- `Suspect spike` flags points that jump >25 % from their neighbours, usually cloud fooling the water
  classifier. Ask the user to check those dates in Global Water Watch imagery (dates may be one day
  off due to time zones) and rerun with `--drop YYYY-MM-DD ...`. Use `--start` to drop observations
  from before the reservoir first filled.
- The workbook has a `Monitoring` sheet and an `Annual` min/average/max volume sheet.

## 4. The Excel template (when the user wants it)

Do not fill the template with openpyxl: it drops the template's charts and pivot table on save. Give
the user our output plus these paste steps (details in method.md §4):

1. Copy the template, rename it to the reservoir; set the name on `Info` (it drives all chart titles).
2. `Data` sheet: paste `BaseLevel_m, Pixels, Area_m2, Capacity_m3` into *SRTM30 Elevation (m)* …
   *Capacity (m3)*; the other columns calculate.
3. `Info` → spillway table: x max = chart capacity max, y = spillway level in DEM datum.
4. Monitoring: paste `time` and `Surface Water Area (km2)` into `Monitoring`; copy the orange No /
   Date / Area columns and Paste Special → Values into `Calcs`; remove cloudy points; Data → Refresh
   All; paste values into `Export`.

## 5. Report back

Give a short summary, then the files:

- Table of area (km²) and capacity (MCM) at the key levels (sill, FRL, MWL if known, top level), plus
  the dead storage below the sill if relevant.
- The EAC chart PNG and workbook; for monitoring, latest volume / level and the annual table.
- The caveats that apply: DEM date (SRTM is Feb 2000, so it cannot see below the water of a reservoir
  filled before then), vertical datum (SRTM is EGM96; dam drawings use a local datum and gauge levels
  differ; Mirani's offset is about 0.4 m), and planning-level accuracy.

When the EAC feeds a hydrology / dam-break study (the `hydrology-dambreak` skill), hand over
elevation (m) vs storage (m³ or MCM) in that study's datum, and state the offset you applied.
