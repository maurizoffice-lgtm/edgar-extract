"""Tests for the LLM extraction. No real model: Ollama is faked with httpx.MockTransport."""

import json
from datetime import date

import httpx
import pytest

from edgar_extract import db
from edgar_extract.extract import (
    COMMON_CORRECTED,
    NONCONTROLLING_CORRECTED,
    PRETAX_REMOVED,
    VERSIONS,
    MetricAnswer,
    apply_common_check,
    apply_detected_units,
    apply_noncontrolling_check,
    build_prompt,
    detect_scales,
    build_tool,
    drop_pretax,
    extract_filing,
    fill_missing,
    is_code_correction,
    normalize_unit,
    parse_number,
    parse_tool_arguments,
    remove_common_adjustments,
    remove_noncontrolling,
    row_cells,
)
from edgar_extract.llm import LLMUnavailableError, OllamaClient

GOOD_ARGUMENTS = {
    "revenue": {"value": 416161, "unit": "millions", "quote": "Total net sales | 416,161"},
    "operating_income": {"value": "133,050", "unit": "In millions", "quote": "Operating income | 133,050"},
    "net_income": {"value": "(1,234)", "unit": "millions", "quote": "Net loss | (1,234)"},
    "eps_diluted": {"value": 7.46, "unit": "per share", "quote": "Diluted | $7.46"},
    "total_assets": {"value": None, "unit": "millions", "quote": ""},
}


@pytest.mark.parametrize(
    "raw, expected, clean",
    [
        (416161, 416161.0, True),
        (7.46, 7.46, True),
        (None, None, True),
        ("416,161", 416161.0, False),
        ("$7.46", 7.46, False),
        ("(321)", -321.0, False),
        ("N/A", None, False),
        ("about a lot", None, False),
    ],
)
def test_parse_number(raw, expected, clean):
    assert parse_number(raw) == (expected, clean)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("millions", "millions"),
        ("In millions", "millions"),
        ("$ in thousands", "thousands"),
        ("billion", "billions"),
        ("USD per share", "per share"),
        ("units", "units"),
        ("furlongs", None),
        (None, None),
    ],
)
def test_normalize_unit(raw, expected):
    assert normalize_unit(raw) == expected


def test_parse_tool_arguments_repairs_and_reports_issues():
    answers, issues = parse_tool_arguments(GOOD_ARGUMENTS)
    by_metric = {a.metric: a for a in answers}

    assert by_metric["Revenue"].value_usd == 416_161_000_000
    assert by_metric["OperatingIncome"].value_usd == 133_050_000_000
    assert by_metric["NetIncome"].value_usd == -1_234_000_000
    assert by_metric["EPS"].value_usd == 7.46
    assert by_metric["TotalAssets"].value_usd is None
    assert issues == ["operating_income:value_not_a_number", "net_income:value_not_a_number"]


def test_parse_tool_arguments_missing_parts():
    answers, issues = parse_tool_arguments({"revenue": {"value": 5, "unit": "furlongs", "quote": "x"}})
    assert len(answers) == 1 and answers[0].value_usd is None
    assert "revenue:unknown_unit" in issues
    assert "total_assets:missing" in issues
    assert parse_tool_arguments(None) == ([], ["no_tool_call"])


@pytest.mark.parametrize("version", ["v1", "v2", "v4"])
def test_prompt_names_fiscal_year_and_contains_text(version):
    prompt = build_prompt("Total net sales | 416,161", date(2025, 9, 27), version)
    assert "2025-09-27" in prompt
    assert prompt.endswith("Total net sales | 416,161")


def test_v2_adds_general_rules_to_v1():
    v1 = build_prompt("TEXT", date(2025, 9, 27), "v1")
    v2 = build_prompt("TEXT", date(2025, 9, 27), "v2")
    assert "Rules:" not in v1
    assert "note reference numbers" in v2
    assert "Income before income taxes is NOT operating income" in v2
    assert len(v2) > len(v1)


