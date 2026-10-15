"""Preprocessing: turn a 10-K HTML document into plain text and keep only the financial statements.

A 10-K is hundreds of pages long, but the five metrics we need are on two pages:
the income statement (Revenue, Operating income, Net income, EPS) and the balance
sheet (Total assets). Sending only those pages to the LLM is cheaper and gives it
less to get confused by.

Statement titles appear many times in a 10-K (table of contents, sentences, the
auditor's report, summary tables in the management discussion). The real statement is
recognized by
1. a title that stands alone on its line,
2. typical line items below it (e.g. "Total assets"),
3. a title that says "consolidated" (if any candidate does),
4. many numbers right after it, and
5. no quarterly columns ("Three Months Ended") in its header.

Usage:
    python -m edgar_extract.preprocess      # all filings in the database
"""

import re
import warnings
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from edgar_extract import db
from edgar_extract.config import CACHE_DIR, DATA_DIR
from edgar_extract.edgar import cache_path_for

PROCESSED_DIR = DATA_DIR / "processed"

# 10-K documents are XHTML (inline XBRL); the lenient HTML parser handles them fine.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

BLOCK_TAGS = ["p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table"]

# ---------------------------------------------------------------- HTML -> text


def _table_to_text(table) -> str:
    """One line per table row, cells separated by " | ".

    SEC tables often split "$", "1,234" and ")" into separate cells; glue them back together.
    """
    lines = []
    for row in table.find_all("tr"):
        cells: list[str] = []
        for cell in row.find_all(["td", "th"]):
            text = " ".join(cell.get_text(" ").split())
            text = re.sub(r"\(\s+", "(", re.sub(r"\s+\)", ")", text))  # "( 321 )" -> "(321)"
            if not text:
                continue
            if cells and text in (")", "%", ")%"):
                cells[-1] += text
            elif cells and cells[-1] in ("$", "(", "$("):
                cells[-1] += text
            else:
                cells.append(text)
        if cells:
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def html_to_text(html: bytes | str) -> str:
    """Convert a 10-K HTML document to readable plain text (tables become " | " rows)."""
    soup = BeautifulSoup(html, "lxml")

    # Invisible parts: scripts, styles and the hidden inline-XBRL header.
    for tag in soup(["script", "style", "head"]):
        tag.decompose()
    for tag in soup.find_all(style=re.compile(r"display:\s*none", re.I)):
        tag.decompose()

    # Line breaks in the HTML source are just spaces (as in a browser); real breaks come from tags.
    for string in soup.find_all(string=re.compile(r"\n")):
        string.replace_with(re.sub(r"\s+", " ", string))

    for table in soup.find_all("table"):
        if table.find_parent("table") is None:  # nested tables are handled by their parent
            table.replace_with("\n" + _table_to_text(table) + "\n")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for tag in soup.find_all(BLOCK_TAGS):
        tag.append("\n")

    lines = (" ".join(line.split()) for line in soup.get_text().splitlines())
    return "\n".join(line for line in lines if line)


# ------------------------------------------------------ find financial statements

# "Consolidated" is optional: e.g. Microsoft titles its statements just "INCOME STATEMENTS".
# Some companies drop "statement of": "Consolidated Results of Operations for the Years
# Ended ...", "Consolidated Financial Position at ...". Without the date these are common
# headings in the management discussion, so the date is required here.
INCOME_TITLE = (
    r"(?:consolidated )?(?:statements? of (?:operations|income|earnings)|income statements?)\b"
    r"|consolidated results of operations(?= for the (?:fiscal )?years? ended)"
)
BALANCE_TITLE = (
    r"(?:consolidated )?(?:balance sheets?|statements? of financial (?:position|condition))\b"
    r"|consolidated financial (?:position|condition)(?= (?:at|as of) )"
)
OTHER_TITLE = (
    r"(?:consolidated )?(?:statements? of (?:comprehensive (?:income|loss)|cash flows?"
    r"|(?:changes in )?(?:share|stock)holders[’']? equity|equity)"
    r"|(?:comprehensive income|cash flows?|(?:share|stock)holders[’']? equity) statements?)\b"
)
ANY_TITLE = f"{INCOME_TITLE}|{BALANCE_TITLE}|{OTHER_TITLE}"

