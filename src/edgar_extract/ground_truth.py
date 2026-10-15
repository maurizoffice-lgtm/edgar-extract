"""Ground truth: the correct metric values for each 10-K, taken from XBRL data.

Companies also file their financial statements in machine-readable form (XBRL).
The SEC "companyfacts" API returns every reported value of a company, tagged with
the filing (accession number) it came from. For each 10-K we keep only values that
1. come from that exact filing (accession number),
2. end on the filing's fiscal-year end date (10-Ks also repeat prior years), and
3. cover roughly one year (not a quarter) for income-statement metrics.

Usage:
    python -m edgar_extract.ground_truth              # development + test companies (see datasets.py)
    python -m edgar_extract.ground_truth AAPL -n 5
"""

import argparse
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from pydantic import BaseModel

from edgar_extract import db
from edgar_extract.datasets import selection
from edgar_extract.edgar import EdgarClient, Filing

COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

# A fiscal year is 52/53 weeks or 12 months; anything else is a quarter, half year, etc.
MIN_YEAR_DAYS = 350
MAX_YEAR_DAYS = 380


@dataclass(frozen=True)
class MetricSpec:
    tags: list[str]  # us-gaap tags in priority order; the first one found is the ground truth
    unit: str
    is_duration: bool  # True = over a period (income statement), False = at a point in time (balance sheet)
    alternative_tags: list[str] = field(default_factory=list)  # related values, stored for error analysis only


METRICS: dict[str, MetricSpec] = {
    "Revenue": MetricSpec(
        tags=[
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
            "SalesRevenueNet",
            "RevenuesNetOfInterestExpense",
        ],
        unit="USD",
        is_duration=True,
    ),
    "OperatingIncome": MetricSpec(tags=["OperatingIncomeLoss"], unit="USD", is_duration=True),
    "NetIncome": MetricSpec(
        tags=["NetIncomeLoss"],
        unit="USD",
        is_duration=True,
        # Includes the share of minority owners; often confused with NetIncome.
        alternative_tags=["ProfitLoss"],
    ),
    "EPS": MetricSpec(tags=["EarningsPerShareDiluted"], unit="USD/shares", is_duration=True),
    "TotalAssets": MetricSpec(tags=["Assets"], unit="USD", is_duration=False),
}


class Fact(BaseModel):
    """One XBRL value that matches a filing's fiscal year."""

    metric: str
    xbrl_tag: str
    value: float
    unit: str
    period_start: date | None
    period_end: date


def _matches_period(entry: dict, spec: MetricSpec, period_end: date) -> bool:
    if entry["end"] != period_end.isoformat():
        return False
    if not spec.is_duration:
        return "start" not in entry
    if "start" not in entry:
        return False
    days = (period_end - date.fromisoformat(entry["start"])).days
    return MIN_YEAR_DAYS <= days <= MAX_YEAR_DAYS


def find_candidates(companyfacts: dict, accession_number: str, period_end: date) -> list[Fact]:
    """All values for our metrics (incl. alternative tags) that belong to this filing's fiscal year."""
    gaap = companyfacts.get("facts", {}).get("us-gaap", {})
    candidates: dict[tuple[str, str], Fact] = {}
    for metric, spec in METRICS.items():
        for tag in spec.tags + spec.alternative_tags:
            entries = gaap.get(tag, {}).get("units", {}).get(spec.unit, [])
            for entry in entries:
                if entry["accn"] != accession_number or not _matches_period(entry, spec, period_end):
                    continue
                # The same value can be listed more than once; keep the first.
                candidates.setdefault(
                    (metric, tag),
                    Fact(
                        metric=metric,
                        xbrl_tag=tag,
                        value=entry["val"],
                        unit=spec.unit,
                        period_start=entry.get("start"),
                        period_end=entry["end"],
                    ),
                )
    return list(candidates.values())


def pick_ground_truth(candidates: list[Fact]) -> dict[str, Fact | None]:
    """Choose one value per metric, following the tag priority. None = not reported."""
    by_key = {(fact.metric, fact.xbrl_tag): fact for fact in candidates}
    result: dict[str, Fact | None] = {}
    for metric, spec in METRICS.items():
        result[metric] = next((by_key[(metric, tag)] for tag in spec.tags if (metric, tag) in by_key), None)
    return result


def build_ground_truth(
    client: EdgarClient, ticker: str, filing: Filing, db_path: Path = db.DB_PATH
) -> dict[str, Fact | None]:
    """Fetch XBRL facts for one filing, pick the ground truth and save both to SQLite."""
    companyfacts = client.fetch_json(COMPANYFACTS_URL.format(cik=filing.cik))
    candidates = find_candidates(companyfacts, filing.accession_number, filing.report_date)
    truth = pick_ground_truth(candidates)

    with db.connect(db_path) as conn:
        db.save_filing(conn, ticker, filing)
        db.save_ground_truth(conn, filing.accession_number, truth, candidates)
    return truth


def _format(fact: Fact | None) -> str:
    if fact is None:
        return "—"
    if fact.unit == "USD/shares":
        return f"{fact.value:.2f}"
    return f"{fact.value / 1e9:,.1f}B"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tickers", nargs="*", help="default: all development and test companies")
    parser.add_argument("-n", "--count", type=int, help="10-Ks per company (default 2 for custom tickers)")
    args = parser.parse_args(argv)

    client = EdgarClient()
    print(f"{'Ticker':6} {'FY end':10} " + " ".join(f"{m:>15}" for m in METRICS))
    for ticker, count in selection(args.tickers, args.count):
        for filing in client.list_10k_filings(ticker, limit=count):
            truth = build_ground_truth(client, ticker, filing)
            print(f"{ticker:6} {filing.report_date!s:10} " + " ".join(f"{_format(truth[m]):>15}" for m in METRICS))

    print(f"\nSaved to {db.DB_PATH.name}. {client.request_count} new requests to the SEC.")
    print("— = the company does not report this metric in XBRL (no ground truth).")


if __name__ == "__main__":
    main()
