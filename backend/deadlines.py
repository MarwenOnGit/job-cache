"""Deadline helpers for study opportunities: find a stated deadline in free text,
and roll a yearly deadline (month/day) forward to its next occurrence."""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

_MONTH_NAMES = {
    1: ["january", "jan", "janvier"], 2: ["february", "feb", "février", "fevrier"],
    3: ["march", "mar", "mars"], 4: ["april", "apr", "avril"], 5: ["may", "mai"],
    6: ["june", "jun", "juin"], 7: ["july", "jul", "juillet"],
    8: ["august", "aug", "août", "aout"], 9: ["september", "sept", "sep", "septembre"],
    10: ["october", "oct", "octobre"], 11: ["november", "nov", "novembre"],
    12: ["december", "dec", "décembre", "decembre"],
}
MONTHS = {name: num for num, names in _MONTH_NAMES.items() for name in names}
_M = "|".join(sorted(MONTHS, key=len, reverse=True))
_DAY_FIRST = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th|er)?\s+({_M})\.?,?\s+(20\d\d)\b", re.I)
_MONTH_FIRST = re.compile(rf"\b({_M})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(20\d\d)\b", re.I)
_CUE = re.compile(r"deadline|closing date|apply before|apply by|applications? close|"
                  r"date limite|avant le", re.I)


def _safe(y: int, m: int, d: int) -> Optional[date]:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def find_deadline(text: str) -> Optional[str]:
    """ISO date of the first date written shortly after a deadline cue, else None.
    Looking only right after the cue avoids picking up start or publish dates."""
    for cue in _CUE.finditer(text or ""):
        window = text[cue.end(): cue.end() + 120]
        hits = []
        for m in _DAY_FIRST.finditer(window):
            d = _safe(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))
            if d:
                hits.append((m.start(), d))
        for m in _MONTH_FIRST.finditer(window):
            d = _safe(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2)))
            if d:
                hits.append((m.start(), d))
        if hits:
            return min(hits)[1].isoformat()
    return None


def upcoming(month: int, day: int, today: date) -> str:
    """Next date (today or later) falling on month/day; clamps e.g. Feb 30 to Feb 28."""
    for year in (today.year, today.year + 1):
        d = _safe(year, month, day) or _safe(year, month, 28)
        if d and d >= today:
            return d.isoformat()
    return today.isoformat()
