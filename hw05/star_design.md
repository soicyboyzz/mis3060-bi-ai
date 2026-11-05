# HW5 Star Design: Wildcat Capital

**Student:** Aiden James Dumm · MIS3060 Business Intelligence with AI · Villanova University

Every number in this document is produced by `scripts/validate_star.py` (68 PASS, 0 FAIL, 24 INFO; full output in `reports/validation_results.csv`). The data is the instructor's eight-file `Wildcat Capital Clean` release, copied unchanged into `data/`.

---

## Part A: Keys

| Table | Type | Primary key | Foreign keys (column → table[column]) |
|---|---|---|---|
| dim_advisor | Dimension | `advisor_id` | — |
| dim_benchmark | Dimension | `benchmark_id` | — |
| dim_client | Dimension | `client_id` | `advisor_id` → dim_advisor[advisor_id] |
| dim_date | Dimension | `date_id` (the facts join on the alternate key `date`, also unique) | — |
| dim_security | Dimension | `security_id` | `benchmark_id` → dim_benchmark[benchmark_id] |
| fact_fees | Fact | `fee_id` | `client_id` → dim_client[client_id]<br>`advisor_id` → dim_advisor[advisor_id]<br>`fee_date` → dim_date[date] |
| fact_portfolio_snapshot | Fact | `snapshot_id` | `client_id` → dim_client[client_id]<br>`advisor_id` → dim_advisor[advisor_id]<br>`benchmark_id` → dim_benchmark[benchmark_id]<br>`snapshot_date` → dim_date[date] |
| fact_transactions | Fact | `txn_id` | `client_id` → dim_client[client_id]<br>`advisor_id` → dim_advisor[advisor_id]<br>`security_id` → dim_security[security_id] *(can be blank, see below)*<br>`txn_date` → dim_date[date] |

**Proven in code (sections 2–4 of the script):**
- All 8 primary keys have no blanks, are whole numbers, and are unique. `dim_date[date]` is also unique, which it must be to sit on the one side of a relationship.
- None of the 13 foreign keys has an orphan (0 orphan rows on every one).
- **The fact dates match `dim_date[date]`, not `dim_date[date_id]`.** `date_id` is just a row number (1 to 1,827). None of the 550,316 fact date values would match it, and 100% of them match `date`.
- **One key can legitimately be blank: `fact_transactions[security_id]`**, on 101,528 rows. Those are exactly the Deposit (35,956), Withdrawal (29,830) and Advisory Fee (35,742) rows. These are cash movements with no security involved, so `shares` and `price` are blank on the same rows. Every Buy, Sell and Dividend row has a valid `security_id`. No other foreign key has a blank.
- `dim_client[client_since]` looks like a date key but is **not** one. 1,532 of 2,500 values (from 2015-01-01 onward) fall before `dim_date` starts on 2020-01-01, so it is a descriptive attribute.

## Part B: Grain

- **fact_transactions:** One row represents a single transaction event in a client's account: one trade, dividend, deposit, withdrawal or advisory-fee debit, identified by `txn_id`.
  *Check:* `txn_id` is unique. No column combination can replace it: 622 rows repeat the same (client, date, type, security), so a client can legitimately do the same thing twice in one day.
- **fact_fees:** One row represents one client's fee charge for one calendar month, with one `fee_type` per client-month.
  *Check:* (`client_id`, `fee_date`) is unique (0 duplicates), and `fee_date` is always the 1st of the month.
- **fact_portfolio_snapshot:** One row represents one client's portfolio position as of the first day of one month.
  *Check:* (`client_id`, `snapshot_date`) is unique (0 duplicates). Each client has exactly one `account_type`, one `benchmark_id` and one `advisor_id` across all their snapshots, so the grain is client-month, not account-month.

## Part C: Measures

### Fact measures

