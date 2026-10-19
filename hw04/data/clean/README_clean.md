# Wildcat Capital — clean tables

Produced by `scripts/02_clean.py` from `data/raw/` (which is never modified). Every change is traceable through `data/audit/` and explained in `decision_log.md` (decision IDs `D##`).

| Table | Raw rows | Clean rows | Quarantined | Added flag columns |
|---|---:|---:|---:|---|
| dim_advisor | 25 | 25 | 0 | — |
| dim_benchmark | 8 | 8 | 0 | — |
| dim_client | 2,525 | 2,500 | 25 | `risk_profile_missing` |
| dim_date | 1,827 | 1,827 | 0 | — |
| dim_security | 500 | 500 | 0 | — |
| fact_fees | 122,197 | 122,197 | 0 | `aum_basis_at_floor` |
| fact_portfolio_snapshot | 129,547 | 129,547 | 0 | `aum_at_floor`, `return_ytd_suspect` |
| fact_transactions | 298,772 | 298,572 | 200 | `trade_on_non_trading_day`, `after_account_closed` |

File names and original columns (names and order) are unchanged. Flag columns are added at the end and are always 0/1.

## Relationships (star schema)

All are many-to-one, from the fact (or child dimension) to the dimension. After cleaning, every one has a 100% match rate (`scripts/03_validate.py`).

| From (many) | To (one) | Notes |
|---|---|---|
| `fact_fees.client_id` | `dim_client.client_id` | |
| `fact_fees.advisor_id` | `dim_advisor.advisor_id` | always equals the client's advisor |
| `fact_fees.fee_date` | `dim_date.date` | always the 1st of the month |
| `fact_portfolio_snapshot.client_id` | `dim_client.client_id` | one snapshot per client per month |
| `fact_portfolio_snapshot.advisor_id` | `dim_advisor.advisor_id` | |
| `fact_portfolio_snapshot.benchmark_id` | `dim_benchmark.benchmark_id` | only 1, 3, 8 are used |
| `fact_portfolio_snapshot.snapshot_date` | `dim_date.date` | always the 1st of the month |
| `fact_transactions.client_id` | `dim_client.client_id` | |
| `fact_transactions.advisor_id` | `dim_advisor.advisor_id` | |
| `fact_transactions.security_id` | `dim_security.security_id` | blank for Deposit / Withdrawal / Advisory Fee (34% of rows); this is by design |
| `fact_transactions.txn_date` | `dim_date.date` | |
| `dim_client.advisor_id` | `dim_advisor.advisor_id` | snowflake: client → advisor |
| `dim_security.benchmark_id` | `dim_benchmark.benchmark_id` | snowflake: security → benchmark |

Join dates on the `date` column (text `YYYY-MM-DD`, or Date type on both sides), not on `date_id`. Facts store the date itself.

`fact_fees` and `fact_portfolio_snapshot` share the grain client × month, so `fee.aum_basis` = `snapshot.aum` for the same client-month (verified on all 122,197 fee rows).

## Column-type settings for a BI tool

| Set as | Columns | Why |
|---|---|---|
| **Text** | `dim_client.zip_code` | 232 ZIPs start with 0 (`03897`) |
| **Text** | `primary_account_type`, `account_type` | the value `529` is a plan name, not a number |
| **Text** | `dim_advisor.certifications` | the value `None` means "no certification"; do not let the import turn it into null |
| **Text** | `risk_profile` | blank for 75 clients; keep the blank (see flags) |
| **Whole number** | all `*_id` columns, `age`, `year`, `month`, `quarter`, `week_of_year`, `years_experience`, flag columns | `security_id` is now `45`, not `45.0` |
| **Decimal** | `aum`, `aum_basis`, `initial_aum`, `amount`, `price`, `shares`, `bps_charged`, `expense_ratio_bps`, `aum_target_mm` | money and quantities |
| **Decimal (fraction, format as %)** | `return_ytd`, `benchmark_return_ytd`, `active_alpha_ytd`, `cash_pct` | stored as fractions (0.0928 = 9.28%). A few values use scientific notation (`-2e-06`); a Decimal import reads them correctly |
| **Date** | `date`, `fee_date`, `snapshot_date`, `txn_date`, `client_since` | ISO `YYYY-MM-DD` |
| **True/False** | `is_active`, `is_etf` | text `True`/`False` |
| **0/1** | `is_month_end`, `is_quarter_end`, `is_year_end`, `is_trading_day` | |

