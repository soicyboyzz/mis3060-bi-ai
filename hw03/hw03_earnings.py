# =============================================================================
# Script:      hw03_earnings.py
# Data source: SEC EDGAR Form 8-K filings, Item 2.02 (Results of Operations)
# Author:      Aiden James
# Generated:   2026-09-29
# Description: For five public companies, finds the four most recent Item 2.02
#              8-K filings, downloads each earnings press release (EX-99.x),
#              extracts revenue, diluted EPS, net income and reporting period
#              with regular expressions, and saves the rows to
#              hw03/earnings_history.csv (missing values stored as "NOT_FOUND").
# Run from the repository root:  python hw03/hw03_earnings.py
# =============================================================================

import csv
import os
import re
import time

import requests
from bs4 import BeautifulSoup

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# STEP 1: User-Agent header required by SEC EDGAR. Passed on EVERY request.
HEADERS = {"User-Agent": "MIS3060 Villanova adumm@villanova.edu"}
REQUEST_PAUSE_SECONDS = 0.2  # stay well under SEC's 10 requests/second limit
REQUEST_TIMEOUT_SECONDS = 30

COMPANIES = [
    {"company": "Apple Inc.", "ticker": "AAPL", "cik": "0000320193"},
    {"company": "Microsoft Corporation", "ticker": "MSFT", "cik": "0000789019"},
    {"company": "NVIDIA Corporation", "ticker": "NVDA", "cik": "0001045810"},
    {"company": "JPMorgan Chase & Co.", "ticker": "JPM", "cik": "0000019617"},
    {"company": "Walmart Inc.", "ticker": "WMT", "cik": "0000104169"},
]

FILINGS_PER_COMPANY = 4
OUTPUT_PATH = "hw03/earnings_history.csv"
CSV_COLUMNS = [
    "company", "ticker", "cik", "filing_date", "period",
    "revenue_reported", "eps_diluted", "net_income",
]
NOT_FOUND = "NOT_FOUND"

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVE_BASE = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/"
SEC_ROOT = "https://www.sec.gov"

# -----------------------------------------------------------------------------
# Regex patterns (kept here so they are easy to improve later).
# Each list is tried in order; the first pattern that matches wins.
# -----------------------------------------------------------------------------
NUM = r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)"   # 94.9 / 94,930 / 1,234.5
UNIT = r"\s*(billion|million)"
HYPHEN = r"[\s\-‐-—]"                          # space or any dash

# Revenue in prose, with a unit word ("$94.9 billion").
REVENUE_PROSE_PATTERNS = [
    # "quarterly revenue of $94.9 billion", "Revenue was $65.6 billion",
    # "Total revenue was $169.6 billion", "reported revenue of $42.7 billion"
    r"(?:total |net |quarterly |reported )?revenues?,? (?:was|were|of|totaled|reached|increased to|rose to)\s*(?:a record )?\$\s*" + NUM + UNIT,
    # "net sales of $94.9 billion"
    r"net sales,? (?:was|were|of|totaled)\s*(?:a record )?\$\s*" + NUM + UNIT,
    # "revenue for the third quarter ended October 27, 2024, of $35.1 billion"
    r"revenues?\b[^$]{0,80}?\$\s*" + NUM + UNIT,
]
# Revenue from a financial table (tables are reported in millions).
REVENUE_TABLE_PATTERNS = [
    r"total (?:net sales|net revenues?|revenues?)\s*\$?\s*" + NUM + r"(?!\s*(?:billion|million|%))",
    r"\brevenues?\s*\$\s*" + NUM + r"(?!\s*(?:billion|million|%))",
]

# Diluted EPS (always dollars and cents).
EPS_PATTERNS = [
    r"diluted earnings per (?:common )?share[^$]{0,40}?\$\s*(\d+\.\d{2})",
    r"earnings per diluted share[^$]{0,40}?\$\s*(\d+\.\d{2})",
    r"\b(?:GAAP |diluted )?EPS,? (?:was |of |were )?\$\s*(\d+\.\d{2})",
    r"\bdiluted\s*\$\s*(\d+\.\d{2})",
]

