# HW02 Part 2A: Known-Answer Benchmarks

Values in "Your Script Produced" come from running `python hw02/hw02_eda.py` from the repository root and reading the terminal output / `hw02/hw02_profile.txt` and the `hw02/charts/` folder.

| Check | Expected | Your Script Produced | Match? | Notes |
|---|---|---|---|---|
| Dataset shape | (298772, 9) | 298,772 rows, 9 columns | Yes | STEP 2; STEP 14 confirmed the expected shape |
| Null count — security_id | 101,597 | 101,597 | Yes | STEP 4; shares and price also have 101,597 nulls (non-security transactions) |
| Null count — amount | 0 | 0 | Yes | STEP 4 |
| Unique txn_type values | 6 | 6 | Yes | STEP 6: Buy, Sell, Dividend, Deposit, Advisory Fee, Withdrawal |
| Count of Buy transactions | 83,556 | 83,556 | Yes | STEP 6; 27.97% of rows |
| txn_date data type | object | object | Yes | STEP 3; loaded as text, not converted |
| Earliest txn_date | 2020-01-01 | 2020-01-01 | Yes | STEP 8 |
| Latest txn_date | 2024-12-30 | 2024-12-30 | Yes | STEP 8 |
| Duplicate txn_id count | 0 | 0 | Yes | STEP 9 |
| Mean amount | $54,075.17 | $54,075.17 | Yes | STEP 10 |
| Median amount | $41,220.48 | $41,220.49 | No | Off by $0.01 — rounding convention difference; see Discrepancies |
| Skewness of amount | 1.15 | 1.15 | Yes | STEP 10; right-skewed |
| Correlation shares–amount | 0.65 | 0.65 | Yes | STEP 12 |
| Correlation price–amount | 0.64 | 0.64 | Yes | STEP 12 |
| Correlation shares–price | 0.00 | 0.00 | Yes | STEP 12 |
| Negative shares count (Buy only) | 836 | 836 | Yes | STEP 13; minimum Buy shares is -499.63 |
| Profile file created | Yes | Yes | Yes | `hw02/hw02_profile.txt` |
| Chart files created (3) | Yes | Yes | Yes | `hist_amount.png`, `box_amount_by_type.png`, `scatter_shares_amount.png` in `hw02/charts/` |

## Discrepancies

### Median amount (expected $41,220.48, script produced $41,220.49)

The dataset has an even number of rows (298,772), so the median is the average of the two middle values after sorting:

(41,219.90 + 41,221.07) / 2 = **41,220.485**

That value falls exactly halfway between two cents. The script formats it with Python's `:,.2f`, which rounded it to .49, while the answer key rounded it down to .48. The underlying median is the same in both cases; this is a rounding convention difference, not a data or calculation error. No change to the script is needed.

## Claude Cowork Investigation (Median Discrepancy)

Verbatim transcript of the Claude Cowork conversation used to investigate the median discrepancy.

---

**AJ:**

~~~text
2A — Known-Answer Benchmarks (8 points)
Complete this table in hw02/validation.md. Every row must be filled in.

Check	Expected	Your Script Produced	Match?	Notes
Dataset shape	(298772, 9)			
Null count — security_id	101,597			
Null count — amount	0			
Unique txn_type values	6			
Count of Buy transactions	83,556			
txn_date data type	object			
Earliest txn_date	2020-01-01			
Latest txn_date	2024-12-30			
Duplicate txn_id count	0			
Mean amount	$54,075.17			
Median amount	$41,220.48			
Skewness of amount	1.15			
Correlation shares–amount	0.65			
Correlation price–amount	0.64			
Correlation shares–price	0.00			
Negative shares count (Buy only)	836			
Profile file created	Yes			
Chart files created (3)	Yes			
For any row where Match = No: describe the discrepancy and paste the Claude Cowork conversation you used to investigate it. : these are the part 2a instructions
~~~

