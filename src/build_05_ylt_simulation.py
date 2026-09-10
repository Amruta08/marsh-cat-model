"""
Module 5: Year Loss Table (YLT) Simulation
=============================================
Simulates 100,000 years of hurricane activity by treating our Event Loss
Table as a marked Poisson process: each event has its own small annual
occurrence rate (most are well under 1/year), and in any given year, zero,
one, or (rarely) more than one event can occur.

METHODOLOGY: this is standard practice in catastrophe modeling - RMS/AIR
call this exact simulation the "Year Loss Table" or "Stochastic Event
Simulation." The mathematical basis is the well-established property that a
sum of independent Poisson processes is itself Poisson with the summed rate,
and conditional on an event occurring, WHICH event it was is a categorical
draw weighted by each event's own rate. This is standard probability theory
(not something I'm uncertain about, unlike some of the earlier modules'
physical constants).

WHY 100,000 YEARS: our rare tail events occur at rates as low as ~1-in-2,600
years (0.4514/year / 130 variants ~ implied per-event rate before rounding -
actually each individual synthetic event's rate is much rarer than the
combined 0.4514/year historical landfall rate). We need enough simulated
years that even a 1-in-1,000-year loss level has multiple simulated
occurrences to estimate from, or the tail of our loss distribution is just
noise. 100,000 years gives ~100 occurrences at the 1-in-1,000-year level,
which is a reasonable (if not huge) sample for tail estimation.
"""

import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "portfolio.db"
N_YEARS = 100_000
RNG = np.random.default_rng(seed=777)


def load_elt(conn):
    rows = conn.execute("""
        SELECT event_id, annual_rate, total_insured_loss FROM event_loss_table
    """).fetchall()
    return {
        "event_id": np.array([r[0] for r in rows]),
        "annual_rate": np.array([r[1] for r in rows]),
        "loss": np.array([r[2] for r in rows]),
    }


def simulate_ylt(elt, n_years=N_YEARS):
    total_rate = elt["annual_rate"].sum()
    weights = elt["annual_rate"] / total_rate  # probability an occurring event IS this specific event

    # Step 1: how many events occur in EACH of the n_years (vectorized Poisson draw)
    counts_per_year = RNG.poisson(total_rate, size=n_years)
    total_draws = int(counts_per_year.sum())
    print(f"Total simulated event occurrences across {n_years:,} years: {total_draws:,} "
          f"(expected ~{total_rate * n_years:,.0f})")

    # Step 2: for each occurrence, which specific event was it (weighted categorical draw)
    event_picks = RNG.choice(len(elt["event_id"]), size=total_draws, p=weights)
    losses_per_draw = elt["loss"][event_picks]

    # Step 3: which year does each draw belong to
    year_ids = np.repeat(np.arange(n_years), counts_per_year)

    # Step 4: aggregate to annual loss (sum) and annual occurrence loss (max single event)
    df = pd.DataFrame({"year": year_ids, "loss": losses_per_draw})
    annual_agg = df.groupby("year")["loss"].sum()
    annual_occ = df.groupby("year")["loss"].max()

    # Reindex so years with ZERO events show up as 0 loss, not missing
    annual_agg = annual_agg.reindex(np.arange(n_years), fill_value=0.0)
    annual_occ = annual_occ.reindex(np.arange(n_years), fill_value=0.0)

    return annual_agg.values, annual_occ.values


def load_ylt_to_sqlite(conn, annual_agg, annual_occ):
    conn.executescript("""
        DROP TABLE IF EXISTS year_loss_table;
        CREATE TABLE year_loss_table (
            sim_year INTEGER PRIMARY KEY,
            annual_aggregate_loss REAL,
            annual_occurrence_loss REAL
        );
    """)
    rows = [(int(y), float(annual_agg[y]), float(annual_occ[y])) for y in range(len(annual_agg))]
    conn.executemany("INSERT INTO year_loss_table VALUES (?,?,?)", rows)
    conn.commit()


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    elt = load_elt(conn)

    annual_agg, annual_occ = simulate_ylt(elt)
    load_ylt_to_sqlite(conn, annual_agg, annual_occ)

    sim_aal = annual_agg.mean()
    analytical_aal = (elt["annual_rate"] * elt["loss"]).sum()
    print(f"\nSimulated AAL (mean of {N_YEARS:,} simulated years): ${sim_aal:,.0f}")
    print(f"Analytical AAL (sum of rate x loss, from Module 4):    ${analytical_aal:,.0f}")
    pct_diff = 100 * abs(sim_aal - analytical_aal) / analytical_aal
    print(f"Difference: {pct_diff:.2f}% (should be small - this is a Monte Carlo")
    print(f"convergence check: with enough simulated years, the simulated mean")
    print(f"should converge to the exact analytical AAL)")

    print(f"\nYears with zero loss: {(annual_agg == 0).sum():,} of {N_YEARS:,} "
          f"({100*(annual_agg==0).sum()/N_YEARS:.1f}%)")
    print(f"Max simulated single-year aggregate loss: ${annual_agg.max():,.0f}")

    conn.close()
