import json

from listing_drafter import store


def test_draft_path_beside_photos_folder(tmp_path):
    photos = tmp_path / "photos-2026-10-26-carhartt-coat"
    photos.mkdir()
    path = store.draft_path(tmp_path, photos, "Carhartt", "wool coat", "2026-01-02")
    assert path.name == "photos-2026-10-26-carhartt-coat-draft.md"
    assert path.parent == tmp_path


def test_draft_path_fallback_uses_date(tmp_path):
    path = store.draft_path(tmp_path, None, "Carhartt", "wool coat", "2026-01-02")
    assert "2026-01-02" in path.name
    assert path.parent.name == "drafts"


def test_save_draft_contains_flaws_section(tmp_path):
    path = store.save_draft(
        tmp_path / "drafts" / "x.md", "A Title",
        [{"word": "A", "aspect": "item", "why": "kept"}],
        "Desc body with flaw note",
        {"date": "2026-10-26", "brand": "Acme", "grade": "Good", "notes": ["grade: capped"]},
    )
    text = path.read_text()
    assert "---" in text and "brand: Acme" in text
    assert "# Draft Listing" in text
    assert "kept" in text
    assert "capped" in text


def test_detect_photos_dir_prefers_newest(tmp_path):
    a = tmp_path / "photos-2026-01-01-a"
    b = tmp_path / "photos-2026-02-01-b"
    a.mkdir()
    b.mkdir()
    import os

    os.utime(a, (1000, 1000))
    os.utime(b, (2000, 2000))
    assert store.detect_photos_dir(tmp_path).name == b.name


def test_photos_date_from_name(tmp_path):
    photos = tmp_path / "photos-2026-01-15-blue-mug"
    photos.mkdir()
    assert store.photos_date(photos.name) == "2026-01-15"
    assert store.photos_date("IMG20260116223000") == "2026-01-16"


def test_slugify():
    assert store.slugify("Men's Wool Coat — Large!") == "men-s-wool-coat-large"
