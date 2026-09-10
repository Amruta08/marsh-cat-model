"""
Module 8: Final PDF Loss Report
==================================
Pulls every number in the report directly from SQL (no hardcoded values),
generates two matplotlib charts, and renders everything through a Jinja2
HTML template into a PDF via WeasyPrint. This mirrors the actual deliverable
format a Cat Analyst produces: a client/broker-facing loss report with
headline metrics, methodology, and an explicit limitations section.
"""

import sqlite3
from pathlib import Path
from datetime import date

import matplotlib
matplotlib.use("Agg")  # headless rendering, no display needed
import matplotlib.pyplot as plt
import jinja2
from weasyprint import HTML

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "portfolio.db"
TEMPLATE_DIR = Path(__file__).resolve().parent / "report_template"
FIGURES_DIR = BASE_DIR / "outputs" / "figures"
REPORT_PATH = BASE_DIR / "outputs" / "reports" / "loss_report.pdf"


def fmt_money(x):
    return f"{x:,.0f}"


def build_charts(conn):
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # --- Chart 1: TIV by county ---
    rows = conn.execute("""
        SELECT l.county, SUM(p.total_insured_value)
        FROM locations l JOIN policies p ON p.location_id = l.location_id
        GROUP BY l.county ORDER BY 2 DESC
    """).fetchall()
    counties = [r[0] for r in rows]
    tivs = [r[1] / 1e6 for r in rows]  # $M

    fig, ax = plt.subplots(figsize=(7, 3))
    ax.bar(counties, tivs, color="#0d2b4e")
    ax.set_ylabel("Total Insured Value ($M)")
    ax.set_title("Exposure Concentration by County")
    for i, v in enumerate(tivs):
        ax.text(i, v + 10, f"${v:,.0f}M", ha="center", fontsize=9)
    plt.tight_layout()
    tiv_chart_path = FIGURES_DIR / "tiv_by_county.png"
    plt.savefig(tiv_chart_path, dpi=150)
    plt.close()

    # --- Chart 2: EP curve (OEP and AEP vs return period, log x-axis) ---
    rows = conn.execute("""
        SELECT return_period_years, oep_loss, aep_loss
        FROM pml_summary ORDER BY return_period_years
    """).fetchall()
    return_periods = [r[0] for r in rows]
    oep = [r[1] / 1e6 for r in rows]
    aep = [r[2] / 1e6 for r in rows]

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.plot(return_periods, oep, marker="o", label="OEP (single largest event)", color="#0d2b4e")
    ax.plot(return_periods, aep, marker="s", label="AEP (annual aggregate)", color="#f5a623")
    ax.set_xscale("log")
    ax.set_xlabel("Return Period (years)")
    ax.set_ylabel("Loss ($M)")
    ax.set_title("Exceedance Probability Curves")
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    ep_chart_path = FIGURES_DIR / "ep_curve.png"
    plt.savefig(ep_chart_path, dpi=150)
    plt.close()

    return tiv_chart_path, ep_chart_path


def gather_report_data(conn, tiv_chart_path, ep_chart_path):
    n_locations = conn.execute("SELECT COUNT(*) FROM locations").fetchone()[0]
    total_tiv = conn.execute("SELECT SUM(total_insured_value) FROM policies").fetchone()[0]
    aal = conn.execute("SELECT AVG(annual_aggregate_loss) FROM year_loss_table").fetchone()[0]

    pml_rows = conn.execute("""
        SELECT return_period_years, oep_loss, aep_loss
        FROM pml_summary ORDER BY return_period_years
    """).fetchall()
    pml_table = [{"return_period": r[0], "oep": fmt_money(r[1]), "aep": fmt_money(r[2])} for r in pml_rows]
    pml_100 = next(r for r in pml_rows if r[0] == 100)
    pml_250 = next(r for r in pml_rows if r[0] == 250)

    county_rows = conn.execute("""
        SELECT l.county, COUNT(*), SUM(p.total_insured_value), AVG(p.total_insured_value)
        FROM locations l JOIN policies p ON p.location_id = l.location_id
        GROUP BY l.county ORDER BY 3 DESC
    """).fetchall()
    county_summary = [
        {"county": r[0], "count": r[1], "total_tiv": fmt_money(r[2]), "avg_tiv": fmt_money(r[3])}
        for r in county_rows
    ]

    top_events_rows = conn.execute("""
        SELECT source_storm_id, max_gust_kt, annual_rate, total_insured_loss
        FROM event_loss_table ORDER BY total_insured_loss DESC LIMIT 10
    """).fetchall()
    top_events = [
        {"storm": r[0], "gust": f"{r[1]:.0f}", "rate": f"{r[2]:.6f}", "loss": fmt_money(r[3])}
        for r in top_events_rows
    ]

    return {
        "generation_date": date.today().strftime("%B %d, %Y"),
        "n_locations": n_locations,
        "total_tiv": fmt_money(total_tiv),
        "aal": fmt_money(aal),
        "pml_100_aep": fmt_money(pml_100[2]),
        "pml_250_aep": fmt_money(pml_250[2]),
        "pml_table": pml_table,
        "county_summary": county_summary,
        "top_events": top_events,
        "tiv_chart_path": tiv_chart_path.resolve().as_uri(),
        "ep_curve_chart_path": ep_chart_path.resolve().as_uri(),
    }


def render_pdf(context):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("report_template.html")
    html_content = template.render(**context)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_content, base_url=str(TEMPLATE_DIR)).write_pdf(str(REPORT_PATH))


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)

    tiv_chart_path, ep_chart_path = build_charts(conn)
    print(f"Charts written: {tiv_chart_path.name}, {ep_chart_path.name}")

    context = gather_report_data(conn, tiv_chart_path, ep_chart_path)
    render_pdf(context)
    print(f"\nReport written to: {REPORT_PATH}")

    conn.close()
