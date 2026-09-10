"""
Module 7: Geospatial Export for QGIS
=======================================
I can't run QGIS myself (it's a desktop GUI app, no GUI in my execution
environment) - so this module's job is to produce a clean GeoPackage (.gpkg)
with properly structured layers that YOU open in QGIS locally to build the
actual accumulation map and export the hero image for your README.

WHAT AN "ACCUMULATION MAP" IS AND WHY IT MATTERS:
This is a real, specific deliverable type in reinsurance - it shows WHERE
exposure (TIV) is geographically concentrated, which matters because two
policies that look fine individually can create dangerous aggregation risk
if they're both in the same flood/wind corridor. Underwriters and brokers
request accumulation maps specifically to check this. Layering event
landfall points and footprint extent on top of it additionally shows WHERE
historical/modeled risk actually materializes relative to that exposure.

LAYERS PRODUCED:
1. portfolio_locations - all 5,000 properties, colored/sized by TIV and
   construction class in QGIS (you'll style this)
2. top_event_landfalls - the 20 costliest synthetic events' landfall points
3. worst_event_footprint - two concentric circles around the SINGLE costliest
   event's landfall, showing the approximate radius of tropical-storm-force
   (34kt+) and hurricane-force (64kt+) winds
4. approx_county_bbox - the rough bounding boxes used in Module 1's synthetic
   portfolio generation - LABELED AS APPROXIMATE, not real county boundaries.
   For a genuinely polished final map, download the real Miami-Dade/
   Broward/Palm Beach boundaries from US Census TIGER/Line
   (https://www.census.gov/cgi-bin/geo/shapefiles/index.php, select
   "Counties" for Florida) and add that as a real layer in QGIS instead -
   that's the actual ArcGIS-equivalent workflow the JD is testing for.
"""

import sqlite3
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_03_hazard_windfield import holland_wind_speed_kt, estimate_rmw_km

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "portfolio.db"
OUTPUT_GPKG = Path(__file__).resolve().parent.parent / "outputs" / "maps" / "portfolio_accumulation.gpkg"

COUNTY_BOUNDS = {  # same approximate boxes as Module 1 - see disclosure above
    "Miami-Dade": (25.14, 25.97, -80.87, -80.11),
    "Broward":    (25.97, 26.44, -80.89, -80.06),
    "Palm Beach": (26.32, 26.97, -80.87, -80.03),
}


def export_portfolio_locations(conn):
    rows = conn.execute("""
        SELECT l.location_id, l.latitude, l.longitude, l.county,
               l.construction_class, p.total_insured_value
        FROM locations l JOIN policies p ON p.location_id = l.location_id
    """).fetchall()
    gdf = gpd.GeoDataFrame(
        {
            "location_id": [r[0] for r in rows],
            "county": [r[3] for r in rows],
            "construction": [r[4] for r in rows],
            "tiv": [r[5] for r in rows],
        },
        geometry=[Point(r[2], r[1]) for r in rows],
        crs="EPSG:4326",
    )
    return gdf


def export_top_event_landfalls(conn):
    rows = conn.execute("""
        SELECT e.event_id, e.source_storm_id, e.annual_rate, elt.max_gust_kt,
               elt.total_insured_loss, s.landfall_lat, s.landfall_lon
        FROM event_loss_table elt
        JOIN synthetic_events s ON s.event_id = elt.event_id
        JOIN synthetic_events e ON e.event_id = elt.event_id
        ORDER BY elt.total_insured_loss DESC LIMIT 20
    """).fetchall()
    gdf = gpd.GeoDataFrame(
        {
            "event_id": [r[0] for r in rows],
            "source_storm": [r[1] for r in rows],
            "annual_rate": [r[2] for r in rows],
            "max_gust_kt": [r[3] for r in rows],
            "insured_loss": [r[4] for r in rows],
        },
        geometry=[Point(r[6], r[5]) for r in rows],
        crs="EPSG:4326",
    )
    return gdf, rows[0]  # also return the single costliest event for the footprint layer


