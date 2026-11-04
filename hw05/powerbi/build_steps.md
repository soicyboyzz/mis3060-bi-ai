# Power BI build steps (Part D)

A click-by-click checklist that builds exactly the model in `star_design.md` Part D. Allow 30–45 minutes.

Data folder: `C:\Users\ajd_d\Documents\Business Intelligence\mis3060-bi-ai\hw05\data`

---

## 0. Turn off auto-detect (saves deleting wrong relationships later)
1. Open **Power BI Desktop** and close the start screen.
2. **File → Options and settings → Options → Current File → Data Load**.
3. Under *Relationships*, **untick** "Import relationships from data sources" and "Autodetect new relationships after data is loaded". Click **OK**.

## 1. Load the eight tables
For **each** of the 8 CSVs:
1. **Home → Get data → Text/CSV**, then pick the file from the data folder.
2. Click **Transform Data**, not Load.

Once all 8 are open in Power Query (they're listed on the left), set the types. Click a column header, then the type icon at the left of the header (**ABC / 123 / 1.2 / calendar**) → choose the type → **Replace current** if asked.

| Table | Whole Number | Date | Decimal Number | Text | True/False |
|---|---|---|---|---|---|
| dim_advisor | advisor_id, years_experience, aum_target_mm | | | (names, region, certifications) | |
| dim_benchmark | benchmark_id | | | (name, asset_class, ticker_proxy) | |
| dim_client | client_id, advisor_id, age | client_since | initial_aum | **zip_code** (check the leading zeros survive, e.g. client 2 = `03897`) | is_active |
| dim_date | date_id, year, quarter, month, week_of_year, is_month_end, is_quarter_end, is_year_end, is_trading_day | **date** | | month_name, day_of_week | |
| dim_security | security_id, benchmark_id | | expense_ratio_bps | ticker, name, asset_class, sector | **is_etf** (its values are True/False, so Whole Number would turn every row into an Error) |
| fact_fees | fee_id, client_id, advisor_id | fee_date | aum_basis, bps_charged, amount | fee_type | |
| fact_portfolio_snapshot | snapshot_id, client_id, advisor_id, benchmark_id, year, month, is_return_suspect | snapshot_date | aum, return_ytd, benchmark_return_ytd, active_alpha_ytd, cash_pct | account_type | |
| fact_transactions | txn_id, client_id, advisor_id, **security_id** (blank on cash rows; keep it Whole Number, blanks become null), is_post_departure_txn | txn_date | shares, price, amount | txn_type | |

Checks before leaving Power Query:
- Dates must be **Date**, not Date/Time (calendar icon with no clock).
- Under **View**, tick **Column quality**. No column should show **Error** above 0%. Empty values are expected only in `security_id`, `shares` and `price` (fact_transactions) and in `sector` and `expense_ratio_bps` (dim_security).

Then **Home → Close & Apply**. Loading takes a minute or two.

## 2. Build the 13 relationships
Open **Model view** (third icon on the left rail). If any relationship lines already exist, right-click each → **Delete**.

For each row below, drag the **From** column onto the **To** column, then double-click the new line and check: **Cardinality = Many to one (\*:1)**, **Cross filter direction = Single**, and **Make this relationship active** as listed.

**Create them in this order.** The fact → dim_advisor links must exist before #13, so Power BI makes #13 inactive.

| # | From (many side) | To (one side) | Active |
|---|---|---|---|
| 1 | fact_transactions[client_id] | dim_client[client_id] | ✔ |
| 2 | fact_transactions[advisor_id] | dim_advisor[advisor_id] | ✔ |
| 3 | fact_transactions[security_id] | dim_security[security_id] | ✔ |
| 4 | fact_transactions[txn_date] | dim_date[**date**] | ✔ |
| 5 | fact_fees[client_id] | dim_client[client_id] | ✔ |
| 6 | fact_fees[advisor_id] | dim_advisor[advisor_id] | ✔ |
| 7 | fact_fees[fee_date] | dim_date[**date**] | ✔ |
| 8 | fact_portfolio_snapshot[client_id] | dim_client[client_id] | ✔ |
| 9 | fact_portfolio_snapshot[advisor_id] | dim_advisor[advisor_id] | ✔ |
| 10 | fact_portfolio_snapshot[benchmark_id] | dim_benchmark[benchmark_id] | ✔ |
| 11 | fact_portfolio_snapshot[snapshot_date] | dim_date[**date**] | ✔ |
| 12 | dim_security[benchmark_id] | dim_benchmark[benchmark_id] | ✔ |
| 13 | dim_client[advisor_id] | dim_advisor[advisor_id] | **✘ inactive (dashed line)** |

- **Don't** link anything to `dim_date[date_id]`, and **don't** link `dim_client[client_since]`.
- If #13 comes up as active, untick "Make this relationship active". If Power BI says a relationship "can't be active because of ambiguous paths", that's expected for #13 only.
- If any relationship says **Many-to-many**, stop: the one-side key isn't unique or a type is wrong. Recheck step 1.

**Layout:** put the three facts in the middle and the five dimensions around them (dim_date on top, dim_client and dim_advisor on the left, dim_security and dim_benchmark on the right) so no lines cross over tables.

## 3. Mark the date table
Click **dim_date** → **Table tools → Mark as date table** → choose **date** → OK. Power BI checks that the column is unique and has no gaps, which it does.

## 4. Check the model (Report view)
1. **Row counts:** add 8 **Card** visuals. Drag each table's primary key in, then click the field's drop-down → **Count** (not Sum). They should read:
   dim_advisor 25 · dim_benchmark 8 · dim_client 2,500 · dim_date 1,827 · dim_security 500 · fact_fees 122,197 · fact_portfolio_snapshot 129,547 · fact_transactions 298,572.
2. **Blank member:** add a **Table** visual with `dim_security[ticker]` and `fact_transactions[amount]`. One `(Blank)` row is expected (the cash rows). No other blank should appear.
3. **Slicer:** add a slicer on `dim_advisor[last_name]`, plus a card for each of `fact_fees[amount]`, `fact_transactions[amount]` and `fact_portfolio_snapshot[aum]`. Picking an advisor should change all three.

You can leave these visuals in the file. Don't add any other DAX.

## 5. Save and screenshot
1. **File → Save as** → `...\mis3060-bi-ai\hw05\powerbi\hw05.pbix`.
2. Go back to **Model view**, fit everything on screen (**View → Fit to page**, or zoom out at the bottom right), and make sure every table and line is visible.
3. Press **Win + Shift + S**, drag around the model, then click the notification → **Save** → `...\hw05\powerbi\model_view.png`.

Tell Claude when both files are saved, and it will check them and push everything to GitHub.
