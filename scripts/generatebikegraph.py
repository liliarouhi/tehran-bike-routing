import osmnx as ox
import networkx as nx

G = ox.load_graphml("data/tehran_drive.graphml")

print("🚴 در حال ساخت گراف دوچرخه‌پسند...")

bike_allowed = []
for u, v, k, data in G.edges(keys=True, data=True):
    highway = data.get("highway", "")
    if isinstance(highway, list):
        highway = highway[0]

    # حذف بزرگراه‌ها و خیابون‌های خیلی خطرناک
    if highway not in ["motorway", "trunk", "motorway_link", "trunk_link"]:
        bike_allowed.append((u, v, k))

G_bike = G.edge_subgraph(bike_allowed).copy()

print("✅ گراف دوچرخه ساخته شد")
print("نودها:", len(G_bike.nodes))
print("یال‌ها:", len(G_bike.edges))

ox.save_graphml(G_bike, "data/tehran_bike.graphml")