def test_unknown_prompt_version_is_rejected():
    with pytest.raises(ValueError, match="Unknown prompt version"):
        build_prompt("TEXT", date(2025, 9, 27), "v99")


def test_tool_requires_all_five_metrics():
    parameters = build_tool()["function"]["parameters"]
    assert parameters["required"] == ["revenue", "operating_income", "net_income", "eps_diluted", "total_assets"]


def fake_ollama(calls: list):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{"function": {"name": "report_financials", "arguments": GOOD_ARGUMENTS}}],
                },
                "prompt_eval_count": 1800,
                "eval_count": 120,
            },
        )

    return handler


def test_client_sends_settings_and_caches(tmp_path):
    calls: list = []
    client = OllamaClient(cache_dir=tmp_path, http=httpx.Client(transport=httpx.MockTransport(fake_ollama(calls))))

    first = client.chat("qwen3.5:4b", "prompt", [build_tool()])
    second = client.chat("qwen3.5:4b", "prompt", [build_tool()])

    assert len(calls) == 1  # second answer came from the cache
    assert calls[0]["think"] is False
    assert calls[0]["options"]["temperature"] == 0
    assert calls[0]["options"]["num_ctx"] >= 8192
    assert not first.cached and second.cached
    assert second.tool_arguments == GOOD_ARGUMENTS
    assert (second.input_tokens, second.output_tokens, second.cost_usd) == (1800, 120, 0.0)


def test_client_reports_when_ollama_is_not_running(tmp_path):
    def refuse(request):
        raise httpx.ConnectError("connection refused")

    client = OllamaClient(cache_dir=tmp_path, http=httpx.Client(transport=httpx.MockTransport(refuse)))
    with pytest.raises(LLMUnavailableError, match="ollama serve"):
        client.chat("qwen3.5:4b", "prompt", [build_tool()])


def test_extract_filing_saves_to_sqlite(tmp_path):
    db_path = tmp_path / "test.db"
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO filings VALUES ('acc-1', 'AAPL', 320193, '10-K', '2025-10-31', '2025-09-27', 2025, 'a.htm', 'u')"
        )

    client = OllamaClient(cache_dir=tmp_path / "llm", http=httpx.Client(transport=httpx.MockTransport(fake_ollama([]))))
    for _ in range(2):  # re-running must not duplicate rows
        extract_filing(client, "qwen3.5:4b", "acc-1", "text", date(2025, 9, 27), version="v2", db_path=db_path)

    with db.connect(db_path) as conn:
        runs = conn.execute("SELECT input_tokens, format_issues FROM extraction_runs").fetchall()
        values = dict(conn.execute("SELECT metric, value_usd FROM extractions").fetchall())

    assert len(runs) == 1
    assert runs[0]["input_tokens"] == 1800
    assert json.loads(runs[0]["format_issues"]) == ["operating_income:value_not_a_number", "net_income:value_not_a_number"]
    assert values["Revenue"] == 416_161_000_000
    assert values["TotalAssets"] is None


STATEMENTS_TEXT = """=== INCOME_STATEMENT ===
CONSOLIDATED STATEMENTS OF OPERATIONS
(In millions, except number of shares, which are reflected in thousands, and per-share amounts)
Total net sales | $416,161 | $391,035
=== BALANCE_SHEET ===
Example Corp
CONSOLIDATED BALANCE SHEETS
(Dollars in Thousands)
Total assets | 5,000 | 4,000"""


def test_detect_scales_takes_first_scale_word_per_statement():
    assert detect_scales(STATEMENTS_TEXT) == {"income_statement": "millions", "balance_sheet": "thousands"}


def test_detect_scales_without_sections_or_header():
    assert detect_scales("just some text in millions") == {}
    assert detect_scales("=== BALANCE_SHEET ===\nTotal assets | 5\n") == {}