| Table | Column | Class | What it means for summing or averaging |
|---|---|---|---|
| fact_transactions | `amount` | **Additive** | Can be summed across clients, securities, advisors and time. Amounts are stored as positive numbers and the direction comes only from `txn_type`, so a total is only meaningful within a type (deposits minus withdrawals has to be calculated, not summed). |
| fact_transactions | `shares` | **Semi-additive** | Shares of the **same** security add up across clients and dates, but adding shares of different securities (one SPY plus one bond fund) is meaningless. Sum only with a single security in context. |
| fact_transactions | `price` | **Non-additive** | A per-share price; a sum is meaningless and a plain average ignores trade size. Use amount ÷ shares for an average price. |
| fact_fees | `amount` | **Additive** | Fee dollars sum across clients, advisors, fee types and months. |
| fact_fees | `aum_basis` | **Semi-additive** | The balance the fee was charged on. It equals that month's snapshot `aum` on all 122,197 rows. It can be summed across clients within one month, but never across months. |
| fact_fees | `bps_charged` | **Non-additive** | An annual rate in basis points. Summing rates is meaningless and a simple average over-weights small accounts. The effective rate is SUM(amount) × 12 × 10,000 ÷ SUM(aum_basis). The script confirms amount = aum_basis × bps ÷ 10,000 ÷ 12 on every row. |
| fact_portfolio_snapshot | `aum` | **Semi-additive** | A balance: it sums across clients and advisors at one date, but not across months. For 2024, the 12 monthly snapshots add up to $135.5B against a December total of $12.7B (10.6×). Over time, take the last month or an average. |
| fact_portfolio_snapshot | `return_ytd` | **Non-additive** | A year-to-date percentage that restarts each January (mean absolute value 5.1% in January vs 32.1% in December). Never sum it. Across clients, use an AUM-weighted average; across months, take the latest month, not an average. |
| fact_portfolio_snapshot | `benchmark_return_ytd` | **Non-additive** | Same as `return_ytd`: a cumulative percentage for that client's benchmark. |
| fact_portfolio_snapshot | `active_alpha_ytd` | **Non-additive** | The difference of two percentages (return − benchmark, true on every row). Summing or averaging it across clients is only valid if the same weighting is used for both returns. |
| fact_portfolio_snapshot | `cash_pct` | **Non-additive** | A share of the portfolio (1%–8%). Combine it across clients as an AUM-weighted average, never as a sum. |

