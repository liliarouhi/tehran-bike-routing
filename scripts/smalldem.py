import rasterio
from rasterio.mask import mask
from shapely.geometry import box

# ----------------------------
# محدوده کوچک (همان محدوده گراف)
# ----------------------------
north = 35.7163   # covers the graph in sample_data/small_tehran.graphml
south = 35.6907   # (lat 35.693-35.714, lon 51.338-51.365) with a small margin
east  = 51.3671
west  = 51.3363

# فایل DEM بزرگ
input_dem = "data/tehran_dem.tif"

# خروجی DEM کوچک
output_dem = "sample_data/tehran_dem_small.tif"

# ----------------------------
# crop DEM
# ----------------------------
with rasterio.open(input_dem) as src:
    bbox = box(west, south, east, north)
    geo = [bbox.__geo_interface__]

    out_image, out_transform = mask(src, geo, crop=True)
    out_meta = src.meta.copy()

    out_meta.update({
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform
    })

    with rasterio.open(output_dem, "w", **out_meta) as dest:
        dest.write(out_image)

print("✅ DEM کوچک ساخته شد:", output_dem)