# =============================================================================
# Script:      03_validate.py
# Assignment:  HW4 - Cleaning the Wildcat Capital Data (Part D)
# Author:      Aiden James Dumm
# Generated:   2026-10-19
# Description: Referential integrity, business-rule validation,
#              cross-table reconciliations and IQR outlier flags, run on BOTH
#              the raw and the clean tables. Saves
#              reports/data_quality_scorecard.csv.
# Run from the repository root:  python hw04/scripts/03_validate.py
# =============================================================================

import pandas as pd


# -----------------------------------------------------------------------------
# Reusable referential-integrity check (kept for Assignment 5)
# -----------------------------------------------------------------------------
def check_referential_integrity(fact_df, fact_key, dim_df, dim_key):
    """Check that every value of fact_df[fact_key] exists in dim_df[dim_key].

    Keys are compared as text (the way a BI join compares them), so a key
    stored as '45.0' does NOT match '45'. Leading/trailing spaces are trimmed
    first (01_profile.py reports whitespace separately). Blank keys are
    counted separately and are not orphans.

    Returns a dict with:
        rows                  rows in the fact table
        null_key_rows         rows whose key is blank
        null_key_rate         null_key_rows / rows
        match_rate            matched rows / non-blank rows (1.0 if none)
        orphan_row_count      non-blank keys with no parent
        distinct_orphan_keys  number of distinct orphan key values
        orphan_key_examples   up to 5 orphan key values
        orphan_rows           the orphan rows themselves (DataFrame)
    """
    fk = fact_df[fact_key].fillna("").astype(str).str.strip()
    parent = set(dim_df[dim_key].fillna("").astype(str).str.strip())
    is_null = fk == ""
    matched = ~is_null & fk.isin(parent)
    orphan = ~is_null & ~matched
    n, non_null = len(fact_df), int((~is_null).sum())
    return {
        "rows": n,
        "null_key_rows": int(is_null.sum()),
        "null_key_rate": float(is_null.sum() / n) if n else 0.0,
        "match_rate": float(matched.sum() / non_null) if non_null else 1.0,
        "orphan_row_count": int(orphan.sum()),
        "distinct_orphan_keys": int(fk[orphan].nunique()),
        "orphan_key_examples": sorted(fk[orphan].unique().tolist())[:5],
        "orphan_rows": fact_df[orphan],
    }


# =============================================================================
# Everything below runs the checks on raw and clean data
# =============================================================================
import numpy as np  # noqa: E402

from dq_common import (ALL_RELATIONSHIPS, CLEAN_DIR, RAW_DIR, REPORTS_DIR, SCHEMA,  # noqa: E402
                       TABLES, blank_mask, column_rule_results, load_tables,
                       required_mask, row_rule_results, to_num, valid_mask)

STAGES = {"raw": RAW_DIR, "clean": CLEAN_DIR}
BOUND_RULES = ("allowed_values", "format_pattern", "range_bound")


# -----------------------------------------------------------------------------
# 1. Referential integrity on every relationship
# -----------------------------------------------------------------------------
def run_ri(T, stage):
    rows = []
    for child, ck, parent, pk in ALL_RELATIONSHIPS:
        r = check_referential_integrity(T[child], ck, T[parent], pk)
        rows.append(dict(stage=stage, relationship=f"{child}.{ck} -> {parent}.{pk}",
                         child_table=child, rows=r["rows"], non_null_keys=r["rows"] - r["null_key_rows"],
                         match_rate_pct=round(r["match_rate"] * 100, 4),
                         orphan_rows=r["orphan_row_count"], distinct_orphan_keys=r["distinct_orphan_keys"],
                         null_key_rate_pct=round(r["null_key_rate"] * 100, 2),
                         orphan_key_examples=" ".join(r["orphan_key_examples"])))
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# 2. Business-rule checks (bounds, code lists, sign rules, row rules)
# -----------------------------------------------------------------------------
def run_rules(T, stage):
    rows = []
    for t in TABLES:
        for r in column_rule_results(T[t], t):
            if r["rule"] in BOUND_RULES:
                rows.append(dict(stage=stage, table=t, column=r["column"], rule=r["rule"],
                                 checked=r["checked"], failed=r["failed"], examples=r["examples"]))
        for r in row_rule_results(T[t], t):
            rows.append(dict(stage=stage, table=t, column="(row rule)", rule=r["rule"],
                             checked=r["checked"], failed=r["failed"], examples=""))
    df = pd.DataFrame(rows)
    df["pass_rate_pct"] = np.where(df["checked"] > 0,
                                   (1 - df["failed"] / df["checked"].clip(lower=1)) * 100, 100).round(3)
    return df


