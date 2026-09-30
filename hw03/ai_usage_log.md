# AI Usage Log
**Assignment: HW3: Building a Corporate Intelligence Database from SEC 8-K Filings**  
**Student: Aiden James Dumm**  
**Date: 9/30/26**  
**Tool: Claude Cowork** (scripts run in the VS Code terminal)

---

## 1. Prompts Sent to Claude Cowork

### Prompt 1: Specification A (Earnings Pipeline, Item 2.02) → `hw03/hw03_earnings.py`

The full text of Specification A from `hw03/specifications.md`, sent as written:

#### Specification A — Earnings Pipeline (Item 2.02)

##### Purpose

I need one Python script, `hw03/hw03_earnings.py`, that builds a quarterly earnings history for five public companies from their SEC Form 8-K filings. Companies file an 8-K under Item 2.02 ("Results of Operations and Financial Condition") when they release earnings, and they attach the earnings press release as an exhibit. The script should find those filings, download each press release, pull out the key numbers, and save them to a CSV file.

##### Context

* **Companies:** Use these five companies and CIK numbers exactly as written. Do not look up or change the CIKs.

  | Company | Ticker | SEC CIK |
  |---|---|---|
  | Apple Inc. | AAPL | 0000320193 |
  | Microsoft Corporation | MSFT | 0000789019 |
  | NVIDIA Corporation | NVDA | 0001045810 |
  | JPMorgan Chase & Co. | JPM | 0000019617 |
  | Walmart Inc. | WMT | 0000104169 |

* **Data source:** SEC EDGAR. The submissions API is at `https://data.sec.gov/submissions/CIK{cik}.json`, where `{cik}` is the 10-digit CIK with leading zeros. In the JSON response, `filings.recent` contains parallel lists (`form`, `filingDate`, `accessionNumber`, `primaryDocument`, `items`, and others). Position *i* in each list describes the same filing. The `items` value is a comma-separated string such as `"2.02,9.01"`.
* **How it will be run:** From the repository root in the VS Code terminal with `python hw03/hw03_earnings.py`. Write all file paths relative to the repository root.
* **Libraries:** Use `requests` for HTTP, `beautifulsoup4` for removing HTML, `re` for pattern matching, and `csv` or `pandas` for saving the output. Do not use any other third-party libraries.

##### Required Steps

1. **Set the User-Agent header.** Define the header `User-Agent: MIS3060 Villanova adumm@villanova.edu` once at the top of the script, and pass it on **every** `requests.get()` call, not only the first one. SEC blocks requests that don't have this header. Also pause about 0.2 seconds between requests so the script stays under SEC's limit of 10 requests per second, and set a timeout on every request.
2. **Find the earnings filings.** For each of the five companies, request the submissions API and keep only filings where `form` is exactly `8-K` and the `items` string contains `"2.02"`.
3. **Keep the four most recent.** Sort the matching filings by `filingDate`, newest first, and keep the four most recent for each company (one per quarter). If a company has fewer than four, use what is available and print a note.
4. **Find and download the press release.** For each filing:
   * Build the filing folder URL: `https://www.sec.gov/Archives/edgar/data/{cik without leading zeros}/{accession number without dashes}/`. The filing index page is `{accession number with dashes}-index.htm` inside that folder.
   * Download the filing index page. Find the earnings press release exhibit, which is the `.htm` document whose type is `EX-99.1` (or another type starting with `EX-99`). If there is no type match, fall back to any `.htm` file whose name contains `99`.
   * Download that exhibit, then use BeautifulSoup to remove the HTML and turn it into plain text. Collapse repeated whitespace so the text is easy to search.
   * If no press release exhibit can be found, or any download fails, **do not crash**. Print a warning that names the ticker and filing date, record a row where every extracted field is `"NOT_FOUND"`, and continue to the next filing.
5. **Extract four fields from the plain text** using regular expressions:
   * **Revenue** (quarterly revenue for the reported quarter). Companies word this differently: "revenue", "total revenues", "net revenue", "net sales". Account for each version and for both "million" and "billion". Store it as a number in **millions of dollars**. For example, "$94.9 billion" becomes `94900`.
   * **Diluted EPS** (earnings per diluted share). Store the dollar amount as a number, for example `1.64`.
   * **Net income** for the quarter. Store it as a number in **millions of dollars**, converting from billions if needed.
   * **Reporting period** as the release describes it, for example `"fourth quarter fiscal 2024"` or `"third-quarter 2025"`.

   When a figure appears more than once, use the first figure for the current quarter, not the prior-year comparison.