def test_apply_detected_units_overrides_the_model():
    answers, _ = parse_tool_arguments(
        {
            "revenue": {"value": 416161, "unit": "units", "quote": ""},  # model picked the wrong unit
            "operating_income": {"value": None, "unit": "millions", "quote": ""},
            "net_income": {"value": 112010, "unit": "per share", "quote": ""},
            "eps_diluted": {"value": 7.46, "unit": "millions", "quote": ""},
            "total_assets": {"value": 5000, "unit": "millions", "quote": ""},
        }
    )
    fixed, issues = apply_detected_units(answers, STATEMENTS_TEXT)
    by_metric = {a.metric: a for a in fixed}
    assert by_metric["Revenue"].value_usd == 416_161_000_000
    assert by_metric["NetIncome"].value_usd == 112_010_000_000
    assert by_metric["EPS"].value_usd == 7.46
    assert by_metric["TotalAssets"].value_usd == 5_000_000  # balance sheet is in thousands
    assert by_metric["OperatingIncome"].value_usd is None
    assert issues == []


def test_apply_detected_units_falls_back_to_model_unit():
    answers, _ = parse_tool_arguments({"revenue": {"value": 5, "unit": "millions", "quote": ""}})
    fixed, issues = apply_detected_units(answers, "no section markers here")
    assert fixed[0].value_usd == 5_000_000
    assert issues == ["Revenue:scale_not_detected"]


def test_v3_uses_v2_prompt_and_code_units(tmp_path):
    calls: list = []
    client = OllamaClient(cache_dir=tmp_path / "llm", http=httpx.Client(transport=httpx.MockTransport(fake_ollama(calls))))
    db_path = tmp_path / "test.db"
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO filings VALUES ('acc-1', 'AAPL', 320193, '10-K', '2025-10-31', '2025-09-27', 2025, 'a.htm', 'u')"
        )

    extract_filing(client, "qwen3.5:4b", "acc-1", STATEMENTS_TEXT, date(2025, 9, 27), version="v2", db_path=db_path)
    _, answers, _ = extract_filing(
        client, "qwen3.5:4b", "acc-1", STATEMENTS_TEXT, date(2025, 9, 27), version="v3", db_path=db_path
    )

    assert len(calls) == 1  # v3 sends the same prompt as v2, so the answer comes from the cache
    by_metric = {a.metric: a for a in answers}
    assert by_metric["Revenue"].value_usd == 416_161_000_000  # income statement header says millions
    assert by_metric["TotalAssets"].value_usd is None  # model gave no value
    with db.connect(db_path) as conn:
        versions = [r[0] for r in conn.execute("SELECT DISTINCT version FROM extraction_runs ORDER BY 1")]
    assert versions == ["v2", "v3"]


NONCONTROLLING_TEXT = """=== INCOME_STATEMENT ===
CONSOLIDATED STATEMENTS OF INCOME
(In millions, except per share amounts)
Years ended | 2025 | 2024
Net income | $17,949 | $12,095
Net income attributable to noncontrolling interests | 443 | 481
Net income attributable to Example Corp | 17,506 | 11,614
Net Income | $17,949 | $12,095
Diluted earnings per share | $4.14 | $2.75
=== BALANCE_SHEET ===
(In millions)
Total assets | 5,000 | 4,000"""

LOSS_TEXT = """=== INCOME_STATEMENT ===
(Dollars in millions, except per share data)
Loss from operations | (10,707) | (773)
Net loss | (11,829) | (2,242)
Less: net loss attributable to noncontrolling interest | (12) | (20)
Net loss attributable to Example shareholders | (11,817) | (2,222)
Less: preferred stock dividends | 58 | —
Net loss attributable to Example common shareholders | ($ 11,875) | ($ 2,222)"""


def _net_income(value, text):
    answers, _ = parse_tool_arguments({"net_income": {"value": value, "unit": "millions", "quote": ""}})
    answers, _ = apply_detected_units(answers, text)
    return answers[0]


