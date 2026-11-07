# HW6: DAX Measure Library (AUM & Performance)

**Student:** Aiden James Dumm · MIS3060 Business Intelligence with AI · Villanova University

Twelve DAX measures on the Wildcat Capital portfolio snapshot, each using the pattern that matches its additivity class (SUM, last balance, or recompute-and-weight). Every number is proven against an independent pandas calculation.

## Structure

```
hw06/
├── README.md                          this file
├── data/                              the 8 Wildcat Capital Clean CSVs (same files as hw05/data)
├── powerbi/
│   ├── hw06.pbix                      posted Wildcat_Star_Model + _Measures (17 measures) + "Measures" page
│   ├── measures.md                    Part A documentation (DAX, pattern, meaning) + Part C answers
│   ├── measures_page.jpg              picture of the Measures report page
│   └── export_queries.dax             the DAX queries behind reports/powerbi_values.csv
├── scripts/
│   ├── 01_reconcile_measures.py       Part B: pandas recomputation + reconciliation + Part C/D evidence
│   └── 02_export_powerbi_values.ps1   runs export_queries.dax against the open hw06.pbix
├── reports/
│   ├── powerbi_values.csv             Power BI numbers, unrounded (measure, slice, value): 159 rows
│   ├── measure_reconciliation.csv     measure, slice, powerbi_value, pandas_value, abs_diff, match
│   ├── part_c_evidence.csv            pandas figures quoted in measures.md Part C and verification.md
│   └── powerbi_part_c.csv             Power BI side of Part C (a)
└── claude/
    ├── model_metadata.md              INFO.VIEW columns / relationships / measures export
    ├── dax_session.md                 Part D prompts and Claude's full responses
    └── verification.md                Part D verification and edge cases
```

## How to run

From the repository root:

```bash
pip install pandas
```
```bash
powershell -ExecutionPolicy Bypass -File hw06/scripts/02_export_powerbi_values.ps1
```
```bash
python hw06/scripts/01_reconcile_measures.py
```

1. **Export (Power BI side).** Open `hw06/powerbi/hw06.pbix` in Power BI Desktop first. The script connects to the model Desktop has open, using the same engine as DAX query view and Power BI's own `Microsoft.PowerBI.AdomdClient.dll`. It refuses to run unless the connected model has the 17 `_Measures` measures, and it writes the values unrounded. Every query in `export_queries.dax` can also be pasted into DAX query view as is.
2. **Reconcile (pandas side, ~3 s).** This recomputes every measure from `hw06/data/` without reading anything from Power BI, then joins to `powerbi_values.csv`. It exits with code 1 if any row mismatches or a required row is missing. The tolerance is 0.01 for currency and counts, 0.0001 for ratios and bps, and exact for the `Alpha Signal` text.

## Results

| | |
|---|---|
| Rows reconciled | **159**: 17 measures × (grand total + 5 years + 3 tiers in 2024) + 6 for December 2024 |
| Match | **159 of 159**; the largest difference is $0.00032 (floating-point noise on the $105B UHNW naive sum, far inside the 1-cent tolerance) |
| Required slices (Part B) | all present (the script checks the list) |
| `AUM (naive SUM)` | $566,681,084,542.48 in both tools, 44.5× the true $12,729,572,078.86 |

**No measure mismatched**, at the first run or later. Two problems came up on the way, both in my export script's labels rather than in a measure:
1. Trailing spaces in the slice prefixes were trimmed, so rows came out as `Year2020`, and the reconciliation refused them as "no pandas twin". I fixed this with explicit `label=Year {}` templates.
2. Removing ADOMD's `[ ]` around result names also ate the closing bracket of `[SUMX over clients of [Ending AUM]]`. The fix removes exactly one outer pair.

### Changes to the posted model
- **`dim_date` was not marked as the date table** in `Wildcat_Star_Model.pbix`, even though the guide says it is. It still had an auto date/time table attached. I marked it on `date` (Table tools → Mark as date table, validated) before writing the time-intelligence measures.
- The posted model has **12** relationships between the eight tables, not 11, plus one auto date/time relationship on `dim_client[client_since]`. I left them all unchanged.
- I set `dim_date[year]` to *Don't summarize*, so the year table groups instead of summing years.
- I added the `_Measures` table and deleted its placeholder `Column1`.

`hw06.pbix` is 21.9 MB, under GitHub's 100 MB limit.

## How the work was done
- Claude (in Claude Code) drafted both scripts, the DAX and the documents. It ran the scripts, and it drove Power BI Desktop, with permission for Power BI only, to create `_Measures`, mark the date table and build the Measures page. The 17 measures were written into the open model through Power BI's own Tabular library (Desktop allows external tools to add measures), and Power BI reported every one as *Ready*.
- The course workflow names Claude Desktop for drafting and VS Code for running. Here both happened in Claude Code, and the scripts run the same way from VS Code or any terminal.

## Claude Code review findings

Claude Code reviewed both scripts before the commit. It tested the reconciliation on a deliberately tampered copy of `powerbi_values.csv`: Ending AUM 2023 off by 2 cents, AUM YoY % 2022 off by 0.00005 (inside the ratio tolerance), the `AUM MoM %` / `Dec 2024` row deleted, and `Alpha Signal` 2022 changed to "In line".

| Script | What Claude Code flagged | What I did |
|---|---|---|
| `01_reconcile_measures.py` | A duplicated `(measure, slice)` row in the Power BI file would be reconciled twice and could hide a stale value | **Fixed**: the script stops on duplicates |
| `01_reconcile_measures.py` | There was no way to test it without overwriting the submitted report | **Fixed**: an optional path argument; a test run writes its output next to the test file |
| `01_reconcile_measures.py` | Checked on the tampered copy | **No change needed**: it reported the 2-cent error and the wrong text as `MISMATCH`, the deleted row as `MISSING`, passed the in-tolerance change, and exited with code 1 |
| `01_reconcile_measures.py` | Blank handling: 2020 `AUM YoY %` and `Organic Growth Rate` are blank in Power BI (`DIVIDE` with no prior year) | **No change**: `div()` returns NaN in the same cases, and the script counts blank = blank as a match |
| `01_reconcile_measures.py` | Is the pandas side independent of Power BI? | **No change**: it reads only `hw06/data/*.csv` before opening `powerbi_values.csv`, and it re-implements the filter context (last snapshot in the slice, SAMEPERIODLASTYEAR / DATEADD as date shifts clipped to `dim_date`) instead of copying values |
| `02_export_powerbi_values.ps1` | It connected to the newest Power BI instance, so with two reports open it could export from the wrong model | **Fixed**: it checks for the 17 `_Measures` measures first and stops otherwise |
| `02_export_powerbi_values.ps1` | The header comment of `export_queries.dax` was sent to the engine as a query ("not a rowset") | **Fixed**: only blocks after a `-- slice:` line are run |
| `02_export_powerbi_values.ps1` | The label trimming and bracket stripping above | **Fixed** (see Results) |
| Part D test query | `VAR LastDate` collides with the DAX function `LASTDATE` | **Fixed** in the session (`LastSnap`); see `claude/verification.md` |
