"""Tests for matching XBRL facts to a filing and storing them in SQLite."""

import json
from datetime import date
from pathlib import Path

import httpx

from edgar_extract import db
from edgar_extract.edgar import EdgarClient, Filing, RateLimiter
from edgar_extract.ground_truth import build_ground_truth, find_candidates, pick_ground_truth

FIXTURES = Path(__file__).parent / "fixtures"
ACCESSION = "0000999-24-000001"
FY_END = date(2024, 12, 31)


def load_companyfacts() -> dict:
    return json.loads((FIXTURES / "companyfacts_sample.json").read_text())


def truth_values() -> dict:
    truth = pick_ground_truth(find_candidates(load_companyfacts(), ACCESSION, FY_END))
    return {metric: (fact.value if fact else None) for metric, fact in truth.items()}


def test_picks_current_year_not_prior_year_or_quarter():
    # Prior year (900) and Q4 only (260) are in the same filing but must be ignored.
    assert truth_values()["Revenue"] == 1000


def test_tag_priority_prefers_revenues():
    truth = pick_ground_truth(find_candidates(load_companyfacts(), ACCESSION, FY_END))
    assert truth["Revenue"].xbrl_tag == "Revenues"


def test_balance_sheet_value_at_year_end():
    assert truth_values()["TotalAssets"] == 5000


def test_eps_uses_per_share_unit():
    assert truth_values()["EPS"] == 1.25


def test_missing_metric_is_none():
    assert truth_values()["OperatingIncome"] is None


def test_alternative_tag_is_candidate_but_not_truth():
    candidates = find_candidates(load_companyfacts(), ACCESSION, FY_END)
    assert ("NetIncome", "ProfitLoss") in {(c.metric, c.xbrl_tag) for c in candidates}
    assert truth_values()["NetIncome"] == 100


def test_duplicates_are_removed():
    candidates = find_candidates(load_companyfacts(), ACCESSION, FY_END)
    net_income = [c for c in candidates if c.xbrl_tag == "NetIncomeLoss"]
    assert len(net_income) == 1


def test_other_filing_is_ignored():
    # The 2025 filing repeats the 2024 revenue, but nothing else for that period.
    truth = pick_ground_truth(find_candidates(load_companyfacts(), "0000999-25-000002", FY_END))
    assert truth["Revenue"].value == 1000
    assert truth["TotalAssets"] is None


def test_build_ground_truth_saves_to_sqlite(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=load_companyfacts())

    client = EdgarClient(
        cache_dir=tmp_path / "cache",
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        rate_limiter=RateLimiter(1000, clock=lambda: 0.0, sleep=lambda _: None),
    )
    filing = Filing(
        cik=999,
        form="10-K",
        accession_number=ACCESSION,
        filing_date=date(2025, 2, 15),
        report_date=FY_END,
        primary_document="example-20241231.htm",
    )
    db_path = tmp_path / "test.db"

    build_ground_truth(client, "exmp", filing, db_path=db_path)
    build_ground_truth(client, "exmp", filing, db_path=db_path)  # re-running must not duplicate rows

    with db.connect(db_path) as conn:
        rows = {r["metric"]: r["value"] for r in conn.execute("SELECT metric, value FROM ground_truth")}
        ticker, fiscal_year = conn.execute("SELECT ticker, fiscal_year FROM filings").fetchone()
        n_candidates = conn.execute("SELECT COUNT(*) FROM xbrl_candidates").fetchone()[0]

    assert rows == {"Revenue": 1000, "OperatingIncome": None, "NetIncome": 100, "EPS": 1.25, "TotalAssets": 5000}
    assert (ticker, fiscal_year) == ("EXMP", 2024)
    assert n_candidates == 6  # 2 revenue tags, NetIncomeLoss, ProfitLoss, EPS, Assets
