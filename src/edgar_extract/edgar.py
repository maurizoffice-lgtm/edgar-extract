"""Client for SEC EDGAR: ticker -> CIK, list 10-K filings, download documents.

SEC fair-access rules (https://www.sec.gov/os/accessing-edgar-data):
- identify yourself with a User-Agent containing name + email
- make at most 10 requests per second

Every response is cached on disk, so nothing is downloaded twice.
To force a refresh (e.g. to see a newly published 10-K), delete the
matching file under data/cache/.
"""

import json
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

from edgar_extract.config import CACHE_DIR, get_sec_user_agent

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/{name}"
ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"

# Stay safely below the SEC limit of 10 requests per second.
MAX_REQUESTS_PER_SECOND = 8

# Some tickers moved to a new legal entity (new CIK) whose filing history starts
# from scratch. Older 10-Ks stay under the predecessor's CIK, so search there too.
PREDECESSOR_CIKS: dict[str, list[int]] = {
    # 2026: Exxon Mobil Corp (34088) became a subsidiary of ExxonMobil Holdings Corp (2115436).
    "XOM": [34088],
}


class Filing(BaseModel):
    """One filing (e.g. a 10-K) as listed by the SEC submissions API."""

    cik: int
    form: str
    accession_number: str  # unique filing id, e.g. "0000320193-24-000123"
    filing_date: date  # when it was submitted to the SEC
    report_date: date  # end of the fiscal period the report covers
    primary_document: str  # file name of the main HTML document

    @property
    def url(self) -> str:
        return ARCHIVES_URL.format(
            cik=self.cik,
            accession=self.accession_number.replace("-", ""),
            document=self.primary_document,
        )


class RateLimiter:
    """Blocks just long enough to keep requests under a fixed rate."""

    def __init__(
        self,
        max_per_second: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.min_interval = 1.0 / max_per_second
        self._clock = clock
        self._sleep = sleep
        self._last: float | None = None

    def wait(self) -> None:
        now = self._clock()
        if self._last is not None:
            delay = self._last + self.min_interval - now
            if delay > 0:
                self._sleep(delay)
                now += delay
        self._last = now


def cache_path_for(url: str, cache_dir: Path) -> Path:
    """Map a URL to a readable file path, e.g. data/cache/www.sec.gov/files/x.json."""
    parsed = urlparse(url)
    return cache_dir / parsed.netloc / parsed.path.lstrip("/")


def parse_ticker_map(data: dict) -> dict[str, int]:
    """Turn company_tickers.json into {"AAPL": 320193, ...}."""
    # Format: {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}
    return {row["ticker"].upper(): int(row["cik_str"]) for row in data.values()}


def parse_filings(cik: int, block: dict, forms: tuple[str, ...] = ("10-K",)) -> list[Filing]:
    """Extract filings of the given form types from a submissions block.

    The SEC stores filings column-wise: one list per field, same index = same filing.
    Amendments (e.g. "10-K/A") are excluded unless asked for explicitly.
    """
    rows = zip(
        block["form"],
        block["accessionNumber"],
        block["filingDate"],
        block["reportDate"],
        block["primaryDocument"],
    )
    return [
        Filing(
            cik=cik,
            form=form,
            accession_number=accession,
            filing_date=filing_date,
            report_date=report_date,
            primary_document=document,
        )
        for form, accession, filing_date, report_date, document in rows
        if form in forms and report_date and document
    ]


class EdgarClient:
    """Fetches data from SEC EDGAR with caching, rate limiting and a proper User-Agent."""

    def __init__(
        self,
        user_agent: str | None = None,
        cache_dir: Path = CACHE_DIR,
        http: httpx.Client | None = None,
        rate_limiter: RateLimiter | None = None,
    ):
        self.cache_dir = Path(cache_dir)
        self.http = http or httpx.Client(
            headers={
                "User-Agent": user_agent or get_sec_user_agent(),
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=30.0,
            follow_redirects=True,
        )
        self.rate_limiter = rate_limiter or RateLimiter(MAX_REQUESTS_PER_SECOND)
        self.request_count = 0  # real network requests (cache hits don't count)

    def fetch(self, url: str) -> bytes:
        """Return the content of a URL, from the cache if we already have it."""
        path = cache_path_for(url, self.cache_dir)
        if path.exists():
            return path.read_bytes()

        self.rate_limiter.wait()
        response = self.http.get(url)
        self.request_count += 1
        response.raise_for_status()

        # Write to a temp file first so an interrupted download never looks complete.
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(path.name + ".part")
        tmp_path.write_bytes(response.content)
        tmp_path.replace(path)
        return response.content

    def fetch_json(self, url: str) -> dict:
        return json.loads(self.fetch(url))

    def get_cik(self, ticker: str) -> int:
        tickers = parse_ticker_map(self.fetch_json(TICKERS_URL))
        try:
            return tickers[ticker.upper()]
        except KeyError:
            raise ValueError(f"Unknown ticker: {ticker}") from None

    def list_10k_filings(self, ticker: str, limit: int | None = None) -> list[Filing]:
        """Return the company's 10-K filings (incl. predecessor entities), newest first."""
        ciks = [self.get_cik(ticker), *PREDECESSOR_CIKS.get(ticker.upper(), [])]
        filings: list[Filing] = []
        for cik in ciks:
            if limit is not None and len(filings) >= limit:
                break
            filings += self._list_10k_filings_for_cik(cik, limit)

        filings.sort(key=lambda f: f.filing_date, reverse=True)
        return filings[:limit] if limit is not None else filings

    def _list_10k_filings_for_cik(self, cik: int, limit: int | None) -> list[Filing]:
        submissions = self.fetch_json(SUBMISSIONS_URL.format(name=f"CIK{cik:010d}.json"))
        filings = parse_filings(cik, submissions["filings"]["recent"])

        # "recent" only holds the latest ~1000 filings. Companies that file a lot
        # (e.g. banks) have their older 10-Ks in extra pages listed under "files".
        for page in submissions["filings"].get("files", []):
            if limit is not None and len(filings) >= limit:
                break
            older = self.fetch_json(SUBMISSIONS_URL.format(name=page["name"]))
            filings += parse_filings(cik, older)
        return filings

    def download(self, filing: Filing) -> Path:
        """Download the filing's main document (if not cached) and return its path."""
        self.fetch(filing.url)
        return cache_path_for(filing.url, self.cache_dir)
