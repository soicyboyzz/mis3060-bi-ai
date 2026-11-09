# HW6 Measure Library: AUM & Performance

**Student:** Aiden James Dumm · MIS3060 Business Intelligence with AI · Villanova University

All measures live in the `_Measures` table of `powerbi/hw06.pbix`, grouped in display folders (0 Base, 1 AUM, 2 Growth, 3 Yield & growth, 4 Performance). Every value below is reconciled to pandas in `reports/measure_reconciliation.csv` (159 rows, all match).

**Additivity patterns** (from HW5 Part C):
- **SUM:** additive amounts (fee dollars, cash flows) that can be added across any dimension.
- **Last balance:** semi-additive balances (`aum`), taken at the last snapshot date in the filter. They are never summed across months.
- **Recompute-and-weight:** non-additive rates and ratios (bps, returns, shares), rebuilt from additive parts or weighted by `aum`. They are never summed or simply averaged.

The last-snapshot logic used throughout is `LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )`. Snapshots are dated the 1st of each month, so `LASTDATE`/`ENDOFMONTH` would land on dates with no rows.

---

## Part A: Measures

### Base measures (from ICE 9 and ICE 10)

| Measure | DAX | Pattern | Format |
|---|---|---|---|
| `Total Fees` | `SUM ( fact_fees[amount] )` | SUM | `$#,0.00` |
| `Net Flows` | `CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Deposit" ) - CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Withdrawal" )` | SUM (by type) | `$#,0.00` |
| `Effective Fee Rate (bps)` | `DIVIDE ( SUM ( fact_fees[amount] ) * 12 * 10000, SUM ( fact_fees[aum_basis] ) )` | recompute | `#,0.00` |

`Effective Fee Rate (bps)` is only there for the comparison in Part C (b).

### 0. `AUM (naive SUM)`: wrong on purpose, never put on a report
```DAX
AUM (naive SUM) = SUM ( fact_portfolio_snapshot[aum] )
```
**Format:** `$#,0.00`. **Pattern:** plain SUM applied to a balance, which is the mistake. **Meaning:** none. At the grand total it reports **$566.68B**, about 44.5× the firm's real $12.73B, because it adds 60 monthly balances together. pandas makes exactly the same mistake (row `AUM (naive SUM), All`), which shows the problem is the formula, not the tool. Its description in the model says "WRONG ON PURPOSE".

### 1. `Ending AUM`
```DAX
Ending AUM =
CALCULATE (
    SUM ( fact_portfolio_snapshot[aum] ),
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
)
```
**Format:** `$#,0.00`. **Pattern:** last balance. **Meaning:** how much Wildcat manages at the end of the selected period. It is **$12,729,572,078.86** at December 2024 for the whole firm.

### 2. `Ending Clients`
```DAX
Ending Clients =
CALCULATE (
    DISTINCTCOUNT ( fact_portfolio_snapshot[client_id] ),
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
)
```
**Format:** `#,0`. **Pattern:** last balance (a distinct count at the last date). **Meaning:** how many clients still hold an account at the end of the period. That's 2,325 today; the other 175 of the 2,500 clients have left.

### 3. `Avg AUM per Client`
```DAX
Avg AUM per Client = DIVIDE ( [Ending AUM], [Ending Clients] )
```
**Format:** `$#,0.00`. **Pattern:** recompute (a ratio of two last-balance measures). **Meaning:** the typical relationship size at period end. It is $5.48M firm-wide, but ranges from $383K for Retail to $39.5M for UHNW.

### 4. `Ending AUM LY` and `AUM YoY %`
```DAX
Ending AUM LY = CALCULATE ( [Ending AUM], SAMEPERIODLASTYEAR ( dim_date[date] ) )

AUM YoY % = DIVIDE ( [Ending AUM] - [Ending AUM LY], [Ending AUM LY] )
```
**Format:** `Ending AUM LY` `$#,0.00`, `AUM YoY %` `0.00%`. **Pattern:** last balance, time-shifted, with a recomputed growth ratio. `LASTNONBLANK` runs inside the shifted dates, so LY is the last snapshot of the prior period. `DIVIDE` without a third argument returns blank for 2020, which has no prior year, instead of a misleading 0%. **Meaning:** how much the book grew over 12 months. 2024: **+19.58%** ($10.64B → $12.73B).

