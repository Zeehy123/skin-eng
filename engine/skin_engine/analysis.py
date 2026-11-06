"""Phase one: understand the user. Phase two (M1b) picks the products."""

from __future__ import annotations

from dataclasses import dataclass, field

from .cautions import Restrictions, compute_restrictions
from .conditions import Context
from .interpret import SkinProfile, concern_bands, interpret_skin
from .snapshot import Snapshot
from .tally import AnswerError, Tally, tally_answers

RECOMMEND = "recommend"
REFER = "refer_to_professional"
NEEDS_MORE = "needs_more_answers"


@dataclass
class Analysis:
    outcome: str
    profile: SkinProfile
    concerns: list[str]
    tally: Tally
    ctx: Context
    restrictions: Restrictions = field(default_factory=Restrictions)
    referral_reasons: list[str] = field(default_factory=list)


def analyse(
    snapshot: Snapshot,
    answers: dict,
    concerns: list[str],
    declared_skin_type: str | None = None,
    declared_sensitive: bool = False,
) -> Analysis:
    for concern in concerns:
        if concern not in snapshot.concerns:
            raise AnswerError(f"Unknown concern: {concern}")

    # Phase 1: profile and skin-type quizzes. They never depend on anything else.
    base_quizzes = [
        quiz["code"]
        for quiz in (snapshot.quiz_by_kind("profile"), snapshot.quiz_by_kind("skin_type"))
        if quiz
    ]
    base = tally_answers(snapshot, answers, base_quizzes)
    profile = interpret_skin(snapshot, base, declared_skin_type, declared_sensitive)

    # Phase 2: concern quizzes. Their show_if rules may use the skin type found above.
    early = Context(
        flags=set(base.flags),
        skin_type=profile.skin_type,
        sensitive=profile.sensitive,
        concerns=list(concerns),
    )
    concern_quizzes = [snapshot.concern_quiz(c)["code"] for c in concerns]
    tally = base.merged(tally_answers(snapshot, answers, concern_quizzes, early))

    ctx = Context(
        flags=set(tally.flags),
        skin_type=profile.skin_type,
        sensitive=profile.sensitive,
        concerns=list(concerns),
    )

    if tally.red_flags:  # a red flag beats everything else
        return Analysis(
            REFER, profile, list(concerns), tally, ctx, referral_reasons=list(tally.red_flags)
        )
    if profile.outcome != "ok":
        return Analysis(NEEDS_MORE, profile, list(concerns), tally, ctx)

    ctx.bands = concern_bands(snapshot, tally, concerns)
    restrictions = compute_restrictions(snapshot, tally, ctx)
    return Analysis(RECOMMEND, profile, list(concerns), tally, ctx, restrictions)