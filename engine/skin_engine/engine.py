# """The front door: answers in, a complete recommendation out."""  # module docstring: this file takes user answers and returns a full recommendation object

from __future__ import annotations  # allow forward references in type hints for dataclasses and functions

from dataclasses import asdict, dataclass, field  # import helpers for dataclass default values and JSON conversion

from .analysis import RECOMMEND, analyse  # import the analysis result plus the constant meaning 'recommend'
from .eligibility import exclusion_reasons  # import rule that filters out ineligible products
from .explain import select_tips  # import tip selection for the final result
from .routine import RoutineStep, build_routine  # import routine-building logic and the step type
from .scoring import ScoringConfig  # import scoring configuration from the snapshot
from .snapshot import Snapshot  # import the data source of products, rules, and quizzes


@dataclass  # create a result object to carry the final recommendation summary
class Result:  # the output returned to callers
    outcome: str  # "recommend", "refer_to_professional" or "needs_more_answers"
    skin_type: str | None  # top skin type or None if not enough information yet
    runner_up: str | None  # second-place skin type if relevant
    confidence: str | None  # confidence level in the chosen skin type
    sensitive: bool  # whether the user is considered sensitive
    concerns: list[str]  # user concerns being assessed
    bands: dict[str, str]  # concern -> severity band
    flags: list[str]  # trigger flags discovered from the answers
    template: str | None = None  # routine template code, if a routine was built
    routine: list[RoutineStep] = field(default_factory=list)  # list of steps in the routine
    tips: list[dict] = field(default_factory=list)  # selected explanations/tips for the user
    excluded: dict[str, list[str]] = field(default_factory=dict)  # product -> reasons it was rejected
    referral_reasons: list[str] = field(default_factory=list)  # reasons that require a professional referral
    warnings: list[str] = field(default_factory=list)  # warnings about missing products in required routine steps

    def to_dict(self) -> dict:  # convert the dataclass into a plain JSON-serializable dict
        """Plain dictionaries and lists only, so it can be sent as JSON."""  # docstring says the output must be JSON-safe
        return asdict(self)  # convert fields recursively into standard Python dict/list structures


def recommend(  # main entry point: process answers and create a final recommendation
    snapshot: Snapshot,  # the product and quiz data source
    answers: dict,  # mapping of question codes to selected answers
    concerns: list[str],  # list of concerns under consideration
    declared_skin_type: str | None = None,  # optional user-declared skin type
    declared_sensitive: bool = False,  # whether the user declared sensitivity
) -> Result:  # returns the final recommendation summary object
    analysis = analyse(snapshot, answers, concerns, declared_skin_type, declared_sensitive)  # run the full analysis pipeline for the user
    profile = analysis.profile  # grab the skin profile produced by the analysis step
    result = Result(  # create an initial Result instance with the profile details
        outcome=analysis.outcome,  # whether the recommendation is ready or not
        skin_type=profile.skin_type,  # selected skin type
        runner_up=profile.runner_up,  # second-best match, if any
        confidence=profile.confidence,  # confidence for the selected skin type
        sensitive=profile.sensitive,  # whether the user is sensitive
        concerns=list(concerns),  # store a copy of the requested concerns
        bands=dict(analysis.ctx.bands),  # map concern -> band for display
        flags=sorted(analysis.ctx.flags),  # list of applicable flags in sorted order
    )
    if analysis.outcome != RECOMMEND:  # if the analysis says we should not recommend yet, stop here
        result.referral_reasons = list(analysis.referral_reasons)  # copy referral reasons into the result
        return result  # return early because no routine can be built safely

    ctx, restrictions = analysis.ctx, analysis.restrictions  # unpack the computed user context and restrictions
    eligible = []  # create a list of products that pass all restrictions
    for code, product in snapshot.products.items():  # inspect every product one by one
        reasons = exclusion_reasons(snapshot, product, ctx, restrictions)  # see if this product is blocked
        if reasons:  # if the product is blocked, record why
            result.excluded[code] = reasons  # save the rejection reasons keyed by product code
        else:  # otherwise, it is eligible to be considered for the routine
            eligible.append(code)  # add to the list of acceptable products

    config = ScoringConfig.from_snapshot(snapshot)  # load the product scoring configuration for the routine builder
    template, routine = build_routine(snapshot, analysis, eligible, config)  # choose a routine template and assemble steps
    result.template = template["code"]  # store the template code used for the final routine
    result.routine = routine  # store the built routine steps
    result.tips = select_tips(snapshot, ctx)  # choose explanation tips relevant to the user context
    result.warnings = [  # build warnings for any required step that has no product picked
        f"No suitable product for the {step.step} step."  # message explaining the missing product for this routine step
        for step in routine  # examine each step in the routine
        if step.pick is None and step.required  # include only required steps without a selected product
    ]
    return result  # return the full recommendation payload to the caller
