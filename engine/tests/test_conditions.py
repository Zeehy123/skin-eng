from skin_engine.conditions import Context, condition_ok,validate_condition

def ctx(**kw):
#  is a small helper that creates a Context from keyword arguments. 
# For example, ctx(flags={"a"}) creates a context with flag "a".
  return Context(**kw)

def test_empty_condition_always_passes():
# confirms that an empty condition {} and None both pass. 
# In this evaluator, no condition means there are no restrictions.
  assert condition_ok({},ctx())
  assert condition_ok(None,ctx())

def test_flag_keys():
# test_flag_keys checks the three flag rules:
# all_flags: every listed flag must be present.
# any_flags: at least one listed flag must be present.
# none_flags: none of the listed flags may be present.
  c=ctx(flags={"a","b"})
  assert condition_ok({"all_flags":["a","b"]},c)
  assert not condition_ok({"all_flags":["a","z"]},c)
  assert condition_ok({"any_flags":["z","b"]},c)
  assert  not condition_ok({"any_flags":["z"]},c)
  assert condition_ok({"none_flags":["z"]},c)
  assert not condition_ok({"none_flags":["a"]},c)

def test_skin_type_needs_a_known_type():
#  checks that a condition listing "dry" passes for a dry context, 
# and fails for oily skin or when the context has no skin type.
  assert condition_ok({"skin_types":["dry"]},ctx(skin_type="dry"))
  assert not condition_ok({"skin_types":["dry"]},ctx(skin_type="oily"))
  assert not condition_ok({"skin_types":["dry"]},ctx(skin_type=None))

def test_sensitive_must_match_exactly():
# checks that the condition’s sensitive value must match the context’s value.
  assert condition_ok({"sensitive":True},ctx(sensitive=True))
  assert not condition_ok({"sensitive":True},ctx(sensitive=False))
  assert condition_ok({"sensitive":False},ctx(sensitive=False))

def test_concerns_and_bands():
# checks concern matching and concern severity bands. 
# A condition listing multiple concerns passes if at least one is in the context. 
# A band condition passes when the context’s band for that concern is in the allowed list.
  c=ctx(concerns=["dehydration"],bands={"dehydration":"severe"})
  assert condition_ok({"concerns":["dehydration","acne"]},c)
  assert not condition_ok({"concerns":["acne"]},c)
  assert condition_ok({"concern_bands":{"dehydration":["severe"]}},c)
  assert not condition_ok({"concern_bands":{"dehydration":["mild"]}},c)

def test_any_of_gives_or_and_other_keys_still_apply():
# checks that any_of works as an “at least one subcondition passes” rule.
# It also confirms that other keys still apply: here, the skin type must be "dry" 
# even if one of the any_of subconditions passes.
  cond={"any_of":[{"all_flags":["a"]},{"all_flags":["b"]}],"skin_types":["dry"]}
  assert condition_ok(cond,ctx(flags={"b"},skin_type="dry"))
  assert not condition_ok(cond,ctx(flags={"c"},skin_type="dry"))
  assert not condition_ok(cond,ctx(flags={"b"},skin_type="oily"))

def test_validator_find_typos(snapshot):
# gives the validator a condition containing several invalid values or keys, 
# then checks that it reports four problems. snapshot is supplied by a pytest fixture.
   problems = validate_condition(
        {"any_flags": ["over_exfoliaton"], "skin_types": ["drry"], "bogus": 1, "sensitive": "yes"},
        snapshot,
    )
   assert len(problems) == 4

def _all_seed_conditions(snapshot):
# this is a helper that yields conditions from different parts of the seed data: quiz questions, 
# caution rules, concern ingredients and their boosts, tips, and templates.
  for quiz in snapshot.quizzes.values():
    for question in quiz["questions"]:
      yield question["show_if"]
  for rule in snapshot.caution_rules:
    yield rule["condition"]
  for rule in snapshot.concern_ingredients:
    yield rule["condition"]
    for boost in rule.get("boosts",[]):
      yield boost["condition"]
  for tip in snapshot.tips:
    yield tip["condition"]
  for template in snapshot.templates:
    yield template["condition"]


def test_every_condition_in_the_seed_is_valid(snapshot):
# validates each yielded seed condition and asserts there are no errors.
#  If one fails, pytest also shows the condition that caused the failure.
  for cond in _all_seed_conditions(snapshot):
    assert validate_condition(cond,snapshot)==[],cond
    
    