### Numeric columns in the facts that are **not** measures
- **Keys:** `txn_id`, `fee_id`, `snapshot_id`, `client_id`, `advisor_id`, `security_id`, `benchmark_id`. They are identifiers, and summing them is meaningless (Power BI's default "Sum of client_id" needs switching to "Don't summarize").
- **Date parts:** `fact_portfolio_snapshot[year]` and `[month]` repeat `snapshot_date` (they agree on every row). Use `dim_date` instead.
- **Flags:** `is_post_departure_txn` (2,410 transactions of inactive clients after their last snapshot) and `is_return_suspect` (3,875 snapshots). Summing them counts flagged rows, which is a count, not a business amount.

### Numeric attributes in the dimension tables that should never be summed
- **dim_advisor:** `years_experience`; `aum_target_mm` (a per-advisor target, repeated on every fact row once joined, so summing it through a fact multiplies it).
- **dim_client:** `age`; `initial_aum` (a balance at onboarding, dated anywhere from 2015 to 2022, so a sum mixes years); `zip_code` (an identifier with leading zeros, 228 of them, so load it as Text).
- **dim_security:** `expense_ratio_bps` (a rate, filled only for the 219 ETFs); `benchmark_id` (a key).
- **dim_date:** `date_id`, `year`, `quarter`, `month`, `week_of_year`, and the 0/1 flags `is_month_end`, `is_quarter_end`, `is_year_end`, `is_trading_day`.
- **All dimensions:** the `*_id` keys.

## Part D: Power BI model

The model in `powerbi/hw05.pbix` loads the eight tables unchanged. Column types follow `powerbi_guide.md`: keys are Whole Number, the five date columns are Date, amounts, prices and returns are Decimal, `zip_code` is Text, `is_active` and `dim_security[is_etf]` are True/False (their values are stored as True/False, so Whole Number would turn every row into an Error), and the other `is_*` flags (stored as 0/1) are Whole Number. `dim_date` is marked as the date table on `date`. The screenshot is `powerbi/model_view.png`: the facts sit in the middle with the dimensions around them, and no line runs through a table. A few lines have to cross each other, because each of the three facts links to all three conformed dimensions (`dim_client`, `dim_advisor`, `dim_date`), and that pattern (a K3,3 graph) cannot be drawn flat without at least one crossing. Report page 1 holds the Part D checks: a Count card per table (all eight match the handout row counts), a `dim_security[ticker]` × `fact_transactions[amount]` table whose only `(Blank)` row is the cash transactions, and a `dim_advisor[last_name]` slicer with fee, transaction and AUM total cards that all change when one advisor is picked.

| # | From (many) | To (one) | Cardinality | Direction | Active |
|---|---|---|---|---|---|
| 1 | fact_transactions[client_id] | dim_client[client_id] | *:1 | Single | Yes |
| 2 | fact_transactions[advisor_id] | dim_advisor[advisor_id] | *:1 | Single | Yes |
| 3 | fact_transactions[security_id] | dim_security[security_id] | *:1 | Single | Yes |
| 4 | fact_transactions[txn_date] | dim_date[date] | *:1 | Single | Yes |
| 5 | fact_fees[client_id] | dim_client[client_id] | *:1 | Single | Yes |
| 6 | fact_fees[advisor_id] | dim_advisor[advisor_id] | *:1 | Single | Yes |
| 7 | fact_fees[fee_date] | dim_date[date] | *:1 | Single | Yes |
| 8 | fact_portfolio_snapshot[client_id] | dim_client[client_id] | *:1 | Single | Yes |
| 9 | fact_portfolio_snapshot[advisor_id] | dim_advisor[advisor_id] | *:1 | Single | Yes |
| 10 | fact_portfolio_snapshot[benchmark_id] | dim_benchmark[benchmark_id] | *:1 | Single | Yes |
| 11 | fact_portfolio_snapshot[snapshot_date] | dim_date[date] | *:1 | Single | Yes |
| 12 | dim_security[benchmark_id] | dim_benchmark[benchmark_id] | *:1 | Single | Yes |
| 13 | dim_client[advisor_id] | dim_advisor[advisor_id] | *:1 | Single | **No (inactive)** |
| — | dim_client[client_since] | dim_date[date] | not created | | |

**Conformed dimensions:** `dim_client`, `dim_advisor` and `dim_date` are shared by all three facts, so one slicer on any of them filters transactions, fees and snapshots consistently. `dim_benchmark` is shared by the snapshot (directly) and the transactions (through `dim_security`), but in two different roles (see (d)). `dim_security` belongs to `fact_transactions` only.

## Part E: Relationships and design questions

**(a) Some transaction rows have no `security_id`. Why, and is that a defect?**
The 101,528 blank rows are exactly the Deposit, Withdrawal and Advisory Fee transactions. Money moves into or out of the account as cash, and no security is bought or sold, so there is no security to point to (and `shares` and `price` are blank too). It is **not a defect**. It is the expected structure of a fact table that mixes trades with cash flows, and the script proves the rule in both directions: every cash row is blank and every Buy/Sell/Dividend row has a key that matches `dim_security`. In Power BI these rows appear as a `(Blank)` ticker, which is correct. Replacing the blank with a fake "cash" security would mean creating a new row, which this assignment forbids, and it would also hide the distinction.

**(b) `advisor_id` is in `dim_client` and on all three fact tables. Which relationship(s) did I keep active, and why?**
I kept the three **fact → dim_advisor** relationships active and made **dim_client → dim_advisor inactive**. With both active, `dim_advisor` would reach each fact two ways (directly, and through `dim_client`). Power BI does not allow that ambiguity, so one path has to be dashed. I chose the direct path because:
1. It keeps the model a true star: every fact is one hop from every dimension it uses, which is what Assignment 6's measures will expect.
2. The advisor recorded on the fact row is the advisor of record for that event. The script shows it matches `dim_client[advisor_id]` on 100% of rows in all three facts, so today both paths give identical totals. If a client were ever reassigned, the fact-level advisor would still credit each fee or trade to the advisor who actually handled it.

The cost: an advisor slicer does not filter the `dim_client` table itself, so a count of clients built from `dim_client` alone will not split by advisor. Counting distinct `client_id` in a fact table works, and the inactive relationship can be switched on inside a measure with `USERELATIONSHIP` if needed.

**(c) The date dimension has its own `date_id`, but the facts store calendar dates. Which column did I join on, and why?**
I joined `txn_date`, `fee_date` and `snapshot_date` to **`dim_date[date]`**. The fact tables contain dates (2024-12-01), not date IDs. `date_id` is a row number from 1 to 1,827 that no fact column stores, so joining on it would match nothing (the script finds 0 of 550,316 fact dates that equal a `date_id`) and every date slicer would show `(Blank)`. `dim_date[date]` is unique and contiguous (2020-01-01 to 2024-12-31, no gaps), so it is a valid one-side key, and it is also the column used when marking the date table. Both columns were loaded as Date, not Date/Time, so the values match exactly. I did **not** relate `dim_client[client_since]` to `dim_date`: 1,532 values fall before 2020 and would appear as blanks, and a second active path from `dim_date` through `dim_client` to the facts would conflict with the fact date relationships.

**(d) Star or snowflake: does anything in the eight tables connect one dimension to another? Did I keep it?**
Yes, two dimension-to-dimension links:
- **dim_client → dim_advisor:** kept but **inactive**, for the reason in (b). The facts carry `advisor_id` themselves, so the snowflake link is not needed.
- **dim_security → dim_benchmark:** kept and **active**. Transactions have no `benchmark_id` of their own, so this is the only way to analyse trades by the benchmark (or asset-class index) a security tracks. It causes no ambiguity, because `dim_benchmark` reaches `fact_transactions` only through `dim_security` and reaches `fact_portfolio_snapshot` only directly.

So the model is **mostly a star with one snowflake arm** (benchmark through security). One caution: `dim_benchmark` plays two roles. On a snapshot it is the client's **portfolio** benchmark (set by risk profile, and only 3 of the 8 benchmarks are used). Through `dim_security` it is the **security's** index (6 of 8 used). A benchmark slicer therefore means different things for different visuals. The cleanest fix would be two copies of the table (portfolio benchmark and security benchmark), but this assignment forbids adding tables, so I documented it instead.

## Part F: Reflection

| # | Fact table | Business question | Single visual, no DAX workaround? |
|---|---|---|---|
| 1 | fact_fees | *How much fee revenue did each advisor earn per quarter in 2024, by fee type?* | **Yes** |
| 2 | fact_transactions | *What was each advisor's net new money (deposits minus withdrawals) in 2024?* | **No** |
| 3 | fact_portfolio_snapshot | *What was each advisor's AUM at the end of each quarter, and what AUM-weighted return did their clients earn against benchmark?* | **No** |

1. **Fee revenue: answerable.** Fee `amount` is fully additive and the fact is related to `dim_advisor`, `dim_date` and its own `fee_type`. A matrix with advisors on rows, `dim_date[quarter]` on columns, `fee_type` as a legend and a year = 2024 filter gives the right totals using the default Sum. (I would not add the Advisory Fee transactions to it: those are cash debits from a different process, $263.7M against $204.7M in `fact_fees`, so adding them would double count.)
2. **Net new money: not answerable.** `amount` is always positive, and its direction lives only in `txn_type`. One visual can show deposits and withdrawals side by side, but not the difference, without a measure that subtracts one from the other. **Schema fix:** store a signed flow amount (inflows +, outflows −), or add a small transaction-type dimension with a +1/−1 sign column, so that a plain Sum returns net flow.
3. **Quarter-end AUM and weighted return: not answerable.** Power BI's default Sum of `aum` at quarter level adds three monthly balances together (at year level the overstatement is 10.6×), and Average of `return_ytd` is unweighted and mixes months. A filter to the last month works for one level of the date hierarchy only. `dim_date`'s `is_quarter_end` flag doesn't help either, because snapshots are dated the 1st of the month, which is never a month-end date. **Schema fix:** date each snapshot at period end (or add "is last snapshot of the month/quarter/year" flags that match snapshot dates), so a balance can be filtered rather than summed. An AUM-weighted return will always need a ratio measure, but storing a monthly return next to opening AUM would make it a simple SUMPRODUCT instead of reverse-engineering YTD figures.

**Honest assessment:** the model joins correctly (no orphans, no ambiguous paths, row counts reconcile), so anything built on additive measures such as fee and transaction dollars works with default aggregations. The weak spots are the balance (`aum`, `aum_basis`) and the ratios (returns, `bps_charged`, `cash_pct`), which will give wrong totals in any visual until Assignment 6 adds measures. There is also the dual-role `dim_benchmark`, which a user could easily misread.
