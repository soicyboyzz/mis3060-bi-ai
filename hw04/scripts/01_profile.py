# =============================================================================
# Script:      01_profile.py
# Assignment:  HW4 - Cleaning the Wildcat Capital Data (Part A)
# Author:      Aiden James Dumm
# Generated:   2026-10-19
# Description: Generic profiler + data-quality audit. profile_table() works on
#              ANY table read as text. The audit then runs four groups of
#              checks driven by dq_common.SCHEMA / relationships / rules:
#                1 column level   2 single-table   3 referential integrity
#                4 cross-table business rules
#              Every finding is tagged ERROR / WARN / INFO (PASS if clean).
# Outputs:     reports/profile_raw.csv, reports/dq_summary_raw.csv
# Run from the repository root:
#     python hw04/scripts/01_profile.py                 (the 8 raw tables)
#     python hw04/scripts/01_profile.py path/to/any.csv (profile any table)
# =============================================================================

import importlib.util
import sys
from pathlib import Path

import pandas as pd

from dq_common import (ALL_RELATIONSHIPS, NULL_TOKENS, RAW_DIR, REPORTS_DIR, ROW_RULES,
                       SCHEMA, TABLES, blank_mask, column_rule_results,
                       cross_table_checks, load_tables, row_rule_results, to_num,
                       valid_mask, value_shape)

# the one reusable RI function lives in 03_validate.py; load it from there
_spec = importlib.util.spec_from_file_location(
    "validate", Path(__file__).resolve().parent / "03_validate.py")
_validate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_validate)
check_referential_integrity = _validate.check_referential_integrity

TYPE_ORDER = ["bool", "date", "int", "decimal"]


# -----------------------------------------------------------------------------
# Generic column profile
# -----------------------------------------------------------------------------
def text_style(v):
    if v.isdigit():
        return "digits"
    if v.isupper():
        return "UPPER"
    if v.islower():
        return "lower"
    if v.istitle():
        return "Title"
    return "Mixed"


def infer_type(s):
    nb = s[~blank_mask(s)]
    if nb.empty:
        return "empty", 1.0
    for kind in TYPE_ORDER:
        share = valid_mask(nb, kind).fillna(False).mean()
        if share >= 0.95:
            return kind, share
    return "text", 1.0


def profile_table(df, table, expected=None):
    """One row per column. `expected` = {column: kind} (optional)."""
    rows = []
    n = len(df)
    for c in df.columns:
        s = df[c].astype(str)
        blank = blank_mask(s)
        nb = s[~blank]
        kind, _ = infer_type(s)
        exp = (expected or {}).get(c, kind)
        valid = valid_mask(nb, exp).fillna(False) if exp not in ("text", "empty") else pd.Series(True, index=nb.index)
        fails = nb[~valid]

        # value shapes (digits -> 9, letters -> A); sign ignored
        shapes = nb.str.lstrip("-").map(value_shape).value_counts()
        if kind == "text" and nb.nunique() > 50:   # free text (names, cities)
            n_formats, minority, format_detail = 1, 0, "free text - style not checked"
        elif kind == "text":
            styles = nb.map(text_style).value_counts()
            n_formats, minority = len(styles), int(styles.iloc[1:].sum()) if len(styles) else 0
            format_detail = "; ".join(f"{k}:{v}" for k, v in styles.items())
        else:
            n_formats, minority = len(shapes), int(shapes.iloc[1:].sum()) if len(shapes) else 0
            format_detail = "; ".join(f"{k}:{v}" for k, v in shapes.head(6).items())

        num = to_num(nb) if kind in ("int", "decimal") or exp in ("int", "decimal") else pd.Series(dtype=float)
        lead_zero = nb.str.fullmatch(r"0\d+").sum()
        rows.append(dict(
            table=table, column=c, rows=n,
            blank_count=int(blank.sum()), blank_pct=round(blank.mean() * 100, 2) if n else 0,
            null_token_count=int(nb.isin(NULL_TOKENS).sum()),
            null_tokens_found="; ".join(sorted(set(nb[nb.isin(NULL_TOKENS)]))),
            distinct_count=int(s.nunique()),
            inferred_type=kind, expected_type=exp,
            parse_fail_count=int(len(fails)),
            parse_fail_pct=round(len(fails) / len(nb) * 100, 3) if len(nb) else 0,
            parse_fail_examples="; ".join(fails.drop_duplicates().head(5)),
            dominant_shape=shapes.index[0] if len(shapes) else "",
            dominant_shape_pct=round(shapes.iloc[0] / len(nb) * 100, 2) if len(nb) else 0,
            n_formats=n_formats, minority_format_rows=minority, formats=format_detail,
            whitespace_issues=int(((s != s.str.strip()) | s.str.contains(r"\s{2,}")).sum()),
            leading_zero_values=int(lead_zero),
            numeric_min=num.min() if len(num) else "", numeric_max=num.max() if len(num) else "",
            min_length=int(nb.str.len().min()) if len(nb) else 0,
            max_length=int(nb.str.len().max()) if len(nb) else 0,
            top_values="; ".join(f"{k}:{v}" for k, v in s.value_counts().head(5).items()),
        ))
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# Findings
# -----------------------------------------------------------------------------
FINDINGS = []


