"""Tests for the LLM extraction. No real model: Ollama is faked with httpx.MockTransport."""

import json
from datetime import date

import httpx
import pytest

from edgar_extract import db
from edgar_extract.extract import (
    apply_detected_units,
    build_prompt,
    detect_scales,
    build_tool,
    extract_filing,
    normalize_unit,
    parse_number,
    parse_tool_arguments,
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


@pytest.mark.parametrize("version", ["v1", "v2"])
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
