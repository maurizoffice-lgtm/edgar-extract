"""Tests for the LLM extraction. No real model: Ollama is faked with httpx.MockTransport."""

import json
from datetime import date

import httpx
import pytest

from edgar_extract import db
from edgar_extract.extract import (
    build_prompt,
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


def test_prompt_names_fiscal_year_and_contains_text():
    prompt = build_prompt("Total net sales | 416,161", date(2025, 9, 27))
    assert "2025-09-27" in prompt
    assert "Total net sales | 416,161" in prompt


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
        extract_filing(client, "qwen3.5:4b", "acc-1", "text", date(2025, 9, 27), db_path=db_path)

    with db.connect(db_path) as conn:
        runs = conn.execute("SELECT input_tokens, format_issues FROM extraction_runs").fetchall()
        values = dict(conn.execute("SELECT metric, value_usd FROM extractions").fetchall())

    assert len(runs) == 1
    assert runs[0]["input_tokens"] == 1800
    assert json.loads(runs[0]["format_issues"]) == ["operating_income:value_not_a_number", "net_income:value_not_a_number"]
    assert values["Revenue"] == 416_161_000_000
    assert values["TotalAssets"] is None
