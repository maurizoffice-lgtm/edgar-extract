"""Tests for grading LLM answers and sorting errors into categories."""

import json
import sqlite3

import pandas as pd
import pytest

from edgar_extract import db
from edgar_extract.evaluate import (
    build_report,
    categorize,
    evaluate,
    is_match,
    numbers_in_line,
    quote_in_source,
)

# A tiny income statement in the format produced by the preprocessing step.
TEXT = """=== INCOME_STATEMENT ===
(millions of dollars) | Note | 2024 | 2023
Sales and other operating revenue | 3 | 339,247 | 334,697
Total revenues and other income | 349,585 | 344,582
Net income including noncontrolling interests | 35,063 | 37,354
Net income attributable to the company | 33,680 | 36,010
Earnings per share - assuming dilution (dollars) | 12 | 7.84 | 8.89
=== BALANCE_SHEET ===
Total assets | 453,475 | 376,317"""

REVENUE = 349_585_000_000
NET_INCOME = 33_680_000_000


def test_is_match_uses_half_percent_tolerance():
    assert is_match(100.4, 100)
    assert not is_match(100.6, 100)
    assert not is_match(None, 100)


def test_numbers_in_line():
    assert numbers_in_line("Other expense | (1,234) | $7.84 | 12") == [1234, 7.84, 12]


def check(metric, truth, value, unit, scale=1e6, **kwargs):
    value_usd = value * scale if value is not None else None
    return categorize(metric, truth, value, unit, value_usd, TEXT, **kwargs)


def test_correct():
    assert check("Revenue", REVENUE, 349_585, "millions").category == "correct"


def test_missing():
    assert check("Revenue", REVENUE, None, None).category == "missing"


def test_unit_error():
    verdict = check("Revenue", REVENUE, 349_585, "thousands", scale=1e3)
    assert verdict.category == "unit_error"
    assert "millions" in verdict.detail


def test_wrong_year():
    verdict = check("Revenue", REVENUE, 344_582, "millions")
    assert verdict.category == "wrong_year"


def test_note_number_is_other():
    # The real Exxon case: the model took the note reference "12" instead of 7.84.
    verdict = check("EPS", 7.84, 12, "per share", scale=1)
    assert verdict.category == "other"
    assert "note" in verdict.detail


def test_wrong_metric_other_row():
    verdict = check("Revenue", REVENUE, 339_247, "millions")
    assert verdict.category == "wrong_metric"
    assert "Sales and other operating revenue" in verdict.detail


def test_wrong_metric_alternative_xbrl_tag():
    verdict = check("NetIncome", NET_INCOME, 35_063, "millions", alternatives={"ProfitLoss": 35_063_000_000})
    assert verdict.category == "wrong_metric"
    assert "ProfitLoss" in verdict.detail


def test_number_not_in_text_is_other():
    assert check("Revenue", REVENUE, 123_456, "millions").category == "other"


def test_no_ground_truth():
    assert check("OperatingIncome", None, None, None).category == "no_truth_null"
    assert check("OperatingIncome", None, 32_581, "millions").category == "no_truth_answered"


@pytest.mark.parametrize(
    "quote, expected",
    [
        ("Total revenues and other income | 349,585", True),
        ("total revenues and other income 349,585", True),  # case, "|" and spacing don't matter
        ("Total revenue for the year ended 2024", False),  # paraphrased
        ("", False),
    ],
)
def test_quote_in_source(quote, expected):
    assert quote_in_source(quote, TEXT) is expected


