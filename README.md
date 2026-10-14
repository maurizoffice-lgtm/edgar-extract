# edgar-extract

> LLM-based extraction of financial metrics from SEC 10-K filings — with automatic
> evaluation against XBRL data as ground truth.

**Status:** 🚧 work in progress (Phase 4 — LLM extraction done)

## Problem

Large language models can read a 10-K and pull out numbers. The interesting
question is *how accurately* — and *why* they fail when they do. This project
extracts five core metrics from 10-K filings with Claude, compares every value
against the company's own XBRL filing data, categorizes the errors, and tracks
how changes to the pipeline improve accuracy.

Metrics (fiscal year of the report):
Revenue · Operating Income · Net Income · EPS (diluted) · Total Assets

## Architecture

_Coming in Phase 7 (Mermaid diagram)._

## Results

_Coming after Phase 5._

| Model | Overall accuracy | Cost per filing |
|-------|------------------|-----------------|
| claude-haiku-5-5  | – | – |
| claude-sonnet-5-5 | – | – |

## Most common errors & fixes

_Coming after Phase 5._

## Getting started

```bash
git clone <repo-url> && cd edgar-extract
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then fill in ANTHROPIC_API_KEY and SEC_USER_AGENT
pytest
```

## Project structure

```
src/edgar_extract/   # package code
tests/               # pytest tests
data/cache/          # cached downloads (git-ignored)
reports/             # generated evaluation reports
```

## License

_To be added (e.g. MIT)._
