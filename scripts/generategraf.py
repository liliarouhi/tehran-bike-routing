import osmnx as ox

osm_file = "data/tehran.osm"

print("🚴 ساخت گراف دوچرخه...")
G_bike = ox.graph_from_xml(osm_file)
ox.save_graphml(G_bike, "data/tehran_bike.graphml")

# print("🚗 ساخت گراف کامل خیابان‌ها...")
# G_drive = ox.graph_from_xml(osm_file, network_type="drive")
# ox.save_graphml(G_drive, "tehran_drive.graphml")

print("✅ گراف‌ها ذخیره شدند")