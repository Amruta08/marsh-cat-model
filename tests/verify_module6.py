"""Verification script for Module 6 (EP curves / PML). Run from project root:
    python tests\\verify_module6.py
"""

import sqlite3

conn = sqlite3.connect("db/portfolio.db")

print("--- Test 1: ep_curve table covers all 100,000 simulated years ---")
n = conn.execute("SELECT COUNT(*) FROM ep_curve").fetchone()[0]
print(f"ep_curve rows: {n} (expected: 100000)")

print()
print("--- Test 2: pml_summary has one row per return period ---")
n_pml = conn.execute("SELECT COUNT(*) FROM pml_summary").fetchone()[0]
print(f"pml_summary rows: {n_pml} (expected: 5)")

print()
print("--- Test 3: PML increases monotonically with return period (both OEP and AEP) ---")
rows = conn.execute(
    "SELECT return_period_years, oep_loss, aep_loss FROM pml_summary ORDER BY return_period_years"
).fetchall()
oep_vals = [r[1] for r in rows]
aep_vals = [r[2] for r in rows]
oep_monotonic = all(oep_vals[i] <= oep_vals[i + 1] for i in range(len(oep_vals) - 1))
aep_monotonic = all(aep_vals[i] <= aep_vals[i + 1] for i in range(len(aep_vals) - 1))
print("OEP monotonically increasing with return period:", oep_monotonic, "(expected: True)")
print("AEP monotonically increasing with return period:", aep_monotonic, "(expected: True)")

print()
print("--- Test 4: AEP >= OEP at every return period (aggregate can't be less than its own max) ---")
all_aep_gte_oep = all(r[2] >= r[1] for r in rows)
print("AEP >= OEP at all return periods:", all_aep_gte_oep, "(expected: True)")

print()
print("--- Test 5: Headline results ---")
aal = conn.execute("SELECT AVG(annual_aggregate_loss) FROM year_loss_table").fetchone()[0]
print(f"AAL: ${aal:,.0f}")
for r in rows:
    print(f"  {r[0]:>6}-yr PML | OEP: ${r[1]:>15,.0f} | AEP: ${r[2]:>15,.0f}")

conn.close()
