"""Condition grading from plain-English notes, plus a sanity check.

The grader never upgrades an item. The worst word in the notes wins,
so a "like new" claim with a "torn" in it will not pass as like new.
"""

from __future__ import annotations

import re

GRADES = [
    "New with Tags",
    "New without Tags",
    "Like New",
    "Excellent",
    "Very Good",
    "Good",
    "Used/For Parts",
]

# severity: 3 = dead or damaged, 2 = visible damage, 1 = normal wear, 0 = near-new claims
SEVERE_TERMS = [
    "doesn't work",
    "does not work",
    "not working",
    "wont work",
    "doesn't turn on",
    "doesn't power on",
    "untested",
    "nonfunctional",
    "non-functional",
    "for parts",
    "broken",
    "dead",
    "whole for parts",
    "junk",
    "smashed",
]

# unsigned negations, so "no stains" is not treated as a stain
NEGATION_RE = re.compile(
    r"\b(no|zero|without|never|isn't|is not|not)\s+(?:\w+\s+)?"
    r"(stains?|holes?|rips?|tears?|cracks?|chips?|wear|worn|scuffs?|damage[sd]?|pilling|fades?|fading)\b",
)

DAMAGE_TERMS = [
    "stain",
    "hole",
    "rip",
    "torn",
    "tear",
    "crack",
    "chipped",
    "missing",
    "shattered",
    "pill",
    "pilling",
    "peeling",
    "fraying",
    "sun damage",
    "water damage",
]

WEAR_TERMS = [
    "wear",
    "worn",
    "scuff",
    "fading",
    "faded",
    "faint",
    "light ",
    "minor",
    "slight",
    "smell",
    "lint",
    "dust",
    "shrunk",
    "shrink",
]

NEAR_NEW_TERMS = ["new with tags", "nwt", "brand new", "never used", "never worn", "sealed", "pristine", "unused"]

HINT_WORDS = [
    (["new with tags", "nwt"], "New with Tags"),
    (["brand new", "new without tags"], "New without Tags"),
    (["like new", "near new"], "Like New"),
    (["excellent"], "Excellent"),
    (["very good"], "Very Good"),
    (["good"], "Good"),
    (["for parts", "not working", "as-is", "as is"], "Used/For Parts"),
]


def _strip_negations(text: str) -> str:
    return NEGATION_RE.sub(" ", text)


def grade_from_notes(condition_notes: str, flaws=None) -> dict:
    """Grade an item honestly from its condition notes and flaw list."""
    condition_notes = (condition_notes or "").strip()
    flaws = [f.strip() for f in (flaws or []) if f and f.strip()]
    flaw_text = " ; ".join(flaws)
    combined = " ; ".join(part for part in (condition_notes, flaw_text) if part)
    everything = combined.lower()
    cleaned = _strip_negations(everything)

    caps = []          # why the grade was capped
    saw = {"3": [], "2": [], "1": [], "0": []}

    for term in SEVERE_TERMS:
        if term in cleaned:
            saw["3"].append(term)
    for term in DAMAGE_TERMS:
        if re.search(r"\b" + re.escape(term), cleaned):
            saw["2"].append(term)
    for term in WEAR_TERMS:
        if term in cleaned:
            saw["1"].append(term)
    for term in NEAR_NEW_TERMS:
        if term in cleaned:
            saw["0"].append(term)

    warnings = []

    if saw["3"]:
        grade = "Used/For Parts"
        caps.append(
            "Your notes mention serious problems: "
            + ", ".join(sorted(set(saw["3"])))
            + ". A listing aimed at buyers expecting a working item would be dishonest."
        )
    elif saw["2"]:
        grade = "Good"
        caps.append(
            "Your notes list visible damage (" + ", ".join(sorted(set(saw["2"]))) + "), so the top grades are off the table."
        )
    elif saw["1"]:
        grade = "Very Good"
        caps.append(
            "Your notes mention light wear (" + ", ".join(sorted(set(saw["1"]))) + "), so keep the grade at Very Good or lower."
        )
    elif saw["0"]:
        grade = "New without Tags"
        caps.append("Notes say the item is unused; no wear words found.")
    else:
        grade = "Very Good"
        caps.append("Notes describe only ordinary condition talk; defaulted to Very Good. Adjust if that feels wrong.")

    # cross-check: does the notes' own language disagree with our grade?
    hinted = _hinted_grade(everything)
    if hinted:
        hint_index = GRADES.index(hinted)
        if hint_index < GRADES.index(grade):
            warnings.append(
                'Notes sound like "%s", but at least one flaw or wear word caps the item at "%s". '
                "List the lower grade and let the note speak for you." % (hinted, grade)
            )

    return {"grade": grade, "why": caps, "warnings": warnings, "matched": {k: sorted(set(v)) for k, v in saw.items() if v}}


def _hinted_grade(text: str):
    low = text
    for keys, grade in HINT_WORDS:
        for key in keys:
            if key in low:
                return grade
    return None


def check_title_grade_claim(title: str, grade: str):
    """Warn if a title claims a condition the grader would not allow."""
    title_low = title.lower()
    out = []
    for optimistic in ("like new", "excellent condition", "perfect condition", "brand new", "new with tags"):
        if optimistic in title_low:
            allowed = grade in ("New with Tags", "New without Tags", "Like New")
            if not allowed:
                out.append('Title says "%s" but graded "%s"' % (optimistic, grade))
    return out
