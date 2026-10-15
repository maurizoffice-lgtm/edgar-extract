# Evaluation report

_Generated 2026-10-15 by `python -m edgar_extract.evaluate`._

A value counts as correct if it is within 0.5% of the XBRL ground truth. Metrics without ground truth are excluded from the accuracy.

- **Development:** 10 filings from 5 companies (AAPL, JNJ, JPM, MSFT, XOM). Prompts and code were tuned on these, so their accuracy is optimistic.
- **Held-out test:** 100 filings from 20 companies (AMZN, BA, BAC, CAT, CVX, DIS, GOOGL, HD, KO, MCD, NEE, NFLX, NVDA, PFE, PG, TRV, UNH, V, VZ, WMT). Added afterwards and never used for tuning.

## Overall accuracy

| Data set | Model / version | Accuracy | Avg input tokens | Avg output tokens | Avg seconds / filing | Cost / filing | Format issues | Quotes found in text |
|---|---|---|---|---|---|---|---|---|
| Development | qwen3.5:2b / v1 | 75% (33/44) | 2,815 | 210 | 6.8 | $0.0000 | 43 | 100% (47/47) |
| Development | qwen3.5:2b / v2 | 77% (34/44) | 3,045 | 203 | 6.9 | $0.0000 | 8 | 98% (43/44) |
| Development | qwen3.5:2b / v3 | 95% (42/44) | 3,045 | 203 | 6.9 | $0.0000 | 8 | 98% (43/44) |
| Development | qwen3.5:4b / v1 | 98% (43/44) | 2,815 | 307 | 15.2 | $0.0000 | 4 | 98% (45/46) |
| Development | qwen3.5:4b / v2 | 100% (44/44) | 3,045 | 291 | 15.8 | $0.0000 | 0 | 98% (45/46) |
| Development | qwen3.5:4b / v3 | 100% (44/44) | 3,045 | 291 | 15.8 | $0.0000 | 0 | 98% (45/46) |
| Held-out test | qwen3.5:2b / v3 | 90% (421/470) | 3,031 | 206 | 6.3 | $0.0000 | 10 | 95% (438/461) |
| Held-out test | qwen3.5:4b / v3 | 97% (455/470) | 3,031 | 310 | 15.0 | $0.0000 | 0 | 100% (473/475) |

## Accuracy per metric

