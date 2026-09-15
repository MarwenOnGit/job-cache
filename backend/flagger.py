"""Free heuristic sponsorship flagging. Hints only — never used to filter jobs out."""
from __future__ import annotations

# Checked first: explicit statements that no sponsorship is offered.
_NO_SPONSOR = [
    "no visa sponsorship", "not able to sponsor", "unable to sponsor", "cannot sponsor",
    "can not sponsor", "do not sponsor", "does not sponsor", "no sponsorship",
    "without sponsorship", "not provide sponsorship", "not offer sponsorship",
    "must have the right to work", "must already have the right to work",
    "must be authorized to work", "must be authorised to work",
    "must have existing work authorization", "must have existing right to work",
    "no relocation", "not offer relocation", "eligible to work in",
]

# Checked second: positive sponsorship / relocation signals.
_LIKELY_SPONSOR = [
    "visa sponsorship", "we sponsor", "will sponsor", "can sponsor", "sponsorship available",
    "sponsor visas", "visa support", "visa assistance", "work permit", "relocation package",
    "relocation assistance", "relocation support", "relocation bonus", "we offer relocation",
    "help you relocate", "immigration support", "sponsor your visa",
]


def classify_sponsorship(description: str) -> str:
    text = (description or "").lower()
    if not text:
        return "silent"
    if any(p in text for p in _NO_SPONSOR):
        return "no_sponsorship"
    if any(p in text for p in _LIKELY_SPONSOR):
        return "likely_sponsors"
    return "silent"
