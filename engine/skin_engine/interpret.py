from __future__ import annotations

from dataclasses import dataclass
from .snapshot import Snapshot
from .tally import AnswerError, Tally

@dataclass
class SkinProfile:
# Defines the result object returned by skin interpretation
  outcome:str
  skin_type:str |None
#  the chosen skin type, or None if there isn’t enough information.
  runner_up:str |None
# a close second-place skin type, if applicable.
  confidence:str |None
#"declared", "high", "medium", "low", or None.
  sensitive:bool
# whether the user is considered sensitive.
  scores:dict[str,int]
# the scores considered when choosing a skin type.

def interpret_skin(snapshot:Snapshot,tally:Tally,declared:str|None=None,declared_sensitive:bool=False,)->SkinProfile:
#  determines sensitivity and skin type from the quiz tally
# snapshot provides the quiz definitions and rules
# tally contains scores and counts of real answers
# declared  is an optional skin type the user specified.
# declared_sensitive is whether the user specified sensitivity.
  quiz=snapshot.quiz_by_kind("skin_type")
# looks up the skin-type quiz.
  rules={rule["kind"]:rule for rule in quiz["result_rules"]} if quiz else {}
  # turns that quiz’s result rules into a dictionary keyed by each rule’s "kind". 
  # If no quiz exists, rules becomes an empty dictionary.
  threshold=rules.get("sensitive_threshold",{}).get("at_least",3)
  # gets the minimum sensitive score needed to count as sensitive. 
  # If the quiz has no such rule, the default is 3.
  sensitive=declared_sensitive or tally.scores.get("sensitive",0)>=threshold
  # makes the result sensitive if either the user declared sensitivity or 
  # their "sensitive" tally score meets the threshold.
  if declared:
  # checks whether the user provided a skin type.
    if declared not in snapshot.skin_types:
      # rejects a value that isn’t a recognized skin type.
      raise AnswerError(f"Unknown skin type: {declared}")
    return SkinProfile("ok",declared,None,"declared",sensitive,{})
  # returns the declared type directly, marks the confidence as "declared", and provides no runner-up or score breakdown
  scores={skin:tally.scores.get(skin,0) for skin in snapshot.skin_types}
  #  builds a score for every known skin type, using 0 when the tally has no score for it.
  real=tally.real_answers.get(quiz["code"],0) if quiz else 0
# gets the number of real answers in the skin-type quiz. If there is no quiz, it uses 0.
  minimum=rules.get("min_answers",{}).get("min",0)
  # reads the minimum number of real answers required. If no rule exists, the default is 0
  if real<minimum or max(scores.values())==0:
    # checks if there are too few answers or no skin type received any points.
    return SkinProfile("needs_more_answers",None,None,None,sensitive,scores)
  # reports "needs_more_answers", with no selected type or confidence, but includes the scores and sensitivity result.

  order=snapshot.skin_types
  # saves the configured ordering of skin types.
  ranked=sorted(order,key=lambda skin:(-scores[skin],order.index(skin)))
  # sorts types by descending score. If scores tie, the configured order breaks the tie.
  top,second=ranked[0],ranked[1]
  # elects the two highest-ranked types.
  margin=scores[top]-scores[second]
  # calculates how many more points the top type has than the second.

  conflict=rules.get("conflict")
  # looks for a special rule that can override the normal ranking.
  if conflict and _conflict_met(conflict["if"],scores):
    # checks whether that rule exists and its score conditions are satisfied.
    result=conflict["result"]
    # gets the type specified by the rule.
    others=[skin for skin in ranked if skin !=result]
    # others = ... finds the other ranked types, excluding the selected result.
    return SkinProfile("ok",result,others[0],"medium",sensitive,scores)
  # return reports that result with the first alternative as runner-up and "medium" confidence.
  
  within=rules.get("tie_break",{}).get("within",0)
  #  reads how close the top score must be to the second for a runner-up to be included. Its default is 0.
  runner_up=second if margin<=within else None
  # includes the second-place type when the score margin is at or below that threshold; otherwise it uses None.
  confidence="high" if margin >= 4 else "medium" if margin >= 2 else "low"
  #  assigns confidence based on the margin: "high" for at least 4 points, "medium" for at least 2, otherwise "low".
  return SkinProfile("ok", top,runner_up,confidence,sensitive,scores)
# eturn creates the successful profile using the top type, runner-up, confidence, sensitivity, and scores.

def _conflict_met(condition:dict,scores:dict[str,int])->bool:
  #  contains key-value requirements, such as "oily_at_least": 3.
  suffix="_at_least"
  # stores the ending used in those requirement keys.
  return all(scores.get(key[:-len(suffix)],0)>=value for key,value in condition.items())
# checks every requirement. 
# It removes the suffix to get the score name (so "oily_at_least" becomes "oily"), 
# then checks that the score is at least the required value. Missing scores count as 0. 
# all(...) returns True only if every requirement passes.

def concern_bands(snapshot:Snapshot,tally:Tally,concerns:list[str])->dict[str,str]:
  # This function converts concern severity totals into labels such as "mild" or "severe".
  bands={}
  #  starts the result mapping.
  for concern in concerns:
    #  processes each requested concern.
    quiz=snapshot.concern_quiz(concern)
    #  looks up that concern’s quiz.
    if quiz is None:
      # checks whether a published quiz exists for it.
      raise AnswerError(f"No published quiz for concern:{concern}")
    #  reports an error if no such quiz exists.
    rule=next((r for r in quiz["result_rules"] if r["kind"]=="band"),None)
    #  finds the first result rule whose kind is "band". If none exists, rule becomes None
    if rule is None:
      #  skips concerns that have no band rule.
      continue
    total=tally.severity.get(concern,0)
    # gets that concern’s severity, defaulting to 0.
    bands[concern]=next(
      #  chooses the first configured band whose "max" is at least the total.
      (b["band"] for b in rule["bands"] if total <=b["max"]), rule["bands"][-1]["band"]
      #  If no band matches, it uses the final band as a fallback.
    )
  return bands

    