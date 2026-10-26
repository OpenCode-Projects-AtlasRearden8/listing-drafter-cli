from listing_drafter import condition as cond


def test_no_notes_defaults_conservatively():
    out = cond.grade_from_notes("", [])
    assert out["grade"] == "Very Good"


def test_severe_word_caps_parts():
    out = cond.grade_from_notes("looks decent overall", ["screen is cracked and it doesn't turn on"])
    assert out["grade"] == "Used/For Parts"
    assert out["matched"]["3"]


def test_damage_word_caps_good():
    out = cond.grade_from_notes("worn once", ["small stain on the sleeve"])
    assert out["grade"] == "Good"


def test_wear_word_caps_very_good():
    out = cond.grade_from_notes("gently worn", ["light fading on the shoulders"])
    assert out["grade"] == "Very Good"


def test_negation_not_treated_as_flaw():
    out = cond.grade_from_notes("no stains, no rips, worn once", [])
    assert out["grade"] == "Very Good"
    assert "2" not in out["matched"]


def test_like_new_claim_with_flaw_warns():
    out = cond.grade_from_notes("like new", ["tiny hole near the hem"])
    assert out["grade"] == "Good"
    assert out["warnings"]


def test_near_new_words_lift_grade_when_flawless():
    out = cond.grade_from_notes("brand new, never worn, with tags", [])
    assert out["grade"] == "New without Tags"


def test_title_grade_claim_check():
    assert cond.check_title_grade_claim("Perfect Condition Coat", "Good")
    assert not cond.check_title_grade_claim("Wool Pea Coat Size L", "Good")
