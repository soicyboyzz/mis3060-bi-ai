# =============================================================================
# STEP 17: Header comment block
# Script:      hw02_eda.py
# Dataset:     data/raw/fact_transactions.csv
# Author:      Aiden James
# Generated:   2026-09-23
# Description: Profiles Wildcat Capital's transaction history (shape, types,
#              missing values, distributions, correlations, and data-quality
#              flags) and saves three charts and a text profile, without
#              modifying the data.
# Run from the repository root:  python hw02/hw02_eda.py
# =============================================================================

import os

import matplotlib
matplotlib.use("Agg")  # save charts to file only; never open a display window
import matplotlib.pyplot as plt
import pandas as pd

DATA_PATH = "data/raw/fact_transactions.csv"
CHART_DIR = "hw02/charts"
PROFILE_PATH = "hw02/hw02_profile.txt"
EXPECTED_ROWS = 298_772
EXPECTED_COLS = 9

# Output from steps 2-13 is collected here so it can be written to the text profile in step 16.
profile_lines = []


def header(step, title, record=True):
    """Print a section header (and optionally record it for the profile)."""
    text = f"\n{'=' * 70}\nSTEP {step}: {title}\n{'=' * 70}"
    print(text)
    if record:
        profile_lines.append(text)


def out(text="", record=True):
    """Print a line of output (and optionally record it for the profile)."""
    text = str(text)
    print(text)
    if record:
        profile_lines.append(text)


# -----------------------------------------------------------------------------
# STEP 1: Load the data (as-is: no type conversion, no date parsing, no drops)
# -----------------------------------------------------------------------------
header(1, "Load the Data", record=False)
df = pd.read_csv(DATA_PATH)
out(f"Loaded {DATA_PATH}", record=False)

# -----------------------------------------------------------------------------
# STEP 2: Print the shape
# -----------------------------------------------------------------------------
header(2, "Dataset Shape")
n_rows, n_cols = df.shape
out(f"Rows:    {n_rows:,}")
out(f"Columns: {n_cols:,}")

# -----------------------------------------------------------------------------
# STEP 3: Print column names and data types (exactly as loaded)
# -----------------------------------------------------------------------------
header(3, "Column Names and Data Types")
out(f"{'Column':<15}{'Data Type':<12}")
out("-" * 27)
for col, dtype in df.dtypes.items():
    out(f"{col:<15}{str(dtype):<12}")

# -----------------------------------------------------------------------------
# STEP 4: Print missing values (every column, including zero-null columns)
# -----------------------------------------------------------------------------
header(4, "Missing Values by Column")
out(f"{'Column':<15}{'Missing':>12}{'% of Rows':>12}")
out("-" * 39)
for col, n_missing in df.isna().sum().items():
    pct = n_missing / n_rows * 100 if n_rows else 0
    out(f"{col:<15}{n_missing:>12,}{pct:>11.2f}%")

# -----------------------------------------------------------------------------
# STEP 5: Print descriptive statistics for every numeric column
# -----------------------------------------------------------------------------
header(5, "Descriptive Statistics (Numeric Columns)")
desc = df.describe()  # count, mean, std, min, 25%, 50% (median), 75%, max
desc = desc.rename(index={"50%": "50% (median)"})
with pd.option_context("display.float_format", "{:,.2f}".format,
                       "display.width", 200, "display.max_columns", None):
    out(desc.to_string())

# -----------------------------------------------------------------------------
# STEP 6: Print transaction type breakdown (count and % of rows)
# -----------------------------------------------------------------------------
header(6, "Transaction Type Breakdown")
type_counts = df["txn_type"].value_counts()  # sorted most to least frequent
out(f"{'txn_type':<15}{'Rows':>12}{'% of Total':>13}")
out("-" * 40)
for txn_type, count in type_counts.items():
    pct = round(count / n_rows * 100, 2)
    out(f"{str(txn_type):<15}{count:>12,}{pct:>12.2f}%")
out("-" * 40)
out(f"{'Total':<15}{type_counts.sum():>12,}")

# -----------------------------------------------------------------------------
# STEP 7: Print unique counts (non-empty values only)
# -----------------------------------------------------------------------------
header(7, "Unique Counts")
out(f"Distinct clients (client_id):     {df['client_id'].nunique(dropna=True):,}")
out(f"Distinct advisors (advisor_id):   {df['advisor_id'].nunique(dropna=True):,}")
out(f"Distinct securities (security_id): {df['security_id'].nunique(dropna=True):,}")

