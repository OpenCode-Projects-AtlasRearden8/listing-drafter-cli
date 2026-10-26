"""Save drafts as local Markdown, named beside your photos-folder naming."""

from __future__ import annotations

import datetime
import re
import unicodedata
from pathlib import Path

PHOTOS_PREFIXES = ("photos", "photo", "pics", "pictures", "img", "images")
MAX_TITLE_LEN = 80


def slugify(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "draft"


def photos_date(name: str) -> str:
    match = re.search(r"\d{4}-\d{2}-\d{2}", name)
    if match:
        return match.group(0)
    match = re.search(r"(\d{4})(\d{2})(\d{2})", name)
    if match:
        return "-".join(match.groups())
    return datetime.date.today().isoformat()


def detect_photos_dir(root: Path):
    """Newest folder that looks like a photos folder (photos..., pics..., etc.)."""
    if not root.exists():
        return None
    candidates = [
        p
        for p in root.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name.lower().startswith(PHOTOS_PREFIXES)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p.stat().st_mtime, p.name))


def draft_path(root: Path, photos_dir=None, brand=None, item=None, date=None):
    """Draft lands beside the photos folder, using its name.

    photos-2026-10-26-carhartt-coat/  →  photos-2026-10-26-carhartt-coat-draft.md
    """
    root = Path(root)
    if photos_dir is not None:
        photos_dir = Path(photos_dir)
        stem = photos_dir.name if photos_dir.name else "photos"
        stem = re.sub(r"[-. ]+$", "", stem)
        return root / (stem + "-draft.md")
    name_fallback = "%s-%s-%s" % (
        photos_date(date or datetime.date.today().isoformat()),
        slugify(brand or ""),
        slugify(item or "draft"),
    )
    return root / "drafts" / (name_fallback + ".md")


def save_draft(path, title, reasoning, description, meta=None):
    """Write the draft next to the photos folder. Returns the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    meta = meta or {}
    lines = []
    lines.append("---")
    lines.append("date: %s" % meta.get("date", datetime.date.today().isoformat()))
    for key in sorted(k for k in meta if k != "date" and k != "notes"):
        value = meta[key]
        if isinstance(value, (str, int, float)):
            lines.append("%s: %s" % (key, value))
    lines.append("title_length: %s" % len(title or ""))
    lines.append("---")
    lines.append("")
    lines.append("# Draft Listing")
    lines.append("")
    lines.append("## Title")
    lines.append("")
    lines.append(title or "")
    lines.append("")
    if reasoning:
        lines.append("### Searchable-word reasoning")
        lines.append("")
        for r in reasoning:
            mark = "cut" if r.get("dropped") else "kept"
            lines.append("- %s (`%s`): %s" % (mark, r["word"], r["why"]))
        lines.append("")
    lines.append("## Description")
    lines.append("")
    lines.append(description or "")
    if meta.get("notes"):
        lines.append("")
        lines.append("### Reviewer notes")
        for note in meta["notes"]:
            lines.append("- " + note)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
