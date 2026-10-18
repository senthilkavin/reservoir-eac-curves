"""Reservoir elevation-area-capacity (EAC) table from a DEM, without QGIS.

Headless equivalent of `02 Tools/Reservoir Stage Calculator V2.py`: for each water level it counts the
DEM cells below the level (area) and sums (level - z) * cell area (capacity), the same as QGIS
`native:rastersurfacevolume` with METHOD 1 ("count only below base level").

Usage:
  python eac_from_dem.py DEM.tif --out eac.xlsx [--mask reservoir.gpkg] [--min 47 --max 95 --step 1]
                         [--plot eac.png] [--name "Mirani Reservoir"] [--res 30] [--crs EPSG:32641]

A geographic DEM (lat/lon, e.g. raw SRTM) is reprojected to the UTM zone of its centre at --res metres
(bilinear) before any area is measured; pass --crs to choose the projected CRS yourself.
"""
import argparse
import sys

import numpy as np
import rasterio
from rasterio.mask import mask as rio_mask
from rasterio.warp import calculate_default_transform, reproject, Resampling

M2_PER_ACRE = 4046.8564224
M3_PER_ACRE_FT = 1233.4818375475
COLUMNS = ["BaseLevel_m", "Pixels", "Area_m2", "Capacity_m3", "Area_ha", "Area_km2",
           "Capacity_MCM", "Area_acre", "Capacity_acre_ft"]


def utm_crs_for(lon, lat):
    zone = int((lon + 180) // 6) + 1
    return f"EPSG:{(32600 if lat >= 0 else 32700) + zone}"


def to_projected(src, dst_crs, res):
    """Reproject an open dataset to dst_crs; returns an in-memory dataset."""
    transform, width, height = calculate_default_transform(
        src.crs, dst_crs, src.width, src.height, *src.bounds, resolution=res)
    nodata = src.nodata if src.nodata is not None else -32768.0
    profile = src.profile.copy()
    profile.update(crs=dst_crs, transform=transform, width=width, height=height,
                   nodata=nodata, dtype="float32", driver="GTiff")
    memfile = rasterio.io.MemoryFile()
    dst = memfile.open(**profile)
    reproject(source=rasterio.band(src, 1), destination=rasterio.band(dst, 1),
              src_nodata=src.nodata, dst_nodata=nodata, resampling=Resampling.bilinear)
    return dst


def read_mask_shapes(path, dst_crs):
    import fiona
    import shapely
    from shapely.geometry import shape, mapping
    from pyproj import Transformer
    with fiona.open(path) as src:
        src_crs = src.crs_wkt or src.crs
        geoms = [shape(f["geometry"]) for f in src if f["geometry"]]
    if not geoms:
        sys.exit(f"No polygons in {path}")
    if src_crs:
        t = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
        geoms = [shapely.transform(g, lambda c: np.column_stack(t.transform(c[:, 0], c[:, 1])))
                 for g in geoms]
    return [mapping(g.buffer(0)) for g in geoms]


def load_dem(path, mask_path=None, crs=None, res=30.0):
    """Return (valid elevations 1-D float64, cell area m2, crs string, note list)."""
    notes = []
    src = rasterio.open(path)
    if src.crs is None:
        sys.exit(f"{path} has no CRS. Assign one (e.g. in QGIS) before measuring areas.")
    if src.crs.is_geographic or crs:
        if crs is None:
            b = src.bounds
            crs = utm_crs_for((b.left + b.right) / 2, (b.bottom + b.top) / 2)
        notes.append(f"Reprojected {src.crs.to_string()} -> {crs} at {res} m (bilinear)")
        src = to_projected(src, crs, res)
    if mask_path:
        shapes = read_mask_shapes(mask_path, src.crs)
        nodata = src.nodata if src.nodata is not None else -32768.0
        data, transform = rio_mask(src, shapes, crop=True, nodata=nodata, filled=True)
        z = data[0].astype("float64")
        valid = z != nodata
        cell_area = abs(transform.a * transform.e - transform.b * transform.d)
        notes.append(f"Clipped to {mask_path}")
    else:
        band = src.read(1, masked=True)
        z = band.filled(np.nan).astype("float64")
        valid = ~band.mask if np.ndim(band.mask) else np.ones(z.shape, bool)
        t = src.transform
        cell_area = abs(t.a * t.e - t.b * t.d)
    z = z[valid & np.isfinite(z)]
    # Values far outside any terrain are almost always an unset nodata (e.g. 99999 or -9999).
    bad = (z < -500) | (z > 9000)
    if bad.any():
        notes.append(f"Ignored {int(bad.sum())} cells with implausible elevations (unset nodata?)")
        z = z[~bad]
    if z.size == 0:
        sys.exit("DEM has no valid cells inside the mask.")
    return z, cell_area, src.crs.to_string(), notes


def eac_table(z, cell_area, zmin, zmax, step):
    """Rows of COLUMNS for levels zmin..zmax (QGIS script's level list)."""
    zs = np.sort(z)
    csum = np.concatenate([[0.0], np.cumsum(zs)])
    n_levels = int((zmax - zmin) / step + 1e-9) + 1
    rows = []
    for i in range(n_levels):
        level = round(zmin + i * step, 6)
        n = int(np.searchsorted(zs, level, side="left"))  # cells strictly below the level
        area = n * cell_area
        vol = (n * level - csum[n]) * cell_area
        rows.append([level, n, area, vol, area / 1e4, area / 1e6, vol / 1e6,
                     area / M2_PER_ACRE, vol / M3_PER_ACRE_FT])
    return rows


def write_table(rows, out, meta):
    if out.lower().endswith(".csv"):
        import csv
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLUMNS)
            w.writerows(rows)
        return
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "EAC"
    ws.append(COLUMNS)
    for r in rows:
        ws.append(r)
    ws.freeze_panes = "A2"
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 16
    info = wb.create_sheet("Info")
    for k, v in meta.items():
        info.append([k, v])
    info.column_dimensions["A"].width = 18
    info.column_dimensions["B"].width = 70
    wb.save(out)


