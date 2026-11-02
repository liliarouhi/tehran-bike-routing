"""Compare the shortest route (by length) with the cost-surface route on the sample data.

Prints summary statistics for random origin/destination pairs and saves an example figure
to docs/example_route.png.  Only needs numpy, networkx, matplotlib and Pillow.

Run from the project root:  python scripts/compare_routes.py
"""
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from routing import add_edge_costs, compute_gradient  # noqa: E402

matplotlib.use("Agg")

# --- load the sample DEM (GeoTIFF tags: 33550 = cell size, 33922 = top-left corner) ---
img = Image.open(ROOT / "sample_data" / "tehran_dem_small.tif")
tags = img.tag_v2
dx, dy = tags[33550][0], -tags[33550][1]
x0, y0 = tags[33922][3], tags[33922][4]
nodata = float(tags[42113]) if 42113 in tags else None
gx, gy = compute_gradient(np.array(img).astype(float), dx, dy, y0, nodata)

# --- load the graph and add costs ---
G = nx.MultiDiGraph(nx.read_graphml(ROOT / "sample_data" / "small_tehran.graphml"))
add_edge_costs(G, gx, gy, x0, y0, dx, dy)
for _, _, d in G.edges(data=True):
    d["len"] = float(d["length"])

nodes = list(G.nodes)
xy = {n: (float(G.nodes[n]["x"]), float(G.nodes[n]["y"])) for n in nodes}


def route_stats(route, weight):
    """Length (m) and total climb (m) of a route; parallel edges: the one the router used."""
    length = ascent = 0.0
    for u, v in zip(route[:-1], route[1:]):
        e = min(G[u][v].values(), key=lambda d: d[weight])
        length += e["len"]
        ascent += e["ascent"]
    return length, ascent


rng = np.random.default_rng(0)
pairs, different, best = 0, 0, None
longer, climb_change = [], []
for _ in range(300):
    a, b = (nodes[i] for i in rng.choice(len(nodes), 2, replace=False))
    if not nx.has_path(G, a, b):
        continue
    pairs += 1
    r_short = nx.shortest_path(G, a, b, weight="len")
    r_cost = nx.shortest_path(G, a, b, weight="cost")
    if r_short == r_cost:
        continue
    different += 1
    (l1, c1), (l2, c2) = route_stats(r_short, "len"), route_stats(r_cost, "cost")
    longer.append(100 * (l2 / l1 - 1))
    if c1 > 0:
        climb_change.append(100 * (c2 / c1 - 1))
    dist = np.hypot(xy[a][0] - xy[b][0], xy[a][1] - xy[b][1])
    score = dist * (c1 - c2)  # prefer a long pair with a clear reduction of the climb
    if best is None or score > best[0]:
        best = (score, a, b, r_short, r_cost, l1, c1, l2, c2)

print(f"{pairs} random reachable pairs, {different} get a different route with the cost surface")
print(f"Median over those routes: {np.median(longer):+.1f}% length, {np.median(climb_change):+.1f}% total climb")
_, a, b, r_short, r_cost, l1, c1, l2, c2 = best
print(f"Example pair (chosen for a clear contrast): shortest {l1:.0f} m / climb {c1:.0f} m; "
      f"cost-surface {l2:.0f} m / climb {c2:.0f} m")

# --- figure: terrain slope (|grad z|, in %) with the two routes ---
grade = 100 * np.hypot(gx, gy)
fig, ax = plt.subplots(figsize=(8, 7.2))
extent = [x0, x0 + grade.shape[1] * dx, y0 + grade.shape[0] * dy, y0]
shown = ax.imshow(grade, extent=extent, cmap="YlOrRd", alpha=0.75, aspect=1 / np.cos(np.radians(35.70)))
for u, v in G.edges():
    ax.plot([xy[u][0], xy[v][0]], [xy[u][1], xy[v][1]], color="0.55", lw=0.35)
for route, color, style, label in (
    (r_short, "tab:blue", "--", f"Shortest by length ({l1:.0f} m, climb {c1:.0f} m)"),
    (r_cost, "k", "-", f"Cost-surface route ({l2:.0f} m, climb {c2:.0f} m)"),
):
    ax.plot([xy[n][0] for n in route], [xy[n][1] for n in route], color=color, ls=style, lw=2.6, label=label)
ax.scatter(*xy[a], c="green", s=70, zorder=5, label="Origin")
ax.scatter(*xy[b], c="red", s=70, zorder=5, label="Destination")
ax.set_xlim(extent[0] + 0.002, extent[1] - 0.002)
ax.set_ylim(extent[2] + 0.002, extent[3] - 0.002)
fig.colorbar(shown, ax=ax, shrink=0.7).set_label("Terrain slope |grad z| (%)")
ax.set(title="Cost-surface routing on the sample area", xlabel="Longitude", ylabel="Latitude")
ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
plt.tight_layout()
out = ROOT / "docs" / "example_route.png"
plt.savefig(out, dpi=160)
print("saved", out)
