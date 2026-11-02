
# import streamlit as st
# from streamlit_folium import st_folium
# import folium
# import rasterio
# import numpy as np
# import os
# import osmnx as ox
# import networkx as nx
# from matplotlib import pyplot as plt
# from mpl_toolkits.mplot3d import Axes3D

# st.set_page_config(layout="wide")
# st.title("پروژه مسیر بهینه دوچرخه تهران")

# # ----------------------------
# # 1️⃣ بارگذاری DEM و ساخت رویه هزینه
# # ----------------------------
# dem_path = "/Users/liliarouhi/Desktop/bicycleProj/tehran_dem.tif"
# if not os.path.exists(dem_path):
#     st.error(f"فایل DEM پیدا نشد: {dem_path}")
#     st.stop()

# with rasterio.open(dem_path) as dem:
#     elevation = dem.read(1).astype(float)
#     transform = dem.transform
# st.success(f"DEM با ابعاد {elevation.shape} بارگذاری شد!")

# # محاسبه شیب (Gradient) برای هندسه دیفرانسیل
# dzdy, dzdx = np.gradient(elevation)
# slope = np.sqrt(dzdx**2 + dzdy**2)

# # نمایش DEM سه بعدی
# fig = plt.figure(figsize=(8,6))
# ax = fig.add_subplot(111, projection='3d')
# X, Y = np.meshgrid(np.arange(elevation.shape[1]), np.arange(elevation.shape[0]))
# ax.plot_surface(X, Y, elevation, cmap='terrain', linewidth=0, antialiased=False)
# ax.set_title("DEM سه بعدی تهران")
# st.pyplot(fig)

# # ----------------------------
# # 2️⃣ بارگذاری گراف‌ها از فایل لوکال
# # ----------------------------
# st.info("بارگذاری گراف‌ها از فایل‌های محلی...")
# bike_graph_file = "tehran_bike.graphml"
# all_graph_file  = "tehran_drive.graphml"

# G_bike = ox.load_graphml(bike_graph_file)
# G_all  = ox.load_graphml(all_graph_file)
# st.success("گراف‌ها بارگذاری شدند!")

# # ----------------------------
# # 3️⃣ تابع هزینه واقعی با وزن رویه‌ها
# # ----------------------------
# # ضریب‌ها از مقالات معتبر
# a_length = 1
# b_slope = 20
# c_curvature = 5
# d_street_type = 10
# e_cycleway = 0.85

# def set_edge_cost(G, dem, slope):
#     for u, v, data in G.edges(data=True):
#         length = data.get('length', 1)
#         street_type = data.get('highway', 'residential')
#         has_cycleway = data.get('cycleway', False)

#         if isinstance(street_type, list):
#             street_type = street_type[0]

#         street_penalty = d_street_type if street_type in ['primary','secondary'] else 0
#         cycleway_bonus = e_cycleway if has_cycleway else 1

#         lat1, lon1 = G.nodes[u]['y'], G.nodes[u]['x']
#         lat2, lon2 = G.nodes[v]['y'], G.nodes[v]['x']

#         row1, col1 = ~dem.transform * (lon1, lat1)
#         row2, col2 = ~dem.transform * (lon2, lat2)
#         row1, col1 = int(max(0,min(dem.shape[0]-1,row1))), int(max(0,min(dem.shape[1]-1,col1)))
#         row2, col2 = int(max(0,min(dem.shape[0]-1,row2))), int(max(0,min(dem.shape[1]-1,col2)))

#         slope_mean = np.mean([slope[row1,col1], slope[row2,col2]])
#         curvature_val = np.sqrt((lat2-lat1)**2 + (lon2-lon1)**2) * c_curvature

#         data['cost'] = (a_length*length + b_slope*slope_mean + curvature_val + street_penalty)
#         data['cost'] *= cycleway_bonus

# # اعمال هزینه روی هر دو گراف
# set_edge_cost(G_bike, dem, slope)
# set_edge_cost(G_all, dem, slope)

# # ----------------------------
# # 4️⃣ انتخاب نقاط مبدا و مقصد و محاسبه مسیر
# # ----------------------------
# st.info("لطفا روی نقشه کلیک کنید تا مبدا و مقصد انتخاب شود")
# m = folium.Map(location=[35.70, 51.42], zoom_start=12)

# if 'points' not in st.session_state:
#     st.session_state['points'] = []

# clicked = st_folium(m, width=800, height=600)
# if clicked and clicked.get("last_clicked"):
#     lat = clicked["last_clicked"]["lat"]
#     lon = clicked["last_clicked"]["lng"]
#     if len(st.session_state['points']) < 2:
#         st.session_state['points'].append((lat, lon))

# # محاسبه مسیر
# if len(st.session_state['points']) == 2:
#     origin_lat, origin_lon = st.session_state['points'][0]
#     dest_lat, dest_lon = st.session_state['points'][1]

#     orig_node_bike = ox.distance.nearest_nodes(G_bike, origin_lon, origin_lat)
#     dest_node_bike = ox.distance.nearest_nodes(G_bike, dest_lon, dest_lat)

#     # مسیر ایمن
#     if nx.has_path(G_bike, orig_node_bike, dest_node_bike):
#         route = nx.shortest_path(G_bike, orig_node_bike, dest_node_bike, weight='cost')
#         st.success(f"مسیر ایمن دوچرخه پیدا شد! تعداد نودها: {len(route)}")
#         G_used = G_bike
#     else:
#         # مسیر اضطراری
#         orig_node_all = ox.distance.nearest_nodes(G_all, origin_lon, origin_lat)
#         dest_node_all = ox.distance.nearest_nodes(G_all, dest_lon, dest_lat)
#         if nx.has_path(G_all, orig_node_all, dest_node_all):
#             route = nx.shortest_path(G_all, orig_node_all, dest_node_all, weight='cost')
#             st.warning(f"مسیر اضطراری پیدا شد! تعداد نودها: {len(route)}")
#             G_used = G_all
#         else:
#             st.error("هیچ مسیری حتی اضطراری پیدا نشد!")
#             route = []

#     # رسم مسیر روی نقشه
#     if route:
#         route_map = folium.Map(location=[35.70, 51.42], zoom_start=12)
#         folium.PolyLine([(G_used.nodes[n]['y'], G_used.nodes[n]['x']) for n in route],
#                         color='red', weight=4).add_to(route_map)
#         st_folium(route_map, width=800, height=600)

#         # آمار مسیر
#         total_length = sum(G_used.edges[u,v,0]['length'] for u,v in zip(route[:-1], route[1:]))
#         st.write(f"طول مسیر: {total_length:.2f} متر")
#         st.write("برای انتخاب مسیر جدید، صفحه را ریفرش کنید.")


