# HW4 Decision Log — Wildcat Capital data cleaning

**Author:** Aiden James Dumm · **Written:** 2026-10-19, after the raw audit (`reports/dq_summary_raw.csv`, finding IDs `F###`) and **before** any cleaning code.

This log is the specification for `scripts/02_clean.py`. Each entry is one issue: the evidence from the audit, the data-quality dimension it violates, what to do, why, and what goes wrong if the decision is wrong. Entries marked **Leave as is** are deliberate. They are either legitimate structure or problems that cannot be repaired without inventing data. They are recorded here so nobody "fixes" them later.

**Rules for the cleaning program**

1. Read every raw file as text (`dtype=str, keep_default_na=False`); never modify `data/raw/`.
2. One transformation at a time. After each one, print rows affected and a before/after check, and `assert` the after-state.
3. Never delete silently. Removed rows go to `data/audit/quarantine_<table>_<reason>.csv`, and `raw rows = clean rows + quarantined rows` must hold for all eight tables.
4. Never invent a value. If a value is suspicious but cannot be proven wrong or recomputed, keep it and add a 0/1 flag column.
5. Log every action to `data/audit/cleaning_log.csv` and every changed cell to `data/audit/value_changes.csv`.

**Order of operations (and why)**

1. **Dimensions first** (D01–D03). Facts are checked against dimensions, so the dimensions must be final before any fact is judged an orphan.
2. **Key formats before referential integrity** (D11 before D12). If `security_id = "45.0"` is checked before it is converted, all 197,175 security transactions look like orphans and would be quarantined by mistake.
3. **Quarantine before value repairs** (D12 before D13). Duplicate rows leave unmodified, so the quarantine file shows exactly what arrived.
4. **Value repairs before flags** (D13, D20 before D14–D15, D22–D23). Flags are computed on final values.

---

## Defects that will be fixed

### D01 — `dim_client`: 25 duplicate clients
| Field | Entry |
|---|---|
| **Table / column** | `dim_client` (all columns; `client_id` 2501–2525) |
| **Evidence** | F240/F241: 25 rows share first name, ZIP, `client_since` and `initial_aum` (to the cent) with an earlier client. The only difference is a last name missing its final letter (`Lopez` → `Lope`, `Taylor` → `Taylo`). F293: none of the 25 has a single fee, snapshot or transaction. |
| **Dimension violated** | Uniqueness |
| **Decision** | **Quarantine** the 25 copies (`quarantine_dim_client_duplicates.csv`, with the `client_id` of the original they duplicate). Before removing them, assert that (a) each copy matches its original on every column except `client_id` and `last_name`, (b) the copy's last name is the original's last name minus its final letter, and (c) no fact row references the copy. |
| **Justification** | One person counted twice inflates client counts (2,525 instead of 2,500) and the advisor's book. The original row holds the full name and all the activity. |
| **Risk** | If a "copy" is really a different person (e.g., a relative with the same first name and ZIP who opened an account the same day with the same balance to the cent), we drop a real client. This is very unlikely, and since the copies have no activity, no revenue or AUM is lost. |

### D02 — `dim_client.state`: full state names mixed with postal codes
| Field | Entry |
|---|---|
| **Table / column** | `dim_client.state` |
| **Evidence** | F054: 78 of 2,525 values are not USPS codes: Pennsylvania 25, Florida 15, New York 14, New Jersey 13, California 5, Illinois 4, Texas 2. Every other value is a valid 2-letter code. |
| **Dimension violated** | Consistency, Validity |
| **Decision** | **Standardize** to the 2-letter USPS code with an explicit name→code map. Assert that every value afterwards is in the USPS list and that each changed value maps back to its original name. |
| **Justification** | A state slicer would show "PA" and "Pennsylvania" as two states and split Pennsylvania's count (414 + 25). The mapping is unambiguous. |
| **Risk** | Practically none. The map is a fixed standard, and an unmapped name would stop the script. |