def test_row_cells():
    assert row_cells("Net loss | (11,829) | ($ 2,242) | — | $4.15") == ("Net loss", [-11829.0, -2242.0, None, 4.15])


def test_remove_noncontrolling_picks_the_company_row():
    fixed = remove_noncontrolling(_net_income(17949, NONCONTROLLING_TEXT), NONCONTROLLING_TEXT)
    assert fixed.value == 17506 and fixed.value_usd == 17_506_000_000


def test_remove_noncontrolling_uses_the_same_column():
    assert remove_noncontrolling(_net_income(12095, NONCONTROLLING_TEXT), NONCONTROLLING_TEXT).value == 11614


def test_remove_noncontrolling_with_losses():
    fixed = remove_noncontrolling(_net_income(-11829, LOSS_TEXT), LOSS_TEXT)
    assert fixed.value == -11817  # not the row after preferred dividends (-11,875)


@pytest.mark.parametrize("value", [17506, 4.14, 999, None])
def test_remove_noncontrolling_leaves_other_answers_alone(value):
    assert remove_noncontrolling(_net_income(value, NONCONTROLLING_TEXT), NONCONTROLLING_TEXT) is None


def test_remove_noncontrolling_needs_numbers_that_add_up():
    text = NONCONTROLLING_TEXT.replace("17,506", "17,000")
    assert remove_noncontrolling(_net_income(17949, text), text) is None


def test_v4_prompt_adds_loss_rule_to_v2():
    v2 = build_prompt("TEXT", date(2025, 9, 27), "v2")
    v4 = build_prompt("TEXT", date(2025, 9, 27), "v4")
    assert v4.startswith(v2.split("\nFinancial statements:")[0])
    assert "Never set a value to null just because it is a loss" in v4
    assert "Never set a value to null" not in v2


def test_v4_corrects_net_income_and_notes_it(tmp_path):
    arguments = {**GOOD_ARGUMENTS, "net_income": {"value": 17949, "unit": "millions", "quote": "Net income"}}

    def handler(request):
        return httpx.Response(
            200,
            json={
                "message": {"tool_calls": [{"function": {"name": "report_financials", "arguments": arguments}}]},
                "prompt_eval_count": 10,
                "eval_count": 5,
            },
        )

    client = OllamaClient(cache_dir=tmp_path / "llm", http=httpx.Client(transport=httpx.MockTransport(handler)))
    db_path = tmp_path / "test.db"
    with db.connect(db_path) as conn:
        conn.execute("INSERT INTO filings VALUES ('acc-1', 'EX', 1, '10-K', '2026-02-01', '2025-12-31', 2025, 'a', 'u')")

    _, answers, issues = extract_filing(
        client, "qwen3.5:2b", "acc-1", NONCONTROLLING_TEXT, date(2025, 12, 31), version="v4", db_path=db_path
    )
    assert {a.metric: a.value for a in answers}["NetIncome"] == 17506
    assert NONCONTROLLING_CORRECTED in issues


FILL_TEXT = """=== INCOME_STATEMENT ===
(Dollars in millions, except per share data)
Years ended December 31, | 2024 | 2023
Total revenues | 66,517 | 77,794
Loss from operations | (10,707) | (773)
Loss from continuing operations before taxes | (12,210) | (2,005)
Net loss | (11,829) | (2,242)
Less: net loss attributable to noncontrolling interest | (12) | (20)
Net loss attributable to Example shareholders | (11,817) | (2,222)
Diluted loss per share | ($ 18.36) | ($ 3.67)
Weighted average shares - Diluted | 644 | 605"""


def _answers(**values):
    fields = {"Revenue": "revenue", "OperatingIncome": "operating_income", "NetIncome": "net_income", "EPS": "eps_diluted"}
    arguments = {fields[m]: {"value": v, "unit": "millions", "quote": ""} for m, v in values.items()}
    answers, _ = parse_tool_arguments(arguments)
    return apply_detected_units(answers, FILL_TEXT)[0]