def build_footprint_circles(worst_event_row):
    """Find the approximate radius (km) where wind drops below 34kt (tropical
    storm) and 64kt (hurricane) thresholds, by sampling the Holland wind
    equation outward from the landfall point. Then buffer in a projected
    (meters-based) CRS for geometric accuracy, and reproject back to
    EPSG:4326 for QGIS/web-map compatibility."""
    event_id, storm_id, rate, max_gust, loss, lat, lon = worst_event_row
    pressure = None
    # We need pressure_mb for the Holland calc - fetch it directly
    conn = sqlite3.connect(DB_PATH)
    pressure = conn.execute(
        "SELECT pressure_mb FROM synthetic_events WHERE event_id = ?", (event_id,)
    ).fetchone()[0]
    conn.close()

    rmw_km = estimate_rmw_km(pressure)
    distances = np.arange(1, 400, 1.0)
    winds = holland_wind_speed_kt(distances, rmw_km, pressure, lat)

    # Find outermost distance where wind still exceeds each threshold
    def radius_for_threshold(threshold_kt):
        above = distances[winds >= threshold_kt]
        return float(above.max()) if len(above) > 0 else float(rmw_km)

    r_34kt = radius_for_threshold(34)
    r_64kt = radius_for_threshold(64)

    center = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326")
    center_projected = center.to_crs("EPSG:3857")  # Web Mercator, meters-based, fine for a local buffer at this latitude
    circle_34 = center_projected.buffer(r_34kt * 1000).to_crs("EPSG:4326")
    circle_64 = center_projected.buffer(r_64kt * 1000).to_crs("EPSG:4326")

    gdf = gpd.GeoDataFrame(
        {"threshold": ["34kt (tropical storm)", "64kt (hurricane)"], "radius_km": [r_34kt, r_64kt]},
        geometry=[circle_34.iloc[0], circle_64.iloc[0]],
        crs="EPSG:4326",
    )
    return gdf, event_id, storm_id, r_34kt, r_64kt


def export_county_bboxes():
    from shapely.geometry import box
    rows = [(name, box(lon_min, lat_min, lon_max, lat_max))
            for name, (lat_min, lat_max, lon_min, lon_max) in COUNTY_BOUNDS.items()]
    gdf = gpd.GeoDataFrame(
        {"county": [r[0] for r in rows], "note": ["APPROXIMATE bounding box, not real boundary"] * len(rows)},
        geometry=[r[1] for r in rows],
        crs="EPSG:4326",
    )
    return gdf


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    OUTPUT_GPKG.parent.mkdir(parents=True, exist_ok=True)

    locations_gdf = export_portfolio_locations(conn)
    print(f"Portfolio locations layer: {len(locations_gdf)} points")

    events_gdf, worst_event_row = export_top_event_landfalls(conn)
    print(f"Top event landfalls layer: {len(events_gdf)} points")

    footprint_gdf, worst_event_id, worst_storm_id, r34, r64 = build_footprint_circles(worst_event_row)
    print(f"Worst event (event_id={worst_event_id}, source_storm={worst_storm_id}): "
          f"34kt radius ~{r34:.0f}km, 64kt radius ~{r64:.0f}km")

    bbox_gdf = export_county_bboxes()

    # GeoPackage supports multiple named layers in a single file - open this
    # in QGIS via Layer > Add Layer > Add Vector Layer, select the .gpkg,
    # and all 4 layers will be listed to add individually.
    if OUTPUT_GPKG.exists():
        OUTPUT_GPKG.unlink()
    locations_gdf.to_file(OUTPUT_GPKG, layer="portfolio_locations", driver="GPKG")
    events_gdf.to_file(OUTPUT_GPKG, layer="top_event_landfalls", driver="GPKG")
    footprint_gdf.to_file(OUTPUT_GPKG, layer="worst_event_footprint", driver="GPKG")
    bbox_gdf.to_file(OUTPUT_GPKG, layer="approx_county_bbox", driver="GPKG")

    print(f"\nGeoPackage written to: {OUTPUT_GPKG}")
    print("Open this in QGIS: Layer > Add Layer > Add Vector Layer > select this .gpkg file")

    conn.close()
