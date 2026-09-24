import pandas as pd

df = pd.read_csv("data/raw/fact_transactions.csv")

total_rows = len(df)
excluded_types = ["Sell", "Deposit", "Withdrawal", "Dividend", "Advisory Fee"]
excluded_count = df["txn_type"].isin(excluded_types).sum()

remaining = total_rows - excluded_count
print(f"Total rows:                        {total_rows:,}")
print(f"Rows in excluded types:            {excluded_count:,}")
print(f"Remaining rows (total - excluded): {remaining:,}")
