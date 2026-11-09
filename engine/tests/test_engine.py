import copy
import json

import pytest

from skin_engine.engine import recommend
from skin_engine.snapshot import Snapshot


@pytest.mark.parametrize("letter", ["A", "B", "E"])
def test_routine_matches_the_seed(snapshot, cases, letter):
    case = cases[letter]
    expected = case["expected_routine"]
    result = recommend(snapshot, case["answers"], case["concerns"])

    assert result.template == expected["template"]
    picks = {step.step: step.pick.code for step in result.routine}
    assert picks == expected["picks"]
    scores = {step.pick.code: step.pick.score for step in result.routine}
    for code, score in expected["pick_scores"].items():
        assert scores[code] == score
    assert result.warnings == []


def test_red_flag_returns_a_referral_and_no_products(snapshot, cases):
    result = recommend(snapshot, cases["C"]["answers"], cases["C"]["concerns"])
    assert result.outcome == "refer_to_professional"
    assert result.routine == []
    assert "see a doctor" in result.referral_reasons[0]


def test_too_few_answers_asks_for_more(snapshot, cases):
    result = recommend(snapshot, cases["D"]["answers"], cases["D"]["concerns"])
    assert result.outcome == "needs_more_answers"
    assert result.routine == []


def test_nothing_recommended_is_ever_excluded(snapshot, cases):
    for letter in "ABE":
        result = recommend(snapshot, cases[letter]["answers"], cases[letter]["concerns"])
        for step in result.routine:
            for pick in [step.pick, *step.alternatives]:
                assert pick.code not in result.excluded, (letter, pick.code)


def test_exclusions_are_explained(snapshot, cases):
    result = recommend(snapshot, cases["A"]["answers"], cases["A"]["concerns"])
    assert "foam_cleanser" in result.excluded
    assert "glow_serum" in result.excluded
    assert "milk_cleanser" not in result.excluded


def test_result_can_be_sent_as_json(snapshot, cases):
    result = recommend(snapshot, cases["A"]["answers"], cases["A"]["concerns"])
    data = json.loads(json.dumps(result.to_dict()))
    assert data["outcome"] == "recommend"
    assert data["routine"][0]["pick"]["code"] == "milk_cleanser"


def test_same_answers_give_the_same_result(snapshot, cases):
    first = recommend(snapshot, cases["A"]["answers"], cases["A"]["concerns"]).to_dict()
    second = recommend(snapshot, cases["A"]["answers"], cases["A"]["concerns"]).to_dict()
    assert first == second


def test_declared_skin_type_skips_the_skin_quiz(snapshot):
    answers = {"hp3": "hp3b", "hp4": "hp4a", "hp6": "hp6a"}
    result = recommend(snapshot, answers, ["hyperpigmentation"], declared_skin_type="oily")
    assert (result.outcome, result.skin_type, result.confidence) == (
        "recommend",
        "oily",
        "declared",
    )
    assert result.bands == {"hyperpigmentation": "moderate"}


def test_missing_product_gives_a_warning(snapshot, cases):
    data = copy.deepcopy(snapshot.data)
    for product in data["products"]:
        if product["step"] == "sunscreen":
            product["active"] = False
    result = recommend(Snapshot(data), cases["B"]["answers"], cases["B"]["concerns"])
    assert result.warnings == ["No suitable product for the sunscreen step."]
    assert result.excluded["mineral_spf"] == ["Not currently available."]