6. **Print each row as it is processed** in this exact format:
   `[Ticker] | [Period] | Revenue: $X | EPS: $X | Net Income: $X`
   For example: `AAPL | fourth quarter fiscal 2024 | Revenue: $94900M | EPS: $0.97 | Net Income: $14736M`.
7. **Save the results** to `hw03/earnings_history.csv` with exactly these columns in this order: `company`, `ticker`, `cik`, `filing_date`, `period`, `revenue_reported`, `eps_diluted`, `net_income`. Keep the CIK as the 10-digit string with leading zeros. After saving, print a confirmation with the file path and the number of rows written.
8. **Use `"NOT_FOUND"` for missing data.** If a regular expression finds no match, store the string `"NOT_FOUND"` in that cell. Never leave a cell blank and never store `None` or `NaN`. A blank cell and a value that couldn't be extracted mean different things.
9. **Add a header comment block** at the top of the script with the script name (`hw03_earnings.py`), the data source (SEC EDGAR 8-K Item 2.02 filings), the author (Aiden James), the date generated, a one-sentence description, and the run command.

##### Constraints

* **One script only.** Everything must be in `hw03/hw03_earnings.py`.
* **Never crash on one bad filing.** Wrap the work for each filing so that an error prints a warning and the script moves on. One unparseable press release must not stop the other 19.
* **No user input.** The script must run from start to finish without asking for anything.
* **Readable code.** Put the company list and the User-Agent at the top as constants. Keep each regex in a clearly named variable so it can be improved later, and add short comments marking each step.

### Prompt 2: Specification B (Executive Events Pipeline, Item 5.02) → `hw03/hw03_executives.py`

The full text of Specification B from `hw03/specifications.md`, sent as written:

#### Specification B — Executive Events Pipeline (Item 5.02)

##### Purpose

I need one Python script, `hw03/hw03_executives.py`, that builds a table of executive and director changes at the same five companies over the past 12 months. Companies file an 8-K under Item 5.02 ("Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers") when a leader leaves or is appointed. The script should find those filings, read the text, and pull out each event.

##### Context

* **Companies:** The same five companies and CIKs as Specification A. Use them exactly as written.

  | Company | Ticker | SEC CIK |
  |---|---|---|
  | Apple Inc. | AAPL | 0000320193 |
  | Microsoft Corporation | MSFT | 0000789019 |
  | NVIDIA Corporation | NVDA | 0001045810 |
  | JPMorgan Chase & Co. | JPM | 0000019617 |
  | Walmart Inc. | WMT | 0000104169 |

* **Data source:** The same EDGAR submissions API, `https://data.sec.gov/submissions/CIK{cik}.json`, with the same parallel lists in `filings.recent`. The main 8-K document for each filing is at `https://www.sec.gov/Archives/edgar/data/{cik without leading zeros}/{accession number without dashes}/{primaryDocument}`.
* **How it will be run:** From the repository root with `python hw03/hw03_executives.py`. All paths are relative to the repository root.
* **Libraries:** `requests`, `beautifulsoup4`, `re`, `datetime`, and `csv` or `pandas`. No other third-party libraries.

##### Required Steps

