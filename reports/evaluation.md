# Evaluation report

_Generated 2026-10-15 by `python -m edgar_extract.evaluate`._

A value counts as correct if it is within 0.5% of the XBRL ground truth. Metrics without ground truth are excluded from the accuracy.

- **Development:** 10 filings from 5 companies (AAPL, JNJ, JPM, MSFT, XOM). Prompts and code were tuned on these, so their accuracy is optimistic.
- **Test set 1:** 100 filings from 20 companies (AMZN, BA, BAC, CAT, CVX, DIS, GOOGL, HD, KO, MCD, NEE, NFLX, NVDA, PFE, PG, TRV, UNH, V, VZ, WMT). Held out until v3; its errors were then studied to build v4, so v4 results here are optimistic too.
- **Test set 2:** 75 filings from 15 companies (AIG, CMCSA, COST, DUK, F, GS, INTC, LLY, LMT, MRNA, NKE, ORCL, T, UBER, WBD). Added after v4 was written and never used for tuning — the honest measure for v4.

## Overall accuracy

| Data set | Model / version | Accuracy | Avg input tokens | Avg output tokens | Avg seconds / filing | Cost / filing | Format issues | Code corrections | Quotes found in text |
|---|---|---|---|---|---|---|---|---|---|
| Development | qwen3.5:2b / v1 | 75% (33/44) | 2,815 | 210 | 6.8 | $0.0000 | 43 | 0 | 100% (47/47) |
| Development | qwen3.5:2b / v2 | 77% (34/44) | 3,045 | 203 | 6.9 | $0.0000 | 8 | 0 | 98% (43/44) |
| Development | qwen3.5:2b / v3 | 95% (42/44) | 3,045 | 203 | 6.9 | $0.0000 | 8 | 0 | 98% (43/44) |
| Development | qwen3.5:2b / v4 | 100% (44/44) | 3,126 | 204 | 6.9 | $0.0000 | 4 | 0 | 100% (44/44) |
| Development | qwen3.5:4b / v1 | 98% (43/44) | 2,815 | 307 | 15.2 | $0.0000 | 4 | 0 | 98% (45/46) |
| Development | qwen3.5:4b / v2 | 100% (44/44) | 3,045 | 291 | 15.8 | $0.0000 | 0 | 0 | 98% (45/46) |
| Development | qwen3.5:4b / v3 | 100% (44/44) | 3,045 | 291 | 15.8 | $0.0000 | 0 | 0 | 98% (45/46) |
| Development | qwen3.5:4b / v4 | 100% (44/44) | 3,126 | 292 | 15.7 | $0.0000 | 0 | 0 | 98% (45/46) |
| Test set 1 | qwen3.5:2b / v3 | 90% (421/470) | 3,031 | 206 | 6.3 | $0.0000 | 10 | 0 | 95% (438/461) |
| Test set 1 | qwen3.5:2b / v4 | 97% (456/470) | 3,112 | 209 | 6.5 | $0.0000 | 20 | 49 | 95% (450/475) |
| Test set 1 | qwen3.5:4b / v3 | 97% (455/470) | 3,031 | 310 | 15.0 | $0.0000 | 0 | 0 | 100% (473/475) |
| Test set 1 | qwen3.5:4b / v4 | 97% (458/470) | 3,112 | 310 | 15.0 | $0.0000 | 0 | 12 | 100% (478/480) |
| Test set 2 | qwen3.5:2b / v3 | 88% (310/351) | 3,285 | 209 | 6.7 | $0.0000 | 23 | 0 | 90% (313/348) |
| Test set 2 | qwen3.5:2b / v4 | 95% (335/351) | 3,366 | 212 | 6.8 | $0.0000 | 20 | 28 | 90% (320/357) |
| Test set 2 | qwen3.5:4b / v3 | 95% (335/351) | 3,285 | 308 | 15.9 | $0.0000 | 20 | 0 | 97% (350/359) |
| Test set 2 | qwen3.5:4b / v4 | 97% (342/351) | 3,366 | 310 | 15.9 | $0.0000 | 20 | 11 | 98% (355/363) |

## Accuracy per metric

