"""LLM extraction: ask a model to read the financial statements and fill in a form (tool call).

For each metric the model reports the number as printed, its unit (scale) and a quote.
The USD value is computed here in code (value × scale), not by the model, so that
reading errors and unit errors can be told apart later. From v3 on, the scale is read
from the table header in code and the model's unit is ignored. From v4 on, code also
fills values the model left empty from rows labeled as such (e.g. "Loss from operations")
and checks whether the model's net income still includes noncontrolling interests.
From v5 on, code also removes "income before taxes" given as operating income and
replaces net income "applicable to common shareholders" with the company's net income.

Usage:
    python -m edgar_extract.extract                         # both default models, latest version, all filings
    python -m edgar_extract.extract --models qwen3.5:4b --version v1
"""

import argparse
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pydantic import BaseModel

from edgar_extract import db
from edgar_extract.config import PROJECT_ROOT
from edgar_extract.llm import LLMResponse, OllamaClient

DEFAULT_MODELS = ["qwen3.5:4b", "qwen3.5:2b"]

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

# v4: losses. Small models left loss rows empty ("Net loss", "Loss from operations"),
# as if a loss were not the metric. Stays general like the v2 rules.
_RULES_V4 = _RULES_V2 + """- Losses: in a year with a loss the rows are labeled as losses, e.g. "Net loss", "Loss from operations", "Operating loss" or "Diluted loss per share". These rows are the net income, operating income and diluted earnings per share you are looking for: report them as negative numbers. Never set a value to null just because it is a loss.
"""

# Keys are the pipeline version that introduced the prompt (v3 reused prompt v2).
PROMPTS = {
    "v1": _INTRO + _STATEMENTS,
    "v2": _INTRO + _RULES_V2 + _STATEMENTS,
    "v4": _INTRO + _RULES_V4 + _STATEMENTS,
}


@dataclass(frozen=True)
class Version:
    prompt: str  # key of PROMPTS
    unit_source: str  # "model" = unit chosen by the model, "code" = read from the table header
    check_noncontrolling: bool = False  # correct a net income that still includes noncontrolling interests
    fill_missing: bool = False  # fill values the model left empty from rows with the metric's usual label
    sum_noncontrolling: bool = False  # the noncontrolling check may also add up several noncontrolling rows
    check_common: bool = False  # replace net income "applicable to common shareholders" with the company's net income
    drop_pretax: bool = False  # remove "income before taxes" given as operating income


# Every change gets a new version, so runs stay comparable. The tool stays the same.
VERSIONS = {
    "v1": Version(prompt="v1", unit_source="model"),
    "v2": Version(prompt="v2", unit_source="model"),  # general rules against the v1 error types
    "v3": Version(prompt="v2", unit_source="code"),  # same LLM answers as v2 (cached); only the unit changes
    "v4": Version(prompt="v4", unit_source="code", check_noncontrolling=True, fill_missing=True),  # see CLAUDE.md
    # Same LLM answers as v4 (cached); only post-processing changes.
    "v5": Version(
        prompt="v4",
        unit_source="code",
        check_noncontrolling=True,
        fill_missing=True,
        sum_noncontrolling=True,
        check_common=True,
        drop_pretax=True,
    ),
}
LATEST_VERSION = "v5"


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


def build_prompt(text: str, report_date: date, prompt: str = "v2") -> str:
    if prompt not in PROMPTS:
        raise ValueError(f"Unknown prompt version {prompt!r}; known: {', '.join(PROMPTS)}")
    template = PROMPTS[prompt]
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


# ------------------------------------------------------- unit from the table header

SECTION_MARKER = re.compile(r"^=== ([A-Z_]+) ===$", re.M)
SCALE_IN_HEADER = re.compile(r"\b(thousands|millions|billions)\b", re.I)
HEADER_LINES = 5  # the scale is stated right below the statement title
METRIC_SECTION = {
    "Revenue": "income_statement",
    "OperatingIncome": "income_statement",
    "NetIncome": "income_statement",
    "TotalAssets": "balance_sheet",
}  # EPS is always "per share"