1. **Set the User-Agent header.** Use `User-Agent: MIS3060 Villanova adumm@villanova.edu` on **every** `requests.get()` call. Pause about 0.2 seconds between requests and set a timeout on each one.
2. **Find executive-change filings from the past 12 months.** For each company, request the submissions API. Keep filings where `form` is exactly `8-K`, `items` contains `"5.02"`, and `filingDate` falls within the 12 months before the day the script is run. Calculate the cutoff date from today's date, not a hard-coded date.
3. **Download and clean each filing.** Download the main 8-K document (`primaryDocument`), remove the HTML with BeautifulSoup, and collapse whitespace. Then isolate the Item 5.02 section: the text from "Item 5.02" up to the next "Item" heading (such as "Item 9.01") or the signature block. Search only that section, so text from other items isn't picked up by mistake. If the section can't be isolated, search the full text.
4. **Extract each event.** From the Item 5.02 text, identify every separate person-level event and extract:
   * **Event type:** `"departure"` if the text says a person is resigning, retiring, stepping down, leaving, being terminated, or will not stand for re-election. `"appointment"` if the text says a person is being appointed, elected, named, or promoted. Use `"both"` only when one sentence describes a single person leaving one role and taking another (for example, a CFO moving to an advisor role) and it can't be split into two clear events.
   * **Person's full name** (for example, `"Luca Maestri"`).
   * **Title** of the role they are leaving or taking (for example, `"Chief Financial Officer"` or `"Director"`).
   * **Effective date** of the change. Convert it to `YYYY-MM-DD` when a full date is given. Otherwise keep the wording as written (for example, `"end of fiscal year 2025"`).

   Any field that can't be extracted is stored as `"NOT_FOUND"`, never blank.
5. **One row per event.** If a single filing reports more than one event, such as one executive departing and a successor being appointed, create a **separate row for each event**. Both rows share the same `filing_date`. For example, a filing that says "Jane Doe will retire as CFO, and John Smith has been appointed CFO effective January 1, 2026" produces two rows: one `departure` for Jane Doe and one `appointment` for John Smith.
6. **Filings with no departure or appointment.** Some Item 5.02 filings are only about compensation or benefit plans and name no departure or appointment. These are not executive events, so do **not** write a row for them. Instead, print a note (`[Ticker] | [Date] | Item 5.02 filing skipped: no departure/appointment language found`) so the filing is still accounted for in the terminal output. Every row in the CSV must be a real event, with `event_type` of `"departure"`, `"appointment"`, or `"both"`.
7. **Print each event as it is processed** in this exact format:
   `[Ticker] | [Date] | [Event Type] | [Name] | [Title]`
   where `[Date]` is the filing date.
8. **Report companies with no events.** If a company has no Item 5.02 filings in the past 12 months, or none of its Item 5.02 filings produced an event row, print exactly `[Ticker]: No executive events in past 12 months` (for example, `NVDA: No executive events in past 12 months`) and continue to the next company. This is valid data, not an error, so the script must not crash or skip the message.
9. **Save the results** to `hw03/executive_events.csv` with exactly these columns in this order: `company`, `ticker`, `cik`, `filing_date`, `event_type`, `person_name`, `title`, `effective_date`. If there are no events for any company, still write the file with just the header row. After saving, print a confirmation with the file path and the number of rows written.
10. **Add a header comment block** at the top of the script with the script name (`hw03_executives.py`), the data source (SEC EDGAR 8-K Item 5.02 filings), the author (Aiden James), the date generated, a one-sentence description, and the run command.

##### Constraints

* **One script only.** Everything must be in `hw03/hw03_executives.py`.
* **Never crash on one bad filing.** An error on any filing prints a warning with the ticker and filing date, and the script continues.
* **Handle both edge cases:** a company with zero Item 5.02 filings, which prints the no-events message (step 8), and a single filing that reports both a departure and an appointment (step 5, two rows).
* **No user input,** and short comments marking each step. Keep the departure and appointment keyword lists and the name/title/date regex patterns in clearly named variables near the top so they can be improved later.

### Prompt 3: Timeline prompt (Part 4) → `hw03/hw03_timeline.py`

> *"Write a Python script that reads `hw03/earnings_history.csv` and `hw03/executive_events.csv`. Do the following:*
>
> *1. For each executive event in the events table, calculate the number of days between the executive event's `filing_date` and the nearest earnings filing date for the same company in the earnings table. Call this `days_to_nearest_earnings`.*
> *2. Add a column `event_timing` that categorizes each executive event as: `'before earnings'` if the event came before the nearest earnings filing, `'after earnings'` if it came after, or `'same week'` if within 7 days of an earnings filing.*
> *3. Save the combined table to `hw03/corporate_events_timeline.csv` with all columns from both source tables plus `days_to_nearest_earnings` and `event_timing`.*
> *4. Print a summary: for each company, list any executive events and whether they occurred before or after the nearest earnings announcement.*
> *5. Print a final count: how many events occurred before vs. after an earnings announcement across all five companies."*

