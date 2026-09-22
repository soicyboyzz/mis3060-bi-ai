# HW2 Specification: EDA Script for Wildcat Capital Transactions

**Author:** Aiden James
**Course:** MIS3060 Business Intelligence with AI, Villanova University
**Deliverable requested:** One Python script, saved as `hw02/hw02_eda.py`

## Purpose

I need a single Python script that performs a complete exploratory data analysis (EDA) of Wildcat Capital's transaction history. The goal is to profile the data: understand its shape, confirm it loaded correctly, describe its key distributions and relationships, and surface anything that needs further investigation. This is profiling only. The script must not clean, fix, or change the data in any way.

All 17 steps below must be in one script and must run together, in order, in one execution. Do not split the work into multiple files or helper modules.

## Context

* **Dataset:** `data/raw/fact_transactions.csv`. Each row is one client transaction recorded from January 2020 through December 2024.
* **Transaction types:** Each row's `txn_type` is one of six values: Buy, Sell, Deposit, Withdrawal, Dividend, or Advisory Fee.
* **Key columns:** `txn_id` (transaction identifier), `txn_type`, `txn_date`, `security_id`, `shares`, `price`, and `amount`, plus a client ID column (`client_id`) and an advisor ID column (`advisor_id`).
* **Expected nulls:** Some transaction types (such as deposits and fees) do not involve a security, so `security_id`, `shares`, and `price` are expected to be empty on those rows. The script should report these nulls, not remove or fill them.
* **How it will be run:** From the repository root in the VS Code terminal with the command `python hw02/hw02_eda.py`. All file paths in the script should be written relative to the repository root.
* **Libraries:** Use pandas for the analysis and matplotlib for the charts.

## Required Steps

The script must perform each of the following steps in this order. Before each step's output, print a clear section header with the step number and a short title (for example, "STEP 6: Transaction Type Breakdown") so the terminal output is easy to read.

1. **Load the data.** Read `data/raw/fact_transactions.csv` into a pandas DataFrame. Load it as-is, without converting any column types, parsing dates, or dropping any rows.
2. **Print the shape.** Print the number of rows and the number of columns in the dataset.
3. **Print column names and data types.** List every column name alongside its data type exactly as pandas loaded it. Do not convert any types before reporting them.
4. **Print missing values.** For every column, print how many values are missing (null). Include columns that have zero missing values.
5. **Print descriptive statistics.** For every numeric column, print the count, mean, standard deviation, minimum, 25th percentile, median, 75th percentile, and maximum.
6. **Print transaction type breakdown.** For each value of `txn_type`, print how many rows it has and what percentage of total rows it represents. Sort from most frequent to least frequent and round percentages to 2 decimal places.
7. **Print unique counts.** Print the number of distinct clients (from `client_id`), distinct advisors (from `advisor_id`), and distinct securities (from `security_id`) in the file. Count only non-empty values.
8. **Print the date range.** Print the earliest and latest transaction date in `txn_date`. It is fine to interpret the values as dates to find the earliest and latest, but do not change the `txn_date` column itself in the DataFrame.
9. **Check for duplicate transaction IDs.** Count how many rows have a `txn_id` that already appeared earlier in the file, and print that duplicate count. Check duplicates by `txn_id` only, not by entire rows.
10. **Print amount summary.** Print the mean, median, and skewness of the `amount` column, rounded to 2 decimal places. After the skewness value, print a short note saying whether the distribution is right-skewed, left-skewed, or roughly symmetric.
11. **Print amount by transaction type.** Group the data by `txn_type`. For each type, print the number of transactions, the mean `amount`, and the median `amount`, with the mean and median rounded to 2 decimal places. Sort the results by mean amount, highest to lowest.
12. **Print correlations.** Compute the correlation matrix for `shares`, `price`, and `amount`, rounded to 2 decimal places, and print it. Then list the three strongest correlations among these variables, ranked by strength (absolute value). Exclude each variable's correlation with itself, and count each pair only once (for example, shares–amount and amount–shares are the same pair).
13. **Print negative share analysis.** For each `txn_type`, print the minimum value of `shares`, the maximum value of `shares`, and the number of rows where `shares` is negative. Some transaction types will have no share values at all. The script should handle those without errors and show them clearly as having no share data.
14. **Validate the shape.** If the dataset does not have exactly 298,772 rows and 9 columns, print a clearly visible warning that states the expected shape and the actual shape. If the shape matches, print a short confirmation message instead.
15. **Create and save three charts.** Save all charts to the `hw02/charts/` folder, creating that folder if it does not exist. Save each chart as a PNG file without opening a display window, so the script never pauses waiting for a chart to be closed. Each chart must have a title, labeled axes, and a legend where relevant.
    * Histogram of `amount` with one vertical line at the mean and another at the median. The two lines should be different colors or styles, and the legend should label each one with its value. Save as `hw02/charts/hist_amount.png`.
    * Horizontal box plot of `amount` by `txn_type`, with one box for each transaction type. Save as `hw02/charts/box_amount_by_type.png`.
    * Scatter plot of `shares` (x-axis) versus `amount` (y-axis), with points colored by `txn_type` and a legend showing which color is which type. Because the dataset is large, use small, partly transparent points so overlapping data is still visible. Save as `hw02/charts/scatter_shares_amount.png`.

    After saving, print the file path of each chart.
16. **Save a text profile.** Write a plain-text summary of the results from steps 2 through 13 to `hw02/hw02_profile.txt`. It should contain the same information printed in the terminal for those steps, with the same section headers, formatted so it is readable on its own. After saving, print the file path.
17. **Add a header comment block.** At the very top of the script, include a comment block that identifies:
    * The script name (`hw02_eda.py`)
    * The dataset (`data/raw/fact_transactions.csv`)
    * The author (Aiden James)
    * The date the script was generated
    * A one-sentence description of what the script does

## Constraints

* **One script only.** Everything must be in `hw02/hw02_eda.py`, with no other files required to run it.
* **Do not modify the data.** Do not drop, fill, correct, convert, or filter any rows or columns. Missing values, negative share counts, and other unusual values are findings to report, not problems to fix.
* **Run without interruption.** The script must run from start to finish without errors and without asking for any user input.
* **Readable output.** Numbers should be formatted to be easy to read. Every step's output should appear under its own section header.
* **Brief comments.** Include short comments in the code marking where each of the 17 steps begins, so each step is easy to find.