### 5. `Ending AUM PM` and `AUM MoM %`
```DAX
Ending AUM PM = CALCULATE ( [Ending AUM], DATEADD ( dim_date[date], -1, MONTH ) )

AUM MoM % = DIVIDE ( [Ending AUM] - [Ending AUM PM], [Ending AUM PM] )
```
**Format:** `Ending AUM PM` `$#,0.00`, `AUM MoM %` `0.00%`. **Pattern:** last balance, shifted one month. **Meaning:** the latest monthly change. December 2024 vs November 2024 is in the reconciliation rows `Dec 2024`.

### 6. `Avg Monthly AUM`
```DAX
Avg Monthly AUM =
DIVIDE (
    SUM ( fact_portfolio_snapshot[aum] ),
    DISTINCTCOUNT ( fact_portfolio_snapshot[snapshot_date] )
)
```
**Format:** `$#,0.00`. **Pattern:** recompute (the sum of balances ÷ the number of months, which is the only valid use of a balance sum). **Meaning:** the average size of the book over the period, which is the right base for anything earned over the whole period. 2024: $11.29B, below the $12.73B year-end figure because AUM grew during the year.

### 7. `Fee Yield (bps)`
```DAX
Fee Yield (bps) = DIVIDE ( [Total Fees] * 12 * 10000, SUM ( fact_portfolio_snapshot[aum] ) )
```
**Format:** `#,0.00` (bps, 2 decimals). **Pattern:** recompute and weight, across **two fact tables** (fees from `fact_fees`, AUM from `fact_portfolio_snapshot`). Both share `dim_date` and `dim_client`, so the same filter reaches both. Multiplying monthly fees by 12 annualizes them; the AUM sum covers the same months. **Meaning:** how many basis points per year Wildcat collects on the money it manages. 2024: 43.15 bps overall; Retail pays 82.81 and UHNW 36.14.

### 8. `Organic Growth Rate`
```DAX
Organic Growth Rate = DIVIDE ( [Net Flows], [Ending AUM LY] )
```
**Format:** `0.00%`. **Pattern:** recompute (an additive flow ÷ a last balance). **Meaning:** how much of the growth came from clients adding money rather than from markets. 2024: 0.73% of the opening balance. At the grand total it divides five years of flows by the December 2023 balance, so read it by year.

### 9. `AUM-Weighted Alpha`
```DAX
AUM-Weighted Alpha =
VAR LastSnapshot =
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
RETURN
    CALCULATE (
        DIVIDE (
            SUMX ( fact_portfolio_snapshot, fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd] ),
            SUM ( fact_portfolio_snapshot[aum] )
        ),
        LastSnapshot,
        fact_portfolio_snapshot[is_return_suspect] = 0
    )
```
**Format:** `0.00%`. **Pattern:** recompute and weight (Σ aum × alpha ÷ Σ aum, row by row with `SUMX`), restricted to the last snapshot and with suspect returns removed. **Meaning:** how far the average client dollar has beaten or trailed its benchmark so far this year. 2024: +1.45%.

### 10. `Alpha Signal`
```DAX
Alpha Signal =
VAR Alpha = [AUM-Weighted Alpha]
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( Alpha ), BLANK (),
        Alpha >= 0.02, "Outperforming",
        Alpha <= -0.02, "Lagging",
        "In line"
    )
```
**Format:** text (no number format). **Pattern:** a text label on a recomputed measure. The `ISBLANK` test comes first, so an empty slice shows blank rather than "In line". **Meaning:** a quick flag for the manager: 2022 (+2.85%) and the Retail tier in 2024 (+2.40%) are "Outperforming", and everything else is "In line".