### D11 — `fact_transactions.security_id` stored as a decimal (`"45.0"`)
| Field | Entry |
|---|---|
| **Table / column** | `fact_transactions.security_id` |
| **Evidence** | F215: 197,175 of 197,175 non-blank values fail the integer check (`45.0`, `174.0`). F287: as text, **0%** match `dim_security.security_id`. F288: after dropping `.0`, 100% match (0 true orphans). |
| **Dimension violated** | Validity, Consistency, Referential Integrity |
| **Decision** | **Convert** to whole-number text (`"45.0"` → `"45"`). Assert that every value had a zero fractional part (no information lost) and that the RI match rate afterwards is 100%. Blank values stay blank (see D19). |
| **Justification** | The column was written out as a float because it contains blanks. As stored, it breaks the join to `dim_security` in Power BI. |
| **Risk** | If a value had a non-zero decimal (`45.5`), truncating it would point to the wrong security. The assert stops the script in that case. |

### D12 — `fact_transactions.client_id`: 200 orphan rows that duplicate real transactions
| Field | Entry |
|---|---|
| **Table / column** | `fact_transactions.client_id` |
| **Evidence** | F285: 200 rows (`txn_id` 298573–298772, the last 200 IDs) have 200 distinct `client_id`s between 2702 and 3192. No such client exists (max is 2525). F269/F270: each one matches an earlier transaction on every other column (advisor, security, date, type, shares, price, amount). Only the `client_id` differs. |
| **Dimension violated** | Referential Integrity, Uniqueness |
| **Decision** | **Quarantine** all 200 (`quarantine_fact_transactions_orphan_duplicates.csv`), recording the `txn_id` and `client_id` of the valid transaction each one copies. Assert the 1-to-1 match before removing them. |
| **Justification** | They cannot be joined to any client, and the real transaction they copy is already in the table. Keeping them would double-count $10,888,495.37 of transaction amounts once someone fixes the join. |
| **Risk** | If the client dimension is merely *missing* 200 clients, we would lose real activity. Two facts argue against this. Every row is an exact copy of another client's trade (same day, shares to 4 decimals, same price). And the 200 rows sit together at the end of the file. The quarantine file keeps them recoverable. |

### D13 — `fact_transactions.shares`: 836 Buys with negative shares
| Field | Entry |
|---|---|
| **Table / column** | `fact_transactions.shares` (`txn_type = Buy`) |
| **Evidence** | F226: 836 negative values, all on Buys (no Sell or Dividend is negative). F273: `amount = shares × price` fails on exactly these 836 rows, but `amount = |shares| × price` holds on all 836 (F274 passes). `amount` is positive in every row. |
| **Dimension violated** | Validity (sign rule), Consistency |
| **Decision** | **Convert** to the absolute value. Reconcile instead of guessing: assert that after the change `round(shares × price, 2) = amount` for all 197,175 security transactions. |
| **Justification** | The amount and price are both positive and agree with the absolute share count, so the minus sign is the only wrong field. Negative Buy shares would subtract from holdings in any position calculation. |
| **Risk** | If some of these were really reversals (cancelled buys), flipping the sign adds shares that were given back. The data has no reversal type and the amount is positive, so a sign error is the best-supported reading. Every change is in `value_changes.csv` and can be undone. |

### D20 — `fact_portfolio_snapshot.return_ytd`: 300 values stored as percent text
| Field | Entry |
|---|---|
| **Table / column** | `fact_portfolio_snapshot.return_ytd` |
| **Evidence** | F190: 300 values such as `9.28%`, `-3.18%` fail the decimal check. Every other value is a fraction (`0.019504`). Default parsing would turn these 300 into NaN. Elsewhere in the table `return_ytd = benchmark_return_ytd + active_alpha_ytd` holds to 1e-5 on all 129,247 numeric rows. |
| **Dimension violated** | Validity, Consistency |
| **Decision** | **Convert** by recomputing `benchmark_return_ytd + active_alpha_ytd`, rounded to 6 decimals (the precision of the rest of the column). Confirm the repair: assert that the recomputed value equals the percent ÷ 100 within 0.00005 (half of the last percent digit shown) for all 300 rows. |
| **Justification** | Dividing by 100 alone gives only 4 decimals (`0.0928`). The two other columns already hold the full-precision value, and the percent text confirms it. |
| **Risk** | If benchmark or alpha were wrong in these rows, the recomputed return would be wrong too. The cross-check against the percent text guards against that. |

