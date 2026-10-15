"""Evaluation: compare the LLM answers with the XBRL ground truth and explain every error.

A value counts as correct if it is within 0.5 % (relative) of the ground truth.
Wrong values are sorted into categories, checked in this order:
1. missing       — the model gave no value
2. unit_error    — the printed number is right, the scale (thousands/millions) is wrong
3. wrong_year    — the number is from the correct row, but a later (prior-year) column
4. wrong_metric  — the number is from a different row of the statements
5. other         — anything else (with a short explanation)

Metrics without ground truth (e.g. OperatingIncome for banks) are not counted in the
accuracy; they are reported separately ("answered although not reported").

Results are always shown per data set: the development companies (used to tune prompts
and code), test set 1 (held out until v3; its errors were studied for v4), test set 2
(held out until v4; its errors were studied for v5) and test set 3 (held out, never used
for tuning), see datasets.py.

Usage:
    python -m edgar_extract.evaluate      # evaluates all runs, writes reports/evaluation.md
"""

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from edgar_extract import db
from edgar_extract.config import PROJECT_ROOT, REPORTS_DIR
from edgar_extract.datasets import DEVELOPMENT, TEST, TEST2, TEST3, dataset_of
from edgar_extract.extract import METRIC_FIELDS, UNIT_SCALE, is_code_correction

TOLERANCE = 0.005  # 0.5 % relative
SCALES = (1.0, 1e3, 1e6, 1e9)

CORRECT = "correct"
CATEGORIES = ["missing", "unit_error", "wrong_year", "wrong_metric", "other"]
NO_TRUTH_ANSWERED = "no_truth_answered"  # model gave a value, but the company doesn't report it
NO_TRUTH_NULL = "no_truth_null"  # model correctly said "not reported"

CATEGORY_LABELS = {
    "missing": "Value missing",
    "unit_error": "Unit error (thousands/millions)",
    "wrong_year": "Wrong year (prior-year column)",
    "wrong_metric": "Wrong metric (other row)",
    "other": "Other",
}

# ------------------------------------------------------------------- matching

NUMBER_IN_TEXT = re.compile(r"\(?\$?\d[\d,]*(?:\.\d+)?\)?")


def is_match(predicted: float | None, truth: float | None) -> bool:
    if predicted is None or truth is None:
        return False
    if truth == 0:
        return abs(predicted) < 1e-9
    return abs(predicted - truth) <= TOLERANCE * abs(truth)


def numbers_in_line(line: str) -> list[float]:
    """All numbers in a line, as absolute values, in reading order ("(1,234)" -> 1234)."""
    numbers = []
    for token in NUMBER_IN_TEXT.findall(line):
        cleaned = re.sub(r"[,$()]", "", token)
        try:
            numbers.append(abs(float(cleaned)))
        except ValueError:
            continue
    return numbers


def printed_variants(value_usd: float, metric: str) -> list[float]:
    """How the ground-truth value may be printed: in dollars, thousands or millions."""
    if metric == "EPS":
        return [abs(value_usd)]
    return [abs(value_usd) / scale for scale in SCALES]


def _index_of(numbers: list[float], targets: list[float]) -> int | None:
    for i, number in enumerate(numbers):
        if any(is_match(number, target) for target in targets):
            return i
    return None


def truth_rows(text: str, truth: float, metric: str) -> list[tuple[str, int]]:
    """Lines that contain the ground-truth value, with the position of that value in the line."""
    rows = []
    for line in text.splitlines():
        position = _index_of(numbers_in_line(line), printed_variants(truth, metric))
        if position is not None:
            rows.append((line, position))
    return rows


def quote_in_source(quote: str, text: str) -> bool:
    """Is the quote really in the text? Ignores case, spacing, "|" and "$"."""

    def simplify(s: str) -> str:
        return " ".join(re.sub(r"[|$]", " ", s.lower()).split())

    q = simplify(quote)
    return bool(q) and q in simplify(text)


# ----------------------------------------------------------------- categorize


