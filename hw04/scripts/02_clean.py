# =============================================================================
# Script:      02_clean.py
# Assignment:  HW4 - Cleaning the Wildcat Capital Data (Part C)
# Author:      Aiden James Dumm
# Generated:   2026-10-19
# Description: Implements decision_log.md. Reads the 8 raw tables as text,
#              applies one transformation at a time (each printed, logged and
#              asserted), and writes a NEW set of 8 tables to data/clean/.
#              The raw files are never modified. Removed rows go to
#              data/audit/quarantine_*.csv; every action goes to
#              data/audit/cleaning_log.csv and every changed cell to
#              data/audit/value_changes.csv.
# Run from the repository root:  python hw04/scripts/02_clean.py
# =============================================================================

import pandas as pd

from dq_common import (AUDIT_DIR, AUM_FLOOR, CLEAN_DIR, RAW_DIR, SCHEMA, STATE_NAME_TO_CODE,
                       TABLES, USPS, blank_mask, load_ri_function, load_tables, to_date,
                       to_num)

check_referential_integrity = load_ri_function()

CLEANING_LOG = []
VALUE_CHANGES = []
QUARANTINE = {}   # (table, reason) -> DataFrame


# -----------------------------------------------------------------------------
# Audit-trail helpers
# -----------------------------------------------------------------------------
def log(table, decision, issue, action, rows, note=""):
    CLEANING_LOG.append(dict(table=table, decision_id=decision, issue=issue, action=action,
                             rows_affected=int(rows), note=note))
    print(f"   -> logged: {action} | {rows:,} rows")


def record_changes(table, df, mask, column, new_values):
    pk = SCHEMA[table]["pk"]
    VALUE_CHANGES.append(pd.DataFrame({
        "table": table, "key_column": pk, "key": df.loc[mask, pk].values,
        "column": column, "old_value": df.loc[mask, column].values,
        "new_value": pd.Series(new_values, index=df.index)[mask].values,
    }))


def step(title):
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78)


def fmt_decimal(x, places=6):
    s = f"{x:.{places}f}".rstrip("0").rstrip(".")
    return "0.0" if s in ("-0", "0", "") else (s if "." in s else s + ".0")


# -----------------------------------------------------------------------------
# D01 - duplicate clients
# -----------------------------------------------------------------------------
def d01_duplicate_clients(C):
    step("D01 dim_client: quarantine near-duplicate clients")
    c = C["dim_client"]
    same = [x for x in c.columns if x not in ("client_id", "last_name")]
    is_copy = c.duplicated(same, keep="first")
    print(f"   before: {len(c):,} clients, {is_copy.sum()} rows repeat another client on {len(same)} columns")

    copies = c[is_copy].merge(
        c[~is_copy][same + ["client_id", "last_name"]].rename(
            columns={"client_id": "original_client_id", "last_name": "original_last_name"}),
        on=same, how="left")
    # verify before removing
    assert copies["original_client_id"].notna().all(), "a copy has no original"
    one_char_off = [(a == b[:-1]) or (a[:-1] == b)   # last letter dropped or added
                    for a, b in zip(copies["last_name"], copies["original_last_name"])]
    assert all(one_char_off), "copy last name differs from the original by more than one end letter"
    assert (copies["client_id"].astype(int) > copies["original_client_id"].astype(int)).all()
    fact_refs = sum(C[t]["client_id"].isin(copies["client_id"]).sum()
                    for t in ("fact_fees", "fact_portfolio_snapshot", "fact_transactions"))
    assert fact_refs == 0, f"{fact_refs} fact rows reference a duplicate client"
    print(f"   verified: all {len(copies)} copies differ from the original only by one letter "
          f"at the end of the last name ({sum(a == b[:-1] for a, b in zip(copies['last_name'], copies['original_last_name']))} dropped, "
          f"{sum(a[:-1] == b for a, b in zip(copies['last_name'], copies['original_last_name']))} added); "
          f"0 fact rows reference them")

    copies["quarantine_reason"] = "D01 duplicate of original_client_id (last name off by one end letter)"
    QUARANTINE[("dim_client", "duplicates")] = copies
    C["dim_client"] = c[~is_copy].copy()
    after = C["dim_client"]
    assert len(after) == len(c) - len(copies)
    assert not after.duplicated(SCHEMA["dim_client"]["natural_key"]).any()
    assert after["client_id"].is_unique
    print(f"   after : {len(after):,} clients, 0 natural-key duplicates")
    log("dim_client", "D01", "25 near-duplicate clients (last name off by one letter, no activity)",
        "quarantine", len(copies), "quarantine_dim_client_duplicates.csv keeps original_client_id")