---

## Suspicious values that will be flagged, not changed

### D03 — `dim_client.risk_profile`: 76 blanks
| Field | Entry |
|---|---|
| **Table / column** | `dim_client.risk_profile` |
| **Evidence** | F058: 76 blanks (one of them is a D01 duplicate, so 75 remain). It is tempting to fill them from the snapshot benchmark, because benchmark 3 is used only by Balanced clients. But F300 shows that **all** 3,942 snapshots of the 75 clients use benchmark 3. Balanced is only 31% of clients with a profile. If these were random clients whose profile simply wasn't recorded, about 69% would be on benchmarks 1 or 8. |
| **Dimension violated** | Completeness |
| **Decision** | **Flag**: leave blank and add `risk_profile_missing` (0/1). Do **not** fill with "Balanced". |
| **Justification** | The 100% pattern means the system gave unprofiled clients the 60/40 benchmark *by default*. The benchmark is a result of the missing profile, not evidence of it. Filling "Balanced" would invent a suitability classification, which is a compliance record. |
| **Risk** | Reports by risk profile will show a "(Blank)" group of 75 clients, and their benchmark-relative performance is measured against a default. Both points are documented in `README_clean.md`. |

### D14 — `fact_transactions`: 40,649 Buys/Sells on weekends
| Field | Entry |
|---|---|
| **Table / column** | `fact_transactions.txn_date` × `dim_date.is_trading_day` |
| **Evidence** | F306: 40,649 of 143,311 Buys and Sells fall on a Saturday or Sunday. Across all types, 28.4% of transactions are on weekends, almost exactly the 28.6% share of weekend days. Dates were assigned with no regard to market days. |
| **Dimension violated** | Accuracy/Plausibility |
| **Decision** | **Flag** with `trade_on_non_trading_day` (Buys/Sells only). Keep the dates. |
| **Justification** | Exchanges are closed on weekends, so these dates are wrong. But the true trade date can't be recovered (Friday? Monday?). Moving them would invent data. Deposits, withdrawals and fees can legitimately post on weekends, so they are not flagged. |
| **Risk** | Daily trading-volume visuals will show weekend activity. Monthly and yearly totals are unaffected. |

### D15 — `fact_transactions`: 2,410 transactions after the account closed
| Field | Entry |
|---|---|
| **Table / column** | `fact_transactions.txn_date` vs the client's last snapshot and `dim_client.is_active` |
| **Evidence** | F308: 2,410 transactions for 131 clients are dated in a month after the client's last portfolio snapshot. All 131 are `is_active = False`. Active clients all have snapshots through 2024-12 (F-check "is_active agrees with snapshots" passes). |
| **Dimension violated** | Consistency, Accuracy/Plausibility |
| **Decision** | **Flag** with `after_account_closed`. |
| **Justification** | Trading after closure is implausible, but the source has no closing date. The last snapshot is only a proxy, so these rows are not proven wrong. Some could be final liquidation or transfer-out activity. |
| **Risk** | Revenue and flow totals for inactive clients may be overstated. Analysts can filter on the flag. |

### D22 — AUM recorded at exactly $1,000 (system floor)
| Field | Entry |
|---|---|
| **Table / column** | `fact_portfolio_snapshot.aum`, `fact_fees.aum_basis` |
| **Evidence** | 420 snapshots (92 clients) show `aum = 1000.0` exactly, and no value is ever below 1,000. Those months then show returns near −97%. 386 fee rows use the same 1,000 basis (fees of $0.65–$0.84). |
| **Dimension violated** | Accuracy/Plausibility |
| **Decision** | **Flag** with `aum_at_floor` (snapshot) and `aum_basis_at_floor` (fees). |
| **Justification** | A hard floor means the true value was lower (possibly zero) and was clamped. The real balance is unknown, so it cannot be repaired. |
| **Risk** | Average-AUM and return statistics for these months are distorted. The flag lets analysts exclude them. |