def detect_scales(text: str) -> dict[str, str]:
    """Scale per statement, e.g. {"income_statement": "millions"}, read from the section header.

    Takes the first scale word: Apple writes "(In millions, except number of shares,
    which are reflected in thousands, ...)" — amounts are in millions.
    """
    scales = {}
    parts = SECTION_MARKER.split(text)  # ["", "INCOME_STATEMENT", body, "BALANCE_SHEET", body]
    for name, body in zip(parts[1::2], parts[2::2]):
        header = "\n".join(body.strip().splitlines()[:HEADER_LINES])
        match = SCALE_IN_HEADER.search(header)
        if match:
            scales[name.lower()] = match.group(1).lower()
    return scales


def apply_detected_units(answers: list[MetricAnswer], text: str) -> tuple[list[MetricAnswer], list[str]]:
    """Replace the model's unit with the scale found in the table header. Keeps the model's unit as fallback."""
    scales = detect_scales(text)
    updated, issues = [], []
    for answer in answers:
        unit = "per share" if answer.metric == "EPS" else scales.get(METRIC_SECTION[answer.metric])
        if unit is None:
            issues.append(f"{answer.metric}:scale_not_detected")
            updated.append(answer)
            continue
        value_usd = answer.value * UNIT_SCALE[unit] if answer.value is not None else None
        updated.append(answer.model_copy(update={"unit": unit, "value_usd": value_usd}))
    return updated, issues


# ------------------------------------------- net income without noncontrolling interests

NONCONTROLLING = re.compile(r"non-?controlling|minority interest", re.I)
NET_INCOME_LABEL = re.compile(r"\bnet\b.*\b(income|earnings|loss|profit)|^(less:\s*)?profit\b", re.I)
NONCONTROLLING_WINDOW = 4  # the rows after "Net income" that may hold the split
NONCONTROLLING_CORRECTED = "NetIncome:noncontrolling_removed"
FILLED_FROM_ROW = ":filled_from_row"  # e.g. "OperatingIncome:filled_from_row"
COMMON_CORRECTED = "NetIncome:common_adjustments_removed"
PRETAX_REMOVED = "OperatingIncome:pretax_removed"
# Notes in format_issues that record a correction made by code, not an answer that broke the form.
CODE_CORRECTIONS = (NONCONTROLLING_CORRECTED, FILLED_FROM_ROW, COMMON_CORRECTED, PRETAX_REMOVED)


def is_code_correction(issue: str) -> bool:
    return issue.endswith(CODE_CORRECTIONS)


def section_lines(text: str, section: str) -> list[str]:
    """The lines of one statement, e.g. section_lines(text, "income_statement")."""
    parts = SECTION_MARKER.split(text)
    for name, body in zip(parts[1::2], parts[2::2]):
        if name.lower() == section:
            return body.splitlines()
    return []


def row_cells(line: str, raw: bool = False) -> tuple[str, list]:
    """Split a table row into its label and its numbers ("(1,234)" -> -1234, "—" -> None).

    raw=True returns the cells as printed instead (same columns).
    """
    label, *cells = [cell.strip() for cell in line.split("|")]
    values = []
    for cell in cells:
        cleaned = cell.replace("$", "").replace(" ", "")
        value, _ = parse_number(cleaned)
        if value is None and cleaned and cleaned.lower() not in NULL_WORDS:
            continue  # not a number (e.g. a footnote marker): no column
        values.append(cell if raw else value)
    return label, values


def _close(a: float, b: float, rows: int = 1) -> bool:
    return abs(a - b) <= rows  # printed amounts are rounded, so a sum can be off by 1 per row added