def add(group, table, column, check, severity, failed, checked, detail="", example=""):
    FINDINGS.append(dict(
        group=group, table=table, column=column, check=check,
        severity=severity if failed else "PASS", rows_affected=int(failed),
        rows_checked=int(checked),
        pct_affected=round(failed / checked * 100, 3) if checked else 0.0,
        detail=detail, example=str(example)))


def profile_findings(prof):
    """Turn generic profile stats into findings (group 1)."""
    for r in prof.itertuples():
        g = "1 Column level"
        if r.whitespace_issues:
            add(g, r.table, r.column, "leading/trailing/double whitespace", "WARN",
                r.whitespace_issues, r.rows)
        if r.null_token_count:
            add(g, r.table, r.column, "text null token (pandas would turn it into NaN)", "INFO",
                r.null_token_count, r.rows, f"tokens: {r.null_tokens_found}")
        if r.leading_zero_values:
            add(g, r.table, r.column, "values with leading zeros (lost if parsed as a number)",
                "INFO", r.leading_zero_values, r.rows)
        if r.minority_format_rows:
            # mixed number/date formats break parsing (WARN); mixed letter case in
            # a code list is often just naming (INFO)
            sev = "INFO" if r.inferred_type == "text" else "WARN"
            add(g, r.table, r.column, "mixed value formats", sev,
                r.minority_format_rows, r.rows - r.blank_count, r.formats)


def column_findings(df, table):
    spec = SCHEMA[table]
    keyish = {spec["pk"]} | {cc for (t, cc, _, _) in ALL_RELATIONSHIPS if t == table}
    sev_by_rule = {"type": "ERROR", "allowed_values": "ERROR", "format_pattern": "ERROR",
                   "range_bound": "ERROR", "blank_when_not_applicable": "WARN"}
    for r in column_rule_results(df, table):
        rule = r["rule"]
        if rule == "completeness":
            sev = "ERROR" if r["column"] in keyish else "WARN"
        else:
            sev = sev_by_rule.get(rule.split("_")[0] if rule.startswith("type") else rule, "ERROR")
        add("1 Column level", table, r["column"], rule, sev, r["failed"], r["checked"],
            example=r["examples"])
    # primary-key uniqueness
    pk = df[spec["pk"]]
    add("1 Column level", table, spec["pk"], "primary key unique", "ERROR",
        pk.duplicated(keep=False).sum(), len(df), example=pk[pk.duplicated()].head(3).tolist())


def single_table_findings(df, table):
    g = "2 Single-table"
    spec = SCHEMA[table]
    non_key = [c for c in df.columns if c != spec["pk"]]
    dup = df.duplicated(non_key, keep="first")
    add(g, table, "(all but PK)", "exact duplicate rows (ignoring primary key)", "ERROR",
        dup.sum(), len(df), example=df.loc[dup, spec["pk"]].head(3).tolist())
    nk = spec["natural_key"]
    dupk = df.duplicated(nk, keep="first")
    add(g, table, "+".join(nk), "natural/business key duplicated", "ERROR", dupk.sum(), len(df),
        example=df.loc[dupk, spec["pk"]].head(3).tolist())
    # near-duplicates: rows identical on every non-key column except one
    for c in non_key:
        others = [x for x in non_key if x != c]
        nd = df.duplicated(others, keep=False) & ~df.duplicated(non_key, keep=False)
        if nd.any():
            grp = df[nd].groupby(others, sort=False)[c].apply(lambda v: " | ".join(v.head(2)))
            add(g, table, c, f"near-duplicates: identical except '{c}'", "WARN",
                int(nd.sum() - len(grp)), len(df),
                f"{len(grp)} groups; the extra copies are counted", grp.head(3).tolist())
    for r in row_rule_results(df, table):
        ex = df.loc[r["failed_index"], spec["pk"]].head(3).tolist()
        add(g, table, "(row rule)", r["rule"], r["severity"], r["failed"], r["checked"], example=ex)


