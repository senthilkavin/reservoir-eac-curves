# Reservoir Elevation-Area-Capacity Curves

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

## Running the stage calculator

1. Load the reservoir DEM in QGIS. It must have a **projected CRS** (e.g. UTM, metres); the script
   stops on a geographic or undefined CRS.
2. Open *Plugins → Python Console → Show Editor*, open `Reservoir Stage Calculator V2.py` and run it.
3. Pick the DEM, then confirm the elevation range and interval it proposes.
4. The result is a layer `Elevation_Area_Volume_<DEM name>` with area (m², ha, km², acre) and capacity
   (m³, MCM, acre-ft) for each elevation. Export it to Excel and paste it into the template's Data sheet.
