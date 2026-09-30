# =============================================================================
# Script:      hw03_yfinance_check.py
# Author:      Aiden James
# Generated:   2026-09-30
# Description: Part 5C cross-validation. Uses yfinance (Yahoo Finance) to get
#              Apple's most recent quarterly revenue and net income as a second,
#              independent source to compare against the 8-K text extraction
#              in hw03/earnings_history.csv.
# Run from the repository root:  python hw03/hw03_yfinance_check.py
# =============================================================================

import pandas as pd
import yfinance as yf

TICKER = "AAPL"

income = yf.Ticker(TICKER).quarterly_income_stmt   # rows = line items, columns = quarter-end dates
if income is None or income.empty:
    raise SystemExit("yfinance returned no data for {} (check the internet connection / yfinance version)".format(TICKER))
latest_quarter = income.columns[0]                  # most recent quarter first


def line_item(*names):
    """Return the first matching line item for the latest quarter (names differ slightly across yfinance versions)."""
    for name in names:
        if name in income.index and pd.notna(income.loc[name, latest_quarter]):
            return float(income.loc[name, latest_quarter])
    return None


revenue = line_item("Total Revenue", "Operating Revenue")
net_income = line_item("Net Income", "Net Income Common Stockholders")
eps = line_item("Diluted EPS")

print("yfinance cross-check for {} - most recent quarter ended {}".format(TICKER, latest_quarter.date()))
print("  Revenue:     ${:,.0f}M".format(revenue / 1e6) if revenue else "  Revenue:     not available")
print("  Net income:  ${:,.0f}M".format(net_income / 1e6) if net_income else "  Net income:  not available")
print("  Diluted EPS: ${:.2f}".format(eps) if eps else "  Diluted EPS: not available")

csv = pd.read_csv("hw03/earnings_history.csv", dtype=str)
row = csv[csv["ticker"] == TICKER].sort_values("filing_date").iloc[-1]
print("\n8-K extraction (hw03/earnings_history.csv, filed {}):".format(row["filing_date"]))
print("  Period: {} | Revenue: ${}M | Net income: ${}M | EPS: ${}".format(
    row["period"], row["revenue_reported"], row["net_income"], row["eps_diluted"]))