def test_fill_missing_takes_loss_rows_from_the_year_column():
    filled, notes = fill_missing(_answers(Revenue=66517, OperatingIncome=None, NetIncome=None, EPS=None), FILL_TEXT)
    by_metric = {a.metric: a for a in filled}
    assert by_metric["OperatingIncome"].value_usd == -10_707_000_000  # not "from continuing operations"
    assert by_metric["NetIncome"].value == -11829  # noncontrolling interests are removed in a later step
    assert by_metric["EPS"].value_usd == -18.36 and by_metric["EPS"].unit == "per share"
    assert notes == ["OperatingIncome:filled_from_row", "NetIncome:filled_from_row", "EPS:filled_from_row"]

    prior_year, _ = fill_missing(_answers(Revenue=77794, OperatingIncome=None), FILL_TEXT)
    assert prior_year[1].value == -773


def test_fill_missing_never_replaces_an_answer():
    answers = _answers(Revenue=66517, OperatingIncome=123, NetIncome=None, EPS=None)
    filled, notes = fill_missing(answers, FILL_TEXT)
    assert filled[1].value == 123
    assert "OperatingIncome:filled_from_row" not in notes


def test_fill_missing_needs_a_known_column_and_a_matching_row():
    assert fill_missing(_answers(Revenue=None, OperatingIncome=None), FILL_TEXT) == (
        _answers(Revenue=None, OperatingIncome=None),
        [],
    )
    text = FILL_TEXT.replace("Loss from operations", "Other operating items")
    filled, notes = fill_missing(_answers(Revenue=66517, OperatingIncome=None), text)
    assert filled[1].value is None and notes == []


def test_code_corrections_are_recognized():
    assert is_code_correction(NONCONTROLLING_CORRECTED)
    assert is_code_correction("EPS:filled_from_row")
    assert is_code_correction(COMMON_CORRECTED)
    assert is_code_correction(PRETAX_REMOVED)
    assert not is_code_correction("revenue:value_not_a_number")


# ------------------------------------------------------------------------------ v5


def _answer(metric: str, value: float | None) -> MetricAnswer:
    return MetricAnswer(metric=metric, value=value, unit="millions", value_usd=None if value is None else value * 1e6, quote="")


TWO_NONCONTROLLING_TEXT = """=== INCOME_STATEMENT ===
(in millions)
Year Ended December 31, | 2024 | 2023
Net loss | (11,482) | (3,079)
Net loss (income) attributable to noncontrolling interests | 129 | (38)
Net loss (income) attributable to redeemable noncontrolling interests | 42 | (9)
Net loss available to Example, Inc. | $(11,311) | $(3,126)"""


@pytest.mark.parametrize("value, expected", [(-11482, -11311), (-3079, -3126)])
def test_remove_noncontrolling_adds_up_several_noncontrolling_rows(value, expected):
    answer = _answer("NetIncome", value)
    assert remove_noncontrolling(answer, TWO_NONCONTROLLING_TEXT, sum_rows=True).value == expected
    assert remove_noncontrolling(answer, TWO_NONCONTROLLING_TEXT) is None  # v4 behavior: one row only


def test_remove_noncontrolling_with_several_rows_still_needs_numbers_that_add_up():
    text = TWO_NONCONTROLLING_TEXT.replace("| 42 |", "| 50 |")
    assert remove_noncontrolling(_answer("NetIncome", -11482), text, sum_rows=True) is None


COMMON_TEXT = """=== INCOME_STATEMENT ===
(Dollars in millions)
Year Ended December | 2025 | 2024
Total net revenues | 58,283 | 53,512
Pre-tax earnings | 21,852 | 18,397
Net income | 18,000 | 15,000
Less: net income attributable to noncontrolling interests | 824 | 724
Net earnings | 17,176 | 14,276
Preferred stock dividends | 876 | 751
Net earnings applicable to common shareholders | $16,300 | $13,525
Diluted earnings per common share | $51.32 | $40.54"""