@pytest.fixture
def small_db(tmp_path, monkeypatch):
    """A database with one filing, ground truth and one extraction run."""
    db_path = tmp_path / "test.db"
    text_path = tmp_path / "acc-1.txt"
    text_path.write_text(TEXT)
    monkeypatch.setattr("edgar_extract.evaluate.PROJECT_ROOT", tmp_path)

    with db.connect(db_path) as conn:
        conn.execute("INSERT INTO filings VALUES ('acc-1', 'XOM', 34088, '10-K', '2025-02-19', '2024-12-31', 2024, 'x.htm', 'u')")
        conn.execute("INSERT INTO preprocessing (accession_number, method, sections_found, chars_before, chars_after, est_tokens_before, est_tokens_after, text_path) VALUES ('acc-1', 'sections', '', 1, 1, 1, 1, 'acc-1.txt')")
        truth = {"Revenue": REVENUE, "OperatingIncome": None, "NetIncome": NET_INCOME, "EPS": 7.84, "TotalAssets": 453_475_000_000}
        for metric, value in truth.items():
            conn.execute("INSERT INTO ground_truth (accession_number, metric, value, xbrl_tag) VALUES ('acc-1', ?, ?, ?)", (metric, value, "Tag" if value else None))
        conn.execute("INSERT INTO extraction_runs VALUES ('acc-1', 'm', 'v1', 2500, 300, 15.0, 0.0, ?, '{}', datetime('now'))", (json.dumps(["revenue:value_not_a_number"]),))
        answers = [
            ("Revenue", 349_585, "millions", REVENUE, "Total revenues and other income | 349,585"),
            ("OperatingIncome", None, None, None, ""),
            ("NetIncome", 33_680, "millions", NET_INCOME, "Net income for the year"),
            ("EPS", 12, "per share", 12, "Earnings per share | 12"),
            # TotalAssets missing entirely (model skipped it)
        ]
        for metric, value, unit, usd, quote in answers:
            conn.execute("INSERT INTO extractions VALUES ('acc-1', 'm', 'v1', ?, ?, ?, ?, ?)", (metric, value, unit, usd, quote))
    return db_path


def test_evaluate_grades_and_stores(small_db):
    df = evaluate(small_db).set_index("metric")
    assert df.loc["Revenue", "category"] == "correct"
    assert df.loc["OperatingIncome", "category"] == "no_truth_null"
    assert df.loc["EPS", "category"] == "other"
    assert df.loc["TotalAssets", "category"] == "missing"
    assert df.loc["Revenue", "quote_in_source"] is True
    assert df.loc["NetIncome", "quote_in_source"] is False

    with db.connect(small_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0] == 5


def test_report_contains_sections(small_db):
    evals = evaluate(small_db)
    runs = pd.DataFrame(
        [{"model": "m", "version": "v1", "input_tokens": 2500, "output_tokens": 300,
          "duration_s": 15.0, "cost_usd": 0.0, "format_issue_count": 1, "code_correction_count": 0,
          "dataset": "development"}]
    )  # fmt: skip
    report = build_report(evals, runs)
    assert "| m / v1 | 50% (2/4)" in report  # Revenue + NetIncome right, EPS + TotalAssets wrong
    assert "## Error categories" in report
    assert "Value missing" in report
    assert "0 of 1 answered anyway" in report


def test_report_separates_data_sets(small_db):
    evals = evaluate(small_db)
    assert set(evals["dataset"]) == {"development"}  # XOM was used for development
    test_evals = evals.assign(dataset="test", ticker="NFLX")
    test2_evals = evals.assign(dataset="test2", ticker="INTC")
    runs = pd.DataFrame(
        [{"model": "m", "version": "v1", "input_tokens": 2500, "output_tokens": 300, "duration_s": 15.0,
          "cost_usd": 0.0, "format_issue_count": 0, "code_correction_count": 2, "dataset": dataset}
         for dataset in ("development", "test", "test2")]
    )  # fmt: skip
    report = build_report(pd.concat([test2_evals, evals, test_evals]), runs)
    assert "**Test set 1:** 1 filings from 1 companies (NFLX)" in report
    assert "**Test set 2:** 1 filings from 1 companies (INTC)" in report
    assert "| Development | m / v1 | 50% (2/4)" in report
    assert "| Test set 2 | m / v1 | 50% (2/4)" in report
    assert "m / v1 · Development | m / v1 · Test set 1 | m / v1 · Test set 2" in report  # per-metric columns
    assert "Code corrections" in report


def test_old_database_gets_dataset_column(tmp_path):
    db_path = tmp_path / "old.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE evaluations (accession_number TEXT, metric TEXT)")  # created before "dataset" existed
    conn.close()
    with db.connect(db_path) as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(evaluations)")}
    assert "dataset" in columns
