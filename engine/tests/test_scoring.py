import pytest

from skin_engine.analysis import analyse
from skin_engine.scoring import ScoringConfig, score_product


def scored(snapshot, case, product_code, **kw):
    analysis = analyse(snapshot, case["answers"], case["concerns"], **kw)
    config = ScoringConfig.from_snapshot(snapshot)
    product = snapshot.products[product_code]
    return score_product(snapshot, product, analysis.ctx, analysis.restrictions, config)


def test_config_is_read_from_the_seed(snapshot):
    config = ScoringConfig.from_snapshot(snapshot)
    assert config.band_multiplier == {"mild": 1.0, "moderate": 1.25, "severe": 1.5}
    assert (config.position_cutoff, config.late_position_factor, config.care_penalty) == (
        5,
        0.5,
        1.0,
    )


def test_severe_case_multiplies_every_match_by_1_5(snapshot, cases):
    # hydra_serum: glycerin 3 + hyaluronic acid 3 + panthenol 2 + aloe 2 = 10, x 1.5 (severe)
    score = scored(snapshot, cases["A"], "hydra_serum")
    assert score.total == 15.0
    assert [m.ingredient for m in score.matches] == [
        "glycerin",
        "hyaluronic_acid",
        "panthenol",
        "aloe",
    ]


def test_boost_and_late_position(snapshot, cases):
    # gel_cream in case A: ceramides get +2 (over-exfoliation flag); panthenol is 6th, so x 0.5
    score = scored(snapshot, cases["A"], "gel_cream")
    points = {m.ingredient: m.points for m in score.matches}
    assert points["ceramides"] == 7.5  # (3 + 2) x 1.0 x 1.5
    assert points["panthenol"] == 1.5  # 2 x 0.5 x 1.5
    assert score.total == 21.0


def test_same_product_scores_lower_without_the_boost(snapshot, cases):
    # case E has no flags (no boost) and a mild band (x 1.0): 3 + 3 + 3 + 2 + 1 = 12
    assert scored(snapshot, cases["E"], "gel_cream").total == 12.0


def test_band_multiplier_for_moderate(snapshot, cases):
    score = scored(snapshot, cases["B"], "niacinamide_serum")
    assert score.total == 3.75  # niacinamide priority 3 x 1.25 (moderate)


def test_product_with_no_matching_ingredient_scores_zero(snapshot, cases):
    score = scored(snapshot, cases["B"], "barrier_cream")
    assert score.total == 0.0
    assert score.matches == []


def test_use_with_care_ingredients_cost_points(snapshot):
    case = {
        "answers": {"st1": "st1a", "st2": "st2a", "st3": "st3a", "hp3": "hp3a", "hp6": "hp6a"},
        "concerns": ["hyperpigmentation"],
    }
    score = scored(snapshot, case, "glow_serum")  # contains lactic acid; dry skin means care
    assert score.penalties == ["lactic_acid"]
    assert score.total == -1.0


@pytest.mark.parametrize("product", ["foam_cleanser", "mineral_spf"])
def test_scores_are_rounded_numbers(snapshot, cases, product):
    total = scored(snapshot, cases["A"], product).total
    assert total == round(total, 4)
