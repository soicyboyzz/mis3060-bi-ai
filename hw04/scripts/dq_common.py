# =============================================================================
# Script:      dq_common.py
# Assignment:  HW4 - Cleaning the Wildcat Capital Data
# Author:      Aiden James Dumm
# Generated:   2026-10-19
# Description: Shared settings used by 01_profile.py, 02_clean.py and
#              03_validate.py: folder paths, a text-only loader, value parsers,
#              the expected schema (types, allowed values, business bounds),
#              the key relationships, and the row-level and cross-table rules.
#              The check LOGIC in the scripts is generic; this file is the only
#              place that knows anything about specific tables.
# =============================================================================

import re
from pathlib import Path

import numpy as np
import pandas as pd

# -----------------------------------------------------------------------------
# Paths (relative to the hw04 folder, so scripts run from any working folder)
# -----------------------------------------------------------------------------
HW_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = HW_DIR / "data" / "raw"
CLEAN_DIR = HW_DIR / "data" / "clean"
AUDIT_DIR = HW_DIR / "data" / "audit"
REPORTS_DIR = HW_DIR / "reports"

TABLES = [
    "dim_advisor", "dim_benchmark", "dim_client", "dim_date", "dim_security",
    "fact_fees", "fact_portfolio_snapshot", "fact_transactions",
]


def load_tables(folder):
    """Read every table as text so nothing is silently converted."""
    return {
        t: pd.read_csv(Path(folder) / f"{t}.csv", dtype=str, keep_default_na=False)
        for t in TABLES
    }


# -----------------------------------------------------------------------------
# Value parsers (all work on text columns)
# -----------------------------------------------------------------------------
INT_PATTERN = r"-?\d+"
DEC_PATTERN = r"-?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?"
DATE_PATTERN = r"\d{4}-\d{2}-\d{2}"
NULL_TOKENS = {"NULL", "null", "None", "NONE", "NaN", "nan", "N/A", "n/a", "NA", "#N/A", "-"}


def blank_mask(s):
    return s.str.strip() == ""


def valid_mask(s, kind):
    """True where a NON-BLANK value parses as the given type."""
    if kind == "int":
        return s.str.fullmatch(INT_PATTERN)
    if kind == "decimal":
        return s.str.fullmatch(DEC_PATTERN)
    if kind == "date":
        return s.str.fullmatch(DATE_PATTERN) & pd.to_datetime(
            s, format="%Y-%m-%d", errors="coerce").notna()
    if kind == "bool":
        return s.isin(["True", "False"])
    if kind == "flag":
        return s.isin(["0", "1"])
    return ~blank_mask(s)  # text


def to_num(s):
    """Numeric value where the text is a clean number, otherwise NaN."""
    return pd.to_numeric(s.where(s.str.fullmatch(DEC_PATTERN)), errors="coerce")


def to_date(s):
    return pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")


def value_shape(v):
    """Generalised shape of a value: digit runs -> 9, letter runs -> A."""
    v = re.sub(r"\d+", "9", v)
    return re.sub(r"[A-Za-z]+", "A", v)


# -----------------------------------------------------------------------------
# Reference lists
# -----------------------------------------------------------------------------
USPS = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO",
    "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA",
    "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
}
STATE_NAME_TO_CODE = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}
RISK_PROFILES = ["Conservative", "Moderately Conservative", "Balanced",
                 "Moderately Aggressive", "Aggressive"]
# Benchmark assigned to each risk profile (observed 1-to-1 in every snapshot
# of every client whose risk profile is filled in).
RISK_TO_BENCHMARK = {"Aggressive": "1", "Moderately Aggressive": "1",
                     "Balanced": "3", "Moderately Conservative": "8",
                     "Conservative": "8"}
ACCOUNT_TYPES = ["Taxable", "IRA", "Roth IRA", "529", "Trust"]
SECTORS = ["Communication Services", "Consumer Discretionary", "Consumer Staples",
           "Energy", "Financials", "Healthcare", "Industrials", "Materials",
           "Real Estate", "Technology", "Utilities"]
SECURITY_TXN_TYPES = ["Buy", "Sell", "Dividend"]
CASH_TXN_TYPES = ["Deposit", "Withdrawal", "Advisory Fee"]
AUM_FLOOR = 1000.0  # the source system never reports AUM below $1,000


