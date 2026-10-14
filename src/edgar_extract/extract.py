"""LLM extraction: ask a model to read the financial statements and fill in a form (tool call).

For each metric the model reports the number as printed, its unit (scale) and a quote.
The USD value is computed here in code (value × scale), not by the model, so that
reading errors and unit errors can be told apart later.

Usage:
    python -m edgar_extract.extract                         # both default models, latest prompt, all filings
    python -m edgar_extract.extract --models qwen3.5:4b --prompt-version v1
"""

import argparse
import re
from datetime import date
from pathlib import Path

from pydantic import BaseModel

from edgar_extract import db
from edgar_extract.config import PROJECT_ROOT
from edgar_extract.llm import LLMResponse, OllamaClient

DEFAULT_MODELS = ["qwen3.5:4b", "qwen3.5:2b"]

# Every prompt change gets a new version, so runs stay comparable. The tool stays the same.
# v2 adds general rules against the error types found in the v1 evaluation.
LATEST_PROMPT_VERSION = "v2"

TOOL_NAME = "report_financials"

# tool field -> metric name used in the ground_truth table
METRIC_FIELDS = {
    "revenue": "Revenue",
    "operating_income": "OperatingIncome",
    "net_income": "NetIncome",
    "eps_diluted": "EPS",
    "total_assets": "TotalAssets",
}

UNIT_SCALE = {"units": 1.0, "thousands": 1e3, "millions": 1e6, "billions": 1e9, "per share": 1.0}

METRIC_DESCRIPTIONS = {
    "revenue": "Total revenues / total net sales for the fiscal year",
    "operating_income": "Operating income (loss) for the fiscal year",
    "net_income": "Net income attributable to the company for the fiscal year",
    "eps_diluted": "Diluted earnings per share for the fiscal year",
    "total_assets": "Total assets at the fiscal year end",
}

_INTRO = """You are extracting financial data from the financial statements of a company's annual report (Form 10-K).

The fiscal year to report on ends on {report_date}. The statements also show prior years; use only the column for the fiscal year ending {report_date}.

Call the tool {tool_name} exactly once. For each metric give:
- value: the number exactly as printed in the table (numbers in parentheses are negative),
- unit: the scale stated in the table header (e.g. "In millions"); for earnings per share use "per share",
- quote: the table row the number comes from, copied from the text.
If a metric does not appear in the statements, set its value to null.
"""

_STATEMENTS = """
Financial statements:

{text}"""

# Rules address error *types* seen in the v1 evaluation; they must stay general
# (no company names, no expected numbers), otherwise the evaluation means nothing.
_RULES_V2 = """
Rules:
- value must be a plain JSON number without commas, currency signs or quotes (e.g. 416161, -321, 7.46).
- Some tables have a column with note reference numbers (small whole numbers such as 3 or 12, often under a "Note" header). These are not amounts; never report them.
- unit: the scale is stated once in the table header, e.g. "(In millions)" or "(millions of dollars)". All amounts in that table use this scale. Earnings per share is always "per share".
- revenue: use the line that totals all revenue (its label usually starts with "Total"), not a single component of revenue.
- operating_income: only a line explicitly labeled operating income (or income from operations). Income before income taxes is NOT operating income. If there is no such line, set value to null.
- net_income: net income attributable to the company itself — not the amount including noncontrolling interests, and not the amount "applicable to common stockholders".
"""

PROMPTS = {
    "v1": _INTRO + _STATEMENTS,
    "v2": _INTRO + _RULES_V2 + _STATEMENTS,
}


def build_tool() -> dict:
    metric_schema = {
        "type": "object",
        "properties": {
            "value": {"type": ["number", "null"], "description": "Number exactly as printed, or null if not reported"},
            "unit": {"type": "string", "enum": list(UNIT_SCALE)},
            "quote": {"type": "string", "description": "The table row the number comes from"},
        },
        "required": ["value", "unit", "quote"],
    }
    return {
        "type": "function",
        "function": {
            "name": TOOL_NAME,
            "description": "Report the five financial metrics found in the statements.",
            "parameters": {
                "type": "object",
                "properties": {
                    field: {**metric_schema, "description": description}
                    for field, description in METRIC_DESCRIPTIONS.items()
                },
                "required": list(METRIC_FIELDS),
            },
        },
    }


def build_prompt(text: str, report_date: date, prompt_version: str = LATEST_PROMPT_VERSION) -> str:
    if prompt_version not in PROMPTS:
        raise ValueError(f"Unknown prompt version {prompt_version!r}; known: {', '.join(PROMPTS)}")
    template = PROMPTS[prompt_version]
    return template.format(report_date=report_date.isoformat(), tool_name=TOOL_NAME, text=text)


# ------------------------------------------------------------ reading the answer


class MetricAnswer(BaseModel):
    metric: str
    value: float | None  # as printed
    unit: str | None  # normalized scale, e.g. "millions"; None if not understood
    value_usd: float | None  # value × scale
    quote: str


NULL_WORDS = {"", "null", "none", "n/a", "na", "-", "—", "–"}