@dataclass(frozen=True)
class Verdict:
    category: str  # CORRECT, one of CATEGORIES, NO_TRUTH_ANSWERED or NO_TRUTH_NULL
    detail: str = ""


def categorize(
    metric: str,
    truth: float | None,
    value: float | None,
    unit: str | None,
    value_usd: float | None,
    text: str,
    other_truths: dict[str, float] | None = None,
    alternatives: dict[str, float] | None = None,
) -> Verdict:
    """Decide whether one answer is correct and, if not, which kind of error it is.

    value/unit are what the model reported (number as printed, normalized scale);
    other_truths = ground truth of the other metrics of the same filing;
    alternatives = related XBRL values that are not the ground truth (e.g. ProfitLoss).
    """
    if truth is None:
        if value is None:
            return Verdict(NO_TRUTH_NULL)
        return Verdict(NO_TRUTH_ANSWERED, f"reported {value:,g} {unit or ''}".strip())

    if is_match(value_usd, truth):
        return Verdict(CORRECT)

    # 1. missing
    if value is None:
        return Verdict("missing", "model returned no value")

    # 2. unit error: the printed number is right, only the scale is wrong
    for scale in SCALES:
        if is_match(value * scale, truth):
            if metric == "EPS":
                correct_unit = "per share"
            else:
                correct_unit = next((u for u, s in UNIT_SCALE.items() if s == scale and u != "per share"), "?")
            return Verdict("unit_error", f"reported unit '{unit}', correct would be '{correct_unit}'")

    # 3./4. where in the text does the model's number come from?
    rows = truth_rows(text, truth, metric)
    for line, truth_position in rows:
        numbers = numbers_in_line(line)
        position = _index_of(numbers, [abs(value)])
        if position is None:
            continue
        if position > truth_position:
            return Verdict("wrong_year", f"later column of the correct row: {line[:90]}")
        return Verdict("other", f"earlier column of the correct row (e.g. a note number): {line[:90]}")

    for name, alt_value in (alternatives or {}).items():
        if is_match(value_usd, alt_value):
            return Verdict("wrong_metric", f"matches related XBRL value {name}")
    for other_metric, other_value in (other_truths or {}).items():
        if is_match(value_usd, other_value):
            return Verdict("wrong_metric", f"matches the ground truth of {other_metric}")

    truth_lines = {line for line, _ in rows}
    for line in text.splitlines():
        if line not in truth_lines and _index_of(numbers_in_line(line), [abs(value)]) is not None:
            return Verdict("wrong_metric", f"number taken from another row: {line[:90]}")

    return Verdict("other", "number does not appear in the statements")


# ------------------------------------------------------------------- evaluate