def col(kind, required=True, allowed=None, pattern=None, min=None, max=None,
        gt=None, required_when=None):
    """Column specification. required_when(df) -> mask of rows that need a value."""
    return dict(kind=kind, required=required, allowed=allowed, pattern=pattern,
                min=min, max=max, gt=gt, required_when=required_when)


def _is_etf(df):
    return df["is_etf"] == "True"


def _is_stock(df):
    return df["is_etf"] == "False"


def _is_security_txn(df):
    return df["txn_type"].isin(SECURITY_TXN_TYPES)


# -----------------------------------------------------------------------------
# Expected schema: primary key, natural (business) key, columns
# -----------------------------------------------------------------------------
SCHEMA = {
    "dim_advisor": dict(
        pk="advisor_id", natural_key=["first_name", "last_name"],
        columns=dict(
            advisor_id=col("int", min=1),
            first_name=col("text"), last_name=col("text"),
            region=col("text", allowed=["Northeast", "Mid-Atlantic", "Southeast",
                                        "Midwest", "West", "Southwest"]),
            years_experience=col("int", min=0, max=60),
            aum_target_mm=col("decimal", gt=0, max=10000),
            certifications=col("text", pattern=r"None|(CFA|CFP|CIMA)(, (CFA|CFP|CIMA))*"),
        )),
    "dim_benchmark": dict(
        pk="benchmark_id", natural_key=["name"],
        columns=dict(
            benchmark_id=col("int", min=1), name=col("text"),
            asset_class=col("text", allowed=["Equity", "Fixed Income", "Multi-Asset",
                                             "International", "Small Cap",
                                             "Emerging", "Cash"]),
            ticker_proxy=col("text", pattern=r"[A-Z0-9_]+"),
        )),
    "dim_client": dict(
        pk="client_id",
        # same person: same first name, ZIP, start date and opening balance
        natural_key=["first_name", "zip_code", "client_since", "initial_aum"],
        columns=dict(
            client_id=col("int", min=1), first_name=col("text"), last_name=col("text"),
            age=col("int", min=18, max=110), city=col("text"),
            state=col("text", allowed=sorted(USPS)),
            zip_code=col("text", pattern=r"\d{5}"),
            risk_profile=col("text", allowed=RISK_PROFILES),
            client_tier=col("text", allowed=["Retail", "HNW", "UHNW"]),
            primary_account_type=col("text", allowed=ACCOUNT_TYPES),
            initial_aum=col("decimal", gt=0),
            client_since=col("date", min="1950-01-01", max="2024-12-31"),
            advisor_id=col("int", min=1), is_active=col("bool"),
        )),
    "dim_date": dict(
        pk="date_id", natural_key=["date"],
        columns=dict(
            date_id=col("int", min=1), date=col("date", min="2020-01-01", max="2024-12-31"),
            year=col("int", min=2020, max=2024), quarter=col("int", min=1, max=4),
            month=col("int", min=1, max=12),
            month_name=col("text", allowed=["January", "February", "March", "April",
                                            "May", "June", "July", "August",
                                            "September", "October", "November",
                                            "December"]),
            week_of_year=col("int", min=1, max=53),
            day_of_week=col("text", allowed=["Monday", "Tuesday", "Wednesday",
                                             "Thursday", "Friday", "Saturday",
                                             "Sunday"]),
            is_month_end=col("flag"), is_quarter_end=col("flag"),
            is_year_end=col("flag"), is_trading_day=col("flag"),
        )),
    "dim_security": dict(
        pk="security_id", natural_key=["ticker"],
        columns=dict(
            security_id=col("int", min=1), ticker=col("text", pattern=r"[A-Z]{1,5}"),
            name=col("text"),
            asset_class=col("text", allowed=["Equity", "Fixed Income", "Alternative",
                                             "Cash Equivalent"]),
            sector=col("text", allowed=SECTORS, required_when=_is_stock),
            benchmark_id=col("int", min=1), is_etf=col("bool"),
            expense_ratio_bps=col("decimal", min=0, max=300, required_when=_is_etf),
        )),
    "fact_fees": dict(
        pk="fee_id", natural_key=["client_id", "fee_date"],
        columns=dict(
            fee_id=col("int", min=1), client_id=col("int", min=1),
            advisor_id=col("int", min=1),
            fee_date=col("date", min="2020-01-01", max="2024-12-31"),
            fee_type=col("text", allowed=["Management", "Advisory", "Custodial",
                                          "Performance"]),
            aum_basis=col("decimal", gt=0), bps_charged=col("decimal", gt=0, max=300),
            amount=col("decimal", gt=0),
        )),
    "fact_portfolio_snapshot": dict(
        pk="snapshot_id", natural_key=["client_id", "snapshot_date"],
        columns=dict(
            snapshot_id=col("int", min=1), client_id=col("int", min=1),
            advisor_id=col("int", min=1), benchmark_id=col("int", min=1),
            snapshot_date=col("date", min="2020-01-01", max="2024-12-31"),
            year=col("int", min=2020, max=2024), month=col("int", min=1, max=12),
            aum=col("decimal", min=0),
            return_ytd=col("decimal", min=-1),           # cannot lose more than 100%
            benchmark_return_ytd=col("decimal", min=-1),
            active_alpha_ytd=col("decimal"),             # no natural bound
            cash_pct=col("decimal", min=0, max=1),
            account_type=col("text", allowed=ACCOUNT_TYPES),
        )),
    "fact_transactions": dict(
        pk="txn_id",
        # content fingerprint: the same trade recorded twice
        natural_key=["advisor_id", "security_id", "txn_date", "txn_type",
                     "shares", "price", "amount"],
        columns=dict(
            txn_id=col("int", min=1), client_id=col("int", min=1),
            advisor_id=col("int", min=1),
            security_id=col("int", min=1, required_when=_is_security_txn),
            txn_date=col("date", min="2020-01-01", max="2024-12-31"),
            txn_type=col("text", allowed=SECURITY_TXN_TYPES + CASH_TXN_TYPES),
            shares=col("decimal", gt=0, required_when=_is_security_txn),  # sign rule
            price=col("decimal", gt=0, required_when=_is_security_txn),
            amount=col("decimal", gt=0),
        )),
}

