from skin_engine.interpret import concern_bands, interpret_skin
from skin_engine.tally import Tally, tally_answers
#  imports the tally data class and the function that calculates it from answers.

def skin(snapshot, answers, **kw):
#  defines a shortcut for the repeated setup. 
# **kw allows extra named arguments, such as a declared skin type.
    tally = tally_answers(snapshot, answers, ["skin_type_v1"])
    #  calculates a tally from answers to the skin-type quiz.
    return interpret_skin(snapshot, tally, **kw)
# passes that tally to the interpretation function and forwards any extra keyword arguments.

def test_clear_combination_skin(snapshot):
    # supplies answers expected to clearly indicate combination skin. 
    answers = {"st1": "st1d", "st2": "st2d", "st3": "st3c", "st4": "st4b"}
    profile = skin(snapshot, answers)
# The assertions check the result, high confidence with no runner-up, and that sensitivity is false.
    assert profile.skin_type == "combination"
    assert (profile.confidence, profile.runner_up) == ("high", None)
    assert profile.sensitive is False


def test_dry_and_sensitive(snapshot):
# supplies answers expected to indicate dry skin and meet the sensitivity threshold.
#  It checks both results.
    answers = {"st1": "st1a", "st2": "st2a", "st3": "st3a", "st5": "st5c", "st6": "st6b"}
    profile = skin(snapshot, answers)
    assert profile.skin_type == "dry"
    assert profile.sensitive is True


def test_sensitivity_threshold(snapshot):
    base = {"st1": "st1a", "st2": "st2a", "st3": "st3a"}
    # base holds answers shared by both cases.
    #  creates a new dictionary containing the base answers plus the specified additional answers.
    assert skin(snapshot, {**base, "st5": "st5b", "st6": "st6b"}).sensitive is False  # 1 + 1 = 2
    # checks that sensitivity points total 2, below the threshold.
    assert skin(snapshot, {**base, "st5": "st5b", "st6": "st6c"}).sensitive is True  # 1 + 2 = 3
# checks that the points total 3, meeting the threshold.


def test_too_few_real_answers(snapshot):
    answers = {"st1": "st1e", "st2": "st2e", "st3": "st3e", "st4": "st4d"}
    assert skin(snapshot, answers).outcome == "needs_more_answers"
    # “Not sure” choices and checks that the result requests more answers.
    assert skin(snapshot, {"st1": "st1a", "st2": "st2a"}).outcome == "needs_more_answers"
    #  has only two answers and checks the same outcome.


def test_oily_and_dry_together_means_combination(snapshot):
    # checks a special rule where combined oily and dry signals produce combination skin. 
    profile = skin(snapshot, {"st1": "st1a", "st2": "st2a", "st3": "st3d"})
    # It also checks medium confidence and dry as the runner-up.
    assert profile.skin_type == "combination"
    assert profile.confidence == "medium"
    assert profile.runner_up == "dry"


def test_close_call_shows_a_runner_up(snapshot):
    # hecks that close scores produce a runner-up. expected dry and normal totals;
    profile = skin(snapshot, {"st1": "st1a", "st2": "st2b", "st4": "st4a"})  # dry 4, normal 3
    assert (profile.skin_type, profile.runner_up, profile.confidence) == ("dry", "normal", "low")
    # checks skin type, runner-up, and confidence together.


def test_declared_skin_type_skips_the_quiz(snapshot):
    # passes no quiz answers but declares oily skin and sensitivity. 
    profile = skin(snapshot, {}, declared="oily", declared_sensitive=True)
    assert (profile.skin_type, profile.confidence, profile.sensitive) == ("oily", "declared", True)
    # It checks that the declared type is returned with "declared" confidence and sensitivity set to true.


def test_concern_bands(snapshot):
    #  checks how severity totals map to named bands.
    def bands(concern, total):
  # reates a Tally with a severity total for one concern, calls concern_bands, and returns that concern’s band.
        return concern_bands(snapshot, Tally(severity={concern: total}), [concern])[concern]

    assert [bands("dehydration", n) for n in (0, 2, 3, 5, 6, 11)] == [
        # tests several totals, verifying the boundaries between mild, moderate, and severe.
        "mild", "mild", "moderate", "moderate", "severe", "severe",
    ]
    assert [bands("hyperpigmentation", n) for n in (1, 2, 3)] == ["mild", "moderate", "severe"]
    # checks that totals 1, 2, and 3 map respectively to mild, moderate, and severe.