def remove_noncontrolling(answer: MetricAnswer, text: str, sum_rows: bool = False) -> MetricAnswer | None:
    """If the model's net income includes noncontrolling interests, return the corrected answer.

    Many income statements show three rows: net income of the whole group, the part that
    belongs to noncontrolling interests (other owners of subsidiaries), and net income
    attributable to the company. Small models often report the first row. The fix is only
    applied if the numbers add up: group = noncontrolling + company, in the same column.
    Some statements split the noncontrolling part into several rows (e.g. a "redeemable"
    one); with sum_rows=True (v5) their sum may add up, too. Returns None if nothing needs
    to change.
    """
    if answer.metric != "NetIncome" or answer.value is None:
        return None
    rows = [row_cells(line) for line in section_lines(text, "income_statement") if "|" in line]
    for i, (label, values) in enumerate(rows):
        if not NET_INCOME_LABEL.search(label):
            continue
        column = next((c for c, v in enumerate(values) if v is not None and abs(v) == abs(answer.value)), None)
        if column is None:
            continue
        if "attributable" in label.lower() and not NONCONTROLLING.search(label):
            return None  # the model already chose the company's row
        group = abs(values[column])
        following = rows[i + 1 : i + 1 + NONCONTROLLING_WINDOW]
        minorities = [v[column] for lab, v in following if NONCONTROLLING.search(lab) and len(v) > column and v[column]]
        companies = [
            v[column]
            for lab, v in following
            if NET_INCOME_LABEL.search(lab) and not NONCONTROLLING.search(lab) and len(v) > column and v[column] is not None
        ]
        # Each row on its own, or all rows together (signs as printed: one may be a loss, one a profit).
        totals = [(abs(m), 1) for m in minorities]
        if sum_rows and len(minorities) > 1:
            totals.append((abs(sum(minorities)), len(minorities)))
        for minority, count in totals:
            for company in companies:
                if abs(company) != group and any(_close(group, abs(company) + s * minority, count) for s in (1, -1)):
                    value = company if answer.value * company >= 0 else -company
                    return answer.model_copy(
                        update={
                            "value": value,
                            "value_usd": value * UNIT_SCALE[answer.unit] if answer.unit else None,
                        }
                    )
        return None  # the model's row has no noncontrolling split below it
    return None


COMMON = re.compile(r"\bcommon\b", re.I)
COMMON_WINDOW = 3  # rows between the company's net income and the common shareholders' row


def remove_common_adjustments(answer: MetricAnswer, text: str) -> MetricAnswer | None:
    """If the model's net income is the amount for common shareholders, return the company's net income.

    Banks and companies with preferred stock show net income, then deductions such as
    preferred dividends, then net income "applicable to common shareholders". The metric is
    the company's net income before those deductions. The fix is only applied if the numbers
    add up: company = common + the rows in between, in the same column. Rows for
    noncontrolling interests are never part of it (that is remove_noncontrolling's job).
    Returns None if nothing needs to change.
    """
    if answer.metric != "NetIncome" or answer.value is None:
        return None
    rows = [row_cells(line) for line in section_lines(text, "income_statement") if "|" in line]
    for i, (label, values) in enumerate(rows):
        if not (NET_INCOME_LABEL.search(label) and COMMON.search(label)):
            continue
        column = next((c for c, v in enumerate(values) if v is not None and abs(v) == abs(answer.value)), None)
        if column is None:
            continue
        common = values[column]
        between = []
        for above_label, above in reversed(rows[max(0, i - COMMON_WINDOW - 1) : i]):
            if NONCONTROLLING.search(above_label) or len(above) <= column or above[column] is None:
                return None
            if not NET_INCOME_LABEL.search(above_label) or COMMON.search(above_label):
                between.append(above[column])
                continue
            company = above[column]
            if not between or abs(company) == abs(common):
                return None
            deductions = abs(sum(between))
            if not any(_close(abs(company), abs(common) + s * deductions, len(between)) for s in (1, -1)):
                return None
            value = company if answer.value * company >= 0 else -company
            return answer.model_copy(
                update={"value": value, "value_usd": value * UNIT_SCALE[answer.unit] if answer.unit else None}
            )
        return None
    return None


def apply_common_check(answers: list[MetricAnswer], text: str) -> tuple[list[MetricAnswer], list[str]]:
    updated, notes = [], []
    for answer in answers:
        corrected = remove_common_adjustments(answer, text)
        if corrected is not None:
            notes.append(COMMON_CORRECTED)
        updated.append(corrected or answer)
    return updated, notes


