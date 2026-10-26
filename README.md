# listing-drafter

Turn messy item notes into honest marketplace listing drafts.

You type in what you know — condition, brand, flaws, measurements — and you get
back a local Markdown draft with three things:

1. **A title with searchable-word reasoning** — every word was chosen because a
   buyer might actually search it, and every cut word is explained.
2. **A plain-honest description** — measurements exact, every flaw listed,
   nothing hidden, no hype words ("amazing", "pristine", "rare find" get
   filtered out on purpose).
3. **A condition-grader sanity check** — the grader never upgrades your item.
   The worst word in your notes wins, so a "like new" claim with a "torn" in it
   won't pass as like new.

Built by **Asdale Dynamics, LLC** — plain English, step by step, never
condescending. Complements resale-lot-builder for when you have a lot of
items, not just one.

## How it's truthful

- The description keeps all flaws, and if a rewrite pass ever drops one, the
  tool calls it out and refuses to save the listing without a warning.
- Hype phrases are stripped from your notes before they hit the description,
  and the removal is reported, not silent.
- Near-grades: your notes may say "like new", but the grader caps the grade at
  what the flaws support, and tells you why.

## How to install

You need Python 3.9+. Nothing else. No API keys. That's the point.

```bash
pip install -e .
```

## Usage

Stand in the folder where you keep your photos folders, then:

```bash
listing-drafter draft \
  --brand Carhartt \
  --item "men's wool pea coat size L in navy" \
  --condition "worn a handful of times, no rips" \
  --flaws "light pilling under the arms" \
  --measurements "chest: 24 in|length: 33 in"
```

Pipe-separated lists for `--flaws`, `--measurements`, and anything else with
more than one value.

Drafts are saved **beside your photos folder**, named after it:

```
photos-2026-10-26-carhartt-coat/
photos-2026-10-26-carhartt-coat-draft.md    ← this is your draft
```

If no photos folder exists, a `drafts/<date>-<name>.md` file is used instead.

### Bash prompt mode

Run `listing-drafter draft` with no flags in a real terminal and it will ask
you for the notes one question at a time. Nothing you type is sent anywhere by
default.

### Optional rewrite pass

Point at any OpenAI-compatible endpoint — the default assumes a local Ollama
server. **No key is ever sent, stored, or asked for.** If you pass a key
somewhere by accident, it's ignored; there is no auth header in the request at
all.

```bash
listing-drafter rewrite photos-2026-10-26-carhartt-coat-draft.md
listing-drafter rewrite photos-2026-10-26-carhartt-coat-draft.md \
  --base-url http://localhost:11434/v1 \
  --model llama3.2
listing-drafter rewrite ... --save   # actually write it back after review
```

You can also set base_url/model in a `listing-drafter.toml` next to your notes:

```toml
base_url = "http://localhost:11434/v1"
model = "llama3.2"
```

or with environment variables `LISTING_DRAFTER_BASE_URL` and
`LISTING_DRAFTER_MODEL`.

The rewrite is guarded: the tool re-checks that every flaw survived, that no
hype words snuck in, and that the title still matches the grade. Problems are
printed. If you choose `--save` anyway, an honest reviewer note goes in the
file.

### Condition check only

```bash
listing-drafter grade --condition "like new" --flaws "small hole"
# Grade: Good
```

## The condition scale

Grades follow the marketplace-style shorthand: New with Tags, New without
Tags, Like New, Excellent, Very Good, Good, Used/For Parts. The grader is
deliberately conservative — when your notes disagree, it picks the lower grade
and explains why.

## Testing

```bash
pytest
```

All endpoint behavior in the tests is mocked; nothing phones home.

## Notes

- Markdown drafts are plain files, no database, no cloud. Git them if you like.
- The rewrite endpoint is *optional*. The default setup never needs to talk to
  the internet.
- Language: keep the tone like the tool does — plain, warm, honest.

## License

MIT — see LICENSE. Copyright (c) 2026 Asdale Dynamics, LLC.
