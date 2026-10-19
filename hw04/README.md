# HW4 — Cleaning the Wildcat Capital Data

**Student:** Aiden James Dumm · MIS3060 Business Intelligence with AI · Villanova University

Audit, clean and validate the eight Wildcat Capital warehouse tables without inventing data, and prove each fix worked.

## Structure

```
hw04/
├── README.md                  this file
├── decision_log.md            Part B: one entry per issue (D01-D27), written before the cleaning code
├── scripts/
│   ├── dq_common.py           shared schema, relationships, business rules (the only table-specific file)
│   ├── 01_profile.py          Part A: generic profiler + 4-group audit
│   ├── 02_clean.py            Part C: cleaning program (one asserted step per decision)
│   └── 03_validate.py         Part D: check_referential_integrity() + rules, reconciliations, IQR, scorecard
├── data/
│   ├── raw/                   the 8 source CSVs, unmodified
│   ├── clean/                 the 8 clean CSVs + README_clean.md
│   └── audit/                 cleaning_log.csv, value_changes.csv, quarantine_*.csv
└── reports/
    ├── profile_raw.csv        75 column profiles
    ├── dq_summary_raw.csv     308 checks tagged ERROR / WARN / INFO / PASS
    ├── data_quality_scorecard.csv   one row per table per stage (raw / clean)
    ├── ri_results.csv, rule_results.csv, reconciliations.csv, iqr_outliers.csv   Part D detail
    └── cleaning_report.md     Part E: report to the portfolio committee
```

## How to run

From the repository root, with the virtual environment active (`pandas`, `numpy`):

```bash
python hw04/scripts/01_profile.py     # ~30 s -> reports/profile_raw.csv, dq_summary_raw.csv
python hw04/scripts/02_clean.py       # ~8 s  -> data/clean/, data/audit/ (stops on any failed assert)
python hw04/scripts/03_validate.py    # ~20 s -> reports/data_quality_scorecard.csv + detail files
```

`01_profile.py path/to/any.csv` profiles any other table. Every script reads files as text (`dtype=str, keep_default_na=False`) and converts columns on purpose. Paths are resolved from the script location, so the scripts also run from other folders.

## Results at a glance

| | Raw | Clean |
|---|---:|---:|
| Rows (8 tables) | 555,401 | 555,176 (+225 quarantined) |
| Relationships at 100% match | 11 of 13 | 13 of 13 |
| `fact_transactions` type validity | 91.73% | 100% |
| `fact_transactions` referential match | 81.95% | 100% |
| Cells changed | | 198,387 (logged in `value_changes.csv`) |

## Design notes

- **Generic vs table-specific:** `profile_table()` and every check function work on any DataFrame. What is specific to Wildcat Capital (types, code lists, bounds, keys, relationships, business rules) lives in one place, `dq_common.py`, so a new table only needs a schema entry.
- **One RI function:** `check_referential_integrity(fact_df, fact_key, dim_df, dim_key)` is defined once in `03_validate.py`. `01_profile.py` and `02_clean.py` load that same function. It compares keys as text, the way a BI join does, which is how it caught the `45.0` vs `45` problem.
- **Order of operations** is defended in `decision_log.md`: dimensions → key formats → quarantine → value repairs → flags.

## IQR outliers: does "flagged" mean "wrong"?

`03_validate.py` applies 1.5 × IQR fences to five columns with no natural upper bound (`reports/iqr_outliers.csv`). **Flagged is not the same as wrong.** Transaction amount, AUM, initial AUM and fee amount are right-skewed by nature (mean AUM is about 9× the median because a few UHNW clients hold most assets), so their outliers (2.4–10.2% of rows) are real large accounts, trades and fees. `active_alpha_ytd` has a narrow fence (−6.3% to +7.1%), so 37,469 rows (28.9%) are flagged, and most of that is ordinary spread. Only its extreme tail is probably wrong: all 1,475 `return_ytd_suspect` rows (D23) fall in that flagged set. Outliers are leads to check, not errors to delete.

## Claude Code review findings

Claude Code (in VS Code) read every script line by line before submission, re-ran the pipeline on the Python 3.9 venv and re-checked every figure in the three documents against the data. Each fix was tested: the pipeline was re-run, all clean, audit and report CSVs came out byte-identical to the previous run, and each new assert was shown to stop the script on deliberately broken input. **15 code findings, 8 fixed; 2 decision-log figures corrected. No output number changed.**

