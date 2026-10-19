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

## Claude Code review findings

*To be completed: run the Claude Code review in VS Code on each script and record what it flagged and what you did.*

| Script | What Claude Code flagged | What I did |
|---|---|---|
| `01_profile.py` | | |
| `02_clean.py` | | |
| `03_validate.py` | | |
| `dq_common.py` | | |

Issues caught by the scripts' own asserts while building them (already fixed):

| Where | What happened | What I did |
|---|---|---|
| `02_clean.py` D01 | The assert "copy's last name = original minus its last letter" failed for 2 of 25 duplicates (`Pace` → `Pacen`, `Lee` → `Leen`, where a letter was added) | Confirmed they are still copies (12 of 14 columns identical, no activity), widened the rule to "one letter dropped or added at the end", and updated the decision log |
| `02_clean.py` D12 | The quarantine file showed `security_id` already converted, because D11 runs first | Quarantine now stores the raw rows exactly as they arrived |
| `decision_log.md` | Three figures written from memory were wrong ($8.6M, inactive-client date range, dividend overstatement) | Recomputed from the data and corrected before writing the cleaning code |