def parse_number(raw) -> tuple[float | None, bool]:
    """Turn the model's value into a float. Returns (number, was_clean).

    was_clean is False if we had to repair it (e.g. "416,161" as text, "(321)").
    """
    if raw is None:
        return None, True
    if isinstance(raw, bool):
        return None, False
    if isinstance(raw, (int, float)):
        return float(raw), True
    text = str(raw).strip()
    if text.lower() in NULL_WORDS:
        return None, False
    negative = text.startswith("(") and text.endswith(")")
    cleaned = re.sub(r"[,$\s()]", "", text)
    try:
        number = float(cleaned)
    except ValueError:
        return None, False
    return (-number if negative else number), False


def normalize_unit(raw) -> str | None:
    """Map free-text units ("In millions", "USD per share", ...) to a key of UNIT_SCALE."""
    text = str(raw or "").lower()
    if "share" in text:
        return "per share"
    for unit in ("billions", "millions", "thousands"):
        if unit.rstrip("s") in text:  # "million" also matches "millions"
            return unit
    if text.strip() in ("units", "unit", "usd", "dollars", "$"):
        return "units"
    return None


def parse_tool_arguments(arguments: dict | None) -> tuple[list[MetricAnswer], list[str]]:
    """Read the tool call leniently. Returns the answers and a list of format issues found."""
    issues: list[str] = []
    if arguments is None:
        return [], ["no_tool_call"]

    answers = []
    for field, metric in METRIC_FIELDS.items():
        item = arguments.get(field)
        if not isinstance(item, dict):
            issues.append(f"{field}:missing")
            continue
        value, clean = parse_number(item.get("value"))
        if not clean:
            issues.append(f"{field}:value_not_a_number")
        unit = normalize_unit(item.get("unit"))
        if unit is None and value is not None:
            issues.append(f"{field}:unknown_unit")
        value_usd = value * UNIT_SCALE[unit] if value is not None and unit else None
        answers.append(
            MetricAnswer(
                metric=metric,
                value=value,
                unit=unit,
                value_usd=value_usd,
                quote=str(item.get("quote") or ""),
            )
        )
    return answers, issues


# --------------------------------------------------------------------- pipeline


def extract_filing(
    client: OllamaClient,
    model: str,
    accession_number: str,
    text: str,
    report_date: date,
    prompt_version: str = LATEST_PROMPT_VERSION,
    db_path: Path = db.DB_PATH,
) -> tuple[LLMResponse, list[MetricAnswer], list[str]]:
    response = client.chat(model, build_prompt(text, report_date, prompt_version), [build_tool()])
    answers, issues = parse_tool_arguments(response.tool_arguments)

    with db.connect(db_path) as conn:
        db.save_extraction(conn, accession_number, prompt_version, response, answers, issues)
    return response, answers, issues


def _short(answer: MetricAnswer | None) -> str:
    if answer is None or answer.value_usd is None:
        return "—"
    if answer.metric == "EPS":
        return f"{answer.value_usd:.2f}"
    return f"{answer.value_usd / 1e9:,.1f}B"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--prompt-version", default=LATEST_PROMPT_VERSION, choices=list(PROMPTS))
    args = parser.parse_args(argv)

    with db.connect() as conn:
        filings = conn.execute(
            """
            SELECT f.accession_number, f.ticker, f.fiscal_year, f.report_date, p.text_path
            FROM filings f JOIN preprocessing p USING (accession_number)
            ORDER BY f.ticker, f.fiscal_year DESC
            """
        ).fetchall()
    if not filings:
        raise SystemExit("No preprocessed filings found. Run edgar_extract.ground_truth and edgar_extract.preprocess first.")

    client = OllamaClient()
    for model in args.models:
        print(f"\n=== {model} (prompt {args.prompt_version}) ===")
        print(f"{'Ticker':6} {'FY':4} " + " ".join(f"{m:>15}" for m in METRIC_FIELDS.values()) + "   tokens in/out   time  issues")
        total_in = total_out = 0
        total_time = total_cost = 0.0
        for row in filings:
            text = (PROJECT_ROOT / row["text_path"]).read_text(encoding="utf-8")
            response, answers, issues = extract_filing(
                client, model, row["accession_number"], text, date.fromisoformat(row["report_date"]), args.prompt_version
            )
            by_metric = {a.metric: a for a in answers}
            total_in += response.input_tokens
            total_out += response.output_tokens
            if not response.cached:
                total_time += response.duration_s
                total_cost += response.cost_usd
            time_note = "cached" if response.cached else f"{response.duration_s:5.1f}s"
            print(
                f"{row['ticker']:6} {row['fiscal_year']:4} "
                + " ".join(f"{_short(by_metric.get(m)):>15}" for m in METRIC_FIELDS.values())
                + f"   {response.input_tokens:>6,}/{response.output_tokens:<5,} {time_note:>7}  {len(issues)}"
            )
        print(
            f"Total: {total_in:,} input + {total_out:,} output tokens, "
            f"{total_time:.0f}s model time (new calls only), cost ${total_cost:.2f}"
        )


if __name__ == "__main__":
    main()