### D23 — Implausible year-to-date returns
| Field | Entry |
|---|---|
| **Table / column** | `fact_portfolio_snapshot.return_ytd` (and therefore `active_alpha_ytd`) |
| **Evidence** | 976 snapshots show a YTD return above +100% (max 94.67, i.e. +9,467%), and 497 below −90%: 1,473 rows, 178 clients. These months coincide with AUM jumping or collapsing (F303: 797 month-over-month AUM moves > 50%). The correlation between monthly AUM change and that month's net deposits/withdrawals is **0.0006**, so the jumps are not explained by recorded cash flows. The return appears to be computed from raw AUM change, not flow-adjusted. |
| **Dimension violated** | Accuracy/Plausibility |
| **Decision** | **Flag** with `return_ytd_suspect` (return > 1.0 or < −0.9). Keep the values. They are internally consistent (return = benchmark + alpha holds). |
| **Justification** | No other source gives the true return. Recomputing a flow-adjusted return is impossible because transactions do not reconcile to AUM (see D27). |
| **Risk** | Averages of return or alpha by advisor will be dominated by these rows if they aren't filtered. Medians are safer. |

---

## Legitimate structure or unfixable — leave as is

### D04 — `dim_client.zip_code` leading zeros
| Field | Entry |
|---|---|
| **Table / column** | `dim_client.zip_code` |
| **Evidence** | F037: 232 ZIPs start with 0 (`03897`). All 2,525 values match `\d{5}`. |
| **Dimension violated** | None (a risk, not a defect) |
| **Decision** | **Leave as is**. Keep as text, and document that BI tools must import it as Text. |
| **Justification** | The values are correct. Only a numeric import would damage them. |
| **Risk** | If imported as a number, `03897` becomes `3897` and map visuals break. |

### D05 — `dim_advisor.certifications = "None"`
| Field | Entry |
|---|---|
| **Table / column** | `dim_advisor.certifications` |
| **Evidence** | F001: 6 of 25 advisors have the literal text `None`. Default `read_csv` would turn it into NaN. |
| **Dimension violated** | None (legitimate value) |
| **Decision** | **Leave as is**. |
| **Justification** | "None" means the advisor holds no certification. It is a real answer, not a missing one. Changing it to blank would make it look unknown. |
| **Risk** | A careless import turns it into null, and the advisor drops out of a "certified vs not" count. Documented. |

### D06 — Mixed letter case / digits in code lists
| Field | Entry |
|---|---|
| **Table / column** | `client_tier` (Retail/HNW/UHNW), `primary_account_type` and snapshot `account_type` (`529`, `IRA`, `Roth IRA`), `dim_benchmark.name` |
| **Evidence** | F038, F039, F164, F023: flagged as mixed formats. Each column has a short, closed list of valid names (3, 5, 5, 8 values). The tier also agrees 100% with the `initial_aum` bands (row rule passes). |
| **Dimension violated** | None |
| **Decision** | **Leave as is**. |
| **Justification** | These are the official names (`529` is the plan type, `HNW` an abbreviation). |
| **Risk** | `529` could be read as a number by a BI tool. Keep the column as Text. |

### D07 — `dim_security`: blank `sector` (219) and blank `expense_ratio_bps` (281)
| Field | Entry |
|---|---|
| **Table / column** | `dim_security.sector`, `dim_security.expense_ratio_bps` |
| **Evidence** | Every one of the 219 ETFs has a blank sector and an expense ratio. Every one of the 281 stocks has a sector and a blank expense ratio. 0 exceptions (completeness and blank-when-not-applicable checks pass). |
| **Dimension violated** | None (structural blanks) |
| **Decision** | **Leave as is**. |
| **Justification** | Funds don't belong to one GICS sector, and individual stocks have no expense ratio. Filling either would be invented data. |
| **Risk** | A sector visual shows a "(Blank)" bar for ETFs. Label it "Fund / multi-sector" in the report layer, not in the data. |

