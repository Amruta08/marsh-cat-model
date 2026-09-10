"""Quick verification script for Module 1 - run this instead of an inline
python -c command, since multi-line -c strings don't paste reliably into
Windows cmd.exe (each line gets executed as a separate cmd command)."""

import sqlite3

conn = sqlite3.connect("db/portfolio.db")
rows = conn.execute("""
    SELECT county, COUNT(*), ROUND(SUM(total_insured_value))
    FROM locations
    JOIN policies USING(location_id)
    GROUP BY county
""").fetchall()

for row in rows:
    print(row)

conn.close()
