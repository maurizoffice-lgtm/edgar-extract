"""Tests for the split into development companies and test sets 1, 2 and 3."""

from edgar_extract.datasets import (
    DEVELOPMENT,
    DEVELOPMENT_TICKERS,
    TEST,
    TEST2,
    TEST2_TICKERS,
    TEST3,
    TEST3_TICKERS,
    TEST_COUNT,
    TEST_TICKERS,
    dataset_of,
    default_selection,
    selection,
)


def test_sets_do_not_overlap():
    sets = [set(DEVELOPMENT_TICKERS), set(TEST_TICKERS), set(TEST2_TICKERS), set(TEST3_TICKERS)]
    assert sum(len(s) for s in sets) == len(set().union(*sets))


def test_dataset_of():
    assert dataset_of("aapl") == DEVELOPMENT
    assert dataset_of("NFLX") == TEST
    assert dataset_of("INTC") == TEST2
    assert dataset_of("MS") == TEST3
    assert dataset_of("ZZZZ") == TEST3  # any company not listed is unseen


def test_selection():
    assert selection([], None) == default_selection()
    assert ("NFLX", TEST_COUNT) in default_selection()
    assert selection(["AAPL"], None) == [("AAPL", 2)]
    assert selection(["AAPL"], 5) == [("AAPL", 5)]