# -----------------------------------------------------------------------------
# 3. Cross-table / recomputation reconciliations
# -----------------------------------------------------------------------------
def run_reconciliations(T, stage):
    out = []
    t, f, s = T["fact_transactions"], T["fact_fees"], T["fact_portfolio_snapshot"]

    def add(name, n_checked, n_match, stored_total, recomputed_total, note=""):
        out.append(dict(stage=stage, reconciliation=name, rows_compared=int(n_checked),
                        rows_matching=int(n_match), match_pct=round(n_match / n_checked * 100, 4) if n_checked else 0,
                        stored_total=round(stored_total, 2), recomputed_total=round(recomputed_total, 2),
                        difference=round(stored_total - recomputed_total, 2), note=note))

    # R1 transaction amount vs shares x price
    sh, px, amt = to_num(t["shares"]), to_num(t["price"]), to_num(t["amount"])
    m = sh.notna() & px.notna()
    calc = (sh * px).round(2)
    add("R1 fact_transactions: amount vs shares x price (Buy/Sell/Dividend)", m.sum(),
        ((calc - amt).abs() <= 0.011)[m].sum(), amt[m].sum(), calc[m].sum())

    # R2 fee amount vs aum_basis x bps / 10000 / 12
    basis, bps, famt = to_num(f["aum_basis"]), to_num(f["bps_charged"]), to_num(f["amount"])
    calc = (basis * bps / 10000 / 12).round(2)
    add("R2 fact_fees: amount vs aum_basis x bps / 10000 / 12", len(f),
        ((calc - famt).abs() <= 0.011).sum(), famt.sum(), calc.sum())

    # R3 fee aum_basis vs snapshot aum (two tables, same fact)
    mm = f.merge(s[["client_id", "snapshot_date", "aum"]], how="left",
                 left_on=["client_id", "fee_date"], right_on=["client_id", "snapshot_date"])
    a_snap = to_num(mm["aum"].fillna(""))
    add("R3 fact_fees.aum_basis vs fact_portfolio_snapshot.aum (same client-month)", len(mm),
        ((to_num(mm["aum_basis"]) - a_snap).abs() <= 0.005).sum(), to_num(mm["aum_basis"]).sum(),
        a_snap.sum(), f"{int(a_snap.isna().sum())} fee rows without a snapshot")

    # R4 return_ytd vs benchmark + alpha
    r, b, a = to_num(s["return_ytd"]), to_num(s["benchmark_return_ytd"]), to_num(s["active_alpha_ytd"])
    add("R4 fact_portfolio_snapshot: return_ytd vs benchmark_return_ytd + active_alpha_ytd", len(s),
        ((r - b - a).abs() <= 1e-5).sum(), r.sum(), (b + a).sum(),
        f"{int(r.isna().sum())} return values not numeric")

    # R5 advisory-fee transactions vs fee table (known not to reconcile)
    af = t[t["txn_type"] == "Advisory Fee"]
    a_cm = to_num(af["amount"]).groupby([af["client_id"], af["txn_date"].str[:7]]).sum()
    f_cm = famt.groupby([f["client_id"], f["fee_date"].str[:7]]).sum()
    j = pd.concat([a_cm.rename("txn"), f_cm.rename("fee")], axis=1).dropna()
    add("R5 Advisory Fee transactions vs fact_fees (same client-month)", len(j),
        ((j["txn"] - j["fee"]).abs() <= 0.01).sum(), to_num(af["amount"]).sum(), famt.sum(),
        "different source systems; fact_fees is the system of record (D17)")
    return pd.DataFrame(out)


# -----------------------------------------------------------------------------
# 4. IQR outliers on columns with no natural upper bound
# -----------------------------------------------------------------------------
IQR_COLUMNS = [("fact_transactions", "amount"), ("fact_portfolio_snapshot", "aum"),
               ("dim_client", "initial_aum"), ("fact_fees", "amount"),
               ("fact_portfolio_snapshot", "active_alpha_ytd")]


