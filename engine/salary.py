"""Pay extraction from posting text for boards that publish no structured pay.

The ATS readers in ``engine/sources`` read structured fields when a board offers
them and leave ``min_amount``/``max_amount`` at zero when it does not. This
module fills that gap by reading the most credible pay figure out of the
description. Structured pay always wins; callers only reach for this fallback.
"""

from __future__ import annotations

import re
from typing import Dict, Iterator, List, Optional, Tuple

# Annual pay is the engine's filter unit, so hourly and monthly figures convert.
_PERIOD_FACTORS = {"year": 1.0, "month": 12.0, "week": 52.0, "day": 260.0, "hour": 2080.0}

# Plausibility windows keep stock grants, stipends, and round-number noise out.
_BOUNDS = {
    "year": (1_000.0, 10_000_000.0),
    "hour": (10.0, 1_000.0),
    "month": (500.0, 100_000.0),
}

_ANNUAL_MIN = 10_000.0

_CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP"}
_CURRENCY_CODES = {"usd": "USD", "eur": "EUR", "gbp": "GBP", "cad": "CAD", "aud": "AUD"}

_NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?"
_SYM = r"[$€£]"
_CODE = r"USD|EUR|GBP|CAD|AUD"

_RANGE_RE = re.compile(
    rf"(?:(?P<precode>{_CODE})\s*)?"
    rf"(?P<sym1>{_SYM})?\s*(?P<num1>(?:{_NUM}))\s*(?P<k1>[kK])?"
    rf"\s*(?:-|–|—|to)\s*"
    rf"(?P<sym2>{_SYM})?\s*(?P<num2>(?:{_NUM}))\s*(?P<k2>[kK])?"
    rf"(?:\s*(?P<code>{_CODE}))?",
    re.IGNORECASE,
)

_SINGLE_RE = re.compile(
    rf"(?:(?P<sym>{_SYM})|(?:(?P<precode>{_CODE})\s*))"
    rf"(?P<num>(?:{_NUM}))\s*(?P<k>[kK])?(?:\s*(?P<code>{_CODE}))?",
    re.IGNORECASE,
)

_TRAILING_CODE_RE = re.compile(
    rf"(?P<num>(?:{_NUM}))\s*(?P<k>[kK])?\s*(?P<code>{_CODE})",
    re.IGNORECASE,
)

_HOUR_RE = re.compile(r"\bper\s+hour\b|\ban\s+hour\b|/\s*(?:hr|hour)\b|\bhourly\b")
_MONTH_RE = re.compile(r"\bper\s+month\b|/\s*(?:mo|month)\b|\bmonthly\b")
_YEAR_RE = re.compile(r"\bper\s+year\b|\ba\s+year\b|\bannually\b|\bannual\b|/\s*(?:yr|year)\b|\bper\s+annum\b")

# Nearby wording that marks a number as something other than base pay.
_PENALTY_TERMS = (
    "bonus",
    "sign-on",
    "signing",
    "equity",
    "stock",
    "stipend",
    "allowance",
    "reimburs",
    "tuition",
    "funding",
    "raised",
    "revenue",
    "budget",
)

_PAY_KEYWORDS = (
    "salary",
    "compensation",
    "comp",
    "pay range",
    "base pay",
    "annual",
    "annually",
    "ote",
    "on-target",
    "hourly",
    "monthly",
    "rate",
    "per year",
    "per hour",
    "per month",
)

# A figure followed by these words is the bonus or equity grant, not base pay.
# A connective such as "plus equity" or "includes bonus" keeps the figure as pay.
_CONNECTIVES = r"plus|and|with|including|includes|as well as|\+"
_POST_PENALTY_RE = re.compile(
    rf"^\s*(?:(?P<connect>{_CONNECTIVES})\s+)?(?:{'|'.join(_PENALTY_TERMS)})\b"
)

_WS_RE = re.compile(r"\s+")


def _to_amount(number: str, thousands: Optional[str]) -> float:
    value = float(number.replace(",", ""))
    return value * 1000.0 if thousands else value


def _currency(symbol: Optional[str], code: Optional[str]) -> str:
    if code:
        return _CURRENCY_CODES.get(code.lower(), "USD")
    return _CURRENCY_SYMBOLS.get(symbol or "", "USD")


