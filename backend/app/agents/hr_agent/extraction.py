# Lightweight, dependency-free heuristics for pulling structured fields out
# of free-text HR requests (employee name/role, leave type, dates).
#
# These are intentionally simple regex/keyword heuristics, not a full NLU
# pipeline -- they trade recall for zero extra dependencies and predictable
# behavior. Future integration point: replace with LLM structured output
# (tool/function calling) or an explicit form once available; see the call
# sites in nodes.py for where to swap this in.
import re
from typing import List, Optional

# Stop the lazy role/name capture before trailing context words rather than
# swallowing the rest of the sentence.
_TRAILING_STOP = r"(?:[.,;]|\s+(?:starting|on|from|next|beginning|effective|who|and)\b|$)"

# Marker words use the scoped `(?i:...)` inline flag so they match
# regardless of sentence-start capitalization ("New hire, ..." as well as
# "new hire, ..."), while the captured name itself stays case-sensitive --
# requiring a capital letter is what keeps this from matching random nouns.
#
# Each name-word ends with `\b` rather than being left to stop wherever
# `[a-zA-Z'-]+` runs out. Without it, a name containing a character the
# (deliberately ASCII-only) class doesn't cover -- e.g. an accented letter
# like "Zoe" with an umlaut, or "Jose" with an accent -- would silently
# truncate mid-word ("Zoe"+umlaut -> "Zo") instead of failing to match. `\b`
# forces the match to end on an actual word boundary (whitespace/punctuation/
# end of string); Python's `\w` -- and therefore `\b` -- is Unicode-aware by
# default, so a position between two letters (ASCII or not) is never a
# boundary, and the match fails cleanly, falling back to "Unknown" the same
# way an unmatched name already does, instead of returning a truncated
# fragment.
_NAME_PATTERNS = [
    re.compile(r"(?i:name is)\s+([A-Z][a-zA-Z'-]+\b(?:\s+[A-Z][a-zA-Z'-]+\b){0,2})"),
    re.compile(r"(?i:new hire)[,:]?\s+([A-Z][a-zA-Z'-]+\b(?:\s+[A-Z][a-zA-Z'-]+\b){0,2})"),
    re.compile(r"(?i:employee)[,:]?\s+([A-Z][a-zA-Z'-]+\b(?:\s+[A-Z][a-zA-Z'-]+\b){0,2})"),
    re.compile(
        r"(?i:for)\s+([A-Z][a-zA-Z'-]+\b(?:\s+[A-Z][a-zA-Z'-]+\b){0,2}),?\s+(?i:who|starting|joining)"
    ),
    # Fallback: "onboard(ing) <Name>" -- e.g. "Please onboard John Doe as a
    # Backend Engineer". Appended last (lowest priority) since it's the most
    # generic marker and the other, more specific patterns above should win
    # when they match.
    re.compile(r"(?i:onboard(?:ing)?)\s+([A-Z][a-zA-Z'-]+\b(?:\s+[A-Z][a-zA-Z'-]+\b){0,2})"),
]

_ROLE_PATTERNS = [
    re.compile(r"\bas an? ([A-Za-z][A-Za-z\s/-]{1,40}?)" + _TRAILING_STOP, re.IGNORECASE),
    re.compile(r"\brole(?: of)?[:\s]+([A-Za-z][A-Za-z\s/-]{1,40}?)" + _TRAILING_STOP, re.IGNORECASE),
    re.compile(r"\bposition[:\s]+([A-Za-z][A-Za-z\s/-]{1,40}?)" + _TRAILING_STOP, re.IGNORECASE),
    # Fallback: "as (our/the) (new) <Role>" without the "a/an" article --
    # e.g. "joining as Software Engineer", "as our new Sales Director". The
    # captured role itself stays capitalized-only (unlike the patterns
    # above) so this broader, article-less match doesn't swallow ordinary
    # phrases like "as of next week".
    re.compile(
        r"(?i:as)\s+(?:(?i:our|the)\s+)?(?:(?i:new)\s+)?([A-Z][A-Za-z\s/-]{1,40}?)" + _TRAILING_STOP
    ),
]