### D08 — `dim_security`: three names used twice
| Field | Entry |
|---|---|
| **Table / column** | `dim_security.name` |
| **Evidence** | `Jones Inc Fund`, `Davis PLC Fund`, `Graham Group Inc.` each appear twice, with different tickers, asset classes or sectors. Tickers are 100% unique. |
| **Dimension violated** | None |
| **Decision** | **Leave as is**. |
| **Justification** | One issuer can offer several funds or share classes. The ticker is the identifier. |
| **Risk** | A visual grouped by name would merge two securities. Group by ticker. |

### D09 — `dim_date.is_trading_day` ignores market holidays
| Field | Entry |
|---|---|
| **Table / column** | `dim_date.is_trading_day` |
| **Evidence** | All 10 derived-column checks pass (year, quarter, month, names, ISO week, month/quarter/year end). `is_trading_day` = 1 on all 1,305 weekdays, including 2020-12-25 and 2022-07-04. |
| **Dimension violated** | Accuracy (minor) |
| **Decision** | **Leave as is**. Document as a limitation. |
| **Justification** | Adding an exchange-holiday calendar means bringing in outside data. The flag is correct as "weekday", and D14 relies only on weekends. |
| **Risk** | About 10 holidays a year are treated as trading days. |

### D10 — `dim_benchmark`: benchmarks with no client portfolios
| Field | Entry |
|---|---|
| **Table / column** | `dim_benchmark` |
| **Evidence** | F290: snapshots use only benchmarks 1, 3, 8. Five are used only by securities, and MSCI Emerging Markets (6) is used by nothing (F291). |
| **Dimension violated** | None |
| **Decision** | **Leave as is**. |
| **Justification** | A dimension may list members with no facts. Benchmarks 2, 4, 5, 7 are the securities' asset-class benchmarks. |
| **Risk** | None. |

### D16 — Dividend amount equals the full position value
| Field | Entry |
|---|---|
| **Table / column** | `fact_transactions.amount` where `txn_type = Dividend` |
| **Evidence** | F275: all 53,864 dividends have `amount = shares × price`, i.e. a 100% "yield" per payment (e.g., txn 1: 455.11 shares × $147.90 = $67,311 dividend). Real dividends are about 0.5–2% of value per payment. |
| **Dimension violated** | Accuracy/Plausibility |
| **Decision** | **Leave as is** and document. A flag would mark every dividend row, so it adds nothing. |
| **Justification** | The true dividend per share is not in the data. Dividing by an assumed yield would invent numbers. |
| **Risk** | Income totals are overstated by a large, unknown factor (a typical 0.5–2% payment would be 50–200× smaller). The report must not present dividend income as real. |

### D17 — Advisory-fee transactions don't match the fee table
| Field | Entry |
|---|---|
| **Table / column** | `fact_transactions` (`Advisory Fee`) vs `fact_fees.amount` |
| **Evidence** | F307: in all 28,746 client-months that have both, the amounts differ (median ratio 3.11). Totals: $263,780,236.09 in transactions vs $204,675,583.12 in the fee table. 1,933 fee debits fall in months with no fee row. By contrast, `fact_fees` reconciles 100% to itself (`amount = aum_basis × bps / 10000 / 12`) and to snapshot AUM (`aum_basis = aum`, 122,197 of 122,197). |
| **Dimension violated** | Consistency (cross-table) |
| **Decision** | **Leave as is**. Treat `fact_fees` as the system of record for fee revenue. |
| **Justification** | The two tables come from different systems, and only `fact_fees` can be proven internally. Neither can be "corrected" from the other. |
| **Risk** | Anyone summing fee revenue from transactions gets a number about 29% higher. Documented in `README_clean.md`. |

### D18 — Near-duplicate cash transactions
| Field | Entry |
|---|---|
| **Table / column** | `fact_transactions` (Deposit / Withdrawal / Advisory Fee) |
| **Evidence** | F272: 528 rows match another row except `amount` (e.g., client 1 deposited $94,893.52 and $26,587.27 on 2024-09-25). F271: 7 Advisory Fee rows match another except `txn_date` (same amount, different dates). Cash rows have only five populated fields, so coincidences are expected. |
| **Dimension violated** | None |
| **Decision** | **Leave as is**. |
| **Justification** | Two deposits on one day, or the same fee in two months, are normal. The amounts or dates differ, so neither row is a copy. |
| **Risk** | Low. |

