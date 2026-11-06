# Load the Knowledge snapshot and build lookup tables
# a lookup code allowas you to retrieve information using a unique identifier
from __future__ import annotations
# this lets type like dict|None and -> (the class's own name) work .

import json
# Python can convert this JSON into dictionaries and lists.
from pathlib import Path

class Snapshot:
  # Read-only view of everything the engine knows: rules, products,quizzes

  def __init__(self,data:dict):
    self.data=data
    vocab=data["vocabularies"]
    self.skin_types:list[str]=[t["code"] for t in vocab["skin_types"]]
    self.flags:set[str]={f["code"] for f in vocab["flags"]}
  # why use a set here?  it removes duplicates, provide efficient checks especially when you care if the item exists
    self.step_types:list[str]=[s["code"] for s in vocab["step_types"]]
    self.forms:set[str]=set(vocab["forms"])
    
  # notice no set comprehenson because the values are directly available
    self.ingredients:dict[str,dict]={i["code"]: i for i in data["ingredients"]}
    # this creates a dictionary where the key is the ingredients unique code
    self.products:dict[str,dict]={p["code"]: p for p in data["products"]}
    self.groups:dict[str,dict]={g["code"]: g for g in data["caution_groups"]}
    self.concerns:dict[str,dict]={c["code"]: c for c in data["concerns"]}
    self.quizzes:dict[str,dict]={q["code"]: q for q in data["quizzes"]}
    self.caution_rules:list[dict]=data["caution_rules"]
# this returns a list since they need to be processes as a goup
    self.concern_ingredients:list[dict]=data["concern_ingredients"]
    self.tips:list[dict]=data["advice_tips"]
    self.templates:list[dict]=data["routine_templates"]
    self.scoring:dict=data.get("scoring",{})

    self.questions:dict[str,tuple[dict,dict]]={}
    # /an empty dictionary to store questions the Dictionary key: string ,
    # Dictionary value a tuple with two dictionaries
    self.options:dict[str,tuple[dict,dict]]={}
      # retireves both the parent question and the specific answer option
    for quiz in data["quizzes"]:
      # loops through every quiz
      for question in quiz["questions"]:
        # then loops through the questions
        _add_unique(self.questions,question["code"],(quiz,question))
# passes three arguments: dictionary where the questions will be stored, the unique identifier fot that question
# finallly the quiz and its corresponding question
        for option in question["options"]:
          _add_unique(self.options,option["code"],(question,option))


  @classmethod
  def from_file(cls, path) -> Snapshot:
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))
 # This method retrieves the latest published quiz of a particular type.
  def quiz_by_kind(self, kind: str) -> dict | None:
# since self.quizzes is a dicionary, calling .values() retrieves all the quiz records without their dictionary keys
      return _latest(q for q in self.quizzes.values() if q["kind"] == kind)
# Go through every quiz and return only the quizzes whose kind matches the requested kind.
  def concern_quiz(self,concern:str)->dict|None:
# this is similar to the other method, but it checks if the quiz is a concern quiz and if the concern matches the requested concern.
      return _latest(q for q in self.quizzes.values() if q["kind"]=="concern" and q["concern"]==concern)

# standalone helper function , it identifies the latest publisehd quiz
def _latest(quizzes)->dict|None:
  published=[q for q in quizzes if q["status"]=="published"]
  # this creates a new list containng only the quizzes that have a status of "published"
  return max(published,key=lambda q:q["version"],default=None)
# find the highest version number among the published quizzes and return that quiz. 
# If there are no published quizzes, return None.

# This function ensures that every question and option has a unique code.
def _add_unique(table:dict,key:str,value)->None:
  # check if the key exist in the dictionary. If it does, raise a ValueError to indicate that there is a duplicate code in the snapshot.
  if key in table:
    raise ValueError(f"Duplicate code in snapshot: {key}")
# If the key doesn't already exist, the function stores the value in the dictionary.
  table[key]=value