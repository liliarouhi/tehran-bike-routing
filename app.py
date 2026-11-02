"""Streamlit app: pick an origin and a destination on a map of central Tehran and get the
route that minimises a cost built from street length and DEM slope.

Run with:  streamlit run app.py
"""
from pathlib import Path

import folium
import networkx as nx
import osmnx as ox
import rasterio
import streamlit as st
from streamlit_folium import st_folium

from routing import add_edge_costs, compute_gradient

DATA_DIR = Path(__file__).parent / "sample_data"
DEM_PATH = DATA_DIR / "tehran_dem_small.tif"
GRAPH_PATH = DATA_DIR / "small_tehran.graphml"

st.set_page_config(layout="wide")
st.title("🚴 Optimal bicycle route (sample area of Tehran)")


@st.cache_resource
def load_network():
    """Load the DEM and the street graph, and add the cost of every edge."""
    with rasterio.open(DEM_PATH) as dem:
        elevation = dem.read(1).astype(float)
        nodata = dem.nodata
        t = dem.transform
    gx, gy = compute_gradient(elevation, t.a, t.e, t.f, nodata)  # gradient of the terrain surface

    G = ox.load_graphml(GRAPH_PATH)
    G = G.subgraph(max(nx.strongly_connected_components(G), key=len)).copy()

    outside = add_edge_costs(G, gx, gy, t.c, t.f, t.a, t.e)
    if outside:
        print(f"warning: {outside} graph nodes lie outside the DEM")

    lats = [d["y"] for _, d in G.nodes(data=True)]
    lons = [d["x"] for _, d in G.nodes(data=True)]
    bbox = (min(lats), max(lats), min(lons), max(lons))  # south, north, west, east
    return G, bbox


G, (south, north, west, east) = load_network()

# ------------------------
# Session state
# ------------------------
if "points" not in st.session_state:
    st.session_state.points = []
if "route" not in st.session_state:
    st.session_state.route = None

# ------------------------
# Map
# ------------------------
m = folium.Map(location=[(north + south) / 2, (east + west) / 2], zoom_start=15, max_bounds=True)
m.fit_bounds([[south, west], [north, east]])
folium.Rectangle(
    bounds=[[south, west], [north, east]],
    color="blue",
    weight=2,
    fill=True,
    fill_opacity=0.05,
    tooltip="Sample area: click inside this rectangle",
).add_to(m)

for i, (lat, lon) in enumerate(st.session_state.points):
    folium.Marker(
        [lat, lon],
        icon=folium.Icon(color="green" if i == 0 else "red"),
        popup="Origin" if i == 0 else "Destination",
    ).add_to(m)

if st.session_state.route:
    folium.PolyLine(
        [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in st.session_state.route],
        color="red",
        weight=5,
    ).add_to(m)
    
clicked = st_folium(
    m,
    height=700,
    use_container_width=True,
    key="map",
    returned_objects=["last_clicked"],  
)

# ------------------------
# Click handling
# ------------------------
if clicked and clicked.get("last_clicked"):
    p = (clicked["last_clicked"]["lat"], clicked["last_clicked"]["lng"])
    if p != st.session_state.get("last_click"): 
        st.session_state.last_click = p
        if not (south <= p[0] <= north and west <= p[1] <= east):
            st.warning("Click inside the blue rectangle (the sample area).")
        elif len(st.session_state.points) < 2:
            st.session_state.points.append(p)
            st.rerun() 

# ------------------------
# Compute route
# ------------------------
if len(st.session_state.points) == 2:
    if st.button("🔍 Compute route"):
        (lat1, lon1), (lat2, lon2) = st.session_state.points

        n1 = ox.distance.nearest_nodes(G, lon1, lat1)
        n2 = ox.distance.nearest_nodes(G, lon2, lat2)

        if not nx.has_path(G, n1, n2):
            st.error("❌ No route between these two points")
        else:
            st.session_state.route = nx.shortest_path(G, n1, n2, weight="cost")
            st.rerun()

if st.button("🔄 Reset"):
    st.session_state.points = []
    st.session_state.route = None
    st.rerun()
