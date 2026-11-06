# """Work out what must be avoided, and why.

from __future__ import annotations

from dataclasses import dataclass, field

from .conditions import Context, condition_ok
# import the user context and the function that checks whethere a condiiton applies
from .snapshot import Snapshot
# object containing skincare data and rules
from .tally import Tally
# the accumulated quiz results

AVOID = "avoid"
# something to avoid
CARE = "use_with_care"
# somthing to be used with care


@dataclass
class Restrictions:
# defines a container for the restrictions this function calculates
    groups: dict[str, str] = field(default_factory=dict)  # group -> level
    # maps each group code to its restriction level
    avoid_ingredients: dict[str, list[str]] = field(default_factory=dict)  # ingredient -> reasons
    # maps ingredients codes to reasons to avoid them
    avoid_forms: dict[str, list[str]] = field(default_factory=dict)  # form -> reasons
    # maps producr forms ro reasons to avoid them
    care_ingredients: dict[str, list[str]] = field(default_factory=dict)  # ingredient -> reasons
    # maps ingredient codes to reasons to use them with care

    def avoided_groups(self) -> list[str]:
        #  declares a method that returns a list of group codes.
        return sorted(group for group, level in self.groups.items() if level == AVOID)
    # The generator expression selects only groups whose level equals AVOID


def compute_restrictions(snapshot: Snapshot, tally: Tally, ctx: Context) -> Restrictions:
    # defines the function. It uses skincare data, quiz totals,
    #  and user context to build and return restrictions.
    avoid_groups: dict[str, list[str]] = {}
    #  maps a group code to the reasons behind its restriction.
    care_groups: dict[str, list[str]] = {}

    for group in sorted(tally.cautions): 
        # Processes caution groups triggered directly by quiz answers, in sorted order
        #  groups the quiz answers triggered directly
        avoid_groups.setdefault(group, []).append("Your quiz answers rule this out.")
# Gets the group’s reasons list, creating it if needed, then adds a reason. These direct quiz cautions count as “avoid.”
    for rule in snapshot.caution_rules:  # groups triggered by flags, skin type or sensitivity
        if condition_ok(rule["condition"], ctx):
            # Applies the rule only if its condition passes for this user’s context.
            target = avoid_groups if rule["level"] == AVOID else care_groups
            # Chooses the avoid-reasons dictionary for an "avoid" rule; otherwise, chooses the care-reasons dictionary
            target.setdefault(rule["group"], []).append(rule["reason"])
            # Creates a reasons list for the rule’s group if needed, then adds the rule’s explanation.

    for group in avoid_groups:  # avoid always beats use-with-care
        # Removes any “use with care” entry for a group that is also marked “avoid.” In other words, avoid takes precedence.
        care_groups.pop(group, None)

    result = Restrictions()
# Builds the group-to-level mapping. It first adds care groups, then avoid groups. 
    result.groups = {**{g: CARE for g in care_groups}, **{g: AVOID for g in avoid_groups}}
# If a group appeared in both, the avoid entry would override the care entry.


    for code, reasons in avoid_groups.items():
        # Processes each group to avoid and its reasons.
        group = snapshot.groups[code]
        for ingredient in group["ingredients"]:
            # Adds the group’s avoid reasons to every ingredient in that group. extend adds all reasons in the list.
            result.avoid_ingredients.setdefault(ingredient, []).extend(reasons)
        for form in group["forms"]:
            result.avoid_forms.setdefault(form, []).extend(reasons)

    for code, reasons in care_groups.items():
        for ingredient in snapshot.groups[code]["ingredients"]:
            result.care_ingredients.setdefault(ingredient, []).extend(reasons)

    for rule in snapshot.concern_ingredients:  # 'avoid' rows written per concern
        if (
            rule["effect"] == AVOID
            and rule["concern"] in ctx.concerns
            and condition_ok(rule["condition"], ctx)
        ):
            result.avoid_ingredients.setdefault(rule["ingredient"], []).append(rule["reason"])
    return result