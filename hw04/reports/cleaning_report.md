# Wildcat Capital Data Warehouse — Cleaning Report

**To:** Portfolio Committee · **From:** Aiden James Dumm · **Date:** October 19, 2026
**Scope:** 8 warehouse tables (5 dimensions, 3 facts), 555,401 raw rows, January 2020 – December 2024

## Executive summary

The extract can be used for reporting after cleaning, with three important caveats. Before cleaning, the warehouse could not be joined correctly: **0% of the 197,175 security transactions matched a security**, because the security ID was stored as `45.0` instead of `45`. It also contained 25 duplicate clients and 200 transactions copied onto client IDs that do not exist ($10.9M of double-counted activity).

After cleaning, **all 13 table relationships match 100%**, every recomputable amount reconciles, and 555,176 rows remain. Only 225 rows (0.04%) were removed, and all of them are kept in quarantine files. No value was invented. Suspicious values that cannot be proven wrong are kept and marked with six 0/1 flag columns.

**The caveats the committee should know before using these numbers:**
1. **Dividend income is not usable.** Every dividend equals the full market value of the position.
2. **Fee revenue must come from the fee table, not from transactions.** The two sources differ by 29%.
3. **Reported YTD returns are not flow-adjusted.** 1,475 snapshots show returns above +100% or below −90%.

## Cleaning summary

| # | Issue found | Rows | Action |
|---|---|---:|---|
| D11 | `security_id` stored as `45.0`, so transactions don't join to securities | 197,175 | Converted to `45`; join match 0% → 100% |
| D13 | Buys recorded with negative shares (amount and price positive) | 835 | Sign corrected; amount = shares × price now holds on all 197,044 security transactions |
| D12 | Transactions on non-existent client IDs (2702–3192), each an exact copy of a real trade | 200 | Quarantined |
| D01 | Duplicate clients (IDs 2501–2525): last name off by one letter, no activity | 25 | Quarantined |
| D20 | YTD returns stored as text (`9.28%`) that a numeric import would drop | 300 | Recomputed as benchmark + alpha; confirmed against the % text |
| D02 | State stored as full name ("Pennsylvania") instead of "PA" | 77 | Standardized to postal code |
| D03 | Client has no risk profile | 75 | Flagged `risk_profile_missing`; **not** filled |
| D14 | Buy/Sell dated on a weekend | 40,630 | Flagged `trade_on_non_trading_day` |
| D15 | Transactions after the client's account closed | 2,410 | Flagged `after_account_closed` |
| D22 | AUM at the system floor of exactly $1,000 | 420 snapshots / 386 fees | Flagged `aum_at_floor` / `aum_basis_at_floor` |
| D23 | YTD return above +100% or below −90% | 1,475 | Flagged `return_ytd_suspect` |

In total, 198,387 individual cell changes were made, each logged with its old and new value in `data/audit/value_changes.csv`. Another 16 issues were investigated and deliberately left as is (see `decision_log.md`). For example, blank sectors on ETFs and blank security fields on deposits are correct structure, not missing data.

### Data-quality scorecard (raw → clean)

| Table | Completeness | Key uniqueness | Type validity | Rule pass | Referential match |
|---|---|---|---|---|---|
| fact_transactions | 100% → 100% | 99.933% → 100% | 91.730% → 100% | 98.039% → 98.098% | **81.95% → 100%** |
| fact_portfolio_snapshot | 100% → 100% | 100% → 100% | 99.982% → 100% | 100% → 100% | 100% → 100% |
| dim_client | 99.785% → 99.786% | 99.010% → 100% | 100% → 100% | 99.718% → 100% | 100% → 100% |
| fact_fees, dim_advisor, dim_benchmark, dim_date, dim_security | 100% | 100% | 100% | 100% | 100% (or n/a) |

Transaction rule pass stays at 98.1% because the dividend plausibility rule fails on all 53,826 dividends (caveat 1). Client completeness stays below 100% because the 75 missing risk profiles were deliberately left blank.

**Reconciliations after cleaning:** transaction amount = shares × price on 197,044 of 197,044 rows (the $0.13 total gap is cent rounding). Fee = AUM basis × bps ÷ 10,000 ÷ 12 on 122,197 of 122,197. Fee AUM basis = snapshot AUM on 122,197 of 122,197. Return = benchmark + alpha on 129,547 of 129,547.

## Key judgment calls

**1. Missing risk profiles were not filled, even though the data seemed to supply an answer.** Every one of the 75 unprofiled clients is measured against the 60/40 benchmark, which is otherwise used only for "Balanced" clients. Filling them in as Balanced looked like an easy fix. But only 31% of profiled clients are Balanced. If the profiles were simply unrecorded, most of these clients would be on other benchmarks. The 100% pattern means the system *defaulted* them to 60/40 because the profile was missing. *Justification:* a risk profile is a suitability record, and inventing one is a compliance risk. *Risk:* risk-profile reports show a blank group of 75 clients, and their benchmark-relative performance is measured against a default.

**2. The 200 orphan transactions were quarantined, not reassigned.** Each one matches a real transaction exactly (same advisor, security, date, shares to four decimals, price and amount) under a client ID that does not exist. *Justification:* the real trade is already in the table, so keeping the copy would double-count $10,888,495.37. *Risk:* if the client table is missing 200 real clients, that activity is lost. The rows are preserved in `quarantine_fact_transactions_orphan_duplicates.csv` with the ID of the trade each one copies, so the decision can be reversed.

**3. Negative Buy shares were treated as sign errors.** On all 835 rows, the amount equals |shares| × price and is positive. Only the minus sign disagrees with the rest of the row. *Justification:* the other two columns confirm the repair. Negative Buys would otherwise reduce holdings in any position calculation. *Risk:* if some were cancelled trades, we have added shares that were given back. The data has no reversal type, and every change can be undone from the audit log.

**4. Fee revenue comes from `fact_fees`, not from transaction fee debits.** In all 28,746 client-months that appear in both, the amounts disagree (totals: $263.7M in transactions vs $204.7M in the fee table). *Justification:* `fact_fees` reconciles to the cent with its own formula and with snapshot AUM. The transaction debits reconcile to nothing. *Risk:* if the transaction system is the one that is right, reported fee revenue is understated.

**5. Weekend trades and post-closure activity were flagged, not moved or deleted.** About 28% of Buys and Sells fall on weekends, which matches the share of weekend days in a year, so the dates look randomly assigned. *Justification:* the true trade dates cannot be recovered, and monthly totals are unaffected. *Risk:* daily trading-activity charts are unreliable.

## Limitations

- **Dividends:** all 53,864 raw dividend records (53,826 after cleaning) equal the position's full market value, a "100% yield". Income figures from this table are not meaningful.
- **Performance:** returns are based on raw AUM change. Month-to-month AUM changes have essentially no correlation (0.0006) with recorded deposits and withdrawals, so flow-adjusted returns cannot be computed. Use medians, or exclude `return_ytd_suspect`.
- **AUM floor:** 420 snapshots (92 clients) report exactly $1,000. The true balance was lower and is unknown.
- **Fees:** 7,350 client-months (5.7%) have a portfolio snapshot but no fee. These may be waivers or unloaded data, and no fees were created.
- **Calendar:** `is_trading_day` treats market holidays as trading days.

---
*AI-assisted report — reviewed for factual accuracy on [date] by Aiden James Dumm*
