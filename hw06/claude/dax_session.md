# Part D — Claude-assisted measure: `Top 10 Client Share` (measure 11)

**Workflow:** Draft → Test → Debug → Review (Week 10).

**Tool note:** the same prompt (Prompt 1 below) was sent twice:
- **Session A, Claude Desktop** (the tool the assignment names). Its full response is in [Session A](#session-a--claude-desktop) below.
- **Session B, Claude in Claude Code** (Claude Opus 5.5). This one ran first, and its measure is the one in `hw06.pbix`. Its draft, debug and test result follow Session A.

Both measures were tested against `hw06.pbix`, and they agree on every slice (see `verification.md`).

---

## Prompt 1 (Draft), used in both sessions

> I need one DAX measure for a Power BI model. Below is the exported model metadata (INFO.VIEW.COLUMNS / RELATIONSHIPS / MEASURES, trimmed to the tables involved), then what the metadata can't tell you.
>
> **Columns** (Table | Column | DataType)
> ```
> fact_portfolio_snapshot | snapshot_id | Integer        dim_client | client_id | Integer
> fact_portfolio_snapshot | client_id | Integer          dim_client | client_tier | Text
> fact_portfolio_snapshot | advisor_id | Integer         dim_client | advisor_id | Integer
> fact_portfolio_snapshot | benchmark_id | Integer       dim_client | is_active | True/False
> fact_portfolio_snapshot | snapshot_date | Date         dim_date | date | Date
> fact_portfolio_snapshot | year | Integer               dim_date | year | Integer
> fact_portfolio_snapshot | month | Integer              dim_date | month | Integer
> fact_portfolio_snapshot | aum | Number                 dim_date | quarter | Integer
> fact_portfolio_snapshot | return_ytd | Number          dim_date | is_month_end | Integer
> fact_portfolio_snapshot | benchmark_return_ytd | Number
> fact_portfolio_snapshot | active_alpha_ytd | Number
> fact_portfolio_snapshot | cash_pct | Number
> fact_portfolio_snapshot | account_type | Text
> fact_portfolio_snapshot | is_return_suspect | Integer
> ```
> **Relationships** (all many-to-one, single direction, active):
> `fact_portfolio_snapshot[client_id] → dim_client[client_id]`, `fact_portfolio_snapshot[snapshot_date] → dim_date[date]`, `fact_portfolio_snapshot[advisor_id] → dim_advisor[advisor_id]`, `fact_portfolio_snapshot[benchmark_id] → dim_benchmark[benchmark_id]`; `fact_fees` and `fact_transactions` also link to `dim_client` and `dim_date[date]`. `dim_date` is marked as the date table on `date`.
>
> **Existing measures** in table `_Measures` (reuse them, don't redefine):
> ```
> Ending AUM = CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ),
>                LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) ) )
> Ending Clients, Avg AUM per Client, Ending AUM LY, AUM YoY %, Ending AUM PM, AUM MoM %,
> Avg Monthly AUM, Fee Yield (bps), Organic Growth Rate, AUM-Weighted Alpha, Alpha Signal,
> Total Fees, Net Flows, Effective Fee Rate (bps), AUM (naive SUM)
> ```
>
> **What the metadata doesn't say:**
> - Grain of `fact_portfolio_snapshot`: **one row per client per month**, dated the **1st** of the month (2020-01-01 … 2024-12-01). There is no row for a month after a client leaves.
> - `aum` is a **balance** (semi-additive): it may be summed across clients at one date, never across months. `active_alpha_ytd` is year-to-date (not used here).
> - 175 of 2,500 clients are inactive; their last snapshot is between 2022-12 and 2023-11.
>
> **Business definition:** `Top 10 Client Share` = share of **Ending AUM** held by the **10 largest clients within the current filter**. It must work at the grand total, by `dim_date[year]`, and in a table by `dim_client[client_tier]` filtered to 2024 (each tier ranks only its own clients, so the result can never exceed 100%).
>
> Please give me: (1) the measure, (2) an explanation of its filter context — what is filtered at each step, (3) a DAX query I can run in DAX query view to test it.

---

## Session A — Claude Desktop

### Response (full, as returned; its filter-context table is laid out as a Markdown table)

**1. The measure**

```DAX
Top 10 Client Share =
VAR LastSnapshotDate =
    MAX ( fact_portfolio_snapshot[snapshot_date] )   -- same date Ending AUM picks
VAR TotalAUM =
    [Ending AUM]
VAR Top10AUM =
    CALCULATE (
        SUMX (
            TOPN (
                10,
                VALUES ( dim_client[client_id] ),
                [Ending AUM], DESC,
                dim_client[client_id], ASC          -- tie-break → exactly 10 rows
            ),
            [Ending AUM]
        ),
        dim_date[date] = LastSnapshotDate           -- pin every client to ONE date
    )
RETURN
    DIVIDE ( Top10AUM, TotalAUM )
```
Format it as a percentage and put it in `_Measures`.

**Why you can't just write `TOPN(10, VALUES(client_id), [Ending AUM])`**

`Ending AUM` uses `LASTNONBLANK` to find the last date for whatever is in context. Inside `TOPN`, each client is in context on its own, so each client gets its own last date. For an inactive client, that's their final snapshot, somewhere from 2022‑12 to 2023‑11.

- **Grand total:** the denominator is AUM at 2024‑12‑01, but the naive numerator can rank and add in balances of clients who left in 2023. That's a stale balance at a different date, which you're not allowed to add for a semi-additive measure. The share is overstated and can go above 100%.
- **Year 2023:** the denominator is 2023‑12‑01, but a client who left in 2023‑06 still counts with their June balance.
- **Tier × 2024:** this one looks fine, because no inactive client has a 2024 row. So the bug hides in exactly the view people usually check.

Pinning `dim_date[date]` to the context's single last snapshot date fixes it. Every client is then measured on the same date the denominator uses. Clients with no row on that date return BLANK, sort to the bottom, and add nothing.

**2. Filter context, step by step**

| Step | What's filtered |
|---|---|
| Outer context | Whatever the visual sets: nothing (grand total), `dim_date[year]`, or `dim_client[client_tier]` + year 2024. These filters reach the fact table through the many-to-one relationships. |
| `LastSnapshotDate` | `MAX` over the fact rows visible in the outer context. It returns the same date as `LASTNONBLANK(..., COUNTROWS(fact))` inside `Ending AUM`: 2024‑12‑01 at the grand total, YYYY‑12‑01 per year (2024‑12‑01 for each tier in 2024). If you filter by client or advisor, it respects that too. |
| `TotalAUM` | `[Ending AUM]` in the outer context: the sum of `aum` across all visible clients on that date. This is the denominator. |
| `CALCULATE(..., dim_date[date] = LastSnapshotDate)` | Replaces the date filter with that one day. `dim_date` is marked as the date table, so filtering its date column also adds `ALL(dim_date)`, which removes the year filter. That's harmless here because the pinned date is inside the year anyway. The tier, advisor and any fact-column filters stay in place. |
| `VALUES(dim_client[client_id])` | The clients visible after the outer `dim_client` filters, such as one tier. The relationship is single-direction, so this list isn't reduced by the fact table. It includes inactive clients, but they're BLANK on the pinned date. This is what makes each tier rank only its own clients. |
| `TOPN` ordering: `[Ending AUM]` per client | Context transition: the client row becomes a filter, combined with the pinned date. `LASTNONBLANK` then has only one date to choose from, so the result is that client's AUM on that date or BLANK. |
| `SUMX(..., [Ending AUM])` | Same evaluation for each of the 10 winners, then summed. This is the numerator. |
| `DIVIDE` | Numerator ÷ denominator. Both are the same set of clients on the same date, so the result is ≤ 100%. A group with fewer than 10 clients returns exactly 100%. |

Two notes:
- "Grand total" means the latest month (Dec 2024), not all of history. That's correct for a balance, but say so in the visual's tooltip or title.
- Ties: `TOPN` returns every row tied at the 10th place, so it can return 11 or more. The secondary sort on `client_id` makes it exactly 10 and keeps the result the same on every refresh.

**3. Test query (DAX query view)**

Paste the whole thing and run it. Each `EVALUATE` returns its own result grid.

```DAX
DEFINE
    -- The naive version, defined locally to show the difference
    MEASURE _Measures[Top 10 Share (naive)] =
        DIVIDE (
            SUMX ( TOPN ( 10, VALUES ( dim_client[client_id] ), [Ending AUM] ), [Ending AUM] ),
            [Ending AUM]
        )
    MEASURE _Measures[Snapshot Date Used] =
        MAX ( fact_portfolio_snapshot[snapshot_date] )
    MEASURE _Measures[Clients on Date] =
        CALCULATE (
            DISTINCTCOUNT ( fact_portfolio_snapshot[client_id] ),
            dim_date[date] = MAX ( fact_portfolio_snapshot[snapshot_date] )
        )

-- A. Grand total
EVALUATE
ROW (
    "Snapshot Date", [Snapshot Date Used],
    "Ending AUM",    [Ending AUM],
    "Top 10 Share",  [Top 10 Client Share],
    "Naive Share",   [Top 10 Share (naive)]       -- expect naive > correct here
)

-- B. By year
EVALUATE
SUMMARIZECOLUMNS (
    dim_date[year],
    "Snapshot Date", [Snapshot Date Used],
    "Ending AUM",    [Ending AUM],
    "Top 10 Share",  [Top 10 Client Share],
    "Naive Share",   [Top 10 Share (naive)]       -- should diverge in 2022/2023 only
)
ORDER BY dim_date[year]

-- C. By tier, 2024 (must be <= 100% on every row)
EVALUATE
SUMMARIZECOLUMNS (
    dim_client[client_tier],
    TREATAS ( { 2024 }, dim_date[year] ),
    "Clients on Date", [Clients on Date],
    "Ending AUM",      [Ending AUM],
    "Top 10 Share",    [Top 10 Client Share],
    "Over 100%?",      IF ( [Top 10 Client Share] > 1, "FAIL", "ok" )
)
ORDER BY dim_client[client_tier]

-- D. Independent check of the grand total: list the actual top 10 on the last date
EVALUATE
VAR d = CALCULATE ( MAX ( fact_portfolio_snapshot[snapshot_date] ), REMOVEFILTERS () )
VAR ClientAUM =
    ADDCOLUMNS (
        CALCULATETABLE ( VALUES ( dim_client[client_id] ), fact_portfolio_snapshot[snapshot_date] = d ),
        "AUM", CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), fact_portfolio_snapshot[snapshot_date] = d )
    )
VAR Top10 = TOPN ( 10, ClientAUM, [AUM], DESC, dim_client[client_id], ASC )
RETURN
    ROW (
        "Date",           d,
        "Top 10 AUM",     SUMX ( Top10, [AUM] ),
        "Total AUM",      SUMX ( ClientAUM, [AUM] ),
        "Manual Share",   DIVIDE ( SUMX ( Top10, [AUM] ), SUMX ( ClientAUM, [AUM] ) )  -- must equal A
    )
```

What to look for in the results:
- A and D should show the same share, with a snapshot date of 2024‑12‑01.
- In B, each year's snapshot date should be YYYY‑12‑01. The naive share should differ from the correct one only in years where clients left (2022, 2023). 2024 matches because nobody left that year.
- In C, every row should say ok, and a tier with 10 or fewer clients on the date should show exactly 100%.

### Result of Session A's test queries (run against `hw06.pbix`)

Desktop's measure was added as a query-scoped measure (`DEFINE MEASURE`), so the file was not changed, and its four queries were run with it. They ran without errors.

| Query | Result |
|---|---|
| A. Grand total | 2024-12-01 · Ending AUM $12,729,572,078.86 · Top 10 Share **0.0615892674657931** · Naive Share **0.0615892674657931** (identical, not "naive > correct") |
| B. By year | Snapshot dates 2020-12-01 … 2024-12-01 as predicted. Top 10 Share = Naive Share in **every** year: 7.04%, 6.38%, 5.53%, 6.04%, 6.16% (no divergence in 2022 or 2023) |
| C. By tier, 2024 | HNW 687 clients, 3.14% · Retail 1,394, 1.83% · UHNW 244, 8.13%. All "ok" |
| D. Independent check | 2024-12-01 · Top 10 AUM $784,005,019.49 · Total $12,729,572,078.86 · Manual Share 0.0615892674657928 (= A to 3×10⁻¹⁶). ClientAUM has **2,500** rows, not the 2,325 present on that date |

How these results bear on Desktop's claims is in `verification.md`.

---

## Session B — Claude in Claude Code

## Response 1

**(1) Measure**

```DAX
Top 10 Client Share =
VAR LastSnapshot =
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
VAR ClientBalances =
    ADDCOLUMNS (
        VALUES ( dim_client[client_id] ),
        "@aum", CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), LastSnapshot )
    )
VAR Top10 = TOPN ( 10, ClientBalances, [@aum], DESC )
RETURN
    DIVIDE ( SUMX ( Top10, [@aum] ), [Ending AUM] )
```
Format: `0.00%`, display folder *4 Performance*.

**(2) Filter context, step by step**

1. **`LastSnapshot`** is evaluated once, in the visual's filter context (for example `year = 2024` and `client_tier = "HNW"`). `LASTNONBLANK` walks the dates visible in `dim_date` and keeps the latest one where `fact_portfolio_snapshot` has rows **for the clients in the current filter**, giving 2024-12-01 for HNW in 2024. It returns a one-row table of dates, which can be used directly as a `CALCULATE` filter.
2. **`VALUES ( dim_client[client_id] )`** lists the clients **visible in the current filter**. A `client_tier` filter reaches `dim_client` directly, so the HNW row ranks only HNW clients. The year filter sits on `dim_date`, which doesn't filter `dim_client`, so the client list still contains clients who have left. That's why step 3 pins the date.
3. **`ADDCOLUMNS … CALCULATE ( SUM ( aum ), LastSnapshot )`**: for each client row, `CALCULATE` does a context transition (that `client_id` becomes a filter) and applies `LastSnapshot`. That gives **each client's balance on the slice's last date**. A client with no row on that date, such as one who left in 2023, gets blank and can't enter the top 10.
4. **`TOPN ( 10, …, [@aum], DESC )`** keeps the 10 largest balances. If two clients tie at the 10th place, `TOPN` returns both. With balances in cents a tie is very unlikely, but worth knowing.
5. **`DIVIDE ( SUMX ( Top10, [@aum] ), [Ending AUM] )`**: the numerator adds the ten balances. The denominator is `[Ending AUM]` in the **original** filter context, which is the same last date and the same client filter, so numerator and denominator describe the same date and the same population. `DIVIDE` returns blank for an empty slice.

Why not the shorter `TOPN ( 10, VALUES ( dim_client[client_id] ), [Ending AUM] )` with `SUMX ( Top10, [Ending AUM] )`? Inside an iterator, `[Ending AUM]` is evaluated **per client**, so its `LASTNONBLANK` finds **each client's own** last snapshot. In a slice that contains departed clients, they would be ranked on a stale balance from 2022–2023 and could enter the numerator, while the denominator only counts balances on the slice's last date. That would **overstate** the share. The two versions should agree whenever no departed client would make the top 10, and differ when one would.

**(3) Test query**

```DAX
DEFINE
    VAR LastDate = CALCULATE ( MAX ( fact_portfolio_snapshot[snapshot_date] ) )
    VAR Balances =
        ADDCOLUMNS (
            VALUES ( dim_client[client_id] ),
            "@aum", CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), fact_portfolio_snapshot[snapshot_date] = LastDate )
        )
    VAR Top10 = TOPN ( 10, Balances, [@aum], DESC )
EVALUATE
ROW (
    "Last snapshot", LastDate,
    "Top 10 AUM (manual)", SUMX ( Top10, [@aum] ),
    "Ending AUM", [Ending AUM],
    "Share (manual)", DIVIDE ( SUMX ( Top10, [@aum] ), [Ending AUM] ),
    "Top 10 Client Share", [Top 10 Client Share]
)
```
This rebuilds the share by hand with `MAX(snapshot_date)` instead of `LASTNONBLANK`, so the two columns test each other. Expect `Share (manual)` = `Top 10 Client Share`, and `Last snapshot` = 2024-12-01 with no filters.

---

## Prompt 2 (Debug)

> The measure was accepted (State = Ready). The test query fails:
> `Query (2, 9) The syntax for 'LastDate' is incorrect.`

## Response 2

`LastDate` collides with the DAX function **`LASTDATE`**. DAX names are case-insensitive, and a query-level `VAR` can't reuse a function name. Rename the variable. Nothing else changes:

```DAX
DEFINE
    VAR LastSnap = CALCULATE ( MAX ( fact_portfolio_snapshot[snapshot_date] ) )
    VAR Balances =
        ADDCOLUMNS (
            VALUES ( dim_client[client_id] ),
            "@aum", CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), fact_portfolio_snapshot[snapshot_date] = LastSnap )
        )
    VAR Top10 = TOPN ( 10, Balances, [@aum], DESC )
EVALUATE
ROW (
    "Last snapshot", LastSnap,
    "Top 10 AUM (manual)", SUMX ( Top10, [@aum] ),
    "Ending AUM", [Ending AUM],
    "Share (manual)", DIVIDE ( SUMX ( Top10, [@aum] ), [Ending AUM] ),
    "Top 10 Client Share", [Top 10 Client Share]
)
```
The measure itself names its variable `LastSnapshot`, which is not a function name, so it's unaffected.

---

## Result of the fixed test query (run against `hw06.pbix`)

| Last snapshot | Top 10 AUM (manual) | Ending AUM | Share (manual) | Top 10 Client Share |
|---|---:|---:|---:|---:|
| 2024-12-01 | $784,005,019.49 | $12,729,572,078.86 | 0.0615892674657931 | 0.0615892674657931 |

Verification and edge cases are in `verification.md`.
