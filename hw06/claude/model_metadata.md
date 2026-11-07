# Model metadata (Part D, step 1)

Exported from the open `powerbi/hw06.pbix` (after adding `_Measures` and marking `dim_date`) with the three INFO.VIEW queries from `powerbi_dax_guide.md` §2. The results are pasted below unchanged, apart from Markdown table formatting. These are the exact tables given to Claude in `dax_session.md`.

What the metadata **cannot** say, which was added to the prompt by hand:
- **Grain** of `fact_portfolio_snapshot`: one row per client per month, dated the **1st** of the month.
- `aum` is a **balance** (semi-additive). `active_alpha_ytd` is **year-to-date** and non-additive. `is_return_suspect = 1` marks impossible returns kept from HW4.
- The relationships include one auto date/time table (`LocalDateTable_…`) on `dim_client[client_since]`. It is unused by any measure.
- `INFO.VIEW.COLUMNS` prints a few `dim_date` and `fact_portfolio_snapshot` names capitalized (`Date`, `Year`, `Month`, `Quarter`), while the relationships and TOM call them `date`, `year`, `month`, `quarter`. DAX names are case-insensitive, so both forms work in a formula.
- Exported after the measures were built. The `Top 10 Client Share` row was **removed** from what Claude was shown (see `dax_session.md`), so it could not copy the answer.

## Columns

```DAX
EVALUATE
SELECTCOLUMNS (
    FILTER ( INFO.VIEW.COLUMNS (), [DataCategory] <> "RowNumber" ),
    [Table], "Column", [Name], [DataType], "DAX formula", [Expression], [IsHidden]
)
ORDER BY [Table]
```