### D19 — Blank `security_id`, `shares`, `price` on cash transactions
| Field | Entry |
|---|---|
| **Table / column** | `fact_transactions.security_id / shares / price` |
| **Evidence** | 101,597 blanks, exactly the 35,981 Deposits + 29,850 Withdrawals + 35,766 Advisory Fees. Every Buy, Sell and Dividend has all three. |
| **Dimension violated** | None (structural blanks) |
| **Decision** | **Leave as is** (blank, not 0). |
| **Justification** | A deposit involves no security. A 0 would be a false value and would join to no security either way. |
| **Risk** | RI checks must report the blank-key rate separately (34%) and not count it as orphans. |

### D21 — Scientific notation in `return_ytd` / `active_alpha_ytd`
| Field | Entry |
|---|---|
| **Table / column** | `fact_portfolio_snapshot.return_ytd` (135 values), `active_alpha_ytd` (756 values) |
| **Evidence** | F162/F163: values such as `-2e-06`. They parse as valid decimals and pass the return = benchmark + alpha check. |
| **Dimension violated** | Consistency (format only) |
| **Decision** | **Leave as is**. |
| **Justification** | They are valid numbers that Python and Power BI both read correctly. Rewriting them would add 891 value changes that change no value. |
| **Risk** | A tool that reads the column as text would sort them oddly. Import as Decimal. |

### D24 — 7,350 snapshot months with no fee charged
| Field | Entry |
|---|---|
| **Table / column** | `fact_fees` vs `fact_portfolio_snapshot` |
| **Evidence** | F302: 7,350 of 129,547 client-months (5.7%, 2,261 clients, typically 3 months each) have a snapshot but no fee. Every fee row has a matching snapshot. |
| **Dimension violated** | Completeness (possible) |
| **Decision** | **Leave as is**. Do not create fee rows. |
| **Justification** | Fees can be legitimately waived or skipped, and creating a fee would invent revenue. |
| **Risk** | If the fees were charged but not loaded, revenue is understated by about 6%. Documented. |

### D25 — `fact_fees` near-duplicate for client 1169
| Field | Entry |
|---|---|
| **Table / column** | `fact_fees` |
| **Evidence** | F260: fee 57446 (2020-06-01) and 57490 (2024-04-01) are identical except the date: Management, basis $1,000.00 (floor), 85.65 bps, $0.71. |
| **Dimension violated** | None |
| **Decision** | **Leave as is** (both rows are already covered by the D22 floor flag). |
| **Justification** | Different months with the same floor balance and rate give the same fee. It is a coincidence, not a copy. |
| **Risk** | None. |

### D26 — `is_active` and account coverage
| Field | Entry |
|---|---|
| **Table / column** | `dim_client.is_active` |
| **Evidence** | 176 inactive clients. Their last snapshots fall between 2022-12 and 2023-11 (one inactive client is a D01 duplicate with no snapshots), and every active client (except the D01 duplicates) has a snapshot in 2024-12. The consistency check passes. |
| **Dimension violated** | None |
| **Decision** | **Leave as is**. |
| **Justification** | Closed accounts are legitimate history. |
| **Risk** | None. Note that D15 depends on this. |

### D27 — AUM changes not explained by deposits/withdrawals
| Field | Entry |
|---|---|
| **Table / column** | `fact_portfolio_snapshot.aum` vs `fact_transactions` (Deposit/Withdrawal) |
| **Evidence** | F303: correlation 0.0006 between monthly AUM change and net deposits − withdrawals. 539 of 797 jumps > 50% have no matching flow. |
| **Dimension violated** | Consistency (cross-table) |
| **Decision** | **Leave as is**. Document as a known limitation, and use the D23 flag for the worst cases. |
| **Justification** | The snapshot and transaction systems were never reconciled. Which one is "right" can't be decided from this data. |
| **Risk** | A flow-adjusted performance analysis is not possible with this extract. |
