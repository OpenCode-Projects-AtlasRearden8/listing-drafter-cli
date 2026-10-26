# STATUS

Last updated: 2026-10-26. Built by Asdale Dynamics, LLC for the
listing-drafter-cli project.

## What was built

**listing-drafter** — a local-first Python CLI that drafts marketplace listing
copy from item notes, staying truthful and never salesy. Verified under
Python 3.13; requires 3.9+. Zero runtime dependencies (standard library only).

Three commands:

- `draft` — takes brand, item, condition notes, flaws, measurements
  (pipe-separated flags, or prompted if run interactively), and writes a
  Markdown draft:
  - **Title with searchable-word reasoning** — picks brand / color / item /
    detail / size / material / honest condition words, explains every kept and
    cut word, respects an 80-character limit.
  - **Plain-honest description** — measurements verbatim, condition notes
    cleaned of hype words (and the removals reported), every flaw listed.
  - **Condition grade** — the worst word in your notes wins (never an
    upgrade); cross-checks "like new"-style claims against actual flaws.
- `rewrite` — optional polish pass via any OpenAI-compatible endpoint
  (default Ollama `http://localhost:11434/v1`, any base_url/model). Sends **no
  Authorization header ever**; config files containing key/token/secret names
  are refused outright. Sanity re-checks the rewrite: did every flaw survive?
  did any hype sneak in? does the title still match the grade? Unsatisfying
  rewrites are not saved unless you insist (`--save`), and reviewer notes go
  in the file.
- `grade` — the condition-grader sanity check alone.

Drafts land **beside your photos folder, named after it**
(`photos-2026-10-26-x/ → photos-2026-10-26-x-draft.md`), with a
`drafts/<date>-<name>.md` fallback. Pure Markdown with front matter.

## How to run it

```bash
pip install -e .          # or just: python3 -m listing_drafter ...
listing-drafter draft --brand Carhartt --item "men's wool pea coat" \
  --condition "worn a few times, no rips" --flaws "light pilling under arms" \
  --measurements "chest: 24 in|length: 33 in"
listing-drafter rewrite <draft.md> [--base-url ...] [--model ...] [--save]
listing-drafter grade --condition "like new" --flaws "small hole"
```

Config: `listing-drafter.toml` (base_url, model) in the working folder or
`~/.config/listing-drafter/config.toml`, env vars
`LISTING_DRAFTER_BASE_URL`/`LISTING_DRAFTER_MODEL`.

## Verification results

- `pytest`: **40 tests, all passing** — condition grader (caps + negation +
  warnings), title planner (searchable reasoning + 80-char cuts + For Parts),
  description builder (flaw disclosure + hype stripping), rewrite client
  (mocked endpoint, no-auth-header check, flaw-survival checks, JSON/fenced
  parse), storage beside photos-folder naming, CLI end-to-end drafts and
  rewrites (mocked endpoint; nothing phones home).
- Manual run-throughs: draft saves beside a photos folder; `rewrite` gives
  friendly errors for missing files and non-draft files; a config file with an
  `api_key` is refused; `--version` and console script work.
- Mocked-endpoint end-to-end `rewrite --save` produces an overwritten draft
  with reviewer notes.

## Known gaps

- The grader is keyword-based (English only); it won't infer condition subtleties
  like counterfeit risk or smell severity. The conservative cap is intentional.
- The rewrite assumes the model returns JSON in the documented shape; fenced
  JSON is tolerated but prose-only replies are rejected with a clear error.
- No `--interactive` answers for `rewrite`; it reads the draft file only.
- No photo file validation (the tool trusts the folder name you give it).
- Windows path handling untested in CI terms (uses pathlib throughout, so it
  should be fine).
- Story-of-the-repo: descriptions intentionally won't close the sale for you —
  the goal is honesty, not conversion copy.

## License

MIT — Copyright (c) 2026 Asdale Dynamics, LLC (see LICENSE).
