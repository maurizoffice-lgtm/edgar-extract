"""Export a small, public copy of the results for the dashboard (data/dashboard.db).

The working database stays local. The dashboard copy contains only what the dashboard
shows — no raw model responses, no local file paths — so it can be committed and the
dashboard can be deployed without Ollama, an API key or the SEC cache.

Usage:
    python -m edgar_extract.export_dashboard
"""

import sqlite3
from pathlib import Path

from edgar_extract import db
from edgar_extract.config import DATA_DIR, PROJECT_ROOT

DASHBOARD_DB_PATH = DATA_DIR / "dashboard.db"

# table -> SELECT that fills it (from the working database, attached as "src")
EXPORTS = {
    "filings": "SELECT accession_number, ticker, cik, form, filing_date, report_date, fiscal_year, url FROM src.filings",
    "ground_truth": "SELECT * FROM src.ground_truth",
    "extraction_runs": (
        "SELECT accession_number, model, version, input_tokens, output_tokens, duration_s, cost_usd, format_issues "
        "FROM src.extraction_runs"
    ),
    "extractions": "SELECT * FROM src.extractions",
    "evaluations": "SELECT * FROM src.evaluations",
}


def export(source: Path = db.DB_PATH, target: Path = DASHBOARD_DB_PATH, project_root: Path = PROJECT_ROOT) -> dict[str, int]:
    """Write the dashboard database from scratch. Returns the row count per table."""
    target.unlink(missing_ok=True)
    conn = sqlite3.connect(target)
    try:
        conn.execute("ATTACH DATABASE ? AS src", (str(source),))
        for table, select in EXPORTS.items():
            conn.execute(f"CREATE TABLE {table} AS {select}")

        # The shortened financial statements, so the error browser can show the source rows.
        conn.execute("CREATE TABLE statement_texts (accession_number TEXT PRIMARY KEY, text TEXT NOT NULL)")
        for accession_number, text_path in conn.execute("SELECT accession_number, text_path FROM src.preprocessing").fetchall():
            text = (project_root / text_path).read_text(encoding="utf-8")
            conn.execute("INSERT INTO statement_texts VALUES (?, ?)", (accession_number, text))

        conn.commit()
        conn.execute("DETACH DATABASE src")
        counts = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in [*EXPORTS, "statement_texts"]
        }
        conn.execute("VACUUM")
    finally:
        conn.close()
    return counts


def main() -> None:
    counts = export()
    for table, count in counts.items():
        print(f"{table:16} {count:>5} rows")
    size_kb = DASHBOARD_DB_PATH.stat().st_size / 1000
    print(f"\nWrote {DASHBOARD_DB_PATH.relative_to(PROJECT_ROOT)} ({size_kb:,.0f} kB)")


if __name__ == "__main__":
    main()
