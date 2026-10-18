# Reservoir Elevation-Area-Capacity Curves

Also packaged as the Claude skill **`area-elevation-capacity`** (`SKILL.md`): Claude computes EAC
tables headlessly from a DEM and converts satellite water-area records into storage and level.

Builds a reservoir's elevation-area-capacity (EAC) table from a DEM in QGIS, then turns it into curves
and storage monitoring in an Excel template. Mirani Reservoir is included as a worked example.

## Layout

| Path | Contents |
|---|---|
| `01 Manual/QGIS Reservoir Curves & Monitoring V1.pdf` | Step-by-step manual: QGIS workflow and Excel template use |
| `02 Tools/Reservoir Stage Calculator V2.py` | QGIS Python Console script: area and volume at each elevation interval from a DEM |
| `02 Tools/Reservoir Elevation-Area-Capacity Template V1.xlsx` | Blank template (sheets: Info, Data, Monitoring, Calcs, Annual Chart, Export) |
| `03 Mirani Reservoir/01 Mirani Reservoir Data.xlsx` | Elevation-area-volume table exported from QGIS for Mirani |
| `03 Mirani Reservoir/02 Mirani Elevation-Area-Capacity.xlsx` | Completed template for Mirani, with monitoring data |
| `SKILL.md` | Claude skill definition (`/area-elevation-capacity`) |
| `scripts/delineate_reservoir.py` | Maximum flooded area polygon from a DEM, seed point and dam/bund axis |
| `04 Chembarambakkam Tank/` | Headless worked example (Copernicus DEM, bund barrier, hidden-bed fill) |
| `05 Krishnagiri Dam/` | Headless example for a gravity dam: dam axis burnt in, hidden bed, curve checked against WRD gauge-storage readings |
| `scripts/eac_from_dem.py` | Headless EAC calculator (no QGIS): DEM + reservoir polygon → table and chart |
| `scripts/monitor_volume.py` | Water-area time series (e.g. Global Water Watch CSV) → volume and level |
| `references/method.md` | Condensed method notes from the manual |

## Running the stage calculator

1. Load the reservoir DEM in QGIS. It must have a **projected CRS** (e.g. UTM, metres); the script
   stops on a geographic or undefined CRS.
2. Open *Plugins → Python Console → Show Editor*, open `Reservoir Stage Calculator V2.py` and run it.
3. Pick the DEM, then confirm the elevation range and interval it proposes.
4. The result is a layer `Elevation_Area_Volume_<DEM name>` with area (m², ha, km², acre) and capacity
   (m³, MCM, acre-ft) for each elevation. Export it to Excel and paste it into the template's Data sheet.

## Without QGIS

```
pip install rasterio fiona shapely pyproj numpy scipy openpyxl matplotlib
python scripts/eac_from_dem.py reservoir_dem.tif --mask reservoir_area.gpkg --min 47 --max 95 \
    --out eac.xlsx --plot eac.png --name "Mirani Reservoir"
python scripts/monitor_volume.py eac.xlsx "Surface Water Area (#88182).csv" --start 2007-01-01 \
    --out monitoring.xlsx --plot monitoring.png --name "Mirani Reservoir"
```

`eac_from_dem.py` matches QGIS `native:rastersurfacevolume` (count below base level), reprojects
geographic DEMs to UTM, and clips to the reservoir polygon. `monitor_volume.py` uses the template's
Calcs-sheet interpolation; on the Mirani workbook it reproduces the Export sheet exactly.

## Credits

The manual, QGIS script and Excel template are from *QGIS for Hydrology – Reservoir
Elevation-Area-Capacity Curves & Reservoir Monitoring V1* by Andreas de Jong (Geosearch, July 2025).
