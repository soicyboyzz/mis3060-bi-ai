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

    Keys are compared exactly as text (the way a BI join compares them), so a
    key stored as '45.0' does NOT match '45'. Blank keys are counted
    separately and are not orphans.

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