def run_iqr(T, stage):
    rows = []
    for t, c in IQR_COLUMNS:
        v = to_num(T[t][c]).dropna()
        q1, q3 = v.quantile(0.25), v.quantile(0.75)
        lo, hi = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
        out = (v < lo) | (v > hi)
        rows.append(dict(stage=stage, table=t, column=c, n=len(v), q1=round(q1, 6), q3=round(q3, 6),
                         lower_fence=round(lo, 6), upper_fence=round(hi, 6),
                         below=int((v < lo).sum()), above=int((v > hi).sum()),
                         flagged_pct=round(out.mean() * 100, 2), max_value=v.max()))
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# 5. Scorecard: one row per table per stage
# -----------------------------------------------------------------------------
def scorecard(T, stage, ri, rules):
    rows = []
    for t in TABLES:
        df, spec = T[t], SCHEMA[t]
        req_cells = filled = typed_cells = typed_ok = 0
        for c, cs in spec["columns"].items():
            req = required_mask(df, cs)
            nb = ~blank_mask(df[c])
            req_cells += int(req.sum())
            filled += int((req & nb).sum())
            typed_cells += int(nb.sum())
            typed_ok += int((valid_mask(df[c], cs["kind"]).fillna(False) & nb).sum())
        key_ok = ~(df.duplicated(spec["pk"], keep="first") | df.duplicated(spec["natural_key"], keep="first"))
        rr = rules[rules["table"] == t]
        rel = ri[ri["child_table"] == t]
        matched = (rel["non_null_keys"] - rel["orphan_rows"]).sum()   # counts, not the rounded %
        rows.append(dict(
            table=t, stage=stage, rows=len(df),
            pct_completeness=round(filled / req_cells * 100, 3),
            pct_key_uniqueness=round(key_ok.mean() * 100, 3),
            pct_type_validity=round(typed_ok / typed_cells * 100, 3),
            pct_rule_pass=round((1 - rr["failed"].sum() / rr["checked"].sum()) * 100, 3),
            pct_referential_match=round(matched / rel["non_null_keys"].sum() * 100, 3) if len(rel) else "n/a",
            relationships_checked=len(rel)))
    return pd.DataFrame(rows)


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    all_ri, all_rules, all_rec, all_iqr, all_score = [], [], [], [], []
    for stage, folder in STAGES.items():
        T = load_tables(folder)
        ri = run_ri(T, stage)
        rules = run_rules(T, stage)
        all_ri.append(ri)
        all_rules.append(rules)
        all_rec.append(run_reconciliations(T, stage))
        all_iqr.append(run_iqr(T, stage))
        all_score.append(scorecard(T, stage, ri, rules))
        print(f"validated {stage}")

    ri = pd.concat(all_ri, ignore_index=True)
    rules = pd.concat(all_rules, ignore_index=True)
    rec = pd.concat(all_rec, ignore_index=True)
    iqr = pd.concat(all_iqr, ignore_index=True)
    score = pd.concat(all_score, ignore_index=True).sort_values(["table", "stage"],
                                                                key=lambda s: s.map({"raw": 0, "clean": 1}).fillna(s) if s.name == "stage" else s)
    ri.to_csv(REPORTS_DIR / "ri_results.csv", index=False)
    rules.to_csv(REPORTS_DIR / "rule_results.csv", index=False)
    rec.to_csv(REPORTS_DIR / "reconciliations.csv", index=False)
    iqr.to_csv(REPORTS_DIR / "iqr_outliers.csv", index=False)
    score.to_csv(REPORTS_DIR / "data_quality_scorecard.csv", index=False)

    w = dict(display_width=250, display_max_colwidth=60)
    with pd.option_context("display.width", w["display_width"], "display.max_colwidth", w["display_max_colwidth"]):
        print("\nREFERENTIAL INTEGRITY (13 relationships)")
        p = ri.pivot(index="relationship", columns="stage", values=["match_rate_pct", "orphan_rows"])
        print(p.to_string())
        print("\nRULES FAILING in either stage")
        piv = rules.pivot_table(index=["table", "column", "rule"], columns="stage", values="failed", aggfunc="sum")
        print(piv[(piv > 0).any(axis=1)].to_string())
        print("\nRECONCILIATIONS")
        print(rec[["stage", "reconciliation", "rows_compared", "rows_matching", "match_pct", "difference"]].to_string(index=False))
        print("\nIQR OUTLIERS")
        print(iqr[["stage", "table", "column", "lower_fence", "upper_fence", "below", "above", "flagged_pct"]].to_string(index=False))
        print("Flagged is not the same as wrong: amounts and AUM are right-skewed by nature "
              "(a few UHNW clients hold most assets), so their IQR outliers are real large "
              "accounts, trades and fees; active_alpha_ytd has a narrow fence, so most of its "
              "flags are ordinary spread, and only the extreme tail (the D23 return_ytd_suspect "
              "rows) is probably wrong. Outliers are leads to check, not errors to delete.")
        print("\nDATA QUALITY SCORECARD")
        print(score.to_string(index=False))


if __name__ == "__main__":
    main()
