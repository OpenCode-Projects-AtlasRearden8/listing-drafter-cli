"""Config: base_url and model only. Never a key."""

from __future__ import annotations

import os
from pathlib import Path

from . import rewrite as _rewrite

ENV_BASE_URL = "LISTING_DRAFTER_BASE_URL"
ENV_MODEL = "LISTING_DRAFTER_MODEL"
ENV_TIMEOUT = "LISTING_DRAFTER_TIMEOUT"


def _read_toml(path: Path):
    try:
        import tomllib
    except ImportError:
        return {}
    if not path.exists():
        return {}
    try:
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    except Exception:  # noqa: BLE001 - bad config should not crash the CLI
        return {}


def load_config(start_dir=None):
    """Flags > env > ./listing-drafter.toml > user config > defaults."""
    start = Path(start_dir or ".")
    settings = {}
    seen_keys = set()
    for path in [
        Path.home() / ".config" / "listing-drafter" / "config.toml",
        start / "listing-drafter.toml",
    ]:
        data = _read_toml(path)
        seen_keys.update(data.keys())
        for key in ("base_url", "model", "timeout"):
            if key in data and key not in settings:
                settings[key] = data[key]

    if ENV_BASE_URL in os.environ:
        settings["base_url"] = os.environ[ENV_BASE_URL]
    if ENV_MODEL in os.environ:
        settings["model"] = os.environ[ENV_MODEL]
    if ENV_TIMEOUT in os.environ and "timeout" not in settings:
        try:
            settings["timeout"] = float(os.environ[ENV_TIMEOUT])
        except ValueError:
            pass
    if "timeout" not in settings:
        settings["timeout"] = 60.0
    if not settings.get("base_url"):
        settings["base_url"] = _rewrite.DEFAULT_BASE_URL
    if not settings.get("model"):
        settings["model"] = _rewrite.DEFAULT_MODEL
    forbidden = [k for k in sorted(seen_keys) if "key" in k.lower() or "token" in k.lower() or "secret" in k.lower()]
    if forbidden:
        raise ValueError(
            "listing-drafter does not use API keys; found %s in a config file. Remove it — only base_url and model are configurable."
            % ", ".join(forbidden)
        )
    return settings