# -----------------------------------------------------------------------------
# D02 - state names -> USPS codes
# -----------------------------------------------------------------------------
def d02_state_codes(C):
    step("D02 dim_client.state: standardize full names to USPS codes")
    c = C["dim_client"]
    bad = ~c["state"].isin(USPS)
    print(f"   before: {bad.sum()} non-code values {c.loc[bad, 'state'].value_counts().to_dict()}; "
          f"PA count {int((c['state'] == 'PA').sum())}")
    new = c["state"].where(~bad, c["state"].map(STATE_NAME_TO_CODE))
    assert new[bad].notna().all(), "unmapped state name"
    # round-trip check: the code maps back to the original name
    code_to_name = {v: k for k, v in STATE_NAME_TO_CODE.items()}
    assert (new[bad].map(code_to_name) == c.loc[bad, "state"]).all()
    record_changes("dim_client", c, bad, "state", new)
    n = int(bad.sum())
    c["state"] = new
    assert c["state"].isin(USPS).all()
    print(f"   after : 0 non-code values; PA count {int((c['state'] == 'PA').sum())}")
    log("dim_client", "D02", "full state names among USPS codes (78 in raw; 1 was on a quarantined duplicate)", "standardize", n,
        "explicit name->code map; round-trip verified")


# -----------------------------------------------------------------------------
# D03 - flag missing risk profile (do NOT fill)
# -----------------------------------------------------------------------------
def d03_risk_profile_flag(C):
    step("D03 dim_client.risk_profile: flag blanks, do not fill")
    c = C["dim_client"]
    blank = blank_mask(c["risk_profile"])
    c["risk_profile_missing"] = blank.astype(int)
    assert c["risk_profile_missing"].sum() == blank.sum()
    assert (c.loc[c["risk_profile_missing"] == 1, "risk_profile"] == "").all()
    print(f"   {blank.sum()} clients flagged; risk_profile values unchanged")
    log("dim_client", "D03", "blank risk_profile (benchmark 3 is a default, not evidence)",
        "flag risk_profile_missing", blank.sum(), "values left blank")


# -----------------------------------------------------------------------------
# D11 - security_id '45.0' -> '45'
# -----------------------------------------------------------------------------
def d11_security_id_format(C):
    step("D11 fact_transactions.security_id: '45.0' -> '45'")
    t = C["fact_transactions"]
    before = check_referential_integrity(t, "security_id", C["dim_security"], "security_id")
    nb = ~blank_mask(t["security_id"])
    assert t.loc[nb, "security_id"].str.fullmatch(r"\d+(\.0+)?").all(), \
        "a security_id has a non-zero decimal part - converting would lose information"
    new = t["security_id"].str.replace(r"\.0+$", "", regex=True)
    changed = new != t["security_id"]
    print(f"   before: match rate {before['match_rate']:.2%}, orphan rows {before['orphan_row_count']:,}")
    record_changes("fact_transactions", t, changed, "security_id", new)
    t["security_id"] = new
    after = check_referential_integrity(t, "security_id", C["dim_security"], "security_id")
    assert after["match_rate"] == 1.0 and after["orphan_row_count"] == 0
    assert after["null_key_rows"] == before["null_key_rows"]  # blanks untouched
    print(f"   after : match rate {after['match_rate']:.2%}, orphan rows 0, "
          f"blank keys unchanged ({after['null_key_rows']:,})")
    log("fact_transactions", "D11", "security_id stored as decimal text breaks join",
        "convert to integer text", changed.sum(), "every fractional part was .0 (asserted)")


