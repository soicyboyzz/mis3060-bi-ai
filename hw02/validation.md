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