# A title line may start with the company name, but must not continue like a sentence,
# a table-of-contents entry ("... for the years ended 2025 ...") or another kind of table.
# A trailing colon introduces a table inside a note ("Consolidated Statements of Income:").
MAX_TITLE_REMAINDER = 60
NOT_A_TITLE = re.compile(
    r"\d|analysis|data|changes|impact|line item|total|refer|see |comprehensive|parent|condensed|segment|gaap|:\s*$",
    re.I,
)
# A title may end with its date, e.g. "... for the Years Ended December 31," (without a year).
TITLE_DATE = re.compile(r"\b(?:for the (?:fiscal )?years? ended|at|as of) [a-z]+ \d{1,2},?$", re.I)
# ... or with a footnote marker, e.g. "Consolidated Balance Sheets (1)".
FOOTNOTE_MARKER = re.compile(r"\(\d\)$")
# Any short line naming a statement ends the previous section.
MAX_STOP_LINE = 100

NUMBER = re.compile(r"\d{1,3}(?:,\d{3})+|\d+\.\d{2}\b")
# Quarterly tables (e.g. a "Quarterly financial data" note) have more columns, hence more numbers.
QUARTERLY = re.compile(r"three months ended|quarter", re.I)
HEADER_CHARS = 300  # where the column headings of a statement are
SCORE_WINDOW = 2_000  # characters after the title in which numbers are counted
MAX_SECTION_CHARS = 20_000


@dataclass(frozen=True)
class StatementKind:
    name: str
    title: str
    required: list[list[str]]  # every inner list needs at least one match (lower-case)


STATEMENTS = [
    StatementKind(
        name="income_statement",
        title=INCOME_TITLE,
        # "profit": some companies call net income just "Profit"; "Net (loss) income" in loss years.
        required=[
            ["net income", "net earnings", "net loss", "net (loss", "net (income", "net (earnings", "profit"],
            ["per share", "per common share", "dilut"],
        ],
    ),
    StatementKind(
        name="balance_sheet",
        title=BALANCE_TITLE,
        # Some balance sheets print the totals without a label ("$117,106"): then only the
        # current-assets/-liabilities subtotals are labeled.
        required=[["total assets", "total current assets"], ["total liabilities", "total current liabilities"]],
    ),
]


@dataclass(frozen=True)
class Section:
    name: str
    title: str
    start: int
    end: int
    score: int

    @property
    def rank(self) -> tuple[bool, int]:
        # Summary tables elsewhere in a 10-K ("Income statement", "Average balance sheet")
        # can hold more numbers than the statement itself, but rarely say "consolidated".
        return "consolidated" in self.title.lower(), self.score


def _matching_lines(text: str, pattern: str):
    """Yield (line_start, line, remainder) for each match; remainder = line without the match."""
    for match in re.finditer(pattern, text, re.I):
        line_start = text.rfind("\n", 0, match.start()) + 1
        line_end = text.find("\n", match.end())
        line_end = len(text) if line_end == -1 else line_end
        line = text[line_start:line_end]
        remainder = (line[: match.start() - line_start] + line[match.end() - line_start :]).strip()
        yield line_start, line.strip(), remainder


def _title_lines(text: str, pattern: str) -> list[tuple[int, str]]:
    """Positions (line start) of lines that are a statement title on their own."""
    titles = []
    for start, line, remainder in _matching_lines(text, pattern):
        remainder = TITLE_DATE.sub("", FOOTNOTE_MARKER.sub("", remainder).strip()).strip()
        if len(remainder) <= MAX_TITLE_REMAINDER and not NOT_A_TITLE.search(remainder):
            titles.append((start, line))
    return titles


def _stop_positions(text: str) -> list[int]:
    """Line starts of every short line that names any financial statement."""
    return sorted({start for start, line, _ in _matching_lines(text, ANY_TITLE) if len(line) <= MAX_STOP_LINE})


def find_statement(text: str, kind: StatementKind) -> Section | None:
    """Locate the real statement of the given kind, or None if not found."""
    stops = _stop_positions(text)

    best: Section | None = None
    for start, title in _title_lines(text, kind.title):
        # The section ends where the next statement begins (or after MAX_SECTION_CHARS).
        next_title = next((pos for pos in stops if pos > start), len(text))
        end = min(next_title, start + MAX_SECTION_CHARS)
        body = text[start:end].lower()
        if not all(any(word in body for word in group) for group in kind.required):
            continue
        if QUARTERLY.search(text, start, start + HEADER_CHARS):
            continue
        score = len(NUMBER.findall(text, start, min(end, start + SCORE_WINDOW)))
        candidate = Section(kind.name, title, start, end, score)
        if best is None or candidate.rank > best.rank:
            best = candidate
    return best