**Supporting prompt (Part 5C):** *"Write Python using yfinance to get the most recent quarterly revenue and net income for AAPL."* → `hw03/hw03_yfinance_check.py`

---

## 2. Extractions That Required Iteration

**Earnings pipeline (Part 2): no iteration needed.** The first run produced all 20 rows (5 companies × 4 quarters) with zero `NOT_FOUND` values, so no regex follow-up was required for any company. Validation in Part 5 then confirmed the Apple figures against Apple's press release and yfinance.

**Executive events pipeline (Part 3): required one round of iteration, affecting all five companies.** The first run "succeeded" (no crash) but saved **36 rows**, many of them wrong:

| Problem in run 1 | Example | Fix |
|---|---|---|
| "named executive officers" (a compensation term) read as an appointment | NVDA: `appointment \| Achievement Target` | Excluded "named executive officer" from the appointment keywords |
| "termination of employment" in non-compete clauses read as a departure | WMT: `departure \| Covenant Not`, `Non-Competition Agreements` | Removed "termination" as a departure keyword; added legal terms to the non-name word list |
| Honorific and possessive references not linked to the full name | NVDA: `Mr. Gawel's`, `Ms. Nora`; WMT: `Mr. McMillon's`, `Mr. John` | "Mr./Ms. X" and "X's" resolved back to the full name; duplicates such as "Nora Johnson" merged into "Suzanne Nora Johnson" |
| Middle initial "A." treated as the stop word "a" | MSFT: Carlos A. Rodriguez → `NOT_FOUND`; JPM: Todd A. Combs → `Mr. Combs'` | Single-letter initials skipped in the stop-word check |
| Lowercase titles and abbreviations not recognised | WMT: "president and chief executive officer"; NVDA: "VP and CAO" | Title matching made case-insensitive; CEO/CAO/VP-style abbreviations added |
| Defined dates not resolved | WMT: `as of the Effective Date`; AAPL: "effective on the Transition Date" | Dates defined as (the "Effective Date") are substituted into later references → 2026-02-01, 2026-09-01 |
| Wrong person chosen for "appointed" | "the Board appointed X" vs. "X was appointed" | Keyword direction added (active voice → person after, passive voice → person before) |

To fix these, I had the raw Item 5.02 text of all 19 filings saved to a local file (a temporary helper script, not part of the submission). The extraction rules were then corrected against the real wording. The second run produced **29 events from 16 filings**, and **3 compensation-only filings were correctly skipped** (JPM 2026-01-22 Dimon pay, MSFT 2025-12-08 stock plan, NVDA 2026-03-06 bonus plan). Every name, title and event type was checked against the filing text.

Two effective dates remain `NOT_FOUND` (Chris Kondo at Apple and Marianne Lake at JPMorgan) because those filings do not state a date. That is a correct `NOT_FOUND`, not an extraction failure.

---

## 3. Something the Generated Script Did That I Would Not Have Specified

The earnings script reads revenue and net income from the **press-release sentence first** (e.g., "quarterly revenue of $109.4 billion"), and only **falls back to the financial-statement table** (e.g., "Net income $ 29,789") when no sentence matches. I never specified where in the document the numbers should come from.

**Was it correct?** Yes, it was correct, with one side effect. Some values in `earnings_history.csv` are rounded headline numbers (Apple Q3 FY26 revenue = 109,400) and others are exact table figures (Apple net income = 29,789), depending on how each company writes its release. The Part 5C cross-check showed this clearly. yfinance reported revenue of $109,417M against our $109,400M, a 0.02% rounding difference, and net income of $29,789M, an exact match. No adjustment was needed for the assignment, but for precise analysis I would specify "always use the income-statement table value" in a future spec.

(Other unspecified behaviours that also turned out correct: the executives script treats "Mr. Borders succeeds Chris Kondo" as a departure for Kondo, and records Tim Cook's "transition from CEO to Executive Chair" as a single `both` event.)

---

**Reflection**

Vibe coding made it fast to build both pipelines, but the executive-events run shows why validation matters: the first run didn't crash and printed a plausible row count, yet about a third of the rows were noise. Looking at the actual source text was what made the fixes accurate. Next time I would ask for a raw-text dump in the original spec, so I can check the output against the source from the first run.