| Metric | qwen3.5:2b / v1 · Development | qwen3.5:2b / v2 · Development | qwen3.5:2b / v3 · Development | qwen3.5:2b / v4 · Development | qwen3.5:4b / v1 · Development | qwen3.5:4b / v2 · Development | qwen3.5:4b / v3 · Development | qwen3.5:4b / v4 · Development | qwen3.5:2b / v3 · Test set 1 | qwen3.5:2b / v4 · Test set 1 | qwen3.5:4b / v3 · Test set 1 | qwen3.5:4b / v4 · Test set 1 | qwen3.5:2b / v3 · Test set 2 | qwen3.5:2b / v4 · Test set 2 | qwen3.5:4b / v3 · Test set 2 | qwen3.5:4b / v4 · Test set 2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Revenue | 50% (5/10) | 70% (7/10) | 90% (9/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 95% (95/100) | 95% (95/100) | 95% (95/100) | 95% (95/100) | 93% (70/75) | 93% (70/75) | 95% (71/75) | 95% (71/75) |
| OperatingIncome | 100% (4/4) | 100% (4/4) | 100% (4/4) | 100% (4/4) | 100% (4/4) | 100% (4/4) | 100% (4/4) | 100% (4/4) | 88% (70/80) | 94% (75/80) | 91% (73/80) | 94% (75/80) | 89% (49/55) | 98% (54/55) | 98% (54/55) | 100% (55/55) |
| NetIncome | 50% (5/10) | 50% (5/10) | 90% (9/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 72% (68/95) | 99% (94/95) | 97% (92/95) | 99% (94/95) | 64% (46/72) | 89% (64/72) | 85% (61/72) | 93% (67/72) |
| EPS | 90% (9/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 90% (9/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 93% (88/95) | 97% (92/95) | 100% (95/95) | 99% (94/95) | 95% (70/74) | 97% (72/74) | 100% (74/74) | 100% (74/74) |
| TotalAssets | 100% (10/10) | 80% (8/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (100/100) | 100% (100/100) | 100% (100/100) | 100% (100/100) | 100% (75/75) | 100% (75/75) | 100% (75/75) | 100% (75/75) |

## Accuracy per company

| Data set | Company | qwen3.5:2b / v1 | qwen3.5:2b / v2 | qwen3.5:2b / v3 | qwen3.5:2b / v4 | qwen3.5:4b / v1 | qwen3.5:4b / v2 | qwen3.5:4b / v3 | qwen3.5:4b / v4 |
|---|---|---|---|---|---|---|---|---|---|
| Development | AAPL | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| Development | JNJ | 50% (4/8) | 25% (2/8) | 100% (8/8) | 100% (8/8) | 100% (8/8) | 100% (8/8) | 100% (8/8) | 100% (8/8) |
| Development | JPM | 62% (5/8) | 75% (6/8) | 75% (6/8) | 100% (8/8) | 100% (8/8) | 100% (8/8) | 100% (8/8) | 100% (8/8) |
| Development | MSFT | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| Development | XOM | 50% (4/8) | 75% (6/8) | 100% (8/8) | 100% (8/8) | 88% (7/8) | 100% (8/8) | 100% (8/8) | 100% (8/8) |
| Test set 1 | AMZN | — | — | 100% (25/25) | 100% (25/25) | — | — | 100% (25/25) | 100% (25/25) |
| Test set 1 | BA | — | — | 48% (12/25) | 100% (25/25) | — | — | 88% (22/25) | 96% (24/25) |
| Test set 1 | BAC | — | — | 95% (19/20) | 95% (19/20) | — | — | 100% (20/20) | 100% (20/20) |
| Test set 1 | CAT | — | — | 100% (20/20) | 100% (20/20) | — | — | 100% (20/20) | 100% (20/20) |
| Test set 1 | CVX | — | — | 90% (18/20) | 100% (20/20) | — | — | 100% (20/20) | 100% (20/20) |
| Test set 1 | DIS | — | — | 52% (13/25) | 68% (17/25) | — | — | 80% (20/25) | 80% (20/25) |
| Test set 1 | GOOGL | — | — | 100% (25/25) | 100% (25/25) | — | — | 100% (25/25) | 100% (25/25) |
| Test set 1 | HD | — | — | 100% (25/25) | 100% (25/25) | — | — | 100% (25/25) | 100% (25/25) |
| Test set 1 | KO | — | — | 100% (25/25) | 100% (25/25) | — | — | 100% (25/25) | 100% (25/25) |
| Test set 1 | MCD | — | — | 100% (25/25) | 100% (25/25) | — | — | 100% (25/25) | 100% (25/25) |
| Test set 1 | NEE | — | — | 80% (20/25) | 80% (20/25) | — | — | 80% (20/25) | 80% (20/25) |
| Test set 1 | NFLX | — | — | 100% (25/25) | 100% (25/25) | — | — | 100% (25/25) | 100% (25/25) |
| Test set 1 | NVDA | — | — | 100% (25/25) | 100% (25/25) | — | — | 100% (25/25) | 100% (25/25) |
| Test set 1 | PFE | — | — | 100% (20/20) | 100% (20/20) | — | — | 95% (19/20) | 95% (19/20) |
| Test set 1 | PG | — | — | 92% (23/25) | 100% (25/25) | — | — | 100% (25/25) | 100% (25/25) |
| Test set 1 | TRV | — | — | 100% (20/20) | 100% (20/20) | — | — | 100% (20/20) | 100% (20/20) |
| Test set 1 | UNH | — | — | 84% (21/25) | 100% (25/25) | — | — | 100% (25/25) | 100% (25/25) |
| Test set 1 | V | — | — | 100% (20/20) | 100% (20/20) | — | — | 100% (20/20) | 100% (20/20) |
| Test set 1 | VZ | — | — | 80% (20/25) | 100% (25/25) | — | — | 96% (24/25) | 100% (25/25) |
| Test set 1 | WMT | — | — | 80% (20/25) | 100% (25/25) | — | — | 100% (25/25) | 100% (25/25) |
| Test set 2 | AIG | — | — | 75% (15/20) | 90% (18/20) | — | — | 85% (17/20) | 100% (20/20) |
| Test set 2 | CMCSA | — | — | 100% (25/25) | 100% (25/25) | — | — | 100% (25/25) | 100% (25/25) |
| Test set 2 | COST | — | — | 100% (25/25) | 100% (25/25) | — | — | 100% (25/25) | 100% (25/25) |
| Test set 2 | DUK | — | — | 64% (16/25) | 84% (21/25) | — | — | 84% (21/25) | 84% (21/25) |
| Test set 2 | F | — | — | 100% (22/22) | 100% (22/22) | — | — | 100% (22/22) | 100% (22/22) |
| Test set 2 | GS | — | — | 80% (16/20) | 90% (18/20) | — | — | 90% (18/20) | 100% (20/20) |
| Test set 2 | INTC | — | — | 80% (20/25) | 96% (24/25) | — | — | 96% (24/25) | 100% (25/25) |
| Test set 2 | LLY | — | — | 100% (20/20) | 100% (20/20) | — | — | 100% (20/20) | 100% (20/20) |
| Test set 2 | LMT | — | — | 100% (25/25) | 100% (25/25) | — | — | 100% (25/25) | 100% (25/25) |
| Test set 2 | MRNA | — | — | 96% (24/25) | 100% (25/25) | — | — | 100% (25/25) | 100% (25/25) |
| Test set 2 | NKE | — | — | 100% (20/20) | 100% (20/20) | — | — | 100% (20/20) | 100% (20/20) |
| Test set 2 | ORCL | — | — | 100% (25/25) | 100% (25/25) | — | — | 100% (25/25) | 100% (25/25) |
| Test set 2 | T | — | — | 72% (18/25) | 92% (23/25) | — | — | 96% (24/25) | 96% (24/25) |
| Test set 2 | UBER | — | — | 88% (22/25) | 100% (25/25) | — | — | 100% (25/25) | 100% (25/25) |
| Test set 2 | WBD | — | — | 71% (17/24) | 79% (19/24) | — | — | 79% (19/24) | 83% (20/24) |

## Error categories

| Category | qwen3.5:2b / v1 · Development | qwen3.5:2b / v2 · Development | qwen3.5:2b / v3 · Development | qwen3.5:2b / v4 · Development | qwen3.5:4b / v1 · Development | qwen3.5:4b / v2 · Development | qwen3.5:4b / v3 · Development | qwen3.5:4b / v4 · Development | qwen3.5:2b / v3 · Test set 1 | qwen3.5:2b / v4 · Test set 1 | qwen3.5:4b / v3 · Test set 1 | qwen3.5:4b / v4 · Test set 1 | qwen3.5:2b / v3 · Test set 2 | qwen3.5:2b / v4 · Test set 2 | qwen3.5:4b / v3 · Test set 2 | qwen3.5:4b / v4 · Test set 2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Value missing | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 19 | 6 | 6 | 3 | 8 | 1 | 1 | 0 |
| Unit error (thousands/millions) | 5 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 |
| Wrong metric (other row) | 5 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 29 | 8 | 9 | 8 | 30 | 12 | 14 | 8 |
| Other | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 1 |

## Metrics the company does not report

There is no ground truth for these (e.g. banks have no operating income). The right answer is "not reported"; a value here means the model picked some other line.

| Model / version · data set | Result |
|---|---|
| qwen3.5:2b / v1 · Development | 4 of 6 answered anyway |
| qwen3.5:2b / v2 · Development | 0 of 6 answered anyway |
| qwen3.5:2b / v3 · Development | 0 of 6 answered anyway |
| qwen3.5:2b / v4 · Development | 0 of 6 answered anyway |
| qwen3.5:4b / v1 · Development | 2 of 6 answered anyway |
| qwen3.5:4b / v2 · Development | 2 of 6 answered anyway |
| qwen3.5:4b / v3 · Development | 2 of 6 answered anyway |
| qwen3.5:4b / v4 · Development | 2 of 6 answered anyway |
| qwen3.5:2b / v3 · Test set 1 | 10 of 30 answered anyway |
| qwen3.5:2b / v4 · Test set 1 | 11 of 30 answered anyway |
| qwen3.5:4b / v3 · Test set 1 | 11 of 30 answered anyway |
| qwen3.5:4b / v4 · Test set 1 | 13 of 30 answered anyway |
| qwen3.5:2b / v3 · Test set 2 | 5 of 24 answered anyway |
| qwen3.5:2b / v4 · Test set 2 | 7 of 24 answered anyway |
| qwen3.5:4b / v3 · Test set 2 | 9 of 24 answered anyway |
| qwen3.5:4b / v4 · Test set 2 | 12 of 24 answered anyway |

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
| Development | qwen3.5:4b / v4 | JNJ | 2024 | OperatingIncome | 16,687 M | Earnings before provision for taxes on income / 16,687 / 15,062 / 19,359 |
| Development | qwen3.5:4b / v4 | JNJ | 2025 | OperatingIncome | 32,581 M | Earnings before provision for taxes on income / 32,581 / 16,687 / 15,062 |
| Test set 1 | qwen3.5:2b / v3 | CAT | 2021 | NetIncome | 6,489 M | Profit 1 |
| Test set 1 | qwen3.5:2b / v3 | CAT | 2022 | NetIncome | 6,705 M | Profit 1 |
| Test set 1 | qwen3.5:2b / v3 | CAT | 2023 | NetIncome | 10,335 M | Profit 1 |
| Test set 1 | qwen3.5:2b / v3 | CAT | 2024 | NetIncome | 10,792 M | Profit 1 |
| Test set 1 | qwen3.5:2b / v3 | CAT | 2025 | NetIncome | 8,884 M | Profit 1 |
| Test set 1 | qwen3.5:2b / v3 | V | 2021 | EPS | 5.63 | Class A common stock - Diluted Earnings Per Share |
| Test set 1 | qwen3.5:2b / v3 | V | 2022 | EPS | 7.00 | Diluted Earnings Per Share Class A common stock |
| Test set 1 | qwen3.5:2b / v3 | V | 2023 | EPS | 8.28 | Diluted Earnings Per Share Class A common stock |
| Test set 1 | qwen3.5:2b / v3 | V | 2024 | EPS | 9.73 | Diluted Earnings Per Share Class A common stock |
| Test set 1 | qwen3.5:2b / v3 | V | 2025 | EPS | 10.20 | Diluted Earnings Per Share Class A common stock |
| Test set 1 | qwen3.5:2b / v4 | CAT | 2021 | NetIncome | 6,489 M | Profit 1 |
| Test set 1 | qwen3.5:2b / v4 | CAT | 2022 | NetIncome | 6,705 M | Profit 1 |
| Test set 1 | qwen3.5:2b / v4 | CAT | 2023 | NetIncome | 10,335 M | Profit 1 |
| Test set 1 | qwen3.5:2b / v4 | CAT | 2024 | NetIncome | 10,792 M | Profit 1 |
| Test set 1 | qwen3.5:2b / v4 | CAT | 2025 | NetIncome | 8,884 M | Profit 1 |
| Test set 1 | qwen3.5:2b / v4 | PFE | 2022 | OperatingIncome | 34,729 M | Income from continuing operations before provision/(benefit) for taxes on income |
| Test set 1 | qwen3.5:2b / v4 | V | 2021 | EPS | 5.63 | Basic Earnings Per Share Class A common stock |
| Test set 1 | qwen3.5:2b / v4 | V | 2022 | EPS | 7.00 | Diluted Earnings Per Share Class A common stock |
| Test set 1 | qwen3.5:2b / v4 | V | 2023 | EPS | 8.28 | Diluted Earnings Per Share Class A common stock |
| Test set 1 | qwen3.5:2b / v4 | V | 2024 | EPS | 9.73 | Diluted Earnings Per Share Class A common stock |
| Test set 1 | qwen3.5:2b / v4 | V | 2025 | EPS | 10.20 | Diluted Earnings Per Share Class A common stock |
| Test set 1 | qwen3.5:4b / v3 | CAT | 2021 | NetIncome | 6,489 M | Profit 1 / $6,489 / $2,998 / $6,093 |
| Test set 1 | qwen3.5:4b / v3 | CAT | 2022 | NetIncome | 6,705 M | Profit 1 / $6,705 / $6,489 / $2,998 |
| Test set 1 | qwen3.5:4b / v3 | CAT | 2023 | NetIncome | 10,335 M | Profit 1 / $10,335 / $6,705 / $6,489 |
| Test set 1 | qwen3.5:4b / v3 | CAT | 2024 | NetIncome | 10,788 M | Profit of consolidated and affiliated companies / 10,788 / 10,332 / 6,704 |
| Test set 1 | qwen3.5:4b / v3 | CAT | 2025 | NetIncome | 8,884 M | Profit 1 / $8,884 / $10,792 / $10,335 |
| Test set 1 | qwen3.5:4b / v3 | PFE | 2025 | OperatingIncome | 7,520 M | Income from continuing operations before provision/(benefit) for taxes on income |
| Test set 1 | qwen3.5:4b / v3 | V | 2021 | EPS | 5.63 | Class A common stock / $5.63 / $4.89 / $5.32 |
| Test set 1 | qwen3.5:4b / v3 | V | 2022 | EPS | 7.00 | Class A common stock / $7.00 / $5.63 / $4.89 |
| Test set 1 | qwen3.5:4b / v3 | V | 2023 | EPS | 8.28 | Class A common stock / $8.28 / $7.00 / $5.63 |
| Test set 1 | qwen3.5:4b / v3 | V | 2024 | EPS | 9.73 | Class A common stock / $9.73 / $8.28 / $7.00 |
| Test set 1 | qwen3.5:4b / v3 | V | 2025 | EPS | 10.20 | Class A common stock / $10.20 / $9.73 / $8.28 |
| Test set 1 | qwen3.5:4b / v4 | CAT | 2021 | NetIncome | 6,489 M | Profit 1 / $6,489 / $2,998 / $6,093 |
| Test set 1 | qwen3.5:4b / v4 | CAT | 2022 | NetIncome | 6,705 M | Profit 1 |
| Test set 1 | qwen3.5:4b / v4 | CAT | 2023 | NetIncome | 10,335 M | Profit 1 |
| Test set 1 | qwen3.5:4b / v4 | CAT | 2024 | NetIncome | 10,792 M | Profit of consolidated and affiliated companies / 10,788 / 10,332 / 6,704 |
| Test set 1 | qwen3.5:4b / v4 | CAT | 2025 | NetIncome | 8,884 M | Profit 1 / $8,884 / $10,792 / $10,335 |
| Test set 1 | qwen3.5:4b / v4 | PFE | 2022 | OperatingIncome | 34,729 M | Income from continuing operations before provision/(benefit) for taxes on income |
| Test set 1 | qwen3.5:4b / v4 | PFE | 2024 | OperatingIncome | 8,023 M | Income from continuing operations before provision/(benefit) for taxes on income |
| Test set 1 | qwen3.5:4b / v4 | PFE | 2025 | OperatingIncome | 7,520 M | Income from continuing operations before provision/(benefit) for taxes on income |
| Test set 1 | qwen3.5:4b / v4 | V | 2021 | EPS | 5.63 | Class A common stock / $5.63 / $4.89 / $5.32 |
| Test set 1 | qwen3.5:4b / v4 | V | 2022 | EPS | 7.00 | Class A common stock / $7.00 / $5.63 / $4.89 |
| Test set 1 | qwen3.5:4b / v4 | V | 2023 | EPS | 8.28 | Class A common stock / $8.28 / $7.00 / $5.63 |
| Test set 1 | qwen3.5:4b / v4 | V | 2024 | EPS | 9.73 | Class A common stock / $9.73 / $8.28 / $7.00 |
| Test set 1 | qwen3.5:4b / v4 | V | 2025 | EPS | 10.20 | Class A common stock / $10.20 / $9.73 / $8.28 |
| Test set 2 | qwen3.5:2b / v3 | F | 2021 | NetIncome | 17,910 M | Net income/(loss) |
| Test set 2 | qwen3.5:2b / v3 | F | 2022 | NetIncome | -2,152 M | Net income/(loss) |
| Test set 2 | qwen3.5:2b / v3 | F | 2025 | NetIncome | -8,162 M | Net income/(loss) attributable to Ford Motor Company |
| Test set 2 | qwen3.5:2b / v3 | GS | 2022 | OperatingIncome | 13,486 M | Pre-tax earnings |
| Test set 2 | qwen3.5:2b / v3 | WBD | 2021 | EPS | 1.54 | Diluted |
| Test set 2 | qwen3.5:2b / v4 | F | 2021 | NetIncome | 17,937 M | Net income/(loss) |
| Test set 2 | qwen3.5:2b / v4 | F | 2022 | NetIncome | -1,981 M | Net income/(loss) |
| Test set 2 | qwen3.5:2b / v4 | F | 2025 | NetIncome | -8,182 M | Net income/(loss) |
| Test set 2 | qwen3.5:2b / v4 | GS | 2022 | OperatingIncome | 13,486 M | Pre-tax earnings |
| Test set 2 | qwen3.5:2b / v4 | GS | 2023 | OperatingIncome | 10,739 M | Pre-tax earnings |
| Test set 2 | qwen3.5:2b / v4 | GS | 2024 | OperatingIncome | 18,397 M | Pre-tax earnings |
| Test set 2 | qwen3.5:2b / v4 | WBD | 2021 | EPS | 1.54 | Diluted |
| Test set 2 | qwen3.5:4b / v3 | F | 2021 | NetIncome | 17,910 M | Net income/(loss) / 84 / (1,276) / 17,910 |
| Test set 2 | qwen3.5:4b / v3 | F | 2022 | NetIncome | -1,981 M | Net income/(loss) attributable to Ford Motor Company / $(1,279) / $17,937 / $(1, |
| Test set 2 | qwen3.5:4b / v3 | F | 2025 | NetIncome | -8,182 M | Net income/(loss) attributable to Ford Motor Company / $4,347 / $5,879 / $(8,182 |
| Test set 2 | qwen3.5:4b / v3 | GS | 2021 | OperatingIncome | 27,044 M | Pre-tax earnings / 27,044 / 12,479 / 10,583 |
| Test set 2 | qwen3.5:4b / v3 | GS | 2022 | OperatingIncome | 13,486 M | Pre-tax earnings / 13,486 / 27,044 / 12,479 |
| Test set 2 | qwen3.5:4b / v3 | GS | 2023 | OperatingIncome | 10,739 M | Pre-tax earnings / 10,739 / 13,486 / 27,044 |
| Test set 2 | qwen3.5:4b / v3 | GS | 2024 | OperatingIncome | 18,397 M | Pre-tax earnings / 18,397 / 10,739 / 13,486 |
| Test set 2 | qwen3.5:4b / v3 | GS | 2025 | OperatingIncome | 21,852 M | Pre-tax earnings / 21,852 / 18,397 / 10,739 |
| Test set 2 | qwen3.5:4b / v3 | WBD | 2021 | EPS | 154.00 | Diluted / $1.54 / $1.81 / $2.88 |
| Test set 2 | qwen3.5:4b / v4 | F | 2021 | NetIncome | 17,937 M | Net income/(loss) / 84 / (1,276) / 17,910 |
| Test set 2 | qwen3.5:4b / v4 | F | 2022 | NetIncome | -1,981 M | Net income/(loss) attributable to Ford Motor Company / $(1,279) / $17,937 / $(1, |
| Test set 2 | qwen3.5:4b / v4 | F | 2025 | NetIncome | -8,182 M | Net income/(loss) attributable to Ford Motor Company / $4,347 / $5,879 / $(8,182 |
| Test set 2 | qwen3.5:4b / v4 | GS | 2021 | OperatingIncome | 27,044 M | Pre-tax earnings / 27,044 / 12,479 / 10,583 |
| Test set 2 | qwen3.5:4b / v4 | GS | 2022 | OperatingIncome | 13,486 M | Pre-tax earnings / 13,486 / 27,044 / 12,479 |
| Test set 2 | qwen3.5:4b / v4 | GS | 2023 | OperatingIncome | 10,739 M | Pre-tax earnings / 10,739 / 13,486 / 27,044 |
| Test set 2 | qwen3.5:4b / v4 | GS | 2024 | OperatingIncome | 18,397 M | Pre-tax earnings / 18,397 / 10,739 / 13,486 |
| Test set 2 | qwen3.5:4b / v4 | GS | 2025 | OperatingIncome | 21,852 M | Pre-tax earnings / 21,852 / 18,397 / 10,739 |
| Test set 2 | qwen3.5:4b / v4 | LLY | 2025 | OperatingIncome | 25,731 M | Income before income taxes / 25,731 / 12,680 / 6,554 |
| Test set 2 | qwen3.5:4b / v4 | NKE | 2022 | OperatingIncome | 6,651 M | Income before income taxes / 6,651 / 6,661 / 2,887 |
| Test set 2 | qwen3.5:4b / v4 | NKE | 2023 | OperatingIncome | 6,201 M | Income before income taxes / 6,201 / 6,651 / 6,661 |
| Test set 2 | qwen3.5:4b / v4 | WBD | 2021 | EPS | 154.00 | Diluted / $1.54 / $1.81 / $2.88 |

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
| Test set 1 | qwen3.5:2b / v3 | BA | 2021 | EPS | -7.15 | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | BA | 2021 | NetIncome | -4,202 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | BA | 2021 | OperatingIncome | -2,902 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | BA | 2022 | EPS | -8.30 | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | BA | 2022 | NetIncome | -4,935 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | BA | 2022 | OperatingIncome | -3,547 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | BA | 2023 | EPS | -3.67 | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | BA | 2023 | NetIncome | -2,222 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | BA | 2023 | OperatingIncome | -773 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | BA | 2024 | EPS | -18.36 | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | BA | 2024 | NetIncome | -11,817 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | BA | 2024 | OperatingIncome | -10,707 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | BA | 2025 | OperatingIncome | 4,281 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | BAC | 2024 | NetIncome | 27,132 M | 25,503 M | Wrong metric (other row) | number taken from another row: Net income applicable to common shareholders / $25,503 / $24,866 / $26,015 |
| Test set 1 | qwen3.5:2b / v3 | CVX | 2021 | EPS | 8.14 | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | CVX | 2025 | NetIncome | 12,299 M | 12,485 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | DIS | 2021 | EPS | 1.09 | 1.11 | Wrong metric (other row) | number taken from another row: Continuing operations / $1.11 / $(1.57) / $6.26 |
| Test set 1 | qwen3.5:2b / v3 | DIS | 2021 | NetIncome | 1,995 M | 2,507 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | DIS | 2021 | OperatingIncome | 7,766 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | DIS | 2022 | EPS | 1.72 | 1.75 | Wrong metric (other row) | number taken from another row: Continuing operations / $1.75 / $1.11 / $(1.57) |
| Test set 1 | qwen3.5:2b / v3 | DIS | 2022 | NetIncome | 3,145 M | 3,505 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | DIS | 2022 | OperatingIncome | 12,121 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | DIS | 2023 | NetIncome | 2,354 M | 3,390 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | DIS | 2023 | OperatingIncome | 12,863 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | DIS | 2024 | NetIncome | 4,972 M | 5,773 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | DIS | 2024 | OperatingIncome | 15,601 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | DIS | 2025 | NetIncome | 12,404 M | 13,431 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | DIS | 2025 | OperatingIncome | 17,551 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v3 | NEE | 2021 | Revenue | 18,800 M | 17,069 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $17,069 / $17,997 / $19,204 |
| Test set 1 | qwen3.5:2b / v3 | NEE | 2022 | Revenue | 23,000 M | 20,956 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $20,956 / $17,069 / $17,997 |
| Test set 1 | qwen3.5:2b / v3 | NEE | 2023 | Revenue | 24,800 M | 28,114 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $28,114 / $20,956 / $17,069 |
| Test set 1 | qwen3.5:2b / v3 | NEE | 2024 | Revenue | 23,500 M | 24,753 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $24,753 / $28,114 / $20,956 |
| Test set 1 | qwen3.5:2b / v3 | NEE | 2025 | Revenue | 25,800 M | 27,412 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $27,412 / $24,753 / $28,114 |
| Test set 1 | qwen3.5:2b / v3 | PG | 2024 | NetIncome | 14,879 M | 14,974 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | PG | 2025 | NetIncome | 15,974 M | 16,065 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | UNH | 2022 | NetIncome | 20,120 M | 20,639 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | UNH | 2023 | NetIncome | 22,381 M | 23,144 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | UNH | 2024 | NetIncome | 14,405 M | 15,242 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | UNH | 2025 | NetIncome | 12,056 M | 12,807 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | VZ | 2021 | NetIncome | 22,065 M | 22,618 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | VZ | 2022 | NetIncome | 21,256 M | 21,748 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | VZ | 2023 | NetIncome | 11,614 M | 12,095 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | VZ | 2024 | NetIncome | 17,506 M | 17,949 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | VZ | 2025 | NetIncome | 17,174 M | 17,608 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | WMT | 2022 | NetIncome | 13,673 M | 13,940 M | Other | earlier column of the correct row (e.g. a note number): Consolidated net income / 13,940 / 13,706 / 15,201 |
| Test set 1 | qwen3.5:2b / v3 | WMT | 2023 | NetIncome | 11,680 M | 11,292 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | WMT | 2024 | NetIncome | 15,511 M | 16,270 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | WMT | 2025 | NetIncome | 19,436 M | 20,157 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v3 | WMT | 2026 | NetIncome | 21,893 M | 22,270 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:2b / v4 | BAC | 2024 | NetIncome | 27,132 M | 25,503 M | Wrong metric (other row) | number taken from another row: Net income applicable to common shareholders / $25,503 / $24,866 / $26,015 |
| Test set 1 | qwen3.5:2b / v4 | DIS | 2021 | EPS | 1.09 | 1.11 | Wrong metric (other row) | number taken from another row: Continuing operations / $1.11 / $(1.57) / $6.26 |
| Test set 1 | qwen3.5:2b / v4 | DIS | 2021 | OperatingIncome | 7,766 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v4 | DIS | 2022 | EPS | 1.72 | 1.75 | Wrong metric (other row) | number taken from another row: Continuing operations / $1.75 / $1.11 / $(1.57) |
| Test set 1 | qwen3.5:2b / v4 | DIS | 2022 | OperatingIncome | 12,121 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v4 | DIS | 2023 | EPS | 1.29 | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v4 | DIS | 2023 | OperatingIncome | 12,863 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v4 | DIS | 2024 | OperatingIncome | 15,601 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v4 | DIS | 2025 | OperatingIncome | 17,551 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:2b / v4 | NEE | 2021 | Revenue | 18,800 M | 17,069 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $17,069 / $17,997 / $19,204 |
| Test set 1 | qwen3.5:2b / v4 | NEE | 2022 | Revenue | 23,000 M | 20,956 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $20,956 / $17,069 / $17,997 |
| Test set 1 | qwen3.5:2b / v4 | NEE | 2023 | Revenue | 24,800 M | 28,114 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $28,114 / $20,956 / $17,069 |
| Test set 1 | qwen3.5:2b / v4 | NEE | 2024 | Revenue | 23,500 M | 24,753 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $24,753 / $28,114 / $20,956 |
| Test set 1 | qwen3.5:2b / v4 | NEE | 2025 | Revenue | 25,800 M | 27,412 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $27,412 / $24,753 / $28,114 |
| Test set 1 | qwen3.5:4b / v3 | BA | 2021 | OperatingIncome | -2,902 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:4b / v3 | BA | 2023 | OperatingIncome | -773 M | 7,724 M | Wrong metric (other row) | number taken from another row: 7,724 / 3,530 / 3,049 |
| Test set 1 | qwen3.5:4b / v3 | BA | 2025 | NetIncome | 2,235 M | 1,890 M | Wrong metric (other row) | number taken from another row: Net earnings/(loss) attributable to Boeing common shareholders / $ 1,890 / ($ 11,875) / ($ |
| Test set 1 | qwen3.5:4b / v3 | DIS | 2021 | OperatingIncome | 7,766 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:4b / v3 | DIS | 2022 | OperatingIncome | 12,121 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:4b / v3 | DIS | 2023 | OperatingIncome | 12,863 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:4b / v3 | DIS | 2024 | OperatingIncome | 15,601 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:4b / v3 | DIS | 2025 | OperatingIncome | 17,551 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:4b / v3 | NEE | 2021 | Revenue | 18,800 M | 17,069 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $17,069 / $17,997 / $19,204 |
| Test set 1 | qwen3.5:4b / v3 | NEE | 2022 | Revenue | 23,000 M | 20,956 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $20,956 / $17,069 / $17,997 |
| Test set 1 | qwen3.5:4b / v3 | NEE | 2023 | Revenue | 24,800 M | 28,114 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $28,114 / $20,956 / $17,069 |
| Test set 1 | qwen3.5:4b / v3 | NEE | 2024 | Revenue | 23,500 M | 24,753 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $24,753 / $28,114 / $20,956 |
| Test set 1 | qwen3.5:4b / v3 | NEE | 2025 | Revenue | 25,800 M | 27,412 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $27,412 / $24,753 / $28,114 |
| Test set 1 | qwen3.5:4b / v3 | PFE | 2023 | NetIncome | 2,119 M | 2,158 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:4b / v3 | VZ | 2023 | NetIncome | 11,614 M | 12,095 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 1 | qwen3.5:4b / v4 | BA | 2025 | NetIncome | 2,235 M | 1,890 M | Wrong metric (other row) | number taken from another row: Net earnings/(loss) attributable to Boeing common shareholders / $ 1,890 / ($ 11,875) / ($ |
| Test set 1 | qwen3.5:4b / v4 | DIS | 2021 | OperatingIncome | 7,766 M | 2,561 M | Wrong metric (other row) | number taken from another row: Income (loss) from continuing operations before income taxes / 2,561 / (1,743) / 13,923 |
| Test set 1 | qwen3.5:4b / v4 | DIS | 2022 | OperatingIncome | 12,121 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:4b / v4 | DIS | 2023 | OperatingIncome | 12,863 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:4b / v4 | DIS | 2024 | OperatingIncome | 15,601 M | 7,569 M | Wrong metric (other row) | number taken from another row: Income from continuing operations before income taxes / 7,569 / 4,769 / 5,285 |
| Test set 1 | qwen3.5:4b / v4 | DIS | 2025 | OperatingIncome | 17,551 M | — | Value missing | model returned no value |
| Test set 1 | qwen3.5:4b / v4 | NEE | 2021 | Revenue | 18,800 M | 17,069 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $17,069 / $17,997 / $19,204 |
| Test set 1 | qwen3.5:4b / v4 | NEE | 2022 | Revenue | 23,000 M | 20,956 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $20,956 / $17,069 / $17,997 |
| Test set 1 | qwen3.5:4b / v4 | NEE | 2023 | Revenue | 24,800 M | 28,114 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $28,114 / $20,956 / $17,069 |
| Test set 1 | qwen3.5:4b / v4 | NEE | 2024 | Revenue | 23,500 M | 24,753 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $24,753 / $28,114 / $20,956 |
| Test set 1 | qwen3.5:4b / v4 | NEE | 2025 | Revenue | 25,800 M | 27,412 M | Wrong metric (other row) | number taken from another row: OPERATING REVENUES / $27,412 / $24,753 / $28,114 |
| Test set 1 | qwen3.5:4b / v4 | PFE | 2022 | EPS | 5.47 | 547.00 | Other | number does not appear in the statements |
| Test set 2 | qwen3.5:2b / v3 | AIG | 2021 | NetIncome | 9,388 M | 9,923 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | AIG | 2022 | NetIncome | 10,276 M | 11,275 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | AIG | 2023 | EPS | 4.98 | — | Value missing | model returned no value |
| Test set 2 | qwen3.5:2b / v3 | AIG | 2023 | NetIncome | 3,643 M | 3,878 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | AIG | 2024 | EPS | -2.17 | 4.07 | Wrong metric (other row) | number taken from another row: Income (loss) from continuing operations / $4.07 / $3.74 / $3.63 |
| Test set 2 | qwen3.5:2b / v3 | DUK | 2021 | NetIncome | 3,908 M | 3,579 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | DUK | 2021 | Revenue | 24,703 M | 25,097 M | Wrong metric (other row) | number taken from another row: Total operating revenues / 25,097 / 23,868 / 25,079 |
| Test set 2 | qwen3.5:2b / v3 | DUK | 2022 | NetIncome | 2,550 M | 2,455 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | DUK | 2023 | NetIncome | 2,841 M | 2,874 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | DUK | 2023 | Revenue | 28,674 M | 29,060 M | Other | earlier column of the correct row (e.g. a note number): Total operating revenues / 29,060 / 28,768 / 24,621 |
| Test set 2 | qwen3.5:2b / v3 | DUK | 2024 | NetIncome | 4,524 M | 4,614 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | DUK | 2024 | Revenue | 30,050 M | 30,357 M | Wrong metric (other row) | number taken from another row: Total operating revenues / 30,357 / 29,060 / 28,768 |
| Test set 2 | qwen3.5:2b / v3 | DUK | 2025 | NetIncome | 4,968 M | 5,071 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | DUK | 2025 | Revenue | 31,741 M | 32,237 M | Wrong metric (other row) | number taken from another row: Total operating revenues / 32,237 / 30,357 / 29,060 |
| Test set 2 | qwen3.5:2b / v3 | GS | 2022 | NetIncome | 11,261 M | 10,764 M | Wrong metric (other row) | number taken from another row: Net earnings applicable to common shareholders / $10,764 / $21,151 / $8,915 |
| Test set 2 | qwen3.5:2b / v3 | GS | 2023 | NetIncome | 8,516 M | 7,907 M | Wrong metric (other row) | number taken from another row: Net earnings applicable to common shareholders / $7,907 / $10,764 / $21,151 |
| Test set 2 | qwen3.5:2b / v3 | GS | 2024 | NetIncome | 14,276 M | 13,525 M | Wrong metric (other row) | number taken from another row: Pre-tax earnings / 18,397 / 10,739 / 13,486 |
| Test set 2 | qwen3.5:2b / v3 | GS | 2025 | NetIncome | 17,176 M | 16,300 M | Wrong metric (other row) | number taken from another row: Net earnings applicable to common shareholders / $16,300 / $13,525 / $7,907 |
| Test set 2 | qwen3.5:2b / v3 | INTC | 2023 | NetIncome | 1,689 M | 1,675 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | INTC | 2024 | NetIncome | -18,756 M | -19,233 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | INTC | 2025 | EPS | -0.06 | — | Value missing | model returned no value |
| Test set 2 | qwen3.5:2b / v3 | INTC | 2025 | NetIncome | -267 M | 26 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | INTC | 2025 | OperatingIncome | -2,214 M | — | Value missing | model returned no value |
| Test set 2 | qwen3.5:2b / v3 | MRNA | 2025 | OperatingIncome | -3,074 M | — | Value missing | model returned no value |
| Test set 2 | qwen3.5:2b / v3 | T | 2021 | NetIncome | 20,081 M | 0 M | Wrong metric (other row) | number taken from another row: Net Income (Loss) / 21,479 / (3,821) / 14,975 |
| Test set 2 | qwen3.5:2b / v3 | T | 2021 | OperatingIncome | 23,347 M | 23 M | Unit error (thousands/millions) | reported unit 'thousands', correct would be 'millions' |
| Test set 2 | qwen3.5:2b / v3 | T | 2021 | Revenue | 168,864 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| Test set 2 | qwen3.5:2b / v3 | T | 2022 | NetIncome | -8,524 M | -7,055 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | T | 2023 | NetIncome | 14,400 M | 15,623 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | T | 2024 | NetIncome | 10,948 M | 12,253 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | T | 2025 | NetIncome | 21,953 M | 23,386 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | UBER | 2021 | OperatingIncome | -3,834 M | — | Value missing | model returned no value |
| Test set 2 | qwen3.5:2b / v3 | UBER | 2022 | NetIncome | -9,141 M | 3 M | Wrong metric (other row) | number taken from another row: Less: net income (loss) attributable to non-controlling interests, net of tax / (20) / (74 |
| Test set 2 | qwen3.5:2b / v3 | UBER | 2022 | OperatingIncome | -1,832 M | — | Value missing | model returned no value |
| Test set 2 | qwen3.5:2b / v3 | WBD | 2021 | NetIncome | 1,006 M | 1,197 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | WBD | 2022 | NetIncome | -7,371 M | -7,297 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | WBD | 2023 | NetIncome | -3,126 M | -3,079 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | WBD | 2024 | EPS | -4.62 | — | Value missing | model returned no value |
| Test set 2 | qwen3.5:2b / v3 | WBD | 2024 | NetIncome | -11,311 M | -11,482 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v3 | WBD | 2024 | OperatingIncome | -10,032 M | — | Value missing | model returned no value |
| Test set 2 | qwen3.5:2b / v3 | WBD | 2025 | NetIncome | 727 M | 749 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v4 | AIG | 2022 | EPS | 13.01 | — | Value missing | model returned no value |
| Test set 2 | qwen3.5:2b / v4 | AIG | 2024 | EPS | -2.17 | 4.07 | Wrong metric (other row) | number taken from another row: Income (loss) from continuing operations / $4.07 / $3.74 / $3.63 |
| Test set 2 | qwen3.5:2b / v4 | DUK | 2021 | Revenue | 24,703 M | 25,097 M | Wrong metric (other row) | number taken from another row: Total operating revenues / 25,097 / 23,868 / 25,079 |
| Test set 2 | qwen3.5:2b / v4 | DUK | 2023 | Revenue | 28,674 M | 29,060 M | Other | earlier column of the correct row (e.g. a note number): Total operating revenues / 29,060 / 28,768 / 24,621 |
| Test set 2 | qwen3.5:2b / v4 | DUK | 2024 | Revenue | 30,050 M | 30,357 M | Wrong metric (other row) | number taken from another row: Total operating revenues / 30,357 / 29,060 / 28,768 |
| Test set 2 | qwen3.5:2b / v4 | DUK | 2025 | Revenue | 31,741 M | 32,237 M | Wrong metric (other row) | number taken from another row: Total operating revenues / 32,237 / 30,357 / 29,060 |
| Test set 2 | qwen3.5:2b / v4 | GS | 2022 | NetIncome | 11,261 M | 10,764 M | Wrong metric (other row) | number taken from another row: Net earnings applicable to common shareholders / $10,764 / $21,151 / $8,915 |
| Test set 2 | qwen3.5:2b / v4 | GS | 2025 | NetIncome | 17,176 M | 16,300 M | Wrong metric (other row) | number taken from another row: Net earnings applicable to common shareholders / $16,300 / $13,525 / $7,907 |
| Test set 2 | qwen3.5:2b / v4 | INTC | 2025 | NetIncome | -267 M | 26 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v4 | T | 2021 | OperatingIncome | 23,347 M | 23 M | Unit error (thousands/millions) | reported unit 'thousands', correct would be 'millions' |
| Test set 2 | qwen3.5:2b / v4 | T | 2021 | Revenue | 168,864 M | 0 M | Unit error (thousands/millions) | reported unit 'units', correct would be 'millions' |
| Test set 2 | qwen3.5:2b / v4 | WBD | 2021 | NetIncome | 1,006 M | 1,197 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v4 | WBD | 2022 | NetIncome | -7,371 M | -7,297 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v4 | WBD | 2023 | NetIncome | -3,126 M | -3,079 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v4 | WBD | 2024 | NetIncome | -11,311 M | -11,482 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:2b / v4 | WBD | 2025 | NetIncome | 727 M | 749 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:4b / v3 | AIG | 2021 | NetIncome | 9,388 M | 9,923 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:4b / v3 | AIG | 2022 | NetIncome | 10,276 M | 11,275 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:4b / v3 | AIG | 2023 | NetIncome | 3,643 M | 3,878 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:4b / v3 | DUK | 2021 | Revenue | 24,703 M | 25,097 M | Wrong metric (other row) | number taken from another row: Total operating revenues / 25,097 / 23,868 / 25,079 |
| Test set 2 | qwen3.5:4b / v3 | DUK | 2023 | Revenue | 28,674 M | 29,060 M | Other | earlier column of the correct row (e.g. a note number): Total operating revenues / 29,060 / 28,768 / 24,621 |
| Test set 2 | qwen3.5:4b / v3 | DUK | 2024 | Revenue | 30,050 M | 30,357 M | Wrong metric (other row) | number taken from another row: Total operating revenues / 30,357 / 29,060 / 28,768 |
| Test set 2 | qwen3.5:4b / v3 | DUK | 2025 | Revenue | 31,741 M | 32,237 M | Wrong metric (other row) | number taken from another row: Total operating revenues / 32,237 / 30,357 / 29,060 |
| Test set 2 | qwen3.5:4b / v3 | GS | 2022 | NetIncome | 11,261 M | 10,764 M | Wrong metric (other row) | number taken from another row: Net earnings applicable to common shareholders / $10,764 / $21,151 / $8,915 |
| Test set 2 | qwen3.5:4b / v3 | GS | 2024 | NetIncome | 14,276 M | 13,525 M | Wrong metric (other row) | number taken from another row: Pre-tax earnings / 18,397 / 10,739 / 13,486 |
| Test set 2 | qwen3.5:4b / v3 | INTC | 2023 | NetIncome | 1,689 M | 1,675 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:4b / v3 | T | 2021 | NetIncome | 20,081 M | 19,874 M | Wrong metric (other row) | number taken from another row: Net Income (Loss) Attributable to Common Stock / $19,874 / $(5,369) / $13,900 |
| Test set 2 | qwen3.5:4b / v3 | WBD | 2022 | NetIncome | -7,371 M | -7,297 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:4b / v3 | WBD | 2023 | NetIncome | -3,126 M | -3,079 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:4b / v3 | WBD | 2024 | NetIncome | -11,311 M | -11,482 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:4b / v3 | WBD | 2024 | OperatingIncome | -10,032 M | — | Value missing | model returned no value |
| Test set 2 | qwen3.5:4b / v3 | WBD | 2025 | NetIncome | 727 M | 749 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:4b / v4 | DUK | 2021 | Revenue | 24,703 M | 25,097 M | Wrong metric (other row) | number taken from another row: Total operating revenues / 25,097 / 23,868 / 25,079 |
| Test set 2 | qwen3.5:4b / v4 | DUK | 2023 | Revenue | 28,674 M | 29,060 M | Other | earlier column of the correct row (e.g. a note number): Total operating revenues / 29,060 / 28,768 / 24,621 |
| Test set 2 | qwen3.5:4b / v4 | DUK | 2024 | Revenue | 30,050 M | 30,357 M | Wrong metric (other row) | number taken from another row: Total operating revenues / 30,357 / 29,060 / 28,768 |
| Test set 2 | qwen3.5:4b / v4 | DUK | 2025 | Revenue | 31,741 M | 32,237 M | Wrong metric (other row) | number taken from another row: Total operating revenues / 32,237 / 30,357 / 29,060 |
| Test set 2 | qwen3.5:4b / v4 | T | 2021 | NetIncome | 20,081 M | 19,874 M | Wrong metric (other row) | number taken from another row: Net Income (Loss) Attributable to Common Stock / $19,874 / $(5,369) / $13,900 |
| Test set 2 | qwen3.5:4b / v4 | WBD | 2022 | NetIncome | -7,371 M | -7,297 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:4b / v4 | WBD | 2023 | NetIncome | -3,126 M | -3,079 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:4b / v4 | WBD | 2024 | NetIncome | -11,311 M | -11,482 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
| Test set 2 | qwen3.5:4b / v4 | WBD | 2025 | NetIncome | 727 M | 749 M | Wrong metric (other row) | matches related XBRL value ProfitLoss |
