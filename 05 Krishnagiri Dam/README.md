# Krishnagiri Dam (KRP): elevation-area-capacity (18 Oct 2026, planning level)

Thenpennaiyar (Ponnaiyar), Krishnagiri district; dam at 12°28'30.96"N, 78°11'7.18"E.

| File | Contents |
|---|---|
| `Krishnagiri_EAC.xlsx` | `EAC adopted` (0.5 m steps + key levels, m and WRD gauge ft, km², MCM, Mcft, 1958 variant), `Key levels`, `WRD bulletin check`, `Copernicus raw`, `SRTM raw`, `Notes` |
| `Krishnagiri_EAC.png` | Curves with the WRD gauge (ft) axis, bulletin readings, 1958 variant and SRTM |
| `Krishnagiri_EAC_0.05m.csv` | Adopted curve at 0.05 m (`elevation_m, area_m2, storage_m3`) for level-pool routing |
| `krishnagiri_area_490m.geojson` | Maximum flooded area polygon at 490 m (WGS84), 17.9 km² |
| `dam_axis.txt` | Dam axis used as the barrier (lon,lat;…), traced on the Copernicus crest, abutment to abutment |
| `build_krishnagiri.py` | Rebuilds the workbook, CSV and chart from the DEMs |

## Key levels

| Level | m | Gauge ft | Area km² | Capacity MCM | Mcft | 1958 variant MCM |
|---|---|---|---|---|---|---|
| Gauge zero (FRL − 52 ft) | 467.26 | 0 | 0 | 0 | 0 | 0 |
| Spillway crest (FRL − 6.10 m gate) | 477.01 | 32.0 | 2.99 | 7.48 | 264 | 24.01 |
| Copernicus water surface | 480.50 | 43.4 | 7.23 | 24.61 | 869 | 45.63 |
| **FRL** | 483.11 | 52.0 | 10.28 | 47.18 | 1,666 | 68.20 |
| **MWL** | 484.63 | 57.0 | 11.89 | 64.11 | 2,264 | 85.13 |
| Top of curve | 490.00 | 74.6 | 17.58 | 141.67 | 5,003 | 162.69 |

## Check against the WRD bulletin

| Date | Gauge ft | WRD Mcft | Curve Mcft | Diff |
|---|---|---|---|---|
| 01 Sep 2026 | 46.85 | 1,129 | 1,154 | +2.3 % |
| 18 Oct 2026 | 50.00 | 1,442 | 1,453 | +0.7 % |
| 04 Oct 2026 | 50.20 | 1,463 | 1,473 | +0.7 % |
| 07 Oct 2026 | 50.35 | 1,479 | 1,489 | +0.7 % |
| Full | 52.00 | 1,666 | 1,666 | 0 (forced) |

All the readings lie above the DEM water surface, so the part of the curve between 46.85 and 52 ft is
measured by the DEM independently of the published table. It matches the department's table to within
2.3 %. Storage increments between readings fit best at a DEM datum offset of +0.3 m, so no offset is applied.

## How it was made

1. DEMs: Copernicus GLO-30 (2011–15) and SRTM 1″ (2000), public AWS tile N12E078, clipped to
   78.06–78.30 E, 12.40–12.62 N and reprojected to UTM 44N at 30 m.
2. Polygon: `delineate_reservoir.py cop.tif --seed 78.17 12.49 --level 490 --barrier "$(cat dam_axis.txt)"`.
   The 30 m DEM under-resolves the masonry dam (crest 482–486 m in the DEM), so the axis is burnt in.
   Without the abutment extensions the fill leaks round the left (south-west) end at 492.3 m. With them
   the basin holds to 501.0 m, then spills over a natural saddle near 12.522 N, 78.199 E.
3. Copernicus flattens the lake at 480.5 m (7.23 km²) and cannot see below it. The storage below is a
   power law from gauge zero, S = 24.61 MCM × ((h − 467.26)/13.24)^3.89. It is sized so that S(FRL)
   equals the WRD full capacity of 1,666 Mcft. The high exponent means a flat, silted bed.
4. The 1958 variant forces S(FRL) to the original gross storage of 68.2 MCM (2,408 Mcft), with an
   exponent of 2.10. Use it as the upper bound for a dam-break storage.
5. SRTM flattens the lake at 483 m and reads about 1.7 m higher than Copernicus on land. It is shown only
   for comparison.

## Sources and caveats

- FRL 483.11 m, MWL 484.63 m, 68.2 MCM gross and 8 gates of 12.19 × 6.10 m come from Wikipedia and an
  IJIRSET 2019 case study. The full depth of 52 ft and 1,666 Mcft come from the WRD/TNAU bulletin. The
  Sep–Oct 2026 readings are from Oneindia's daily dam levels.
- Derived, not published: gauge zero (FRL − 52 ft) and spillway crest (FRL − gate height). The TBL was
  not found. Confirm all three from the dam drawings.
- One source gives a water spread of 12.32 km² at FRL; the DEM gives 10.28 km² at FRL and 11.89 km² at MWL.
- Below 480.5 m (43.4 ft) the curve is a fit, not a measurement: dead storage and the sluice-level storage
  need a bathymetric survey.
- Copernicus is a surface model (EGM2008). Trees and embankments in the flood fringe read as ground.
