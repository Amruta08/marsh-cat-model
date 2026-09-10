"""Verification script for Module 7 (geospatial export). Run from project root:
    python tests\\verify_module7.py
"""

import fiona
import geopandas as gpd

GPKG_PATH = "outputs/maps/portfolio_accumulation.gpkg"

print("--- Test 1: All 4 expected layers exist ---")
layers = fiona.listlayers(GPKG_PATH)
expected = {"portfolio_locations", "top_event_landfalls", "worst_event_footprint", "approx_county_bbox"}
print("Layers found:", layers)
print("All expected layers present:", expected.issubset(set(layers)), "(expected: True)")

print()
print("--- Test 2: Portfolio locations layer matches Module 1's 5,000 properties ---")
gdf = gpd.read_file(GPKG_PATH, layer="portfolio_locations")
print(f"Feature count: {len(gdf)} (expected: 5000)")

print()
print("--- Test 3: Top event landfalls layer has exactly 20 events ---")
gdf = gpd.read_file(GPKG_PATH, layer="top_event_landfalls")
print(f"Feature count: {len(gdf)} (expected: 20)")
print("Sorted descending by loss (largest first):",
      list(gdf["insured_loss"]) == sorted(gdf["insured_loss"], reverse=True))

print()
print("--- Test 4: Footprint circles - 34kt radius should be LARGER than 64kt radius ---")
print("(34kt = tropical storm force, extends further out; 64kt = hurricane force,")
print(" only near the core - so the 34kt circle should be the bigger one)")
gdf = gpd.read_file(GPKG_PATH, layer="worst_event_footprint")
radii = dict(zip(gdf["threshold"], gdf["radius_km"]))
print("Radii (km):", radii)
r34 = [v for k, v in radii.items() if "34" in k][0]
r64 = [v for k, v in radii.items() if "64" in k][0]
print("34kt radius > 64kt radius:", r34 > r64, "(expected: True)")

print()
print("--- Test 5: County bounding boxes cover all 3 counties in the portfolio ---")
gdf = gpd.read_file(GPKG_PATH, layer="approx_county_bbox")
print("Counties:", sorted(gdf["county"].tolist()), "(expected: Broward, Miami-Dade, Palm Beach)")
