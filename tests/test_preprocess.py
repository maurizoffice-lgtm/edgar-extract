"""Tests for HTML -> text and locating the financial statements."""

from pathlib import Path

from edgar_extract.preprocess import (
    STATEMENTS,
    answer_in_text,
    estimate_tokens,
    extract_financial_sections,
    find_statement,
    html_to_text,
)

FIXTURES = Path(__file__).parent / "fixtures"
INCOME, BALANCE = STATEMENTS


def mini_text() -> str:
    return html_to_text((FIXTURES / "mini_10k.htm").read_bytes())


def test_html_to_text_removes_hidden_parts():
    text = mini_text()
    assert "Hidden XBRL header" not in text
    assert ".x{color:red}" not in text


def test_table_cells_are_glued_together():
    text = mini_text()
    assert "Net sales | $1,000 | $900" in text
    assert "Other expense | (21) | (5)" in text


def test_paragraph_stays_on_one_line():
    # Neither inline <span> nor a line break in the HTML source may split a paragraph.
    assert (
        "Item 7. As shown in the Consolidated Statements of Operations, net income increased. "
        "Total assets are discussed in the Consolidated Balance Sheets section of this report."
    ) in mini_text().splitlines()


def test_finds_real_income_statement_not_toc_sentence_or_parent():
    section = find_statement(mini_text(), INCOME)
    assert section is not None
    assert section.title == "CONSOLIDATED STATEMENTS OF OPERATIONS"
    body = mini_text()[section.start : section.end]
    assert "Net income | $150 | $140" in body
    assert "Comprehensive income" not in body  # stops at the next statement


def test_finds_balance_sheet_without_consolidated_in_title():
    section = find_statement(mini_text(), BALANCE)
    assert section is not None
    assert section.title == "BALANCE SHEETS"
    assert "Net cash from operations" not in mini_text()[section.start : section.end]


def test_extract_financial_sections():
    result = extract_financial_sections(mini_text())
    assert result.method == "sections"
    assert result.sections_found == ["income_statement", "balance_sheet"]
    assert result.text.startswith("=== INCOME_STATEMENT ===")
    assert len(result.text) < result.full_text_chars


def test_fallback_to_full_text_when_nothing_found():
    text = "Just a letter to shareholders.\nNo tables here."
    result = extract_financial_sections(text)
    assert result.method == "full_text"
    assert result.text == text


def test_answer_in_text_handles_units():
    text = "Net sales | $1,000 | $900\nTotal assets | 5,000\nDiluted | $1.25"
    assert answer_in_text(1_000_000_000, "Revenue", text)  # reported in millions
    assert answer_in_text(1.25, "EPS", text)
    assert not answer_in_text(2_000_000_000, "Revenue", text)
    assert not answer_in_text(100_000_000, "Revenue", text)  # "100" must not match inside "1000"


def test_estimate_tokens():
    assert estimate_tokens(4_000) == 1_000
