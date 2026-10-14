# Evaluation report

_Generated 2026-10-14 by `python -m edgar_extract.evaluate`._

A value counts as correct if it is within 0.5% of the XBRL ground truth. 10 filings, 44 graded values per model (metrics without ground truth are excluded).

## Overall accuracy

| Model / prompt | Accuracy | Avg input tokens | Avg output tokens | Avg seconds / filing | Cost / filing | Format issues | Quotes found in text |
|---|---|---|---|---|---|---|---|
| qwen3.5:2b / v1 | 75% (33/44) | 2,815 | 210 | 6.8 | $0.0000 | 43 | 100% (47/47) |
| qwen3.5:2b / v2 | 77% (34/44) | 3,045 | 203 | 6.9 | $0.0000 | 8 | 98% (43/44) |
| qwen3.5:4b / v1 | 98% (43/44) | 2,815 | 307 | 15.2 | $0.0000 | 4 | 98% (45/46) |
| qwen3.5:4b / v2 | 100% (44/44) | 3,045 | 291 | 15.8 | $0.0000 | 0 | 98% (45/46) |

## Accuracy per metric

| Metric | qwen3.5:2b / v1 | qwen3.5:2b / v2 | qwen3.5:4b / v1 | qwen3.5:4b / v2 |
|---|---|---|---|---|
| Revenue | 50% (5/10) | 70% (7/10) | 100% (10/10) | 100% (10/10) |
| OperatingIncome | 100% (4/4) | 100% (4/4) | 100% (4/4) | 100% (4/4) |
| NetIncome | 50% (5/10) | 50% (5/10) | 100% (10/10) | 100% (10/10) |
| EPS | 90% (9/10) | 100% (10/10) | 90% (9/10) | 100% (10/10) |
| TotalAssets | 100% (10/10) | 80% (8/10) | 100% (10/10) | 100% (10/10) |

## Accuracy per company

| Company | qwen3.5:2b / v1 | qwen3.5:2b / v2 | qwen3.5:4b / v1 | qwen3.5:4b / v2 |
|---|---|---|---|---|
| AAPL | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| JNJ | 50% (4/8) | 25% (2/8) | 100% (8/8) | 100% (8/8) |
| JPM | 62% (5/8) | 75% (6/8) | 100% (8/8) | 100% (8/8) |
| MSFT | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| XOM | 50% (4/8) | 75% (6/8) | 88% (7/8) | 100% (8/8) |

## Error categories

| Category | qwen3.5:2b / v1 | qwen3.5:2b / v2 | qwen3.5:4b / v1 |
|---|---|---|---|
| Value missing | 1 | 0 | 0 |
| Unit error (thousands/millions) | 5 | 8 | 0 |
| Wrong metric (other row) | 5 | 2 | 0 |
| Other | 0 | 0 | 1 |

## Metrics the company does not report

There is no ground truth for these (e.g. banks have no operating income). The right answer is "not reported"; a value here means the model picked some other line.

| Model / prompt | Result |
|---|---|
| qwen3.5:2b / v1 | 4 of 6 answered anyway |
| qwen3.5:2b / v2 | 0 of 6 answered anyway |
| qwen3.5:4b / v1 | 2 of 6 answered anyway |
| qwen3.5:4b / v2 | 2 of 6 answered anyway |

| Model / prompt | Company | FY | Metric | Extracted | Quote |
|---|---|---|---|---|---|
| qwen3.5:2b / v1 | JNJ | 2024 | OperatingIncome | 0 M | Earnings before provision for taxes on income |
| qwen3.5:2b / v1 | JNJ | 2025 | OperatingIncome | 0 M | Earnings before provision for taxes on income |
| qwen3.5:2b / v1 | JPM | 2024 | OperatingIncome | 75,081 M | Income before income tax expense |
| qwen3.5:2b / v1 | JPM | 2025 | OperatingIncome | 72,595 M | Income before income tax expense |
| qwen3.5:4b / v1 | JNJ | 2024 | OperatingIncome | 16,687 M | Earnings before provision for taxes on income / 16,687 / 15,062 / 19,359 |
| qwen3.5:4b / v1 | JNJ | 2025 | OperatingIncome | 32,581 M | Earnings before provision for taxes on income / 32,581 / 16,687 / 15,062 |
| qwen3.5:4b / v2 | JNJ | 2024 | OperatingIncome | 16,687 M | Earnings before provision for taxes on income / 16,687 / 15,062 / 19,359 |
| qwen3.5:4b / v2 | JNJ | 2025 | OperatingIncome | 32,581 M | Earnings before provision for taxes on income / 32,581 / 16,687 / 15,062 |