def _sentence(text: str, start: int, end: int) -> str:
    """Return the sentence that contains ``text[start:end]``."""
    left = max(text.rfind(". ", 0, start), text.rfind("\n", 0, start), text.rfind("; ", 0, start))
    right_marks = [pos for pos in (text.find(". ", end), text.find("\n", end), text.find("; ", end)) if pos != -1]
    right = min(right_marks) if right_marks else len(text)
    return text[left + 1 : right].lower()


def _is_rejected(text: str, start: int, end: int) -> bool:
    before = text[max(0, start - 35) : start].lower()
    if any(term in before for term in _PENALTY_TERMS):
        return True
    match = _POST_PENALTY_RE.match(text[end : end + 18].lower())
    return bool(match and not match.group("connect"))


def _keyword_score(sentence: str) -> int:
    return sum(1 for keyword in _PAY_KEYWORDS if keyword in sentence)


def _period(text: str, start: int, end: int, max_amount: float) -> Optional[str]:
    context = f"{text[max(0, start - 45) : start]} {text[end : end + 30]}".lower()
    if _HOUR_RE.search(context):
        return "hour"
    if _MONTH_RE.search(context):
        return "month"
    if _YEAR_RE.search(context):
        return "year"
    if max_amount >= _ANNUAL_MIN:
        return "year"
    return None


def _bounds_fit(low: float, high: float, period: str) -> bool:
    floor, ceiling = _BOUNDS[period]
    return floor <= high <= ceiling and (low == 0 or floor <= low <= ceiling)


def _candidates(text: str) -> Iterator[Dict]:
    spans: List[Tuple[int, int]] = []
    for match in _RANGE_RE.finditer(text):
        symbol = match.group("sym1") or match.group("sym2")
        code = match.group("code") or match.group("precode")
        thousands_1 = match.group("k1")
        thousands_2 = match.group("k2")
        low = _to_amount(match.group("num1"), thousands_1)
        high = _to_amount(match.group("num2"), thousands_2)
        if low > high:
            low, high = high, low
        spans.append((match.start(), match.end()))
        yield {
            "start": match.start(),
            "end": match.end(),
            "min_amount": low,
            "max_amount": high,
            "currency": _currency(symbol, code),
            "has_currency": bool(symbol or code),
        }

    def inside_range(position: int) -> bool:
        return any(start <= position < end for start, end in spans)

    for match in _SINGLE_RE.finditer(text):
        if inside_range(match.start()):
            continue
        amount = _to_amount(match.group("num"), match.group("k"))
        yield {
            "start": match.start(),
            "end": match.end(),
            "min_amount": amount,
            "max_amount": amount,
            "currency": _currency(match.group("sym"), match.group("code") or match.group("precode")),
            "has_currency": True,
        }

    for match in _TRAILING_CODE_RE.finditer(text):
        if inside_range(match.start()):
            continue
        amount = _to_amount(match.group("num"), match.group("k"))
        yield {
            "start": match.start(),
            "end": match.end(),
            "min_amount": amount,
            "max_amount": amount,
            "currency": _currency(None, match.group("code")),
            "has_currency": True,
        }


def extract_pay(text: str) -> Optional[dict]:
    """Return ``{min_amount, max_amount, currency, period}`` from posting text.

    Returns ``None`` when the text carries no credible pay figure. ``period`` is
    ``year``, ``hour``, or ``month`` so the card can keep the unit the posting
    used. Callers convert to annual pay before comparing against a floor.
    """
    if not text:
        return None
    text = _WS_RE.sub(" ", str(text))
    best: Optional[dict] = None
    best_score = -1

    for candidate in _candidates(text):
        low, high = candidate["min_amount"], candidate["max_amount"]
        if high <= 0 or _is_rejected(text, candidate["start"], candidate["end"]):
            continue
        period = _period(text, candidate["start"], candidate["end"], high)
        if period is None or not _bounds_fit(low, high, period):
            continue
        score = _keyword_score(_sentence(text, candidate["start"], candidate["end"]))
        if not candidate["has_currency"] and score == 0:
            continue
        if score > best_score:
            best = {
                "min_amount": low,
                "max_amount": high,
                "currency": candidate["currency"],
                "period": period,
            }
            best_score = score

    return best


def annual_max_amount(amount: float, period: str = "year") -> float:
    """Convert a maximum pay figure into annual pay for floor comparisons."""
    factor = _PERIOD_FACTORS.get(str(period or "year").lower(), 1.0)
    return float(amount or 0) * factor
