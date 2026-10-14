"""Tests for the dashboard export and the dashboard's data functions (no Streamlit needed)."""

import json
import sqlite3

import pytest

import dashboard_data as data
from edgar_extract import db
from edgar_extract.export_dashboard import export

TEXT = "=== INCOME_STATEMENT ===\n(In millions)\nTotal net sales | $416,161 | $391,035\nNet income | 112,010 | 93,736"


@pytest.fixture
def dashboard_db(tmp_path):
    """Working DB with two runs of one filing, exported to a dashboard DB."""
    source = tmp_path / "edgar.db"
    (tmp_path / "acc-1.txt").write_text(TEXT)
    with db.connect(source) as conn:
        conn.execute("INSERT INTO filings VALUES ('acc-1', 'AAPL', 320193, '10-K', '2025-10-31', '2025-09-27', 2025, 'a.htm', 'u')")
        conn.execute(
            "INSERT INTO preprocessing (accession_number, method, sections_found, chars_before, chars_after, "
            "est_tokens_before, est_tokens_after, text_path) VALUES ('acc-1', 'sections', '', 1, 1, 1, 1, 'acc-1.txt')"
        )
        for model, issues in (("big", []), ("small", ["revenue:value_not_a_number"])):
            conn.execute(
                "INSERT INTO extraction_runs VALUES ('acc-1', ?, 'v1', 2500, 300, 10.0, 0.0, ?, 'RAW', datetime('now'))",
                (model, json.dumps(issues)),
            )
        rows = [
            # model, metric, truth, value, value_usd, category
            ("big", "Revenue", 416_161e6, 416_161, 416_161e6, "correct"),
            ("big", "NetIncome", 112_010e6, 112_010, 112_010e6, "correct"),
            ("small", "Revenue", 416_161e6, 391_035, 391_035e6, "wrong_year"),
            ("small", "NetIncome", 112_010e6, 112_010, 112_010e6, "correct"),
            ("small", "OperatingIncome", None, 5, 5e6, "no_truth_answered"),
        ]
        for model, metric, truth, value, usd, category in rows:
            conn.execute(
                "INSERT INTO evaluations VALUES ('acc-1', ?, 'v1', 'AAPL', 2025, ?, ?, ?, 'millions', ?, ?, '', 'q', 1)",
                (model, metric, truth, value, usd, category),
            )
    target = tmp_path / "dashboard.db"
    counts = export(source, target, project_root=tmp_path)
    return target, counts


def test_export_copies_tables_without_raw_responses(dashboard_db):
    target, counts = dashboard_db
    assert counts["evaluations"] == 5
    assert counts["statement_texts"] == 1
    conn = sqlite3.connect(target)
    columns = [r[1] for r in conn.execute("PRAGMA table_info(extraction_runs)")]
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "raw_response" not in columns
    assert "preprocessing" not in tables  # contains local file paths


def test_run_summary(dashboard_db):
    target, _ = dashboard_db
    summary = data.run_summary(data.load_evaluations(target), data.load_runs(target)).set_index("model")
    assert summary.loc["big", "accuracy"] == 1.0
    assert summary.loc["small", "accuracy"] == 0.5  # the OperatingIncome answer has no ground truth
    assert summary.loc["small", "format_issues"] == 1


def test_accuracy_by_metric_and_error_counts(dashboard_db):
    target, _ = dashboard_db
    evals = data.load_evaluations(target)
    per_metric = data.accuracy_by(evals, "metric").set_index(["metric", "model"])
    assert per_metric.loc[("Revenue", "small"), "accuracy"] == 0.0
    counts = data.error_counts(evals)
    assert counts.loc["small / v1", "Wrong year"] == 1
    assert counts.loc["big / v1"].sum() == 0


def test_disagreements(dashboard_db):
    target, _ = dashboard_db
    diff = data.disagreements(data.load_evaluations(target), "big / v1", "small / v1")
    assert list(diff["metric"]) == ["Revenue"]
    assert diff.iloc[0]["category_b"] == "wrong_year"


def test_statement_text_and_marking(dashboard_db):
    target, _ = dashboard_db
    text = data.load_statement_text("acc-1", target)
    assert "Total net sales" in text
    marked = dict((line, marker) for marker, line in data.mark_source_lines(text, 416_161e6, 391_035, "Revenue"))
    assert marked["Total net sales | $416,161 | $391,035"] == "✓▶"
    assert marked["Net income | 112,010 | 93,736"] == "  "


def test_format_usd():
    assert data.format_usd(416_161e6, "Revenue") == "$416.2 B"
    assert data.format_usd(7.46, "EPS") == "$7.46"
    assert data.format_usd(None, "Revenue") == "—"
