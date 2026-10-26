import json

import pytest

from listing_drafter import cli
from listing_drafter import rewrite as rw


def run_draft(args, cwd):
    return cli.main(["draft", "--root", str(cwd)] + args)


def make_mock_client(reply):
    """A rew.Client stand-in that records calls and returns a canned reply."""
    calls = []

    class FakeClient:
        def __init__(self, base_url=rw.DEFAULT_BASE_URL, model=rw.DEFAULT_MODEL, **kwargs):
            self.base_url = base_url
            self.model = model
            calls.append({"base_url": base_url, "model": model})

        def chat(self, system, user):
            calls.append({"system": system, "user": user})
            return reply

    return FakeClient, calls


def test_draft_writes_markdown_beside_photos_folder(tmp_path, capsys):
    photos = tmp_path / "photos-2026-10-20-blue-mug"
    photos.mkdir()
    rc = run_draft(
        [
            "--brand", "Acme", "--item", "ceramic mug", "--condition", "used twice, no chips",
            "--flaws", "tiny scuff under the handle",
            "--measurements", "height: 4 in|size: 10 oz",
        ],
        tmp_path,
    )
    assert rc == 0
    saved = tmp_path / "photos-2026-10-20-blue-mug-draft.md"
    assert saved.exists()
    text = saved.read_text()
    assert "brand: Acme" in text
    assert "tiny scuff under the handle" in text
    assert "Searchable-word reasoning" in text
    out = capsys.readouterr().out
    assert "Grade:" in out
    assert "Saved:" in out


def test_draft_requires_item_off_tty(tmp_path):
    with pytest.raises(SystemExit) as exc:
        run_draft([], tmp_path)
    assert "--item" in str(exc.value)


def test_draft_dry_run_writes_nothing(tmp_path):
    rc = run_draft(
        ["--item", "wristwatch", "--condition", "worn", "--dry-run", "--out", "never.md"],
        tmp_path,
    )
    assert rc == 0
    assert not (tmp_path / "never.md").exists()


def test_rewrite_with_mocked_endpoint(tmp_path, capsys, monkeypatch):
    photos = tmp_path / "photos-2026-10-20-broken-lamp"
    photos.mkdir()
    run_draft(
        [
            "--brand", "Litra", "--item", "desk lamp", "--condition", "damaged power cord",
            "--flaws", "cracked base", "--measurements", "height: 20 in",
        ],
        tmp_path,
    )
    draft = tmp_path / "photos-2026-10-20-broken-lamp-draft.md"
    assert draft.exists()

    reply = json.dumps({
        "title": "Litra Desk Lamp For Parts",
        "description": "Litra desk lamp. Height: 20 in. Flaws, honestly all of them:\n- cracked base\n- damaged power cord.",
    })
    FakeClient, calls = make_mock_client(reply)
    monkeypatch.setattr(rw, "Client", FakeClient)
    rc = cli.main(["rewrite", str(draft), "--base-url", "http://mock.local/v1", "--model", "test-model"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "no key is ever sent" in out
    assert "Litra Desk Lamp For Parts" in out
    assert any(c.get("model") == "test-model" for c in calls)
    assert all("api key" not in json.dumps(c).lower() for c in calls)


def test_rewrite_flags_dropped_flaw(tmp_path, capsys, monkeypatch):
    photos = tmp_path / "photos-2026-10-20-teapot"
    photos.mkdir()
    cli.main(
        [
            "draft", "--root", str(tmp_path), "--brand", "Alds", "--item", "teapot",
            "--condition", "worn", "--flaws", "cracked lid hinge|faded glaze",
        ]
    )
    draft = tmp_path / "photos-2026-10-20-teapot-draft.md"
    assert draft.exists()

    reply = json.dumps({
        "title": "Alds Teapot",
        "description": "Alds teapot. Faded glaze only. Questions welcome.",
    })
    FakeClient, _ = make_mock_client(reply)
    monkeypatch.setattr(rw, "Client", FakeClient)
    rc = cli.main(["rewrite", str(draft)])
    assert rc == 3
    out = capsys.readouterr().out
    assert "cracked lid hinge" in out
    assert "Not saved" in out


def test_rewrite_persists_on_save(tmp_path, monkeypatch):
    photos = tmp_path / "photos-2026-10-20-frame"
    photos.mkdir()
    cli.main(["draft", "--root", str(tmp_path), "--brand", "IKEA", "--item", "picture frame", "--condition", "new, sealed"])
    draft = tmp_path / "photos-2026-10-20-frame-draft.md"
    assert draft.exists()

    reply = json.dumps({
        "title": "IKEA Picture Frame New With Tags",
        "description": "IKEA picture frame, new in the box, sealed. Questions welcome. Happy to send extra photos.",
    })
    FakeClient, _ = make_mock_client(reply)
    monkeypatch.setattr(rw, "Client", FakeClient)
    rc = cli.main(["rewrite", str(draft), "--save"])
    assert rc == 0
    text = draft.read_text()
    assert "IKEA Picture Frame New With Tags" in text
    assert "rewritten by" in text


def test_rewrite_rejects_hype(tmp_path, capsys, monkeypatch):
    photos = tmp_path / "photos-2026-10-20-vase"
    photos.mkdir()
    cli.main(["draft", "--root", str(tmp_path), "--brand", "Fenton", "--item", "vase", "--condition", "worn"])
    draft = tmp_path / "photos-2026-10-20-vase-draft.md"
    assert draft.exists()

    reply = json.dumps({
        "title": "Amazing Fenton Vase",
        "description": "This stunning vase is a rare find. Questions welcome.",
    })
    FakeClient, _ = make_mock_client(reply)
    monkeypatch.setattr(rw, "Client", FakeClient)
    rc = cli.main(["rewrite", str(draft)])
    assert rc == 3
    out = capsys.readouterr().out
    assert "hype" in out


def test_grade_command(tmp_path, capsys):
    rc = cli.main(["grade", "--condition", "like new", "--flaws", "small hole"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Grade: Good" in out