| Metric | qwen3.5:2b / v1 · Development | qwen3.5:2b / v2 · Development | qwen3.5:2b / v3 · Development | qwen3.5:4b / v1 · Development | qwen3.5:4b / v2 · Development | qwen3.5:4b / v3 · Development | qwen3.5:2b / v3 · Held-out test | qwen3.5:4b / v3 · Held-out test |
|---|---|---|---|---|---|---|---|---|
| Revenue | 50% (5/10) | 70% (7/10) | 90% (9/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 95% (95/100) | 95% (95/100) |
| OperatingIncome | 100% (4/4) | 100% (4/4) | 100% (4/4) | 100% (4/4) | 100% (4/4) | 100% (4/4) | 88% (70/80) | 91% (73/80) |
| NetIncome | 50% (5/10) | 50% (5/10) | 90% (9/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 72% (68/95) | 97% (92/95) |
| EPS | 90% (9/10) | 100% (10/10) | 100% (10/10) | 90% (9/10) | 100% (10/10) | 100% (10/10) | 93% (88/95) | 100% (95/95) |
| TotalAssets | 100% (10/10) | 80% (8/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (100/100) | 100% (100/100) |

## Accuracy per company

| Data set | Company | qwen3.5:2b / v1 | qwen3.5:2b / v2 | qwen3.5:2b / v3 | qwen3.5:4b / v1 | qwen3.5:4b / v2 | qwen3.5:4b / v3 |
|---|---|---|---|---|---|---|---|
| Development | AAPL | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| Development | JNJ | 50% (4/8) | 25% (2/8) | 100% (8/8) | 100% (8/8) | 100% (8/8) | 100% (8/8) |
| Development | JPM | 62% (5/8) | 75% (6/8) | 75% (6/8) | 100% (8/8) | 100% (8/8) | 100% (8/8) |
| Development | MSFT | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| Development | XOM | 50% (4/8) | 75% (6/8) | 100% (8/8) | 88% (7/8) | 100% (8/8) | 100% (8/8) |
| Held-out test | AMZN | — | — | 100% (25/25) | — | — | 100% (25/25) |
| Held-out test | BA | — | — | 48% (12/25) | — | — | 88% (22/25) |
| Held-out test | BAC | — | — | 95% (19/20) | — | — | 100% (20/20) |
| Held-out test | CAT | — | — | 100% (20/20) | — | — | 100% (20/20) |
| Held-out test | CVX | — | — | 90% (18/20) | — | — | 100% (20/20) |
| Held-out test | DIS | — | — | 52% (13/25) | — | — | 80% (20/25) |
| Held-out test | GOOGL | — | — | 100% (25/25) | — | — | 100% (25/25) |
| Held-out test | HD | — | — | 100% (25/25) | — | — | 100% (25/25) |
| Held-out test | KO | — | — | 100% (25/25) | — | — | 100% (25/25) |
| Held-out test | MCD | — | — | 100% (25/25) | — | — | 100% (25/25) |
| Held-out test | NEE | — | — | 80% (20/25) | — | — | 80% (20/25) |
| Held-out test | NFLX | — | — | 100% (25/25) | — | — | 100% (25/25) |
| Held-out test | NVDA | — | — | 100% (25/25) | — | — | 100% (25/25) |
| Held-out test | PFE | — | — | 100% (20/20) | — | — | 95% (19/20) |
| Held-out test | PG | — | — | 92% (23/25) | — | — | 100% (25/25) |
| Held-out test | TRV | — | — | 100% (20/20) | — | — | 100% (20/20) |
| Held-out test | UNH | — | — | 84% (21/25) | — | — | 100% (25/25) |
| Held-out test | V | — | — | 100% (20/20) | — | — | 100% (20/20) |
| Held-out test | VZ | — | — | 80% (20/25) | — | — | 96% (24/25) |
| Held-out test | WMT | — | — | 80% (20/25) | — | — | 100% (25/25) |

## Error categories

| Category | qwen3.5:2b / v1 · Development | qwen3.5:2b / v2 · Development | qwen3.5:2b / v3 · Development | qwen3.5:4b / v1 · Development | qwen3.5:4b / v2 · Development | qwen3.5:4b / v3 · Development | qwen3.5:2b / v3 · Held-out test | qwen3.5:4b / v3 · Held-out test |
|---|---|---|---|---|---|---|---|---|
| Value missing | 1 | 0 | 0 | 0 | 0 | 0 | 19 | 6 |
| Unit error (thousands/millions) | 5 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| Wrong metric (other row) | 5 | 2 | 2 | 0 | 0 | 0 | 29 | 9 |
| Other | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 0 |

## Metrics the company does not report

There is no ground truth for these (e.g. banks have no operating income). The right answer is "not reported"; a value here means the model picked some other line.

| Model / version · data set | Result |
|---|---|
| qwen3.5:2b / v1 · Development | 4 of 6 answered anyway |
| qwen3.5:2b / v2 · Development | 0 of 6 answered anyway |
| qwen3.5:2b / v3 · Development | 0 of 6 answered anyway |
| qwen3.5:4b / v1 · Development | 2 of 6 answered anyway |
| qwen3.5:4b / v2 · Development | 2 of 6 answered anyway |
| qwen3.5:4b / v3 · Development | 2 of 6 answered anyway |
| qwen3.5:2b / v3 · Held-out test | 10 of 30 answered anyway |
| qwen3.5:4b / v3 · Held-out test | 11 of 30 answered anyway |

| Data set | Model / version | Company | FY | Metric | Extracted | Quote |
|---|---|---|---|---|---|---|
| Development | qwen3.5:2b / v1 | JNJ | 2024 | OperatingIncome | 0 M | Earnings before provision for taxes on income |
| Development | qwen3.5:2b / v1 | JNJ | 2025 | OperatingIncome | 0 M | Earnings before provision for taxes on income |
| Development | qwen3.5:2b / v1 | JPM | 2024 | OperatingIncome | 75,081 M | Income before income tax expense |
| Development | qwen3.5:2b / v1 | JPM | 2025 | OperatingIncome | 72,595 M | Income before income tax expense |
| Development | qwen3.5:4b / v1 | JNJ | 2024 | OperatingIncome | 16,687 M | Earnings before provision for taxes on income / 16,687 / 15,062 / 19,359 |
| Development | qwen3.5:4b / v1 | JNJ | 2025 | OperatingIncome | 32,581 M | Earnings before provision for taxes on income / 32,581 / 16,687 / 15,062 |
| Development | qwen3.5:4b / v2 | JNJ | 2024 | OperatingIncome | 16,687 M | Earnings before provision for taxes on income / 16,687 / 15,062 / 19,359 |
| Development | qwen3.5:4b / v2 | JNJ | 2025 | OperatingIncome | 32,581 M | Earnings before provision for taxes on income / 32,581 / 16,687 / 15,062 |
| Development | qwen3.5:4b / v3 | JNJ | 2024 | OperatingIncome | 16,687 M | Earnings before provision for taxes on income / 16,687 / 15,062 / 19,359 |
| Development | qwen3.5:4b / v3 | JNJ | 2025 | OperatingIncome | 32,581 M | Earnings before provision for taxes on income / 32,581 / 16,687 / 15,062 |
| Held-out test | qwen3.5:2b / v3 | CAT | 2021 | NetIncome | 6,489 M | Profit 1 |
| Held-out test | qwen3.5:2b / v3 | CAT | 2022 | NetIncome | 6,705 M | Profit 1 |
| Held-out test | qwen3.5:2b / v3 | CAT | 2023 | NetIncome | 10,335 M | Profit 1 |
| Held-out test | qwen3.5:2b / v3 | CAT | 2024 | NetIncome | 10,792 M | Profit 1 |
| Held-out test | qwen3.5:2b / v3 | CAT | 2025 | NetIncome | 8,884 M | Profit 1 |
| Held-out test | qwen3.5:2b / v3 | V | 2021 | EPS | 5.63 | Class A common stock - Diluted Earnings Per Share |
| Held-out test | qwen3.5:2b / v3 | V | 2022 | EPS | 7.00 | Diluted Earnings Per Share Class A common stock |
| Held-out test | qwen3.5:2b / v3 | V | 2023 | EPS | 8.28 | Diluted Earnings Per Share Class A common stock |
| Held-out test | qwen3.5:2b / v3 | V | 2024 | EPS | 9.73 | Diluted Earnings Per Share Class A common stock |
| Held-out test | qwen3.5:2b / v3 | V | 2025 | EPS | 10.20 | Diluted Earnings Per Share Class A common stock |
| Held-out test | qwen3.5:4b / v3 | CAT | 2021 | NetIncome | 6,489 M | Profit 1 / $6,489 / $2,998 / $6,093 |
| Held-out test | qwen3.5:4b / v3 | CAT | 2022 | NetIncome | 6,705 M | Profit 1 / $6,705 / $6,489 / $2,998 |
| Held-out test | qwen3.5:4b / v3 | CAT | 2023 | NetIncome | 10,335 M | Profit 1 / $10,335 / $6,705 / $6,489 |
| Held-out test | qwen3.5:4b / v3 | CAT | 2024 | NetIncome | 10,788 M | Profit of consolidated and affiliated companies / 10,788 / 10,332 / 6,704 |
| Held-out test | qwen3.5:4b / v3 | CAT | 2025 | NetIncome | 8,884 M | Profit 1 / $8,884 / $10,792 / $10,335 |
| Held-out test | qwen3.5:4b / v3 | PFE | 2025 | OperatingIncome | 7,520 M | Income from continuing operations before provision/(benefit) for taxes on income |
| Held-out test | qwen3.5:4b / v3 | V | 2021 | EPS | 5.63 | Class A common stock / $5.63 / $4.89 / $5.32 |
| Held-out test | qwen3.5:4b / v3 | V | 2022 | EPS | 7.00 | Class A common stock / $7.00 / $5.63 / $4.89 |
| Held-out test | qwen3.5:4b / v3 | V | 2023 | EPS | 8.28 | Class A common stock / $8.28 / $7.00 / $5.63 |
| Held-out test | qwen3.5:4b / v3 | V | 2024 | EPS | 9.73 | Class A common stock / $9.73 / $8.28 / $7.00 |
| Held-out test | qwen3.5:4b / v3 | V | 2025 | EPS | 10.20 | Class A common stock / $10.20 / $9.73 / $8.28 |

## All errors

| Data set | Model / version | Company | FY | Metric | Correct | Extracted | Category | Detail |
|---|---|---|---|---|---|---|---|---|
| Development | qwen3.5:2b / v1 | JNJ | 2024 | NetIncome | 14,066 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| Development | qwen3.5:2b / v1 | JNJ | 2024 | Revenue | 88,821 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| Development | qwen3.5:2b / v1 | JNJ | 2025 | NetIncome | 26,804 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| Development | qwen3.5:2b / v1 | JNJ | 2025 | Revenue | 94,193 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| Development | qwen3.5:2b / v1 | JPM | 2024 | NetIncome | 58,471 M | 56,868 M | Wrong metric (other row) | number taken from another row: Net income applicable to common stockholders / $56,868 / $47,760 / $35,892 |
| Development | qwen3.5:2b / v1 | JPM | 2024 | Revenue | 177,556 M | 84,973 M | Wrong metric (other row) | number taken from another row: Noninterest revenue / 84,973 / 68,837 / 61,985 |
| Development | qwen3.5:2b / v1 | JPM | 2025 | Revenue | 182,447 M | 87,004 M | Wrong metric (other row) | number taken from another row: Noninterest revenue / 87,004 / 84,973 / 68,837 |
| Development | qwen3.5:2b / v1 | XOM | 2024 | EPS | 7.84 | — | Value missing | model returned no value |
| Development | qwen3.5:2b / v1 | XOM | 2024 | NetIncome | 33,680 M | 35,063 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Development | qwen3.5:2b / v1 | XOM | 2025 | NetIncome | 28,844 M | 0 M | Unit error (thousands/millions) | reported unit 'per share', correct would be 'millions' |
| Development | qwen3.5:2b / v1 | XOM | 2025 | Revenue | 332,238 M | 324 M | Wrong metric (other row) | number taken from another row: Sales and other operating revenue / 3 / 323,905 / 339,247 / 334,697 |
| Development | qwen3.5:2b / v2 | JNJ | 2024 | NetIncome | 14,066 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| Development | qwen3.5:2b / v2 | JNJ | 2024 | Revenue | 88,821 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| Development | qwen3.5:2b / v2 | JNJ | 2024 | TotalAssets | 180,104 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| Development | qwen3.5:2b / v2 | JNJ | 2025 | NetIncome | 26,804 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| Development | qwen3.5:2b / v2 | JNJ | 2025 | Revenue | 94,193 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| Development | qwen3.5:2b / v2 | JNJ | 2025 | TotalAssets | 199,210 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| Development | qwen3.5:2b / v2 | JPM | 2024 | NetIncome | 58,471 M | 56,868 M | Wrong metric (other row) | number taken from another row: Net income applicable to common stockholders / $56,868 / $47,760 / $35,892 |
| Development | qwen3.5:2b / v2 | JPM | 2024 | Revenue | 177,556 M | 84,973 M | Wrong metric (other row) | number taken from another row: Noninterest revenue / 84,973 / 68,837 / 61,985 |
| Development | qwen3.5:2b / v2 | XOM | 2024 | NetIncome | 33,680 M | 0 M | Unit error (thousands/millions) | reported unit 'per share', correct would be 'millions' |
| Development | qwen3.5:2b / v2 | XOM | 2025 | NetIncome | 28,844 M | 0 M | Unit error (thousands/millions) | reported unit 'per share', correct would be 'millions' |
| Development | qwen3.5:2b / v3 | JPM | 2024 | NetIncome | 58,471 M | 56,868 M | Wrong metric (other row) | number taken from another row: Net income applicable to common stockholders / $56,868 / $47,760 / $35,892 |
| Development | qwen3.5:2b / v3 | JPM | 2024 | Revenue | 177,556 M | 84,973 M | Wrong metric (other row) | number taken from another row: Noninterest revenue / 84,973 / 68,837 / 61,985 |
| Development | qwen3.5:4b / v1 | XOM | 2024 | EPS | 7.84 | 12.00 | Other | earlier column of the correct row (e.g. a note number): Earnings (loss) per common share (dollars) / 12 / 7.84 / 8.89 / 13.26 |
| Held-out test | qwen3.5:2b / v3 | BA | 2021 | EPS | -7.15 | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | BA | 2021 | NetIncome | -4,202 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | BA | 2021 | OperatingIncome | -2,902 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | BA | 2022 | EPS | -8.30 | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | BA | 2022 | NetIncome | -4,935 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | BA | 2022 | OperatingIncome | -3,547 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | BA | 2023 | EPS | -3.67 | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | BA | 2023 | NetIncome | -2,222 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | BA | 2023 | OperatingIncome | -773 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | BA | 2024 | EPS | -18.36 | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | BA | 2024 | NetIncome | -11,817 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | BA | 2024 | OperatingIncome | -10,707 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | BA | 2025 | OperatingIncome | 4,281 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | BAC | 2024 | NetIncome | 27,132 M | 25,503 M | Wrong metric (other row) | number taken from another row: Net income applicable to common shareholders / $25,503 / $24,866 / $26,015 |
| Held-out test | qwen3.5:2b / v3 | CVX | 2021 | EPS | 8.14 | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | CVX | 2025 | NetIncome | 12,299 M | 12,485 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | DIS | 2021 | EPS | 1.09 | 1.11 | Wrong metric (other row) | number taken from another row: Continuing operations / $1.11 / $(1.57) / $6.26 |
| Held-out test | qwen3.5:2b / v3 | DIS | 2021 | NetIncome | 1,995 M | 2,507 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | DIS | 2021 | OperatingIncome | 7,766 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | DIS | 2022 | EPS | 1.72 | 1.75 | Wrong metric (other row) | number taken from another row: Continuing operations / $1.75 / $1.11 / $(1.57) |
| Held-out test | qwen3.5:2b / v3 | DIS | 2022 | NetIncome | 3,145 M | 3,505 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | DIS | 2022 | OperatingIncome | 12,121 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | DIS | 2023 | NetIncome | 2,354 M | 3,390 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | DIS | 2023 | OperatingIncome | 12,863 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | DIS | 2024 | NetIncome | 4,972 M | 5,773 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | DIS | 2024 | OperatingIncome | 15,601 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | DIS | 2025 | NetIncome | 12,404 M | 13,431 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | DIS | 2025 | OperatingIncome | 17,551 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:2b / v3 | NEE | 2021 | Revenue | 18,800 M | 17,069 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $17,069 / $17,997 / $19,204 |
| Held-out test | qwen3.5:2b / v3 | NEE | 2022 | Revenue | 23,000 M | 20,956 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $20,956 / $17,069 / $17,997 |
| Held-out test | qwen3.5:2b / v3 | NEE | 2023 | Revenue | 24,800 M | 28,114 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $28,114 / $20,956 / $17,069 |
| Held-out test | qwen3.5:2b / v3 | NEE | 2024 | Revenue | 23,500 M | 24,753 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $24,753 / $28,114 / $20,956 |
| Held-out test | qwen3.5:2b / v3 | NEE | 2025 | Revenue | 25,800 M | 27,412 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $27,412 / $24,753 / $28,114 |
| Held-out test | qwen3.5:2b / v3 | PG | 2024 | NetIncome | 14,879 M | 14,974 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | PG | 2025 | NetIncome | 15,974 M | 16,065 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | UNH | 2022 | NetIncome | 20,120 M | 20,639 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | UNH | 2023 | NetIncome | 22,381 M | 23,144 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | UNH | 2024 | NetIncome | 14,405 M | 15,242 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | UNH | 2025 | NetIncome | 12,056 M | 12,807 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | VZ | 2021 | NetIncome | 22,065 M | 22,618 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | VZ | 2022 | NetIncome | 21,256 M | 21,748 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | VZ | 2023 | NetIncome | 11,614 M | 12,095 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | VZ | 2024 | NetIncome | 17,506 M | 17,949 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | VZ | 2025 | NetIncome | 17,174 M | 17,608 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | WMT | 2022 | NetIncome | 13,673 M | 13,940 M | Other | earlier column of the correct row (e.g. a note number): Consolidated net income / 13,940 / 13,706 / 15,201 |
| Held-out test | qwen3.5:2b / v3 | WMT | 2023 | NetIncome | 11,680 M | 11,292 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | WMT | 2024 | NetIncome | 15,511 M | 16,270 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | WMT | 2025 | NetIncome | 19,436 M | 20,157 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:2b / v3 | WMT | 2026 | NetIncome | 21,893 M | 22,270 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:4b / v3 | BA | 2021 | OperatingIncome | -2,902 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:4b / v3 | BA | 2023 | OperatingIncome | -773 M | 7,724 M | Wrong metric (other row) | number taken from another row: 7,724 / 3,530 / 3,049 |
| Held-out test | qwen3.5:4b / v3 | BA | 2025 | NetIncome | 2,235 M | 1,890 M | Wrong metric (other row) | number taken from another row: Net earnings/(loss) attributable to Boeing common shareholders / $ 1,890 / ($ 11,875) / ($ |
| Held-out test | qwen3.5:4b / v3 | DIS | 2021 | OperatingIncome | 7,766 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:4b / v3 | DIS | 2022 | OperatingIncome | 12,121 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:4b / v3 | DIS | 2023 | OperatingIncome | 12,863 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:4b / v3 | DIS | 2024 | OperatingIncome | 15,601 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:4b / v3 | DIS | 2025 | OperatingIncome | 17,551 M | — | Value missing | model returned no value |
| Held-out test | qwen3.5:4b / v3 | NEE | 2021 | Revenue | 18,800 M | 17,069 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $17,069 / $17,997 / $19,204 |
| Held-out test | qwen3.5:4b / v3 | NEE | 2022 | Revenue | 23,000 M | 20,956 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $20,956 / $17,069 / $17,997 |
| Held-out test | qwen3.5:4b / v3 | NEE | 2023 | Revenue | 24,800 M | 28,114 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $28,114 / $20,956 / $17,069 |
| Held-out test | qwen3.5:4b / v3 | NEE | 2024 | Revenue | 23,500 M | 24,753 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $24,753 / $28,114 / $20,956 |
| Held-out test | qwen3.5:4b / v3 | NEE | 2025 | Revenue | 25,800 M | 27,412 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $27,412 / $24,753 / $28,114 |
| Held-out test | qwen3.5:4b / v3 | PFE | 2023 | NetIncome | 2,119 M | 2,158 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Held-out test | qwen3.5:4b / v3 | VZ | 2023 | NetIncome | 11,614 M | 12,095 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
