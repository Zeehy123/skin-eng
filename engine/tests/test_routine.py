import copy

from skin_engine.analysis import analyse
from skin_engine.routine import build_routine, choose_template
from skin_engine.scoring import ScoringConfig
from skin_engine.snapshot import Snapshot


def routine_for(snapshot, case, eligible=None):
    analysis = analyse(snapshot, case["answers"], case["concerns"])
    if eligible is None:
        eligible = list(snapshot.products)
    config = ScoringConfig.from_snapshot(snapshot)
    return analysis, *build_routine(snapshot, analysis, eligible, config)


def test_highest_priority_template_wins(snapshot, cases):
    for letter, expected in {
        "A": "barrier_first",
        "B": "hyperpigmentation_routine",
        "E": "dehydration_routine",
    }.items():
        ctx = analyse(snapshot, cases[letter]["answers"], cases[letter]["concerns"]).ctx
        assert choose_template(snapshot, ctx)["code"] == expected


def test_default_template_when_no_concern_is_chosen(snapshot, cases):
    case = {"answers": cases["B"]["answers"], "concerns": []}
    analysis = analyse(snapshot, case["answers"], case["concerns"])
    assert choose_template(snapshot, analysis.ctx)["code"] == "default"


def test_ties_prefer_the_template_form_then_price(snapshot, cases):
    eligible = ["milk_cleanser", "gel_cleanser"]
    # case A: equal scores, and the template prefers milk first
    _, _, steps = routine_for(snapshot, cases["A"], eligible)
    assert [steps[0].pick.code] + [a.code for a in steps[0].alternatives] == [
        "milk_cleanser",
        "gel_cleanser",
    ]
    # case B: equal scores and no preferred form, so the cheaper gel cleanser wins
    _, _, steps = routine_for(snapshot, cases["B"], eligible)
    assert steps[0].pick.code == "gel_cleanser"


def test_alternatives_are_ranked_and_limited(snapshot, cases):
    # build_routine trusts the list it is given, so we can try any products for the step.
    eligible = ["niacinamide_serum", "vitc_serum", "azelaic_treatment", "hydra_serum"]
    _, _, steps = routine_for(snapshot, cases["B"], eligible)
    treatment = next(s for s in steps if s.step == "treatment_serum")
    # azelaic acid is boosted by the post-acne flag and the product also holds niacinamide
    assert treatment.pick.code == "azelaic_treatment"
    assert treatment.pick.score == 8.75
    assert [a.code for a in treatment.alternatives] == ["niacinamide_serum", "vitc_serum"]


def test_only_two_alternatives_are_kept(snapshot, cases):
    eligible = ["niacinamide_serum", "vitc_serum", "azelaic_treatment", "retinol_serum"]
    _, _, steps = routine_for(snapshot, cases["B"], eligible)
    treatment = next(s for s in steps if s.step == "treatment_serum")
    assert len(treatment.alternatives) == 2


def test_step_without_a_product_is_reported(snapshot, cases):
    _, _, steps = routine_for(snapshot, cases["B"], eligible=["gel_cleanser"])
    sunscreen = next(s for s in steps if s.step == "sunscreen")
    assert sunscreen.pick is None
    assert sunscreen.required is True
    assert "No suitable product" in sunscreen.note


def test_required_step_from_the_answers_is_added_if_the_template_lacks_it(snapshot, cases):
    data = copy.deepcopy(snapshot.data)
    for template in data["routine_templates"]:
        template["steps"] = [s for s in template["steps"] if s["step"] != "sunscreen"]
    trimmed = Snapshot(data)
    _, _, steps = routine_for(trimmed, cases["B"])
    sunscreen = steps[-1]
    assert sunscreen.step == "sunscreen"
    assert (sunscreen.required, sunscreen.priority) == (True, 2)
