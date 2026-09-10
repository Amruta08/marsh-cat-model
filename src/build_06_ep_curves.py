"""
Module 6: AAL, EP Curves, and PML - via SQL
==============================================
This is the module the JD is most directly testing for: "provide modelled
loss outputs in various forms" and "proficiency in SQL." Every rollup here
is a SQL query against the Year Loss Table, using window functions (RANK())
rather than pandas - this is genuinely how you'd want to do it in practice
too, since these are exactly the aggregations a database is good at.

KEY CONCEPTS (all standard cat-modeling terminology, correctly used here -
these definitions are NOT domain-uncertain, unlike some earlier modules'
physical constants):

- AAL (Average Annual Loss): the mean loss per year, averaged across all
  simulated years - the "expected value" of annual loss.

- OEP (Occurrence Exceedance Probability): based on the SINGLE LARGEST event
  in each simulated year. Answers "what's the probability that the worst
  single event in a year exceeds $X?" Used for per-event/per-occurrence
  reinsurance layer pricing (e.g., "1-in-100-year single event").

- AEP (Aggregate Exceedance Probability): based on the TOTAL loss across ALL
  events in each simulated year (a bad year could have 2-3 storms). Answers
  "what's the probability that TOTAL annual loss exceeds $X?" Used for
  aggregate/stop-loss reinsurance layer pricing.

- Return period (e.g., "1-in-100-year"): the inverse of exceedance
  probability. A 1-in-100-year loss is the loss level exceeded, on average,
  once every 100 years (i.e., 1% annual exceedance probability).

- PML (Probable Maximum Loss): the loss AT a specific return period - e.g.,
  "the 250-year PML is $X" means there's a 1/250 (0.4%) chance of losing at
  least $X in any given year.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "portfolio.db"
N_YEARS = 100_000
RETURN_PERIODS = [100, 250, 500, 1000, 10000]  # years


def build_ep_curve_table(conn):
    """Ranks every simulated year by both occurrence and aggregate loss, and
    computes exceedance probability / implied return period for each rank.
    This single table is the source for both the OEP and AEP curves."""
    conn.executescript(f"""
        DROP TABLE IF EXISTS ep_curve;
        CREATE TABLE ep_curve AS
        SELECT
            sim_year,
            annual_occurrence_loss,
            annual_aggregate_loss,
            RANK() OVER (ORDER BY annual_occurrence_loss DESC) AS occ_rank,
            RANK() OVER (ORDER BY annual_aggregate_loss DESC) AS agg_rank,
            RANK() OVER (ORDER BY annual_occurrence_loss DESC) * 1.0 / {N_YEARS} AS occ_exceedance_prob,
            RANK() OVER (ORDER BY annual_aggregate_loss DESC) * 1.0 / {N_YEARS} AS agg_exceedance_prob,
            {N_YEARS} * 1.0 / RANK() OVER (ORDER BY annual_occurrence_loss DESC) AS occ_return_period,
            {N_YEARS} * 1.0 / RANK() OVER (ORDER BY annual_aggregate_loss DESC) AS agg_return_period
        FROM year_loss_table;

        CREATE INDEX idx_ep_occ_rank ON ep_curve(occ_rank);
        CREATE INDEX idx_ep_agg_rank ON ep_curve(agg_rank);
    """)
    conn.commit()


def compute_pml_summary(conn):
    """PML at each standard return period, via SQL. Uses the standard
    'nearest rank' method: the loss value at the highest rank not exceeding
    the target rank (N_YEARS/T). An EXACT rank match isn't guaranteed because
    our event catalog is a finite discrete set of 10,270 events - the same
    event can recur across different simulated years and produce identical
    loss values, so SQL's RANK() correctly skips numbers after ties (e.g. if
    3 years tie for rank 5, the next rank is 8, not 6). I caught this by
    testing an exact-match query first and getting NULL results at several
    return periods - the nearest-rank approach below is the standard fix and
    is itself how real EP curves are constructed from discrete simulations."""
    rows = []
    for T in RETURN_PERIODS:
        target_rank = N_YEARS // T
        occ_loss = conn.execute(
            "SELECT annual_occurrence_loss FROM ep_curve WHERE occ_rank <= ? ORDER BY occ_rank DESC LIMIT 1",
            (target_rank,),
        ).fetchone()[0]
        agg_loss = conn.execute(
            "SELECT annual_aggregate_loss FROM ep_curve WHERE agg_rank <= ? ORDER BY agg_rank DESC LIMIT 1",
            (target_rank,),
        ).fetchone()[0]
        rows.append({
            "return_period_years": T,
            "target_rank": target_rank,
            "oep_loss": occ_loss,
            "aep_loss": agg_loss,
        })
    return rows


def load_pml_summary_to_sqlite(conn, pml_rows):
    conn.executescript("""
        DROP TABLE IF EXISTS pml_summary;
        CREATE TABLE pml_summary (
            return_period_years INTEGER PRIMARY KEY,
            target_rank INTEGER,
            oep_loss REAL,
            aep_loss REAL
        );
    """)
    conn.executemany(
        "INSERT INTO pml_summary VALUES (:return_period_years,:target_rank,:oep_loss,:aep_loss)",
        pml_rows,
    )
    conn.commit()


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)

    build_ep_curve_table(conn)
    pml_rows = compute_pml_summary(conn)
    load_pml_summary_to_sqlite(conn, pml_rows)

    aal = conn.execute("SELECT AVG(annual_aggregate_loss) FROM year_loss_table").fetchone()[0]

    print("=" * 65)
    print("HEADLINE LOSS METRICS - Florida Residential Hurricane Portfolio")
    print("=" * 65)
    print(f"Average Annual Loss (AAL): ${aal:,.0f}")
    print()
    print(f"{'Return Period':>15} | {'OEP (single event)':>20} | {'AEP (annual total)':>20}")
    print("-" * 62)
    for row in pml_rows:
        print(f"{row['return_period_years']:>12}-yr | ${row['oep_loss']:>18,.0f} | ${row['aep_loss']:>18,.0f}")

    conn.close()
