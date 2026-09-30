# =============================================================================
# Script:      hw03_executives.py
# Data source: SEC EDGAR Form 8-K filings, Item 5.02 (Departure of Directors or
#              Certain Officers; Election of Directors; Appointment of Certain
#              Officers)
# Author:      Aiden James
# Generated:   2026-09-30
# Description: For five public companies, finds every Item 5.02 8-K filed in the
#              past 12 months, isolates the Item 5.02 text, extracts one row per
#              departure/appointment event (person, title, effective date), and
#              saves the events to hw03/executive_events.csv.
# Run from the repository root:  python hw03/hw03_executives.py
# =============================================================================

import csv
import os
import re
import time
from datetime import date, datetime

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

OUTPUT_PATH = "hw03/executive_events.csv"
CSV_COLUMNS = [
    "company", "ticker", "cik", "filing_date",
    "event_type", "person_name", "title", "effective_date",
]
NOT_FOUND = "NOT_FOUND"

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
DOCUMENT_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{document}"

# -----------------------------------------------------------------------------
# Keyword lists and regex patterns (kept here so they are easy to improve).
# -----------------------------------------------------------------------------

# Departure language. The person is normally the subject BEFORE the keyword
# ("Kate Adams ... will retire"). "retirement plan"-style compensation phrases
# are excluded, and "termination" is deliberately NOT a keyword because it
# appears in almost every non-compete / severance clause.
DEPARTURE_PATTERN = re.compile(
    r"\b(?:resign(?:s|ed|ing|ation)?|retire(?:s|d)?|retiring"
    r"|retirement(?!\s(?:plan|savings|benefit|program|account|contribution))"
    r"|step(?:s|ped|ping)?\sdown|depart(?:s|ed|ing|ure)?(?!\s(?:of|from)\s(?:directors|certain))"
    r"|not\s(?:to\s)?stand\sfor\sre-?election|leave\sthe\sCompany|separate\sfrom\semployment)\b",
    re.IGNORECASE,
)

# Succession: "Mr. Borders succeeds Chris Kondo" -> the person AFTER the
# keyword is leaving the role.
SUCCESSION_PATTERN = re.compile(r"\bsucceed(?:s|ed|ing)?\b", re.IGNORECASE)

# Role change: "Tim Cook will transition from his role as CEO to Executive Chair"
# -> the same person both leaves one role and takes another.
TRANSITION_PATTERN = re.compile(
    r"\btransition(?:s|ing)?\sfrom\s(?:his|her|their)\s(?:role|position)[^.;]{0,100}?\bto\b",
    re.IGNORECASE,
)

# Appointment language. "named executive officer" is a compensation term,
# not an appointment, so it is excluded.
APPOINTMENT_PATTERN = re.compile(
    r"\b(?:appoint(?:s|ed|ing|ment)?|elect(?:s|ed|ing)?|named(?!\sexecutive\sofficer)"
    r"|promot(?:ed|ion|ions)|hired|will\s(?:join|become))\b",
    re.IGNORECASE,
)
# "X was appointed" (person before) vs. "the Board appointed X" (person after).
PASSIVE_BEFORE = re.compile(r"\b(?:was|were|been|be|is|are)(?:\s(?:also|each|subsequently|previously|today))?\s$")

# A person's full name: optional first initial, first name, optional middle
# initial, then one or two surname words (handles "McMillon", "Di Sibio").
NAME_PATTERN = re.compile(
    r"\b(?:[A-Z]\.\s)?[A-Z][a-z]+(?:\s[A-Z]\.)?(?:\s[A-Z][a-zA-Z'\-]+){1,2}(?:,?\s(?:Jr\.|Sr\.|II|III|IV))?"
)
# "Mr. Furner", "Ms. Nora Johnson", "Mr. Gawel's" -> refers to a full name.
HONORIFIC_PATTERN = re.compile(r"\b(?:Mr|Ms|Mrs|Dr|Mx)\.\s([A-Z][a-zA-Z\-]+(?:\s[A-Z][a-zA-Z\-]+)?)")
# Sentence-opening pronouns that refer to the most recently mentioned person.
PRONOUN_PATTERN = re.compile(r"\b(?:He|She|His|Her|They|Their)\b")