@pytest.mark.parametrize("value, expected", [(16300, 17176), (13525, 14276)])
def test_remove_common_adjustments_takes_net_income_before_preferred_dividends(value, expected):
    corrected = remove_common_adjustments(_answer("NetIncome", value), COMMON_TEXT)
    assert corrected.value == expected and corrected.value_usd == expected * 1e6


@pytest.mark.parametrize("value", [17176, 18000, None])
def test_remove_common_adjustments_leaves_other_answers_alone(value):
    assert remove_common_adjustments(_answer("NetIncome", value), COMMON_TEXT) is None


def test_remove_common_adjustments_needs_numbers_that_add_up():
    text = COMMON_TEXT.replace("| 876 |", "| 900 |")
    assert remove_common_adjustments(_answer("NetIncome", 16300), text) is None


def test_remove_common_adjustments_ignores_noncontrolling_rows():
    # The row right above the common row is noncontrolling: the common row *is* the company's net income.
    text = """=== INCOME_STATEMENT ===
(millions)
Year | 2025
Net income before allocation to noncontrolling interests | 8,050
Less: Net income attributable to noncontrolling interests | 19
Net income attributable to Example Inc. common shareholders | $8,031"""
    assert remove_common_adjustments(_answer("NetIncome", 8031), text) is None


def test_v5_turns_common_and_group_rows_into_the_company_row():
    text = """=== INCOME_STATEMENT ===
(millions)
Year | 2025
Net Income | 21,479
Less: Net Income Attributable to Noncontrolling Interest | (1,398)
Net Income Attributable to Example | $20,081
Less: Preferred Stock Dividends | (207)
Net Income Attributable to Common Stock | $19,874"""
    for value, note in ((19874, COMMON_CORRECTED), (21479, NONCONTROLLING_CORRECTED)):
        answers, notes = apply_common_check([_answer("NetIncome", value)], text)  # same order as extract_filing
        answers, more = apply_noncontrolling_check(answers, text)
        assert answers[0].value == 20081 and notes + more == [note]


PRETAX_TEXT = """=== INCOME_STATEMENT ===
(in millions)
Year | 2025 | 2024
Total revenues | 94,000 | 88,000
Income from continuing operations before income taxes | 7,569 | 4,769
Net income | 5,000 | 2,500"""


def test_drop_pretax_removes_income_before_taxes_as_operating_income():
    answers, notes = drop_pretax([_answer("Revenue", 94000), _answer("OperatingIncome", 7569)], PRETAX_TEXT)
    assert answers[0].value == 94000
    assert answers[1].value is None and answers[1].value_usd is None
    assert notes == [PRETAX_REMOVED]


@pytest.mark.parametrize("label", ["Operating income", "Earnings from operations", "Income (loss) from operations"])
def test_drop_pretax_keeps_an_operating_row(label):
    text = PRETAX_TEXT.replace("Total revenues | 94,000 | 88,000", f"{label} | 7,569 | 4,769")
    answers, notes = drop_pretax([_answer("OperatingIncome", 7569)], text)
    assert answers[0].value == 7569 and notes == []


def test_drop_pretax_keeps_values_it_cannot_find():
    answers, notes = drop_pretax([_answer("OperatingIncome", 1234), _answer("OperatingIncome", None)], PRETAX_TEXT)
    assert [a.value for a in answers] == [1234, None] and notes == []


def test_v5_reuses_the_v4_prompt():
    assert VERSIONS["v5"].prompt == VERSIONS["v4"].prompt
    assert VERSIONS["v5"].check_common and VERSIONS["v5"].drop_pretax and VERSIONS["v5"].sum_noncontrolling
    assert not VERSIONS["v4"].sum_noncontrolling  # v4 results must not change