### 11. `Top 10 Client Share`
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
**Format:** `0.00%`. **Pattern:** recompute (a ratio of two last-balance sums), where **both parts use the same last date**. `VALUES ( dim_client[client_id] )` keeps the ranking inside the current filter, so in the tier table each tier ranks only its own clients and the share can't exceed 100%. **Meaning:** concentration risk, or how much of the book walks out the door if the ten biggest relationships leave. It is 6.16% firm-wide, but 8.13% within UHNW and 67–81% within single advisors' books (the four checked in Part D). Part D explains why the date is fixed once instead of using `[Ending AUM]` per client.

### Report page **Measures** (`powerbi/hw06.pbix`, picture in `powerbi/measures_page.jpg`)
- **Card:** Ending AUM, Ending Clients, Avg AUM per Client, Top 10 Client Share.
- **Table by `dim_date[year]`:** Ending AUM, AUM YoY %, Avg Monthly AUM, Fee Yield (bps), Organic Growth Rate, AUM-Weighted Alpha, Alpha Signal.
- **Table by `dim_client[client_tier]`** with a visual-level filter `year is 2024`: Ending AUM, Avg AUM per Client, AUM YoY %, Fee Yield (bps), Organic Growth Rate, AUM-Weighted Alpha, Alpha Signal, Top 10 Client Share.

Model changes beyond the posted file:
1. Added `_Measures` (with its placeholder `Column1` deleted).
2. Marked `dim_date` as the date table on `date`. Despite the guide, it was **not** marked in the posted file, and auto date/time tables were still attached to it.
3. Set `dim_date[year]` to *Don't summarize* so tables group by year instead of adding 2020 + 2021 + …

All three fact-to-`dim_date` relationships were left as posted.

---

## Part C: Design questions

Pandas evidence for every number below is in `reports/part_c_evidence.csv` (written by `scripts/01_reconcile_measures.py`). The Power BI side of (a) is in `reports/powerbi_part_c.csv`.

### (a) `Ending AUM` vs `SUMX ( VALUES ( dim_client[client_id] ), [Ending AUM] )`

| | Power BI | pandas |
|---|---:|---:|
| `Ending AUM` (no filters) | $12,729,572,078.86 | $12,729,572,078.86 |
| `SUMX ( VALUES ( dim_client[client_id] ), [Ending AUM] )` | $13,149,297,713.80 | $13,149,297,713.80 |
| **Difference** | **$419,725,634.94** | **$419,725,634.94** |

`Ending AUM` finds **one** last date for the whole filter (2024-12-01) and adds the balances on it. `SUMX` iterates client by client, and context transition makes `[Ending AUM]` find **each client's own** last snapshot. For the 2,325 active clients that is still December 2024. But **175 clients left the firm** (all 175 are `is_active = False`), and their last snapshots fall between **2022-12-01 and 2023-11-01**. The SUMX version adds their final balances, $419,725,634.94 in total, which is money Wildcat no longer manages. The difference is exactly their sum.

**"How much do we manage today?" is answered by `Ending AUM` ($12.73B).** The SUMX figure mixes balances from different dates and counts departed clients, so it describes no real point in time.

### (b) Why 2024 `Fee Yield (bps)` (43.15) is lower than `Effective Fee Rate (bps)` (45.53)

Both measures have the same numerator: 2024 fees × 12 × 10,000. Only the denominators differ:

| 2024 | value |
|---|---:|
| `SUM ( fact_portfolio_snapshot[aum] )`, the Fee Yield base | $135,459,843,783.73 over **27,900** client-months |
| `SUM ( fact_fees[aum_basis] )`, the Effective Fee Rate base | $128,385,303,527.10 over **26,216** fee rows |
| Snapshot client-months with **no fee row** | **1,684**, holding **$7,074,540,256.63** (5.2% of 2024 AUM) |
| `aum_basis` vs snapshot `aum` where a fee row exists | identical on every one of the 26,216 rows |

