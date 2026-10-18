# Method notes (condensed from the QGIS manual)

Source: *QGIS for Hydrology – Reservoir Elevation-Area-Capacity Curves & Reservoir Monitoring V1*,
Andreas de Jong, July 2025 (`01 Manual/`). Videos: methodology https://youtu.be/lnesQRzeqcU,
monitoring with Global Water Monitor https://youtu.be/-0BGnorZgMg.

## 1. DEM and datum

- **SRTM30** (1 arc-second, ~30 m at the equator) was flown 11–22 February 2000. It describes the
  ground at that time and cannot see beneath water.
  - Dam built after Feb 2000: SRTM gives the full pre-impoundment valley, so the curve is complete.
  - Reservoir already filled in Feb 2000: only the part of the curve above that day's water level is
    valid. Merge it with curves from construction documents (see the Kakai Dam video,
    https://youtu.be/SU3csjbq5lA).
- SRTM comes in geographic WGS84; reproject to a projected CRS (UTM) at 30 m before measuring
  anything. `eac_from_dem.py` does this automatically.
- SRTM heights are relative to the **EGM96 geoid**. Current satellite altimetry uses EGM2008, GPS
  gives WGS84 ellipsoid heights, and dam drawings use a local datum, so none of these compare
  directly with SRTM levels. Orthometric height = ellipsoid height − geoid undulation. Standard GPS
  vertical error is about 3× its horizontal error.
- Public downloads with no login (1° tiles named by the lower-left corner):
  - Copernicus GLO-30 (preferred; EGM2008; water bodies flattened):
    `https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N12_00_E080_00_DEM/Copernicus_DSM_COG_10_N12_00_E080_00_DEM.tif`
  - SRTM 1″: `https://s3.amazonaws.com/elevation-tiles-prod/skadi/N25/N25E062.hgt.gz`
  - Also USGS EarthExplorer, OpenTopography, NASA Earthdata (SRTMGL1). Use whichever the network allows.
- Both are surface models: trees, buildings and road embankments show up as ground, which matters
  in flat, built-up country. A local survey or a
  finer DEM is better than SRTM whenever the user has one.

## 2. Polygon of the maximum flooded area (QGIS, manual §3.1–3.8)

1. Load Google Hybrid, the projected DEM, the dam site and its catchment.
2. *Raster › Extraction › Clip Raster by Extent* over everything that could flood, generously.
3. *Raster › Extraction › Contour*, 5 m interval.
4. Pick a contour **10–20 m above the dam crest** where the dam meets the hillside (Mirani: 95 m).
   Copy it to a scratch layer.
5. Edit: *Split Features* across the contour at the dam and delete the downstream part.
6. Turn on snapping, digitise the dam axis (and any ridge gaps) from vertex to vertex, then *Dissolve*.
7. *Vector › Geometry Tools › Lines to Polygons*.
8. Fix self-intersections ("bowties", slivers): *Buffer* +1 m (flat cap, mitre join), then *Buffer*
   −1 m, then *Delete holes*. Save as GeoPackage in UTM and in WGS84 (the WGS84 copy is the
   "cookie-cutter" for remote-sensing data).
9. *Raster › Extraction › Clip Raster by Mask Layer* with the polygon, and **set the nodata value to
   99999** (otherwise cells outside become 0 m and wreck the curve). Save as GeoTIFF.

With the polygon in hand, `eac_from_dem.py --mask polygon.gpkg` replaces steps 9 and 10.

## 3. Stage calculator (manual §3.10)

The QGIS script (`02 Tools/Reservoir Stage Calculator V2.py`): open it in *Plugins › Python Console
› Show Editor* and run it. Pick the clipped DEM. Minimum = DEM minimum. **Maximum = the contour used
for the polygon** (the DEM maximum is usually an island top). Increment 1 m. It runs
`native:rastersurfacevolume` (count below base level) per level, merges the results into
`Elevation_Area_Volume_<DEM>`, and you export that as XLSX. It refuses DEMs with no CRS or a
geographic CRS.

## 4. Excel template (manual §4, §5.4)

Sheets: `Info` (name, country, location, coordinates, purpose, status; `tbl_Spillway` for the dashed
spillway line), `Data` (`tbl_Data`), `Monitoring` (`tbl_Reservoir`), `Calcs` (`tbl_Monitoring`, six
charts), `Annual Chart` (pivot), `Export` (`tbl_Export`).

- `Data`: paste the first four QGIS columns (BaseLevel_m … Capacity_m3) into *SRTM30 Elevation (m)* …
  *Capacity (m3)*. Area km², MCM, acre and acre-ft calculate.
- Reservoir Curves chart: capacity on the primary x axis, area on the secondary, elevation on y. Set
  the capacity axis max and interval first (Mirani 0–3,500 by 500), then match the area gridlines.
  Set both y axes (Mirani 40–100 m) and number format 0 dp with a thousands separator.
- Spillway line: unless the spillway level is known *in SRTM datum*, estimate it from the monitoring
  record. The highest sustained water level is at or just above the spillway; floods can go several
  metres above it. Mirani: 76 m, about 400 MCM and 60 km².
- `Calcs` formulas: volume and elevation are linear interpolation in `tbl_Data` on Area (km²),
  using `MATCH(area, tbl_Data[Area (km2)], 1)` for the row below. Areas outside the table give
  "Area below/above Calibration range". `monitor_volume.py` reproduces this exactly (verified against
  the Mirani workbook).

## 5. Satellite water-area monitoring (manual §5)

- Optical: Landsat 5/7/8 (30 m, since 1982), Sentinel-2 (10–20 m, 5-day revisit), MODIS (250–500 m,
  daily). All are blind under cloud.
- SAR: Sentinel-1 (5–20 m, 6–12 days) sees through cloud.
- **Global Water Watch** (Deltares / WRI / WWF): https://www.globalwaterwatch.earth/map → Reservoirs
  → click the reservoir → *DOWNLOAD .CSV(s)*. The file is `Surface Water Area (#<id>).csv` with
  `time` (e.g. `2006-09-06T06:04:00`) and `Surface Water Area (km2)`. Mirani is #88182.
- QC: delete observations from before the first filling. For each spike, open that date's image in
  GWW (dates may be one day off) and delete the point if it is cloudy or blurred. Clouds usually make
  the area look too large.
