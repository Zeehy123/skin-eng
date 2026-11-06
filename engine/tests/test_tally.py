import pytest

from skin_engine.conditions import Context
# import the user context used to describe  the user such as skin type
from skin_engine.tally import AnswerError, Tally,tally_answers



def test_effect_add_up(snapshot):
  # defines a test and pytest supplies snapshot though a fixture
  answers={"st1":["st1a"],"st2":["st2a"],"st4":["st4a"],"st5":["st5c"]}
#  maps question codes to the selected option codes.
  tally=tally_answers(snapshot,answers,["skin_type_v1"])
  # processes those answers for the skin_type quiz
  assert tally.scores=={"dry":6,"normal":1,"sensitive":3}
  # checks that the oprions score feects added up to exactly those totals

def test_every_effect_kind_is_applied(snapshot):
  answers={"dh1":"dh1d","hp4":"hp4c","hp6":"hp6b"}
  # seleects options from the dehydration and hyperpigmentation quizzes
  tally=tally_answers(snapshot,answers,["dehydration_v1","hyperpigmentation_v1"])
  # processes both quizzes together
  assert tally.severity=={"dehydration":2}
  # checks one kind of accumulated effect: concern severity,
  #  flags, cautions, and required steps.
  assert tally.flags=={"possible_barrier_damage"}
  assert tally.cautions=={"all_actives"}
  assert tally.required_steps=={"sunscreen":3}
  assert len(tally.red_flags)==1
  #  checks that one red-flag message was recorded.

def test_not_sure_does_not_count_as_a_real_answer(snapshot):
  answers={"st1":["st1e"],"st2":["st2a"]}
  # includes a “Not sure” choice for one question and a real choice for another.
  tally=tally_answers(snapshot,answers,["skin_type_v1"])
  assert tally.real_answers=={"skin_type_v1":1}
  # checks that only one real answer is counted; “Not sure” does not increase that count.

def test_bad_answers_are_rejected(snapshot):
  quizzes=["skin_type_v1","dehydration_v1"]
  with pytest.raises(AnswerError,match="Unknown question"):
    # block expects a particular invalid answer to raise AnswerError:
    tally_answers(snapshot,{"zz9":["a"]},quizzes)
    # "zz9" is an unknown question.
  with pytest.raises(AnswerError,match="does not belong"):
    tally_answers(snapshot,{"st1":["st2a"]},quizzes)
    # "st2a" does not belong to question "st1".
  with pytest.raises(AnswerError,match="only one answer"):
    tally_answers(snapshot,{"st1":["st1a","st1b"]},quizzes)
    # Two choices are supplied for a single-answer question.
  with pytest.raises(AnswerError,match="Not sure"):
    tally_answers(snapshot,{"dh2":["dh2b","dh2e"]},quizzes)
    # “Not sure” is combined with another answer.


def test_multiple_choice_adds_every_chosen_option(snapshot):
  tally=tally_answers(snapshot,{"dh2":["dh2b","dh2c","dh2b"]},["dehydration_v1"])
  #  with two distinct options plus a duplicate option for a multiple-choice question.
  assert tally.flags=={"over_exfoliation","dry_air"}
#  checks that the selected options’ flags are included in the tally.

def test_hidden_questions_are_ignored(snapshot):
  answers={"dh6":["dh6a"]}
  #  selects an option for question "dh6", noted as visible only for oily or combination skin.
  dry=Context(skin_type="dry")
  # dry and oily create contexts with different skin types.
  oily=Context(skin_type="oily")
  assert tally_answers(snapshot,answers,["dehydration_v1"],dry).flags==set()
  # checks that the answer is ignored for dry skin.
  assert tally_answers(snapshot,answers,["dehydration_v1"],oily).flags=={"oily_dehydrated"}
  # The second checks that it contributes the "oily_dehydrated" flag for oily skin.

def test_merge_combines_two_tallies(snapshot):
  a=Tally(scores={"dry":2},flags={"x"},required_steps={"sunscreen":1})
  # a and b create two tallies with overlapping scores and step priorities, plus different flags.
  b=Tally(scores={"dry":3},flags={"y"},required_steps={"sunscreen":3},red_flags=["r"])
  merged=a.merged(b)
  # merged = a.merged(b) combines them.
  #   The assertions  check that scores are added, flags are combined, 
  # the higher step priority is kept, and the red-flag message appears in the result.
  assert merged.scores == {"dry": 5}
  assert merged.flags == {"x", "y"}
  assert merged.required_steps == {"sunscreen": 3}
  assert merged.red_flags == ["r"]


