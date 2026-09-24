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

**Me:** Pasted the Part 2A instructions and the table of expected values, and asked how to complete it.

**Claude:** Read `hw02/hw02_profile.txt` and the `hw02/charts/` folder, and compared each expected value to the script's output. 17 of 18 rows matched. The only difference was the median amount: the profile showed 41,220.49 vs. the expected 41,220.48.

To investigate, Claude loaded the raw data and inspected the exact median and the two middle values:

```python
import pandas as pd
s = pd.read_csv('data/raw/fact_transactions.csv')['amount'].sort_values().reset_index(drop=True)
n = len(s)
print(n, repr(s.median()), s.iloc[n//2 - 1], s.iloc[n//2])
```

Output:

```
298772 np.float64(41220.485) 41219.9 41221.07
```

**Claude's conclusion:** Because the row count is even, the median is the average of 41,219.90 and 41,221.07, which is exactly 41,220.485. That sits on a half-cent boundary, so the displayed value depends on the rounding method: Python's formatting produced .49, while the answer key shows .48. The median itself is correct, so this is a rounding difference, not an error in the script or the data. The row is marked "No" because the displayed values differ, with this explanation attached.