def ri_findings(T):
    g = "3 Referential integrity"
    for child, ck, parent, pk in ALL_RELATIONSHIPS:
        res = check_referential_integrity(T[child], ck, T[parent], pk)
        add(g, child, ck, f"{child}.{ck} -> {parent}.{pk}", "ERROR", res["orphan_row_count"],
            res["rows"] - res["null_key_rows"],
            f"match rate {res['match_rate']:.4%}; distinct orphan keys {res['distinct_orphan_keys']}; "
            f"null-key rate {res['null_key_rate']:.2%}", res["orphan_key_examples"])
        if res["orphan_row_count"]:
            # would the join work if the key were stored as a whole number?
            fixed = T[child].assign(**{ck: T[child][ck].str.replace(r"\.0+$", "", regex=True)})
            res2 = check_referential_integrity(fixed, ck, T[parent], pk)
            if res2["orphan_row_count"] != res["orphan_row_count"]:
                add(g, child, ck, f"{child}.{ck} -> {parent}.{pk} after dropping '.0'", "INFO",
                    res2["orphan_row_count"], res2["rows"] - res2["null_key_rows"],
                    f"{res['orphan_row_count'] - res2['orphan_row_count']} orphans were only a "
                    f"number-format problem; {res2['orphan_row_count']} remain (true orphans)",
                    res2["orphan_key_examples"])


def cross_findings(T):
    for r in cross_table_checks(T):
        add("4 Cross-table", r["tables"], "", r["check"], r["severity"], r["failed"],
            r["checked"], r["detail"], r["example"])


# -----------------------------------------------------------------------------
def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1:   # profile arbitrary file(s) only
        for p in sys.argv[1:]:
            df = pd.read_csv(p, dtype=str, keep_default_na=False)
            print(profile_table(df, Path(p).stem).to_string())
        return

    T = load_tables(RAW_DIR)
    profiles = []
    for t in TABLES:
        exp = {c: s["kind"] for c, s in SCHEMA[t]["columns"].items()}
        prof = profile_table(T[t], t, exp)
        profiles.append(prof)
        profile_findings(prof)
        column_findings(T[t], t)
        single_table_findings(T[t], t)
        print(f"profiled {t:<26} {len(T[t]):>8,} rows x {T[t].shape[1]} cols")
    ri_findings(T)
    cross_findings(T)

    prof_all = pd.concat(profiles, ignore_index=True)
    prof_all.to_csv(REPORTS_DIR / "profile_raw.csv", index=False)
    summ = pd.DataFrame(FINDINGS)
    order = {"ERROR": 0, "WARN": 1, "INFO": 2, "PASS": 3}
    summ = summ.sort_values(["group", "table"], kind="stable").reset_index(drop=True)
    summ.insert(0, "finding_id", [f"F{i + 1:03d}" for i in range(len(summ))])
    summ.to_csv(REPORTS_DIR / "dq_summary_raw.csv", index=False)

    print(f"\nprofile_raw.csv   : {len(prof_all)} column profiles")
    print(f"dq_summary_raw.csv: {len(summ)} checks -> "
          + ", ".join(f"{k} {v}" for k, v in summ["severity"].value_counts()
                      .sort_index(key=lambda i: i.map(order)).items()))
    issues = summ[summ["severity"] != "PASS"]
    with pd.option_context("display.max_colwidth", 70, "display.width", 220):
        print(issues[["finding_id", "group", "table", "column", "check", "severity",
                      "rows_affected"]].to_string(index=False))


if __name__ == "__main__":
    main()