# Net income in prose, with a unit word ("$24.7 billion").
NET_INCOME_PROSE_PATTERNS = [
    r"net income(?: attributable to [A-Za-z .,&]{1,40}?)?,? (?:was|were|of|totaled)\s*(?:a record )?\$\s*" + NUM + UNIT,
]
# Net income from a financial table (millions). The "attributable to the
# company" line is preferred over the consolidated line when both exist.
NET_INCOME_TABLE_PATTERNS = [
    r"net income attributable to (?:Walmart|common stockholders|the company)\s*\$?\s*" + NUM + r"(?!\s*(?:billion|million|%))",
    r"net income\s*\$\s*" + NUM + r"(?!\s*(?:billion|million|%))",
]

# Reporting period. The earliest match in the text is used.
QUARTER = r"(?:first|second|third|fourth)"
MONTH_DATE = r"[A-Z][a-z]+ \d{1,2}, \d{4}"
PERIOD_PATTERNS = [
    # "fiscal 2024 fourth quarter ended September 28, 2024" (Apple)
    r"fiscal(?: year)? \d{4},? " + QUARTER + r" quarter(?: ended " + MONTH_DATE + r")?",
    # "third quarter of fiscal 2025" / "third quarter ended October 27, 2024" (NVIDIA)
    QUARTER + r" quarter(?: of fiscal(?: year)? \d{4})?,? ended " + MONTH_DATE,
    QUARTER + r" quarter of fiscal(?: year)? \d{4}",
    # "third-quarter 2024" (JPMorgan)
    QUARTER + HYPHEN + r"quarter(?: fiscal(?: year)?)? (?:\d{4}|FY\s?\d{2})",
    # "Q3 FY25" (Walmart)
    r"\bQ[1-4] (?:FY|fiscal(?: year)? )\s?\d{2,4}",
    # "quarter ended September 30, 2024" (Microsoft)
    r"quarter ended " + MONTH_DATE,
]


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

def sec_get(url):
    """GET a URL from SEC with the required User-Agent, a timeout and a pause."""
    time.sleep(REQUEST_PAUSE_SECONDS)
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response