| Table | Column | DataType | DAX formula | IsHidden |
|---|---|---|---|---|
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | Date | Date |  | True |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | Day | Integer | DAY([Date]) | True |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | Quarter | Text | "Qtr " & [QuarterNo] | True |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | QuarterNo | Integer | INT(([MonthNo] + 2) / 3) | True |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | Month | Text | FORMAT([Date], "MMMM") | True |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | MonthNo | Integer | MONTH([Date]) | True |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | Year | Integer | YEAR([Date]) | True |
| dim_advisor | years_experience | Integer |  | False |
| dim_advisor | certifications | Text |  | False |
| dim_advisor | advisor_id | Integer |  | False |
| dim_advisor | first_name | Text |  | False |
| dim_advisor | last_name | Text |  | False |
| dim_advisor | region | Text |  | False |
| dim_advisor | aum_target_mm | Integer |  | False |
| dim_benchmark | ticker_proxy | Text |  | False |
| dim_benchmark | asset_class | Text |  | False |
| dim_benchmark | name | Text |  | False |
| dim_benchmark | benchmark_id | Integer |  | False |
| dim_client | client_since | Date |  | False |
| dim_client | first_name | Text |  | False |
| dim_client | primary_account_type | Text |  | False |
| dim_client | client_tier | Text |  | False |
| dim_client | risk_profile | Text |  | False |
| dim_client | zip_code | Text |  | False |
| dim_client | state | Text |  | False |
| dim_client | city | Text |  | False |
| dim_client | age | Integer |  | False |
| dim_client | last_name | Text |  | False |
| dim_client | initial_aum | Number |  | False |
| dim_client | client_id | Integer |  | False |
| dim_client | is_active | True/False |  | False |
| dim_client | advisor_id | Integer |  | False |
| dim_date | is_quarter_end | Integer |  | False |
| dim_date | is_year_end | Integer |  | False |
| dim_date | is_trading_day | Integer |  | False |
| dim_date | Year | Integer |  | False |
| dim_date | Date | Date |  | False |
| dim_date | date_id | Integer |  | False |
| dim_date | Month | Integer |  | False |
| dim_date | Quarter | Integer |  | False |
| dim_date | month_name | Text |  | False |
| dim_date | week_of_year | Integer |  | False |
| dim_date | day_of_week | Text |  | False |
| dim_date | is_month_end | Integer |  | False |
| dim_security | expense_ratio_bps | Integer |  | False |
| dim_security | security_id | Integer |  | False |
| dim_security | ticker | Text |  | False |
| dim_security | name | Text |  | False |
| dim_security | asset_class | Text |  | False |
| dim_security | sector | Text |  | False |
| dim_security | benchmark_id | Integer |  | False |
| dim_security | is_etf | True/False |  | False |
| fact_fees | client_id | Integer |  | False |
| fact_fees | amount | Number |  | False |
| fact_fees | bps_charged | Number |  | False |
| fact_fees | aum_basis | Number |  | False |
| fact_fees | fee_type | Text |  | False |
| fact_fees | fee_date | Date |  | False |
| fact_fees | advisor_id | Integer |  | False |
| fact_fees | fee_id | Integer |  | False |
| fact_portfolio_snapshot | aum | Number |  | False |
| fact_portfolio_snapshot | Year | Integer |  | False |
| fact_portfolio_snapshot | snapshot_date | Date |  | False |
| fact_portfolio_snapshot | benchmark_id | Integer |  | False |
| fact_portfolio_snapshot | advisor_id | Integer |  | False |
| fact_portfolio_snapshot | client_id | Integer |  | False |
| fact_portfolio_snapshot | snapshot_id | Integer |  | False |
| fact_portfolio_snapshot | is_return_suspect | Integer |  | False |
| fact_portfolio_snapshot | account_type | Text |  | False |
| fact_portfolio_snapshot | cash_pct | Number |  | False |
| fact_portfolio_snapshot | active_alpha_ytd | Number |  | False |
| fact_portfolio_snapshot | benchmark_return_ytd | Number |  | False |
| fact_portfolio_snapshot | return_ytd | Number |  | False |
| fact_portfolio_snapshot | Month | Integer |  | False |
| fact_transactions | txn_id | Integer |  | False |
| fact_transactions | amount | Number |  | False |
| fact_transactions | price | Number |  | False |
| fact_transactions | shares | Number |  | False |
| fact_transactions | txn_type | Text |  | False |
| fact_transactions | txn_date | Date |  | False |
| fact_transactions | security_id | Integer |  | False |
| fact_transactions | advisor_id | Integer |  | False |
| fact_transactions | client_id | Integer |  | False |
| fact_transactions | is_post_departure_txn | Integer |  | False |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | Month | Text | FORMAT([Date], "MMMM") | True |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | QuarterNo | Integer | INT(([MonthNo] + 2) / 3) | True |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | Quarter | Text | "Qtr " & [QuarterNo] | True |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | Day | Integer | DAY([Date]) | True |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | Date | Date |  | True |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | Year | Integer | YEAR([Date]) | True |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | MonthNo | Integer | MONTH([Date]) | True |

_91 rows._

## Relationships

```DAX
EVALUATE INFO.VIEW.RELATIONSHIPS ()
```