def evaluate(db_path: Path = db.DB_PATH) -> pd.DataFrame:
    """Grade every extraction run and store the result in the evaluations table."""
    with db.connect(db_path) as conn:
        runs = conn.execute(
            """
            SELECT r.accession_number, r.model, r.version, f.ticker, f.fiscal_year, p.text_path
            FROM extraction_runs r
            JOIN filings f USING (accession_number)
            JOIN preprocessing p USING (accession_number)
            """
        ).fetchall()
        truths = {
            (row["accession_number"], row["metric"]): row["value"]
            for row in conn.execute("SELECT accession_number, metric, value FROM ground_truth")
        }
        alternatives: dict[tuple[str, str], dict[str, float]] = {}
        for row in conn.execute(
            """
            SELECT c.accession_number, c.metric, c.xbrl_tag, c.value
            FROM xbrl_candidates c
            JOIN ground_truth g USING (accession_number, metric)
            WHERE c.xbrl_tag != g.xbrl_tag OR g.xbrl_tag IS NULL
            """
        ):
            alternatives.setdefault((row["accession_number"], row["metric"]), {})[row["xbrl_tag"]] = row["value"]
        answers = {
            (row["accession_number"], row["model"], row["version"], row["metric"]): row
            for row in conn.execute("SELECT * FROM extractions")
        }

    results = []
    texts: dict[str, str] = {}
    for run in runs:
        acc = run["accession_number"]
        text = texts.setdefault(run["text_path"], (PROJECT_ROOT / run["text_path"]).read_text(encoding="utf-8"))
        filing_truths = {m: truths.get((acc, m)) for m in METRIC_FIELDS.values()}
        for metric in METRIC_FIELDS.values():
            answer = answers.get((acc, run["model"], run["version"], metric))
            value = answer["value"] if answer else None
            unit = answer["unit"] if answer else None
            value_usd = answer["value_usd"] if answer else None
            quote = answer["quote"] if answer else ""
            verdict = categorize(
                metric,
                filing_truths[metric],
                value,
                unit,
                value_usd,
                text,
                other_truths={m: v for m, v in filing_truths.items() if m != metric and v is not None},
                alternatives=alternatives.get((acc, metric)),
            )
            results.append(
                {
                    "accession_number": acc,
                    "model": run["model"],
                    "version": run["version"],
                    "ticker": run["ticker"],
                    "fiscal_year": run["fiscal_year"],
                    "metric": metric,
                    "truth": filing_truths[metric],
                    "value": value,
                    "unit": unit,
                    "value_usd": value_usd,
                    "category": verdict.category,
                    "detail": verdict.detail,
                    "quote": quote,
                    "quote_in_source": quote_in_source(quote, text) if value is not None else None,
                    "dataset": dataset_of(run["ticker"]),
                }
            )

    df = pd.DataFrame(results)
    with db.connect(db_path) as conn:
        db.save_evaluations(conn, df)
    return df


# --------------------------------------------------------------------- report


def _table(df: pd.DataFrame) -> str:
    """Render a DataFrame as a Markdown table (without extra dependencies)."""
    header = "| " + " | ".join(str(c) for c in df.columns) + " |"
    divider = "|" + "|".join("---" for _ in df.columns) + "|"
    rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([header, divider, *rows])


def _pct(series: pd.Series) -> str:
    return f"{series.mean():.0%} ({int(series.sum())}/{len(series)})"


