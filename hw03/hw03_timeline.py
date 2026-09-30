# =============================================================================
# Script:      hw03_timeline.py
# Inputs:      hw03/earnings_history.csv, hw03/executive_events.csv
# Author:      Aiden James
# Generated:   2026-09-30
# Description: Joins each executive event to the nearest earnings filing for the
#              same company, measures the gap in days, labels the timing
#              ("before earnings" / "after earnings" / "same week"), saves the
#              combined table to hw03/corporate_events_timeline.csv and prints a
#              per-company summary plus overall before/after counts.
# Run from the repository root:  python hw03/hw03_timeline.py
# =============================================================================

import os

import pandas as pd

EARNINGS_PATH = "hw03/earnings_history.csv"
EVENTS_PATH = "hw03/executive_events.csv"
OUTPUT_PATH = "hw03/corporate_events_timeline.csv"
SAME_WEEK_DAYS = 7

# Load both tables as text so values such as "NOT_FOUND" and CIKs with
# leading zeros are kept exactly as they were written.
earnings = pd.read_csv(EARNINGS_PATH, dtype=str)
events = pd.read_csv(EVENTS_PATH, dtype=str)

earnings["_date"] = pd.to_datetime(earnings["filing_date"])
events["_date"] = pd.to_datetime(events["filing_date"])

# Earnings columns get an "earnings_" prefix where the name would clash
# (both tables have filing_date); company/ticker/cik are shared keys.
EARNINGS_COLUMNS = {
    "filing_date": "earnings_filing_date",
    "period": "earnings_period",
    "revenue_reported": "revenue_reported",
    "eps_diluted": "eps_diluted",
    "net_income": "net_income",
}

# -----------------------------------------------------------------------------
# STEP 1 + 2: nearest earnings filing, days between, and timing label
# -----------------------------------------------------------------------------
rows = []
for _, event in events.iterrows():
    company_earnings = earnings[earnings["ticker"] == event["ticker"]]
    row = {col: event[col] for col in events.columns if col != "_date"}

    if company_earnings.empty:
        for new_name in EARNINGS_COLUMNS.values():
            row[new_name] = "NOT_FOUND"
        row["days_to_nearest_earnings"] = "NOT_FOUND"
        row["event_timing"] = "NOT_FOUND"
        rows.append(row)
        continue

    # Signed gap: earnings date minus event date.
    #   positive -> the earnings filing came AFTER the event (event was before earnings)
    #   negative -> the earnings filing came BEFORE the event (event was after earnings)
    gaps = (company_earnings["_date"] - event["_date"]).dt.days
    nearest_index = gaps.abs().idxmin()
    nearest = company_earnings.loc[nearest_index]
    days = int(gaps.loc[nearest_index])

    for old_name, new_name in EARNINGS_COLUMNS.items():
        row[new_name] = nearest[old_name]
    row["days_to_nearest_earnings"] = days

    if abs(days) <= SAME_WEEK_DAYS:
        row["event_timing"] = "same week"
    elif days > 0:
        row["event_timing"] = "before earnings"
    else:
        row["event_timing"] = "after earnings"
    rows.append(row)

timeline = pd.DataFrame(rows)

# -----------------------------------------------------------------------------
# STEP 3: save the combined table
# -----------------------------------------------------------------------------
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
timeline.to_csv(OUTPUT_PATH, index=False)

# -----------------------------------------------------------------------------
# STEP 4: per-company summary
# -----------------------------------------------------------------------------
print("CORPORATE EVENTS TIMELINE")
print("days_to_nearest_earnings = nearest earnings filing date minus event filing date")
print("(positive = event came before that earnings release; negative = after)\n")

for ticker in earnings["ticker"].drop_duplicates():
    company_rows = timeline[timeline["ticker"] == ticker] if not timeline.empty else timeline
    company_name = earnings.loc[earnings["ticker"] == ticker, "company"].iloc[0]
    print("=== {} ({}) ===".format(company_name, ticker))
    if company_rows.empty:
        print("  No executive events in past 12 months")
    for _, r in company_rows.iterrows():
        print("  {} | {:<11} | {:<25} | {:>4} days | {:<15} | nearest earnings {} ({})".format(
            r["filing_date"], r["event_type"], r["person_name"],
            r["days_to_nearest_earnings"], r["event_timing"],
            r["earnings_filing_date"], r["earnings_period"]))
    print()

# -----------------------------------------------------------------------------
# STEP 5: overall counts
# -----------------------------------------------------------------------------
counts = timeline["event_timing"].value_counts() if not timeline.empty else pd.Series(dtype=int)
print("=== TOTAL ACROSS ALL FIVE COMPANIES ({} events) ===".format(len(timeline)))
for label in ["before earnings", "after earnings", "same week"]:
    print("  {:<16} {}".format(label + ":", int(counts.get(label, 0))))
print("\nSaved {} rows to {}".format(len(timeline), OUTPUT_PATH))