| ID | Name | Relationship | Model | IsActive | CrossFilteringBehavior | RelyOnReferentialIntegrity | FromTable | FromColumn | FromCardinality | ToTable | ToColumn | ToCardinality | State | SecurityFilteringBehavior |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2450 | AutoDetected_47d2c78f-3915-4351-b30d-fc5f654a65f4 | 'fact_transactions'[advisor_id] *[<-]1 'dim_advisor'[advisor_id] | 865eb9c8-67ee-43be-a8df-155b4bc0bbdb | True | OneDirection | False | fact_transactions | advisor_id | Many | dim_advisor | advisor_id | One | Ready | Single |
| 3424 | AutoDetected_080dc0c9-a847-4102-8fe6-5527ad4e80b2 | 'fact_transactions'[client_id] *[<-]1 'dim_client'[client_id] | 865eb9c8-67ee-43be-a8df-155b4bc0bbdb | True | OneDirection | False | fact_transactions | client_id | Many | dim_client | client_id | One | Ready | Single |
| 4453 | AutoDetected_2f815d05-ddf4-42b9-bf11-303f56a168d6 | 'fact_transactions'[security_id] *[<-]1 'dim_security'[security_id] | 865eb9c8-67ee-43be-a8df-155b4bc0bbdb | True | OneDirection | False | fact_transactions | security_id | Many | dim_security | security_id | One | Ready | Single |
| 4712 | 6deec966-5197-f019-8717-87cd3326e62d | 'fact_transactions'[txn_date] *[<-]1 'dim_date'[date] | 865eb9c8-67ee-43be-a8df-155b4bc0bbdb | True | OneDirection | False | fact_transactions | txn_date | Many | dim_date | date | One | Ready | Single |
| 2451 | AutoDetected_515f758c-a4c4-4e3e-8414-fe1239270ac5 | 'fact_portfolio_snapshot'[advisor_id] *[<-]1 'dim_advisor'[advisor_id] | 865eb9c8-67ee-43be-a8df-155b4bc0bbdb | True | OneDirection | False | fact_portfolio_snapshot | advisor_id | Many | dim_advisor | advisor_id | One | Ready | Single |
| 2639 | AutoDetected_27290db9-48a2-4230-a18e-ac5fca16ab64 | 'fact_portfolio_snapshot'[benchmark_id] *[<-]1 'dim_benchmark'[benchmark_id] | 865eb9c8-67ee-43be-a8df-155b4bc0bbdb | True | OneDirection | False | fact_portfolio_snapshot | benchmark_id | Many | dim_benchmark | benchmark_id | One | Ready | Single |
| 3425 | AutoDetected_8da07bbb-379a-44b4-8620-2cb9df480b79 | 'fact_portfolio_snapshot'[client_id] *[<-]1 'dim_client'[client_id] | 865eb9c8-67ee-43be-a8df-155b4bc0bbdb | True | OneDirection | False | fact_portfolio_snapshot | client_id | Many | dim_client | client_id | One | Ready | Single |
| 4695 | aa81e5e4-13d7-2473-c80b-1050d4fb268e | 'fact_portfolio_snapshot'[snapshot_date] *[<-]1 'dim_date'[date] | 865eb9c8-67ee-43be-a8df-155b4bc0bbdb | True | OneDirection | False | fact_portfolio_snapshot | snapshot_date | Many | dim_date | date | One | Ready | Single |
| 2452 | AutoDetected_13cb45f8-9f1d-42c6-9326-a4402ef86ceb | 'fact_fees'[advisor_id] *[<-]1 'dim_advisor'[advisor_id] | 865eb9c8-67ee-43be-a8df-155b4bc0bbdb | True | OneDirection | False | fact_fees | advisor_id | Many | dim_advisor | advisor_id | One | Ready | Single |
| 3426 | AutoDetected_6b7ee019-ebcc-4ab0-a5f6-23016186f549 | 'fact_fees'[client_id] *[<-]1 'dim_client'[client_id] | 865eb9c8-67ee-43be-a8df-155b4bc0bbdb | True | OneDirection | False | fact_fees | client_id | Many | dim_client | client_id | One | Ready | Single |
| 4678 | fbd94a81-c893-0c31-c79a-9a0f84f664a0 | 'fact_fees'[fee_date] *[<-]1 'dim_date'[date] | 865eb9c8-67ee-43be-a8df-155b4bc0bbdb | True | OneDirection | False | fact_fees | fee_date | Many | dim_date | date | One | Ready | Single |
| 2662 | 371030ed-f05a-47f6-a233-06998810b983 | 'dim_client'[client_since] *[<-]1 'LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8'[Date] | 865eb9c8-67ee-43be-a8df-155b4bc0bbdb | True | OneDirection | False | dim_client | client_since | Many | LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | date | One | Ready | Single |
| 4454 | AutoDetected_031cb484-3962-4004-9c23-08d705a8563e | 'dim_security'[benchmark_id] *[<-]1 'dim_benchmark'[benchmark_id] | 865eb9c8-67ee-43be-a8df-155b4bc0bbdb | True | OneDirection | False | dim_security | benchmark_id | Many | dim_benchmark | benchmark_id | One | Ready | Single |

