"""Check the cost formulas on a synthetic terrain (a plane rising 5 % to the north).

Run from the project root:  python tests/test_routing.py
"""
import math
import sys
from pathlib import Path

import networkx as nx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from routing import add_edge_costs, cell_size_m, compute_gradient  # noqa: E402

dx, dy, x0, y0, h, w = 0.0003, -0.0003, 51.0, 36.0, 60, 60
_, cy = cell_size_m(dx, dy, y0 + h * dy / 2)
rows = np.arange(h)[:, None] * np.ones((1, w))
z = 1000 + 0.05 * cy * (h - 1 - rows)                 # elevation rises towards the north (row 0)
gx, gy = compute_gradient(z, dx, dy, y0, sigma=0)
assert abs(gx).max() < 1e-9 and abs(gy[10:50, 10:50].mean() - 0.05) < 1e-6

lon, lat = 51.009, 35.991
G = nx.MultiDiGraph()
G.add_node(1, x=lon, y=lat)
G.add_node(2, x=lon, y=lat + 100 / 110574)                                        # 100 m north
G.add_node(3, x=lon + 100 / (111320 * math.cos(math.radians(lat))), y=lat)        # 100 m east
for a, b in ((1, 2), (2, 1), (1, 3), (3, 1)):
    G.add_edge(a, b, length=100.0)
assert add_edge_costs(G, gx, gy, x0, y0, dx, dy) == 0

north, south, east = G[1][2][0], G[2][1][0], G[1][3][0]
assert abs(north["cost"] - 250) < 0.5 and abs(north["ascent"] - 5) < 0.05     # 5 % climb: 2.5x
assert abs(south["cost"] - 125) < 0.5 and abs(south["descent"] - 5) < 0.05    # 5 % descent: 1.25x
assert abs(east["cost"] - 100) < 0.5                                          # flat: unchanged
print("all checks passed")
