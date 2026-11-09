# Part D — Verification of Claude's `Top 10 Client Share`

**Did the measure run as written?** Yes. It was added to `_Measures` unchanged, and Power BI reported `State = Ready` (see the Measures table in `model_metadata.md`). Claude's **test query did not run at first**: it failed with `The syntax for 'LastDate' is incorrect`, because `LastDate` is the DAX function `LASTDATE` (names are case-insensitive). After renaming the variable to `LastSnap`, the query returned `Last snapshot` 2024-12-01, top-10 AUM **$784,005,019.49**, Ending AUM **$12,729,572,078.86**, and **0.0615892674657931** in both the hand-built column and the measure. The two independent routes (`MAX(snapshot_date)` and `LASTNONBLANK`) agree to the last digit.

**Reconciliation rows that prove it** (`reports/measure_reconciliation.csv`, all `match = True`):

| Row | Power BI | pandas |
|---|---:|---:|
| `Top 10 Client Share`, `All` | 0.061589267 | 0.061589267 |
| `Top 10 Client Share`, `2024 \| HNW` | 0.031396747 | 0.031396747 |
| `Top 10 Client Share`, `2024 \| Retail` | 0.018348218 | 0.018348218 |
| `Top 10 Client Share`, `2024 \| UHNW` | 0.081264268 | 0.081264268 |
| `Top 10 Client Share`, `Year 2020` … `Year 2024` | 5 rows | all match |

pandas computes the share independently: take the slice's latest `snapshot_date`, sum `aum` by client on that date, then `nlargest(10)` ÷ the total.

## Edge cases checked

1. **Grand total (no filters):** 6.16%, and the test query reproduces it by hand (above).
2. **`dim_date[year] = 2022`:** 5.53% (row `Year 2022` matches pandas). By tier in 2022, the shares are HNW 2.78%, Retail 1.57% and UHNW 7.37%, with 737 / 1,510 / 253 clients. Even in the year when departures started, no tier exceeds 100% and each tier ranks only its own clients.
3. **2024 tier table:** the three tier values are each far below 100% and below the firm figure for HNW and Retail. That is what ranking *within* the filter should give (`VALUES`, not `ALL`). The UHNW share (8.13%) is above the firm's 6.16% because the same top ten clients are divided by the smaller UHNW book.
4. **A single client** (`dim_client[client_id] = 1`): exactly 100% with 1 Ending Client. This checks `TOPN` when the slice has fewer than 10 clients.
5. **Ties:** the 10th and 11th balances at 2024-12-01 differ ($74,424,366.68 vs $72,106,567.72), so `TOPN` returns exactly 10 rows. All ten are UHNW clients, which is why UHNW's own share is the highest of the three tiers.
6. **Advisor slices, all years:** this is where the simpler draft breaks (next section).

## Claim confirmed: the shorter `TOPN ( …, [Ending AUM] )` version overstates the share

Claude claimed the shorter pattern from the assignment hint would rank departed clients on a stale balance, and would agree with the final measure unless a departed client was big enough to make the top 10. I **confirmed** this in Power BI, with a query-scoped measure `Top 10 (simple draft)`, and again in pandas (`reports/part_c_evidence.csv`, section D):

| Slice | Final measure | Simple draft | Departed clients in the draft's top 10 |
|---|---:|---:|---:|
| Grand total, every year, every 2024 tier | identical | identical | 0 |
| Advisor 1, all years | 76.56% | **85.47%** | 1 |
| Advisor 5, all years | 81.08% | **88.09%** | 1 |
| Advisor 14, all years | 67.16% | **76.09%** | 1 |
| Advisor 23, all years | 78.01% | **86.29%** | 1 |

Power BI found **8 of 25 advisors** where the two versions differ. In each of the four checked in pandas, exactly one departed client's last 2022–2023 balance entered the draft's top 10. **All the slices the assignment reconciles agree**, so the reconciliation alone would not have caught this. Only an edge case with departed clients exposes it.

## Claude Desktop session (Session A in `dax_session.md`)

I sent the same prompt to Claude Desktop. It returned a measure written differently: `MAX(snapshot_date)` pinned with `dim_date[date] = …` instead of `LASTNONBLANK` passed to `CALCULATE`, and a second sort key on `client_id`. I tested it as a query-scoped measure against `hw06.pbix`, next to the model's measure and the naive version:

| Slices compared | Rows | Desktop ≠ model measure | Naive ≠ model measure |
|---|---:|---:|---:|
| Grand total | 1 | 0 | 0 |
| By year | 5 | 0 | 0 |
| By month | 60 | 0 | 0 |
| By tier, 2024 | 3 | 0 | 0 |
| By tier × year | 15 | 0 | 0 |
| By advisor | 25 | 0 | **8** |
| By advisor × year | 125 | 0 | **7** |

**Desktop's measure is correct.** It equals the model's measure on all 234 slices (the largest difference is 3×10⁻¹⁶, rounding noise), including the advisor slices where the naive version fails.

**Claims refuted:**
1. *"Grand total … the share is overstated"* (query A comment: *"expect naive > correct here"*) and *"the naive share should differ … in 2022, 2023"*. **Refuted.** Naive = correct at the grand total and in every year, to the last digit. The mechanism Desktop describes is real, but no departed client's stale balance is large enough to reach the firm's top 10. The divergence appears only in small slices (single advisors), which Desktop never mentioned. Its claim that the naive share "can go above 100%" never happened on any of the 234 slices.
2. Query D's `CALCULATETABLE ( VALUES ( dim_client[client_id] ), fact_portfolio_snapshot[snapshot_date] = d )` was meant to list the clients present on the last date. **Refuted:** it returns all **2,500** clients, because a filter on the fact table does not reach `dim_client` through a single-direction relationship. Ironically, Desktop's own table states this rule for `VALUES` in the measure. The share is still right, because the 175 departed clients are blank on that date and add nothing.

**Claims confirmed:** the date-pinning logic, that the 2024 tier view hides the bug, the ≤ 100% guarantee (query C: all "ok"), and that A equals D.

**Tie-break:** Desktop's `dim_client[client_id], ASC` makes `TOPN` return exactly 10 rows. I kept the model's measure unchanged. With and without the tie-break, the two measures agree on all 234 slices above, so no tie affects any result in this data (see also edge case 5). Desktop's version would be the safer choice in a model where ties are possible.

## What I changed and why

- **The measure: nothing changed.** It passed every reconciliation row and every edge case. Pinning one `LastSnapshot` for both the ranking and the denominator is what keeps it correct on the advisor slices.
- **The test query:** I renamed `LastDate` to `LastSnap`. Claude's first query was syntactically invalid, which is a reminder to **run** AI-written DAX instead of trusting that it reads well.

## Judgement on Claude's output

The measure and the filter-context explanation were correct and specific to this model. They used the real column names from the metadata, reused `[Ending AUM]` instead of redefining it, and anticipated the stale-balance trap that Part C (a) exposes. The weak spot was the test query: it used a reserved name, which shows that a confident explanation is not the same as working code. Claude Desktop, given the same prompt, reached an equally correct measure by a different route, and added a sensible tie-break. Its weak spot was the predictions: it said where the naive version would fail (grand total, 2022–2023) without checking, and it was wrong both times. Its test query D also contradicted a rule it had just explained. Both sessions show the same lesson: the logic was sound, but every claim about the data had to be run to be trusted. The grain and "balance" facts added to the prompt made the difference. Without "there is no row after a client leaves", the per-client `[Ending AUM]` version looks equally valid, and it passes all of the assignment's required slices.
