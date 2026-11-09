"""Write the human-readable parts: why a product, and which tips apply."""  # module docstring: explain why a product was chosen and which advice is relevant

from __future__ import annotations  # allow postponed evaluation of type hints like tuple[str, list[str]]

from .conditions import Context, condition_ok  # import the user context and condition evaluator
from .scoring import ProductScore  # import the product score object that stores ingredient matches
from .snapshot import Snapshot  # import the dataset that names ingredients and concerns

MAX_REASONS = 3  # only show the top three reasons in a product summary


def explain_pick(snapshot: Snapshot, score: ProductScore, ctx: Context) -> tuple[str, list[str]]:  # create a human-readable explanation for one product
    """Return (summary, reasons) for one product."""  # docstring: returns a summary sentence and the detailed reasons it was picked
    if not score.matches:  # if no helpful ingredient matches were found, say it suits the user's skin and avoids flagged ingredients
        text = f"Suits {ctx.skin_type} skin and avoids the ingredients we flagged for you."  # friendly fallback sentence
        return text, [text]  # return both the summary and the list of reasons

    top = sorted(score.matches, key=lambda match: -match.points)[:MAX_REASONS]  # sort by strongest match and keep only the top three
    reasons = [match.reason for match in top]  # collect the human-readable reasons from the strongest matches

    names_by_concern: dict[str, list[str]] = {}  # map each concern to the ingredient names that help it
    for match in top:  # examine each of the strongest matches
        name = snapshot.ingredient_name(match.ingredient)  # look up the ingredient's display name
        names_by_concern.setdefault(match.concern, []).append(name)  # group ingredients by concern

    clauses = []  # list of phrases such as "niacinamide and hyaluronic acid, which help with dehydration"
    for concern, names in names_by_concern.items():  # for each concern group
        verb = "helps" if len(names) == 1 else "help"  # singular/plural agreement for the verb
        concern_name = snapshot.concerns[concern]["name"].lower()  # human-readable concern label, lowercased
        clauses.append(f"{_join(names)}, which {verb} with {concern_name}")  # add one clause for this concern
    return "Contains " + "; ".join(clauses) + ".", reasons  # build the final summary sentence and return the reasons list


def select_tips(snapshot: Snapshot, ctx: Context) -> list[dict]:  # choose all advice tips that apply to this user
    """The advice tips that apply to this user's concerns and answers."""  # docstring: only relevant tips are returned
    chosen = []  # list of selected tip dictionaries
    for tip in snapshot.tips:  # inspect every available tip
        if tip["concern"] is not None and tip["concern"] not in ctx.concerns:  # skip tips for different concerns
            continue  # ignore this tip because it's not relevant to the user's concerns
        if condition_ok(tip["condition"], ctx):  # only include tips whose condition matches the user's context
            chosen.append(  # store the tip in the final list
                {
                    "code": tip["code"],  # unique code for the tip
                    "text": tip["text"],  # human-readable text to show the user
                    "source": tip["source"],  # where the tip came from
                    "needs_review": tip["needs_review"],  # whether a human should review it
                }
            )
    return chosen  # return all applicable tips, in order


def _join(names: list[str]) -> str:  # helper to format a name list nicely in English
    """['a'] -> 'a'; ['a', 'b'] -> 'a and b'; ['a', 'b', 'c'] -> 'a, b and c'."""  # docstring shows the formatting rules
    if len(names) <= 1:  # single-item list stays as-is
        return "".join(names)  # join without punctuation
    return ", ".join(names[:-1]) + " and " + names[-1]  # format as comma-separated list with final 'and'
