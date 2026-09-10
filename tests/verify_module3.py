"""Verification script for Module 3 (Holland wind field). Run from project root:
    python tests\\verify_module3.py

This module doesn't persist a SQL table (see design decision in
build_03_hazard_windfield.py docstring - a full 10,270 x 5,000 footprint
table would be ~28.5M rows with no analytical benefit). Instead, we verify
the physics functions behave correctly in isolation.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
from build_03_hazard_windfield import (
    holland_wind_speed_kt, estimate_rmw_km, estimate_b_parameter,
    compute_event_footprint, haversine_km_vec
)

print("--- Test 1: Wind speed should PEAK near RMW, then DECREASE monotonically beyond it ---")
print("(NOTE: near the exact center (the 'eye'), real hurricanes are calm - wind rises")
print(" from ~0 at the center to a peak AT the radius of maximum winds (RMW), then decays")
print(" outward. So we only expect monotonic decay for distances >= RMW, not from r=0.)")
distances = np.array([5, 20, 50, 100, 200, 400])
rmw_test = 30
winds = holland_wind_speed_kt(distances, rmw_km=rmw_test, pressure_mb=930, storm_lat=25.5)
print("distances (km):", distances, f" (RMW={rmw_test}km)")
print("wind (kt):     ", np.round(winds, 1))
beyond_rmw = distances >= rmw_test
is_monotonic_decreasing = np.all(np.diff(winds[beyond_rmw]) <= 0)
print("Monotonically decreasing beyond RMW:", is_monotonic_decreasing, "(expected: True)")

print()
print("--- Test 2: Stronger storms (lower pressure) should produce higher wind at same distance ---")
weak = holland_wind_speed_kt(np.array([50]), rmw_km=30, pressure_mb=990, storm_lat=25.5)[0]
strong = holland_wind_speed_kt(np.array([50]), rmw_km=30, pressure_mb=920, storm_lat=25.5)[0]
print(f"Weak storm (990mb) wind at 50km: {weak:.1f}kt")
print(f"Strong storm (920mb) wind at 50km: {strong:.1f}kt")
print("Strong > weak:", strong > weak, "(expected: True)")

print()
print("--- Test 3: RMW and B-parameter stay within physically valid bounds ---")
for p in [990, 950, 920, 890]:
    rmw = estimate_rmw_km(p)
    b = estimate_b_parameter(p)
    print(f"pressure={p}mb -> RMW={rmw:.1f}km (valid range 15-60), B={b:.2f} (valid range 1.0-2.5)")

print()
print("--- Test 4: Hurricane Andrew (1992) real parameters produce plausible peak gust ---")
print("(Using 3 locations all clearly OUTSIDE the eye/RMW radius, to test simple outward")
print(" decay - a point placed exactly at the storm center would show the calm-eye effect")
print(" from Test 1, which is correct physics, not something to test for decay against.)")
andrew_event = {"landfall_lat": 25.5, "landfall_lon": -80.2, "pressure_mb": 926.0,
                 "forward_speed_kmh": 30.0, "heading_deg": 280.0}
loc_lat = np.array([25.7, 26.0, 27.0])   # ~22km, ~56km, ~167km from landfall - all outside typical RMW
loc_lon = np.array([-80.3, -80.3, -80.1])
dists = haversine_km_vec(andrew_event["landfall_lat"], andrew_event["landfall_lon"], loc_lat, loc_lon)
gust = compute_event_footprint(andrew_event, loc_lat, loc_lon)
print("Distances from landfall (km):", np.round(dists, 1))
print("Gust at each location (kt):  ", np.round(gust, 1))
print("Gust decreases as distance increases:", gust[0] >= gust[1] >= gust[2], "(expected: True)")
