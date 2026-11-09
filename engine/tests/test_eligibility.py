from skin_engine.analysis import analyse
from skin_engine.eligibility import exclusion_reasons


def reasons(snapshot, case, product_code, product=None):
    analysis = analyse(snapshot, case["answers"], case["concerns"])
    product = product or snapshot.products[product_code]
    return exclusion_reasons(snapshot, product, analysis.ctx, analysis.restrictions)


def test_eligible_product_has_no_reasons(snapshot, cases):
    assert reasons(snapshot, cases["A"], "milk_cleanser") == []


def test_foaming_sulfate_cleanser_is_excluded_for_tight_skin(snapshot, cases):
    text = " ".join(reasons(snapshot, cases["A"], "foam_cleanser"))
    assert "foaming" in text
    assert "sodium lauryl sulfate" in text
    assert "fragrance" in text


def test_acid_serum_excluded_after_over_exfoliation(snapshot, cases):
    text = " ".join(reasons(snapshot, cases["A"], "glow_serum"))
    assert "lactic acid" in text


def test_wrong_skin_type_is_a_reason(snapshot, cases):
    assert reasons(snapshot, cases["A"], "barrier_cream") == ["Not designed for combination skin."]


def test_sensitive_skin_excludes_fragrance(snapshot, cases):
    text = " ".join(reasons(snapshot, cases["B"], "perfumed_cream"))
    assert "Contains fragrance" in text
    assert "sensitive" in text.lower()


def test_inactive_products_are_not_available(snapshot, cases):
    off = {**snapshot.products["milk_cleanser"], "active": False}
    assert reasons(snapshot, cases["A"], "milk_cleanser", product=off) == [
        "Not currently available."
    ]


def test_reasons_are_not_repeated(snapshot, cases):
    found = reasons(snapshot, cases["A"], "foam_cleanser")
    assert len(found) == len(set(found))
