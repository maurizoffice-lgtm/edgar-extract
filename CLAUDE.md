# CLAUDE.md — edgar-extract

## What this project is
LLM-based extraction of financial metrics from SEC 10-K filings, with automatic
evaluation against XBRL data as ground truth.

The point is **not** "an LLM can extract numbers", but: *measure how accurately
it does so, understand the errors, and improve the system measurably.*

The author has never programmed before. Explain every step in plain German,
without jargon (or explain each technical word the first time), 2–3 sentences:
what and why. Whenever the author has to do something themselves, give exact
click-by-click instructions (they use PyCharm on macOS). Stop after each phase
so it can be reviewed and committed.

## Metrics (v1, numeric only)
For the fiscal year the 10-K reports on:

| Metric            | Typical XBRL tags (us-gaap)                                                                 |
|-------------------|---------------------------------------------------------------------------------------------|
| Revenue           | `Revenues`, `RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueNet`, ...    |
| OperatingIncome   | `OperatingIncomeLoss`                                                                       |
| NetIncome         | `NetIncomeLoss`                                                                             |
| EPS (diluted)     | `EarningsPerShareDiluted`                                                                   |
| TotalAssets       | `Assets`                                                                                    |

Revenue is reported under different tags depending on company and year — the
mapping must try several tags in priority order. Banks (e.g. JPM) often have no
classic "Revenue" or "OperatingIncome"; handle missing ground truth explicitly.

