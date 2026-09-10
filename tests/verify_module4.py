"""Verification script for Module 4 (vulnerability + loss / ELT). Run from
project root:
    python tests\\verify_module4.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import sqlite3
import numpy as np
from build_04_vulnerability_loss import damage_ratio

conn = sqlite3.connect("db/portfolio.db")

print("--- Test 1: Event Loss Table row count ---")
n_elt = conn.execute("SELECT COUNT(*) FROM event_loss_table").fetchone()[0]
print(f"ELT rows: {n_elt} (expected: 10270)")

print()
print("--- Test 2: Event-location detail table only covers top 20 events ---")
n_detail_events = conn.execute("SELECT COUNT(DISTINCT event_id) FROM event_location_losses").fetchone()[0]
print(f"Distinct events in detail table: {n_detail_events} (expected: 20)")

print()
print("--- Test 3: Damage curve ordering - Manufactured Home > Wood Frame > Masonry at same wind ---")
test_wind = np.array([100.0])
mh = damage_ratio(test_wind, np.array(["Manufactured Home"]))[0]
wf = damage_ratio(test_wind, np.array(["Wood Frame"]))[0]
ma = damage_ratio(test_wind, np.array(["Masonry"]))[0]
print(f"At 100kt: Manufactured Home={mh:.2f}, Wood Frame={wf:.2f}, Masonry={ma:.2f}")
print("Correct ordering (MH > WF > Masonry):", mh > wf > ma, "(expected: True)")

print()
print("--- Test 4: Damage ratio bounds - must stay in [0,1] even at extreme wind ---")
extreme_wind = np.array([250.0])
d = damage_ratio(extreme_wind, np.array(["Wood Frame"]))[0]
print(f"Damage ratio at 250kt (extreme): {d:.3f} (expected: close to 1.0, never > 1.0)")

print()
print("--- Test 5: Below onset threshold (39kt), damage should be exactly 0 ---")
low_wind = np.array([35.0])
d_low = damage_ratio(low_wind, np.array(["Wood Frame"]))[0]
print(f"Damage ratio at 35kt: {d_low} (expected: 0.0)")

print()
print("--- Test 6: Portfolio-level AAL sanity check ---")
total_tiv = conn.execute("SELECT SUM(total_insured_value) FROM policies").fetchone()[0]
aal = conn.execute("SELECT SUM(annual_rate * total_insured_loss) FROM event_loss_table").fetchone()[0]
print(f"AAL: ${aal:,.0f}  |  TIV: ${total_tiv:,.0f}  |  AAL as %% of TIV: {100*aal/total_tiv:.2f}%%")
print("(Real coastal FL residential wind AAL is typically ~0.5-1.5% of TIV in actual")
print(" calibrated models - ours runs higher, which flags that our illustrative")
print(" vulnerability curves are likely steeper than real HAZUS curves. This is an")
print(" honest finding to report, not something to quietly adjust away.)")

conn.close()
