# Chembarambakkam Tank: elevation-area-capacity (18 Oct 2026, planning level)

| File | Contents |
|---|---|
| `Chembarambakkam_EAC.xlsx` | `EAC adopted` (0.25 m steps + key levels, m/ft, km², MCM, Mcft), `Key levels`, `Copernicus raw`, `SRTM raw`, `Notes` |
| `Chembarambakkam_EAC.png` | Curves, compared with the hydrology-dambreak study's assumed curve and SRTM |
| `chembarambakkam_area_28.5m.geojson` | Maximum flooded area polygon at 28.5 m (WGS84), 31.4 km² |
| `bund_axis.txt` | Bund axis used as the barrier (lon,lat;…), traced on the Copernicus crest |
| `build_chembarambakkam.py` | Rebuilds the workbook and chart from the DEMs |

## Key levels

| Level | m | Area km² | Capacity MCM | Mcft | Study assumed curve, MCM |
|---|---|---|---|---|---|
| Gauge zero | 18.71 | 0 | 0 | 0 | 0 |
| Copernicus water surface | 21.00 | 14.49 | 16.54 | 584 | 20.06 |
| Regulator sill | 23.03 | 15.52 | 47.00 | 1,660 | 49.09 |
| **FRL** | 26.03 | 22.45 | 103.21 | 3,645 | 103.23 |
| **MWL** | 26.94 | 25.20 | 124.93 | 4,412 | 122.33 |
| Top of closed basin | 28.50 | 31.21 | 168.66 | 5,956 | 159.17 |

## How it was made

1. DEMs: Copernicus GLO-30 (2011–15) and SRTM 1″ (2000), public AWS tiles N12/N13 × E079/E080,
   mosaicked to 79.85–80.15 E, 12.90–13.12 N and reprojected to UTM 44N at 30 m.
2. Polygon: `delineate_reservoir.py --seed 80.05 13.01 --level 28.5 --barrier "$(cat bund_axis.txt)"`.
   The first bund line (drawn by eye) leaked at 24.19 m round its south-west end. Retraced on the DEM
   crest, the basin holds to 28.60 m, then spills over a low point at 13.059 N, 80.053 E (north of
   the lake), so the curve stops at 28.5 m.
3. Copernicus flattens the lake at 21.0 m (14.49 km²) and cannot see below it. The storage below is
   a power law from gauge zero, S = 16.54 MCM × ((h − 18.71)/2.29)^2.00. It is sized so that
   S(FRL) equals the published 3,645 Mcft; the exponent then matches the 14.49 km² surface at 21.0 m.
4. SRTM flattens the lake at 19 m, has artefacts down to −1.9 m, and measures more storage above
   19 m (120.6 MCM at FRL) than the published total, so it is shown only for comparison.

## Caveats

- Datum: Copernicus heights are EGM2008, WRD levels GTS/MSL. The DEM bund crest (27.2–28.9 m) is
  consistent with TBL 28.77 m, but a ±1 m offset has not been ruled out.
- The adopted curve is forced through the design capacity at FRL. Sedimentation has reportedly
  reduced the live capacity, so a bathymetric survey should replace the part below 21.0 m.
- The DEM curve above FRL (26.03 → 28.5 m) is measured independently of the published figures. It
  gives 2–6 % more storage than the study's assumed curve, so the dam-break study can adopt it.
- TBL (28.77 m) lies above the DEM's spill level. Check the 13.059 N, 80.053 E saddle on the ground:
  a real saddle, a cross bund, or a surface-model artefact (Copernicus is a surface model, so
  roads and buildings appear as ground).