# -----------------------------------------------------------------------------
# STEP 8: Print the date range (parsed into a separate Series; df is untouched)
# -----------------------------------------------------------------------------
header(8, "Transaction Date Range")
parsed_dates = pd.to_datetime(df["txn_date"], errors="coerce")
out(f"Earliest txn_date: {parsed_dates.min().date()}")
out(f"Latest txn_date:   {parsed_dates.max().date()}")
n_unparsed = parsed_dates.isna().sum() - df["txn_date"].isna().sum()
if n_unparsed > 0:
    out(f"Note: {n_unparsed:,} txn_date values could not be read as dates.")

# -----------------------------------------------------------------------------
# STEP 9: Check for duplicate transaction IDs (by txn_id only)
# -----------------------------------------------------------------------------
header(9, "Duplicate Transaction IDs")
dup_count = int(df["txn_id"].duplicated().sum())
out(f"Rows whose txn_id already appeared earlier in the file: {dup_count:,}")

# -----------------------------------------------------------------------------
# STEP 10: Print amount summary (mean, median, skewness + interpretation)
# -----------------------------------------------------------------------------
header(10, "Amount Summary")
amt_mean = df["amount"].mean()
amt_median = df["amount"].median()
amt_skew = df["amount"].skew()
out(f"Mean amount:   {amt_mean:,.2f}")
out(f"Median amount: {amt_median:,.2f}")
out(f"Skewness:      {amt_skew:,.2f}")
if amt_skew > 0.5:
    out("Note: The amount distribution is right-skewed (a long tail of large values pulls the mean above the median).")
elif amt_skew < -0.5:
    out("Note: The amount distribution is left-skewed (a long tail of small/negative values pulls the mean below the median).")
else:
    out("Note: The amount distribution is roughly symmetric.")

# -----------------------------------------------------------------------------
# STEP 11: Print amount by transaction type (sorted by mean, high to low)
# -----------------------------------------------------------------------------
header(11, "Amount by Transaction Type")
amt_by_type = (
    df.groupby("txn_type")["amount"]
    .agg(transactions="count", mean_amount="mean", median_amount="median")
    .sort_values("mean_amount", ascending=False)
)
out(f"{'txn_type':<15}{'Transactions':>14}{'Mean Amount':>18}{'Median Amount':>18}")
out("-" * 65)
for txn_type, row in amt_by_type.iterrows():
    out(f"{str(txn_type):<15}{int(row['transactions']):>14,}"
        f"{round(row['mean_amount'], 2):>18,.2f}{round(row['median_amount'], 2):>18,.2f}")

# -----------------------------------------------------------------------------
# STEP 12: Print correlations (matrix + three strongest unique pairs)
# -----------------------------------------------------------------------------
header(12, "Correlations (shares, price, amount)")
corr_cols = ["shares", "price", "amount"]
corr = df[corr_cols].corr().round(2)
out("Correlation matrix:")
out(corr.to_string())
out()
pairs = []
for i, a in enumerate(corr_cols):
    for b in corr_cols[i + 1:]:  # each pair once, no self-correlation
        pairs.append((a, b, corr.loc[a, b]))
pairs.sort(key=lambda p: abs(p[2]) if pd.notna(p[2]) else -1, reverse=True)
out("Strongest correlations (ranked by absolute value):")
for rank, (a, b, r) in enumerate(pairs[:3], start=1):
    out(f"  {rank}. {a} - {b}: {r:.2f}")

# -----------------------------------------------------------------------------
# STEP 13: Print negative share analysis by transaction type
# -----------------------------------------------------------------------------
header(13, "Negative Share Analysis by Transaction Type")
out(f"{'txn_type':<15}{'Min Shares':>16}{'Max Shares':>16}{'Negative Rows':>16}")
out("-" * 63)
for txn_type in sorted(df["txn_type"].dropna().unique()):
    shares = df.loc[df["txn_type"] == txn_type, "shares"]
    if shares.notna().sum() == 0:
        out(f"{str(txn_type):<15}{'no share data':>16}{'no share data':>16}{'n/a':>16}")
    else:
        n_neg = int((shares < 0).sum())
        out(f"{str(txn_type):<15}{shares.min():>16,.4f}{shares.max():>16,.4f}{n_neg:>16,}")

