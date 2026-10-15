"""Which companies are used to develop the pipeline and which are held out to test it.

Prompts and post-processing were tuned while looking at the development filings, so
their accuracy is optimistic. The test companies were added afterwards to show how well
the pipeline works on unseen companies.

Test set 1 was used to find the error types that v4 targets, so from v4 on it is "seen"
as well. Test set 2 was added only after v4 had been written and is the honest measure
for v4; it must never be used to tune anything.
"""

DEVELOPMENT = "development"
TEST = "test"  # test set 1 (held out until v3; its errors were studied for v4)
TEST2 = "test2"  # test set 2 (held out; added for v4)

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

# Chosen before running v4 on them: several companies with losses or noncontrolling
# interests (the two error types v4 targets), a bank (GS), an insurer (AIG), fiscal
# years ending in May (ORCL, NKE) or August/September (COST), and ordinary cases (LLY, LMT).
TEST2_TICKERS = [
    "INTC", "T", "CMCSA", "UBER", "WBD", "MRNA", "F", "DUK", "AIG", "GS",
    "COST", "ORCL", "NKE", "LLY", "LMT",
]  # fmt: skip
TEST2_COUNT = 5

DATASETS = [DEVELOPMENT, TEST, TEST2]


def dataset_of(ticker: str) -> str:
    """Data set of a company. Any company not listed is unseen, like test set 2."""
    ticker = ticker.upper()
    if ticker in DEVELOPMENT_TICKERS:
        return DEVELOPMENT
    if ticker in TEST_TICKERS:
        return TEST
    return TEST2


def default_selection() -> list[tuple[str, int]]:
    """(ticker, number of 10-Ks) for all data sets."""
    return (
        [(t, DEVELOPMENT_COUNT) for t in DEVELOPMENT_TICKERS]
        + [(t, TEST_COUNT) for t in TEST_TICKERS]
        + [(t, TEST2_COUNT) for t in TEST2_TICKERS]
    )


def selection(tickers: list[str], count: int | None) -> list[tuple[str, int]]:
    """The command-line choice: given tickers (default count 2), or all data sets if none are given."""
    if not tickers:
        return default_selection()
    return [(t, count or DEVELOPMENT_COUNT) for t in tickers]
