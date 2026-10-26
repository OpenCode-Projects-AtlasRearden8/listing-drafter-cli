"""Draft title and description from item notes. Truthful, never salesy.

The title planner keeps only searchable words and explains every word it
kept or dropped, so the listing survives editor-truncation with still
honest words.
"""

from __future__ import annotations

import re

FILLER = {
    "a", "an", "the", "of", "in", "at", "for", "to", "with", "my", "your",
    "item", "thing", "stuff", "used", "great", "nice", "awesome", "fun",
    "super", "really", "very", "some", "selling", "sale", "model", "style",
    "size", "wording",
}

HYPE_PHRASES = [
    "amazing", "perfect", "stunning", "gorgeous", "flawless", "incredible",
    "unbelievable", "one of a kind", "rare find", "must have",
    "must-have", "don't miss", "do not miss", "steal of a deal",
    "unicorn", "pristine",
]

COLORS = {
    "black", "white", "red", "blue", "green", "yellow", "orange", "purple",
    "pink", "brown", "gray", "grey", "tan", "navy", "olive", "beige",
    "cream", "gold", "silver", "maroon", "teal", "rose gold", "charcoal",
}

MATERIALS = {
    "wool", "cotton", "leather", "linen", "silk", "denim", "cashmere",
    "polyester", "canvas", "corduroy", "flannel", "suede", "nylon",
    "stainless", "oak", "walnut", "ceramic", "porcelain", "cast iron",
}

SIZE_HINT_RE = re.compile(r"\bsize\s*[:=]?\s*(?:([0-9]{1,3})|([Xx]{0,3}[SLM]))\b")


def _clean_words(text: str):
    raw = re.findall(r"[A-Za-z0-9'\-]+", text or "")
    return [w for w in raw]


def _size_from_notes(measurements, item=""):
    joined = "; ".join(list(measurements or []) + [item or ""])
    m = SIZE_HINT_RE.search(joined)
    if m:
        token = m.group(1) or m.group(2)
        return token.upper() if token.isalpha() else token
    return None


def _color_from_notes(*texts):
    joined = " ".join(t for t in texts if t).lower()
    for c in sorted(COLORS, key=len, reverse=True):
        if re.search(r"\b" + re.escape(c) + r"\b", joined):
            return c if c != "grey" else "gray"
    return None


def _material_from_notes(*texts):
    joined = " ".join(t for t in texts if t).lower()
    for mat in sorted(MATERIALS, key=len, reverse=True):
        if re.search(r"\b" + re.escape(mat) + r"\b", joined):
            return mat
    return None


READ_ORDER = ["brand", "color", "item", "detail", "size", "material", "condition"]
DROP_PRIORITY = {"color": 0, "size": 1, "material": 2, "detail": 3}