# Capitalised words that are never part of a person's name.
NAME_STOPWORDS = {
    "a", "an", "and", "the", "of", "for", "on", "in", "as", "at", "to", "by", "this", "that",
    "also", "not", "board", "directors", "director", "chief", "executive", "officer", "officers",
    "president", "presidents", "vice", "senior", "company", "corporation", "inc", "co", "chairman",
    "chair", "chairwoman", "general", "counsel", "financial", "operating", "technology",
    "accounting", "committee", "compensation", "item", "form", "section", "exhibit", "securities",
    "exchange", "commission", "act", "united", "states", "apple", "microsoft", "nvidia",
    "jpmorgan", "jpmorganchase", "chase", "walmart", "bank", "annual", "meeting", "shareholders",
    "stockholders", "plan", "agreement", "agreements", "report", "current", "human", "resources",
    "people", "global", "group", "international", "north", "america", "legal", "policy",
    "retirement", "equity", "award", "awards", "stock", "effective", "fiscal", "following", "upon",
    "his", "her", "their", "he", "she", "they", "prior", "since", "new", "principal", "lead",
    "independent", "member", "trust", "finance", "audit", "nominating", "governance", "risk",
    "operations", "services", "cloud", "data", "center", "signature", "signatures", "pursuant",
    "dated", "date", "u.s", "us", "mr", "ms", "mrs", "dr", "messrs", "our", "its", "january",
    "february", "march", "april", "may", "june", "july", "august", "september", "october",
    "november", "december", "incentive", "restricted", "performance", "share", "units", "cash",
    "bonus", "salary", "base", "offer", "letter", "secretary", "treasurer", "controller",
    "strategy", "marketing", "sales", "worldwide", "commercial", "investment", "consumer",
    "community", "banking", "asset", "wealth", "management", "corporate", "marketplace", "sam's",
    "club", "store", "stores", "covenant", "compete", "non-compete", "non-competition",
    "achievement", "target", "goals", "firm", "transition", "successor", "hardware",
    "engineering", "retention", "continuity", "development", "regulation", "proxy", "statement",
    "standard", "index", "composite", "field", "variable", "payment", "position", "industry",
}

# Job titles. Title words are matched case-insensitively ("president and chief
# executive officer"), abbreviations (CEO, VP, CAO) case-sensitively.
_TITLE_CORE = (
    r"(?:(?i:(?:executive|senior|corporate|group|sole)\s)?(?i:vice\s)?"
    r"(?:(?i:chair(?:man|woman)?(?:\sof\s(?:the\s)?board(?:\sof\sdirectors)?)?"
    r"|lead\sindependent\sdirector|chief(?:\s[a-z&]+){1,3}\sofficer|(?:co-)?presidents?"
    r"|general\scounsel|(?:corporate\s)?secretary|treasurer|(?:corporate\s)?controller"
    r"|principal\s(?:accounting|financial|executive)\sofficer"
    r"|(?:a\s)?member\sof\sthe\sboard(?:\sof\sdirectors)?|director(?!s))"
    r"|(?:Co-)?C[A-Z]{1,2}Os?|S?E?VP"
    r"|(?:(?<=to\s)|(?<=from\s)|(?<=join\s))(?:its|the)\sBoard(?:\sof\sDirectors)?))"
)
# Optional "of Walmart U.S." / ", Worldwide Field Operations" after a title.
_TITLE_SUFFIX = (
    r"(?:\s(?:of|for)\s(?:the\s)?[A-Z][A-Za-z.&'\-]*(?:\s(?:&\s)?[A-Z][A-Za-z.&'\-]*){0,3})?"
    r"(?:,\s(?!and\b)[A-Z][A-Za-z.&'\-]*(?:\s(?:&\s)?[A-Z][A-Za-z.&'\-]*){0,3})?"
)
_TITLE_UNIT = _TITLE_CORE + _TITLE_SUFFIX
TITLE_PATTERN = re.compile(_TITLE_UNIT + r"(?:(?:,\s(?:and\s)?|\sand\s|\s&\s)" + _TITLE_UNIT + r")*")

MONTH_DATE = (r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
              r"\s\d{1,2},\s\d{4}")