Known EDGAR quirks:
- In 2026 the ticker XOM moved to a new holding company (CIK 2115436) without
  10-Ks yet; Exxon's 10-Ks are under the old CIK 34088. See `PREDECESSOR_CIKS`
  in `edgar.py`. Always use `Filing.cik` (not the ticker's current CIK) downstream.
- Heavy filers (JPM) have older 10-Ks in paginated submission files, not in "recent".

Ground-truth findings (Phase 2, 5 companies × 2 years):
- No `OperatingIncomeLoss` in XBRL for JNJ, JPM, XOM → OperatingIncome ground truth is NULL
  (6 of 50 values). Evaluation must treat these as "no ground truth", not as LLM errors.
- XOM's `Revenues` is "Total revenues and other income", not "Sales and other operating
  revenue" — an LLM may plausibly pick the smaller line. Expect this as an error category.
- XOM `NetIncomeLoss` (attributable to ExxonMobil) vs `ProfitLoss` (incl. noncontrolling
  interests) differ by ~1 B; both are stored in `xbrl_candidates`.
- `fiscal_year` = calendar year of the fiscal-year end date (MSFT FY ending 2026-06-30 → 2026).

Preprocessing findings (Phase 3):
- Only income statement + balance sheet are sent to the LLM: ~9.5k of ~1.3M estimated
  tokens (0.7 %). `answer_in_text` checks every ground-truth value is in the extract
  (44/44) — if it isn't, that's a preprocessing bug, not an LLM error.
- Title variants: MSFT uses "INCOME STATEMENTS"/"BALANCE SHEETS" (no "Consolidated");
  XOM writes "Earnings per common share – assuming dilution". JPM has parent-company
  statements in the notes that must not be picked.
- Empty table cells are dropped, so a "Note" column (XOM) can shift values left in rows
  without a note number. Possible future improvement — measure before changing.
- Token counts in Phase 3 are estimates (chars / 4); exact counts come from the API in Phase 4.

## Phases
0. Setup — structure, config, README skeleton
1. EDGAR client — ticker → CIK, list 10-K filings, download main document
2. Ground truth — XBRL companyfacts, matched to filing via accession number → SQLite
3. Preprocessing — HTML → text, locate financial statements / Item 8, log tokens before/after
4. LLM extraction — Claude tool use + pydantic schema; value, unit, USD-normalized value, source quote; log tokens + cost
5. Evaluation — compare to ground truth (0.5 % relative tolerance), error categories, Markdown report in `reports/`
6. Dashboard — Streamlit, reads **only** from SQLite (no API key needed)
7. README — problem, Mermaid architecture, results, top errors, cost per filing, how to run

Scope: start with AAPL, MSFT, JNJ, JPM, XOM × last 2 10-Ks. Only after that
works, expand to ~20 companies × 5 years.

## Tech stack
Python 3.11+, venv + pip (pyproject.toml), httpx, anthropic SDK, pydantic,
SQLite (stdlib `sqlite3`), pandas, Streamlit, pytest, python-dotenv.

Models: **the author does not want to pay**, so v1 uses free local models via Ollama
(installed with Homebrew, API at http://localhost:11434). Model A = `qwen3.5:4b` (4.0 GB),
model B = `qwen3.5:2b` (3.1 GB) — chosen by the author to save disk space; ask before
downloading any further model. Claude
(`claude-haiku-5-5` / `claude-sonnet-5-5`) stays an optional provider that must never
be called without explicit approval. Model must be configurable, never hard-coded at call sites.

Ollama findings (v0.40.4, qwen3.5:4b):
- `format` (JSON mode / JSON schema) returns 501 "structured output is unavailable".
  Tool calling works → use a tool whose parameters come from the pydantic schema, then
  validate the arguments with pydantic.
- Send `"think": false` (thinking model) and `temperature: 0`.
- Real prompt tokens are ~2.4× the Phase-3 estimate (AAPL: 1,816 vs ~770), because
  numbers split into many tokens. Always log the API's real counts.
- Quotes from the model can be paraphrased; verify them against the source text.
- Tool arguments don't always follow the schema types: qwen3.5:2b returned
  `"value": "416,161"` (string with comma) instead of a number. Parse leniently
  (strip commas, parentheses = negative) and count such format errors.
- Ollama is not a login service: start it with `ollama serve` before extraction runs.

Extraction findings (Phase 4, prompt v1, 10 filings, $0):
- qwen3.5:4b: ~15 s per filing, ~2.5–3.6k input tokens. Nearly all values right on first look.
  Errors seen: XOM 2024 EPS = 12 (the "Note Reference Number" column — see Phase 3 note);
  JNJ OperatingIncome = "Earnings before provision for taxes" (no ground truth exists).
- qwen3.5:2b: ~7 s per filing, values mostly returned as strings (format issues), unit
  errors (JNJ "units" instead of millions → values 10^6 too small), XOM Revenue = "Sales and
  other operating revenue" in "thousands", JPM Revenue = "Noninterest revenue", NetIncome
  vs ProfitLoss confusion, EPS null.
- Do not fix these before Phase 5 has measured the v1 baseline; then fix and re-measure.

Evaluation baseline (Phase 5, prompt v1, 44 graded values per model) — see reports/evaluation.md:
- qwen3.5:4b: 98 % (43/44). Only error: XOM 2024 EPS = note number 12 ("other").
- qwen3.5:2b: 75 % (33/44). 5 unit errors, 5 wrong metric, 1 missing; 43 format issues.
- Where no ground truth exists, both models fill OperatingIncome with "income before
  taxes" (4b: 2 of 6, 2b: 4 of 6).
- Quote check is lenient: label-only quotes ("Net earnings") count as found. Possible
  improvement: require the quote to contain the reported number.
- Ideas for v2 (measure each change separately): keep the note column / empty cells in
  preprocessing; prompt: "do not use note reference numbers", "if there is no operating
  income line, return null".

Prompt v2 (only change vs v1: a general "Rules:" block in the prompt; tool and text unchanged):
- qwen3.5:4b: 98 % → 100 % (note number fixed). Still answers OperatingIncome for JNJ
  with "income before taxes" (2 of 6) despite the rule.
- qwen3.5:2b: 75 % → 77 %. Format issues 43 → 8, guessing OperatingIncome 4 → 0, but unit
  errors 5 → 8: JNJ header "(Dollars and Shares in Millions …)" → model picks "units";
  XOM NetIncome unit "per share". In every unit error the printed number itself was right.
- Caveat: these 10 filings are also the development set — 100 % here is not proof of
  generalization. Check on new companies (the 20 × 5 expansion) before claiming it.
- Idea for v3: detect the scale from the table header in code and stop asking the model
  for the unit (moves a weak-model task into deterministic code). Measure separately.

Version 3 (= prompt v2 + scale read from the table header in code; LLM answers are the
cached v2 answers, so only post-processing changed):
- `extraction_runs`/`extractions`/`evaluations` use a `version` column (pipeline version:
  prompt + post-processing). `VERSIONS` in extract.py maps each version to its prompt and
  unit source. The DB was rebuilt from cache after the rename; v1/v2 scores unchanged.
- qwen3.5:2b: 77 % → 95 % (unit errors 8 → 0). Remaining: JPM 2024 Revenue
  ("Noninterest revenue") and NetIncome ("applicable to common stockholders") — wrong row.
- qwen3.5:4b: stays 100 %.
- `detect_scales` found "millions" in all 20 sections; "thousands"/"billions" are only
  covered by unit tests so far — check again with more companies.
- Lesson: move tasks a small model is bad at (choosing the scale) into deterministic code.

## Layout
```
src/edgar_extract/   # package code
tests/               # pytest tests
data/cache/          # raw downloads + API responses (git-ignored)
reports/             # generated Markdown evaluation reports
```

## Rules
- **Never commit API keys.** Secrets live in `.env` (git-ignored); `.env.example` documents the variables.
- **Cache every external call** (SEC and Anthropic). Re-running must not re-download or re-pay.
- **SEC fair-access rules:** User-Agent with name + email (`SEC_USER_AGENT`), max 10 requests/second.
- **Ask before expensive runs** — anything estimated above $1 needs explicit approval.
- Propose small, meaningful commits with clear messages (imperative mood, e.g. "Add EDGAR client with caching").
- Code, comments, docstrings and README in English.

## Conventions
- Type hints everywhere; pydantic models for structured data crossing boundaries.
- Monetary values stored as USD floats (not thousands/millions); keep the raw value + unit alongside.
- Pure functions for parsing and evaluation logic so they are easy to unit test.
- Tests must not hit the network — use small fixtures in `tests/fixtures/`.

## Commands
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```