def plot_eac(rows, png, title):
    """Classic EAC chart: elevation on y, capacity on the bottom axis, area on a reversed top axis."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    a = np.array(rows, dtype=float)
    elev, area_km2, cap_mcm = a[:, 0], a[:, 5], a[:, 6]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(cap_mcm, elev, color="#1f5aa6", lw=2, label="Capacity (MCM)")
    ax.set_xlabel("Capacity (MCM)", color="#1f5aa6")
    ax.set_ylabel("Water level (m)")
    ax.grid(True, alpha=0.3)
    top = ax.twiny()
    top.plot(area_km2, elev, color="#c8551b", lw=2, label="Area (km²)")
    top.set_xlim(max(area_km2.max(), 1e-9) * 1.05, 0)
    top.set_xlabel("Area (km²)", color="#c8551b")
    ax.set_xlim(0, max(cap_mcm.max(), 1e-9) * 1.05)
    fig.suptitle(f"{title} – Elevation-Area-Capacity Curves")
    fig.tight_layout()
    fig.savefig(png, dpi=150)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dem")
    p.add_argument("--out", required=True, help=".xlsx or .csv")
    p.add_argument("--mask", help="reservoir (maximum flooded area) polygon: gpkg/shp/geojson")
    p.add_argument("--min", type=float, help="lowest level (default: DEM minimum, floored)")
    p.add_argument("--max", type=float, help="highest level (default: DEM maximum)")
    p.add_argument("--step", type=float, default=1.0)
    p.add_argument("--crs", help="projected CRS to reproject to (default: UTM if DEM is geographic)")
    p.add_argument("--res", type=float, default=30.0, help="cell size in m when reprojecting")
    p.add_argument("--plot", help="PNG path for the EAC chart")
    p.add_argument("--name", default="Reservoir")
    a = p.parse_args()

    if a.step <= 0:
        sys.exit("--step must be positive")
    z, cell_area, crs, notes = load_dem(a.dem, a.mask, a.crs, a.res)
    zmin = a.min if a.min is not None else float(np.floor(z.min()))
    zmax = a.max if a.max is not None else float(z.max())
    if zmin >= zmax:
        sys.exit("--min must be below --max")
    rows = eac_table(z, cell_area, zmin, zmax, a.step)
    meta = {"Reservoir": a.name, "DEM": a.dem, "Mask": a.mask or "(none: whole DEM)", "CRS": crs,
            "Cell area (m2)": cell_area, "Valid cells": int(z.size),
            "DEM min / max (m)": f"{z.min():.2f} / {z.max():.2f}",
            "Levels": f"{zmin} to {zmax} step {a.step}", "Notes": "; ".join(notes) or "-"}
    write_table(rows, a.out, meta)
    if a.plot:
        plot_eac(rows, a.plot, a.name)
    for n in notes:
        print("note:", n)
    last = rows[-1]
    print(f"{len(rows)} levels, cell {cell_area:.1f} m2, CRS {crs}")
    print(f"At {last[0]} m: area {last[5]:.3f} km2, capacity {last[6]:.3f} MCM -> {a.out}")


if __name__ == "__main__":
    main()