# A defined date: 'September 1, 2026 (the "Transition Date")'. Later mentions
# of "the Transition Date" are replaced with the actual date.
DEFINED_DATE_PATTERN = re.compile(r"(" + MONTH_DATE + r")\s*\((?:the\s)?\"([A-Z][A-Za-z ]{2,40}?)\"\)")
# Effective date: a full date shortly after "effective" (normalised to YYYY-MM-DD) ...
EFFECTIVE_DATE_PATTERN = re.compile(r"effective\s[^.;]{0,120}?(" + MONTH_DATE + r")", re.IGNORECASE)
# ... or wording such as "effective immediately" / "effective upon ..." (kept as written) ...
EFFECTIVE_WORDING_PATTERN = re.compile(
    r"effective\s(immediately|upon\s[^,.;]{3,70}|at\sthe\s[^,.;]{3,60}|following\s[^,.;]{3,60})",
    re.IGNORECASE,
)
# ... or a full date introduced by on/as of/through/until ...
OTHER_DATE_PATTERN = re.compile(r"\b(?:on|as\sof|through|until)\s(" + MONTH_DATE + r")")
# ... or "at/until the 2026 annual shareholder meeting" / "retirement in late 2026".
MEETING_WORDING_PATTERN = re.compile(
    r"(?:at|until)\sthe\s(?:Company's\s)?((?:\d{4}\s)?annual\s(?:shareholders?'?|stockholders?'?)\s?meeting)",
    re.IGNORECASE,
)
RETIREMENT_WHEN_PATTERN = re.compile(r"retirement\sin\s((?:early|mid|late)[\s-]\d{4})", re.IGNORECASE)

# Item 5.02 section boundaries.
ITEM_502_START = re.compile(r"Item\s*5\.02", re.IGNORECASE)
NEXT_ITEM = re.compile(r"Item\s*\d{1,2}\.\d{2}|SIGNATURES?\b", re.IGNORECASE)

# The standard Item 5.02 heading contains "Departure", "Election" and
# "Appointment" itself, so it is removed before searching for events.
ITEM_502_HEADING = re.compile(
    r"\.?\s*Departure of Directors or (?:Certain )?(?:Principal )?Officers.{0,250}?"
    r"Compensatory Arrangements of Certain Officers\.?",
    re.IGNORECASE,
)


# -----------------------------------------------------------------------------
# Download helpers
# -----------------------------------------------------------------------------

def sec_get(url):
    """GET a URL from SEC with the required User-Agent, a timeout and a pause."""
    time.sleep(REQUEST_PAUSE_SECONDS)
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response