_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_ABSOLUTE_DATE_PATTERN = re.compile(
    r"\b("
    r"\d{4}-\d{2}-\d{2}"  # 2026-08-01
    r"|\d{1,2}/\d{1,2}/\d{2,4}"  # 08/01/2026
    rf"|{_MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?"  # Aug 1(st)(, 2026)
    rf"|\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH}(?:,?\s+\d{{4}})?"  # 1st Aug(, 2026)
    r")\b",
    re.IGNORECASE,
)
_RELATIVE_DATE_PATTERN = re.compile(
    r"\b(today|tomorrow|day after tomorrow|next week|next month|"
    r"next (?:mon|tues?|wednes|thurs?|fri|satur|sun)day)\b",
    re.IGNORECASE,
)

# Fallback markers for a free-text leave reason -- e.g. "because I have a
# family emergency", "due to a medical procedure". Reuses `_TRAILING_STOP`
# (rather than a second stop pattern) so the reason capture stops at the
# same connector words/punctuation as the name/role patterns above (e.g.
# before a trailing "on 2026-08-01" or "starting Monday").
# More specific phrases ("because of") are listed before their substrings
# ("because") so the more precise match wins.
_LEAVE_REASON_PATTERNS = [
    re.compile(r"(?i:because of)\s+(.+?)" + _TRAILING_STOP),
    re.compile(r"(?i:because)\s+(.+?)" + _TRAILING_STOP),
    re.compile(r"(?i:due to)\s+(.+?)" + _TRAILING_STOP),
    re.compile(r"(?i:reason(?: is)?:?)\s+(.+?)" + _TRAILING_STOP),
]

# keyword -> canonical label. Checked in order, first match wins.
_LEAVE_TYPE_KEYWORDS = [
    ("sick", "sick leave"),
    ("maternity", "maternity leave"),
    ("paternity", "paternity leave"),
    ("parental", "parental leave"),
    ("bereavement", "bereavement leave"),
    ("unpaid", "unpaid leave"),
    ("annual", "annual leave"),
    ("vacation", "vacation"),
    ("pto", "paid time off"),
    ("personal", "personal leave"),
]


def extract_name(text: str) -> Optional[str]:
    """Best-effort extraction of a person's name from free text (e.g.
    "new hire, Jane Smith," or "name is Jane Smith"). Returns None if no
    pattern matches -- callers should fall back to a placeholder."""
    for pattern in _NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def extract_role(text: str) -> Optional[str]:
    """Best-effort extraction of a job title/role (e.g. "as a Product
    Manager", "role: Backend Engineer"). Returns None if no pattern
    matches."""
    for pattern in _ROLE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip().rstrip(".,")
    return None


def extract_dates(text: str, max_dates: int = 2) -> List[str]:
    """Return up to `max_dates` date-like substrings found in `text`, in the
    order they appear. Tries absolute dates first (e.g. "Aug 1, 2026",
    "2026-08-01"); if none are found, falls back to relative phrases (e.g.
    "next week", "tomorrow") so callers still get something more useful
    than a placeholder when the user writes casually.

    Purely pattern-based: it does not validate that a match is a real
    calendar date, and does not resolve relative phrases to actual dates.
    """
    matches = [m.group(0) for m in _ABSOLUTE_DATE_PATTERN.finditer(text)]
    if not matches:
        matches = [m.group(0) for m in _RELATIVE_DATE_PATTERN.finditer(text)]
    return matches[:max_dates]


def extract_leave_reason(text: str) -> Optional[str]:
    """Best-effort extraction of the free-text reason behind a leave request
    (e.g. "because I have a family emergency", "due to a medical
    procedure"). Returns None if no marker phrase matches -- callers should
    fall back to a placeholder."""
    for pattern in _LEAVE_REASON_PATTERNS:
        match = pattern.search(text)
        if match:
            reason = match.group(1).strip().rstrip(".,;")
            if reason:
                return reason
    return None


def extract_leave_type(text: str) -> Optional[str]:
    """Match the request against a small set of common leave-type keywords.
    Returns None if nothing matches."""
    lowered = text.lower()
    for keyword, label in _LEAVE_TYPE_KEYWORDS:
        if keyword in lowered:
            return label
    return None
