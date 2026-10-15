"""Tests for the split into development companies and test sets 1 and 2."""

from edgar_extract.datasets import (
    DEVELOPMENT,
    DEVELOPMENT_TICKERS,
    TEST,
    TEST2,
    TEST_COUNT,
    TEST_TICKERS,
    dataset_of,
    default_selection,
    selection,
)


def test_sets_do_not_overlap():
    assert not set(DEVELOPMENT_TICKERS) & set(TEST_TICKERS)


def test_dataset_of():
    assert dataset_of("aapl") == DEVELOPMENT
    assert dataset_of("NFLX") == TEST
    assert dataset_of("INTC") == TEST2
    assert dataset_of("ZZZZ") == TEST2  # any company not listed is unseen


def test_selection():
    assert selection([], None) == default_selection()
    assert ("NFLX", TEST_COUNT) in default_selection()
    assert selection(["AAPL"], None) == [("AAPL", 2)]
    assert selection(["AAPL"], 5) == [("AAPL", 5)]
