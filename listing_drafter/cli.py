"""Command line entry point.

Commands:
  draft    turn item notes into a markdown draft (title + reasoning + description + grade)
  rewrite  optional polish pass through an OpenAI-compatible endpoint
  grade    condition-grader sanity check only
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

from listing_drafter import __version__
from listing_drafter import condition as cond_mod
from listing_drafter import draft as draft_mod
from listing_drafter import rewrite as rw
from listing_drafter import store
from listing_drafter.config import load_config

SCHEMA_HINT = 'Reply with JSON only: {"title": "...", "description": "..."}.'


def _split(value):
    if not value:
        return []
    if isinstance(value, str):
        value = [value]
    parts = [p.strip() for part in value for p in str(part).split("|")]
    return [p for p in parts if p]


def _prompt(label, default=""):
    try:
        answer = input(("%s [%s]: " % (label, default)) if default else (label + ": "))
    except EOFError as exc:
        raise SystemExit("\nNeed input for %r but nothing was provided." % label) from exc
    return answer.strip() or default


def _collect_notes(args):
    """Prompt for missing required notes when running in a real terminal."""
    if not (sys.stdin.isatty() and args.command == "draft"):
        return args
    if not args.item:
        args.item = _prompt("What is it? (plain words: 'men's wool pea coat')")
    if not args.condition:
        args.condition = _prompt("Condition notes (e.g. 'worn a few times, no rips')")
    if not args.flaws:
        args.flaws = _prompt("Flaws, pipe-separated (blank is fine if flawless)")
    if not args.measurements:
        args.measurements = _prompt("Measurements, pipe-separated (blank is fine)")
    return args


def cmd_draft(args):
    args.brand = (args.brand or "").strip()
    args.item = (args.item or "").strip()
    args.condition = (args.condition or "").strip()
    args.details = (args.details or "").strip()
    if not args.item:
        raise SystemExit("Missing --item. Run interactively in a terminal for prompts, or pass flags.")
    if not args.condition and not flaws_all_blank(args):
        pass  # condition is allowed to be empty only if notes truly say nothing

    flaws = _split(args.flaws)
    measurements = _split(args.measurements)
    condition = args.condition or "no condition notes given"

    graded = cond_mod.grade_from_notes(condition, flaws)
    title, reasoning = draft_mod.plan_title(
        args.brand, args.item, args.details, measurements, graded["grade"]
    )
    description, hype_notes = draft_mod.build_description(
        args.brand, args.item, measurements, condition, flaws, graded["grade"], graded["why"]
    )

    root = Path(args.root or Path.cwd())
    photos_dir = Path(args.photos_dir).resolve() if args.photos_dir else store.detect_photos_dir(root)
    date = store.photos_date(photos_dir.name) if photos_dir else datetime.date.today().isoformat()
    if args.out:
        path = root / args.out
    else:
        path = store.draft_path(root, photos_dir, args.brand or None, args.item)

    notes = ["grade check: " + " ".join(graded["why"])] + graded["warnings"] + hype_notes

    if not args.dry_run:
        store.save_draft(
            path,
            title,
            reasoning,
            description,
            meta={
                "date": date,
                "brand": args.brand or None,
                "item": args.item,
                "grade": graded["grade"],
                "flaws": " ; ".join(flaws) if flaws else None,
                "photos_folder": photos_dir.name if photos_dir else None,
                "notes": notes,
            },
        )

    print("Grade: %s" % graded["grade"])
    for why in graded["why"]:
        print("  - %s" % why)
    for warn in graded["warnings"]:
        print("  ! %s" % warn)
    print("")
    print("Title (%d chars): %s" % (len(title), title))
    print("")
    print("Searchable-word reasoning:")
    for r in reasoning:
        mark = "cut  " if r.get("dropped") else "kept "
        print("  %s [%-8s] %s" % (mark, r["aspect"], r["word"]))
        print("      %s" % r["why"])
    print("")
    print("Description:")
    print("-" * 60)
    print(description)
    print("-" * 60)
    for note in hype_notes:
        print("! %s" % note)
    if args.dry_run:
        print("(dry run: nothing written)")
    else:
        print("")
        print("Saved: %s" % path)
    return 0


def flaws_all_blank(args):
    return not (args.flaws or args.measurements)


def cmd_rewrite(args):
    path = Path(args.draft)
    if not path.exists():
        raise SystemExit("No draft found at %s" % path)
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---") or _section(text, "## Title", "## Description") is None:
        raise SystemExit("That file does not look like a listing-drafter draft (front matter + sections).")

    settings = load_config(start_dir=path.parent)
    base_url = args.base_url or settings["base_url"]
    model = args.model or settings["model"]

    section_title = (_section(text, "## Title", "### Searchable") or "").strip()
    section_desc = (_section(text, "## Description", "### Reviewer notes") or "").strip()
    grade = _front_field(text, "grade") or "Very Good"
    flaws = _split(_front_field(text, "flaws") or _flaws_from_text(text))

    user_prompt = (
        "Edit this marketplace listing draft. Follow every system rule.\n\n"
        "Existing title:\n%s\n\nExisting description:\n%s\n\n%s"
        % (section_title, section_desc, SCHEMA_HINT)
    )
    client = rw.Client(base_url=base_url, model=model, timeout=settings.get("timeout", 60.0))
    print("Asking %s (model: %s) for a rewrite... no key is ever sent." % (base_url, model))
    reply = client.chat(rw.SYSTEM_PROMPT, user_prompt)
    parsed = rw.parse_response(reply)

    problems = []
    for warn in cond_mod.check_title_grade_claim(parsed["title"], grade):
        problems.append(warn)
    missing = rw.check_flaws(parsed["description"], flaws)
    for flaw in missing:
        problems.append("flaw may have dropped out of the rewrite: %r" % flaw)
    for phrase in rw.hype_words(parsed["description"]):
        problems.append("hype phrase in rewrite: %r" % phrase)

    print("")
    print("Rewritten title (%d chars): %s" % (len(parsed["title"]), parsed["title"]))
    print("")
    print("Rewritten description:")
    print("-" * 60)
    print(parsed["description"])
    print("-" * 60)
    if problems:
        print("")
        print("Sanity check found issues:")
        for p in problems:
            print("! %s" % p)
    if args.save:
        store.save_draft(
            path,
            parsed["title"],
            _reasoning_from(text, parsed["title"]),
            parsed["description"],
            meta={
                "date": _front_field(text, "date") or datetime.date.today().isoformat(),
                "brand": _front_field(text, "brand"),
                "item": _front_field(text, "item"),
                "grade": grade,
                "flaws": " ; ".join(flaws) if flaws else None,
                "photos_folder": _front_field(text, "photos_folder"),
                "notes": ["rewritten by %s (%s); keep your photos folder as the source of truth" % (base_url, model)]
                + problems,
            },
        )
        print("")
        print("Overwrote: %s" % path)
        return 0
    if problems:
        print("")
        print("Not saved. Fix your notes and re-run, or pass --save to keep it anyway (an honest reviewer note goes in the file).")
        return 3
    print("")
    print("Rewrite looked honest. Re-run with --save to write it back.")
    return 0


def cmd_grade(args):
    graded = cond_mod.grade_from_notes(args.condition or "", _split(args.flaws))
    print("Grade: %s" % graded["grade"])
    for why in graded["why"]:
        print("  - %s" % why)
    for warn in graded["warnings"]:
        print("  ! %s" % warn)
    return 0


def _front_field(text, key):
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    head = text[3:end] if end >= 0 else text
    for line in head.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            if k.strip() == key:
                return v.strip()
    return None


def _section(text, start_marker, stop_marker):
    i = text.find(start_marker)
    if i < 0:
        return None
    body = text[i + len(start_marker):]
    if stop_marker:
        j = body.find(stop_marker)
        if j >= 0:
            body = body[:j]
    return body.strip()


def _flaws_from_text(text):
    flaws = []
    in_flaws = False
    for line in text.splitlines():
        s = line.strip()
        if s.lower().startswith("flaws"):
            in_flaws = True
            continue
        if in_flaws:
            if s.startswith("- "):
                flaws.append(s[2:])
            elif s.startswith(("Condition:", "Questions", "###", "##")):
                break
            elif not s and flaws:
                break
    return " ; ".join(flaws)


def _reasoning_from(text, new_title):
    reasoning = []
    in_reason = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("### Searchable-word reasoning"):
            in_reason = True
            continue
        if in_reason:
            if s.startswith("- "):
                rest = s[2:]
                word = rest.split(":", 1)[0] if ":" in rest else rest
                reasoning.append({"word": word.strip("`"), "why": rest})
            elif s.startswith("##") and reasoning:
                break
    if not reasoning:
        reasoning = [{"word": new_title, "aspect": "item", "why": "kept from original draft"}]
    return reasoning


def build_parser():
    parser = argparse.ArgumentParser(
        prog="listing-drafter",
        description="Draft honest marketplace listings from item notes. No hype, no key, local-first.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    sub = parser.add_subparsers(dest="command")

    p_draft = sub.add_parser("draft", help="build a draft from item notes")
    p_draft.add_argument("--brand")
    p_draft.add_argument("--item", help='plain words, e.g. "men\'s wool pea coat"')
    p_draft.add_argument("--condition", help="plain condition notes")
    p_draft.add_argument("--flaws", help='pipe-separated, e.g. "scuff on left arm|pilling under arms"')
    p_draft.add_argument("--measurements", help='pipe-separated, e.g. "chest: 24 in|length: 33 in"')
    p_draft.add_argument("--details", help="extra searchable words, e.g. model number, material")
    p_draft.add_argument("--photos-dir", help="photos folder; draft is saved beside it using its name")
    p_draft.add_argument("--out", help="explicit output path for the markdown draft")
    p_draft.add_argument("--root", help="folder to scan for photos folders (default: cwd)")
    p_draft.add_argument("--dry-run", action="store_true")
    p_draft.set_defaults(func=cmd_draft)

    p_rw = sub.add_parser("rewrite", help="optional rewrite pass via OpenAI-compatible endpoint")
    p_rw.add_argument("draft", help="path to the draft markdown file")
    p_rw.add_argument("--base-url", help="OpenAI-compatible endpoint, e.g. http://localhost:11434/v1")
    p_rw.add_argument("--model")
    p_rw.add_argument("--save", action="store_true")
    p_rw.set_defaults(func=cmd_rewrite)

    p_grade = sub.add_parser("grade", help="condition-grader sanity check only")
    p_grade.add_argument("--condition", help="plain condition notes")
    p_grade.add_argument("--flaws", help="pipe-separated flaw list")
    p_grade.set_defaults(func=cmd_grade)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 2
    args = _collect_notes(args)
    return args.func(args)


def run():
    sys.exit(main())


if __name__ == "__main__":
    run()
