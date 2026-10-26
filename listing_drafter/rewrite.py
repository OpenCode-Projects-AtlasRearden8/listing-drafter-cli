"""Optional rewrite pass via a configurable OpenAI-compatible endpoint.

Default points at a local Ollama server (http://localhost:11434/v1).
Any base_url/model works. No API key is ever used or stored; the client
sends no Authorization header at all.
"""

from __future__ import annotations

import json
import re
import urllib.request

SCHEMA_REMINDER = (
    'Reply with JSON only, no commentary, in the shape '
    '{"title": "...", "description": "..."}.'
)

SYSTEM_PROMPT = (
    "You are a marketplace listing editor for a careful reseller. "
    "Your rules, in order: "
    "(1) Never add a fact that is not in the item notes or existing draft; "
    "if you are tempted to embellish, don't. "
    "(2) Never drop or soften a flaw. Every flaw listed must appear in your "
    "description wording. "
    "(3) No hype, no sales pressure, no emojis. Write like an honest friend "
    "describing the item: plain sentences, plain facts. "
    "(4) Keep the measurements as written; buyers need exact numbers. "
    "(5) Keep the title at 80 characters or fewer and use searchable words "
    "(brand, item, size), not adjectives. "
    + SCHEMA_REMINDER
)

DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "llama3.2"


class RewriteError(RuntimeError):
    pass


class Client:
    """Minimal OpenAI-compatible chat client. No key, no auth header."""

    def __init__(self, base_url=DEFAULT_BASE_URL, model=DEFAULT_MODEL, timeout=60.0, urlopen=None):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or DEFAULT_MODEL
        self.timeout = timeout
        self._urlopen = urlopen or urllib.request.urlopen

    def chat(self, system, user):
        url = self.base_url + "/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001 - surface a friendly message
            raise RewriteError(
                "Could not reach %s (is your local model server running?)." % url
            ) from exc
        try:
            data = json.loads(body)
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise RewriteError("Endpoint reply was not in OpenAI chat format.") from exc


def parse_response(text):
    """Accept JSON directly, or fenced-in-```json code fences."""
    text = (text or "").strip()
    candidates = [
        text,
        re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL).group(1) if re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL) else None,
        re.search(r"\{.*\}", text, re.DOTALL).group(0) if re.search(r"\{.*\}", text, re.DOTALL) else None,
    ]
    for cand in candidates:
        if not cand:
            continue
        try:
            data = json.loads(cand)
        except ValueError:
            continue
        if isinstance(data, dict) and "title" in data and "description" in data:
            title = str(data["title"]).strip()
            description = str(data["description"]).strip()
            if title and description:
                return {"title": title, "description": description}
    raise RewriteError(
        "Model output was not usable JSON with 'title' and 'description'. "
        "Try a different model, or draft a lower temperature."
    )


def check_flaws(description, flaws):
    """Every flaw must survive the rewrite. Report the missing ones."""
    low = (description or "").lower()
    normalized = re.sub(r"[^a-z0-9 ]+", " ", low)
    missing = []
    for flaw in flaws or []:
        words = [w for w in re.split(r"\s+", flaw.lower()) if w]
        stem_words = [w[: max(4, len(w) - 2)] if len(w) > 5 else w for w in words]
        found = all(
            any(stem in tok or tok in stem for tok in normalized.split())
            for stem in stem_words
        )
        if not found:
            missing.append(flaw)
    return missing


def hype_words(text):
    from .draft import strip_hype

    return strip_hype(text)[1]
