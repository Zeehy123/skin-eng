import pytest
from skin_engine.snapshot import Snapshot

def test_loads_the_seed(snapshot):
  # creates a dictionary of products
  # len() counts the number of entries in a collection
  # checks that the loaded snapshot contains 14 products
  assert len(snapshot.products)==14
  # when you convert dictionary to set it removes the keys
  assert set(snapshot.concerns)=={"hyperpigmentation","dehydration"}
  # checks the skin types are loaded correctly and in the expected order
  assert snapshot.skin_types==["normal","dry","oily","combination"]

# This test checks the relationship between quiz questions and their answer options.
def test_option_lookup_points_back_to_its_question(snapshot):
  question,option=snapshot.options["dh6a"]
  assert question["code"]=="dh6"
  assert option["text"]=="Yes"

def test_newest_published_quiz_is_found(snapshot):
    assert snapshot.quiz_by_kind("skin_type")["code"] == "skin_type_v1"
    assert snapshot.concern_quiz("dehydration")["code"] == "dehydration_v1"
    assert snapshot.concern_quiz("acne") is None


def test_duplicate_code_are_rejected(snapshot):
  broken={**snapshot.data,"quizzes":snapshot.data["quizzes"]+snapshot.data["quizzes"]}
  with pytest.raises(ValueError, match="Duplicate code"):
    Snapshot(broken)