# -----------------------------------------------------------------------------
# STEP 14: Validate the shape against the expected 298,772 x 9
# -----------------------------------------------------------------------------
header(14, "Shape Validation", record=False)
if (n_rows, n_cols) != (EXPECTED_ROWS, EXPECTED_COLS):
    print("!" * 70)
    print("WARNING: Dataset shape does not match expectations!")
    print(f"  Expected: {EXPECTED_ROWS:,} rows x {EXPECTED_COLS} columns")
    print(f"  Actual:   {n_rows:,} rows x {n_cols} columns")
    print("!" * 70)
else:
    print(f"OK: Shape matches the expected {EXPECTED_ROWS:,} rows x {EXPECTED_COLS} columns.")

# -----------------------------------------------------------------------------
# STEP 15: Create and save three charts (PNG only, no display window)
# -----------------------------------------------------------------------------
header(15, "Create and Save Charts", record=False)
os.makedirs(CHART_DIR, exist_ok=True)
chart_paths = []

# Chart 1: Histogram of amount with mean and median lines
hist_path = os.path.join(CHART_DIR, "hist_amount.png")
amount_values = df["amount"].dropna()  # local copy for plotting; df is untouched
fig, ax = plt.subplots(figsize=(10, 6))
ax.hist(amount_values, bins=100, color="steelblue", edgecolor="white", alpha=0.8)
ax.axvline(amt_mean, color="red", linestyle="--", linewidth=2, label=f"Mean = {amt_mean:,.2f}")
ax.axvline(amt_median, color="orange", linestyle="-", linewidth=2, label=f"Median = {amt_median:,.2f}")
ax.set_title("Distribution of Transaction Amount")
ax.set_xlabel("Amount")
ax.set_ylabel("Number of Transactions")
ax.legend()
fig.tight_layout()
fig.savefig(hist_path, dpi=150)
plt.close(fig)
chart_paths.append(hist_path)

# Chart 2: Horizontal box plot of amount by txn_type
box_path = os.path.join(CHART_DIR, "box_amount_by_type.png")
box_types = amt_by_type.index.tolist()
box_data = [df.loc[df["txn_type"] == t, "amount"].dropna() for t in box_types]
fig, ax = plt.subplots(figsize=(10, 6))
ax.boxplot(box_data, vert=False, labels=box_types, showfliers=True,
           flierprops={"markersize": 2, "alpha": 0.3})
ax.set_title("Transaction Amount by Transaction Type")
ax.set_xlabel("Amount")
ax.set_ylabel("Transaction Type")
fig.tight_layout()
fig.savefig(box_path, dpi=150)
plt.close(fig)
chart_paths.append(box_path)

# Chart 3: Scatter of shares vs amount, colored by txn_type
scatter_path = os.path.join(CHART_DIR, "scatter_shares_amount.png")
fig, ax = plt.subplots(figsize=(10, 6))
for txn_type in sorted(df["txn_type"].dropna().unique()):
    subset = df.loc[(df["txn_type"] == txn_type) & df["shares"].notna() & df["amount"].notna(),
                    ["shares", "amount"]]
    if subset.empty:
        continue  # types with no share data have nothing to plot
    ax.scatter(subset["shares"], subset["amount"], s=3, alpha=0.3, label=txn_type)
ax.set_title("Shares vs. Amount by Transaction Type")
ax.set_xlabel("Shares")
ax.set_ylabel("Amount")
ax.legend(title="Transaction Type", markerscale=4)
fig.tight_layout()
fig.savefig(scatter_path, dpi=150)
plt.close(fig)
chart_paths.append(scatter_path)

for path in chart_paths:
    print(f"Saved chart: {path}")

# -----------------------------------------------------------------------------
# STEP 16: Save a text profile of steps 2-13
# -----------------------------------------------------------------------------
header(16, "Save Text Profile", record=False)
with open(PROFILE_PATH, "w", encoding="utf-8") as f:
    f.write("WILDCAT CAPITAL - TRANSACTION DATA PROFILE\n")
    f.write(f"Source: {DATA_PATH}\n")
    f.write("\n".join(profile_lines))
    f.write("\n")
print(f"Saved text profile: {PROFILE_PATH}")

print("\nEDA complete.")
