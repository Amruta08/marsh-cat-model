"""Verification script for Module 2 (event set). Run from project root:
    python tests\\verify_module2.py
"""

import sqlite3

conn = sqlite3.connect("db/portfolio.db")

print("--- Historical Florida landfalls: count + top 5 by wind ---")
count = conn.execute("SELECT COUNT(*) FROM historical_events").fetchone()[0]
print("Total historical landfalls:", count, "(expected: 79)")

for row in conn.execute("""
    SELECT name, year, max_wind_kt, pressure_mb
    FROM historical_events
    ORDER BY max_wind_kt DESC LIMIT 5
"""):
    print(row)

print()
print("--- Synthetic catalog: size + rate calibration check ---")
n_synth = conn.execute("SELECT COUNT(*) FROM synthetic_events").fetchone()[0]
rate_sum = conn.execute("SELECT SUM(annual_rate) FROM synthetic_events").fetchone()[0]
print(f"Synthetic events: {n_synth} (expected: 10270)")
print(f"Sum of annual rates: {rate_sum:.4f} (expected: ~0.4514, matches historical rate)")

print()
print("--- Wind speed sanity: should be >= 34kt (tropical storm threshold) ---")
row = conn.execute("SELECT MIN(max_wind_kt), MAX(max_wind_kt) FROM synthetic_events").fetchone()
print("min/max wind (kt):", row, "(expected min: 34.0)")

print()
print("--- Known-storm check: Hurricane Andrew (1992) should show ~145kt / ~922-926mb ---")
for row in conn.execute("""
    SELECT name, year, max_wind_kt, pressure_mb
    FROM historical_events WHERE name LIKE '%ANDREW%'
"""):
    print(row)

conn.close()