@dataclass(frozen=True)
class Preprocessed:
    text: str
    sections_found: list[str]
    full_text_chars: int

    @property
    def method(self) -> str:
        return "sections" if self.sections_found else "full_text"


def extract_financial_sections(full_text: str) -> Preprocessed:
    """Keep only the income statement and balance sheet. Falls back to the full text."""
    sections = [s for kind in STATEMENTS if (s := find_statement(full_text, kind))]
    if not sections:
        return Preprocessed(full_text, [], len(full_text))
    parts = [f"=== {s.name.upper()} ===\n{full_text[s.start : s.end].strip()}" for s in sections]
    return Preprocessed("\n\n".join(parts), [s.name for s in sections], len(full_text))


def answer_in_text(value: float, metric: str, text: str) -> bool:
    """Does the ground-truth value appear in the text (in dollars, thousands or millions)?

    If not, the LLM cannot possibly find it — a preprocessing problem, not an LLM error.
    """
    plain = text.replace(",", "")
    value = abs(value)  # losses are printed in parentheses: "(2,722)"
    if metric == "EPS":
        variants = {f"{value:.2f}"}
    else:
        # Some companies print one decimal in millions, e.g. "25,493.7".
        variants = {f"{value / scale:.{decimals}f}" for scale in (1e6, 1e3, 1) for decimals in (0, 1)}
    return any(re.search(rf"(?<![\d.]){re.escape(v)}(?!\d)", plain) for v in variants)


def estimate_tokens(chars: int) -> int:
    """Rough token estimate (~4 characters per token). Phase 4 logs exact counts from the API."""
    return round(chars / 4)


# --------------------------------------------------------------------- pipeline


def preprocess_filing(accession_number: str, html_path: Path, db_path: Path = db.DB_PATH) -> Preprocessed:
    result = extract_financial_sections(html_to_text(html_path.read_bytes()))
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / f"{accession_number}.txt"
    out_path.write_text(result.text, encoding="utf-8")

    with db.connect(db_path) as conn:
        db.save_preprocessing(
            conn,
            accession_number=accession_number,
            method=result.method,
            sections_found=result.sections_found,
            chars_before=result.full_text_chars,
            chars_after=len(result.text),
            est_tokens_before=estimate_tokens(result.full_text_chars),
            est_tokens_after=estimate_tokens(len(result.text)),
            text_path=str(out_path.relative_to(DATA_DIR.parent)),
        )
    return result


def main() -> None:
    with db.connect() as conn:
        filings = conn.execute(
            "SELECT accession_number, ticker, fiscal_year, url FROM filings ORDER BY ticker, fiscal_year DESC"
        ).fetchall()

    print(f"{'Ticker':6} {'FY':4} {'tokens before':>14} {'tokens after':>13} {'kept':>6}  sections")
    total_before = total_after = 0
    for row in filings:
        result = preprocess_filing(row["accession_number"], cache_path_for(row["url"], CACHE_DIR))
        before, after = estimate_tokens(result.full_text_chars), estimate_tokens(len(result.text))
        total_before += before
        total_after += after
        sections = ", ".join(result.sections_found) or "NONE FOUND — using full text"
        print(f"{row['ticker']:6} {row['fiscal_year']:4} {before:>14,} {after:>13,} {after / before:>6.1%}  {sections}")

    print(f"{'Total':11} {total_before:>14,} {total_after:>13,} {total_after / total_before:>6.1%}")
    print(f"\nTexts saved to {PROCESSED_DIR.relative_to(DATA_DIR.parent)}/ (token numbers are estimates: ~4 characters per token).")
    _print_answer_coverage()


def _print_answer_coverage() -> None:
    """Check how many ground-truth values are present in the shortened texts."""
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT f.ticker, f.fiscal_year, g.metric, g.value, p.text_path
            FROM ground_truth g
            JOIN filings f USING (accession_number)
            JOIN preprocessing p USING (accession_number)
            WHERE g.value IS NOT NULL
            ORDER BY f.ticker, f.fiscal_year DESC
            """
        ).fetchall()
    texts: dict[str, str] = {}
    missing = []
    for row in rows:
        text = texts.setdefault(row["text_path"], (DATA_DIR.parent / row["text_path"]).read_text(encoding="utf-8"))
        if not answer_in_text(row["value"], row["metric"], text):
            missing.append(f"{row['ticker']} {row['fiscal_year']} {row['metric']}")
    print(f"Answer coverage: {len(rows) - len(missing)} of {len(rows)} ground-truth values appear in the extracted text.")
    for item in missing:
        print(f"  not found: {item}")


if __name__ == "__main__":
    main()
