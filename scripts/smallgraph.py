import osmnx as ox

# مرکز نمونه (دانشگاه تهران)
center_lat = 35.7036
center_lon = 51.3517

# شعاع به متر (اول کوچک، بعداً زیاد کن)
radius = 1200  # ۱.۲ کیلومتر

print("🚴 در حال ساخت گراف کوچک تهران...")

G = ox.graph_from_point(
    (center_lat, center_lon),
    dist=radius,
    network_type="drive",   # مهم!
    simplify=True
)

ox.save_graphml(G, "sample_data/small_tehran.graphml")

print("✅ گراف کوچک ذخیره شد!")
print("nodes:", len(G.nodes))
print("edges:", len(G.edges))