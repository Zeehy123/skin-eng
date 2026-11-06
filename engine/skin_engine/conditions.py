
# This file answers one question,
#  over and over: “does this rule apply to this user?”
#  Everything in the engine that says “only when...” (a question that appears only for oily skin, an ingredient that’s only recommended when there’s no irritation, a tip that appears only for severe dehydration) uses it.
from __future__ import annotations

from dataclasses import dataclass, field

KNOWN_KEYS={
  # This is the vocabulary of the condition language: the only words a condition may use. 
  # It’s a set because we only ever ask “is this word allowed?”, and sets answer that instantly. It’s used by validate_condition further down, to catch a misspelled key such as "any_flag" (missing the s), which would otherwise be silently ignored and make the rule apply to everyone.
    "all_flags",
    "any_flags",
    "none_flags",
    "skin_types",
    "sensitive",
    "concerns",
    "concern_bands",
    "any_of",
}
# facts about the user-CONTEXT
@dataclass
# a condition is a set of question and Context holds answer to those questions

class Context:
  flags:set[str]=field(default_factory=set)
  skin_type:str |None=None
  sensitive:bool=False
  concerns:list[str]=field(default_factory=list)
  bands:dict[str,str]=field(default_factory=dict)

# the evaluator 
# it takes a condtion and a context and returns True of false
def condition_ok(cond:dict|None, ctx:Context)->bool:
  if not cond:
    return True
  if "any_of" in cond and not any(condition_ok(sub,ctx) for sub in cond["any_of"]):
# any_of holds a list of conditions and atleast 1 must pass.
# checks each subcondition against the same context
    return False
  if not set(cond.get("all_flags",[]))<=ctx.flags:
# this returns a list , or an empty list if the key is missing,
# <= between sets means is a subset of ;that is everyitem on the left is in the right
    return False
  any_flags=cond.get("any_flags")  
# 
  if any_flags and not (set(any_flags)&ctx.flags):
# checks whether any requested flag appears in the context.
#  & finds the shared flags. If the list is nonempty and there are no shared flags, the condition fails.
    return False
  if set(cond.get("none_flags",[]))&ctx.flags:
# checks for flags that must not be present. Any overlap makes the condition fail.
    return False
  skin_types = cond.get("skin_types")
  if skin_types and ctx.skin_type not in skin_types:
    return False
  if "sensitive" in cond and cond["sensitive"]!=ctx.sensitive:
    # checks sensitivity only when the condition explicitly specifies it
    # If the requested value differs from the context, the condition fails.
    return False
  concerns=cond.get("concerns")
  if concerns and not (set(concerns)&set(ctx.concerns)):
    # atleast one of the concerns in the condition must be in the context
    return False

  for concern, bands in cond.get("concern_bands",{}).items():
    # for loop checks each pair : the user's bands for that concern must be in if the allowed ones.
    if ctx.bands.get(concern) not in bands:
  # concern bands maps a concern to its allowed severity bands,
      return False 
  return True

# validate_condition:
#  checks whether a condition is well-formed, not whether it applies to a particular user. 
# It returns a list of error messages; an empty list means no problems were found.
def validate_condition(cond,snapshot)->list[str]:
# Accepts a condition and a snapshot containing the allowed flags, skin types, and concerns.
  if not isinstance(cond,dict):
  #rejects anything that isn’t a dictionary and returns an error immediately.
    return ["condition must be an object"]
  problems=[f"unknown key:{key}" for key in cond if key not in KNOWN_KEYS]
  # collects a message for each key in cond that isn’t in KNOWN_KEYS.
  for key in ("all_flags","any_flags","none_flags"):
    problems+=[f"unknown flag in {key}:{code}"
               for code in cond.get(key,[])
               if code not in snapshot.flags]
# oop checks each listed flag against the flags known to the snapshot. 
# Unknown ones add error messages to problems.
  problems+=[f"unknown skin_types:{code}"
               for code in cond.get("skin_types",[])
               if code not in snapshot.skin_types]

  problems+=[f"unknown concern:{code}"
             for code in cond.get("concerns",[])
             if code not in snapshot.concerns]

  problems+=[f"unknown concern in concern_bands:{code}"
             for code in cond.get("concern_bands",[])
             if code not in snapshot.concerns]
  if "sensitive" in cond and not isinstance(cond["sensitive"],bool):
  #sensitive check ensures that, if provided, its value is a Boolean (True or False); otherwise it adds an error.
    problems.append("sensitive must be true or false")
    # .append adds one item and += adds a list of items
  for sub in cond.get("any_of",[]):
  # loop recursively validates each condition inside any_of, adding its errors to the same list.
    problems+=validate_condition(sub,snapshot)
  return problems