def html_to_text(html):
    """Strip HTML tags and collapse all whitespace into single spaces."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(" ")
    return re.sub(r"\s+", " ", text).strip()


def to_number(value_str):
    """'1,234.5' -> 1234.5; whole numbers returned as int."""
    value = float(value_str.replace(",", ""))
    value = round(value, 2)
    return int(value) if value.is_integer() else value


def to_millions(value_str, unit):
    """Convert a figure with a unit word into millions of dollars."""
    value = float(value_str.replace(",", ""))
    if unit.lower() == "billion":
        value *= 1000
    return to_number(str(round(value, 2)))


def first_match(patterns, text):
    """Return the first regex match from an ordered list of patterns."""
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match
    return None


def extract_money_in_millions(prose_patterns, table_patterns, text):
    """Try prose patterns (with a unit word) first, then table patterns (millions)."""
    match = first_match(prose_patterns, text)
    if match:
        return to_millions(match.group(1), match.group(2))
    match = first_match(table_patterns, text)
    if match:
        return to_number(match.group(1))
    return NOT_FOUND


def extract_eps(text):
    match = first_match(EPS_PATTERNS, text)
    return to_number(match.group(1)) if match else NOT_FOUND


def extract_period(text):
    """Use the earliest period phrase that appears in the press release."""
    best = None
    for pattern in PERIOD_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match and (best is None or match.start() < best.start()
                      or (match.start() == best.start() and len(match.group(0)) > len(best.group(0)))):
            best = match
    if best is None:
        return NOT_FOUND
    return re.sub(r"[‐-—]", "-", best.group(0))  # normalise fancy dashes


def get_earnings_filings(cik):
    """STEP 2 + 3: return the most recent 8-K filings that include Item 2.02."""
    data = sec_get(SUBMISSIONS_URL.format(cik=cik)).json()
    recent = data["filings"]["recent"]
    matches = []
    for i, form in enumerate(recent["form"]):
        items = recent["items"][i] or ""
        if form == "8-K" and "2.02" in items.split(","):
            matches.append({
                "filing_date": recent["filingDate"][i],
                "accession": recent["accessionNumber"][i],
                "primary_document": recent["primaryDocument"][i],
            })
    matches.sort(key=lambda f: f["filing_date"], reverse=True)
    return matches[:FILINGS_PER_COMPANY]


def find_press_release_url(cik, accession):
    """STEP 4: locate the EX-99 press release (.htm) on the filing index page."""
    cik_int = str(int(cik))
    acc_nodash = accession.replace("-", "")
    folder_url = ARCHIVE_BASE.format(cik_int=cik_int, acc_nodash=acc_nodash)
    index_url = folder_url + accession + "-index.htm"

    soup = BeautifulSoup(sec_get(index_url).text, "html.parser")
    documents = []  # (type, href)
    for table in soup.find_all("table", class_="tableFile"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            link = cells[2].find("a")
            if not link or not link.get("href"):
                continue
            href = link["href"].replace("/ix?doc=", "")
            documents.append((cells[3].get_text(strip=True).upper(), href))

    htm_docs = [(t, h) for t, h in documents if h.lower().endswith((".htm", ".html"))]
    # Preferred: type EX-99.1, then any EX-99.x
    for wanted in ("EX-99.1", "EX-99"):
        for doc_type, href in htm_docs:
            if doc_type.startswith(wanted):
                return SEC_ROOT + href if href.startswith("/") else folder_url + href
    # Fallback: any .htm whose file name contains "99"
    for doc_type, href in htm_docs:
        if "99" in href.rsplit("/", 1)[-1]:
            return SEC_ROOT + href if href.startswith("/") else folder_url + href
    return None


def not_found_row(company, filing_date):
    return {
        "company": company["company"], "ticker": company["ticker"], "cik": company["cik"],
        "filing_date": filing_date, "period": NOT_FOUND, "revenue_reported": NOT_FOUND,
        "eps_diluted": NOT_FOUND, "net_income": NOT_FOUND,
    }


def format_money(value):
    return value if value == NOT_FOUND else "${}M".format(value)


def print_row(row):
    """STEP 6: print each row in the required format."""
    eps = row["eps_diluted"] if row["eps_diluted"] == NOT_FOUND else "${:.2f}".format(row["eps_diluted"])
    print("{} | {} | Revenue: {} | EPS: {} | Net Income: {}".format(
        row["ticker"], row["period"], format_money(row["revenue_reported"]),
        eps, format_money(row["net_income"])))


# -----------------------------------------------------------------------------
# Main pipeline
# -----------------------------------------------------------------------------

def main():
    rows = []

    for company in COMPANIES:
        ticker = company["ticker"]
        print("\n=== {} ({}) ===".format(company["company"], ticker))

        # STEP 2 + 3: find the four most recent Item 2.02 8-K filings
        try:
            filings = get_earnings_filings(company["cik"])
        except Exception as error:
            print("WARNING: could not load EDGAR submissions for {}: {}".format(ticker, error))
            continue
        if len(filings) < FILINGS_PER_COMPANY:
            print("NOTE: only {} Item 2.02 filings found for {}".format(len(filings), ticker))

        for filing in filings:
            filing_date = filing["filing_date"]
            try:
                # STEP 4: find, download and clean the press release
                release_url = find_press_release_url(company["cik"], filing["accession"])
                if release_url is None:
                    print("WARNING: {} {} - no press release exhibit found; skipping extraction".format(ticker, filing_date))
                    row = not_found_row(company, filing_date)
                else:
                    text = html_to_text(sec_get(release_url).text)

                    # STEP 5 + 8: extract fields, NOT_FOUND when no regex match
                    row = {
                        "company": company["company"],
                        "ticker": ticker,
                        "cik": company["cik"],
                        "filing_date": filing_date,
                        "period": extract_period(text),
                        "revenue_reported": extract_money_in_millions(
                            REVENUE_PROSE_PATTERNS, REVENUE_TABLE_PATTERNS, text),
                        "eps_diluted": extract_eps(text),
                        "net_income": extract_money_in_millions(
                            NET_INCOME_PROSE_PATTERNS, NET_INCOME_TABLE_PATTERNS, text),
                    }
            except Exception as error:
                # One bad filing never stops the pipeline.
                print("WARNING: {} {} - error while processing filing: {}".format(ticker, filing_date, error))
                row = not_found_row(company, filing_date)

            rows.append(row)
            print_row(row)  # STEP 6

    # STEP 7: save every row to CSV (no blank cells: missing = "NOT_FOUND")
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: (NOT_FOUND if row.get(col) in (None, "") else row[col]) for col in CSV_COLUMNS})

    print("\nSaved {} rows to {}".format(len(rows), OUTPUT_PATH))


if __name__ == "__main__":
    main()
