"""HW5 - prove the star schema design in code.

Checks the eight Wildcat Capital clean tables for:
  1. row and column counts against the handout
  2. primary keys: present, whole numbers, unique
  3. foreign keys: every relationship in star_design.md Part A, with blank keys
     counted separately from orphans (a blank is only allowed where Part A says so)
  4. date keys: fact dates match dim_date[date] (not date_id); dim_date is a
     valid Power BI date table (unique, contiguous, no gaps)
  5. grain: the column set named in Part B is unique in each fact table
  6. design evidence used in Parts C and E (advisor paths agree, measure
     identities hold, AUM is a balance, client_since is outside dim_date)

Standard library only. Every file is read as text and converted on purpose.
Writes hw05/reports/validation_results.csv and exits with code 1 if any check FAILs.

Run from anywhere:  python hw05/scripts/validate_star.py [data_folder]
(data_folder defaults to hw05/data; pass another folder to test a modified copy)
"""
import csv
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

HW = Path(__file__).resolve().parent.parent
DATA = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HW / "data"
# A test run on another folder writes its report there, so the submitted report is never overwritten
OUT = (HW / "reports" if len(sys.argv) == 1 else DATA) / "validation_results.csv"

# Handout table (HW05_Star_Schema_and_Power_BI.md, Data section)
EXPECTED = {
    "dim_advisor": (25, 7),
    "dim_benchmark": (8, 4),
    "dim_client": (2_500, 14),
    "dim_date": (1_827, 12),
    "dim_security": (500, 8),
    "fact_fees": (122_197, 8),
    "fact_portfolio_snapshot": (129_547, 14),
    "fact_transactions": (298_572, 10),
}

PRIMARY_KEYS = {
    "dim_advisor": "advisor_id",
    "dim_benchmark": "benchmark_id",
    "dim_client": "client_id",
    "dim_date": "date_id",
    "dim_security": "security_id",
    "fact_fees": "fee_id",
    "fact_portfolio_snapshot": "snapshot_id",
    "fact_transactions": "txn_id",
}

