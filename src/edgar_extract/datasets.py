"""Which companies are used to develop the pipeline and which are held out to test it.

Prompts and post-processing were tuned while looking at the development filings, so
their accuracy is optimistic. The test companies were added afterwards and must never
be used to tune anything — they show how well the pipeline works on unseen companies.
"""

DEVELOPMENT = "development"
TEST = "test"

DEVELOPMENT_TICKERS = ["AAPL", "MSFT", "JNJ", "JPM", "XOM"]
DEVELOPMENT_COUNT = 2  # latest 10-Ks per company

# Mixed industries; incl. a bank (BAC), an insurer (TRV), retailers whose fiscal year
# ends in January/February (WMT, HD), a company reporting in thousands (NFLX) and one
# with losses (BA).
TEST_TICKERS = [
    "NVDA", "GOOGL", "AMZN", "NFLX", "BAC", "TRV", "UNH", "PFE", "WMT", "HD",
    "KO", "PG", "MCD", "CAT", "BA", "CVX", "VZ", "NEE", "V", "DIS",
]  # fmt: skip
TEST_COUNT = 5


def dataset_of(ticker: str) -> str:
    return DEVELOPMENT if ticker.upper() in DEVELOPMENT_TICKERS else TEST


def default_selection() -> list[tuple[str, int]]:
    """(ticker, number of 10-Ks) for both data sets."""
    return [(t, DEVELOPMENT_COUNT) for t in DEVELOPMENT_TICKERS] + [(t, TEST_COUNT) for t in TEST_TICKERS]


def selection(tickers: list[str], count: int | None) -> list[tuple[str, int]]:
    """The command-line choice: given tickers (default count 2), or both data sets if none are given."""
    if not tickers:
        return default_selection()
    return [(t, count or DEVELOPMENT_COUNT) for t in tickers]
