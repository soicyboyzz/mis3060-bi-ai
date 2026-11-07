"""HW6 Part B - reconcile every DAX measure to an independent pandas calculation.

1. Recomputes each measure in pandas from the eight Wildcat Capital Clean CSVs
   (hw06/data/). Nothing is read from Power BI for this step.
2. Reads the Power BI numbers from hw06/reports/powerbi_values.csv
   (columns: measure, slice, value), exported from DAX queries.
3. Writes hw06/reports/measure_reconciliation.csv with columns
   measure, slice, powerbi_value, pandas_value, abs_diff, match
   (tolerance 0.01 for currency and counts, 0.0001 for ratios and bps,
   exact text for Alpha Signal).
4. Writes hw06/reports/part_c_evidence.csv with the pandas figures behind
   the Part C answers in powerbi/measures.md.

The pandas side copies the DAX *filter context*, not the DAX code:
  * a slice is a set of dim_date dates (all dates, one year, or one month)
    plus, for the tier slices, the set of clients in that tier;
  * "last snapshot" = the latest snapshot_date that has rows inside the slice
    (what LASTNONBLANK over dim_date[date] returns);
  * LY = the slice's dates moved back one year (SAMEPERIODLASTYEAR), PM = moved
    back one month (DATEADD -1 MONTH), both clipped to the dim_date range.

Run from anywhere:  python hw06/scripts/01_reconcile_measures.py
Exits with code 1 if any required row is missing or does not match.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HW = Path(__file__).resolve().parent.parent
DATA = HW / "data"
REPORTS = HW / "reports"
# Optional argument: another powerbi_values file (used to test the script on a tampered copy).
# A test run writes its reconciliation next to that file, never over the submitted one.
PBI_FILE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else REPORTS / "powerbi_values.csv"
OUT_FILE = (PBI_FILE.parent if len(sys.argv) > 1 else REPORTS) / "measure_reconciliation.csv"
EVIDENCE_FILE = REPORTS / "part_c_evidence.csv"

TOL_CURRENCY = 0.01
TOL_RATIO = 0.0001

# measure name -> kind (decides the tolerance)
MEASURES = {
    "Total Fees": "currency",
    "Net Flows": "currency",
    "Effective Fee Rate (bps)": "ratio",
    "AUM (naive SUM)": "currency",
    "Ending AUM": "currency",
    "Ending Clients": "currency",          # a count: exact, so the currency tolerance is plenty
    "Avg AUM per Client": "currency",
    "Ending AUM LY": "currency",
    "AUM YoY %": "ratio",
    "Ending AUM PM": "currency",
    "AUM MoM %": "ratio",
    "Avg Monthly AUM": "currency",
    "Fee Yield (bps)": "ratio",
    "Organic Growth Rate": "ratio",
    "AUM-Weighted Alpha": "ratio",
    "Alpha Signal": "text",
    "Top 10 Client Share": "ratio",
}

# The assignment's minimum coverage (Part B): every measure at the grand total;
# measures 1, 4, 6-10 by year; 1, 3, 4, 7-11 by tier for 2024; 5 for Dec 2024;
# plus the naive SUM. Every one of these rows must exist and match.
YEARS = [2020, 2021, 2022, 2023, 2024]
TIERS = ["HNW", "Retail", "UHNW"]
BY_YEAR = ["AUM (naive SUM)", "Ending AUM", "Ending AUM LY", "AUM YoY %", "Avg Monthly AUM",
           "Fee Yield (bps)", "Organic Growth Rate", "AUM-Weighted Alpha", "Alpha Signal"]
BY_TIER = ["Ending AUM", "Avg AUM per Client", "Ending AUM LY", "AUM YoY %", "Fee Yield (bps)",
           "Organic Growth Rate", "AUM-Weighted Alpha", "Alpha Signal", "Top 10 Client Share"]
DEC_2024 = ["Ending AUM", "Ending AUM PM", "AUM MoM %"]


def required_rows():
    rows = {(m, "All") for m in MEASURES}
    rows |= {(m, f"Year {y}") for m in BY_YEAR for y in YEARS}
    rows |= {(m, f"2024 | {t}") for m in BY_TIER for t in TIERS}
    rows |= {(m, "Dec 2024") for m in DEC_2024}
    return rows


# --------------------------------------------------------------------------- data
def load():
    def read(name, dates=()):
        return pd.read_csv(DATA / f"{name}.csv", parse_dates=list(dates), dtype={"zip_code": str})
    return {
        "date": read("dim_date", ["date"]),
        "client": read("dim_client", ["client_since"]),
        "snap": read("fact_portfolio_snapshot", ["snapshot_date"]),
        "fees": read("fact_fees", ["fee_date"]),
        "tx": read("fact_transactions", ["txn_date"]),
    }


class Slice:
    """A filter context: a date range from dim_date and an optional client set."""

    def __init__(self, label, start, end, clients=None):
        self.label, self.start, self.end, self.clients = label, pd.Timestamp(start), pd.Timestamp(end), clients

    def shifted(self, **offset):
        """SAMEPERIODLASTYEAR / DATEADD: move both ends back, keep the client filter."""
        off = pd.DateOffset(**offset)
        return Slice(self.label, self.start - off, self.end - off, self.clients)


class Model:
    def __init__(self, t):
        self.t = t
        self.dmin, self.dmax = t["date"]["date"].min(), t["date"]["date"].max()

    def rows(self, table, date_col, s):
        df = self.t[table]
        lo, hi = max(s.start, self.dmin), min(s.end, self.dmax)   # dates outside dim_date do not exist
        df = df[(df[date_col] >= lo) & (df[date_col] <= hi)]
        if s.clients is not None:
            df = df[df["client_id"].isin(s.clients)]
        return df

    # base measures (ICE 9 / ICE 10)
    def total_fees(self, s):
        return self.rows("fees", "fee_date", s)["amount"].sum()

    def net_flows(self, s):
        tx = self.rows("tx", "txn_date", s)
        return tx.loc[tx.txn_type == "Deposit", "amount"].sum() - tx.loc[tx.txn_type == "Withdrawal", "amount"].sum()

    def effective_fee_rate(self, s):
        f = self.rows("fees", "fee_date", s)
        return div(f["amount"].sum() * 12 * 10_000, f["aum_basis"].sum())

    # snapshot measures
    def last_rows(self, s):
        snap = self.rows("snap", "snapshot_date", s)
        if snap.empty:
            return snap
        return snap[snap.snapshot_date == snap.snapshot_date.max()]

    def naive_sum(self, s):
        return blank_if_empty(self.rows("snap", "snapshot_date", s)["aum"])

    def ending_aum(self, s):
        return blank_if_empty(self.last_rows(s)["aum"])

    def ending_clients(self, s):
        last = self.last_rows(s)
        return np.nan if last.empty else float(last.client_id.nunique())

    def avg_aum_per_client(self, s):
        return div(self.ending_aum(s), self.ending_clients(s))

    def ending_aum_ly(self, s):
        return self.ending_aum(s.shifted(years=1))

    def yoy(self, s):
        ly = self.ending_aum_ly(s)
        return div(self.ending_aum(s) - ly, ly)

    def ending_aum_pm(self, s):
        return self.ending_aum(s.shifted(months=1))

    def mom(self, s):
        pm = self.ending_aum_pm(s)
        return div(self.ending_aum(s) - pm, pm)

    def avg_monthly_aum(self, s):
        snap = self.rows("snap", "snapshot_date", s)
        return div(snap.aum.sum(), snap.snapshot_date.nunique()) if not snap.empty else np.nan

    def fee_yield(self, s):
        snap = self.rows("snap", "snapshot_date", s)
        return div(self.total_fees(s) * 12 * 10_000, snap.aum.sum()) if not snap.empty else np.nan

    def organic_growth(self, s):
        return div(self.net_flows(s), self.ending_aum_ly(s))

    def weighted_alpha(self, s, include_suspect=False):
        last = self.last_rows(s)
        if not include_suspect:
            last = last[last.is_return_suspect == 0]
        return div((last.aum * last.active_alpha_ytd).sum(), last.aum.sum()) if not last.empty else np.nan

    def alpha_signal(self, s):
        a = self.weighted_alpha(s)
        if np.isnan(a):
            return ""
        return "Outperforming" if a >= 0.02 else "Lagging" if a <= -0.02 else "In line"

    def top10_share(self, s):
        last = self.last_rows(s)
        if last.empty:
            return np.nan
        by_client = last.groupby("client_id").aum.sum()
        return div(by_client.nlargest(10).sum(), by_client.sum())

    def all_measures(self, s):
        return {
            "Total Fees": self.total_fees(s),
            "Net Flows": self.net_flows(s),
            "Effective Fee Rate (bps)": self.effective_fee_rate(s),
            "AUM (naive SUM)": self.naive_sum(s),
            "Ending AUM": self.ending_aum(s),
            "Ending Clients": self.ending_clients(s),
            "Avg AUM per Client": self.avg_aum_per_client(s),
            "Ending AUM LY": self.ending_aum_ly(s),
            "AUM YoY %": self.yoy(s),
            "Ending AUM PM": self.ending_aum_pm(s),
            "AUM MoM %": self.mom(s),
            "Avg Monthly AUM": self.avg_monthly_aum(s),
            "Fee Yield (bps)": self.fee_yield(s),
            "Organic Growth Rate": self.organic_growth(s),
            "AUM-Weighted Alpha": self.weighted_alpha(s),
            "Alpha Signal": self.alpha_signal(s),
            "Top 10 Client Share": self.top10_share(s),
        }


def div(a, b):
    """DIVIDE(): blank (NaN) when the denominator is blank or zero."""
    if b is None or (isinstance(b, float) and np.isnan(b)) or b == 0 or a is None or np.isnan(a):
        return np.nan
    return a / b


def blank_if_empty(series):
    return np.nan if series.empty else series.sum()


def slices(t):
    tiers = t["client"].groupby("client_tier").client_id.apply(set)
    out = [Slice("All", "2020-01-01", "2024-12-31")]
    out += [Slice(f"Year {y}", f"{y}-01-01", f"{y}-12-31") for y in YEARS]
    out += [Slice("Dec 2024", "2024-12-01", "2024-12-31")]
    out += [Slice(f"2024 | {k}", "2024-01-01", "2024-12-31", tiers[k]) for k in TIERS]
    return out


# ----------------------------------------------------------------------- Part C
def part_c(m, t):
    allslice = slices(t)[0]
    y24 = Slice("Year 2024", "2024-01-01", "2024-12-31")
    snap = t["snap"]
    ev = []

    # (a) Ending AUM vs SUMX over clients of each client's own last balance
    last_per_client = snap.sort_values("snapshot_date").groupby("client_id").tail(1)
    sumx = last_per_client.aum.sum()
    ending = m.ending_aum(allslice)
    stale = last_per_client[last_per_client.snapshot_date < snap.snapshot_date.max()]
    ev += [("a", "Ending AUM (grand total)", ending),
           ("a", "SUMX over clients of [Ending AUM]", sumx),
           ("a", "difference", sumx - ending),
           ("a", "clients whose last snapshot is before 2024-12-01", len(stale)),
           ("a", "their last balances (sum)", stale.aum.sum()),
           ("a", "those clients that are inactive in dim_client",
            int(stale.client_id.isin(t["client"].query("is_active == False").client_id).sum())),
           ("a", "earliest / latest stale snapshot", f"{stale.snapshot_date.min().date()} / {stale.snapshot_date.max().date()}")]

    # (b) Fee Yield vs Effective Fee Rate, 2024
    fees24 = m.rows("fees", "fee_date", y24)
    snap24 = m.rows("snap", "snapshot_date", y24)
    keyed = snap24.merge(fees24[["client_id", "fee_date"]], left_on=["client_id", "snapshot_date"],
                         right_on=["client_id", "fee_date"], how="left", indicator=True)
    no_fee = keyed[keyed._merge == "left_only"]
    ev += [("b", "Fee Yield (bps) 2024", m.fee_yield(y24)),
           ("b", "Effective Fee Rate (bps) 2024", m.effective_fee_rate(y24)),
           ("b", "2024 SUM(aum) in snapshot", snap24.aum.sum()),
           ("b", "2024 SUM(aum_basis) in fees", fees24.aum_basis.sum()),
           ("b", "2024 snapshot client-months", len(snap24)),
           ("b", "2024 fee rows", len(fees24)),
           ("b", "2024 snapshot client-months with no fee row", len(no_fee)),
           ("b", "AUM in those client-months", no_fee.aum.sum()),
           ("b", "share of 2024 snapshot AUM with no fee row", no_fee.aum.sum() / snap24.aum.sum()),
           ("b", "aum_basis = snapshot aum on matched rows (all 2024 fee rows)",
            bool((snap24.merge(fees24, left_on=["client_id", "snapshot_date"], right_on=["client_id", "fee_date"])
                  .eval("aum == aum_basis")).all())),
           ("b", "clients with at least one no-fee month in 2024", no_fee.client_id.nunique()),
           ("b", "no-fee client-months by tier 2024",
            "; ".join(f"{k} {v}" for k, v in no_fee.merge(t["client"][["client_id", "client_tier"]], on="client_id")
                      .client_tier.value_counts().sort_index().items()))]
    all_fee = m.rows("fees", "fee_date", allslice)
    all_keyed = snap.merge(all_fee[["client_id", "fee_date"]], left_on=["client_id", "snapshot_date"],
                           right_on=["client_id", "fee_date"], how="left", indicator=True)
    nf = all_keyed[all_keyed._merge == "left_only"]
    ev += [("b", "no-fee client-months, all years", len(nf)),
           ("b", "no-fee client-months by year",
            "; ".join(f"{k} {v}" for k, v in nf.snapshot_date.dt.year.value_counts().sort_index().items()))]

    # (c) weighted alpha at the last snapshot vs simple mean, with and without suspects
    last = m.last_rows(allslice)
    clean = last[last.is_return_suspect == 0]
    ev += [("c", "last snapshot date", str(last.snapshot_date.max().date())),
           ("c", "rows at last snapshot / suspect rows", f"{len(last)} / {int(last.is_return_suspect.sum())}"),
           ("c", "AUM-Weighted Alpha (suspects excluded)", m.weighted_alpha(allslice)),
           ("c", "simple mean of active_alpha_ytd, same rows", clean.active_alpha_ytd.mean()),
           ("c", "AUM-weighted alpha, suspects included", m.weighted_alpha(allslice, include_suspect=True)),
           ("c", "simple mean, suspects included", last.active_alpha_ytd.mean()),
           ("c", "min / max alpha of suspect rows at last snapshot",
            f"{last[last.is_return_suspect == 1].active_alpha_ytd.min():.4f} / "
            f"{last[last.is_return_suspect == 1].active_alpha_ytd.max():.4f}"),
           ("c", "AUM-weighted alpha over ALL 2024 rows (wrong: mixes 12 YTD readings)",
            div((snap24.query('is_return_suspect == 0').eval('aum * active_alpha_ytd')).sum(),
                snap24.query('is_return_suspect == 0').aum.sum()))]

    # (d) organic growth vs AUM YoY by tier, 2024
    for s in slices(t)[-3:]:
        ev += [("d", f"{s.label}: Organic Growth Rate", m.organic_growth(s)),
               ("d", f"{s.label}: AUM YoY %", m.yoy(s)),
               ("d", f"{s.label}: market + other (YoY - organic)", m.yoy(s) - m.organic_growth(s)),
               ("d", f"{s.label}: Net Flows", m.net_flows(s)),
               ("d", f"{s.label}: Ending AUM LY", m.ending_aum_ly(s)),
               ("d", f"{s.label}: Ending Clients / LY",
                f"{m.ending_clients(s):.0f} / {m.ending_clients(s.shifted(years=1)):.0f}")]
    # Part D: Top 10 Client Share, final measure vs the simpler "TOPN over [Ending AUM]" draft.
    # The draft lets every client use its OWN last snapshot, so a client who left early
    # still counts with an old balance in the numerator while the denominator is the
    # balance at the slice's last date.
    def top10_simple(df):
        own_last = df.sort_values("snapshot_date").groupby("client_id").tail(1).set_index("client_id").aum
        last = df[df.snapshot_date == df.snapshot_date.max()].aum.sum()
        return own_last.nlargest(10).sum() / last

    for adv in [1, 5, 14, 23]:
        sub = snap[snap.advisor_id == adv]
        last = sub[sub.snapshot_date == sub.snapshot_date.max()]
        final = last.groupby("client_id").aum.sum().nlargest(10).sum() / last.aum.sum()
        own_last = sub.sort_values("snapshot_date").groupby("client_id").tail(1)
        departed_in_top10 = own_last.nlargest(10, "aum").snapshot_date.lt(sub.snapshot_date.max()).sum()
        ev += [("D", f"advisor {adv}: Top 10 Client Share (final)", final),
               ("D", f"advisor {adv}: Top 10 share, simple draft", top10_simple(sub)),
               ("D", f"advisor {adv}: departed clients in the draft's top 10", int(departed_in_top10))]
    return pd.DataFrame(ev, columns=["question", "figure", "value"])


# ------------------------------------------------------------------- reconcile
def compare(kind, pbi, pan):
    if kind == "text":
        p = "" if pd.isna(pbi) else str(pbi)
        q = "" if pd.isna(pan) else str(pan)
        return None, p == q
    pbi_blank, pan_blank = pd.isna(pbi), pd.isna(pan)
    if pbi_blank or pan_blank:
        return None, pbi_blank and pan_blank          # both blank (e.g. 2020 YoY) is a match
    diff = abs(float(pbi) - float(pan))
    return diff, diff <= (TOL_CURRENCY if kind == "currency" else TOL_RATIO)


def main():
    t = load()
    m = Model(t)
    pandas_vals = {(meas, s.label): v for s in slices(t) for meas, v in m.all_measures(s).items()}

    REPORTS.mkdir(exist_ok=True)
    evidence = part_c(m, t)
    evidence.to_csv(EVIDENCE_FILE, index=False)

    if not PBI_FILE.exists():
        print(f"{PBI_FILE} not found: export the Power BI values first. Pandas side computed only.")
        return 1
    pbi = pd.read_csv(PBI_FILE, dtype={"value": str}, keep_default_na=False)
    dupes = pbi[pbi.duplicated(["measure", "slice"], keep=False)]
    if len(dupes):
        raise SystemExit(f"powerbi_values.csv has {len(dupes)} duplicated (measure, slice) rows, e.g. "
                         f"{dupes.iloc[0].measure} / {dupes.iloc[0].slice}")

    rows = []
    for _, r in pbi.iterrows():
        key = (r.measure, r.slice)
        if key not in pandas_vals:
            raise SystemExit(f"Power BI row has no pandas twin: {key}")
        kind = MEASURES[r.measure]
        pbi_val = r.value if kind == "text" else (np.nan if r.value == "" else float(r.value))
        pan_val = pandas_vals[key]
        diff, ok = compare(kind, pbi_val, pan_val)
        rows.append({"measure": r.measure, "slice": r.slice,
                     "powerbi_value": r.value,
                     "pandas_value": pan_val if kind == "text" else ("" if np.isnan(pan_val) else repr(float(pan_val))),
                     "abs_diff": "" if diff is None else f"{diff:.10f}",
                     "match": ok})
    rec = pd.DataFrame(rows)
    rec.to_csv(OUT_FILE, index=False)

    missing = required_rows() - set(zip(rec.measure, rec.slice))
    bad = rec[~rec.match]
    print(f"{len(rec)} rows reconciled -> {OUT_FILE}")
    print(f"  match: {int(rec.match.sum())}, mismatch: {len(bad)}, required rows missing: {len(missing)}")
    print(f"  Part C evidence -> {EVIDENCE_FILE}")
    for _, r in bad.iterrows():
        print(f"  MISMATCH {r.measure} [{r.slice}] powerbi={r.powerbi_value} pandas={r.pandas_value}")
    for k in sorted(missing):
        print(f"  MISSING  {k}")
    return 1 if len(bad) or missing else 0


if __name__ == "__main__":
    sys.exit(main())
