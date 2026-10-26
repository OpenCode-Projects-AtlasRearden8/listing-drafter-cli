from listing_drafter import draft as d


def test_title_prefers_searchable_words():
    title, reasoning = d.plan_title(
        "Hagstrom", "acoustic guitar", "model 542", ["guitar length: 40 in", "size: full"], "Very Good"
    )
    assert title.startswith("Hagstrom")
    assert "guitar" in title.lower()
    kept_words = " ".join(r["word"] for r in reasoning if not r.get("dropped"))
    assert kept_words == title


def test_title_reasoning_marks_cut_words():
    long_item = "genuine leather bomber jacket villages fairness determinator"
    title, reasoning = d.plan_title(
        "Brand X Y Z", long_item, "Extra Detail Word", ["size: XL"], "Good", max_len=45
    )
    assert len(title) <= 45
    dropped = [r for r in reasoning if r.get("dropped")]
    assert dropped
    for r in dropped:
        assert "80-character" in r["why"]


def test_for_parts_in_title_when_broken():
    title, _ = d.plan_title("Bissell", "upright vacuum", "", [], "Used/For Parts")
    assert "for parts" in title.lower()


def test_no_condition_word_for_mid_grades():
    title, _ = d.plan_title("Bissell", "upright vacuum", "", [], "Good")
    assert "good" not in title.lower()
    assert "very good" not in title.lower()


def test_description_discloses_every_flaw():
    desc, notes = d.build_description(
        "carhartt", "wool coat", ["chest: 24 in"],
        "worn a few times", ["scuff on right elbow", "missing one button tag"],
        "Good", ["capped by flaws"],
    )
    assert "scuff on right elbow" in desc
    assert "missing one button tag" in desc
    assert "Measurements:" in desc


def test_hype_is_stripped_and_reported():
    desc, notes = d.build_description(
        "acme", "wristwatch", [], "amazing condition, like perfect",
        [], "Very Good", [],
    )
    assert "amazing" not in desc
    assert "perfect" not in desc.lower().replace("condition:", "")
    assert notes and "amazing" in notes[0]


def test_flaw_that_is_all_hype_still_gets_disclosed_placeholder():
    desc, notes = d.build_description("acme", "mug", [], "", ["amazing"], "Excellent", [])
    assert "amazing" in desc
    assert "flaw needs rewording" in desc