# -----------------------------------------------------------------------------
# D12 - orphan client_ids that duplicate valid transactions
# -----------------------------------------------------------------------------
def d12_orphan_transactions(C, R):
    step("D12 fact_transactions.client_id: quarantine orphan duplicates")
    t = C["fact_transactions"]
    res = check_referential_integrity(t, "client_id", C["dim_client"], "client_id")
    orphans = res["orphan_rows"]
    print(f"   before: {res['orphan_row_count']} orphan rows, {res['distinct_orphan_keys']} "
          f"distinct client_ids, match rate {res['match_rate']:.4%}")
    same = [x for x in t.columns if x not in ("txn_id", "client_id")]
    valid = t[~t.index.isin(orphans.index)]
    m = orphans.merge(valid[same + ["txn_id", "client_id"]].rename(
        columns={"txn_id": "copy_of_txn_id", "client_id": "copy_of_client_id"}), on=same, how="left")
    assert len(m) == len(orphans), "an orphan matches more than one valid transaction"
    assert m["copy_of_txn_id"].notna().all(), "an orphan is not a copy of a valid transaction"
    assert m["copy_of_txn_id"].is_unique, "two orphans copy the same valid transaction (not 1-to-1)"
    print(f"   verified: each of the {len(m)} orphans is a 1-to-1 copy of a valid transaction "
          f"(${to_num(m['amount']).sum():,.2f} total)")
    m["quarantine_reason"] = "D12 client_id not in dim_client; exact copy of copy_of_txn_id"
    # store the rows exactly as they arrived (before the D11 key-format fix)
    raw_rows = R["fact_transactions"].loc[orphans.index].reset_index(drop=True)
    assert (raw_rows["txn_id"].values == m["txn_id"].values).all()
    m = pd.concat([raw_rows, m[["copy_of_txn_id", "copy_of_client_id", "quarantine_reason"]]], axis=1)
    QUARANTINE[("fact_transactions", "orphan_duplicates")] = m
    C["fact_transactions"] = t[~t.index.isin(orphans.index)].copy()
    after = check_referential_integrity(C["fact_transactions"], "client_id", C["dim_client"], "client_id")
    assert after["orphan_row_count"] == 0 and len(C["fact_transactions"]) == len(t) - len(m)
    print(f"   after : {len(C['fact_transactions']):,} rows, match rate {after['match_rate']:.2%}")
    log("fact_transactions", "D12", "200 transactions with client_id not in dim_client",
        "quarantine", len(m), "each is a verified copy of a valid transaction")


# -----------------------------------------------------------------------------
# D13 - negative shares on Buys
# -----------------------------------------------------------------------------
def d13_negative_shares(C):
    step("D13 fact_transactions.shares: fix sign on Buys")
    t = C["fact_transactions"]
    sh, px, amt = to_num(t["shares"]), to_num(t["price"]), to_num(t["amount"])
    neg = sh < 0
    print(f"   before: {neg.sum()} negative share values, types {t.loc[neg, 'txn_type'].value_counts().to_dict()}")
    assert (t.loc[neg, "txn_type"] == "Buy").all()
    # reconcile: the stored amount must equal |shares| x price for every row we change
    assert (((sh[neg].abs() * px[neg]).round(2) - amt[neg]).abs() <= 0.011).all()
    new = t["shares"].str.lstrip("-")
    record_changes("fact_transactions", t, neg, "shares", new)
    t["shares"] = new
    sh2 = to_num(t["shares"])
    sec = sh2.notna()
    mismatch = (((sh2 * px).round(2) - amt).abs() > 0.011) & sec
    assert (sh2[sec] > 0).all() and mismatch.sum() == 0
    print(f"   after : 0 negative shares; amount = shares x price holds on all {sec.sum():,} security rows")
    log("fact_transactions", "D13", "Buys with negative shares (amount = |shares| x price); 836 in raw, 1 was a quarantined copy",
        "convert to absolute value", neg.sum(), "amount reconciliation asserted on all security rows")


# -----------------------------------------------------------------------------
# D20 - return_ytd stored as '9.28%'
# -----------------------------------------------------------------------------
def d20_percent_returns(C):
    step("D20 fact_portfolio_snapshot.return_ytd: percent text -> fraction")
    s = C["fact_portfolio_snapshot"]
    pct = s["return_ytd"].str.endswith("%")
    b, a = to_num(s["benchmark_return_ytd"]), to_num(s["active_alpha_ytd"])
    from_pct = to_num(s["return_ytd"].str.rstrip("%")) / 100
    recomputed = (b + a).round(6)
    gap = (recomputed - from_pct)[pct].abs()
    print(f"   before: {pct.sum()} percent strings, e.g. {s.loc[pct, 'return_ytd'].head(3).tolist()}")
    assert gap.max() <= 0.00005 + 1e-12, f"benchmark+alpha disagrees with percent text by {gap.max()}"
    print(f"   verified: benchmark + alpha agrees with percent/100 on all {pct.sum()} rows "
          f"(max gap {gap.max():.6f} <= 0.00005)")
    new = s["return_ytd"].copy()
    new[pct] = recomputed[pct].map(fmt_decimal)
    record_changes("fact_portfolio_snapshot", s, pct, "return_ytd", new)
    s["return_ytd"] = new
    r = to_num(s["return_ytd"])
    assert r.notna().all()
    assert ((r - b - a).abs() <= 1e-5).all()
    print(f"   after : 0 non-numeric values; e.g. {s.loc[pct, 'return_ytd'].head(3).tolist()}; "
          f"return = benchmark + alpha on all {len(s):,} rows")
    log("fact_portfolio_snapshot", "D20", "return_ytd stored as percent text",
        "convert (recompute benchmark + alpha, confirmed by percent/100)", pct.sum(), "")


