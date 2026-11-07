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

## What I changed and why

- **The measure: nothing changed.** It passed every reconciliation row and every edge case. Pinning one `LastSnapshot` for both the ranking and the denominator is what keeps it correct on the advisor slices.
- **The test query:** I renamed `LastDate` to `LastSnap`. Claude's first query was syntactically invalid, which is a reminder to **run** AI-written DAX instead of trusting that it reads well.

## Judgement on Claude's output

The measure and the filter-context explanation were correct and specific to this model. They used the real column names from the metadata, reused `[Ending AUM]` instead of redefining it, and anticipated the stale-balance trap that Part C (a) exposes. The weak spot was the test query: it used a reserved name, which shows that a confident explanation is not the same as working code. The grain and "balance" facts added to the prompt made the difference. Without "there is no row after a client leaves", the per-client `[Ending AUM]` version looks equally valid, and it passes all of the assignment's required slices.
