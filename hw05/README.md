# HW5 — Modeling the Wildcat Capital Data as a Star Schema in Power BI

**Student:** Aiden James Dumm · MIS3060 Business Intelligence with AI · Villanova University

Work out how the eight clean Wildcat Capital tables fit together (keys, grain, measure behavior) and build the star schema in Power BI, without creating any new tables or columns.

## Structure

```
hw05/
├── README.md                  this file
├── star_design.md             Parts A, B, C, E and F (and the Part D relationship table)
├── scripts/
│   └── validate_star.py       proves every key, grain and design claim in star_design.md
├── data/                      the 8 CSVs from the instructor's "Wildcat Capital Clean" release, unchanged
├── reports/
│   └── validation_results.csv one row per check (section, check, PASS/FAIL/INFO, actual, expected)
└── powerbi/
    ├── hw05.pbix              Part D model (8 tables, 13 relationships, dim_date marked, check visuals on page 1)
    ├── model_view.png         Model view screenshot
    └── build_steps.md         the click-by-click checklist used to build the model
```

## How to run

From the repository root. The script needs only Python 3 (no packages):

```bash
python hw05/scripts/validate_star.py     # ~5 s -> hw05/reports/validation_results.csv
```

It exits with code 1 if any check fails. `python hw05/scripts/validate_star.py path/to/folder` runs the same checks on another copy of the eight CSVs and writes that run's report into the folder, so the submitted report is never overwritten. The Power BI model loads the CSVs from `hw05/data/`. If the repo is cloned elsewhere, use **Transform data → Data source settings → Change source** to point at the new folder.

**Data note:** HW5 uses the instructor's clean release, as the handout requires, not my own HW4 output. The files differ (my HW4 clean tables carry six extra flag columns), so everyone models identical data.

## Results at a glance

| | |
|---|---|
| Checks | **68 PASS, 0 FAIL**, 24 INFO |
| Row and column counts | all 8 tables match the handout |
| Primary keys | 8 of 8 unique, no blanks, whole numbers |
| Foreign keys | 13 of 13 with 0 orphans; only `fact_transactions[security_id]` has blanks (101,528 cash rows, by design) |
| Grains | transactions: `txn_id`; fees: (client, month); snapshot: (client, month), each 0 duplicates |
| Power BI | 12 active relationships, 1 inactive (`dim_client → dim_advisor`), all *:1 single-direction; `dim_date` marked on `date`; report page 1 has the row-count cards (all 8 reconcile), the `(Blank)` ticker check and an advisor slicer that filters all three facts |

## Claude Code review findings

Claude Code reviewed `validate_star.py` before submission. It reran the script on the real data, then on a deliberately broken copy (one orphan client, one duplicate fee client-month, a blank `security_id` on a Buy, an advisor mismatch, and a missing date in `dim_date`) to prove that each check can actually fail. It also checked every figure in `star_design.md` against the script output.

| What Claude Code flagged | What I did |
|---|---|
| On the broken copy, the script **crashed** (`KeyError: '99999'`) in the advisor-consistency check instead of reporting the orphan client, so one bad key would hide every later result | **Fixed**: the lookups use `.get()`, so an orphan is reported as a FAIL in section 3 and counted as a mismatch in section 6. The rerun reports 12 FAILs covering all 5 planted faults and exits with code 1 |
| The "return_ytd restarts each January" check only counted January rows, so it proved nothing | **Fixed**: it now compares the mean absolute `return_ytd` in January (5.06%) and December (32.11%), which shows it is cumulative |
| A comment said summing a year of AUM overstates it "about 12 times"; the data gives 10.6× (clients join and leave during the year) | **Fixed** the comment; `star_design.md` quotes the measured 10.6× |
| A test run on another folder would overwrite `reports/validation_results.csv` | **Fixed**: a run on another folder writes its report into that folder |
| `star_design.md` gave the `client_since` values outside `dim_date` as "2015-01-01 to 2019-12-31", but the script only reports the minimum | **Fixed**: the text now says "from 2015-01-01 onward, before 2020-01-01" |
| Checked: every FK in Part A is in `FOREIGN_KEYS`; blanks and orphans are counted separately; dates are compared as text exactly as stored, the way Power BI matches Date to Date | **No change**: no defects |
