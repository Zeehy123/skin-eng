import pytest

from skin_engine.analysis import RECOMMEND, analyse
from skin_engine.tally import AnswerError


def run_case(snapshot, case):
    return analyse(snapshot, case["answers"], case["concerns"])


@pytest.mark.parametrize("letter", ["A", "B", "C", "D", "E"])
def test_seed_cases(snapshot, cases, letter):
    case = cases[letter]
    expected = case["expected"]
    result = run_case(snapshot, case)

    assert result.outcome == expected["outcome"]
    if result.outcome != RECOMMEND:
        return
    assert result.profile.skin_type == expected["skin_type"]
    assert result.profile.sensitive == expected["sensitive"]
    assert result.ctx.bands == expected["bands"]
    assert sorted(result.ctx.flags) == sorted(expected["flags"])
    assert result.restrictions.avoided_groups() == sorted(expected["groups"])
    assert result.tally.required_steps == expected.get("required_steps", {})


def test_red_flag_beats_everything(snapshot, cases):
    result = run_case(snapshot, cases["C"])
    assert result.outcome == "refer_to_professional"
    assert "see a doctor" in result.referral_reasons[0]


def test_unknown_concern_is_rejected(snapshot):
    with pytest.raises(AnswerError, match="Unknown concern"):
        analyse(snapshot, {}, ["acne"])


def test_restrictions_for_case_a(snapshot, cases):
    r = run_case(snapshot, cases["A"]).restrictions
    avoided = set(r.avoid_ingredients)
    assert {"lactic_acid", "retinol", "sodium_lauryl_sulfate", "fragrance"} <= avoided
    assert set(r.avoid_forms) == {"foaming"}
    assert r.care_ingredients == {}


def test_avoid_beats_use_with_care(snapshot, cases):
    # Dry skin alone only asks for care with acids, but sensitivity and irritation say avoid.
    r = run_case(snapshot, cases["B"]).restrictions
    assert r.groups["exfoliating_acids"] == "avoid"
    assert r.care_ingredients == {}


def test_use_with_care_for_dry_skin_alone(snapshot):
    answers = {"st1": "st1a", "st2": "st2a", "st3": "st3a", "hp3": "hp3a", "hp6": "hp6a"}
    result = analyse(snapshot, answers, ["hyperpigmentation"])
    assert result.restrictions.groups == {"exfoliating_acids": "use_with_care"}
    assert "lactic_acid" in result.restrictions.care_ingredients
    assert "lactic_acid" not in result.restrictions.avoid_ingredients


def test_exclusions_come_with_reasons(snapshot, cases):
    r = run_case(snapshot, cases["B"]).restrictions
    assert any("sensitive" in reason.lower() for reason in r.avoid_ingredients["fragrance"])
    assert any("pregnan" in reason.lower() for reason in r.avoid_ingredients["retinol"])