# ------------------------------------------------- income before taxes is not operating income

PRETAX = re.compile(r"\bbefore\b.*\btax|\bpre-?tax", re.I)
OPERATING_ROW = re.compile(r"^operating|from operations\W*$", re.I)  # as in ROW_LABELS["OperatingIncome"]


def drop_pretax(answers: list[MetricAnswer], text: str) -> tuple[list[MetricAnswer], list[str]]:
    """Remove an operating income that is really "income before taxes".

    Where a statement has no operating income line, models often report income before
    income taxes instead, although the prompt says not to. The value is removed if every
    income-statement row that shows it is an income-before-taxes row; a row that is also
    labeled as operating (e.g. "Operating income" with the same amount) keeps it.
    """
    rows = [row_cells(line) for line in section_lines(text, "income_statement") if "|" in line]
    updated, notes = [], []
    for answer in answers:
        if answer.metric != "OperatingIncome" or answer.value is None:
            updated.append(answer)
            continue
        labels = [label for label, values in rows if any(v is not None and abs(v) == abs(answer.value) for v in values)]
        pretax_only = bool(labels) and all(
            PRETAX.search(label) and not OPERATING_ROW.search(label) for label in labels
        )
        if pretax_only:
            notes.append(PRETAX_REMOVED)
            answer = answer.model_copy(update={"value": None, "value_usd": None})
        updated.append(answer)
    return updated, notes


def apply_noncontrolling_check(
    answers: list[MetricAnswer], text: str, sum_rows: bool = False
) -> tuple[list[MetricAnswer], list[str]]:
    updated, notes = [], []
    for answer in answers:
        corrected = remove_noncontrolling(answer, text, sum_rows)
        if corrected is not None:
            notes.append(NONCONTROLLING_CORRECTED)
        updated.append(corrected or answer)
    return updated, notes


# ------------------------------------------------------ fill values the model left empty

# Labels of the rows a metric is usually printed in, incl. loss years ("Net loss",
# "Loss from operations", "Diluted loss per share"). "from continuing operations" is not
# operating income, so the label must end with "from operations".
ROW_LABELS = {
    "OperatingIncome": re.compile(
        r"^(operating (income|loss|profit)|.*\b(income|loss|earnings|profit)\b.*\bfrom operations)\W*$", re.I
    ),
    "NetIncome": re.compile(r"^net\W+(income|earnings|loss)(\W+(income|earnings|loss))?\W*$", re.I),
    "EPS": re.compile(r"dilut", re.I),
}
PER_SHARE_AMOUNT = re.compile(r"\d\.\d{2}\b")


def year_column(answers: list[MetricAnswer], rows: list[tuple[str, list]]) -> int | None:
    """Column of the fiscal year, taken from an income-statement value the model did report."""
    for answer in answers:
        if answer.value is None or answer.metric not in ("Revenue", "OperatingIncome", "NetIncome", "EPS"):
            continue
        for _, values in rows:
            column = next((c for c, v in enumerate(values) if v is not None and abs(v) == abs(answer.value)), None)
            if column is not None:
                return column
    return None