# -----------------------------------------------------------------------------
# Relationships: (child table, child column, parent table, parent column)
# -----------------------------------------------------------------------------
ID_RELATIONSHIPS = [
    ("dim_client", "advisor_id", "dim_advisor", "advisor_id"),
    ("dim_security", "benchmark_id", "dim_benchmark", "benchmark_id"),
    ("fact_fees", "client_id", "dim_client", "client_id"),
    ("fact_fees", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_portfolio_snapshot", "client_id", "dim_client", "client_id"),
    ("fact_portfolio_snapshot", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_portfolio_snapshot", "benchmark_id", "dim_benchmark", "benchmark_id"),
    ("fact_transactions", "client_id", "dim_client", "client_id"),
    ("fact_transactions", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_transactions", "security_id", "dim_security", "security_id"),
]
DATE_RELATIONSHIPS = [
    ("fact_fees", "fee_date", "dim_date", "date"),
    ("fact_portfolio_snapshot", "snapshot_date", "dim_date", "date"),
    ("fact_transactions", "txn_date", "dim_date", "date"),
]
ALL_RELATIONSHIPS = ID_RELATIONSHIPS + DATE_RELATIONSHIPS


# -----------------------------------------------------------------------------
# Column-level rule evaluation (generic: driven by SCHEMA)
# -----------------------------------------------------------------------------
def required_mask(df, spec):
    if spec["required_when"] is not None:
        return spec["required_when"](df)
    return pd.Series(spec["required"], index=df.index)


def column_rule_results(df, table):
    """Yield one dict per (column, rule) with rows checked and rows failing."""
    out = []
    for c, spec in SCHEMA[table]["columns"].items():
        if c not in df.columns:
            out.append(dict(table=table, column=c, rule="column_present",
                            checked=1, failed=1, examples="missing column"))
            continue
        s = df[c]
        blank = blank_mask(s)
        req = required_mask(df, spec)
        nb = ~blank

        def add(rule, checked_mask, fail_mask):
            fail_mask = fail_mask & checked_mask
            ex = ", ".join(s[fail_mask].drop_duplicates().head(5).tolist())
            out.append(dict(table=table, column=c, rule=rule,
                            checked=int(checked_mask.sum()), failed=int(fail_mask.sum()),
                            examples=ex))

        add("completeness", req, blank)
        if spec["required_when"] is not None:   # structural blank: must BE blank otherwise
            add("blank_when_not_applicable", ~req, nb)
        valid = valid_mask(s, spec["kind"]).fillna(False)
        add("type_" + spec["kind"], nb, ~valid)
        if spec["allowed"] is not None:
            add("allowed_values", nb, ~s.isin(spec["allowed"]))
        if spec["pattern"] is not None:
            add("format_pattern", nb, ~s.str.fullmatch(spec["pattern"]).fillna(False))
        if any(spec[k] is not None for k in ("min", "max", "gt")):
            if spec["kind"] == "date":
                v = to_date(s)
                lo = pd.Timestamp(spec["min"]) if spec["min"] else None
                hi = pd.Timestamp(spec["max"]) if spec["max"] else None
            else:
                v = to_num(s)
                lo, hi = spec["min"], spec["max"]
            parsed = v.notna()
            bad = pd.Series(False, index=df.index)
            if lo is not None:
                bad |= v < lo
            if hi is not None:
                bad |= v > hi
            if spec["gt"] is not None:
                bad |= v <= spec["gt"]
            add("range_bound", nb & parsed, bad)
    return out


# -----------------------------------------------------------------------------
# Row-level (single-table) rules: name, severity, function(df) -> (applies, fails)
# -----------------------------------------------------------------------------
def _date_rules():
    def derived(colname, fn):
        def rule(df):
            d = to_date(df["date"])
            ok = d.notna()
            # derive only from parseable dates: one NaT would turn year into
            # '2020.0' for every row (and crash the ISO-week cast)
            expected = pd.Series("", index=df.index)
            expected[ok] = fn(d[ok]).astype(str).values
            return ok, expected.values != df[colname].values
        return rule
    return [
        ("year matches date", "ERROR", derived("year", lambda d: d.dt.year)),
        ("quarter matches date", "ERROR", derived("quarter", lambda d: d.dt.quarter)),
        ("month matches date", "ERROR", derived("month", lambda d: d.dt.month)),
        ("month_name matches date", "ERROR", derived("month_name", lambda d: d.dt.month_name())),
        ("day_of_week matches date", "ERROR", derived("day_of_week", lambda d: d.dt.day_name())),
        ("week_of_year is ISO week", "ERROR",
         derived("week_of_year", lambda d: d.dt.isocalendar().week.astype(int))),
        ("is_month_end matches date", "ERROR",
         derived("is_month_end", lambda d: d.dt.is_month_end.astype(int))),
        ("is_quarter_end matches date", "ERROR",
         derived("is_quarter_end", lambda d: d.dt.is_quarter_end.astype(int))),
        ("is_year_end matches date", "ERROR",
         derived("is_year_end", lambda d: d.dt.is_year_end.astype(int))),
        ("is_trading_day = weekday", "ERROR",
         derived("is_trading_day", lambda d: (d.dt.dayofweek < 5).astype(int))),
    ]


def _client_tier_rule(df):
    a = to_num(df["initial_aum"])
    expected = np.select([a < 500_000, a < 5_000_000], ["Retail", "HNW"], "UHNW")
    return a.notna(), expected != df["client_tier"].values


def _snapshot_year_month(df):
    d = to_date(df["snapshot_date"])
    bad = (d.dt.year.astype("Int64").astype(str) != df["year"]) | \
          (d.dt.month.astype("Int64").astype(str) != df["month"])
    return d.notna(), bad


def _snapshot_first_of_month(df):
    d = to_date(df["snapshot_date"])
    return d.notna(), d.dt.day != 1


def _fee_first_of_month(df):
    d = to_date(df["fee_date"])
    return d.notna(), d.dt.day != 1


def _return_equals_bench_plus_alpha(df):
    r, b, a = to_num(df["return_ytd"]), to_num(df["benchmark_return_ytd"]), to_num(df["active_alpha_ytd"])
    ok = r.notna() & b.notna() & a.notna()
    return ok, (r - b - a).abs() > 1e-5


def _fee_amount_recompute(df):
    basis, bps, amt = to_num(df["aum_basis"]), to_num(df["bps_charged"]), to_num(df["amount"])
    ok = basis.notna() & bps.notna() & amt.notna()
    return ok, ((basis * bps / 10000 / 12).round(2) - amt).abs() > 0.011


def _txn_amount_recompute(df):
    sh, px, amt = to_num(df["shares"]), to_num(df["price"]), to_num(df["amount"])
    ok = sh.notna() & px.notna() & amt.notna()
    return ok, ((sh * px).round(2) - amt).abs() > 0.011


def _txn_amount_recompute_abs(df):
    """Same as above but on |shares|: tells a sign error from a wrong amount."""
    sh, px, amt = to_num(df["shares"]), to_num(df["price"]), to_num(df["amount"])
    ok = sh.notna() & px.notna() & amt.notna()
    return ok, ((sh.abs() * px).round(2) - amt).abs() > 0.011


def _etf_sector_blank(df):
    return _is_etf(df), ~blank_mask(df["sector"])


def _dividend_amount_is_full_value(df):
    """Plausibility: a dividend should be a small % of position value, not 100%."""
    is_div = df["txn_type"] == "Dividend"
    sh, px, amt = to_num(df["shares"]), to_num(df["price"]), to_num(df["amount"])
    ratio = amt / (sh.abs() * px)
    return is_div & ratio.notna(), ratio > 0.25


ROW_RULES = {
    "dim_date": _date_rules(),
    "dim_client": [("client_tier matches initial_aum band (<500K Retail, <5M HNW, else UHNW)",
                    "WARN", _client_tier_rule)],
    "dim_security": [("ETFs have no sector", "WARN", _etf_sector_blank)],
    "fact_fees": [
        ("fee_date is first of month", "ERROR", _fee_first_of_month),
        ("amount = aum_basis x bps / 10000 / 12", "ERROR", _fee_amount_recompute),
    ],
    "fact_portfolio_snapshot": [
        ("year/month match snapshot_date", "ERROR", _snapshot_year_month),
        ("snapshot_date is first of month", "ERROR", _snapshot_first_of_month),
        ("return_ytd = benchmark_return_ytd + active_alpha_ytd", "ERROR",
         _return_equals_bench_plus_alpha),
    ],
    "fact_transactions": [
        ("amount = shares x price", "ERROR", _txn_amount_recompute),
        ("amount = |shares| x price", "ERROR", _txn_amount_recompute_abs),
        ("dividend amount <= 25% of position value", "WARN", _dividend_amount_is_full_value),
    ],
}


def row_rule_results(df, table):
    out = []
    for name, sev, fn in ROW_RULES.get(table, []):
        applies, fails = fn(df)
        applies = pd.Series(applies, index=df.index).fillna(False).astype(bool)
        fails = pd.Series(fails, index=df.index).fillna(False).astype(bool) & applies
        out.append(dict(table=table, rule=name, severity=sev,
                        checked=int(applies.sum()), failed=int(fails.sum()),
                        failed_index=fails))
    return out


# -----------------------------------------------------------------------------
# Cross-table business rules (group 4). Each returns a dict per check.
# Values are parsed defensively so the same checks run on raw and clean data.
# -----------------------------------------------------------------------------
def _norm_id(s):
    """'45.0' -> '45' so a formatting defect does not hide a business-rule result."""
    return s.str.replace(r"\.0+$", "", regex=True)


def cross_table_checks(T):
    out = []

    def add(check, tables, severity, checked, failed, detail="", example=""):
        out.append(dict(check=check, tables=tables, severity=severity if failed else "PASS",
                        checked=int(checked), failed=int(failed), detail=detail,
                        example=str(example)))

    c, s, f, t, d = (T["dim_client"], T["fact_portfolio_snapshot"], T["fact_fees"],
                     T["fact_transactions"], T["dim_date"])
    snap_month = s["snapshot_date"]
    txn_month = t["txn_date"].str[:7] + "-01"

    # 1. Fee basis must equal the AUM in the snapshot for the same client-month
    m = f.merge(s[["client_id", "snapshot_date", "aum"]], how="left",
                left_on=["client_id", "fee_date"], right_on=["client_id", "snapshot_date"])
    has = m["aum"].notna()
    bad = has & ((to_num(m["aum_basis"]) - to_num(m["aum"].fillna(""))).abs() > 0.005)
    add("fee aum_basis = snapshot aum for same client-month", "fact_fees ~ fact_portfolio_snapshot",
        "ERROR", has.sum(), bad.sum(), f"{int((~has).sum())} fee rows have no snapshot that month",
        m.loc[bad, "fee_id"].head(3).tolist())

    # 2. Every fact row carries the client's assigned advisor
    adv = c.set_index("client_id")["advisor_id"]
    for name, df in [("fact_fees", f), ("fact_portfolio_snapshot", s), ("fact_transactions", t)]:
        exp = df["client_id"].map(adv)
        chk = exp.notna()
        bad = chk & (exp != df["advisor_id"])
        add(f"{name}.advisor_id = dim_client.advisor_id", f"{name} ~ dim_client", "ERROR",
            chk.sum(), bad.sum())

    # 3. Snapshot account type = client's primary account type
    exp = s["client_id"].map(c.set_index("client_id")["primary_account_type"])
    chk = exp.notna()
    add("snapshot account_type = client primary_account_type",
        "fact_portfolio_snapshot ~ dim_client", "ERROR", chk.sum(), (chk & (exp != s["account_type"])).sum())

    # 4. Snapshot benchmark follows the client's risk profile
    rp = s["client_id"].map(c.set_index("client_id")["risk_profile"])
    exp = rp.map(RISK_TO_BENCHMARK)
    chk = exp.notna()
    add("snapshot benchmark_id matches risk profile (Aggr/ModAggr->1, Balanced->3, Cons/ModCons->8)",
        "fact_portfolio_snapshot ~ dim_client", "ERROR", chk.sum(), (chk & (exp != s["benchmark_id"])).sum())
    blank_rp = rp.fillna("x").str.strip() == ""
    if blank_rp.any():
        dist = s.loc[blank_rp, "benchmark_id"].value_counts().to_dict()
        n_cli = s.loc[blank_rp, "client_id"].nunique()
        expected_share = (c["risk_profile"] == "Balanced").sum() / max((c["risk_profile"].str.strip() != "").sum(), 1)
        add("benchmark of clients with NO risk profile", "fact_portfolio_snapshot ~ dim_client", "WARN",
            blank_rp.sum(), blank_rp.sum(),
            f"{n_cli} clients without a profile; snapshot benchmark_id counts {dist}. "
            f"If the profile were merely unrecorded, only ~{expected_share:.0%} would be on "
            f"benchmark 3, so 3 looks like a system default, not evidence of the profile")

    # 5. No activity before the client relationship started
    since = c.set_index("client_id")["client_since"].str[:7] + "-01"
    for name, df, dcol in [("fact_fees", f, "fee_date"), ("fact_portfolio_snapshot", s, "snapshot_date"),
                           ("fact_transactions", t, "txn_date")]:
        st = df["client_id"].map(since)
        chk = st.notna()
        bad = chk & (df[dcol].str[:7] + "-01" < st)
        add(f"{name} dated before client_since month", f"{name} ~ dim_client", "ERROR", chk.sum(), bad.sum())

    # 6. Transactions after the client's last snapshot (account closed)
    last = s.groupby("client_id")["snapshot_date"].max()
    lt = t["client_id"].map(last)
    chk = lt.notna()
    bad = chk & (txn_month > lt)
    add("transactions in a month after the client's last snapshot (closed account)",
        "fact_transactions ~ fact_portfolio_snapshot ~ dim_client", "WARN", chk.sum(), bad.sum(),
        f"{t.loc[bad, 'client_id'].nunique()} clients; "
        f"all inactive: {bool(t.loc[bad, 'client_id'].map(c.set_index('client_id')['is_active']).eq('False').all())}",
        t.loc[bad, "txn_id"].head(3).tolist())

    # 7. is_active flag agrees with snapshot coverage
    end = s["snapshot_date"].max()
    cl = c.assign(last=c["client_id"].map(last))
    has_snap = cl["last"].notna()
    bad = has_snap & (((cl["is_active"] == "True") & (cl["last"] < end)) |
                      ((cl["is_active"] == "False") & (cl["last"] == end)))
    add("is_active agrees with snapshots (active clients reported through the last month)",
        "dim_client ~ fact_portfolio_snapshot", "ERROR", has_snap.sum(), bad.sum())

    # 8. Dimension members with no facts
    used = set(f["client_id"]) | set(s["client_id"]) | set(t["client_id"])
    nofacts = ~c["client_id"].isin(used)
    add("clients with no fees, snapshots or transactions", "dim_client ~ facts", "WARN",
        len(c), nofacts.sum(), "", c.loc[nofacts, "client_id"].head(5).tolist())
    used_b = set(s["benchmark_id"]) | set(T["dim_security"]["benchmark_id"])
    unused_b = ~T["dim_benchmark"]["benchmark_id"].isin(used_b)
    add("benchmarks not used by any snapshot or security", "dim_benchmark ~ facts", "INFO",
        len(T["dim_benchmark"]), unused_b.sum(), "", T["dim_benchmark"].loc[unused_b, "name"].tolist())
    unused_b2 = ~T["dim_benchmark"]["benchmark_id"].isin(set(s["benchmark_id"]))
    add("benchmarks never used as a client portfolio benchmark", "dim_benchmark ~ fact_portfolio_snapshot",
        "INFO", len(T["dim_benchmark"]), unused_b2.sum(), "",
        T["dim_benchmark"].loc[unused_b2, "name"].tolist())

    # 9. Trades on non-trading days
    trading = d.set_index("date")["is_trading_day"]
    is_trade = t["txn_type"].isin(["Buy", "Sell"])
    nt = t["txn_date"].map(trading) == "0"
    add("Buy/Sell dated on a non-trading day (weekend)", "fact_transactions ~ dim_date", "WARN",
        is_trade.sum(), (is_trade & nt).sum(),
        f"all transaction types on weekends: {int(nt.sum())} of {len(t)} "
        f"({nt.mean():.1%}); weekends are {(trading == '0').mean():.1%} of calendar days")

    # 10. Snapshot months with no fee
    fk = set(zip(f["client_id"], f["fee_date"]))
    nofee = pd.Series([(a, b) not in fk for a, b in zip(s["client_id"], snap_month)], index=s.index)
    add("snapshot client-months with no fee charged", "fact_portfolio_snapshot ~ fact_fees", "INFO",
        len(s), nofee.sum(), f"{s.loc[nofee, 'client_id'].nunique()} clients affected")

    # 11. Advisory-fee debits in transactions vs the fee table
    af = t[t["txn_type"] == "Advisory Fee"].assign(a=lambda x: to_num(x["amount"]),
                                                    mo=lambda x: x["txn_date"].str[:7] + "-01")
    a_cm = af.groupby(["client_id", "mo"])["a"].sum()
    f_cm = f.assign(a=to_num(f["amount"])).groupby(["client_id", "fee_date"])["a"].sum()
    f_cm.index.names = ["client_id", "mo"]
    j = pd.concat([a_cm.rename("txn"), f_cm.rename("fee")], axis=1)
    both = j.dropna()
    add("Advisory Fee transactions = fee table amount (same client-month)",
        "fact_transactions ~ fact_fees", "WARN", len(both), ((both["txn"] - both["fee"]).abs() > 0.01).sum(),
        f"advisory-fee txns total ${af['a'].sum():,.2f} vs fee table total ${to_num(f['amount']).sum():,.2f}; "
        f"{int(j['fee'].isna().sum())} txn client-months have no fee row; median txn/fee ratio "
        f"{(both['txn'] / both['fee']).median():.2f}")

    # 12. AUM movements explained by deposits/withdrawals?
    sn = s.assign(aumn=to_num(s["aum"])).sort_values(["client_id", "snapshot_date"])
    sn["chg"] = sn.groupby("client_id")["aumn"].diff()
    sn["prev"] = sn.groupby("client_id")["aumn"].shift()
    tt = t.assign(a=to_num(t["amount"]), mo=txn_month)
    tt["flow"] = np.where(tt["txn_type"] == "Deposit", tt["a"],
                          np.where(tt["txn_type"] == "Withdrawal", -tt["a"], 0.0))
    flow = tt.groupby(["client_id", "mo"])["flow"].sum()
    sn["flow"] = pd.Series(list(zip(sn["client_id"], sn["snapshot_date"]))).map(flow).fillna(0).values
    x = sn.dropna(subset=["chg"])
    jumps = x[x["chg"].abs() > 0.5 * x["prev"]]
    corr = np.corrcoef(x["chg"], x["flow"])[0, 1] if len(x) > 2 else np.nan
    add("month-to-month AUM jumps > 50% are explained by net deposits/withdrawals",
        "fact_portfolio_snapshot ~ fact_transactions", "WARN", len(x),
        (jumps["flow"].abs() < 0.5 * jumps["chg"].abs()).sum(),
        f"correlation of monthly AUM change with net deposits-withdrawals = {corr:.4f}; "
        f"{len(jumps)} jumps > 50%")
    return out


def load_ri_function():
    """Return check_referential_integrity() from 03_validate.py (the one copy)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "validate_mod", Path(__file__).resolve().parent / "03_validate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.check_referential_integrity