# -----------------------------------------------------------------------------
# Flags (computed on final values)
# -----------------------------------------------------------------------------
def flags(C):
    step("D14/D15/D22/D23 flag columns")
    t, s, f = C["fact_transactions"], C["fact_portfolio_snapshot"], C["fact_fees"]
    c, d = C["dim_client"], C["dim_date"]

    # D14 trades on non-trading days
    trading = t["txn_date"].map(d.set_index("date")["is_trading_day"])
    flag = (t["txn_type"].isin(["Buy", "Sell"]) & (trading == "0")).astype(int)
    # independent check in both directions: every flagged row is a Sat/Sun and
    # no weekend Buy/Sell was missed (e.g. a txn_date missing from dim_date)
    weekend = to_date(t["txn_date"]).dt.dayofweek >= 5
    assert (flag == (t["txn_type"].isin(["Buy", "Sell"]) & weekend).astype(int)).all(), \
        "weekend flag disagrees with the calendar"
    t["trade_on_non_trading_day"] = flag
    print(f"   D14 trade_on_non_trading_day : {flag.sum():,} Buy/Sell rows (all verified Sat/Sun)")
    log("fact_transactions", "D14", "Buy/Sell on weekend", "flag trade_on_non_trading_day", flag.sum())

    # D15 transactions after the client's last snapshot
    last = s.groupby("client_id")["snapshot_date"].max()
    month = t["txn_date"].str[:7] + "-01"
    flag = (month > t["client_id"].map(last)).astype(int)
    active = t.loc[flag == 1, "client_id"].map(c.set_index("client_id")["is_active"])
    assert (active == "False").all(), "an active client was flagged as closed"
    t["after_account_closed"] = flag
    print(f"   D15 after_account_closed      : {flag.sum():,} rows, "
          f"{t.loc[flag == 1, 'client_id'].nunique()} clients, all is_active=False")
    log("fact_transactions", "D15", "transactions after client's last snapshot (inactive)",
        "flag after_account_closed", flag.sum())

    # D22 AUM floor
    aum, basis = to_num(s["aum"]), to_num(f["aum_basis"])
    assert aum.min() >= AUM_FLOOR and basis.min() >= AUM_FLOOR
    s["aum_at_floor"] = (aum == AUM_FLOOR).astype(int)
    f["aum_basis_at_floor"] = (basis == AUM_FLOOR).astype(int)
    print(f"   D22 aum_at_floor              : {s['aum_at_floor'].sum()} snapshots; "
          f"aum_basis_at_floor: {f['aum_basis_at_floor'].sum()} fees")
    log("fact_portfolio_snapshot", "D22", "AUM at $1,000 floor", "flag aum_at_floor", s["aum_at_floor"].sum())
    log("fact_fees", "D22", "fee basis at $1,000 floor", "flag aum_basis_at_floor", f["aum_basis_at_floor"].sum())

    # D23 implausible YTD returns
    r = to_num(s["return_ytd"])
    s["return_ytd_suspect"] = ((r > 1.0) | (r < -0.9)).astype(int)
    flagged = s["return_ytd_suspect"] == 1
    # every unflagged value is numeric and inside [-0.9, 1.0] (a NaN would fail here)
    assert r[~flagged].between(-0.9, 1.0).all(), "an unflagged return is outside the band or not numeric"
    # flagged values are kept, and they are internally consistent (decision log D23)
    b, a = to_num(s["benchmark_return_ytd"]), to_num(s["active_alpha_ytd"])
    assert ((r - b - a).abs() <= 1e-5)[flagged].all()
    print(f"   D23 return_ytd_suspect        : {s['return_ytd_suspect'].sum():,} snapshots "
          f"({(r > 1.0).sum()} > +100%, {(r < -0.9).sum()} < -90%), "
          f"{s.loc[s['return_ytd_suspect'] == 1, 'client_id'].nunique()} clients")
    log("fact_portfolio_snapshot", "D23", "YTD return > +100% or < -90%", "flag return_ytd_suspect",
        s["return_ytd_suspect"].sum())