# (child table, child column, parent table, parent column, blanks allowed?)
FOREIGN_KEYS = [
    ("dim_client", "advisor_id", "dim_advisor", "advisor_id", False),
    ("dim_security", "benchmark_id", "dim_benchmark", "benchmark_id", False),
    ("fact_transactions", "client_id", "dim_client", "client_id", False),
    ("fact_transactions", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_transactions", "security_id", "dim_security", "security_id", True),
    ("fact_transactions", "txn_date", "dim_date", "date", False),
    ("fact_fees", "client_id", "dim_client", "client_id", False),
    ("fact_fees", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_fees", "fee_date", "dim_date", "date", False),
    ("fact_portfolio_snapshot", "client_id", "dim_client", "client_id", False),
    ("fact_portfolio_snapshot", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_portfolio_snapshot", "benchmark_id", "dim_benchmark", "benchmark_id", False),
    ("fact_portfolio_snapshot", "snapshot_date", "dim_date", "date", False),
]

# Part B grains: the columns that must be unique together
GRAINS = {
    "fact_transactions": ["txn_id"],
    "fact_fees": ["client_id", "fee_date"],
    "fact_portfolio_snapshot": ["client_id", "snapshot_date"],
}

CASH_TYPES = {"Deposit", "Withdrawal", "Advisory Fee"}
SECURITY_TYPES = {"Buy", "Sell", "Dividend"}

results = []


def record(section, check, passed, actual, expected="", status=None):
    """Store one check. status overrides PASS/FAIL for informational rows."""
    status = status or ("PASS" if passed else "FAIL")
    results.append({"section": section, "check": check, "status": status,
                    "actual": actual, "expected": expected})


def load(name):
    with open(DATA / f"{name}.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames, rows


def is_whole(text):
    return text.isdigit() and not (len(text) > 1 and text.startswith("0"))


def as_float(text):
    return float(text)


def main():
    tables, columns = {}, {}
    for name in EXPECTED:
        columns[name], tables[name] = load(name)

    # 1. Row and column counts -----------------------------------------------
    for name, (rows, cols) in EXPECTED.items():
        got = (len(tables[name]), len(columns[name]))
        record("1 counts", f"{name} rows x cols", got == (rows, cols),
               f"{got[0]:,} x {got[1]}", f"{rows:,} x {cols}")

    # 2. Primary keys ----------------------------------------------------------
    for name, pk in PRIMARY_KEYS.items():
        values = [r[pk] for r in tables[name]]
        blank = sum(1 for v in values if v == "")
        not_whole = sum(1 for v in values if v != "" and not is_whole(v))
        dupes = len(values) - len(set(values))
        record("2 primary keys", f"{name}[{pk}] blank / non-integer / duplicate",
               blank == 0 and not_whole == 0 and dupes == 0,
               f"{blank} / {not_whole} / {dupes}", "0 / 0 / 0")

    # dim_date[date] is the column the facts join to, so it must be unique too
    dd_dates = [r["date"] for r in tables["dim_date"]]
    record("2 primary keys", "dim_date[date] unique (alternate key used for joins)",
           len(dd_dates) == len(set(dd_dates)),
           f"{len(dd_dates) - len(set(dd_dates))} duplicates", "0 duplicates")

    # 3 + 4. Foreign keys --------------------------------------------------------
    for child, ccol, parent, pcol, nullable in FOREIGN_KEYS:
        parent_keys = {r[pcol] for r in tables[parent]}
        values = [r[ccol] for r in tables[child]]
        blanks = sum(1 for v in values if v == "")
        orphans = [v for v in values if v != "" and v not in parent_keys]
        label = f"{child}[{ccol}] -> {parent}[{pcol}]"
        record("3 foreign keys", f"{label}: orphan rows (distinct keys)",
               not orphans, f"{len(orphans):,} ({len(set(orphans))})", "0 (0)")
        blank_ok = nullable or blanks == 0
        record("3 foreign keys", f"{label}: blank keys",
               blank_ok, f"{blanks:,}", "allowed (cash rows)" if nullable else "0")
        # One-side check: every parent key the child uses exists exactly once
        used = {v for v in values if v}
        record("3 foreign keys", f"{label}: share of {parent} keys used by {child}",
               True, f"{len(used & parent_keys)} of {len(parent_keys)}", status="INFO")

    # The blank security_id must be exactly the cash rows
    tx = tables["fact_transactions"]
    blank_types = Counter(r["txn_type"] for r in tx if r["security_id"] == "")
    filled_types = Counter(r["txn_type"] for r in tx if r["security_id"] != "")
    record("3 foreign keys", "blank security_id only on Deposit/Withdrawal/Advisory Fee",
           set(blank_types) <= CASH_TYPES and not (set(filled_types) & CASH_TYPES),
           ", ".join(f"{k} {v:,}" for k, v in sorted(blank_types.items())),
           "cash types only, and every cash row blank")
    record("3 foreign keys", "every Buy/Sell/Dividend row has a security_id",
           set(filled_types) == SECURITY_TYPES and not (set(blank_types) & SECURITY_TYPES),
           ", ".join(f"{k} {v:,}" for k, v in sorted(filled_types.items())),
           "Buy, Dividend, Sell")
    blank_shares = sum(1 for r in tx if r["security_id"] == "" and (r["shares"] or r["price"]))
    record("3 foreign keys", "cash rows also have blank shares and price",
           blank_shares == 0, f"{blank_shares} cash rows with shares/price", "0")

    # 4. Date dimension ----------------------------------------------------------
    parsed = sorted(date.fromisoformat(d) for d in dd_dates)
    gaps = sum(1 for a, b in zip(parsed, parsed[1:]) if b - a != timedelta(days=1))
    record("4 dates", "dim_date[date] contiguous, one row per day",
           gaps == 0 and len(parsed) == (parsed[-1] - parsed[0]).days + 1,
           f"{parsed[0]} to {parsed[-1]}, {gaps} gaps", "no gaps")
    ids = [int(r["date_id"]) for r in tables["dim_date"]]
    record("4 dates", "dim_date[date_id] is a row number 1..n, not a date",
           ids == list(range(1, len(ids) + 1)), f"{min(ids)}..{max(ids)}", f"1..{len(ids)}")
    date_ids = {r["date_id"] for r in tables["dim_date"]}
    for name, col in [("fact_transactions", "txn_date"), ("fact_fees", "fee_date"),
                      ("fact_portfolio_snapshot", "snapshot_date")]:
        vals = [r[col] for r in tables[name]]
        match_id = sum(1 for v in vals if v in date_ids)
        record("4 dates", f"{name}[{col}] values that would match dim_date[date_id]",
               match_id == 0, f"{match_id:,} of {len(vals):,}", "0 (join on date, not date_id)")
        record("4 dates", f"{name}[{col}] range",
               True, f"{min(vals)} to {max(vals)}", status="INFO")
    for name, col in [("fact_fees", "fee_date"), ("fact_portfolio_snapshot", "snapshot_date")]:
        not_first = sum(1 for r in tables[name] if not r[col].endswith("-01"))
        record("4 dates", f"{name}[{col}] always the 1st of the month",
               not_first == 0, f"{not_first} rows on another day", "0")
    month_end_hits = sum(1 for r in tables["dim_date"] if r["date"].endswith("-01") and r["is_month_end"] == "1")
    record("4 dates", "dim_date[is_month_end] on any 1st-of-month date",
           True, f"{month_end_hits} (so month-end flags never select a snapshot row)", status="INFO")
    lo, hi = min(dd_dates), max(dd_dates)
    since = [r["client_since"] for r in tables["dim_client"]]
    outside = sum(1 for d in since if not (lo <= d <= hi))
    record("4 dates", "dim_client[client_since] outside dim_date range",
           True, f"{outside:,} of {len(since):,} ({min(since)} to {max(since)})",
           "reason client_since gets no relationship", status="INFO")

    # 5. Grain -------------------------------------------------------------------
    for name, cols in GRAINS.items():
        keys = [tuple(r[c] for c in cols) for r in tables[name]]
        dupes = len(keys) - len(set(keys))
        record("5 grain", f"{name} unique on ({', '.join(cols)})",
               dupes == 0, f"{dupes} duplicates", "0")
    # Transactions have no natural key: the same client can do the same thing twice in a day
    nat = Counter((r["client_id"], r["txn_date"], r["txn_type"], r["security_id"]) for r in tx)
    repeats = sum(c - 1 for c in nat.values() if c > 1)
    record("5 grain", "fact_transactions rows repeating (client, date, type, security)",
           True, f"{repeats:,} (why txn_id, not a column combination, defines the grain)",
           status="INFO")
    snap = tables["fact_portfolio_snapshot"]
    per_client = defaultdict(lambda: {"benchmark_id": set(), "account_type": set(), "advisor_id": set()})
    for r in snap:
        for c in per_client[r["client_id"]]:
            per_client[r["client_id"]][c].add(r[c])
    for c in ["benchmark_id", "account_type", "advisor_id"]:
        multi = sum(1 for v in per_client.values() if len(v[c]) > 1)
        record("5 grain", f"clients with more than one {c} across their snapshots",
               multi == 0, f"{multi}", "0 (snapshot is per client, not per account)")
    ym_bad = sum(1 for r in snap if r["snapshot_date"][:4] != r["year"]
                 or int(r["snapshot_date"][5:7]) != int(r["month"]))
    record("5 grain", "snapshot year/month agree with snapshot_date",
           ym_bad == 0, f"{ym_bad} mismatches", "0")

    # 6. Design evidence ---------------------------------------------------------
    client_adv = {r["client_id"]: r["advisor_id"] for r in tables["dim_client"]}
    for name in ["fact_transactions", "fact_fees", "fact_portfolio_snapshot"]:
        # .get(): an orphan client_id is reported in section 3; here it counts as a mismatch, not a crash
        diff = sum(1 for r in tables[name] if client_adv.get(r["client_id"]) != r["advisor_id"])
        record("6 evidence", f"{name}[advisor_id] differs from dim_client[advisor_id]",
               diff == 0, f"{diff:,} rows", "0 (both advisor paths give the same answer)")

    fees = tables["fact_fees"]
    off = sum(1 for r in fees if abs(as_float(r["aum_basis"]) * as_float(r["bps_charged"]) / 10_000 / 12
                                     - as_float(r["amount"])) > 0.011)
    record("6 evidence", "fee amount = aum_basis x bps_charged / 10,000 / 12",
           off == 0, f"{off:,} rows off by more than 1 cent", "0")
    snap_aum = {(r["client_id"], r["snapshot_date"]): r["aum"] for r in snap}
    same = sum(1 for r in fees if snap_aum.get((r["client_id"], r["fee_date"])) == r["aum_basis"])
    record("6 evidence", "fee aum_basis equals that client-month's snapshot aum",
           same == len(fees), f"{same:,} of {len(fees):,}", f"{len(fees):,}")
    no_fee = len(snap_aum) - len({(r["client_id"], r["fee_date"]) for r in fees})
    record("6 evidence", "snapshot client-months with no fee row",
           True, f"{no_fee:,}", status="INFO")

    off = sum(1 for r in snap if abs(as_float(r["return_ytd"]) - as_float(r["benchmark_return_ytd"])
                                     - as_float(r["active_alpha_ytd"])) > 1e-5)
    record("6 evidence", "active_alpha_ytd = return_ytd - benchmark_return_ytd",
           off == 0, f"{off:,} rows off", "0")
    off = sum(1 for r in tx if r["shares"] and abs(as_float(r["shares"]) * as_float(r["price"])
                                                   - as_float(r["amount"])) > 0.011)
    record("6 evidence", "Buy/Sell/Dividend amount = shares x price",
           off == 0, f"{off:,} rows off by more than 1 cent", "0")
    neg = sum(1 for r in tx if as_float(r["amount"]) < 0)
    record("6 evidence", "transaction amounts stored as positive numbers",
           True, f"{neg} negative (direction comes from txn_type only)", status="INFO")

    # AUM is a balance: summing a year of months overstates it roughly 10-12 times
    dec = sum(as_float(r["aum"]) for r in snap if r["snapshot_date"] == "2024-12-01")
    yr = sum(as_float(r["aum"]) for r in snap if r["year"] == "2024")
    record("6 evidence", "2024 AUM: sum of 12 months vs December snapshot",
           True, f"${yr:,.0f} vs ${dec:,.0f} ({yr / dec:.1f}x)", "semi-additive over time",
           status="INFO")
    # return_ytd resets each January, so it is a running figure, not a monthly one:
    # the typical size of the value grows from January to December
    def mean_abs(month):
        v = [abs(as_float(r["return_ytd"])) for r in snap if r["month"] == month]
        return sum(v) / len(v)
    jan, dec_ = mean_abs("1"), mean_abs("12")
    record("6 evidence", "mean |return_ytd| in January vs December",
           True, f"{jan:.2%} vs {dec_:.2%} (year-to-date, restarts each January)",
           "cumulative, not monthly", status="INFO")

    fee_txn = sum(as_float(r["amount"]) for r in tx if r["txn_type"] == "Advisory Fee")
    fee_fact = sum(as_float(r["amount"]) for r in fees)
    record("6 evidence", "Advisory Fee transactions vs fact_fees amount",
           True, f"${fee_txn:,.2f} vs ${fee_fact:,.2f}",
           "different processes: do not add them together", status="INFO")

    active = {r["client_id"]: r["is_active"] for r in tables["dim_client"]}
    post = [r for r in tx if r["is_post_departure_txn"] == "1"]
    on_inactive = sum(1 for r in post if active.get(r["client_id"]) == "False")
    record("6 evidence", "is_post_departure_txn rows belong to inactive clients",
           on_inactive == len(post), f"{on_inactive:,} of {len(post):,}", f"{len(post):,}")

    # Report -----------------------------------------------------------------------
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["section", "check", "status", "actual", "expected"])
        w.writeheader()
        w.writerows(results)

    width = max(len(r["check"]) for r in results)
    section = None
    for r in results:
        if r["section"] != section:
            section = r["section"]
            print(f"\n== {section}")
        print(f"  {r['status']:<4}  {r['check']:<{width}}  {r['actual']}")
    tally = Counter(r["status"] for r in results)
    print(f"\n{tally['PASS']} PASS, {tally['FAIL']} FAIL, {tally['INFO']} INFO -> {OUT}")
    return 1 if tally["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
