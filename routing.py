"""Cost-surface routing helpers: terrain gradient and direction-dependent edge costs.

The cost of travelling along a street is a line integral along the street's curve gamma(s):

    cost = integral of  m( grad z . T ) ds

where z is the terrain elevation, T is the unit tangent of the street and grad z . T is the
directional derivative of z along the street (the signed grade: positive uphill, negative
downhill).  m(g) is the effort multiplier for a grade g.  Because the grade changes sign when
the direction is reversed, the cost depends on the direction of travel.

The module has no GUI or raster-library imports so that it can be tested on its own.
"""
import math

import numpy as np
from scipy import ndimage

# Effort multiplier m(g) = 1 + K_UP * max(g, 0) + K_DOWN * max(-g, 0)   (g = rise / run)
# Hand-chosen heuristic values: a 5 % climb costs 2.5x the flat effort, a 5 % descent 1.25x.
K_UP = 30.0
K_DOWN = 5.0
SMOOTH_SIGMA = 1.0   # Gaussian smoothing of the DEM in cells (the elevations are whole metres)
STEP_M = 10.0        # the integral is evaluated on pieces of at most this length (metres)

M_PER_DEG_LAT = 110574.0
M_PER_DEG_LON_EQ = 111320.0


def cell_size_m(dx, dy, lat):
    """Size of a DEM cell in metres (east-west, north-south) for cell sizes dx, dy in degrees."""
    return abs(dx) * M_PER_DEG_LON_EQ * math.cos(math.radians(lat)), abs(dy) * M_PER_DEG_LAT


def compute_gradient(elevation, dx, dy, y0, nodata=None, sigma=SMOOTH_SIGMA):
    """Gradient of the elevation surface in metres of rise per metre of run.

    Returns (gx, gy): the derivatives of z towards the east and towards the north, as arrays
    with the shape of the DEM.  Cells equal to `nodata` are filled with the nearest valid value
    first, and the DEM is smoothed with a Gaussian filter of `sigma` cells before differentiating.
    """
    z = np.asarray(elevation, dtype=float).copy()
    if nodata is not None:
        invalid = z == nodata
        if invalid.all():
            raise ValueError("DEM contains only nodata values")
        if invalid.any():
            idx = ndimage.distance_transform_edt(invalid, return_distances=False, return_indices=True)
            z = z[tuple(idx)]
    if sigma and sigma > 0:
        z = ndimage.gaussian_filter(z, sigma, mode="nearest")
    lat_mid = y0 + z.shape[0] * dy / 2.0
    cx, cy = cell_size_m(dx, dy, lat_mid)
    dz_drow, dz_dcol = np.gradient(z)      # rows increase to the south, columns to the east
    return dz_dcol / cx, -dz_drow / cy


def effort_multiplier(grade, k_up=K_UP, k_down=K_DOWN):
    """m(g) = 1 + k_up * max(g, 0) + k_down * max(-g, 0)."""
    g = np.asarray(grade, dtype=float)
    return 1.0 + k_up * np.maximum(g, 0.0) + k_down * np.maximum(-g, 0.0)


def _edge_polyline(G, u, v, data):
    """Longitude/latitude vertices of an edge, from its geometry if it has one, oriented u -> v."""
    p_u = (float(G.nodes[u]["x"]), float(G.nodes[u]["y"]))
    p_v = (float(G.nodes[v]["x"]), float(G.nodes[v]["y"]))
    geom = data.get("geometry")
    pts = None
    if geom is not None:
        if hasattr(geom, "coords"):                       # shapely LineString (OSMnx)
            pts = [(float(x), float(y)) for x, y in geom.coords]
        elif isinstance(geom, str) and "(" in geom:       # WKT string
            body = geom[geom.index("(") + 1: geom.rindex(")")]
            pts = [tuple(float(c) for c in pair.split()[:2]) for pair in body.split(",")]
    if not pts or len(pts) < 2:
        return np.array([p_u, p_v])
    pts = np.array(pts)
    if np.hypot(*(pts[0] - p_u)) > np.hypot(*(pts[-1] - p_u)):   # stored in the other direction
        pts = pts[::-1]
    return pts


def add_edge_costs(G, gx, gy, x0, y0, dx, dy, k_up=K_UP, k_down=K_DOWN, step_m=STEP_M):
    """Set on every edge of G:

    cost    = length * (average effort multiplier along the edge)
    ascent  = metres climbed along the edge   (integral of max(grade, 0) ds)
    descent = metres descended along the edge (integral of max(-grade, 0) ds)

    The directional derivative grade = grad z . T is evaluated by bilinear interpolation of the
    gradient field at the middle of every piece of the edge.  Returns the number of graph nodes
    that lie outside the DEM (the gradient is then taken from the nearest border cell).
    """
    h, w = gx.shape
    lat_mid = y0 + h * dy / 2.0
    mx = M_PER_DEG_LON_EQ * math.cos(math.radians(lat_mid))
    my = M_PER_DEG_LAT
    outside = set()

    def inside(lon, lat):
        return x0 <= lon <= x0 + w * dx and y0 + h * dy <= lat <= y0

    for u, v, data in G.edges(data=True):
        length = float(data.get("length", 1.0))
        poly = _edge_polyline(G, u, v, data)
        for n in (u, v):
            if not inside(float(G.nodes[n]["x"]), float(G.nodes[n]["y"])):
                outside.add(n)

        mids, lens, tx, ty = [], [], [], []
        for (lon1, lat1), (lon2, lat2) in zip(poly[:-1], poly[1:]):
            ex, ey = (lon2 - lon1) * mx, (lat2 - lat1) * my
            seg = math.hypot(ex, ey)
            if seg == 0:
                continue
            n_pieces = max(1, math.ceil(seg / step_m))
            for k in range(n_pieces):
                f = (k + 0.5) / n_pieces
                mids.append((lon1 + f * (lon2 - lon1), lat1 + f * (lat2 - lat1)))
                lens.append(seg / n_pieces)
                tx.append(ex / seg)
                ty.append(ey / seg)
        if not lens:
            data.update(cost=length, ascent=0.0, descent=0.0)
            continue
        mids = np.array(mids)
        cols = (mids[:, 0] - x0) / dx - 0.5            # cell centres are at +0.5
        rows = (mids[:, 1] - y0) / dy - 0.5
        coords = np.vstack([rows, cols])
        gxs = ndimage.map_coordinates(gx, coords, order=1, mode="nearest")
        gys = ndimage.map_coordinates(gy, coords, order=1, mode="nearest")
        lens = np.array(lens)
        grade = gxs * np.array(tx) + gys * np.array(ty)    # directional derivative along the street
        scale = length / lens.sum()                        # use the OSM length as the base length
        data["cost"] = float(np.sum(lens * effort_multiplier(grade, k_up, k_down)) * scale)
        data["ascent"] = float(np.sum(lens * np.maximum(grade, 0.0)) * scale)
        data["descent"] = float(np.sum(lens * np.maximum(-grade, 0.0)) * scale)
    return len(outside)
