import os
from pathlib import Path

import pytest

from listing_drafter.config import load_config, ENV_BASE_URL, ENV_MODEL


def test_defaults():
    cfg = load_config(start_dir="/tmp")
    assert cfg["base_url"].startswith("http://localhost:11434")
    assert cfg["model"]
    assert "key" not in cfg


def test_env_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_BASE_URL, "http://127.0.0.1:9999/v1")
    monkeypatch.setenv(ENV_MODEL, "test-model")
    cfg = load_config(start_dir=tmp_path)
    assert cfg["base_url"] == "http://127.0.0.1:9999/v1"
    assert cfg["model"] == "test-model"


def test_key_in_config_is_refused(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_BASE_URL, raising=False)
    cfg = tmp_path / "listing-drafter.toml"
    cfg.write_text('base_url = "http://localhost:11434/v1"\napi_key = "sk-nope"\n')
    with pytest.raises(ValueError) as err:
        load_config(start_dir=tmp_path)
    assert "does not use API keys" in str(err.value)