def fill_missing(answers: list[MetricAnswer], text: str) -> tuple[list[MetricAnswer], list[str]]:
    """Fill OperatingIncome, NetIncome and EPS the model left empty from the row with their usual label.

    Small models leave loss rows empty ("Net loss", "Loss from operations"). The value is
    taken from the same column as the values the model did report. Only empty answers
    are touched, so a value the model gave is never replaced.
    """
    lines = [line for line in section_lines(text, "income_statement") if "|" in line]
    rows = [row_cells(line) for line in lines]
    column = year_column(answers, rows)
    if column is None:
        return answers, []
    scale = detect_scales(text).get("income_statement")
    updated, notes = [], []
    for answer in answers:
        pattern = ROW_LABELS.get(answer.metric)
        if answer.value is not None or pattern is None:
            updated.append(answer)
            continue
        found = None
        for line, (label, values) in zip(lines, rows):
            if not pattern.search(label) or len(values) <= column or values[column] is None:
                continue
            if answer.metric == "EPS" and not PER_SHARE_AMOUNT.search(row_cells(line, raw=True)[1][column]):
                continue  # e.g. "Diluted | 384" (number of shares)
            found = (line, values[column])
            break
        if found is None:
            updated.append(answer)
            continue
        line, value = found
        unit = "per share" if answer.metric == "EPS" else scale
        updated.append(
            answer.model_copy(
                update={
                    "value": value,
                    "unit": unit,
                    "value_usd": value * UNIT_SCALE[unit] if unit else None,
                    "quote": line,
                }
            )
        )
        notes.append(answer.metric + FILLED_FROM_ROW)
    return updated, notes


# --------------------------------------------------------------------- pipeline


def extract_filing(
    client: OllamaClient,
    model: str,
    accession_number: str,
    text: str,
    report_date: date,
    version: str = LATEST_VERSION,
    db_path: Path = db.DB_PATH,
) -> tuple[LLMResponse, list[MetricAnswer], list[str]]:
    spec = VERSIONS[version]
    response = client.chat(model, build_prompt(text, report_date, spec.prompt), [build_tool()])
    answers, issues = parse_tool_arguments(response.tool_arguments)
    if spec.unit_source == "code":
        answers, unit_issues = apply_detected_units(answers, text)
        # The model's own unit no longer matters, so its unit problems are not issues anymore.
        issues = [i for i in issues if not i.endswith(":unknown_unit")] + unit_issues
    if spec.drop_pretax:  # before filling: a real "Loss from operations" row may then take its place
        answers, notes = drop_pretax(answers, text)
        issues += notes
    if spec.fill_missing:
        answers, notes = fill_missing(answers, text)
        issues += notes
    if spec.check_common:  # before the noncontrolling check, which needs the company's (not the common) row
        answers, notes = apply_common_check(answers, text)
        issues += notes
    if spec.check_noncontrolling:  # after filling: a filled net income may include noncontrolling interests
        answers, notes = apply_noncontrolling_check(answers, text, spec.sum_noncontrolling)
        issues += notes

    with db.connect(db_path) as conn:
        db.save_extraction(conn, accession_number, version, response, answers, issues)
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
    parser.add_argument("--version", default=LATEST_VERSION, choices=list(VERSIONS))
    args = parser.parse_args(argv)

    with db.connect() as conn:
        filings = conn.execute(
            """
            SELECT f.accession_number, f.ticker, f.fiscal_year, f.report_date, p.text_path, p.method
            FROM filings f JOIN preprocessing p USING (accession_number)
            ORDER BY f.ticker, f.fiscal_year DESC
            """
        ).fetchall()
    if not filings:
        raise SystemExit("No preprocessed filings found. Run edgar_extract.ground_truth and edgar_extract.preprocess first.")
    # Without the statements (found neither in the main document nor in an exhibit) the
    # model would get the whole 10-K and the answers could not be in it: skip these filings.
    skipped = [f"{row['ticker']} {row['fiscal_year']}" for row in filings if row["method"] != "sections"]
    filings = [row for row in filings if row["method"] == "sections"]
    if skipped:
        print(f"Skipped (financial statements not found in the 10-K or its exhibit): {', '.join(skipped)}")

    client = OllamaClient()
    for model in args.models:
        print(f"\n=== {model} (version {args.version}) ===")
        print(f"{'Ticker':6} {'FY':4} " + " ".join(f"{m:>15}" for m in METRIC_FIELDS.values()) + "   tokens in/out   time  issues")
        total_in = total_out = 0
        total_time = total_cost = 0.0
        for row in filings:
            text = (PROJECT_ROOT / row["text_path"]).read_text(encoding="utf-8")
            response, answers, issues = extract_filing(
                client, model, row["accession_number"], text, date.fromisoformat(row["report_date"]), args.version
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