| Script | What Claude Code flagged | What I did |
|---|---|---|
| `dq_common.py` | `dim_date` row rules: one unparseable date would make `year`/`month` fail on **every** row (`d.dt.year` turns into float text `2020.0`) and crash the ISO-week check (`cannot convert NA to integer`). Reproduced by injecting a bad date | **Fixed**: expected values are derived only from parseable dates. With a bad date injected, the rules now check 1,826 rows and report only the real mismatch |
| `dq_common.py` | Recompute tolerances (0.011 on 2-decimal amounts, 1e-5 on returns, 0.005 on AUM) could hide real differences | **No change**: each is one cent or the last stored digit; checked against the values' precision |
| `dq_common.py` | `load_ri_function()` repeats the loader code at the top of `01_profile.py` | **No change**: both load the same single `check_referential_integrity()`; style only |
| `01_profile.py` | Checked: generic `profile_table()` (also runs on any CSV given as an argument), all 7 per-column statistics, the 4 check groups, ERROR/WARN/INFO/PASS tagging, PK-duplicate counting (counts every copy) | **No change**: no defects found; the re-run gives the same 308 checks and finding IDs |
| `01_profile.py` | `value_shape()` collapses digit runs, so `2020-1-5` and `2020-01-05` have the same shape | **No change**: the date parse-failure check (`\d{4}-\d{2}-\d{2}`) catches that case anyway |
| `02_clean.py` D12 | The assert claimed a "1-to-1" match but only checked that each orphan matches one valid transaction, not that no two orphans copy the same one | **Fixed**: added `copy_of_txn_id` uniqueness assert (passes: 200 distinct originals) |
| `02_clean.py` D14 | The "independent check" was one-way: it confirmed flagged rows are weekends, but a weekend trade whose date is missing from `dim_date` would have been silently left unflagged | **Fixed**: the flag must equal Buy/Sell × weekend computed from the date itself (both directions). Tested by deleting a Saturday from `dim_date`: the script now stops |
| `02_clean.py` D23 | The assert could not fail (`flag.sum() == (r > 1).sum() + (r < -0.9).sum()` is always true), and a non-numeric return would be silently unflagged | **Fixed**: now asserts every unflagged return is numeric and inside [−0.9, 1.0], and every flagged row still satisfies return = benchmark + alpha (values kept, as D23 says) |
| `02_clean.py` | `raw = clean + quarantined` compared row counts only, so a row dropped and another duplicated would cancel out | **Fixed**: also asserts that every raw primary key is in clean or quarantine exactly once, for all 8 tables |
| `02_clean.py` D20 | The `gap.max()` assert skips NaN, and the max gap (0.000050) sits exactly on the tolerance | **No change**: a NaN becomes text `nan`, and the next assert (`r.notna().all()`) stops the script; 0.00005 is the theoretical maximum when a percent is rounded to 2 decimals |
| `02_clean.py` | Issue descriptions in `cleaning_log.csv` contain fixed counts ("25", "200", "836 in raw") | **No change**: they describe the decision-log entry; the `rows_affected` column is computed and matches the run |
| `03_validate.py` | Scorecard `% referential match` rebuilt matched rows from the rounded `match_rate_pct` | **Fixed**: uses `non_null_keys − orphan_rows` (exact counts); the scorecard values are unchanged at 3 decimals |
| `03_validate.py` | The IQR "flagged ≠ wrong" sentence was only printed to the console, and it called all five columns right-skewed by asset concentration, which is wrong for `active_alpha_ytd` | **Fixed**: sentence corrected in the script and added to this README (section above) |
| `03_validate.py` | The docstring says keys are compared "exactly" as text, but the code trims spaces | **Fixed** the docstring. Behavior kept: no raw column has whitespace problems (profile), and the profiler reports whitespace separately |
| `03_validate.py` | Checked: `check_referential_integrity()` returns match rate, orphan rows, distinct orphan keys and null-key rate, is defined once, and is applied to all 13 relationships | **No change**: 13 of 13 at 100% in the clean stage |
| `decision_log.md` D22 | Floor-basis fees were cited as "$0.65–$0.84" and floor-month returns as "near −97%" | **Fixed**: data shows $0.65–$0.80, with a median return of −94% (59% below −90%) |
| `decision_log.md` D17 | "1,933 fee debits" with no fee row: 1,933 counts client-months, not debits | **Fixed**: "1,933 client-months with fee debits (2,297 debits)" |

Issues caught by the scripts' own asserts while building them (already fixed):

| Where | What happened | What I did |
|---|---|---|
| `02_clean.py` D01 | The assert "copy's last name = original minus its last letter" failed for 2 of 25 duplicates (`Pace` → `Pacen`, `Lee` → `Leen`, where a letter was added) | Confirmed they are still copies (12 of 14 columns identical, no activity), widened the rule to "one letter dropped or added at the end", and updated the decision log |
| `02_clean.py` D12 | The quarantine file showed `security_id` already converted, because D11 runs first | Quarantine now stores the raw rows exactly as they arrived |
| `decision_log.md` | Three figures written from memory were wrong ($8.6M, inactive-client date range, dividend overstatement) | Recomputed from the data and corrected before writing the cleaning code |