**Claude** *(tool steps: read `hw02/hw02_profile.txt`, listed `hw02/charts/`, then ran this check on the raw data)*:

~~~python
import pandas as pd
s = pd.read_csv('data/raw/fact_transactions.csv')['amount'].sort_values().reset_index(drop=True)
n = len(s); print(n, repr(s.median()), s.iloc[n//2-1], s.iloc[n//2])
~~~

Output:

~~~text
298772 np.float64(41220.485) 41219.9 41221.07
~~~

**Claude:**

> Your script's output matches the expected values on **17 of 18 rows**. The only mismatch is the median amount, and it's a half-cent rounding difference, not a bug.
>
> ### Step 1: Run the script (done)
>
> You've already run `python hw02/hw02_eda.py`. It created `hw02/hw02_profile.txt` and three charts in `hw02/charts/`.
>
> ### Step 2: Find each value in your output
>
> Every row can be filled in from `hw02_profile.txt` or the charts folder:
>
> | Check | Where to find it |
> |---|---|
> | Shape | STEP 2 |
> | Nulls in `security_id` and `amount` | STEP 4 |
> | Unique `txn_type` values and Buy count | STEP 6 (count the rows; Buy is the top row) |
> | `txn_date` data type | STEP 3 |
> | Earliest and latest date | STEP 8 |
> | Duplicate `txn_id` | STEP 9 |
> | Mean, median and skewness | STEP 10 |
> | Correlations | STEP 12 |
> | Negative shares for Buy | STEP 13 ("Negative Rows" column) |
> | Profile and chart files | `hw02/` and `hw02/charts/` in the VS Code file explorer |
>
> ### Step 3: Create `hw02/validation.md` and fill in the table
>
> Here's the completed table using your script's actual output: *(the table as it appears at the top of this file, with the median row marked "No", followed by this explanation:)*
>
> **Median amount (expected $41,220.48, script produced 41,220.49)**
>
> The dataset has an even number of rows (298,772), so the median is the average of the two middle values: (41,219.90 + 41,221.07) / 2 = 41,220.485. That value is exactly halfway between two cents. Python's rounding turned it into .49, while the answer key rounded it down to .48. The underlying median is identical; this is a rounding convention difference, not a data or calculation error.
>
> ### Step 4: Paste the investigation conversation
>
> For the median row, the assignment wants the Cowork conversation you used to investigate it. This one works: I checked the raw data and got an exact median of **41,220.485** from the two middle values **41,219.90** and **41,221.07**. Copy that exchange, from your Part 2a question through this answer, under the Discrepancies section.
>
> I marked the median row "No" because the numbers as shown do differ by a cent, and saying so is safer for grading. If your instructor treats rounding differences as matches, you could mark it "Yes" and keep the note.
>
> I haven't created `validation.md` in your folder. I can save it there if you'd like.

---

# HW02 Part 2B: Explain the Code and Output

Both prompts were sent in a new Claude Cowork session, not the one that generated the script. My first attempt at Prompt 1 had my project folder connected, and that session ran the script itself instead of predicting the output from the code. I started over in a new session with no folder connected so the predictions came from the code alone. The answers below use that second session.

### 1. Did Claude's predicted outputs (from Prompt 1) match what I actually saw in the terminal?

Mostly yes, on structure. With no access to the data, Claude described the exact format of every section (the step banners, table layouts, the "no share data" rows in Step 13, the `OK: Shape matches...` message in Step 14, the three `Saved chart:` lines, `Saved text profile:` and `EDA complete.`) and marked the actual numbers as data-dependent. Every format it predicted appeared in my terminal. It also correctly pointed out that the "top 3 correlations" are simply all three possible pairs, and that `duplicated()` counts repeat rows, not groups.

Discrepancies:

- **Number of transaction types:** Its summary said the tables in Steps 6, 11 and 13 would have "3 transaction types' worth of rows." The terminal shows 6 types (Buy, Sell, Dividend, Deposit, Advisory Fee, Withdrawal).
- **Step 1 banner:** It first said Step 1 prints no banner, then corrected itself in the same sentence. The banner does print; it just isn't saved to the profile.
- **Profile contents:** It said steps 1, 14 and 15 are left out of `hw02_profile.txt`. Step 16 is also left out.
- **Step 5 columns:** It said the ID columns would "possibly" appear in the statistics table. They all do (`txn_id`, `client_id`, `advisor_id`, `security_id`), because they are numeric.
- **Missed warning:** It did not predict the `MatplotlibDeprecationWarning` about the `labels` parameter of `boxplot()` that prints at the top of my terminal output.
- **No explicit values:** The prompt asked it to list each expected value explicitly, but without the data it could not predict actual numbers (row counts, means, correlations, dates), so those could not be checked against the terminal.

### 2. What did Claude flag as potentially unexpected or worth investigating (from Prompt 2)?

1. **Negative shares on 836 Buy transactions** (its top concern). Sells are all positive, so the data is not using a "negative = sell" convention; the negative Buys could be data-entry errors, unhandled cancellations/corrections, or an unlabeled sub-type such as reversals.
2. **Advisory Fee skew.** The mean fee ($7,375.17) is about 8.5 times the median ($859.12), much more skewed than any other type. This could be a few very large fees, different fee schedules mixed together, or a units/decimal error.
3. **Gaps in `client_id`.** The highest ID is 3,192, but only 2,700 distinct clients appear, so about 492 IDs never show up. This matters if the data will be joined to a client master table.
4. **`txn_id` is a gapless 1 to 298,772 sequence.** This suggests the ID was assigned at export rather than being the source system's real transaction key.

When I checked its explanations against the data, one was wrong: it said the correlations of `shares` and `price` with `amount` (0.65 and 0.64) are "diluted" by deposits, withdrawals and fees. Those rows have no shares or price, so pandas `.corr()` leaves them out. For every Buy, Sell and Dividend row, `amount` is exactly |shares × price|; the correlations are below 1.0 because amount is the product of two independent variables, not a linear function of either one.

It also missed two things worth flagging:

- The 836 negative-share Buys still have positive amounts ($88.80 to $239,631.51), so the sign of shares and the sign of amount disagree on those rows.
- Every Dividend's amount equals shares × price, which is the full market value of the position rather than a realistic dividend payment.

### 3. Did Claude mention the 101,597 null values in `security_id`? What explanation did it give?

Yes. Claude noted that `security_id`, `shares` and `price` are each missing in exactly 101,597 rows (34%) while every other column is complete. It explained that this matches three cash-only transaction types: Advisory Fee (35,766) + Deposit (35,981) + Withdrawal (29,850) = 101,597. Because those transactions do not involve a security, the nulls are a structural pattern rather than a data-quality defect. It also noted this is why the Step 5 count for those columns is 197,175 (298,772 − 101,597), and recommended confirming the business logic before dropping or filling anything in those columns.

### 4. Did Claude flag the `txn_date` column as a concern? Why would that matter for a time-series analysis?

No. Claude only noted that `txn_date` is `object` (text) because the script deliberately did not parse it, and it described the five-year date range without treating the string type as a risk.

It matters for time-series analysis because a string is not a date:

- **No date math.** You cannot subtract dates to get days between transactions, add time periods, or measure gaps.
- **No time grouping.** Grouping or resampling by month, quarter or year does not work until the column is converted with `pd.to_datetime()`.
- **Sorting depends on the format.** Min/max and sorting only work because these strings happen to be in `YYYY-MM-DD` format; a format like `MM/DD/YYYY` would sort in the wrong order.
- **Bad dates stay hidden.** Invalid values (typos, impossible dates) stay hidden as text until the column is converted.

### 5. Do the three charts match Claude's explanation of that section of the output?

- **`hist_amount.png`:** Matches. There is a dashed red mean line (54,075.17) and a solid orange median line (41,220.49), both labeled in the legend, and the long right tail confirms the right skew. Two features Claude did not mention: a very tall first bar near $0 (over 30,000 transactions, mostly small advisory fees) and a sudden drop in the bars at $100,000.
- **`box_amount_by_type.png`:** Mostly matches: one horizontal box per type, with small, semi-transparent outlier markers. Differences:
  - **Box order:** Claude said the boxes would be ordered "highest mean amount first." Dividend is first in the data, but matplotlib draws the first box at the bottom, so visually Dividend is at the bottom and Advisory Fee is at the top.
  - **Deposit and Withdrawal ceiling:** Both stop at exactly $100,000 with no outliers, which explains the drop in the histogram.
  - **Advisory Fee tail:** Advisory Fee has a very small box but a long line of outliers reaching about $143,000, which visually supports Claude's fee-skew flag.
- **`scatter_shares_amount.png`:** Matches the description: shares on the x-axis, amount on the y-axis, small semi-transparent points colored by Buy, Dividend and Sell, with a legend, and no points for the three cash types. Differences:
  - **Wedge, not a line:** Claude said it should "visually show the 0.65 correlation." The chart is actually a wedge (fan) shape rather than a linear cloud, because amount = shares × price with prices from $10 to $500.
  - **Negative Buys:** They form a mirror-image triangle on the left side with positive amounts, which makes the sign problem obvious.
  - **Hidden points:** Sell points are drawn last and cover most of the Buy and Dividend points on the right side.

### 6. One follow-up question I asked Claude, and Claude's answer

**My question:**

> You said the shares–amount and price–amount correlations are diluted by the cash transactions (fees, deposits, withdrawals). But those rows have no shares or price values. Doesn't pandas .corr() skip rows with missing values? If so, why are the correlations only 0.65 and 0.64 instead of close to 1.0?

**Claude's answer:**

> Good catch — I got that explanation wrong. Pandas `.corr()` does skip missing values, but it does pairwise deletion, not listwise deletion across the whole subset. For each pair of columns, it uses whatever rows have non-null values in that specific pair — it doesn't require all three columns (`shares`, `price`, `amount`) to be non-null simultaneously before including a row anywhere.
>
> In this dataset that distinction turns out not to matter, because of how the nulls line up: `shares` and `price` are null on exactly the same 101,597 rows (the Advisory Fee/Deposit/Withdrawal rows), and `amount` has zero nulls anywhere. So every one of the three pairwise correlations — shares–price, shares–amount, price–amount — ends up computed over the same 197,175 rows (the security-related transactions) regardless of pairwise vs. listwise logic. The cash-only rows are excluded from all three calculations, but they were never mixed in to begin with, so there's no dilution effect from them at all. My earlier explanation was wrong on that point.
>
> The real reason shares–amount and price–amount land at 0.65/0.64 instead of near 1.0 is mathematical, not a missing-data artifact. If `amount` is roughly `shares × price` for these trades, and `shares` and `price` are close to independent of each other (which the 0.00 shares–price correlation confirms), then a product of two independent variables is only moderately correlated with either factor alone — not close to 1 — even when the relationship is perfectly deterministic. Intuitively: `amount` swings for two separate reasons (shares moving, or price moving), so knowing just `shares` only explains part of `amount`'s variance; the unexplained part comes from `price` varying independently, and vice versa. A quick way to see this yourself: compute `df["shares"] * df["price"]` and compare it directly to `df["amount"]` for the security-related rows — if that reconstructed value doesn't line up closely, `amount` isn't a clean product of the two and something else (fees, rounding, a different formula) is driving it instead.
>
> One more thing that could be pulling the shares–amount correlation down specifically: the 836 negative-share Buy rows I flagged earlier. If `amount` stays positive on those rows while `shares` goes negative, that breaks the simple proportional relationship for those rows and would weaken (not strengthen) the shares–amount correlation. Worth checking those rows' `amount` sign as part of investigating that anomaly — it'd also help explain part of this correlation question.

**My check:** I confirmed Claude's suggestion in the data: for all 197,175 Buy, Sell and Dividend rows, `amount` equals |shares × price| exactly, and the 836 negative-share Buys all have positive amounts.

---

# HW02 Part 2C: Business Check & Cross-Validation

### 1. Which three transaction types would have no security, and do the counts add up to 101,597?

Advisory Fee, Deposit, and Withdrawal are the three types that don't have a security. None of them involve buying or selling an actual holding, so they don't need a security_id, shares, or price. Their counts are 35,766 + 35,981 + 29,850, which equals 101,597. That matches the null count from Part 2A exactly, so yes, it adds up.

### 2. What does it mean to have significantly more Buys (83,556) than Sells (59,755) over five years?

Having way more Buys than Sells over five years probably means the firm's assets are growing instead of staying flat. If people are buying more than they're selling, that means new money is coming in and getting invested, clients are reinvesting dividends, and advisors are building up positions instead of trading in and out a lot. It's not necessarily a bad sign, it's just what you'd expect if the client base is still in a growth phase. It would be a good idea to check the total dollar amount of Buys versus Sells by year to make sure this is really about growth and not just that Buy trades happen more often but are smaller.

### 3. What would go wrong computing average days between transactions if `txn_date` stayed a string?

If txn_date stayed a string, you wouldn't be able to subtract one date from another to find the number of days between transactions. Pandas would either throw an error since you can't subtract text, or it just wouldn't give a real answer. Sorting the dates would also only work by accident, since it depends on every date being written the exact same way. And any date that was typed wrong or doesn't make sense would just look like normal text instead of showing up as an error. You would need to convert the column with pd.to_datetime() first so it actually works like a real date.

### 4. Is 2,700 clients / 25 advisors (about 108 per advisor) plausible for an RIA?

It seems plausible. According to SmartAsset, the median is about 73 clients per advisor, and a comfortable range is usually around 50 to 150 clients, so 108 clients per advisor fits inside that range, just on the higher end of it.

Source: SmartAsset, "Average Number of Clients Per Financial Advisor" — https://smartasset.com/advisor-resources/average-number-of-clients-per-financial-advisor

### 5. Two plausible explanations for negative shares on 836 Buy transactions, and what I'd do next

Two possible reasons for the negative shares: one, it could just be a mistake where someone typed the shares as negative when they weren't supposed to. Two, it could be some kind of correction or reversal, like a canceled or returned purchase, that the system is recording as a negative Buy instead of giving it its own category. Since the amount for these rows is still positive, that means the shares sign doesn't match the amount sign, so it's probably not just a simple "negative means sell" rule. If I were investigating this, I would look at whether these transactions are grouped around certain advisors or certain dates, which would point to a bigger issue, or if they look random, which would suggest it's just individual mistakes. I would also want to ask whoever manages the source system what a negative share Buy is even supposed to mean.

### 6. What did each script return?

- Approach A (`hw02/count_buy_a.py`, direct filter): `Rows where txn_type == 'Buy': 83,556`
- Approach B (`hw02/count_buy_b.py`, total minus other types): `Total rows: 298,772`, `Rows in excluded types: 215,216`, `Remaining rows (total - excluded): 83,556`

### 7. Do the results agree? If not, which one is wrong and why?

Yes, they agree. Both scripts end up with 83,556 Buy transactions. Approach A counts them directly, and Approach B gets the same number by subtracting all the other transaction types from the total. Since the two methods don't depend on each other, getting the same answer both times means neither one is wrong.

### 8. Why is it useful to verify a count using subtraction rather than direct filtering?

Verifying with subtraction is useful because it checks the number using a totally different method than the direct filter. This can catch mistakes that a direct filter alone might miss, like a typo in the text being matched, a filter that accidentally returns zero results, or getting the number of transaction types wrong. If both methods are built separately and still land on the same number, that's a good sign the count is actually correct and not just the same mistake showing up twice.