_13 rows._

## Measures

```DAX
EVALUATE
SELECTCOLUMNS (
    INFO.VIEW.MEASURES (),
    [Table], "Measure", [Name], "DAX formula", [Expression], [FormatString], [State]
)
```

| Table | Measure | DAX formula | FormatString | State |
|---|---|---|---|---|
| _Measures | Total Fees | SUM ( fact_fees[amount] ) |  | Valid |
| _Measures | Net Flows | CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Deposit" )<br>    - CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Withdrawal" ) |  | Valid |
| _Measures | Effective Fee Rate (bps) | DIVIDE ( SUM ( fact_fees[amount] ) * 12 * 10000, SUM ( fact_fees[aum_basis] ) ) |  | Valid |
| _Measures | AUM (naive SUM) | SUM ( fact_portfolio_snapshot[aum] ) |  | Valid |
| _Measures | Ending AUM | CALCULATE (<br>    SUM ( fact_portfolio_snapshot[aum] ),<br>    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )<br>) |  | Valid |
| _Measures | Ending Clients | CALCULATE (<br>    DISTINCTCOUNT ( fact_portfolio_snapshot[client_id] ),<br>    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )<br>) |  | Valid |
| _Measures | Avg AUM per Client | DIVIDE ( [Ending AUM], [Ending Clients] ) |  | Valid |
| _Measures | Ending AUM LY | CALCULATE ( [Ending AUM], SAMEPERIODLASTYEAR ( dim_date[date] ) ) |  | Valid |
| _Measures | AUM YoY % | DIVIDE ( [Ending AUM] - [Ending AUM LY], [Ending AUM LY] ) |  | Valid |
| _Measures | Ending AUM PM | CALCULATE ( [Ending AUM], DATEADD ( dim_date[date], -1, MONTH ) ) |  | Valid |
| _Measures | AUM MoM % | DIVIDE ( [Ending AUM] - [Ending AUM PM], [Ending AUM PM] ) |  | Valid |
| _Measures | Avg Monthly AUM | DIVIDE (<br>    SUM ( fact_portfolio_snapshot[aum] ),<br>    DISTINCTCOUNT ( fact_portfolio_snapshot[snapshot_date] )<br>) |  | Valid |
| _Measures | Fee Yield (bps) | DIVIDE ( [Total Fees] * 12 * 10000, SUM ( fact_portfolio_snapshot[aum] ) ) |  | Valid |
| _Measures | Organic Growth Rate | DIVIDE ( [Net Flows], [Ending AUM LY] ) |  | Valid |
| _Measures | AUM-Weighted Alpha | VAR LastSnapshot =<br>    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )<br>RETURN<br>    CALCULATE (<br>        DIVIDE (<br>            SUMX ( fact_portfolio_snapshot, fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd] ),<br>            SUM ( fact_portfolio_snapshot[aum] )<br>        ),<br>        LastSnapshot,<br>        fact_portfolio_snapshot[is_return_suspect] = 0<br>    ) |  | Valid |
| _Measures | Alpha Signal | VAR Alpha = [AUM-Weighted Alpha]<br>RETURN<br>    SWITCH (<br>        TRUE (),<br>        ISBLANK ( Alpha ), BLANK (),<br>        Alpha >= 0.02, "Outperforming",<br>        Alpha <= -0.02, "Lagging",<br>        "In line"<br>    ) |  | Valid |
| _Measures | Top 10 Client Share | VAR LastSnapshot =<br>    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )<br>VAR ClientBalances =<br>    ADDCOLUMNS (<br>        VALUES ( dim_client[client_id] ),<br>        "@aum", CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), LastSnapshot )<br>    )<br>VAR Top10 = TOPN ( 10, ClientBalances, [@aum], DESC )<br>RETURN<br>    DIVIDE ( SUMX ( Top10, [@aum] ), [Ending AUM] ) |  | Valid |

_17 rows._