When reading in pandas, use `dtype=str, keep_default_na=False` and convert columns on purpose. Otherwise `None` and blank become NaN and ZIP codes lose their zeros.

## Flag columns added

| Column | Table | Rows = 1 | Meaning | Decision |
|---|---|---:|---|---|
| `risk_profile_missing` | dim_client | 75 | No risk profile on file. These clients are all benchmarked to 60/40 (id 3) **by default**, so do not treat them as Balanced | D03 |
| `aum_basis_at_floor` | fact_fees | 386 | Fee charged on the system's $1,000 AUM floor; the true balance was lower | D22 |
| `aum_at_floor` | fact_portfolio_snapshot | 420 | AUM reported at exactly $1,000 (floor), 92 clients | D22 |
| `return_ytd_suspect` | fact_portfolio_snapshot | 1,475 | YTD return > +100% (977) or < −90% (498), 178 clients. These come from unexplained AUM jumps, not investment performance | D23 |
| `trade_on_non_trading_day` | fact_transactions | 40,630 | Buy or Sell dated on a Saturday or Sunday | D14 |
| `after_account_closed` | fact_transactions | 2,410 | Transaction in a month after the client's last snapshot; all 131 clients are inactive | D15 |

Recommended default: exclude `return_ytd_suspect = 1` and `aum_at_floor = 1` from performance averages, and show the other flags as filters.

## Changes made (see `data/audit/`)

- **D01**: 25 duplicate clients (IDs 2501–2525) quarantined. Each one copies an earlier client with one letter dropped from or added to the last name, and none has any activity. → `quarantine_dim_client_duplicates.csv` (includes `original_client_id`)
- **D02**: 77 full state names converted to USPS codes (the 78th was on a duplicate)
- **D11**: 197,175 `security_id` values converted from `45.0` to `45`. This includes 131 rows that D12 then quarantined. The quarantine file keeps them as they arrived.
- **D12**: 200 transactions with non-existent client IDs (2702–3192) quarantined. Each is an exact copy of a valid transaction ($10,888,495.37). → `quarantine_fact_transactions_orphan_duplicates.csv` (includes `copy_of_txn_id`)
- **D13**: 835 Buys with negative shares changed to positive. `amount = shares × price` now holds on all 197,044 security transactions.
- **D20**: 300 `return_ytd` values stored as `9.28%` replaced by `benchmark_return_ytd + active_alpha_ytd` (6 decimals), confirmed against the percent text within 0.00005.

`value_changes.csv` has one row per changed cell (198,387). `cleaning_log.csv` has one row per action.

## Known limitations (deliberately not fixed)

| # | Limitation | Why it is not fixed |
|---|---|---|
| 1 | **Dividend amounts equal the full market value of the position** (`amount = shares × price` on all 53,864 dividends) | The real dividend per share is not in the data, and assuming a yield would invent income. Do not report dividend income from this table (D16). |
| 2 | **Advisory-fee transactions do not match `fact_fees`.** No client-month agrees (median 3.11× the fee table); totals are $263.7M vs $204.7M after cleaning | Different source systems. `fact_fees` reconciles 100% internally and to snapshot AUM, so use it as the system of record for fee revenue (D17). |
| 3 | **AUM changes are not explained by deposits/withdrawals** (correlation 0.0006) | The snapshot and transaction systems were never reconciled. Flow-adjusted performance cannot be computed (D27). |
| 4 | **`return_ytd` is not flow-adjusted** (raw AUM change), which produces extreme values | No source has the true return. The worst 1,475 are flagged (D23). |
| 5 | **75 clients have no risk profile**, and their benchmark is a default | Filling it would invent a suitability classification (D03). |
| 6 | **40,630 trades dated on weekends** | The true trade date is unknowable. Flagged; monthly totals are unaffected (D14). |
| 7 | **2,410 transactions after an account closed** | There is no closing date in the source. The last snapshot is a proxy, so these are flagged, not removed (D15). |
| 8 | **7,350 client-months (5.7%) with a snapshot but no fee** | Fees may have been waived. Creating fee rows would invent revenue (D24). |
| 9 | **`is_trading_day` counts market holidays as trading days** | It would need an external exchange calendar. Only weekends are used for D14 (D09). |
| 10 | **ETFs have no sector and stocks have no expense ratio** | This is correct structure, not missing data (D07). |
