# HW3 Part 5: Validation

## 5A — Known-Answer Check: Earnings

**Company / quarter checked:** Apple Inc. (AAPL), fiscal 2026 third quarter ended June 27, 2026 (8-K filed 2026-07-30).

**Official source:** Apple Newsroom press release "Apple reports third quarter results," July 30, 2026 (https://www.apple.com/newsroom/2026/07/apple-reports-third-quarter-results/): *"The Company posted quarterly revenue of $109.4 billion, up 16 percent year over year"* and *"Diluted earnings per share was $2.02."* Net income of $29.8 billion is confirmed by MacRumors' earnings coverage (https://www.macrumors.com/2026/07/30/apple-3q-2026-earnings/).

| Check | Official Source | Your CSV | Match? |
|---|---|---|---|
| Apple Q3 FY2026 Revenue | $109.4 billion | 109400 ($ millions) | Yes |
| Apple Q3 FY2026 EPS Diluted | $2.02 | 2.02 | Yes |
| Apple Q3 FY2026 Net Income (extra check) | $29.8 billion | 29789 ($ millions) | Yes |

**Notes:** All values match. Revenue is stored as 109400 because the script reads the rounded headline sentence ("$109.4 billion") first. Net income does not appear in Apple's prose, so the script fell back to the income-statement table, which gives the exact figure ($29,789 million, which rounds to the official $29.8 billion). No value was `NOT_FOUND`, so no regex fix was needed for this check.

## 5B — Known-Answer Check: Executive Events

**Event checked:** Walmart Inc., filing date 2025-11-14. CSV row: `departure | C. Douglas McMillon | President and Chief Executive Officer | effective 2026-01-31`.

**News source:** CBS News, "Walmart says longtime CEO Doug McMillon will retire in January," November 14, 2025 (https://www.cbsnews.com/news/walmart-ceo-doug-mcmillon-retiring-2026-john-furner/): *"McMillon, 59, will step down as CEO on Jan. 31 but remain on the retailer's board of directors until its annual shareholders' meeting."* and *"John Furner ... will take over as chief executive on Feb. 1."*

| Check | News Source Confirms? | Notes |
|---|---|---|
| Person name and title | Yes | CBS names Doug McMillon as Walmart's CEO. The 8-K uses his legal name "C. Douglas McMillon" and the title "president and chief executive officer." |
| Event type (departure/appointment) | Yes | Departure (retirement). The same filing also produced a separate appointment row for John R. Furner, effective 2026-02-01, which CBS also confirms. |
| Effective date | Yes | CBS: "step down as CEO on Jan. 31." CSV: 2026-01-31 (the 8-K says "effective on the close of business on January 31, 2026"). |

## 5C — Cross-Validation: Earnings via Yahoo Finance

Same company and quarter as 5A (Apple Q3 FY2026). Script: `hw03/hw03_yfinance_check.py`, generated from the prompt *"Write Python using yfinance to get the most recent quarterly revenue and net income for AAPL."*

| Metric | From 8-K text extraction | From yfinance | Match? |
|---|---|---|---|
| Revenue | $109,400M | $109,417M | Yes (within rounding, $17M / 0.02% difference) |
| Net Income | $29,789M | $29,789M | Yes (exact) |

yfinance output (run 2026-09-30): most recent quarter ended 2026-06-30. Revenue $109,417M, net income $29,789M, diluted EPS $2.02.

**Explanation of the small revenue difference:** this is a rounding difference, not an extraction error or a period mismatch. The earnings pipeline reads revenue from the press-release headline sentence ("quarterly revenue of $109.4 billion"), which Apple rounds to the nearest $0.1 billion, so it is stored as 109,400. yfinance reports the exact income-statement figure, $109,417 million, which rounds to the same $109.4 billion. Net income matches exactly because Apple's release gives no net income sentence, so the pipeline took the exact table value ($29,789M), the same number yfinance reports. The quarter dates also line up: yfinance labels the quarter by calendar month-end (2026-06-30), while Apple's fiscal quarter officially ended Saturday, June 27, 2026. Both refer to Apple's fiscal 2026 third quarter.

## 5D — Pipeline Integrity Checks

| Check | Expected | Actual | Pass/Fail |
|---|---|---|---|
| `earnings_history.csv` row count | Up to 20 (5 companies × 4 quarters) | 20 | Pass |
| `executive_events.csv` row count | At least 0 (document actual) | 29 (from 16 Item 5.02 filings; 3 compensation-only filings skipped) | Pass |
| `corporate_events_timeline.csv` created | Yes | Yes (29 rows, one per executive event) | Pass |
| Rows with all three fields `"NOT_FOUND"` | 0 (investigate if > 0) | 0 (no `NOT_FOUND` values in any earnings field) | Pass |
