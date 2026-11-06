# goes through the user's answers, apply each chosen option's effects and keep running totals

from __future__ import annotations

from dataclasses import dataclass, field

from .conditions import Context, condition_ok
from .snapshot import Snapshot


class AnswerError(ValueError):
    """The answers sent to the engine do not make sense."""


@dataclass

# asks python to geenrate standard class methods 
class Tally:
  scores:dict[str,int]=field(default_factory=dict)
  # integers total, keyed by score category
  severity:dict[str,int]=field(default_factory=dict)
  # interger totals keyed by concern
  flags:set[str]=field(default_factory=set)
  # a set of flags that have been activated
  cautions:set[str]=field(default_factory=set)
  # a set of caution groups
  required_steps:dict[str,int]=field(default_factory=dict)
  # step priorities,higher number represent higher priority
  red_flags:list[str]=field(default_factory=list)
  # messages or warnings
  real_answers:dict[str,int]=field(default_factory=dict)
  # counts of answered questions by quiz

  def apply(self,effect:list)->None:
      # applies on effect to this tally, expects the effect list to start with a kind followed by its data
      kind=effect[0]
      # read the effect type
      if kind =="score":
        self.scores[effect[1]]=self.scores.get(effect[1],0)+effect[2]
        # adds effect[2] to the score named effect[1], it starts from 0 if there isnt total yet
      elif kind=="severity":
        self.severity[effect[1]]=self.severity.get(effect[1],0)+effect[2]
        # does the same as score
      elif kind=="flag":
        self.flags.add(effect[1])
        # adds the named flag to the set.since sets avoid duplicate
      elif kind=="caution":
        self.cautions.add(effect[1])
        # adds a caution group to its set
      elif kind=="require_step":
        self.required_steps[effect[1]]=max(self.required_steps.get(effect[1],0),effect[2])
        # stres the highest of the existing priority and the new one
      elif kind =="red_flag":
        if effect[1] not in self.red_flags:
          self.red_flags.append(effect[1])
          # adds message only if it isn't already in the list
      else:
        raise ValueError(f"Unknown effect kind: {kind}")

  def merged(self,other:Tally)->Tally:
      # combines two tallies and returns a new one
      result=Tally()
      # ?starts the new tallpy empty
      for part in(self,other):
        # processes both existing tallies
        for key,value in part.scores.items():
          # it loops over scores,severity and real_answers
          # add thier values together for matching keys
          result.scores[key]=result.scores.get(key,0)+value
        for key,value in part.severity.items():
          result.severity[key]=result.severity.get(key,0)+value
        for key,value in part.real_answers.items():
          result.real_answers[key]=result.real_answers.get(key,0)+value
        for key,value in part.required_steps.items():
          # loops pver required_steps keeps the greater priority for each step
          result.required_steps[key]=max(result.required_steps.get(key,0),value)
        result.flags|=part.flags
        result.cautions|=part.cautions
        # add each tally's set members to the result
        for message in part.red_flags:
          # loop copies each message once
          if message not in result.red_flags:
            result.red_flags.append(message)
        
      return result

def tally_answers(
        # processes answers fpr the listed quizzes and returns thier combined effects
      snapshot:Snapshot,
      # data defining quizzes and options
      answers:dict,
      # maps question codes to selected option codes
      quiz_codes:list[str],
      # identifies the quizzes to process
      ctx:Context|None=None,
      #  optionally supplies context for deciding whether a question should be shown.
    )->Tally:

      for question_code in answers:
        #  checks every question code supplied in the answers.
        if question_code not in snapshot.questions:
          #  raises AnswerError if an answer refers to an unknown question.
          raise AnswerError(f"Unknown question: {question_code}")

      tally=Tally()
      # creates an empty result
      for quiz_code in quiz_codes:
        #  looks up each quiz and processes its questions.
        quiz=snapshot.quizzes[quiz_code]
        for question in quiz["questions"]:
          chosen=answers.get(question["code"])
          # gets the user’s answer for that question.
          if not chosen:
            continue
          # skips unanswered questions
          if ctx is not None and not condition_ok(question["show_if"],ctx):
          # skips the answer if a context was supplied and the question’s show_if condition does not pass.
            continue
          options = _validated_options(snapshot, question, chosen)
          # checks the selected option code(s) and returns their option records.
          if any(not option["not_sure"] for option in options):
                  # checks whether at least one selected option is a real answer.
                  tally.real_answers[quiz_code] = tally.real_answers.get(quiz_code, 0) + 1
                  #  increments the count for that quiz once if it has a real answer
          for option in options:
              for effect in option["effects"]:
                      tally.apply(effect)
                      # adds each effect to the tally.
      return tally
def _validated_options(snapshot:Snapshot,question:dict, chosen)->list[dict]:
    #  checks selected option codes and returns the matching option records.
    if isinstance(chosen,str):
    # turns a single code into a list, so the remaining code can handle one or multiple selections consistently
        chosen =[chosen]
    options=[]
    #  starts the list of validated option records.
    for code in dict.fromkeys(chosen):
        #  iterates through the chosen codes while removing duplicates and preserving their order.
        entry=snapshot.options.get(code)
        # looks up the option.
        if entry is None or entry[0]["code"]!=question["code"]:
            # rejects unknown options and options belonging to a different question.
          raise AnswerError(f"Option {code} does not belong to question {question['code']}")
        options.append(entry[1])
        # adds the option record to the result. 
        # The lookup entry is a pair: its question record, then its option record.
    if question["type"]=="single" and len(options) >1:
        #   rejects multiple selected options for a single-answer question.
        raise AnswerError(f"Question {question['code']} takes only one answer")
    if len(options)>1 and any(option["not_sure"] for option in options):
  # rejects combining “Not sure” with another answer.
        raise AnswerError(
              f"'Not sure' cannot be combined with other answers in {question['code']}"
          )
    return options