def _money(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    if abs(value) < 1_000:
        return f"{value:,.2f}"
    return f"{value / 1e6:,.0f} M"


DATASET_LABELS = {DEVELOPMENT: "Development", TEST: "Test set 1", TEST2: "Test set 2", TEST3: "Test set 3"}


def _with_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Add "run" (model / version), "set" (data set label) and "column" (both, for wide tables)."""
    df = df.copy()
    df["run"] = df["model"] + " / " + df["version"]
    df["set"] = df["dataset"].map(DATASET_LABELS)
    df["column"] = df["run"] + " · " + df["set"]
    return df


def _column_order(df: pd.DataFrame) -> list[str]:
    """Wide-table columns: development runs first, then test sets 1, 2 and 3."""
    keys = df[["dataset", "run", "column"]].drop_duplicates()
    keys = keys.assign(order=keys["dataset"].map(list(DATASET_LABELS).index)).sort_values(["order", "run"])
    return list(keys["column"])


def _dataset_summary(evals: pd.DataFrame, dataset: str) -> str:
    filings = evals[evals["dataset"] == dataset]
    tickers = sorted(filings["ticker"].unique())
    return f"{filings['accession_number'].nunique()} filings from {len(tickers)} companies ({', '.join(tickers)})"


def build_report(evals: pd.DataFrame, runs: pd.DataFrame, skipped: list[str] = ()) -> str:
    evals = _with_labels(evals)
    graded = evals[evals["truth"].notna()].copy()
    graded["correct"] = graded["category"] == CORRECT
    no_truth = evals[evals["truth"].isna()]
    columns = _column_order(evals)

    lines = [
        "# Evaluation report",
        "",
        f"_Generated {date.today().isoformat()} by `python -m edgar_extract.evaluate`._",
        "",
        f"A value counts as correct if it is within {TOLERANCE:.1%} of the XBRL ground truth. "
        "Metrics without ground truth are excluded from the accuracy.",
        "",
    ]
    if (evals["dataset"] == DEVELOPMENT).any():
        lines.append(
            f"- **Development:** {_dataset_summary(evals, DEVELOPMENT)}. "
            "Prompts and code were tuned on these, so their accuracy is optimistic."
        )
    if (evals["dataset"] == TEST).any():
        lines.append(
            f"- **Test set 1:** {_dataset_summary(evals, TEST)}. "
            "Held out until v3; its errors were then studied to build v4, so v4 results here are optimistic too."
        )
    if (evals["dataset"] == TEST2).any():
        lines.append(
            f"- **Test set 2:** {_dataset_summary(evals, TEST2)}. "
            "Held out until v4 (the honest measure for v4); its errors were then studied to build v5, "
            "so v5 results here are optimistic too."
        )
    if (evals["dataset"] == TEST3).any():
        lines.append(
            f"- **Test set 3:** {_dataset_summary(evals, TEST3)}. "
            "Added before v5 was written and never used for tuning — the honest measure for v5."
        )
    if skipped:
        lines.append(
            f"- **Not extracted:** {', '.join(skipped)} — the financial statements were found neither in "
            "the main 10-K document nor in an annual-report exhibit (EX-13), so these filings were not "
            "sent to the models."
        )
    lines += ["", "## Overall accuracy", ""]

    runs = _with_labels(runs)
    overall = []
    for column in columns:
        group = graded[graded["column"] == column]
        if group.empty:
            continue
        r = runs[runs["column"] == column]
        quotes = evals[(evals["column"] == column) & evals["quote_in_source"].notna()]["quote_in_source"]
        overall.append(
            {
                "Data set": group["set"].iloc[0],
                "Model / version": group["run"].iloc[0],
                "Accuracy": _pct(group["correct"]),
                "Avg input tokens": f"{r['input_tokens'].mean():,.0f}",
                "Avg output tokens": f"{r['output_tokens'].mean():,.0f}",
                "Avg seconds / filing": f"{r['duration_s'].mean():.1f}",
                "Cost / filing": f"${r['cost_usd'].mean():.4f}",
                "Format issues": int(r["format_issue_count"].sum()),
                "Code corrections": int(r["code_correction_count"].sum()),
                "Quotes found in text": _pct(quotes.astype(bool)) if len(quotes) else "—",
            }
        )
    lines += [_table(pd.DataFrame(overall)), ""]

    lines += ["## Accuracy per metric", ""]
    per_metric = graded.pivot_table(index="metric", columns="column", values="correct", aggfunc=_pct)
    per_metric = per_metric.reindex(
        index=[m for m in METRIC_FIELDS.values() if m in per_metric.index],
        columns=[c for c in columns if c in per_metric.columns],
    )
    lines += [_table(per_metric.fillna("—").reset_index().rename(columns={"metric": "Metric"})), ""]

    lines += ["## Accuracy per company", ""]
    per_company = graded.pivot_table(index=["set", "ticker"], columns="run", values="correct", aggfunc=_pct)
    per_company = per_company.reindex(
        index=sorted(per_company.index, key=lambda key: (list(DATASET_LABELS.values()).index(key[0]), key[1]))
    )
    per_company = per_company.fillna("—").reset_index().rename(columns={"set": "Data set", "ticker": "Company"})
    lines += [_table(per_company), ""]

    lines += ["## Error categories", ""]
    errors = graded[~graded["correct"]]
    counts = graded.assign(error=~graded["correct"]).pivot_table(
        index="category", columns="column", values="error", aggfunc="sum", fill_value=0
    )
    counts = counts.reindex(
        index=[c for c in CATEGORIES if c in counts.index], columns=[c for c in columns if c in counts.columns]
    )
    counts.index = [CATEGORY_LABELS[c] for c in counts.index]
    if errors.empty:
        lines += ["No errors.", ""]
    else:
        lines += [_table(counts.astype(int).reset_index().rename(columns={"index": "Category"})), ""]

    lines += [
        "## Metrics the company does not report",
        "",
        "There is no ground truth for these (e.g. banks have no operating income). "
        "The right answer is \"not reported\"; a value here means the model picked some other line.",
        "",
    ]
    if no_truth.empty:
        lines += ["None.", ""]
    else:
        nt = no_truth.assign(answered=no_truth["category"] == NO_TRUTH_ANSWERED)
        summary = nt.groupby("column")["answered"].agg(lambda s: f"{int(s.sum())} of {len(s)} answered anyway")
        summary = summary.reindex([c for c in columns if c in summary.index])
        lines += [_table(summary.reset_index().rename(columns={"column": "Model / version · data set", "answered": "Result"})), ""]
        answered = nt[nt["answered"]].sort_values(["set", "run", "ticker", "fiscal_year"])
        if not answered.empty:
            table = pd.DataFrame(
                {
                    "Data set": answered["set"],
                    "Model / version": answered["run"],
                    "Company": answered["ticker"],
                    "FY": answered["fiscal_year"],
                    "Metric": answered["metric"],
                    "Extracted": answered["value_usd"].map(_money),
                    "Quote": answered["quote"].str.replace("|", "/", regex=False).str[:80],
                }
            )
            lines += [_table(table), ""]

    lines += ["## All errors", ""]
    if errors.empty:
        lines += ["None.", ""]
    else:
        detail = errors.sort_values(["set", "run", "ticker", "fiscal_year", "metric"])
        table = pd.DataFrame(
            {
                "Data set": detail["set"],
                "Model / version": detail["run"],
                "Company": detail["ticker"],
                "FY": detail["fiscal_year"],
                "Metric": detail["metric"],
                "Correct": detail["truth"].map(_money),
                "Extracted": detail["value_usd"].map(_money),
                "Category": detail["category"].map(CATEGORY_LABELS),
                "Detail": detail["detail"].str.replace("|", "/", regex=False),
            }
        )
        lines += [_table(table), ""]

    return "\n".join(lines)


def load_runs(db_path: Path = db.DB_PATH) -> pd.DataFrame:
    with db.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT r.model, r.version, r.input_tokens, r.output_tokens, r.duration_s, r.cost_usd, r.format_issues, f.ticker "
            "FROM extraction_runs r JOIN filings f USING (accession_number)"
        ).fetchall()
    df = pd.DataFrame([dict(r) for r in rows])
    issues = df["format_issues"].map(json.loads)
    df["format_issue_count"] = issues.map(lambda items: sum(not is_code_correction(i) for i in items))
    df["code_correction_count"] = issues.map(lambda items: sum(is_code_correction(i) for i in items))
    df["dataset"] = df["ticker"].map(dataset_of)
    return df


def load_skipped(db_path: Path = db.DB_PATH) -> list[str]:
    """Companies whose filings were not extracted because no statements were found, e.g. "IBM (5 filings)"."""
    with db.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT f.ticker, COUNT(*) AS n FROM preprocessing p JOIN filings f USING (accession_number) "
            "WHERE p.method != 'sections' GROUP BY f.ticker ORDER BY f.ticker"
        ).fetchall()
    return [f"{row['ticker']} ({row['n']} filings)" for row in rows]


def main() -> None:
    evals = evaluate()
    if evals.empty:
        raise SystemExit("No extraction runs found. Run edgar_extract.extract first.")
    report = build_report(evals, load_runs(), load_skipped())
    REPORTS_DIR.mkdir(exist_ok=True)
    path = REPORTS_DIR / "evaluation.md"
    path.write_text(report, encoding="utf-8")

    graded = evals[evals["truth"].notna()]
    for (dataset, model, version), group in graded.groupby(["dataset", "model", "version"]):
        correct = (group["category"] == CORRECT).sum()
        print(f"{DATASET_LABELS[dataset]:13} {model} / {version}: {correct}/{len(group)} correct ({correct / len(group):.0%})")
    print(f"\nReport written to {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
