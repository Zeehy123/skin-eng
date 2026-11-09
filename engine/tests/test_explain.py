from skin_engine.analysis import analyse
from skin_engine.explain import _join, explain_pick, select_tips
from skin_engine.scoring import ProductScore, ScoringConfig, score_product


def explained(snapshot, case, product_code):
    analysis = analyse(snapshot, case["answers"], case["concerns"])
    config = ScoringConfig.from_snapshot(snapshot)
    product = snapshot.products[product_code]
    score = score_product(snapshot, product, analysis.ctx, analysis.restrictions, config)
    return explain_pick(snapshot, score, analysis.ctx)


def test_summary_names_the_strongest_ingredients(snapshot, cases):
    summary, reasons = explained(snapshot, cases["A"], "hydra_serum")
    assert (
        summary == "Contains glycerin, hyaluronic acid and panthenol, which help with dehydration."
    )
    assert reasons[0] == "Glycerin draws water into the skin."
    assert len(reasons) == 3


def test_single_ingredient_uses_helps(snapshot, cases):
    summary, _ = explained(snapshot, cases["B"], "niacinamide_serum")
    assert summary.startswith("Contains niacinamide, which helps with hyperpigmentation")


def test_product_with_no_matches_gets_a_plain_reason(snapshot, cases):
    summary, reasons = explained(snapshot, cases["B"], "barrier_cream")
    assert summary == "Suits dry skin and avoids the ingredients we flagged for you."
    assert reasons == [summary]


def test_join_helper():
    assert _join([]) == ""
    assert _join(["a"]) == "a"
    assert _join(["a", "b"]) == "a and b"
    assert _join(["a", "b", "c"]) == "a, b and c"


def test_tips_follow_flags_and_concerns(snapshot, cases):
    ctx_a = analyse(snapshot, cases["A"]["answers"], cases["A"]["concerns"]).ctx
    codes = {tip["code"] for tip in select_tips(snapshot, ctx_a)}
    assert codes == {
        "tip_dh_cleanser",
        "tip_dh_lukewarm",
        "tip_dh_overexfoliation",
        "tip_dh_air",
        "tip_dh_oily",
        "tip_dh_foaming",
    }

    ctx_b = analyse(snapshot, cases["B"]["answers"], cases["B"]["concerns"]).ctx
    codes = {tip["code"] for tip in select_tips(snapshot, ctx_b)}
    assert codes == {"tip_hp_sunscreen", "tip_hp_picking", "tip_hp_patience"}


def test_no_tips_when_no_condition_passes(snapshot, cases):
    ctx = analyse(snapshot, cases["E"]["answers"], cases["E"]["concerns"]).ctx
    assert select_tips(snapshot, ctx) == []


def test_unscored_zero_match_object_is_handled(snapshot, cases):
    ctx = analyse(snapshot, cases["B"]["answers"], cases["B"]["concerns"]).ctx
    summary, _ = explain_pick(snapshot, ProductScore(total=0.0), ctx)
    assert "dry skin" in summary