## All errors

| Model / prompt | Company | FY | Metric | Correct | Extracted | Category | Detail |
|---|---|---|---|---|---|---|---|
| qwen3.5:2b / v1 | JNJ | 2024 | NetIncome | 14,066 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| qwen3.5:2b / v1 | JNJ | 2024 | Revenue | 88,821 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| qwen3.5:2b / v1 | JNJ | 2025 | NetIncome | 26,804 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| qwen3.5:2b / v1 | JNJ | 2025 | Revenue | 94,193 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| qwen3.5:2b / v1 | JPM | 2024 | NetIncome | 58,471 M | 56,868 M | Wrong metric (other row) | number taken from another row: Net income applicable to common stockholders / $56,868 / $47,760 / $35,892 |
| qwen3.5:2b / v1 | JPM | 2024 | Revenue | 177,556 M | 84,973 M | Wrong metric (other row) | number taken from another row: Noninterest revenue / 84,973 / 68,837 / 61,985 |
| qwen3.5:2b / v1 | JPM | 2025 | Revenue | 182,447 M | 87,004 M | Wrong metric (other row) | number taken from another row: Noninterest revenue / 87,004 / 84,973 / 68,837 |
| qwen3.5:2b / v1 | XOM | 2024 | EPS | 7.84 | — | Value missing | model returned no value |
| qwen3.5:2b / v1 | XOM | 2024 | NetIncome | 33,680 M | 35,063 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| qwen3.5:2b / v1 | XOM | 2025 | NetIncome | 28,844 M | 0 M | Unit error (thousands/millions) | reported unit 'per share', correct would be 'millions' |
| qwen3.5:2b / v1 | XOM | 2025 | Revenue | 332,238 M | 324 M | Wrong metric (other row) | number taken from another row: Sales and other operating revenue / 3 / 323,905 / 339,247 / 334,697 |
| qwen3.5:2b / v2 | JNJ | 2024 | NetIncome | 14,066 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| qwen3.5:2b / v2 | JNJ | 2024 | Revenue | 88,821 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| qwen3.5:2b / v2 | JNJ | 2024 | TotalAssets | 180,104 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| qwen3.5:2b / v2 | JNJ | 2025 | NetIncome | 26,804 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| qwen3.5:2b / v2 | JNJ | 2025 | Revenue | 94,193 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| qwen3.5:2b / v2 | JNJ | 2025 | TotalAssets | 199,210 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| qwen3.5:2b / v2 | JPM | 2024 | NetIncome | 58,471 M | 56,868 M | Wrong metric (other row) | number taken from another row: Net income applicable to common stockholders / $56,868 / $47,760 / $35,892 |
| qwen3.5:2b / v2 | JPM | 2024 | Revenue | 177,556 M | 84,973 M | Wrong metric (other row) | number taken from another row: Noninterest revenue / 84,973 / 68,837 / 61,985 |
| qwen3.5:2b / v2 | XOM | 2024 | NetIncome | 33,680 M | 0 M | Unit error (thousands/millions) | reported unit 'per share', correct would be 'millions' |
| qwen3.5:2b / v2 | XOM | 2025 | NetIncome | 28,844 M | 0 M | Unit error (thousands/millions) | reported unit 'per share', correct would be 'millions' |
| qwen3.5:4b / v1 | XOM | 2024 | EPS | 7.84 | 12.00 | Other | earlier column of the correct row (e.g. a note number): Earnings (loss) per common share (dollars) / 12 / 7.84 / 8.89 / 13.26 |