def html_to_text(html):
    """Strip HTML tags, straighten curly quotes and collapse whitespace."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(" ")
    text = (text.replace("’", "'").replace("‘", "'")
                .replace("“", '"').replace("”", '"'))
    return re.sub(r"\s+", " ", text).strip()


def twelve_month_cutoff(today):
    """The same calendar day one year ago (Feb 29 -> Feb 28)."""
    try:
        return today.replace(year=today.year - 1)
    except ValueError:
        return today.replace(year=today.year - 1, day=28)


def get_502_filings(cik, cutoff):
    """STEP 2: 8-K filings with Item 5.02 filed on/after the cutoff date."""
    data = sec_get(SUBMISSIONS_URL.format(cik=cik)).json()
    recent = data["filings"]["recent"]
    matches = []
    for i, form in enumerate(recent["form"]):
        items = recent["items"][i] or ""
        filing_date = recent["filingDate"][i]
        if (form == "8-K" and "5.02" in items.split(",")
                and datetime.strptime(filing_date, "%Y-%m-%d").date() >= cutoff):
            matches.append({
                "filing_date": filing_date,
                "accession": recent["accessionNumber"][i],
                "primary_document": recent["primaryDocument"][i],
            })
    matches.sort(key=lambda f: f["filing_date"])
    return matches


def isolate_item_502(text):
    """STEP 3: the text from 'Item 5.02' to the next Item heading / signatures."""
    start = ITEM_502_START.search(text)
    if not start:
        return text
    rest = text[start.end():]
    end = NEXT_ITEM.search(rest)
    section = rest[: end.start() if end else len(rest)]
    return ITEM_502_HEADING.sub(" ", section, count=1).strip()


# -----------------------------------------------------------------------------
# Text helpers for event extraction
# -----------------------------------------------------------------------------

def replace_defined_dates(text):
    """'effective September 1, 2026 (the "Transition Date")' ... 'on the Transition Date'
    -> every later 'the Transition Date' becomes 'September 1, 2026'."""
    definitions = {term: day for day, term in DEFINED_DATE_PATTERN.findall(text)}
    text = DEFINED_DATE_PATTERN.sub(lambda m: m.group(1), text)
    for term, day in definitions.items():
        text = re.sub(r"\bthe\s" + re.escape(term) + r"\b", day, text)
    return text


def split_sentences(text):
    """Split on sentence-ending periods, ignoring honorifics, initials and 'Inc.'."""
    protected = re.sub(r"\b(Mr|Ms|Mrs|Dr|Mx|Messrs|No|St|Jr|Sr)\.", r"\1<DOT>", text)
    protected = re.sub(r"\b(Inc|Co|Corp|Ltd|U\.S)\.(?=\s*[(,a-z])", r"\1<DOT>", protected)
    protected = re.sub(r"\b([A-Z])\.(?=\s[A-Z])", r"\1<DOT>", protected)   # "C. Douglas"
    parts = re.split(r"(?<=[.;])\s+(?=[A-Z\"(])", protected)
    return [p.replace("<DOT>", ".") for p in parts if p.strip()]


def clean_name(candidate):
    """Longest run of non-stopword tokens; needs a first name and a surname."""
    tokens = candidate.replace(",", "").split()
    best, current = [], []
    for token in tokens:
        is_initial = re.fullmatch(r"[A-Z]\.", token) is not None   # "A." in "Todd A. Combs"
        if (not is_initial and token.lower().strip(".'") in NAME_STOPWORDS) or token.endswith("'s"):
            current = []
        else:
            current.append(token)
            if len(current) > len(best):
                best = list(current)
    if len([t for t in best if len(t.rstrip(".")) > 1]) < 2:
        return None
    return " ".join(best)


def core_tokens(name):
    return [t for t in name.split() if t.rstrip(".") not in ("Jr", "Sr", "II", "III", "IV")]


def build_canonical_names(names):
    """Map short forms to the fullest version: 'Nora Johnson' -> 'Suzanne Nora Johnson',
    'John Furner' -> 'John R. Furner'."""
    canonical = {}
    for name in names:
        tokens = core_tokens(name)
        best = name
        for other in names:
            other_tokens = core_tokens(other)
            if len(other) <= len(best):
                continue
            is_suffix = other_tokens[-len(tokens):] == tokens
            same_first_last = other_tokens[0] == tokens[0] and other_tokens[-1] == tokens[-1]
            if is_suffix or same_first_last:
                best = other
        canonical[name] = best
    return canonical


def resolve_honorific(words, canonical):
    """'Nora Johnson' / 'Gawel' -> the full name it refers to (or None)."""
    full_names = set(canonical.values())
    for candidate in (words, words.split()[0]):
        cand_tokens = candidate.split()
        for full in full_names:
            if core_tokens(full)[-len(cand_tokens):] == cand_tokens:
                return full
    return None


def find_mentions(sentence, canonical):
    """Every person mention in a sentence as (start, end, full name)."""
    mentions = []
    for match in NAME_PATTERN.finditer(sentence):
        name = clean_name(match.group(0))
        if name:
            start = match.start() + max(match.group(0).find(name.split()[0]), 0)
            mentions.append((start, match.end(), canonical.get(name, name)))
    for match in HONORIFIC_PATTERN.finditer(sentence):
        if any(s <= match.start(1) < e for s, e, _ in mentions):
            continue  # "Mr. John R. Furner": the full name is already captured
        full = resolve_honorific(match.group(1), canonical)
        if full:
            mentions.append((match.start(), match.end(), full))
    return sorted(mentions)


def pick_person(sentence, mentions, keyword_start, keyword_end, direction):
    """Choose who a keyword refers to. Returns a list of names (usually one)."""
    before = [m for m in mentions if m[1] <= keyword_start]
    after = [m for m in mentions if m[0] >= keyword_end and m[0] - keyword_end <= 80]
    if direction == "after" and after:
        return [after[0][2]]
    if before:
        chosen = [before[-1]]
        # "Doug Petno, 61, and Troy Rohrbaugh, 56, ... have been elected"
        for previous in reversed(before[:-1]):
            gap = sentence[previous[1]:chosen[-1][0]]
            if re.fullmatch(r"[^.;]{0,20}\band\s", gap):
                chosen.append(previous)
            else:
                break
        return [m[2] for m in reversed(chosen)]
    if after:
        return [after[0][2]]
    return []


def clean_title(title):
    title = re.sub(r"^a\s", "", title.strip(" ,"))
    title = re.sub(r"\bPresidents\b", "President", title)
    title = re.sub(r"\bCEOs\b", "CEO", title)
    if re.match(r"(?:its|the)\sBoard", title):
        return "Director"
    # Drop a trailing "of the Company" / "of Microsoft Corporation" (the company is its own column)
    title = re.sub(r"\sof\s(?:the\s)?(?:Company|Firm|[A-Z][A-Za-z]+\s(?:Inc\.?|Corporation|Co\.?))$", "", title)
    # "president and chief executive officer" -> "President and Chief Executive Officer"
    if title == title.lower():
        title = " ".join(w if w in ("and", "of", "the", "a") else w.capitalize() for w in title.split())
    return title


def find_title(sentence, keyword_start, keyword_end, kind):
    titles = [(m.start(), m.end(), clean_title(m.group(0))) for m in TITLE_PATTERN.finditer(sentence)]
    if not titles:
        return None
    if kind == "appointment":
        after = [t for t in titles if t[0] >= keyword_end and t[0] - keyword_end <= 150]
        # Prefer "... as President and Chief Executive Officer"
        for t in after:
            if re.search(r"\bas\s(?:the\s|its\s|our\s|a\s|[A-Z][A-Za-z]+'s\s)?$", sentence[:t[0]]):
                return t[2]
        if after and after[0][0] - keyword_end <= 60:
            return after[0][2]
    position = keyword_start
    return min(titles, key=lambda t: 0 if t[0] <= position <= t[1]
               else min(abs(position - t[0]), abs(position - t[1])))[2]


def to_iso(raw):
    return datetime.strptime(raw, "%B %d, %Y").strftime("%Y-%m-%d")


def find_effective_date(sentence, position):
    def nearest(matches):
        return min(matches, key=lambda m: abs(m.start() - position))
    found = list(EFFECTIVE_DATE_PATTERN.finditer(sentence))
    if found:
        return to_iso(nearest(found).group(1))
    found = list(EFFECTIVE_WORDING_PATTERN.finditer(sentence))
    if found:
        return nearest(found).group(1).strip()
    found = list(OTHER_DATE_PATTERN.finditer(sentence))
    if found:
        return to_iso(nearest(found).group(1))
    for pattern in (MEETING_WORDING_PATTERN, RETIREMENT_WHEN_PATTERN):
        found = list(pattern.finditer(sentence))
        if found:
            return nearest(found).group(1)
    return None


def find_keywords(sentence):
    """All event keywords in a sentence as (start, end, event_type, direction)."""
    keywords = []
    for m in TRANSITION_PATTERN.finditer(sentence):
        keywords.append((m.start(), m.start() + 10, "departure", "before"))
        keywords.append((m.end() - 2, m.end(), "appointment", "before"))
    for m in DEPARTURE_PATTERN.finditer(sentence):
        keywords.append((m.start(), m.end(), "departure", "before"))
    for m in SUCCESSION_PATTERN.finditer(sentence):
        keywords.append((m.start(), m.end(), "departure", "after"))
    for m in APPOINTMENT_PATTERN.finditer(sentence):
        word = m.group(0).lower()
        if word in ("appointment", "promotion", "promotions"):
            direction = "after" if sentence[m.end():m.end() + 4] == " of " else "before"
            if re.search(r"\b(?:his|her|their)\s$", sentence[:m.start()]):
                direction = "after"   # "In connection with his appointment, Mr. Gawel ..."
        elif word.startswith("will"):
            direction = "before"
        else:
            direction = "before" if PASSIVE_BEFORE.search(sentence[:m.start()]) else "after"
        keywords.append((m.start(), m.end(), "appointment", direction))
    return sorted(keywords)


# -----------------------------------------------------------------------------
# STEP 4 + 5: event extraction
# -----------------------------------------------------------------------------

def extract_events(section_text):
    """
    Return one event per person: event_type, person_name, title, effective_date.
    Each departure/appointment keyword is attached to the person it describes
    (the subject before it, or the object after it for "the Board appointed X"
    and "succeeds X"). A person with both a departure and an appointment in the
    same filing (a role change) is reported once as "both".
    """
    text = replace_defined_dates(section_text)
    sentences = split_sentences(text)

    # Collect full names first so "Mr. Furner" can be resolved to "John R. Furner".
    names = []
    for sentence in sentences:
        for match in NAME_PATTERN.finditer(sentence):
            name = clean_name(match.group(0))
            if name and name not in names:
                names.append(name)
    canonical = build_canonical_names(names)

    people, order = {}, []
    first_mention_sentence = {}
    last_person = None

    for index, sentence in enumerate(sentences):
        mentions = find_mentions(sentence, canonical)
        for m in mentions:
            first_mention_sentence.setdefault(m[2], (sentence, m[0]))

        for start, end, event_type, direction in find_keywords(sentence):
            chosen = pick_person(sentence, mentions, start, end, direction)
            if not chosen and last_person and PRONOUN_PATTERN.search(sentence):
                chosen = [last_person]
            for name in chosen:
                if name not in people:
                    people[name] = {"types": [], "departure_title": None,
                                    "appointment_title": None, "date": None}
                    order.append(name)
                record = people[name]
                if event_type not in record["types"]:
                    record["types"].append(event_type)
                title_key = event_type + "_title"
                if record[title_key] is None:
                    record[title_key] = find_title(sentence, start, end, event_type)
                if record["date"] is None:
                    record["date"] = find_effective_date(sentence, start)
                    # Not in this sentence? Try the next sentence about the same person.
                    if record["date"] is None and index + 1 < len(sentences):
                        following = sentences[index + 1]
                        if any(m[2] == name for m in find_mentions(following, canonical)):
                            record["date"] = find_effective_date(following, 0)

        if mentions:
            last_person = mentions[-1][2]

    events = []
    for name in order:
        record = people[name]
        departure_title, appointment_title = record["departure_title"], record["appointment_title"]
        # Fallback title: the one closest to where the person is first introduced.
        if not departure_title and not appointment_title and name in first_mention_sentence:
            sentence, position = first_mention_sentence[name]
            departure_title = find_title(sentence, position, position, "departure")
        if len(record["types"]) == 2:
            event_type = "both"
            if departure_title and appointment_title and departure_title != appointment_title:
                title = "{} to {}".format(departure_title, appointment_title)
            else:
                title = appointment_title or departure_title
        else:
            event_type = record["types"][0]
            title = appointment_title if event_type == "appointment" else departure_title
            title = title or departure_title or appointment_title
        events.append({
            "event_type": event_type,
            "person_name": name,
            "title": title or NOT_FOUND,
            "effective_date": record["date"] or NOT_FOUND,
        })
    return events


# -----------------------------------------------------------------------------
# Main pipeline
# -----------------------------------------------------------------------------

def main():
    cutoff = twelve_month_cutoff(date.today())
    print("Looking for Item 5.02 8-K filings filed on or after {}".format(cutoff.isoformat()))
    rows = []

    for company in COMPANIES:
        ticker = company["ticker"]
        print("\n=== {} ({}) ===".format(company["company"], ticker))
        company_event_count = 0

        # STEP 2: find Item 5.02 filings from the past 12 months
        try:
            filings = get_502_filings(company["cik"], cutoff)
        except Exception as error:
            print("WARNING: could not load EDGAR submissions for {}: {}".format(ticker, error))
            filings = []

        for filing in filings:
            filing_date = filing["filing_date"]
            try:
                # STEP 3: download the 8-K, strip HTML, isolate Item 5.02
                url = DOCUMENT_URL.format(
                    cik_int=str(int(company["cik"])),
                    acc_nodash=filing["accession"].replace("-", ""),
                    document=filing["primary_document"],
                )
                text = html_to_text(sec_get(url).text)
                section = isolate_item_502(text)

                # STEP 4 + 5: one row per event
                events = extract_events(section)
            except Exception as error:
                print("WARNING: {} {} - error while processing filing: {}".format(ticker, filing_date, error))
                continue

            # STEP 6: filings with no departure/appointment language get no row
            if not events:
                print("{} | {} | Item 5.02 filing skipped: no departure/appointment language found".format(
                    ticker, filing_date))
                continue

            for event in events:
                row = {
                    "company": company["company"], "ticker": ticker, "cik": company["cik"],
                    "filing_date": filing_date,
                }
                row.update(event)
                rows.append(row)
                company_event_count += 1
                # STEP 7: print each event
                print("{} | {} | {} | {} | {}".format(
                    ticker, filing_date, row["event_type"], row["person_name"], row["title"]))

        # STEP 8: companies with no events are reported, not skipped
        if company_event_count == 0:
            print("{}: No executive events in past 12 months".format(ticker))

    # STEP 9: save (header row is written even if there are no events)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: (NOT_FOUND if row.get(col) in (None, "") else row[col]) for col in CSV_COLUMNS})

    print("\nSaved {} rows to {}".format(len(rows), OUTPUT_PATH))


if __name__ == "__main__":
    main()
