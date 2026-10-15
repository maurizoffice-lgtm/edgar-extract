"""Download the latest 10-K filings for a list of companies.

Usage:
    python -m edgar_extract.download                  # development + test companies (see datasets.py)
    python -m edgar_extract.download AAPL MSFT -n 5   # custom tickers / count
"""

import argparse

from edgar_extract.config import PROJECT_ROOT
from edgar_extract.datasets import selection
from edgar_extract.edgar import EdgarClient


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tickers", nargs="*", help="default: all development and test companies")
    parser.add_argument("-n", "--count", type=int, help="10-Ks per company (default 2 for custom tickers)")
    args = parser.parse_args(argv)

    client = EdgarClient()
    for ticker, count in selection(args.tickers, args.count):
        filings = client.list_10k_filings(ticker, limit=count)
        if not filings:
            print(f"{ticker:5} no 10-K filings found")
        for filing in filings:
            path = client.download(filing)
            size_mb = path.stat().st_size / 1_000_000
            print(
                f"{ticker:5} FY ending {filing.report_date}  {filing.accession_number}  "
                f"{size_mb:5.1f} MB  {path.relative_to(PROJECT_ROOT)}"
            )

    print(f"\nDone. {client.request_count} new requests to the SEC (everything else came from the cache).")


if __name__ == "__main__":
    main()
