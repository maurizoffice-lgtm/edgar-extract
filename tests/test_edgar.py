"""Tests for the EDGAR client. No real network: HTTP is faked with httpx.MockTransport."""

import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from edgar_extract import edgar
from edgar_extract.edgar import (
    EdgarClient,
    Filing,
    RateLimiter,
    cache_path_for,
    parse_filings,
    parse_ticker_map,
)

FIXTURES = Path(__file__).parent / "fixtures"
TICKERS_JSON = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
}


def load_submissions() -> dict:
    return json.loads((FIXTURES / "submissions_sample.json").read_text())


def make_client(tmp_path: Path, handler) -> EdgarClient:
    http = httpx.Client(transport=httpx.MockTransport(handler), headers={"User-Agent": "Test test@example.org"})
    no_wait = RateLimiter(1000, clock=lambda: 0.0, sleep=lambda _: None)
    return EdgarClient(cache_dir=tmp_path, http=http, rate_limiter=no_wait)


def fake_sec(requests_seen: list[httpx.Request]):
    """A tiny fake SEC server that answers the three kinds of URLs we use."""

    def handler(request: httpx.Request) -> httpx.Response:
        requests_seen.append(request)
        url = str(request.url)
        if url.endswith("company_tickers.json"):
            return httpx.Response(200, json=TICKERS_JSON)
        if "/submissions/CIK0000320193.json" in url:
            return httpx.Response(200, json=load_submissions())
        if "/Archives/" in url:
            return httpx.Response(200, content=b"<html>10-K</html>")
        return httpx.Response(404)

    return handler


def test_parse_ticker_map():
    assert parse_ticker_map(TICKERS_JSON) == {"AAPL": 320193, "MSFT": 789019}


def test_parse_filings_keeps_only_10k_without_amendments():
    filings = parse_filings(320193, load_submissions()["filings"]["recent"])
    assert [f.accession_number for f in filings] == ["0000320193-24-000123", "0000320193-23-000106"]
    assert filings[0].report_date == date(2024, 9, 28)


def test_filing_url():
    filing = Filing(
        cik=320193,
        form="10-K",
        accession_number="0000320193-24-000123",
        filing_date=date(2024, 11, 1),
        report_date=date(2024, 9, 28),
        primary_document="aapl-20240928.htm",
    )
    assert filing.url == "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm"


def test_cache_path_is_readable(tmp_path):
    path = cache_path_for("https://data.sec.gov/submissions/CIK0000320193.json", tmp_path)
    assert path == tmp_path / "data.sec.gov" / "submissions" / "CIK0000320193.json"


def test_rate_limiter_waits_between_calls():
    fake_time = [0.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        fake_time[0] += seconds

    limiter = RateLimiter(10, clock=lambda: fake_time[0], sleep=sleep)
    limiter.wait()  # first call: no wait
    limiter.wait()  # immediately again: must wait 0.1 s
    assert sleeps == [pytest.approx(0.1)]


def test_list_and_download_use_cache(tmp_path):
    seen: list[httpx.Request] = []
    client = make_client(tmp_path, fake_sec(seen))

    filings = client.list_10k_filings("aapl", limit=1)
    assert len(filings) == 1
    path = client.download(filings[0])
    assert path.read_bytes() == b"<html>10-K</html>"
    first_run = len(seen)
    assert first_run == 3  # tickers + submissions + document

    # Second time: everything comes from the cache, no new requests.
    client.download(client.list_10k_filings("AAPL", limit=1)[0])
    assert len(seen) == first_run
    assert seen[0].headers["User-Agent"] == "Test test@example.org"


def test_predecessor_cik_is_searched(tmp_path, monkeypatch):
    # NEWCO is a fresh holding company without 10-Ks; its predecessor has them.
    monkeypatch.setitem(edgar.PREDECESSOR_CIKS, "NEWCO", [320193])
    empty = {"filings": {"recent": {k: [] for k in load_submissions()["filings"]["recent"]}, "files": []}}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("company_tickers.json"):
            return httpx.Response(200, json={"0": {"cik_str": 999, "ticker": "NEWCO", "title": "NewCo"}})
        if "/submissions/CIK0000000999.json" in url:
            return httpx.Response(200, json=empty)
        return fake_sec([])(request)

    filings = make_client(tmp_path, handler).list_10k_filings("NEWCO", limit=2)
    assert [f.cik for f in filings] == [320193, 320193]


def test_unknown_ticker_raises(tmp_path):
    client = make_client(tmp_path, fake_sec([]))
    with pytest.raises(ValueError, match="Unknown ticker"):
        client.get_cik("NOPE")


def test_http_error_is_not_cached(tmp_path):
    client = make_client(tmp_path, lambda request: httpx.Response(500))
    with pytest.raises(httpx.HTTPStatusError):
        client.fetch("https://www.sec.gov/files/company_tickers.json")
    assert not any(tmp_path.rglob("*.json"))