So the gap is not a pricing difference. On every client-month that has a fee, the fee basis equals the snapshot AUM to the cent. The gap comes entirely from the **1,684 client-months that appear in the snapshot but have no fee charge**. Fee Yield counts that AUM in the denominator and earns nothing on it, which pulls it down by the same ratio: 45.53 × (128.39 ÷ 135.46) = 43.15.

**The data limitation:** `fact_fees` does not have a row for every client-month. 1,082 clients have at least one fee-less month in 2024 (Retail 1,054 months, HNW 472, UHNW 158), and the gap exists every year (7,350 client-months in 2020–2024). The data can't tell us whether those months were **waived or unbilled** (real lost revenue) or **missing from the extract** (a data-quality gap). Effective Fee Rate tells you what is charged *when* Wildcat bills. Fee Yield tells you what the firm actually earns on everything it manages. The difference between them is the question to put to the billing team.

### (c) Why `AUM-Weighted Alpha` uses the last snapshot only, and excludes suspects

**Last snapshot only:** `active_alpha_ytd` is **year-to-date**. January's value covers one month and December's covers twelve, and the value restarts every January. Averaging across months adds readings that overlap (December already contains January), so the result describes no period. Weighting all 2024 rows gives **+0.32%**, against **+1.45%** at the December snapshot, which is the real full-year figure. At one snapshot date every client's value covers the same span, so they can be combined.

**Excluding `is_return_suspect = 1`:** at 2024-12-01 there are 148 suspect rows among 2,325, with alphas from −120.9% to **+7,133.8%**. These are impossible returns, flagged in HW4 rather than deleted.

| Rows at 2024-12-01 | AUM-weighted | Simple mean |
|---|---:|---:|
| Suspects excluded (the measure) | **+1.45%** | +0.88% |
| Suspects included | +1.67% | **+15.56%** |

A single 7,000% row moves the simple mean by about 3 points on its own. Including the suspects inflates the simple mean to 15.6%, which is absurd. The AUM weighting dampens them, but they still add 0.22 points, enough to change a signal near a ±2% threshold. The simple mean without suspects (+0.88%) is lower than the weighted value (+1.45%), which means large accounts outperformed small ones. **The weighted figure is the one that answers "how did client money do?"**

### (d) Organic Growth Rate by client tier, 2024

| Tier (2024) | Net Flows | Ending AUM LY | Organic Growth | AUM YoY % | YoY − organic |
|---|---:|---:|---:|---:|---:|
| HNW | $25.2M | $2.13B | 1.18% | 19.64% | 18.46 pts |
| Retail | $44.2M | $0.45B | **9.87%** | 19.13% | 9.26 pts |
| UHNW | $8.1M | $8.07B | 0.10% | 19.59% | 19.49 pts |
| **Firm** | $77.5M | $10.64B | 0.73% | 19.58% | 18.85 pts |

**What it says:** every tier grew about 19–20% in 2024, but almost none of that came from new money. For UHNW, the tier that holds 76% of the firm's AUM, net flows explain 0.1 points of 19.6. Retail is the only tier where clients are adding money at a meaningful rate: about half its growth is organic, and it brings in the most new dollars ($44.2M) despite being the smallest book. **Wildcat's growth in 2024 came from markets, not from winning assets.** Retail is the growth engine for flows, and it also pays the highest fee yield (82.8 bps).

**What it does not tell you:**
- **The residual is not "market performance".** YoY − organic also contains fees debited, dividends and any data gaps. It's a remainder, not a measured return.
- **Client wins and losses.** Net flows come from existing clients only. Ending Clients is unchanged in 2024 (687 / 1,394 / 244 at both ends), so the 175 departures (2022–2023) and any new accounts don't show up here.
- **Tier migration.** `client_tier` is a current attribute in `dim_client`, so a client who moved up a tier is counted in its current tier for every year.
- **Size of the effect.** A 9.9% Retail rate on a $0.45B base is still only $44M, so ratios across tiers with very different bases can mislead without the dollar figures next to them.
- **Why.** It describes the flows but doesn't explain them (marketing, advisor effort, client life stage).