def unchanged_tables(C, R):
    step("Tables with no changes (decisions D04-D10, D16-D19, D21, D24-D27: leave as is)")
    for t in ("dim_advisor", "dim_benchmark", "dim_date", "dim_security"):
        assert C[t].equals(R[t])
        print(f"   {t:<16} identical to raw ({len(C[t]):,} rows)")
        log(t, "-", "no defects requiring change", "none", 0, "passed through unchanged")


# -----------------------------------------------------------------------------
def main():
    R = load_tables(RAW_DIR)
    C = {t: df.copy() for t, df in R.items()}
    print("raw rows: " + ", ".join(f"{t} {len(df):,}" for t, df in R.items()))

    d01_duplicate_clients(C)
    d02_state_codes(C)
    d03_risk_profile_flag(C)
    d11_security_id_format(C)
    d12_orphan_transactions(C, R)
    d13_negative_shares(C)
    d20_percent_returns(C)
    flags(C)
    unchanged_tables(C, R)

    # ----- raw = clean + quarantined, same columns, unique keys --------------
    step("Row reconciliation: raw = clean + quarantined")
    recon = []
    for t in TABLES:
        q = sum(len(df) for (tt, _), df in QUARANTINE.items() if tt == t)
        ok = len(R[t]) == len(C[t]) + q
        recon.append((t, len(R[t]), len(C[t]), q, ok))
        print(f"   {t:<26} raw {len(R[t]):>8,} = clean {len(C[t]):>8,} + quarantined {q:>4}  {'OK' if ok else 'FAIL'}")
        assert ok, t
        # same check on the keys: every raw row is in clean or quarantine, exactly once
        pk = SCHEMA[t]["pk"]
        q_keys = [df[pk] for (tt, _), df in QUARANTINE.items() if tt == t]
        kept_or_q = pd.concat([C[t][pk]] + q_keys, ignore_index=True)
        assert kept_or_q.is_unique and set(kept_or_q) == set(R[t][pk]), f"{t} keys do not reconcile"
        assert list(C[t].columns[:R[t].shape[1]]) == list(R[t].columns), f"{t} columns changed"
        added = list(C[t].columns[R[t].shape[1]:])
        for a in added:
            assert set(C[t][a].unique()) <= {0, 1}, f"{t}.{a} is not 0/1"
        assert C[t][SCHEMA[t]["pk"]].is_unique

    # ----- write outputs -------------------------------------------------------
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    for t in TABLES:
        C[t].to_csv(CLEAN_DIR / f"{t}.csv", index=False)
    for (t, reason), df in QUARANTINE.items():
        df.to_csv(AUDIT_DIR / f"quarantine_{t}_{reason}.csv", index=False)
    pd.DataFrame(CLEANING_LOG).to_csv(AUDIT_DIR / "cleaning_log.csv", index=False)
    vc = pd.concat(VALUE_CHANGES, ignore_index=True)
    vc.to_csv(AUDIT_DIR / "value_changes.csv", index=False)

    # re-read what was written and confirm it round-trips
    for t in TABLES:
        back = pd.read_csv(CLEAN_DIR / f"{t}.csv", dtype=str, keep_default_na=False)
        assert back.shape == C[t].shape, f"{t} did not round-trip"
    print(f"\nwrote 8 clean tables to {CLEAN_DIR.relative_to(CLEAN_DIR.parents[2])}")
    print(f"cleaning_log.csv: {len(CLEANING_LOG)} actions | value_changes.csv: {len(vc):,} cell changes "
          f"{vc.groupby(['table', 'column']).size().to_dict()}")
    print(f"quarantine files: " + ", ".join(f"quarantine_{t}_{r}.csv ({len(df)})" for (t, r), df in QUARANTINE.items()))


if __name__ == "__main__":
    main()
