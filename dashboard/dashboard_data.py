"""Data loading and calculations for the dashboard. Reads only data/dashboard.db (read-only).

Kept free of Streamlit so it can be tested, and free of the edgar_extract package so the
dashboard can be deployed on its own (only streamlit, pandas and altair are needed).
"""

import json
import re
import sqlite3
from pathlib import Path

import pandas as pd

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "dashboard.db"

METRICS = ["Revenue", "OperatingIncome", "NetIncome", "EPS", "TotalAssets"]
CORRECT = "correct"
NO_TRUTH = ("no_truth_answered", "no_truth_null")
CATEGORY_LABELS = {
    "correct": "Correct",
    "missing": "Value missing",
    "unit_error": "Unit error",
    "wrong_year": "Wrong year",
    "wrong_metric": "Wrong metric",
    "other": "Other",
    "no_truth_answered": "Answered, but not reported by company",
    "no_truth_null": "Correctly left empty",
}


def _query(db_path: Path, sql: str, params: tuple = ()) -> pd.DataFrame:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def run_label(model: str, version: str) -> str:
    return f"{model} / {version}"


def load_evaluations(db_path: Path = DEFAULT_DB_PATH) -> pd.DataFrame:
    df = _query(db_path, "SELECT * FROM evaluations")
    df["run"] = [run_label(m, v) for m, v in zip(df["model"], df["version"])]
    df["graded"] = df["truth"].notna()
    df["is_correct"] = df["category"] == CORRECT
    return df


def load_runs(db_path: Path = DEFAULT_DB_PATH) -> pd.DataFrame:
    df = _query(db_path, "SELECT * FROM extraction_runs")
    df["format_issue_count"] = df["format_issues"].map(lambda s: len(json.loads(s)))
    df["run"] = [run_label(m, v) for m, v in zip(df["model"], df["version"])]
    return df


def load_statement_text(accession_number: str, db_path: Path = DEFAULT_DB_PATH) -> str:
    df = _query(db_path, "SELECT text FROM statement_texts WHERE accession_number = ?", (accession_number,))
    return df["text"].iloc[0] if len(df) else ""


def run_summary(evals: pd.DataFrame, runs: pd.DataFrame) -> pd.DataFrame:
    """One row per model/version: accuracy on graded values plus speed, cost and format issues."""
    graded = evals[evals["graded"]]
    summary = graded.groupby(["model", "version", "run"], as_index=False).agg(
        correct=("is_correct", "sum"), graded=("is_correct", "size")
    )
    summary["accuracy"] = summary["correct"] / summary["graded"]
    per_run = runs.groupby("run", as_index=False).agg(
        seconds_per_filing=("duration_s", "mean"),
        cost_per_filing=("cost_usd", "mean"),
        input_tokens=("input_tokens", "mean"),
        format_issues=("format_issue_count", "sum"),
    )
    return summary.merge(per_run, on="run", how="left").sort_values(["model", "version"]).reset_index(drop=True)


def accuracy_by(evals: pd.DataFrame, column: str) -> pd.DataFrame:
    """Accuracy per value of `column` (e.g. metric or ticker) and run, as a long table."""
    graded = evals[evals["graded"]]
    out = graded.groupby([column, "run", "model", "version"], as_index=False).agg(
        correct=("is_correct", "sum"), graded=("is_correct", "size")
    )
    out["accuracy"] = out["correct"] / out["graded"]
    return out


ERROR_CATEGORIES = ["missing", "unit_error", "wrong_year", "wrong_metric", "other"]


def error_counts(evals: pd.DataFrame) -> pd.DataFrame:
    """Number of errors per run (rows) and category (columns), graded values only."""
    graded = evals[evals["graded"]]
    errors = graded[~graded["is_correct"]]
    counts = pd.crosstab(errors["run"], errors["category"])
    counts = counts.reindex(index=sorted(graded["run"].unique()), columns=ERROR_CATEGORIES, fill_value=0)
    return counts.rename(columns=CATEGORY_LABELS)


def disagreements(evals: pd.DataFrame, run_a: str, run_b: str) -> pd.DataFrame:
    """Values where exactly one of the two runs is correct."""
    keys = ["accession_number", "ticker", "fiscal_year", "metric", "truth"]
    a = evals[evals["run"] == run_a].set_index(keys)
    b = evals[evals["run"] == run_b].set_index(keys)
    both = a[["value_usd", "category", "is_correct", "graded"]].join(
        b[["value_usd", "category", "is_correct"]], lsuffix="_a", rsuffix="_b", how="inner"
    )
    differ = both[both["graded"] & (both["is_correct_a"] != both["is_correct_b"])]
    return differ.reset_index().sort_values(["ticker", "fiscal_year", "metric"]).reset_index(drop=True)


# ----------------------------------------------------------- source highlighting

_NUMBER = re.compile(r"\(?\$?\d[\d,]*(?:\.\d+)?\)?")


def _numbers(line: str) -> list[float]:
    values = []
    for token in _NUMBER.findall(line):
        try:
            values.append(abs(float(re.sub(r"[,$()]", "", token))))
        except ValueError:
            continue
    return values


def _contains(line: str, targets: list[float]) -> bool:
    return any(abs(n - t) <= 0.005 * abs(t) for n in _numbers(line) for t in targets if t)


def mark_source_lines(text: str, truth: float | None, value: float | None, metric: str) -> list[tuple[str, str]]:
    """Return (marker, line) for every line: "✓" contains the correct value, "▶" the model's value."""
    truth_targets = [] if truth is None else ([abs(truth)] if metric == "EPS" else [abs(truth) / s for s in (1, 1e3, 1e6)])
    value_targets = [] if value is None else [abs(value)]
    marked = []
    for line in text.splitlines():
        is_truth = _contains(line, truth_targets)
        is_value = _contains(line, value_targets)
        marker = "✓▶" if is_truth and is_value else "✓ " if is_truth else "▶ " if is_value else "  "
        marked.append((marker, line))
    return marked


def format_usd(value: float | None, metric: str) -> str:
    if value is None or pd.isna(value):
        return "—"
    if metric == "EPS":
        return f"${value:,.2f}"
    return f"${value / 1e9:,.1f} B"
