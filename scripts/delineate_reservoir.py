"""Maximum flooded area polygon of a reservoir from a DEM, without QGIS.

Headless version of manual sections 3.3-3.8 (contour above the crest + dam axis -> polygon): every DEM
cell below --level that is connected to --seed (a point in the reservoir) is flooded, and the dam or
tank bund axis given by --barrier is burnt into the DEM as a wall so the fill cannot leak past it
where a 30 m DEM under-resolves the crest. Holes (islands) are removed, as in the manual.

Usage:
  python delineate_reservoir.py DEM.tif --seed 80.05 13.01 --level 29 \
      --barrier "80.0707,13.0395;80.0815,13.0005;80.0745,12.9975" --out reservoir_area.geojson

--spill reports the level at which the fill first escapes and where (a gap at the end of the bund line,
or a natural saddle); run it after each barrier edit until the basin holds to the level you need.

--barrier takes "lon,lat;lon,lat;..." (WGS84) or a GeoJSON/GPKG file of line(s). Several lines may be
separated with "|". Output is a WGS84 GeoJSON polygon, to pass to eac_from_dem.py --mask.
"""
import argparse
import json
import os
import sys

import numpy as np
import rasterio
from rasterio import features
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eac_from_dem import to_projected, utm_crs_for  # noqa: E402


def barrier_lines(arg):
    from shapely.geometry import LineString, shape
    if os.path.exists(arg):
        import fiona
        with fiona.open(arg) as src:
            if src.crs and src.crs.to_epsg() not in (None, 4326):
                sys.exit("Barrier file must be in WGS84 (EPSG:4326)")
            return [shape(f["geometry"]) for f in src]
    lines = []
    for part in arg.split("|"):
        pts = [tuple(float(v) for v in p.split(",")) for p in part.split(";") if p.strip()]
        if len(pts) < 2:
            sys.exit(f"Barrier needs at least two points: {part}")
        lines.append(LineString(pts))
    return lines


def flood(z, r, c, level):
    labels, _ = ndimage.label(z < level)
    return labels == labels[r, c]


BORDER = None  # cells on the array frame or next to nodata: reaching them means the fill escaped


def touches_edge(m):
    return bool((m & BORDER).any())


def report_spill(z, r, c, top, transform, to_wgs):
    """Bisect for the level where the fill from the seed first reaches the DEM edge (leaks past the
    dam or over a saddle into the next valley), then name the lowest cells where it breaks out."""
    lo = float(z[r, c])
    if not touches_edge(flood(z, r, c, top)):
        print(f"No spill up to {top} m: the basin is closed at that level.")
        return
    hi = top
    while hi - lo > 0.01:
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if touches_edge(flood(z, r, c, mid)) else (mid, hi)
    lake = flood(z, r, c, lo)
    rest, _ = ndimage.label((z < hi) & ~lake)
    outside = np.isin(rest, np.unique(rest[BORDER & (rest > 0)]))  # regions that reach the edge
    contact = outside & ndimage.binary_dilation(lake)
    rr, cc = np.nonzero(contact)
    order = np.argsort(z[rr, cc])[:3]
    xs, ys = rasterio.transform.xy(transform, rr[order], cc[order])
    lon, lat = to_wgs.transform(np.array(xs), np.array(ys))
    cell = abs(transform.a * transform.e)
    print(f"Basin closed up to {lo:.2f} m ({lake.sum() * cell / 1e6:.2f} km2); spills at {hi:.2f} m near "
          + ", ".join(f"({x:.4f}, {y:.4f}) z={v:.2f}" for x, y, v in zip(lon, lat, z[rr[order], cc[order]])))
    print("Extend --barrier there if it is the dam/bund (follow its crest), or cap the curve below that level "
          "if it is a natural saddle.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dem")
    p.add_argument("--seed", nargs=2, type=float, required=True, metavar=("LON", "LAT"))
    p.add_argument("--level", type=float, required=True, help="top level, at or just above the crest/TBL")
    p.add_argument("--barrier", help='dam/bund axis: "lon,lat;lon,lat;..." or a line file (WGS84)')
    p.add_argument("--out", help="output polygon (.geojson, WGS84)")
    p.add_argument("--spill", action="store_true",
                   help="find the lowest level at which the fill escapes to the DEM edge, and where")
    p.add_argument("--res", type=float, default=30.0)
    a = p.parse_args()

    import shapely
    from shapely.geometry import shape, mapping, Point
    from shapely.ops import unary_union
    from pyproj import Transformer

    src = rasterio.open(a.dem)
    if src.crs is None:
        sys.exit("DEM has no CRS")
    if src.crs.is_geographic:
        b = src.bounds
        src = to_projected(src, utm_crs_for((b.left + b.right) / 2, (b.bottom + b.top) / 2), a.res)
    band = src.read(1, masked=True)
    z = band.filled(np.nan).astype("float64")
    z[(z < -500) | (z > 9000)] = np.nan
    global BORDER
    BORDER = ndimage.binary_dilation(np.isnan(z))
    BORDER[0, :] = BORDER[-1, :] = BORDER[:, 0] = BORDER[:, -1] = True
    to_dem = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
    to_wgs = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)

    if a.barrier:
        lines = [shapely.transform(l, lambda c: np.column_stack(to_dem.transform(c[:, 0], c[:, 1])))
                 for l in barrier_lines(a.barrier)]
        wall = features.rasterize([(l, 1) for l in lines], out_shape=z.shape, transform=src.transform,
                                  all_touched=True, dtype="uint8").astype(bool)
        z[wall] = np.inf

    sx, sy = to_dem.transform(*a.seed)
    r, c = rasterio.transform.rowcol(src.transform, sx, sy)
    if not (0 <= r < z.shape[0] and 0 <= c < z.shape[1]) or not z[r, c] < a.level:
        sys.exit(f"Seed is outside the DEM or not below {a.level} m (DEM there: {z[r, c] if 0 <= r < z.shape[0] and 0 <= c < z.shape[1] else 'n/a'})")

    if a.spill:
        report_spill(z, r, c, a.level, src.transform, to_wgs)
        if not a.out:
            return
    if not a.out:
        sys.exit("--out is required unless --spill is given")
    labels, _ = ndimage.label(z < a.level)  # 4-connected: no diagonal leaks through the wall
    flooded = labels == labels[r, c]
    flooded = ndimage.binary_fill_holes(flooded)
    edge = touches_edge(flooded)

    cell = abs(src.transform.a * src.transform.e)
    polys = [shape(g) for g, v in features.shapes(flooded.astype("uint8"), mask=flooded,
                                                    transform=src.transform) if v == 1]
    poly = unary_union(polys)
    poly_wgs = shapely.transform(poly, lambda c: np.column_stack(to_wgs.transform(c[:, 0], c[:, 1])))
    with open(a.out, "w") as f:
        json.dump({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {
            "level_m": a.level, "area_km2": round(flooded.sum() * cell / 1e6, 4), "dem": os.path.basename(a.dem)},
            "geometry": mapping(poly_wgs)}]}, f)
    print(f"Flooded area at {a.level} m: {flooded.sum() * cell / 1e6:.3f} km2 ({int(flooded.sum())} cells) -> {a.out}")
    if edge:
        print("WARNING: the flooded area reaches the DEM edge. Either the DEM is too small or the fill "
              "leaked past the dam (extend the barrier); check a plot before using it.")


if __name__ == "__main__":
    main()
