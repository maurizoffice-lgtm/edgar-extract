"""Tests for HTML -> text and locating the financial statements."""

from pathlib import Path

from edgar_extract import db
from edgar_extract.preprocess import (
    STATEMENTS,
    answer_in_text,
    estimate_tokens,
    extract_financial_sections,
    find_statement,
    html_to_text,
    preprocess_filing,
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


def test_answer_in_text_handles_losses_and_decimals():
    text = "Net income (loss) | $(2,722) | $33,364\nTotal revenues | 25,493.7 | 23,182.6"
    assert answer_in_text(-2_722_000_000, "NetIncome", text)  # printed in parentheses
    assert answer_in_text(25_493_700_000, "Revenue", text)  # millions with one decimal
    assert answer_in_text(-0.27, "EPS", "Diluted | $(0.27)")


def _statement(title: str, rows: int = 5, columns: int = 3) -> str:
    numbers = " | ".join(f"{1_000 + i:,}" for i in range(columns))
    body = "\n".join(f"Line item {i} | {numbers}" for i in range(rows))
    return f"{title}\n(In millions)\n{body}\nNet income | {numbers}\nDiluted earnings per share | 1.23 | 1.11\n"


def test_prefers_consolidated_title_over_bigger_summary_table():
    # A quarterly summary table in the management discussion has more numbers than the statement.
    summary = _statement("Income statement", rows=20, columns=8)
    statement = _statement("Consolidated Statement of Income")
    section = find_statement(f"{summary}\n{statement}", INCOME)
    assert section is not None and section.title == "Consolidated Statement of Income"


def test_title_with_trailing_colon_is_a_note_table():
    note = _statement("Consolidated Statements of Income:", rows=20, columns=8)
    statement = _statement("Consolidated Statements of Income")
    section = find_statement(f"{statement}\n{note}", INCOME)
    assert section is not None and section.title == "Consolidated Statements of Income"


def test_results_of_operations_title_needs_its_date():
    heading = _statement("Consolidated Results of Operations", rows=20)  # a heading in the discussion
    statement = _statement("Consolidated Results of Operations for the Years Ended December 31,")
    section = find_statement(f"{heading}\n{statement}", INCOME)
    assert section is not None and section.title.endswith("December 31,")

    balance = "Consolidated Financial Position at December 31,\nTotal assets | 87,764\nTotal liabilities | 68,270\n"
    assert find_statement(balance, BALANCE) is not None


def test_net_loss_income_label_counts_as_net_income():
    statement = _statement("CONSOLIDATED STATEMENTS OF OPERATIONS").replace("Net income", "Net (loss) income")
    section = find_statement(statement, INCOME)
    assert section is not None


def test_quarterly_table_is_not_the_statement():
    statement = _statement("Consolidated Statements of Income (Loss)")
    quarterly = _statement("CONSOLIDATED STATEMENTS OF INCOME (LOSS)", rows=20, columns=8).replace(
        "(In millions)", "Three Months Ended\nMarch 31, | June 30, | September 30, | December 31,"
    )
    section = find_statement(f"{statement}\n{quarterly}", INCOME)
    assert section is not None and section.title == "Consolidated Statements of Income (Loss)"


def test_title_with_footnote_marker():
    balance = "Consolidated Balance Sheets (1)\nTotal assets | 479,843\nTotal liabilities | 438,000\n"
    section = find_statement(balance, BALANCE)
    assert section is not None and section.title == "Consolidated Balance Sheets (1)"


def test_balance_sheet_with_unlabeled_totals():
    balance = (
        "Consolidated Balance Sheet\nTotal current assets | 38,782\n$117,106 | $106,675\n"
        "Total current liabilities | 28,420\n$117,106 | $106,675\n"
    )
    assert find_statement(balance, BALANCE) is not None


def test_statement_continued_on_next_page_is_joined():
    text = (
        "CONSOLIDATED STATEMENTS OF OPERATIONS\n(Amounts in Thousands)\n"
        "Total Revenues | 19,464,307 | 21,878,698\nIncome Before Taxes | 7,099,160 | 5,860,433\n164\n"
        "CONSOLIDATED STATEMENTS OF OPERATIONS (CONTINUED)\n(Amounts in Thousands)\n"
        "Net Income | 6,145,412 | 4,906,037\nDiluted earnings per share | $ 2.34 | $ 3.28\n165\n"
        "CONSOLIDATED STATEMENTS OF CASH FLOWS\nNet Income | 6,145,412 | 4,906,037\n"
    )
    section = find_statement(text, INCOME)
    assert section is not None and section.title == "CONSOLIDATED STATEMENTS OF OPERATIONS"
    kept = text[section.start : section.end]
    assert "Total Revenues" in kept and "Diluted earnings per share" in kept
    assert "CASH FLOWS" not in kept


def test_continued_page_of_another_statement_is_not_joined():
    text = (
        "Consolidated Statements of Income\nNet income | 1,000\nDiluted earnings per share | 1.00\n"
        "Consolidated Statements of Cash Flows (continued)\nNet income | 1,000\n"
    )
    section = find_statement(text, INCOME)
    assert section is not None and "Cash Flows" not in text[section.start : section.end]


def _filing_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.db"
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO filings (accession_number, ticker, cik, form, filing_date, report_date, fiscal_year, "
            "primary_document, url) VALUES ('acc-1', 'X', 1, '10-K', '2026-02-01', '2025-12-31', 2025, 'main.htm', '')"
        )
    return db_path


def test_statements_taken_from_exhibit_when_main_document_has_none(tmp_path, monkeypatch):
    monkeypatch.setattr("edgar_extract.preprocess.PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr("edgar_extract.preprocess.DATA_DIR", tmp_path)
    main_document = tmp_path / "main.htm"
    main_document.write_text("<p>Item 8. Incorporated by reference to the 2025 Annual Report.</p>")
    exhibit = tmp_path / "ex13.htm"
    exhibit.write_bytes((FIXTURES / "mini_10k.htm").read_bytes())
    db_path = _filing_db(tmp_path)

    result = preprocess_filing("acc-1", main_document, db_path, find_exhibit=lambda: exhibit)
    assert result.method == "sections" and result.source_document == "ex13.htm"
    with db.connect(db_path) as conn:
        row = conn.execute("SELECT method, source_document FROM preprocessing").fetchone()
    assert tuple(row) == ("sections", "ex13.htm")


def test_exhibit_is_not_looked_up_when_main_document_has_statements(tmp_path, monkeypatch):
    monkeypatch.setattr("edgar_extract.preprocess.PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr("edgar_extract.preprocess.DATA_DIR", tmp_path)
    main_document = tmp_path / "main.htm"
    main_document.write_bytes((FIXTURES / "mini_10k.htm").read_bytes())

    def find_exhibit():
        raise AssertionError("must not be called")

    result = preprocess_filing("acc-1", main_document, _filing_db(tmp_path), find_exhibit=find_exhibit)
    assert result.source_document == "main.htm"


def test_zero_width_spaces_count_as_empty_cells():
    html = "<table><tr><td>Net income</td><td>​</td><td>$</td><td>1,639</td></tr></table><p>​</p>"
    assert html_to_text(html) == "Net income | $1,639"


def test_title_with_page_number_and_company_name():
    statement = "Net income | 10,593 | 6,023\nDiluted earnings per share | 11.17 | 6.43\n"
    for title in (
        "42 | Consolidated Income Statement Acme Corporation and Subsidiary Companies",
        "46Consolidated Income Statement",
    ):
        section = find_statement(f"{title}\n{statement}", INCOME)
        assert section is not None and section.title == title


def test_long_title_line_ends_the_previous_statement():
    text = (
        "Consolidated Income Statement\nNet income | 10,593\nDiluted earnings per share | 11.17\n"
        "Consolidated Statement of Comprehensive Income Acme Corporation and Subsidiary Companies | 43\n"
        "Other comprehensive income | 1,234\n"
    )
    section = find_statement(text, INCOME)
    assert section is not None and "Other comprehensive income" not in text[section.start : section.end]


def test_balance_sheet_continued_page_is_not_joined():
    text = (
        "Consolidated Balance Sheets\nTotal assets | 410,144\nTotal liabilities | 328,512\n"
        "Consolidated Balance Sheets (Continued)\nBalances of consolidated funds | 93,170\n"
    )
    section = find_statement(text, BALANCE)
    assert section is not None and "consolidated funds" not in text[section.start : section.end]
