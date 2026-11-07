# Part D — Claude-assisted measure: `Top 10 Client Share` (measure 11)

**Workflow:** Draft → Test → Debug → Review (Week 10).

**Tool note:** this session ran with **Claude in Claude Code** (Claude Opus 5.5, Anthropic), the same assistant that drafted the other scripts here, rather than the Claude Desktop app. The prompt and responses below are the full exchange.

---

## Prompt 1 (Draft)

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
