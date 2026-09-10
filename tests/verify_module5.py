"""Verification script for Module 5 (YLT simulation). Run from project root:
    python tests\\verify_module5.py
"""

import sqlite3
import numpy as np

conn = sqlite3.connect("db/portfolio.db")

print("--- Test 1: YLT row count ---")
n_years = conn.execute("SELECT COUNT(*) FROM year_loss_table").fetchone()[0]
print(f"Simulated years: {n_years} (expected: 100000)")

print()
print("--- Test 2: Monte Carlo convergence - simulated AAL vs analytical AAL ---")
sim_aal = conn.execute("SELECT AVG(annual_aggregate_loss) FROM year_loss_table").fetchone()[0]
analytical_aal = conn.execute(
    "SELECT SUM(annual_rate * total_insured_loss) FROM event_loss_table"
).fetchone()[0]
pct_diff = 100 * abs(sim_aal - analytical_aal) / analytical_aal
print(f"Simulated AAL: ${sim_aal:,.0f}")
print(f"Analytical AAL: ${analytical_aal:,.0f}")
print(f"Difference: {pct_diff:.2f}% (expected: small, <5% - confirms simulation is unbiased)")

print()
print("--- Test 3: Zero-loss year frequency matches theoretical Poisson(0) probability ---")
total_rate = conn.execute("SELECT SUM(annual_rate) FROM event_loss_table").fetchone()[0]
theoretical_zero_pct = 100 * np.exp(-total_rate)
zero_years = conn.execute(
    "SELECT COUNT(*) FROM year_loss_table WHERE annual_aggregate_loss = 0"
).fetchone()[0]
actual_zero_pct = 100 * zero_years / n_years
print(f"Theoretical P(zero events in a year) = e^(-{total_rate:.4f}) = {theoretical_zero_pct:.2f}%")
print(f"Actual zero-loss years in simulation: {actual_zero_pct:.2f}%")
print(f"Match within 1 percentage point:", abs(theoretical_zero_pct - actual_zero_pct) < 1.0)

print()
print("--- Test 4: Occurrence loss should always be <= aggregate loss (same year) ---")
violations = conn.execute(
    "SELECT COUNT(*) FROM year_loss_table WHERE annual_occurrence_loss > annual_aggregate_loss"
).fetchone()[0]
print(f"Years where occurrence loss > aggregate loss: {violations} (expected: 0 - would be impossible)")

conn.close()