def plan_title(brand, item, details, measurements, grade, max_len=80):
    """Return (title, reasoning) where reasoning explains every word choice.

    A condition word only earns its spot when it keeps the listing honest
    (for-parts) or when the near-new grade is real selling info.
    """
    size = _size_from_notes(measurements, item)
    color = _color_from_notes(item, details, brand)
    material = _material_from_notes(item, details)
    core_words = [w for w in _clean_words(item or "") if w.lower() not in FILLER]
    if size:
        core_words = [w for w in core_words if w.lower() != size.lower()]
    if color:
        core_words = [w for w in core_words if w.lower() != color.lower()]
    lucky = [
        w for w in _clean_words(details or "")
        if w.lower() not in FILLER and len(w) >= 3
    ]

    pieces = []
    if brand:
        pieces.append({
            "word": brand.strip().title(), "aspect": "brand",
            "why": "brand names are what buyers type or filter first; easily searchable",
        })
    if color:
        pieces.append({
            "word": color.title(), "aspect": "color",
            "why": "color is a common filter/search word",
        })
    if core_words:
        pieces.append({
            "word": " ".join(core_words), "aspect": "item",
            "why": "says plainly what the thing is; the main words buyers search",
        })
    for extra in lucky[:3]:
        low = " ".join(core_words).lower() + " " + (brand or "").lower()
        if extra.lower() not in low:
            pieces.append({
                "word": extra, "aspect": "detail",
                "why": "extra searchable keyword from your notes (style or model detail)",
            })
    if size:
        pieces.append({
            "word": "Size " + size, "aspect": "size",
            "why": "size cuts returns, matches buyer filters and inbox searches",
        })
    if material:
        pieces.append({
            "word": material.title(), "aspect": "material",
            "why": "material is a searchable quality signal",
        })
    if grade.endswith("For Parts"):
        pieces.append({
            "word": "For Parts", "aspect": "condition",
            "why": "keeps the title honest and finds project buyers; they search these words",
        })
    elif grade in ("New with Tags", "New without Tags", "Like New"):
        word = "New With Tags" if grade == "New with Tags" else grade
        pieces.append({
            "word": word, "aspect": "condition",
            "why": "near-new condition wins real buyers; worth a title word when true",
        })

    droppable = sorted(
        [p for p in pieces if p["aspect"] in DROP_PRIORITY],
        key=lambda p: DROP_PRIORITY[p["aspect"]],
    )
    title_terms = [p["word"] for p in sorted(pieces, key=lambda p: READ_ORDER.index(p["aspect"]))]

    def too_long():
        terms = title_terms[:]
        return sum(len(t) for t in terms) + max(0, len(terms) - 1) > max_len

    while too_long() and title_terms:
        if droppable:
            victim = droppable.pop(0)
            title_terms = [t for t in title_terms if t != victim["word"]]
        else:
            # core words only; the description still carries the full note
            title_terms.pop()

    title = " ".join(title_terms)
    flair = "; cut only to fit the 80-character title limit, not for meaning"
    reasoning_all = []
    placed = set()
    for aspect in READ_ORDER:
        for p in pieces:
            if p["aspect"] != aspect or p["word"] in placed:
                continue
            placed.add(p["word"])
            if p["word"] in title_terms and p["word"].lower() in title.lower():
                reasoning_all.append({"word": p["word"], "aspect": p["aspect"], "why": p["why"]})
            else:
                reasoning_all.append({
                    "word": p["word"], "aspect": p["aspect"], "dropped": True,
                    "why": p["why"] + flair,
                })
    return title, reasoning_all


HYPE_NOTE = "plain-honest: removed hype phrase"


def strip_hype(text):
    """Remove salesy phrases; return (clean_text, removed list)."""
    low = (" " + (text or "") + " ")
    removed = []
    for phrase in HYPE_PHRASES:
        p = phrase.strip()
        if p and re.search(r"\b" + re.escape(p) + r"\b", low):
            removed.append(p)
            low = re.sub(r"\b" + re.escape(p) + r"\b", " ", low)
    clean = re.sub(r"\s{2,}", " ", low).strip()
    return clean, [r for r in removed if r]


def build_description(brand, item, measurements, condition_notes, flaws, grade, grade_why):
    lines = []
    what = " ".join(part for part in ((brand or "").strip().title(), (item or "").strip()) if part)
    lines.append(what if what else "Listing Draft")

    if measurements:
        lines.append("")
        lines.append("Measurements:")
        for m in measurements:
            m = m.strip()
            if m:
                lines.append("- " + m)

    hype_seen = []
    if condition_notes or grade_why:
        lines.append("")
        lines.append("Condition: " + grade)
        for note in (condition_notes or "").split(";"):
            cleaned_note, note_hype = strip_hype(note)
            hype_seen.extend(note_hype)
            cleaned_note = cleaned_note.strip()
            if cleaned_note:
                lines.append("- " + cleaned_note)

    flaws_section = []
    for f in flaws or []:
        cleaned, removed = strip_hype(f)
        hype_seen.extend(removed)
        cleaned = cleaned.strip()
        if cleaned:
            flaws_section.append(cleaned)
        else:
            # a flaw that was 100% hype wording still needs to be disclosed,
            # so fall back to a plain-language placeholder
            flaws_section.append("(flaw needs rewording — original note was all hype wording: %r)" % f)

    lines.append("")
    lines.append("Flaws, honestly all of them:")
    if flaws_section:
        for f in flaws_section:
            lines.append("- " + f)
    else:
        lines.append("- none noted; double-check the item before listing, you know it best")

    lines.append("")
    lines.append("Questions welcome. Happy to send extra photos or specific measurements.")

    notes = []
    if hype_seen:
        notes.append(HYPE_NOTE + "s: " + ", ".join(sorted(set(hype_seen))) + ".")
    return "\n".join(lines), notes
