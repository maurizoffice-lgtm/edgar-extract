"""SQLite storage. One file (data/edgar.db) holds filings, ground truth and the LLM results."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from edgar_extract.config import DATA_DIR
from edgar_extract.edgar import Filing

if TYPE_CHECKING:
    from edgar_extract.extract import MetricAnswer
    from edgar_extract.ground_truth import Fact
    from edgar_extract.llm import LLMResponse

DB_PATH = DATA_DIR / "edgar.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS filings (
    accession_number TEXT PRIMARY KEY,
    ticker           TEXT NOT NULL,
    cik              INTEGER NOT NULL,
    form             TEXT NOT NULL,
    filing_date      TEXT NOT NULL,
    report_date      TEXT NOT NULL,  -- fiscal year end
    fiscal_year      INTEGER NOT NULL,  -- calendar year of the fiscal year end
    primary_document TEXT NOT NULL,
    url              TEXT NOT NULL
);

-- The correct value per filing and metric. value IS NULL = not reported in XBRL.
CREATE TABLE IF NOT EXISTS ground_truth (
    accession_number TEXT NOT NULL REFERENCES filings(accession_number),
    metric           TEXT NOT NULL,
    value            REAL,
    unit             TEXT,
    xbrl_tag         TEXT,
    period_start     TEXT,
    period_end       TEXT,
    PRIMARY KEY (accession_number, metric)
);

-- Every matching XBRL value, incl. alternative tags. Used to explain LLM errors.
CREATE TABLE IF NOT EXISTS xbrl_candidates (
    accession_number TEXT NOT NULL REFERENCES filings(accession_number),
    metric           TEXT NOT NULL,
    xbrl_tag         TEXT NOT NULL,
    value            REAL NOT NULL,
    unit             TEXT NOT NULL,
    period_start     TEXT,
    period_end       TEXT NOT NULL,
    PRIMARY KEY (accession_number, metric, xbrl_tag)
);

-- How each 10-K was shortened before going to the LLM. Token numbers are estimates.
CREATE TABLE IF NOT EXISTS preprocessing (
    accession_number  TEXT PRIMARY KEY REFERENCES filings(accession_number),
    method            TEXT NOT NULL,  -- "sections" or "full_text" (fallback)
    sections_found    TEXT NOT NULL,  -- comma-separated, e.g. "income_statement,balance_sheet"
    chars_before      INTEGER NOT NULL,
    chars_after       INTEGER NOT NULL,
    est_tokens_before INTEGER NOT NULL,
    est_tokens_after  INTEGER NOT NULL,
    text_path         TEXT NOT NULL,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

-- One LLM call per filing, model and prompt version.
CREATE TABLE IF NOT EXISTS extraction_runs (
    accession_number TEXT NOT NULL REFERENCES filings(accession_number),
    model            TEXT NOT NULL,
    prompt_version   TEXT NOT NULL,
    input_tokens     INTEGER NOT NULL,
    output_tokens    INTEGER NOT NULL,
    duration_s       REAL NOT NULL,
    cost_usd         REAL NOT NULL,
    format_issues    TEXT NOT NULL,  -- JSON list, e.g. ["revenue:value_not_a_number"]
    raw_response     TEXT NOT NULL,  -- full JSON answer of the model, for debugging
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (accession_number, model, prompt_version)
);

-- The model's answer per metric. value_usd = value × unit scale, computed in code.
CREATE TABLE IF NOT EXISTS extractions (
    accession_number TEXT NOT NULL,
    model            TEXT NOT NULL,
    prompt_version   TEXT NOT NULL,
    metric           TEXT NOT NULL,
    value            REAL,
    unit             TEXT,
    value_usd        REAL,
    quote            TEXT NOT NULL,
    PRIMARY KEY (accession_number, model, prompt_version, metric),
    FOREIGN KEY (accession_number, model, prompt_version)
        REFERENCES extraction_runs(accession_number, model, prompt_version)
);
"""


@contextmanager
def connect(path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    """Open the database, create tables if needed, commit on success and always close."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_filing(conn: sqlite3.Connection, ticker: str, filing: Filing) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO filings
            (accession_number, ticker, cik, form, filing_date, report_date, fiscal_year, primary_document, url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            filing.accession_number,
            ticker.upper(),
            filing.cik,
            filing.form,
            filing.filing_date.isoformat(),
            filing.report_date.isoformat(),
            filing.report_date.year,
            filing.primary_document,
            filing.url,
        ),
    )


def save_ground_truth(
    conn: sqlite3.Connection,
    accession_number: str,
    truth: "dict[str, Fact | None]",
    candidates: "list[Fact]",
) -> None:
    """Replace all ground-truth rows of one filing (safe to re-run)."""
    conn.execute("DELETE FROM ground_truth WHERE accession_number = ?", (accession_number,))
    conn.execute("DELETE FROM xbrl_candidates WHERE accession_number = ?", (accession_number,))

    for metric, fact in truth.items():
        conn.execute(
            "INSERT INTO ground_truth VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                accession_number,
                metric,
                fact.value if fact else None,
                fact.unit if fact else None,
                fact.xbrl_tag if fact else None,
                _iso(fact.period_start) if fact else None,
                _iso(fact.period_end) if fact else None,
            ),
        )
    for fact in candidates:
        conn.execute(
            "INSERT INTO xbrl_candidates VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                accession_number,
                fact.metric,
                fact.xbrl_tag,
                fact.value,
                fact.unit,
                _iso(fact.period_start),
                _iso(fact.period_end),
            ),
        )


def save_preprocessing(
    conn: sqlite3.Connection,
    *,
    accession_number: str,
    method: str,
    sections_found: list[str],
    chars_before: int,
    chars_after: int,
    est_tokens_before: int,
    est_tokens_after: int,
    text_path: str,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO preprocessing
            (accession_number, method, sections_found, chars_before, chars_after,
             est_tokens_before, est_tokens_after, text_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            accession_number,
            method,
            ",".join(sections_found),
            chars_before,
            chars_after,
            est_tokens_before,
            est_tokens_after,
            text_path,
        ),
    )


def save_extraction(
    conn: sqlite3.Connection,
    accession_number: str,
    prompt_version: str,
    response: "LLMResponse",
    answers: "list[MetricAnswer]",
    format_issues: list[str],
) -> None:
    """Replace the run and answers of one filing/model/prompt version (safe to re-run)."""
    key = (accession_number, response.model, prompt_version)
    conn.execute("DELETE FROM extractions WHERE accession_number = ? AND model = ? AND prompt_version = ?", key)
    conn.execute("DELETE FROM extraction_runs WHERE accession_number = ? AND model = ? AND prompt_version = ?", key)
    conn.execute(
        """
        INSERT INTO extraction_runs
            (accession_number, model, prompt_version, input_tokens, output_tokens,
             duration_s, cost_usd, format_issues, raw_response)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            *key,
            response.input_tokens,
            response.output_tokens,
            response.duration_s,
            response.cost_usd,
            json.dumps(format_issues),
            json.dumps(response.raw),
        ),
    )
    for answer in answers:
        conn.execute(
            "INSERT INTO extractions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (*key, answer.metric, answer.value, answer.unit, answer.value_usd, answer.quote),
        )


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None
